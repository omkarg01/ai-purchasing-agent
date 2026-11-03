from datetime import date, timedelta
from decimal import Decimal
import pytest
from app.models import (
    DemandForecast,
    EvaluationHistory,
    Inventory,
    Product,
    PurchaseRecommendation,
    PurchasingBudget,
    Supplier,
    SupplierProduct,
)


@pytest.fixture
def seed_eval_environment(db_session):
    """Sets up a complete purchasing environment for evaluation tests."""
    today = date.today()

    # Product
    product = Product(name="Control Valve X", sku="VALVE-X-1")
    db_session.add(product)
    db_session.flush()

    # Suppliers
    sup1 = Supplier(supplier_name="Alpha Industrial")
    sup2 = Supplier(supplier_name="Beta Logistics")
    db_session.add_all([sup1, sup2])
    db_session.flush()

    # Supplier Products
    sp1 = SupplierProduct(
        supplier_id=sup1.id,
        product_id=product.id,
        unit_price=Decimal("20.00"),
        lead_time_days=3,
        minimum_order_quantity=50,
    )
    sp2 = SupplierProduct(
        supplier_id=sup2.id,
        product_id=product.id,
        unit_price=Decimal("18.00"),
        lead_time_days=5,
        minimum_order_quantity=100,
    )
    db_session.add_all([sp1, sp2])

    # Inventory
    inv = Inventory(
        product_id=product.id,
        available_quantity=50,
        storage_capacity=1000,
    )
    db_session.add(inv)

    # Demand Forecast
    df = DemandForecast(
        product_id=product.id,
        period_start=today,
        period_end=today + timedelta(days=14),
        forecast_quantity=250,
    )
    db_session.add(df)

    # Budget
    budget = PurchasingBudget(
        total_budget=Decimal("50000.00"),
        committed_amount=Decimal("0.00"),
    )
    db_session.add(budget)

    # Initial Purchase Recommendation
    rec = PurchaseRecommendation(
        product_id=product.id,
        supplier_id=sup1.id,
        recommended_quantity=400,
        requested_delivery_date=today + timedelta(days=7),
        status="PENDING_APPROVAL",
    )
    db_session.add(rec)
    db_session.commit()

    return {
        "product": product,
        "sup1": sup1,
        "sup2": sup2,
        "recommendation": rec,
    }


def test_first_evaluation_creates_history_record(client, db_session, seed_eval_environment):
    rec = seed_eval_environment["recommendation"]
    sup1 = seed_eval_environment["sup1"]

    resp = client.post(f"/api/recommendations/{rec.id}/run-evaluation")
    assert resp.status_code == 200, resp.text

    history = (
        db_session.query(EvaluationHistory)
        .filter_by(recommendation_id=rec.id)
        .all()
    )
    assert len(history) == 1
    h1 = history[0]

    assert h1.evaluation_sequence == 1
    assert h1.evaluated_quantity == 400
    assert h1.evaluated_supplier_id == sup1.id
    # Test adjustment #1: Stored snapshot of supplier name
    assert h1.evaluated_supplier_name == "Alpha Industrial"
    assert h1.agent_decision in ["ACCEPT", "MODIFY", "REJECT", "INVESTIGATE"]
    assert h1.explanation is not None
    assert h1.calculations is not None
    # First evaluation has no buyer modifications
    assert h1.buyer_modifications is None


def test_subsequent_evaluation_creates_another_record(client, db_session, seed_eval_environment):
    rec = seed_eval_environment["recommendation"]

    # Evaluation #1
    r1 = client.post(f"/api/recommendations/{rec.id}/run-evaluation")
    assert r1.status_code == 200

    # Evaluation #2
    r2 = client.post(f"/api/recommendations/{rec.id}/run-evaluation")
    assert r2.status_code == 200

    history = (
        db_session.query(EvaluationHistory)
        .filter_by(recommendation_id=rec.id)
        .order_by(EvaluationHistory.evaluation_sequence.asc())
        .all()
    )
    assert len(history) == 2
    assert history[0].evaluation_sequence == 1
    assert history[1].evaluation_sequence == 2


