# Implementation Plan: Python Purchasing Decision Engine

## 1. Overview & Architectural Role

The **Purchasing Decision Engine** is a deterministic, modular Python calculation module residing in `backend/app/decision_engine/`. It evaluates purchasing recommendations against real-time operational data (inventory levels, burn rates, supplier lead times/MOQs, open PO arrival schedules, and remaining purchasing budget).

### Key Architectural Boundaries
- **Decision-Support Only**: The engine assists human buyers with structured evaluation; it never autonomously places orders, updates budgets, or communicates with vendors.
- **Pure & Deterministic**: Functions are pure Python calculations without direct database queries, HTTP dependencies, or ORM coupling.
- **LLM Decoupled**: The engine does **not** call Gemini or generate natural language prose. It produces structured data (facts, numbers, risks, trade-offs) that the Agent Orchestrator delivers to Gemini for explanation generation.

```
┌────────────────────────────────────────────────────────┐
│                   Agent Orchestrator                   │
│   (Fetches DB models -> Assembles EngineInput)         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             Purchasing Decision Engine                 │
│         (Pure Deterministic Python Functions)          │
│                                                        │
│  ┌─────────────────────────┐ ┌──────────────────────┐  │
│  │ Inventory Position Calc │ │ Stockout Timing Calc │  │
│  └─────────────────────────┘ └──────────────────────┘  │
│  ┌─────────────────────────┐ ┌──────────────────────┐  │
│  │  Supplier Feasibility   │ │  Budget Constraints  │  │
│  └─────────────────────────┘ └──────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │     Decision & Option Generation Rules           │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────────┬─────────────────────────────┘
                           │ Returns DecisionResult
                           ▼
┌────────────────────────────────────────────────────────┐
│                 Gemini AI Synthesizer                  │
│    (Generates clear business reasoning from facts)     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                Evaluation API Storage                  │
│      (POST /api/recommendations/{id}/evaluate)         │
└────────────────────────────────────────────────────────┘
```

---

## 2. Module & Function Architecture

The engine code will be organized under `backend/app/decision_engine/`:

```
backend/app/decision_engine/
├── __init__.py           # Exports public evaluation API and schemas
├── types.py              # Pydantic / Dataclass input & output contracts
├── inventory.py          # Inventory position and timeline stockout calculations
├── suppliers.py          # Supplier feasibility, MOQ, pricing, and timing analysis
├── options.py            # Feasible purchasing options generation and ranking
└── engine.py             # Main entry point and deterministic decision rule engine
```

### 2.1. Responsibilities and Function Signatures

#### A. Module: `inventory.py`
1. **`calculate_inventory_position(current_stock: int, open_orders: List[PurchaseOrderData]) -> InventoryPositionSummary`**
   - **Responsibility**: Computes current on-hand inventory, total on-order quantity from open POs, and total effective inventory position ($I_{pos} = I_{on\_hand} + \sum Q_{open\_po}$).
   - **Inputs**: Available quantity (integer $\ge 0$), list of open POs.
   - **Outputs**: `InventoryPositionSummary(on_hand, on_order, total_position, open_po_count)`.

2. **`analyze_stockout_timeline(on_hand: int, demand_forecast: DemandForecastData, open_orders: List[PurchaseOrderData], target_date: date) -> StockoutTimelineAnalysis`**
   - **Responsibility**: Evaluates the inventory trajectory day-by-day. Calculates average daily demand ($D_{daily} = Q_{forecast} / N_{days}$), days of coverage on current stock ($T_{cov} = I_{on\_hand} / D_{daily}$), estimated stockout date, and determines if open POs arrive before stockout occurs.
   - **Inputs**: Current on-hand stock, forecast details (period start, end, quantity), open POs with arrival dates, target evaluation date.
   - **Outputs**: `StockoutTimelineAnalysis(daily_demand, days_of_coverage, stockout_date, is_stockout_imminent, incoming_po_delays, interim_shortage)`.

