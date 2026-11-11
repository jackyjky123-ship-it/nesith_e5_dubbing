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
from core.secure_storage import secure_storage
from core.gemini_service import (
    GEMINI_TTS_MODELS, GEMINI_PREBUILT_VOICES, DEFAULT_SPEECH_INSTRUCTION
)


class TextToSpeechTab(QWidget):
    """Standalone Text-to-Speech Studio."""
    engineChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_result: Optional[TTSResult] = None
        self.worker: Optional[TTSWorkerThread] = None
        cfg = load_config()
        self.current_engine = cfg.get("tts_engine", "mms_khmer")

        self.init_ui()
        self.set_engine(self.current_engine)
        self.on_mode_changed(0)
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

        # Header Row: "Text to speak" (Left) + Auto-detect Badge (Right)
        header_row = QHBoxLayout()
        title = QLabel("Text to speak")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header_row.addWidget(title)
        header_row.addStretch()

        auto_badge = QLabel("Auto-detect: Khmer & English")
        auto_badge.setStyleSheet("""
            QLabel {
                color: #0F6B58;
                background-color: #ECFDF5;
                border: 1px solid #A7F3D0;
                border-radius: 12px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        header_row.addWidget(auto_badge)

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

        # Header Row: Title & Engine Badge
        header_row = QHBoxLayout()
        title = QLabel("Voice")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header_row.addWidget(title)
        header_row.addStretch()

        self.engine_badge = QLabel("Meta MMS-TTS Khmer")
        self.engine_badge.setStyleSheet("""
            QLabel {
                color: #0F6B58;
                background-color: #ECFDF5;
                border: 1px solid #A7F3D0;
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        header_row.addWidget(self.engine_badge)
        layout.addLayout(header_row)

        # Engine Selector: [Local Khmer TTS | Gemini AI TTS]
        init_idx = 0 if self.current_engine == "mms_khmer" else 1
        self.engine_toggle = SegmentedTab(["Local Khmer TTS", "Gemini AI TTS"], initial_index=init_idx)
        self.engine_toggle.tabChanged.connect(self.on_engine_tab_changed)
        layout.addWidget(self.engine_toggle)

        # ---------------------------------------------------------------------
        # Container A: Local Engine Controls (Meta MMS-TTS Khmer)
        # ---------------------------------------------------------------------
        self.local_voice_box = QWidget()
        local_layout = QVBoxLayout(self.local_voice_box)
        local_layout.setContentsMargins(0, 0, 0, 0)
        local_layout.setSpacing(8)

        # Mode Selector: [Auto | Preset]
        self.mode_toggle = SegmentedTab(["Auto", "Preset"], initial_index=0)
        self.mode_toggle.setStyleSheet("""
            QWidget {
                background-color: #F3F4F6;
                border-radius: 8px;
            }
        """)
        self.mode_toggle.tabChanged.connect(self.on_mode_changed)
        local_layout.addWidget(self.mode_toggle)

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
        local_layout.addWidget(self.preset_box)

        # Quality Slider (8 steps is default balanced for CPU)
        self.quality_label = QLabel("Quality: 8 steps (Balanced CPU ~40s)")
        self.quality_label.setStyleSheet("color: #374151; font-size: 11px; font-weight: 500;")
        local_layout.addWidget(self.quality_label)

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(4, 24)
        self.quality_slider.setValue(8)
        self.quality_slider.valueChanged.connect(self.on_quality_changed)
        local_layout.addWidget(self.quality_slider)

        layout.addWidget(self.local_voice_box)

        # ---------------------------------------------------------------------
        # Container B: Gemini AI Voice Controls (Cloud BYOK)
        # ---------------------------------------------------------------------
        self.gemini_voice_box = QWidget()
        gemini_layout = QVBoxLayout(self.gemini_voice_box)
        gemini_layout.setContentsMargins(0, 0, 0, 0)
        gemini_layout.setSpacing(8)

        # Row 1: Model & Voice Pickers side-by-side
        pickers_row = QHBoxLayout()
        pickers_row.setSpacing(8)

        # Model picker
        m_col = QVBoxLayout()
        m_col.setSpacing(2)
        lbl_m = QLabel("Model")
        lbl_m.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: 500;")
        m_col.addWidget(lbl_m)
        self.gemini_model_combo = QComboBox()
        for m_id, m_name in GEMINI_TTS_MODELS.items():
            self.gemini_model_combo.addItem(m_id, m_id)
        m_col.addWidget(self.gemini_model_combo)
        pickers_row.addLayout(m_col, stretch=1)

        # Prebuilt Voice picker
        v_col = QVBoxLayout()
        v_col.setSpacing(2)
        lbl_v = QLabel("Voice (30 Prebuilt)")
        lbl_v.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: 500;")
        v_col.addWidget(lbl_v)
        self.gemini_voice_combo = QComboBox()
        for v_item in GEMINI_PREBUILT_VOICES:
            display_name = f"{v_item['name']} ({v_item['gender']}) - {v_item['desc'].split(',')[0]}"
            self.gemini_voice_combo.addItem(display_name, v_item["id"])
        v_col.addWidget(self.gemini_voice_combo)
        pickers_row.addLayout(v_col, stretch=1)

        gemini_layout.addLayout(pickers_row)

        # Row 2: Speaking Style
        style_row = QHBoxLayout()
        style_row.setSpacing(8)
        lbl_style = QLabel("Style")
        lbl_style.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: 500;")
        self.gemini_style_combo = QComboBox()
        self.gemini_style_combo.addItems([
            "Natural and expressive conversational",
            "Professional documentary narration",
            "Passionate and energetic podcast",
            "Calm, soft, and soothing storytelling",
            "Clear and articulate broadcast news"
        ])
        style_col = QVBoxLayout()
        style_col.setSpacing(2)
        style_col.addWidget(lbl_style)
        style_col.addWidget(self.gemini_style_combo)
        gemini_layout.addLayout(style_col)

        # Row 3: Code-Switching Speech Instruction
        inst_header = QHBoxLayout()
        lbl_inst = QLabel("Khmer + English Speech Instruction")
        lbl_inst.setStyleSheet("color: #374151; font-size: 11px; font-weight: 600;")
        inst_header.addWidget(lbl_inst)
        inst_header.addStretch()

        btn_reset_inst = QPushButton("Reset to Default")
        btn_reset_inst.setFixedHeight(20)
        btn_reset_inst.setStyleSheet("font-size: 10px; color: #0F6B58; border: none; background: transparent;")
        btn_reset_inst.setCursor(Qt.PointingHandCursor)
        btn_reset_inst.clicked.connect(self.reset_gemini_instruction)
        inst_header.addWidget(btn_reset_inst)
        gemini_layout.addLayout(inst_header)

        self.gemini_instruction_edit = QTextEdit()
        self.gemini_instruction_edit.setFixedHeight(64)
        self.gemini_instruction_edit.setPlainText(DEFAULT_SPEECH_INSTRUCTION)
        self.gemini_instruction_edit.setStyleSheet("""
            QTextEdit {
                font-size: 11px;
                line-height: 1.4;
                padding: 6px;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                background-color: #F9FAFB;
            }
            QTextEdit:focus {
                border: 1.5px solid #0F6B58;
                background-color: #FFFFFF;
            }
        """)
        gemini_layout.addWidget(self.gemini_instruction_edit)

        self.gemini_voice_box.setVisible(False)
        layout.addWidget(self.gemini_voice_box)

        # ---------------------------------------------------------------------
        # Shared Controls: Speed Slider & Quick Presets
        # ---------------------------------------------------------------------
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

    def set_engine(self, engine_name: str):
        """Switches between Local Khmer TTS ('mms_khmer') and Gemini AI TTS ('gemini')."""
        is_gemini = (engine_name in ("gemini", 1))
        self.current_engine = "gemini" if is_gemini else "mms_khmer"

        # Update toggle buttons without triggering recursion
        self.engine_toggle.active_index = 1 if is_gemini else 0
        self.engine_toggle.update_styles()

        self.gemini_voice_box.setVisible(is_gemini)
        self.local_voice_box.setVisible(not is_gemini)

        if is_gemini:
            self.engine_badge.setText("Gemini AI (Cloud BYOK)")
            self.engine_badge.setStyleSheet("""
                QLabel {
                    color: #1D4ED8;
                    background-color: #EFF6FF;
                    border: 1px solid #BFDBFE;
                    border-radius: 6px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)
        else:
            self.engine_badge.setText("Meta MMS-TTS Khmer (Offline)")
            self.engine_badge.setStyleSheet("""
                QLabel {
                    color: #0F6B58;
                    background-color: #ECFDF5;
                    border: 1px solid #A7F3D0;
                    border-radius: 6px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)

        cfg = load_config()
        cfg["tts_engine"] = self.current_engine
        save_config(cfg)
        self.engineChanged.emit(self.current_engine)

    def on_engine_tab_changed(self, idx: int):
        target = "gemini" if idx == 1 else "mms_khmer"
        self.set_engine(target)

    def reset_gemini_instruction(self):
        """Restores default single-speaker code-switching instruction."""
        self.gemini_instruction_edit.setPlainText(DEFAULT_SPEECH_INSTRUCTION)

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
        """Switches between Auto (0) and Preset (1)."""
        is_preset = (index == 1)
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

        # Engine 1: Google Gemini AI TTS
        if self.current_engine == "gemini":
            if not secure_storage.has_api_key():
                QMessageBox.warning(
                    self,
                    "Gemini API Key Required",
                    "You have selected Gemini AI TTS, but no API key was found.\n\n"
                    "Please open the Settings tab to enter and save your Gemini API key."
                )
                return

            speed = self.speed_slider.value() / 100.0
            model = self.gemini_model_combo.currentText() if hasattr(self, "gemini_model_combo") else "gemini-3.8-flash-tts"
            voice = self.gemini_voice_combo.currentData() if hasattr(self, "gemini_voice_combo") else "Kore"
            style = self.gemini_style_combo.currentText() if hasattr(self, "gemini_style_combo") else "natural"
            instruction = self.gemini_instruction_edit.toPlainText().strip() if hasattr(self, "gemini_instruction_edit") else None

            self.generate_btn.setEnabled(False)
            self.generate_btn.setText("Generating speech...")
            self.lbl_gen_status.setText("Connecting to Gemini API...")

            self.worker = TTSWorkerThread(
                text=text,
                speed=speed,
                engine_override="gemini",
                gemini_model=model,
                gemini_voice=voice,
                gemini_style=style,
                gemini_instruction=instruction,
                parent=self
            )
            self.worker.status_updated.connect(self.on_worker_status)
            self.worker.finished_success.connect(self.on_synthesis_success)
            self.worker.finished_error.connect(self.on_synthesis_error)
            self.worker.start()
            return

        # Engine 2: Local Meta MMS-TTS Khmer
        mode_idx = self.mode_toggle.active_index
        mode = "preset" if mode_idx == 1 else "auto"

        # Language is automatically detected (Khmer, English, or mixed bilingual)
        lang = "auto"
        engine_override = "mms_khmer"

        preset_name = self.preset_combo.currentText() if mode == "preset" else None
        speed = self.speed_slider.value() / 100.0
        quality_steps = self.quality_slider.value()

        # UI state: Generating
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("Generating speech...")
        self.lbl_gen_status.setText("Preparing model...")

        self.worker = TTSWorkerThread(
            text=text,
            language=lang,
            mode=mode,
            ref_audio_path=None,
            ref_text=None,
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

        engine_display = "Gemini AI" if result.engine_name == "gemini" else "Meta MMS-TTS"
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
