"""
KhmerDub - Text-to-Speech Studio Tab.
Implements the complete TTS workflow matching the UI mockup:
- Text editor with real-time character count and language selector.
- Voice configuration: Voice Cloning (with reference audio), Presets, Auto.
- Engine mode selector: Meta MMS-TTS Khmer (Local), Bilingual Transliteration.
- Background QThread synthesis worker (non-blocking UI).
- Real-time Waveform Player with seeking and audio playback.
- WAV and MP3 export using bundled ffmpeg.
- Persistent recent generations history with click-to-replay.
"""

import os
import time
import soundfile as sf
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSlider, QTextEdit, QLineEdit, QFrame, QSizePolicy, QListWidget,
    QListWidgetItem, QApplication, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor

from ui.styles import (
    COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_BORDER, COLOR_BG_WINDOW
)
from ui.components import SegmentedTab, WaveformWidget
from core.config import (
    ASSETS_DIR, EXPORTS_DIR, TEMP_DIR, load_config, save_config
)
from core.tts_engine import tts_manager, TTSResult, compute_waveform_bars
from core.controller import TTSWorkerThread, load_recent_tts, add_recent_tts


class TextToSpeechTab(QWidget):
    """Tab 2: Standalone Text-to-Speech Studio."""
    useInDubClicked = Signal(str, str)  # (audio_path, text)

    def __init__(self, parent=None):
        super().__init__(parent)
        cfg = load_config()
        saved_clip = cfg.get("last_reference_clip")
        phanith_clip = os.path.join(ASSETS_DIR, "phanith_speaker.wav")
        sample_clip = os.path.join(ASSETS_DIR, "sample_speaker.wav")
        if saved_clip and os.path.exists(saved_clip):
            self.current_ref_clip = saved_clip
        elif os.path.exists(phanith_clip):
            self.current_ref_clip = phanith_clip
        else:
            self.current_ref_clip = sample_clip

        self.current_result: Optional[TTSResult] = None
        self.worker: Optional[TTSWorkerThread] = None

        self.init_ui()
        self.on_mode_changed(2)
        self.load_initial_ref_clip()
        self.refresh_recent_list()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 18, 24, 18)
        main_layout.setSpacing(16)

        # Upper Row: Text to speak (Left) + Voice Configuration (Right)
        upper_layout = QHBoxLayout()
        upper_layout.setSpacing(16)

        text_card = self.create_text_input_card()
        upper_layout.addWidget(text_card, stretch=60)

        voice_card = self.create_voice_card()
        upper_layout.addWidget(voice_card, stretch=40)

        main_layout.addLayout(upper_layout, stretch=58)

        # Lower Row: Result Player (Left) + Recent Generations (Right)
        lower_layout = QHBoxLayout()
        lower_layout.setSpacing(16)

        result_card = self.create_result_card()
        lower_layout.addWidget(result_card, stretch=60)

        recent_card = self.create_recent_card()
        lower_layout.addWidget(recent_card, stretch=40)

        main_layout.addLayout(lower_layout, stretch=42)

    # -------------------------------------------------------------------------
    # Card 1: Text to Speak
    # -------------------------------------------------------------------------
    def create_text_input_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "CardFrame")
        card.setStyleSheet("""
            QFrame.CardFrame {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Header Row: "Text to speak" (Left) + Language Selector (Right)
        header_row = QHBoxLayout()
        title = QLabel("Text to speak")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header_row.addWidget(title)
        header_row.addStretch()

        lang_label = QLabel("Language")
        lang_label.setStyleSheet("color: #6B7280; font-size: 12px; font-weight: 500;")
        header_row.addWidget(lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Khmer", "English", "Auto-detect"])
        self.lang_combo.setCurrentText("Khmer")
        self.lang_combo.setFixedWidth(120)
        header_row.addWidget(self.lang_combo)

        layout.addLayout(header_row)

        # Multi-line Text Editor
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("វាយ ឬចម្លងអត្ថបទនៅទីនេះ... (Type or paste text here...)")
        self.text_edit.setText(
            "សួស្តី សូមស្វាគមន៍មកកាន់ដំណើរទស្សនកិច្ចផលិតផលរបស់យើង។ "
            "ថ្ងៃនេះ យើងនឹងបង្ហាញអ្នកអំពីជំហានសាមញ្ញចំនួនបី។"
        )
        self.text_edit.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                line-height: 1.6;
                padding: 12px;
                border: 1px solid #D1D5DB;
                border-radius: 8px;
            }
            QTextEdit:focus {
                border: 1.5px solid #0F6B58;
            }
        """)
        self.text_edit.textChanged.connect(self.update_char_count)
        layout.addWidget(self.text_edit)

        # Bottom Bar: Char counter (Left) + Paste / Clear buttons (Right)
        bottom_row = QHBoxLayout()
        self.char_count_label = QLabel("96 of 2,000 characters")
        self.char_count_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        bottom_row.addWidget(self.char_count_label)
        bottom_row.addStretch()

        paste_btn = QPushButton("Paste")
        paste_btn.setProperty("class", "SecondaryButton")
        paste_btn.clicked.connect(self.paste_text)
        bottom_row.addWidget(paste_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setProperty("class", "SecondaryButton")
        clear_btn.clicked.connect(self.clear_text)
        bottom_row.addWidget(clear_btn)

        layout.addLayout(bottom_row)
        return card

    # -------------------------------------------------------------------------
    # Card 2: Voice Configuration
    # -------------------------------------------------------------------------
    def create_voice_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "CardFrame")
        card.setStyleSheet("""
            QFrame.CardFrame {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Header Row: Title & Engine dropdown
        header_row = QHBoxLayout()
        title = QLabel("Voice")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header_row.addWidget(title)
        header_row.addStretch()

        self.engine_combo = QComboBox()
        self.engine_combo.addItems([
            "Meta MMS-TTS Khmer (Local)",
            "Meta MMS-TTS (Bilingual Transliteration)"
        ])
        self.engine_combo.setFixedWidth(220)
        self.engine_combo.setStyleSheet("font-size: 11px;")
        header_row.addWidget(self.engine_combo)
        layout.addLayout(header_row)

        # Mode Selector: [Clone voice | Preset | Auto] (Default to Auto for fast native TTS)
        self.mode_toggle = SegmentedTab(["Clone voice", "Preset", "Auto"], initial_index=2)
        self.mode_toggle.setStyleSheet("""
            QWidget {
                background-color: #F3F4F6;
                border-radius: 8px;
            }
        """)
        self.mode_toggle.tabChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_toggle)

        # Speaker Reference Clip Box (Clone voice mode)
        self.ref_clip_box = QFrame()
        self.ref_clip_box.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border: 1px dashed #D1D5DB;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        ref_layout = QHBoxLayout(self.ref_clip_box)
        ref_layout.setContentsMargins(12, 8, 12, 8)

        clip_info = QVBoxLayout()
        clip_info.setSpacing(2)
        self.lbl_clip_name = QLabel("speaker_ref.wav")
        self.lbl_clip_name.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        self.lbl_clip_meta = QLabel("8 seconds, mono")
        self.lbl_clip_meta.setStyleSheet("color: #6B7280; font-size: 11px;")
        clip_info.addWidget(self.lbl_clip_name)
        clip_info.addWidget(self.lbl_clip_meta)
        ref_layout.addLayout(clip_info)

        ref_layout.addStretch()

        change_clip_btn = QPushButton("Change clip")
        change_clip_btn.setProperty("class", "SecondaryButton")
        change_clip_btn.clicked.connect(self.choose_reference_clip)
        ref_layout.addWidget(change_clip_btn)

        layout.addWidget(self.ref_clip_box)

        # Reference Transcript Input (Clone voice mode)
        self.ref_trans_label = QLabel("Reference transcript (optional, auto-filled if empty)")
        self.ref_trans_label.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.ref_trans_label)

        self.ref_trans_input = QLineEdit()
        self.ref_trans_input.setPlaceholderText("Leave empty to auto-transcribe...")
        layout.addWidget(self.ref_trans_input)

        # Preset Voice Dropdown (Preset mode, initially hidden)
        self.preset_box = QWidget()
        preset_layout = QVBoxLayout(self.preset_box)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(4)
        lbl_preset = QLabel("Preset Voice Character")
        lbl_preset.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        preset_layout.addWidget(lbl_preset)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "Professional Female",
            "Friendly Male",
            "Deep Male",
            "Warm Storyteller",
            "News Anchor"
        ])
        preset_layout.addWidget(self.preset_combo)
        self.preset_box.setVisible(False)
        layout.addWidget(self.preset_box)

        # Speed Slider & Fine Granular Presets
        self.speed_label = QLabel("Speed: 1.0x")
        self.speed_label.setStyleSheet("color: #374151; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.speed_label)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setSingleStep(5)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        layout.addWidget(self.speed_slider)

        # Quick Speed Presets: 0.75x, 1.0x, 1.25x, 1.5x, 1.75x, 2.0x
        presets_row = QHBoxLayout()
        presets_row.setSpacing(4)
        for s_val, s_txt in [
            (0.75, "0.75x"),
            (1.0, "1.0x"),
            (1.25, "1.25x"),
            (1.5, "1.5x"),
            (1.75, "1.75x"),
            (2.0, "2.0x")
        ]:
            btn = QPushButton(s_txt)
            btn.setFixedHeight(22)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F3F4F6;
                    color: #4B5563;
                    border: 1px solid #E5E7EB;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 500;
                    padding: 0px 4px;
                }
                QPushButton:hover {
                    background-color: #E5E7EB;
                    color: #111827;
                }
            """)
            btn.clicked.connect(lambda checked=False, val=s_val: self.set_speed(val))
            presets_row.addWidget(btn)
        layout.addLayout(presets_row)

        # Quality Slider (8 steps is default balanced for CPU)
        self.quality_label = QLabel("Quality: 8 steps (Balanced CPU ~40s)")
        self.quality_label.setStyleSheet("color: #374151; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.quality_label)

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(4, 24)
        self.quality_slider.setValue(8)
        self.quality_slider.valueChanged.connect(self.on_quality_changed)
        layout.addWidget(self.quality_slider)

        layout.addStretch()

        # Status & Generate Speech Button
        self.lbl_gen_status = QLabel("")
        self.lbl_gen_status.setStyleSheet("color: #0F6B58; font-size: 11px; font-weight: 500;")
        self.lbl_gen_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_gen_status)

        self.generate_btn = QPushButton("Generate speech")
        self.generate_btn.setProperty("class", "PrimaryButton")
        self.generate_btn.setFixedHeight(38)
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.clicked.connect(self.on_generate_clicked)
        layout.addWidget(self.generate_btn)

        return card

    # -------------------------------------------------------------------------
    # Card 3: Result Player & Export
    # -------------------------------------------------------------------------
    def create_result_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "CardFrame")
        card.setStyleSheet("""
            QFrame.CardFrame {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("Result")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header_row.addWidget(title)
        header_row.addStretch()

        self.latency_label = QLabel("Ready to synthesize")
        self.latency_label.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        header_row.addWidget(self.latency_label)

        self.free_ram_btn = QPushButton("Free RAM")
        self.free_ram_btn.setProperty("class", "SecondaryButton")
        self.free_ram_btn.setFixedHeight(22)
        self.free_ram_btn.setStyleSheet("font-size: 10px; padding: 1px 8px;")
        self.free_ram_btn.setToolTip("Unload model from memory to free system RAM")
        self.free_ram_btn.clicked.connect(self.free_ram)
        header_row.addWidget(self.free_ram_btn)

        layout.addLayout(header_row)

        # Waveform Player
        self.waveform = WaveformWidget()
        layout.addWidget(self.waveform)

        layout.addStretch()

        # Action Buttons
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.wav_btn = QPushButton("Save as .wav")
        self.wav_btn.setProperty("class", "SecondaryButton")
        self.wav_btn.clicked.connect(self.save_as_wav)
        actions_row.addWidget(self.wav_btn)

        self.mp3_btn = QPushButton("Save as .mp3")
        self.mp3_btn.setProperty("class", "SecondaryButton")
        self.mp3_btn.clicked.connect(self.save_as_mp3)
        actions_row.addWidget(self.mp3_btn)

        self.dub_btn = QPushButton("Use in a dub")
        self.dub_btn.setProperty("class", "SecondaryButton")
        self.dub_btn.clicked.connect(self.on_use_in_dub_clicked)
        self.dub_btn.setVisible(False)

        actions_row.addStretch()
        layout.addLayout(actions_row)

        return card

    # -------------------------------------------------------------------------
    # Card 4: Recent Generations History
    # -------------------------------------------------------------------------
    def create_recent_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "CardFrame")
        card.setStyleSheet("""
            QFrame.CardFrame {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        # Header
        title = QLabel("Recent")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(title)

        # Recent list widget
        self.recent_list = QListWidget()
        self.recent_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
            }
            QListWidget::item {
                border-bottom: 1px solid #F3F4F6;
                color: #111827;
            }
            QListWidget::item:hover {
                background-color: #F9FAFB;
                border-radius: 6px;
            }
        """)
        self.recent_list.itemClicked.connect(self.on_recent_item_clicked)
        layout.addWidget(self.recent_list)

        return card

    # -------------------------------------------------------------------------
    # Event Handlers & Core Methods
    # -------------------------------------------------------------------------
    def on_mode_changed(self, index: int):
        """Switches between Clone voice (0), Preset (1), and Auto (2)."""
        is_clone = (index == 0)
        is_preset = (index == 1)

        self.ref_clip_box.setVisible(is_clone)
        self.ref_trans_label.setVisible(is_clone)
        self.ref_trans_input.setVisible(is_clone)
        self.preset_box.setVisible(is_preset)

    def on_speed_changed(self, v: int):
        """Updates speed slider label with precise formatting."""
        speed_val = v / 100.0
        if v % 10 == 0:
            self.speed_label.setText(f"Speed: {speed_val:.1f}x")
        else:
            self.speed_label.setText(f"Speed: {speed_val:.2f}x")

    def set_speed(self, speed_val: float):
        """Sets speed slider to exact preset value."""
        self.speed_slider.setValue(int(round(speed_val * 100)))

    def on_quality_changed(self, v: int):
        """Updates quality slider label with estimated CPU performance."""
        speed_tag = "Fast CPU (~20s)" if v <= 6 else "Balanced (~45s)" if v <= 10 else "High Quality (~90s+)"
        self.quality_label.setText(f"Quality: {v} steps ({speed_tag})")

    def free_ram(self):
        """Manually unloads models from memory to free host RAM."""
        tts_manager.unload_model()
        self.latency_label.setText("Model unloaded · RAM freed")

    def load_initial_ref_clip(self):
        """Loads and inspects the default reference audio clip."""
        if os.path.exists(self.current_ref_clip):
            self.update_clip_display(self.current_ref_clip)
        else:
            self.lbl_clip_name.setText("No clip selected")
            self.lbl_clip_meta.setText("Click 'Change clip' to select a reference audio")

    def update_clip_display(self, clip_path: str):
        """Reads audio duration and channels to display in the UI card and auto-populates reference text."""
        self.current_ref_clip = clip_path
        filename = os.path.basename(clip_path)
        self.lbl_clip_name.setText(filename)
        try:
            info = sf.info(clip_path)
            chan_str = "mono" if info.channels == 1 else "stereo"
            self.lbl_clip_meta.setText(f"{info.duration:.1f} seconds, {chan_str}")
        except Exception:
            self.lbl_clip_meta.setText("Audio clip loaded")

        # Auto-populate reference transcript if known or if empty
        lower_name = filename.lower()
        if "phanith" in lower_name:
            self.ref_trans_input.setText("There's a lot of people on the street, but they don't have a lot of people on the street.")
        elif "sample_speaker" in lower_name:
            self.ref_trans_input.setText("Hello, welcome to KhmerTTS, an offline speech studio.")

    def choose_reference_clip(self):
        """Prompts user to select a custom voice reference clip."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Speaker Reference Audio",
            ASSETS_DIR,
            "Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a)"
        )
        if file_path:
            self.update_clip_display(file_path)
            try:
                cfg = load_config()
                cfg["last_reference_clip"] = file_path
                save_config(cfg)
            except Exception:
                pass

    def update_char_count(self):
        count = len(self.text_edit.toPlainText())
        self.char_count_label.setText(f"{count} of 2,000 characters")

    def paste_text(self):
        clipboard = QApplication.clipboard()
        self.text_edit.insertPlainText(clipboard.text())

    def clear_text(self):
        self.text_edit.clear()
        self.update_char_count()

    def on_generate_clicked(self):
        """Starts background speech synthesis."""
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty Text", "Please enter some text to synthesize.")
            return

        mode_idx = self.mode_toggle.active_index
        mode_map = {0: "clone", 1: "preset", 2: "auto"}
        mode = mode_map.get(mode_idx, "clone")

        lang_text = self.lang_combo.currentText().lower()
        if "khmer" in lang_text:
            lang = "km"
        elif "english" in lang_text:
            lang = "en"
        else:
            lang = "auto"

        # Resolve engine selection (Meta MMS-TTS)
        engine_override = "mms_khmer"

        preset_name = self.preset_combo.currentText() if mode == "preset" else None
        speed = self.speed_slider.value() / 100.0
        quality_steps = self.quality_slider.value()
        ref_text = self.ref_trans_input.text().strip()

        # UI state: Generating
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("Generating speech...")
        self.lbl_gen_status.setText("Preparing model...")

        self.worker = TTSWorkerThread(
            text=text,
            language=lang,
            mode=mode,
            ref_audio_path=self.current_ref_clip if mode == "clone" else None,
            ref_text=ref_text if mode == "clone" else None,
            preset_name=preset_name,
            speed=speed,
            quality_steps=quality_steps,
            engine_override=engine_override,
            parent=self
        )
        self.worker.status_updated.connect(self.on_worker_status)
        self.worker.finished_success.connect(self.on_synthesis_success)
        self.worker.finished_error.connect(self.on_synthesis_error)
        self.worker.start()

    def on_worker_status(self, msg: str):
        self.lbl_gen_status.setText(msg)

    def on_synthesis_success(self, result: TTSResult):
        self.current_result = result
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate speech")
        self.lbl_gen_status.setText("")

        engine_display = "Meta MMS-TTS"
        self.latency_label.setText(
            f"Generated in {result.latency_seconds:.1f} s · {result.duration_seconds:.1f} s audio ({engine_display})"
        )

        # Update Waveform
        self.waveform.set_audio(
            result.temp_wav_path,
            bars=result.waveform_bars,
            duration_seconds=result.duration_seconds
        )

        # Refresh recent history
        self.refresh_recent_list()

    def on_synthesis_error(self, err_msg: str):
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate speech")
        self.lbl_gen_status.setText("")
        QMessageBox.critical(self, "Synthesis Error", err_msg)

    def save_as_wav(self):
        """Exports currently generated audio as .wav file."""
        if not self.current_result or not os.path.exists(self.current_result.temp_wav_path):
            QMessageBox.information(self, "No Audio", "Please generate speech first before saving.")
            return

        default_name = f"tts_{int(time.time())}.wav"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Audio as WAV",
            os.path.join(EXPORTS_DIR, default_name),
            "WAV Audio (*.wav)"
        )
        if save_path:
            try:
                tts_manager.export_audio(self.current_result.temp_wav_path, save_path, fmt="wav")
                QMessageBox.information(self, "Saved", f"Audio successfully saved to:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save WAV: {e}")

    def save_as_mp3(self):
        """Exports currently generated audio as .mp3 file using bundled ffmpeg."""
        if not self.current_result or not os.path.exists(self.current_result.temp_wav_path):
            QMessageBox.information(self, "No Audio", "Please generate speech first before saving.")
            return

        default_name = f"tts_{int(time.time())}.mp3"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Audio as MP3",
            os.path.join(EXPORTS_DIR, default_name),
            "MP3 Audio (*.mp3)"
        )
        if save_path:
            try:
                tts_manager.export_audio(self.current_result.temp_wav_path, save_path, fmt="mp3")
                QMessageBox.information(self, "Saved", f"MP3 successfully exported to:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to save MP3: {e}")

    def on_use_in_dub_clicked(self):
        """Emits signal to pass audio to Dubbing tab."""
        if not self.current_result or not os.path.exists(self.current_result.temp_wav_path):
            QMessageBox.information(self, "No Audio", "Please generate speech first.")
            return

        self.useInDubClicked.emit(
            self.current_result.temp_wav_path,
            self.current_result.text
        )
        QMessageBox.information(
            self,
            "Dub Studio",
            "This generated audio has been forwarded for video dubbing!"
        )

    def refresh_recent_list(self):
        """Reloads the recent items list from disk."""
        self.recent_list.clear()
        recent_items = load_recent_tts()

        if not recent_items:
            placeholder = QListWidgetItem("No recent generations yet")
            placeholder.setFlags(Qt.NoItemFlags)
            self.recent_list.addItem(placeholder)
            return

        for item in recent_items:
            text = item.get("text", "")
            dur_str = item.get("duration_str", "")

            item_widget = QWidget()
            item_widget.setFixedHeight(34)
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(6, 0, 6, 0)

            lbl_name = QLabel(text)
            lbl_name.setFont(QFont("Segoe UI", 10))
            lbl_name.setStyleSheet("color: #111827;")

            lbl_dur = QLabel(dur_str)
            lbl_dur.setStyleSheet("color: #6B7280; font-size: 11px;")

            item_layout.addWidget(lbl_name)
            item_layout.addStretch()
            item_layout.addWidget(lbl_dur)

            list_item = QListWidgetItem()
            list_item.setSizeHint(QSize(100, 36))
            list_item.setData(Qt.UserRole, item)
            self.recent_list.addItem(list_item)
            self.recent_list.setItemWidget(list_item, item_widget)

    def on_recent_item_clicked(self, list_item: QListWidgetItem):
        """Reloads a previously generated speech item into the Result player."""
        data = list_item.data(Qt.UserRole)
        if not data:
            return

        wav_path = data.get("wav_path")
        full_text = data.get("full_text", "")
        dur_sec = data.get("duration_sec", 0.0)

        if wav_path and os.path.exists(wav_path):
            try:
                audio_np, sr = sf.read(wav_path)
                bars = compute_waveform_bars(audio_np, 40)
                dur = len(audio_np) / float(sr)

                self.current_result = TTSResult(
                    audio_np=audio_np,
                    sample_rate=sr,
                    duration_seconds=dur,
                    latency_seconds=0.0,
                    real_time_factor=0.0,
                    temp_wav_path=wav_path,
                    waveform_bars=bars,
                    text=full_text,
                    language=data.get("language", "km"),
                    engine_name=data.get("engine", "mms_khmer"),
                    mode="recent"
                )

                self.latency_label.setText(f"Loaded from recent · {dur:.1f} s of audio")
                self.waveform.set_audio(wav_path, bars=bars, duration_seconds=dur)
            except Exception as e:
                print(f"[tts_tab] Error reloading recent item: {e}")
