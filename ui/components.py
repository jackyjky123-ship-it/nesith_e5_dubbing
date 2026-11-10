"""
Reusable UI components matching the KhmerDub design mockup.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QFontMetrics

from ui.styles import (
    COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_PRIMARY_HOVER,
    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY, COLOR_TEXT_MUTED,
    STATUS_GREEN_BG, STATUS_GREEN_TEXT, STATUS_AMBER_BG, STATUS_AMBER_TEXT,
    STATUS_GRAY_BG, STATUS_GRAY_TEXT
)


class StatusBadge(QLabel):
    """Rounded status pill badge (e.g. 'Voice ready', 'Generating', 'Connected')."""
    def __init__(self, text: str, status_type: str = "green", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(24)
        self.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        self.set_status(text, status_type)

    def set_status(self, text: str, status_type: str):
        self.setText(text)
        if status_type in ("green", "ready", "connected", "loaded"):
            bg = STATUS_GREEN_BG
            fg = STATUS_GREEN_TEXT
        elif status_type in ("amber", "generating", "warning", "processing"):
            bg = STATUS_AMBER_BG
            fg = STATUS_AMBER_TEXT
        else: # gray, waiting, disconnected
            bg = STATUS_GRAY_BG
            fg = STATUS_GRAY_TEXT
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border-radius: 12px;
                padding: 2px 12px;
                font-weight: 600;
                font-size: 11px;
            }}
        """)


class PipelineStepper(QWidget):
    """
    Horizontal 5-step progress indicator for the dubbing pipeline:
    [ (✓) Extract audio ] ─────── [ (✓) Transcribe ] ─────── [ (3) Translate ] ─────── [ (4) Generate voice ] ─────── [ (5) Mix and export ]
    Lines connect strictly between steps without passing through text.
    """
    stepClicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.steps = [
            "Extract audio",
            "Transcribe",
            "Translate",
            "Generate voice",
            "Mix and export"
        ]
        self.current_step = 3 # Step 3 active in mockup
        self.setMouseTracking(True)

    def set_current_step(self, step: int):
        self.current_step = max(1, min(len(self.steps), step))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        n = len(self.steps)
        circle_radius = 11.0
        y_center = self.height() / 2.0

        font_active = QFont("Segoe UI", 10, QFont.Bold)
        font_inactive = QFont("Segoe UI", 10, QFont.Normal)
        fm = QFontMetrics(font_active)

        # Calculate layout and item widths
        item_widths = []
        for title in self.steps:
            text_w = fm.horizontalAdvance(title)
            # circle + gap + text
            total_w = (circle_radius * 2) + 8 + text_w
            item_widths.append((total_w, text_w))

        total_items_w = sum(w for w, _ in item_widths)
        margin_x = 20.0
        available_line_w = max(0.0, width - (margin_x * 2) - total_items_w)
        line_spacing = available_line_w / max(1, n - 1)

        # Calculate exact positions
        step_coords = []
        curr_x = margin_x
        for i in range(n):
            tot_w, txt_w = item_widths[i]
            step_coords.append({
                "x_circle": curr_x + circle_radius,
                "x_text": curr_x + (circle_radius * 2) + 8,
                "text_w": txt_w,
                "tot_w": tot_w,
                "x_start": curr_x,
                "x_end": curr_x + tot_w
            })
            curr_x += tot_w + line_spacing

        # 1. Draw connecting lines between steps
        for i in range(n - 1):
            x1 = step_coords[i]["x_end"] + 10
            x2 = step_coords[i + 1]["x_start"] - 10
            if x2 > x1:
                line_pen = QPen()
                line_pen.setWidth(2)
                if i + 1 < self.current_step:
                    line_pen.setColor(QColor(COLOR_PRIMARY))
                else:
                    line_pen.setColor(QColor("#D1D5DB"))
                painter.setPen(line_pen)
                painter.drawLine(QPointF(x1, y_center), QPointF(x2, y_center))

        # 2. Draw each step circle and label
        for i, title in enumerate(self.steps):
            step_num = i + 1
            info = step_coords[i]
            cx = info["x_circle"]
            cy = y_center

            # Circle
            if step_num < self.current_step:
                # Completed: filled primary with white checkmark
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(COLOR_PRIMARY))
                painter.drawEllipse(QRectF(cx - circle_radius, cy - circle_radius, circle_radius * 2, circle_radius * 2))

                pen = QPen(QColor("#FFFFFF"))
                pen.setWidth(2)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.drawLine(QPointF(cx - 5, cy), QPointF(cx - 1, cy + 4))
                painter.drawLine(QPointF(cx - 1, cy + 4), QPointF(cx + 5, cy - 3))

            elif step_num == self.current_step:
                # Current active: white background, thick primary border, primary number
                pen = QPen(QColor(COLOR_PRIMARY))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(QColor("#FFFFFF"))
                painter.drawEllipse(QRectF(cx - circle_radius, cy - circle_radius, circle_radius * 2, circle_radius * 2))

                painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
                painter.setPen(QColor(COLOR_PRIMARY))
                painter.drawText(QRectF(cx - circle_radius, cy - circle_radius, circle_radius * 2, circle_radius * 2),
                                 Qt.AlignCenter, str(step_num))
            else:
                # Pending: light gray outline, gray text
                pen = QPen(QColor("#D1D5DB"))
                pen.setWidth(1.5)
                painter.setPen(pen)
                painter.setBrush(QColor("#FFFFFF"))
                painter.drawEllipse(QRectF(cx - circle_radius, cy - circle_radius, circle_radius * 2, circle_radius * 2))

                painter.setFont(QFont("Segoe UI", 9, QFont.Medium))
                painter.setPen(QColor(COLOR_TEXT_MUTED))
                painter.drawText(QRectF(cx - circle_radius, cy - circle_radius, circle_radius * 2, circle_radius * 2),
                                 Qt.AlignCenter, str(step_num))

            # Step title text
            if step_num <= self.current_step:
                painter.setFont(font_active)
                painter.setPen(QColor(COLOR_TEXT_PRIMARY))
            else:
                painter.setFont(font_inactive)
                painter.setPen(QColor(COLOR_TEXT_SECONDARY))

            text_rect = QRectF(info["x_text"], cy - 12, info["text_w"] + 8, 24)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, title)


