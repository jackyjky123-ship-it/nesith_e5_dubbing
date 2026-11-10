"""
KhmerTTS - TTS Engine Spike Benchmark
Evaluates speech synthesis quality, latency, and memory footprint on CPU
for Khmer and bilingual text using Meta MMS-TTS (facebook/mms-tts-khm).

Strict constraints enforced:
- HF_HOME is pinned to project models/ directory.
- Model cache explicitly loaded from models/.
- Measures RAM footprint and synthesis time.
"""

import os
import sys
import time
import resource
import gc

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
TEMP_DIR = os.path.join(PROJECT_DIR, "temp")
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
FFMPEG_DIR = os.path.join(PROJECT_DIR, "tools", "ffmpeg")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.environ["HF_HOME"] = MODELS_DIR
os.environ["TRANSFORMERS_CACHE"] = MODELS_DIR
os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")


def get_peak_ram_mb() -> float:
    """Returns peak resident set size (RAM) in megabytes."""
    usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return usage_kb / 1024.0


def run_spike():
    print("=" * 65)
    print("KhmerTTS - Meta MMS-TTS Spike Benchmark")
    print("Execution Mode: CPU (Intel i7-8750H)")
    print(f"Model Cache: {MODELS_DIR}")
    print(f"Initial RAM: {get_peak_ram_mb():.1f} MB")
    print("=" * 65)

    from core.tts_engine import tts_manager, TTSResult

    km_text = "សួស្តី សូមស្វាគមន៍មកកាន់ KhmerTTS ដែលជាកម្មវិធីសំឡេងកម្ពុជា។"
    print(f"\n[Step 1/2] Synthesizing Khmer text: '{km_text}'...")
    res_km = tts_manager.synthesize(text=km_text, mode="auto")
    print(f"✓ Khmer generated in {res_km.latency_seconds:.2f} s ({res_km.duration_seconds:.1f} s audio, RTF: {res_km.real_time_factor:.2f})")
    print(f"  File saved: {res_km.temp_wav_path}")

    en_text = "Hello and welcome to KhmerTTS speech studio."
    print(f"\n[Step 2/2] Synthesizing English text via phonetic engine: '{en_text}'...")
    res_en = tts_manager.synthesize(text=en_text, mode="auto")
    print(f"✓ English generated in {res_en.latency_seconds:.2f} s ({res_en.duration_seconds:.1f} s audio, RTF: {res_en.real_time_factor:.2f})")
    print(f"  File saved: {res_en.temp_wav_path}")

    peak_ram = get_peak_ram_mb()

    print("\n" + "=" * 65)
    print("TTS SPIKE BENCHMARK COMPLETE — RESULTS")
    print(f"- Khmer Latency:   {res_km.latency_seconds:.2f} s ({res_km.duration_seconds:.1f} s audio)")
    print(f"- English Latency: {res_en.latency_seconds:.2f} s ({res_en.duration_seconds:.1f} s audio)")
    print(f"- Peak RAM Footprint: {peak_ram:.1f} MB (~{peak_ram/1024:.2f} GB)")
    print("=" * 65)


if __name__ == "__main__":
    run_spike()
