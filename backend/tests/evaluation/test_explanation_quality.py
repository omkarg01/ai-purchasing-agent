from unittest.mock import MagicMock, patch
import pytest

from app.decision_engine import evaluate_purchasing_decision
from app.agent.purchasing_agent import generate_purchasing_briefing
from tests.evaluation.test_decision_quality import SCENARIOS, build_engine_input


@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s["scenario_id"] for s in SCENARIOS],
)
def test_deterministic_explanation_fidelity(scenario):
    """Verifies that the engine's synthesized reasoning points accurately reflect facts and constraints without contradictions."""
    engine_input = build_engine_input(scenario["input"])
    result = evaluate_purchasing_decision(engine_input)
    explanation = "\n\n".join(result.reasoning_points)

    expected_decision = scenario["expected"]["decision"]
    scenario_id = scenario["scenario_id"]

    # 1. No decision contradiction
    if expected_decision == "REJECT":
        assert "is fully justified" not in explanation.lower()
        assert "unnecessary" in explanation.lower() or "rejected" in explanation.lower() or "fully cover" in explanation.lower()
    elif expected_decision == "ACCEPT":
        assert "rejected" not in explanation.lower()
        assert "fully justified" in explanation.lower() or "optimal" in explanation.lower()
    elif expected_decision == "INVESTIGATE":
        assert "fully justified" not in explanation.lower()
        assert any(
            term in explanation.lower()
            for term in ["investigate", "insufficient", "cannot prevent stockout", "rush delivery"]
        ), f"[{scenario_id}] INVESTIGATE explanation should mention required inquiry."

    # 2. Correct quantities referenced for actionable recommendations
    if expected_decision in ["ACCEPT", "MODIFY"] and result.suggested_quantity is not None and result.suggested_quantity > 0:
        assert str(result.suggested_quantity) in explanation, (
            f"[{scenario_id}] Explanation should mention suggested quantity {result.suggested_quantity}."
        )

    # 3. No false purchase order execution claims
    lower_exp = explanation.lower()
    assert "order has been submitted" not in lower_exp
    assert "po has been placed" not in lower_exp
    assert "payment executed" not in lower_exp


def test_gemini_briefing_synthesis_structure_and_safeguards():
    """Tests Gemini briefing generation with a mocked LLM client to verify prompt contract and non-contradiction."""
    scenario = SCENARIOS[0]  # EV-001: Excessive Quantity -> MODIFY
    engine_input = build_engine_input(scenario["input"])
    result = evaluate_purchasing_decision(engine_input)

    mock_llm_text = """**Strategic Assessment**
The verdict is MODIFY because the buyer recommended 500 units when net demand shortage is only 200 units.

**Supply & Operational Analysis**
Acme Industrial Supplies can deliver 200 units in 3 days, arriving before the stockout deadline.

**Recommended Buyer Action Plan**
Adjust the recommendation to 200 units to avoid unnecessary holding costs and approve."""

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_llm_text
    mock_client.models.generate_content.return_value = mock_response

    with patch("os.getenv", return_value="fake-api-key"), \
         patch("google.genai.Client", return_value=mock_client):

        briefing = generate_purchasing_briefing(
            engine_input=engine_input,
            decision_result=result,
            product_name="Precision Industrial Widget A",
            product_sku="SKU-WIDGET-A",
        )

        # 1. Structure matches contract
        assert "Strategic Assessment" in briefing
        assert "Supply & Operational Analysis" in briefing
        assert "Recommended Buyer Action Plan" in briefing

        # 2. Verdict alignment
        assert "MODIFY" in briefing
        assert "500 units" in briefing or "200 units" in briefing

        # 3. No false execution claims
        assert "order executed" not in briefing.lower()
