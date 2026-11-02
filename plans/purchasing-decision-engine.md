# Implementation Plan: Purchasing Decision Engine

## 1. Overview & Architectural Role

The **Purchasing Decision Engine** is a deterministic, modular calculation module residing in `backend/app/decision_engine/`. It evaluates purchasing recommendations against business data: on-hand inventory levels, daily burn rates, chronological incoming purchase order arrivals, supplier commercial terms (unit price, lead time, MOQ), storage capacity, and remaining purchasing budget.

### Key Architectural Boundaries
- **Decision-Support Only**: The engine assists human buyers with structured evaluation; it never autonomously places orders, updates budgets, or negotiates with vendors.
- **Pure & Deterministic**: Functions are pure Python calculations without direct database queries, HTTP dependencies, or ORM coupling.
- **LLM Decoupled**: The engine does **not** call Gemini or generate natural language prose. It produces structured data (facts, numbers, risks, trade-offs) that the Agent Orchestrator delivers to Gemini for explanation generation.
- **Data Model Grounding**: All calculations strictly operate on the existing 8 database entities. No new database tables or synthetic fields (such as external supplier stock availability) are introduced.

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
│  │ Date-Aware Timeline     │ │ Stockout Gap & Timing│  │
│  │ Inventory Calculations  │ │ Analysis             │  │
│  └─────────────────────────┘ └──────────────────────┘  │
│  ┌─────────────────────────┐ ┌──────────────────────┐  │
│  │ Supplier Evaluation     │ │ Dynamic Storage &    │  │
│  │ (Price, Lead time, MOQ) │ │ Budget Validation    │  │
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
├── types.py              # Pure Python dataclass input & output contracts
├── inventory.py          # Date-aware chronological stockout & timeline calculations
├── suppliers.py          # Supplier feasibility (price, lead time, MOQ) & storage checks
├── options.py            # Feasible purchasing and investigation options generation
└── engine.py             # Main entry point and deterministic decision rule engine
```

### 2.1. Responsibilities and Function Signatures

#### A. Module: `inventory.py` (Date-Aware Inventory Calculations)
Total on-order inventory is **not** treated as immediately available stock. The module chronologically models daily stock depletion against expected PO arrival dates.

1. **`calculate_daily_demand(forecast: DemandForecastInput) -> float`**
   - **Responsibility**: Computes average daily consumption rate over the forecast horizon:
     $$D_{daily} = \frac{Q_{forecast}}{\max(1, (T_{end} - T_{start}).\text{days})}$$
   - **Inputs**: `DemandForecastInput`.
   - **Outputs**: `float` (daily burn rate in units/day).

2. **`analyze_chronological_stockout_timeline(on_hand: int, daily_demand: float, open_orders: List[OpenPurchaseOrderInput], horizon_start: date, horizon_end: date) -> StockoutTimelineAnalysis`**
   - **Responsibility**: Simulates day-by-day inventory trajectory from `horizon_start` to `horizon_end`:
     - Initial stock on Day 0 is strictly `on_hand`.
     - Stock depletes daily by $D_{daily}$.
     - When an open PO reaches its `expected_delivery_date`, on-hand stock is replenished by that PO's quantity.
     - Identifies:
       - **Days of Initial Coverage**: How long initial on-hand stock lasts before any PO arrives ($I_{on\_hand} / D_{daily}$).
       - **Interim Stockout Period**: Dates when stock drops to $\le 0$ before an incoming PO arrives.
       - **Cumulative Net Shortage at Horizon End**: Final unfulfilled demand after all scheduled POs arrive.
   - **Inputs**: Current unreserved on-hand stock, daily demand rate, list of open POs, evaluation horizon dates.
   - **Outputs**: `StockoutTimelineAnalysis(days_of_initial_coverage, stockout_date, has_interim_stockout, interim_stockout_days, final_projected_inventory, net_shortage)`.

#### B. Module: `suppliers.py` (Supplier Evaluation & Dynamic Storage Validation)
Evaluates suppliers strictly within current data boundaries (`unit_price`, `lead_time_days`, `minimum_order_quantity`). **Does not assume external supplier stock availability**, as this is not in the data model.

3. **`validate_projected_storage_capacity(on_hand: int, daily_demand: float, open_orders: List[OpenPurchaseOrderInput], proposed_quantity: int, proposed_arrival_date: date, storage_capacity: int, evaluation_date: date) -> Tuple[bool, int]`**
   - **Responsibility**: Calculates projected warehouse stock around the proposed order's delivery date:
     $$\text{Projected Stock at Arrival} = \max\left(0, I_{on\_hand} - (\text{Days to Arrival} \times D_{daily})\right) + \sum_{T_{PO} \le T_{arrival}} Q_{PO} + Q_{proposed}$$
     Verifies whether $\text{Projected Stock at Arrival} \le \text{StorageCapacity}$.
   - **Inputs**: On-hand stock, daily demand, scheduled open POs, proposed quantity, arrival date, warehouse storage capacity, evaluation date.
   - **Outputs**: `Tuple[is_storage_feasible: bool, projected_stock_at_arrival: int]`.

4. **`evaluate_supplier_product(supplier_prod: SupplierProductInput, net_shortage: int, remaining_budget: Decimal, storage_capacity: int, on_hand: int, daily_demand: float, open_orders: List[OpenPurchaseOrderInput], evaluation_date: date, target_delivery_date: date) -> EvaluatedSupplierOption`**
   - **Responsibility**: Evaluates a supplier against commercial terms and physical constraints:
     - Order quantity adjusted to satisfy supplier MOQ: $Q_{order} = \max(\text{net\_shortage}, \text{MOQ})$.
     - Order cost: $C_{order} = Q_{order} \times \text{unit\_price}$.
     - Estimated delivery date: $\text{arrival\_date} = \text{evaluation\_date} + \text{lead\_time\_days}$.
     - Hard budget constraint check: $C_{order} \le \text{remaining\_budget}$.
     - Dynamic storage validation using `validate_projected_storage_capacity`.
     - Timing feasibility: $\text{arrival\_date} \le \text{target\_delivery_date}$.
     - Identifies trade-offs: excess units ($Q_{order} - \text{net\_shortage}$), additional capital required.
   - **Inputs**: Supplier product data, net shortage units, available budget, warehouse capacity, on-hand stock, daily demand, open POs, evaluation date, target date.
   - **Outputs**: `EvaluatedSupplierOption`.

#### C. Module: `options.py` (Option Generation & Investigation Pathways)
5. **`generate_purchasing_options(suppliers: List[SupplierProductInput], net_shortage: int, remaining_budget: Decimal, storage_capacity: int, on_hand: int, daily_demand: float, open_orders: List[OpenPurchaseOrderInput], evaluation_date: date, target_date: date) -> List[EvaluatedSupplierOption]`**
   - **Responsibility**: Evaluates all catalog suppliers. Retains feasible options within budget and storage, even if MOQ creates excess inventory, clearly annotating excess quantity and cost trade-offs.

6. **`generate_investigation_pathways(timeline: StockoutTimelineAnalysis, open_orders: List[OpenPurchaseOrderInput], suppliers: List[SupplierProductInput], evaluation_date: date) -> List[InvestigationOption]`**
   - **Responsibility**: When an interim stockout or delivery delay is identified, generates actionable investigation paths for human buyer review:
     - **Existing Supplier Expedite/Split**: If an open PO exists with delivery after stockout, identifies an option to negotiate earlier or partial delivery with the existing vendor.
     - **Alternative Fast Supplier**: Evaluates alternate catalog suppliers whose lead times beat the stockout date.
     - **Constraint Disclaimer**: Clearly tags all pathways with `is_confirmed = False`, indicating that supplier negotiation is required and must be conducted by the human buyer.

7. **`rank_preferred_option(feasible_options: List[EvaluatedSupplierOption], target_date: date) -> Tuple[Optional[EvaluatedSupplierOption], List[str]]`**
   - **Responsibility**: Selects the best option using deterministic multi-criteria ranking:
     1. Delivery on or before target stockout date.
     2. Lowest total purchase cost.
     3. Minimal excess inventory above shortage.

#### D. Module: `engine.py` (Decision Engine Entry Point)
8. **`evaluate_purchasing_decision(input_data: EngineInput) -> DecisionResult`**
   - **Responsibility**: Top-level coordinator executing calculations and applying deterministic business rules to yield `ACCEPT`, `MODIFY`, `REJECT`, or `INVESTIGATE`.

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
    available_quantity: int       # Unreserved on-hand stock immediately available
    storage_capacity: int         # Maximum warehouse units

@dataclass(frozen=True)
class DemandForecastInput:
    forecast_quantity: int        # Forecasted units
    period_start: date
    period_end: date

@dataclass(frozen=True)
class OpenPurchaseOrderInput:
    id: int
    supplier_id: int
    supplier_name: Optional[str]
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
    projected_stock_at_arrival: int
    is_timing_feasible: bool
    is_budget_feasible: bool
    is_storage_feasible: bool
    trade_offs: List[str]

@dataclass(frozen=True)
class InvestigationOption:
    pathway_type: Literal["EXISTING_SUPPLIER_EXPEDITE", "ALTERNATIVE_SUPPLIER_EMERGENCY"]
    description: str
    target_supplier_id: int
    target_supplier_name: str
    required_delivery_date: str
    potential_quantity: int
    action_required_by_buyer: str
    is_confirmed: bool = False   # Always False: human negotiation required

@dataclass(frozen=True)
class DecisionResult:
    decision: Literal["ACCEPT", "MODIFY", "REJECT", "INVESTIGATE"]
    suggested_quantity: Optional[int]
    suggested_supplier_id: Optional[int]
    preferred_option: Optional[PurchasingOption]
    feasible_options: List[PurchasingOption]
    investigation_options: List[InvestigationOption]
    
    # Chronological quantitative calculations for transparency
    calculations: Dict[str, Any]
    # - daily_burn_rate
    # - days_of_initial_coverage
    # - estimated_stockout_date
    # - has_interim_stockout
    # - interim_stockout_days
    # - net_shortage_at_horizon_end
    # - projected_stock_at_arrival
    
    # Factual justifications and risks
    risks: List[str]
    warnings: List[str]
    reasoning_points: List[str]
```

