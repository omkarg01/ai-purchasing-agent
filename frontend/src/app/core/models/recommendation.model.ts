export type AgentDecision = 'ACCEPT' | 'MODIFY' | 'REJECT' | 'INVESTIGATE';

export type RecommendationStatus = 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | string;

export interface RecommendationResponse {
  id: number;
  product_id: number;
  product_name?: string | null;
  product_sku?: string | null;
  recommended_quantity: number;
  supplier_id: number;
  supplier_name?: string | null;
  requested_delivery_date: string;
  status: RecommendationStatus;
  agent_decision: AgentDecision | null;
  agent_suggested_quantity: number | null;
  agent_suggested_supplier_id: number | null;
  agent_suggested_supplier_name?: string | null;
  agent_reasoning: string | null;
  evaluated_at: string | null;
}

export interface RecommendationCreatePayload {
  product_id: number;
  supplier_id?: number | null;
  recommended_quantity: number;
  requested_delivery_date: string;
}

export interface RecommendationUpdatePayload {
  recommended_quantity?: number;
  supplier_id?: number | null;
  requested_delivery_date?: string;
}

export interface ProductLookup {
  id: number;
  name: string;
  sku: string;
  description?: string | null;
}

export interface SupplierLookup {
  id: number;
  supplier_name: string;
}

export interface EvaluationPayload {
  agent_decision: AgentDecision;
  agent_suggested_quantity?: number | null;
  agent_suggested_supplier_id?: number | null;
  agent_reasoning?: string | null;
  evaluated_at?: string | null;
}
