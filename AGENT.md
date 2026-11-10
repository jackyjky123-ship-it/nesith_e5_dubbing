# agent.md: Rules for AI Agents Working on KhmerDub

KhmerDub is a free, offline Windows desktop app that dubs videos between English and Khmer and also does text-to-speech, using OmniVoice. Read `plan.md` first. If this file and `plan.md` disagree, ask the owner before acting.

## 1. Hard rules (never break these)

1. **Free only.** Use no paid services, paid APIs, or API keys. Do not add cloud speech-to-text, cloud translation, or any usage-billed service. Do not use unofficial wrappers around web translators.
2. **Everything stays inside the project folder.** All downloaded AI models go in `models/`. The Python environment is `venv/`. ffmpeg is in `tools/ffmpeg/`. Temporary files go in `temp/`. Output goes in `exports/`. Deleting the project folder must remove every model.
3. **Set the model cache before any model loads.** Set `HF_HOME` to `models/` at the very top of `app.py` (before importing `torch`, `transformers`, `omnivoice`, or any Hugging Face library) and pass `cache_dir` explicitly when loading each model. Never let a model download to `C:\Users\<name>\.cache`.
4. **Only English and Khmer.** Do not add other languages or language pickers beyond these two.
5. **Stay offline after setup.** The only allowed network use is a one-time model download from Hugging Face and package installs. Never send the user's videos, audio, text, or voice clips anywhere.
6. **Never touch files outside the project** without the owner's explicit permission. Do not delete, move, or overwrite the user's own videos, audio, or documents. Work on copies.
7. **No secrets in the repo.** Do not commit tokens, keys, or personal paths.

## 2. Licenses

- Track the license of every model and package you add in `LICENSES.md` (name, version, license, where it is used).
- Only add components that are free to use. Flag non-commercial licenses clearly.
- Known issues: NLLB-200 is CC-BY-NC-4.0 (non-commercial only). OmniVoice: the model card says Apache 2.0, but one mirror says the weights are CC-BY-NC. Check the official page and note the result in `LICENSES.md`.
- Do not claim the app is safe for commercial use unless every model has been verified as allowing it.
- Do not clone a real person's voice for impersonation. The app should remind users to use voice cloning only with consent.

## 3. Target machine and performance

The reference computer is an MSI GV72 8RC: Intel i7-8750H, GTX 1050 with 2 GB VRAM, 8 GB RAM, Windows.

- Load only one AI model at a time. Free it (`del` the model, `gc.collect()`, `torch.cuda.empty_cache()`) before loading the next.
- OmniVoice needs roughly 1.3 GB VRAM at FP16. Keep text chunks short. Offer INT8 and CPU fallback.
- Catch out-of-memory errors and show a clear message with a fix (shorter text, CPU mode, lower quality steps). Never crash silently.
- Run all model work in background threads. The UI must never freeze.
- Process long videos segment by segment and save progress so a failed run can resume.

## 4. Tech stack (do not swap without asking)

- Python 3.10+, PySide6 for the UI, PyTorch, the `omnivoice` package, ffmpeg.
- Speech to text: `faster-whisper` (English) and a Khmer Whisper fine-tune (Khmer).
- Translation: NLLB-200 distilled 600M, local.
- Packaging: PyInstaller.
- Pin dependency versions in `requirements.txt`. Add a new dependency only if it is free, necessary, and recorded in `LICENSES.md`.

## 5. Code structure

Follow the layout in `plan.md`:

```
khmerdub/
  app.py            ui/            core/
  models/  venv/  tools/ffmpeg/  temp/  exports/
```

- UI code lives in `ui/`. It contains no model or ffmpeg logic.
- Pipeline and model code lives in `core/`. It contains no UI code.
- Keep each file focused and small. Name things clearly.
- Handle Khmer text correctly: UTF-8 everywhere, and a font that renders Khmer (such as Noto Sans Khmer) in the UI.

## 6. How to work

- **Test first.** Before building features, run the spike test: one Khmer sentence and one English sentence through OmniVoice, with models saved in `models/`. Report quality, speed, and VRAM use. Do not continue past this step if Khmer output is unusable without telling the owner.
- Build in the order of `plan.md` section 8. Finish and test each step before the next.
- Run the code you write. Do not say something works unless you ran it. If you could not test something (for example, no GPU in your environment), say so plainly.
- Keep changes small and reviewable. Do not refactor unrelated code.
- Do not install anything system-wide. Install packages into `venv/` with `pip install --no-cache-dir`.
- Ask the owner before any decision that cannot be undone or that changes the plan (new dependency, new model, new language, removing a feature).

## 7. Reporting

- Report briefly: what changed, how it was tested, what is still unverified.
- Be honest about limits. Khmer transcription and translation are weaker than paid services, and the UI should say so where it matters (for example, "review the Khmer text before generating the voice").
- When something fails, show the real error and the fix you tried. Do not hide failures or claim success.

## 8. Cleanup guarantee

Before finishing any task, confirm:

- [ ] No model files exist outside `models/`.
- [ ] No new global cache or system-wide install was created, or it is listed in `plan.md` with how to remove it.
- [ ] `LICENSES.md` is up to date.
- [ ] No paid service or API key was added.
