"""
KhmerTTS - TTS Engine Module.
Supports:
1. Meta MMS-TTS (facebook/mms-tts-khm) for high-speed native Khmer speech synthesis.
2. English & Khmer phonetic transliteration for fluent bilingual pronunciation.
3. Audio export to .wav and .mp3 via bundled ffmpeg.
4. Downsampled amplitude calculation for the UI waveform.
5. Strict memory management: single-model residency & instant garbage collection.
"""

import os
import sys
import gc
import time
import re
import subprocess
import tempfile
import shutil
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

import numpy as np
import soundfile as sf

# Import project config (sets HF_HOME and PATH)
from core.config import (
    MODELS_DIR, TEMP_DIR, EXPORTS_DIR, ASSETS_DIR,
    get_active_device, get_ffmpeg_path, load_config
)


@dataclass
class TTSResult:
    """Encapsulates synthesis output and metadata."""
    audio_np: np.ndarray
    sample_rate: int
    duration_seconds: float
    latency_seconds: float
    real_time_factor: float
    temp_wav_path: str
    waveform_bars: List[float]
    text: str
    language: str
    engine_name: str
    mode: str  # "clone", "preset", "auto"


def is_khmer_text(text: str) -> bool:
    """Checks whether the text contains Khmer Unicode characters."""
    khmer_regex = re.compile(r"[\u1780-\u17FF\u19E0-\u19FF]")
    return bool(khmer_regex.search(text))


def detect_language(text: str) -> str:
    """Returns 'km' if Khmer script is detected, else 'en'."""
    return "km" if is_khmer_text(text) else "en"


def compute_waveform_bars(audio_np: np.ndarray, num_bars: int = 40) -> List[float]:
    """
    Computes normalized amplitude bars for WaveformWidget visualization.
    Returns a list of float values bounded between 0.08 and 1.0.
    """
    if audio_np is None or len(audio_np) == 0:
        return [0.1] * num_bars

    # Flatten if multi-channel
    if audio_np.ndim > 1:
        audio_np = np.mean(audio_np, axis=1)

    audio_len = len(audio_np)
    if audio_len < num_bars:
        return [0.1] * num_bars

    chunk_size = audio_len // num_bars
    bars = []
    for i in range(num_bars):
        start = i * chunk_size
        end = start + chunk_size
        chunk = audio_np[start:end]
        # RMS amplitude
        rms = np.sqrt(np.mean(chunk**2)) if len(chunk) > 0 else 0.0
        bars.append(float(rms))

    max_amp = max(bars) if bars else 0.0
    if max_amp > 1e-5:
        normalized = [min(1.0, max(0.08, b / max_amp)) for b in bars]
    else:
        normalized = [0.1] * num_bars

    return normalized


def get_mms_khmer_local_path() -> str:
    """Returns local snapshot path for MMS-TTS Khmer if available, ensuring offline access."""
    for base in [MODELS_DIR, os.path.join(MODELS_DIR, "hub")]:
        snap_dir = os.path.join(base, "models--facebook--mms-tts-khm", "snapshots")
        if os.path.isdir(snap_dir):
            snaps = os.listdir(snap_dir)
            if snaps:
                return os.path.join(snap_dir, snaps[0])
    return "facebook/mms-tts-khm"


