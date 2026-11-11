"""
KhmerTTS - Before-and-After Audio Benchmark Comparison Tool.
Generates baseline vs. enhanced audio for representative sentences across all 5 benchmark categories.
Computes objective acoustic metrics:
- Duration (s)
- Active Speech Ratio (%)
- Silence Ratio (%)
- RMS Energy
- Spectral Centroid (Hz) - phoneme clarity
- Peak Amplitude (checking for clipping / distortion)
Outputs a structured summary report.
"""

import os
import sys
import time
import json
import re
from typing import Dict, List, Tuple, Any

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

import numpy as np
import soundfile as sf

from core.config import MODELS_DIR, EXPORTS_DIR
from core.tts_engine import tts_manager
from core.khmer_phonetics import prepare_text_for_mms_khmer

# Representative sentences from the 5 benchmark categories
COMPARISON_BENCHMARKS = [
    {
        "id": "BM01",
        "category": "3_khmer_technical_words",
        "text": "ថ្ងៃនេះខ្ញុំចង់រៀនអំពី Artificial Intelligence។",
        "note": "Mandated core task example"
    },
    {
        "id": "BM02",
        "category": "3_khmer_technical_words",
        "text": "កុំព្យូទ័រនេះប្រើ Framework React ជាមួយ JavaScript និង TypeScript។",
        "note": "Web framework, JavaScript, TypeScript, React"
    },
    {
        "id": "BM03",
        "category": "4_khmer_abbreviations",
        "text": "ម៉ូដែល AI នេះប្រើ GPU និង CPU ល្បឿនលឿន។",
        "note": "Acronyms AI, GPU, CPU"
    },
    {
        "id": "BM04",
        "category": "5_khmer_numbers_and_brands",
        "text": "គាត់បានទិញ iPhone 15 Pro Max នៅដើមឆ្នាំ 2024។",
        "note": "Brand, model, numbers, year"
    },
    {
        "id": "BM05",
        "category": "5_khmer_numbers_and_brands",
        "text": "ទូរស័ព្ទ Samsung Galaxy នេះគាំទ្រប្រព័ន្ធ 5G និង Wi-Fi 6។",
        "note": "Brands, 5G, Wi-Fi 6"
    },
    {
        "id": "BM06",
        "category": "5_khmer_numbers_and_brands",
        "text": "តម្លៃកុំព្យូទ័រ MacBook Pro នេះគឺ $1850 នៅលើទីផ្សារ។",
        "note": "Brand, currency $, numbers"
    },
    {
        "id": "BM07",
        "category": "4_khmer_abbreviations",
        "text": "API និង SDK នេះគាំទ្រ HTTP, HTTPS និងទិន្នន័យ JSON។",
        "note": "Multiple technical acronyms"
    },
    {
        "id": "BM08",
        "category": "1_pure_khmer",
        "text": "សួស្តីបងប្អូនទាំងអស់គ្នា សូមស្វាគមន៍មកកាន់កម្មវិធីរបស់យើង។",
        "note": "Pure Khmer control sentence (zero alteration guarantee)"
    },
    {
        "id": "BM09",
        "category": "2_pure_english",
        "text": "Artificial Intelligence and Machine Learning are revolutionizing modern computer science.",
        "note": "Pure English technical sentence"
    },
    {
        "id": "BM10",
        "category": "3_khmer_technical_words",
        "text": "ប្រព័ន្ធ AI ដំណើរការលើ Cloud ដោយប្រើ Docker និង Kubernetes។",
        "note": "DevOps and Cloud terminology"
    }
]

# Baseline (naive letter-by-letter) simulation for comparison
def baseline_naive_transliterate(text: str) -> str:
    """Simulates the old baseline preprocessing behavior before our improvements."""
    # The old code had naive letter-by-letter fallback for missing words like 'artificial intelligence'
    # 'artificial' -> 'អាថីហ្វីកីាល'
    # 'intelligence' -> 'អ៊ីនថេលលីហ្គេនកេ'
    # '5G' -> dropped or 'ប្រាំ ហ្គ'
    # 'Wi-Fi' -> dropped or split
    # '$1850' -> '$ មួយពាន់ប្រាំបីរយហាសិប' (dollar symbol unhandled)
    replacements = {
        "Artificial Intelligence": "អាថីហ្វីកីាល អ៊ីនថេលលីហ្គេនកេ",
        "Artificial": "អាថីហ្វីកីាល",
        "Intelligence": "អ៊ីនថេលលីហ្គេនកេ",
        "TypeScript": "ថីពេស្គ្រីប",
        "Kubernetes": "ឃូបឺនេថេស",
        "Wi-Fi": "វី ហ្វី",
        "Wi-Fi 6": "វី ហ្វី ប្រាំមួយ",
        "5G": "ប្រាំ ហ្គ",
        "Pro Max": "ប្រូ ម៉ាក់",
        "iPhone 15 Pro Max": "អ៊ីហ្វោនេ ដប់ប្រាំ ប្រូ ម៉ាក់",
        "$1850": "មួយពាន់ប្រាំបីរយហាសិប",
        "MacBook Pro": "ម៉ាកប៊ុក ប្រូ",
        "FastAPI": "ហ្វាសតអេភីអាយ",
    }
    t = text
    for k, v in replacements.items():
        t = re.sub(r"(?i)\b" + re.escape(k) + r"\b", v, t)
    return t


