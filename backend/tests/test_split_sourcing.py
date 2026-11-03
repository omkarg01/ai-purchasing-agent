from datetime import date, timedelta
from decimal import Decimal
import pytest

from app.decision_engine.engine import evaluate_purchasing_decision
from app.decision_engine.options import generate_purchasing_options
from app.decision_engine.types import (
    BudgetInput,
    DemandForecastInput,
    EngineInput,
    InventoryInput,
    RecommendationToEvaluate,
    SupplierProductInput,
)


def test_assignment_scenario_2_split_sourcing_allocation():
    """Assignment Scenario 2 Verification:
    Requirement is 500 units.
    Primary supplier (Acme) confirms only 250 units capacity.
    Secondary supplier (Global) can fulfill the remainder.
    Engine must output a split-sourcing recommendation allocating 250 to Acme and 250 to Global.
    """
    today = date(2026, 11, 3)

    supplier_acme = SupplierProductInput(
        supplier_id=1,
        supplier_name="Acme Industrial",
        unit_price=Decimal("10.00"),
        lead_time_days=4,
        minimum_order_quantity=50,
        available_capacity=250,  # Capacity capped at 250!
    )
    supplier_global = SupplierProductInput(
        supplier_id=2,
        supplier_name="Global Parts",
        unit_price=Decimal("12.00"),
        lead_time_days=5,
        minimum_order_quantity=100,
        available_capacity=500,
    )

    engine_input = EngineInput(
        evaluation_date=today,
        recommendation=RecommendationToEvaluate(
            id=10,
            product_id=101,
            recommended_quantity=500,  # Recommended 500 from Acme
            supplier_id=1,
            requested_delivery_date=today + timedelta(days=7),
        ),
        inventory=InventoryInput(
            available_quantity=0,
            storage_capacity=1000,
            safety_stock_quantity=0,
        ),
        forecast=DemandForecastInput(
            forecast_quantity=500,
            period_start=today,
            period_end=today + timedelta(days=14),
        ),
        open_orders=[],
        suppliers=[supplier_acme, supplier_global],
        budget=BudgetInput(
            total_budget=Decimal("15000.00"),
            committed_amount=Decimal("0.00"),
        ),
    )

    result = evaluate_purchasing_decision(engine_input)

    # 1. Decision must be MODIFY
    assert result.decision == "MODIFY"
    # Total suggested quantity must be 500
    assert result.suggested_quantity == 500

    # 2. Preferred option must be split sourcing
    assert result.preferred_option is not None
    assert result.preferred_option.is_split_sourcing is True
    assert "Split Sourcing" in result.preferred_option.supplier_name

    # 3. Calculation must contain split allocation details
    assert result.calculations["is_split_sourcing"] is True
    split = result.calculations["split_allocation"]
    assert split["primary_supplier_id"] == 1
    assert split["primary_supplier_name"] == "Acme Industrial"
    assert split["primary_quantity"] == 250
    assert split["primary_cost"] == 2500.00  # 250 * $10.00

    assert split["secondary_supplier_id"] == 2
    assert split["secondary_supplier_name"] == "Global Parts"
    assert split["secondary_quantity"] == 250
    assert split["secondary_cost"] == 3000.00  # 250 * $12.00
    assert split["total_cost"] == 5500.00

    # 4. Reasoning points must describe the split
    assert any("250 units with Acme Industrial" in r for r in result.reasoning_points)
    assert any("250 units with Global Parts" in r for r in result.reasoning_points)
