import os
import sys
import glob
import subprocess
import time
from playwright.sync_api import sync_playwright

# Ensure project backend is importable
sys.path.insert(0, os.path.abspath("backend"))
sys.stdout.reconfigure(line_buffering=True)

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

def ensure_state():
    from app.database.session import SessionLocal
    from app.models.purchase_recommendation import PurchaseRecommendation
    from app.models.evaluation_history import EvaluationHistory
    
    db = SessionLocal()
    r1 = db.query(PurchaseRecommendation).filter_by(id=1).first()
    if r1:
        r1.status = "PENDING_APPROVAL"
        db.commit()
        
    # Ensure R1 has a visible diff in history
    h_items = db.query(EvaluationHistory).filter_by(recommendation_id=1).order_by(EvaluationHistory.evaluation_sequence.asc()).all()
    if len(h_items) >= 2:
        h_items[1].buyer_modifications = {
            'quantity': {'previous': 600, 'updated': 500},
            'supplier': {'previous': 1, 'updated': 1, 'previous_name': 'Acme Industrial Supplies', 'updated_name': 'Acme Industrial Supplies (Split)'}
        }
        db.commit()
    db.close()
    print("Database state primed for recording: Rec #1 is PENDING_APPROVAL with rich diff history.", flush=True)

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

