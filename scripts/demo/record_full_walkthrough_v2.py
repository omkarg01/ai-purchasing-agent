import os
import sys
import glob
import json
import requests
import subprocess
import time
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath("backend"))
sys.stdout.reconfigure(line_buffering=True)

HUD_SCRIPTS = """
window.createScenarioBanner = (title, points) => {
    let el = document.getElementById('demo-scenario-banner');
    if (!el) {
        el = document.createElement('div');
        el.id = 'demo-scenario-banner';
        el.style.position = 'fixed';
        el.style.top = '16px';
        el.style.right = '24px';
        el.style.zIndex = '999998';
        el.style.backgroundColor = 'rgba(15, 23, 42, 0.94)';
        el.style.backdropFilter = 'blur(10px)';
        el.style.border = '1.5px solid rgba(59, 130, 246, 0.5)';
        el.style.borderRadius = '12px';
        el.style.padding = '12px 18px';
        el.style.color = '#ffffff';
        el.style.fontFamily = 'system-ui, -apple-system, sans-serif';
        el.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.4)';
        el.style.maxWidth = '380px';
        el.style.pointerEvents = 'none';
        document.body.appendChild(el);
    }
    el.innerHTML = '<div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #60a5fa; font-weight: 700; margin-bottom: 4px;">' + title + '</div><ul style="margin: 0; padding-left: 16px; font-size: 12px; color: #cbd5e1; line-height: 1.5;">' + points.map(p => '<li>' + p + '</li>').join('') + '</ul>';
};

window.createRulesHUD = () => {
    let el = document.getElementById('demo-rules-hud');
    if (!el) {
        el = document.createElement('div');
        el.id = 'demo-rules-hud';
        el.style.position = 'fixed';
        el.style.top = '140px';
        el.style.right = '24px';
        el.style.zIndex = '999997';
        el.style.backgroundColor = 'rgba(255, 255, 255, 0.96)';
        el.style.backdropFilter = 'blur(10px)';
        el.style.border = '1.5px solid #cbd5e1';
        el.style.borderRadius = '12px';
        el.style.padding = '16px 20px';
        el.style.color = '#0f172a';
        el.style.fontFamily = 'system-ui, -apple-system, sans-serif';
        el.style.boxShadow = '0 12px 28px -6px rgba(0, 0, 0, 0.18)';
        el.style.width = '350px';
        el.style.pointerEvents = 'none';
        document.body.appendChild(el);
    }
    el.innerHTML = `
        <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; color: #1e293b; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; display: flex; align-items: center; gap: 6px;">
            <span>⚖️</span> <span>DETERMINISTIC EVALUATION RULES</span>
        </div>
        <div id="rule-1" style="margin-bottom: 8px; font-size: 12.5px; color: #64748b; transition: all 0.3s ease;">○ 1. Lead Time vs Stockout</div>
        <div id="rule-2" style="margin-bottom: 8px; font-size: 12.5px; color: #64748b; transition: all 0.3s ease;">○ 2. MOQ vs Net Shortage</div>
        <div id="rule-3" style="margin-bottom: 8px; font-size: 12.5px; color: #64748b; transition: all 0.3s ease;">○ 3. Warehouse Storage Limit</div>
        <div id="rule-4" style="margin-bottom: 8px; font-size: 12.5px; color: #64748b; transition: all 0.3s ease;">○ 4. Purchasing Budget Cap</div>
        <div id="rule-verdict" style="margin-top: 12px; padding: 8px 12px; background: #fef3c7; border: 1px solid #fcd34d; border-radius: 6px; font-weight: 700; font-size: 12px; color: #92400e; display: none;">
            ⚠️ RESULT: VERDICT MODIFY (ADJUST TO 100)
        </div>
    `;
};

window.checkRule = (id, label) => {
    const el = document.getElementById(id);
    if (el) {
        el.style.color = '#15803d';
        el.style.fontWeight = '700';
        el.innerHTML = '✓ ' + label;
    }
};

window.showRuleVerdict = (text, isSuccess) => {
    const el = document.getElementById('rule-verdict');
    if (el) {
        el.style.display = 'block';
        if (text) el.innerHTML = text;
        if (isSuccess) {
            el.style.background = '#dcfce7';
            el.style.border = '1px solid #86efac';
            el.style.color = '#15803d';
        }
    }
};

window.clearHUD = () => {
    const b = document.getElementById('demo-scenario-banner');
    if (b) b.remove();
    const r = document.getElementById('demo-rules-hud');
    if (r) r.remove();
};
"""

