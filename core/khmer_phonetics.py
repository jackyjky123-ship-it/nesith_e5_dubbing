"""
KhmerDub - Khmer Phonetic Transliteration Engine.
Enables Meta MMS-TTS Khmer to fluently pronounce English technical terms,
loanwords, brand names, and acronyms without dropping or skipping words.
"""

import re
from typing import Dict, Optional

# Acronym letter sounds in Khmer
LETTER_NAMES: Dict[str, str] = {
    "a": "អេ", "b": "ប៊ី", "c": "ស៊ី", "d": "ឌី", "e": "អ៊ី",
    "f": "អែហ្វ", "g": "ជី", "h": "អេច", "i": "អាយ", "j": "ជេ",
    "k": "ខេ", "l": "អែល", "m": "អិម", "n": "អិន", "o": "អូ",
    "p": "ភី", "q": "ឃ្យូ", "r": "អ័រ", "s": "អេស", "t": "ធី",
    "u": "យូ", "v": "វី", "w": "ដាប់ប៊លយូ", "x": "អិច", "y": "វ៉ាយ", "z": "ហ្សេត"
}

# Rich English-to-Khmer Tech & Everyday Loanwords Dictionary
TECH_LOANWORDS: Dict[str, str] = {
    # Conversational English & Love / Greeting Phrases (matched first)
    "i love you so much": "អាយ ឡូវ យូ សូ ម៉ាត់ឆ៍",
    "i love you honey": "អាយ ឡូវ យូ ហាន់នី",
    "i love you baby": "អាយ ឡូវ យូ បេប៊ី",
    "i love you": "អាយ ឡូវ យូ",
    "i miss you so much": "អាយ មីស យូ សូ ម៉ាត់ឆ៍",
    "i miss you": "អាយ មីស យូ",
    "love you so much": "ឡូវ យូ សូ ម៉ាត់ឆ៍",
    "love you honey": "ឡូវ យូ ហាន់នី",
    "love you baby": "ឡូវ យូ បេប៊ី",
    "love you": "ឡូវ យូ",
    "thank you very much": "ថេងឃ្យូ វេរី ម៉ាត់ឆ៍",
    "thank you so much": "ថេងឃ្យូ សូ ម៉ាត់ឆ៍",
    "thank you": "ថេងឃ្យូ",
    "thanks so much": "ថេងស៍ សូ ម៉ាត់ឆ៍",
    "thanks a lot": "ថេងស៍ អឺ ឡុត",
    "thanks": "ថេងស៍",
    "good morning": "ហ្គូដ ម៉ូនិញ",
    "good afternoon": "ហ្គូដ អាហ្វធើនូន",
    "good evening": "ហ្គូដ អ៊ីវនីង",
    "good night": "ហ្គូដ ណាយ",
    "good luck": "ហ្គូដ ឡាក់",
    "good job": "ហ្គូដ ចប់",
    "have a nice day": "ហេវ អឺ ណាយស៍ ដេ",
    "have a good day": "ហេវ អឺ ហ្គូដ ដេ",
    "see you tomorrow": "ស៊ី យូ ធូម៉ូរ៉ូ",
    "see you later": "ស៊ី យូ ឡេធ័រ",
    "see you again": "ស៊ី យូ អឺហ្គេន",
    "see you soon": "ស៊ី យូ ស៊ូន",
    "see you": "ស៊ី យូ",
    "happy birthday": "ហេបភី បឺតដេ",
    "happy new year": "ហេបភី ញូវយា",
    "you are welcome": "យូ អា វេល់ខាំ",
    "you're welcome": "យូ អា វេល់ខាំ",
    "welcome": "វេល់ខាំ",
    "excuse me": "អិចស្គ្យូស មី",
    "no problem": "ណូ ប្រូប្លឹម",
    "don't worry": "ដុន វ៉ូរី",
    "take care": "ថេក ឃែរ",

    # Single Everyday Conversational Words
    "i": "អាយ",
    "you": "យូ",
    "love": "ឡូវ",
    "honey": "ហាន់នី",
    "baby": "បេប៊ី",
    "sweetheart": "ស្វីតហាត",
    "darling": "ដាលីង",
    "dear": "ឌា",
    "hello": "ហេឡូ",
    "hi": "ហាយ",
    "hey": "ហេ",
    "bye": "បាយ",
    "goodbye": "ហ្គូដបាយ",
    "sorry": "សូរី",
    "please": "ផ្លីស",
    "yes": "យេស",
    "no": "ណូ",
    "okay": "អូខេ",
    "ok": "អូខេ",
    "nice": "ណាយស៍",
    "cool": "ឃូល",
    "super": "ស៊ូភ័រ",
    "bro": "ប្រូ",
    "sis": "ស៊ីស",
    "brother": "ប្រាឌ័រ",
    "sister": "ស៊ីសស្ទ័រ",
    "guy": "ហ្គាយ",
    "guys": "ហ្គាយ",
    "friend": "ហ្វ្រេន",
    "friends": "ហ្វ្រេន",
    "boy": "ប៊យ",
    "girl": "ហ្គើល",
    "kiss": "ឃីស",
    "hug": "ហាក់",
    "heart": "ហាត",
    "cute": "ឃ្យូត",

    # Multi-word tech phrases (matched first)
    "web development": "វេប ឌីវេឡុបមិន",
    "source code": "សូសកូដ",
    "machine learning": "ម៉ាស៊ីន ឡឺននីង",
    "hard disk": "ហាឌីស",
    "operating system": "អូភើរ៉េតធីង ស៊ីស្ទឹម",
    "open source": "អូផិនសូស",
    "artificial intelligence": "អាធីហ្វីសល អ៊ីនថេលីជិន",
    "full stack": "ហ្វូលស្ទែក",
    "front end": "ហ្វ្រុនអិន",
    "back end": "ប៊ែកអិន",
    "sign in": "សាញអ៊ីន",
    "sign up": "សាញអាប់",
    "log in": "ឡុកអ៊ីន",
    "log out": "ឡុកអោត",
    "wi fi": "វ៉ាយហ្វាយ",

    # Operating Systems & Platforms
    "ubuntu": "អ៊ូប៊ុនទូ",
    "linux": "លីនុច",
    "windows": "វីនដូ",
    "window": "វីនដូ",
    "macos": "ម៉ាកអូអេស",
    "mac": "ម៉ាក",
    "android": "អានដ្រយ",
    "ios": "អាយអូអេស",

    # Core Tech & Developer Terms
    "license": "ឡាយសិន",
    "licenses": "ឡាយសិន",
    "developer": "ឌីវេឡុបភ័រ",
    "developers": "ឌីវេឡុបភ័រ",
    "development": "ឌីវេឡុបមិន",
    "programmer": "ប្រូក្រាមម័រ",
    "programmers": "ប្រូក្រាមម័រ",
    "programming": "ប្រូក្រាមីង",
    "program": "ប្រូក្រាម",
    "programs": "ប្រូក្រាម",
    "code": "កូដ",
    "coding": "កូដឌីង",
    "terminal": "ធើមីណល",
    "package": "ផាកខេក",
    "packages": "ផាកខេក",
    "server": "សឺវើ",
    "servers": "សឺវើ",
    "client": "ខ្លាយអិន",
    "clients": "ខ្លាយអិន",
    "service": "សេវាកម្ម",
    "services": "សេវាកម្ម",
    "database": "ដាតាបេស",
    "sql": "អេសឃ្យូអែល",
    "mysql": "ម៉ាយអេសឃ្យូអែល",
    "postgresql": "ផូសហ្គ្រេសអេសឃ្យូអែល",
    "cloud": "ខ្លោដ",
    "script": "ស្គ្រីប",
    "scripts": "ស្គ្រីប",
    "function": "ហ្វាំងសិន",
    "variable": "វ៉ារៀរបល",
    "class": "ខ្លាស",
    "framework": "ហ្វ្រេមវើក",
    "library": "ឡាយប៊្រឺរី",
    "module": "ម៉ូឌុល",
    "modules": "ម៉ូឌុល",
    "system": "ស៊ីស្ទឹម",
    "systems": "ស៊ីស្ទឹម",
    "command": "ខមមែន",
    "commands": "ខមមែន",

    # Tools, Git & Containers
    "git": "ហ្គីត",
    "github": "ហ្គីតហាប់",
    "gitlab": "ហ្គីតឡាប",
    "docker": "ដុកឃ័រ",
    "container": "ខន់ធែនណ័រ",
    "branch": "ប្រេន",
    "commit": "ខមមីត",
    "push": "ភុស្យ",
    "pull": "ភូល",
    "merge": "មឺច",
    "clone": "ក្លូន",
    "cloning": "ក្លូននីង",

    # Web & Languages
    "web": "វេប",
    "website": "វេបសាយ",
    "frontend": "ហ្វ្រុនអិន",
    "backend": "ប៊ែកអិន",
    "fullstack": "ហ្វូលស្ទែក",
    "html": "អេចធីអិមអែល",
    "css": "ស៊ីអេសអេស",
    "javascript": "ចាវ៉ាស្គ្រីប",
    "typescript": "ថាយស្គ្រីប",
    "python": "ផាយថុន",
    "java": "ចាវ៉ា",
    "php": "ភីអេចភី",
    "react": "រីអាក់",
    "node": "ណូត",
    "nodejs": "ណូតជេអេស",
    "vue": "វ្យូ",
    "angular": "អានហ្គូឡា",
    "rust": "រ៉ាស",
    "golang": "ហ្គោឡាង",
    "json": "ជេសុន",
    "api": "អេភីអាយ",
    "apis": "អេភីអាយ",
    "ui": "យូអាយ",
    "ux": "យូអិច",
    "url": "យូអរអែល",
    "http": "អេចធីធីភី",
    "https": "អេចធីធីភីអេស",

    # Hardware & Devices
    "computer": "កុំព្យូទ័រ",
    "computers": "កុំព្យូទ័រ",
    "laptop": "ឡេបថប",
    "pc": "ភីស៊ី",
    "cpu": "ស៊ីភីយូ",
    "ram": "រ៉េម",
    "gpu": "ជីភីយូ",
    "ssd": "អេសអេសឌី",
    "usb": "យូអេសប៊ី",
    "wifi": "វ៉ាយហ្វាយ",
    "bluetooth": "ប៊្លូធូស",
    "camera": "កាមេរ៉ា",
    "mouse": "ម៉ៅស៍",
    "keyboard": "ឃីប៊ត",
    "monitor": "ម៉ូនីទ័រ",
    "screen": "ស្គ្រីន",
    "device": "ឧបករណ៍",
    "phone": "ទូរស័ព្ទ",
    "smartphone": "ស្មាតហ្វូន",

    # Internet, Data & Media
    "internet": "អ៊ីនធឺណិត",
    "online": "អនឡាញ",
    "offline": "អហ្វឡាញ",
    "data": "ដាតា",
    "digital": "ឌីជីថល",
    "network": "ណេតវើក",
    "video": "វីដេអូ",
    "videos": "វីដេអូ",
    "audio": "អូឌីយ៉ូ",
    "sound": "សោន",
    "file": "ហ្វាល",
    "files": "ហ្វាល",
    "folder": "ហ្វូលឌ័រ",
    "folders": "ហ្វូលឌ័រ",
    "download": "ដោនឡូត",
    "upload": "អាប់ឡូត",
    "install": "អ៊ិនស្តល",
    "setup": "សេតអាប់",
    "update": "អាប់ដេត",
    "upgrade": "អាប់ក្រេត",
    "version": "វើហ្សិន",
    "bug": "បាក់",
    "bugs": "បាក់",
    "error": "អេរ័រ",
    "errors": "អេរ័រ",

    # Social & Content Creation
    "follow": "ហ្វូឡូ",
    "follower": "ហ្វូឡូវើ",
    "followers": "ហ្វូឡូវើ",
    "content": "ខន់ថិន",
    "creator": "គ្រីអេតធ័រ",
    "post": "ផុស",
    "posts": "ផុស",
    "comment": "ខមិន",
    "comments": "ខមិន",
    "like": "ឡាច",
    "likes": "ឡាច",
    "share": "ស៊ែរ",
    "shares": "ស៊ែរ",
    "subscribe": "សាប់ស្ក្រាយ",
    "subscriber": "សាប់ស្ក្រាយប័រ",
    "channel": "ឆាណែល",
    "page": "ផេក",
    "group": "គ្រុប",
    "link": "លីង",
    "profile": "ប្រូហ្វាល",
    "account": "អាខោន",
    "admin": "អាដមីន",
    "user": "យូស៊ើ",
    "users": "យូស៊ើ",
    "password": "ផាសវើដ",
    "login": "ឡុកអ៊ីន",
    "logout": "ឡុកអោត",
    "register": "រ៉េជីស្ទ័រ",
    "setting": "សេតធីង",
    "settings": "សេតធីង",
    "free": "ហ្វ្រី",
    "pro": "ប្រូ",
    "premium": "ព្រីមៀម",
    "app": "អែប",
    "apps": "អែប",
    "application": "អែបភ្លីខេសិន",
    "studio": "ស្ទូឌីយោ",
    "dub": "ដាប់",
    "dubbing": "ដាប់ប៊ីង",
    "khmerdub": "ខ្មែរដាប់",

    # Companies & Brands
    "google": "ហ្គូហ្គល",
    "facebook": "ហ្វេសប៊ុក",
    "youtube": "យូធូប",
    "tiktok": "ទិកតុក",
    "telegram": "តេឡេក្រាម",
    "instagram": "អ៊ិនស្តាក្រាម",
    "twitter": "ធ្វីតធ័រ",
    "meta": "មេតា",
    "microsoft": "ម៉ៃក្រូសូហ្វ",
    "apple": "អេបផល",
    "openai": "អូផិនអេអាយ",

    # Common Acronyms
    "it": "អាយធី",
    "ai": "អេអាយ",
    "pc": "ភីស៊ី",
    "tv": "ធីវី",
    "id": "អាយឌី",
    "ok": "អូខេ",
    "pdf": "ភីឌីអែហ្វ",
    "mp3": "អិមភីស្រ៊ី",
    "mp4": "អិមភីហ្វ័រ",
    "vip": "វីអាយភី",
    "ceo": "ស៊ីអ៊ីអូ",
    "cv": "ស៊ីវី",
    "sim": "ស៊ីម",
}

