from datetime import date, timedelta
from typing import List, Optional

from app.decision_engine.types import (
    DemandForecastInput,
    OpenPurchaseOrderInput,
    StockoutTimelineAnalysis,
)


def calculate_daily_demand(forecast: DemandForecastInput) -> float:
    """Calculates average daily demand rate over the forecast horizon.
    
    If period_end <= period_start, treats duration as at least 1 day.
    """
    days = (forecast.period_end - forecast.period_start).days
    effective_days = max(1, days)
    return forecast.forecast_quantity / effective_days


def analyze_chronological_stockout_timeline(
    on_hand: int,
    forecast: DemandForecastInput,
    open_orders: List[OpenPurchaseOrderInput],
    evaluation_date: date,
    safety_stock_quantity: int = 0,
) -> StockoutTimelineAnalysis:
    """Chronologically simulates daily inventory levels to evaluate stockout risk.
    
    Separates:
    1. Interim stockout gap (days and shortfall when stock depletes before a PO arrives).
    2. Final unmet demand (overall cumulative deficit at the end of the horizon, including safety buffer).
    3. Additional purchasing requirement (units required to cover shortages or bridge gaps).
    """
    daily_demand = calculate_daily_demand(forecast)
    horizon_start = max(evaluation_date, forecast.period_start)
    horizon_end = max(horizon_start, forecast.period_end)
    total_days = max(1, (horizon_end - horizon_start).days)

    # 1. Initial days of coverage before any replenishment
    if daily_demand > 0:
        days_of_initial_coverage = on_hand / daily_demand
    else:
        days_of_initial_coverage = float(total_days)

    # Initial stockout date if no POs arrive
    initial_stockout_date: Optional[date] = None
    if daily_demand > 0 and days_of_initial_coverage < total_days:
        initial_stockout_date = horizon_start + timedelta(
            days=int(days_of_initial_coverage)
        )

    # Group open POs by expected delivery date (only those within or affecting horizon)
    po_deliveries_by_date = {}
    total_open_po_quantity = 0
    for po in open_orders:
        if po.status.upper() in ("OPEN", "PENDING", "IN_TRANSIT"):
            total_open_po_quantity += po.quantity
            po_deliveries_by_date[po.expected_delivery_date] = (
                po_deliveries_by_date.get(po.expected_delivery_date, 0) + po.quantity
            )

    # 2. Day-by-day chronological trajectory
    current_stock = float(on_hand)
    has_interim_stockout = False
    interim_stockout_days = 0
    max_deficit_during_interim = 0.0
    first_stockout_date: Optional[date] = None

    for day_offset in range(total_days):
        current_date = horizon_start + timedelta(days=day_offset)

        # Incoming PO arrivals credited at start of day
        if current_date in po_deliveries_by_date:
            current_stock += po_deliveries_by_date[current_date]

        # Daily consumption during the day (discrete series curve if provided, else flat rate)
        if forecast.daily_demand_series and day_offset < len(forecast.daily_demand_series):
            consumption_today = float(forecast.daily_demand_series[day_offset])
        else:
            consumption_today = daily_demand

        current_stock -= consumption_today

        # Floating-point tolerance threshold
        if current_stock < -1e-4:
            has_interim_stockout = True
            interim_stockout_days += 1
            deficit = abs(current_stock)
            if deficit > max_deficit_during_interim:
                max_deficit_during_interim = deficit
            if first_stockout_date is None:
                first_stockout_date = current_date

    # 3. Final unmet demand & purchasing requirement
    # Final projected inventory at horizon end
    final_projected_inventory = int(round(current_stock))
    
    # Cumulative gross requirement includes safety stock buffer (Rule 1)
    gross_requirement = forecast.forecast_quantity + safety_stock_quantity
    total_supply = on_hand + total_open_po_quantity
    final_unmet_demand = max(0, gross_requirement - total_supply)

    # Additional purchasing requirement:
    # If there is final unmet demand, that is the primary purchasing requirement.
    # If final unmet demand is 0, but an interim stockout occurs because a PO arrives late,
    # the additional requirement represents the bridge stock needed to avert the interim gap.
    if final_unmet_demand > 0:
        additional_purchasing_requirement = final_unmet_demand
    elif has_interim_stockout:
        additional_purchasing_requirement = int(round(max_deficit_during_interim + safety_stock_quantity))
    else:
        additional_purchasing_requirement = 0

    return StockoutTimelineAnalysis(
        daily_demand=daily_demand,
        days_of_initial_coverage=days_of_initial_coverage,
        stockout_date=first_stockout_date or initial_stockout_date,
        has_interim_stockout=has_interim_stockout,
        interim_stockout_days=interim_stockout_days,
        interim_shortage_quantity=int(round(max_deficit_during_interim)),
        final_projected_inventory=final_projected_inventory,
        final_unmet_demand=final_unmet_demand,
        additional_purchasing_requirement=additional_purchasing_requirement,
        safety_stock_quantity=safety_stock_quantity,
        target_ending_inventory=safety_stock_quantity,
    )
