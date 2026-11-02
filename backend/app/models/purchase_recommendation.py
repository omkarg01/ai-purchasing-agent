from sqlalchemy import CheckConstraint, Column, Date, ForeignKey, Integer, String, Text
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

    # Agent evaluation fields
    agent_suggested_quantity = Column(Integer, nullable=True)
    agent_suggested_supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    agent_reasoning = Column(Text, nullable=True)
    agent_decision = Column(String(20), nullable=True)

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

    def __repr__(self) -> str:
        return (
            f"<PurchaseRecommendation(id={self.id}, product_id={self.product_id}, "
            f"supplier_id={self.supplier_id}, quantity={self.recommended_quantity}, "
            f"status='{self.status}', agent_decision='{self.agent_decision}')>"
        )
