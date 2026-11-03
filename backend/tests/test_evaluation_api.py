from datetime import date, datetime, timezone
import pytest
from app.models import Product, PurchaseRecommendation, Supplier


def test_evaluate_recommendation_api_preserves_original_fields(client, db_session):
    # Setup test data
    product = Product(name="Hydraulic Pump", sku="PUMP-101")
    supplier1 = Supplier(supplier_name="Primary Supplier Ltd")
    supplier2 = Supplier(supplier_name="Expedited Supplier Inc")
    db_session.add_all([product, supplier1, supplier2])
    db_session.commit()

    original_rec = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=500,
        supplier_id=supplier1.id,
        requested_delivery_date=date(2026, 11, 25),
        status="PENDING_APPROVAL",
    )
    db_session.add(original_rec)
    db_session.commit()
    rec_id = original_rec.id

    # Call evaluation API
    eval_payload = {
        "agent_decision": "MODIFY",
        "agent_suggested_quantity": 350,
        "agent_suggested_supplier_id": supplier2.id,
        "agent_reasoning": "Lead time from Primary Supplier is too long; Expedited Supplier satisfies delivery window.",
    }
    response = client.post(f"/recommendations/{rec_id}/evaluate", json=eval_payload)
    assert response.status_code == 200, response.text
    data = response.json()

    # 1. Proposed values written ONLY to agent_suggested_* fields
    assert data["agent_decision"] == "MODIFY"
    assert data["agent_suggested_quantity"] == 350
    assert data["agent_suggested_supplier_id"] == supplier2.id
    assert data["agent_reasoning"] == eval_payload["agent_reasoning"]
    assert data["evaluated_at"] is not None

    # 2. Original recommendation fields MUST NOT be overwritten
    assert data["recommended_quantity"] == 500
    assert data["supplier_id"] == supplier1.id

    # 3. Status remains PENDING_APPROVAL and is NOT overwritten by agent_decision
    assert data["status"] == "PENDING_APPROVAL"

    # Verify directly from database session
    db_session.expire_all()
    refreshed = db_session.query(PurchaseRecommendation).filter_by(id=rec_id).one()
    assert refreshed.recommended_quantity == 500
    assert refreshed.supplier_id == supplier1.id
    assert refreshed.status == "PENDING_APPROVAL"
    assert refreshed.agent_decision == "MODIFY"
    assert refreshed.agent_suggested_quantity == 350
    assert refreshed.agent_suggested_supplier_id == supplier2.id
    assert refreshed.evaluated_at is not None


def test_evaluate_recommendation_api_with_custom_evaluated_at(client, db_session):
    product = Product(name="Control Valve", sku="VALVE-200")
    supplier = Supplier(supplier_name="Valve Works")
    db_session.add_all([product, supplier])
    db_session.commit()

    rec = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=200,
        supplier_id=supplier.id,
        requested_delivery_date=date(2026, 11, 30),
        status="PENDING",
    )
    db_session.add(rec)
    db_session.commit()

    custom_time = "2026-11-03T12:00:00Z"
    response = client.post(
        f"/recommendations/{rec.id}/evaluate",
        json={
            "agent_decision": "ACCEPT",
            "agent_suggested_quantity": 200,
            "agent_suggested_supplier_id": supplier.id,
            "agent_reasoning": "Recommendation satisfies constraints perfectly.",
            "evaluated_at": custom_time,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["agent_decision"] == "ACCEPT"
    assert "2026-11-03" in data["evaluated_at"]


def test_evaluate_recommendation_api_errors(client, db_session):
    # 404 for non-existent recommendation
    response = client.post(
        "/recommendations/99999/evaluate",
        json={"agent_decision": "ACCEPT"},
    )
    assert response.status_code == 404

    # 400 for non-existent suggested supplier
    product = Product(name="Sensor", sku="SENS-99")
    db_session.add(product)
    db_session.commit()

    rec = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=50,
        requested_delivery_date=date(2026, 12, 1),
    )
    db_session.add(rec)
    db_session.commit()

    response = client.post(
        f"/recommendations/{rec.id}/evaluate",
        json={
            "agent_decision": "MODIFY",
            "agent_suggested_supplier_id": 99999,
        },
    )
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]

    # 422 for invalid decision
    response = client.post(
        f"/recommendations/{rec.id}/evaluate",
        json={"agent_decision": "INVALID_DECISION"},
    )
    assert response.status_code == 422

    # 422 for negative suggested quantity
    response = client.post(
        f"/recommendations/{rec.id}/evaluate",
        json={
            "agent_decision": "ACCEPT",
            "agent_suggested_quantity": -10,
        },
    )
    assert response.status_code == 422


def test_list_recommendations_api(client, db_session):
    product = Product(name="O-Ring", sku="ORING-01")
    db_session.add(product)
    db_session.commit()

    rec1 = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=100,
        requested_delivery_date=date(2026, 12, 1),
    )
    rec2 = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=200,
        requested_delivery_date=date(2026, 12, 10),
    )
    db_session.add_all([rec1, rec2])
    db_session.commit()

    response = client.get("/api/recommendations")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 2
    ids = [item["id"] for item in items]
    assert rec1.id in ids
    assert rec2.id in ids


def test_run_evaluation_with_engine_api(client, db_session):
    from decimal import Decimal
    from app.models import Inventory, DemandForecast, SupplierProduct

    product = Product(name="Electric Motor", sku="MOT-01")
    supplier = Supplier(supplier_name="Motor Dynamics")
    db_session.add_all([product, supplier])
    db_session.commit()

    inv = Inventory(
        product_id=product.id,
        available_quantity=50,
        storage_capacity=1000,
    )
    forecast = DemandForecast(
        product_id=product.id,
        forecast_quantity=200,
        period_start=date(2026, 11, 1),
        period_end=date(2026, 11, 15),
    )
    sp = SupplierProduct(
        supplier_id=supplier.id,
        product_id=product.id,
        unit_price=Decimal("45.00"),
        lead_time_days=3,
        minimum_order_quantity=150,
    )
    db_session.add_all([inv, forecast, sp])
    db_session.commit()

    rec = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=100,
        supplier_id=supplier.id,
        requested_delivery_date=date(2026, 11, 10),
        status="PENDING",
    )
    db_session.add(rec)
    db_session.commit()

    response = client.post(f"/api/recommendations/{rec.id}/run-evaluation")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rec.id
    assert data["agent_decision"] in ("ACCEPT", "MODIFY", "INVESTIGATE")
    assert data["agent_suggested_quantity"] is not None
    assert data["status"] == "PENDING_APPROVAL"
    assert data["evaluated_at"] is not None
    assert data["recommended_quantity"] == 100
    assert data["supplier_id"] == supplier.id


