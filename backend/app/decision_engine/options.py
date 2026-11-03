from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app.decision_engine.suppliers import (
    calculate_projected_stock_at_arrival,
    evaluate_supplier_product,
)
from app.decision_engine.types import (
    InvestigationOption,
    NegotiationLever,
    OpenPurchaseOrderInput,
    PurchasingOption,
    SplitOrderAllocation,
    StockoutTimelineAnalysis,
    SupplierProductInput,
)


def generate_purchasing_options(
    suppliers: List[SupplierProductInput],
    net_shortage: int,
    remaining_budget: Decimal,
    storage_capacity: int,
    on_hand: int,
    daily_demand: float,
    open_orders: List[OpenPurchaseOrderInput],
    evaluation_date: date,
    target_delivery_date: date,
    shelf_life_days: Optional[int] = None,
    unit_volume_m3: float = 1.0,
    facility_available_m3: Optional[float] = None,
) -> List[PurchasingOption]:
    """Generates and evaluates purchasing options for all catalog suppliers,
    including single-supplier options and multi-vendor split-order options (Rule 3).
    """
    options: List[PurchasingOption] = []
    
    # 1. Single-supplier options
    for s in suppliers:
        opt = evaluate_supplier_product(
            supplier_prod=s,
            net_shortage=net_shortage,
            remaining_budget=remaining_budget,
            storage_capacity=storage_capacity,
            on_hand=on_hand,
            daily_demand=daily_demand,
            open_orders=open_orders,
            evaluation_date=evaluation_date,
            target_delivery_date=target_delivery_date,
            shelf_life_days=shelf_life_days,
            unit_volume_m3=unit_volume_m3,
            facility_available_m3=facility_available_m3,
        )
        options.append(opt)

    # 2. Multi-vendor split sourcing options (Rule 3 / Scenario 2)
    # Triggered when a supplier has limited capacity that cannot cover the entire net shortage
    if net_shortage > 0 and len(suppliers) >= 2:
        for s1 in suppliers:
            if s1.available_capacity is not None and 0 < s1.available_capacity < net_shortage:
                needed_rem = net_shortage - s1.available_capacity
                for s2 in suppliers:
                    if s2.supplier_id == s1.supplier_id:
                        continue
                    qty_2 = max(needed_rem, s2.minimum_order_quantity)
                    if s2.available_capacity is not None and qty_2 > s2.available_capacity:
                        continue  # Secondary supplier cannot fulfill remainder

                    price_1 = float(s1.unit_price)
                    price_2 = float(s2.unit_price)
                    cost_1 = round(s1.available_capacity * price_1, 2)
                    cost_2 = round(qty_2 * price_2, 2)
                    split_total_cost = round(cost_1 + cost_2, 2)

                    lead_1 = s1.lead_time_days + max(0, s1.historical_delay_days)
                    lead_2 = s2.lead_time_days + max(0, s2.historical_delay_days)
                    arrival_1 = evaluation_date + timedelta(days=lead_1)
                    arrival_2 = evaluation_date + timedelta(days=lead_2)
                    split_arrival = max(arrival_1, arrival_2)
                    split_lead = max(lead_1, lead_2)

                    is_timing = arrival_1 <= target_delivery_date and arrival_2 <= target_delivery_date
                    is_budget = split_total_cost <= float(remaining_budget)
                    total_split_qty = s1.available_capacity + qty_2
                    excess_split = max(0, total_split_qty - net_shortage)

                    projected_stock = calculate_projected_stock_at_arrival(
                        on_hand=on_hand,
                        daily_demand=daily_demand,
                        open_orders=open_orders,
                        proposed_quantity=total_split_qty,
                        arrival_date=split_arrival,
                        evaluation_date=evaluation_date,
                    )
                    is_storage = projected_stock <= storage_capacity
                    if facility_available_m3 is not None and facility_available_m3 > 0:
                        if (total_split_qty * unit_volume_m3) > facility_available_m3:
                            is_storage = False

                    allocation = SplitOrderAllocation(
                        primary_supplier_id=s1.supplier_id,
                        primary_supplier_name=s1.supplier_name,
                        primary_quantity=s1.available_capacity,
                        primary_unit_price=price_1,
                        primary_cost=cost_1,
                        secondary_supplier_id=s2.supplier_id,
                        secondary_supplier_name=s2.supplier_name,
                        secondary_quantity=qty_2,
                        secondary_unit_price=price_2,
                        secondary_cost=cost_2,
                        total_cost=split_total_cost,
                    )

                    split_trade_offs = [
                        f"Split sourcing order: {s1.supplier_name} capacity is {s1.available_capacity} units. "
                        f"Remainder ({needed_rem} units) allocated to {s2.supplier_name} ({qty_2} units)."
                    ]
                    if excess_split > 0:
                        split_trade_offs.append(
                            f"Secondary supplier MOQ creates {excess_split} excess units ({total_split_qty} total)."
                        )
                    if not is_budget:
                        split_trade_offs.append(
                            f"Split order total cost (${split_total_cost:,.2f}) exceeds remaining budget (${float(remaining_budget):,.2f})."
                        )
                    if not is_timing:
                        split_trade_offs.append(
                            f"Split order completion date ({split_arrival}) misses target deadline ({target_delivery_date})."
                        )
                    if not is_storage:
                        split_trade_offs.append(
                            f"Projected stock at arrival ({projected_stock} units) exceeds storage capacity ({storage_capacity} units)."
                        )

                    options.append(
                        PurchasingOption(
                            supplier_id=s1.supplier_id,
                            supplier_name=f"{s1.supplier_name} & {s2.supplier_name} (Split Sourcing)",
                            quantity=total_split_qty,
                            unit_price=round(split_total_cost / max(1, total_split_qty), 2),
                            total_cost=split_total_cost,
                            lead_time_days=split_lead,
                            estimated_delivery_date=split_arrival,
                            excess_quantity=excess_split,
                            projected_stock_at_arrival=projected_stock,
                            is_timing_feasible=is_timing,
                            is_budget_feasible=is_budget,
                            is_storage_feasible=is_storage,
                            trade_offs=split_trade_offs,
                            is_split_sourcing=True,
                            split_allocation=allocation,
                            effective_lead_time_days=split_lead,
                        )
                    )

    return options


