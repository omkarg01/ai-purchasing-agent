# Architecture & Engineering Decisions

## 1. Database Architecture: SQLite & SQLAlchemy ORM

### Technology Choices
- **Database Engine**: SQLite 3 (lightweight, zero-configuration, ideal for local development and embedded edge processing).
- **ORM**: SQLAlchemy 2.0 (standard Python ORM with full support for declarative models, explicit relationship mappings, and type safety).
- **Driver / Foreign Keys**: SQLite disables foreign key constraints by default. We enable them globally across all sessions using an engine connection event listener:
  ```python
  @event.listens_for(Engine, "connect")
  def set_sqlite_pragma(dbapi_connection, connection_record):
      cursor = dbapi_connection.cursor()
      cursor.execute("PRAGMA foreign_keys=ON")
      cursor.close()
  ```

### Data Model Specifications & Invariants
For complete field-by-field definitions, refer to [`plans/sqlite-data-models.md`](../plans/sqlite-data-models.md).

1. **`Product`**: Core product catalog (`sku` unique, indexed).
2. **`Inventory`**: One-to-one with `Product` (`product_id` unique). `available_quantity` represents stock available for purchasing decisions after accounting for existing reservations (`reserved_quantity` omitted for MVP).
3. **`DemandForecast`**: One-to-many with `Product`. Stores forecasted demand over `[period_start, period_end]`.
4. **`Supplier`**: Registered vendors and supplier profiles.
5. **`SupplierProduct`**: Association table linking `Supplier` and `Product` (many-to-many) with commercial terms: `unit_price`, `lead_time_days`, `minimum_order_quantity`. Enforces unique `(supplier_id, product_id)`.
6. **`PurchaseRecommendation`**: Decision engine proposals with `recommended_quantity`, delivery target, nullable `supplier_id`, and embedded agent evaluation attributes (`agent_suggested_quantity`, `agent_suggested_supplier_id`, `agent_reasoning`, `agent_decision` e.g. `ACCEPT`, `MODIFY`, `REJECT`, `INVESTIGATE`, and `evaluated_at`).
7. **`PurchaseOrder`**: Confirmed or active orders placed with suppliers (`quantity`, `unit_price`, `expected_delivery_date`, `status`). Includes optional `recommendation_id` FK to trace back to originating recommendations.
8. **`PurchasingBudget`**: Shared budget tracking `total_budget` and `committed_amount`.

### Key Architectural Invariants
- **Preservation of Purchasing History**: Purchase orders and recommendations enforce `ondelete="RESTRICT"` for `Product` and `Supplier` foreign keys, preventing cascading loss of history when catalog records are deleted.
- **Transactional PO & Budget Updates**: Creation of any `PurchaseOrder` and the increment of `PurchasingBudget.committed_amount` must execute inside a single atomic database transaction.
- **Evaluation API Immutability Guarantee**: The recommendation evaluation endpoint (`POST /recommendations/{id}/evaluate`) writes strictly to the `agent_suggested_*`, `agent_decision`, `agent_reasoning`, and `evaluated_at` fields. The original `recommended_quantity`, `supplier_id`, and human approval `status` are never overwritten.
- **Explicit Table Creation Ordering**: All model modules are explicitly imported in `init_db()` prior to calling `Base.metadata.create_all()`.
