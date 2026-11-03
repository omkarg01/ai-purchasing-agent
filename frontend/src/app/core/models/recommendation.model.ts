export type AgentDecision = 'ACCEPT' | 'MODIFY' | 'REJECT' | 'INVESTIGATE';

export type RecommendationStatus = 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | string;

export interface RecommendationResponse {
  id: number;
  product_id: number;
  recommended_quantity: number;
  supplier_id: number;
  requested_delivery_date: string;
  status: RecommendationStatus;
  agent_decision: AgentDecision | null;
  agent_suggested_quantity: number | null;
  agent_suggested_supplier_id: number | null;
  agent_reasoning: string | null;
  evaluated_at: string | null;
}

export interface EvaluationPayload {
  agent_decision: AgentDecision;
  agent_suggested_quantity?: number | null;
  agent_suggested_supplier_id?: number | null;
  agent_reasoning?: string | null;
  evaluated_at?: string | null;
}

