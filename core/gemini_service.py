"""
KhmerTTS / Nesith TTS - Google Gemini Text-to-Speech (TTS) Service (BYOK).
Handles:
1. Speech generation via official Gemini generateContent audio modality endpoint.
2. Lightweight API key validation and model accessibility checks.
3. 24kHz linear PCM decoding and WAV container synthesis.
4. Khmer + English code-switching direction with consistent single-speaker identity.
5. Robust, key-sanitized error handling.
"""

import os
import io
import time
import base64
import wave
import re
from typing import Dict, List, Tuple, Optional, Any

import requests
import numpy as np
import soundfile as sf

from core.config import TEMP_DIR, get_ffmpeg_path
from core.quota_tracker import gemini_quota_tracker


GEMINI_TTS_MODELS: Dict[str, str] = {
    "gemini-3.8-flash-tts": "Gemini 3.8 Flash TTS (Studio Grade, Flagship)",
    "gemini-3.8-flash-lite-tts": "Gemini 3.8 Flash Lite TTS (Fast & Cost-Efficient)",
    "gemini-2.5-flash": "Gemini 2.5 Flash (Multimodal Audio)",
}

GEMINI_PREBUILT_VOICES: List[Dict[str, str]] = [
    {"id": "Kore", "name": "Kore", "gender": "Female", "desc": "Strong, firm, natural"},
    {"id": "Puck", "name": "Puck", "gender": "Male", "desc": "Upbeat, lively (Default)"},
    {"id": "Zephyr", "name": "Zephyr", "gender": "Female", "desc": "Bright, clear, friendly"},
    {"id": "Charon", "name": "Charon", "gender": "Male", "desc": "Calm, professional, informative"},
    {"id": "Fenrir", "name": "Fenrir", "gender": "Male", "desc": "Passionate, energetic"},
    {"id": "Aoede", "name": "Aoede", "gender": "Female", "desc": "Relaxed, breezy, natural"},
    {"id": "Callirrhoe", "name": "Callirrhoe", "gender": "Female", "desc": "Friendly, easy-going"},
    {"id": "Autonoe", "name": "Autonoe", "gender": "Female", "desc": "Bright, cheerful"},
    {"id": "Enceladus", "name": "Enceladus", "gender": "Male", "desc": "Soft, calm, breathy"},
    {"id": "Iapetus", "name": "Iapetus", "gender": "Male", "desc": "Clear, clean, articulate"},
    {"id": "Umbriel", "name": "Umbriel", "gender": "Male", "desc": "Relaxed, casual"},
    {"id": "Algieba", "name": "Algieba", "gender": "Male", "desc": "Smooth, flowing narrator"},
    {"id": "Despina", "name": "Despina", "gender": "Female", "desc": "Smooth, gentle, soothing"},
    {"id": "Erinome", "name": "Erinome", "gender": "Female", "desc": "Clear, articulate"},
    {"id": "Algenib", "name": "Algenib", "gender": "Male", "desc": "Textured, deep, resonant"},
    {"id": "Rasalgethi", "name": "Rasalgethi", "gender": "Male", "desc": "Professional documentary narrator"},
    {"id": "Laomedeia", "name": "Laomedeia", "gender": "Female", "desc": "Positive, upbeat"},
    {"id": "Achernar", "name": "Achernar", "gender": "Female", "desc": "Soft, warm, reassuring"},
    {"id": "Alnilam", "name": "Alnilam", "gender": "Male", "desc": "Confident, authoritative"},
    {"id": "Schedar", "name": "Schedar", "gender": "Male", "desc": "Even, steady, balanced"},
    {"id": "Gacrux", "name": "Gacrux", "gender": "Female", "desc": "Mature, distinguished"},
    {"id": "Pulcherrima", "name": "Pulcherrima", "gender": "Female", "desc": "Forward, engaging"},
    {"id": "Achird", "name": "Achird", "gender": "Male", "desc": "Warm, friendly"},
    {"id": "Zubenelgenubi", "name": "Zubenelgenubi", "gender": "Male", "desc": "Casual, conversational"},
    {"id": "Vindemiatrix", "name": "Vindemiatrix", "gender": "Female", "desc": "Gentle, polite"},
    {"id": "Sadachbia", "name": "Sadachbia", "gender": "Male", "desc": "Lively, modern"},
    {"id": "Sadaltager", "name": "Sadaltager", "gender": "Male", "desc": "Knowledgeable, professor"},
    {"id": "Sulafat", "name": "Sulafat", "gender": "Female", "desc": "Warm, welcoming"},
    {"id": "Leda", "name": "Leda", "gender": "Female", "desc": "Youthful, energetic"},
    {"id": "Orus", "name": "Orus", "gender": "Male", "desc": "Calm, firm, steady"},
]

