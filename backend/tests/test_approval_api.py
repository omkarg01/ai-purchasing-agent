from datetime import date, datetime, timezone
import pytest
from app.models import Product, PurchaseRecommendation, Supplier


def test_approve_recommendation_success(client, db_session):
    product = Product(name="Industrial Sensor", sku="SENS-500")
    supplier1 = Supplier(supplier_name="Primary Electronics")
    supplier2 = Supplier(supplier_name="Backup Components")
    db_session.add_all([product, supplier1, supplier2])
    db_session.commit()

    evaluation_time = datetime(2026, 11, 3, 10, 30, 0)
    rec = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=600,
        supplier_id=supplier1.id,
        requested_delivery_date=date(2026, 11, 28),
        status="PENDING_APPROVAL",
        agent_decision="MODIFY",
        agent_suggested_quantity=450,
        agent_suggested_supplier_id=supplier2.id,
        agent_reasoning="Recommended reducing order to 450 units from Backup Components to avoid storage overflow.",
        evaluated_at=evaluation_time,
    )
    db_session.add(rec)
    db_session.commit()

    # Call approval endpoint via /api/recommendations/{id}/approve
    response = client.post(f"/api/recommendations/{rec.id}/approve")
    assert response.status_code == 200, response.text
    data = response.json()

    # Verify status changed to APPROVED
    assert data["id"] == rec.id
    assert data["status"] == "APPROVED"

    # Verify original fields are fully preserved
    assert data["recommended_quantity"] == 600
    assert data["supplier_id"] == supplier1.id
    assert data["product_id"] == product.id
    assert data["requested_delivery_date"] == "2026-11-28"

    # Verify all AI evaluation fields are fully preserved
    assert data["agent_decision"] == "MODIFY"
    assert data["agent_suggested_quantity"] == 450
    assert data["agent_suggested_supplier_id"] == supplier2.id
    assert data["agent_reasoning"] == rec.agent_reasoning
    assert "2026-11-03" in data["evaluated_at"]

    # Verify persistence in database
    db_session.expire_all()
    refreshed = db_session.query(PurchaseRecommendation).filter_by(id=rec.id).one()
    assert refreshed.status == "APPROVED"
    assert refreshed.recommended_quantity == 600
    assert refreshed.supplier_id == supplier1.id
    assert refreshed.agent_decision == "MODIFY"
    assert refreshed.agent_suggested_quantity == 450


def test_approve_recommendation_missing_404(client):
    response = client.post("/api/recommendations/99999/approve")
    assert response.status_code == 404
    assert response.json()["detail"] == "Purchase recommendation not found"


@pytest.mark.parametrize("initial_status", ["PENDING", "APPROVED", "REJECTED"])
def test_approve_recommendation_invalid_transitions_400(client, db_session, initial_status):
    product = Product(name="Control Relay", sku="RELAY-01")
    db_session.add(product)
    db_session.commit()

    rec = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=100,
        requested_delivery_date=date(2026, 12, 1),
        status=initial_status,
        agent_decision="ACCEPT",
    )
    db_session.add(rec)
    db_session.commit()

    response = client.post(f"/api/recommendations/{rec.id}/approve")
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert f"Cannot approve recommendation with status '{initial_status}'" in detail
    assert "Only recommendations with status 'PENDING_APPROVAL' can be approved." in detail


def test_approve_recommendation_direct_route(client, db_session):
    product = Product(name="Direct Route Item", sku="DIR-01")
    db_session.add(product)
    db_session.commit()

    rec = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=50,
        requested_delivery_date=date(2026, 12, 5),
        status="PENDING_APPROVAL",
    )
    db_session.add(rec)
    db_session.commit()

    # Route without /api prefix should also work
    response = client.post(f"/recommendations/{rec.id}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
