import os
import sys
import glob
import subprocess
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(line_buffering=True)

CURSOR_INJECTION_SCRIPT = """
(() => {
    if (document.getElementById('demo-cursor')) return;
    const cursor = document.createElement('div');
    cursor.id = 'demo-cursor';
    cursor.style.position = 'fixed';
    cursor.style.zIndex = '2147483647';
    cursor.style.width = '26px';
    cursor.style.height = '26px';
    cursor.style.borderRadius = '50%';
    cursor.style.backgroundColor = 'rgba(37, 99, 235, 0.45)';
    cursor.style.border = '2.5px solid #2563eb';
    cursor.style.boxShadow = '0 0 16px rgba(37, 99, 235, 0.6)';
    cursor.style.pointerEvents = 'none';
    cursor.style.transform = 'translate(-50%, -50%)';
    cursor.style.transition = 'transform 0.08s ease-out, background-color 0.15s';
    cursor.style.left = '300px';
    cursor.style.top = '160px';

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
        cursor.style.transform = 'translate(-50%, -50%) scale(0.7)';
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

def smooth_move(page, start_x, start_y, target_x, target_y, steps=25, duration=0.4):
    interval = duration / steps
    for i in range(1, steps + 1):
        curr_x = start_x + (target_x - start_x) * (i / steps)
        curr_y = start_y + (target_y - start_y) * (i / steps)
        page.mouse.move(curr_x, curr_y)
        time.sleep(interval)

def record():
    raw_dir = os.path.abspath("scripts/demo/raw_video")
    os.makedirs(raw_dir, exist_ok=True)
    
    # Remove older webm files
    for f in glob.glob(os.path.join(raw_dir, "*.webm")):
        try:
            os.remove(f)
        except Exception:
            pass

    print("Launching browser for recording...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=raw_dir,
            record_video_size={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        page.add_init_script(CURSOR_INJECTION_SCRIPT)

        # 1. Dashboard View (0.0s - 3.5s)
        print("Opening dashboard...", flush=True)
        page.goto("http://localhost:4200/dashboard", wait_until="networkidle")
        page.wait_for_selector("table tbody tr")
        page.evaluate(CURSOR_INJECTION_SCRIPT)
        
        # Position cursor at top left
        page.mouse.move(300, 160)
        time.sleep(0.5)

        # Pan across KPI metrics
        print("Pan across KPI metric cards...", flush=True)
        smooth_move(page, 300, 160, 480, 240, steps=20, duration=0.45)
        time.sleep(0.5)
        smooth_move(page, 480, 240, 760, 240, steps=20, duration=0.45)
        time.sleep(0.5)
        smooth_move(page, 760, 240, 1020, 240, steps=20, duration=0.45)
        time.sleep(0.4)

        # Move to first recommendation link
        print("Locating first recommendation row...", flush=True)
        link = page.locator("a[href='/recommendations/1']").first
        box = link.bounding_box()
        
        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2
        
        print(f"Moving to review button at ({target_x}, {target_y})...", flush=True)
        smooth_move(page, 1020, 240, target_x, target_y, steps=25, duration=0.5)
        time.sleep(0.2)
        
        # Click via mouse
        print("Clicking recommendation...", flush=True)
        page.mouse.click(target_x, target_y)

        # 2. Recommendation Detail View (3.5s - 10.5s)
        print("Waiting for detail view to load...", flush=True)
        page.wait_for_url("**/recommendations/1", timeout=8000)
        page.wait_for_selector(".header-title", timeout=8000)
        page.evaluate(CURSOR_INJECTION_SCRIPT)
        time.sleep(0.5)

        # Move cursor to AI decision badge
        print("Hovering AI decision badge...", flush=True)
        smooth_move(page, target_x, target_y, 450, 180, steps=20, duration=0.5)
        time.sleep(0.8)

        # Smooth scroll down to highlight AI strategic evaluation points
        print("Scrolling through AI decision analysis & supplier comparison...", flush=True)
        for _ in range(3):
            page.mouse.wheel(0, 150)
            time.sleep(0.3)
        
        smooth_move(page, 450, 180, 680, 450, steps=25, duration=0.6)
        time.sleep(1.8)

        print("Finalizing video capture...", flush=True)
        context.close()
        browser.close()

    videos = glob.glob(os.path.join(raw_dir, "*.webm"))
    if not videos:
        raise RuntimeError("No recorded video found in raw_video directory!")
    
    raw_video = videos[0]
    print(f"Raw video recorded successfully: {raw_video}", flush=True)
    return raw_video

def merge_audio_and_video(raw_video_path, audio_path, output_mp4):
    print(f"Merging video and audio into {output_mp4} using FFmpeg...", flush=True)

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", raw_video_path,
        "-i", audio_path,
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_mp4
    ]

    subprocess.check_call(ffmpeg_cmd)
    print(f"SUCCESS: Final demo video generated at {output_mp4}", flush=True)

if __name__ == "__main__":
    raw = record()
    audio = os.path.abspath("scripts/demo/narration_10s.mp3")
    out = os.path.abspath("scripts/demo/ai_purchasing_agent_10s_demo.mp4")
    merge_audio_and_video(raw, audio, out)
