# Gemini TTS (BYOK) Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Google's Gemini Text-to-Speech API into Nesith TTS using a Bring Your Own Key (BYOK) architecture with OS-level secure credential storage, bilingual Khmer-English code-switching in a single speaker identity, engine selection, and complete playback/export support.

**Architecture:** A modular backend consisting of `SecureKeyStorage` (Windows DPAPI / Credential Manager / Keyring with strict no-plaintext-fallback), `GeminiTTSService` (REST API client using `v1beta/models/{model}:generateContent` with `response_modalities: ["AUDIO"]`, PCM-to-WAV conversion, and structured error handling), and `TTSWorkerThread` pipeline routing. The PySide6 UI is extended with a dedicated **Gemini AI Settings** card in `SettingsTab` and dynamic engine switching in `TextToSpeechTab`.

**Tech Stack:** Python 3.10+, PySide6, `requests` (for HTTPS API calls), standard `ctypes` / Windows DPAPI / `keyring` (for secure credential storage), `wave` / `soundfile` / `numpy` (for audio PCM-to-WAV wrapping and waveform calculation), and bundled `ffmpeg` (for speed/export).

**Spec:** User request: "Feature Implementation: Gemini TTS Integration (BYOK)"

## Global Constraints

- Never expose the API key in application logs, terminal outputs, error messages, or frontend-visible state.
- Do not store API keys as plaintext in JSON (`config.json`), SQLite, localStorage, or config files.
- If secure credential storage is unavailable, fail explicitly with an actionable error—never silently fall back to plaintext storage.
- Do not require users to create a Nesith account.
- Keep model IDs configurable; default to `gemini-3.8-flash-tts` and `gemini-3.8-flash-lite-tts`.
- Never make Gemini API calls automatically in the background without explicit user interaction.
- Preserve full backward compatibility with the existing offline Meta MMS-TTS Khmer engine.

## Review Focus

1. **Missing or blank API key when attempting generation or connection test:** Expected: Clear descriptive warning dialog prompting the user to enter and save their Gemini key in Settings, without initiating an empty network request.
2. **API returns 401 Unauthorized or 403 Forbidden (invalid key or disabled billing/API):** Expected: User-friendly message explaining that the key is invalid or lacks Gemini TTS permissions; no API key string leaked in the message or log.
3. **API returns raw PCM audio chunk (`audio/L16;codec=pcm;rate=24000`) instead of containerized WAV:** Expected: Audio decoder automatically detects linear PCM, prepends a valid RIFF/WAV header (24kHz, 16-bit, 1 channel), and outputs a playable WAV file.
4. **Network connectivity failure or timeout during generation:** Expected: Clear error message ("Network connection timed out or unreachable") with retry capability; UI controls re-enabled cleanly.
5. **Secure storage is unavailable on the host OS:** Expected: `SecureStorageUnavailableError` is raised and reported to the user with guidance; no unencrypted file is created.

---

### Task 1: Secure API Key Storage (`core/secure_storage.py`)

**Files:**
- Create: `core/secure_storage.py`
- Test: `tests/test_secure_storage.py`

**Interfaces:**
- Produces:
  - `class SecureStorageError(Exception)`
  - `class SecureStorageUnavailableError(SecureStorageError)`
  - `class SecureKeyStorage:`
    - `save_api_key(api_key: str) -> bool`
    - `get_api_key() -> Optional[str]`
    - `delete_api_key() -> bool`
    - `has_api_key() -> bool`
    - `is_secure_storage_available() -> bool`

- [ ] **Step 1: Write failing tests for `SecureKeyStorage`**

