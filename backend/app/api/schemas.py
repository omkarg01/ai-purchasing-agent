from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class EvaluationRequest(BaseModel):
    agent_decision: Literal["ACCEPT", "MODIFY", "REJECT", "INVESTIGATE"]
    agent_suggested_quantity: Optional[int] = Field(default=None, ge=0)
    agent_suggested_supplier_id: Optional[int] = None
    agent_reasoning: Optional[str] = None
    evaluated_at: Optional[datetime] = None


class ValueChange(BaseModel):
    previous: Any
    updated: Any
    previous_name: Optional[str] = None
    updated_name: Optional[str] = None


class BuyerModifications(BaseModel):
    quantity: Optional[ValueChange] = None
    supplier: Optional[ValueChange] = None
    split_allocation: Optional[ValueChange] = None


class EvaluationHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recommendation_id: int
    evaluation_sequence: int
    evaluated_quantity: int
    evaluated_supplier_id: Optional[int] = None
    evaluated_supplier_name: Optional[str] = None
    agent_decision: str
    explanation: Optional[str] = None
    calculations: Optional[Dict[str, Any]] = None
    risks: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    buyer_modifications: Optional[BuyerModifications] = None
    evaluated_at: datetime



class RecommendationCreateRequest(BaseModel):
    product_id: int = Field(gt=0, description="Product to purchase")
    supplier_id: Optional[int] = Field(default=None, description="Preferred supplier id")
    recommended_quantity: int = Field(gt=0, description="Quantity to purchase")
    requested_delivery_date: date = Field(description="Desired target delivery date")
    split_allocation: Optional[Dict[str, Any]] = Field(default=None, description="Optional multi-vendor split allocation")


class RecommendationUpdateRequest(BaseModel):
    recommended_quantity: Optional[int] = Field(default=None, gt=0, description="Updated quantity")
    supplier_id: Optional[int] = Field(default=None, description="Updated preferred supplier")
    requested_delivery_date: Optional[date] = Field(default=None, description="Updated delivery date")
    split_allocation: Optional[Dict[str, Any]] = Field(default=None, description="Updated multi-vendor split allocation")


class ProductLookupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    description: Optional[str] = None


class SupplierLookupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_name: str
    unit_price: Optional[float] = None
    lead_time_days: Optional[int] = None
    minimum_order_quantity: Optional[int] = None
    available_capacity: Optional[int] = None
    is_moq_negotiable: Optional[bool] = None
    expedited_lead_time_days: Optional[int] = None


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    recommended_quantity: int
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    requested_delivery_date: date
    status: str

    agent_decision: Optional[str] = None
    agent_suggested_quantity: Optional[int] = None
    agent_suggested_supplier_id: Optional[int] = None
    agent_suggested_supplier_name: Optional[str] = None
    agent_reasoning: Optional[str] = None
    evaluated_at: Optional[datetime] = None
    split_allocation: Optional[Dict[str, Any]] = None


class ApproveRequest(BaseModel):
    manager_override: bool = False
