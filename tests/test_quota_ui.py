"""
UI tests for the Gemini Free Tier Rate Limit & Refresh Timer in SettingsTab.
"""

import os
import sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import unittest

from PySide6.QtWidgets import QApplication, QProgressBar, QLabel
from PySide6.QtCore import QTimer

app = QApplication.instance() or QApplication(sys.argv)

from ui.settings_tab import SettingsTab
from core.quota_tracker import gemini_quota_tracker


class TestQuotaUI(unittest.TestCase):
    def setUp(self):
        gemini_quota_tracker.reset_local()
        self.tab = SettingsTab()
        self.tab.show()

    def test_quota_ui_elements_exist(self):
        self.assertTrue(hasattr(self.tab, "rpm_progress_bar"))
        self.assertTrue(hasattr(self.tab, "rpm_usage_label"))
        self.assertTrue(hasattr(self.tab, "rpm_refresh_badge"))
        self.assertTrue(hasattr(self.tab, "tpm_progress_bar"))
        self.assertTrue(hasattr(self.tab, "tpm_usage_label"))
        self.assertTrue(hasattr(self.tab, "rpd_progress_bar"))
        self.assertTrue(hasattr(self.tab, "rpd_usage_label"))
        self.assertTrue(hasattr(self.tab, "quota_health_badge"))
        self.assertTrue(hasattr(self.tab, "quota_refresh_timer"))

    def test_quota_ui_updates_on_usage(self):
        # Record usage
        gemini_quota_tracker.record_usage(prompt_tokens=100, candidate_tokens=200, total_tokens=300)
        self.tab.update_quota_display()

        # Check that RPM progress bar and label updated
        self.assertEqual(self.tab.rpm_progress_bar.value(), 1)
        self.assertIn("1 / 15", self.tab.rpm_usage_label.text())

        # Check TPM
        self.assertEqual(self.tab.tpm_progress_bar.value(), 300)
        self.assertIn("300", self.tab.tpm_usage_label.text())

        # Check RPD
        self.assertEqual(self.tab.rpd_progress_bar.value(), 1)
        self.assertIn("1 / 1,500", self.tab.rpd_usage_label.text())

        # Check health badge
        self.assertEqual(self.tab.quota_health_badge.text(), "Within limits")