```python
# tests/test_secure_storage.py
import unittest
from unittest.mock import patch, MagicMock
from core.secure_storage import (
    SecureKeyStorage, SecureStorageUnavailableError
)

class TestSecureStorage(unittest.TestCase):
    def test_save_and_get_key_mocked(self):
        storage = SecureKeyStorage(service_name="NesithTTS_Test")
        with patch.object(storage, "_store_raw", return_value=True), \
             patch.object(storage, "_retrieve_raw", return_value="AIzaSyTestKey123"):
            saved = storage.save_api_key("AIzaSyTestKey123")
            self.assertTrue(saved)
            key = storage.get_api_key()
            self.assertEqual(key, "AIzaSyTestKey123")
            self.assertTrue(storage.has_api_key())

    def test_delete_key_mocked(self):
        storage = SecureKeyStorage(service_name="NesithTTS_Test")
        with patch.object(storage, "_delete_raw", return_value=True):
            deleted = storage.delete_api_key()
            self.assertTrue(deleted)

    def test_fails_when_secure_storage_unavailable_without_plaintext_fallback(self):
        storage = SecureKeyStorage(service_name="NesithTTS_Test")
        with patch.object(storage, "is_secure_storage_available", return_value=False):
            with self.assertRaises(SecureStorageUnavailableError):
                storage.save_api_key("AIzaSyTestKey123")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m unittest tests/test_secure_storage.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.secure_storage'`

- [ ] **Step 3: Implement `SecureKeyStorage` in `core/secure_storage.py`**

