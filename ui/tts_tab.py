"""
Text-to-Speech Tab for KhmerDub.
Implements the TTS studio view with text input, voice cloning parameters,
waveform result player, and recent generation history.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSlider, QTextEdit, QLineEdit, QFrame, QSizePolicy, QListWidget,
    QListWidgetItem, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor

from ui.styles import (
    COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_BORDER
)
from ui.components import SegmentedTab, WaveformWidget


class TextToSpeechTab(QWidget):
    """Tab 2: Text to speech interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

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

        main_layout.addLayout(upper_layout, stretch=60)

        # Lower Row: Result Player (Left) + Recent Generations (Right)
        lower_layout = QHBoxLayout()
        lower_layout.setSpacing(16)

        result_card = self.create_result_card()
        lower_layout.addWidget(result_card, stretch=60)

        recent_card = self.create_recent_card()
        lower_layout.addWidget(recent_card, stretch=40)

        main_layout.addLayout(lower_layout, stretch=40)

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
        layout.setSpacing(12)

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
        self.lang_combo.setFixedWidth(130)
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
        clear_btn.clicked.connect(self.text_edit.clear)
        bottom_row.addWidget(clear_btn)

        layout.addLayout(bottom_row)
        return card

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
        layout.setSpacing(12)

        # Header
        title = QLabel("Voice")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(title)

        # Mode Selector: [Clone voice | Preset | Auto]
        self.mode_toggle = SegmentedTab(["Clone voice", "Preset", "Auto"], initial_index=0)
        self.mode_toggle.setStyleSheet("""
            QWidget {
                background-color: #F3F4F6;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.mode_toggle)

        # Speaker Reference Clip Box
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
        clip_name = QLabel("speaker_ref.wav")
        clip_name.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        clip_meta = QLabel("8 seconds, mono")
        clip_meta.setStyleSheet("color: #6B7280; font-size: 11px;")
        clip_info.addWidget(clip_name)
        clip_info.addWidget(clip_meta)
        ref_layout.addLayout(clip_info)

        ref_layout.addStretch()

        change_clip_btn = QPushButton("Change clip")
        change_clip_btn.setProperty("class", "SecondaryButton")
        ref_layout.addWidget(change_clip_btn)

        layout.addWidget(self.ref_clip_box)

        # Reference Transcript Input
        ref_trans_label = QLabel("Reference transcript (optional, auto-filled if empty)")
        ref_trans_label.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        layout.addWidget(ref_trans_label)

        self.ref_trans_input = QLineEdit()
        self.ref_trans_input.setPlaceholderText("Leave empty to auto-transcribe...")
        layout.addWidget(self.ref_trans_input)

        # Speed Slider
        self.speed_label = QLabel("Speed: 1.0x")
        self.speed_label.setStyleSheet("color: #374151; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.speed_label)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(5, 20)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"Speed: {v/10:.1f}x")
        )
        layout.addWidget(self.speed_slider)

        # Quality Slider
        self.quality_label = QLabel("Quality: 16 steps (faster to better)")
        self.quality_label.setStyleSheet("color: #374151; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.quality_label)

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(4, 64)
        self.quality_slider.setValue(16)
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"Quality: {v} steps (faster to better)")
        )
        layout.addWidget(self.quality_slider)

        layout.addStretch()

        # Generate Speech Button
        self.generate_btn = QPushButton("Generate speech")
        self.generate_btn.setProperty("class", "PrimaryButton")
        self.generate_btn.setFixedHeight(38)
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.generate_btn)

        return card

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

        self.latency_label = QLabel("Generated in 2.1 s · 6.4 s of audio")
        self.latency_label.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        header_row.addWidget(self.latency_label)

        layout.addLayout(header_row)

        # Waveform Player
        self.waveform = WaveformWidget()
        layout.addWidget(self.waveform)

        layout.addStretch()

        # Action Buttons
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        wav_btn = QPushButton("Save as .wav")
        wav_btn.setProperty("class", "SecondaryButton")
        actions_row.addWidget(wav_btn)

        mp3_btn = QPushButton("Save as .mp3")
        mp3_btn.setProperty("class", "SecondaryButton")
        actions_row.addWidget(mp3_btn)

        dub_btn = QPushButton("Use in a dub")
        dub_btn.setProperty("class", "SecondaryButton")
        actions_row.addWidget(dub_btn)

        actions_row.addStretch()
        layout.addLayout(actions_row)

        return card

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

        # Recent list
        list_widget = QListWidget()
        list_widget.setStyleSheet("""
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

        recent_items = [
            ("Welcome message (Khmer)", "6.4 s"),
            ("Intro line (English)", "3.1 s"),
            ("Closing thanks (Khmer)", "4.8 s")
        ]

        for text, dur in recent_items:
            item_widget = QWidget()
            item_widget.setFixedHeight(34)
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(4, 0, 4, 0)

            lbl_name = QLabel(text)
            lbl_name.setFont(QFont("Segoe UI", 10))
            lbl_dur = QLabel(dur)
            lbl_dur.setStyleSheet("color: #6B7280; font-size: 11px;")

            item_layout.addWidget(lbl_name)
            item_layout.addStretch()
            item_layout.addWidget(lbl_dur)

            list_item = QListWidgetItem()
            list_item.setSizeHint(QSize(100, 36))
            list_widget.addItem(list_item)
            list_widget.setItemWidget(list_item, item_widget)

        layout.addWidget(list_widget)
        return card

    def update_char_count(self):
        count = len(self.text_edit.toPlainText())
        self.char_count_label.setText(f"{count} of 2,000 characters")

    def paste_text(self):
        clipboard = QApplication.clipboard()
        self.text_edit.insertPlainText(clipboard.text())
