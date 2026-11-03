"""Autonomous Purchasing Intelligence Agent.

Combines deterministic decision engine facts with LLM synthesis to produce
executive-grade purchasing briefings, risk analysis, and actionable buyer recommendations.
"""
import os
import logging
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.decision_engine.types import DecisionResult, EngineInput

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")


def generate_purchasing_briefing(
    engine_input: EngineInput,
    decision_result: DecisionResult,
    product_name: Optional[str] = None,
    product_sku: Optional[str] = None,
) -> str:
    """Generates an executive-grade procurement briefing using the LLM agent.
    
    If GEMINI_API_KEY is not configured or an error occurs, falls back cleanly
    to the deterministic engine's rule-based reasoning points.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.info("GEMINI_API_KEY not configured. Using deterministic reasoning points.")
        return "\n\n".join(decision_result.reasoning_points)

    try:
        client = genai.Client(api_key=api_key)

        calc = decision_result.calculations or {}
        has_interim_stockout = calc.get("has_interim_stockout", False)
        net_shortage = calc.get("additional_purchasing_requirement", calc.get("final_unmet_demand", 0))
        stockout_date = calc.get("stockout_date", "None detected")

        # Build supplier comparison text
        suppliers_info = []
        for s in engine_input.suppliers:
            suppliers_info.append(
                f"- {s.supplier_name} (ID: {s.supplier_id}): "
                f"${s.unit_price:.2f}/unit, {s.lead_time_days} days lead time, MOQ {s.minimum_order_quantity} units"
            )
        suppliers_text = "\n".join(suppliers_info) if suppliers_info else "No alternative suppliers registered."

        open_orders_info = []
        for po in engine_input.open_orders:
            open_orders_info.append(
                f"- PO #{po.id}: {po.quantity} units arriving on {po.expected_delivery_date} (Status: {po.status})"
            )
        open_orders_text = "\n".join(open_orders_info) if open_orders_info else "No incoming open purchase orders."

        prompt = f"""You are the AI Purchasing Intelligence Agent for an enterprise supply chain.
Analyze the following verified purchasing data and produce a professional, structured executive briefing for the human procurement buyer.

### CORE FACTS (VERIFIED BY CALCULATION ENGINE - DO NOT CHANGE THESE NUMBERS):
- Product: {product_name or 'Product'} (SKU: {product_sku or f'#{engine_input.recommendation.product_id}'})
- Current On-Hand Available Inventory: {engine_input.inventory.available_quantity} units
- Warehouse Storage Capacity: {engine_input.inventory.storage_capacity} units
- Projected Demand Forecast: {engine_input.forecast.forecast_quantity} units by {engine_input.forecast.period_end}
- Open Orders In-Transit:
{open_orders_text}
- Available Suppliers:
{suppliers_text}
- Total Purchasing Budget: ${engine_input.budget.total_budget:,.2f} | Remaining Uncommitted: ${engine_input.budget.remaining_budget:,.2f}

### ENGINE DECISION:
- Verdict: {decision_result.decision}
- Suggested Purchase Quantity: {decision_result.suggested_quantity if decision_result.suggested_quantity is not None else 'None (0)'} units
- Preferred Supplier ID: {decision_result.suggested_supplier_id or 'None'}
- Requested Delivery Deadline: {engine_input.recommendation.requested_delivery_date}
- Interim Stockout Detected: {'YES (Stock exhausts before delivery)' if has_interim_stockout else 'NO'}
- Projected Stockout Date: {stockout_date}
- Net Shortage: {net_shortage} units

### INSTRUCTIONS:
Synthesize this into a structured briefing with exactly these 3 sections:

**Strategic Assessment**
Explain why the verdict is {decision_result.decision} in 2-3 clear business sentences, citing the demand vs stock numbers and delivery timing.

**Supply & Operational Analysis**
Detail the lead time, supplier MOQ, and warehouse capacity feasibility. If an alternative supplier was chosen or rejected, explain the trade-off.

**Recommended Buyer Action Plan**
Provide clear, practical next steps for the buyer (e.g. approve immediately, request expedited delivery, split order, or reject due to overstocking).

Maintain a formal, objective, senior procurement analyst tone. Do not use generic filler words. Format cleanly with standard markdown.
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1500,
            ),
        )

        if response and response.text:
            return response.text.strip()

    except Exception as exc:
        logger.warning(f"Gemini API call failed: {exc}. Falling back to deterministic reasoning.")

    # Graceful fallback to deterministic engine points
    return "\n\n".join(decision_result.reasoning_points)