Implement Windows DPAPI (`ctypes.windll.crypt32.CryptProtectData` / `CryptUnprotectData`) and optional `keyring` support for cross-platform secure storage. If neither secure backend is functional, raise `SecureStorageUnavailableError`. Never write plaintext keys to disk.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m unittest tests/test_secure_storage.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/secure_storage.py tests/test_secure_storage.py
git commit -m "feat: implement SecureKeyStorage with OS-level encryption"
```

---

### Task 2: Gemini TTS Service (`core/gemini_service.py`)

**Files:**
- Create: `core/gemini_service.py`
- Modify: `core/config.py`
- Test: `tests/test_gemini_service.py`

**Interfaces:**
- Consumes: `load_config`, `TEMP_DIR` from `core/config.py`
- Produces:
  - `GEMINI_TTS_MODELS: Dict[str, str]` (default models including `gemini-3.8-flash-tts` and `gemini-3.8-flash-lite-tts`)
  - `GEMINI_PREBUILT_VOICES: List[Dict[str, str]]` (list of 30 voices: Puck, Charon, Kore, Fenrir, Aoede, Zephyr, etc.)
  - `DEFAULT_SPEECH_INSTRUCTION: str`
  - `class GeminiAPIError(Exception)`
  - `class GeminiTTSService:`
    - `validate_api_key(api_key: str) -> Tuple[bool, str]`
    - `generate_speech(text: str, api_key: str, model: str = ..., voice: str = ..., style: str = ..., instruction: str = ..., speed: float = 1.0) -> Tuple[np.ndarray, int, str]`
    - `pcm_to_wav_bytes(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes`
    - `handle_api_error(status_code: int, response_json: dict) -> str`

- [ ] **Step 1: Write failing tests for `GeminiTTSService`**

```python
# tests/test_gemini_service.py
import unittest
import base64
import numpy as np
from unittest.mock import patch, MagicMock
from core.gemini_service import (
    GeminiTTSService, GeminiAPIError, GEMINI_TTS_MODELS, GEMINI_PREBUILT_VOICES,
    DEFAULT_SPEECH_INSTRUCTION
)

class TestGeminiService(unittest.TestCase):
    def setUp(self):
        self.service = GeminiTTSService()

    def test_models_and_voices_exist(self):
        self.assertIn("gemini-3.8-flash-tts", GEMINI_TTS_MODELS)
        self.assertIn("gemini-3.8-flash-lite-tts", GEMINI_TTS_MODELS)
        voice_names = [v["id"] for v in GEMINI_PREBUILT_VOICES]
        self.assertIn("Kore", voice_names)
        self.assertIn("Puck", voice_names)
        self.assertIn("Zephyr", voice_names)

    def test_pcm_to_wav_conversion(self):
        # 1 second of 24kHz 16-bit silence
        raw_pcm = b"\x00\x00" * 24000
        wav_bytes = self.service.pcm_to_wav_bytes(raw_pcm, sample_rate=24000)
        self.assertTrue(wav_bytes.startswith(b"RIFF"))
        self.assertIn(b"WAVE", wav_bytes[:12])

    @patch("requests.post")
    def test_validate_api_key_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp
        ok, msg = self.service.validate_api_key("AIzaSyValidKey")
        self.assertTrue(ok)
        self.assertIn("valid", msg.lower())

    @patch("requests.post")
    def test_validate_api_key_invalid(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {"error": {"message": "API key not valid"}}
        mock_post.return_value = mock_resp
        ok, msg = self.service.validate_api_key("AIzaSyInvalidKey")
        self.assertFalse(ok)
        self.assertNotIn("AIzaSyInvalidKey", msg)  # Must never leak key
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m unittest tests/test_gemini_service.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.gemini_service'`

- [ ] **Step 3: Implement `core/gemini_service.py`**

- Connect to `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`.
- Format payload with `response_modalities: ["AUDIO"]`, `speech_config.voice_config.prebuilt_voice_config.voice_name`, and natural language instruction.
- Extract `inlineData.data` and `inlineData.mimeType`.
- Convert PCM to WAV using Python's standard `wave` module, and handle tempo adjustments if `speed != 1.0`.
- Implement sanitization in error handling: never return or log raw API key.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m unittest tests/test_gemini_service.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/gemini_service.py tests/test_gemini_service.py
git commit -m "feat: implement GeminiTTSService with speech generation and PCM decoding"
```

---

### Task 3: Pipeline & Worker Controller Integration (`core/controller.py`)

**Files:**
- Modify: `core/controller.py`
- Modify: `core/config.py`
- Test: `tests/test_gemini_controller.py`

**Interfaces:**
- Consumes: `GeminiTTSService`, `SecureKeyStorage`
- Produces:
  - Extended `TTSWorkerThread` supporting:
    - `engine: str = "mms_khmer"` ("mms_khmer" or "gemini")
    - `gemini_model: Optional[str] = None`
    - `gemini_voice: Optional[str] = None`
    - `gemini_style: Optional[str] = None`
    - `gemini_instruction: Optional[str] = None`
  - `TestGeminiKeyWorkerThread(QThread)`:
    - Signals: `test_finished = Signal(bool, str)`

- [ ] **Step 1: Write failing test for controller with Gemini engine**

```python
# tests/test_gemini_controller.py
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from core.controller import TTSWorkerThread
from core.tts_engine import TTSResult

class TestGeminiController(unittest.TestCase):
    @patch("core.secure_storage.SecureKeyStorage.get_api_key", return_value="AIzaSyMockKey")
    @patch("core.gemini_service.GeminiTTSService.generate_speech")
    def test_worker_thread_gemini_success(self, mock_gen, mock_key):
        dummy_audio = np.zeros(24000, dtype=np.float32)
        mock_gen.return_value = (dummy_audio, 24000, "/tmp/test.wav")

        worker = TTSWorkerThread(
            text="សួស្តី Hello World",
            engine_override="gemini",
            gemini_model="gemini-3.8-flash-tts",
            gemini_voice="Kore"
        )

        results = []
        errors = []
        worker.finished_success.connect(lambda res: results.append(res))
        worker.finished_error.connect(lambda err: errors.append(err))

        worker.run()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].engine_name, "gemini")
        self.assertEqual(results[0].sample_rate, 24000)

    @patch("core.secure_storage.SecureKeyStorage.get_api_key", return_value=None)
    def test_worker_thread_gemini_missing_key(self, mock_key):
        worker = TTSWorkerThread(
            text="Test missing key",
            engine_override="gemini"
        )
        errors = []
        worker.finished_error.connect(lambda err: errors.append(err))
        worker.run()
        self.assertEqual(len(errors), 1)
        self.assertIn("API key", errors[0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m unittest tests/test_gemini_controller.py`
Expected: FAIL (missing gemini parameters / branch in worker)

- [ ] **Step 3: Update `core/controller.py`**

- Add Gemini synthesis execution branch in `TTSWorkerThread.run()`.
- Add `TestGeminiKeyWorkerThread` for non-blocking API key connection testing from UI.
- Update `config.py` default configuration to include default Gemini model, voice, and engine selection without storing secrets.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m unittest tests/test_gemini_controller.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/controller.py core/config.py tests/test_gemini_controller.py
git commit -m "feat: integrate Gemini synthesis and key test worker in controller"
```

---

### Task 4: BYOK Settings Section (`ui/settings_tab.py`)

**Files:**
- Modify: `ui/settings_tab.py`
- Test: `tests/test_settings_gemini.py`

**Interfaces:**
- Consumes: `SecureKeyStorage`, `TestGeminiKeyWorkerThread`, `GeminiTTSService`
- Produces:
  - `SettingsTab.create_gemini_settings_card() -> QFrame`:
    - API Key input (masked by default with show/hide button)
    - Model selection dropdown
    - Connection status badge (`StatusBadge`)
    - Test API Key button (`QPushButton`)
    - Save API Key button (`QPushButton`)
    - Remove API Key button (`QPushButton`)
    - Cost advisory info label

- [ ] **Step 1: Write failing UI test for `SettingsTab` Gemini section**

```python
# tests/test_settings_gemini.py
import sys
import unittest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton
from ui.settings_tab import SettingsTab

app = QApplication.instance() or QApplication(sys.argv)

class TestSettingsGemini(unittest.TestCase):
    def setUp(self):
        self.tab = SettingsTab()

    def test_gemini_card_elements_exist(self):
        self.assertTrue(hasattr(self.tab, "gemini_key_input"))
        self.assertTrue(hasattr(self.tab, "gemini_model_combo"))
        self.assertTrue(hasattr(self.tab, "btn_test_gemini_key"))
        self.assertTrue(hasattr(self.tab, "btn_save_gemini_key"))
        self.assertTrue(hasattr(self.tab, "btn_remove_gemini_key"))
        self.assertTrue(hasattr(self.tab, "gemini_status_badge"))
        # Key input must be password masked by default
        self.assertEqual(self.tab.gemini_key_input.echoMode(), QLineEdit.Password)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m unittest tests/test_settings_gemini.py`
Expected: FAIL with `AttributeError`

- [ ] **Step 3: Implement Gemini Settings Card in `ui/settings_tab.py`**

- Add `create_gemini_settings_card()` matching the existing design system.
- Implement masked key input with eye toggle ("Show" / "Hide").
- Wire Save, Test, and Remove buttons with asynchronous worker for testing.
- Show clear status feedback (Not configured, Checking..., Connected, Error).
- Include billing / cost advisory notice.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m unittest tests/test_settings_gemini.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ui/settings_tab.py tests/test_settings_gemini.py
git commit -m "feat: add Gemini BYOK settings section in SettingsTab"
```

---

### Task 5: TTS Studio UI Extension & Engine Switching (`ui/tts_tab.py` & `ui/main_window.py`)

**Files:**
- Modify: `ui/tts_tab.py`
- Modify: `ui/main_window.py`
- Test: `tests/test_tts_tab_gemini.py`

**Interfaces:**
- Consumes: `TTSWorkerThread`, `load_config`, `save_config`, `GEMINI_TTS_MODELS`, `GEMINI_PREBUILT_VOICES`
- Produces:
  - Engine selector: `SegmentedTab` or `QComboBox` for `["Local Khmer TTS", "Gemini AI TTS"]`
  - Dynamic Voice Settings view switching:
    - Local: Preset/Auto pitch & tempo controls
    - Gemini: Model selection, 30 Prebuilt voices, Speaking style, Speed, Custom code-switching speech instruction
  - Status display & Waveform / Player integration

- [ ] **Step 1: Write failing UI test for TTS engine switching**

```python
# tests/test_tts_tab_gemini.py
import sys
import unittest
from PySide6.QtWidgets import QApplication
from ui.tts_tab import TextToSpeechTab

app = QApplication.instance() or QApplication(sys.argv)

class TestTTSTabGemini(unittest.TestCase):
    def setUp(self):
        self.tab = TextToSpeechTab()

    def test_engine_selector_present(self):
        self.assertTrue(hasattr(self.tab, "engine_selector"))
        self.assertTrue(hasattr(self.tab, "gemini_voice_box"))
        self.assertTrue(hasattr(self.tab, "gemini_voice_combo"))
        self.assertTrue(hasattr(self.tab, "gemini_instruction_edit"))

    def test_switching_to_gemini_shows_gemini_controls(self):
        self.tab.set_engine("gemini")
        self.assertTrue(self.tab.gemini_voice_box.isVisible())
        self.assertFalse(self.tab.local_voice_box.isVisible())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m unittest tests/test_tts_tab_gemini.py`
Expected: FAIL with `AttributeError`

- [ ] **Step 3: Implement Engine Selector and Gemini Voice Panel in `ui/tts_tab.py`**

- Add Engine switcher: `[Local Khmer TTS, Gemini AI TTS]`.
- Organize voice settings cards so Local settings (quality steps, local presets) hide when Gemini is active, and Gemini controls (model, voice selector, style, natural language instruction) appear.
- Connect speech generation to pass Gemini configuration to `TTSWorkerThread`.
- Update top header indicator in `ui/main_window.py` to reflect active engine.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m unittest tests/test_tts_tab_gemini.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ui/tts_tab.py ui/main_window.py tests/test_tts_tab_gemini.py
git commit -m "feat: add engine switcher and Gemini voice controls in TTS Studio"
```

---

### Task 6: Comprehensive Test Suite & Code-Switching Verification (`tests/test_gemini_integration.py`)

**Files:**
- Create: `tests/test_gemini_integration.py`
- Modify: `README.md` (or docs)
- Modify: `LICENSES.md`

**Interfaces:**
- Validates:
  1. Khmer-only text synthesis request payload.
  2. English-only text synthesis request payload.
  3. Khmer-English mixed sentence code-switching request with single speaker identity instructions.
  4. Long paragraph formatting and character counters.
  5. Technical terms (React, Laravel, JavaScript, Python, API).
  6. Missing API key handling.
  7. Invalid API key error sanitization.
  8. Network failure / timeout error handling.
  9. API quota exceeded error handling.
  10. Audio export to WAV and MP3 with Gemini generated audio.

- [ ] **Step 1: Write comprehensive integration and edge case tests**

```python
# tests/test_gemini_integration.py
import unittest
from core.gemini_service import GeminiTTSService, DEFAULT_SPEECH_INSTRUCTION

class TestGeminiIntegration(unittest.TestCase):
    def test_code_switching_instruction_present(self):
        self.assertIn("Khmer", DEFAULT_SPEECH_INSTRUCTION)
        self.assertIn("English", DEFAULT_SPEECH_INSTRUCTION)
        self.assertIn("speaker identity", DEFAULT_SPEECH_INSTRUCTION)

    def test_mixed_sentence_payload_construction(self):
        service = GeminiTTSService()
        text = "សួស្តីអ្នកទាំងអស់គ្នា! ថ្ងៃនេះយើងនឹងរៀនអំពី Artificial Intelligence និងរបៀបប្រើ Python ដើម្បីបង្កើតកម្មវិធីថ្មីមួយ។"
        payload = service.build_request_payload(
            text=text,
            voice="Kore",
            style="natural",
            instruction=DEFAULT_SPEECH_INSTRUCTION
        )
        self.assertEqual(payload["generation_config"]["response_modalities"], ["AUDIO"])
        self.assertEqual(
            payload["generation_config"]["speech_config"]["voice_config"]["prebuilt_voice_config"]["voice_name"],
            "Kore"
        )
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], text)
```

- [ ] **Step 2: Run all tests to verify everything passes**

Run: `./venv/bin/python -m unittest discover tests`
Expected: All tests pass (Phase 2 local tests + Gemini tests).

- [ ] **Step 3: Update documentation (`README.md`, `LICENSES.md`)**

Document BYOK architecture, setup instructions, security guarantees, Gemini TTS models and supported voices, code-switching guidelines, and known limitations.

- [ ] **Step 4: Commit**

```bash
git add tests/test_gemini_integration.py README.md LICENSES.md
git commit -m "docs & test: add Gemini integration test suite, setup guide, and license tracking"
```
