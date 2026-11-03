from datetime import date, timedelta
from decimal import Decimal
import pytest

from app.agent.purchasing_agent import _generate_deterministic_briefing
from app.decision_engine.engine import evaluate_purchasing_decision
from app.decision_engine.inventory import analyze_chronological_stockout_timeline
from app.decision_engine.options import generate_negotiation_levers
from app.decision_engine.types import (
    BudgetInput,
    DemandForecastInput,
    EngineInput,
    InventoryInput,
    NegotiationLever,
    RecommendationToEvaluate,
    SupplierProductInput,
)


def test_lead_time_expediting_lever():
    """Verifies that an off-schedule supplier generates an exact lead time expediting target."""
    eval_date = date(2026, 11, 3)
    stockout_date = date(2026, 11, 9)  # 6 days away

    forecast = DemandForecastInput(
        forecast_quantity=600,
        period_start=eval_date,
        period_end=eval_date + timedelta(days=30),
    )
    timeline = analyze_chronological_stockout_timeline(
        on_hand=120,  # 120 / (600/30 = 20/day) = 6 days coverage -> stockout on Nov 9
        forecast=forecast,
        open_orders=[],
        evaluation_date=eval_date,
    )
    assert timeline.stockout_date == stockout_date

    suppliers = [
        SupplierProductInput(
            supplier_id=1,
            supplier_name="Acme Parts",
            unit_price=Decimal("20.00"),
            lead_time_days=10,  # 10 days > 6 days -> late by 4 days
            minimum_order_quantity=50,
            expedited_lead_time_days=5,
        )
    ]

    levers = generate_negotiation_levers(
        suppliers=suppliers,
        timeline=timeline,
        net_shortage=480,
        evaluation_date=eval_date,
        target_delivery_date=date(2026, 11, 15),
    )

    lead_levers = [l for l in levers if l.lever_type == "LEAD_TIME_EXPEDITE"]
    assert len(lead_levers) == 1
    lev = lead_levers[0]
    assert lev.target_supplier_id == 1
    assert lev.current_value == "10 days"
    assert lev.target_value == "<= 6 days"
    assert "from 10 days to <= 6 days" in lev.recommended_talking_point
    assert "target delivery: 2026-11-09" in lev.recommended_talking_point
    assert "expedited capability of 5 days" in lev.recommended_talking_point


def test_moq_reduction_lever():
    """Verifies that supplier MOQ excess generates an exact capital holding savings target."""
    eval_date = date(2026, 11, 3)
    forecast = DemandForecastInput(
        forecast_quantity=100,
        period_start=eval_date,
        period_end=eval_date + timedelta(days=10),
    )
    timeline = analyze_chronological_stockout_timeline(
        on_hand=60,  # 100 - 60 = 40 net shortage
        forecast=forecast,
        open_orders=[],
        evaluation_date=eval_date,
    )

    suppliers = [
        SupplierProductInput(
            supplier_id=2,
            supplier_name="Bulk Supply Co",
            unit_price=Decimal("15.00"),
            lead_time_days=3,
            minimum_order_quantity=100,  # MOQ 100 vs shortage 40 -> 60 excess
            is_moq_negotiable=True,
        )
    ]

    levers = generate_negotiation_levers(
        suppliers=suppliers,
        timeline=timeline,
        net_shortage=40,
        evaluation_date=eval_date,
        target_delivery_date=date(2026, 11, 10),
    )

    moq_levers = [l for l in levers if l.lever_type == "MOQ_REDUCTION"]
    assert len(moq_levers) == 1
    lev = moq_levers[0]
    assert lev.current_value == "100 units"
    assert lev.target_value == "40 units"
    assert lev.potential_savings == 900.0  # 60 excess * $15.00 = $900.00
    assert "reduction from 100 to 40 units" in lev.recommended_talking_point
    assert "$900.00 in excess holding stock" in lev.recommended_talking_point
    assert "flexibility on minimum order quantities" in lev.recommended_talking_point


