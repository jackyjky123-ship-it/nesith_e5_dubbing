"""
Settings Tab for KhmerDub.
Implements the configuration interface for pipeline engines, hardware performance
(GTX 1050 vs CPU), low-memory management, and local storage/cache cleanup.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCheckBox, QLineEdit, QFrame, QFileDialog, QSizePolicy, QMessageBox,
    QProgressBar, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from ui.styles import (
    COLOR_PRIMARY, COLOR_PRIMARY_LIGHT, COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY, COLOR_BORDER, STATUS_WARNING_BANNER_BG,
    STATUS_WARNING_BANNER_BORDER, STATUS_WARNING_BANNER_TEXT
)
from ui.components import StatusBadge
from core.pronunciation_dict import load_user_dictionary, get_user_dictionary_path
from core.secure_storage import secure_storage, SecureStorageUnavailableError
from core.gemini_service import GEMINI_TTS_MODELS
from core.controller import TestGeminiKeyWorkerThread
from core.quota_tracker import gemini_quota_tracker
from core.config import load_config, save_config


class SettingsTab(QWidget):
    """Tab 3: Settings interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # Outer container layout holding the scroll area
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Scroll area for responsive scaling on small screens
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)

        # Main scrollable content widget
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")

        main_layout = QVBoxLayout(self.scroll_content)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Upper Two Columns: Engines & Gemini BYOK (Left) + Performance & Storage (Right)
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(16)

        # Left Column: Local Engines Card + Gemini AI Card
        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        engines_card = self.create_engines_card()
        left_col.addWidget(engines_card)

        gemini_card = self.create_gemini_settings_card()
        left_col.addWidget(gemini_card)

        columns_layout.addLayout(left_col, stretch=55)

        # Right Column: Performance & Storage
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        perf_card = self.create_performance_card()
        right_col.addWidget(perf_card)

        storage_card = self.create_storage_card()
        right_col.addWidget(storage_card)
        right_col.addStretch()

        columns_layout.addLayout(right_col, stretch=45)

        main_layout.addLayout(columns_layout)

        # Bottom Banner: License & Quality Advisory
        banner = self.create_license_banner()
        main_layout.addWidget(banner)

        self.scroll_area.setWidget(self.scroll_content)
        outer_layout.addWidget(self.scroll_area)

        # Load existing key if stored securely
        self.load_stored_gemini_key()

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

        layout.addWidget(self.create_divider())

        # Row 3: Custom Pronunciation Dictionary
        dict_row = QHBoxLayout()
        dict_row.setSpacing(12)
        d_label = QLabel("Pronunciation")
        d_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        d_label.setFixedWidth(130)
        dict_row.addWidget(d_label)

        d_info = QVBoxLayout()
        d_info.setSpacing(2)
        d_name = QLabel("Pronunciation Dictionary")
        d_name.setFont(QFont("Segoe UI", 11, QFont.Medium))
        rule_count = len(load_user_dictionary())
        d_desc = QLabel(f"pronunciation_dict.json ({rule_count} user rules active)")
        d_desc.setStyleSheet("color: #6B7280; font-size: 11px;")
        d_info.addWidget(d_name)
        d_info.addWidget(d_desc)
        dict_row.addLayout(d_info, stretch=1)

        d_badge = StatusBadge("Active", "green")
        dict_row.addWidget(d_badge)

        layout.addLayout(dict_row)

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

    # -------------------------------------------------------------------------
    # Card 4: Google Gemini AI Settings (BYOK)
    # -------------------------------------------------------------------------
    def create_gemini_settings_card(self) -> QFrame:
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
        layout.setSpacing(14)

        # Header: Title & Storage Security Badge
        header_row = QHBoxLayout()
        title = QLabel("Google Gemini AI Settings (BYOK)")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header_row.addWidget(title)
        header_row.addStretch()

        self.gemini_status_badge = StatusBadge("Not configured", "gray")
        header_row.addWidget(self.gemini_status_badge)
        layout.addLayout(header_row)

        desc = QLabel(
            "Bring Your Own Key (BYOK) for studio-grade natural speech synthesis with "
            "seamless Khmer and English code-switching. Keys are protected with OS-level encryption."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6B7280; font-size: 11px;")
        layout.addWidget(desc)

        # Row 1: API Key Input with Show/Hide toggle
        key_lbl = QLabel("Gemini API Key")
        key_lbl.setStyleSheet("color: #374151; font-size: 11px; font-weight: 600;")
        layout.addWidget(key_lbl)

        key_input_row = QHBoxLayout()
        key_input_row.setSpacing(8)

        self.gemini_key_input = QLineEdit()
        self.gemini_key_input.setEchoMode(QLineEdit.Password)
        self.gemini_key_input.setPlaceholderText("Enter your Google Gemini API key (AIza...)")
        self.gemini_key_input.setMinimumHeight(36)
        self.gemini_key_input.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1.5px solid #0F6B58;
            }
        """)
        key_input_row.addWidget(self.gemini_key_input, stretch=1)

        self.btn_toggle_key_visibility = QPushButton("Show")
        self.btn_toggle_key_visibility.setFixedWidth(60)
        self.btn_toggle_key_visibility.setMinimumHeight(36)
        self.btn_toggle_key_visibility.setProperty("class", "SecondaryButton")
        self.btn_toggle_key_visibility.clicked.connect(self.toggle_key_visibility)
        key_input_row.addWidget(self.btn_toggle_key_visibility)

        layout.addLayout(key_input_row)

        # Row 2: Model Selection
        model_row = QHBoxLayout()
        model_row.setSpacing(12)

        m_label_col = QVBoxLayout()
        m_label_col.setSpacing(2)
        m_title = QLabel("Model")
        m_title.setStyleSheet("color: #374151; font-size: 11px; font-weight: 600;")
        m_sub = QLabel("Select speech synthesis model")
        m_sub.setStyleSheet("color: #6B7280; font-size: 10px;")
        m_label_col.addWidget(m_title)
        m_label_col.addWidget(m_sub)
        model_row.addLayout(m_label_col, stretch=1)

        self.gemini_model_combo = QComboBox()
        self.gemini_model_combo.setMinimumWidth(260)
        self.gemini_model_combo.setMinimumHeight(36)
        for model_id, model_name in GEMINI_TTS_MODELS.items():
            self.gemini_model_combo.addItem(model_name, model_id)

        # Load saved model preference
        cfg = load_config()
        saved_model = cfg.get("gemini_model", "gemini-3.8-flash-tts")
        idx = self.gemini_model_combo.findData(saved_model)
        if idx >= 0:
            self.gemini_model_combo.setCurrentIndex(idx)
        self.gemini_model_combo.currentIndexChanged.connect(self.on_gemini_model_changed)
        model_row.addWidget(self.gemini_model_combo)

        layout.addLayout(model_row)

        # Row 3: Action Buttons (Test, Save, Remove)
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.btn_test_gemini_key = QPushButton("Test connection")
        self.btn_test_gemini_key.setProperty("class", "SecondaryButton")
        self.btn_test_gemini_key.setMinimumHeight(32)
        self.btn_test_gemini_key.clicked.connect(self.test_gemini_key)
        actions_row.addWidget(self.btn_test_gemini_key)

        self.btn_save_gemini_key = QPushButton("Save key")
        self.btn_save_gemini_key.setProperty("class", "PrimaryButton")
        self.btn_save_gemini_key.setMinimumHeight(32)
        self.btn_save_gemini_key.clicked.connect(self.save_gemini_key)
        actions_row.addWidget(self.btn_save_gemini_key)

        self.btn_remove_gemini_key = QPushButton("Remove key")
        self.btn_remove_gemini_key.setProperty("class", "SecondaryButton")
        self.btn_remove_gemini_key.setMinimumHeight(32)
        self.btn_remove_gemini_key.setStyleSheet("""
            QPushButton {
                background-color: #FEF2F2;
                color: #B91C1C;
                border: 1px solid #FECACA;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #FEE2E2;
            }
        """)
        self.btn_remove_gemini_key.clicked.connect(self.remove_gemini_key)
        actions_row.addWidget(self.btn_remove_gemini_key)

        actions_row.addStretch()
        layout.addLayout(actions_row)

        # Row 4: Free Tier Rate Limit & Live Refresh Monitor
        layout.addWidget(self.create_divider())
        quota_widget = self.create_quota_monitor_widget()
        layout.addWidget(quota_widget)

        # 1-second refresh timer for live rate-limit ticking
        self.quota_refresh_timer = QTimer(self)
        self.quota_refresh_timer.timeout.connect(self.update_quota_display)
        self.quota_refresh_timer.start(1000)
        self.update_quota_display()

        # Cost & Usage Notice Box
        cost_notice = QLabel(
            "⚠️ Cost Advisory: Gemini API calls use your own API key and may incur charges on your "
            "Google AI Studio / Cloud account according to Google's pricing. Nesith TTS never charges you."
        )
        cost_notice.setWordWrap(True)
        cost_notice.setStyleSheet("""
            QLabel {
                background-color: #FFFBEB;
                color: #92400E;
                border: 1px solid #FDE68A;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 10px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(cost_notice)

        return card

    def create_quota_monitor_widget(self) -> QWidget:
        """Builds the Free Tier token and rate limit dashboard."""
        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header Row
        header = QHBoxLayout()
        title = QLabel("Free Tier Rate Limits & Live Refresh")
        title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title.setStyleSheet("color: #111827; border: none; background: transparent;")
        header.addWidget(title)
        header.addStretch()

        self.quota_health_badge = StatusBadge("Within limits", "green")
        header.addWidget(self.quota_health_badge)
        layout.addLayout(header)

        pbar_style = """
            QProgressBar {
                border: 1px solid #E5E7EB;
                border-radius: 4px;
                text-align: right;
                background-color: #E5E7EB;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #0F6B58;
                border-radius: 3px;
            }
        """

        # 1. RPM Row
        rpm_header = QHBoxLayout()
        rpm_title = QLabel("Requests / Minute (RPM)")
        rpm_title.setStyleSheet("color: #4B5563; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        self.rpm_usage_label = QLabel("0 / 15 req/min")
        self.rpm_usage_label.setStyleSheet("color: #111827; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        rpm_header.addWidget(rpm_title)
        rpm_header.addStretch()
        rpm_header.addWidget(self.rpm_usage_label)
        layout.addLayout(rpm_header)

        self.rpm_progress_bar = QProgressBar()
        self.rpm_progress_bar.setRange(0, 15)
        self.rpm_progress_bar.setValue(0)
        self.rpm_progress_bar.setTextVisible(False)
        self.rpm_progress_bar.setFixedHeight(8)
        self.rpm_progress_bar.setStyleSheet(pbar_style)
        layout.addWidget(self.rpm_progress_bar)

        self.rpm_refresh_badge = QLabel("⏱️ 60s window: Ready (Full 15 available)")
        self.rpm_refresh_badge.setStyleSheet("color: #059669; font-size: 10px; font-weight: 500; border: none; background: transparent;")
        layout.addWidget(self.rpm_refresh_badge)

        # 2. TPM Row
        tpm_header = QHBoxLayout()
        tpm_title = QLabel("Tokens / Minute (TPM)")
        tpm_title.setStyleSheet("color: #4B5563; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        self.tpm_usage_label = QLabel("0 / 1,000,000 tokens")
        self.tpm_usage_label.setStyleSheet("color: #111827; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        tpm_header.addWidget(tpm_title)
        tpm_header.addStretch()
        tpm_header.addWidget(self.tpm_usage_label)
        layout.addLayout(tpm_header)

        self.tpm_progress_bar = QProgressBar()
        self.tpm_progress_bar.setRange(0, 1_000_000)
        self.tpm_progress_bar.setValue(0)
        self.tpm_progress_bar.setTextVisible(False)
        self.tpm_progress_bar.setFixedHeight(8)
        self.tpm_progress_bar.setStyleSheet(pbar_style)
        layout.addWidget(self.tpm_progress_bar)

        # 3. RPD Row
        rpd_header = QHBoxLayout()
        rpd_title = QLabel("Daily Requests (RPD)")
        rpd_title.setStyleSheet("color: #4B5563; font-size: 11px; font-weight: 500; border: none; background: transparent;")
        self.rpd_usage_label = QLabel("0 / 1,500 daily req")
        self.rpd_usage_label.setStyleSheet("color: #111827; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        rpd_header.addWidget(rpd_title)
        rpd_header.addStretch()
        rpd_header.addWidget(self.rpd_usage_label)
        layout.addLayout(rpd_header)

        self.rpd_progress_bar = QProgressBar()
        self.rpd_progress_bar.setRange(0, 1500)
        self.rpd_progress_bar.setValue(0)
        self.rpd_progress_bar.setTextVisible(False)
        self.rpd_progress_bar.setFixedHeight(8)
        self.rpd_progress_bar.setStyleSheet(pbar_style)
        layout.addWidget(self.rpd_progress_bar)

        self.daily_reset_label = QLabel("📅 Daily quota resets at: 00:00 UTC")
        self.daily_reset_label.setStyleSheet("color: #6B7280; font-size: 10px; border: none; background: transparent;")
        layout.addWidget(self.daily_reset_label)

        return box

    def update_quota_display(self):
        """Updates the real-time rate limit progress bars and countdown timers."""
        snap = gemini_quota_tracker.get_snapshot()

        # Update RPM
        self.rpm_progress_bar.setValue(min(snap.rpm_limit, snap.rpm_used))
        self.rpm_usage_label.setText(f"{snap.rpm_used} / {snap.rpm_limit} req/min")
        if snap.seconds_to_minute_refresh > 0:
            self.rpm_refresh_badge.setText(f"⏱️ 60s window refreshes in: {snap.seconds_to_minute_refresh}s")
            self.rpm_refresh_badge.setStyleSheet("color: #1D4ED8; font-size: 10px; font-weight: 500; border: none; background: transparent;")
        else:
            self.rpm_refresh_badge.setText("⏱️ 60s window: Ready (Full 15 RPM available)")
            self.rpm_refresh_badge.setStyleSheet("color: #059669; font-size: 10px; font-weight: 500; border: none; background: transparent;")

        # Update TPM
        self.tpm_progress_bar.setValue(min(snap.tpm_limit, snap.tpm_used))
        self.tpm_usage_label.setText(f"{snap.tpm_used:,} / {snap.tpm_limit:,} tokens")

        # Update RPD
        self.rpd_progress_bar.setValue(min(snap.rpd_limit, snap.rpd_used))
        self.rpd_usage_label.setText(f"{snap.rpd_used:,} / {snap.rpd_limit:,} daily requests")
        self.daily_reset_label.setText(f"📅 Daily quota resets at: {snap.time_to_daily_reset_str}")

        # Update health status badge
        if snap.status == "throttled":
            self.quota_health_badge.set_status(f"Throttled ({snap.throttle_remaining_seconds}s)", "amber")
        elif snap.status == "warning":
            self.quota_health_badge.set_status("Approaching limit", "amber")
        else:
            self.quota_health_badge.set_status("Within limits", "green")

    def load_stored_gemini_key(self):
        """Loads securely stored API key into the UI if present."""
        try:
            if secure_storage.has_api_key():
                key = secure_storage.get_api_key()
                if key:
                    self.gemini_key_input.setText(key)
                    self.gemini_status_badge.set_status("Configured", "green")
            else:
                self.gemini_status_badge.set_status("Not configured", "gray")
        except Exception:
            self.gemini_status_badge.set_status("Storage error", "amber")

    def toggle_key_visibility(self):
        """Toggles masking between password dots and plain characters."""
        if self.gemini_key_input.echoMode() == QLineEdit.Password:
            self.gemini_key_input.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_key_visibility.setText("Hide")
        else:
            self.gemini_key_input.setEchoMode(QLineEdit.Password)
            self.btn_toggle_key_visibility.setText("Show")

    def on_gemini_model_changed(self, index: int):
        """Persists model selection to application configuration."""
        model_id = self.gemini_model_combo.itemData(index)
        if model_id:
            cfg = load_config()
            cfg["gemini_model"] = model_id
            save_config(cfg)

    def test_gemini_key(self):
        """Initiates a lightweight non-blocking API connectivity check."""
        key = self.gemini_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Missing Key", "Please enter a Gemini API key to test.")
            return

        self.btn_test_gemini_key.setEnabled(False)
        self.btn_test_gemini_key.setText("Testing...")
        self.gemini_status_badge.set_status("Testing...", "amber")

        self.key_test_worker = TestGeminiKeyWorkerThread(api_key=key, parent=self)
        self.key_test_worker.test_finished.connect(self.on_key_test_finished)
        self.key_test_worker.start()

    def on_key_test_finished(self, ok: bool, msg: str):
        """Handles key test result on main UI thread."""
        self.btn_test_gemini_key.setEnabled(True)
        self.btn_test_gemini_key.setText("Test connection")

        if ok:
            self.gemini_status_badge.set_status("Connected", "green")
            QMessageBox.information(self, "Gemini Connection Test", msg)
        else:
            self.gemini_status_badge.set_status("Error", "amber")
            QMessageBox.critical(self, "Gemini Connection Failed", msg)

    def save_gemini_key(self):
        """Validates and stores the key in OS secure storage."""
        key = self.gemini_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Empty Key", "API key cannot be empty.")
            return

        try:
            secure_storage.save_api_key(key)
            self.gemini_status_badge.set_status("Configured", "green")
            QMessageBox.information(
                self,
                "API Key Saved",
                f"Your Gemini API key has been securely saved using {secure_storage.get_storage_backend_name()}."
            )
        except SecureStorageUnavailableError as e:
            QMessageBox.critical(
                self,
                "Secure Storage Error",
                f"Cannot save API key: {str(e)}\n\nPlaintext fallback is prohibited."
            )
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save key: {str(e)}")

    def remove_gemini_key(self):
        """Removes the stored key after confirmation."""
        try:
            secure_storage.delete_api_key()
            self.gemini_key_input.clear()
            self.gemini_status_badge.set_status("Not configured", "gray")
            QMessageBox.information(self, "Key Removed", "Your Gemini API key has been securely removed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to remove key: {str(e)}")

