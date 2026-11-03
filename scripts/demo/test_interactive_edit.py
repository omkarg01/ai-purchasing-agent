import time
from playwright.sync_api import sync_playwright

def test_interactive_edit():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # 1. Open Rec 2
        print("Opening Rec 2...")
        page.goto("http://localhost:4200/recommendations/2", wait_until="networkidle")
        
        # 2. Click Run AI Evaluation
        rerun_btn = page.locator("button:has-text('Run AI Evaluation'), button:has-text('Re-run Evaluation')").first
        print("Clicking Run AI Evaluation and waiting for API...")
        with page.expect_response("**/run-evaluation", timeout=25000):
            rerun_btn.click()
            
        page.wait_for_timeout(1500)
        diff_pill = page.locator(".diff-pill")
        print("Diff pills count:", diff_pill.count())
        if diff_pill.count() > 0:
            print("Diff text:", diff_pill.first.inner_text().replace("\n", " "))
            
        print("Latest decision badge:", page.locator("app-status-badge[type='decision']").inner_text())
        browser.close()

if __name__ == "__main__":
    test_interactive_edit()
