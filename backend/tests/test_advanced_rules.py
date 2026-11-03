from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.decision_engine.engine import evaluate_purchasing_decision
from app.decision_engine.suppliers import evaluate_supplier_product
from app.decision_engine.types import (
    BudgetInput,
    DemandForecastInput,
    EngineInput,
    InventoryInput,
    PriceTier,
    RecommendationToEvaluate,
    SupplierProductInput,
)
from app.models import Product, PurchaseRecommendation, Supplier, SupplierProduct


def test_rule_2_shelf_life_spoilage_guard():
    """Rule 2: If supplier MOQ forces an order that exceeds demand during product shelf life,
    the engine flags spoilage risk and treats it as infeasible.
    """
    today = date(2026, 11, 3)

    supplier = SupplierProductInput(
        supplier_id=1,
        supplier_name="Bulk Chemical Vendor",
        unit_price=Decimal("5.00"),
        lead_time_days=3,
        minimum_order_quantity=500,  # MOQ is 500 units!
    )

    # Daily demand is 10 units. Shelf life is 10 days -> max consumption is 100 units.
    # MOQ 500 will cause 400 units (80%) to spoil!
    option = evaluate_supplier_product(
        supplier_prod=supplier,
        net_shortage=50,
        remaining_budget=Decimal("10000.00"),
        storage_capacity=1000,
        on_hand=0,
        daily_demand=10.0,
        open_orders=[],
        evaluation_date=today,
        target_delivery_date=today + timedelta(days=7),
        shelf_life_days=10,  # 10 days shelf life
    )

    assert option.is_storage_feasible is False
    assert any("Shelf-life spoilage risk" in t for t in option.trade_offs)
    assert any("400 spoiled/expired units" in t for t in option.trade_offs)


def test_rule_4_facility_aggregate_storage_cap():
    """Rule 4: Verify that total facility cubic volume constraint prevents warehouse overflow."""
    today = date(2026, 11, 3)

    supplier = SupplierProductInput(
        supplier_id=1,
        supplier_name="Heavy Machinery Parts",
        unit_price=Decimal("100.00"),
        lead_time_days=4,
        minimum_order_quantity=100,
    )

    # 100 units * 2.5 m3/unit = 250 m3. Available facility space is only 150 m3.
    option = evaluate_supplier_product(
        supplier_prod=supplier,
        net_shortage=100,
        remaining_budget=Decimal("50000.00"),
        storage_capacity=1000,  # SKU unit limit is large (1000)
        on_hand=0,
        daily_demand=5.0,
        open_orders=[],
        evaluation_date=today,
        target_delivery_date=today + timedelta(days=10),
        unit_volume_m3=2.5,
        facility_available_m3=150.0,  # Only 150 m3 total facility space available
    )

    assert option.is_storage_feasible is False
    assert any("Facility volume exceeded" in t for t in option.trade_offs)
    assert any("250.0 m³" in t for t in option.trade_offs)


def test_rule_5_supplier_otif_delay_variance_padding():
    """Rule 5: Verify that historical supplier delay days pad quoted lead time and can cause timing infeasibility."""
    today = date(2026, 11, 3)

    # Quoted lead time is 4 days, but historical delay is 3 days -> effective lead time is 7 days!
    supplier_unreliable = SupplierProductInput(
        supplier_id=1,
        supplier_name="Frequently Late Logistics",
        unit_price=Decimal("20.00"),
        lead_time_days=4,
        minimum_order_quantity=10,
        historical_delay_days=3,  # 3 days delay buffer
    )

    # Target delivery date is Day 5. Quoted 4 days would pass, but effective 7 days misses deadline!
    option = evaluate_supplier_product(
        supplier_prod=supplier_unreliable,
        net_shortage=10,
        remaining_budget=Decimal("1000.00"),
        storage_capacity=100,
        on_hand=0,
        daily_demand=2.0,
        open_orders=[],
        evaluation_date=today,
        target_delivery_date=today + timedelta(days=5),
    )

    assert option.effective_lead_time_days == 7
    assert option.is_timing_feasible is False
    assert any("padded by 3 day(s) (effective: 7 days)" in t for t in option.trade_offs)


def test_rule_6_volume_price_break_tier_optimization():
    """Rule 6: Verify volume price discount tiers identify opportunities where buying more units saves net money."""
    today = date(2026, 11, 3)

    # Base price: $10.00/unit for MOQ 10.
    # Volume tier: 100 units at $7.00/unit.
    # Buying 90 units at $10 = $900.
    # Buying 100 units at $7 = $700 ($200 net savings!).
    supplier_tiers = SupplierProductInput(
        supplier_id=1,
        supplier_name="Bulk Electronics Direct",
        unit_price=Decimal("10.00"),
        lead_time_days=4,
        minimum_order_quantity=10,
        price_tiers=[
            PriceTier(min_quantity=50, unit_price=Decimal("9.00")),
            PriceTier(min_quantity=100, unit_price=Decimal("7.00")),
        ],
    )

    option = evaluate_supplier_product(
        supplier_prod=supplier_tiers,
        net_shortage=90,
        remaining_budget=Decimal("5000.00"),
        storage_capacity=500,
        on_hand=0,
        daily_demand=5.0,
        open_orders=[],
        evaluation_date=today,
        target_delivery_date=today + timedelta(days=8),
    )

    assert any("Volume price break opportunity" in t for t in option.trade_offs)
    assert any("saving $110.00 net" in t or "saving" in t for t in option.trade_offs)


def test_governance_approval_threshold_limit(client, db_session):
    """FM-7: Verify approval threshold blocks orders exceeding $10,000 without manager override."""
    prod = Product(name="High Precision Sensor", sku="SENS-HP-999")
    supp = Supplier(supplier_name="Enterprise Aerospace Supply")
    db_session.add_all([prod, supp])
    db_session.flush()

    # Price $100/unit
    sp = SupplierProduct(
        supplier_id=supp.id,
        product_id=prod.id,
        unit_price=Decimal("100.00"),
        lead_time_days=5,
        minimum_order_quantity=10,
    )
    db_session.add(sp)

    # Order 150 units * $100 = $15,000 (exceeds $10,000 threshold!)
    rec = PurchaseRecommendation(
        product_id=prod.id,
        supplier_id=supp.id,
        recommended_quantity=150,
        requested_delivery_date=date(2026, 11, 20),
        status="PENDING_APPROVAL",
    )
    db_session.add(rec)
    db_session.commit()

    # 1. Attempt approval without override -> 400 Bad Request
    res_blocked = client.post(f"/api/recommendations/{rec.id}/approve")
    assert res_blocked.status_code == 400
    assert "exceeds the direct approval threshold limit" in res_blocked.json()["detail"]

    # 2. Approval with manager override -> 200 OK
    res_override = client.post(
        f"/api/recommendations/{rec.id}/approve",
        json={"manager_override": True},
    )
    assert res_override.status_code == 200
    assert res_override.json()["status"] == "APPROVED"
