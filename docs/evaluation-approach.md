# AI Purchasing Agent: V1 Decision Evaluation Approach & Dataset Report

## 1. Evaluation Objective

The objective of this evaluation is to rigorously assess the quality, correctness, and constraint fidelity of the **AI Purchasing Agent's** purchasing decisions using a manually curated, independently verified evaluation dataset.

In alignment with the core assignment requirements, this evaluation demonstrates whether the agent:
1. **Makes the correct purchasing decision** (`ACCEPT`, `MODIFY`, `REJECT`, or `INVESTIGATE`).
2. **Obtains and uses the necessary information** (inventory on-hand, forecast demand rate, incoming POs, lead times, MOQ, budget, and storage capacity).
3. **Respects purchasing constraints** (hard budget limits, warehouse storage capacity, supplier MOQs, and delivery deadlines).
4. **Takes appropriate actions** (proposing optimal order quantities and supplier alternatives when adjustments are warranted).
5. **Validates results** (ensuring proposed parameters mitigate stockouts without creating overstock).
6. **Handles situations where initial parameters fail** (flagging risks and triggering human investigation pathways).

---

## 2. Dataset Design & Scenario Descriptions

The V1 evaluation dataset consists of **eight distinct, realistic scenarios** defined in [`backend/tests/evaluation/scenarios.json`](file:///c:/Users/omkar/Documents/Project/AI/AI%20Purchasing%20Agent/backend/tests/evaluation/scenarios.json). Each scenario tests a unique decision-making capability without redundancy:

| Scenario ID | Scenario Name | Primary Situation | Expected Decision | Core Verification Objective |
|---|---|---|:---:|---|
| **EV-001** | Excessive Recommended Quantity | Buyer requested 500 units; net shortage is only 200 units. | **`MODIFY`** | Downward adjustment to prevent holding costs while choosing fastest feasible supplier. |
| **EV-002** | Optimal Recommendation | Buyer requested 150 units from Acme; matches net shortage, lead time, and budget. | **`ACCEPT`** | Affirmation of already optimal parameters. |
| **EV-003** | Demand Fully Covered by Stock | On-hand inventory (200) covers entire 14-day forecast demand (150). Net shortage = 0. | **`REJECT`** | Preventing unnecessary procurement and holding costs when stock suffices. |
| **EV-004** | Supplier MOQ Exceeds Shortage | Net shortage is 20 units; only catalog supplier enforces MOQ of 100 units. | **`MODIFY`** | Upward adjustment to 100 units to satisfy MOQ, noting 80 excess units while verifying warehouse capacity. |
| **EV-005** | Insufficient Purchasing Budget | Imminent stockout in 1 day; replenishment cost ($4,500) exceeds remaining budget ($200). | **`INVESTIGATE`** | Refusal to execute an over-budget purchase; escalating for human budget review. |
| **EV-006** | Storage Capacity Exceeded | Replenishment of 210 units would result in 240 units on-hand, exceeding 120-unit warehouse limit. | **`INVESTIGATE`** | Blocking storage overflow when physical warehouse constraints cannot be met. |
| **EV-007** | Supplier Lead Time Causes Stockout | Stockout occurs in 2 days (2026-11-03); only supplier has 12-day lead time (2026-11-13). | **`INVESTIGATE`** | Identifying lead time failure and triggering expediting/rush investigation. |
| **EV-008** | No Catalog Suppliers Available | Urgent shortage of 160 units; product has no approved suppliers in catalog. | **`INVESTIGATE`** | Detecting supply catalog gap and prompting external human sourcing. |

---

## 3. Evaluation Dimensions & Metrics

| Dimension | Metric | Measurement Method |
|---|---|---|
| **Decision Accuracy** | $100\%$ match with verified verdict | Automated equality check against independently calculated verdict (`ACCEPT`, `MODIFY`, `REJECT`, `INVESTIGATE`). |
| **Quantity Accuracy** | Exact unit match | Comparison between engine suggested quantity and calculated net requirement / MOQ. |
| **Supplier Selection** | Exact ID match | Verification that the chosen supplier delivers on time at lowest total cost. |
| **Constraint Adherence** | 0 constraint violations | Negative assertions verifying no over-budget or storage-overflow options are accepted. |
| **Explanation Fidelity** | Factual non-contradiction | Verifying that natural language explanations cite real numbers, do not contradict verdicts, and never claim automated PO execution. |

---

## 4. How Expected Outcomes Were Independently Determined

Expected outcomes were **calculated manually from foundational supply chain rules before executing the test suite**:

### Arithmetic Verification for Each Scenario

1. **EV-001 (Excessive Quantity)**:
   - Demand = $300$ over $14$ days $\rightarrow 21.43\text{ units/day}$.
   - Available stock = $100$ units $\rightarrow$ coverage = $100 / 21.43 = 4.67\text{ days}$ (Stockout on Day 4: `2026-11-05`).
   - Net requirement = $300 - 100 = 200\text{ units}$.
   - Supplier 1 delivers in $3$ days (`2026-11-04`), before stockout and before deadline (`2026-11-06`).
   - Cost: $200 \times \$15.00 = \$3,000 \le \$20,000$ (Budget OK). Storage: $100 - 3(21.43) + 200 = 235 \le 1,000$ (Storage OK).
   - Expected Decision: **`MODIFY`** to $200$ units from Supplier 1.

2. **EV-002 (Optimal Recommendation)**:
   - Demand = $200$ over $10$ days $\rightarrow 20\text{ units/day}$.
   - Stock = $50$ units $\rightarrow$ coverage = $2.5\text{ days}$ (Stockout on `2026-11-03`).
   - Net requirement = $200 - 50 = 150\text{ units}$.
   - Buyer recommended $150$ units from Supplier 1. Lead time = $2$ days (delivers `2026-11-03`).
   - Cost = $150 \times \$10.00 = \$1,500 \le \$10,000$.
   - Parameters match optimal values $\rightarrow$ Expected Decision: **`ACCEPT`**.

3. **EV-003 (No Purchase Needed)**:
   - Forecast demand = $150$ units. Available stock = $200$ units.
   - Day-by-day inventory never drops below zero (ending balance = $+50$ units).
   - Final unmet demand = $0$, interim stockout = False.
   - Expected Decision: **`REJECT`** (Suggested quantity = $0$, prevents excess inventory).

4. **EV-004 (Supplier MOQ > Shortage)**:
   - Net shortage = $120 - 100 = 20\text{ units}$.
   - Supplier MOQ = $100\text{ units}$.
   - Formula: $\text{Order Quantity} = \max(20, 100) = 100\text{ units}$.
   - Excess units = $80$. Storage at arrival = $(100 - 4 \times 12) + 100 = 152 \le 500$ (Storage OK). Cost = $\$1,200 \le \$10,000$ (Budget OK).
   - Expected Decision: **`MODIFY`** to $100$ units from Supplier 1.

5. **EV-005 (Insufficient Budget)**:
   - On-hand stock = $20$ units. Daily demand = $20\text{ units/day} \rightarrow$ Stockout tomorrow (`2026-11-02`).
   - Shortage = $180\text{ units} \rightarrow$ Order cost = $180 \times \$25.00 = \$4,500.00$.
   - Remaining budget = $\$5,000 - \$4,800 = \$200.00$.
   - Order exceeds remaining budget by $\$4,300.00$. Imminent stockout prohibits outright rejection.
   - Expected Decision: **`INVESTIGATE`** (Human budget escalation required).

6. **EV-006 (Storage Overflow)**:
   - On-hand stock = $90$ units. Storage capacity = $120$ units.
   - Shortage = $210\text{ units}$. Daily demand = $30\text{ units/day}$.
   - Supplier arrives on day 2. On-hand at arrival = $90 - 2(30) = 30\text{ units}$.
   - Total inventory upon delivery = $30 + 210 = 240\text{ units} > 120\text{ capacity}$.
   - Zero catalog suppliers can deliver without warehouse overflow.
   - Expected Decision: **`INVESTIGATE`** (Storage bottleneck).

7. **EV-007 (Lead Time Misses Stockout)**:
   - Stockout date = `2026-11-03` (2 days coverage). Target deadline = `2026-11-05`.
   - Supplier lead time = $12$ days $\rightarrow$ Delivery date = `2026-11-13` ($8$ days late).
   - Expected Decision: **`INVESTIGATE`** (Buyer must negotiate rush freight or expedite open orders).

8. **EV-008 (Empty Supplier Catalog)**:
   - Shortage = $160\text{ units}$.
   - Catalog suppliers = `[]`.
   - Expected Decision: **`INVESTIGATE`** (Human buyer must source external vendor).

---

## 5. Test Execution Methodology

The evaluation is executed automatically via pytest in the existing test environment:

```powershell
$env:PYTHONPATH="backend"
pytest backend/tests/evaluation -v
```

Two dedicated test suites enforce quality:
1. [`backend/tests/evaluation/test_decision_quality.py`](file:///c:/Users/omkar/Documents/Project/AI/AI%20Purchasing%20Agent/backend/tests/evaluation/test_decision_quality.py): Deserializes `scenarios.json` into typed `EngineInput` dataclasses and evaluates decision accuracy, suggested quantities, selected suppliers, and failure condition prohibitions.
2. [`backend/tests/evaluation/test_explanation_quality.py`](file:///c:/Users/omkar/Documents/Project/AI/AI%20Purchasing%20Agent/backend/tests/evaluation/test_explanation_quality.py): Verifies that generated briefings maintain factual fidelity with engine outputs, never contradict the verdict, and never claim automatic purchase order execution.

---

## 6. Actual Test Results

Executed on Python 3.14.0, pytest-9.1.1:

```text
============================= test session starts =============================
collected 17 items

backend/tests/evaluation/test_decision_quality.py::test_deterministic_decision_quality[EV-001] PASSED [  5%]
backend/tests/evaluation/test_decision_quality.py::test_deterministic_decision_quality[EV-002] PASSED [ 11%]
backend/tests/evaluation/test_decision_quality.py::test_deterministic_decision_quality[EV-003] PASSED [ 17%]
backend/tests/evaluation/test_decision_quality.py::test_deterministic_decision_quality[EV-004] PASSED [ 23%]
backend/tests/evaluation/test_decision_quality.py::test_deterministic_decision_quality[EV-005] PASSED [ 29%]
backend/tests/evaluation/test_decision_quality.py::test_deterministic_decision_quality[EV-006] PASSED [ 35%]
backend/tests/evaluation/test_decision_quality.py::test_deterministic_decision_quality[EV-007] PASSED [ 41%]
backend/tests/evaluation/test_decision_quality.py::test_deterministic_decision_quality[EV-008] PASSED [ 47%]
backend/tests/evaluation/test_explanation_quality.py::test_deterministic_explanation_fidelity[EV-001] PASSED [ 52%]
backend/tests/evaluation/test_explanation_quality.py::test_deterministic_explanation_fidelity[EV-002] PASSED [ 58%]
backend/tests/evaluation/test_explanation_quality.py::test_deterministic_explanation_fidelity[EV-003] PASSED [ 64%]
backend/tests/evaluation/test_explanation_quality.py::test_deterministic_explanation_fidelity[EV-004] PASSED [ 70%]
backend/tests/evaluation/test_explanation_quality.py::test_deterministic_explanation_fidelity[EV-005] PASSED [ 76%]
backend/tests/evaluation/test_explanation_quality.py::test_deterministic_explanation_fidelity[EV-006] PASSED [ 82%]
backend/tests/evaluation/test_explanation_quality.py::test_deterministic_explanation_fidelity[EV-007] PASSED [ 88%]
backend/tests/evaluation/test_explanation_quality.py::test_deterministic_explanation_fidelity[EV-008] PASSED [ 94%]
backend/tests/evaluation/test_explanation_quality.py::test_gemini_briefing_synthesis_structure_and_safeguards PASSED [100%]

======================== 17 passed, 1 warning in 0.11s ========================
```

---

## 7. Pass / Fail Summary

- **Evaluation Suite**: **17 / 17 passed (100%)**
  - Decision Quality Tests: 8 passed / 0 failed.
  - Explanation Fidelity Tests: 9 passed / 0 failed.
- **Complete Backend Test Suite**: **66 / 66 passed (100%)**
  - `test_decision_quality.py`: 8 passed
  - `test_explanation_quality.py`: 9 passed
  - `test_approval_api.py`: 6 passed
  - `test_database.py`: 2 passed
  - `test_decision_engine.py`: 12 passed
  - `test_e2e_flow.py`: 1 passed
  - `test_evaluation_api.py`: 5 passed
  - `test_evaluation_history.py`: 6 passed
  - `test_models.py`: 11 passed
  - `test_recommendation_crud.py`: 6 passed

---

## 8. Known Limitations & Unsupported Scenarios

### Assignment Scenario 2: Supplier Partial Fulfilment Limitation
- **Description**: The assignment prompt references Scenario 2 where an external supplier confirms that only 250 units can be supplied against an order of 500 units.
- **Current Architecture Analysis**: The existing `SupplierProduct` and `SupplierProductInput` data models support unit prices, lead times, and minimum order quantities (MOQ), but **do not model supplier production capacity limits or dynamic partial fulfilment responses**.
- **Deliberate Design Decision**: In strict accordance with scope boundaries, we did not fabricate an artificial supplier-capacity attribute or pretend external supplier confirmation is implemented.
- **Handling**: This scenario is documented as a known V1 boundary.

### Zero Automated Purchasing Execution
- The agent is intentionally designed as an **autonomous decision-support and human-in-the-loop recommendation system**.
- Purchase orders are **never automatically placed** with real suppliers; the human buyer retains final approval authority.

---

## 9. Future Improvements

1. **Dynamic Supplier Capacity Attributes**: Extend `SupplierProduct` to include `max_capacity_per_order` and `daily_production_rate`.
2. **Interactive Supplier Confirmation Sidecar**: Introduce a mock supplier interaction webhook simulating partial order confirmations (e.g. 250 of 500 available) and triggering automatic re-optimization of the remaining shortage.
3. **Multi-Item Order Bundling**: Evaluate multiple product shortages simultaneously to capitalize on shared supplier delivery fees.

