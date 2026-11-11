"""
Unit tests for Nesith TTS application branding, logo assets, and phonetic dictionary integration.
"""

import os
import sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import unittest
from PIL import Image

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QIcon, QPixmap

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app import setup_application
from ui.main_window import MainWindow
from core.khmer_phonetics import prepare_text_for_mms_khmer


class TestAppBranding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = setup_application()

    def test_application_properties(self):
        self.assertEqual(self.app.applicationName(), "Nesith TTS by JKY")
        self.assertEqual(self.app.organizationName(), "Nesith TTS by JKY")
        self.assertFalse(self.app.windowIcon().isNull(), "Application window icon should not be null")

    def test_main_window_branding(self):
        window = MainWindow()
        self.assertIn("Nesith TTS by JKY", window.windowTitle())
        self.assertFalse(window.windowIcon().isNull(), "MainWindow window icon should not be null")

        # Find header brand title label and logo
        labels = window.findChildren(QLabel)
        title_labels = [lbl for lbl in labels if lbl.text() == "Nesith TTS by JKY"]
        self.assertGreaterEqual(len(title_labels), 1, "Header must display 'Nesith TTS by JKY' brand label")

        # Check logo pixmap creation
        logo_pix = window.create_logo_pixmap(38)
        self.assertFalse(logo_pix.isNull())
        self.assertEqual(logo_pix.width(), 38)
        self.assertEqual(logo_pix.height(), 38)
        window.close()

    def test_logo_asset_files_exist(self):
        logo_png = os.path.join(PROJECT_DIR, "assets", "logo.png")
        icon_ico = os.path.join(PROJECT_DIR, "assets", "icon.ico")
        logo_full = os.path.join(PROJECT_DIR, "assets", "logo_full.png")

        self.assertTrue(os.path.exists(logo_png), "assets/logo.png must exist")
        self.assertTrue(os.path.exists(icon_ico), "assets/icon.ico must exist")
        self.assertTrue(os.path.exists(logo_full), "assets/logo_full.png must exist")

        with Image.open(logo_png) as img:
            self.assertEqual(img.size, (1024, 1024))
            self.assertEqual(img.mode, "RGBA")

    def test_phonetic_dictionary_nesith(self):
        result = prepare_text_for_mms_khmer("Nesith TTS")
        self.assertIn("និស្សិត", result)
        self.assertIn("ធីធីអេស", result)


if __name__ == "__main__":
    unittest.main()
