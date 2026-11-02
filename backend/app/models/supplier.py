from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database.session import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String(255), nullable=False, unique=True, index=True)

    # Relationships
    supplier_products = relationship(
        "SupplierProduct",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )
    purchase_recommendations = relationship(
        "PurchaseRecommendation",
        back_populates="supplier",
    )
    purchase_orders = relationship(
        "PurchaseOrder",
        back_populates="supplier",
    )

    def __repr__(self) -> str:
        return f"<Supplier(id={self.id}, supplier_name='{self.supplier_name}')>"

