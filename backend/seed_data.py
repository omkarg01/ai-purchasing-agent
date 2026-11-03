"""Seed script to populate SQLite database with realistic purchasing scenarios."""
import sys
import os
from datetime import date, timedelta
from decimal import Decimal

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import SessionLocal, init_db
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.inventory import Inventory
from app.models.demand_forecast import DemandForecast
from app.models.purchasing_budget import PurchasingBudget
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_recommendation import PurchaseRecommendation


def seed():
    init_db()
    db = SessionLocal()

    try:
        # Clear existing data
        db.query(PurchaseOrder).delete()
        db.query(PurchaseRecommendation).delete()
        db.query(PurchasingBudget).delete()
        db.query(DemandForecast).delete()
        db.query(Inventory).delete()
        db.query(SupplierProduct).delete()
        db.query(Product).delete()
        db.query(Supplier).delete()
        db.commit()

        today = date.today()

        # 1. Suppliers
        acme = Supplier(supplier_name="Acme Industrial Supplies")
        global_parts = Supplier(supplier_name="Global Logistics & Parts")
        quick_parts = Supplier(supplier_name="QuickParts Express")
        db.add_all([acme, global_parts, quick_parts])
        db.flush()

        # 2. Products
        prod_a = Product(sku="SKU-WIDGET-A", name="Precision Industrial Widget A", description="Standard precision industrial widget")
        prod_b = Product(sku="SKU-GADGET-B", name="Electronic Micro-Gadget B", description="High sensitivity micro sensor component")
        prod_c = Product(sku="SKU-GEAR-C", name="Heavy Duty Gear Assembly C", description="Steel gear assembly for heavy robotics")
        prod_d = Product(sku="SKU-SENSOR-D", name="Optical Distance Sensor D", description="IR proximity and laser distance sensor")
        db.add_all([prod_a, prod_b, prod_c, prod_d])
        db.flush()

        # 3. Supplier Products
        sp_a1 = SupplierProduct(supplier_id=acme.id, product_id=prod_a.id, unit_price=Decimal("15.00"), lead_time_days=5, minimum_order_quantity=50)
        sp_a2 = SupplierProduct(supplier_id=global_parts.id, product_id=prod_a.id, unit_price=Decimal("13.50"), lead_time_days=10, minimum_order_quantity=100)
        sp_b1 = SupplierProduct(supplier_id=quick_parts.id, product_id=prod_b.id, unit_price=Decimal("25.00"), lead_time_days=3, minimum_order_quantity=20)
        sp_c1 = SupplierProduct(supplier_id=acme.id, product_id=prod_c.id, unit_price=Decimal("8.00"), lead_time_days=7, minimum_order_quantity=50)
        sp_d1 = SupplierProduct(supplier_id=global_parts.id, product_id=prod_d.id, unit_price=Decimal("45.00"), lead_time_days=14, minimum_order_quantity=10)
        db.add_all([sp_a1, sp_a2, sp_b1, sp_c1, sp_d1])

        # 4. Inventory
        inv_a = Inventory(product_id=prod_a.id, available_quantity=100, storage_capacity=1000)
        inv_b = Inventory(product_id=prod_b.id, available_quantity=50, storage_capacity=500)
        inv_c = Inventory(product_id=prod_c.id, available_quantity=300, storage_capacity=800)
        inv_d = Inventory(product_id=prod_d.id, available_quantity=10, storage_capacity=300)
        db.add_all([inv_a, inv_b, inv_c, inv_d])

        # 5. Demand Forecasts
        df_a = DemandForecast(product_id=prod_a.id, period_start=today, period_end=today + timedelta(days=14), forecast_quantity=300)
        df_b = DemandForecast(product_id=prod_b.id, period_start=today, period_end=today + timedelta(days=10), forecast_quantity=150)
        df_c = DemandForecast(product_id=prod_c.id, period_start=today, period_end=today + timedelta(days=14), forecast_quantity=150)
        df_d = DemandForecast(product_id=prod_d.id, period_start=today, period_end=today + timedelta(days=5), forecast_quantity=100)
        db.add_all([df_a, df_b, df_c, df_d])

        # 6. Budget (Total $50,000, Committed $5,000)
        budget = PurchasingBudget(
            total_budget=Decimal("50000.00"),
            committed_amount=Decimal("5000.00")
        )
        db.add(budget)

        # 7. Recommendations
        # Rec 1: Normal need -> Expected ACCEPT
        rec1 = PurchaseRecommendation(
            product_id=prod_a.id,
            supplier_id=acme.id,
            recommended_quantity=200,
            requested_delivery_date=today + timedelta(days=8),
            status="PENDING_APPROVAL"
        )
        # Rec 2: Excessive quantity (need 100, requested 300) -> Expected MODIFY
        rec2 = PurchaseRecommendation(
            product_id=prod_b.id,
            supplier_id=quick_parts.id,
            recommended_quantity=300,
            requested_delivery_date=today + timedelta(days=6),
            status="PENDING_APPROVAL"
        )
        # Rec 3: Stock 300 > Forecast 150, no need to buy -> Expected REJECT
        rec3 = PurchaseRecommendation(
            product_id=prod_c.id,
            supplier_id=acme.id,
            recommended_quantity=200,
            requested_delivery_date=today + timedelta(days=10),
            status="PENDING_APPROVAL"
        )
        # Rec 4: Requested delivery in 4 days, but supplier lead time is 14 days -> Expected INVESTIGATE
        rec4 = PurchaseRecommendation(
            product_id=prod_d.id,
            supplier_id=global_parts.id,
            recommended_quantity=90,
            requested_delivery_date=today + timedelta(days=4),
            status="PENDING_APPROVAL"
        )
        # Rec 5: Already Approved historical record
        rec5 = PurchaseRecommendation(
            product_id=prod_a.id,
            supplier_id=acme.id,
            recommended_quantity=100,
            requested_delivery_date=today + timedelta(days=5),
            status="APPROVED",
            agent_decision="ACCEPT",
            agent_suggested_quantity=100,
            agent_suggested_supplier_id=acme.id,
            agent_reasoning="Evaluation confirmed stock shortage and verified supplier terms.",
            evaluated_at=today
        )

        db.add_all([rec1, rec2, rec3, rec4, rec5])
        db.commit()
        print("Database seeded successfully with 5 purchase recommendations.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
