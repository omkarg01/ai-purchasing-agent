from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import EvaluationRequest, RecommendationResponse
from app.database.session import get_db
from app.models.purchase_recommendation import PurchaseRecommendation
from app.models.supplier import Supplier

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


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