#### B. Module: `suppliers.py`
3. **`evaluate_supplier_product(supplier_prod: SupplierProductData, net_shortage: int, remaining_budget: Decimal, target_delivery_date: date, evaluation_date: date) -> EvaluatedSupplierOption`**
   - **Responsibility**: Assesses a single supplier product against requirements:
     - Adjusts ordered quantity to satisfy MOQ: $Q_{order} = \max(\text{net\_shortage}, \text{MOQ})$.
     - Calculates order cost: $C_{order} = Q_{order} \times \text{unit\_price}$.
     - Determines lead-time arrival: $\text{arrival\_date} = \text{evaluation\_date} + \text{lead\_time\_days}$.
     - Flags hard constraint violations: budget overrun ($C_{order} > \text{remaining\_budget}$) or MOQ violations.
     - Flags timing feasibility: does order arrive on or before `target_delivery_date`?
   - **Inputs**: Supplier product data, net shortage units, available budget, delivery deadline, evaluation date.
   - **Outputs**: `EvaluatedSupplierOption(supplier_id, supplier_name, unit_price, moq, order_quantity, total_cost, lead_time_days, arrival_date, is_budget_feasible, is_timing_feasible, excess_units)`.

#### C. Module: `options.py`
4. **`generate_purchasing_options(supplier_products: List[SupplierProductData], net_shortage: int, remaining_budget: Decimal, target_date: date, evaluation_date: date) -> List[EvaluatedSupplierOption]`**
   - **Responsibility**: Runs all available suppliers through evaluation and filters out hard-constraint violations (e.g. exceeding total budget), while keeping options that satisfy MOQ even if they produce excess inventory.
   - **Outputs**: Ordered list of feasible purchasing options.

5. **`rank_preferred_option(feasible_options: List[EvaluatedSupplierOption], target_date: date) -> Tuple[Optional[EvaluatedSupplierOption], List[str]]`**
   - **Responsibility**: Selects the best option using multi-criteria ranking:
     1. Timing: Must deliver on or before the stockout/target deadline.
     2. Cost efficiency: Lowest total cost while meeting demand.
     3. Minimal excess: Smallest excess inventory over net shortage.
   - **Outputs**: `(preferred_option, ranking_reasons)`.

#### D. Module: `engine.py`
6. **`evaluate_purchasing_decision(input_data: EngineInput) -> DecisionResult`**
   - **Responsibility**: Orchestrates the calculation sequence and applies business rules to determine final decision: `ACCEPT`, `MODIFY`, `REJECT`, or `INVESTIGATE`.
   - **Inputs**: Full `EngineInput` dataclass.
   - **Outputs**: Complete `DecisionResult`.

---

## 3. Input & Output Contract

### 3.1. Input Contract (`EngineInput`)

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

@dataclass(frozen=True)
class InventoryInput:
    available_quantity: int       # Unreserved stock
    storage_capacity: int         # Warehouse maximum

@dataclass(frozen=True)
class DemandForecastInput:
    forecast_quantity: int        # Forecasted units
    period_start: date
    period_end: date

@dataclass(frozen=True)
class OpenPurchaseOrderInput:
    id: int
    supplier_id: int
    quantity: int
    unit_price: Decimal
    expected_delivery_date: date
    status: str

@dataclass(frozen=True)
class SupplierProductInput:
    supplier_id: int
    supplier_name: str
    unit_price: Decimal
    lead_time_days: int
    minimum_order_quantity: int

@dataclass(frozen=True)
class BudgetInput:
    total_budget: Decimal
    committed_amount: Decimal

    @property
    def remaining_budget(self) -> Decimal:
        return self.total_budget - self.committed_amount

@dataclass(frozen=True)
class RecommendationToEvaluate:
    id: int
    product_id: int
    recommended_quantity: int
    supplier_id: Optional[int]
    requested_delivery_date: date
    status: str

@dataclass(frozen=True)
class EngineInput:
    evaluation_date: date
    recommendation: RecommendationToEvaluate
    inventory: InventoryInput
    forecast: DemandForecastInput
    open_orders: List[OpenPurchaseOrderInput]
    suppliers: List[SupplierProductInput]
    budget: BudgetInput
```

### 3.2. Output Contract (`DecisionResult`)

```python
from dataclasses import dataclass
from typing import List, Optional, Literal, Dict, Any

@dataclass(frozen=True)
class PurchasingOption:
    supplier_id: int
    supplier_name: str
    quantity: int
    unit_price: float
    total_cost: float
    lead_time_days: int
    estimated_delivery_date: str
    excess_quantity: int
    is_timing_feasible: bool
    is_budget_feasible: bool
    trade_offs: List[str]

