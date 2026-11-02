# Plan: Human Approval API for Purchasing Recommendations

## 1. Objective & Context
Implement the human buyer approval endpoint (`POST /api/recommendations/{id}/approve`) for purchasing recommendations that have undergone AI agent evaluation.

The AI agent proposes decisions and suggested changes in `agent_*` fields without self-approving. A human buyer reviews the recommendation and explicitly triggers approval.

---

## 2. Scope & Boundaries
- **In Scope:**
  - Endpoint: `POST /api/recommendations/{recommendation_id}/approve` (also exposed as `POST /recommendations/{recommendation_id}/approve`).
  - Validation: Verify recommendation exists (404) and current status is `PENDING_APPROVAL` (400 if invalid transition).
  - Status mutation: Update `status` to `APPROVED`.
  - Preservation: Keep all original recommendation fields and AI evaluation fields intact.
  - Return: Structured `RecommendationResponse`.
- **Out of Scope (Explicitly Excluded):**
  - Purchase order creation.
  - Budget updates or balance adjustments.
  - Supplier integrations or messaging.
  - Autonomous purchasing execution.

---

## 3. Implementation Steps
1. **API Endpoint (`backend/app/api/recommendations.py`):**
   - Add `@router.post("/{recommendation_id}/approve", response_model=RecommendationResponse)`.
   - Query `PurchaseRecommendation` by ID; raise `HTTPException(404)` if missing.
   - Guard against invalid status transitions: if `status != "PENDING_APPROVAL"`, raise `HTTPException(400)`.
   - Set `recommendation.status = "APPROVED"`.
   - Ensure original fields (`recommended_quantity`, `supplier_id`) and AI evaluation fields (`agent_decision`, `agent_suggested_*`, `agent_reasoning`, `evaluated_at`) are untouched.
   - Commit transaction and refresh instance.
2. **Tests (`backend/tests/test_approval_api.py`):**
   - Test successful approval from `PENDING_APPROVAL` to `APPROVED`.
   - Test 404 error when recommendation does not exist.
   - Test 400 error when attempting approval from `PENDING` (unevaluated).
   - Test 400 error when attempting approval on already `APPROVED` recommendation.
   - Test 400 error when attempting approval on `REJECTED` recommendation.
   - Test preservation of all original and AI fields upon approval.
3. **Documentation:**
   - Update `docs/architecture-and-decisions.md` with approval workflow specification.

