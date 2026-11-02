from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.session import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    sku = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Relationships
    inventory = relationship(
        "Inventory",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
    )
    demand_forecasts = relationship(
        "DemandForecast",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    supplier_products = relationship(
        "SupplierProduct",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    purchase_recommendations = relationship(
        "PurchaseRecommendation",
        back_populates="product",
    )
    purchase_orders = relationship(
        "PurchaseOrder",
        back_populates="product",
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}')>"

