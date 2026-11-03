from typing import Optional
from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.session import Base


class PurchaseRecommendation(Base):
    __tablename__ = "purchase_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    recommended_quantity = Column(Integer, nullable=False)
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    requested_delivery_date = Column(Date, nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")

    # Agent evaluation fields (separate from approval status)
    agent_suggested_quantity = Column(Integer, nullable=True)
    agent_suggested_supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    agent_reasoning = Column(Text, nullable=True)
    agent_decision = Column(String(20), nullable=True)
    evaluated_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "recommended_quantity >= 0",
            name="check_recommendation_quantity_non_negative",
        ),
        CheckConstraint(
            "agent_suggested_quantity IS NULL OR agent_suggested_quantity >= 0",
            name="check_agent_suggested_quantity_non_negative",
        ),
        CheckConstraint(
            "agent_decision IS NULL OR agent_decision IN ('ACCEPT', 'MODIFY', 'REJECT', 'INVESTIGATE')",
            name="check_agent_decision_valid",
        ),
    )

    # Relationships
    product = relationship("Product", back_populates="purchase_recommendations")
    supplier = relationship(
        "Supplier",
        foreign_keys=[supplier_id],
        back_populates="purchase_recommendations",
    )
    agent_suggested_supplier = relationship(
        "Supplier",
        foreign_keys=[agent_suggested_supplier_id],
        back_populates="agent_evaluations",
    )
    purchase_orders = relationship("PurchaseOrder", back_populates="recommendation")

    @property
    def product_name(self) -> Optional[str]:
        return self.product.name if self.product else None

    @property
    def product_sku(self) -> Optional[str]:
        return self.product.sku if self.product else None

    @property
    def supplier_name(self) -> Optional[str]:
        return self.supplier.supplier_name if self.supplier else None

    @property
    def agent_suggested_supplier_name(self) -> Optional[str]:
        return (
            self.agent_suggested_supplier.supplier_name
            if self.agent_suggested_supplier
            else None
        )

    def __repr__(self) -> str:
        return (
            f"<PurchaseRecommendation(id={self.id}, product_id={self.product_id}, "
            f"supplier_id={self.supplier_id}, quantity={self.recommended_quantity}, "
            f"status='{self.status}', agent_decision='{self.agent_decision}', "
            f"evaluated_at='{self.evaluated_at}')>"
        )