def generate_investigation_pathways(
    timeline: StockoutTimelineAnalysis,
    open_orders: List[OpenPurchaseOrderInput],
    suppliers: List[SupplierProductInput],
    evaluation_date: date,
    target_date: date,
    negotiation_levers: Optional[List[NegotiationLever]] = None,
) -> List[InvestigationOption]:
    """Generates negotiation and expediting investigation pathways for human buyer review."""
    pathways: List[InvestigationOption] = []
    stockout_ref = timeline.stockout_date or target_date

    # 1. Existing Supplier Expedite / Partial Delivery
    for po in open_orders:
        if po.status.upper() in ("OPEN", "PENDING", "IN_TRANSIT"):
            if po.expected_delivery_date > stockout_ref:
                needed_units = (
                    timeline.interim_shortage_quantity
                    if timeline.has_interim_stockout and timeline.interim_shortage_quantity > 0
                    else min(po.quantity, max(1, timeline.additional_purchasing_requirement))
                )
                supp_name = po.supplier_name or f"Supplier #{po.supplier_id}"
                days_late = (po.expected_delivery_date - stockout_ref).days

                pathways.append(
                    InvestigationOption(
                        pathway_type="EXISTING_SUPPLIER_EXPEDITE",
                        description=(
                            f"Investigate expediting or partial delivery of {needed_units} units "
                            f"from open PO #{po.id} with {supp_name}. Scheduled arrival is "
                            f"{po.expected_delivery_date} ({days_late} days after estimated stockout on {stockout_ref})."
                        ),
                        target_supplier_id=po.supplier_id,
                        target_supplier_name=supp_name,
                        required_delivery_date=stockout_ref,
                        potential_quantity=needed_units,
                        action_required_by_buyer=(
                            f"Contact {supp_name} to negotiate early shipment or partial batch delivery "
                            f"before {stockout_ref} to prevent stockout."
                        ),
                        is_confirmed=False,
                    )
                )

    # 2. Alternative Supplier Fast Emergency Delivery
    for s in suppliers:
        effective_lead = s.lead_time_days + max(0, s.historical_delay_days)
        arrival = evaluation_date + timedelta(days=effective_lead)
        if arrival <= stockout_ref:
            pathways.append(
                InvestigationOption(
                    pathway_type="ALTERNATIVE_SUPPLIER_EMERGENCY",
                    description=(
                        f"Investigate emergency bridge order with alternative supplier {s.supplier_name}. "
                        f"Lead time is {effective_lead} days (estimated arrival {arrival} <= stockout {stockout_ref})."
                    ),
                    target_supplier_id=s.supplier_id,
                    target_supplier_name=s.supplier_name,
                    required_delivery_date=stockout_ref,
                    potential_quantity=s.minimum_order_quantity,
                    action_required_by_buyer=(
                        f"Confirm spot availability and lead time of {effective_lead} days with {s.supplier_name}."
                    ),
                    is_confirmed=False,
                )
            )

    # 3. Specific Quantified Negotiation Levers
    if negotiation_levers:
        pathway_map: Dict[str, str] = {
            "LEAD_TIME_EXPEDITE": "EXISTING_SUPPLIER_EXPEDITE",
            "MOQ_REDUCTION": "MOQ_REDUCTION_REQUEST",
            "PRICE_BENCHMARK_COUNTER_OFFER": "PRICE_BENCHMARK_COUNTER_OFFER",
            "PARTIAL_BATCH_DELIVERY": "PARTIAL_BATCH_DELIVERY",
        }
        for lever in negotiation_levers:
            ptype = pathway_map.get(lever.lever_type, "EXISTING_SUPPLIER_EXPEDITE")
            pathways.append(
                InvestigationOption(
                    pathway_type=ptype,  # type: ignore[arg-type]
                    description=lever.recommended_talking_point,
                    target_supplier_id=lever.target_supplier_id,
                    target_supplier_name=lever.target_supplier_name,
                    required_delivery_date=stockout_ref,
                    potential_quantity=timeline.additional_purchasing_requirement or 1,
                    action_required_by_buyer=lever.recommended_talking_point,
                    is_confirmed=False,
                    negotiation_lever=lever,
                )
            )

    return pathways