# Compile multi-word and single-word regex patterns for speed
_SORTED_KEYS = sorted(TECH_LOANWORDS.keys(), key=lambda k: len(k), reverse=True)
_LOANWORDS_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _SORTED_KEYS) + r")\b",
    re.IGNORECASE
)

# Rule-based fallback phonetic mapping for unknown Latin words
_CONSONANT_RULES = [
    ("ch", "ឆ"),
    ("sh", "ស"),
    ("th", "ថ"),
    ("ph", "ហ្វ"),
    ("wh", "វ"),
    ("ck", "ក"),
    ("ng", "ង"),
    ("qu", "ក្វ"),
    ("b", "ប"),
    ("c", "ក"),
    ("d", "ដ"),
    ("f", "ហ្វ"),
    ("g", "ហ្គ"),
    ("h", "ហ"),
    ("j", "ជ"),
    ("k", "ក"),
    ("l", "ល"),
    ("m", "ម"),
    ("n", "ន"),
    ("p", "ផ"),
    ("q", "ក"),
    ("r", "រ"),
    ("s", "ស"),
    ("t", "ត"),
    ("v", "វ"),
    ("w", "វ"),
    ("x", "ចស"),
    ("y", "យ"),
    ("z", "ហ្ស"),
]

_VOWEL_RULES = [
    ("tion", "សិន"),
    ("sion", "សិន"),
    ("ment", "មិន"),
    ("ing", "ីង"),
    ("ee", "ី"),
    ("ea", "ី"),
    ("oo", "ូ"),
    ("ou", "ៅ"),
    ("ow", "ៅ"),
    ("ai", "ាយ"),
    ("ay", "ាយ"),
    ("ey", "េ"),
    ("a", "ា"),
    ("e", "េ"),
    ("i", "ី"),
    ("o", "ោ"),
    ("u", "៊ូ"),
]


