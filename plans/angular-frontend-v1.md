# Plan: Angular Frontend for AI Purchasing Decision-Support System (Version 1)

## 1. Summary of Existing Frontend and Backend

### 1.1. Existing Frontend State
- **Directory**: `frontend/` (contains only `.gitkeep`).
- **Environment**: Node.js `v22.19.0`, npm `10.9.3`, Angular CLI `21.0.1`.
- **Target Architecture**: Standalone Angular 21 components with Signal-based state management, Angular Router, and pure CSS / Tailwind CSS for responsive enterprise design.

### 1.2. Existing Backend State
- **Framework**: FastAPI with SQLAlchemy 2.0 and SQLite.
- **Models** (`backend/app/models/`):
  - `Product`: `id`, `name`, `sku`, `description`.
  - `Inventory`: `id`, `product_id`, `available_quantity` (unreserved), `storage_capacity`.
  - `DemandForecast`: `id`, `product_id`, `forecast_quantity`, `period_start`, `period_end`.
  - `Supplier`: `id`, `supplier_name`.
  - `SupplierProduct`: `id`, `supplier_id`, `product_id`, `unit_price`, `lead_time_days`, `minimum_order_quantity`.
  - `PurchaseOrder`: `id`, `product_id`, `supplier_id`, `recommendation_id`, `quantity`, `unit_price`, `expected_delivery_date`, `status`.
  - `PurchasingBudget`: `id`, `total_budget`, `committed_amount`.
  - `PurchaseRecommendation`:
    - Original: `id`, `product_id`, `recommended_quantity`, `supplier_id`, `requested_delivery_date`, `status` (`PENDING`, `PENDING_APPROVAL`, `APPROVED`, etc.).
    - AI Evaluation: `agent_decision` (`ACCEPT`, `MODIFY`, `REJECT`, `INVESTIGATE`), `agent_suggested_quantity`, `agent_suggested_supplier_id`, `agent_reasoning`, `evaluated_at`.
- **Existing API Endpoints** (`backend/app/api/recommendations.py`):
  1. `GET /api/recommendations/{id}`: Returns `RecommendationResponse`.
  2. `POST /api/recommendations/{id}/evaluate`: Accepts `EvaluationRequest`, writes to `agent_*` fields, preserves original recommendation fields and `status`. Returns `RecommendationResponse`.
  3. `POST /api/recommendations/{id}/approve`: Transitions status from `PENDING_APPROVAL` to `APPROVED`. Returns `RecommendationResponse`.
  4. `GET /health`: Basic health check.
- **Decision Engine** (`backend/app/decision_engine/`):
  - Pure Python deterministic engine (`evaluate_purchasing_decision`).
  - Evaluates chronological daily demand, interim stockout gaps, supplier MOQ/pricing, dynamic storage capacity at arrival, and budget limits.

---

## 2. Recommended Version 1 User Journey

```
┌────────────────────────────────────────────────────────┐
│ 1. Purchasing Dashboard                                │
│    - Displays recommendation cards & status filters    │
│    - Highlights pending evaluations & approvals        │
└──────────────────────────┬─────────────────────────────┘
                           │ User selects a recommendation
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. Recommendation Details Screen                       │
│    - Displays original request (Product, Qty, Target)  │
│    - Shows inventory context & scheduled deliveries    │
└──────────────────────────┬─────────────────────────────┘
                           │ User clicks "Run AI Evaluation"
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. Evaluation In-Progress (Loading State)              │
│    - Deterministic engine calculation + AI synthesis   │
└──────────────────────────┬─────────────────────────────┘
                           │ Results rendered
                           ▼
┌────────────────────────────────────────────────────────┐
│ 4. Decision-Support Results Presentation               │
│    - Decision Banner: ACCEPT / MODIFY / REJECT / INVESTIGATE│
│    - Original vs. AI Suggested Quantity & Supplier     │
│    - Gemini-generated business explanation             │
│    - Key calculation metrics (coverage days, stockout) │
│    - Feasible supplier alternatives & trade-offs       │
└──────────────────────────┬─────────────────────────────┘
                           │ Human buyer review
                           ▼
┌────────────────────────────────────────────────────────┐
│ 5. Human Buyer Approval Action                         │
│    - "Approve Recommendation" (Enabled for PENDING_APPROVAL)│
│    - Success confirmation banner                       │
│    - Status updates to APPROVED                        │
└────────────────────────────────────────────────────────┘
```

---

## 3. Screen-by-Screen Breakdown

