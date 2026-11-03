import os
from playwright.sync_api import sync_playwright

OUTPUT_DIR = os.path.abspath("scripts/demo/screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

RULES_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Enterprise Deterministic Decision Engine Rules</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    body {
      background: radial-gradient(circle at 20% 20%, #0f172a 0%, #020617 100%);
      color: #f8fafc;
      min-height: 1080px;
      width: 1920px;
      height: 1080px;
      padding: 48px 64px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      overflow: hidden;
    }
    
    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      padding-bottom: 24px;
    }
    .header-left h1 {
      font-size: 34px;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .badge-core {
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid #38bdf8;
      color: #38bdf8;
      font-size: 13px;
      font-weight: 700;
      padding: 4px 14px;
      border-radius: 9999px;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      -webkit-text-fill-color: #38bdf8;
    }
    .header-left p {
      color: #94a3b8;
      font-size: 16px;
      margin-top: 6px;
    }
    .header-right {
      display: flex;
      gap: 16px;
    }
    .metric-pill {
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      padding: 10px 20px;
      text-align: right;
    }
    .metric-pill .label { font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700; }
    .metric-pill .value { font-size: 18px; font-weight: 800; color: #38bdf8; }

    .grid-rules {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      grid-template-rows: repeat(2, 1fr);
      gap: 20px;
      margin-top: 24px;
      flex: 1;
    }

    .rule-card {
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 22px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
      overflow: hidden;
      box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);
    }
    .rule-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 3px;
      background: linear-gradient(90deg, #38bdf8, transparent);
    }
    .rule-card.warning::before {
      background: linear-gradient(90deg, #f59e0b, transparent);
    }
    .rule-card.purple::before {
      background: linear-gradient(90deg, #a855f7, transparent);
    }
    .rule-card.emerald::before {
      background: linear-gradient(90deg, #10b981, transparent);
    }

    .rule-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .rule-num {
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.1em;
      color: #38bdf8;
      text-transform: uppercase;
    }
    .rule-card.warning .rule-num { color: #f59e0b; }
    .rule-card.purple .rule-num { color: #a855f7; }
    .rule-card.emerald .rule-num { color: #10b981; }

    .rule-tag {
      font-size: 11px;
      font-weight: 700;
      padding: 2px 10px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.06);
      color: #cbd5e1;
    }

    .rule-title {
      font-size: 18px;
      font-weight: 700;
      color: #f1f5f9;
      margin-bottom: 8px;
      line-height: 1.3;
    }
    .rule-formula {
      font-family: "JetBrains Mono", Consolas, monospace;
      font-size: 12px;
      background: rgba(2, 6, 23, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 8px;
      padding: 8px 12px;
      color: #38bdf8;
      margin-bottom: 12px;
      word-break: break-all;
    }
    .rule-card.warning .rule-formula { color: #fbbf24; }
    .rule-card.purple .rule-formula { color: #c084fc; }
    .rule-card.emerald .rule-formula { color: #34d399; }

    .rule-desc {
      font-size: 13px;
      line-height: 1.5;
      color: #94a3b8;
      margin-bottom: 12px;
      flex-grow: 1;
    }

    .rule-footer {
      border-top: 1px solid rgba(255, 255, 255, 0.06);
      padding-top: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
    }
    .rule-inputs {
      color: #64748b;
      font-weight: 600;
    }
    .rule-action {
      font-weight: 700;
      color: #e2e8f0;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #10b981;
    }
    .status-dot.warn { background: #f59e0b; }

    .footer-bar {
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: #64748b;
      font-size: 13px;
    }
    .footer-bar strong { color: #cbd5e1; }
  </style>
</head>
<body>

  <div class="header">
    <div class="header-left">
      <h1>
        Deterministic Decision Engine Architecture
        <span class="badge-core">100% Zero-Hallucination Math</span>
      </h1>
      <p>8 Enterprise Procurement Verification Rules Executed Sequentially Prior to Generative AI Synthesis</p>
    </div>
    <div class="header-right">
      <div class="metric-pill">
        <div class="label">Decision Engine Latency</div>
        <div class="value">&lt; 12ms</div>
      </div>
      <div class="metric-pill">
        <div class="label">Binding Authority</div>
        <div class="value">Deterministic</div>
      </div>
      <div class="metric-pill">
        <div class="label">Audit Guarantee</div>
        <div class="value">Immutable</div>
      </div>
    </div>
  </div>

  <div class="grid-rules">
    <!-- Rule 1 -->
    <div class="rule-card">
      <div class="rule-top">
        <span class="rule-num">Rule 01</span>
        <span class="rule-tag">Depletion</span>
      </div>
      <div class="rule-title">Chronological Stockout Simulation</div>
      <div class="rule-formula">S(t) = S₀ - Σ(DailyDemand) + Σ(OpenPOs)</div>
      <div class="rule-desc">Simulates inventory day-by-day across demand horizon. Accurately isolates interim stockout events from final unmet demand.</div>
      <div class="rule-footer">
        <span class="rule-inputs">Demand, On-Hand, Open POs</span>
        <span class="rule-action"><span class="status-dot"></span>Calculates Net Shortage</span>
      </div>
    </div>

    <!-- Rule 2 -->
    <div class="rule-card warning">
      <div class="rule-top">
        <span class="rule-num">Rule 02</span>
        <span class="rule-tag">Quality</span>
      </div>
      <div class="rule-title">Shelf-Life & Spoilage Ceiling</div>
      <div class="rule-formula">OrderQty ≤ ShelfLifeDays × DailyDemand</div>
      <div class="rule-desc">Guards perishable goods against over-ordering. Rejects or adjusts order volume if arrival risks &gt;25% product expiration.</div>
      <div class="rule-footer">
        <span class="rule-inputs">Shelf Life, Daily Burn Rate</span>
        <span class="rule-action"><span class="status-dot warn"></span>Spoilage Risk Guard</span>
      </div>
    </div>

    <!-- Rule 3 -->
    <div class="rule-card purple">
      <div class="rule-top">
        <span class="rule-num">Rule 03</span>
        <span class="rule-tag">Supply</span>
      </div>
      <div class="rule-title">Supplier Fulfillment Capacity Capping</div>
      <div class="rule-formula">OrderQty ≤ SupplierAvailableCapacity</div>
      <div class="rule-desc">Validates current vendor manufacturing throughput limits to ensure suppliers do not accept unfulfillable purchase orders.</div>
      <div class="rule-footer">
        <span class="rule-inputs">Supplier Throughput Cap</span>
        <span class="rule-action"><span class="status-dot"></span>Capacity Allocation</span>
      </div>
    </div>

    <!-- Rule 4 -->
    <div class="rule-card warning">
      <div class="rule-top">
        <span class="rule-num">Rule 04</span>
        <span class="rule-tag">Logistics</span>
      </div>
      <div class="rule-title">Dynamic Storage & Volume (m³) Feasibility</div>
      <div class="rule-formula">StockAtArrival ≤ CapacitySKU &amp; Vol ≤ FacAvailable</div>
      <div class="rule-desc">Checks both SKU-level warehouse bin limits and total facility cubic meter (m³) availability upon delivery arrival.</div>
      <div class="rule-footer">
        <span class="rule-inputs">Unit m³, Facility Free m³</span>
        <span class="rule-action"><span class="status-dot warn"></span>Adjusts Order Volume</span>
      </div>
    </div>

    <!-- Rule 5 -->
    <div class="rule-card emerald">
      <div class="rule-top">
        <span class="rule-num">Rule 05</span>
        <span class="rule-tag">Reliability</span>
      </div>
      <div class="rule-title">OTIF Lateness Buffer Variance</div>
      <div class="rule-formula">EffectiveLead = LeadTime + Max(0, HistoricalDelay)</div>
      <div class="rule-desc">Pads supplier lead-time using historical On-Time In-Full (OTIF) delay variance to prevent unexpected stockouts.</div>
      <div class="rule-footer">
        <span class="rule-inputs">Historical Delay Variance</span>
        <span class="rule-action"><span class="status-dot"></span>Arrival Date Padding</span>
      </div>
    </div>

    <!-- Rule 6 -->
    <div class="rule-card emerald">
      <div class="rule-top">
        <span class="rule-num">Rule 06</span>
        <span class="rule-tag">Commercial</span>
      </div>
      <div class="rule-title">Volume Price Breaks & MOQ Optimization</div>
      <div class="rule-formula">Min(CostNet) across Supplier Price Tiers</div>
      <div class="rule-desc">Enforces supplier Minimum Order Quantities and dynamically flags tier discounts where ordering more saves net capital.</div>
      <div class="rule-footer">
        <span class="rule-inputs">Price Tiers, MOQ Threshold</span>
        <span class="rule-action"><span class="status-dot"></span>Tier Alpha Unlocked</span>
      </div>
    </div>

    <!-- Rule 7 -->
    <div class="rule-card warning">
      <div class="rule-top">
        <span class="rule-num">Rule 07</span>
        <span class="rule-tag">Finance</span>
      </div>
      <div class="rule-title">Departmental Budget Cap Feasibility</div>
      <div class="rule-formula">TotalOrderCost ≤ BudgetUncommitted</div>
      <div class="rule-desc">Hard gatekeeper validating real-time committed and uncommitted purchasing funds before purchase order authorization.</div>
      <div class="rule-footer">
        <span class="rule-inputs">PO Cost, Remaining Budget</span>
        <span class="rule-action"><span class="status-dot warn"></span>Budget Feasibility Gate</span>
      </div>
    </div>

    <!-- Rule 8 -->
    <div class="rule-card purple">
      <div class="rule-top">
        <span class="rule-num">Rule 08</span>
        <span class="rule-tag">Strategy</span>
      </div>
      <div class="rule-title">Dual-Source Split Risk Hedging</div>
      <div class="rule-formula">Alloc(A, B) = f(LeadTime, RiskScore, Cost)</div>
      <div class="rule-desc">Splits purchase order volume across multiple suppliers to balance rapid lead times, vendor risk, and total procurement spend.</div>
      <div class="rule-footer">
        <span class="rule-inputs">Supplier Risk, Lead Times</span>
        <span class="rule-action"><span class="status-dot"></span>Multi-Vendor Resilience</span>
      </div>
    </div>
  </div>

  <div class="footer-bar">
    <div><strong>Deterministic Separation of Concerns:</strong> Mathematical algorithms make binding decisions; Google Gemini synthesizes strategic explanations.</div>
    <div>AI Purchasing Agent &bull; Enterprise Supply Chain Intelligence</div>
  </div>

</body>
</html>
"""

def generate_graphic():
    temp_html = os.path.abspath("scripts/demo/rules_engine_temp.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(RULES_HTML)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(f"file:///{temp_html.replace(os.sep, '/')}", wait_until="networkidle")
        page.wait_for_timeout(1000)
        target_path = os.path.join(OUTPUT_DIR, "07_sophisticated_rules_engine.png")
        page.screenshot(path=target_path)
        print("Generated:", target_path)
        browser.close()

    if os.path.exists(temp_html):
        os.remove(temp_html)

if __name__ == "__main__":
    generate_graphic()

