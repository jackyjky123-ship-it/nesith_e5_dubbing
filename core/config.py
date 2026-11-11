"""
KhmerDub - Core Configuration and Environment Setup.
Strictly adheres to AGENT.md rules:
- HF_HOME is locked to project models/ directory.
- ffmpeg path is pinned to tools/ffmpeg.
- Manages paths, hardware settings, and persistent configuration.
"""

import os
import sys
import json
import shutil
from typing import Dict, Any

# Root Project Directories
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
TEMP_DIR = os.path.join(PROJECT_DIR, "temp")
EXPORTS_DIR = os.path.join(PROJECT_DIR, "exports")
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
TOOLS_DIR = os.path.join(PROJECT_DIR, "tools")
FFMPEG_DIR = os.path.join(TOOLS_DIR, "ffmpeg")
FFMPEG_EXE = os.path.join(FFMPEG_DIR, "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
CONFIG_FILE = os.path.join(PROJECT_DIR, "config.json")
RECENT_TTS_FILE = os.path.join(TEMP_DIR, "recent_tts.json")

# Ensure critical workspace directories exist
for d in (MODELS_DIR, TEMP_DIR, EXPORTS_DIR, ASSETS_DIR):
    os.makedirs(d, exist_ok=True)

# HARD RULE 3 & 5: Set environment cache variables and enforce offline mode
os.environ["HF_HOME"] = MODELS_DIR
os.environ["TRANSFORMERS_CACHE"] = MODELS_DIR
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Add bundled ffmpeg to PATH
if os.path.exists(FFMPEG_DIR):
    os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

# Default Application Configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "device": "cpu",                     # "cpu" or "cuda"
    "precision": "fp32",                 # "fp32" or "fp16"
    "low_memory_mode": True,             # Unload model after generation to conserve 8GB RAM
    "tts_engine": "mms_khmer",           # "mms_khmer" (Local), "gemini" (Gemini AI)
    "tts_default_quality_steps": 8,      # 4 to 32 steps (8 is balanced for CPU)
    "tts_default_speed": 1.0,            # 0.5 to 2.0
    "export_folder": EXPORTS_DIR,
    # Gemini AI BYOK Settings (Non-secret preferences; API key is stored in OS secure storage only)
    "gemini_model": "gemini-3.8-flash-tts",
    "gemini_voice": "Kore",
    "gemini_style": "Natural, clear, and expressive",
}


def load_config() -> Dict[str, Any]:
    """Loads configuration from config.json or returns defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                cfg = DEFAULT_CONFIG.copy()
                cfg.update(user_cfg)
                return cfg
        except Exception as e:
            print(f"[config] Warning loading config.json: {e}")
    return DEFAULT_CONFIG.copy()


def save_config(cfg: Dict[str, Any]) -> bool:
    """Saves configuration to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[config] Error saving config.json: {e}")
        return False


def get_active_device() -> str:
    """Returns 'cuda' or 'cpu' according to config and hardware availability."""
    cfg = load_config()
    req_device = cfg.get("device", "cpu")
    if req_device == "cuda":
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
    return "cpu"


def get_ffmpeg_path() -> str:
    """Returns path to the bundled or system ffmpeg executable."""
    if os.path.exists(FFMPEG_EXE) and os.access(FFMPEG_EXE, os.X_OK):
        return FFMPEG_EXE
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    return FFMPEG_EXE