@dataclass(frozen=True)
class DecisionResult:
    decision: Literal["ACCEPT", "MODIFY", "REJECT", "INVESTIGATE"]
    suggested_quantity: Optional[int]
    suggested_supplier_id: Optional[int]
    preferred_option: Optional[PurchasingOption]
    feasible_options: List[PurchasingOption]
    
    # Quantitative calculations for transparency
    calculations: Dict[str, Any]  # inventory_position, net_shortage, daily_burn_rate, coverage_days
    
    # Deterministic facts and justifications
    risks: List[str]
    warnings: List[str]
    reasoning_points: List[str]
```

---

## 4. Business Rule Execution Sequence

```
                                  [Start Evaluation]
                                          │
                    1. Calculate Daily Demand Rate & Net Shortage
                       - Daily demand = Forecast Qty / Forecast Days
                       - Inventory Position = On-hand + Open POs
                       - Net Shortage = max(0, Forecast Qty - Inventory Position)
                                          │
                    2. Analyze Stockout Timeline vs. Open POs
                       - Days of coverage = On-hand / Daily demand
                       - Stockout date = Evaluation Date + Coverage Days
                       - Do open POs arrive before stockout date?
                                          │
             ┌────────────────────────────┴─────────────────────────────┐
             ▼                                                          ▼
  [Inventory Position >= Demand]                            [Net Shortage > 0]
             │                                                          │
  Check Stockout Gap Before Open PO:                        Check Supplier Feasibility:
  - If coverage runs out before open PO                     - Calculate MOQ-adjusted qty
    arrives -> INVESTIGATE (expedite PO)                    - Check budget constraints
  - If coverage covers until PO arrives                     - Check arrival vs. deadline
    -> REJECT (unnecessary order)                                       │
                                                    ┌───────────────────┴───────────────────┐
                                                    ▼                                       ▼
                                          [Feasible Options Exist]             [No Feasible Supplier]
                                                    │                                       │
                                     Does Recommendation match Preferred?       Can Open PO be expedited?
                                     - Same qty & supplier -> ACCEPT            - Yes -> INVESTIGATE
                                     - Different qty/supplier -> MODIFY         - No -> REJECT (Budget/Lead time)
