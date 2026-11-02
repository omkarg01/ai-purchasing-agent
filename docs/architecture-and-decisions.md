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

### Data Model Specifications
For field-by-field explanations and justification of all attributes, refer to [`plans/sqlite-data-models.md`](../plans/sqlite-data-models.md).

#### Entity Summary:
1. **`Product`**: Core product catalog (`sku` unique, indexed).
2. **`Inventory`**: One-to-one with `Product` (`product_id` unique). Tracks `available_quantity` and `storage_capacity`.
3. **`DemandForecast`**: One-to-many with `Product`. Stores forecasted demand over `[period_start, period_end]`.
4. **`Supplier`**: Registered vendors and supplier profiles.
5. **`SupplierProduct`**: Association table linking `Supplier` and `Product` (many-to-many) with commercial terms: `unit_price`, `lead_time_days`, `minimum_order_quantity`. Enforces unique `(supplier_id, product_id)`.
6. **`PurchaseRecommendation`**: Decision engine proposals with `recommended_quantity`, delivery target, and nullable `supplier_id`.
7. **`PurchaseOrder`**: Confirmed or active orders placed with suppliers (`quantity`, `unit_price`, `expected_delivery_date`, `status`).
8. **`PurchasingBudget`**: Shared budget tracking `total_budget` and `committed_amount`.
