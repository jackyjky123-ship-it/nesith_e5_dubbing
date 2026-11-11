"""
Unit tests for Gemini Free Tier Quota and Rate Limit Tracker.
"""

import time
import unittest
from unittest.mock import patch

from core.quota_tracker import GeminiQuotaTracker, QuotaSnapshot


class TestQuotaTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = GeminiQuotaTracker()
        self.tracker.reset_local()

    def test_initial_state(self):
        snap = self.tracker.get_snapshot()
        self.assertEqual(snap.rpm_used, 0)
        self.assertEqual(snap.rpm_limit, 15)
        self.assertEqual(snap.tpm_used, 0)
        self.assertEqual(snap.tpm_limit, 1_000_000)
        self.assertEqual(snap.rpd_used, 0)
        self.assertEqual(snap.rpd_limit, 1_500)
        self.assertEqual(snap.status, "normal")

    def test_record_usage_increments_metrics(self):
        self.tracker.record_usage(prompt_tokens=50, candidate_tokens=150, total_tokens=200)
        snap = self.tracker.get_snapshot()
        self.assertEqual(snap.rpm_used, 1)
        self.assertEqual(snap.tpm_used, 200)
        self.assertEqual(snap.rpd_used, 1)

    def test_sliding_window_expiration(self):
        now = time.time()
        # Simulate request made 65 seconds ago
        with patch("time.time", return_value=now - 65):
            self.tracker.record_usage(prompt_tokens=10, candidate_tokens=20, total_tokens=30)

        # Simulate request made 10 seconds ago
        with patch("time.time", return_value=now - 10):
            self.tracker.record_usage(prompt_tokens=10, candidate_tokens=20, total_tokens=30)

        # Check snapshot at current time
        with patch("time.time", return_value=now):
            snap = self.tracker.get_snapshot()
            # Only the 10-second-old request should be within the 60s window
            self.assertEqual(snap.rpm_used, 1)
            self.assertEqual(snap.tpm_used, 30)
            # RPD counts all requests today
            self.assertEqual(snap.rpd_used, 2)
            # Time to refresh should be 60 - 10 = 50s
            self.assertEqual(snap.seconds_to_minute_refresh, 50)

    def test_throttling_cooldown(self):
        now = time.time()
        with patch("time.time", return_value=now):
            self.tracker.record_throttle(retry_after_seconds=25)
            snap = self.tracker.get_snapshot()
            self.assertEqual(snap.status, "throttled")
            self.assertEqual(snap.throttle_remaining_seconds, 25)

        # 30 seconds later, throttle should be expired
        with patch("time.time", return_value=now + 30):
            snap = self.tracker.get_snapshot()
            self.assertNotEqual(snap.status, "throttled")
            self.assertEqual(snap.throttle_remaining_seconds, 0)

    def test_status_warning_threshold(self):
        # 12 requests out of 15 is 80% (approaching limit)
        for _ in range(12):
            self.tracker.record_usage(prompt_tokens=10, candidate_tokens=10, total_tokens=20)
        snap = self.tracker.get_snapshot()
        self.assertEqual(snap.status, "warning")
