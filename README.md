# Nesith TTS - Desktop Text-to-Speech Studio

A modern Windows desktop Text-to-Speech (TTS) application for natural **Khmer and English speech synthesis**, supporting both high-speed offline local synthesis (Meta MMS-TTS) and studio-grade cloud speech generation powered by **Google Gemini TTS** with a **Bring Your Own Key (BYOK)** architecture.

---

## Key Features

1. **Dual TTS Engines with Instant Switching**:
   - **Local Khmer TTS**: 100% offline synthesis using Meta MMS-TTS Khmer (`facebook/mms-tts-khm`) with G2P phonetic transliteration for English words and technical loanwords.
   - **Gemini AI TTS (BYOK)**: Studio-grade cloud synthesis using Google Gemini Speech Generation API (`gemini-3.8-flash-tts` & `gemini-3.8-flash-lite-tts`).

2. **Khmer + English Code-Switching with Single Speaker Identity**:
   - Synthesizes mixed Khmer and English sentences naturally in one voice without awkward engine jumps or pronunciation dropouts.
   - Example: *"សួស្តីអ្នកទាំងអស់គ្នា! ថ្ងៃនេះយើងនឹងរៀនអំពី Artificial Intelligence និងរបៀបប្រើ Python ដើម្បីបង្កើតកម្មវិធីថ្មីមួយ។"*
   - Speaks Khmer with natural cadence while pronouncing English technical terms (e.g. Python, React, JavaScript, API) cleanly in English, keeping voice tone, pitch, and identity completely uniform.

3. **30 Prebuilt Gemini Voices & Creative Direction**:
   - Full access to 30 Google prebuilt voices (e.g. *Kore, Puck, Zephyr, Charon, Fenrir, Aoede, Callirrhoe, Enceladus, Iapetus, Despina, Algieba*, etc.).
   - Granular speaking style controls (conversational, studio documentary, passionate podcast, calm storytelling, broadcast news).
   - Custom speech instructions prompt with one-click restore to defaults.

4. **Hardware-Backed Credential Security (BYOK)**:
   - **No Nesith Account Required**: Users supply their own Gemini API key directly from Google AI Studio.
   - **Zero Plaintext Storage**: Keys are encrypted using OS-level secure credential storage (Windows DPAPI `CryptProtectData` and Windows Credential Manager / OS keyring).
   - Keys are **never** stored in plaintext JSON (`config.json`), SQLite, or plain text configuration files.
   - Plaintext fallback is strictly prohibited: if OS secure storage is unavailable, the application warns the user rather than creating unencrypted files.
   - Sensitive keys are never printed in application logs, error dialogs, or terminal outputs.

5. **Live Free Tier Rate Limits & Token Refresh Monitor**:
   - Real-time tracking of Gemini API Free Tier limits in the Settings panel:
     - **Requests / Minute (RPM)**: Progress bar against 15 RPM with live ticking countdown (`60s window refreshes in: XXs`).
     - **Tokens / Minute (TPM)**: Progress bar against 1,000,000 TPM tracking exact prompt & candidate tokens from `usageMetadata`.
     - **Daily Requests (RPD)**: Progress bar against 1,500 RPD with 24-hour UTC midnight reset time indicator.
   - Dynamic health status pill (`Within limits`, `Approaching limit`, `Throttled: Retry in Xs`).

6. **Audio Player, Waveform & Export**:
   - Interactive 40-bar amplitude waveform visualization with real-time seeking.
   - Play, pause, and progress indicator.
   - Export generated audio to uncompressed `.wav` or compressed `.mp3` (using bundled ffmpeg).

---

## Getting Started

### 1. Prerequisites
- **Operating System**: Windows 10/11 (or Linux with Python 3.10+)
- **Python**: 3.10+
- **Virtual Environment**: Included in `venv/`

### 2. Launching the Application

Run the application using:
```bash
# On Linux / Bash
./run.sh

# On Windows
python app.py
```

---

## Configuring Gemini TTS (BYOK)

1. Open the application and click the **Settings** tab in the top navigation bar.
2. Locate the **Google Gemini AI Settings (BYOK)** card.
3. Obtain an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
4. Paste your API key into the **Gemini API Key** field (masked by default, with a "Show" toggle).
5. Select your preferred default model (`gemini-3.8-flash-tts` is recommended for studio-grade fidelity).
6. Click **Test connection** to verify the key with Google's servers. This performs a lightweight model query without generating audio or consuming generation quota.
7. Click **Save key**. The key is immediately encrypted and persisted via Windows DPAPI / OS Keyring.

---

## Synthesizing Speech

1. Switch to the **Text to speech** tab.
2. Under the **Voice** panel on the right, select **Gemini AI TTS** on the engine selector.
3. Choose your desired:
   - **Model**: `gemini-3.8-flash-tts` or `gemini-3.8-flash-lite-tts`.
   - **Voice**: Choose from 30 prebuilt voices.
   - **Style**: Select from conversational, narrative, or broadcast styles.
   - **Speed**: Adjust playback tempo from 0.5x to 2.0x.
   - **Speech Instruction**: View or edit the code-switching instruction.
4. Type or paste your text (Khmer, English, or mixed bilingual) in the **Text to speak** editor.
5. Click **Generate speech**.
6. Listen to the audio with the waveform player, or click **Save as .wav** / **Save as .mp3** to export.

---

## Architecture

```
core/
├── secure_storage.py       # OS-level credential management (Windows DPAPI & Keyring)
├── gemini_service.py       # Official Gemini generateContent TTS client & PCM-to-WAV converter
├── controller.py           # Background QThread workers (TTSWorkerThread, TestGeminiKeyWorkerThread)
├── config.py               # Application paths, hardware settings, and non-secret config
├── tts_engine.py           # Local Meta MMS-TTS Khmer engine and audio export
└── khmer_phonetics.py      # Khmer text normalization & phonetic lexicon
ui/
├── main_window.py          # Application window, top navigation header & engine status indicator
├── tts_tab.py              # Text editor, engine switcher, voice controls & waveform player
├── settings_tab.py         # Hardware settings, local engines & Gemini BYOK settings card
├── components.py           # WaveformWidget, SegmentedTab, StatusBadge
└── styles.py               # Modern emerald & slate UI design tokens
```

---

## Security & Billing Disclosures

- **Cost Advisory**: Gemini API calls utilize your personal Google API key and may incur charges according to your Google AI Studio or Google Cloud billing plan. Nesith TTS is an independent client and does not bill users.
- **Data Privacy**: Your API key is stored locally in Windows DPAPI / OS Keyring on your machine. Text submitted for synthesis is transmitted via HTTPS directly to Google Generative Language endpoints.
- **Model IDs**: Model IDs are configurable in `core/config.py` and `core/gemini_service.py`, allowing updates as Google releases new Gemini TTS models.

---

## Running the Test Suite

Run unit and integration tests:
```bash
./venv/bin/python -m unittest discover tests
```

To run only Gemini BYOK tests:
```bash
./venv/bin/python -m unittest tests/test_secure_storage.py tests/test_gemini_service.py tests/test_gemini_controller.py tests/test_settings_gemini.py tests/test_tts_tab_gemini.py tests/test_gemini_integration.py
```
