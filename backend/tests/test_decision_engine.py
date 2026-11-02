from datetime import date, timedelta
from decimal import Decimal
import pytest

from app.decision_engine import (
    BudgetInput,
    DemandForecastInput,
    EngineInput,
    InventoryInput,
    OpenPurchaseOrderInput,
    RecommendationToEvaluate,
    SupplierProductInput,
    evaluate_purchasing_decision,
)
from app.decision_engine.inventory import (
    analyze_chronological_stockout_timeline,
    calculate_daily_demand,
)
from app.decision_engine.suppliers import (
    calculate_projected_stock_at_arrival,
    evaluate_supplier_product,
)


def test_calculate_daily_demand():
    forecast = DemandForecastInput(
        forecast_quantity=900,
        period_start=date(2026, 11, 1),
        period_end=date(2026, 11, 15),  # 14 days
    )
    daily_demand = calculate_daily_demand(forecast)
    assert round(daily_demand, 2) == 64.29


def test_inventory_timeline_with_interim_stockout():
    start = date(2026, 11, 1)
    end = date(2026, 11, 15)  # 14 days
    forecast = DemandForecastInput(
        forecast_quantity=900,
        period_start=start,
        period_end=end,
    )
    po = OpenPurchaseOrderInput(
        id=1,
        supplier_id=10,
        quantity=400,
        unit_price=Decimal("10.00"),
        expected_delivery_date=start + timedelta(days=8),
        status="OPEN",
    )

    analysis = analyze_chronological_stockout_timeline(
        on_hand=300,
        forecast=forecast,
        open_orders=[po],
        evaluation_date=start,
    )

    assert round(analysis.days_of_initial_coverage, 1) == 4.7
    assert analysis.has_interim_stockout is True
    assert analysis.interim_stockout_days > 0
    assert analysis.final_unmet_demand == 200  # 900 - (300 + 400)
    assert analysis.additional_purchasing_requirement == 200


def test_inventory_timeline_po_arrives_before_stockout():
    start = date(2026, 11, 1)
    end = date(2026, 11, 15)
    forecast = DemandForecastInput(
        forecast_quantity=900,
        period_start=start,
        period_end=end,
    )
    po = OpenPurchaseOrderInput(
        id=2,
        supplier_id=10,
        quantity=700,
        unit_price=Decimal("10.00"),
        expected_delivery_date=start + timedelta(days=2),
        status="OPEN",
    )

    analysis = analyze_chronological_stockout_timeline(
        on_hand=300,
        forecast=forecast,
        open_orders=[po],
        evaluation_date=start,
    )

    assert analysis.has_interim_stockout is False
    assert analysis.interim_stockout_days == 0
    assert analysis.final_unmet_demand == 0
    assert analysis.additional_purchasing_requirement == 0


def test_supplier_evaluation_moq_and_excess():
    start = date(2026, 11, 1)
    supplier = SupplierProductInput(
        supplier_id=1,
        supplier_name="Bulk Supplier",
        unit_price=Decimal("12.50"),
        lead_time_days=4,
        minimum_order_quantity=500,
    )
    option = evaluate_supplier_product(
        supplier_prod=supplier,
        net_shortage=300,
        remaining_budget=Decimal("10000.00"),
        storage_capacity=1000,
        on_hand=100,
        daily_demand=20.0,
        open_orders=[],
        evaluation_date=start,
        target_delivery_date=start + timedelta(days=5),
    )
    assert option.quantity == 500
    assert option.excess_quantity == 200
    assert option.total_cost == 6250.0
    assert option.is_budget_feasible is True
    assert option.is_timing_feasible is True
    assert option.is_storage_feasible is True


# --- Full Decision Engine Business Rules Scenarios ---


