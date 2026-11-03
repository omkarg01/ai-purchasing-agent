import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    ApproveRequest,
    EvaluationHistoryResponse,
    EvaluationRequest,
    RecommendationCreateRequest,
    RecommendationResponse,
    RecommendationUpdateRequest,
)
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
from app.models.evaluation_history import EvaluationHistory
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_recommendation import PurchaseRecommendation
from app.models.purchasing_budget import PurchasingBudget
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.agent.purchasing_agent import generate_purchasing_briefing

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def validate_and_format_split_allocation(
    product_id: int, total_qty: int, split_data: dict, db: Session
) -> dict:
    """Validates multi-supplier split sourcing allocation against catalog data."""
    primary_id = split_data.get("primary_supplier_id")
    primary_qty = int(split_data.get("primary_quantity", 0))
    secondary_id = split_data.get("secondary_supplier_id")
    secondary_qty = int(split_data.get("secondary_quantity", 0))

    if not primary_id or not secondary_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Split sourcing requires both primary and secondary supplier IDs.",
        )
    if primary_id == secondary_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primary and secondary suppliers in split sourcing must be different.",
        )
    if primary_qty <= 0 or secondary_qty <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Split allocation quantities must be greater than zero.",
        )
    if (primary_qty + secondary_qty) != total_qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Sum of split quantities ({primary_qty} + {secondary_qty} = {primary_qty + secondary_qty}) "
                f"must equal total quantity ({total_qty})."
            ),
        )

    sp_primary = (
        db.query(SupplierProduct)
        .filter_by(supplier_id=primary_id, product_id=product_id)
        .first()
    )
    if not sp_primary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Supplier #{primary_id} is not registered for product #{product_id}.",
        )
    sp_secondary = (
        db.query(SupplierProduct)
        .filter_by(supplier_id=secondary_id, product_id=product_id)
        .first()
    )
    if not sp_secondary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Supplier #{secondary_id} is not registered for product #{product_id}.",
        )

    p_price = float(sp_primary.unit_price)
    s_price = float(sp_secondary.unit_price)
    p_cost = round(primary_qty * p_price, 2)
    s_cost = round(secondary_qty * s_price, 2)

    return {
        "primary_supplier_id": primary_id,
        "primary_supplier_name": sp_primary.supplier.supplier_name,
        "primary_quantity": primary_qty,
        "primary_unit_price": p_price,
        "primary_cost": p_cost,
        "secondary_supplier_id": secondary_id,
        "secondary_supplier_name": sp_secondary.supplier.supplier_name,
        "secondary_quantity": secondary_qty,
        "secondary_unit_price": s_price,
        "secondary_cost": s_cost,
        "total_cost": round(p_cost + s_cost, 2),
    }


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
    "",
    response_model=RecommendationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recommendation(
    payload: RecommendationCreateRequest,
    db: Session = Depends(get_db),
):
    """Creates a new purchasing recommendation in PENDING_APPROVAL status."""
    # 1. Validate product exists
    product = db.query(Product).filter_by(id=payload.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with id {payload.product_id} does not exist",
        )

    # 2. Validate supplier exists if provided
    if payload.supplier_id is not None:
        supplier = db.query(Supplier).filter_by(id=payload.supplier_id).first()
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier with id {payload.supplier_id} does not exist",
            )

    # 3. Validate delivery date is not in the past
    if payload.requested_delivery_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested delivery date cannot be in the past",
        )

    split_alloc = None
    if payload.split_allocation:
        split_alloc = validate_and_format_split_allocation(
            payload.product_id, payload.recommended_quantity, payload.split_allocation, db
        )
        if payload.supplier_id is None:
            payload.supplier_id = split_alloc["primary_supplier_id"]

    new_rec = PurchaseRecommendation(
        product_id=payload.product_id,
        supplier_id=payload.supplier_id,
        recommended_quantity=payload.recommended_quantity,
        requested_delivery_date=payload.requested_delivery_date,
        split_allocation=split_alloc,
        status="PENDING_APPROVAL",
    )
    db.add(new_rec)
    db.commit()
    db.refresh(new_rec)
    return new_rec


