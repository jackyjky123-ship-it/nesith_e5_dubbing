"""
Main Application Window for KhmerDub.
Hosts the top navigation header bar, segmented tab switcher,
backend status indicator, and stacked view pages.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QBrush, QPen

from ui.styles import (
    GLOBAL_STYLESHEET, COLOR_PRIMARY, COLOR_PRIMARY_LIGHT,
    COLOR_BG_CARD, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY
)
from ui.tts_tab import TextToSpeechTab
from ui.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    """Main desktop application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("KhmerTTS - English and Khmer Speech Studio")
        self.resize(1180, 800)
        self.setMinimumSize(980, 660)

        # Apply global stylesheet
        self.setStyleSheet(GLOBAL_STYLESHEET)

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Navigation Header Bar
        header = self.create_header_bar()
        root_layout.addWidget(header)

        # 2. Main Stacked Content Pages
        self.stack = QStackedWidget()
        self.tts_tab = TextToSpeechTab()
        self.settings_tab = SettingsTab()

        self.stack.addWidget(self.tts_tab)
        self.stack.addWidget(self.settings_tab)

        root_layout.addWidget(self.stack)

        # Default to Text to Speech tab
        self.switch_tab(0)

    def create_header_bar(self) -> QFrame:
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_CARD};
                border-bottom: 1px solid {COLOR_BORDER};
            }}
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)

        # --- Left: Logo & Title ---
        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(12)

        # Logo Icon Box
        logo_label = QLabel()
        logo_label.setFixedSize(36, 36)
        logo_pixmap = self.create_logo_pixmap(36)
        logo_label.setPixmap(logo_pixmap)
        brand_layout.addWidget(logo_label)

        # Title & Subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_box.setAlignment(Qt.AlignVCenter)
        
        lbl_title = QLabel("KhmerTTS")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        lbl_title.setStyleSheet("color: #111827;")
        
        lbl_sub = QLabel("English and Khmer speech synthesis studio")
        lbl_sub.setFont(QFont("Segoe UI", 10))
        lbl_sub.setStyleSheet("color: #6B7280;")
        
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        brand_layout.addLayout(title_box)

        layout.addLayout(brand_layout)
        layout.addStretch()

        # --- Center: Segmented Navigation Pills ---
        nav_container = QWidget()
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)

        self.nav_buttons = []
        tabs = [
            ("Text to speech", 0),
            ("Settings", 1)
        ]

        for title, idx in tabs:
            btn = QPushButton(title)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=idx: self.switch_tab(i))
            self.nav_buttons.append(btn)
            nav_layout.addWidget(btn)

        layout.addWidget(nav_container)
        layout.addStretch()

        # --- Right: Backend Engine Status Indicator ---
        status_box = QHBoxLayout()
        status_box.setSpacing(8)
        
        # Green Dot Indicator
        dot = QLabel("●")
        dot.setStyleSheet("color: #10B981; font-size: 14px;")
        status_box.addWidget(dot)

        from core.config import get_active_device
        device_str = get_active_device().upper()
        status_text = QLabel(f"Meta MMS-TTS ({device_str})")
        status_text.setStyleSheet("color: #374151; font-size: 12px; font-weight: 500;")
        status_box.addWidget(status_text)

        layout.addLayout(status_box)

        self.update_nav_styles(0)

        return header

    def switch_tab(self, index: int):
        prev_index = self.stack.currentIndex()
        if prev_index == 0 and index != 0:
            # Free TTS model RAM when leaving the TTS Studio (AGENT.md Rule 3)
            try:
                from core.tts_engine import tts_manager
                tts_manager.unload_model()
            except Exception:
                pass
        self.stack.setCurrentIndex(index)
        self.update_nav_styles(index)

    def update_nav_styles(self, active_index: int):
        for i, btn in enumerate(self.nav_buttons):
            if i == active_index:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLOR_PRIMARY_LIGHT};
                        color: {COLOR_PRIMARY};
                        font-weight: 600;
                        font-size: 13px;
                        border: none;
                        border-radius: 8px;
                        padding: 6px 16px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {COLOR_TEXT_SECONDARY};
                        font-weight: 500;
                        font-size: 13px;
                        border: none;
                        border-radius: 8px;
                        padding: 6px 16px;
                    }}
                    QPushButton:hover {{
                        background-color: #F3F4F6;
                        color: {COLOR_TEXT_PRIMARY};
                    }}
                """)

    def create_logo_pixmap(self, size: int) -> QPixmap:
        """Draws the emerald soundwave logo icon matching the design mockup."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Rounded rectangle background
        painter.setBrush(QColor(COLOR_PRIMARY))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, size, size, 8, 8)

        # 4 soundwave bars in white
        painter.setBrush(QColor("#FFFFFF"))
        bars = [0.4, 0.8, 1.0, 0.55]
        bar_w = 2.5
        gap = 3.0
        total_w = len(bars) * bar_w + (len(bars) - 1) * gap
        start_x = (size - total_w) / 2.0
        mid_y = size / 2.0
        max_h = size * 0.5

        for i, h_ratio in enumerate(bars):
            bh = max_h * h_ratio
            bx = start_x + i * (bar_w + gap)
            by = mid_y - (bh / 2.0)
            painter.drawRoundedRect(bx, by, bar_w, bh, 1.2, 1.2)

        painter.end()
        return pixmap

