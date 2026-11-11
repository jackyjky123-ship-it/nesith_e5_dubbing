"""
UI unit tests for Gemini AI Settings card in SettingsTab.
Verifies input masking, show/hide toggle, model selection, buttons, and status indicator.
"""

import os
import sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QComboBox, QScrollArea
from PySide6.QtCore import Qt

# Ensure QApplication exists for UI tests
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from ui.settings_tab import SettingsTab
from ui.main_window import MainWindow
from ui.components import StatusBadge


class TestSettingsGemini(unittest.TestCase):
    def setUp(self):
        self.tab = SettingsTab()

    def test_gemini_card_widgets_exist(self):
        self.assertTrue(hasattr(self.tab, "gemini_key_input"))
        self.assertTrue(hasattr(self.tab, "btn_toggle_key_visibility"))
        self.assertTrue(hasattr(self.tab, "gemini_model_combo"))
        self.assertTrue(hasattr(self.tab, "gemini_status_badge"))
        self.assertTrue(hasattr(self.tab, "btn_test_gemini_key"))
        self.assertTrue(hasattr(self.tab, "btn_save_gemini_key"))
        self.assertTrue(hasattr(self.tab, "btn_remove_gemini_key"))

    def test_api_key_is_masked_by_default(self):
        self.assertEqual(self.tab.gemini_key_input.echoMode(), QLineEdit.Password)

    def test_toggle_key_visibility(self):
        self.assertEqual(self.tab.gemini_key_input.echoMode(), QLineEdit.Password)
        self.tab.toggle_key_visibility()
        self.assertEqual(self.tab.gemini_key_input.echoMode(), QLineEdit.Normal)
        self.tab.toggle_key_visibility()
        self.assertEqual(self.tab.gemini_key_input.echoMode(), QLineEdit.Password)

    @patch("PySide6.QtWidgets.QMessageBox.information")
    @patch("core.secure_storage.SecureKeyStorage.save_api_key", return_value=True)
    def test_save_key_action(self, mock_save, mock_info):
        self.tab.gemini_key_input.setText("AIzaSyTestNewKey123")
        self.tab.save_gemini_key()
        mock_save.assert_called_once_with("AIzaSyTestNewKey123")

    @patch("PySide6.QtWidgets.QMessageBox.information")
    @patch("core.secure_storage.SecureKeyStorage.delete_api_key", return_value=True)
    def test_remove_key_action(self, mock_delete, mock_info):
        self.tab.gemini_key_input.setText("AIzaSyTestKeyToDelete")
        self.tab.remove_gemini_key()
        mock_delete.assert_called_once()
        self.assertEqual(self.tab.gemini_key_input.text(), "")

    def test_gemini_card_not_crushed_on_small_screen(self):
        win = MainWindow()
        win.switch_tab(1)
        win.resize(980, 660)
        win.show()
        QApplication.processEvents()

        tab = win.settings_tab
        self.assertTrue(hasattr(tab, "scroll_area"), "SettingsTab should have scroll_area attribute")
        self.assertIsInstance(tab.scroll_area, QScrollArea)
        self.assertTrue(tab.scroll_area.widgetResizable())
        self.assertGreaterEqual(
            tab.gemini_key_input.height(), 24,
            f"Gemini key input was crushed to {tab.gemini_key_input.height()}px"
        )
        self.assertGreaterEqual(
            tab.gemini_model_combo.height(), 24,
            f"Gemini model combo was crushed to {tab.gemini_model_combo.height()}px"
        )
        win.close()
