# Gemini Free Tier Rate Limit & Refresh Timer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a real-time Free Tier rate limit and token refresh monitor inside the Gemini AI Settings tab, tracking RPM, TPM, and RPD with live rolling-window refresh countdowns.

**Architecture:** A standalone `GeminiQuotaTracker` (`core/quota_tracker.py`) captures actual token consumption from Gemini API `usageMetadata` and `Retry-After` throttling responses using a 60-second rolling window and daily UTC tracking. `ui/settings_tab.py` embeds an interactive quota section with animated progress bars, live refresh timers, and health badges updated via a 1s `QTimer`.

**Tech Stack:** Python 3.10+, PySide6 (`QProgressBar`, `QTimer`, `QLabel`), `time`, `datetime`.

**Spec:** [`docs/superpowers/specs/2026-11-11-gemini-rate-limit-ui-design.md`](file:///media/spiderweb/DATA/Niseth_E5/docs/superpowers/specs/2026-11-11-gemini-rate-limit-ui-design.md)

## Global Constraints

- Free tier rate limits fixed to standard Gemini limits: 15 RPM, 1,000,000 TPM, 1,500 RPD.
- Never block UI or make unnecessary network calls; track consumption from actual generation responses.
- Real-time refresh timer must tick smoothly at 1-second intervals when the Settings tab is visible.
- Health badge must accurately reflect usage: `Within limits` (< 80%), `Approaching limit` (>= 80%), `Throttled` (HTTP 429).

## Review Focus

1. **Window rolling expiration:** A request made 61 seconds ago must drop out of the RPM and TPM window calculation.
2. **Day boundary reset:** Requests from previous calendar days (UTC) must reset `rpd_used` to 0.
3. **Empty / zero state:** When no requests have been made yet, RPM is 0/15, TPM is 0/1,000,000, RPD is 0/1,500, and refresh displays full 60s or "Idle".
4. **429 Throttling response:** Quota tracker captures `Retry-After` header or default backoff and displays remaining throttle seconds.
5. **No background CPU burn:** `QTimer` operates cleanly without memory leaks or heavy polling.

---

### Task 1: Core Quota Tracker (`core/quota_tracker.py`)

**Files:**
- Create: `core/quota_tracker.py`
- Modify: `core/gemini_service.py`
- Test: `tests/test_quota_tracker.py`

**Interfaces:**
- Produces:
  - `class QuotaSnapshot`:
    - `rpm_used: int`, `rpm_limit: int` (15)
    - `tpm_used: int`, `tpm_limit: int` (1,000,000)
    - `rpd_used: int`, `rpd_limit: int` (1,500)
    - `seconds_to_minute_refresh: int`
    - `time_to_daily_reset_str: str`
    - `status: str` ("normal", "warning", "throttled")
    - `throttle_remaining_seconds: int`
  - `class GeminiQuotaTracker`:
    - `record_usage(prompt_tokens: int, candidate_tokens: int, total_tokens: int)`
    - `record_throttle(retry_after_seconds: float = 60.0)`
    - `get_snapshot() -> QuotaSnapshot`
    - `reset_local()`

- [ ] **Step 1: Write failing tests for `GeminiQuotaTracker`**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `core/quota_tracker.py` and hook into `GeminiTTSService.generate_speech`**
- [ ] **Step 4: Run test to verify it passes**

---

### Task 2: Free Tier Rate Limit & Refresh UI in Settings Tab (`ui/settings_tab.py`)

**Files:**
- Modify: `ui/settings_tab.py`
- Test: `tests/test_quota_ui.py`

**Interfaces:**
- Produces:
  - `SettingsTab.create_quota_monitor_widget() -> QWidget`
  - `rpm_bar: QProgressBar`, `rpm_label: QLabel`, `rpm_timer_badge: QLabel`
  - `tpm_bar: QProgressBar`, `tpm_label: QLabel`
  - `rpd_bar: QProgressBar`, `rpd_label: QLabel`, `rpd_reset_label: QLabel`
  - `quota_health_badge: StatusBadge`
  - `quota_timer: QTimer` updating every 1000ms

- [ ] **Step 1: Write failing UI tests for quota monitor**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement Quota Monitor widget and 1s timer in `ui/settings_tab.py`**
- [ ] **Step 4: Run test to verify it passes**

---

### Task 3: Full Test Suite Verification

- [ ] **Step 1: Run complete test suite**
- [ ] **Step 2: Update documentation**
