# Nesith TTS: English and Khmer Text-to-Speech Desktop Studio

A lightweight, 100% offline desktop application for Khmer and English text-to-speech synthesis using single Meta MMS-TTS Khmer neural engine (`facebook/mms-tts-khm`) with advanced phonetic transliteration.

## 1. Goals

- **Text-to-Speech Studio**: Enter Khmer, English, or mixed bilingual text and generate clear, natural speech audio.
- **Unified Single-Voice Speech**: Speaks both Khmer and English in one consistent, natural voice using Meta MMS-TTS Khmer without artificial model swapping or voice mismatched timbres. English technical terms, words, acronyms, and numbers are phonetically mapped into authentic Khmer script.
- **Audio Export**: Export generated speech to `.wav` and `.mp3` (with bitrate options) using bundled ffmpeg.
- **Interactive Waveform Player**: Visualize real audio amplitude bars with seek-on-click, live playback progress, and timestamp counters.
- **Voice Character Presets & Pitch Styling**: Offers presets (Professional Female, Friendly Male, Deep Male, Warm Storyteller, News Anchor) as well as speed and pitch shaping.
- **Runs on modest hardware**: Runs entirely on CPU with < 1 GB peak RAM and low latency (< 1s RTF) on modest laptops (Intel i7-8750H / 8 GB RAM).

## 2. Important facts and licensing

- **Engine**: Meta MMS-TTS Khmer (`facebook/mms-tts-khm`, 139 MB) based on VITS architecture. Requires no GPU.
- **Phonetic Transliteration**: Enables Meta MMS-TTS Khmer to fluently speak English words, web/programming technical jargon, conversational phrases, acronyms, and numbers in a single cohesive voice.
- **Licensing**: Meta MMS-TTS is licensed under CC-BY-NC-4.0 (free for personal and non-commercial use). PySide6 is LGPLv3. ffmpeg is LGPL/GPL.
- **No Video Dubbing / No OmniVoice**: OmniVoice and video dubbing pipelines (ASR, machine translation) are removed to keep the project focused, lightweight, and responsive.

## 3. Everything stays inside the project folder

All AI models and dependencies live strictly within the project directory:
- Models cache: `models/` (enforced via `HF_HOME`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_OFFLINE=1`).
- Virtual environment: `venv/`.
- Bundled utilities: `tools/ffmpeg/`.
- Temporary outputs: `temp/` (recent TTS history, intermediate wav files).
- Exported audio: `exports/`.

Deleting the project folder completely removes all models and dependencies with zero residue.

## 4. Architecture

```
Desktop Window (PySide6): Text to Speech | Settings
        │
Background Controller (QThread worker, non-blocking UI)
        │
   ┌────┴──────────────────────────┐
   │                               │
Meta MMS-TTS Khmer        Bundled ffmpeg
(VITS Synthesis, 139MB)   (Pitch, Tempo, MP3 Export)
```

## 5. Screens & Functions

### Text to Speech Studio
- **Text Editor**: Rich text input area with character count and auto-detection for Khmer and English scripts.
- **Voice Selector**: Meta MMS-TTS Khmer engine with options for native Khmer and bilingual phonetic transliteration.
- **Voice Styling Modes**:
  - *Auto*: Balanced native synthesis for Khmer and bilingual mixed speech.
  - *Preset*: Professional Female, Friendly Male, Deep Male, Warm Storyteller, News Anchor.
- **Speed & Timing**: Granular speed slider (0.5x to 2.0x) with quick shortcut buttons (0.75x, 1.0x, 1.25x, 1.5x, 2.0x).
- **Waveform Player**: 40-bar amplitude waveform, interactive seek bar, play/pause, volume control, and duration timer.
- **Export Actions**: One-click "Save as .wav" and "Save as .mp3" saving to `exports/`.
- **Recent History**: Persistent list of recent generations with click-to-replay.

### Settings
- **Hardware & Device**: Toggle between CPU and CUDA GPU acceleration.
- **Performance**: Precision selection (FP32/FP16) and low-memory mode toggle (frees RAM after generation).
- **Storage Management**: Display model directory size, "Delete downloaded models", and "Clear temporary files".

## 6. Project Layout

```
khmer_tts/
├── app.py                       # Application entry point (HF_HOME locked at top)
├── run.sh                       # Launcher script
├── requirements.txt             # Pinned project dependencies
├── LICENSES.md                  # Third-party license documentation
├── PLAN.md                      # Architecture and specifications
├── implementation_plan.md       # Phased roadmap and status
├── assets/                      # UI icons, sample speaker audio
├── ui/                          # PySide6 presentation layer
│   ├── main_window.py           # Top navigation bar, header, tab switching
│   ├── tts_tab.py               # Standalone TTS Studio tab
│   ├── settings_tab.py          # Device, memory, and storage settings
│   ├── components.py            # WaveformWidget, SegmentedTab, StatusBadge
│   └── styles.py                # Emerald/teal design system stylesheet
├── core/                        # Engine and pipeline layer
│   ├── config.py                # Path management and environment flags
│   ├── tts_engine.py            # Meta MMS-TTS engine and audio export
│   ├── khmer_phonetics.py       # English-to-Khmer phonetic transliteration
│   ├── controller.py            # Background QThread synthesis worker & history
│   └── spike_test.py            # Standalone benchmarking script
├── models/                      # HuggingFace cache for MMS-TTS (~139 MB)
├── tools/ffmpeg/                # Bundled static ffmpeg
├── temp/                        # Temporary wav files and history JSON
└── exports/                     # Finished audio exports (.wav, .mp3)
```

## 7. Phased Roadmap

1. **Phase 1: MMS-TTS Engine & Spike Benchmark (Completed)**: Verified offline local loading, low RAM footprint (< 1 GB), and fast CPU generation.
2. **Phase 2: TTS Studio & Waveform Integration (Completed)**: Wired background worker, audio playback, presets, and .wav/.mp3 export.
3. **Phase 3: Phonetic Engine & Bilingual Transliteration (Completed)**: Comprehensive dictionary and rule-based transliteration for English words and loanwords in Khmer.
4. **Phase 4: Packaging & Distribution**: Build portable Windows/Linux executable using PyInstaller.
