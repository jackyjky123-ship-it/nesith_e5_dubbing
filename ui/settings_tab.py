"""
Settings Tab for KhmerDub.
Implements the configuration interface for pipeline engines, hardware performance
(GTX 1050 vs CPU), low-memory management, and local storage/cache cleanup.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QLineEdit, QFrame, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ui.styles import (
    COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_BORDER, STATUS_WARNING_BANNER_BG,
    STATUS_WARNING_BANNER_BORDER, STATUS_WARNING_BANNER_TEXT
)
from ui.components import StatusBadge


class SettingsTab(QWidget):
    """Tab 3: Settings interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Upper Two Columns: Engines (Left) + Performance & Storage (Right)
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(16)

        # Left Column: Engines Card
        engines_card = self.create_engines_card()
        columns_layout.addWidget(engines_card, stretch=55)

        # Right Column: Performance & Storage
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        perf_card = self.create_performance_card()
        right_col.addWidget(perf_card)

        storage_card = self.create_storage_card()
        right_col.addWidget(storage_card)

        columns_layout.addLayout(right_col, stretch=45)

        main_layout.addLayout(columns_layout, stretch=1)

        # Bottom Banner: License & Quality Advisory
        banner = self.create_license_banner()
        main_layout.addWidget(banner)

    def create_engines_card(self) -> QFrame:
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
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(18)

        # Title
        title = QLabel("Text-to-Speech Engines (Local & Offline)")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(title)

        # Row 1: Speech Synthesis Engine (Meta MMS-TTS Khmer)
        layout.addLayout(self.create_engine_row(
            label_text="Speech Engine",
            input_label="Engine",
            combo_items=[
                "Meta MMS-TTS Khmer (Local, 139 MB) — Khmer & English"
            ],
            badge_text="Loaded",
            badge_type="green"
        ))

        layout.addWidget(self.create_divider())

        # Row 2: Audio tools (ffmpeg)
        video_row = QHBoxLayout()
        video_row.setSpacing(12)

        v_label = QLabel("Audio tools")
        v_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        v_label.setFixedWidth(130)
        video_row.addWidget(v_label)

        v_info = QVBoxLayout()
        v_info.setSpacing(2)
        v_name = QLabel("ffmpeg")
        v_name.setFont(QFont("Segoe UI", 11, QFont.Medium))
        v_desc = QLabel("Bundled with the app for audio processing & MP3/WAV export")
        v_desc.setStyleSheet("color: #6B7280; font-size: 11px;")
        v_info.addWidget(v_name)
        v_info.addWidget(v_desc)
        video_row.addLayout(v_info, stretch=1)

        v_badge = StatusBadge("Ready", "green")
        video_row.addWidget(v_badge)

        layout.addLayout(video_row)
        layout.addStretch()

        return card

    def create_engine_row(self, label_text: str, input_label: str,
                          combo_items: list[str], badge_text: str, badge_type: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        lbl = QLabel(label_text)
        lbl.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        lbl.setFixedWidth(130)
        row.addWidget(lbl)

        field_col = QVBoxLayout()
        field_col.setSpacing(4)
        sub_lbl = QLabel(input_label)
        sub_lbl.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: 500;")
        combo = QComboBox()
        combo.addItems(combo_items)
        field_col.addWidget(sub_lbl)
        field_col.addWidget(combo)
        row.addLayout(field_col, stretch=1)

        badge = StatusBadge(badge_text, badge_type)
        row.addWidget(badge)

        return row

    def create_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("background-color: #F3F4F6; max-height: 1px;")
        return line

    def create_performance_card(self) -> QFrame:
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

        # Title
        title = QLabel("Performance")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(title)

        # Run model on
        run_lbl = QLabel("Run voice model on")
        run_lbl.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        layout.addWidget(run_lbl)

        self.device_combo = QComboBox()
        self.device_combo.addItems([
            "GPU (GTX 1050, 2 GB)",
            "CPU (Intel i7-8750H, 8 threads)"
        ])
        layout.addWidget(self.device_combo)

        # Precision
        prec_lbl = QLabel("Precision")
        prec_lbl.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        layout.addWidget(prec_lbl)

        self.prec_combo = QComboBox()
        self.prec_combo.addItems([
            "FP16 (about 1.3 GB VRAM)",
            "INT8 (about 0.7 GB VRAM, CPU/GPU)",
            "FP32 (Standard CPU)"
        ])
        layout.addWidget(self.prec_combo)

        # Low-memory mode checkbox
        self.low_mem_cb = QCheckBox("Low-memory mode: free each model after its step")
        self.low_mem_cb.setChecked(True)
        layout.addWidget(self.low_mem_cb)

        return card

    def create_storage_card(self) -> QFrame:
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

        # Title
        title = QLabel("Storage")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(title)

        # Output folder
        out_lbl = QLabel("Output folder")
        out_lbl.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        layout.addWidget(out_lbl)

        out_row = QHBoxLayout()
        self.output_input = QLineEdit("exports/")
        out_row.addWidget(self.output_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.setProperty("class", "SecondaryButton")
        browse_btn.clicked.connect(self.browse_folder)
        out_row.addWidget(browse_btn)
        layout.addLayout(out_row)

        # Model files and cache size
        cache_row = QHBoxLayout()
        cache_lbl = QLabel("Model files and cache")
        cache_lbl.setStyleSheet("color: #374151; font-size: 12px; font-weight: 500;")
        cache_size = QLabel("3.2 GB")
        cache_size.setStyleSheet("color: #6B7280; font-size: 12px; font-weight: 600;")
        cache_row.addWidget(cache_lbl)
        cache_row.addStretch()
        cache_row.addWidget(cache_size)
        layout.addLayout(cache_row)

        # Cleanup Buttons
        actions_row = QHBoxLayout()
        clear_temp_btn = QPushButton("Clear temporary files")
        clear_temp_btn.setProperty("class", "SecondaryButton")
        actions_row.addWidget(clear_temp_btn)

        del_models_btn = QPushButton("Delete downloaded models")
        del_models_btn.setProperty("class", "SecondaryButton")
        actions_row.addWidget(del_models_btn)

        layout.addLayout(actions_row)

        return card

    def create_license_banner(self) -> QFrame:
        banner = QFrame()
        banner.setStyleSheet(f"""
            QFrame {{
                background-color: {STATUS_WARNING_BANNER_BG};
                border: 1px solid {STATUS_WARNING_BANNER_BORDER};
                border-radius: 8px;
                padding: 10px 14px;
            }}
        """)
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(12, 10, 12, 10)

        icon_lbl = QLabel("ℹ️")
        icon_lbl.setStyleSheet("font-size: 14px;")
        layout.addWidget(icon_lbl)

        text_lbl = QLabel(
            "Check the model license before selling or monetizing generated audio. "
            "Output quality for Khmer should be tested with your own sample clips first."
        )
        text_lbl.setStyleSheet(f"""
            color: {STATUS_WARNING_BANNER_TEXT};
            font-size: 12px;
            font-weight: 500;
        """)
        layout.addWidget(text_lbl, stretch=1)

        return banner

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_input.setText(folder)