def record_full_walkthrough():
    ensure_state()
    raw_dir = os.path.abspath("scripts/demo/raw_video")
    os.makedirs(raw_dir, exist_ok=True)
    
    for f in glob.glob(os.path.join(raw_dir, "*.webm")):
        try:
            os.remove(f)
        except Exception:
            pass

    print("Launching browser for calibrated 2-minute walkthrough recording...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=raw_dir,
            record_video_size={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        page.add_init_script(CURSOR_INJECTION_SCRIPT)

        # -------------------------------------------------------------
        # SCENE 1: Executive Dashboard & Procurement KPIs (0.0s - 19.5s)
        # -------------------------------------------------------------
        print("[Scene 1: 0.0s - 19.5s] Navigating to Dashboard...", flush=True)
        page.goto("http://localhost:4200/dashboard", wait_until="networkidle")
        page.wait_for_selector("table tbody tr")
        page.evaluate(CURSOR_INJECTION_SCRIPT)
        
        cx, cy = 350, 160
        page.mouse.move(cx, cy)
        time.sleep(1.0)

        # Pan across KPI metric cards
        print("[Scene 1] Highlighting KPI cards...", flush=True)
        smooth_move(page, cx, cy, 480, 240, steps=25, duration=0.6); cx, cy = 480, 240
        time.sleep(1.5)
        smooth_move(page, cx, cy, 760, 240, steps=25, duration=0.6); cx, cy = 760, 240
        time.sleep(1.5)
        smooth_move(page, cx, cy, 1020, 240, steps=25, duration=0.6); cx, cy = 1020, 240
        time.sleep(1.5)
        smooth_move(page, cx, cy, 1300, 240, steps=25, duration=0.6); cx, cy = 1300, 240
        time.sleep(1.5)

        # Scroll down to recommendations table
        print("[Scene 1] Scrolling recommendations table...", flush=True)
        smooth_scroll(page, 240, steps=12, step_delay=0.04)
        time.sleep(2.5)

        # Hover over table verdicts
        smooth_move(page, cx, cy, 800, 480, steps=25, duration=0.6); cx, cy = 800, 480
        time.sleep(2.5)

        # Move to row #2 (Electronic Micro-Gadget B - Single Source)
        print("[Scene 1] Navigating to Rec #2 (Single Source)...", flush=True)
        link2 = page.locator("a[href='/recommendations/2']").first
        box2 = link2.bounding_box()
        t2_x = box2["x"] + box2["width"] / 2
        t2_y = box2["y"] + box2["height"] / 2
        smooth_move(page, cx, cy, t2_x, t2_y, steps=25, duration=0.6); cx, cy = t2_x, t2_y
        time.sleep(0.8)
        page.mouse.click(t2_x, t2_y)
        
        # -------------------------------------------------------------
        # SCENE 2: Single-Source Replenishment & Decision Rules (19.5s - 50.0s)
        # -------------------------------------------------------------
        print("[Scene 2: 19.5s - 50.0s] Loaded Rec #2 (Single Source)...", flush=True)
        page.wait_for_url("**/recommendations/2", timeout=10000)
        page.wait_for_selector(".header-title", timeout=10000)
        page.evaluate(CURSOR_INJECTION_SCRIPT)
        time.sleep(1.2)

        # Hover header badges
        smooth_move(page, cx, cy, 450, 180, steps=25, duration=0.6); cx, cy = 450, 180
        time.sleep(2.5)

        # Scroll to stockout simulation
        print("[Scene 2] Highlighting Chronological Stockout Simulation...", flush=True)
        smooth_scroll(page, 280, steps=14, step_delay=0.03)
        time.sleep(1.5)
        smooth_move(page, cx, cy, 500, 360, steps=25, duration=0.6); cx, cy = 500, 360
        time.sleep(3.5)
        smooth_move(page, cx, cy, 850, 360, steps=25, duration=0.6); cx, cy = 850, 360
        time.sleep(3.5)

        # Scroll down to supplier options and rule evaluations
        print("[Scene 2] Highlighting Supplier Constraints & Feasibility...", flush=True)
        smooth_scroll(page, 380, steps=15, step_delay=0.03)
        time.sleep(1.5)
        smooth_move(page, cx, cy, 600, 480, steps=25, duration=0.6); cx, cy = 600, 480
        time.sleep(4.5)
        smooth_move(page, cx, cy, 1100, 480, steps=25, duration=0.6); cx, cy = 1100, 480
        time.sleep(4.5)
        smooth_scroll(page, -250, steps=12, step_delay=0.03)
        time.sleep(3.5)

        # -------------------------------------------------------------
        # SCENE 3: Multi-Vendor Split Sourcing Allocation (50.0s - 82.0s)
        # -------------------------------------------------------------
        print("[Scene 3: 50.0s - 82.0s] Navigating to Rec #1 (Multi-Vendor Split)...", flush=True)
        page.goto("http://localhost:4200/recommendations/1", wait_until="networkidle")
        page.wait_for_selector(".header-title", timeout=10000)
        page.evaluate(CURSOR_INJECTION_SCRIPT)
        time.sleep(1.5)

        # Hover decision badge (MODIFY - Split Required)
        smooth_move(page, cx, cy, 450, 180, steps=25, duration=0.6); cx, cy = 450, 180
        time.sleep(3.5)

        # Scroll down to the Multi-Vendor Split Sourcing Card
        print("[Scene 3] Highlighting Multi-Vendor Split Sourcing Card...", flush=True)
        smooth_scroll(page, 340, steps=14, step_delay=0.03)
        time.sleep(2.0)

        # Hover Primary Vendor (Acme - 250 units)
        smooth_move(page, cx, cy, 520, 420, steps=25, duration=0.6); cx, cy = 520, 420
        time.sleep(5.5)

        # Move across "+" icon to Secondary Vendor (Global - 250 units)
        smooth_move(page, cx, cy, 760, 420, steps=20, duration=0.5); cx, cy = 760, 420
        time.sleep(2.0)
        smooth_move(page, cx, cy, 1020, 420, steps=25, duration=0.6); cx, cy = 1020, 420
        time.sleep(5.5)

        # Move to bottom total cost & capacity note
        smooth_move(page, cx, cy, 760, 520, steps=25, duration=0.6); cx, cy = 760, 520
        time.sleep(6.5)

        # -------------------------------------------------------------
        # SCENE 4: The Buyer Feedback Loop & View History (82.0s - 112.0s)
        # -------------------------------------------------------------
        print("[Scene 4: 82.0s - 112.0s] Scrolling to Evaluation History Section...", flush=True)
        smooth_scroll(page, 450, steps=15, step_delay=0.03)
        time.sleep(2.0)

        # Hover over Evaluation History panel header
        smooth_move(page, cx, cy, 480, 320, steps=25, duration=0.6); cx, cy = 480, 320
        time.sleep(3.5)

        # Hover over Buyer Parameter Modifications diff callout (diff-pill)
        print("[Scene 4] Highlighting Buyer Diff Callout...", flush=True)
        diff_pill = page.locator(".diff-pill").first
        if diff_pill.count() > 0:
            dbox = diff_pill.bounding_box()
            if dbox:
                dp_x = dbox["x"] + dbox["width"] / 2
                dp_y = dbox["y"] + dbox["height"] / 2
                smooth_move(page, cx, cy, dp_x, dp_y, steps=25, duration=0.6); cx, cy = dp_x, dp_y
                time.sleep(8.0)

        # Scroll slightly through historical evaluation cards
        smooth_scroll(page, 200, steps=12, step_delay=0.03)
        time.sleep(4.0)
        smooth_move(page, cx, cy, 600, 450, steps=25, duration=0.6); cx, cy = 600, 450
        time.sleep(6.5)

        # -------------------------------------------------------------
        # SCENE 5: Gemini Briefing & One-Click Approval (112.0s - 133.0s)
        # -------------------------------------------------------------
        print("[Scene 5: 112.0s - 133.0s] Scrolling to AI Strategic Briefing...", flush=True)
        # Scroll up to briefing
        smooth_scroll(page, -600, steps=18, step_delay=0.03)
        time.sleep(2.0)

        # Hover Strategic Assessment & Negotiation Levers
        smooth_move(page, cx, cy, 650, 420, steps=25, duration=0.6); cx, cy = 650, 420
        time.sleep(6.0)

        # Scroll up to top actions bar to Approve
        print("[Scene 5] Moving to Approve Button...", flush=True)
        smooth_scroll(page, -400, steps=14, step_delay=0.03)
        time.sleep(1.5)

        # Find and click Approve button
        approve_btn = page.locator("button.btn-success, button:has-text('Approve')").first
        if approve_btn.count() > 0:
            abox = approve_btn.bounding_box()
            if abox:
                ab_x = abox["x"] + abox["width"] / 2
                ab_y = abox["y"] + abox["height"] / 2
                smooth_move(page, cx, cy, ab_x, ab_y, steps=25, duration=0.6); cx, cy = ab_x, ab_y
                time.sleep(0.8)
                print("[Scene 5] Clicking Approve Recommendation!", flush=True)
                page.mouse.click(ab_x, ab_y)
                time.sleep(2.5)

        # Let the APPROVED badge display clearly
        smooth_move(page, cx, cy, 450, 180, steps=20, duration=0.5); cx, cy = 450, 180
        time.sleep(6.0)

        print("[Done] Closing recording context...", flush=True)
        context.close()
        browser.close()

    videos = glob.glob(os.path.join(raw_dir, "*.webm"))
    if not videos:
        raise RuntimeError("No recorded video found in raw_video directory!")
    
    raw_video = videos[0]
    print(f"Raw video recorded: {raw_video}", flush=True)
    return raw_video

def merge_final_demo(raw_video_path, audio_path, output_mp4):
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
    print(f"SUCCESS! Final demo video created at: {output_mp4}", flush=True)

if __name__ == "__main__":
    raw = record_full_walkthrough()
    audio = os.path.abspath("scripts/demo/audio/master_narration.m4a")
    out = os.path.abspath("scripts/demo/ai_purchasing_agent_demo_walkthrough.mp4")
    merge_final_demo(raw, audio, out)
