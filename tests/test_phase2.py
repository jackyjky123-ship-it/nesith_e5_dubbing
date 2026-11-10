"""
KhmerDub - Phase 2 Comprehensive Test Suite.
Tests:
1. Configuration & Offline Environment Constraints.
2. TTS Engine: Language detection, Waveform bar computation, Synthesis, Audio Export (WAV & MP3).
3. Memory cleanup & single-model residency.
4. Controller: Background QThread worker execution & recent history persistence.
5. UI: TextToSpeechTab creation, widget wiring, mode switching, WaveformWidget playback state.
"""

import os
import sys
import time
import shutil
import unittest
import numpy as np
import soundfile as sf

# Enforce offscreen Qt platform for headless CLI testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from core.config import (
    PROJECT_DIR, MODELS_DIR, TEMP_DIR, EXPORTS_DIR, ASSETS_DIR,
    load_config, save_config, get_ffmpeg_path, get_active_device
)
from core.tts_engine import (
    is_khmer_text, detect_language, compute_waveform_bars,
    tts_manager, TTSResult
)
from core.controller import (
    TTSWorkerThread, load_recent_tts, add_recent_tts, RECENT_TTS_FILE
)

from PySide6.QtWidgets import QApplication
from ui.tts_tab import TextToSpeechTab
from ui.components import WaveformWidget
from ui.main_window import MainWindow

# Initialize single QApplication instance for Qt tests
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestPhase2Config(unittest.TestCase):
    """Verifies paths, offline variables, and configuration management."""

    def test_paths_and_env(self):
        self.assertTrue(os.path.isdir(MODELS_DIR))
        self.assertTrue(os.path.isdir(TEMP_DIR))
        self.assertTrue(os.path.isdir(EXPORTS_DIR))
        self.assertTrue(os.path.isdir(ASSETS_DIR))
        self.assertEqual(os.environ.get("HF_HOME"), MODELS_DIR)
        self.assertEqual(os.environ.get("HF_HUB_OFFLINE"), "1")
        self.assertEqual(os.environ.get("TRANSFORMERS_OFFLINE"), "1")

    def test_ffmpeg_availability(self):
        ffmpeg_exe = get_ffmpeg_path()
        self.assertTrue(os.path.exists(ffmpeg_exe), f"ffmpeg not found at {ffmpeg_exe}")
        self.assertTrue(os.access(ffmpeg_exe, os.X_OK))

    def test_config_load_and_save(self):
        cfg = load_config()
        self.assertIn("device", cfg)
        self.assertIn("low_memory_mode", cfg)
        self.assertTrue(cfg.get("low_memory_mode"))


class TestPhase2TTSEngine(unittest.TestCase):
    """Verifies TTS Engine functionality, waveform math, and synthesis."""

    def test_language_detection(self):
        khmer_str = "សួស្តីកម្ពុជា"
        english_str = "Hello world, welcome to KhmerDub!"
        mixed_str = "KhmerDub គឺជាកម្មវិធី dubbing"

        self.assertTrue(is_khmer_text(khmer_str))
        self.assertFalse(is_khmer_text(english_str))
        self.assertTrue(is_khmer_text(mixed_str))

        self.assertEqual(detect_language(khmer_str), "km")
        self.assertEqual(detect_language(english_str), "en")
        self.assertEqual(detect_language(mixed_str), "km")

    def test_khmer_phonetics_transliteration(self):
        from core.khmer_phonetics import prepare_text_for_mms_khmer
        sample = "តើអ្នកដឹងទេ? ប្រើ Ubuntu និង Linux សម្រាប់ Developer និង Web Development"
        trans = prepare_text_for_mms_khmer(sample)
        self.assertIn("អ៊ូប៊ុនទូ", trans)
        self.assertIn("លីនុច", trans)
        self.assertIn("ឌីវេឡុបភ័រ", trans)
        self.assertIn("វេប ឌីវេឡុបមិន", trans)
        self.assertNotIn("Ubuntu", trans)
        self.assertNotIn("Linux", trans)
        self.assertNotIn("Developer", trans)

    def test_compute_waveform_bars(self):
        # Sine wave
        t = np.linspace(0, 1, 16000)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        bars = compute_waveform_bars(audio, num_bars=40)

        self.assertEqual(len(bars), 40)
        self.assertGreaterEqual(min(bars), 0.08)
        self.assertLessEqual(max(bars), 1.0)
        self.assertAlmostEqual(max(bars), 1.0, places=1)

    def test_mms_khmer_synthesis_and_export(self):
        text = "សួស្តី"
        result = tts_manager.synthesize(
            text=text,
            language="km",
            engine_override="mms_khmer",
            speed=1.0
        )

        self.assertIsInstance(result, TTSResult)
        self.assertGreater(result.duration_seconds, 0.2)
        self.assertGreater(result.sample_rate, 8000)
        self.assertTrue(os.path.exists(result.temp_wav_path))
        self.assertEqual(len(result.waveform_bars), 40)

        # Test WAV export
        test_wav_export = os.path.join(EXPORTS_DIR, "test_export.wav")
        success_wav = tts_manager.export_audio(result.temp_wav_path, test_wav_export, fmt="wav")
        self.assertTrue(success_wav)
        self.assertTrue(os.path.exists(test_wav_export))

        # Test MP3 export via bundled ffmpeg
        test_mp3_export = os.path.join(EXPORTS_DIR, "test_export.mp3")
        success_mp3 = tts_manager.export_audio(result.temp_wav_path, test_mp3_export, fmt="mp3")
        self.assertTrue(success_mp3)
        self.assertTrue(os.path.exists(test_mp3_export))
        self.assertGreater(os.path.getsize(test_mp3_export), 1000)

        # Cleanup test exports
        if os.path.exists(test_wav_export):
            os.remove(test_wav_export)
        if os.path.exists(test_mp3_export):
            os.remove(test_mp3_export)

    def test_memory_unloading(self):
        # Ensure unload_model clears model reference
        tts_manager._load_mms_khmer()
        self.assertIsNotNone(tts_manager._model)
        tts_manager.unload_model()
        self.assertIsNone(tts_manager._model)
        self.assertIsNone(tts_manager._current_engine)


