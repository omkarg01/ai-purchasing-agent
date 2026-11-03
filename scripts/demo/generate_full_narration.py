import asyncio
import edge_tts
import subprocess
import os

scenes = [
    (
        "scene1_dashboard.mp3",
        "For enterprise procurement buyers, balancing daily warehouse stock, fluctuating demand, and supplier constraints is an uphill battle. The AI Purchasing Agent acts as an intelligent co-pilot, uniting deterministic supply chain rules with generative AI to evaluate purchasing recommendations with mathematical certainty."
    ),
    (
        "scene2_single_source.mp3",
        "Let's first examine a standard single-source replenishment. The deterministic engine calculates real-time burn rates and simulates stock depletion day by day to forecast the exact stockout date. It then tests qualified suppliers against hard operational rules: Does the vendor arrive before stockout? Does the order satisfy Minimum Order Quantities without exceeding warehouse storage capacity or the remaining budget? When all constraints pass, the engine issues a green Accept verdict."
    ),
    (
        "scene3_split_sourcing.mp3",
        "However, supply chains rarely follow ideal conditions. In this critical scenario, 500 units of Precision Industrial Widgets are urgently required, but our primary vendor, Acme Industrial, is hard-capped at 250 units of capacity. Rather than risking an interim stockout, the engine automatically calculates a multi-vendor split sourcing allocation: 250 units to Acme at ten dollars, and the remaining 250 units to Global Logistics, securing inventory at the lowest blended cost."
    ),
    (
        "scene4_view_history.mp3",
        "Central to this platform is human-in-the-loop governance and the buyer feedback loop. Under Evaluation History, every evaluation run is captured as an immutable snapshot. When a buyer adjusts order quantities, delivery dates, or vendor selections, the system immediately flags visual diffs, comparing previous versus updated parameters. This transparent audit trail lets procurement teams see exactly how human oversight and AI calculations converge over successive iterations."
    ),
    (
        "scene5_gemini_approval.mp3",
        "Finally, Google Gemini synthesizes the mathematical evidence into an executive procurement briefing, equipping buyers with concrete counter-offers and negotiation levers to take directly to suppliers. Once satisfied, the buyer approves the recommendation with a single click, locking the parameters and handing off a verified, audit-ready purchase order."
    )
]

async def main():
    voice = "en-US-GuyNeural"
    out_dir = os.path.abspath("scripts/demo/audio")
    os.makedirs(out_dir, exist_ok=True)
    
    total_dur = 0.0
    for filename, text in scenes:
        filepath = os.path.join(out_dir, filename)
        comm = edge_tts.Communicate(text, voice, rate="+1%", pitch="-1Hz")
        await comm.save(filepath)
        
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", filepath
        ]).decode().strip()
        dur = float(probe)
        total_dur += dur
        print(f"Generated {filename}: {dur:.2f}s")
        
    print(f"\nTotal Narration Duration: {total_dur:.2f}s ({total_dur/60:.2f} minutes)")

if __name__ == "__main__":
    asyncio.run(main())

