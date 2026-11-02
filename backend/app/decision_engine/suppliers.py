from datetime import date, timedelta
from decimal import Decimal
from typing import List, Tuple

from app.decision_engine.types import (
    OpenPurchaseOrderInput,
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
) -> PurchasingOption:
    """Evaluates a single supplier product based on commercial terms.
    
    Note: Evaluates strictly using unit_price, lead_time_days, and minimum_order_quantity.
    Supplier stock availability is not in the data model and is not assumed.
    """
    # 1. Quantity adjusted to satisfy supplier MOQ
    order_quantity = max(net_shortage, supplier_prod.minimum_order_quantity)
    excess_quantity = max(0, order_quantity - net_shortage)

    # 2. Financial calculation and budget constraint
    unit_price_float = float(supplier_prod.unit_price)
    total_cost = round(order_quantity * unit_price_float, 2)
    is_budget_feasible = total_cost <= float(remaining_budget)

    # 3. Delivery arrival calculation
    arrival_date = evaluation_date + timedelta(days=supplier_prod.lead_time_days)
    is_timing_feasible = arrival_date <= target_delivery_date

    # 4. Dynamic chronological storage validation
    projected_stock_at_arrival = calculate_projected_stock_at_arrival(
        on_hand=on_hand,
        daily_demand=daily_demand,
        open_orders=open_orders,
        proposed_quantity=order_quantity,
        arrival_date=arrival_date,
        evaluation_date=evaluation_date,
    )
    is_storage_feasible = projected_stock_at_arrival <= storage_capacity

    # 5. Document trade-offs and constraint details
    trade_offs: List[str] = []
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
    if not is_storage_feasible:
        trade_offs.append(
            f"Projected stock at arrival ({projected_stock_at_arrival} units) exceeds warehouse storage capacity ({storage_capacity} units)."
        )

    return PurchasingOption(
        supplier_id=supplier_prod.supplier_id,
        supplier_name=supplier_prod.supplier_name,
        quantity=order_quantity,
        unit_price=unit_price_float,
        total_cost=total_cost,
        lead_time_days=supplier_prod.lead_time_days,
        estimated_delivery_date=arrival_date,
        excess_quantity=excess_quantity,
        projected_stock_at_arrival=projected_stock_at_arrival,
        is_timing_feasible=is_timing_feasible,
        is_budget_feasible=is_budget_feasible,
        is_storage_feasible=is_storage_feasible,
        trade_offs=trade_offs,
    )

