# AI Purchasing Agent

An autonomous, enterprise-grade AI purchasing agent for supply chain inventory risk evaluation, multi-supplier replenishment decisions, and human-in-the-loop procurement management.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
  - [1. Environment Configuration](#1-environment-configuration)
  - [2. Backend Setup](#2-backend-setup)
  - [3. Database Initialization & Seeding](#3-database-initialization--seeding)
  - [4. Frontend Setup](#4-frontend-setup)
- [Running the Application](#running-the-application)
- [Application URLs](#application-urls)
- [Buyer Workflow Walkthrough](#buyer-workflow-walkthrough)
- [Testing & Quality Verification](#testing--quality-verification)
- [Documentation Index](#documentation-index)

---

## Overview

The **AI Purchasing Agent** solves a critical enterprise supply chain problem: ensuring inventory replenishment decisions are mathematically rigorous, constrained by real-world warehouse and budgetary limits, and clearly communicated to procurement buyers.

The application adopts a **Dual-Core Architecture**:
1. **Deterministic Decision Authority**: A 100% deterministic Python calculation engine analyzes burn rates, simulates stock depletion day-by-day, evaluates supplier lead times and MOQs, and checks hard budget and storage constraints to produce a binding verdict (`ACCEPT`, `MODIFY`, `REJECT`, `INVESTIGATE`).
2. **AI Intelligence Synthesizer**: Google Gemini generates executive procurement briefings grounded strictly on the deterministic engine's mathematical evidence. If the API key is not configured or an outage occurs, the agent automatically falls back to deterministic rule-based reasoning points without downtime.
3. **Human-in-the-Loop Feedback & Audit**: Human buyers retain full approval control. Every evaluation run is permanently archived as an immutable snapshot in `EvaluationHistory`, and buyer parameter adjustments between runs are tracked and displayed as visual diffs.

---

## Key Features

- **Chronological Stockout Simulation**: Projects inventory depletion across demand periods, isolates interim stockouts from final unmet demand, and accounts for incoming purchase order arrivals.
- **Supplier Multi-Criteria Evaluation**: Evaluates lead-time viability, unit prices, and Minimum Order Quantity (MOQ) surfeits across primary and secondary vendors.
- **Hard Constraint Enforcement**: Validates available warehouse storage capacity and uncommitted purchasing budget before recommending orders.
- **Dual-Core Separation of Concerns**: LLM never decides purchase quantities or approval status; it only synthesizes strategic explanations from verified numbers.
- **Evaluation History & Diff Tracking**: Tracks changes made by the buyer (e.g. `Quantity: 500 → 200`, `Supplier: Acme → QuickParts`) between successive evaluation runs with an interactive timeline.
- **Human Approval Safeguards**: Strict status transition rules prevent unapproved orders from proceeding and prohibit modification of approved recommendations.

---

## System Architecture

```
[Angular 21 SPA] ──(HTTP/JSON)──► [FastAPI ASGI Backend]
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
     [Deterministic Decision Engine]                  [SQLite 3 Database]
     ├── Chronological Stockout Simulation            ├── Catalog & Inventory
     ├── Supplier Lead Time & MOQ Checks              ├── Recommendations
     └── Budget & Capacity Constraints                └── Immutable Evaluation History
                  │
                  ▼ (Verified Facts & Verdict)
     [Gemini AI Explainer] ──(Fallback)──► [Deterministic Reasoner]
```

For detailed architectural diagrams and layer breakdowns, see [`docs/architecture.md`](docs/architecture.md).

---

## Project Structure

```
purchasing-agent/
├── frontend/                               # Angular 21 SPA
│   ├── src/app/
│   │   ├── core/                           # Models & Recommendation HTTP Service
│   │   ├── features/
│   │   │   ├── dashboard/                  # Metrics cards & recommendation table
│   │   │   ├── recommendation-detail/      # Parameters, AI briefing & history timeline
│   │   │   └── recommendation-form/        # Create/Edit recommendation forms
│   │   └── shared/                         # Status & decision badges
│   └── package.json
├── backend/                                # FastAPI Backend
│   ├── app/
│   │   ├── agent/                          # AI Purchasing Agent (Gemini synthesis & fallback)
│   │   ├── api/                            # REST routers (recommendations, catalog, history)
│   │   ├── database/                       # SQLAlchemy 2.0 session & root path anchor
│   │   ├── decision_engine/                # Pure Python deterministic calculation engine
│   │   │   ├── engine.py                   # Verdict synthesis (ACCEPT, MODIFY, REJECT, INVESTIGATE)
│   │   │   ├── inventory.py                # Chronological inventory timeline simulation
│   │   │   ├── suppliers.py                # Lead time, MOQ, budget, & storage evaluation
│   │   │   ├── options.py                  # Multi-criteria alternative supplier ranking
│   │   │   └── types.py                    # Engine dataclasses & typed structures
│   │   ├── models/                         # Relational SQLite ORM models
│   │   └── main.py                         # FastAPI ASGI entrypoint & lifespan hook
│   ├── tests/                              # Pytest test suite (66 tests)
│   │   ├── evaluation/                     # Decision & explanation quality benchmark tests
│   │   │   ├── scenarios.json              # 8 curated benchmark scenarios (EV-001 - EV-008)
│   │   │   ├── test_decision_quality.py    # Automated decision quality validation
│   │   │   └── test_explanation_quality.py # Explanation fidelity & prompt compliance tests
│   │   └── ...                             # Unit & API integration tests
│   ├── requirements.txt                    # Backend Python dependencies
│   └── seed_data.py                        # Database reset and scenario seed script
├── docs/                                   # Architectural & operational documentation
│   ├── architecture.md                     # System architecture & layer specifications
│   ├── database-architecture-and-invariants.md # SQLite schema & persistence invariants
│   ├── evaluation-approach.md              # Quality evaluation methodology & scenario proofs
│   └── thinking-document.md                # System design & thought process
├── .env.example                            # Template environment configuration
└── README.md                               # Project documentation & runbook
```

---

## Prerequisites

Ensure you have the following installed on your system:

- **Python**: Version `3.10` or higher (tested with Python 3.14)
- **Node.js**: Version `18.x` or higher (tested with Node.js 20+ / npm 10+)
- **Git**: For version control
- *(Optional)* **Google Gemini API Key**: For AI executive briefings. If omitted, the agent operates in deterministic reasoning mode.

---

## Installation & Setup

### 1. Environment Configuration

Copy the example environment file to `.env` in the project root:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and set your Gemini API key (optional):

```ini
# Environment Configuration
GEMINI_API_KEY=your_gemini_api_key_here
PORT=8000
ENVIRONMENT=development
```

> **Note**: If `GEMINI_API_KEY` is left blank, the application runs normally and automatically uses deterministic rule-based reasoning points for all briefings.

---

### 2. Backend Setup

Create and activate a virtual environment, then install the Python dependencies:

#### Windows (PowerShell)
```powershell
# Create virtual environment (optional but recommended)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt
```

#### macOS / Linux
```bash
# Create virtual environment (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

---

### 3. Database Initialization & Seeding

Seed the SQLite database with realistic products, suppliers, inventory levels, demand forecasts, and purchasing recommendations:

#### Windows (PowerShell)
```powershell
$env:PYTHONPATH="backend"
python backend/seed_data.py
```

#### macOS / Linux
```bash
PYTHONPATH=backend python backend/seed_data.py
```

This populates `purchasing_agent.db` at the project root with baseline scenarios (e.g. excessive quantity, optimal order, stockout risk, and supplier MOQ challenges).

---

### 4. Frontend Setup

Navigate to the `frontend/` directory and install npm packages:

```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

To run the full stack locally, open two terminal windows:

### Terminal 1: Backend (FastAPI)

#### Windows (PowerShell)
```powershell
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### macOS / Linux
```bash
PYTHONPATH=backend python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend server starts at `http://127.0.0.1:8000`.

---

### Terminal 2: Frontend (Angular 21)

```bash
cd frontend
npx ng serve --port 4200
```

The Angular development server starts at `http://localhost:4200`.

---

## Application URLs

| Service | URL | Description |
|---|---|---|
| **Web Application** | [http://localhost:4200](http://localhost:4200) | Procurement Dashboard & Recommendation Management |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | FastAPI ASGI REST Service |
| **Interactive API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI for testing endpoints |
| **Alternative API Docs** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | ReDoc API specifications |
| **Health Check** | [http://localhost:8000/health](http://localhost:8000/health) | Service uptime check (`{"status":"ok"}`) |

---

## Buyer Workflow Walkthrough

1. **Dashboard**: Navigate to `http://localhost:4200` to review open recommendations, current approval statuses, and operational metrics.
2. **Review Recommendation**: Click **View** on any recommendation to see the split-view comparison between user-submitted parameters and the AI Purchasing Agent's analysis.
3. **Run AI Evaluation**: Click **Run Evaluation** to execute the deterministic decision engine and synthesize the executive briefing.
4. **Modify Parameters**: If the agent returns `MODIFY` (e.g., suggesting a lower quantity or alternative supplier), click **Edit Parameters**, update the quantity or supplier, and save.
5. **Re-evaluate & View History**: Click **Re-evaluate**. The system automatically computes buyer modification deltas (`previous → updated`), records a new chronological snapshot, and displays the changes in the **Evaluation History Timeline**.
6. **Approve**: Once satisfied with the parameters, click **Approve Recommendation** to finalize human approval.

---

## Testing & Quality Verification

### 1. Backend Test Suite

Run the full backend test suite (66 tests covering models, decision engine, APIs, approval flows, evaluation history, and quality benchmarks):

#### Windows (PowerShell)
```powershell
$env:PYTHONPATH="backend"
pytest backend/tests -v
```

#### macOS / Linux
```bash
PYTHONPATH=backend pytest backend/tests -v
```

### 2. Decision & Explanation Quality Benchmark

Run the isolated V1 evaluation dataset test suite:

```powershell
$env:PYTHONPATH="backend"
pytest backend/tests/evaluation/ -v
```

- **`test_decision_quality.py`**: Verifies that the engine reaches mathematically verified verdicts across all 8 standard scenarios (`EV-001` to `EV-008`).
- **`test_explanation_quality.py`**: Validates briefing prompt structure, 3-section formatting (*Strategic Assessment*, *Supply & Operational Analysis*, *Recommended Buyer Action Plan*), and grounded facts.

### 3. Frontend Unit Tests

Run the Angular unit test suite (Vitest):

```bash
cd frontend
npx ng test --no-watch
```

*(Runs 26 unit tests across components, services, and models with 100% pass rate).*

### 4. Frontend Production Build Check

Verify that the Angular project compiles cleanly for production:

```bash
cd frontend
npm run build
```

---

## Documentation Index

- [`docs/architecture.md`](docs/architecture.md): Complete system architecture, layer descriptions, Mermaid flowcharts, and sequence diagrams.
- [`docs/database-architecture-and-invariants.md`](docs/database-architecture-and-invariants.md): SQLite configuration, SQLAlchemy relational models, and transactional invariants.
- [`docs/evaluation-approach.md`](docs/evaluation-approach.md): Evaluation methodology, mathematical proof of scenarios EV-001 through EV-008, and limitation analysis.
- [`docs/thinking-document.md`](docs/thinking-document.md): Conceptual design thinking and rationale.