def test_scenario_1_inventory_sufficient_rejects():
    """Scenario 1: On-hand inventory covers demand -> REJECT with suggested_qty=0."""
    start = date(2026, 11, 1)
    engine_input = EngineInput(
        evaluation_date=start,
        recommendation=RecommendationToEvaluate(
            id=1,
            product_id=101,
            recommended_quantity=500,
            supplier_id=1,
            requested_delivery_date=start + timedelta(days=10),
        ),
        inventory=InventoryInput(available_quantity=1000, storage_capacity=2000),
        forecast=DemandForecastInput(
            forecast_quantity=800,
            period_start=start,
            period_end=start + timedelta(days=14),
        ),
        open_orders=[],
        suppliers=[
            SupplierProductInput(
                supplier_id=1,
                supplier_name="Standard Co",
                unit_price=Decimal("15.00"),
                lead_time_days=5,
                minimum_order_quantity=100,
            )
        ],
        budget=BudgetInput(
            total_budget=Decimal("20000.00"),
            committed_amount=Decimal("0.00"),
        ),
    )

    result = evaluate_purchasing_decision(engine_input)
    assert result.decision == "REJECT"
    assert result.suggested_quantity == 0
    assert result.calculations["final_unmet_demand"] == 0
    assert any("unnecessary" in r.lower() for r in result.reasoning_points)


def test_scenario_2_stockout_before_open_po_arrives_investigates():
    """Scenario 2: Stockout gap before PO arrives and no fast supplier -> INVESTIGATE."""
    start = date(2026, 11, 1)
    engine_input = EngineInput(
        evaluation_date=start,
        recommendation=RecommendationToEvaluate(
            id=2,
            product_id=101,
            recommended_quantity=400,
            supplier_id=1,
            requested_delivery_date=start + timedelta(days=10),
        ),
        inventory=InventoryInput(available_quantity=300, storage_capacity=2000),
        forecast=DemandForecastInput(
            forecast_quantity=900,
            period_start=start,
            period_end=start + timedelta(days=14),
        ),
        open_orders=[
            OpenPurchaseOrderInput(
                id=101,
                supplier_id=1,
                supplier_name="Primary Vendor",
                quantity=400,
                unit_price=Decimal("10.00"),
                expected_delivery_date=start + timedelta(days=8),
            )
        ],
        # Supplier lead time is 10 days, meaning new order arrives at Day 10 (too late to avert Day 4.7 stockout)
        suppliers=[
            SupplierProductInput(
                supplier_id=1,
                supplier_name="Primary Vendor",
                unit_price=Decimal("10.00"),
                lead_time_days=10,
                minimum_order_quantity=100,
            )
        ],
        budget=BudgetInput(
            total_budget=Decimal("50000.00"),
            committed_amount=Decimal("4000.00"),
        ),
    )

    result = evaluate_purchasing_decision(engine_input)
    assert result.decision == "INVESTIGATE"
    assert result.calculations["has_interim_stockout"] is True
    # Verify investigation pathway generated for existing supplier expedite
    expedite_paths = [
        p for p in result.investigation_options if p.pathway_type == "EXISTING_SUPPLIER_EXPEDITE"
    ]
    assert len(expedite_paths) >= 1
    assert expedite_paths[0].is_confirmed is False
    assert "Primary Vendor" in expedite_paths[0].description


def test_scenario_3_open_po_arrives_before_stockout_rejects():
    """Scenario 3: Open PO arrives safely before coverage depletes -> REJECT redundant purchase."""
    start = date(2026, 11, 1)
    engine_input = EngineInput(
        evaluation_date=start,
        recommendation=RecommendationToEvaluate(
            id=3,
            product_id=101,
            recommended_quantity=400,
            supplier_id=1,
            requested_delivery_date=start + timedelta(days=10),
        ),
        inventory=InventoryInput(available_quantity=500, storage_capacity=2000),
        forecast=DemandForecastInput(
            forecast_quantity=900,
            period_start=start,
            period_end=start + timedelta(days=14),
        ),
        open_orders=[
            OpenPurchaseOrderInput(
                id=102,
                supplier_id=1,
                quantity=400,
                unit_price=Decimal("10.00"),
                expected_delivery_date=start + timedelta(days=3),  # Arrives Day 3 (well before Day 7.7 depletion)
            )
        ],
        suppliers=[
            SupplierProductInput(
                supplier_id=1,
                supplier_name="Primary Vendor",
                unit_price=Decimal("10.00"),
                lead_time_days=5,
                minimum_order_quantity=100,
            )
        ],
        budget=BudgetInput(
            total_budget=Decimal("50000.00"),
            committed_amount=Decimal("4000.00"),
        ),
    )

    result = evaluate_purchasing_decision(engine_input)
    assert result.decision == "REJECT"
    assert result.suggested_quantity == 0


