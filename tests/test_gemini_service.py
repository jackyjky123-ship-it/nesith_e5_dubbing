"""
Unit tests for GeminiTTSService.
Verifies API request schemas, voice mappings, PCM-to-WAV conversion,
key validation, and error sanitization.
"""

import io
import wave
import unittest
import numpy as np
from unittest.mock import patch, MagicMock

from core.gemini_service import (
    GeminiTTSService,
    GeminiAPIError,
    GEMINI_TTS_MODELS,
    GEMINI_PREBUILT_VOICES,
    DEFAULT_SPEECH_INSTRUCTION
)


class TestGeminiService(unittest.TestCase):
    def setUp(self):
        self.service = GeminiTTSService()

    def test_default_models_and_voices_exist(self):
        self.assertIn("gemini-3.8-flash-tts", GEMINI_TTS_MODELS)
        self.assertIn("gemini-3.8-flash-lite-tts", GEMINI_TTS_MODELS)
        self.assertGreaterEqual(len(GEMINI_PREBUILT_VOICES), 20)

        voice_ids = [v["id"] for v in GEMINI_PREBUILT_VOICES]
        self.assertIn("Kore", voice_ids)
        self.assertIn("Puck", voice_ids)
        self.assertIn("Zephyr", voice_ids)
        self.assertIn("Aoede", voice_ids)

    def test_default_instruction_contains_khmer_english_single_speaker(self):
        self.assertIn("Khmer", DEFAULT_SPEECH_INSTRUCTION)
        self.assertIn("English", DEFAULT_SPEECH_INSTRUCTION)
        self.assertIn("speaker identity", DEFAULT_SPEECH_INSTRUCTION)

    def test_pcm_to_wav_conversion_produces_valid_wav(self):
        # Generate 0.5s of 24kHz 16-bit PCM silence
        pcm_data = b"\x00\x00" * 12000
        wav_bytes = self.service.pcm_to_wav_bytes(pcm_data, sample_rate=24000, channels=1, sample_width=2)
        
        # Check header
        self.assertTrue(wav_bytes.startswith(b"RIFF"))
        self.assertIn(b"WAVE", wav_bytes[:12])

        # Validate with wave module
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), 24000)
            self.assertEqual(wf.getnframes(), 12000)

    def test_build_request_payload_structure(self):
        payload = self.service.build_request_payload(
            text="សួស្តី Hello World",
            voice="Kore",
            style="cheerful",
            instruction=DEFAULT_SPEECH_INSTRUCTION
        )
        # Validate schema adheres to official Gemini speech-generation doc
        self.assertIn("contents", payload)
        self.assertEqual(payload["contents"][0]["role"], "user")
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], "សួស្តី Hello World")
        self.assertIn("speech_metadata", payload["contents"][0]["parts"][0])
        # Verify system_instruction is NOT present (TTS models reject it with 400)
        self.assertNotIn("system_instruction", payload)
        
        gen_cfg = payload["generation_config"]
        self.assertEqual(gen_cfg["response_modalities"], ["AUDIO"])
        v_name = gen_cfg["speech_config"]["voice_config"]["prebuilt_voice_config"]["voice_name"]
        self.assertEqual(v_name, "Kore")

    @patch("requests.get")
    def test_validate_api_key_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "models/gemini-3.8-flash-tts"}]}
        mock_get.return_value = mock_resp

        ok, msg = self.service.validate_api_key('"AQ.Ab8MockAuthKey1234567890"')
        self.assertTrue(ok)
        self.assertIn("valid", msg.lower())
        # Verify query param and header were called with stripped key
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["key"], "AQ.Ab8MockAuthKey1234567890")
        self.assertEqual(kwargs["headers"]["x-goog-api-key"], "AQ.Ab8MockAuthKey1234567890")

    @patch("requests.get")
    def test_validate_api_key_invalid_400(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"error": {"message": "API key not valid. Please pass a valid API key."}}
        mock_get.return_value = mock_resp

        ok, msg = self.service.validate_api_key("AQ.Ab8MockAuthKey1234567890")
        self.assertFalse(ok)
        self.assertIn("invalid", msg.lower())
        # Crucial security check: Never leak raw API key (both AIza and AQ auth keys)
        self.assertNotIn("AQ.Ab8MockAuthKey1234567890", msg)

    @patch("requests.post")
    def test_generate_speech_success(self, mock_post):
        # Create a tiny 0.1s dummy WAV
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(b"\x00\x00" * 2400)
        wav_raw = buf.getvalue()

        import base64
        b64_data = base64.b64encode(wav_raw).decode("utf-8")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/wav",
                                    "data": b64_data
                                }
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        audio_np, sr, wav_path = self.service.generate_speech(
            text="សួស្តី Hello",
            api_key="AIzaSyMockKey",
            voice="Kore"
        )
        self.assertIsInstance(audio_np, np.ndarray)
        self.assertEqual(sr, 24000)
        self.assertTrue(len(audio_np) > 0)
        self.assertTrue(wav_path.endswith(".wav"))
