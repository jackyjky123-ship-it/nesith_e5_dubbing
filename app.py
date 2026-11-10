"""
KhmerTTS - English and Khmer Offline Text-to-Speech Studio
Entry Point.

Hard rules enforced:
- HF_HOME is pinned to ./models at the very top before any ML imports.
- UTF-8 encoding and Khmer font fallbacks configured for the GUI.
- Completely self-contained: loads local shared libraries from tools/lib if needed.
"""

import sys
import os
import ctypes

# --- HARD RULE 3: Set HF_HOME to project models/ before ANY model imports ---
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
FFMPEG_DIR = os.path.join(PROJECT_DIR, "tools", "ffmpeg")
os.makedirs(MODELS_DIR, exist_ok=True)
os.environ["HF_HOME"] = MODELS_DIR
os.environ["TRANSFORMERS_CACHE"] = MODELS_DIR
os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

# Self-contained Linux dependency fallback (loads bundled libxcb-cursor if present)
_local_xcb = os.path.join(PROJECT_DIR, "tools", "lib", "usr", "lib", "x86_64-linux-gnu", "libxcb-cursor.so.0")
if os.path.exists(_local_xcb):
    try:
        ctypes.CDLL(_local_xcb)
    except Exception:
        pass

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from ui.main_window import MainWindow


def setup_application() -> QApplication:
    # Enable high-DPI scaling
    app = QApplication(sys.argv)
    app.setApplicationName("KhmerTTS")
    app.setOrganizationName("KhmerTTS")

    # Set up global font with Khmer support fallback
    font = QFont()
    font_families = [
        "Segoe UI",
        "Noto Sans Khmer",
        "Kantumruy Pro",
        "Hanuman",
        "Khmer OS Battambang",
        "Leelawadee UI",
        "Roboto",
        "Ubuntu",
        "sans-serif"
    ]
    font.setFamilies(font_families)
    font.setPointSize(10)
    app.setFont(font)

    return app


def main():
    app = setup_application()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