### Screen A: Purchasing Dashboard (`/dashboard`)
- **Purpose**: Overview of all purchasing recommendations requiring attention.
- **Key UI Elements**:
  - **KPI Summary Cards**: Total Recommendations, Pending Evaluation, Pending Approval, Approved.
  - **Recommendations Table**:
    - Columns: ID, Product, Requested Qty, Target Date, Workflow Status, Agent Decision, Actions.
    - Badges for Status (`PENDING_APPROVAL` in amber, `APPROVED` in green) and Decision (`ACCEPT` in green, `MODIFY` in blue, `INVESTIGATE` in purple, `REJECT` in red).
  - **Quick Action**: "Review & Evaluate" button linking to `/recommendations/:id`.

### Screen B: Recommendation Details & Context (`/recommendations/:id`)
- **Purpose**: Display original purchasing parameters alongside warehouse operational context.
- **Key UI Elements**:
  - **Header**: Breadcrumb navigation (`Dashboard > Recommendation #X`), current status badge, action bar.
  - **Original Request Card**:
    - Product ID / SKU.
    - Recommended Quantity.
    - Target Delivery Date.
    - Assigned Supplier.
  - **Action Panel**:
    - Primary Button: "Run AI Evaluation" (disabled if already evaluated or loading).
    - Approval Section: "Approve Recommendation" button (enabled only when status is `PENDING_APPROVAL`).

### Screen C: Evaluation Results Section (Embedded in `/recommendations/:id`)
- **Purpose**: Present deterministic calculations and AI-synthesized explanation for human decision-making.
- **Key UI Elements**:
  - **Decision Banner**: Large color-coded card indicating `ACCEPT`, `MODIFY`, `REJECT`, or `INVESTIGATE`.
  - **Side-by-Side Comparison**:
    | Parameter | Original Recommendation | Agent Suggested | Change / Rationale |
    |---|---|---|---|
    | **Quantity** | 500 units | 350 units | Reduced to match net shortage |
    | **Supplier** | Supplier #1 | Supplier #2 | Faster lead time prevents stockout |
  - **AI Business Reasoning Card**:
    - Displays `agent_reasoning` in structured markdown/prose.
    - Timestamp badge: "Evaluated at: [datetime]".
  - **Risk & Warning Indicators**:
    - Stockout alerts, storage capacity warnings, budget impact flags.

### Screen D: Human Approval State & Feedback
- **Purpose**: Facilitate explicit human governance.
- **Key UI Elements**:
  - Clear label: *"Human Review Required: The AI Purchasing Agent provides decision support. Purchasing commitment requires human authorization."*
  - **Approval Button**: Calls `POST /api/recommendations/{id}/approve`.
  - **Disabled States**: Disabled if status is already `APPROVED`, or not yet in `PENDING_APPROVAL`.
  - **Success Toast / State Banner**: Confirms status transition to `APPROVED` with audit record.

---

## 4. Proposed Angular Folder & Component Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── core/                           # Singleton services, interceptors, models
│   │   │   ├── models/
│   │   │   │   ├── recommendation.model.ts  # Backend API contracts (Request/Response)
│   │   │   │   └── decision-engine.model.ts # Engine calculation & option interfaces
│   │   │   ├── services/
│   │   │   │   └── recommendation.service.ts# HTTP client for recommendation endpoints
│   │   │   └── interceptors/
│   │   │       └── error.interceptor.ts     # Global HTTP error toast & status handling
│   │   │
│   │   ├── shared/                         # Reusable UI widgets & dumb components
│   │   │   ├── components/
│   │   │   │   ├── navbar/                 # Enterprise app header & navigation
│   │   │   │   ├── status-badge/           # Color-coded badge for Status & Agent Decision
│   │   │   │   ├── kpi-card/               # Dashboard metric summary card
│   │   │   │   ├── comparison-table/       # Side-by-side original vs. suggested values
│   │   │   │   └── empty-state/            # Visual feedback for empty tables/errors
│   │   │   └── pipes/
│   │   │       └── date-format.pipe.ts     # Consistent enterprise date formatting
│   │   │
│   │   ├── features/                       # Routed page modules (Smart components)
│   │   │   ├── dashboard/
│   │   │   │   ├── dashboard.component.ts  # Main recommendation table & KPI metrics
│   │   │   │   ├── dashboard.component.html
│   │   │   │   └── dashboard.component.css
│   │   │   │
│   │   │   └── recommendation-detail/
│   │   │       ├── recommendation-detail.component.ts # Detail view, evaluation, approval
│   │   │       ├── recommendation-detail.component.html
│   │   │       └── recommendation-detail.component.css
│   │   │
│   │   ├── app.component.ts                # Shell component with <router-outlet>
│   │   ├── app.config.ts                   # Standalone app configuration (Router, HttpClient)
│   │   └── app.routes.ts                   # Route definitions
│   │
│   ├── styles.css                          # Enterprise design tokens & base typography
│   └── index.html
├── angular.json
├── package.json
└── tsconfig.json
```

---

## 5. TypeScript Interfaces Matching Actual Backend Schemas

```typescript
// frontend/src/app/core/models/recommendation.model.ts

