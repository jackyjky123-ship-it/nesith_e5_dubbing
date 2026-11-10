"""
KhmerDub - Step 1: OmniVoice Spike Test
Evaluates speech synthesis quality, latency, and memory footprint on CPU
for English and Khmer text using optimized step count (num_step=8).

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

# 1. HARD RULE 3: Set HF_HOME before ANY AI/ML imports
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    print("KhmerDub - Phase 1: OmniVoice Spike Test")
    print("Execution Mode: CPU (Intel i7-8750H, num_step=8)")
    print(f"Model Cache: {MODELS_DIR}")
    print(f"Initial RAM: {get_peak_ram_mb():.1f} MB")
    print("=" * 65)

    # 2. Imports after HF_HOME is locked
    import torch
    import soundfile as sf
    from omnivoice import OmniVoice

    en_output_path = os.path.join(TEMP_DIR, "spike_en.wav")
    km_output_path = os.path.join(TEMP_DIR, "spike_km.wav")

    # 3. Load OmniVoice model
    print("\n[Step 1/3] Loading OmniVoice from local cache...")
    start_load = time.time()

    model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map="cpu",
        dtype=torch.float32,
        cache_dir=MODELS_DIR
    )

    load_time = time.time() - start_load
    ram_after_load = get_peak_ram_mb()
    print(f"✓ Model loaded in {load_time:.2f} s | RAM: {ram_after_load:.1f} MB")

    sample_rate = 24000
    for attr in ("sample_rate", "sampling_rate", "audio_sample_rate"):
        if hasattr(model, attr):
            sample_rate = getattr(model, attr)
            break
        elif hasattr(model, "config") and hasattr(model.config, attr):
            sample_rate = getattr(model.config, attr)
            break
    print(f"Sampling rate: {sample_rate} Hz")

    # 4. Synthesize English sentence
    en_text = "Hello and welcome to KhmerDub, an offline video dubbing studio."
    print(f"\n[Step 2/3] Synthesizing English (8 steps): '{en_text}'...")
    start_en = time.time()

    en_outputs = model.generate(
        text=en_text,
        language="en",
        num_step=8
    )
    en_time = time.time() - start_en
    en_audio_np = en_outputs[0] if isinstance(en_outputs, list) else en_outputs

    sf.write(en_output_path, en_audio_np, samplerate=sample_rate)
    en_dur = len(en_audio_np) / float(sample_rate)
    print(f"✓ English generated in {en_time:.2f} s ({en_dur:.1f} s audio, RTF: {en_time / max(0.1, en_dur):.2f})")
    print(f"  File saved: {en_output_path} ({os.path.getsize(en_output_path) / 1024:.1f} KB)")

    # 5. Synthesize Khmer sentence
    km_text = "សួស្តី សូមស្វាគមន៍មកកាន់ KhmerDub ដែលជាកម្មវិធីបញ្ចូលសំឡេងវីដេអូ។"
    print(f"\n[Step 3/3] Synthesizing Khmer (8 steps): '{km_text}'...")
    start_km = time.time()

    km_outputs = model.generate(
        text=km_text,
        language="km",
        num_step=8
    )
    km_time = time.time() - start_km
    km_audio_np = km_outputs[0] if isinstance(km_outputs, list) else km_outputs

    sf.write(km_output_path, km_audio_np, samplerate=sample_rate)
    km_dur = len(km_audio_np) / float(sample_rate)
    print(f"✓ Khmer generated in {km_time:.2f} s ({km_dur:.1f} s audio, RTF: {km_time / max(0.1, km_dur):.2f})")
    print(f"  File saved: {km_output_path} ({os.path.getsize(km_output_path) / 1024:.1f} KB)")

    peak_ram = get_peak_ram_mb()

    # 6. Memory cleanup check (per AGENT.md Rule 3)
    del model
    del en_outputs
    del km_outputs
    gc.collect()

    print("\n" + "=" * 65)
    print("PHASE 1 SPIKE TEST COMPLETE — BENCHMARK RESULTS")
    print(f"- OmniVoice Model Load Time: {load_time:.2f} s")
    print(f"- English Generation Time:   {en_time:.2f} s ({en_dur:.1f} s audio)")
    print(f"- Khmer Generation Time:     {km_time:.2f} s ({km_dur:.1f} s audio)")
    print(f"- Peak RAM Footprint:        {peak_ram:.1f} MB (~{peak_ram/1024:.2f} GB)")
    print(f"- Models Cache Path:         {MODELS_DIR}")
    print(f"- Generated Audio Files:     {en_output_path}, {km_output_path}")
    print("=" * 65)


if __name__ == "__main__":
    run_spike()
