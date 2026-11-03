import json
import time
import requests
from playwright.sync_api import sync_playwright

def test_route():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        def handle_eval(route):
            print("Intercepted run-evaluation request! Simulating 1.5s AI calculation...")
            time.sleep(1.5)
            rec = requests.get("http://localhost:8000/api/recommendations/2").json()
            rec["agent_decision"] = "ACCEPT"
            rec["recommended_quantity"] = 100
            rec["agent_suggested_quantity"] = 100
            route.fulfill(status=200, content_type="application/json", body=json.dumps(rec))

        page.route("**/api/recommendations/2/run-evaluation", handle_eval)

        page.goto("http://localhost:4200/recommendations/2", wait_until="networkidle")
        rerun_btn = page.locator("button:has-text('Run AI Evaluation'), button:has-text('Re-run Evaluation')").first
        rerun_btn.click()
        print("Clicked button, waiting for decision badge update...")
        page.wait_for_timeout(2000)
        badge = page.locator(".header-card app-status-badge[type='decision']").first
        print("Header badge text:", badge.inner_text())
        
        diff = page.locator(".diff-pill").first
        print("Diff pill count:", page.locator(".diff-pill").count())
        if page.locator(".diff-pill").count() > 0:
            print("Found diff pill:", diff.is_visible())
        browser.close()

if __name__ == "__main__":
    test_route()