def test_scenario_4_prioritize_feasible_alternative_over_investigate():
    """Gap 1: When default supplier is slow, but feasible alternative can prevent stockout -> MODIFY."""
    start = date(2026, 11, 1)
    # Target delivery date is Day 4 (Nov 5)
    target = start + timedelta(days=4)
    engine_input = EngineInput(
        evaluation_date=start,
        recommendation=RecommendationToEvaluate(
            id=4,
            product_id=101,
            recommended_quantity=200,
            supplier_id=1,  # Recommended supplier is slow
            requested_delivery_date=target,
        ),
        inventory=InventoryInput(available_quantity=100, storage_capacity=1000),
        forecast=DemandForecastInput(
            forecast_quantity=300,
            period_start=start,
            period_end=start + timedelta(days=6),  # 50 units/day -> 2 days coverage (stockout Day 2)
        ),
        open_orders=[],
        suppliers=[
            SupplierProductInput(
                supplier_id=1,
                supplier_name="Slow Primary",
                unit_price=Decimal("10.00"),
                lead_time_days=7,  # Misses Day 2 stockout
                minimum_order_quantity=100,
            ),
            SupplierProductInput(
                supplier_id=2,
                supplier_name="Fast Alternative",
                unit_price=Decimal("12.00"),
                lead_time_days=1,  # Arrives in 1 day! Prevents stockout!
                minimum_order_quantity=150,
            ),
        ],
        budget=BudgetInput(
            total_budget=Decimal("10000.00"),
            committed_amount=Decimal("0.00"),
        ),
    )

    result = evaluate_purchasing_decision(engine_input)
    # Must prioritize alternative supplier over INVESTIGATE!
    assert result.decision == "MODIFY"
    assert result.suggested_supplier_id == 2
    assert result.suggested_quantity == 200
    assert result.preferred_option is not None
    assert result.preferred_option.supplier_name == "Fast Alternative"


def test_scenario_5_alternative_supplier_higher_moq():
    """Scenario 5: Net shortage is 150, supplier MOQ is 200 -> MODIFY to 200 with excess note."""
    start = date(2026, 11, 1)
    engine_input = EngineInput(
        evaluation_date=start,
        recommendation=RecommendationToEvaluate(
            id=5,
            product_id=101,
            recommended_quantity=150,
            supplier_id=1,
            requested_delivery_date=start + timedelta(days=5),
        ),
        inventory=InventoryInput(available_quantity=50, storage_capacity=1000),
        forecast=DemandForecastInput(
            forecast_quantity=200,
            period_start=start,
            period_end=start + timedelta(days=10),
        ),
        open_orders=[],
        suppliers=[
            SupplierProductInput(
                supplier_id=1,
                supplier_name="MOQ Supplier",
                unit_price=Decimal("20.00"),
                lead_time_days=3,
                minimum_order_quantity=200,  # MOQ > 150 shortage
            )
        ],
        budget=BudgetInput(
            total_budget=Decimal("10000.00"),
            committed_amount=Decimal("0.00"),
        ),
    )

    result = evaluate_purchasing_decision(engine_input)
    assert result.decision == "MODIFY"
    assert result.suggested_quantity == 200
    assert result.preferred_option.excess_quantity == 50