@router.put(
    "/{recommendation_id}",
    response_model=RecommendationResponse,
)
def update_recommendation(
    recommendation_id: int,
    payload: RecommendationUpdateRequest,
    db: Session = Depends(get_db),
):
    """Updates an existing purchasing recommendation.

    Invariants enforced:
    - Only recommendations in 'PENDING_APPROVAL' status can be modified.
    - If already 'APPROVED', returns 400 Bad Request.
    - Modifying parameters resets previous AI evaluation to ensure fresh evaluation.
    """
    rec = db.query(PurchaseRecommendation).filter_by(id=recommendation_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase recommendation not found",
        )

    if rec.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot edit recommendation with status '{rec.status}'. "
                "Only recommendations with status 'PENDING_APPROVAL' can be edited."
            ),
        )

    if payload.supplier_id is not None:
        supplier = db.query(Supplier).filter_by(id=payload.supplier_id).first()
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier with id {payload.supplier_id} does not exist",
            )
        rec.supplier_id = payload.supplier_id

    if payload.recommended_quantity is not None:
        rec.recommended_quantity = payload.recommended_quantity

    if payload.requested_delivery_date is not None:
        if payload.requested_delivery_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested delivery date cannot be in the past",
            )
        rec.requested_delivery_date = payload.requested_delivery_date

    target_qty = payload.recommended_quantity if payload.recommended_quantity is not None else rec.recommended_quantity
    if payload.split_allocation:
        rec.split_allocation = validate_and_format_split_allocation(
            rec.product_id, target_qty, payload.split_allocation, db
        )
        rec.supplier_id = rec.split_allocation["primary_supplier_id"]
    elif "split_allocation" in payload.model_fields_set and payload.split_allocation is None:
        rec.split_allocation = None

    # Reset previous AI evaluation because parameters changed
    rec.agent_decision = None
    rec.agent_suggested_quantity = None
    rec.agent_suggested_supplier_id = None
    rec.agent_reasoning = None
    rec.evaluated_at = None

    db.commit()
    db.refresh(rec)
    return rec



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


APPROVAL_THRESHOLD_LIMIT = float(os.getenv("MAX_DIRECT_APPROVAL_AMOUNT", "10000.0"))


