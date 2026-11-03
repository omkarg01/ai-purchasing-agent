from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional


@dataclass(frozen=True)
class PriceTier:
    """Volume discount pricing tier for a supplier product."""
    min_quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class SplitOrderAllocation:
    """Multi-vendor order split allocation when single supplier capacity is capped."""
    primary_supplier_id: int
    primary_supplier_name: str
    primary_quantity: int
    primary_unit_price: float
    primary_cost: float
    secondary_supplier_id: int
    secondary_supplier_name: str
    secondary_quantity: int
    secondary_unit_price: float
    secondary_cost: float
    total_cost: float


@dataclass(frozen=True)
class InventoryInput:
    """Current warehouse inventory state for the product."""
    available_quantity: int                   # Immediately available unreserved on-hand stock
    storage_capacity: int                     # Maximum warehouse capacity in units
    safety_stock_quantity: int = 0            # Desired safety buffer units (Rule 1)
    facility_available_m3: Optional[float] = None  # Aggregate facility storage in m3 (Rule 4)


@dataclass(frozen=True)
class DemandForecastInput:
    """Projected demand across a specified time period."""
    forecast_quantity: int                    # Total projected demand units
    period_start: date
    period_end: date
    daily_demand_series: Optional[List[int]] = None  # Optional discrete daily demand curve (FM-4)


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
    available_capacity: Optional[int] = None         # Maximum supplier order capacity (Rule 3)
    historical_delay_days: int = 0                   # Supplier OTIF lead-time delay variance (Rule 5)
    price_tiers: Optional[List[PriceTier]] = None     # Bulk volume discount tiers (Rule 6)
    is_moq_negotiable: bool = True                   # Whether vendor is open to MOQ adjustments
    expedited_lead_time_days: Optional[int] = None   # Vendor emergency rush lead time if available


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
    shelf_life_days: Optional[int] = None            # Product shelf life in days (Rule 2)
    unit_volume_m3: float = 1.0                      # Cubic volume per unit (Rule 4)
    ranking_weights: Optional[Dict[str, float]] = None  # Custom scoring weights (FM-9)


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
    safety_stock_quantity: int = 0
    target_ending_inventory: int = 0


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
    is_capacity_feasible: bool = True
    trade_offs: List[str] = field(default_factory=list)
    is_split_sourcing: bool = False
    split_allocation: Optional[SplitOrderAllocation] = None
    effective_lead_time_days: Optional[int] = None
    unlocked_price_tier: Optional[PriceTier] = None
    composite_score: float = 0.0


@dataclass(frozen=True)
class NegotiationLever:
    """Actionable numerical negotiation lever for buyer counter-offers."""
    lever_type: Literal[
        "LEAD_TIME_EXPEDITE",
        "MOQ_REDUCTION",
        "PRICE_BENCHMARK_COUNTER_OFFER",
        "PARTIAL_BATCH_DELIVERY",
    ]
    title: str
    target_supplier_id: int
    target_supplier_name: str
    current_value: str
    target_value: str
    potential_savings: Optional[float]
    recommended_talking_point: str


@dataclass(frozen=True)
class InvestigationOption:
    """Actionable negotiation or expediting pathway for human buyer review.
    
    Tagged with is_confirmed=False since external negotiations are not assumed.
    """
    pathway_type: Literal[
        "EXISTING_SUPPLIER_EXPEDITE",
        "ALTERNATIVE_SUPPLIER_EMERGENCY",
        "MOQ_REDUCTION_REQUEST",
        "PRICE_BENCHMARK_COUNTER_OFFER",
        "PARTIAL_BATCH_DELIVERY",
    ]
    description: str
    target_supplier_id: Optional[int]
    target_supplier_name: Optional[str]
    required_delivery_date: date
    potential_quantity: int
    action_required_by_buyer: str
    is_confirmed: bool = False
    negotiation_lever: Optional[NegotiationLever] = None


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