---

## 4. Business Rule Execution Sequence

```
                                  [Start Evaluation]
                                          │
               1. Date-Aware Timeline & Chronological Stockout Analysis
                  - Daily Demand Rate = Forecast Qty / Horizon Days
                  - Model daily inventory curve: On-hand - (Day * Burn Rate)
                  - Add incoming PO quantities on their respective delivery dates
                  - Identify:
                    a) Initial stockout date (when on-hand runs out)
                    b) Interim stockout gap (days depleted before PO arrives)
                    c) Net shortage at horizon end
                                          │
         ┌────────────────────────────────┴─────────────────────────────────┐
         ▼                                                                  ▼
 [Interim Stockout Detected Before PO Arrives]              [No Interim Stockout / Continuous Supply]
         │                                                                  │
 Generate Investigation Pathways:                           Evaluate Net Shortage at Horizon End:
 - Existing supplier: negotiate earlier/partial PO delivery  - If Net Shortage == 0:
 - Alternate suppliers: emergency fast delivery               -> REJECT (purchase is redundant; causes excess)
 - Mark unconfirmed (buyer action needed)                   - If Net Shortage > 0:
 -> Decision: INVESTIGATE                                     -> Proceed to Supplier Evaluation
                                                                            │
                                                                            ▼
                                                            2. Supplier Feasibility & Storage Validation
                                                               - Adjust quantity to max(Shortage, MOQ)
                                                               - Calculate Cost = Qty * Unit Price
                                                               - Dynamic Storage Check at arrival date
                                                               - Hard Budget Check (Cost <= Remaining Budget)
                                                               - Arrival Timing Check (Arrival <= Target Date)
                                                                            │
                                                       ┌────────────────────┴────────────────────┐
                                                       ▼                                         ▼
                                             [Feasible Options Exist]                  [No Feasible Supplier]
                                                       │                                         │
                                       Does Recommendation match Preferred?           Check Budget / Lead Time:
                                       - Same Qty, Supplier, Feasible -> ACCEPT        - If all over budget -> REJECT
                                       - Different Qty or Supplier   -> MODIFY        - If timing gap      -> INVESTIGATE
```