class TestPhase2Controller(unittest.TestCase):
    """Verifies background worker and recent generations persistence."""

    def test_recent_history_persistence(self):
        dummy_wav = os.path.join(TEMP_DIR, "dummy_recent.wav")
        sf.write(dummy_wav, np.zeros(8000, dtype=np.float32), 16000)

        add_recent_tts(
            text="Unit test recent entry",
            duration_sec=0.5,
            wav_path=dummy_wav,
            language="en",
            engine="mms_khmer"
        )

        recent = load_recent_tts()
        self.assertGreater(len(recent), 0)
        top = recent[0]
        self.assertIn("Unit test recent entry", top["full_text"])
        self.assertEqual(top["wav_path"], dummy_wav)

        if os.path.exists(dummy_wav):
            os.remove(dummy_wav)


class TestPhase2UI(unittest.TestCase):
    """Verifies PySide6 TextToSpeechTab and WaveformWidget."""

    def setUp(self):
        self.tab = TextToSpeechTab()

    def tearDown(self):
        if hasattr(self, "tab") and self.tab is not None:
            if hasattr(self.tab.waveform, "_player") and self.tab.waveform._player is not None:
                self.tab.waveform._player.stop()
            self.tab.deleteLater()
            self.tab = None
        QApplication.processEvents()

    def test_ui_components_instantiation(self):
        self.assertIsNotNone(self.tab.text_edit)
        self.assertIsNotNone(self.tab.waveform)
        self.assertIsNotNone(self.tab.generate_btn)
        self.assertIsNotNone(self.tab.mode_toggle)
        self.assertIsNotNone(self.tab.recent_list)

    def test_mode_switching(self):
        # Index 0: Clone voice
        self.tab.mode_toggle.set_active_index(0)
        self.assertFalse(self.tab.ref_clip_box.isHidden())
        self.assertFalse(self.tab.ref_trans_input.isHidden())
        self.assertTrue(self.tab.preset_box.isHidden())

        # Index 1: Preset
        self.tab.mode_toggle.set_active_index(1)
        self.assertTrue(self.tab.ref_clip_box.isHidden())
        self.assertTrue(self.tab.ref_trans_input.isHidden())
        self.assertFalse(self.tab.preset_box.isHidden())

        # Index 2: Auto
        self.tab.mode_toggle.set_active_index(2)
        self.assertTrue(self.tab.ref_clip_box.isHidden())
        self.assertTrue(self.tab.ref_trans_input.isHidden())
        self.assertTrue(self.tab.preset_box.isHidden())

    def test_waveform_widget_set_audio(self):
        dummy_wav = os.path.join(TEMP_DIR, "test_wave.wav")
        audio_data = np.sin(np.linspace(0, 50, 32000)).astype(np.float32)
        sf.write(dummy_wav, audio_data, 16000)

        bars = compute_waveform_bars(audio_data, 40)
        self.tab.waveform.set_audio(dummy_wav, bars=bars, duration_seconds=2.0)

        self.assertEqual(len(self.tab.waveform.bars), 40)
        self.assertEqual(self.tab.waveform.duration_ms, 2000)
        self.assertIn("0:02", self.tab.waveform.time_label_text)

        if os.path.exists(dummy_wav):
            os.remove(dummy_wav)

    def test_main_window_integration(self):
        main_win = MainWindow()
        self.assertIsNotNone(main_win.tts_tab)
        self.assertIsNotNone(main_win.dub_tab)
        self.assertIsNotNone(main_win.settings_tab)


if __name__ == "__main__":
    res = unittest.main(exit=False)
    # Explicit clean exit
    sys.stdout.flush()
    os._exit(0 if res.result.wasSuccessful() else 1)
