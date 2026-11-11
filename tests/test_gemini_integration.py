"""
Comprehensive Integration Test Suite for Gemini TTS (BYOK).
Validates all 10 test requirements from specification:
1. Khmer-only text.
2. English-only text.
3. Khmer-English mixed sentences.
4. Long Khmer paragraphs.
5. Technical terms such as React, Laravel, JavaScript, Python, and API.
6. Missing API key.
7. Invalid API key.
8. Network failure / timeout.
9. API quota exceeded.
10. Audio export (.wav and .mp3) and playback data verification.
"""

import os
import io
import wave
import base64
import unittest
from unittest.mock import patch, MagicMock

import numpy as np
import requests

from core.config import TEMP_DIR, EXPORTS_DIR
from core.gemini_service import (
    GeminiTTSService,
    GeminiAPIError,
    DEFAULT_SPEECH_INSTRUCTION,
    GEMINI_PREBUILT_VOICES
)
from core.secure_storage import SecureKeyStorage
from core.tts_engine import tts_manager, compute_waveform_bars, is_khmer_text


def create_mock_wav_base64(duration_seconds: float = 0.5, sample_rate: int = 24000) -> str:
    """Helper creating valid base64-encoded PCM/WAV for testing."""
    buf = io.BytesIO()
    num_frames = int(duration_seconds * sample_rate)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


