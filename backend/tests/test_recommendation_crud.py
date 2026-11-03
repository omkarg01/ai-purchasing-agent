"""Tests for recommendation create, update, and catalog endpoints."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.main import app
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.purchase_recommendation import PurchaseRecommendation


@pytest.fixture
def crud_client_and_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    supplier = Supplier(supplier_name="Acme Parts Corp")
    db.add(supplier)
    db.flush()

    prod = Product(sku="SKU-CRUD", name="CRUD Test Widget", description="Testing widget")
    db.add(prod)
    db.commit()

    prod_id = prod.id
    supp_id = supplier.id
    db.close()

    client = TestClient(app)
    yield client, TestingSessionLocal, prod_id, supp_id

    app.dependency_overrides.clear()


def test_catalog_endpoints(crud_client_and_db):
    client, _, prod_id, supp_id = crud_client_and_db

    # Test /api/catalog/products
    prod_resp = client.get("/api/catalog/products")
    assert prod_resp.status_code == 200
    prods = prod_resp.json()
    assert len(prods) == 1
    assert prods[0]["id"] == prod_id
    assert prods[0]["name"] == "CRUD Test Widget"

    # Test /api/catalog/suppliers without filter
    supp_resp = client.get("/api/catalog/suppliers")
    assert supp_resp.status_code == 200
    supps = supp_resp.json()
    assert len(supps) == 1
    assert supps[0]["id"] == supp_id
    assert supps[0]["supplier_name"] == "Acme Parts Corp"

    # Test /api/catalog/suppliers with product_id filter (no mapping yet -> empty)
    filtered_resp = client.get(f"/api/catalog/suppliers?product_id={prod_id}")
    assert filtered_resp.status_code == 200
    assert filtered_resp.json() == []


def test_create_recommendation_success(crud_client_and_db):
    client, _, prod_id, supp_id = crud_client_and_db
    delivery_date = (date.today() + timedelta(days=7)).isoformat()

    payload = {
        "product_id": prod_id,
        "supplier_id": supp_id,
        "recommended_quantity": 250,
        "requested_delivery_date": delivery_date,
    }

    resp = client.post("/api/recommendations", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["product_id"] == prod_id
    assert data["supplier_id"] == supp_id
    assert data["recommended_quantity"] == 250
    assert data["requested_delivery_date"] == delivery_date
    assert data["status"] == "PENDING_APPROVAL"
    assert data["agent_decision"] is None


def test_create_recommendation_invalid_product(crud_client_and_db):
    client, _, _, supp_id = crud_client_and_db
    payload = {
        "product_id": 99999,
        "supplier_id": supp_id,
        "recommended_quantity": 100,
        "requested_delivery_date": (date.today() + timedelta(days=5)).isoformat(),
    }
    resp = client.post("/api/recommendations", json=payload)
    assert resp.status_code == 400
    assert "Product with id 99999 does not exist" in resp.json()["detail"]


def test_create_recommendation_past_delivery_date(crud_client_and_db):
    client, _, prod_id, supp_id = crud_client_and_db
    payload = {
        "product_id": prod_id,
        "supplier_id": supp_id,
        "recommended_quantity": 100,
        "requested_delivery_date": (date.today() - timedelta(days=2)).isoformat(),
    }
    resp = client.post("/api/recommendations", json=payload)
    assert resp.status_code == 400
    assert "Requested delivery date cannot be in the past" in resp.json()["detail"]


def test_update_recommendation_success_and_resets_evaluation(crud_client_and_db):
    client, SessionLocal, prod_id, supp_id = crud_client_and_db
    db = SessionLocal()

    # Pre-create recommendation with existing AI evaluation
    rec = PurchaseRecommendation(
        product_id=prod_id,
        supplier_id=supp_id,
        recommended_quantity=100,
        requested_delivery_date=date.today() + timedelta(days=5),
        status="PENDING_APPROVAL",
        agent_decision="ACCEPT",
        agent_suggested_quantity=100,
        agent_suggested_supplier_id=supp_id,
        agent_reasoning="Previously evaluated.",
    )
    db.add(rec)
    db.commit()
    rec_id = rec.id
    db.close()

    new_delivery = (date.today() + timedelta(days=12)).isoformat()
    update_payload = {
        "recommended_quantity": 300,
        "requested_delivery_date": new_delivery,
    }

    resp = client.put(f"/api/recommendations/{rec_id}", json=update_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommended_quantity"] == 300
    assert data["requested_delivery_date"] == new_delivery
    # Invariant: Previous AI evaluation is reset
    assert data["agent_decision"] is None
    assert data["agent_suggested_quantity"] is None
    assert data["agent_reasoning"] is None


def test_update_recommendation_blocked_when_approved(crud_client_and_db):
    client, SessionLocal, prod_id, supp_id = crud_client_and_db
    db = SessionLocal()

    rec = PurchaseRecommendation(
        product_id=prod_id,
        supplier_id=supp_id,
        recommended_quantity=100,
        requested_delivery_date=date.today() + timedelta(days=5),
        status="APPROVED",
    )
    db.add(rec)
    db.commit()
    rec_id = rec.id
    db.close()

    resp = client.put(f"/api/recommendations/{rec_id}", json={"recommended_quantity": 200})
    assert resp.status_code == 400
    assert "Only recommendations with status 'PENDING_APPROVAL' can be edited" in resp.json()["detail"]

