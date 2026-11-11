"""
UI unit tests for TextToSpeechTab Gemini engine switching and controls.
"""

import os
import sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from ui.tts_tab import TextToSpeechTab
from core.gemini_service import DEFAULT_SPEECH_INSTRUCTION


class TestTTSTabGemini(unittest.TestCase):
    def setUp(self):
        self.tab = TextToSpeechTab()
        self.tab.show()

    def test_engine_selector_and_gemini_widgets_exist(self):
        self.assertTrue(hasattr(self.tab, "engine_toggle"))
        self.assertTrue(hasattr(self.tab, "local_voice_box"))
        self.assertTrue(hasattr(self.tab, "gemini_voice_box"))
        self.assertTrue(hasattr(self.tab, "gemini_model_combo"))
        self.assertTrue(hasattr(self.tab, "gemini_voice_combo"))
        self.assertTrue(hasattr(self.tab, "gemini_style_combo"))
        self.assertTrue(hasattr(self.tab, "gemini_instruction_edit"))

    def test_switching_to_gemini_engine_shows_gemini_box(self):
        # Switch to Gemini (index 1)
        self.tab.set_engine("gemini")
        self.assertTrue(self.tab.gemini_voice_box.isVisible())
        self.assertFalse(self.tab.local_voice_box.isVisible())

        # Switch back to Local (index 0)
        self.tab.set_engine("mms_khmer")
        self.assertFalse(self.tab.gemini_voice_box.isVisible())
        self.assertTrue(self.tab.local_voice_box.isVisible())

    def test_default_instruction_populated(self):
        current_instruction = self.tab.gemini_instruction_edit.toPlainText()
        self.assertEqual(current_instruction.strip(), DEFAULT_SPEECH_INSTRUCTION.strip())

    @patch("core.controller.TTSWorkerThread.start")
    @patch("core.secure_storage.SecureKeyStorage.has_api_key", return_value=True)
    def test_on_generate_clicked_with_gemini(self, mock_has_key, mock_start):
        self.tab.set_engine("gemini")
        self.tab.text_edit.setText("សួស្តី Hello Python")
        self.tab.on_generate_clicked()

        self.assertIsNotNone(self.tab.worker)
        self.assertEqual(self.tab.worker.engine_override, "gemini")
        self.assertEqual(self.tab.worker.text, "សួស្តី Hello Python")