export type RecommendationStatus = 
  | 'PENDING'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | string;

export type AgentDecision = 
  | 'ACCEPT'
  | 'MODIFY'
  | 'REJECT'
  | 'INVESTIGATE';

/** Matches backend app.api.schemas.RecommendationResponse */
export interface RecommendationResponse {
  id: number;
  product_id: number;
  recommended_quantity: number;
  supplier_id: number | null;
  requested_delivery_date: string; // ISO date 'YYYY-MM-DD'
  status: RecommendationStatus;

  // Agent evaluation fields (nullable prior to evaluation)
  agent_decision: AgentDecision | null;
  agent_suggested_quantity: number | null;
  agent_suggested_supplier_id: number | null;
  agent_reasoning: string | null;
  evaluated_at: string | null;     // ISO datetime string
}

/** Matches backend app.api.schemas.EvaluationRequest */
export interface EvaluationRequest {
  agent_decision: AgentDecision;
  agent_suggested_quantity?: number | null;
  agent_suggested_supplier_id?: number | null;
  agent_reasoning?: string | null;
  evaluated_at?: string | null;
}

/** UI Dashboard aggregate metrics */
export interface DashboardMetrics {
  total: number;
  pendingApproval: number;
  approved: number;
  evaluatedCount: number;
}
```

---

## 6. API Integration Mapping

| Screen / Action | Target Endpoint | HTTP Method | Request Body / Params | Expected Response | Error Handling | Backend Status |
|---|---|---|---|---|---|---|
| **Health Check** | `/health` | `GET` | None | `{"status": "ok"}` | Service unavailable banner | **Supported** |
| **Fetch Recommendation** | `/api/recommendations/{id}` | `GET` | `id` (path) | `RecommendationResponse` | 404 $\rightarrow$ Show Not Found card | **Supported** |
| **Store Evaluation** | `/api/recommendations/{id}/evaluate` | `POST` | `EvaluationRequest` | `RecommendationResponse` | 400 (bad supplier), 422 (invalid schema) | **Supported** |
| **Approve Recommendation** | `/api/recommendations/{id}/approve` | `POST` | None | `RecommendationResponse` (`status: "APPROVED"`) | 400 (status $\ne$ `PENDING_APPROVAL`) | **Supported** |
| **List Recommendations** | `/api/recommendations` | `GET` | `?status=...` | `RecommendationResponse[]` | 500 error toast | **Gap (Backend Needs Endpoint)** |
| **Trigger Agent Evaluation** | `/api/recommendations/{id}/evaluate` (or orchestrator) | `POST` | Pre-calculated evaluation or orchestrator trigger | `RecommendationResponse` | 404 / 500 error toast | **Gap (Orchestrator Trigger API)** |

---

## 7. Component Responsibilities & State Management

### State Management: Angular Signals
- **Approach**: Lightweight, reactive, and built into Angular 21 (no external store library needed).
- **Service-Level Signals**:
  ```typescript
  @Injectable({ providedIn: 'root' })
  export class RecommendationService {
    private readonly http = inject(HttpClient);
    
    // Reactive signals
    readonly activeRecommendation = signal<RecommendationResponse | null>(null);
    readonly isLoading = signal<boolean>(false);
    readonly errorMessage = signal<string | null>(null);
    
    // Computed signals
    readonly isApproved = computed(() => this.activeRecommendation()?.status === 'APPROVED');
    readonly isPendingApproval = computed(() => this.activeRecommendation()?.status === 'PENDING_APPROVAL');
    readonly hasEvaluation = computed(() => this.activeRecommendation()?.agent_decision !== null);
  }
  ```

### Component Responsibilities:
1. **`DashboardComponent`**:
   - Manages list state, status filter tabs (`ALL`, `PENDING_APPROVAL`, `APPROVED`), and search.
   - Computes KPI card figures using `computed()` signals.
2. **`RecommendationDetailComponent`**:
   - Fetches active recommendation on route param change (`:id`).
   - Renders original parameters vs. agent suggestions.
   - Handles user action clicks ("Evaluate", "Approve").
3. **`StatusBadgeComponent`**:
   - Pure presentation component mapping status strings (`APPROVED`, `MODIFY`, etc.) to semantic colors and accessible labels.
4. **`ComparisonTableComponent`**:
   - Displays clean side-by-side delta between human recommendation and AI agent suggestion.

---

## 8. Implementation Milestones

```
Milestone 1: Project Setup & Core API Infrastructure  (FOUNDATION)
                      │
                      ▼
Milestone 2: Shared UI Kit & Design System
                      │
                      ▼
Milestone 3: Recommendation Detail & Evaluation Screen
                      │
                      ▼
Milestone 4: Human Approval Workflow Integration
                      │
                      ▼
Milestone 5: Dashboard Overview & KPI Metrics
                      │
                      ▼
