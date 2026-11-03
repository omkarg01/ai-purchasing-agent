import os
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath("scripts/demo/screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BADGE_STYLE = """
<style id="screenshot-badge-style">
.demo-badge {
    position: absolute;
    z-index: 999999;
    background: rgba(15, 23, 42, 0.92);
    backdrop-filter: blur(12px);
    border: 1.5px solid #38bdf8;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 0 15px rgba(56, 189, 248, 0.35);
    color: #ffffff;
    padding: 7px 16px;
    border-radius: 9999px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.04em;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    pointer-events: none;
}
.demo-badge .badge-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #38bdf8;
    box-shadow: 0 0 8px #38bdf8;
}
.demo-badge.warning {
    border-color: #f59e0b;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 0 15px rgba(245, 158, 11, 0.35);
}
.demo-badge.warning .badge-dot {
    background: #f59e0b;
    box-shadow: 0 0 8px #f59e0b;
}
.demo-badge.success {
    border-color: #10b981;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 0 15px rgba(168, 85, 247, 0.35);
}
.demo-badge.success .badge-dot {
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
}
.demo-badge.purple {
    border-color: #a855f7;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 0 15px rgba(168, 85, 247, 0.35);
}
.demo-badge.purple .badge-dot {
    background: #a855f7;
    box-shadow: 0 0 8px #a855f7;
}
</style>
"""

def inject_badges(page, badges):
    page.evaluate(f"""() => {{
        const existing = document.getElementById('screenshot-badge-style');
        if (!existing) {{
            document.head.insertAdjacentHTML('beforeend', `{BADGE_STYLE}`);
        }}
        document.querySelectorAll('.demo-badge').forEach(e => e.remove());
        const badges = {badges};
        badges.forEach(b => {{
            const div = document.createElement('div');
            div.className = 'demo-badge ' + (b.type || '');
            div.style.top = b.top;
            div.style.left = b.left;
            div.innerHTML = `<span class="badge-dot"></span><span>${{b.text}}</span>`;
            document.body.appendChild(div);
        }});
    }}""")

def capture_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # 01 Dashboard
        print("Capturing 01_dashboard_pipeline.png...")
        page.goto("http://localhost:4200/dashboard", wait_until="networkidle")
        page.wait_for_timeout(1000)
        inject_badges(page, [
            {"top": "125px", "left": "150px", "text": "KPI Metrics Overview", "type": "info"},
            {"top": "240px", "left": "400px", "text": "Stockout Risk Guard", "type": "warning"},
            {"top": "340px", "left": "950px", "text": "Active PO Pipeline", "type": "success"}
        ])
        page.screenshot(path=os.path.join(OUTPUT_DIR, "01_dashboard_pipeline.png"))

        # 02 Create Recommendation Form
        print("Capturing 02_create_recommendation.png...")
        page.goto("http://localhost:4200/recommendations/new", wait_until="networkidle")
        page.wait_for_timeout(1000)
        inject_badges(page, [
            {"top": "160px", "left": "420px", "text": "Catalog Item Selection", "type": "info"},
            {"top": "270px", "left": "620px", "text": "Target Demand & Date", "type": "purple"},
            {"top": "430px", "left": "420px", "text": "Vendor Sourcing Mode", "type": "success"}
        ])
        page.screenshot(path=os.path.join(OUTPUT_DIR, "02_create_recommendation.png"))

        # 03 Single Source Evaluation
        print("Capturing 03_single_source_evaluation.png...")
        page.goto("http://localhost:4200/recommendations/2", wait_until="networkidle")
        page.wait_for_timeout(1000)
        inject_badges(page, [
            {"top": "140px", "left": "350px", "text": "Deterministic Rule Check", "type": "info"},
            {"top": "140px", "left": "920px", "text": "Binding Verdict: MODIFY", "type": "warning"},
            {"top": "460px", "left": "480px", "text": "Storage Capacity Guard", "type": "warning"}
        ])
        page.screenshot(path=os.path.join(OUTPUT_DIR, "03_single_source_evaluation.png"))

        # 04 Edit Parameters
        print("Capturing 04_edit_parameters.png...")
        page.goto("http://localhost:4200/recommendations/2/edit", wait_until="networkidle")
        page.wait_for_timeout(1000)
        inject_badges(page, [
            {"top": "260px", "left": "420px", "text": "Interactive Parameter Edit", "type": "info"},
            {"top": "345px", "left": "780px", "text": "Quantity Override: 100 Units", "type": "purple"},
            {"top": "580px", "left": "360px", "text": "Instant Re-Evaluation", "type": "success"}
        ])
        page.screenshot(path=os.path.join(OUTPUT_DIR, "04_edit_parameters.png"))

        # 05 Evaluation History
        print("Capturing 05_evaluation_history.png...")
        page.goto("http://localhost:4200/recommendations/2", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.evaluate("window.scrollTo(0, 680)")
        page.wait_for_timeout(500)
        inject_badges(page, [
            {"top": "730px", "left": "280px", "text": "Immutable Audit Trail", "type": "info"},
            {"top": "790px", "left": "540px", "text": "Parameter Diff: 200 → 100", "type": "purple"},
            {"top": "850px", "left": "950px", "text": "Multi-Run Feedback Loop", "type": "success"}
        ])
        page.screenshot(path=os.path.join(OUTPUT_DIR, "05_evaluation_history.png"))

        # 06 Split Sourcing
        print("Capturing 06_split_sourcing.png...")
        page.goto("http://localhost:4200/recommendations/1", wait_until="networkidle")
        page.wait_for_timeout(1000)
        inject_badges(page, [
            {"top": "140px", "left": "360px", "text": "Dual-Vendor Split Allocation", "type": "purple"},
            {"top": "260px", "left": "850px", "text": "Risk Hedging Strategy", "type": "info"},
            {"top": "460px", "left": "350px", "text": "Lead Time vs Cost Trade-off", "type": "success"}
        ])
        page.screenshot(path=os.path.join(OUTPUT_DIR, "06_split_sourcing.png"))

        # 07 Gemini Briefing & Approval
        print("Capturing 07_gemini_briefing_approval.png...")
        import json
        evaluated_rec = {
            "id": 2,
            "product_id": 2,
            "product_name": "Electronic Micro-Gadget B",
            "product_sku": "SKU-GADG-002",
            "recommended_quantity": 100,
            "supplier_id": 3,
            "supplier_name": "QuickParts Express",
            "requested_delivery_date": "2026-11-11",
            "status": "PENDING_APPROVAL",
            "agent_decision": "ACCEPT",
            "agent_suggested_quantity": 100,
            "agent_suggested_supplier_id": 3,
            "agent_suggested_supplier_name": "QuickParts Express",
            "evaluated_at": "2026-11-03T14:20:00Z",
            "agent_reasoning": (
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
        }
        page.route("**/api/recommendations/2", lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(evaluated_rec)
        ))
        page.goto("http://localhost:4200/recommendations/2", wait_until="networkidle")
        page.wait_for_timeout(1000)
        inject_badges(page, [
            {"top": "130px", "left": "1280px", "text": "1-Click PO Approval", "type": "info"},
            {"top": "320px", "left": "1300px", "text": "Verdict: ACCEPT", "type": "success"},
            {"top": "930px", "left": "1260px", "text": "$400 Negotiation Alpha", "type": "purple"}
        ])
        page.screenshot(path=os.path.join(OUTPUT_DIR, "07_gemini_briefing_approval.png"))

        browser.close()
        print("All UI screenshots captured successfully!")

if __name__ == "__main__":
    capture_all()
