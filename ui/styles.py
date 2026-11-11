"""
UI styling and theme constants for KhmerDub.
Matches the clean emerald/teal design from Khmer-English Dubbing App UI mockup.
"""

import os

# Base paths for assets
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
ARROW_SVG = os.path.join(ASSETS_DIR, "down_arrow.svg").replace("\\", "/")
CHECKED_SVG = os.path.join(ASSETS_DIR, "checkbox_checked.svg").replace("\\", "/")

# Color Palette
COLOR_PRIMARY = "#0F6B58"         # Deep Emerald / Teal
COLOR_PRIMARY_HOVER = "#0c5646"   # Slightly darker emerald
COLOR_PRIMARY_PRESSED = "#094135" # Dark pressed emerald
COLOR_PRIMARY_LIGHT = "#E0F2EE"   # Soft mint background for active pills/tags
COLOR_PRIMARY_LIGHT_HOVER = "#CCEBE4"

COLOR_BG_WINDOW = "#F5F6F8"       # Subtle cool gray window background
COLOR_BG_CARD = "#FFFFFF"         # Pure white cards
COLOR_BORDER = "#E5E7EB"          # Card and divider border
COLOR_BORDER_FOCUS = "#0F6B58"    # Focus border

COLOR_TEXT_PRIMARY = "#111827"    # Dark gray / black for titles and strong text
COLOR_TEXT_SECONDARY = "#6B7280"  # Medium gray for secondary labels and metadata
COLOR_TEXT_MUTED = "#9CA3AF"      # Light gray for disabled or tertiary info

# Status pill colors
STATUS_GREEN_BG = "#E0F2EE"
STATUS_GREEN_TEXT = "#0F6B58"

STATUS_AMBER_BG = "#FEF3C7"
STATUS_AMBER_TEXT = "#D97706"

STATUS_GRAY_BG = "#F3F4F6"
STATUS_GRAY_TEXT = "#6B7280"

STATUS_WARNING_BANNER_BG = "#FEF3C7"
STATUS_WARNING_BANNER_BORDER = "#FDE68A"
STATUS_WARNING_BANNER_TEXT = "#92400E"

# Main QSS Stylesheet
GLOBAL_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLOR_BG_WINDOW};
}}

QWidget {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans Khmer", "Hanuman", "Kantumruy Pro", Roboto, Helvetica, Arial, sans-serif;
    color: {COLOR_TEXT_PRIMARY};
}}

/* Card containers */
QFrame.CardFrame {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
}}

QLabel.CardTitle {{
    font-size: 15px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.CardSubtitle {{
    font-size: 12px;
    color: {COLOR_TEXT_SECONDARY};
}}

/* Primary Buttons */
QPushButton.PrimaryButton {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    min-height: 22px;
}}
QPushButton.PrimaryButton:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}
QPushButton.PrimaryButton:pressed {{
    background-color: {COLOR_PRIMARY_PRESSED};
}}
QPushButton.PrimaryButton:disabled {{
    background-color: #D1D5DB;
    color: #9CA3AF;
}}

/* Secondary / Outline Buttons */
QPushButton.SecondaryButton {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 500;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    padding: 6px 12px;
    min-height: 20px;
}}
QPushButton.SecondaryButton:hover {{
    background-color: #F9FAFB;
    border-color: #9CA3AF;
}}
QPushButton.SecondaryButton:pressed {{
    background-color: #F3F4F6;
}}

/* Inputs & Comboboxes */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    padding: 8px;
    font-size: 13px;
    color: {COLOR_TEXT_PRIMARY};
    selection-background-color: {COLOR_PRIMARY_LIGHT};
    selection-color: {COLOR_PRIMARY};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1.5px solid {COLOR_PRIMARY};
}}

QComboBox {{
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    color: {COLOR_TEXT_PRIMARY};
    min-height: 22px;
}}
QComboBox:focus {{
    border: 1.5px solid {COLOR_PRIMARY};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 26px;
    border-left: none;
}}
QComboBox::down-arrow {{
    image: url({ARROW_SVG});
    width: 11px;
    height: 11px;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 8px;
    selection-background-color: {COLOR_PRIMARY_LIGHT};
    selection-color: {COLOR_PRIMARY};
    padding: 4px;
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 6px;
    background: #E5E7EB;
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {COLOR_PRIMARY};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {COLOR_PRIMARY};
    width: 16px;
    height: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
    border: 2px solid #FFFFFF;
}}
QSlider::handle:horizontal:hover {{
    background: {COLOR_PRIMARY_HOVER};
}}

/* Checkboxes */
QCheckBox {{
    font-size: 13px;
    color: {COLOR_TEXT_PRIMARY};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    background-color: #FFFFFF;
}}
QCheckBox::indicator:checked {{
    background-color: {COLOR_PRIMARY};
    border-color: {COLOR_PRIMARY};
    image: url({CHECKED_SVG});
}}

/* Table Widget */
QTableWidget {{
    background-color: #FFFFFF;
    border: none;
    gridline-color: #F3F4F6;
    font-size: 13px;
    color: {COLOR_TEXT_PRIMARY};
    selection-background-color: {COLOR_PRIMARY_LIGHT};
    selection-color: {COLOR_TEXT_PRIMARY};
}}
QTableWidget::item {{
    padding: 8px;
    border-bottom: 1px solid #F3F4F6;
}}
QHeaderView::section {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 600;
    border: none;
    border-bottom: 1px solid #E5E7EB;
    padding: 8px;
    text-align: left;
}}

/* Scroll Area */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: #D1D5DB;
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #9CA3AF;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
