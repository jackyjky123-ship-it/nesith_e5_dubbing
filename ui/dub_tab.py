"""
Dub Video Tab for KhmerDub.
Implements the 5-step dubbing pipeline view with video player preview,
dubbing settings, interactive editable segments table, and status bar.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSlider, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from ui.styles import (
    COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_BORDER
)
from ui.components import PipelineStepper, StatusBadge


class DubVideoTab(QWidget):
    """Tab 1: Dub video interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 14, 24, 18)
        main_layout.setSpacing(14)

        # 1. Pipeline Stepper
        self.stepper = PipelineStepper()
        self.stepper.set_current_step(3) # "Translate" active in mockup
        main_layout.addWidget(self.stepper)

        # 2. Upper Row: Video Preview (Left) + Dubbing Options (Right)
        upper_layout = QHBoxLayout()
        upper_layout.setSpacing(16)

        # Left: Video Player Preview Frame
        video_card = self.create_video_preview_card()
        upper_layout.addWidget(video_card, stretch=64)

        # Right: Dubbing Options Card
        options_card = self.create_options_card()
        upper_layout.addWidget(options_card, stretch=36)

        main_layout.addLayout(upper_layout, stretch=48)

        # 3. Lower Row: Segments Table Card
        segments_card = self.create_segments_card()
        main_layout.addWidget(segments_card, stretch=52)

        # 4. Bottom Resource / Action Bar
        bottom_bar = self.create_bottom_bar()
        main_layout.addLayout(bottom_bar)

    def create_video_preview_card(self) -> QFrame:
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
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Video Screen Container (Dark background)
        screen_frame = QFrame()
        screen_frame.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border-radius: 8px;
            }
        """)
        screen_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        screen_layout = QVBoxLayout(screen_frame)
        screen_layout.setContentsMargins(14, 14, 14, 14)

        # Top tag: product_tour.mp4
        top_row = QHBoxLayout()
        filename_badge = QLabel("product_tour.mp4")
        filename_badge.setStyleSheet("""
            background-color: rgba(31, 41, 55, 0.85);
            color: #E5E7EB;
            font-size: 11px;
            font-weight: 500;
            padding: 3px 10px;
            border-radius: 6px;
        """)
        top_row.addWidget(filename_badge)
        top_row.addStretch()
        screen_layout.addLayout(top_row)

        screen_layout.addStretch()

        # Center Play Button
        play_btn = QPushButton("▶")
        play_btn.setFixedSize(48, 48)
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.25);
                color: #FFFFFF;
                border: 2px solid rgba(255, 255, 255, 0.6);
                border-radius: 24px;
                font-size: 18px;
                padding-left: 3px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.4);
            }
        """)
        center_row = QHBoxLayout()
        center_row.addStretch()
        center_row.addWidget(play_btn)
        center_row.addStretch()
        screen_layout.addLayout(center_row)

        screen_layout.addStretch()

        # Bottom Subtitle Overlay
        sub_label = QLabel("ជាដំបូង សូមបើកកម្មវិធី ហើយចូលគណនីរបស់អ្នក។")
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setStyleSheet("""
            background-color: rgba(17, 24, 39, 0.85);
            color: #FFFFFF;
            font-size: 14px;
            font-weight: 500;
            padding: 6px 16px;
            border-radius: 6px;
        """)
        sub_row = QHBoxLayout()
        sub_row.addStretch()
        sub_row.addWidget(sub_label)
        sub_row.addStretch()
        screen_layout.addLayout(sub_row)

        layout.addWidget(screen_frame)

        # Timeline Scrubber Bar
        timeline_layout = QHBoxLayout()
        timeline_layout.setContentsMargins(4, 0, 4, 0)
        time_cur = QLabel("00:10")
        time_cur.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        timeline_layout.addWidget(time_cur)

        self.video_slider = QSlider(Qt.Horizontal)
        self.video_slider.setRange(0, 62)
        self.video_slider.setValue(10)
        timeline_layout.addWidget(self.video_slider)

        time_total = QLabel("01:02")
        time_total.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        timeline_layout.addWidget(time_total)

        layout.addLayout(timeline_layout)
        return card

    def create_options_card(self) -> QFrame:
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
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Title
        title = QLabel("Dubbing options")
        title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(title)

        # From / To Language Selectors
        lang_row = QHBoxLayout()
        lang_row.setSpacing(8)

        # From
        from_col = QVBoxLayout()
        from_col.setSpacing(3)
        from_label = QLabel("From")
        from_label.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        self.from_combo = QComboBox()
        self.from_combo.addItems(["English", "Khmer"])
        from_col.addWidget(from_label)
        from_col.addWidget(self.from_combo)
        lang_row.addLayout(from_col, stretch=1)

        # Swap button
        swap_col = QVBoxLayout()
        swap_col.setSpacing(3)
        swap_col.addSpacing(16)
        swap_btn = QPushButton("⇆")
        swap_btn.setFixedSize(32, 32)
        swap_btn.setCursor(Qt.PointingHandCursor)
        swap_btn.setStyleSheet("""
            QPushButton {
                background-color: #F3F4F6;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #E5E7EB;
            }
        """)
        swap_btn.clicked.connect(self.swap_languages)
        swap_col.addWidget(swap_btn)
        lang_row.addLayout(swap_col)

        # To
        to_col = QVBoxLayout()
        to_col.setSpacing(3)
        to_label = QLabel("To")
        to_label.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        self.to_combo = QComboBox()
        self.to_combo.addItems(["Khmer", "English"])
        to_col.addWidget(to_label)
        to_col.addWidget(self.to_combo)
        lang_row.addLayout(to_col, stretch=1)

        layout.addLayout(lang_row)

        # Voice Selector
        voice_col = QVBoxLayout()
        voice_col.setSpacing(3)
        voice_label = QLabel("Voice")
        voice_label.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        self.voice_combo = QComboBox()
        self.voice_combo.addItems([
            "Clone original speaker",
            "Preset: Male 1 (Natural)",
            "Preset: Female 1 (Clear)",
            "Preset: Male 2 (Deep)"
        ])
        voice_col.addWidget(voice_label)
        voice_col.addWidget(self.voice_combo)
        layout.addLayout(voice_col)

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

        # Original Audio Volume Slider
        self.vol_label = QLabel("Original audio volume: 15%")
        self.vol_label.setStyleSheet("color: #374151; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.vol_label)

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(15)
        self.vol_slider.valueChanged.connect(
            lambda v: self.vol_label.setText(f"Original audio volume: {v}%")
        )
        layout.addWidget(self.vol_slider)

        layout.addStretch()

        # Start Dubbing Button
        self.start_btn = QPushButton("Start dubbing")
        self.start_btn.setProperty("class", "PrimaryButton")
        self.start_btn.setFixedHeight(38)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.start_btn)

        return card

    def create_segments_card(self) -> QFrame:
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
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        # Header with actions
        header_row = QHBoxLayout()
        header_title = QLabel("Segments · 12 total, sample shown")
        header_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header_row.addWidget(header_title)
        header_row.addStretch()

        regen_btn = QPushButton("Regenerate selected")
        regen_btn.setProperty("class", "SecondaryButton")
        header_row.addWidget(regen_btn)

        export_srt_btn = QPushButton("Export subtitles (.srt)")
        export_srt_btn.setProperty("class", "SecondaryButton")
        header_row.addWidget(export_srt_btn)

        layout.addLayout(header_row)

        # Segments Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "#", "Time", "English (original)", "Khmer (editable)", "Status"
        ])

        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setMinimumHeight(190)

        # Column sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 36)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 115)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 125)

        # Sample rows
        sample_rows = [
            (
                "1",
                "00:00 to 00:04",
                "Hello and welcome to our product tour.",
                "សួស្តី សូមស្វាគមន៍មកកាន់ដំណើរទស្សនកិច្ចផលិតផលរបស់យើង។",
                ("Voice ready", "green")
            ),
            (
                "2",
                "00:04 to 00:09",
                "Today we will show you three simple steps.",
                "ថ្ងៃនេះ យើងនឹងបង្ហាញអ្នកអំពីជំហានសាមញ្ញចំនួនបី។",
                ("Voice ready", "green")
            ),
            (
                "3",
                "00:09 to 00:14",
                "First, open the app and sign in.",
                "ជាដំបូង សូមបើកកម្មវិធី ហើយចូលគណនីរបស់អ្នក។",
                ("Generating", "amber")
            ),
            (
                "4",
                "00:14 to 00:19",
                "Then choose the file you want to share.",
                "បន្ទាប់មក សូមជ្រើសរើសឯកសារដែលអ្នកចង់ចែករំលែក។",
                ("Waiting", "gray")
            )
        ]

        self.table.setRowCount(len(sample_rows))
        for row_idx, (num, time_str, en_text, km_text, (status_text, status_type)) in enumerate(sample_rows):
            item_num = QTableWidgetItem(num)
            item_num.setTextAlignment(Qt.AlignCenter)
            item_num.setFlags(item_num.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_idx, 0, item_num)

            item_time = QTableWidgetItem(time_str)
            item_time.setForeground(QColor("#6B7280"))
            item_time.setFlags(item_time.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_idx, 1, item_time)

            item_en = QTableWidgetItem(en_text)
            item_en.setFlags(item_en.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row_idx, 2, item_en)

            item_km = QTableWidgetItem(km_text)
            self.table.setItem(row_idx, 3, item_km)

            badge_container = QWidget()
            badge_layout = QHBoxLayout(badge_container)
            badge_layout.setContentsMargins(4, 2, 4, 2)
            badge = StatusBadge(status_text, status_type)
            badge_layout.addWidget(badge)
            self.table.setCellWidget(row_idx, 4, badge_container)

            self.table.setRowHeight(row_idx, 38)

        layout.addWidget(self.table)
        return card

    def create_bottom_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setContentsMargins(4, 2, 4, 0)

        self.resource_label = QLabel("Segment 3 of 12 · RAM 5.1 / 8 GB · VRAM 1.4 / 2 GB")
        self.resource_label.setStyleSheet("color: #6B7280; font-size: 12px; font-weight: 500;")
        bar.addWidget(self.resource_label)

        bar.addStretch()

        export_btn = QPushButton("Export dubbed video")
        export_btn.setProperty("class", "SecondaryButton")
        export_btn.setFixedHeight(32)
        export_btn.setStyleSheet("""
            QPushButton.SecondaryButton {
                padding: 6px 16px;
                font-weight: 600;
            }
        """)
        bar.addWidget(export_btn)

        return bar

    def swap_languages(self):
        from_idx = self.from_combo.currentIndex()
        to_idx = self.to_combo.currentIndex()
        self.from_combo.setCurrentIndex(to_idx)
        self.to_combo.setCurrentIndex(from_idx)