def transliterate_unknown_english_word(word: str) -> str:
    """
    Fallback phonetic transliteration of an unknown English word to Khmer script.
    If the word is 2-4 uppercase letters, spells it out as an acronym.
    """
    cleaned = word.strip()
    if not cleaned:
        return ""

    # Check if all uppercase (Acronym, e.g., 'SDK', 'LAN', 'RAM')
    if cleaned.isupper() and 2 <= len(cleaned) <= 4:
        spelled = [LETTER_NAMES.get(c.lower(), c) for c in cleaned]
        return "".join(spelled)

    # Phonetic Grapheme conversion
    lower = cleaned.lower()
    res = ""
    i = 0
    n = len(lower)

    # Check common suffixes first
    suffix_khmer = ""
    for suffix, k_rep in [("tion", "សិន"), ("sion", "សិន"), ("ment", "មិន"), ("ing", "ីង")]:
        if lower.endswith(suffix) and len(lower) > len(suffix):
            suffix_khmer = k_rep
            lower = lower[:-len(suffix)]
            n = len(lower)
            break

    while i < n:
        matched = False
        # Try 2-char then 1-char patterns
        for l_chars, k_char in _VOWEL_RULES + _CONSONANT_RULES:
            if lower.startswith(l_chars, i):
                res += k_char
                i += len(l_chars)
                matched = True
                break
        if not matched:
            # Skip unmapped character
            i += 1

    return res + suffix_khmer if res else word