class WaveformWidget(QWidget):
    """
    Visual audio waveform display matching the TTS result card mockup.
    Includes circular play button, vertical amplitude bars, and playback timer.
    """
    playToggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self.is_playing = False
        self.playback_progress = 0.35

        self.bars = [
            0.25, 0.45, 0.9, 0.4, 0.7, 0.8, 0.95, 0.6, 0.8, 0.4,
            0.7, 0.9, 1.0, 0.5, 0.3, 0.6, 0.75, 0.9, 0.8, 0.6,
            0.4, 0.7, 0.85, 0.5, 0.3, 0.6, 0.8, 0.9, 0.7, 0.5,
            0.4, 0.75, 0.9, 0.85, 0.6, 0.4, 0.3, 0.2
        ]

    def set_playing(self, playing: bool):
        self.is_playing = playing
        self.update()

    def set_progress(self, progress: float):
        self.playback_progress = max(0.0, min(1.0, progress))
        self.update()

    def mousePressEvent(self, event):
        if event.position().x() < 44:
            self.is_playing = not self.is_playing
            self.playToggled.emit(self.is_playing)
            self.update()
        else:
            wave_x = event.position().x() - 54
            wave_w = self.width() - 140
            if wave_w > 0:
                self.set_progress(max(0.0, min(1.0, wave_x / wave_w)))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Circular play button
        play_btn_rect = QRectF(2, (self.height() - 36) / 2, 36, 36)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(COLOR_PRIMARY))
        painter.drawEllipse(play_btn_rect)

        # Play / Pause symbol
        painter.setBrush(QColor("#FFFFFF"))
        cx = play_btn_rect.center().x()
        cy = play_btn_rect.center().y()
        if not self.is_playing:
            path = QPainterPath()
            path.moveTo(cx - 3, cy - 6)
            path.lineTo(cx + 6, cy)
            path.lineTo(cx - 3, cy + 6)
            path.closeSubpath()
            painter.drawPath(path)
        else:
            painter.drawRect(QRectF(cx - 5, cy - 6, 3, 12))
            painter.drawRect(QRectF(cx + 2, cy - 6, 3, 12))

        # Waveform bars
        start_x = 52.0
        time_width = 80.0
        wave_width = self.width() - start_x - time_width
        num_bars = len(self.bars)

        if num_bars > 0 and wave_width > 0:
            bar_w = 4.0
            gap = max(2.0, (wave_width - (num_bars * bar_w)) / max(1, num_bars - 1))
            mid_y = self.height() / 2.0
            max_h = self.height() * 0.68

            for i, amp in enumerate(self.bars):
                bx = start_x + i * (bar_w + gap)
                bh = max(6.0, amp * max_h)
                by = mid_y - (bh / 2.0)
                bar_rect = QRectF(bx, by, bar_w, bh)

                bar_ratio = i / float(num_bars)
                if bar_ratio <= self.playback_progress:
                    painter.setBrush(QColor(COLOR_PRIMARY))
                else:
                    painter.setBrush(QColor("#A3D9C9"))

                painter.drawRoundedRect(bar_rect, 2.0, 2.0)

        # Timestamp on right
        painter.setFont(QFont("Segoe UI", 10, QFont.Medium))
        painter.setPen(QColor(COLOR_TEXT_SECONDARY))
        time_rect = QRectF(self.width() - time_width, 0, time_width - 8, self.height())
        painter.drawText(time_rect, Qt.AlignRight | Qt.AlignVCenter, "0:02 / 0:06")


class SegmentedTab(QWidget):
    """Horizontal segmented toggle buttons with a pill background for active state."""
    tabChanged = Signal(int)

    def __init__(self, options: list[str], initial_index: int = 0, parent=None):
        super().__init__(parent)
        self.options = options
        self.active_index = initial_index
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        self.buttons = []
        for i, opt in enumerate(options):
            btn = QPushButton(opt)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, idx=i: self.set_active_index(idx))
            self.buttons.append(btn)
            layout.addWidget(btn)

        self.update_styles()

    def set_active_index(self, index: int):
        if 0 <= index < len(self.options) and index != self.active_index:
            self.active_index = index
            self.update_styles()
            self.tabChanged.emit(self.active_index)

    def update_styles(self):
        for i, btn in enumerate(self.buttons):
            if i == self.active_index:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLOR_PRIMARY_LIGHT};
                        color: {COLOR_PRIMARY};
                        font-weight: 600;
                        font-size: 13px;
                        border: none;
                        border-radius: 6px;
                        padding: 4px 14px;
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
                        border-radius: 6px;
                        padding: 4px 14px;
                    }}
                    QPushButton:hover {{
                        background-color: #F3F4F6;
                        color: {COLOR_TEXT_PRIMARY};
                    }}
                """)
