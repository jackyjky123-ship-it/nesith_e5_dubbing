# Third-Party Licenses

This document tracks all libraries, tools, and AI models utilized in the KhmerTTS project, their versions, licenses, and usage context.

| Component | Version | License | Usage Context | Commercial Safe? | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PySide6** | 6.12.0 | LGPLv3 / Commercial | Desktop GUI framework | Yes (under LGPL dynamic linking) | Standard Qt bindings for Python |
| **Python** | 3.12 | PSF License | Runtime environment | Yes | Core programming language |
| **pip** | 26.x | MIT | Package installer in `venv/` | Yes | Local dependency management |
| **ffmpeg** | 9.0.2 static | LGPL / GPL | Pitch, tempo adjustment, and audio export | Conditional | Bundled in `tools/ffmpeg/ffmpeg` |
| **Meta MMS-TTS Khmer** | facebook/mms-tts-khm | CC-BY-NC-4.0 | High-speed Native Khmer & Bilingual Text-to-Speech | **No** (Non-commercial only) | VITS architecture (139 MB, ~0.3s latency on CPU) |