### Detailed Decision Logic & Rules:

1. **Rule 1: Chronological Stockout Gap Investigation (`INVESTIGATE`)**:
   - Even if total on-hand + on-order inventory covers total forecast demand, if on-hand stock runs out *before* an incoming PO arrives, an interim stockout occurs.
   - **Action**: Generates `InvestigationOption` for the human buyer:
     - Negotiate with existing supplier to expedite or deliver partial quantity before the stockout date.
     - Evaluate alternative suppliers with short lead times for an emergency bridge batch.
   - **Decision**: `INVESTIGATE`. Flags that negotiations are unconfirmed.

2. **Rule 2: Zero Net Shortage / Redundant Purchase (`REJECT`)**:
   - If initial on-hand stock covers demand until all scheduled POs arrive, and total inventory position meets or exceeds total forecast demand:
   - **Decision**: `REJECT`.
   - **Reasoning**: All demand is covered by current stock and committed orders. Purchasing creates redundant inventory and ties up capital.

3. **Rule 3: Genuine Shortage with Feasible Supplier (`ACCEPT` vs. `MODIFY`)**:
   - When a net shortage exists ($S_{net} > 0$) and feasible suppliers exist:
     - **Case 3A (Recommendation matches preferred option)**:
       If `recommended_quantity == preferred_option.quantity` and `supplier_id == preferred_option.supplier_id` without constraint violations $\rightarrow$ `ACCEPT`.
     - **Case 3B (Recommendation quantity or supplier requires adjustment)**:
       If recommendation differs from preferred option (e.g. recommended quantity was excessive, or another supplier provides faster delivery/lower cost within constraints) $\rightarrow$ `MODIFY`.
       Sets `suggested_quantity = preferred_option.quantity` and `suggested_supplier_id = preferred_option.supplier_id`.

