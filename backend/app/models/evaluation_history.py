from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.session import Base


class EvaluationHistory(Base):
    __tablename__ = "evaluation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(
        Integer,
        ForeignKey("purchase_recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evaluation_sequence = Column(Integer, nullable=False, default=1)
    evaluated_quantity = Column(Integer, nullable=False)
    evaluated_supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Stored snapshot of supplier name to remain immutable even if supplier record changes/deletes
    evaluated_supplier_name = Column(String(255), nullable=True)

    # Deterministic decision and explanation
    agent_decision = Column(String(20), nullable=False)
    explanation = Column(Text, nullable=True)

    # Structured snapshots of engine results
    calculations = Column(JSON, nullable=True)
    risks = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)

    # Buyer modifications since previous evaluation snapshot
    buyer_modifications = Column(JSON, nullable=True)

    evaluated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    recommendation = relationship(
        "PurchaseRecommendation",
        back_populates="evaluation_history",
    )
    evaluated_supplier = relationship(
        "Supplier",
        foreign_keys=[evaluated_supplier_id],
    )

    def __repr__(self) -> str:
        return (
            f"<EvaluationHistory(id={self.id}, recommendation_id={self.recommendation_id}, "
            f"sequence={self.evaluation_sequence}, decision='{self.agent_decision}', "
            f"evaluated_qty={self.evaluated_quantity}, evaluated_at='{self.evaluated_at}')>"
        )

