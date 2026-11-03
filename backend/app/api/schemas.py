from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class EvaluationRequest(BaseModel):
    agent_decision: Literal["ACCEPT", "MODIFY", "REJECT", "INVESTIGATE"]
    agent_suggested_quantity: Optional[int] = Field(default=None, ge=0)
    agent_suggested_supplier_id: Optional[int] = None
    agent_reasoning: Optional[str] = None
    evaluated_at: Optional[datetime] = None


class RecommendationCreateRequest(BaseModel):
    product_id: int = Field(gt=0, description="Product to purchase")
    supplier_id: Optional[int] = Field(default=None, description="Preferred supplier id")
    recommended_quantity: int = Field(gt=0, description="Quantity to purchase")
    requested_delivery_date: date = Field(description="Desired target delivery date")


class RecommendationUpdateRequest(BaseModel):
    recommended_quantity: Optional[int] = Field(default=None, gt=0, description="Updated quantity")
    supplier_id: Optional[int] = Field(default=None, description="Updated preferred supplier")
    requested_delivery_date: Optional[date] = Field(default=None, description="Updated delivery date")


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


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    recommended_quantity: int
    supplier_id: Optional[int] = None
    requested_delivery_date: date
    status: str

    agent_decision: Optional[str] = None
    agent_suggested_quantity: Optional[int] = None
    agent_suggested_supplier_id: Optional[int] = None
    agent_reasoning: Optional[str] = None
    evaluated_at: Optional[datetime] = None
