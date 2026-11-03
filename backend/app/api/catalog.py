from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas import ProductLookupResponse, SupplierLookupResponse
from app.database.session import get_db
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/products", response_model=List[ProductLookupResponse])
def list_products(db: Session = Depends(get_db)):
    """Returns available products for purchasing recommendation forms."""
    return db.query(Product).order_by(Product.name.asc()).all()


@router.get("/suppliers", response_model=List[SupplierLookupResponse])
def list_suppliers(
    product_id: Optional[int] = Query(default=None, description="Filter suppliers selling this product"),
    db: Session = Depends(get_db),
):
    """Returns available suppliers for purchasing recommendation forms.
    
    If product_id is supplied, returns only suppliers registered for that product,
    enriched with unit price, lead time, MOQ, and capacity.
    """
    if product_id is not None:
        rows = (
            db.query(Supplier, SupplierProduct)
            .join(SupplierProduct, Supplier.id == SupplierProduct.supplier_id)
            .filter(SupplierProduct.product_id == product_id)
            .order_by(Supplier.supplier_name.asc())
            .all()
        )
        return [
            SupplierLookupResponse(
                id=s.id,
                supplier_name=s.supplier_name,
                unit_price=float(sp.unit_price) if sp.unit_price is not None else None,
                lead_time_days=sp.lead_time_days,
                minimum_order_quantity=sp.minimum_order_quantity,
                available_capacity=sp.available_capacity,
                is_moq_negotiable=getattr(sp, "is_moq_negotiable", True),
                expedited_lead_time_days=getattr(sp, "expedited_lead_time_days", None),
            )
            for s, sp in rows
        ]

    return [
        SupplierLookupResponse(
            id=s.id,
            supplier_name=s.supplier_name,
        )
        for s in db.query(Supplier).order_by(Supplier.supplier_name.asc()).all()
    ]

