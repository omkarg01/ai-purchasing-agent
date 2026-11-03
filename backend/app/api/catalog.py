from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import ProductLookupResponse, SupplierLookupResponse
from app.database.session import get_db
from app.models.product import Product
from app.models.supplier import Supplier

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/products", response_model=List[ProductLookupResponse])
def list_products(db: Session = Depends(get_db)):
    """Returns available products for purchasing recommendation forms."""
    return db.query(Product).order_by(Product.name.asc()).all()


@router.get("/suppliers", response_model=List[SupplierLookupResponse])
def list_suppliers(db: Session = Depends(get_db)):
    """Returns available suppliers for purchasing recommendation forms."""
    return db.query(Supplier).order_by(Supplier.supplier_name.asc()).all()

