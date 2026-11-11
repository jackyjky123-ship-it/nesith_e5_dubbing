"""
KhmerDub - Pipeline and Worker Controllers.
Provides background QThread workers for TTS synthesis and pipeline execution,
ensuring the desktop UI remains responsive at all times (AGENT.md Rule 3).
"""

import os
import json
import time
from typing import Optional, List, Dict, Any

from PySide6.QtCore import QThread, Signal

from core.config import RECENT_TTS_FILE, TEMP_DIR
from core.tts_engine import tts_manager, TTSResult, compute_waveform_bars, is_khmer_text
from core.secure_storage import secure_storage
from core.gemini_service import gemini_tts_service


class TestGeminiKeyWorkerThread(QThread):
    """
    Background worker thread for verifying Gemini API key connectivity
    without blocking the PySide6 UI thread.
    """
    test_finished = Signal(bool, str)

    def __init__(self, api_key: str, parent=None):
        super().__init__(parent)
        self.api_key = api_key

    def run(self):
        try:
            ok, msg = gemini_tts_service.validate_api_key(self.api_key)
            self.test_finished.emit(ok, msg)
        except Exception as e:
            self.test_finished.emit(False, f"Verification failed: {str(e)}")


class TTSWorkerThread(QThread):
    """
    Background worker thread for Text-to-Speech synthesis.
    Supports both local Meta MMS-TTS inference and Google Gemini AI TTS API,
    ensuring the UI thread remains completely responsive.
    """
    status_updated = Signal(str)
    finished_success = Signal(TTSResult)
    finished_error = Signal(str)

    def __init__(
        self,
        text: str,
        language: str = "auto",
        mode: str = "auto",
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        preset_name: Optional[str] = None,
        speed: float = 1.0,
        quality_steps: int = 8,
        engine_override: Optional[str] = None,
        gemini_model: Optional[str] = None,
        gemini_voice: Optional[str] = None,
        gemini_style: Optional[str] = None,
        gemini_instruction: Optional[str] = None,
        keep_warm: bool = True,
        parent=None
    ):
        super().__init__(parent)
        self.text = text
        self.language = language
        self.mode = mode
        self.ref_audio_path = ref_audio_path
        self.ref_text = ref_text
        self.preset_name = preset_name
        self.speed = speed
        self.quality_steps = quality_steps
        self.engine_override = engine_override
        self.gemini_model = gemini_model
        self.gemini_voice = gemini_voice
        self.gemini_style = gemini_style
        self.gemini_instruction = gemini_instruction
        self.keep_warm = keep_warm

    def run(self):
        try:
            # ---------------------------------------------------------
            # Engine 1: Google Gemini AI TTS (BYOK Cloud Engine)
            # ---------------------------------------------------------
            if self.engine_override == "gemini":
                self.status_updated.emit("Checking Gemini API credentials...")
                api_key = secure_storage.get_api_key()
                if not api_key:
                    self.finished_error.emit(
                        "Missing Gemini API key. Please enter and save your Gemini API key in the Settings tab."
                    )
                    return

                def on_gemini_progress(msg: str):
                    self.status_updated.emit(msg)

                start_time = time.time()
                audio_np, sample_rate, temp_wav_path = gemini_tts_service.generate_speech(
                    text=self.text,
                    api_key=api_key,
                    model=self.gemini_model or "gemini-3.8-flash-tts",
                    voice=self.gemini_voice or "Kore",
                    style=self.gemini_style,
                    instruction=self.gemini_instruction,
                    speed=self.speed,
                    progress_callback=on_gemini_progress
                )

                latency = time.time() - start_time
                duration = len(audio_np) / float(sample_rate)
                rtf = latency / max(0.01, duration)
                waveform_bars = compute_waveform_bars(audio_np, num_bars=40)
                resolved_lang = "km" if is_khmer_text(self.text) else "en"

                result = TTSResult(
                    audio_np=audio_np,
                    sample_rate=sample_rate,
                    duration_seconds=duration,
                    latency_seconds=latency,
                    real_time_factor=rtf,
                    temp_wav_path=temp_wav_path,
                    waveform_bars=waveform_bars,
                    text=self.text,
                    language=resolved_lang,
                    engine_name="gemini",
                    mode="gemini"
                )

                add_recent_tts(
                    text=self.text,
                    duration_sec=result.duration_seconds,
                    wav_path=result.temp_wav_path,
                    language=result.language,
                    engine="Gemini AI"
                )

                self.finished_success.emit(result)
                return

            # ---------------------------------------------------------
            # Engine 2: Local Meta MMS-TTS Khmer Engine
            # ---------------------------------------------------------
            self.status_updated.emit("Initializing speech synthesizer...")

            def on_progress(msg: str):
                self.status_updated.emit(msg)

            result = tts_manager.synthesize(
                text=self.text,
                language=self.language,
                mode=self.mode,
                ref_audio_path=self.ref_audio_path,
                ref_text=self.ref_text,
                preset_name=self.preset_name,
                speed=self.speed,
                quality_steps=self.quality_steps,
                engine_override=self.engine_override,
                progress_callback=on_progress,
                keep_warm=self.keep_warm,
            )

            # Record in recent history
            add_recent_tts(
                text=self.text,
                duration_sec=result.duration_seconds,
                wav_path=result.temp_wav_path,
                language=result.language,
                engine=result.engine_name
            )

            self.finished_success.emit(result)

        except torch_oom if "torch_oom" in locals() else MemoryError:
            self.finished_error.emit(
                "Out of memory error: The system ran out of RAM/VRAM. "
                "Try shortening your text chunk or reducing the quality steps (e.g. 8 steps)."
            )
        except Exception as e:
            err_msg = str(e)
            if "CUDA out of memory" in err_msg or "DefaultCPUAllocator: can't allocate" in err_msg:
                self.finished_error.emit(
                    "Out of memory: Insufficient memory to synthesize audio. "
                    "Try shortening your text or reducing quality steps."
                )
            else:
                self.finished_error.emit(f"Synthesis failed: {err_msg}")


def load_recent_tts() -> List[Dict[str, Any]]:
    """Loads recent TTS generations history."""
    if os.path.exists(RECENT_TTS_FILE):
        try:
            with open(RECENT_TTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Filter only entries where the audio file still exists
                    return [d for d in data if os.path.exists(d.get("wav_path", ""))]
        except Exception as e:
            print(f"[controller] Warning loading recent TTS: {e}")
    return []


def add_recent_tts(
    text: str,
    duration_sec: float,
    wav_path: str,
    language: str,
    engine: str
):
    """Appends an item to recent TTS generations and saves to disk."""
    recent = load_recent_tts()
    # Truncate preview text
    clean_text = text.replace("\n", " ").strip()
    preview = clean_text[:40] + ("..." if len(clean_text) > 40 else "")
    dur_str = f"{duration_sec:.1f} s"

    entry = {
        "text": preview,
        "full_text": text,
        "duration_str": dur_str,
        "duration_sec": duration_sec,
        "wav_path": wav_path,
        "language": language,
        "engine": engine,
        "timestamp": time.time()
    }

    # Deduplicate by path or prepend
    recent = [r for r in recent if r.get("wav_path") != wav_path]
    recent.insert(0, entry)
    recent = recent[:15]  # Keep up to 15 items

    try:
        with open(RECENT_TTS_FILE, "w", encoding="utf-8") as f:
            json.dump(recent, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[controller] Warning saving recent TTS: {e}")
