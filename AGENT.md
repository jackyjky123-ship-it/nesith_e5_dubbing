# AGENT.md: Rules for AI Agents Working on KhmerTTS

KhmerTTS is a free, offline desktop app for English and Khmer text-to-speech synthesis using single Meta MMS-TTS Khmer engine with advanced phonetic transliteration. Read `PLAN.md` first. If this file and `PLAN.md` disagree, ask the owner before acting.

## 1. Hard rules (never break these)

1. **Free only.** Use no paid services, paid APIs, or API keys. Do not add cloud services or usage-billed APIs.
2. **Everything stays inside the project folder.** All downloaded AI models go in `models/`. The Python environment is `venv/`. ffmpeg is in `tools/ffmpeg/`. Temporary files go in `temp/`. Output goes in `exports/`. Deleting the project folder must remove every model.
3. **Set the model cache before any model loads.** Set `HF_HOME` to `models/` at the very top of `app.py` (before importing `torch`, `transformers`, or any Hugging Face library) and pass `cache_dir` explicitly when loading each model. Never let a model download to global user caches.
4. **Only English and Khmer.** Do not add other languages or language pickers beyond these two.
5. **Stay offline after setup.** The only allowed network use is a one-time model download from Hugging Face and package installs. Never send user audio or text anywhere.
6. **Never touch files outside the project** without the owner's explicit permission.
7. **No secrets in the repo.** Do not commit tokens, keys, or personal paths.
8. **Text-to-Speech focus.** The application focuses purely on text-to-speech synthesis. Video dubbing and OmniVoice are excluded.

## 2. Licenses

- Track the license of every model and package you add in `LICENSES.md` (name, version, license, where it is used).
- Only add components that are free to use. Flag non-commercial licenses clearly.
- Meta MMS-TTS Khmer (`facebook/mms-tts-khm`) is licensed under CC-BY-NC-4.0 (non-commercial only).
- Do not claim the app is safe for commercial use unless verified.

## 3. Target machine and performance

The reference computer is an MSI GV72 8RC: Intel i7-8750H, GTX 1050 with 2 GB VRAM, 8 GB RAM.

- Meta MMS-TTS Khmer is compact (~139 MB) and operates comfortably within < 1 GB RAM on CPU.
- Single-model residency: Unload models when leaving TTS Studio or after generation if `low_memory_mode` is enabled.
- Catch out-of-memory errors and show a clear message with a fix. Never crash silently.
- Run all model synthesis work in background threads (`QThread`). The UI must never freeze.

## 4. Tech stack (do not swap without asking)

- Python 3.10+, PySide6 for the UI, PyTorch, `transformers`, `soundfile`, ffmpeg.
- Speech Synthesis Engine: Meta MMS-TTS Khmer (`facebook/mms-tts-khm`) with comprehensive phonetic transliteration for English words, technical terms, and bilingual mixed text.
- Packaging: PyInstaller.
- Pin dependency versions in `requirements.txt`. Add a new dependency only if it is free, necessary, and recorded in `LICENSES.md`.

## 5. Code structure

```
khmer_tts/
  app.py            ui/            core/
  models/  venv/  tools/ffmpeg/  temp/  exports/
```

- UI code lives in `ui/`. It contains no model or ffmpeg logic.
- Engine and audio code lives in `core/`. It contains no UI code.
- Keep each file focused and small. Name things clearly.
- Handle Khmer text correctly: UTF-8 everywhere, and proper Khmer Unicode normalization.

## 6. How to work

- **Test first.** Run tests or benchmarks before building features. Finish and test each step before the next.
- Run the code you write. Do not say something works unless you ran it.
- Keep changes small and reviewable. Do not refactor unrelated code.
- Do not install anything system-wide. Install packages into `venv/` with `pip install --no-cache-dir`.
- Ask the owner before any decision that cannot be undone or that changes the plan.

## 7. Cleanup guarantee

Before finishing any task, confirm:

- [ ] No model files exist outside `models/`.
- [ ] No new global cache or system-wide install was created.
- [ ] `LICENSES.md` is up to date.
- [ ] No paid service or API key was added.
