# Third-Party Licenses

This document tracks all libraries, tools, and AI models utilized in the KhmerDub project, their versions, licenses, and usage context.

| Component | Version | License | Usage Context | Commercial Safe? | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PySide6** | 6.12.0 | LGPLv3 / Commercial | Desktop GUI framework | Yes (under LGPL dynamic linking) | Standard Qt bindings for Python |
| **Python** | 3.12 | PSF License | Runtime environment | Yes | Core programming language |
| **pip** | 26.x | MIT | Package installer in `venv/` | Yes | Local dependency management |
| **ffmpeg** | 9.0.2 static | LGPL / GPL | Audio extraction, timing fit, mixing | Conditional | Bundled in `tools/ffmpeg/ffmpeg` |
| **OmniVoice** | 0.2.1 (613M) | Apache 2.0 (code) / **CC-BY-NC** (weights) | Multilingual Text-to-Speech & Voice Cloning | **No** (Non-commercial only) | Training data constraints (Emilia dataset) |
| **Whisper Turbo** | large-v3-turbo | MIT | Voice cloning reference feature extractor | Yes | Used internally by OmniVoice for audio embeddings |
| **faster-whisper** | (Planned Phase 3) | MIT | English Speech-to-Text | Yes | Fast local CTranslate2 inference |
| **Hongleng Khmer ASR** | (Planned Phase 3) | Apache 2.0 | Khmer Speech-to-Text fine-tune | Yes | Research checkpoint |
| **NLLB-200 distilled 600M** | (Planned Phase 3) | CC-BY-NC-4.0 | English <-> Khmer machine translation | **No** (Non-commercial research only) | Attribution & non-commercial use only |
