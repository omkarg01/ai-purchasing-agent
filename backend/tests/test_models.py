from datetime import date, datetime
from decimal import Decimal
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    DemandForecast,
    Inventory,
    Product,
    PurchaseOrder,
    PurchaseRecommendation,
    PurchasingBudget,
    Supplier,
    SupplierProduct,
)


def test_product_creation_and_unique_sku(db_session):
    prod1 = Product(name="Widget A", sku="WIDGET-001", description="Standard widget")
    db_session.add(prod1)
    db_session.commit()

    assert prod1.id is not None
    assert prod1.name == "Widget A"
    assert prod1.sku == "WIDGET-001"

    # Duplicate SKU should raise IntegrityError
    prod2 = Product(name="Widget Duplicate", sku="WIDGET-001")
    db_session.add(prod2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_product_inventory_relationship_and_constraints(db_session):
    product = Product(name="Component X", sku="COMP-X-01")
    db_session.add(product)
    db_session.commit()

    inventory = Inventory(
        product_id=product.id,
        available_quantity=300,
        storage_capacity=1000,
    )
    db_session.add(inventory)
    db_session.commit()

    # Test relationship navigation
    assert product.inventory.available_quantity == 300
    assert inventory.product.sku == "COMP-X-01"

    # Enforce 1-to-1: second inventory for same product should fail
    duplicate_inv = Inventory(
        product_id=product.id,
        available_quantity=50,
        storage_capacity=500,
    )
    db_session.add(duplicate_inv)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Negative available_quantity check constraint
    invalid_inv = Inventory(
        product_id=product.id,
        available_quantity=-10,
        storage_capacity=500,
    )
    db_session.add(invalid_inv)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_product_demand_forecast_relationship(db_session):
    product = Product(name="Assembly Unit", sku="ASM-UNIT-01")
    db_session.add(product)
    db_session.commit()

    forecast1 = DemandForecast(
        product_id=product.id,
        forecast_quantity=900,
        period_start=date(2026, 11, 1),
        period_end=date(2026, 11, 14),
    )
    forecast2 = DemandForecast(
        product_id=product.id,
        forecast_quantity=1200,
        period_start=date(2026, 11, 15),
        period_end=date(2026, 11, 28),
    )
    db_session.add_all([forecast1, forecast2])
    db_session.commit()

    assert len(product.demand_forecasts) == 2

    # Negative forecast quantity check constraint
    invalid_forecast = DemandForecast(
        product_id=product.id,
        forecast_quantity=-50,
        period_start=date(2026, 12, 1),
        period_end=date(2026, 12, 15),
    )
    db_session.add(invalid_forecast)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_supplier_and_supplier_product_many_to_many(db_session):
    product = Product(name="Raw Material", sku="RAW-001")
    supplier1 = Supplier(supplier_name="Acme Corp")
    supplier2 = Supplier(supplier_name="Global Logistics")
    db_session.add_all([product, supplier1, supplier2])
    db_session.commit()

    sp1 = SupplierProduct(
        supplier_id=supplier1.id,
        product_id=product.id,
        unit_price=Decimal("15.50"),
        lead_time_days=5,
        minimum_order_quantity=100,
    )
    sp2 = SupplierProduct(
        supplier_id=supplier2.id,
        product_id=product.id,
        unit_price=Decimal("14.00"),
        lead_time_days=10,
        minimum_order_quantity=200,
    )
    db_session.add_all([sp1, sp2])
    db_session.commit()

    assert len(product.supplier_products) == 2
    assert len(supplier1.supplier_products) == 1
    assert supplier1.supplier_products[0].unit_price == Decimal("15.50")

    # Composite uniqueness: duplicate (supplier_id, product_id) must fail
    duplicate_sp = SupplierProduct(
        supplier_id=supplier1.id,
        product_id=product.id,
        unit_price=Decimal("16.00"),
        lead_time_days=4,
        minimum_order_quantity=50,
    )
    db_session.add(duplicate_sp)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # MOQ < 1 check constraint failure
    invalid_moq_sp = SupplierProduct(
        supplier_id=supplier1.id,
        product_id=product.id,
        unit_price=Decimal("15.50"),
        lead_time_days=5,
        minimum_order_quantity=0,
    )
    db_session.add(invalid_moq_sp)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_purchase_recommendation(db_session):
    product = Product(name="Special Valve", sku="VALVE-01")
    supplier = Supplier(supplier_name="Valve Works")
    db_session.add_all([product, supplier])
    db_session.commit()

    # Recommendation with supplier
    rec1 = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=800,
        supplier_id=supplier.id,
        requested_delivery_date=date(2026, 11, 10),
    )
    # Recommendation without supplier (nullable)
    rec2 = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=400,
        supplier_id=None,
        requested_delivery_date=date(2026, 11, 15),
    )
    db_session.add_all([rec1, rec2])
    db_session.commit()

    assert rec1.status == "PENDING"
    assert rec1.supplier.supplier_name == "Valve Works"
    assert rec2.supplier is None
    assert len(product.purchase_recommendations) == 2

    # Negative recommended_quantity check constraint
    invalid_rec = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=-100,
        requested_delivery_date=date(2026, 11, 10),
    )
    db_session.add(invalid_rec)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_purchase_recommendation_with_agent_evaluation(db_session):
    product = Product(name="Smart Thermostat", sku="THERM-01")
    supplier1 = Supplier(supplier_name="Default HVAC Co")
    supplier2 = Supplier(supplier_name="FastTrack Components")
    db_session.add_all([product, supplier1, supplier2])
    db_session.commit()

    # Agent evaluates original recommendation and decides to MODIFY
    rec = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=500,
        supplier_id=supplier1.id,
        requested_delivery_date=date(2026, 11, 20),
        status="PENDING_APPROVAL",
        agent_suggested_quantity=350,
        agent_suggested_supplier_id=supplier2.id,
        agent_reasoning="Lead time with Default HVAC Co risks stockout; FastTrack delivers in 3 days with MOQ 350.",
        agent_decision="MODIFY",
        evaluated_at=datetime(2026, 11, 3, 10, 0, 0),
    )
    db_session.add(rec)
    db_session.commit()

    assert rec.id is not None
    assert rec.status == "PENDING_APPROVAL"
    assert rec.agent_decision == "MODIFY"
    assert rec.agent_suggested_quantity == 350
    assert rec.evaluated_at == datetime(2026, 11, 3, 10, 0, 0)
    assert "FastTrack" in rec.agent_reasoning

    # Verify relationships
    assert rec.supplier.supplier_name == "Default HVAC Co"
    assert rec.agent_suggested_supplier.supplier_name == "FastTrack Components"
    assert rec in supplier1.purchase_recommendations
    assert rec in supplier2.agent_evaluations

    # Invalid agent_decision check constraint
    invalid_decision_rec = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=100,
        requested_delivery_date=date(2026, 11, 20),
        agent_decision="INVALID_STATUS",
    )
    db_session.add(invalid_decision_rec)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Negative agent_suggested_quantity check constraint
    invalid_qty_rec = PurchaseRecommendation(
        product_id=product.id,
        recommended_quantity=100,
        requested_delivery_date=date(2026, 11, 20),
        agent_suggested_quantity=-25,
        agent_decision="ACCEPT",
    )
    db_session.add(invalid_qty_rec)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_purchase_order_with_recommendation_traceability(db_session):
    product = Product(name="Steel Bolt", sku="BOLT-88")
    supplier = Supplier(supplier_name="Bolt Supply Ltd")
    db_session.add_all([product, supplier])
    db_session.commit()

    # 1. Existing PO without recommendation (recommendation_id is nullable)
    existing_po = PurchaseOrder(
        product_id=product.id,
        supplier_id=supplier.id,
        quantity=400,
        unit_price=Decimal("2.25"),
        expected_delivery_date=date(2026, 11, 8),
        recommendation_id=None,
    )
    db_session.add(existing_po)
    db_session.commit()

    assert existing_po.id is not None
    assert existing_po.recommendation_id is None
    assert existing_po.recommendation is None

    # 2. Executed PO linked to a recommendation
    recommendation = PurchaseRecommendation(
        product_id=product.id,
        supplier_id=supplier.id,
        recommended_quantity=200,
        requested_delivery_date=date(2026, 11, 12),
        status="APPROVED",
    )
    db_session.add(recommendation)
    db_session.commit()

    linked_po = PurchaseOrder(
        product_id=product.id,
        supplier_id=supplier.id,
        recommendation_id=recommendation.id,
        quantity=200,
        unit_price=Decimal("2.25"),
        expected_delivery_date=date(2026, 11, 12),
    )
    db_session.add(linked_po)
    db_session.commit()

    assert linked_po.recommendation_id == recommendation.id
    assert linked_po.recommendation.status == "APPROVED"
    assert len(recommendation.purchase_orders) == 1
    assert recommendation.purchase_orders[0].id == linked_po.id