def normalize_khmer_typos(text: str) -> str:
    """
    Normalizes common Khmer keyboard typos and Unicode anomalies:
    1. Legacy Limon 'To + Coeng Ba' (\\u1791\\u17d2\\u1794) -> 'Lo' (\\u17a1).
       e.g. ស្រទ្បាញ់ -> ស្រឡាញ់, ឡាន -> ទ្បាន, ឡើង -> ទ្បើង.
    2. Cleans up duplicate diacritics / vowels (e.g. duplicate bantoc, nikahit, coeng).
    3. Cleans up zero-width spaces (\\u200b) around punctuation marks.
    """
    if not text:
        return ""

    # Fix 1: Legacy Limon Lo typo (\\u1791\\u17d2\\u1794 -> \\u17a1)
    cleaned = text.replace("\u1791\u17d2\u1794", "\u17a1")

    # Fix 2: Consolidate duplicate subscript markers / vowels / diacritics
    cleaned = re.sub(r"\u17d2+", "\u17d2", cleaned)   # Coeng
    cleaned = re.sub(r"\u17b6+", "\u17b6", cleaned)   # Vowel Aa
    cleaned = re.sub(r"\u17cb+", "\u17cb", cleaned)   # Bantoc
    cleaned = re.sub(r"\u17c6+", "\u17c6", cleaned)   # Nikahit
    cleaned = re.sub(r"\u17cd+", "\u17cd", cleaned)   # Toandakhiat
    cleaned = re.sub(r"\u17c9+", "\u17c9", cleaned)   # Muusikatoan
    cleaned = re.sub(r"\u17ca+", "\u17ca", cleaned)   # Triisap

    # Fix 3: Remove zero-width spaces immediately adjacent to punctuation
    cleaned = re.sub(r"\u200b+([។៕\.\,\?\!])", r"\1", cleaned)

    return cleaned


