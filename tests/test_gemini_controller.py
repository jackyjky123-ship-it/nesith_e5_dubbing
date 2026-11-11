"""
Unit tests for controller.py with Gemini integration.
Tests background TTSWorkerThread execution with Gemini engine and TestGeminiKeyWorkerThread.
"""

import os
import sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

from PySide6.QtWidgets import QApplication

# Ensure Qt GUI application exists for workers and widgets
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from core.controller import TTSWorkerThread, TestGeminiKeyWorkerThread
from core.tts_engine import TTSResult


class TestGeminiController(unittest.TestCase):
    @patch("core.secure_storage.SecureKeyStorage.get_api_key", return_value="AIzaSyMockKeyForController")
    @patch("core.gemini_service.GeminiTTSService.generate_speech")
    def test_worker_thread_gemini_success(self, mock_gen, mock_key):
        dummy_audio = np.zeros(24000, dtype=np.float32)
        mock_gen.return_value = (dummy_audio, 24000, "/tmp/mock_gemini.wav")

        worker = TTSWorkerThread(
            text="សួស្តី Hello World",
            engine_override="gemini",
            gemini_model="gemini-3.8-flash-tts",
            gemini_voice="Kore",
            gemini_style="natural",
            gemini_instruction="Speak clearly"
        )

        results = []
        errors = []
        worker.finished_success.connect(lambda res: results.append(res))
        worker.finished_error.connect(lambda err: errors.append(err))

        worker.run()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.engine_name, "gemini")
        self.assertEqual(res.sample_rate, 24000)
        self.assertEqual(res.text, "សួស្តី Hello World")
        self.assertGreaterEqual(len(res.waveform_bars), 20)

    @patch("core.secure_storage.SecureKeyStorage.get_api_key", return_value=None)
    def test_worker_thread_gemini_missing_key(self, mock_key):
        worker = TTSWorkerThread(
            text="សួស្តី No Key",
            engine_override="gemini"
        )
        errors = []
        worker.finished_error.connect(lambda err: errors.append(err))

        worker.run()

        self.assertEqual(len(errors), 1)
        self.assertIn("key", errors[0].lower())

    @patch("core.gemini_service.GeminiTTSService.validate_api_key", return_value=(True, "Key is valid"))
    def test_test_key_worker_thread_success(self, mock_val):
        worker = TestGeminiKeyWorkerThread(api_key="AIzaSyValidKey")
        statuses = []
        worker.test_finished.connect(lambda ok, msg: statuses.append((ok, msg)))

        worker.run()

        self.assertEqual(len(statuses), 1)
        self.assertTrue(statuses[0][0])
        self.assertEqual(statuses[0][1], "Key is valid")
