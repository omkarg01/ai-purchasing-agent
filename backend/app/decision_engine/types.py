from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional


@dataclass(frozen=True)
class InventoryInput:
    """Current warehouse inventory state for the product."""
    available_quantity: int       # Immediately available unreserved on-hand stock
    storage_capacity: int         # Maximum warehouse capacity in units


@dataclass(frozen=True)
class DemandForecastInput:
    """Projected demand across a specified time period."""
    forecast_quantity: int        # Total projected demand units
    period_start: date
    period_end: date


@dataclass(frozen=True)
class OpenPurchaseOrderInput:
    """Committed or active incoming purchase order."""
    id: int
    supplier_id: int
    quantity: int
    unit_price: Decimal
    expected_delivery_date: date
    status: str = "OPEN"
    supplier_name: Optional[str] = None


@dataclass(frozen=True)
class SupplierProductInput:
    """Supplier catalog terms for the product."""
    supplier_id: int
    supplier_name: str
    unit_price: Decimal
    lead_time_days: int
    minimum_order_quantity: int


@dataclass(frozen=True)
class BudgetInput:
    """Purchasing budget state."""
    total_budget: Decimal
    committed_amount: Decimal

    @property
    def remaining_budget(self) -> Decimal:
        return self.total_budget - self.committed_amount


@dataclass(frozen=True)
class RecommendationToEvaluate:
    """The incoming recommendation under evaluation."""
    id: int
    product_id: int
    recommended_quantity: int
    supplier_id: Optional[int]
    requested_delivery_date: date
    status: str = "PENDING_APPROVAL"


@dataclass(frozen=True)
class EngineInput:
    """Complete input contract for decision engine evaluation."""
    evaluation_date: date
    recommendation: RecommendationToEvaluate
    inventory: InventoryInput
    forecast: DemandForecastInput
    open_orders: List[OpenPurchaseOrderInput]
    suppliers: List[SupplierProductInput]
    budget: BudgetInput


@dataclass(frozen=True)
class StockoutTimelineAnalysis:
    """Detailed chronological inventory trajectory analysis.
    
    Distinguishes interim stockout, final unmet demand, and additional
    purchasing requirements as separate metrics.
    """
    daily_demand: float
    days_of_initial_coverage: float
    stockout_date: Optional[date]
    has_interim_stockout: bool
    interim_stockout_days: int
    interim_shortage_quantity: int
    final_projected_inventory: int
    final_unmet_demand: int
    additional_purchasing_requirement: int


@dataclass(frozen=True)
class PurchasingOption:
    """Evaluated purchasing alternative from a supplier."""
    supplier_id: int
    supplier_name: str
    quantity: int
    unit_price: float
    total_cost: float
    lead_time_days: int
    estimated_delivery_date: date
    excess_quantity: int
    projected_stock_at_arrival: int
    is_timing_feasible: bool
    is_budget_feasible: bool
    is_storage_feasible: bool
    trade_offs: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class InvestigationOption:
    """Actionable negotiation or expediting pathway for human buyer review.
    
    Tagged with is_confirmed=False since external negotiations are not assumed.
    """
    pathway_type: Literal["EXISTING_SUPPLIER_EXPEDITE", "ALTERNATIVE_SUPPLIER_EMERGENCY"]
    description: str
    target_supplier_id: Optional[int]
    target_supplier_name: Optional[str]
    required_delivery_date: date
    potential_quantity: int
    action_required_by_buyer: str
    is_confirmed: bool = False


@dataclass(frozen=True)
class DecisionResult:
    """Structured deterministic outcome of the purchasing evaluation."""
    decision: Literal["ACCEPT", "MODIFY", "REJECT", "INVESTIGATE"]
    suggested_quantity: Optional[int]
    suggested_supplier_id: Optional[int]
    preferred_option: Optional[PurchasingOption]
    feasible_options: List[PurchasingOption]
    investigation_options: List[InvestigationOption]
    calculations: Dict[str, Any]
    risks: List[str]
    warnings: List[str]
    reasoning_points: List[str]

