"""
KhmerDub - Benchmark Meta MMS-TTS Khmer Fallback
Evaluates facebook/mms-tts-khm for natural Khmer pronunciation and speed.
"""

import os
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
TEMP_DIR = os.path.join(PROJECT_DIR, "temp")

os.environ["HF_HOME"] = MODELS_DIR
os.environ["TRANSFORMERS_CACHE"] = MODELS_DIR

import torch
import soundfile as sf
from transformers import AutoTokenizer, VitsModel


def run_mms_test():
    print("=" * 60)
    print("Benchmarking Meta MMS-TTS Khmer ('facebook/mms-tts-khm')")
    print(f"Cache location: {MODELS_DIR}")
    print("=" * 60)

    start_load = time.time()
    tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-khm", cache_dir=MODELS_DIR)
    model = VitsModel.from_pretrained("facebook/mms-tts-khm", cache_dir=MODELS_DIR)
    load_time = time.time() - start_load
    print(f"✓ MMS-TTS Khmer loaded in {load_time:.2f} s")

    km_text = "សួស្តី សូមស្វាគមន៍មកកាន់ KhmerDub ដែលជាកម្មវិធីបញ្ចូលសំឡេងវីដេអូ។"
    print(f"Synthesizing: '{km_text}'...")

    start_gen = time.time()
    inputs = tokenizer(km_text, return_tensors="pt")
    with torch.no_grad():
        output = model(**inputs).waveform

    gen_time = time.time() - start_gen
    audio_np = output.squeeze().cpu().numpy()
    sr = model.config.sampling_rate

    out_file = os.path.join(TEMP_DIR, "mms_khmer.wav")
    sf.write(out_file, audio_np, samplerate=sr)
    dur = len(audio_np) / float(sr)

    print(f"✓ Generated in {gen_time:.3f} s ({dur:.2f} s audio, RTF: {gen_time / dur:.3f})")
    print(f"✓ Saved audio to: {out_file} ({os.path.getsize(out_file)/1024:.1f} KB)")


if __name__ == "__main__":
    run_mms_test()