4. **Rule 4: Supplier MOQ & Excess Inventory Handling**:
   - If supplier MOQ exceeds net shortage, the option is **not** discarded.
   - The engine sets order quantity to MOQ, calculates cost, and dynamically validates warehouse storage capacity at arrival date.
   - If storage and budget permit, it remains a feasible option with an explicit `excess_quantity` trade-off warning.

5. **Rule 5: Dynamic Storage Capacity Validation**:
   - Evaluates:
     $$\text{Projected Inventory at Arrival} = \max(0, I_{on\_hand} - (\text{Days to Arrival} \times D_{daily})) + \sum_{T_{PO} \le T_{arrival}} Q_{PO} + Q_{proposed}$$
   - If $\text{Projected Inventory at Arrival} > \text{StorageCapacity}$, the option is marked `is_storage_feasible = False` and rejected or flagged with a warehouse overflow risk.

6. **Rule 6: Hard Budget Constraints**:
   - If order cost exceeds `remaining_budget`, the option is marked `is_budget_feasible = False`.
   - If all options exceed budget:
     - If stockout is critical $\rightarrow$ `INVESTIGATE` (with budget escalation request).
     - Otherwise $\rightarrow$ `REJECT` (budget exceeded).

---

## 5. Integration with Agent Orchestrator

The Agent Orchestrator (`backend/app/agent/`) coordinates the workflow:

1. **DB Ingestion**: Loads database entities (`Product`, `Inventory`, `DemandForecast`, open `PurchaseOrder`s, `SupplierProduct`s, `PurchasingBudget`, `PurchaseRecommendation`).
2. **Contract Construction**: Maps database entities to pure Python `EngineInput`.
3. **Engine Call**: Executes `evaluate_purchasing_decision(engine_input)` synchronously.
4. **Gemini Synthesis**: Sends `DecisionResult` to Gemini:
   - System instruction: *"Explain these exact calculation results and options in business terms. Do not modify numbers, decisions, or suggested quantities."*
5. **Persistence**: Writes evaluation results to `POST /api/recommendations/{id}/evaluate` (`agent_decision`, `agent_suggested_*`, `agent_reasoning`, `evaluated_at`). Status remains `PENDING_APPROVAL`.

---

## 6. Focused Testing Strategy

Test suite in `backend/tests/test_decision_engine.py`:

| # | Test Scenario | Fixture Conditions | Expected Output |
|---|---|---|---|
| 1 | **Inventory Sufficient** | On-hand = 1000, Demand = 800 (14d), Rec = 500 | `REJECT`, suggested_quantity=0, reason="Inventory covers demand" |
| 2 | **Stockout Before Open PO Arrives** | On-hand = 300, Demand = 900 (14d; 64.3/d), PO = 400 arriving Day 8 (stockout Day 4.7) | `INVESTIGATE`, detects 3.3 day stockout gap; generates unconfirmed existing supplier expedite pathway |
| 3 | **Open PO Arrives Before Stockout** | On-hand = 500, Demand = 900 (14d; 64.3/d), PO = 400 arriving Day 4 (stockout Day 7.7) | `REJECT`, incoming PO arrives before depletion; no gap |
| 4 | **Existing Supplier Delivery Delay** | Default supplier lead time = 10 days (misses stockout). Alternate supplier lead time = 3 days | `MODIFY`, selects alternate supplier to prevent stockout |
| 5 | **Alternate Supplier Higher MOQ** | Shortage = 150 units. Supplier MOQ = 200 units, budget & storage ample | `MODIFY`, suggested_quantity = 200, notes 50 excess units |
| 6 | **Alternative Exceeding Budget** | Shortage cost = \$12,000, Remaining budget = \$10,000 | Infeasible budget; flags budget warning |
| 7 | **Dynamic Storage Overflow** | Shortage = 300, Storage Capacity = 500, On-hand at arrival = 300 | Infeasible storage; flags warehouse capacity overflow |
| 8 | **Recommendation Accepted Directly** | Shortage = 500, Rec = 500, Supplier lead time, MOQ, budget, storage match | `ACCEPT`, suggested_quantity = 500, supplier unchanged |

---

## 7. Scope Constraints & Validation

- **No New Tables or Fields**: Operates strictly within the 8 existing models. No supplier stock availability is assumed or simulated.
- **Pure Python**: Zero external dependencies beyond standard library (`dataclasses`, `datetime`, `decimal`, `typing`).
- **Human Authority Preserved**: Investigation options explicitly state that supplier expedite negotiations must be conducted and confirmed by the human buyer.