Milestone 6: End-to-End Verification & Polish
```

- **Milestone 1: Project Setup & Core API Infrastructure**
  - Scaffold Angular 21 app in `frontend/`.
  - Configure `app.config.ts`, `HttpClient`, routing, proxy configuration (`/api` $\rightarrow$ `http://localhost:8000`).
  - Implement `RecommendationService` with TypeScript interfaces matching backend response schemas.
  
- **Milestone 2: Shared UI Kit & Design System**
  - Define enterprise color palette (neutral slates, semantic greens/blues/ambers/reds).
  - Create `NavbarComponent`, `StatusBadgeComponent`, and loading spinner/skeleton loaders.

- **Milestone 3: Recommendation Detail & Evaluation Screen**
  - Build `RecommendationDetailComponent` (`/recommendations/:id`).
  - Implement original recommendation panel and AI evaluation results presentation.
  - Implement evaluation trigger integration.

- **Milestone 4: Human Approval Workflow Integration**
  - Wire up `POST /api/recommendations/{id}/approve` with reactive button states and feedback toasts.
  - Test transitions: `PENDING_APPROVAL` $\rightarrow$ `APPROVED`.

- **Milestone 5: Dashboard Overview & KPI Metrics**
  - Build `DashboardComponent` (`/dashboard`).
  - Create KPI summary cards and sortable/filterable recommendation table.

- **Milestone 6: End-to-End Verification & Polish**
  - Verify complete workflow with backend running.
  - Add edge case handling (404 missing IDs, 400 invalid transitions).

---

## 9. Testing Strategy

1. **Unit Tests (Karma/Jasmine or Vitest)**:
   - `RecommendationService`: Test HTTP calls, error interceptors, and signal updates.
   - `StatusBadgeComponent`: Verify badge color classes for each decision and status.
   - `RecommendationDetailComponent`: Verify button enable/disable conditions based on `isPendingApproval`.
2. **Component Harness / Integration Tests**:
   - Test approval button click triggers `approveRecommendation()` and updates DOM state to `APPROVED`.
3. **End-to-End Smoke Test**:
   - Load dashboard $\rightarrow$ Navigate to detail $\rightarrow$ Review evaluation $\rightarrow$ Click approve $\rightarrow$ Verify status badge shows "APPROVED".

---

## 10. Backend Gaps & Decisions Requiring Clarification

| # | Gap / Question | Current Backend Behavior | Impact on Frontend | Proposed Clean Solution |
|---|---|---|---|---|
| **1** | **List Recommendations Endpoint** | Backend only has `GET /api/recommendations/{id}`. There is no `GET /api/recommendations` to list all records. | Dashboard cannot populate table dynamically from backend without calling individual IDs. | Add `GET /api/recommendations` to `backend/app/api/recommendations.py` returning `List[RecommendationResponse]`. Until added, frontend service can support a mock catalog or seed ID list. |
| **2** | **Evaluation Trigger Mechanism** | `POST /api/recommendations/{id}/evaluate` expects caller to pass `EvaluationRequest` payload. | Frontend button "Run AI Evaluation" needs an endpoint that runs the Decision Engine on the server. | Expose an endpoint like `POST /api/recommendations/{id}/run-evaluation` that executes the engine and Gemini server-side, or have the client call a service that executes this workflow. |
| **3** | **Product & Supplier Names in Response** | `RecommendationResponse` returns `product_id: int` and `supplier_id: int`. It does not include `product_name`, `sku`, or `supplier_name`. | Detail view will show "Product #1" instead of "Widget A (SKU: WIDGET-001)". | Either add optional `product_name`, `product_sku`, `supplier_name` to `RecommendationResponse`, or provide lightweight lookup endpoints. |
| **4** | **Rejection Endpoint** | Backend implements `POST /api/recommendations/{id}/approve`, but no reject endpoint exists yet. | User journey step 8 mentions "User approves or rejects the recommendation, where supported". | Disable or omit the Reject button for Version 1, explicitly showing that the backend currently supports approval. |

---

## Recommendation for First Frontend Milestone

### Recommended First Milestone: **Milestone 1 (Project Setup & Core API Infrastructure)**
#### Rationale:
1. **Establishes the Execution Runtime**: Scaffolds Angular 21, configures `HttpClient`, routing, and the development proxy to `http://localhost:8000`.
2. **Locks in Verified Contracts**: Directly implements the TypeScript interfaces against the actual backend schemas (`RecommendationResponse`, `EvaluationRequest`), ensuring compile-time safety from day one.
3. **Validates Connectivity Immediately**: Connects to the running FastAPI server (`GET /health` and `GET /api/recommendations/{id}`), verifying CORS and proxy routing before writing any UI views.
4. **Zero Throwaway Work**: Every interface and service method built in Milestone 1 directly powers all subsequent screens and components.