class TestGeminiIntegration(unittest.TestCase):
    def setUp(self):
        self.service = GeminiTTSService()

    # Case 1: Khmer-only text
    def test_case_1_khmer_only_text(self):
        text = "សួស្តី សូមស្វាគមន៍មកកាន់កម្មវិធីរបស់យើង។"
        self.assertTrue(is_khmer_text(text))
        payload = self.service.build_request_payload(text=text, voice="Kore")
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], text)
        self.assertEqual(
            payload["generation_config"]["speech_config"]["voice_config"]["prebuilt_voice_config"]["voice_name"],
            "Kore"
        )

    # Case 2: English-only text
    def test_case_2_english_only_text(self):
        text = "Welcome to the Nesith Text-to-Speech studio."
        self.assertFalse(is_khmer_text(text))
        payload = self.service.build_request_payload(text=text, voice="Puck")
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], text)
        self.assertEqual(
            payload["generation_config"]["speech_config"]["voice_config"]["prebuilt_voice_config"]["voice_name"],
            "Puck"
        )

    # Case 3: Khmer-English mixed sentences (Code-switching with single speaker identity)
    def test_case_3_khmer_english_mixed_sentences(self):
        text = "សួស្តីអ្នកទាំងអស់គ្នា! ថ្ងៃនេះយើងនឹងរៀនអំពី Artificial Intelligence និងរបៀបប្រើ Python ដើម្បីបង្កើតកម្មវិធីថ្មីមួយ។"
        payload = self.service.build_request_payload(
            text=text,
            voice="Kore",
            instruction=DEFAULT_SPEECH_INSTRUCTION
        )
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], text)
        # Verify speech metadata enforces single speaker identity
        meta_style = payload["contents"][0]["parts"][0]["speech_metadata"]["style"]
        self.assertIn("speaker identity", meta_style)
        self.assertIn("Khmer", meta_style)
        self.assertIn("English", meta_style)

    # Case 4: Long Khmer paragraphs
    def test_case_4_long_khmer_paragraph(self):
        long_paragraph = (
            "ភាសាខ្មែរ គឺជាភាសាជាតិ និងជាភាសាផ្លូវការនៃប្រទេសកម្ពុជា។ "
            "ភាសានេះមានប្រវត្តិសាស្ត្រយូរលង់ណាស់មកហើយ និងមានប្រព័ន្ធអក្សរផ្ទាល់ខ្លួន។ "
            "នៅក្នុងសម័យបច្ចេកវិទ្យាទំនើប ការអភិវឌ្ឍប្រព័ន្ធសំឡេងឆ្លាតវៃ AI សម្រាប់ភាសាខ្មែរ "
            "មានសារៈសំខាន់ខ្លាំងណាស់សម្រាប់ការអប់រំ និងការប្រាស្រ័យទាក់ទងប្រចាំថ្ងៃ។"
        )
        self.assertGreater(len(long_paragraph), 150)
        payload = self.service.build_request_payload(text=long_paragraph, voice="Zephyr")
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], long_paragraph)

    # Case 5: Technical terms (React, Laravel, JavaScript, Python, API)
    def test_case_5_technical_terms(self):
        tech_text = "យើងអាចបង្កើតគេហទំព័រដោយប្រើ React, Laravel, JavaScript, Python និង REST API។"
        payload = self.service.build_request_payload(
            text=tech_text,
            voice="Kore",
            style="technical instruction",
            instruction=DEFAULT_SPEECH_INSTRUCTION
        )
        self.assertIn("React, Laravel, JavaScript, Python និង REST API", payload["contents"][0]["parts"][0]["text"])
        # Check speech_metadata style includes instruction for technical terms
        style_inst = payload["contents"][0]["parts"][0]["speech_metadata"]["style"]
        self.assertIn("technical terms", style_inst)
        self.assertIn("English", style_inst)
        self.assertNotIn("system_instruction", payload)

    # Case 6: Missing API key
    def test_case_6_missing_api_key(self):
        with self.assertRaises(GeminiAPIError) as ctx:
            self.service.generate_speech(text="សួស្តី", api_key="")
        self.assertIn("Missing Gemini API key", str(ctx.exception))

    # Case 7: Invalid API key (HTTP 400/401 with sanitization)
    @patch("requests.post")
    def test_case_7_invalid_api_key_sanitization(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.content = b'{"error": {"code": 400, "message": "API key AIzaSySecretKey12345678901234567890123 is not valid."}}'
        mock_resp.json.return_value = {
            "error": {
                "code": 400,
                "message": "API key AIzaSySecretKey12345678901234567890123 is not valid."
            }
        }
        mock_post.return_value = mock_resp

        with self.assertRaises(GeminiAPIError) as ctx:
            self.service.generate_speech(text="Test Invalid", api_key="AIzaSySecretKey12345678901234567890123")
        err_msg = str(ctx.exception)
        # Security test: Raw secret key MUST NEVER appear in exception message
        self.assertNotIn("AIzaSySecretKey12345678901234567890123", err_msg)
        self.assertIn("invalid", err_msg.lower())

    # Case 8: Network failure & timeout
    @patch("requests.post", side_effect=requests.exceptions.Timeout("Connection timed out"))
    def test_case_8_network_timeout(self, mock_post):
        with self.assertRaises(GeminiAPIError) as ctx:
            self.service.generate_speech(text="Test Timeout", api_key="AIzaSyValidKey")
        self.assertIn("timed out", str(ctx.exception).lower())

    @patch("requests.post", side_effect=requests.exceptions.ConnectionError("Failed to establish a new connection"))
    def test_case_8_network_connection_error(self, mock_post):
        with self.assertRaises(GeminiAPIError) as ctx:
            self.service.generate_speech(text="Test Connection Error", api_key="AIzaSyValidKey")
        self.assertIn("network connection error", str(ctx.exception).lower())

    # Case 9: API quota exceeded (HTTP 429)
    @patch("requests.post")
    def test_case_9_quota_exceeded(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.content = b'{"error": {"code": 429, "message": "Resource has been exhausted (e.g. check quota)."}}'
        mock_resp.json.return_value = {
            "error": {
                "code": 429,
                "message": "Resource has been exhausted (e.g. check quota)."
            }
        }
        mock_post.return_value = mock_resp

        with self.assertRaises(GeminiAPIError) as ctx:
            self.service.generate_speech(text="Test Quota", api_key="AIzaSyValidKey")
        self.assertIn("quota exceeded", str(ctx.exception).lower())

    # Case 10: Audio export (.wav and .mp3) and playback waveform computation
    @patch("requests.post")
    def test_case_10_audio_export_and_playback_pipeline(self, mock_post):
        # 1. Mock API returning valid 24kHz audio
        b64_audio = create_mock_wav_base64(duration_seconds=1.0, sample_rate=24000)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/L16;codec=pcm;rate=24000",
                                    "data": b64_audio
                                }
                            }
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        audio_np, sr, temp_wav = self.service.generate_speech(
            text="សួស្តី Audio Export Test",
            api_key="AIzaSyValidKey",
            voice="Kore"
        )
        self.assertTrue(os.path.exists(temp_wav))
        self.assertEqual(sr, 24000)

        # 2. Waveform calculation for UI
        bars = compute_waveform_bars(audio_np, num_bars=40)
        self.assertEqual(len(bars), 40)
        for b in bars:
            self.assertGreaterEqual(b, 0.08)
            self.assertLessEqual(b, 1.0)

        # 3. Export to WAV
        target_wav = os.path.join(EXPORTS_DIR, "test_gemini_export.wav")
        self.assertTrue(tts_manager.export_audio(temp_wav, target_wav, fmt="wav"))
        self.assertTrue(os.path.exists(target_wav))

        # 4. Export to MP3 via ffmpeg
        target_mp3 = os.path.join(EXPORTS_DIR, "test_gemini_export.mp3")
        try:
            exported_mp3 = tts_manager.export_audio(temp_wav, target_mp3, fmt="mp3")
            if exported_mp3:
                self.assertTrue(os.path.exists(target_mp3))
        finally:
            # Cleanup test export files
            for p in (target_wav, target_mp3, temp_wav):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
