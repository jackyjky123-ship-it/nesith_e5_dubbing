# Design Document: Gemini Free Tier Rate Limit & Refresh Timer UI

## 1. Intent and Why
Users supplying their own Gemini API key (BYOK) on the Free Tier need visibility into their current rate limit consumption (Requests Per Minute, Tokens Per Minute, Daily Requests) and the exact time remaining until rolling rate-limit windows refresh, preventing unexpected `429 Too Many Requests` errors.

## 2. Goals, Non-Goals, and Anti-Goals
- **Goals**:
  - Track real-time token counts from Gemini API's `usageMetadata` (`promptTokenCount`, `candidatesTokenCount`, `totalTokenCount`).
  - Track rolling 60-second window requests (RPM) and tokens (TPM) against Free Tier limits (15 RPM, 1,000,000 TPM).
  - Track daily requests (RPD) against the Free Tier limit (1,500 RPD).
  - Show a live ticking countdown timer indicating seconds until the current 1-minute quota window refreshes.
  - Show the 24-hour daily quota reset time (Midnight UTC / local time).
  - Provide a clean visual presentation within the existing Gemini AI Settings card matching Nesith TTS's emerald/slate design system.
  - Display responsive health states (`Normal`, `Approaching Limit`, `Throttled (Retry-After: Xs)`).
- **Non-Goals**:
  - Querying private Google Cloud billing account balances or paid tier invoices.
  - Artificially delaying or queuing synthesis requests unless throttled.
- **Anti-Goals**:
  - Cluttering the UI with noisy or unverified simulated metrics.
  - Adding persistent background network polling when the app is idle.

## 3. Approaches Considered
- **Approach A (Selected)**: Integrated Quota Monitor inside the existing Gemini AI Settings card in `ui/settings_tab.py`. Keeps credentials, connection status, and quota consumption together in a unified view. Compact progress bars and countdown pill badge.
- **Approach B**: Standalone "Usage & Quota" card occupying the right column. Rejected to prevent fragmentation between key configuration and rate limit viewing, and to preserve space on smaller desktop resolutions.

## 4. Architecture & Component Design

### 4.1. Core Quota Tracker (`core/gemini_service.py` / `core/quota_tracker.py`)
- `GeminiQuotaTracker`:
  - Free Tier Constants:
    - `RPM_LIMIT = 15`
    - `TPM_LIMIT = 1_000_000`
    - `RPD_LIMIT = 1_500`
  - Rolling 60s window tracking using timestamps `(timestamp, token_count)`.
  - Daily request tracking with calendar date / UTC day boundary reset.
  - Method `record_usage(prompt_tokens: int, candidate_tokens: int, total_tokens: int)` called automatically upon each successful Gemini API response.
  - Method `record_throttle(retry_after_seconds: float)` called on HTTP 429 to capture Google's throttle window.
  - Method `get_snapshot() -> QuotaSnapshot`:
    - `rpm_used: int`, `rpm_limit: int`
    - `tpm_used: int`, `tpm_limit: int`
    - `rpd_used: int`, `rpd_limit: int`
    - `seconds_to_minute_refresh: int`
    - `time_to_daily_reset_str: str`
    - `status: str` ("normal", "warning", "throttled")

### 4.2. UI Components (`ui/settings_tab.py` & `ui/components.py`)
- Sub-card in `create_gemini_settings_card()`:
  - Header: "Free Tier Rate Limits & Quota" with status pill.
  - 3 Metric Rows:
    1. **RPM**: Progress bar showing `X / 15 req/min`, with a live badge: `Refreshes in XXs`.
    2. **TPM**: Progress bar showing `X / 1,000,000 tokens/min`.
    3. **RPD**: Progress bar showing `X / 1,500 req/day`, with a subtitle: `Daily reset at 00:00 UTC (XX:XX AM local)`.
  - Timer: A 1-second interval `QTimer` updating the countdown and window cleanup smoothly while the Settings tab is visible.
