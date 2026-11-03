import os
from playwright.sync_api import sync_playwright

HUD_SCRIPT = """
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
        el.style.maxWidth = '360px';
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
        el.style.top = '130px';
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
        el.style.width = '340px';
        el.style.pointerEvents = 'none';
        document.body.appendChild(el);
    }
    el.innerHTML = `
        <div style="font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; color: #1e293b; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; display: flex; align-items: center; gap: 6px;">
            <span>⚖️</span> <span>DETERMINISTIC EVALUATION RULES</span>
        </div>
        <div id="rule-1" style="margin-bottom: 8px; font-size: 12.5px; color: #64748b; transition: all 0.3s ease;">○ 1. Lead Time vs Stockout</div>
        <div id="rule-2" style="margin-bottom: 8px; font-size: 12.5px; color: #64748b; transition: all 0.3s ease;">○ 2. MOQ vs Net Shortage</div>
        <div id="rule-3" style="margin-bottom: 8px; font-size: 12.5px; color: #64748b; transition: all 0.3s ease;">○ 3. Warehouse Space Limit</div>
        <div id="rule-4" style="margin-bottom: 8px; font-size: 12.5px; color: #64748b; transition: all 0.3s ease;">○ 4. Purchasing Budget Cap</div>
        <div id="rule-verdict" style="margin-top: 12px; padding: 6px 10px; background: #dcfce7; border: 1px solid #86efac; border-radius: 6px; font-weight: 700; font-size: 12px; color: #15803d; display: none;">
            ✅ RESULT: VERDICT ACCEPT
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

window.showRuleVerdict = () => {
    const el = document.getElementById('rule-verdict');
    if (el) el.style.display = 'block';
};

window.clearHUD = () => {
    const b = document.getElementById('demo-scenario-banner');
    if (b) b.remove();
    const r = document.getElementById('demo-rules-hud');
    if (r) r.remove();
};
"""

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto("http://localhost:4200/recommendations/2", wait_until="networkidle")
        page.evaluate(HUD_SCRIPT)
        page.evaluate("""
            window.createScenarioBanner('SCENARIO 1: SINGLE-SOURCE REPLENISHMENT', [
                'Simulating real-time stock burn rate',
                'Evaluating qualified supplier constraints',
                'Generating deterministic verdict'
            ]);
            window.createRulesHUD();
            window.checkRule('rule-1', '1. Lead Time: Arrives before stockout');
            window.checkRule('rule-2', '2. MOQ: Complies with order shortage');
            window.checkRule('rule-3', '3. Storage: Within warehouse limits');
            window.checkRule('rule-4', '4. Budget: Approved within limit');
            window.showRuleVerdict();
        """)
        os.makedirs("scripts/demo", exist_ok=True)
        page.screenshot(path="scripts/demo/hud_test.png")
        print("HUD test rendered to scripts/demo/hud_test.png!")
        browser.close()

if __name__ == "__main__":
    test()

