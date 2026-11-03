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
    to the structured deterministic executive briefing.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or os.getenv("TESTING") == "true":
        logger.info("Using deterministic structured briefing.")
        return _generate_deterministic_briefing(engine_input, decision_result, product_name, product_sku)

    try:
        client = genai.Client(api_key=api_key)

        calc = decision_result.calculations or {}
        has_interim_stockout = calc.get("has_interim_stockout", False)
        net_shortage = calc.get("additional_purchasing_requirement", calc.get("final_unmet_demand", 0))
        stockout_date = calc.get("stockout_date", "None detected")
        levers_data = calc.get("negotiation_levers", [])

        # Build supplier comparison text
        suppliers_info = []
        for s in engine_input.suppliers:
            flex_info = []
            if s.available_capacity is not None:
                flex_info.append(f"Cap: {s.available_capacity} units")
            if getattr(s, "expedited_lead_time_days", None):
                flex_info.append(f"Rush Lead: {s.expedited_lead_time_days}d")
            flex_str = f" [{', '.join(flex_info)}]" if flex_info else ""
            suppliers_info.append(
                f"- {s.supplier_name} (ID: {s.supplier_id}): "
                f"${s.unit_price:.2f}/unit, {s.lead_time_days} days lead time, MOQ {s.minimum_order_quantity} units{flex_str}"
            )
        suppliers_text = "\n".join(suppliers_info) if suppliers_info else "No alternative suppliers registered."

        open_orders_info = []
        for po in engine_input.open_orders:
            open_orders_info.append(
                f"- PO #{po.id}: {po.quantity} units arriving on {po.expected_delivery_date} (Status: {po.status})"
            )
        open_orders_text = "\n".join(open_orders_info) if open_orders_info else "No incoming open purchase orders."

        # Build negotiation levers text
        if levers_data:
            levers_lines = []
            for lev in levers_data:
                savings_note = f" (Financial Savings: ${lev['potential_savings']:,.2f})" if lev.get("potential_savings") else ""
                levers_lines.append(f"- [{lev.get('lever_type')}]: {lev.get('recommended_talking_point')}{savings_note}")
            levers_text = "\n".join(levers_lines)
        else:
            levers_text = "- No specific negotiation levers identified; standard terms apply."

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

### QUANTIFIED NEGOTIATION LEVERS & COUNTER-OFFER DATA:
{levers_text}

### INSTRUCTIONS:
Synthesize this into a structured briefing with exactly these sections:

**Strategic Assessment**
Explain why the verdict is {decision_result.decision} in 2-3 clear business sentences, citing the demand vs stock numbers and delivery timing.

**Supply & Operational Analysis**
Detail the lead time, supplier MOQ, vendor fulfillment capacity, and warehouse space feasibility. If split sourcing or an alternative supplier was chosen, explain the trade-offs.

**Recommended Buyer Action Plan**
Provide clear, practical next steps for the buyer (e.g. approve immediately, request expedited delivery, split order, or reject due to overstocking).

#### Buyer Negotiation Strategy & Counter-Offers
Provide 2-3 precise bullet points using the exact numbers from the QUANTIFIED NEGOTIATION LEVERS (target lead time days, suggested MOQ reduction, benchmark price counter-offer, or partial batch quantities) that the buyer can immediately use in communications with the vendor.

Maintain a formal, objective, senior procurement analyst tone. Do not invent any numbers. Format cleanly with standard markdown.
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

    # Graceful fallback to deterministic structured executive briefing
    return _generate_deterministic_briefing(engine_input, decision_result, product_name, product_sku)