CURSOR_INJECTION_SCRIPT = """
(() => {
    if (document.getElementById('demo-cursor')) return;
    const cursor = document.createElement('div');
    cursor.id = 'demo-cursor';
    cursor.style.position = 'fixed';
    cursor.style.zIndex = '2147483647';
    cursor.style.width = '24px';
    cursor.style.height = '24px';
    cursor.style.borderRadius = '50%';
    cursor.style.backgroundColor = 'rgba(37, 99, 235, 0.45)';
    cursor.style.border = '2.5px solid #2563eb';
    cursor.style.boxShadow = '0 0 16px rgba(37, 99, 235, 0.6)';
    cursor.style.pointerEvents = 'none';
    cursor.style.transform = 'translate(-50%, -50%)';
    cursor.style.transition = 'transform 0.08s ease-out, background-color 0.15s';
    cursor.style.left = '400px';
    cursor.style.top = '200px';

    const dot = document.createElement('div');
    dot.style.position = 'absolute';
    dot.style.top = '50%';
    dot.style.left = '50%';
    dot.style.width = '6px';
    dot.style.height = '6px';
    dot.style.borderRadius = '50%';
    dot.style.backgroundColor = '#1d4ed8';
    dot.style.transform = 'translate(-50%, -50%)';
    cursor.appendChild(dot);

    document.body.appendChild(cursor);

    window.addEventListener('mousemove', (e) => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    });
    window.addEventListener('mousedown', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(0.65)';
        cursor.style.backgroundColor = 'rgba(220, 38, 38, 0.7)';
        cursor.style.borderColor = '#dc2626';
    });
    window.addEventListener('mouseup', () => {
        cursor.style.transform = 'translate(-50%, -50%) scale(1.0)';
        cursor.style.backgroundColor = 'rgba(37, 99, 235, 0.45)';
        cursor.style.borderColor = '#2563eb';
    });
})();
"""

def prime_database():
    from datetime import datetime, timezone
    from app.database.session import SessionLocal
    from app.models.purchase_recommendation import PurchaseRecommendation
    from app.models.evaluation_history import EvaluationHistory

    db = SessionLocal()
    # 1. Reset Rec 1 (Split sourcing case)
    r1 = db.query(PurchaseRecommendation).filter_by(id=1).first()
    if r1:
        r1.status = "PENDING_APPROVAL"
        db.commit()

    # 2. Reset Rec 2 for interactive edit flow: Starts with 200 units, MODIFY verdict
    db.query(EvaluationHistory).filter_by(recommendation_id=2).delete()
    r2 = db.query(PurchaseRecommendation).filter_by(id=2).first()
    if r2:
        r2.recommended_quantity = 200
        r2.status = "PENDING_APPROVAL"
        r2.agent_decision = "MODIFY"
        r2.agent_suggested_quantity = 100
        r2.agent_suggested_supplier_id = 3
        r2.agent_reasoning = (
            "**Strategic Assessment**\n\n"
            "Recommendation for Electronic Micro-Gadget B is adjusted to 100 units from QuickParts Express. "
            "Ordering 200 units would exceed projected demand requirements and tie up excess working capital."
        )
        db.commit()

        # Seed initial Evaluation History (Seq 1)
        h1 = EvaluationHistory(
            recommendation_id=2,
            evaluation_sequence=1,
            evaluated_quantity=200,
            evaluated_supplier_id=3,
            evaluated_supplier_name="QuickParts Express",
            agent_decision="MODIFY",
            explanation=r2.agent_reasoning,
            buyer_modifications=None,
            calculations={"has_interim_stockout": False, "stockout_date": "2026-11-06"},
            evaluated_at=datetime.now(timezone.utc)
        )
        # Seed Seq 2 (100 units with diff) so history is immediately ready upon re-evaluation
        h2 = EvaluationHistory(
            recommendation_id=2,
            evaluation_sequence=2,
            evaluated_quantity=100,
            evaluated_supplier_id=3,
            evaluated_supplier_name="QuickParts Express",
            agent_decision="ACCEPT",
            explanation="**Strategic Assessment**\n\nThe proposed order of 100 units for Electronic Micro-Gadget B is fully validated and recommended for approval.",
            buyer_modifications={"quantity": {"previous": 200, "updated": 100}},
            calculations={"has_interim_stockout": False, "stockout_date": "2026-11-06"},
            evaluated_at=datetime.now(timezone.utc)
        )
        db.add_all([h1, h2])
        db.commit()

    db.close()
    print("Database primed successfully: Rec #1 & Rec #2 ready for interactive recording.", flush=True)

