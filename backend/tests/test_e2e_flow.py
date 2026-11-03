"""End-to-end integration test for the purchasing recommendation API endpoints used by the Angular frontend."""
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
from app.models.inventory import Inventory
from app.models.demand_forecast import DemandForecast
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.purchasing_budget import PurchasingBudget
from app.models.purchase_recommendation import PurchaseRecommendation


@pytest.fixture
def client_and_db():
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

    # Seed minimal flow
    db = TestingSessionLocal()
    today = date.today()
    supplier = Supplier(supplier_name="Acme Corp")
    db.add(supplier)
    db.flush()

    product = Product(sku="SKU-E2E", name="E2E Product")
    db.add(product)
    db.flush()

    inv = Inventory(product_id=product.id, available_quantity=50, storage_capacity=500)
    db.add(inv)

    df = DemandForecast(
        product_id=product.id,
        forecast_quantity=200,
        period_start=today,
        period_end=today + timedelta(days=10),
    )
    db.add(df)

    sp = SupplierProduct(
        supplier_id=supplier.id,
        product_id=product.id,
        unit_price=Decimal("10.00"),
        lead_time_days=5,
        minimum_order_quantity=20,
    )
    db.add(sp)

    budget = PurchasingBudget(
        total_budget=Decimal("10000.00"),
        committed_amount=Decimal("0.00"),
    )
    db.add(budget)

    rec = PurchaseRecommendation(
        product_id=product.id,
        supplier_id=supplier.id,
        recommended_quantity=150,
        requested_delivery_date=today + timedelta(days=7),
        status="PENDING_APPROVAL",
    )
    db.add(rec)
    db.commit()
    rec_id = rec.id
    db.close()

    client = TestClient(app)
    yield client, rec_id

    app.dependency_overrides.clear()


def test_full_frontend_user_journey(client_and_db):
    client, rec_id = client_and_db

    # 1. Dashboard: list all recommendations
    list_resp = client.get("/api/recommendations")
    assert list_resp.status_code == 200
    recs = list_resp.json()
    assert len(recs) == 1
    assert recs[0]["id"] == rec_id
    assert recs[0]["status"] == "PENDING_APPROVAL"
    assert recs[0]["agent_decision"] is None

    # 2. Detail Page: get single recommendation
    get_resp = client.get(f"/api/recommendations/{rec_id}")
    assert get_resp.status_code == 200
    rec_data = get_resp.json()
    assert rec_data["recommended_quantity"] == 150
    assert rec_data["agent_decision"] is None

    # 3. User clicks "Run AI Evaluation"
    eval_resp = client.post(f"/api/recommendations/{rec_id}/run-evaluation")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["agent_decision"] == "ACCEPT"
    assert eval_data["agent_suggested_quantity"] == 150
    assert eval_data["agent_suggested_supplier_id"] is not None
    assert eval_data["agent_reasoning"] is not None
    assert len(eval_data["agent_reasoning"]) > 20
    assert eval_data["status"] == "PENDING_APPROVAL"
    # Ensure original fields were not overwritten
    assert eval_data["recommended_quantity"] == 150

    # 4. Human buyer reviews and clicks "Approve Recommendation"
    approve_resp = client.post(f"/api/recommendations/{rec_id}/approve")
    assert approve_resp.status_code == 200
    approved_data = approve_resp.json()
    assert approved_data["status"] == "APPROVED"
    assert approved_data["agent_decision"] == "ACCEPT"
    assert approved_data["agent_suggested_quantity"] == 150

    # 5. Subsequent approval attempt is blocked (not PENDING_APPROVAL)
    reapprove_resp = client.post(f"/api/recommendations/{rec_id}/approve")
    assert reapprove_resp.status_code == 400
    assert "Cannot approve recommendation with status 'APPROVED'" in reapprove_resp.json()["detail"]