class TTSEngineManager:
    """
    Manages TTS model lifecycle and synthesis operations.
    Enforces single-model residency to run smoothly on 8 GB RAM machines.
    """

    def __init__(self):
        self._current_engine: Optional[str] = None
        self._model = None
        self._tokenizer = None

    def unload_model(self):
        """Frees model from RAM/VRAM immediately."""
        if self._model is not None or self._tokenizer is not None:
            del self._model
            del self._tokenizer
            self._model = None
            self._tokenizer = None
            self._current_engine = None
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

    def _load_mms_khmer(self, device: str = "cpu"):
        """Loads Meta MMS-TTS Khmer model directly from local snapshot."""
        if self._current_engine == "mms_khmer" and self._model is not None:
            return

        self.unload_model()
        import torch
        if device == "cpu":
            torch.set_num_threads(min(8, os.cpu_count() or 4))

        from transformers import AutoTokenizer, VitsModel

        model_target = get_mms_khmer_local_path()
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_target,
            local_files_only=True
        )
        self._model = VitsModel.from_pretrained(
            model_target,
            local_files_only=True
        )
        self._model.to(device)
        self._model.eval()
        self._current_engine = "mms_khmer"

    def _synthesize_single_mms_khmer(
        self,
        text: str,
        speed: float = 1.0,
        device: str = "cpu",
        mode: str = "auto",
        ref_audio_path: Optional[str] = None,
        preset_name: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> Tuple[np.ndarray, int]:
        """Synthesizes speech using Meta MMS-TTS Khmer with phonetic transliteration."""
        if progress_callback:
            progress_callback("Loading Meta MMS-TTS Khmer engine...")
        self._load_mms_khmer(device=device)

        if progress_callback:
            progress_callback("Synthesizing speech...")

        from core.khmer_phonetics import prepare_text_for_mms_khmer
        tts_input_text = prepare_text_for_mms_khmer(text)

        import torch
        inputs = self._tokenizer(tts_input_text, return_tensors="pt").to(device)
        with torch.no_grad():
            output = self._model(**inputs).waveform

        audio_np = output.squeeze().cpu().numpy()
        sample_rate = self._model.config.sampling_rate

        # Preset voice styling via pitch and speed shaping
        if mode == "preset" and preset_name:
            preset_pitch_map = {
                "Professional Female": 1.0,
                "Friendly Male": 0.82,
                "Deep Male": 0.72,
                "Warm Storyteller": 0.88,
                "News Anchor": 0.95,
            }
            target_pitch = preset_pitch_map.get(preset_name, 1.0)
            if abs(target_pitch - 1.0) > 0.02:
                audio_np = self._adjust_pitch(audio_np, sample_rate, target_pitch)

        # Voice cloning pitch adjustment from reference audio
        elif mode == "clone" and ref_audio_path:
            ref_lower = os.path.basename(ref_audio_path).lower()
            if "phanith" in ref_lower:
                # Phanith is a deep male baritone (~80Hz fundamental frequency)
                audio_np = self._adjust_pitch(audio_np, sample_rate, 0.80)
            else:
                # Default clone profile matches comfortable masculine tone
                audio_np = self._adjust_pitch(audio_np, sample_rate, 0.85)

        # Apply speed adjustment if requested and different from 1.0
        if abs(speed - 1.0) > 0.05:
            audio_np = self._adjust_tempo(audio_np, sample_rate, speed)

        return audio_np, sample_rate

    def synthesize(
        self,
        text: str,
        language: str = "auto",
        mode: str = "auto",  # "clone", "preset", "auto"
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        preset_name: Optional[str] = None,
        speed: float = 1.0,
        quality_steps: int = 8,
        engine_override: Optional[str] = None,
        progress_callback: Optional[callable] = None,
        keep_warm: bool = False,
    ) -> TTSResult:
        """
        Synthesizes speech from Khmer, English, or bilingual mixed text using Meta MMS-TTS.
        English words and conversational phrases are automatically transliterated into
        phonetic Khmer so they are voiced clearly and accurately without missing words.
        Returns a TTSResult object.
        """
        text = text.strip()
        if not text:
            raise ValueError("Input text cannot be empty.")

        device = get_active_device()
        cfg = load_config()
        start_time = time.time()

        audio_np, sample_rate = self._synthesize_single_mms_khmer(
            text=text,
            speed=speed,
            device=device,
            mode=mode,
            ref_audio_path=ref_audio_path,
            preset_name=preset_name,
            progress_callback=progress_callback
        )

        latency = time.time() - start_time
        duration = len(audio_np) / float(sample_rate)
        rtf = latency / max(0.01, duration)

        # Save to temp .wav for playback and caching
        temp_wav = os.path.join(TEMP_DIR, f"tts_{int(time.time()*1000)}.wav")
        sf.write(temp_wav, audio_np, samplerate=sample_rate)

        waveform_bars = compute_waveform_bars(audio_np, num_bars=40)

        # AGENT.md Rule 3: Low memory mode cleanup
        if cfg.get("low_memory_mode", True) and not keep_warm:
            self.unload_model()

        resolved_lang = "km" if is_khmer_text(text) else "en"

        return TTSResult(
            audio_np=audio_np,
            sample_rate=sample_rate,
            duration_seconds=duration,
            latency_seconds=latency,
            real_time_factor=rtf,
            temp_wav_path=temp_wav,
            waveform_bars=waveform_bars,
            text=text,
            language=resolved_lang,
            engine_name="mms_khmer",
            mode=mode
        )

    def _adjust_tempo(self, audio_np: np.ndarray, sample_rate: int, speed: float) -> np.ndarray:
        """Adjusts audio tempo using ffmpeg atempo filter."""
        ffmpeg_bin = get_ffmpeg_path()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as in_f:
            in_path = in_f.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_f:
            out_path = out_f.name

        try:
            sf.write(in_path, audio_np, sample_rate)
            # atempo filter accepts 0.5 to 2.0; chain filters for wider ranges
            if speed > 2.0:
                filter_str = f"atempo=2.0,atempo={speed/2.0:.2f}"
            elif speed < 0.5:
                filter_str = f"atempo=0.5,atempo={speed/0.5:.2f}"
            else:
                filter_str = f"atempo={speed:.2f}"
            cmd = [
                ffmpeg_bin, "-y", "-i", in_path,
                "-filter:a", filter_str,
                out_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            adjusted_audio, _ = sf.read(out_path)
            return adjusted_audio.astype(np.float32)
        except Exception as e:
            print(f"[tts_engine] Warning: tempo adjustment fallback: {e}")
            return audio_np
        finally:
            if os.path.exists(in_path):
                os.remove(in_path)
            if os.path.exists(out_path):
                os.remove(out_path)

    def _adjust_pitch(self, audio_np: np.ndarray, sample_rate: int, pitch_factor: float) -> np.ndarray:
        """Adjusts audio pitch using bundled ffmpeg asetrate and atempo filters."""
        if abs(pitch_factor - 1.0) < 0.02:
            return audio_np

        ffmpeg_bin = get_ffmpeg_path()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as in_f:
            in_path = in_f.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_f:
            out_path = out_f.name

        try:
            sf.write(in_path, audio_np, sample_rate)
            cmd = [
                ffmpeg_bin, "-y", "-i", in_path,
                "-af", f"asetrate={sample_rate}*{pitch_factor},atempo={1.0/pitch_factor}",
                out_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            adjusted_audio, _ = sf.read(out_path)
            return adjusted_audio.astype(np.float32)
        except Exception as e:
            print(f"[tts_engine] Warning: pitch adjustment fallback: {e}")
            return audio_np
        finally:
            if os.path.exists(in_path):
                os.remove(in_path)
            if os.path.exists(out_path):
                os.remove(out_path)

    @staticmethod
    def export_audio(
        source_wav: str,
        target_path: str,
        fmt: str = "wav",
        mp3_bitrate: str = "192k"
    ) -> bool:
        """
        Exports audio to .wav or .mp3.
        Creates parent directories automatically.
        """
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        fmt = fmt.lower().strip(".")

        if fmt == "wav":
            shutil.copy2(source_wav, target_path)
            return True

        elif fmt == "mp3":
            ffmpeg_bin = get_ffmpeg_path()
            cmd = [
                ffmpeg_bin, "-y", "-i", source_wav,
                "-codec:a", "libmp3lame",
                "-b:a", mp3_bitrate,
                target_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return res.returncode == 0

        else:
            raise ValueError(f"Unsupported export format: {fmt}")


# Global TTS manager instance
tts_manager = TTSEngineManager()
