from datetime import date, timedelta
from decimal import Decimal
import pytest

from app.decision_engine.inventory import (
    analyze_chronological_stockout_timeline,
    calculate_daily_demand,
)
from app.decision_engine.types import (
    DemandForecastInput,
    EngineInput,
    InventoryInput,
    OpenPurchaseOrderInput,
    RecommendationToEvaluate,
    SupplierProductInput,
    BudgetInput,
)
from app.decision_engine.engine import evaluate_purchasing_decision


def test_safety_stock_triggers_replenishment_when_stock_matches_forecast():
    """Rule 1: Verify that configuring a safety stock buffer causes the engine
    to recommend purchasing even when on-hand stock equals forecast demand.
    """
    today = date(2026, 11, 3)
    forecast = DemandForecastInput(
        forecast_quantity=100,
        period_start=today,
        period_end=today + timedelta(days=10),
    )
    
    # 1. Without safety stock: on-hand 100 covers demand 100 -> shortage is 0
    timeline_no_buffer = analyze_chronological_stockout_timeline(
        on_hand=100,
        forecast=forecast,
        open_orders=[],
        evaluation_date=today,
        safety_stock_quantity=0,
    )
    assert timeline_no_buffer.final_unmet_demand == 0
    assert timeline_no_buffer.additional_purchasing_requirement == 0

    # 2. With safety stock of 40 units: gross requirement is 140 -> shortage is 40
    timeline_with_buffer = analyze_chronological_stockout_timeline(
        on_hand=100,
        forecast=forecast,
        open_orders=[],
        evaluation_date=today,
        safety_stock_quantity=40,
    )
    assert timeline_with_buffer.final_unmet_demand == 40
    assert timeline_with_buffer.additional_purchasing_requirement == 40
    assert timeline_with_buffer.target_ending_inventory == 40


def test_discrete_daily_demand_catches_early_stockout():
    """FM-4: Verify that discrete daily demand series detects early consumption spikes
    that would be missed by flat daily burn rate averages.
    """
    today = date(2026, 11, 3)
    
    # 100 units total over 10 days
    # Flat rate: 10 units/day -> on-hand of 30 units lasts 3 days (stockout Day 3)
    forecast_flat = DemandForecastInput(
        forecast_quantity=100,
        period_start=today,
        period_end=today + timedelta(days=10),
    )
    timeline_flat = analyze_chronological_stockout_timeline(
        on_hand=30,
        forecast=forecast_flat,
        open_orders=[],
        evaluation_date=today,
    )
    assert timeline_flat.stockout_date == today + timedelta(days=3)

    # Discrete curve: Day 0 = 20, Day 1 = 20 (batch job requires 40 units in first 2 days)
    # On-hand 30 units: Day 0 drops to 10. Day 1 drops to -10 (stockout on Day 1!)
    forecast_discrete = DemandForecastInput(
        forecast_quantity=100,
        period_start=today,
        period_end=today + timedelta(days=10),
        daily_demand_series=[20, 20, 10, 10, 10, 10, 5, 5, 5, 5],
    )
    timeline_discrete = analyze_chronological_stockout_timeline(
        on_hand=30,
        forecast=forecast_discrete,
        open_orders=[],
        evaluation_date=today,
    )
    assert timeline_discrete.has_interim_stockout is True
    # Stockout occurs on Day 1 (2026-11-04), 2 days earlier than the flat average predicted!
    assert timeline_discrete.stockout_date == today + timedelta(days=1)


def test_engine_end_to_end_safety_stock_decision():
    """Verify end-to-end engine outputs MODIFY to order safety buffer."""
    today = date(2026, 11, 3)
    engine_input = EngineInput(
        evaluation_date=today,
        recommendation=RecommendationToEvaluate(
            id=1,
            product_id=1,
            recommended_quantity=10,  # Buyer originally proposed only 10
            supplier_id=1,
            requested_delivery_date=today + timedelta(days=8),
        ),
        inventory=InventoryInput(
            available_quantity=100,
            storage_capacity=500,
            safety_stock_quantity=50,  # Buffer 50 units
        ),
        forecast=DemandForecastInput(
            forecast_quantity=100,
            period_start=today,
            period_end=today + timedelta(days=10),
        ),
        open_orders=[],
        suppliers=[
            SupplierProductInput(
                supplier_id=1,
                supplier_name="Acme Supplies",
                unit_price=Decimal("10.00"),
                lead_time_days=4,
                minimum_order_quantity=10,
            )
        ],
        budget=BudgetInput(
            total_budget=Decimal("5000.00"),
            committed_amount=Decimal("0.00"),
        ),
    )

    result = evaluate_purchasing_decision(engine_input)
    # Net shortage is 50 (safety stock buffer). Suggested quantity must be 50.
    assert result.decision == "MODIFY"
    assert result.suggested_quantity == 50
    assert result.calculations["safety_stock_quantity"] == 50
    assert result.calculations["additional_purchasing_requirement"] == 50
