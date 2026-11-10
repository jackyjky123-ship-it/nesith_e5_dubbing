# KhmerDub: English and Khmer Video Dubbing Desktop App

A Windows desktop app that dubs videos between English and Khmer and also works as a text-to-speech tool, using OmniVoice for the voice.

## 1. Goals

- Dub a video from English to Khmer or from Khmer to English, keeping the original speaker's voice by cloning it.
- Text-to-speech tab: type text, pick a voice, get a `.wav` or `.mp3`.
- Only two languages: English and Khmer.
- Runs on a modest laptop (MSI GV72 8RC: i7-8750H, GTX 1050 with 2 GB VRAM, 8 GB RAM).

## 2. Important facts and risks

- OmniVoice is a text-to-speech model, not speech-to-speech. Dubbing needs a pipeline around it.
- OmniVoice has about 613M parameters and needs roughly 1.3 GB of VRAM at FP16. It also runs on CPU, only slower.
- It claims 600+ languages, but Khmer support is NOT yet confirmed. Test one Khmer sentence before building anything else.
- Khmer speech-to-text and translation are likely the weakest steps. Free local models for Khmer exist but are early or research-grade, so expect to review and fix the text.
- License: the model card lists Apache 2.0, but one mirror says the weights are CC-BY-NC. Read the official license before selling or monetizing anything made with it.
- "Free" here means no payment and no API keys. Free to run is not the same as free for commercial use: the NLLB translation model is non-commercial only (see section 2a).
- 8 GB RAM is tight. Load one model at a time and free it after its step.

## 2a. Free-only setup (no paid services, no API keys)

Everything runs locally on your laptop. Nothing is billed per use.

| Step                           | Free choice                                                      | License                                                         | Notes                                                                                                                                                           |
| ------------------------------ | ---------------------------------------------------------------- | --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Voice (TTS)                    | OmniVoice                                                        | Apache 2.0 per model card; one mirror says CC-BY-NC for weights | Verify on the official page                                                                                                                                     |
| Speech to text, English        | Whisper via `faster-whisper`                                     | MIT                                                             | Good for English                                                                                                                                                |
| Speech to text, Khmer          | `Hongleng/kasekor-asr-v0.0` (Whisper-small fine-tuned for Khmer) | Apache 2.0                                                      | Early research checkpoint. Self-reported 3.74% character error rate, but the author says it does not estimate accuracy on new speakers. Test on your own videos |
| Translation, English and Khmer | NLLB-200 distilled 600M (`facebook/nllb-200-distilled-600M`)     | CC-BY-NC-4.0                                                    | Khmer (`khm_Khmr`) supported. Free for personal and non-commercial use only. Described as a research model                                                      |
| UI                             | PySide6                                                          | LGPL                                                            | Free                                                                                                                                                            |
| ML runtime                     | PyTorch                                                          | BSD                                                             | Free                                                                                                                                                            |
| Video and audio                | ffmpeg                                                           | LGPL / GPL (depends on build)                                   | Free. Keep it as a separate bundled program                                                                                                                     |
| Packaging                      | PyInstaller                                                      | GPL with exception for your own app                             | Free                                                                                                                                                            |

What was removed from the first plan: paid cloud speech-to-text and cloud translators. Unofficial "free" wrappers around web translators are also left out, because they can break or be blocked at any time.

Limits of the free route:

- Khmer transcription and translation will be less accurate than paid cloud services. The segments table lets you edit the Khmer text before the voice is generated.
- Non-commercial limit: with NLLB you can make dubs for yourself, learning, and non-commercial sharing. Selling dubbing services or monetized videos needs a different translation model or a license change.
- Models download once from Hugging Face (free account not needed for public models), then work offline.

## 2b. Everything stays inside the project folder

Decision: all AI models live inside the project, so deleting the project folder removes them. Nothing is left behind in a shared cache.

How:

- Set the Hugging Face cache to `khmerdub/models/` before any model loads (environment variable `HF_HOME` set in `app.py` before importing the libraries, and `cache_dir` passed explicitly when loading each model).
- Create the Python environment inside the project (`khmerdub/venv/`), so PyTorch and the other packages are removed with it.
- Bundle ffmpeg in `khmerdub/tools/ffmpeg/`.
- Keep temporary files in `khmerdub/temp/` and finished videos and audio in `khmerdub/exports/` by default (the user can pick another output folder).
- Settings screen shows the model location and size, with a "Delete downloaded models" button and a "Clear temporary files" button.

What still lives outside the project (small, not the models):

- The Python program itself, if installed system-wide. Python can be removed from Windows "Installed apps" separately.
- pip's download cache, a global cache that can hold a few GB of downloaded packages. Install with `pip install --no-cache-dir`, or delete it afterwards with `pip cache purge`.
- Anything you choose to export to a folder outside the project.

To remove everything: delete the `khmerdub/` folder, then run `pip cache purge` if you used pip's cache.