def test_scenario_6_alternative_exceeds_available_budget():
    """Scenario 6: Supplier cost exceeds remaining budget -> Flags budget warning."""
    start = date(2026, 11, 1)
    engine_input = EngineInput(
        evaluation_date=start,
        recommendation=RecommendationToEvaluate(
            id=6,
            product_id=101,
            recommended_quantity=500,
            supplier_id=1,
            requested_delivery_date=start + timedelta(days=5),
        ),
        inventory=InventoryInput(available_quantity=100, storage_capacity=2000),
        forecast=DemandForecastInput(
            forecast_quantity=600,
            period_start=start,
            period_end=start + timedelta(days=10),
        ),
        open_orders=[],
        suppliers=[
            SupplierProductInput(
                supplier_id=1,
                supplier_name="Expensive Vendor",
                unit_price=Decimal("100.00"),  # 500 * 100 = 50,000
                lead_time_days=3,
                minimum_order_quantity=100,
            )
        ],
        budget=BudgetInput(
            total_budget=Decimal("20000.00"),
            committed_amount=Decimal("15000.00"),  # Only 5,000 remaining!
        ),
    )

    result = evaluate_purchasing_decision(engine_input)
    assert any("exceed remaining purchasing budget" in w for w in result.warnings)
    assert result.decision in ("REJECT", "INVESTIGATE")


def test_scenario_7_dynamic_storage_overflow():
    """Gap 2: Projected stock at arrival exceeds warehouse capacity -> option infeasible."""
    start = date(2026, 11, 1)
    engine_input = EngineInput(
        evaluation_date=start,
        recommendation=RecommendationToEvaluate(
            id=7,
            product_id=101,
            recommended_quantity=300,
            supplier_id=1,
            requested_delivery_date=start + timedelta(days=4),
        ),
        inventory=InventoryInput(available_quantity=350, storage_capacity=500),
        forecast=DemandForecastInput(
            forecast_quantity=800,
            period_start=start,
            period_end=start + timedelta(days=10),  # 80 units/day
        ),
        # An incoming PO of 200 arrives on Day 2
        open_orders=[
            OpenPurchaseOrderInput(
                id=201,
                supplier_id=1,
                quantity=200,
                unit_price=Decimal("10.00"),
                expected_delivery_date=start + timedelta(days=2),
            )
        ],
        # Lead time is 3 days. On Day 3: on-hand was 350 - 90 + 200 = 460. New order 300 -> 760 > 500!
        suppliers=[
            SupplierProductInput(
                supplier_id=1,
                supplier_name="Bulk Vendor",
                unit_price=Decimal("10.00"),
                lead_time_days=3,
                minimum_order_quantity=300,
            )
        ],
        budget=BudgetInput(
            total_budget=Decimal("20000.00"),
            committed_amount=Decimal("0.00"),
        ),
    )

    result = evaluate_purchasing_decision(engine_input)
    assert len(result.feasible_options) == 1
    assert result.feasible_options[0].is_storage_feasible is False
    assert any("exceeds warehouse storage capacity" in t for t in result.feasible_options[0].trade_offs)


def test_scenario_8_recommendation_accepted_directly():
    """Scenario 8: Recommendation matches preferred supplier, lead time, MOQ, budget -> ACCEPT."""
    start = date(2026, 11, 1)
    engine_input = EngineInput(
        evaluation_date=start,
        recommendation=RecommendationToEvaluate(
            id=8,
            product_id=101,
            recommended_quantity=200,
            supplier_id=10,
            requested_delivery_date=start + timedelta(days=5),
        ),
        inventory=InventoryInput(available_quantity=100, storage_capacity=1000),
        forecast=DemandForecastInput(
            forecast_quantity=300,
            period_start=start,
            period_end=start + timedelta(days=10),
        ),
        open_orders=[],
        suppliers=[
            SupplierProductInput(
                supplier_id=10,
                supplier_name="Perfect Match Vendor",
                unit_price=Decimal("15.00"),
                lead_time_days=3,  # Arrives Day 3 <= Day 5
                minimum_order_quantity=200,  # Matches 200
            )
        ],
        budget=BudgetInput(
            total_budget=Decimal("20000.00"),
            committed_amount=Decimal("0.00"),
        ),
    )

    result = evaluate_purchasing_decision(engine_input)
    assert result.decision == "ACCEPT"
    assert result.suggested_quantity == 200
    assert result.suggested_supplier_id == 10
    assert any("fully justified" in r for r in result.reasoning_points)
