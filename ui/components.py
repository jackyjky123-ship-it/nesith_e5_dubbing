"""
Reusable UI components matching the KhmerDub design mockup.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QUrl
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QFontMetrics
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
import os

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


class WaveformWidget(QWidget):
    """
    Visual audio waveform display matching the TTS result card mockup.
    Includes circular play button, vertical amplitude bars, audio player, and playback timer.
    """
    playToggled = Signal(bool)
    playbackProgressChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self.is_playing = False
        self.playback_progress = 0.0
        self.duration_ms = 0
        self.position_ms = 0
        self.audio_path = None
        self.time_label_text = "0:00 / 0:00"

        self.bars = [
            0.15, 0.35, 0.7, 0.4, 0.6, 0.75, 0.9, 0.6, 0.8, 0.4,
            0.65, 0.85, 0.95, 0.5, 0.3, 0.6, 0.75, 0.85, 0.75, 0.6,
            0.4, 0.7, 0.85, 0.5, 0.3, 0.6, 0.8, 0.85, 0.7, 0.5,
            0.4, 0.7, 0.85, 0.8, 0.6, 0.4, 0.3, 0.15
        ]

        self._player = None
        self._audio_output = None
        self._init_player()

    def _init_player(self):
        try:
            self._player = QMediaPlayer(self)
            self._audio_output = QAudioOutput(self)
            self._player.setAudioOutput(self._audio_output)
            self._player.positionChanged.connect(self._on_position_changed)
            self._player.durationChanged.connect(self._on_duration_changed)
            self._player.playbackStateChanged.connect(self._on_state_changed)
        except Exception as e:
            self._player = None

    def set_audio(self, audio_path: str, bars: list = None, duration_seconds: float = 0.0):
        """Sets the audio file, updates bars and duration."""
        self.audio_path = audio_path
        if bars:
            self.bars = bars
        if duration_seconds > 0:
            self.duration_ms = int(duration_seconds * 1000)
        else:
            self.duration_ms = 0

        self.position_ms = 0
        self.playback_progress = 0.0
        self.is_playing = False
        self._update_time_label()

        if self._player and audio_path and os.path.exists(audio_path):
            try:
                self._player.setSource(QUrl.fromLocalFile(audio_path))
            except Exception as e:
                pass

        self.update()

    def _on_duration_changed(self, dur_ms: int):
        if dur_ms > 0:
            self.duration_ms = dur_ms
            self._update_time_label()
            self.update()

    def _on_position_changed(self, pos_ms: int):
        self.position_ms = pos_ms
        if self.duration_ms > 0:
            self.playback_progress = min(1.0, max(0.0, pos_ms / float(self.duration_ms)))
            self.playbackProgressChanged.emit(self.playback_progress)
        self._update_time_label()
        self.update()

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.is_playing = True
        else:
            self.is_playing = False
        self.update()

    def _update_time_label(self):
        cur_s = int(self.position_ms / 1000)
        dur_s = int(self.duration_ms / 1000)
        cur_str = f"{cur_s // 60}:{cur_s % 60:02d}"
        dur_str = f"{dur_s // 60}:{dur_s % 60:02d}"
        self.time_label_text = f"{cur_str} / {dur_str}"

    def toggle_play(self):
        if not self._player:
            self.is_playing = not self.is_playing
            self.playToggled.emit(self.is_playing)
            self.update()
            return

        if self.is_playing:
            self._player.pause()
            self.is_playing = False
        else:
            if self.duration_ms > 0 and self.position_ms >= self.duration_ms - 200:
                self._player.setPosition(0)
            self._player.play()
            self.is_playing = True
        self.playToggled.emit(self.is_playing)
        self.update()

    def seek_to_ratio(self, ratio: float):
        self.playback_progress = max(0.0, min(1.0, ratio))
        if self.duration_ms > 0:
            target_ms = int(self.playback_progress * self.duration_ms)
            if self._player:
                self._player.setPosition(target_ms)
            self.position_ms = target_ms
            self._update_time_label()
        self.update()

    def set_playing(self, playing: bool):
        if playing != self.is_playing:
            self.toggle_play()

    def set_progress(self, progress: float):
        self.seek_to_ratio(progress)

    def mousePressEvent(self, event):
        if event.position().x() < 44:
            self.toggle_play()
        else:
            wave_x = event.position().x() - 54
            wave_w = self.width() - 140
            if wave_w > 0:
                self.seek_to_ratio(max(0.0, min(1.0, wave_x / wave_w)))

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
        time_width = 86.0
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
        painter.drawText(time_rect, Qt.AlignRight | Qt.AlignVCenter, self.time_label_text)


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