def prepare_text_for_mms_khmer(text: str) -> str:
    """
    Prepares text for Meta MMS-TTS Khmer synthesis by:
    1. Normalizing Khmer keyboard typos and Unicode anomalies (e.g. ទ្ប -> ឡ).
    2. Transliterating English loanwords, conversational phrases, and acronyms into phonetic Khmer script.
    Guarantees that MMS-TTS speaks both Khmer and English smoothly without dropping words.
    """
    if not text:
        return ""

    # Step 0: Normalize Khmer keyboard typos
    text = normalize_khmer_typos(text)

    # Step 1: Replace known dictionary loanwords (case-insensitive)
    def _loanword_sub(match: re.Match) -> str:
        key = match.group(0).lower()
        return TECH_LOANWORDS.get(key, match.group(0))

    text_transformed = _LOANWORDS_PATTERN.sub(_loanword_sub, text)

    # Step 2: Catch any remaining isolated English words / acronyms
    def _fallback_sub(match: re.Match) -> str:
        w = match.group(0)
        # If already Khmer or punctuation, leave untouched
        if re.search(r"[\u1780-\u17FF]", w):
            return w
        transliterated = transliterate_unknown_english_word(w)
        return transliterated if transliterated else w

    # Matches any remaining sequence of Latin letters
    text_transformed = re.sub(r"\b[A-Za-z]+\b", _fallback_sub, text_transformed)

    return text_transformed


