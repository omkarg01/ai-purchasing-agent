from typing import Any, Dict, List, Optional
from app.decision_engine.inventory import (
    analyze_chronological_stockout_timeline,
)
from app.decision_engine.options import (
    generate_investigation_pathways,
    generate_purchasing_options,
    rank_preferred_option,
)
from app.decision_engine.types import (
    DecisionResult,
    EngineInput,
)


def evaluate_purchasing_decision(input_data: EngineInput) -> DecisionResult:
    """Evaluates a purchasing recommendation using deterministic business rules.
    
    Responsibilities:
    - Chronological date-aware inventory & stockout analysis with safety stock buffer (Rule 1).
    - Discrete daily demand time-series simulation when provided (FM-4).
    - Multi-vendor split-sourcing order allocation (Rule 3 / Scenario 2).
    - Facility-wide aggregate storage constraint validation (Rule 4).
    - Supplier OTIF historical lead-time delay variance buffer (Rule 5).
    - Volume price break discount tier optimization (Rule 6).
    - Shelf-life spoilage guard against high MOQs (Rule 2).
    - Multi-criteria policy weighting utility scoring (FM-9).
    """
    rec = input_data.recommendation
    eval_date = input_data.evaluation_date

    # 1. Chronological Date-Aware Stockout Analysis (with Rule 1 Safety Stock)
    timeline = analyze_chronological_stockout_timeline(
        on_hand=input_data.inventory.available_quantity,
        forecast=input_data.forecast,
        open_orders=input_data.open_orders,
        evaluation_date=eval_date,
        safety_stock_quantity=input_data.inventory.safety_stock_quantity,
    )

    # Compile quantitative calculation evidence
    calculations: Dict[str, Any] = {
        "daily_burn_rate": round(timeline.daily_demand, 2),
        "days_of_initial_coverage": round(timeline.days_of_initial_coverage, 2),
        "stockout_date": timeline.stockout_date.isoformat() if timeline.stockout_date else None,
        "has_interim_stockout": timeline.has_interim_stockout,
        "interim_stockout_days": timeline.interim_stockout_days,
        "interim_shortage_quantity": timeline.interim_shortage_quantity,
        "final_projected_inventory": timeline.final_projected_inventory,
        "final_unmet_demand": timeline.final_unmet_demand,
        "additional_purchasing_requirement": timeline.additional_purchasing_requirement,
        "safety_stock_quantity": timeline.safety_stock_quantity,
        "target_ending_inventory": timeline.target_ending_inventory,
        "remaining_budget": float(input_data.budget.remaining_budget),
        "storage_capacity": input_data.inventory.storage_capacity,
    }

    risks: List[str] = []
    warnings: List[str] = []
    reasoning_points: List[str] = []

    if timeline.safety_stock_quantity > 0:
        reasoning_points.append(
            f"Gross demand requirement includes {timeline.safety_stock_quantity} units of safety stock buffer."
        )

    # 2. Case: Zero Net Shortage and No Interim Stockout
    if timeline.final_unmet_demand == 0 and not timeline.has_interim_stockout:
        reasoning_points.append(
            f"Existing on-hand stock ({input_data.inventory.available_quantity} units) and scheduled "
            f"incoming orders fully satisfy forecast demand ({input_data.forecast.forecast_quantity} units) "
            f"without any stockout gap."
        )
        reasoning_points.append(
            f"Recommended purchase of {rec.recommended_quantity} units is unnecessary and would cause "
            f"excess holding costs."
        )
        return DecisionResult(
            decision="REJECT",
            suggested_quantity=0,
            suggested_supplier_id=None,
            preferred_option=None,
            feasible_options=[],
            investigation_options=[],
            calculations=calculations,
            risks=[],
            warnings=["Unnecessary purchase: current inventory and open POs cover demand."],
            reasoning_points=reasoning_points,
        )

    # 3. Target deadline for replenishment
    target_date = rec.requested_delivery_date
    if timeline.stockout_date and timeline.stockout_date < target_date:
        risks.append(
            f"Estimated stockout date ({timeline.stockout_date}) is earlier than requested delivery date "
            f"({rec.requested_delivery_date}). Prioritizing suppliers who can deliver before stockout."
        )

    # 4. Generate purchasing options and investigation pathways
    net_requirement = max(1, timeline.additional_purchasing_requirement)
    feasible_options = generate_purchasing_options(
        suppliers=input_data.suppliers,
        net_shortage=net_requirement,
        remaining_budget=input_data.budget.remaining_budget,
        storage_capacity=input_data.inventory.storage_capacity,
        on_hand=input_data.inventory.available_quantity,
        daily_demand=timeline.daily_demand,
        open_orders=input_data.open_orders,
        evaluation_date=eval_date,
        target_delivery_date=target_date,
        shelf_life_days=input_data.shelf_life_days,
        unit_volume_m3=input_data.unit_volume_m3,
        facility_available_m3=input_data.inventory.facility_available_m3,
    )

    investigation_options = generate_investigation_pathways(
        timeline=timeline,
        open_orders=input_data.open_orders,
        suppliers=input_data.suppliers,
        evaluation_date=eval_date,
        target_date=timeline.stockout_date or target_date,
    )

    preferred_option, ranking_reasons = rank_preferred_option(
        feasible_options=feasible_options,
        target_delivery_date=target_date,
        stockout_date=timeline.stockout_date,
        ranking_weights=input_data.ranking_weights,
    )

    # 5. Decision Determination Logic
    has_open_pos = any(
        po.status.upper() in ("OPEN", "PENDING", "IN_TRANSIT") for po in input_data.open_orders
    )
    can_prevent_stockout = True
    if timeline.has_interim_stockout and has_open_pos and timeline.stockout_date and preferred_option:
        can_prevent_stockout = preferred_option.estimated_delivery_date <= timeline.stockout_date

    if (
        preferred_option
        and preferred_option.is_timing_feasible
        and preferred_option.is_budget_feasible
        and preferred_option.is_storage_feasible
        and can_prevent_stockout
    ):
        reasoning_points.extend(ranking_reasons)

        if timeline.has_interim_stockout:
            risks.append(
                f"Interim stockout of {timeline.interim_shortage_quantity} units was projected across "
                f"{timeline.interim_stockout_days} day(s), but {preferred_option.supplier_name} "
                f"arrives on {preferred_option.estimated_delivery_date} before stockout occurs."
            )

        if preferred_option.is_split_sourcing and preferred_option.split_allocation:
            alloc = preferred_option.split_allocation
            calculations["is_split_sourcing"] = True
            calculations["split_allocation"] = {
                "primary_supplier_id": alloc.primary_supplier_id,
                "primary_supplier_name": alloc.primary_supplier_name,
                "primary_quantity": alloc.primary_quantity,
                "primary_cost": alloc.primary_cost,
                "secondary_supplier_id": alloc.secondary_supplier_id,
                "secondary_supplier_name": alloc.secondary_supplier_name,
                "secondary_quantity": alloc.secondary_quantity,
                "secondary_cost": alloc.secondary_cost,
                "total_cost": alloc.total_cost,
            }
            decision = "MODIFY"
            reasoning_points.append(
                f"Split sourcing order: {alloc.primary_quantity} units with {alloc.primary_supplier_name} "
                f"and {alloc.secondary_quantity} units with {alloc.secondary_supplier_name} to fulfill "
                f"total requirement of {preferred_option.quantity} units within supplier capacity limits."
            )
        else:
            # Compare preferred option with original recommendation
            matches_qty = rec.recommended_quantity == preferred_option.quantity
            matches_supplier = rec.supplier_id == preferred_option.supplier_id

            if matches_qty and matches_supplier:
                decision = "ACCEPT"
                reasoning_points.append(
                    f"Recommendation to purchase {rec.recommended_quantity} units from {preferred_option.supplier_name} "
                    f"is fully justified, feasible within budget, and arrives on time."
                )
            else:
                decision = "MODIFY"
                reasoning_points.append(
                    f"Modifying recommendation to {preferred_option.quantity} units from {preferred_option.supplier_name} "
                    f"to optimize delivery timing, meet supplier MOQ, and prevent stockout."
                )

        return DecisionResult(
            decision=decision,
            suggested_quantity=preferred_option.quantity,
            suggested_supplier_id=preferred_option.supplier_id,
            preferred_option=preferred_option,
            feasible_options=feasible_options,
            investigation_options=investigation_options,
            calculations=calculations,
            risks=risks,
            warnings=warnings,
            reasoning_points=reasoning_points,
        )

    # 6. Fallback when no supplier can arrive in time or within budget
    all_over_budget = feasible_options and all(not o.is_budget_feasible for o in feasible_options)
    all_too_late = feasible_options and all(not o.is_timing_feasible for o in feasible_options)

    if all_over_budget:
        warnings.append(
            f"All supplier options exceed remaining purchasing budget (${float(input_data.budget.remaining_budget):,.2f})."
        )
        if timeline.has_interim_stockout:
            risks.append("Stockout is imminent and budget is insufficient for new procurement.")
            decision = "INVESTIGATE"
            reasoning_points.append(
                "Insufficient budget for new purchase order. Human buyer must investigate budget escalation "
                "or negotiate split payment terms."
            )
        else:
            decision = "REJECT"
            reasoning_points.append(
                "Recommendation rejected due to hard purchasing budget constraint."
            )

        return DecisionResult(
            decision=decision,
            suggested_quantity=preferred_option.quantity if preferred_option else None,
            suggested_supplier_id=preferred_option.supplier_id if preferred_option else None,
            preferred_option=preferred_option,
            feasible_options=feasible_options,
            investigation_options=investigation_options,
            calculations=calculations,
            risks=risks,
            warnings=warnings,
            reasoning_points=reasoning_points,
        )

    # If supplier lead times miss stockout date, investigate expediting existing open PO
    if all_too_late or timeline.has_interim_stockout:
        risks.append(
            f"Standard supplier lead times cannot deliver replenishment before stockout date ({target_date})."
        )
        decision = "INVESTIGATE"
        reasoning_points.append(
            "Standard lead times cannot prevent stockout. Buyer must investigate expediting an open order "
            "or negotiating emergency rush delivery with suppliers."
        )

        return DecisionResult(
            decision=decision,
            suggested_quantity=preferred_option.quantity if preferred_option else None,
            suggested_supplier_id=preferred_option.supplier_id if preferred_option else None,
            preferred_option=preferred_option,
            feasible_options=feasible_options,
            investigation_options=investigation_options,
            calculations=calculations,
            risks=risks,
            warnings=warnings,
            reasoning_points=reasoning_points,
        )

    # General fallback
    decision = "MODIFY" if preferred_option else "INVESTIGATE"
    return DecisionResult(
        decision=decision,
        suggested_quantity=preferred_option.quantity if preferred_option else None,
        suggested_supplier_id=preferred_option.supplier_id if preferred_option else None,
        preferred_option=preferred_option,
        feasible_options=feasible_options,
        investigation_options=investigation_options,
        calculations=calculations,
        risks=risks,
        warnings=warnings,
        reasoning_points=reasoning_points,
    )
