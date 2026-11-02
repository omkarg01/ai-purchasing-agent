from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class EvaluationRequest(BaseModel):
    agent_decision: Literal["ACCEPT", "MODIFY", "REJECT", "INVESTIGATE"]
    agent_suggested_quantity: Optional[int] = Field(default=None, ge=0)
    agent_suggested_supplier_id: Optional[int] = None
    agent_reasoning: Optional[str] = None
    evaluated_at: Optional[datetime] = None


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