DEFAULT_SPEECH_INSTRUCTION = (
    "Speak naturally in Cambodian Khmer. When English words or technical terms appear, "
    "pronounce them correctly in English. Maintain one consistent speaker identity, "
    "voice tone, and speaking style throughout the entire recording. "
    "Do not translate, omit, or replace any words. Use a natural Cambodian speaking rhythm."
)


class GeminiAPIError(Exception):
    """Exception raised for Gemini API communication or generation failures."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GeminiTTSService:
    """Official Google Gemini Speech Generation REST API Client."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, timeout_seconds: int = 90):
        self.timeout_seconds = timeout_seconds

    def pcm_to_wav_bytes(
        self,
        pcm_data: bytes,
        sample_rate: int = 24000,
        channels: int = 1,
        sample_width: int = 2
    ) -> bytes:
        """
        Encapsulates raw linear PCM bytes (e.g. 24kHz 16-bit) in a standard RIFF/WAV header.
        """
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_data)
        return wav_buf.getvalue()

    def build_request_payload(
        self,
        text: str,
        voice: str = "Kore",
        style: Optional[str] = None,
        instruction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds the JSON payload adhering to the official Gemini speech generation documentation.
        Note: Dedicated TTS models do NOT accept 'system_instruction' (returns 400).
        All style, pronunciation, and language directions belong in speech_metadata['style'].
        """
        # Combine style and speech instructions for the speech_metadata field
        full_style_direction = (style or "natural, clear, and expressive").strip()
        if instruction and instruction.strip():
            full_style_direction = f"{full_style_direction}. {instruction.strip()}"

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": text,
                            "speech_metadata": {
                                "style": full_style_direction
                            }
                        }
                    ]
                }
            ],
            "generation_config": {
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": voice
                        }
                    }
                }
            }
        }

        return payload

    def validate_api_key(self, api_key: str) -> Tuple[bool, str]:
        """
        Performs a lightweight, zero-generation-cost API call to verify the key.
        Lists available models from Google AI endpoint without spending generation quota.
        Returns (is_valid, user_message).
        """
        if not api_key or not api_key.strip():
            return False, "API key cannot be empty."

        clean_key = api_key.strip().strip('"\'').strip()
        if clean_key.startswith("Bearer "):
            clean_key = clean_key[7:].strip()

        url = f"{self.BASE_URL}/models"
        headers = {
            "x-goog-api-key": clean_key,
            "Content-Type": "application/json"
        }
        params = {
            "key": clean_key
        }

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                models_count = len(data.get("models", []))
                return True, f"Connection successful! API key is valid ({models_count} models available)."
            
            error_msg = self.handle_api_error(resp.status_code, resp.json() if resp.content else {})
            return False, error_msg

        except requests.exceptions.Timeout:
            return False, "Connection timed out while verifying Gemini API key. Please check your internet connection."
        except requests.exceptions.ConnectionError:
            return False, "Network error: Unable to connect to Google Generative Language service."
        except Exception as e:
            return False, f"Unexpected error testing API key: {str(e)}"

    def handle_api_error(self, status_code: int, response_json: dict) -> str:
        """
        Converts Gemini HTTP error payloads into clear, user-friendly messages.
        Crucial: Strips and sanitizes any sensitive API keys (both AIza... and AQ.... auth keys).
        """
        raw_msg = ""
        if isinstance(response_json, dict) and "error" in response_json:
            err = response_json["error"]
            raw_msg = err.get("message", "")
            status = err.get("status", "")
        else:
            raw_msg = str(response_json)

        # Sanitize against any potential key string (both legacy AIza and new AQ. auth keys)
        sanitized_msg = re.sub(r"AIza[0-9A-Za-z-_]{35}|AQ\.[0-9A-Za-z-_]{30,80}", "[MASKED_KEY]", raw_msg)

        if status_code in (400, 401):
            if "API_KEY_INVALID" in sanitized_msg or "not valid" in sanitized_msg.lower():
                return "The supplied Gemini API key is invalid or unrecognized by Google AI Studio."
            return f"Bad request to Gemini API (HTTP {status_code}): {sanitized_msg}"

        if status_code == 403:
            return (
                "Permission denied (HTTP 403): Your API key does not have permission to use the "
                "Gemini Speech Generation API, or billing is not active for this project."
            )

        if status_code == 429:
            return (
                "Gemini API rate limit or quota exceeded (HTTP 429). "
                "Please wait a moment before trying again or check your Google AI Studio quota limits."
            )

        if status_code == 404:
            return (
                "Model endpoint not found (HTTP 404). "
                "The selected Gemini TTS model ID may be deprecated or unsupported in your region."
            )

        if status_code >= 500:
            return f"Google Gemini server error (HTTP {status_code}). Please try again in a moment."

        return f"Gemini API Error (HTTP {status_code}): {sanitized_msg or 'Unknown error'}"

    def generate_speech(
        self,
        text: str,
        api_key: str,
        model: str = "gemini-3.8-flash-tts",
        voice: str = "Kore",
        style: Optional[str] = "natural",
        instruction: Optional[str] = DEFAULT_SPEECH_INSTRUCTION,
        speed: float = 1.0,
        progress_callback: Optional[callable] = None
    ) -> Tuple[np.ndarray, int, str]:
        """
        Invokes Gemini Speech Generation API and returns (audio_np, sample_rate, temp_wav_path).
        """
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty.")
        if not api_key or not api_key.strip():
            raise GeminiAPIError("Missing Gemini API key. Please configure your key in Settings.")

        clean_text = text.strip()
        clean_key = api_key.strip().strip('"\'').strip()
        if clean_key.startswith("Bearer "):
            clean_key = clean_key[7:].strip()

        if progress_callback:
            progress_callback(f"Connecting to Google Gemini API ({model})...")

        url = f"{self.BASE_URL}/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": clean_key,
            "Content-Type": "application/json"
        }
        params = {
            "key": clean_key
        }

        payload = self.build_request_payload(
            text=clean_text,
            voice=voice,
            style=style,
            instruction=instruction
        )

        try:
            resp = requests.post(
                url,
                headers=headers,
                params=params,
                json=payload,
                timeout=self.timeout_seconds
            )
        except requests.exceptions.Timeout:
            raise GeminiAPIError("Generation timed out. The network or Gemini API was slow to respond.")
        except requests.exceptions.ConnectionError:
            raise GeminiAPIError("Network connection error. Please verify your internet connection.")
        except Exception as e:
            raise GeminiAPIError(f"Network error invoking Gemini TTS: {str(e)}")

        if resp.status_code != 200:
            if resp.status_code == 429:
                retry_header = resp.headers.get("Retry-After", "60")
                try:
                    retry_sec = float(retry_header)
                except ValueError:
                    retry_sec = 60.0
                gemini_quota_tracker.record_throttle(retry_sec)

            err_details = resp.json() if resp.content else {}
            err_msg = self.handle_api_error(resp.status_code, err_details)
            raise GeminiAPIError(err_msg, status_code=resp.status_code)

        if progress_callback:
            progress_callback("Decoding synthesized audio stream...")

        resp_json = resp.json()

        # Record token usage from Gemini usageMetadata
        usage_meta = resp_json.get("usageMetadata", {})
        prompt_tokens = usage_meta.get("promptTokenCount", max(1, len(clean_text) // 4))
        cand_tokens = usage_meta.get("candidatesTokenCount", 40)
        total_tokens = usage_meta.get("totalTokenCount", prompt_tokens + cand_tokens)
        gemini_quota_tracker.record_usage(prompt_tokens, cand_tokens, total_tokens)

        candidates = resp_json.get("candidates", [])
        if not candidates:
            raise GeminiAPIError("Gemini API returned an empty candidate list for audio generation.")

        first_cand = candidates[0]
        content = first_cand.get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise GeminiAPIError("Gemini API response did not contain any content parts.")

        # Find part containing inline audio data
        audio_part = None
        for part in parts:
            if "inlineData" in part:
                audio_part = part["inlineData"]
                break

        if not audio_part or "data" not in audio_part:
            raise GeminiAPIError("Gemini API did not return audio data in the generation response.")

        b64_audio = audio_part["data"]
        mime_type = audio_part.get("mimeType", "audio/wav")

        try:
            raw_audio_bytes = base64.b64decode(b64_audio)
        except Exception as e:
            raise GeminiAPIError(f"Failed to decode base64 audio response: {e}")

        # Check if returned payload is already a WAV container
        if raw_audio_bytes.startswith(b"RIFF"):
            wav_bytes = raw_audio_bytes
        else:
            # Assume 16-bit linear PCM (extract rate from mimeType if available)
            sr = 24000
            rate_match = re.search(r"rate=(\d+)", mime_type)
            if rate_match:
                try:
                    sr = int(rate_match.group(1))
                except ValueError:
                    sr = 24000
            wav_bytes = self.pcm_to_wav_bytes(raw_audio_bytes, sample_rate=sr, channels=1, sample_width=2)

        # Read into numpy array for playback and waveform analysis
        try:
            audio_np, sample_rate = sf.read(io.BytesIO(wav_bytes))
        except Exception as e:
            raise GeminiAPIError(f"Failed to parse synthesized audio stream: {e}")

        audio_np = audio_np.astype(np.float32)

        # Apply speed adjustment if requested
        if abs(speed - 1.0) > 0.05:
            if progress_callback:
                progress_callback(f"Adjusting playback tempo to {speed:.2f}x...")
            audio_np = self._adjust_tempo(audio_np, sample_rate, speed)

        temp_wav_path = os.path.join(TEMP_DIR, f"gemini_tts_{int(time.time() * 1000)}.wav")
        sf.write(temp_wav_path, audio_np, sample_rate)

        return audio_np, sample_rate, temp_wav_path

    def _adjust_tempo(self, audio_np: np.ndarray, sample_rate: int, speed: float) -> np.ndarray:
        """Adjusts audio tempo using bundled ffmpeg atempo filter."""
        ffmpeg_bin = get_ffmpeg_path()
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as in_f:
            in_path = in_f.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_f:
            out_path = out_f.name

        try:
            sf.write(in_path, audio_np, sample_rate)
            if speed > 2.0:
                filter_str = f"atempo=2.0,atempo={speed/2.0:.2f}"
            elif speed < 0.5:
                filter_str = f"atempo=0.5,atempo={speed/0.5:.2f}"
            else:
                filter_str = f"atempo={speed:.2f}"
            import subprocess
            cmd = [
                ffmpeg_bin, "-y", "-i", in_path,
                "-filter:a", filter_str,
                out_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            adjusted_audio, _ = sf.read(out_path)
            return adjusted_audio.astype(np.float32)
        except Exception as e:
            print(f"[gemini_service] Warning: tempo adjustment fallback: {e}")
            return audio_np
        finally:
            if os.path.exists(in_path):
                os.remove(in_path)
            if os.path.exists(out_path):
                os.remove(out_path)


# Global default service instance
gemini_tts_service = GeminiTTSService()
