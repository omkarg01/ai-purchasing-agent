from datetime import date, timedelta
from decimal import Decimal
import pytest
from app.models import Product, Supplier, SupplierProduct, PurchaseRecommendation, PurchaseOrder


@pytest.fixture
def split_catalog(db_session):
    product = Product(name="Split Test Part", sku="PART-SPLIT")
    db_session.add(product)
    db_session.flush()

    sup1 = Supplier(supplier_name="Vendor Alpha")
    sup2 = Supplier(supplier_name="Vendor Beta")
    db_session.add_all([sup1, sup2])
    db_session.flush()

    sp1 = SupplierProduct(
        supplier_id=sup1.id,
        product_id=product.id,
        unit_price=Decimal("10.00"),
        lead_time_days=4,
        minimum_order_quantity=100,
        available_capacity=250,
    )
    sp2 = SupplierProduct(
        supplier_id=sup2.id,
        product_id=product.id,
        unit_price=Decimal("12.00"),
        lead_time_days=5,
        minimum_order_quantity=100,
        available_capacity=500,
    )
    db_session.add_all([sp1, sp2])
    db_session.commit()

    return product, sup1, sup2


def test_create_recommendation_with_split_allocation(client, split_catalog):
    product, sup1, sup2 = split_catalog

    payload = {
        "product_id": product.id,
        "recommended_quantity": 500,
        "requested_delivery_date": (date.today() + timedelta(days=14)).isoformat(),
        "split_allocation": {
            "primary_supplier_id": sup1.id,
            "primary_quantity": 250,
            "secondary_supplier_id": sup2.id,
            "secondary_quantity": 250,
        },
    }

    res = client.post("/api/recommendations", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["recommended_quantity"] == 500
    assert data["supplier_id"] == sup1.id
    assert data["split_allocation"] is not None
    assert data["split_allocation"]["primary_supplier_id"] == sup1.id
    assert data["split_allocation"]["primary_quantity"] == 250
    assert data["split_allocation"]["secondary_supplier_id"] == sup2.id
    assert data["split_allocation"]["secondary_quantity"] == 250
    assert data["split_allocation"]["total_cost"] == 5500.0


def test_update_recommendation_with_split_allocation(client, split_catalog):
    product, sup1, sup2 = split_catalog

    # Create single supplier recommendation first
    rec_res = client.post("/api/recommendations", json={
        "product_id": product.id,
        "supplier_id": sup1.id,
        "recommended_quantity": 500,
        "requested_delivery_date": (date.today() + timedelta(days=14)).isoformat(),
    })
    rec_id = rec_res.json()["id"]

    # Update with split allocation
    update_res = client.put(f"/api/recommendations/{rec_id}", json={
        "split_allocation": {
            "primary_supplier_id": sup1.id,
            "primary_quantity": 250,
            "secondary_supplier_id": sup2.id,
            "secondary_quantity": 250,
        },
    })
    assert update_res.status_code == 200, update_res.text
    data = update_res.json()
    assert data["split_allocation"] is not None
    assert data["split_allocation"]["primary_quantity"] == 250
    assert data["split_allocation"]["secondary_quantity"] == 250
    assert data["split_allocation"]["total_cost"] == 5500.0


def test_invalid_split_allocation_mismatched_quantity_400(client, split_catalog):
    product, sup1, sup2 = split_catalog

    payload = {
        "product_id": product.id,
        "recommended_quantity": 500,
        "requested_delivery_date": (date.today() + timedelta(days=14)).isoformat(),
        "split_allocation": {
            "primary_supplier_id": sup1.id,
            "primary_quantity": 200,
            "secondary_supplier_id": sup2.id,
            "secondary_quantity": 200,  # 200 + 200 = 400 != 500
        },
    }

    res = client.post("/api/recommendations", json=payload)
    assert res.status_code == 400
    assert "must equal total quantity" in res.json()["detail"]


def test_approve_split_recommendation_creates_purchase_orders(client, split_catalog, db_session):
    product, sup1, sup2 = split_catalog

    # Create recommendation with split allocation
    payload = {
        "product_id": product.id,
        "recommended_quantity": 500,
        "requested_delivery_date": (date.today() + timedelta(days=14)).isoformat(),
        "split_allocation": {
            "primary_supplier_id": sup1.id,
            "primary_quantity": 250,
            "secondary_supplier_id": sup2.id,
            "secondary_quantity": 250,
        },
    }
    rec_res = client.post("/api/recommendations", json=payload)
    rec_id = rec_res.json()["id"]

    # Approve recommendation
    approve_res = client.post(f"/api/recommendations/{rec_id}/approve")
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # Verify 2 PurchaseOrder records created
    pos = db_session.query(PurchaseOrder).filter_by(recommendation_id=rec_id).all()
    assert len(pos) == 2
    po_sup1 = next(po for po in pos if po.supplier_id == sup1.id)
    po_sup2 = next(po for po in pos if po.supplier_id == sup2.id)
    assert po_sup1.quantity == 250
    assert po_sup1.unit_price == Decimal("10.00")
    assert po_sup2.quantity == 250
    assert po_sup2.unit_price == Decimal("12.00")

