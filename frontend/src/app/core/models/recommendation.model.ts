export type AgentDecision = 'ACCEPT' | 'MODIFY' | 'REJECT' | 'INVESTIGATE';

export type RecommendationStatus = 'PENDING_APPROVAL' | 'APPROVED' | 'REJECTED' | string;

export interface SplitAllocation {
  primary_supplier_id: number;
  primary_supplier_name?: string | null;
  primary_quantity: number;
  primary_unit_price?: number | null;
  primary_cost?: number | null;
  secondary_supplier_id: number;
  secondary_supplier_name?: string | null;
  secondary_quantity: number;
  secondary_unit_price?: number | null;
  secondary_cost?: number | null;
  total_cost?: number | null;
}

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
  split_allocation?: SplitAllocation | null;
}

export interface RecommendationCreatePayload {
  product_id: number;
  supplier_id?: number | null;
  recommended_quantity: number;
  requested_delivery_date: string;
  split_allocation?: SplitAllocation | null;
}

export interface RecommendationUpdatePayload {
  recommended_quantity?: number;
  supplier_id?: number | null;
  requested_delivery_date?: string;
  split_allocation?: SplitAllocation | null;
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

export interface ValueChange<T = any> {
  previous: T;
  updated: T;
  previous_name?: string | null;
  updated_name?: string | null;
}

export interface BuyerModifications {
  quantity?: ValueChange<number>;
  supplier?: ValueChange<number>;
  split_allocation?: ValueChange<any>;
}

export interface EvaluationHistoryItem {
  id: number;
  recommendation_id: number;
  evaluation_sequence: number;
  evaluated_quantity: number;
  evaluated_supplier_id?: number | null;
  evaluated_supplier_name?: string | null;
  agent_decision: AgentDecision;
  explanation?: string | null;
  calculations?: Record<string, any> | null;
  risks?: string[] | null;
  warnings?: string[] | null;
  buyer_modifications?: BuyerModifications | null;
  evaluated_at: string;
}
