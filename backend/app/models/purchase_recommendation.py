from sqlalchemy import CheckConstraint, Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.session import Base


class PurchaseRecommendation(Base):
    __tablename__ = "purchase_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommended_quantity = Column(Integer, nullable=False)
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requested_delivery_date = Column(Date, nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")

    __table_args__ = (
        CheckConstraint(
            "recommended_quantity >= 0",
            name="check_recommendation_quantity_non_negative",
        ),
    )

    # Relationships
    product = relationship("Product", back_populates="purchase_recommendations")
    supplier = relationship("Supplier", back_populates="purchase_recommendations")

    def __repr__(self) -> str:
        return (
            f"<PurchaseRecommendation(id={self.id}, product_id={self.product_id}, "
            f"supplier_id={self.supplier_id}, quantity={self.recommended_quantity}, "
            f"status='{self.status}')>"
        )

