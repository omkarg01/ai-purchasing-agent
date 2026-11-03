from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import EvaluationRequest, RecommendationResponse
from app.database.session import get_db
from app.decision_engine import (
    BudgetInput,
    DemandForecastInput,
    EngineInput,
    InventoryInput,
    OpenPurchaseOrderInput,
    RecommendationToEvaluate,
    SupplierProductInput,
    evaluate_purchasing_decision,
)
from app.models.demand_forecast import DemandForecast
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_recommendation import PurchaseRecommendation
from app.models.purchasing_budget import PurchasingBudget
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=List[RecommendationResponse])
def list_recommendations(
    db: Session = Depends(get_db),
):
    """Returns all purchase recommendations."""
    return (
        db.query(PurchaseRecommendation)
        .order_by(PurchaseRecommendation.id.asc())
        .all()
    )


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
):
    recommendation = (
        db.query(PurchaseRecommendation).filter_by(id=recommendation_id).first()
    )
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase recommendation not found",
        )
    return recommendation


@router.post(
    "/{recommendation_id}/evaluate",
    response_model=RecommendationResponse,
)
def evaluate_recommendation(
    recommendation_id: int,
    payload: EvaluationRequest,
    db: Session = Depends(get_db),
):
    """Stores the agent's evaluation results alongside the original recommendation.

    Invariants enforced:
    - Writes proposed quantity/supplier to agent_suggested_* fields only.
    - Never overwrites recommended_quantity or the original supplier_id.
    - Keeps agent_decision strictly separate from approval status.
    """
    recommendation = (
        db.query(PurchaseRecommendation).filter_by(id=recommendation_id).first()
    )
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase recommendation not found",
        )

    # Validate suggested supplier exists if provided
    if payload.agent_suggested_supplier_id is not None:
        supplier = (
            db.query(Supplier)
            .filter_by(id=payload.agent_suggested_supplier_id)
            .first()
        )
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Suggested supplier id {payload.agent_suggested_supplier_id} does not exist",
            )

    # Capture original fields to guarantee they remain untouched
    original_recommended_quantity = recommendation.recommended_quantity
    original_supplier_id = recommendation.supplier_id
    original_status = recommendation.status

    # Write ONLY to agent_suggested_* fields and evaluation metadata
    recommendation.agent_decision = payload.agent_decision
    recommendation.agent_suggested_quantity = payload.agent_suggested_quantity
    recommendation.agent_suggested_supplier_id = payload.agent_suggested_supplier_id
    recommendation.agent_reasoning = payload.agent_reasoning
    recommendation.evaluated_at = payload.evaluated_at or datetime.now(timezone.utc)

    # Protect original fields & approval status
    assert recommendation.recommended_quantity == original_recommended_quantity
    assert recommendation.supplier_id == original_supplier_id
    assert recommendation.status == original_status

    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.post(
    "/{recommendation_id}/approve",
    response_model=RecommendationResponse,
)
def approve_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
):
    """Approves a purchase recommendation after human review.

    Invariants enforced:
    - Only recommendations in 'PENDING_APPROVAL' status can be approved.
    - Transitions status strictly to 'APPROVED'.
    - Preserves all original recommendation fields and agent evaluation fields.
    """
    recommendation = (
        db.query(PurchaseRecommendation).filter_by(id=recommendation_id).first()
    )
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase recommendation not found",
        )

    if recommendation.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot approve recommendation with status '{recommendation.status}'. "
                "Only recommendations with status 'PENDING_APPROVAL' can be approved."
            ),
        )

    recommendation.status = "APPROVED"

    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.post(
    "/{recommendation_id}/run-evaluation",
    response_model=RecommendationResponse,
)
def run_evaluation_with_engine(
    recommendation_id: int,
    db: Session = Depends(get_db),
):
    """Executes the deterministic decision engine on the recommendation and stores evaluation results.

    Invariants enforced:
    - Writes proposed quantity/supplier to agent_suggested_* fields only.
    - Never overwrites recommended_quantity or the original supplier_id.
    - Updates status to PENDING_APPROVAL for human review.
    """
    recommendation = (
        db.query(PurchaseRecommendation).filter_by(id=recommendation_id).first()
    )
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase recommendation not found",
        )

    product = recommendation.product
    if not product or not product.inventory:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product or inventory record missing for this recommendation",
        )

    # 1. On-hand inventory
    inv_input = InventoryInput(
        available_quantity=product.inventory.available_quantity,
        storage_capacity=product.inventory.storage_capacity,
    )

    # 2. Demand forecast
    forecast_rec = (
        db.query(DemandForecast)
        .filter_by(product_id=product.id)
        .order_by(DemandForecast.period_start.desc())
        .first()
    )
    if not forecast_rec:
        forecast_input = DemandForecastInput(
            forecast_quantity=recommendation.recommended_quantity,
            period_start=date.today(),
            period_end=recommendation.requested_delivery_date,
        )
    else:
        forecast_input = DemandForecastInput(
            forecast_quantity=forecast_rec.forecast_quantity,
            period_start=forecast_rec.period_start,
            period_end=forecast_rec.period_end,
        )

    # 3. Open purchase orders
    open_pos = (
        db.query(PurchaseOrder)
        .filter_by(product_id=product.id)
        .filter(PurchaseOrder.status.in_(["OPEN", "PENDING", "IN_TRANSIT"]))
        .all()
    )
    open_orders_input = [
        OpenPurchaseOrderInput(
            id=po.id,
            supplier_id=po.supplier_id,
            supplier_name=po.supplier.supplier_name if po.supplier else None,
            quantity=po.quantity,
            unit_price=po.unit_price,
            expected_delivery_date=po.expected_delivery_date,
            status=po.status,
        )
        for po in open_pos
    ]

    # 4. Suppliers
    supplier_prods = (
        db.query(SupplierProduct)
        .filter_by(product_id=product.id)
        .all()
    )
    suppliers_input = [
        SupplierProductInput(
            supplier_id=sp.supplier_id,
            supplier_name=sp.supplier.supplier_name,
            unit_price=sp.unit_price,
            lead_time_days=sp.lead_time_days,
            minimum_order_quantity=sp.minimum_order_quantity,
        )
        for sp in supplier_prods
    ]

    # 5. Budget
    budget_rec = db.query(PurchasingBudget).first()
    if budget_rec:
        budget_input = BudgetInput(
            total_budget=budget_rec.total_budget,
            committed_amount=budget_rec.committed_amount,
        )
    else:
        budget_input = BudgetInput(
            total_budget=Decimal("100000.00"),
            committed_amount=Decimal("0.00"),
        )

    engine_input = EngineInput(
        evaluation_date=date.today(),
        recommendation=RecommendationToEvaluate(
            id=recommendation.id,
            product_id=recommendation.product_id,
            recommended_quantity=recommendation.recommended_quantity,
            supplier_id=recommendation.supplier_id,
            requested_delivery_date=recommendation.requested_delivery_date,
            status=recommendation.status,
        ),
        inventory=inv_input,
        forecast=forecast_input,
        open_orders=open_orders_input,
        suppliers=suppliers_input,
        budget=budget_input,
    )

    decision_result = evaluate_purchasing_decision(engine_input)

    # Capture original fields to guarantee they remain untouched
    original_recommended_quantity = recommendation.recommended_quantity
    original_supplier_id = recommendation.supplier_id

    # Update recommendation with evaluation results
    recommendation.agent_decision = decision_result.decision
    recommendation.agent_suggested_quantity = decision_result.suggested_quantity
    recommendation.agent_suggested_supplier_id = decision_result.suggested_supplier_id
    recommendation.agent_reasoning = "\n\n".join(decision_result.reasoning_points)
    recommendation.evaluated_at = datetime.now(timezone.utc)
    recommendation.status = "PENDING_APPROVAL"

    # Protect original fields
    assert recommendation.recommended_quantity == original_recommended_quantity
    assert recommendation.supplier_id == original_supplier_id

    db.commit()
    db.refresh(recommendation)
    return recommendation