@router.post(
    "/{recommendation_id}/approve",
    response_model=RecommendationResponse,
)
def approve_recommendation(
    recommendation_id: int,
    payload: Optional[ApproveRequest] = None,
    db: Session = Depends(get_db),
):
    """Approves a purchase recommendation after human review.

    Invariants enforced:
    - Only recommendations in 'PENDING_APPROVAL' status can be approved.
    - Transitions status strictly to 'APPROVED'.
    - Preserves all original recommendation fields and agent evaluation fields.
    - Enforces governance approval dollar threshold limit (Rule / FM-7).
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

    # Governance threshold validation (Rule / FM-7)
    order_val = None
    if recommendation.split_allocation:
        order_val = float(recommendation.split_allocation.get("total_cost", 0.0))
    elif recommendation.supplier_id:
        sp = db.query(SupplierProduct).filter_by(
            supplier_id=recommendation.supplier_id,
            product_id=recommendation.product_id,
        ).first()
        if sp:
            order_val = float(recommendation.recommended_quantity * sp.unit_price)

    has_override = payload.manager_override if payload else False
    if order_val is not None and order_val > APPROVAL_THRESHOLD_LIMIT and not has_override:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Order total value (${order_val:,.2f}) exceeds the direct approval threshold limit "
                f"(${APPROVAL_THRESHOLD_LIMIT:,.2f}). Manager override authorization is required."
            ),
        )

    recommendation.status = "APPROVED"

    # Create PurchaseOrder records upon approval
    if recommendation.split_allocation:
        alloc = recommendation.split_allocation
        p_price = Decimal(str(alloc.get("primary_unit_price", 0.0)))
        s_price = Decimal(str(alloc.get("secondary_unit_price", 0.0)))
        po1 = PurchaseOrder(
            product_id=recommendation.product_id,
            supplier_id=alloc["primary_supplier_id"],
            recommendation_id=recommendation.id,
            quantity=alloc["primary_quantity"],
            unit_price=p_price,
            expected_delivery_date=recommendation.requested_delivery_date,
            status="OPEN",
        )
        po2 = PurchaseOrder(
            product_id=recommendation.product_id,
            supplier_id=alloc["secondary_supplier_id"],
            recommendation_id=recommendation.id,
            quantity=alloc["secondary_quantity"],
            unit_price=s_price,
            expected_delivery_date=recommendation.requested_delivery_date,
            status="OPEN",
        )
        db.add_all([po1, po2])
    elif recommendation.supplier_id:
        sp = db.query(SupplierProduct).filter_by(
            supplier_id=recommendation.supplier_id,
            product_id=recommendation.product_id,
        ).first()
        if sp:
            po = PurchaseOrder(
                product_id=recommendation.product_id,
                supplier_id=recommendation.supplier_id,
                recommendation_id=recommendation.id,
                quantity=recommendation.recommended_quantity,
                unit_price=sp.unit_price,
                expected_delivery_date=recommendation.requested_delivery_date,
                status="OPEN",
            )
            db.add(po)

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
            available_capacity=getattr(sp, "available_capacity", None),
            is_moq_negotiable=getattr(sp, "is_moq_negotiable", True),
            expedited_lead_time_days=getattr(sp, "expedited_lead_time_days", None),
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

    # 1. Fetch previous evaluation snapshot to calculate buyer modifications
    previous_run = (
        db.query(EvaluationHistory)
        .filter_by(recommendation_id=recommendation.id)
        .order_by(EvaluationHistory.evaluation_sequence.desc())
        .first()
    )

    if previous_run is None:
        sequence = 1
        buyer_modifications = None
    else:
        sequence = previous_run.evaluation_sequence + 1
        mods = {}
        if recommendation.recommended_quantity != previous_run.evaluated_quantity:
            mods["quantity"] = {
                "previous": previous_run.evaluated_quantity,
                "updated": recommendation.recommended_quantity,
            }
        if recommendation.supplier_id != previous_run.evaluated_supplier_id:
            mods["supplier"] = {
                "previous": previous_run.evaluated_supplier_id,
                "updated": recommendation.supplier_id,
                "previous_name": previous_run.evaluated_supplier_name,
                "updated_name": recommendation.supplier_name,
            }
        prev_split = (previous_run.calculations or {}).get("split_allocation") if previous_run.calculations else None
        if recommendation.split_allocation != prev_split:
            mods["split_allocation"] = {
                "previous": prev_split,
                "updated": recommendation.split_allocation,
            }
        buyer_modifications = mods if mods else None

    # 2. Atomic persistence: update recommendation & insert EvaluationHistory in one transaction
    try:
        briefing = generate_purchasing_briefing(
            engine_input=engine_input,
            decision_result=decision_result,
            product_name=product.name,
            product_sku=product.sku,
        )

        recommendation.agent_decision = decision_result.decision
        recommendation.agent_suggested_quantity = decision_result.suggested_quantity
        recommendation.agent_suggested_supplier_id = decision_result.suggested_supplier_id
        recommendation.agent_reasoning = briefing
        eval_time = datetime.now(timezone.utc)
        recommendation.evaluated_at = eval_time
        recommendation.status = "PENDING_APPROVAL"

        # If decision engine determined split sourcing, assign to recommendation.split_allocation
        if decision_result.preferred_option and decision_result.preferred_option.is_split_sourcing:
            recommendation.split_allocation = decision_result.calculations.get("split_allocation")

        # Protect original fields
        assert recommendation.recommended_quantity == original_recommended_quantity
        assert recommendation.supplier_id == original_supplier_id

        history_entry = EvaluationHistory(
            recommendation_id=recommendation.id,
            evaluation_sequence=sequence,
            evaluated_quantity=recommendation.recommended_quantity,
            evaluated_supplier_id=recommendation.supplier_id,
            evaluated_supplier_name=recommendation.supplier_name,
            agent_decision=decision_result.decision,
            explanation=briefing,
            calculations=decision_result.calculations,
            risks=decision_result.risks,
            warnings=decision_result.warnings,
            buyer_modifications=buyer_modifications,
            evaluated_at=eval_time,
        )
        db.add(history_entry)

        db.commit()
        db.refresh(recommendation)
        return recommendation
    except Exception:
        db.rollback()
        raise


@router.get(
    "/{recommendation_id}/history",
    response_model=List[EvaluationHistoryResponse],
)
def get_recommendation_history(
    recommendation_id: int,
    db: Session = Depends(get_db),
):
    """Returns chronological evaluation history for a recommendation."""
    rec = db.query(PurchaseRecommendation).filter_by(id=recommendation_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase recommendation not found",
        )

    return (
        db.query(EvaluationHistory)
        .filter_by(recommendation_id=recommendation_id)
        .order_by(EvaluationHistory.evaluation_sequence.asc())
        .all()
    )

