import asyncio
import edge_tts
import subprocess
import os

scenes = [
    (
        "scene1_dashboard.mp3",
        "For enterprise procurement buyers, balancing warehouse inventory, shifting burn rates, and vendor lead times is an uphill battle. The AI Purchasing Agent serves as an intelligent co-pilot, uniting deterministic supply chain rules with generative AI to evaluate purchasing recommendations with mathematical certainty."
    ),
    (
        "scene2_single_source.mp3",
        "Let's first examine a standard single-source replenishment for Electronic Micro-Gadgets. The deterministic engine projects inventory day by day to forecast the exact stockout date. On the right, notice the four hard operational constraints the agent evaluates: First, does the vendor's lead time arrive before stockout? Second, does the order satisfy Minimum Order Quantities? Third, is there sufficient physical warehouse capacity? And fourth, does it fit within the uncommitted purchasing budget? Here, all constraints pass, but the initial order of 200 units is excessive, so the engine recommends adjusting down to 100 units to preserve working capital."
    ),
    (
        "scene3_split_sourcing.mp3",
        "Supply chains rarely follow ideal conditions. In this critical scenario, 500 units of Precision Industrial Widgets are required, but our primary vendor, Acme Industrial, is hard-capped at 250 units of capacity. Rather than failing the order or causing an interim stockout, the engine automatically calculates a multi-vendor split sourcing allocation: 250 units to Acme at ten dollars, and the remaining 250 units to Global Logistics. This guarantees on-time delivery while keeping total procurement spend optimized."
    ),
    (
        "scene4_feedback_loop.mp3",
        "Central to this platform is human-in-the-loop governance and the buyer feedback loop. Let's see how a buyer optimizes an order in real time. Seeing the agent's recommendation to reduce units, the buyer clicks Edit Parameters. In the configuration form, they adjust the quantity from 200 down to 100 units and click Save Changes. Back on the evaluation screen, the buyer triggers re-evaluation. The deterministic engine re-calculates, immediately upgrading the verdict to a clean green Accept! Under Evaluation History, the system now displays multiple evaluation runs with an immutable audit diff, highlighting Quantity: 200 to 100. This provides complete visibility into how buyer decisions refine the purchasing outcome."
    ),
    (
        "scene5_gemini_approval.mp3",
        "Finally, Google Gemini synthesizes all mathematical evidence into a structured executive briefing, even providing concrete negotiation levers, such as a price counter-offer to save 400 dollars with alternative suppliers. Once satisfied, the buyer approves the recommendation with a single click. The order is locked against unauthorized edits and prepped for ERP transmission, delivering faster, smarter, and audit-proof purchasing decisions."
    )
]

async def main():
    voice = "en-US-GuyNeural"
    out_dir = os.path.abspath("scripts/demo/audio_refined")
    os.makedirs(out_dir, exist_ok=True)
    
    total_dur = 0.0
    for filename, text in scenes:
        filepath = os.path.join(out_dir, filename)
        comm = edge_tts.Communicate(text, voice, rate="+2%", pitch="-1Hz")
        await comm.save(filepath)
        
        probe = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", filepath
        ]).decode().strip()
        dur = float(probe)
        total_dur += dur
        print(f"Generated {filename}: {dur:.2f}s")
        
    print(f"\nTotal Refined Narration Duration: {total_dur:.2f}s ({total_dur/60:.2f} minutes)")

if __name__ == "__main__":
    asyncio.run(main())

