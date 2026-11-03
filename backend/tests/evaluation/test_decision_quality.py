import json
from datetime import date
from decimal import Decimal
from pathlib import Path
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


def load_scenarios():
    json_path = Path(__file__).parent / "scenarios.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["scenarios"]


SCENARIOS = load_scenarios()


def build_engine_input(raw_input: dict) -> EngineInput:
    rec_data = raw_input["recommendation"]
    inv_data = raw_input["inventory"]
    fc_data = raw_input["forecast"]
    budget_data = raw_input["budget"]

    rec = RecommendationToEvaluate(
        id=rec_data["id"],
        product_id=rec_data["product_id"],
        recommended_quantity=rec_data["recommended_quantity"],
        supplier_id=rec_data.get("supplier_id"),
        requested_delivery_date=date.fromisoformat(rec_data["requested_delivery_date"]),
        status=rec_data.get("status", "PENDING_APPROVAL"),
    )

    inv = InventoryInput(
        available_quantity=inv_data["available_quantity"],
        storage_capacity=inv_data["storage_capacity"],
    )

    fc = DemandForecastInput(
        forecast_quantity=fc_data["forecast_quantity"],
        period_start=date.fromisoformat(fc_data["period_start"]),
        period_end=date.fromisoformat(fc_data["period_end"]),
    )

    open_pos = [
        OpenPurchaseOrderInput(
            id=po["id"],
            supplier_id=po["supplier_id"],
            quantity=po["quantity"],
            unit_price=Decimal(str(po["unit_price"])),
            expected_delivery_date=date.fromisoformat(po["expected_delivery_date"]),
            status=po.get("status", "OPEN"),
            supplier_name=po.get("supplier_name"),
        )
        for po in raw_input.get("open_orders", [])
    ]

    suppliers = [
        SupplierProductInput(
            supplier_id=s["supplier_id"],
            supplier_name=s["supplier_name"],
            unit_price=Decimal(str(s["unit_price"])),
            lead_time_days=s["lead_time_days"],
            minimum_order_quantity=s["minimum_order_quantity"],
        )
        for s in raw_input.get("suppliers", [])
    ]

    budget = BudgetInput(
        total_budget=Decimal(str(budget_data["total_budget"])),
        committed_amount=Decimal(str(budget_data["committed_amount"])),
    )

    return EngineInput(
        evaluation_date=date.fromisoformat(raw_input["evaluation_date"]),
        recommendation=rec,
        inventory=inv,
        forecast=fc,
        open_orders=open_pos,
        suppliers=suppliers,
        budget=budget,
    )


@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s["scenario_id"] for s in SCENARIOS],
)
def test_deterministic_decision_quality(scenario):
    """Evaluates whether the deterministic engine produces the independently verified decision."""
    scenario_id = scenario["scenario_id"]
    scenario_name = scenario["scenario_name"]
    expected = scenario["expected"]

    engine_input = build_engine_input(scenario["input"])
    result = evaluate_purchasing_decision(engine_input)

    # 1. Decision correctness
    assert result.decision == expected["decision"], (
        f"[{scenario_id} - {scenario_name}] Decision mismatch: "
        f"expected {expected['decision']}, got {result.decision}. "
        f"Reasoning: {result.reasoning_points}"
    )

    # 2. Suggested quantity correctness (if specified)
    if "suggested_quantity" in expected and expected["suggested_quantity"] is not None:
        assert result.suggested_quantity == expected["suggested_quantity"], (
            f"[{scenario_id} - {scenario_name}] Suggested quantity mismatch: "
            f"expected {expected['suggested_quantity']}, got {result.suggested_quantity}."
        )

    # 3. Suggested supplier correctness (if specified)
    if "suggested_supplier_id" in expected and expected["suggested_supplier_id"] is not None:
        assert result.suggested_supplier_id == expected["suggested_supplier_id"], (
            f"[{scenario_id} - {scenario_name}] Suggested supplier mismatch: "
            f"expected {expected['suggested_supplier_id']}, got {result.suggested_supplier_id}."
        )

    # 4. Failure conditions verification
    for failure in expected.get("failure_conditions", []):
        if failure in ["ACCEPT", "MODIFY", "REJECT", "INVESTIGATE"]:
            assert result.decision != failure, (
                f"[{scenario_id}] Violated failure condition: decision should not be {failure}."
            )
        elif failure == "suggested_quantity > 0":
            assert not (result.suggested_quantity and result.suggested_quantity > 0), (
                f"[{scenario_id}] Violated failure condition: suggested_quantity must be 0."
            )
        elif failure == "suggested_quantity < 100":
            assert not (result.suggested_quantity and result.suggested_quantity < 100), (
                f"[{scenario_id}] Violated failure condition: suggested_quantity must satisfy MOQ >= 100."
            )

    # 5. Core quantitative calculation verification
    calc = result.calculations
    assert "daily_burn_rate" in calc
    assert "days_of_initial_coverage" in calc
    assert "final_unmet_demand" in calc
    assert len(result.reasoning_points) > 0, "Engine must produce non-empty reasoning points."