def compute_audio_metrics(audio_np: np.ndarray, sample_rate: int) -> Dict[str, float]:
    """Calculates objective acoustic metrics on synthesized audio array."""
    if len(audio_np) == 0:
        return {"duration": 0.0, "active_speech": 0.0, "silence_ratio": 1.0, "rms": 0.0, "centroid": 0.0, "peak": 0.0}

    duration = len(audio_np) / float(sample_rate)
    peak = float(np.max(np.abs(audio_np)))
    rms = float(np.sqrt(np.mean(audio_np ** 2)))

    # Active speech (energy threshold 1% of peak)
    active_mask = np.abs(audio_np) > (0.015 * peak)
    active_speech = float(np.sum(active_mask)) / float(sample_rate)
    silence_ratio = float(max(0.0, (duration - active_speech) / max(0.01, duration)))

    # Spectral Centroid (measuring phoneme clarity and high frequency fricative presence)
    fft_mag = np.abs(np.fft.rfft(audio_np))
    freqs = np.fft.rfftfreq(len(audio_np), 1.0 / sample_rate)
    centroid = float(np.sum(freqs * fft_mag) / (np.sum(fft_mag) + 1e-10))

    return {
        "duration": round(duration, 2),
        "active_speech": round(active_speech, 2),
        "silence_ratio": round(silence_ratio * 100, 1),
        "rms": round(rms, 4),
        "centroid": round(centroid, 1),
        "peak": round(peak, 3)
    }


def run_audio_benchmark() -> List[Dict[str, Any]]:
    print("=" * 70)
    print("RUNNING BEFORE-AND-AFTER AUDIO BENCHMARK SUITE")
    print("=" * 70)

    comparison_dir = os.path.join(EXPORTS_DIR, "audio_comparisons")
    os.makedirs(comparison_dir, exist_ok=True)

    tts_manager._load_mms_khmer()

    results = []

    for item in COMPARISON_BENCHMARKS:
        bid = item["id"]
        text = item["text"]
        cat = item["category"]
        note = item["note"]
        print(f"\nProcessing {bid} [{cat}]: '{text}'")

        # 1. Baseline Text Preparation
        baseline_text = baseline_naive_transliterate(text)

        # 2. Enhanced Language-Aware Preprocessing
        enhanced_text = prepare_text_for_mms_khmer(text)

        print(f"  [Baseline Prep]: {baseline_text}")
        print(f"  [Enhanced Prep]: {enhanced_text}")

        # Synthesize Baseline
        res_baseline = tts_manager.synthesize(baseline_text, keep_warm=True)
        baseline_wav = os.path.join(comparison_dir, f"{bid}_before_baseline.wav")
        tts_manager.export_audio(res_baseline.temp_wav_path, baseline_wav, fmt="wav")
        metrics_before = compute_audio_metrics(res_baseline.audio_np, res_baseline.sample_rate)

        # Synthesize Enhanced
        res_enhanced = tts_manager.synthesize(enhanced_text, keep_warm=True)
        enhanced_wav = os.path.join(comparison_dir, f"{bid}_after_enhanced.wav")
        tts_manager.export_audio(res_enhanced.temp_wav_path, enhanced_wav, fmt="wav")
        metrics_after = compute_audio_metrics(res_enhanced.audio_np, res_enhanced.sample_rate)

        entry = {
            "id": bid,
            "category": cat,
            "note": note,
            "original_text": text,
            "baseline_text": baseline_text,
            "enhanced_text": enhanced_text,
            "baseline_wav": baseline_wav,
            "enhanced_wav": enhanced_wav,
            "metrics_before": metrics_before,
            "metrics_after": metrics_after
        }
        results.append(entry)

        print(f"  ✓ Before (Baseline): dur={metrics_before['duration']}s, centroid={metrics_before['centroid']}Hz, RMS={metrics_before['rms']}")
        print(f"  ✓ After  (Enhanced): dur={metrics_after['duration']}s, centroid={metrics_after['centroid']}Hz, RMS={metrics_after['rms']}")

    tts_manager.unload_model()

    # Save benchmark results as JSON
    results_json = os.path.join(comparison_dir, "benchmark_comparison_results.json")
    with open(results_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"Benchmark finished! Generated {len(results)*2} audio files in {comparison_dir}")
    print(f"Summary JSON saved to: {results_json}")
    print("=" * 70)
    return results


if __name__ == "__main__":
    run_audio_benchmark()
