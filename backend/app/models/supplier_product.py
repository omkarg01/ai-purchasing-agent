from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.session import Base


class SupplierProduct(Base):
    __tablename__ = "supplier_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_price = Column(Numeric(10, 2), nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    minimum_order_quantity = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint(
            "supplier_id",
            "product_id",
            name="uq_supplier_product",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="check_supplier_product_unit_price_non_negative",
        ),
        CheckConstraint(
            "lead_time_days >= 0",
            name="check_supplier_product_lead_time_non_negative",
        ),
        CheckConstraint(
            "minimum_order_quantity >= 1",
            name="check_supplier_product_moq_positive",
        ),
    )

    # Relationships
    supplier = relationship("Supplier", back_populates="supplier_products")
    product = relationship("Product", back_populates="supplier_products")

    def __repr__(self) -> str:
        return (
            f"<SupplierProduct(id={self.id}, supplier_id={self.supplier_id}, "
            f"product_id={self.product_id}, price={self.unit_price}, "
            f"lead_time={self.lead_time_days}, moq={self.minimum_order_quantity})>"
        )