def split_bilingual_segments(text: str) -> list[tuple[str, str]]:
    """
    Intelligently segments text into language-coherent blocks: list of (segment_text, 'km' | 'en').
    Features:
    1. Splits on standard sentence delimiters (Khmer: ។, ៕; Latin: ., !, ?, newline).
    2. Corrects unpunctuated transitions (e.g. 'បងស្រឡាញ់អូន I love you honey').
    3. Retains embedded tech loanwords (e.g. 'Ubuntu', 'Linux') inside Khmer sentences as 'km'.
    """
    if not text:
        return []

    # Step 0: Normalize typos and invisible spaces
    normalized = normalize_khmer_typos(text.strip())
    normalized = re.sub(r"[\u200b\u200c\u200d]+", " ", normalized)

    # Step 1: Split by standard sentence delimiters
    raw_sentences = re.split(r"([។៕\.\!\?\n]+)", normalized)

    reconstructed = []
    i = 0
    while i < len(raw_sentences):
        sentence = raw_sentences[i].strip()
        if not sentence:
            i += 1
            continue
        if i + 1 < len(raw_sentences) and re.match(r"^[។៕\.\!\?\n]+$", raw_sentences[i+1]):
            sentence += raw_sentences[i+1].strip()
            i += 2
        else:
            i += 1
        reconstructed.append(sentence)

    segments = []
    for s in reconstructed:
        has_km = bool(re.search(r"[\u1780-\u17FF]", s))
        has_en = bool(re.search(r"[A-Za-z]{2,}", s))

        # Check for unpunctuated language transitions inside a single sentence
        if has_km and has_en:
            # Trailing English phrase (e.g. "បងស្រឡាញ់អូន I love you honey.")
            m = re.match(r"^(.+?[\u1780-\u17FF][។៕]?)\s+([A-Za-z][A-Za-z0-9\s,!?\x27\"]+)$", s)
            if m and len(m.group(2).strip().split()) >= 2:
                segments.append((m.group(1).strip(), "km"))
                segments.append((m.group(2).strip(), "en"))
                continue

            # Leading English phrase (e.g. "Hello honey បងស្រឡាញ់អូន។")
            m2 = re.match(r"^([A-Za-z][A-Za-z0-9\s,!?\x27\"]+)\s+([\u1780-\u17FF].*)$", s)
            if m2 and len(m2.group(1).strip().split()) >= 2:
                segments.append((m2.group(1).strip(), "en"))
                segments.append((m2.group(2).strip(), "km"))
                continue

        lang = "km" if has_km else "en"
        segments.append((s, lang))

    return segments