```

### Detailed Decision Determination Rules:

1. **Rule 1 (Zero Net Shortage / Unnecessary Purchase)**:
   - If $I_{pos} \ge Q_{demand}$ and current stock covers demand until all open POs arrive:
   - **Decision**: `REJECT`.
   - **Reasoning**: Existing inventory and committed purchase orders fully cover the forecast period. Additional purchasing would cause excess holding cost.

2. **Rule 2 (Interim Stockout Before Open PO Arrives)**:
   - If total $I_{pos} \ge Q_{demand}$, BUT current stock runs out before the open PO's expected delivery date:
   - **Decision**: `INVESTIGATE`.
   - **Reasoning**: A stockout gap exists. The system recommends investigating whether the supplier for the existing PO can expedite or make a partial delivery before committing new capital.

3. **Rule 3 (Genuine Shortage & Feasible Supplier Exists)**:
   - If $S_{net} > 0$ and feasible supplier options exist within budget:
     - **Case 3A (Recommendation matches preferred option)**:
       If `recommended_quantity` equals preferred option quantity and `supplier_id` equals preferred supplier $\rightarrow$ **Decision**: `ACCEPT`.
     - **Case 3B (Recommendation differs in quantity or supplier)**:
       If `recommended_quantity` would cause stockout or create avoidable excess compared to preferred supplier $\rightarrow$ **Decision**: `MODIFY`.
       Sets `suggested_quantity = preferred_option.quantity` and `suggested_supplier_id = preferred_option.supplier_id`.

4. **Rule 4 (MOQ Handling & Excess Inventory)**:
   - If a supplier's MOQ exceeds $S_{net}$, the option is **not** discarded.
   - It is calculated with $Q = \text{MOQ}$, and the difference is documented as `excess_quantity`.
   - If storage capacity ($I_{on\_hand} + \text{MOQ} \le \text{StorageCapacity}$) and budget permit, it remains a feasible option with an explicit excess warning.

5. **Rule 5 (Lead Time Exceeds Stockout Date)**:
   - If no supplier's standard lead time can arrive before stockout date:
   - **Decision**: `INVESTIGATE`.
   - **Reasoning**: Standard procurement cannot prevent stockout. Buyer must investigate emergency air freight or alternative expedite terms.

6. **Rule 6 (Hard Budget Violation)**:
   - Any option where $\text{cost} > \text{remaining\_budget}$ is marked `is_budget_feasible = False`.
   - If all options exceed remaining budget:
   - **Decision**: `REJECT` (or `INVESTIGATE` if critical stockout requires budget escalation).
   - Generates hard budget warning.

---

## 5. Integration with Agent Orchestrator

The Agent Orchestrator (`backend/app/agent/`) acts as the workflow coordinator:

1. **Data Ingestion**:
   - Queries `PurchaseRecommendation` by ID.
   - Loads related `Product`, `Inventory`, active `DemandForecast`, open `PurchaseOrder`s, `SupplierProduct`s, and `PurchasingBudget`.
2. **Engine Invocation**:
   - Translates database records into an immutable `EngineInput` object.
   - Calls `evaluate_purchasing_decision(engine_input)`.
3. **LLM Context Synthesis**:
   - Packages the resulting `DecisionResult` (calculations, preferred option, risks, warnings) into a structured prompt for Gemini.
   - Prompt instructions: *"Explain this purchasing evaluation in professional business terms. Do not alter the calculations, decisions, or suggested values."*
4. **Evaluation Persistence**:
   - Calls the evaluation service / internal API:
     - `agent_decision = decision_result.decision`
     - `agent_suggested_quantity = decision_result.suggested_quantity`
     - `agent_suggested_supplier_id = decision_result.suggested_supplier_id`
     - `agent_reasoning = gemini_generated_explanation`
     - `evaluated_at = datetime.now(timezone.utc)`
   - Status remains `PENDING_APPROVAL` for human buyer review.

---

## 6. Focused Testing Strategy

Tests will be placed in `backend/tests/test_decision_engine.py` using realistic fixtures matching the business discovery document:

| # | Test Scenario | Fixture Conditions | Expected Output |
|---|---|---|---|
| 1 | **Inventory Sufficient** | Stock = 1000, Demand = 800, Rec = 500 | `REJECT`, suggested_quantity=0, reason="No net shortage" |
| 2 | **Stockout Before Open PO Arrives** | Stock = 300, Demand = 900 (14d), Open PO = 400 arriving Day 8 (stockout on Day 4.7) | `INVESTIGATE`, risk="Stockout gap of 3.3 days before PO arrival", prompt buyer to expedite PO |
| 3 | **Open PO Arrives Before Stockout** | Stock = 500, Demand = 900 (14d), Open PO = 400 arriving Day 3 (stockout on Day 7.7) | `REJECT`, position covers demand safely without interim gap |
| 4 | **Existing Supplier Delay / Alternate Faster** | Default supplier lead time = 10 days (too slow). Alternate supplier lead time = 3 days | `MODIFY`, switches to alternate supplier to avert stockout |
| 5 | **Alternate Supplier Higher MOQ** | Shortage = 150 units. Supplier MOQ = 200 units, budget ample | `MODIFY`, suggested_quantity = 200, notes 50 excess units |
| 6 | **Alternative Exceeds Available Budget** | Shortage cost = \$12,000, Remaining budget = \$10,000 | Marks option infeasible; flags budget breach |
| 7 | **No Feasible Supplier Alternative** | All suppliers lead times > stockout date and exceed budget | `INVESTIGATE` / `REJECT` with critical stockout warning |
| 8 | **Recommendation Accepted Directly** | Shortage = 500, Rec = 500, Default supplier lead time and MOQ match, budget ample | `ACCEPT`, suggested_quantity = 500, supplier unchanged |

---

## 7. Scope Constraints & Validation

- **No New Tables**: Works strictly with the existing 8 database entities.
- **Pure Python**: Standard library only (`dataclasses`, `datetime`, `decimal`, `typing`).
- **Explainability**: Every decision includes exact mathematical derivations (`inventory_position`, `days_of_coverage`, `net_shortage`).
- **No Architectural Conflicts**: Matches the existing `agent_decision` schema (`ACCEPT`, `MODIFY`, `REJECT`, `INVESTIGATE`) and immutability invariants.
