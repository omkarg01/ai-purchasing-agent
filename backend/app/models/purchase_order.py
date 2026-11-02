from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.database.session import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    expected_delivery_date = Column(Date, nullable=False)
    status = Column(String(50), nullable=False, default="OPEN")

    __table_args__ = (
        CheckConstraint(
            "quantity >= 0",
            name="check_purchase_order_quantity_non_negative",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="check_purchase_order_unit_price_non_negative",
        ),
    )

    # Relationships
    product = relationship("Product", back_populates="purchase_orders")
    supplier = relationship("Supplier", back_populates="purchase_orders")

    def __repr__(self) -> str:
        return (
            f"<PurchaseOrder(id={self.id}, product_id={self.product_id}, "
            f"supplier_id={self.supplier_id}, quantity={self.quantity}, "
            f"unit_price={self.unit_price}, status='{self.status}')>"
        )

