"""Seed script to populate SQLite database with 30 products, 15 suppliers, and realistic scenarios."""
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
from app.models.evaluation_history import EvaluationHistory


def seed():
    init_db()
    db = SessionLocal()

    try:
        # Clear existing data in foreign-key safe order
        db.query(EvaluationHistory).delete()
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

        # -------------------------------------------------------------
        # 1. 15 Diverse Enterprise Suppliers
        # -------------------------------------------------------------
        suppliers_data = [
            "Acme Industrial Supplies",             # 1
            "Global Logistics & Parts",              # 2
            "QuickParts Express",                    # 3
            "Apex Precision Manufacturing",          # 4
            "Titan Heavy Industries",                # 5
            "Nexus Semiconductor & Sensors",         # 6
            "Horizon Aerospace & Robotics",          # 7
            "Vanguard Fasteners & Hardware",         # 8
            "Pacific Rim Microelectronics",          # 9
            "Atlas Hydraulic & Pneumatic",           # 10
            "Delta Automation Systems",              # 11
            "Summit Materials & Alloys",             # 12
            "Quantum Logic Technologies",            # 13
            "Beacon Cable & Wire",                   # 14
            "Sterling Polymer Dynamics",             # 15
        ]
        supplier_objs = [Supplier(supplier_name=name) for name in suppliers_data]
        db.add_all(supplier_objs)
        db.flush()
        s = {sup.supplier_name: sup for sup in supplier_objs}

        # -------------------------------------------------------------
        # 2. 30 Industrial Products
        # -------------------------------------------------------------
        products_def = [
            ("SKU-WIDG-001", "Precision Industrial Widget A", "Standard precision industrial widget for high-speed machinery"),
            ("SKU-GADG-002", "Electronic Micro-Gadget B", "High sensitivity micro sensor component for IoT telemetry"),
            ("SKU-GEAR-003", "Heavy Duty Gear Assembly C", "Steel planetary gear assembly for heavy robotics and drivetrains"),
            ("SKU-SENS-004", "Optical Distance Sensor D", "Infrared proximity and multi-point laser distance sensor"),
            ("SKU-MOTO-005", "High-Torque Stepper Motor", "NEMA 23 bipolar stepper motor with integrated digital encoder"),
            ("SKU-DRIV-006", "Brushless DC Servo Driver", "48V 20A closed-loop servo controller with CANopen bus"),
            ("SKU-BEAR-007", "Linear Ball Bearing Carriage", "Precision linear guide block 20mm with pre-load wipers"),
            ("SKU-PNEU-008", "Pneumatic Cylinder 50mm Bore", "Double acting ISO 15552 standard pneumatic air cylinder"),
            ("SKU-VALV-009", "Proportional Solenoid Valve", "24V DC 2-way proportional flow control valve with analog driver"),
            ("SKU-FAST-010", "Titanium Alloy Hex Fasteners M6", "Grade 5 titanium aerospace bolts box of 100 with locking washers"),
            ("SKU-POWR-011", "Industrial Power Supply 24V 480W", "DIN-rail mount active PFC regulated industrial power supply"),
            ("SKU-MCU-012", "ARM Cortex-M7 Embedded Controller", "Industrial grade 480MHz telemetry core with cryptographic engine"),
            ("SKU-DISP-013", "Industrial Capacitive Touch Display 7in", "Sunlight readable IP65 sealed TFT-LCD human machine interface"),
            ("SKU-COMP-014", "Carbon Fiber Reinforced Strut", "Ultra lightweight aerospace structural beam with titanium end fittings"),
            ("SKU-SEAL-015", "High-Temperature Silicone Gasket Kit", "Chemical resistant fluoroelastomer sealing pack for autoclave chambers"),
            ("SKU-CABL-016", "Shielded Ethernet Industrial Cable 50m", "Cat6A double shielded drag chain rated heavy flexible cable"),
            ("SKU-ENCO-017", "Rotary Absolute Optical Encoder", "16-bit multi-turn industrial SSI encoder with stainless shaft"),
            ("SKU-THRM-018", "Thermal Imaging Core Module", "Long wave infrared uncooled microbolometer sensor 640x512"),
            ("SKU-SCRW-019", "Hardened Steel Ball Screw Assembly", "25mm diameter precision ground ball screw with anti-backlash nut"),
            ("SKU-VIBR-020", "Piezoelectric Vibration Sensor", "Triaxial industrial condition monitoring sensor 100mV/g IEPE"),
            ("SKU-BATT-021", "Rechargeable LiFePO4 Battery Module", "24V 50Ah modular deep-cycle energy storage pack for AGVs"),
            ("SKU-HYDR-022", "Hydraulic Check Valve 350 Bar", "Cartridge style zero-leakage pilot operated check valve"),
            ("SKU-ENCL-023", "Stainless Steel Enclosure NEMA 4X", "Weatherproof corrosion-resistant electrical junction cabinet"),
            ("SKU-RELY-024", "Semiconductor Relay 3-Phase 50A", "Zero-crossing DIN-rail solid state power relay with heatsink"),
            ("SKU-BELT-025", "Polyurethane Timing Belt 25mm", "Steel cord reinforced AT10 metric synchronous timing belt 2m"),
            ("SKU-LASR-026", "Laser Profilometer Sensor 3D", "High speed blue line laser displacement scanner 0.5um repeatability"),
            ("SKU-ALUM-027", "Aerospace Aluminum Billet 7075-T6", "High strength pre-machined alloy stock block 150x150x200mm"),
            ("SKU-FLOW-028", "Ultrasonic Flow Meter Transducer", "Non-invasive clamp-on liquid flow sensor for cleanroom utilities"),
            ("SKU-SAFE-029", "Emergency Stop Safety Relay Module", "Dual channel SIL3 PLe rated safety monitoring controller"),
            ("SKU-CONN-030", "Hermetic Sealed Circular Connector 12P", "IP68 MIL-DTL-38999 spec industrial power socket receptacle"),
        ]
        product_objs = [Product(sku=sku, name=name, description=desc) for sku, name, desc in products_def]
        db.add_all(product_objs)
        db.flush()

        # -------------------------------------------------------------
        # 3. Supplier Products (Every Product has 2 to 3 Qualified Suppliers)
        # -------------------------------------------------------------
        # Format: (product_idx, supplier_name, price, lead_days, moq, capacity)
        sp_definitions = [
            # Prod 1: Precision Widget A (Assignment Scenario 2 Split Sourcing)
            (0, "Acme Industrial Supplies", Decimal("10.00"), 4, 100, 250),
            (0, "Global Logistics & Parts", Decimal("12.00"), 5, 100, 500),
            (0, "Apex Precision Manufacturing", Decimal("14.00"), 3, 50, None),

            # Prod 2: Electronic Micro-Gadget B
            (1, "QuickParts Express", Decimal("22.00"), 3, 20, 200),
            (1, "Nexus Semiconductor & Sensors", Decimal("19.50"), 7, 50, 400),
            (1, "Pacific Rim Microelectronics", Decimal("18.00"), 12, 100, None),

            # Prod 3: Heavy Duty Gear Assembly C
            (2, "Titan Heavy Industries", Decimal("80.00"), 7, 10, 100),
            (2, "Apex Precision Manufacturing", Decimal("85.00"), 4, 15, 80),
            (2, "Acme Industrial Supplies", Decimal("76.00"), 12, 20, 150),

            # Prod 4: Optical Distance Sensor D
            (3, "Nexus Semiconductor & Sensors", Decimal("45.00"), 5, 25, 250),
            (3, "Quantum Logic Technologies", Decimal("42.00"), 8, 50, 300),
            (3, "Global Logistics & Parts", Decimal("48.00"), 3, 10, 100),

            # Prod 5: High-Torque Stepper Motor
            (4, "Delta Automation Systems", Decimal("38.00"), 6, 10, 200),
            (4, "Apex Precision Manufacturing", Decimal("35.00"), 10, 25, 300),

            # Prod 6: Brushless DC Servo Driver
            (5, "Delta Automation Systems", Decimal("120.00"), 8, 5, 50),
            (5, "Quantum Logic Technologies", Decimal("115.00"), 12, 10, 100),

            # Prod 7: Linear Ball Bearing Carriage
            (6, "Apex Precision Manufacturing", Decimal("28.50"), 4, 20, 150),
            (6, "Titan Heavy Industries", Decimal("26.00"), 9, 50, 300),
            (6, "Acme Industrial Supplies", Decimal("30.00"), 3, 10, 100),

            # Prod 8: Pneumatic Cylinder 50mm Bore
            (7, "Atlas Hydraulic & Pneumatic", Decimal("64.00"), 5, 10, 100),
            (7, "Global Logistics & Parts", Decimal("68.00"), 3, 5, 80),

            # Prod 9: Proportional Solenoid Valve
            (8, "Atlas Hydraulic & Pneumatic", Decimal("145.00"), 7, 4, 60),
            (8, "Acme Industrial Supplies", Decimal("150.00"), 5, 5, 50),

            # Prod 10: Titanium Alloy Fasteners M6
            (9, "Vanguard Fasteners & Hardware", Decimal("55.00"), 3, 10, 500),
            (9, "Summit Materials & Alloys", Decimal("52.00"), 7, 25, 800),

            # Prod 11: Industrial Power Supply 24V
            (10, "Global Logistics & Parts", Decimal("82.00"), 5, 10, 120),
            (10, "Delta Automation Systems", Decimal("79.00"), 8, 15, 200),

            # Prod 12: ARM Cortex-M7 Embedded Controller
            (11, "Quantum Logic Technologies", Decimal("34.00"), 6, 50, 400),
            (11, "Pacific Rim Microelectronics", Decimal("31.50"), 12, 100, 1000),

            # Prod 13: Industrial Touch Display 7in
            (12, "Pacific Rim Microelectronics", Decimal("110.00"), 9, 10, 150),
            (12, "QuickParts Express", Decimal("125.00"), 3, 5, 60),

            # Prod 14: Carbon Fiber Reinforced Strut
            (13, "Horizon Aerospace & Robotics", Decimal("210.00"), 14, 5, 40),
            (13, "Sterling Polymer Dynamics", Decimal("195.00"), 20, 10, 80),

            # Prod 15: High-Temperature Silicone Gasket Kit
            (14, "Sterling Polymer Dynamics", Decimal("18.00"), 4, 50, 600),
            (14, "Acme Industrial Supplies", Decimal("16.50"), 8, 100, 1000),

            # Prod 16: Shielded Ethernet Cable 50m
            (15, "Beacon Cable & Wire", Decimal("42.00"), 3, 10, 200),
            (15, "Global Logistics & Parts", Decimal("40.00"), 6, 20, 300),

            # Prod 17: Rotary Absolute Optical Encoder
            (16, "Nexus Semiconductor & Sensors", Decimal("175.00"), 8, 5, 80),
            (16, "Apex Precision Manufacturing", Decimal("168.00"), 12, 10, 120),

            # Prod 18: Thermal Imaging Core Module
            (17, "Horizon Aerospace & Robotics", Decimal("450.00"), 15, 2, 25),
            (17, "Quantum Logic Technologies", Decimal("420.00"), 21, 5, 50),

            # Prod 19: Hardened Steel Ball Screw Assembly
            (18, "Titan Heavy Industries", Decimal("280.00"), 10, 4, 30),
            (18, "Apex Precision Manufacturing", Decimal("295.00"), 5, 5, 50),

            # Prod 20: Piezoelectric Vibration Sensor
            (19, "Nexus Semiconductor & Sensors", Decimal("95.00"), 5, 10, 150),
            (19, "Pacific Rim Microelectronics", Decimal("88.00"), 11, 20, 250),

            # Prod 21: Rechargeable LiFePO4 Battery Module
            (20, "Global Logistics & Parts", Decimal("360.00"), 10, 2, 30),
            (20, "Delta Automation Systems", Decimal("345.00"), 15, 5, 50),

            # Prod 22: Hydraulic Check Valve 350 Bar
            (21, "Atlas Hydraulic & Pneumatic", Decimal("130.00"), 6, 8, 80),
            (21, "Titan Heavy Industries", Decimal("125.00"), 10, 12, 120),

            # Prod 23: Stainless Steel Enclosure NEMA 4X
            (22, "Acme Industrial Supplies", Decimal("185.00"), 5, 4, 50),
            (22, "Titan Heavy Industries", Decimal("175.00"), 9, 8, 80),

            # Prod 24: Semiconductor Relay 3-Phase 50A
            (23, "Delta Automation Systems", Decimal("48.00"), 4, 15, 200),
            (23, "QuickParts Express", Decimal("52.00"), 2, 10, 100),

            # Prod 25: Polyurethane Timing Belt 25mm
            (24, "Sterling Polymer Dynamics", Decimal("32.00"), 4, 25, 300),
            (24, "Vanguard Fasteners & Hardware", Decimal("35.00"), 2, 15, 150),

            # Prod 26: Laser Profilometer Sensor 3D
            (25, "Horizon Aerospace & Robotics", Decimal("890.00"), 14, 1, 15),
            (25, "Nexus Semiconductor & Sensors", Decimal("850.00"), 18, 2, 20),

            # Prod 27: Aerospace Aluminum Billet 7075-T6
            (26, "Summit Materials & Alloys", Decimal("140.00"), 7, 10, 100),
            (26, "Acme Industrial Supplies", Decimal("145.00"), 4, 10, 80),

            # Prod 28: Ultrasonic Flow Meter Transducer
            (27, "Atlas Hydraulic & Pneumatic", Decimal("220.00"), 8, 5, 40),
            (27, "Quantum Logic Technologies", Decimal("205.00"), 12, 10, 60),

            # Prod 29: Emergency Stop Safety Relay Module
            (28, "Delta Automation Systems", Decimal("92.00"), 3, 10, 150),
            (28, "Beacon Cable & Wire", Decimal("88.00"), 7, 15, 200),

            # Prod 30: Hermetic Sealed Circular Connector 12P
            (29, "Beacon Cable & Wire", Decimal("28.00"), 4, 50, 500),
            (29, "Vanguard Fasteners & Hardware", Decimal("31.00"), 2, 25, 300),
        ]

        sp_objs = [
            SupplierProduct(
                supplier_id=s[sup_name].id,
                product_id=product_objs[p_idx].id,
                unit_price=price,
                lead_time_days=lead_days,
                minimum_order_quantity=moq,
                available_capacity=cap,
                is_moq_negotiable=True if moq > 20 else False,
                expedited_lead_time_days=max(1, lead_days - 3) if lead_days > 4 else None,
            )
            for p_idx, sup_name, price, lead_days, moq, cap in sp_definitions
        ]
        db.add_all(sp_objs)

        # -------------------------------------------------------------
        # 4. Warehouse Inventories (30 Products)
        # -------------------------------------------------------------
        # Base inventories: on-hand available quantity & maximum storage capacity
        inv_configs = [
            (100, 1000),  # Prod 1 (Net Shortage = 500 when forecast is 600)
            (50, 500),    # Prod 2
            (300, 800),   # Prod 3
            (10, 300),    # Prod 4
            (40, 400),    # Prod 5
            (15, 200),    # Prod 6
            (120, 600),   # Prod 7
            (35, 300),    # Prod 8
            (20, 150),    # Prod 9
            (250, 1000),  # Prod 10
            (45, 300),    # Prod 11
            (100, 800),   # Prod 12
            (25, 200),    # Prod 13
            (10, 100),    # Prod 14
            (180, 800),   # Prod 15
            (60, 400),    # Prod 16
            (12, 100),    # Prod 17
            (5, 50),      # Prod 18
            (18, 100),    # Prod 19
            (30, 200),    # Prod 20
            (8, 60),      # Prod 21
            (22, 150),    # Prod 22
            (14, 80),     # Prod 23
            (40, 250),    # Prod 24
            (90, 400),    # Prod 25
            (4, 30),      # Prod 26
            (35, 200),    # Prod 27
            (12, 100),    # Prod 28
            (28, 200),    # Prod 29
            (150, 800),   # Prod 30
        ]
        inv_objs = [
            Inventory(product_id=product_objs[i].id, available_quantity=avail, storage_capacity=cap)
            for i, (avail, cap) in enumerate(inv_configs)
        ]
        db.add_all(inv_objs)

        # -------------------------------------------------------------
        # 5. Demand Forecasts (30 Products)
        # -------------------------------------------------------------
        forecast_configs = [
            (600, 14),   # Prod 1: 600 demand - 100 stock = 500 units net requirement (Scenario 2)
            (150, 10),   # Prod 2
            (150, 14),   # Prod 3: 300 stock > 150 demand (Overstocked)
            (100, 5),    # Prod 4: Imminent demand in 5 days
            (120, 14),   # Prod 5
            (60, 21),    # Prod 6
            (250, 14),   # Prod 7
            (90, 10),    # Prod 8
            (50, 14),    # Prod 9
            (600, 30),   # Prod 10
            (110, 14),   # Prod 11
            (300, 21),   # Prod 12
            (80, 14),    # Prod 13
            (30, 30),    # Prod 14
            (350, 14),   # Prod 15
            (150, 14),   # Prod 16
            (40, 21),    # Prod 17
            (15, 30),    # Prod 18
            (45, 21),    # Prod 19
            (80, 14),    # Prod 20
            (25, 30),    # Prod 21
            (65, 14),    # Prod 22
            (40, 21),    # Prod 23
            (100, 14),   # Prod 24
            (220, 14),   # Prod 25
            (10, 30),    # Prod 26
            (90, 21),    # Prod 27
            (35, 14),    # Prod 28
            (75, 14),    # Prod 29
            (400, 30),   # Prod 30
        ]
        df_objs = [
            DemandForecast(
                product_id=product_objs[i].id,
                period_start=today,
                period_end=today + timedelta(days=days),
                forecast_quantity=qty,
            )
            for i, (qty, days) in enumerate(forecast_configs)
        ]
        db.add_all(df_objs)

        # -------------------------------------------------------------
        # 6. Corporate Purchasing Budget
        # -------------------------------------------------------------
        budget = PurchasingBudget(
            total_budget=Decimal("250000.00"),
            committed_amount=Decimal("35000.00"),
        )
        db.add(budget)

        # -------------------------------------------------------------
        # 7. Initial Purchasing Recommendations (Covering all key workflows)
        # -------------------------------------------------------------
        recommendations = [
            # Rec 1: Assignment Scenario 2 Multi-Vendor Split Sourcing
            PurchaseRecommendation(
                product_id=product_objs[0].id,  # Widget A
                supplier_id=s["Acme Industrial Supplies"].id,
                recommended_quantity=500,
                requested_delivery_date=today + timedelta(days=14),
                status="PENDING_APPROVAL",
                agent_decision="MODIFY",
                agent_suggested_quantity=500,
                agent_suggested_supplier_id=s["Acme Industrial Supplies"].id,
                agent_reasoning=(
                    "Selected Acme Industrial Supplies & Global Logistics & Parts (Split Sourcing) as preferred: "
                    "delivers before target deadline at lowest cost ($5,500.00).\n\n"
                    "Split order allocation: 250 units with Acme Industrial Supplies ($2,500.00) + "
                    "250 units with Global Logistics & Parts ($3,000.00).\n\n"
                    "Split sourcing order: 250 units with Acme Industrial Supplies and 250 units with Global "
                    "Logistics & Parts to fulfill total requirement of 500 units within supplier capacity limits."
                ),
                split_allocation={
                    "primary_supplier_id": s["Acme Industrial Supplies"].id,
                    "primary_supplier_name": "Acme Industrial Supplies",
                    "primary_quantity": 250,
                    "primary_unit_price": 10.0,
                    "primary_cost": 2500.0,
                    "secondary_supplier_id": s["Global Logistics & Parts"].id,
                    "secondary_supplier_name": "Global Logistics & Parts",
                    "secondary_quantity": 250,
                    "secondary_unit_price": 12.0,
                    "secondary_cost": 3000.0,
                    "total_cost": 5500.0,
                },
                evaluated_at=today,
            ),
            # Rec 2: Normal replenishment -> Expected ACCEPT
            PurchaseRecommendation(
                product_id=product_objs[1].id,  # Micro-Gadget B
                supplier_id=s["QuickParts Express"].id,
                recommended_quantity=100,
                requested_delivery_date=today + timedelta(days=8),
                status="PENDING_APPROVAL",
            ),
            # Rec 3: Overstocked part -> Expected REJECT
            PurchaseRecommendation(
                product_id=product_objs[2].id,  # Gear Assembly C
                supplier_id=s["Titan Heavy Industries"].id,
                recommended_quantity=200,
                requested_delivery_date=today + timedelta(days=10),
                status="PENDING_APPROVAL",
            ),
            # Rec 4: Urgent demand with long supplier lead time -> Expected INVESTIGATE
            PurchaseRecommendation(
                product_id=product_objs[3].id,  # Distance Sensor D
                supplier_id=s["Nexus Semiconductor & Sensors"].id,
                recommended_quantity=90,
                requested_delivery_date=today + timedelta(days=4),
                status="PENDING_APPROVAL",
            ),
            # Rec 5: High-Torque Stepper Motor -> Approved Historical Record
            PurchaseRecommendation(
                product_id=product_objs[4].id,
                supplier_id=s["Delta Automation Systems"].id,
                recommended_quantity=80,
                requested_delivery_date=today + timedelta(days=12),
                status="APPROVED",
                agent_decision="ACCEPT",
                agent_suggested_quantity=80,
                agent_suggested_supplier_id=s["Delta Automation Systems"].id,
                agent_reasoning="Evaluation confirmed stock requirement and verified delivery feasibility.",
                evaluated_at=today,
            ),
            # Rec 6: Linear Ball Bearing Carriage
            PurchaseRecommendation(
                product_id=product_objs[6].id,
                supplier_id=s["Apex Precision Manufacturing"].id,
                recommended_quantity=130,
                requested_delivery_date=today + timedelta(days=9),
                status="PENDING_APPROVAL",
            ),
            # Rec 7: Pneumatic Cylinder
            PurchaseRecommendation(
                product_id=product_objs[7].id,
                supplier_id=s["Atlas Hydraulic & Pneumatic"].id,
                recommended_quantity=55,
                requested_delivery_date=today + timedelta(days=7),
                status="PENDING_APPROVAL",
            ),
            # Rec 8: Titanium Fasteners Box
            PurchaseRecommendation(
                product_id=product_objs[9].id,
                supplier_id=s["Vanguard Fasteners & Hardware"].id,
                recommended_quantity=350,
                requested_delivery_date=today + timedelta(days=15),
                status="PENDING_APPROVAL",
            ),
            # Rec 9: Industrial Power Supply
            PurchaseRecommendation(
                product_id=product_objs[10].id,
                supplier_id=s["Global Logistics & Parts"].id,
                recommended_quantity=65,
                requested_delivery_date=today + timedelta(days=10),
                status="PENDING_APPROVAL",
            ),
            # Rec 10: High-Temperature Gaskets
            PurchaseRecommendation(
                product_id=product_objs[14].id,
                supplier_id=s["Sterling Polymer Dynamics"].id,
                recommended_quantity=170,
                requested_delivery_date=today + timedelta(days=8),
                status="PENDING_APPROVAL",
            ),
        ]
        db.add_all(recommendations)
        db.commit()

        # Seed evaluation history for Rec 1 so historical timeline and split metrics load immediately
        hist1 = EvaluationHistory(
            recommendation_id=recommendations[0].id,
            evaluation_sequence=1,
            evaluated_quantity=500,
            evaluated_supplier_id=s["Acme Industrial Supplies"].id,
            evaluated_supplier_name="Acme Industrial Supplies",
            agent_decision="MODIFY",
            explanation=recommendations[0].agent_reasoning,
            calculations={
                "daily_burn_rate": 42.86,
                "days_of_initial_coverage": 2.33,
                "stockout_date": (today + timedelta(days=2)).isoformat(),
                "has_interim_stockout": True,
                "interim_stockout_days": 12,
                "interim_shortage_quantity": 500,
                "final_projected_inventory": -500,
                "final_unmet_demand": 500,
                "additional_purchasing_requirement": 500,
                "safety_stock_quantity": 0,
                "target_ending_inventory": 0,
                "remaining_budget": 215000.0,
                "storage_capacity": 1000,
                "is_split_sourcing": True,
                "split_allocation": recommendations[0].split_allocation,
            },
            risks=["Interim stockout projected before delivery."],
            warnings=[],
            evaluated_at=today,
        )
        db.add(hist1)
        db.commit()

        print(f"Database successfully seeded with {len(supplier_objs)} suppliers, {len(product_objs)} products, "
              f"{len(sp_objs)} catalog mappings, and {len(recommendations)} recommendations.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