def test_price_benchmark_counter_offer():
    """Verifies that price benchmarking against qualified competitors generates exact contract savings."""
    eval_date = date(2026, 11, 3)
    forecast = DemandForecastInput(
        forecast_quantity=500,
        period_start=eval_date,
        period_end=eval_date + timedelta(days=20),
    )
    timeline = analyze_chronological_stockout_timeline(
        on_hand=0,
        forecast=forecast,
        open_orders=[],
        evaluation_date=eval_date,
    )

    suppliers = [
        SupplierProductInput(
            supplier_id=1,
            supplier_name="Incumbent Premium Vendor",
            unit_price=Decimal("15.00"),
            lead_time_days=5,
            minimum_order_quantity=50,
        ),
        SupplierProductInput(
            supplier_id=2,
            supplier_name="Cheaper Qualified Alternate",
            unit_price=Decimal("13.50"),
            lead_time_days=5,
            minimum_order_quantity=50,
        ),
    ]

    levers = generate_negotiation_levers(
        suppliers=suppliers,
        timeline=timeline,
        net_shortage=500,
        evaluation_date=eval_date,
        target_delivery_date=date(2026, 11, 10),
        incumbent_supplier_id=1,
    )

    price_levers = [l for l in levers if l.lever_type == "PRICE_BENCHMARK_COUNTER_OFFER"]
    assert len(price_levers) == 1
    lev = price_levers[0]
    assert lev.target_supplier_id == 1
    assert lev.current_value == "$15.00/unit"
    assert lev.target_value == "$13.50/unit"
    # ($15.00 - $13.50) * 500 = $750.00 savings
    assert lev.potential_savings == 750.0
    assert "Counter-offer incumbent supplier Incumbent Premium Vendor at $13.50/unit" in lev.recommended_talking_point
    assert "$750.00" in lev.recommended_talking_point


def test_partial_batch_delivery_lever():
    """Verifies that imminent stockout triggers an exact partial critical shipment breakdown."""
    eval_date = date(2026, 11, 3)
    stockout_date = date(2026, 11, 8)  # 5 days of coverage
    forecast = DemandForecastInput(
        forecast_quantity=500,
        period_start=eval_date,
        period_end=eval_date + timedelta(days=20),
    )
    # Burn rate: 500/20 = 25/day. 5 days * 25 = 125 stock
    timeline = analyze_chronological_stockout_timeline(
        on_hand=125,
        forecast=forecast,
        open_orders=[],
        evaluation_date=eval_date,
    )

    suppliers = [
        SupplierProductInput(
            supplier_id=1,
            supplier_name="Long Haul Logistics",
            unit_price=Decimal("10.00"),
            lead_time_days=10,  # Arrives on Nov 13, 5 days after Nov 8 stockout
            minimum_order_quantity=100,
        )
    ]

    levers = generate_negotiation_levers(
        suppliers=suppliers,
        timeline=timeline,
        net_shortage=375,
        evaluation_date=eval_date,
        target_delivery_date=date(2026, 11, 14),
    )

    batch_levers = [l for l in levers if l.lever_type == "PARTIAL_BATCH_DELIVERY"]
    assert len(batch_levers) == 1
    lev = batch_levers[0]
    assert lev.target_supplier_id == 1
    assert "priority air-shipment" in lev.recommended_talking_point
    assert "standard ground transit" in lev.recommended_talking_point


def test_deterministic_fallback_negotiation_section():
    """Verifies executive structured briefing and negotiation talking points in deterministic fallback."""
    eval_date = date(2026, 11, 3)
    rec = RecommendationToEvaluate(
        id=1,
        product_id=1,
        recommended_quantity=500,
        supplier_id=1,
        requested_delivery_date=date(2026, 11, 15),
    )
    inv = InventoryInput(available_quantity=100, storage_capacity=1000)
    fc = DemandForecastInput(
        forecast_quantity=600,
        period_start=eval_date,
        period_end=eval_date + timedelta(days=14),
    )
    suppliers = [
        SupplierProductInput(
            supplier_id=1,
            supplier_name="Acme Parts",
            unit_price=Decimal("10.00"),
            lead_time_days=4,
            minimum_order_quantity=100,
            available_capacity=250,
        ),
        SupplierProductInput(
            supplier_id=2,
            supplier_name="Global Logistics",
            unit_price=Decimal("12.00"),
            lead_time_days=5,
            minimum_order_quantity=100,
            available_capacity=500,
        ),
    ]
    budget = BudgetInput(total_budget=Decimal("50000.00"), committed_amount=Decimal("0.00"))

    engine_input = EngineInput(
        evaluation_date=eval_date,
        recommendation=rec,
        inventory=inv,
        forecast=fc,
        open_orders=[],
        suppliers=suppliers,
        budget=budget,
    )

    res = evaluate_purchasing_decision(engine_input)
    assert res.decision == "MODIFY"
    assert "negotiation_levers" in res.calculations

    briefing = _generate_deterministic_briefing(engine_input, res, "Industrial Bearing A", "SKU-BEAR-01")
    assert "**Strategic Assessment**" in briefing
    assert "**Supply & Operational Analysis**" in briefing
    assert "**Recommended Buyer Action Plan**" in briefing
    assert "#### Buyer Negotiation Strategy & Counter-Offers" in briefing
    assert "Counter-offer incumbent supplier" in briefing or "Expedite Lead Time" in briefing