## 3. Architecture

```
Desktop window (PySide6): Dub video | Text to speech | Settings
        |
Controller (background threads, progress reporting)
        |
  ffmpeg      Speech-to-text    Translation     OmniVoice (TTS)
  (audio)     (timestamps)      EN <-> KM       (voice cloning)

Dubbing: ffmpeg -> speech-to-text -> translate -> OmniVoice -> timing fit -> ffmpeg mix
TTS tab: OmniVoice only
```

### Dubbing pipeline

1. Extract audio from the video with ffmpeg.
2. Transcribe the speech into timed segments.
3. Translate each segment (English to Khmer or Khmer to English).
4. Let the user review and edit the translations.
5. Generate each segment with OmniVoice, cloning the speaker from a short reference clip.
6. Fit each generated line to its original time slot (adjust speed within a limit).
7. Mix the new speech with the original audio at a low volume and export the video.

## 4. Framework and tools

| Part            | Choice                                                                      | Reason                                                        |
| --------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Language        | Python 3.10+                                                                | OmniVoice and PyTorch are Python                              |
| Desktop UI      | PySide6 (Qt)                                                                | Native Windows app, easy threading, good Khmer text rendering |
| Voice           | `omnivoice` package + PyTorch                                               | The chosen TTS model                                          |
| Audio and video | ffmpeg                                                                      | Extract audio, mix, export                                    |
| Speech to text  | `faster-whisper` (English) and a Khmer Whisper fine-tune (Khmer), all local | Free, offline                                                 |
| Translation     | NLLB-200 distilled 600M, local                                              | Free, offline, non-commercial license                         |
| Packaging       | PyInstaller                                                                 | Windows installer                                             |

## 5. Requirements

- Python 3.10+, PyTorch with a CUDA build that supports the GTX 1050 (an older CUDA build may be needed), ffmpeg.
- About 4 GB of disk space for model files.
- No API keys and no paid accounts. All models run locally.
- Extra disk space for the Khmer speech model and NLLB (plan for about 6 to 8 GB in total, including OmniVoice).
- A clean reference clip of 5 to 15 seconds for voice cloning.

## 6. Screens and functions

### Dub video

- Open a video and preview it with a subtitle overlay.
- Choose the language direction (From / To, with a swap button).
- Pipeline progress: Extract audio, Transcribe, Translate, Generate voice, Mix and export.
- Options: voice (clone original speaker or preset), quality steps, original audio volume.
- Segments table: time, original text, editable translation, status. Regenerate selected segments.
- Export the dubbed video and `.srt` subtitles.
- Status bar: current segment, RAM and VRAM use.

### Text to speech

- Text box with a character counter and a language selector (Khmer, English, auto-detect).
- Voice modes: clone voice, preset, auto.
- Reference clip and optional transcript for cloning.
- Speed and quality sliders.
- Result player with a waveform, save as `.wav` or `.mp3`, use in a dub, and a recent-items list.

### Settings

- Engine per step: speech-to-text, translation, voice, video tools.
- Performance: GPU or CPU, precision (FP16 or INT8), low-memory mode.
- Storage: output folder (default inside the project), model location and size (inside the project), delete downloaded models, clear temporary files.

UI mockup: a three-screen canvas was made in the conversation (Dub video, Text to speech, Settings).

## 7. Suggested project structure

```
khmerdub/
  app.py                  # entry point
  ui/
    main_window.py
    dub_tab.py
    tts_tab.py
    settings_tab.py
  core/
    controller.py         # job queue, threads, progress signals
    pipeline.py           # dubbing steps in order
    audio_tools.py        # ffmpeg wrappers, timing fit, mixing
    stt.py                # speech-to-text engines
    translate.py          # translation engines
    tts_omnivoice.py      # OmniVoice load, generate, free memory
    config.py             # settings storage
  assets/
  requirements.txt
  venv/                   # Python environment (created here)
  models/                 # all downloaded AI models (Hugging Face cache)
  tools/ffmpeg/           # bundled ffmpeg
  temp/                   # temporary files
  exports/                # finished dubs and audio
```

## 8. Build plan

1. **Spike test (first):** run OmniVoice on one Khmer sentence and one English sentence on the laptop. Check quality, speed, and VRAM use. Decide whether Khmer is good enough to continue.
2. **TTS tab:** working text-to-speech with voice cloning and saving audio.
3. **Pipeline core:** ffmpeg audio extraction, speech-to-text, translation, per-segment generation, mixing, as a command-line script.
4. **Dub tab:** connect the pipeline to the UI with progress and an editable segments table.
5. **Settings tab:** engine choices, GPU/CPU, low-memory mode.
6. **Polish and package:** error handling, long-video handling, PyInstaller installer.

## 9. Open questions

- Will dubbed videos be sold or monetized? With the free setup (NLLB is non-commercial) this would need a different translation model.
- Which Windows version and how much free disk space are available?