def generate_negotiation_levers(
    suppliers: List[SupplierProductInput],
    timeline: StockoutTimelineAnalysis,
    net_shortage: int,
    evaluation_date: date,
    target_delivery_date: date,
    incumbent_supplier_id: Optional[int] = None,
) -> List[NegotiationLever]:
    """Computes actionable, mathematically quantified negotiation levers with exact numerical targets."""
    levers: List[NegotiationLever] = []
    stockout_ref = timeline.stockout_date or target_delivery_date

    # 1. Lead Time Expediting Lever
    for s in suppliers:
        effective_lead = s.lead_time_days + max(0, s.historical_delay_days)
        arrival = evaluation_date + timedelta(days=effective_lead)
        if arrival > stockout_ref:
            days_to_stockout = (stockout_ref - evaluation_date).days
            required_lead = max(1, days_to_stockout)
            if effective_lead > required_lead:
                talking_point = (
                    f"Negotiate rush/expedited lead time from {effective_lead} days to <= {required_lead} days "
                    f"(target delivery: {stockout_ref.isoformat()}) to avert stockout."
                )
                if s.expedited_lead_time_days is not None and s.expedited_lead_time_days <= required_lead:
                    talking_point += f" (Vendor profile specifies expedited capability of {s.expedited_lead_time_days} days)."
                levers.append(
                    NegotiationLever(
                        lever_type="LEAD_TIME_EXPEDITE",
                        title=f"Expedite Lead Time with {s.supplier_name}",
                        target_supplier_id=s.supplier_id,
                        target_supplier_name=s.supplier_name,
                        current_value=f"{effective_lead} days",
                        target_value=f"<= {required_lead} days",
                        potential_savings=None,
                        recommended_talking_point=talking_point,
                    )
                )

    # 2. MOQ Reduction / Waiver Lever
    if net_shortage > 0:
        for s in suppliers:
            if s.minimum_order_quantity > net_shortage:
                excess_units = s.minimum_order_quantity - net_shortage
                excess_capital = round(excess_units * float(s.unit_price), 2)
                talking_point = (
                    f"Request supplier MOQ waiver or temporary reduction from {s.minimum_order_quantity} to {net_shortage} units "
                    f"to eliminate ${excess_capital:,.2f} in excess holding stock."
                )
                if getattr(s, "is_moq_negotiable", True):
                    talking_point += " (Vendor profile indicates flexibility on minimum order quantities)."
                levers.append(
                    NegotiationLever(
                        lever_type="MOQ_REDUCTION",
                        title=f"Negotiate MOQ Reduction with {s.supplier_name}",
                        target_supplier_id=s.supplier_id,
                        target_supplier_name=s.supplier_name,
                        current_value=f"{s.minimum_order_quantity} units",
                        target_value=f"{net_shortage} units",
                        potential_savings=excess_capital,
                        recommended_talking_point=talking_point,
                    )
                )

    # 3. Price Benchmark Counter-Offer Lever
    if len(suppliers) >= 2:
        cheapest_s = min(suppliers, key=lambda x: float(x.unit_price))
        min_price = float(cheapest_s.unit_price)
        for s in suppliers:
            s_price = float(s.unit_price)
            if s_price > min_price:
                price_diff = round(s_price - min_price, 2)
                order_qty = net_shortage if net_shortage > 0 else s.minimum_order_quantity
                savings = round(price_diff * order_qty, 2)
                talking_point = (
                    f"Counter-offer incumbent supplier {s.supplier_name} at ${min_price:.2f}/unit "
                    f"(matching {cheapest_s.supplier_name} quote) for an immediate contract savings of ${savings:,.2f}."
                )
                levers.append(
                    NegotiationLever(
                        lever_type="PRICE_BENCHMARK_COUNTER_OFFER",
                        title=f"Price Benchmark Counter-Offer to {s.supplier_name}",
                        target_supplier_id=s.supplier_id,
                        target_supplier_name=s.supplier_name,
                        current_value=f"${s_price:.2f}/unit",
                        target_value=f"${min_price:.2f}/unit",
                        potential_savings=savings,
                        recommended_talking_point=talking_point,
                    )
                )

    # 4. Partial Batch Delivery Lever
    if net_shortage > 1 and timeline.stockout_date:
        for s in suppliers:
            effective_lead = s.lead_time_days + max(0, s.historical_delay_days)
            arrival = evaluation_date + timedelta(days=effective_lead)
            if arrival > timeline.stockout_date:
                gap_days = (arrival - timeline.stockout_date).days
                bridge_units = max(1, round(timeline.daily_demand * gap_days)) if timeline.daily_demand > 0 else 1
                critical_units = min(net_shortage - 1, max(1, bridge_units))
                balance_units = net_shortage - critical_units
                if 0 < critical_units < net_shortage:
                    talking_point = (
                        f"Negotiate split delivery: request priority air-shipment of {critical_units} critical units "
                        f"by {timeline.stockout_date.isoformat()} and balance of {balance_units} units via standard ground transit."
                    )
                    levers.append(
                        NegotiationLever(
                            lever_type="PARTIAL_BATCH_DELIVERY",
                            title=f"Partial Split Batch Delivery with {s.supplier_name}",
                            target_supplier_id=s.supplier_id,
                            target_supplier_name=s.supplier_name,
                            current_value=f"{net_shortage} units single standard batch",
                            target_value=f"{critical_units} urgent + {balance_units} standard",
                            potential_savings=None,
                            recommended_talking_point=talking_point,
                        )
                    )

    return levers