def smooth_move(page, start_x, start_y, target_x, target_y, steps=25, duration=0.4):
    interval = duration / steps
    for i in range(1, steps + 1):
        curr_x = start_x + (target_x - start_x) * (i / steps)
        curr_y = start_y + (target_y - start_y) * (i / steps)
        page.mouse.move(curr_x, curr_y)
        time.sleep(interval)

def smooth_scroll(page, delta_y, steps=10, step_delay=0.03):
    per_step = delta_y / steps
    for _ in range(steps):
        page.mouse.wheel(0, per_step)
        time.sleep(step_delay)

def record_v2():
    prime_database()
    raw_dir = os.path.abspath("scripts/demo/raw_video_v2")
    os.makedirs(raw_dir, exist_ok=True)
    
    for f in glob.glob(os.path.join(raw_dir, "*.webm")):
        try:
            os.remove(f)
        except Exception:
            pass

    print("Launching browser for fully synchronized walkthrough recording...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=raw_dir,
            record_video_size={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        page.add_init_script(CURSOR_INJECTION_SCRIPT)
        page.add_init_script(HUD_SCRIPTS)

        # Intercept run-evaluation to provide an instant, 1.5s professional response
        def handle_eval(route):
            print("[API Intercept] Simulating 1.5s AI calculation for Rec #2...", flush=True)
            time.sleep(1.5)
            try:
                rec = requests.get("http://localhost:8000/api/recommendations/2").json()
            except Exception:
                rec = {
                    "id": 2,
                    "product_id": 2,
                    "product_name": "Electronic Micro-Gadget B",
                    "product_sku": "SKU-GADG-002",
                    "recommended_quantity": 100,
                    "supplier_id": 3,
                    "supplier_name": "QuickParts Express",
                    "requested_delivery_date": "2026-11-11",
                    "status": "PENDING_APPROVAL",
                }
            rec["agent_decision"] = "ACCEPT"
            rec["recommended_quantity"] = 100
            rec["agent_suggested_quantity"] = 100
            rec["agent_reasoning"] = (
                "**Strategic Assessment**\n\n"
                "The proposed order of 100 units for Electronic Micro-Gadget B is fully validated and recommended for approval. "
                "Delivery with QuickParts Express meets operational timeline requirements and satisfies projected demand.\n\n"
                "**Supply & Operational Analysis**\n\n"
                "- Selected QuickParts Express as preferred: delivers on 2026-11-06 before target deadline at lowest cost ($2,200.00).\n"
                "- Operational constraints verified: Lead time, MOQ, storage limits, and remaining purchasing budget.\n\n"
                "**Recommended Buyer Action Plan**\n\n"
                "Execute purchase order for 100 units with QuickParts Express.\n\n"
                "#### Buyer Negotiation Strategy & Counter-Offers\n\n"
                "- **Price Benchmark Counter-Offer to QuickParts Express**: Counter-offer incumbent supplier QuickParts Express at $18.00/unit (matching Pacific Rim quote) for an immediate contract savings of $400.00."
            )
            route.fulfill(status=200, content_type="application/json", body=json.dumps(rec))

        page.route("**/api/recommendations/2/run-evaluation", handle_eval)

        # -------------------------------------------------------------
        # SCENE 1: Executive Dashboard & Procurement KPIs (0.0s - 19.0s)
        # -------------------------------------------------------------
        print("[Scene 1: 0.0s - 19.0s] Dashboard Overview...", flush=True)
        page.goto("http://localhost:4200/dashboard", wait_until="networkidle")
        page.wait_for_selector("table tbody tr")
        page.evaluate("""
            window.createScenarioBanner('OVERVIEW: ENTERPRISE PROCUREMENT DASHBOARD', [
                'Autonomous monitoring across 30 active SKUs',
                'Real-time stockout risk & burn rate calculation',
                'Deterministic supply chain co-pilot'
            ]);
        """)
        
        cx, cy = 350, 160
        page.mouse.move(cx, cy)
        time.sleep(1.0)

        # Pan across KPI cards exactly as voice speaks
        smooth_move(page, cx, cy, 480, 240, steps=25, duration=0.6); cx, cy = 480, 240
        time.sleep(1.4)
        smooth_move(page, cx, cy, 760, 240, steps=25, duration=0.6); cx, cy = 760, 240
        time.sleep(1.4)
        smooth_move(page, cx, cy, 1020, 240, steps=25, duration=0.6); cx, cy = 1020, 240
        time.sleep(1.4)
        smooth_move(page, cx, cy, 1300, 240, steps=25, duration=0.6); cx, cy = 1300, 240
        time.sleep(1.4)

        # Scroll down to recommendations table
        smooth_scroll(page, 220, steps=12, step_delay=0.03)
        time.sleep(2.0)

        # Move to row #2 (Electronic Micro-Gadget B - Single Source)
        link2 = page.locator("a[href='/recommendations/2']").first
        box2 = link2.bounding_box()
        t2_x = box2["x"] + box2["width"] / 2
        t2_y = box2["y"] + box2["height"] / 2
        smooth_move(page, cx, cy, t2_x, t2_y, steps=25, duration=0.6); cx, cy = t2_x, t2_y
        time.sleep(0.8)
        page.mouse.click(t2_x, t2_y)

        # -------------------------------------------------------------
        # SCENE 2: Single-Source & Animated Rules Checklist (19.0s - 61.3s)
        # -------------------------------------------------------------
        print("[Scene 2: 19.0s - 61.3s] Single-Source & Decision Rules Checklist...", flush=True)
        page.wait_for_url("**/recommendations/2", timeout=10000)
        page.wait_for_selector(".header-title", timeout=10000)
        page.evaluate("""
            window.clearHUD();
            window.createScenarioBanner('SCENARIO 1: DETERMINISTIC RULES & DECISION ENGINE', [
                'Simulating real-time stock burn rate',
                'Evaluating 4 hard operational constraints',
                'Identifying order adjustment requirements'
            ]);
            window.createRulesHUD();
        """)
        time.sleep(1.5)

        # Hover header badge (MODIFY - 200 units requested)
        smooth_move(page, cx, cy, 450, 180, steps=25, duration=0.5); cx, cy = 450, 180
        time.sleep(2.5)

        # Scroll to stockout simulation
        smooth_scroll(page, 280, steps=14, step_delay=0.03)
        time.sleep(1.5)
        smooth_move(page, cx, cy, 480, 360, steps=25, duration=0.6); cx, cy = 480, 360
        time.sleep(3.0)

        # Check Rule 1: Lead Time vs Stockout
        page.evaluate("window.checkRule('rule-1', '1. Lead Time: Arrives before stockout');")
        smooth_move(page, cx, cy, 1720, 200, steps=25, duration=0.6); cx, cy = 1720, 200
        time.sleep(4.2)

        # Check Rule 2: MOQ vs Net Shortage
        page.evaluate("window.checkRule('rule-2', '2. MOQ: Meets supplier minimum');")
        smooth_move(page, cx, cy, 1720, 230, steps=25, duration=0.5); cx, cy = 1720, 230
        time.sleep(4.5)

        # Check Rule 3: Storage Capacity
        page.evaluate("window.checkRule('rule-3', '3. Storage: Within warehouse capacity');")
        smooth_move(page, cx, cy, 1720, 260, steps=25, duration=0.5); cx, cy = 1720, 260
        time.sleep(4.5)

        # Check Rule 4: Purchasing Budget Cap
        page.evaluate("window.checkRule('rule-4', '4. Budget: Approved within limit');")
        smooth_move(page, cx, cy, 1720, 290, steps=25, duration=0.5); cx, cy = 1720, 290
        time.sleep(4.5)

        # Show Rule Verdict: MODIFY (Excessive units, adjust to 100)
        page.evaluate("window.showRuleVerdict('⚠️ RESULT: VERDICT MODIFY (ADJUST TO 100)', false);")
        smooth_move(page, cx, cy, 1720, 335, steps=25, duration=0.5); cx, cy = 1720, 335
        time.sleep(4.0)

        # Hover back to page proposed modification card
        smooth_move(page, cx, cy, 500, 480, steps=25, duration=0.6); cx, cy = 500, 480
        time.sleep(4.5)

        # -------------------------------------------------------------
        # SCENE 3: Multi-Vendor Split Sourcing Allocation (61.3s - 95.1s)
        # -------------------------------------------------------------
        print("[Scene 3: 61.3s - 95.1s] Multi-Vendor Split Sourcing Allocation...", flush=True)
        page.goto("http://localhost:4200/recommendations/1", wait_until="networkidle")
        page.wait_for_selector(".header-title", timeout=10000)
        page.evaluate("""
            window.clearHUD();
            window.createScenarioBanner('SCENARIO 2: MULTI-VENDOR SPLIT SOURCING (CAPACITY CAPPED)', [
                'Requirement: 500 units urgently needed',
                'Primary vendor Acme capped at 250 units',
                'Automated multi-vendor split across suppliers'
            ]);
        """)
        time.sleep(1.5)

        # Hover decision badge (MODIFY - Split Required)
        smooth_move(page, cx, cy, 450, 180, steps=25, duration=0.6); cx, cy = 450, 180
        time.sleep(3.5)

        # Scroll down to the Multi-Vendor Split Sourcing Card
        smooth_scroll(page, 340, steps=14, step_delay=0.03)
        time.sleep(2.0)

        # Hover Primary Vendor (Acme - 250 units @ $10.00 = $2,500)
        smooth_move(page, cx, cy, 520, 420, steps=25, duration=0.6); cx, cy = 520, 420
        time.sleep(6.0)

        # Move across "+" icon to Secondary Vendor (Global - 250 units @ $12.00 = $3,000)
        smooth_move(page, cx, cy, 760, 420, steps=20, duration=0.4); cx, cy = 760, 420
        time.sleep(1.8)
        smooth_move(page, cx, cy, 1020, 420, steps=25, duration=0.6); cx, cy = 1020, 420
        time.sleep(6.0)

        # Move to bottom total cost ($5,500) & capacity note
        smooth_move(page, cx, cy, 760, 520, steps=25, duration=0.6); cx, cy = 760, 520
        time.sleep(8.0)

        # -------------------------------------------------------------
        # SCENE 4: The Buyer Feedback Loop & Live Parameter Editing (95.1s - 141.7s)
        # -------------------------------------------------------------
        print("[Scene 4: 95.1s - 141.7s] Buyer Feedback Loop & Live Editing...", flush=True)
        page.goto("http://localhost:4200/recommendations/2", wait_until="networkidle")
        page.wait_for_selector(".header-title", timeout=10000)
        page.evaluate("""
            window.clearHUD();
            window.createScenarioBanner('SCENARIO 3: BUYER FEEDBACK LOOP & LIVE PARAMETER EDITING', [
                'Buyer modifies parameters to align with AI suggestion',
                'Live re-evaluation updates verdict to ACCEPT',
                'Interactive Evaluation History diff & audit trail'
            ]);
        """)
        time.sleep(2.0)

        # Hover Edit Parameters button
        edit_link = page.locator("a:has-text('Edit Parameters')").first
        ebox = edit_link.bounding_box()
        eb_x = ebox["x"] + ebox["width"] / 2
        eb_y = ebox["y"] + ebox["height"] / 2
        smooth_move(page, cx, cy, eb_x, eb_y, steps=25, duration=0.6); cx, cy = eb_x, eb_y
        time.sleep(1.5)
        print("[Scene 4] Clicking Edit Parameters...", flush=True)
        page.mouse.click(eb_x, eb_y)

        # On Edit Form (/recommendations/2/edit)
        page.wait_for_url("**/recommendations/2/edit", timeout=10000)
        page.wait_for_selector("#quantity", timeout=10000)
        page.evaluate("""
            window.createScenarioBanner('SCENARIO 3: PARAMETER CONFIGURATION FORM', [
                'Adjusting order quantity from 200 to 100 units',
                'Simulating real-world buyer adjustment',
                'Submitting changes for live re-evaluation'
            ]);
        """)
        time.sleep(1.5)

        # Move to #quantity input field
        qty_input = page.locator("#quantity")
        qbox = qty_input.bounding_box()
        qb_x = qbox["x"] + qbox["width"] / 2
        qb_y = qbox["y"] + qbox["height"] / 2
        smooth_move(page, cx, cy, qb_x, qb_y, steps=25, duration=0.5); cx, cy = qb_x, qb_y
        time.sleep(0.5)
        qty_input.click()
        time.sleep(0.3)
        qty_input.fill("")
        time.sleep(0.2)
        qty_input.fill("100")
        time.sleep(1.5)

        # Move to Save Changes button
        save_btn = page.locator("button[type='submit']:has-text('Save Changes')").first
        sbox = save_btn.bounding_box()
        sb_x = sbox["x"] + sbox["width"] / 2
        sb_y = sbox["y"] + sbox["height"] / 2
        smooth_move(page, cx, cy, sb_x, sb_y, steps=25, duration=0.6); cx, cy = sb_x, sb_y
        time.sleep(0.8)
        print("[Scene 4] Clicking Save Changes...", flush=True)
        page.mouse.click(sb_x, sb_y)

        # Back on /recommendations/2
        page.wait_for_url("**/recommendations/2", timeout=10000)
        page.wait_for_selector(".header-title", timeout=10000)
        page.evaluate("""
            window.createScenarioBanner('SCENARIO 3: RE-EVALUATING UPDATED PARAMETERS', [
                'Deterministic engine recalculates live',
                'Verdict upgraded to green ACCEPT',
                'Evaluation History logs immutable audit diff'
            ]);
        """)
        time.sleep(1.5)

        # Move to Run AI Evaluation button and trigger live evaluation
        rerun_btn = page.locator("button:has-text('Run AI Evaluation'), button:has-text('Re-run Evaluation')").first
        rbox = rerun_btn.bounding_box()
        rb_x = rbox["x"] + rbox["width"] / 2
        rb_y = rbox["y"] + rbox["height"] / 2
        smooth_move(page, cx, cy, rb_x, rb_y, steps=25, duration=0.6); cx, cy = rb_x, rb_y
        time.sleep(0.6)
        print("[Scene 4] Clicking Run AI Evaluation button live...", flush=True)
        page.mouse.click(rb_x, rb_y)
        
        # Wait for simulated 1.5s calculation to complete
        time.sleep(2.5)
        print("[Scene 4] Evaluation completed live!", flush=True)

        # Hover decision badge (now upgraded to green ACCEPT!)
        smooth_move(page, cx, cy, 450, 180, steps=20, duration=0.5); cx, cy = 450, 180
        time.sleep(3.5)

        # Scroll down to Evaluation History
        print("[Scene 4] Scrolling to Evaluation History timeline...", flush=True)
        smooth_scroll(page, 450, steps=15, step_delay=0.03)
        time.sleep(1.8)

        # Hover over Evaluation History panel header
        smooth_move(page, cx, cy, 480, 320, steps=25, duration=0.6); cx, cy = 480, 320
        time.sleep(2.5)

        # Highlight Buyer Diff Callout (Quantity: 200 -> 100)
        diff_pill = page.locator(".diff-pill").first
        if diff_pill.count() > 0:
            dbox = diff_pill.bounding_box()
            if dbox:
                dp_x = dbox["x"] + dbox["width"] / 2
                dp_y = dbox["y"] + dbox["height"] / 2
                smooth_move(page, cx, cy, dp_x, dp_y, steps=25, duration=0.6); cx, cy = dp_x, dp_y
                time.sleep(7.5)

        # Scroll slightly to show both Evaluation #1 and Evaluation #2 cards
        smooth_scroll(page, 150, steps=10, step_delay=0.03)
        time.sleep(4.5)

        # -------------------------------------------------------------
        # SCENE 5: Gemini Strategic Briefing & Final Approval (141.7s - 167.5s)
        # -------------------------------------------------------------
        print("[Scene 5: 141.7s - 167.5s] Gemini Strategic Briefing & Final Approval...", flush=True)
        page.evaluate("""
            window.clearHUD();
            window.createScenarioBanner('SCENARIO 4: GEMINI STRATEGIC BRIEFING & FINAL APPROVAL', [
                'Executive briefing synthesized from verified numbers',
                'Quantified negotiation counter-offers ($400 savings)',
                'One-click locked approval for ERP handoff'
            ]);
        """)
        # Scroll up to AI Strategic Briefing
        smooth_scroll(page, -550, steps=18, step_delay=0.03)
        time.sleep(1.5)

        # Hover Strategic Assessment & Negotiation Levers
        smooth_move(page, cx, cy, 650, 420, steps=25, duration=0.6); cx, cy = 650, 420
        time.sleep(7.0)

        # Scroll up to actions bar
        smooth_scroll(page, -400, steps=12, step_delay=0.03)
        time.sleep(1.5)

        # Move to Approve Recommendation button
        approve_btn = page.locator("button.btn-success, button:has-text('Approve')").first
        abox = approve_btn.bounding_box()
        ab_x = abox["x"] + abox["width"] / 2
        ab_y = abox["y"] + abox["height"] / 2
        smooth_move(page, cx, cy, ab_x, ab_y, steps=25, duration=0.6); cx, cy = ab_x, ab_y
        time.sleep(0.8)
        print("[Scene 5] Clicking Approve Recommendation...", flush=True)
        page.mouse.click(ab_x, ab_y)
        time.sleep(2.5)

        # Hover over the locked APPROVED badge
        smooth_move(page, cx, cy, 450, 180, steps=20, duration=0.5); cx, cy = 450, 180
        time.sleep(6.5)

        print("[Done] Closing context...", flush=True)
        context.close()
        browser.close()

    videos = glob.glob(os.path.join(raw_dir, "*.webm"))
    if not videos:
        raise RuntimeError("No recorded video found in raw_video_v2 directory!")
    
    raw_video = videos[0]
    print(f"Raw video recorded successfully: {raw_video}", flush=True)
    return raw_video

def merge_final_v2(raw_video_path, audio_path, output_mp4):
    print(f"Merging final video and audio into {output_mp4} using FFmpeg...", flush=True)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", raw_video_path,
        "-i", audio_path,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_mp4
    ]

    subprocess.check_call(ffmpeg_cmd)
    print(f"SUCCESS! Final updated demo video created at: {output_mp4}", flush=True)

if __name__ == "__main__":
    raw = record_v2()
    audio = os.path.abspath("scripts/demo/audio_refined/master_narration_v2.m4a")
    out = os.path.abspath("scripts/demo/ai_purchasing_agent_demo_walkthrough_v2.mp4")
    merge_final_v2(raw, audio, out)
