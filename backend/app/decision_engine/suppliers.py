from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from app.decision_engine.types import (
    OpenPurchaseOrderInput,
    PriceTier,
    PurchasingOption,
    SupplierProductInput,
)


def calculate_projected_stock_at_arrival(
    on_hand: int,
    daily_demand: float,
    open_orders: List[OpenPurchaseOrderInput],
    proposed_quantity: int,
    arrival_date: date,
    evaluation_date: date,
) -> int:
    """Calculates projected inventory at the proposed order arrival date.
    
    Accounts for:
    - Ongoing consumption between evaluation_date and arrival_date.
    - Intervening open PO deliveries arriving on or before arrival_date.
    - The new proposed order quantity.
    """
    days_to_arrival = max(0, (arrival_date - evaluation_date).days)
    consumption_before_arrival = days_to_arrival * daily_demand

    remaining_on_hand_before_arrival = max(0.0, float(on_hand) - consumption_before_arrival)

    intervening_po_quantity = 0
    for po in open_orders:
        if po.status.upper() in ("OPEN", "PENDING", "IN_TRANSIT"):
            if evaluation_date <= po.expected_delivery_date <= arrival_date:
                intervening_po_quantity += po.quantity

    projected = remaining_on_hand_before_arrival + intervening_po_quantity + proposed_quantity
    return int(round(projected))


def evaluate_supplier_product(
    supplier_prod: SupplierProductInput,
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
) -> PurchasingOption:
    """Evaluates a single supplier product based on commercial terms.
    
    Includes Rule 2 (Shelf Life), Rule 4 (Facility Storage),
    Rule 5 (OTIF Lateness Buffer), and Rule 6 (Volume Price Breaks).
    """
    # 1. Quantity adjusted to satisfy supplier MOQ
    order_quantity = max(net_shortage, supplier_prod.minimum_order_quantity)
    excess_quantity = max(0, order_quantity - net_shortage)

    # 2. Financial calculation and volume price break check (Rule 6)
    unit_price_float = float(supplier_prod.unit_price)
    unlocked_tier: Optional[PriceTier] = None
    trade_offs: List[str] = []

    if supplier_prod.price_tiers:
        for tier in sorted(supplier_prod.price_tiers, key=lambda t: t.min_quantity):
            if order_quantity >= tier.min_quantity:
                unit_price_float = float(tier.unit_price)
                unlocked_tier = tier
            elif order_quantity < tier.min_quantity:
                # Check if buying more units at tier discount saves money net
                tier_cost = round(tier.min_quantity * float(tier.unit_price), 2)
                current_cost_est = round(order_quantity * unit_price_float, 2)
                if tier_cost < current_cost_est:
                    trade_offs.append(
                        f"Volume price break opportunity: Increasing order from {order_quantity} to {tier.min_quantity} "
                        f"units unlocks ${float(tier.unit_price):.2f}/unit tier, saving ${current_cost_est - tier_cost:,.2f} net."
                    )

    total_cost = round(order_quantity * unit_price_float, 2)
    is_budget_feasible = total_cost <= float(remaining_budget)

    # 3. Delivery arrival calculation with OTIF historical delay buffer (Rule 5)
    effective_lead_time = supplier_prod.lead_time_days + max(0, supplier_prod.historical_delay_days)
    arrival_date = evaluation_date + timedelta(days=effective_lead_time)
    is_timing_feasible = arrival_date <= target_delivery_date

    if supplier_prod.historical_delay_days > 0:
        trade_offs.append(
            f"Supplier lead time padded by {supplier_prod.historical_delay_days} day(s) (effective: {effective_lead_time} days) "
            f"based on historical delivery variance."
        )

    # 4. Dynamic chronological storage validation (Per-SKU & Facility-Wide / Rule 4)
    projected_stock_at_arrival = calculate_projected_stock_at_arrival(
        on_hand=on_hand,
        daily_demand=daily_demand,
        open_orders=open_orders,
        proposed_quantity=order_quantity,
        arrival_date=arrival_date,
        evaluation_date=evaluation_date,
    )
    is_storage_feasible = projected_stock_at_arrival <= storage_capacity

    if facility_available_m3 is not None and facility_available_m3 > 0:
        order_vol = order_quantity * unit_volume_m3
        if order_vol > facility_available_m3:
            is_storage_feasible = False
            trade_offs.append(
                f"Facility volume exceeded: Order requires {order_vol:,.1f} m³, exceeding available warehouse facility space ({facility_available_m3:,.1f} m³)."
            )

    # 5. Shelf-life and expiration guard (Rule 2)
    if shelf_life_days and shelf_life_days > 0 and daily_demand > 0:
        demand_in_shelf_life = int(round(shelf_life_days * daily_demand))
        if order_quantity > demand_in_shelf_life:
            spoilage_units = order_quantity - demand_in_shelf_life
            trade_offs.append(
                f"Shelf-life spoilage risk: Order quantity ({order_quantity}) exceeds projected demand ({demand_in_shelf_life}) "
                f"over product shelf life ({shelf_life_days} days), risking {spoilage_units} spoiled/expired units."
            )
            if spoilage_units > (0.25 * order_quantity):
                is_storage_feasible = False

    # 6. Supplier fulfillment capacity check (Rule 3)
    is_capacity_feasible = True
    if supplier_prod.available_capacity is not None and order_quantity > supplier_prod.available_capacity:
        is_capacity_feasible = False
        trade_offs.append(
            f"Supplier capacity capped: Supplier confirms only {supplier_prod.available_capacity} units available "
            f"against requested order of {order_quantity} units."
        )

    # 7. Document standard constraint trade-offs
    if excess_quantity > 0:
        trade_offs.append(
            f"MOQ of {supplier_prod.minimum_order_quantity} creates {excess_quantity} excess units above net shortage of {net_shortage}."
        )
    if not is_budget_feasible:
        trade_offs.append(
            f"Total cost (${total_cost:,.2f}) exceeds remaining budget (${float(remaining_budget):,.2f})."
        )
    if not is_timing_feasible:
        days_late = (arrival_date - target_delivery_date).days
        trade_offs.append(
            f"Delivery date ({arrival_date}) misses target deadline ({target_delivery_date}) by {days_late} day(s)."
        )
    if projected_stock_at_arrival > storage_capacity:
        trade_offs.append(
            f"Projected stock at arrival ({projected_stock_at_arrival} units) exceeds warehouse storage capacity ({storage_capacity} units)."
        )

    return PurchasingOption(
        supplier_id=supplier_prod.supplier_id,
        supplier_name=supplier_prod.supplier_name,
        quantity=order_quantity,
        unit_price=unit_price_float,
        total_cost=total_cost,
        lead_time_days=effective_lead_time,
        estimated_delivery_date=arrival_date,
        excess_quantity=excess_quantity,
        projected_stock_at_arrival=projected_stock_at_arrival,
        is_timing_feasible=is_timing_feasible,
        is_budget_feasible=is_budget_feasible,
        is_storage_feasible=is_storage_feasible,
        is_capacity_feasible=is_capacity_feasible,
        trade_offs=trade_offs,
        effective_lead_time_days=effective_lead_time,
        unlocked_price_tier=unlocked_tier,
    )
