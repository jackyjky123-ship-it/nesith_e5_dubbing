"""
KhmerTTS / Nesith TTS - Gemini Free Tier Quota & Rate Limit Tracker.
Tracks:
1. Requests Per Minute (RPM) over rolling 60-second window (Limit: 15).
2. Tokens Per Minute (TPM) over rolling 60-second window (Limit: 1,000,000).
3. Requests Per Day (RPD) with UTC calendar day boundary (Limit: 1,500).
4. Seconds remaining until rolling window refreshes.
5. Throttling backoff tracking when HTTP 429 occurs.
"""

import time
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class QuotaSnapshot:
    """Read-only snapshot of current rate limit metrics and refresh timings."""
    rpm_used: int
    rpm_limit: int
    tpm_used: int
    tpm_limit: int
    rpd_used: int
    rpd_limit: int
    seconds_to_minute_refresh: int
    time_to_daily_reset_str: str
    status: str  # "normal", "warning", "throttled"
    throttle_remaining_seconds: int


class GeminiQuotaTracker:
    """Client-side quota and rate-limit monitor for Gemini Free Tier."""

    RPM_LIMIT: int = 15
    TPM_LIMIT: int = 1_000_000
    RPD_LIMIT: int = 1_500
    WINDOW_SECONDS: float = 60.0

    def __init__(self):
        # List of (timestamp, total_tokens)
        self._minute_events: List[Tuple[float, int]] = []
        # List of (timestamp, total_tokens) for current UTC day
        self._daily_events: List[Tuple[float, int]] = []
        self._current_utc_date: str = self._get_utc_date_str()
        self._throttle_until: float = 0.0

    @staticmethod
    def _get_utc_date_str(ts: Optional[float] = None) -> str:
        t = datetime.fromtimestamp(ts or time.time(), tz=timezone.utc)
        return t.strftime("%Y-%m-%d")

    def reset_local(self):
        """Clears local in-memory event tracking."""
        self._minute_events.clear()
        self._daily_events.clear()
        self._current_utc_date = self._get_utc_date_str()
        self._throttle_until = 0.0

    def record_usage(self, prompt_tokens: int = 0, candidate_tokens: int = 0, total_tokens: int = 0):
        """Records a successful Gemini API request and its token consumption."""
        now = time.time()
        effective_tokens = max(1, total_tokens or (prompt_tokens + candidate_tokens))

        # Check for UTC day rollover
        today_utc = self._get_utc_date_str(now)
        if today_utc != self._current_utc_date:
            self._daily_events.clear()
            self._current_utc_date = today_utc

        self._minute_events.append((now, effective_tokens))
        self._daily_events.append((now, effective_tokens))
        self._clean_expired(now)

    def record_throttle(self, retry_after_seconds: float = 60.0):
        """Records that Google API returned HTTP 429 with cooldown duration."""
        cooldown = max(1.0, float(retry_after_seconds))
        self._throttle_until = time.time() + cooldown

    def _clean_expired(self, now: float):
        """Removes minute events that have rolled outside the 60-second window."""
        cutoff = now - self.WINDOW_SECONDS
        self._minute_events = [ev for ev in self._minute_events if ev[0] > cutoff]

        # Clean daily events that belong to a previous calendar day
        today_utc = self._get_utc_date_str(now)
        self._daily_events = [ev for ev in self._daily_events if self._get_utc_date_str(ev[0]) == today_utc]

    def get_snapshot(self) -> QuotaSnapshot:
        """Computes and returns the current QuotaSnapshot."""
        now = time.time()
        self._clean_expired(now)

        rpm_used = len(self._minute_events)
        tpm_used = sum(ev[1] for ev in self._minute_events)
        rpd_used = len(self._daily_events)

        # Seconds until the oldest event in the 60s window rolls off
        if self._minute_events:
            oldest_ts = self._minute_events[0][0]
            seconds_to_refresh = max(1, int(round((oldest_ts + self.WINDOW_SECONDS) - now)))
        else:
            seconds_to_refresh = 0

        # Time until next 00:00 UTC
        now_dt = datetime.fromtimestamp(now, tz=timezone.utc)
        seconds_into_day = now_dt.hour * 3600 + now_dt.minute * 60 + now_dt.second
        seconds_to_utc_midnight = 86400 - seconds_into_day
        hours_to_reset = seconds_to_utc_midnight // 3600
        mins_to_reset = (seconds_to_utc_midnight % 3600) // 60
        daily_reset_str = f"00:00 UTC (in {hours_to_reset}h {mins_to_reset}m)"

        # Check status
        throttle_remaining = 0
        if self._throttle_until > now:
            status = "throttled"
            throttle_remaining = int(round(self._throttle_until - now))
        elif (rpm_used >= int(self.RPM_LIMIT * 0.8)) or (tpm_used >= int(self.TPM_LIMIT * 0.8)) or (rpd_used >= int(self.RPD_LIMIT * 0.8)):
            status = "warning"
        else:
            status = "normal"

        return QuotaSnapshot(
            rpm_used=rpm_used,
            rpm_limit=self.RPM_LIMIT,
            tpm_used=tpm_used,
            tpm_limit=self.TPM_LIMIT,
            rpd_used=rpd_used,
            rpd_limit=self.RPD_LIMIT,
            seconds_to_minute_refresh=seconds_to_refresh,
            time_to_daily_reset_str=daily_reset_str,
            status=status,
            throttle_remaining_seconds=throttle_remaining
        )


# Global singleton instance
gemini_quota_tracker = GeminiQuotaTracker()
