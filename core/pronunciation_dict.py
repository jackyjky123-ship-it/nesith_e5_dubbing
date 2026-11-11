"""
KhmerTTS - User Pronunciation Dictionary Manager.
Allows users to define custom phonetic pronunciations for English words, acronyms,
and technical terminology that take highest priority during TTS synthesis.
Persisted in a human-editable JSON file.
"""

import os
import json
import re
from typing import Dict, Optional, Tuple
from core.config import PROJECT_DIR

DEFAULT_USER_DICT_FILE = os.path.join(PROJECT_DIR, "pronunciation_dict.json")

# Default starter pronunciation entries
STARTER_DICTIONARY: Dict[str, str] = {
    "Artificial Intelligence": "អាធីហ្វីសល អ៊ិនធែលលីជិន",
    "Computer": "កុំព្យូទ័រ",
    "Framework": "ហ្វ្រេមវើក",
    "JavaScript": "ចាវ៉ាស្គ្រីប",
    "React": "រីអាក់",
    "Tailwind": "ថេលវីន",
    "PostgreSQL": "ប៉ុសហ្គ្រេស ឃ្យូអែល",
    "FastAPI": "ហ្វាស អេភីអាយ",
    "OpenAI": "អូផិនអេអាយ",
    "ChatGPT": "ឆាតជីភីធី",
    "TypeScript": "ថាយស្គ្រីប",
    "Next.js": "ណិច ជេអេស",
    "Node.js": "ណូដ ជេអេស",
    "Vue": "វ្យូ",
    "Angular": "អេងហ្គូឡា",
    "PyTorch": "ផាយថច",
    "TensorFlow": "ធេនស័រផ្លូ",
}

_cached_user_dict: Optional[Dict[str, str]] = None
_cached_mtime: float = 0.0


def get_user_dictionary_path() -> str:
    """Returns absolute path to the user pronunciation dictionary file."""
    return DEFAULT_USER_DICT_FILE


def load_user_dictionary(file_path: Optional[str] = None) -> Dict[str, str]:
    """
    Loads user-defined pronunciation dictionary from JSON.
    Returns normalized lowercase dictionary {english_word: khmer_phonetic}.
    Caches in memory and invalidates automatically if file changes.
    """
    global _cached_user_dict, _cached_mtime
    path = file_path or get_user_dictionary_path()

    # Create default file if it doesn't exist
    if not os.path.exists(path):
        save_user_dictionary(STARTER_DICTIONARY, path)
        _cached_user_dict = {k.lower(): v for k, v in STARTER_DICTIONARY.items()}
        _cached_mtime = os.path.getmtime(path)
        return dict(_cached_user_dict)

    try:
        current_mtime = os.path.getmtime(path)
        if _cached_user_dict is not None and current_mtime == _cached_mtime:
            return dict(_cached_user_dict)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            # Normalize keys to lowercase for case-insensitive matching
            _cached_user_dict = {str(k).strip().lower(): str(v).strip() for k, v in data.items() if str(k).strip()}
            _cached_mtime = current_mtime
            return dict(_cached_user_dict)
    except Exception as e:
        print(f"[pronunciation_dict] Warning: failed to load {path}: {e}")

    return {k.lower(): v for k, v in STARTER_DICTIONARY.items()}


def save_user_dictionary(dictionary: Dict[str, str], file_path: Optional[str] = None) -> bool:
    """Saves user dictionary to JSON file."""
    global _cached_user_dict, _cached_mtime
    path = file_path or get_user_dictionary_path()
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dictionary, f, indent=2, ensure_ascii=False)
        _cached_user_dict = {k.lower(): v for k, v in dictionary.items()}
        _cached_mtime = os.path.getmtime(path)
        return True
    except Exception as e:
        print(f"[pronunciation_dict] Error saving {path}: {e}")
        return False


def add_user_pronunciation(word: str, pronunciation: str, file_path: Optional[str] = None) -> bool:
    """Adds or updates a custom pronunciation for a word or phrase."""
    path = file_path or get_user_dictionary_path()
    raw_dict: Dict[str, str] = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    raw_dict = loaded
        except Exception:
            raw_dict = {}

    raw_dict[word.strip()] = pronunciation.strip()
    return save_user_dictionary(raw_dict, path)


def remove_user_pronunciation(word: str, file_path: Optional[str] = None) -> bool:
    """Removes a custom pronunciation entry."""
    path = file_path or get_user_dictionary_path()
    if not os.path.exists(path):
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_dict = json.load(f)
        target_key = None
        for k in raw_dict:
            if k.lower() == word.lower().strip():
                target_key = k
                break
        if target_key:
            del raw_dict[target_key]
            return save_user_dictionary(raw_dict, path)
        return False
    except Exception as e:
        print(f"[pronunciation_dict] Error removing word: {e}")
        return False