def _generate_deterministic_briefing(
    engine_input: EngineInput,
    decision_result: DecisionResult,
    product_name: Optional[str] = None,
    product_sku: Optional[str] = None,
) -> str:
    """Renders a structured, executive-grade briefing when LLM synthesis is offline."""
    calc = decision_result.calculations or {}
    p_name = product_name or f"Product #{engine_input.recommendation.product_id}"
    verdict = decision_result.decision
    suggested_qty = decision_result.suggested_quantity if decision_result.suggested_quantity is not None else 0
    supplier_name = (
        decision_result.preferred_option.supplier_name
        if decision_result.preferred_option
        else (f"Supplier #{decision_result.suggested_supplier_id}" if decision_result.suggested_supplier_id else "Unassigned")
    )

    # 1. Strategic Assessment
    strat_lines = []
    if verdict == "ACCEPT":
        strat_lines.append(
            f"The proposed order of {suggested_qty} units for {p_name} is fully validated and recommended for approval. "
            f"Delivery with {supplier_name} meets operational timeline requirements and satisfies projected demand."
        )
    elif verdict == "MODIFY":
        if calc.get("is_split_sourcing"):
            alloc = calc.get("split_allocation", {})
            strat_lines.append(
                f"Evaluation determines that a multi-vendor split order of {suggested_qty} units is required for {p_name}. "
                f"Primary supplier capacity is capped; remainder is allocated to a qualified secondary supplier to prevent supply disruption."
            )
        else:
            strat_lines.append(
                f"Recommendation for {p_name} is adjusted to {suggested_qty} units from {supplier_name}. "
                f"This aligns inventory replenishment with demand burn rates, avoids excessive capital lockup, and satisfies vendor constraints."
            )
    elif verdict == "REJECT":
        strat_lines.append(
            f"Recommendation of {engine_input.recommendation.recommended_quantity} units for {p_name} is rejected. "
            f"Existing inventory and scheduled open orders sufficiently cover projected demand without risk of stockout."
        )
    else:  # INVESTIGATE
        strat_lines.append(
            f"Recommendation for {p_name} requires immediate buyer investigation. "
            f"Lead times or budget constraints prevent standard automated replenishment before projected stockout."
        )

    # 2. Supply & Operational Analysis
    ops_lines = []
    if decision_result.reasoning_points:
        ops_lines.extend(decision_result.reasoning_points)
    if decision_result.warnings:
        ops_lines.extend([f"Warning: {w}" for w in decision_result.warnings])
    if decision_result.risks:
        ops_lines.extend([f"Operational Risk: {r}" for r in decision_result.risks])

    # 3. Recommended Buyer Action Plan
    action_lines = []
    if verdict == "ACCEPT":
        action_lines.append(f"Execute purchase order for {suggested_qty} units with {supplier_name}.")
    elif verdict == "MODIFY":
        if calc.get("is_split_sourcing"):
            alloc = calc.get("split_allocation", {})
            action_lines.append(
                f"Issue split purchase orders: {alloc.get('primary_quantity')} units to {alloc.get('primary_supplier_name')} "
                f"(${alloc.get('primary_cost', 0):,.2f}) and {alloc.get('secondary_quantity')} units to {alloc.get('secondary_supplier_name')} "
                f"(${alloc.get('secondary_cost', 0):,.2f})."
            )
        else:
            action_lines.append(
                f"Update purchase order parameters to {suggested_qty} units with {supplier_name} and proceed with procurement approval."
            )
    elif verdict == "REJECT":
        action_lines.append("Cancel purchase recommendation. Re-evaluate stock levels at the next replenishment cycle.")
    else:
        action_lines.append("Engage suppliers for emergency rush shipment or escalate for budget approval.")

    # 4. Buyer Negotiation Strategy & Counter-Offers
    levers = calc.get("negotiation_levers", [])
    negotiation_bullets = []
    if levers:
        for lev in levers[:3]:  # Top 2-3 precise points
            negotiation_bullets.append(f"- **{lev['title']}**: {lev['recommended_talking_point']}")
    else:
        negotiation_bullets.append("- Proceed with standard supplier contract terms.")

    briefing_parts = [
        "**Strategic Assessment**",
        "\n".join(strat_lines),
        "**Supply & Operational Analysis**",
        "\n".join(f"- {pt}" for pt in ops_lines) if ops_lines else "- Operational constraints verified.",
        "**Recommended Buyer Action Plan**",
        "\n".join(action_lines),
        "#### Buyer Negotiation Strategy & Counter-Offers",
        "\n".join(negotiation_bullets),
    ]

    return "\n\n".join(briefing_parts)

