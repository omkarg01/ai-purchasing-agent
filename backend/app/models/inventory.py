from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database.session import Base


class Inventory(Base):
    __tablename__ = "inventories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    available_quantity = Column(Integer, nullable=False, default=0)
    storage_capacity = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "available_quantity >= 0",
            name="check_inventory_available_quantity_non_negative",
        ),
        CheckConstraint(
            "storage_capacity >= 0",
            name="check_inventory_storage_capacity_non_negative",
        ),
    )

    # Relationships
    product = relationship("Product", back_populates="inventory")

    def __repr__(self) -> str:
        return (
            f"<Inventory(id={self.id}, product_id={self.product_id}, "
            f"available={self.available_quantity}, capacity={self.storage_capacity})>"
        )