def test_previous_evaluation_remains_unchanged(client, db_session, seed_eval_environment):
    rec = seed_eval_environment["recommendation"]

    # Evaluation #1
    client.post(f"/api/recommendations/{rec.id}/run-evaluation")
    h1_before = (
        db_session.query(EvaluationHistory)
        .filter_by(recommendation_id=rec.id, evaluation_sequence=1)
        .first()
    )
    h1_snapshot = {
        "id": h1_before.id,
        "quantity": h1_before.evaluated_quantity,
        "decision": h1_before.agent_decision,
        "explanation": h1_before.explanation,
        "supplier_name": h1_before.evaluated_supplier_name,
        "evaluated_at": h1_before.evaluated_at,
    }

    # Buyer modifies quantity
    client.put(
        f"/api/recommendations/{rec.id}",
        json={"recommended_quantity": 200},
    )

    # Evaluation #2
    client.post(f"/api/recommendations/{rec.id}/run-evaluation")

    # Verify Evaluation #1 is completely immutable
    db_session.expire_all()
    h1_after = (
        db_session.query(EvaluationHistory)
        .filter_by(recommendation_id=rec.id, evaluation_sequence=1)
        .first()
    )
    assert h1_after.id == h1_snapshot["id"]
    assert h1_after.evaluated_quantity == h1_snapshot["quantity"]
    assert h1_after.agent_decision == h1_snapshot["decision"]
    assert h1_after.explanation == h1_snapshot["explanation"]
    assert h1_after.evaluated_supplier_name == h1_snapshot["supplier_name"]
    assert h1_after.evaluated_at == h1_snapshot["evaluated_at"]


def test_buyer_quantity_modifications_recorded_correctly(client, db_session, seed_eval_environment):
    rec = seed_eval_environment["recommendation"]

    # Run initial evaluation with quantity 400
    client.post(f"/api/recommendations/{rec.id}/run-evaluation")

    # Buyer updates quantity from 400 to 200
    put_resp = client.put(
        f"/api/recommendations/{rec.id}",
        json={"recommended_quantity": 200},
    )
    assert put_resp.status_code == 200

    # Re-evaluate
    client.post(f"/api/recommendations/{rec.id}/run-evaluation")

    h2 = (
        db_session.query(EvaluationHistory)
        .filter_by(recommendation_id=rec.id, evaluation_sequence=2)
        .first()
    )
    assert h2 is not None
    assert h2.buyer_modifications is not None
    assert "quantity" in h2.buyer_modifications
    assert h2.buyer_modifications["quantity"] == {"previous": 400, "updated": 200}
    # Supplier wasn't changed, so not in buyer_modifications
    assert "supplier" not in h2.buyer_modifications


def test_buyer_supplier_modifications_recorded_correctly(client, db_session, seed_eval_environment):
    rec = seed_eval_environment["recommendation"]
    sup1 = seed_eval_environment["sup1"]
    sup2 = seed_eval_environment["sup2"]

    # Run initial evaluation
    client.post(f"/api/recommendations/{rec.id}/run-evaluation")

    # Buyer changes supplier from sup1 to sup2
    put_resp = client.put(
        f"/api/recommendations/{rec.id}",
        json={"supplier_id": sup2.id},
    )
    assert put_resp.status_code == 200

    # Re-evaluate
    client.post(f"/api/recommendations/{rec.id}/run-evaluation")

    h2 = (
        db_session.query(EvaluationHistory)
        .filter_by(recommendation_id=rec.id, evaluation_sequence=2)
        .first()
    )
    assert h2 is not None
    assert h2.buyer_modifications is not None
    assert "supplier" in h2.buyer_modifications
    assert h2.buyer_modifications["supplier"] == {
        "previous": sup1.id,
        "updated": sup2.id,
        "previous_name": "Alpha Industrial",
        "updated_name": "Beta Logistics",
    }
    assert h2.evaluated_supplier_name == "Beta Logistics"


def test_history_api_returns_evaluations_in_chronological_order(client, db_session, seed_eval_environment):
    rec = seed_eval_environment["recommendation"]

    # 1. Run 3 evaluations with edits
    client.post(f"/api/recommendations/{rec.id}/run-evaluation")

    client.put(f"/api/recommendations/{rec.id}", json={"recommended_quantity": 300})
    client.post(f"/api/recommendations/{rec.id}/run-evaluation")

    client.put(f"/api/recommendations/{rec.id}", json={"recommended_quantity": 200})
    client.post(f"/api/recommendations/{rec.id}/run-evaluation")

    # 2. Call history API
    resp = client.get(f"/api/recommendations/{rec.id}/history")
    assert resp.status_code == 200
    history = resp.json()

    assert len(history) == 3
    assert history[0]["evaluation_sequence"] == 1
    assert history[0]["evaluated_quantity"] == 400
    assert history[0]["buyer_modifications"] is None

    assert history[1]["evaluation_sequence"] == 2
    assert history[1]["evaluated_quantity"] == 300
    assert history[1]["buyer_modifications"]["quantity"]["previous"] == 400
    assert history[1]["buyer_modifications"]["quantity"]["updated"] == 300

    assert history[2]["evaluation_sequence"] == 3
    assert history[2]["evaluated_quantity"] == 200
    assert history[2]["buyer_modifications"]["quantity"]["previous"] == 300
    assert history[2]["buyer_modifications"]["quantity"]["updated"] == 200

    # 3. Non-existent recommendation returns 404
    err_resp = client.get("/api/recommendations/99999/history")
    assert err_resp.status_code == 404