def rank_preferred_option(
    feasible_options: List[PurchasingOption],
    target_delivery_date: date,
    stockout_date: Optional[date] = None,
    ranking_weights: Optional[Dict[str, float]] = None,
) -> Tuple[Optional[PurchasingOption], List[str]]:
    """Ranks and selects the optimal purchasing option.
    
    Supports both standard multi-criteria ranking and dynamic utility scoring (FM-9).
    Prioritization criteria:
    1. Feasible timing (arrival_date <= target_delivery_date).
    2. Prevention of stockout (arrival_date <= stockout_date if stockout is imminent).
    3. Feasible budget and storage.
    4. Lowest total order cost / composite utility score.
    5. Minimal excess inventory above net requirement.
    """
    if not feasible_options:
        return None, ["No supplier options available."]

    # Valid candidates must satisfy hard constraints: budget, storage, and supplier fulfillment capacity
    valid_candidates = [
        o for o in feasible_options
        if o.is_budget_feasible and o.is_storage_feasible and getattr(o, "is_capacity_feasible", True)
    ]
    if not valid_candidates:
        return None, ["No supplier options satisfy hard budget and storage constraints."]

    # Separate candidates that arrive in time vs those that are late
    on_time_candidates = [o for o in valid_candidates if o.is_timing_feasible]

    reasons: List[str] = []
    if on_time_candidates:
        # If stockout_date is provided and any on-time candidate arrives before stockout, prioritize them
        if stockout_date:
            before_stockout = [
                o for o in on_time_candidates if o.estimated_delivery_date <= stockout_date
            ]
            if before_stockout:
                on_time_candidates = before_stockout

        # Multi-Criteria Scoring (FM-9): If weights are provided, compute composite utility score
        if ranking_weights:
            w_speed = ranking_weights.get("speed", 0.4)
            w_cost = ranking_weights.get("cost", 0.4)
            w_moq = ranking_weights.get("moq_waste", 0.2)

            min_cost = min(o.total_cost for o in on_time_candidates) or 1.0
            min_lead = min(o.lead_time_days for o in on_time_candidates) or 1.0

            scored = []
            for o in on_time_candidates:
                cost_score = min_cost / max(1.0, o.total_cost)
                speed_score = min_lead / max(1.0, float(o.lead_time_days))
                excess_penalty = o.excess_quantity / max(1.0, float(o.quantity))
                composite = (w_speed * speed_score) + (w_cost * cost_score) - (w_moq * excess_penalty)
                scored.append((composite, o))

            scored.sort(key=lambda item: item[0], reverse=True)
            preferred = scored[0][1]
            reasons.append(
                f"Selected {preferred.supplier_name} using multi-criteria policy weights (speed: {w_speed}, cost: {w_cost}): "
                f"delivers on {preferred.estimated_delivery_date} at total cost ${preferred.total_cost:,.2f}."
            )
        else:
            # Standard ranking: lowest total cost, then minimal excess quantity, then lead time
            sorted_candidates = sorted(
                on_time_candidates,
                key=lambda o: (o.total_cost, o.excess_quantity, o.lead_time_days),
            )
            preferred = sorted_candidates[0]
            reasons.append(
                f"Selected {preferred.supplier_name} as preferred: delivers on {preferred.estimated_delivery_date} "
                f"before target deadline {target_delivery_date} at lowest cost (${preferred.total_cost:,.2f})."
            )

        if preferred.is_split_sourcing and preferred.split_allocation:
            alloc = preferred.split_allocation
            reasons.append(
                f"Split order allocation: {alloc.primary_quantity} units with {alloc.primary_supplier_name} (${alloc.primary_cost:,.2f}) + "
                f"{alloc.secondary_quantity} units with {alloc.secondary_supplier_name} (${alloc.secondary_cost:,.2f})."
            )
        elif preferred.excess_quantity > 0:
            reasons.append(
                f"Includes {preferred.excess_quantity} excess units to satisfy supplier MOQ ({preferred.quantity} total)."
            )
        return preferred, reasons
    else:
        # All candidates miss target delivery date.
        # Pick the fastest candidate among those that satisfy budget and storage
        sorted_by_speed = sorted(
            valid_candidates,
            key=lambda o: (o.lead_time_days, o.total_cost),
        )
        fastest = sorted_by_speed[0]
        reasons.append(
            f"No supplier can meet target deadline {target_delivery_date}. "
            f"{fastest.supplier_name} is the earliest available (arriving {fastest.estimated_delivery_date})."
        )
        return fastest, reasons
