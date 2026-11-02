from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from app.decision_engine.suppliers import evaluate_supplier_product
from app.decision_engine.types import (
    InvestigationOption,
    OpenPurchaseOrderInput,
    PurchasingOption,
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
) -> List[PurchasingOption]:
    """Generates and evaluates purchasing options for all catalog suppliers."""
    options: List[PurchasingOption] = []
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
        )
        options.append(opt)
    return options


def generate_investigation_pathways(
    timeline: StockoutTimelineAnalysis,
    open_orders: List[OpenPurchaseOrderInput],
    suppliers: List[SupplierProductInput],
    evaluation_date: date,
    target_date: date,
) -> List[InvestigationOption]:
    """Generates negotiation and expediting investigation pathways for human buyer review.
    
    All pathways are unconfirmed (is_confirmed=False) because supplier negotiations
    must be conducted and confirmed by the human buyer.
    """
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
    # Only if alternate supplier lead time can meet the required stockout date
    for s in suppliers:
        est_arrival = evaluation_date + (s.lead_time_days * date.resolution)
        # s.lead_time_days arrival
        from datetime import timedelta
        arrival = evaluation_date + timedelta(days=s.lead_time_days)
        if arrival <= stockout_ref:
            pathways.append(
                InvestigationOption(
                    pathway_type="ALTERNATIVE_SUPPLIER_EMERGENCY",
                    description=(
                        f"Investigate emergency bridge order with alternative supplier {s.supplier_name}. "
                        f"Lead time is {s.lead_time_days} days (estimated arrival {arrival} <= stockout {stockout_ref})."
                    ),
                    target_supplier_id=s.supplier_id,
                    target_supplier_name=s.supplier_name,
                    required_delivery_date=stockout_ref,
                    potential_quantity=s.minimum_order_quantity,
                    action_required_by_buyer=(
                        f"Confirm spot availability and lead time of {s.lead_time_days} days with {s.supplier_name}."
                    ),
                    is_confirmed=False,
                )
            )

    return pathways


def rank_preferred_option(
    feasible_options: List[PurchasingOption],
    target_delivery_date: date,
    stockout_date: Optional[date] = None,
) -> Tuple[Optional[PurchasingOption], List[str]]:
    """Ranks and selects the optimal purchasing option.
    
    Prioritization criteria:
    1. Feasible timing (arrival_date <= target_delivery_date).
    2. Prevention of stockout (arrival_date <= stockout_date if stockout is imminent).
    3. Feasible budget and storage.
    4. Lowest total order cost.
    5. Minimal excess inventory above net requirement.
    """
    if not feasible_options:
        return None, ["No supplier options available."]

    # Valid candidates must satisfy hard constraints: budget and storage
    valid_candidates = [
        o for o in feasible_options if o.is_budget_feasible and o.is_storage_feasible
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

        # Sort on-time candidates by lowest total cost, then minimal excess quantity
        sorted_candidates = sorted(
            on_time_candidates,
            key=lambda o: (o.total_cost, o.excess_quantity, o.lead_time_days),
        )
        preferred = sorted_candidates[0]
        reasons.append(
            f"Selected {preferred.supplier_name} as preferred: delivers on {preferred.estimated_delivery_date} "
            f"before target deadline {target_delivery_date} at lowest cost (${preferred.total_cost:,.2f})."
        )
        if preferred.excess_quantity > 0:
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