def test_preserve_purchasing_history_on_delete_attempt(db_session):
    product = Product(name="Crucial Raw Part", sku="CRP-999")
    supplier = Supplier(supplier_name="Safe Supplier")
    db_session.add_all([product, supplier])
    db_session.commit()

    po = PurchaseOrder(
        product_id=product.id,
        supplier_id=supplier.id,
        quantity=100,
        unit_price=Decimal("50.00"),
        expected_delivery_date=date(2026, 11, 20),
    )
    db_session.add(po)
    db_session.commit()

    # Attempting to delete product while PO exists must be rejected (RESTRICT)
    db_session.delete(product)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Attempting to delete supplier while PO exists must be rejected (RESTRICT)
    db_session.delete(supplier)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_transactional_purchase_order_and_budget_update(db_session):
    product = Product(name="Monitored Sensor", sku="SENS-01")
    supplier = Supplier(supplier_name="Sensors Direct")
    budget = PurchasingBudget(
        total_budget=Decimal("10000.00"),
        committed_amount=Decimal("1000.00"),
    )
    db_session.add_all([product, supplier, budget])
    db_session.commit()

    order_qty = 50
    order_price = Decimal("20.00")
    total_order_cost = order_price * order_qty  # 1000.00

    # Successful atomic transaction: PO creation + budget commitment update
    with db_session.begin_nested():
        po = PurchaseOrder(
            product_id=product.id,
            supplier_id=supplier.id,
            quantity=order_qty,
            unit_price=order_price,
            expected_delivery_date=date(2026, 11, 25),
        )
        db_session.add(po)
        budget.committed_amount += total_order_cost
    db_session.commit()

    assert budget.committed_amount == Decimal("2000.00")
    assert budget.remaining_budget == 8000.0

    # Failed transaction simulation: failure rolls back both PO and budget update
    initial_committed = budget.committed_amount
    try:
        with db_session.begin_nested():
            failed_po = PurchaseOrder(
                product_id=product.id,
                supplier_id=supplier.id,
                quantity=-5,  # Violates check constraint
                unit_price=Decimal("20.00"),
                expected_delivery_date=date(2026, 11, 25),
            )
            db_session.add(failed_po)
            budget.committed_amount += Decimal("100.00")
            db_session.flush()
    except IntegrityError:
        pass

    db_session.rollback()
    refreshed_budget = db_session.query(PurchasingBudget).filter_by(id=budget.id).one()
    assert refreshed_budget.committed_amount == initial_committed


def test_purchasing_budget(db_session):
    budget = PurchasingBudget(
        total_budget=Decimal("50000.00"),
        committed_amount=Decimal("12500.00"),
    )
    db_session.add(budget)
    db_session.commit()

    assert budget.id is not None
    assert budget.remaining_budget == 37500.0

    # Negative total budget check constraint
    invalid_budget = PurchasingBudget(
        total_budget=Decimal("-1000.00"),
        committed_amount=Decimal("0.00"),
    )
    db_session.add(invalid_budget)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_foreign_key_enforcement(db_session):
    # Attempt to insert inventory for non-existent product
    orphan_inv = Inventory(
        product_id=99999,
        available_quantity=100,
        storage_capacity=500,
    )
    db_session.add(orphan_inv)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
