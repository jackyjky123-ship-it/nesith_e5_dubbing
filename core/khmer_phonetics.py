"""
KhmerTTS - Advanced English-to-Khmer Phonetic Transliteration Engine.
Enables Meta MMS-TTS Khmer to fluently and naturally pronounce:
1. English words, technical terminology, and conversational speech.
2. Mixed Khmer-English scripts (code-switching).
3. Numbers and dates into spoken Khmer words.
4. Acronyms, abbreviations, and contractions.
5. Unknown English words via intelligent rule-based Grapheme-to-Phoneme (G2P).

Ensures all phonetic outputs use valid Khmer Unicode character sequences anchored
by valid base consonants (preventing orphaned dependent vowels or dropped tokens).
"""

import re
from typing import Dict, List, Tuple, Optional

# Acronym letter names in Khmer
LETTER_NAMES: Dict[str, str] = {
    "a": "អេ", "b": "ប៊ី", "c": "ស៊ី", "d": "ឌី", "e": "អ៊ី",
    "f": "អែហ្វ", "g": "ជី", "h": "អេច", "i": "អាយ", "j": "ជេ",
    "k": "ខេ", "l": "អែល", "m": "អិម", "n": "អិន", "o": "អូ",
    "p": "ភី", "q": "ឃ្យូ", "r": "អ័រ", "s": "អេស", "t": "ធី",
    "u": "យូ", "v": "វី", "w": "ដាប់ប៊លយូ", "x": "អិច", "y": "វ៉ាយ", "z": "ហ្សេត"
}

# Number expansion map
_DIGIT_MAP: Dict[int, str] = {
    0: "សូន្យ", 1: "មួយ", 2: "ពីរ", 3: "បី", 4: "បួន", 5: "ប្រាំ",
    6: "ប្រាំមួយ", 7: "ប្រាំពីរ", 8: "ប្រាំបី", 9: "ប្រាំបួន", 10: "ដប់"
}

_TENS_MAP: Dict[int, str] = {
    2: "ម្ភៃ", 3: "សាមសិប", 4: "សែសិប", 5: "ហាសិប",
    6: "ហុកសិប", 7: "ចិតសិប", 8: "ប៉ែតសិប", 9: "កៅសិប"
}

def number_to_khmer(num_str: str) -> str:
    """Converts a string of digits to spoken Khmer words."""
    try:
        val = int(num_str)
        if val <= 10:
            return _DIGIT_MAP.get(val, num_str)
        if val < 20:
            return "ដប់" + _DIGIT_MAP.get(val - 10, "")
        if val < 100:
            tens = val // 10
            rem = val % 10
            base = _TENS_MAP.get(tens, "")
            return base + (_DIGIT_MAP.get(rem, "") if rem > 0 else "")
        if val < 1000:
            hundreds = val // 100
            rem = val % 100
            res = _DIGIT_MAP.get(hundreds, "") + "រយ"
            if rem > 0:
                res += " " + number_to_khmer(str(rem))
            return res
        if val < 10000:
            thousands = val // 1000
            rem = val % 1000
            res = _DIGIT_MAP.get(thousands, "") + "ពាន់"
            if rem > 0:
                res += " " + number_to_khmer(str(rem))
            return res
        return " ".join(_DIGIT_MAP.get(int(d), d) for d in num_str)
    except Exception:
        return num_str


_EN_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
            "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
            "seventeen", "eighteen", "nineteen"]
_EN_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

def english_int_to_words(n: int) -> str:
    """Converts an integer into spoken English words."""
    if n == 0:
        return "zero"
    if n < 0:
        return "minus " + english_int_to_words(-n)
    if n < 20:
        return _EN_ONES[n]
    if n < 100:
        ten = _EN_TENS[n // 10]
        rem = _EN_ONES[n % 10]
        return f"{ten} {rem}".strip()
    if n < 1000:
        hundred = f"{_EN_ONES[n // 100]} hundred"
        rem = n % 100
        return f"{hundred} {english_int_to_words(rem)}".strip() if rem else hundred
    if n < 1000000:
        thousand = f"{english_int_to_words(n // 1000)} thousand"
        rem = n % 1000
        return f"{thousand} {english_int_to_words(rem)}".strip()
    return str(n)

def normalize_english_numbers(text: str) -> str:
    """Expands digit sequences in English text into spoken English words."""
    def repl(m):
        try:
            return english_int_to_words(int(m.group(0)))
        except Exception:
            return m.group(0)
    return re.sub(r"\b\d+\b", repl, text)


# Comprehensive English-to-Khmer Phonetic Lexicon
TECH_LOANWORDS: Dict[str, str] = {
    # Conversational Phrases & Greetings (Longest first)
    "thank you very much": "ថេងឃ្យូ វ៉េរី ម៉ាត់ឆ៍",
    "thank you so much": "ថេងឃ្យូ សូ ម៉ាត់ឆ៍",
    "thank you": "ថេងឃ្យូ",
    "thanks very much": "ថេងស៍ វ៉េរី ម៉ាត់ឆ៍",
    "thanks so much": "ថេងស៍ សូ ម៉ាត់ឆ៍",
    "thanks a lot": "ថេងស៍ អឺ ឡុត",
    "thanks": "ថេងស៍",
    "you are welcome": "យូ អា វេល់ខាំ",
    "you're welcome": "យូ អា វេល់ខាំ",
    "welcome": "វេល់ខាំ",
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
    "excuse me": "អិចស្គ្យូស មី",
    "no problem": "ណូ ប្រូប្លឹម",
    "don't worry": "ដូន វ៉ូរី",
    "take care": "ថេក ឃែរ",
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
    "how are you": "ហៅ អា យូ",
    "what's up": "វ៉ាត់ស៍ អាប់",
    "by the way": "បាយ ដឹ វេ",
    "no longer": "ណូ ឡងហ្គ័រ",
    "as soon as possible": "អែស ស៊ូន អែស ផូស៊ីបល",
    "never mind": "ណេវ៉ា ម៉ាញ",
    "of course": "អហ្វ ខូស",
    "right now": "រ៉ាយ ណាវ",

    # English Contractions
    "don't": "ដូន",
    "dont": "ដូន",
    "doesn't": "ដាសសិន",
    "doesnt": "ដាសសិន",
    "didn't": "ឌីតដិន",
    "didnt": "ឌីតដិន",
    "can't": "ខេន",
    "cant": "ខេន",
    "cannot": "ខេនណត់",
    "couldn't": "ឃូដដិន",
    "couldnt": "ឃូដដិន",
    "won't": "វូន",
    "wont": "វូន",
    "wouldn't": "វូដដិន",
    "wouldnt": "វូដដិន",
    "shouldn't": "ស៊ូដដិន",
    "shouldnt": "ស៊ូដដិន",
    "isn't": "អ៊ីសសិន",
    "isnt": "អ៊ីសសិន",
    "aren't": "អាន",
    "arent": "អាន",
    "wasn't": "វ៉សសិន",
    "wasnt": "វ៉សសិន",
    "weren't": "វើន",
    "werent": "វើន",
    "haven't": "ហេវវិន",
    "havent": "ហេវវិន",
    "hasn't": "ហេសសិន",
    "hasnt": "ហេសសិន",
    "hadn't": "ហេតដិន",
    "hadnt": "ហេតដិន",
    "it's": "អ៊ិតស៍",
    "its": "អ៊ិតស៍",
    "that's": "ដេតស៍",
    "thats": "ដេតស៍",
    "what's": "វ៉ាត់ស៍",
    "whats": "វ៉ាត់ស៍",
    "there's": "ដ៊ែរ ស៍",
    "theres": "ដ៊ែរ ស៍",
    "here's": "ហ៊ីយែរ ស៍",
    "heres": "ហ៊ីយែរ ស៍",
    "i'm": "អាយម",
    "im": "អាយម",
    "you're": "យូ អា",
    "youre": "យូ អា",
    "we're": "វី អា",
    "were": "វើ",
    "they're": "ដេ អា",
    "theyre": "ដេ អា",
    "i've": "អាយវ",
    "ive": "អាយវ",
    "you've": "យូ វ",
    "youve": "យូ វ",
    "we've": "វី វ",
    "weve": "វី វ",
    "they've": "ដេ វ",
    "theyve": "ដេ វ",
    "i'll": "អាយល",
    "ill": "អាយល",
    "you'll": "យូ ល",
    "youll": "យូ ល",
    "he'll": "ហ៊ី ល",
    "hell": "ហេល",
    "she'll": "ស៊ី ល",
    "shell": "សែល",
    "we'll": "វី ល",
    "they'll": "ដេ ល",
    "theyll": "ដេ ល",
    "let's": "ឡេតស៍",
    "lets": "ឡេតស៍",

    # Key Speech & Script Words (Addressing user's exact issues)
    "speech": "ស្ពីច",
    "speeches": "ស្ពីចស៍",
    "script": "ស្គ្រីប",
    "scripts": "ស្គ្រីបស៍",
    "scripting": "ស្គ្រីបធីង",
    "natural": "ណេតឆឺរ៉ល",
    "naturally": "ណេតឆឺរ៉លី",
    "language": "ឡេងហ្គ្វិច",
    "languages": "ឡេងហ្គ្វិចស៍",
    "quality": "ខ្វាលីធី",
    "qualities": "ខ្វាលីធីស",
    "mix": "ម៉ិកស៍",
    "mixed": "ម៉ិកស៍",
    "mixing": "ម៉ិកស៊ីង",
    "mixes": "ម៉ិកស៍",
    "work": "វើក",
    "working": "វើកឃីង",
    "worked": "វើក",
    "works": "វើកស៍",
    "worker": "វើកខ័រ",
    "workers": "វើកខ័រ",
    "word": "វើត",
    "words": "វើតស៍",
    "know": "ណូ",
    "knows": "ណូស",
    "knew": "ញូ",
    "known": "ណូន",
    "knowing": "ណូអ៊ីង",
    "sound": "សោន",
    "sounds": "សោនស៍",
    "sounded": "សោនឌីដ",
    "sounding": "សោនឌីង",
    "improve": "អុីមព្រូវ",
    "improves": "អុីមព្រូវស៍",
    "improved": "អុីមព្រូវ",
    "improving": "អុីមព្រូវវីង",
    "improvement": "អុីមព្រូវមិន",
    "dubbing": "ដាប់ប៊ីង",
    "dub": "ដាប់",
    "dubbed": "ដាប់",
    "cloning": "ក្លូនីង",
    "clone": "ក្លូន",
    "cloned": "ក្លូន",
    "delete": "ឌីលីត",
    "deletes": "ឌីលីតស៍",
    "deleted": "ឌីលីតធីត",
    "deleting": "ឌីលីតធីង",
    "remove": "រីមូវ",
    "removes": "រីមូវស៍",
    "removed": "រីមូវដ៍",
    "removing": "រីមូវវីង",
    "plan": "ផ្លែន",
    "plans": "ផ្លែនស៍",
    "planned": "ផ្លែន",
    "planning": "ផ្លេននីង",
    "build": "បៀលដ៍",
    "builds": "បៀលដ៍",
    "building": "បៀលឌីង",
    "built": "បៀលត",
    "builder": "បៀលឌ័រ",
    "voice": "វ៉យស៍",
    "voices": "វ៉យស៍",
    "video": "វីដេអូ",
    "videos": "វីដេអូ",
    "audio": "អូឌីយ៉ូ",
    "project": "ប្រូជេក",
    "projects": "ប្រូជេកស៍",
    "studio": "ស្ទូឌីយូ",
    "studios": "ស្ទូឌីយូ",
    "ui": "យូអាយ",
    "gui": "ជីយូអាយ",
    "perfect": "ភើហ្វិក",
    "perfectly": "ភើហ្វិកលី",
    "english": "អង់គ្លេស",
    "khmer": "ខ្មែរ",
    "khmertts": "ខ្មែរ ធីធីអេស",
    "khmerdub": "ខ្មែរដាប់",

    # Pronouns & Determiners
    "the": "ដឹ",
    "a": "អឺ",
    "an": "អ៊ែន",
    "this": "ឌីស",
    "that": "ដេត",
    "these": "ឌីស",
    "those": "ដូស",
    "i": "អាយ",
    "you": "យូ",
    "he": "ហ៊ី",
    "she": "ស៊ី",
    "it": "អ៊ិត",
    "we": "វី",
    "they": "ដេ",
    "me": "មី",
    "him": "ហ៊ីម",
    "her": "ហើ",
    "us": "អាស",
    "them": "ដិម",
    "my": "ម៉ាយ",
    "your": "យ័រ",
    "his": "ហ៊ីស",
    "our": "អាវើ",
    "their": "ដ៊ែរ",
    "mine": "ម៉ាញ",
    "yours": "យ័រ",
    "ours": "អាវើ",
    "theirs": "ដ៊ែរ",

    # Auxiliary Verbs & Core Copulas
    "is": "អ៊ីស",
    "am": "អ៊ែម",
    "are": "អា",
    "was": "វ៉ស",
    "were": "វើ",
    "be": "ប៊ី",
    "been": "ប៊ីន",
    "being": "ប៊ីអ៊ីង",
    "have": "ហេវ",
    "has": "ហេស",
    "had": "ហេដ",
    "having": "ហេវវីង",
    "do": "ឌូ",
    "does": "ដាស",
    "did": "ឌីដ",
    "doing": "ឌូអ៊ីង",
    "done": "ដាន់",
    "can": "ខេន",
    "could": "ឃូដ",
    "will": "វិល",
    "would": "វូដ",
    "shall": "ស៊ែល",
    "should": "ស៊ូដ",
    "may": "មេ",
    "might": "ម៉ាយ",
    "must": "ម៉ាស្ត",

    # Common Prepositions & Conjunctions
    "in": "អ៊ិន",
    "on": "អន",
    "at": "អែត",
    "to": "ធូ",
    "too": "ធូ",
    "for": "ហ្វ័រ",
    "with": "វិដ",
    "without": "វិដអាវត",
    "by": "បាយ",
    "from": "ហ្វ្រម",
    "up": "អាប់",
    "down": "ដោន",
    "out": "អាវត",
    "over": "អូវើ",
    "under": "អាន់ឌ័រ",
    "about": "អឹបៅត",
    "of": "អហ្វ",
    "off": "អហ្វ",
    "into": "អ៊ិនធូ",
    "through": "ស្រ៊ូ",
    "after": "អាហ្វធ័រ",
    "before": "ប៊ីហ្វ័រ",
    "between": "ប៊ីធ្វីន",
    "during": "ឌ្យូរីង",
    "and": "អ៊ែន",
    "but": "បាត់",
    "or": "អរ",
    "so": "សូ",
    "because": "ប៊ីខស",
    "if": "អ៊ិហ្វ",
    "as": "អ៊ែស",
    "than": "ដេន",
    "then": "ដេន",
    "when": "វេន",
    "where": "វែរ",
    "why": "វ៉ាយ",
    "how": "ហៅ",
    "what": "វ៉ាត់",
    "who": "ហ៊ូ",
    "which": "វិច",
    "not": "ណត់",
    "no": "ណូ",
    "yes": "យេស",

    # High Frequency Verbs
    "make": "មេក",
    "makes": "មេកស៍",
    "made": "មេដ",
    "making": "មេឃីង",
    "take": "ថេក",
    "takes": "ថេកស៍",
    "took": "ធូក",
    "taken": "ថេខិន",
    "taking": "ថេឃីង",
    "get": "ហ្គេត",
    "gets": "ហ្គេតស៍",
    "got": "ហ្គត់",
    "getting": "ហ្គេតធីង",
    "give": "ហ្គីវ",
    "gives": "ហ្គីវស៍",
    "gave": "ហ្គេវ",
    "given": "ហ្គីវវិន",
    "giving": "ហ្គីវវីង",
    "find": "ហ្វាយ",
    "finds": "ហ្វាយស៍",
    "found": "ហ្វោន",
    "finding": "ហ្វាយឌីង",
    "see": "ស៊ី",
    "sees": "ស៊ីស",
    "saw": "ស",
    "seen": "ស៊ីន",
    "seeing": "ស៊ីអ៊ីង",
    "look": "លូក",
    "looks": "លូកស៍",
    "looked": "លូក",
    "looking": "លូឃីង",
    "come": "ខាំ",
    "comes": "ខាំស",
    "came": "ខេម",
    "coming": "ខាំមីង",
    "go": "ហ្គោ",
    "goes": "ហ្គោស",
    "went": "វេនត",
    "gone": "ហ្គន",
    "going": "ហ្គោអ៊ីង",
    "say": "សេ",
    "says": "សេស",
    "said": "សេដ",
    "saying": "សេអ៊ីង",
    "tell": "ថេល",
    "tells": "ថេលស៍",
    "told": "ថូលដ៍",
    "telling": "ថេលលីង",
    "ask": "អាសក៍",
    "asks": "អាសក៍",
    "asked": "អាសក៍",
    "asking": "អាសឃីង",
    "think": "ធីងក៍",
    "thinks": "ធីងក៍",
    "thought": "ថត",
    "thinking": "ធីងឃីង",
    "feel": "ហ្វីល",
    "feels": "ហ្វីលស៍",
    "felt": "ហ្វេលត",
    "feeling": "ហ្វីលលីង",
    "try": "ត្រាយ",
    "tries": "ត្រាយស៍",
    "tried": "ត្រាយ",
    "trying": "ត្រាយអ៊ីង",
    "need": "នីដ",
    "needs": "នីដស៍",
    "needed": "នីដឌីត",
    "needing": "នីដឌីង",
    "want": "វ៉ន",
    "wants": "វ៉នស៍",
    "wanted": "វ៉នធីត",
    "wanting": "វ៉នធីង",
    "use": "យូស",
    "uses": "យូសសឺស",
    "used": "យូសដ៍",
    "using": "យូស៊ីង",
    "like": "ឡាយខ៍",
    "likes": "ឡាយខ៍",
    "liked": "ឡាយខ៍",
    "liking": "ឡាយឃីង",
    "love": "ឡូវ",
    "loves": "ឡូវស៍",
    "loved": "ឡូវដ៍",
    "loving": "ឡូវវីង",
    "start": "ស្តាត",
    "starts": "ស្តាតស៍",
    "started": "ស្តាតធិត",
    "starting": "ស្តាតធីង",
    "stop": "ស្តុប",
    "stops": "ស្តុបស៍",
    "stopped": "ស្តុប",
    "stopping": "ស្តុបភីង",
    "keep": "ឃីប",
    "keeps": "ឃីបស៍",
    "kept": "ខេបត",
    "keeping": "ឃីបភីង",
    "wait": "វ៉េត",
    "waits": "វ៉េតស៍",
    "waited": "វ៉េតធីត",
    "waiting": "វ៉េតធីង",
    "run": "រ៉ាន់",
    "runs": "រ៉ាន់ស៍",
    "ran": "រ៉េន",
    "running": "រ៉ាន់នីង",
    "move": "មូវ",
    "moves": "មូវស៍",
    "moved": "មូវដ៍",
    "moving": "មូវវីង",
    "live": "លីវ",
    "lives": "លីវស៍",
    "lived": "លីវដ៍",
    "living": "លីវវីង",
    "leave": "លីវ",
    "leaves": "លីវស៍",
    "left": "ឡេហ្វ",
    "leaving": "លីវវីង",
    "show": "សូ",
    "shows": "សូស",
    "showed": "សូដ",
    "shown": "សូន",
    "showing": "សូអ៊ីង",
    "play": "ផ្លេ",
    "plays": "ផ្លេស",
    "played": "ផ្លេដ",
    "playing": "ផ្លេយីង",
    "player": "ផ្លេយ័រ",
    "help": "ហេលផ៍",
    "helps": "ហេលផ៍",
    "helped": "ហេលផ៍",
    "helping": "ហេលភីង",
    "call": "ខល",
    "calls": "ខលស៍",
    "called": "ខល",
    "calling": "ខលលីង",
    "check": "ឆែក",
    "checks": "ឆែកស៍",
    "checked": "ឆែក",
    "checking": "ឆែកឃីង",
    "test": "ថេស្ត",
    "tests": "ថេស្តស៍",
    "tested": "ថេស្តធីត",
    "testing": "ថេស្តធីង",
    "open": "អូផិន",
    "opens": "អូផិនស៍",
    "opened": "អូផិន",
    "opening": "អូផិននីង",
    "close": "ក្លូស",
    "closes": "ក្លូសសឺស",
    "closed": "ក្លូសដ៍",
    "closing": "ក្លូស៊ីង",
    "save": "សេវ",
    "saves": "សេវស៍",
    "saved": "សេវដ៍",
    "saving": "សេវវីង",
    "change": "ឆេញ",
    "changes": "ឆេញជឺស",
    "changed": "ឆេញ",
    "changing": "ឆេញជីង",
    "create": "គ្រីអេត",
    "creates": "គ្រីអេតស៍",
    "created": "គ្រីអេតធីត",
    "creating": "គ្រីអេតធីង",
    "read": "រីដ",
    "reads": "រីដស៍",
    "reading": "រីដឌីង",
    "write": "រ៉ាយ",
    "writes": "រ៉ាយស៍",
    "wrote": "រ៉ូត",
    "written": "រ៉ីតធិន",
    "writing": "រ៉ាយធីង",
    "learn": "លើន",
    "learns": "លើនស៍",
    "learned": "លើន",
    "learning": "លើននីង",
    "teach": "ធីច",
    "teaches": "ធីចឆឺស",
    "taught": "ថត",
    "teaching": "ធីចជីង",
    "teacher": "ធីឆ័រ",
    "understand": "អាន់ឌើស្តេន",
    "understands": "អាន់ឌើស្តេនស៍",
    "understood": "អាន់ឌើស្តូដ",
    "remember": "រីមេមប័រ",
    "remembers": "រីមេមប័រ",
    "remembered": "រីមេមប័រ",
    "forget": "ហ្វរហ្គេត",
    "forgets": "ហ្វរហ្គេតស៍",
    "forgot": "ហ្វរហ្គត់",
    "forgotten": "ហ្វរហ្គត់ធិន",
    "send": "សេន",
    "sends": "សេនស៍",
    "sent": "សេនត",
    "sending": "សេនឌីង",
    "receive": "រីស៊ីវ",
    "receives": "រីស៊ីវស៍",
    "received": "រីស៊ីវដ៍",
    "listen": "លីសសិន",
    "listens": "លីសសិនស៍",
    "listened": "លីសសិន",
    "listening": "លីសសិននីង",
    "hear": "ហ៊ីយែរ",
    "hears": "ហ៊ីយែរ",
    "heard": "ហើត",
    "speak": "ស្ពីក",
    "speaks": "ស្ពីកស៍",
    "spoke": "ស្ពូក",
    "spoken": "ស្ពូខិន",
    "speaking": "ស្ពីឃីង",
    "speaker": "ស្ពីកខ័រ",
    "talk": "ថក",
    "talks": "ថកស៍",
    "talked": "ថក",
    "talking": "ថកឃីង",

    # Common Everyday Adjectives & Adverbs
    "good": "ហ្គូដ",
    "better": "បេតធ័រ",
    "best": "បេស្ត",
    "bad": "ប៊ែត",
    "worse": "វើស",
    "worst": "វើសត",
    "nice": "ណាយស៍",
    "cool": "ឃូល",
    "great": "ហ្គ្រេត",
    "fine": "ហ្វាញ",
    "ok": "អូខេ",
    "okay": "អូខេ",
    "big": "ប៊ីក",
    "small": "ស្មល",
    "large": "ឡាច",
    "little": "លីថល",
    "long": "ឡង",
    "short": "សត",
    "high": "ហាយ",
    "low": "ឡូ",
    "new": "ញូវ",
    "old": "អូលដ៍",
    "fast": "ហ្វាសត",
    "slow": "ស្លូ",
    "easy": "អ៊ីស៊ី",
    "hard": "ហាដ",
    "clear": "ឃ្លៀ",
    "real": "រីល",
    "really": "រីលី",
    "very": "វ៉េរី",
    "much": "ម៉ាត់ឆ៍",
    "many": "មេនី",
    "more": "ម៉រ",
    "most": "ម៉ូសត",
    "all": "អល",
    "some": "សាំ",
    "any": "អ៊េនី",
    "every": "អ៊េវរី",
    "each": "អ៊ិច",
    "both": "បូត",
    "few": "ហ្វ្យូ",
    "other": "អាដ័រ",
    "another": "អឹណាដ័រ",
    "same": "សេម",
    "different": "ឌីហ្វរ៉ិន",
    "sure": "សួរ",
    "maybe": "មេប៊ី",
    "always": "អលវេស",
    "never": "ណេវ៉ា",
    "sometimes": "សាំថាមស៍",
    "often": "អូហ្វិន",
    "usually": "យូហ្សួលី",
    "now": "ណាវ",
    "today": "ធូដេ",
    "tomorrow": "ធូម៉ូរ៉ូ",
    "yesterday": "យេសស្តឺដេ",
    "soon": "ស៊ូន",
    "later": "ឡេធ័រ",
    "again": "អឺហ្គេន",
    "here": "ហ៊ីយែរ",
    "there": "ដ៊ែរ",
    "together": "ធូហ្គេតឌ័រ",
    "already": "អលរ៉េឌី",
    "still": "ស្តៀល",
    "almost": "អលម៉ូសត",
    "enough": "អ៊ីណាហ៊្វ",
    "ready": "រ៉េឌី",
    "done": "ដាន់",
    "complete": "ខមផ្លីត",
    "finish": "ហ្វីនីស",
    "success": "សាក់សេស",
    "fail": "ហ្វេល",

    # Common Everyday Nouns
    "time": "ថាម",
    "times": "ថាមស៍",
    "day": "ដេ",
    "days": "ដេស",
    "week": "វីក",
    "weeks": "វីកស៍",
    "month": "ម៉ាន",
    "months": "ម៉ានស៍",
    "year": "យា",
    "years": "យាស",
    "morning": "ម៉ូនិញ",
    "afternoon": "អាហ្វធើនូន",
    "evening": "អ៊ីវនីង",
    "night": "ណាយ",
    "life": "ឡាយហ្វ",
    "people": "ភីផល",
    "person": "ភើសិន",
    "man": "មែន",
    "men": "មេន",
    "woman": "វូមែន",
    "women": "វីមិន",
    "child": "ឆាលដ៍",
    "children": "ឈីលដ្រិន",
    "friend": "ហ្វ្រេន",
    "friends": "ហ្វ្រេនស៍",
    "brother": "ប្រាឌ័រ",
    "sister": "ស៊ីសស្ទ័រ",
    "bro": "ប្រូ",
    "sis": "ស៊ីស",
    "guy": "ហ្គាយ",
    "guys": "ហ្គាយស៍",
    "boy": "ប៊យ",
    "girl": "ហ្គើល",
    "family": "ហ្វេមីលី",
    "home": "ហូម",
    "house": "ហោស",
    "school": "ស្គូល",
    "team": "ធីម",
    "group": "គ្រុប",
    "world": "វើលដ៍",
    "country": "ខាន់ទ្រី",
    "city": "ស៊ីធី",
    "place": "ផ្លេស",
    "way": "វេ",
    "part": "ផាត",
    "side": "សាយដ៍",
    "point": "ភ័ញ",
    "case": "ខេស",
    "thing": "ធីង",
    "things": "ធីងស៍",
    "something": "សាំធីង",
    "anything": "អ៊េនីធីង",
    "nothing": "ណាធីង",
    "everything": "អ៊េវរីធីង",
    "someone": "សាំវ៉ាន់",
    "anyone": "អ៊េនីវ៉ាន់",
    "everyone": "អ៊េវរីវ៉ាន់",
    "problem": "ប្រូប្លឹម",
    "problems": "ប្រូប្លឹមស៍",
    "question": "ខ្វេសឆិន",
    "questions": "ខ្វេសឆិនស៍",
    "answer": "អានស័រ",
    "answers": "អានស័រ",
    "idea": "អាយឌា",
    "ideas": "អាយឌាស",
    "job": "ចប់",
    "jobs": "ចប់ស៍",
    "name": "ណេម",
    "names": "ណេមស៍",
    "number": "ណាំប៊័រ",
    "numbers": "ណាំប៊័រ",
    "reason": "រីសិន",
    "story": "ស្តូរី",
    "fact": "ហ្វេក",

    # Tech & Software Terminology
    "computer": "កុំព្យូទ័រ",
    "software": "សូហ្វវែរ",
    "hardware": "ហាដវែរ",
    "developer": "ឌីវេឡុបភ័រ",
    "developers": "ឌីវេឡុបភ័រ",
    "development": "ឌីវេឡុបមិន",
    "develop": "ឌីវេឡុប",
    "programmer": "ប្រូក្រាមម័រ",
    "programming": "ប្រូក្រាមមីង",
    "program": "ប្រូក្រាម",
    "programs": "ប្រូក្រាម",
    "code": "កូដ",
    "coder": "កូដឌ័រ",
    "coding": "កូដឌីង",
    "system": "ស៊ីស្ទឹម",
    "systems": "ស៊ីស្ទឹមស៍",
    "file": "ហ្វាល់",
    "files": "ហ្វាល់ស៍",
    "folder": "ហ្វូលឌ័រ",
    "folders": "ហ្វូលឌ័រ",
    "data": "ដាតា",
    "database": "ដាតាបេស",
    "server": "ស៊ើវវ័រ",
    "servers": "ស៊ើវវ័រ",
    "cloud": "ខ្លោដ",
    "network": "ណេតវើក",
    "internet": "អ៊ីនធឺណែត",
    "web": "វេប",
    "website": "វេបសាយ",
    "app": "អែប",
    "apps": "អែបស៍",
    "application": "អែបភ្លីខេសិន",
    "applications": "អែបភ្លីខេសិន",
    "download": "ដោនឡូត",
    "upload": "អាប់ឡូត",
    "update": "អាប់ដេត",
    "updates": "អាប់ដេត",
    "upgrade": "អាប់ហ្គ្រេត",
    "install": "អ៊ីនស្តូល",
    "installation": "អ៊ីនស្តូលឡេសិន",
    "edit": "អេឌីត",
    "editor": "អេឌីធ័រ",
    "copy": "ខបភី",
    "paste": "ផេស",
    "cut": "ខាត់",
    "click": "ឃ្លីក",
    "button": "ប៊ូតុង",
    "buttons": "ប៊ូតុង",
    "screen": "ស្គ្រីន",
    "screens": "ស្គ្រីន",
    "window": "វីនដូ",
    "windows": "វីនដូ",
    "page": "ផេក",
    "pages": "ផេកស៍",
    "login": "ឡុកអ៊ិន",
    "logout": "ឡុកអាវត",
    "sign in": "សាញ អ៊ិន",
    "sign out": "សាញ អាវត",
    "password": "ផាសវើត",
    "user": "យូស័រ",
    "users": "យូស័រ",
    "account": "អាក់ខោន",
    "accounts": "អាក់ខោន",
    "email": "អ៊ីម៉ែល",
    "message": "មេសសេច",
    "messages": "មេសសេចស៍",
    "chat": "ឆាត",
    "post": "ផូស្ត",
    "comment": "ខមមិន",
    "share": "ស៊ែ",
    "link": "លីងក៍",
    "links": "លីងក៍",
    "online": "អនឡាញ",
    "offline": "អហ្វឡាញ",
    "camera": "ខាមេរ៉ា",
    "photo": "ហ្វូតូ",
    "picture": "ភីកឈ័រ",
    "image": "អ៊ីមេច",
    "images": "អ៊ីមេចស៍",
    "music": "ម្ញូស៊ីក",
    "song": "សង",
    "game": "ហ្គេម",
    "games": "ហ្គេមស៍",
    "format": "ហ្វរម៉ាត",
    "mp3": "អិមភីស្រ៊ី",
    "wav": "វ៉េវ",
    "export": "អិចស្ព័ត",
    "exports": "អិចស្ព័ត",
    "import": "អ៊ីមស្ព័ត",
    "imports": "អ៊ីមស្ព័ត",
    "settings": "សេតធីងស៍",
    "options": "អបសិន",
    "preset": "ព្រីសេត",
    "presets": "ព្រីសេតស៍",
    "auto": "អូតូ",
    "manual": "ម៉ានូអែល",
    "mode": "ម៉ូដ",
    "modes": "ម៉ូដស៍",
    "device": "ឌីវ៉ាយស៍",
    "devices": "ឌីវ៉ាយស៍",
    "memory": "មេម៉ូរី",
    "storage": "ស្តូរ៉េច",
    "cache": "ខេស",
    "speed": "ស្ពីដ",
    "status": "ស្តេតឹស",
    "error": "អេរ័រ",
    "errors": "អេរ័រ",
    "bug": "បាក់",
    "bugs": "បាក់ស៍",
    "crash": "ក្រាស",
    "fix": "ហ្វិកស៍",
    "fixed": "ហ្វិកស៍",
    "fixes": "ហ្វិកស៍",
    "tool": "ធូល",
    "tools": "ធូលស៍",
    "neural": "ញូ feed រ៉ល",
    "model": "ម៉ូដែល",
    "models": "ម៉ូដែលស៍",
    "version": "វើហ្សិន",
    "versions": "វើហ្សិន",
    "step": "ស្តេប",
    "steps": "ស្តេបស៍",
    "level": "ឡេវែល",
    "levels": "ឡេវែល",
    "volume": "វ៉ុលល្យូម",
    "track": "ត្រែក",
    "tracks": "ត្រែកស៍",
    "font": "ហ្វុន",
    "fonts": "ហ្វុន",
    "size": "សាយស៍",
    "color": "ខលលើ",
    "style": "ស្តាយ",
    "design": "ឌីហ្សាញ",
    "phone": "ហ្វូន",
    "laptop": "ឡេបថប",
    "tablet": "ថេប្លេត",
    "keyboard": "ឃីបត",
    "mouse": "ម៉ៅស៍",
    "wifi": "វ៉ាយហ្វាយ",
    "bluetooth": "ប៊្លូធូស",
    "usb": "យូអេសប៊ី",
    "temp": "ថេម",
    "backup": "ប៊ែកអាប់",
    "log": "ឡុក",
    "logs": "ឡុកស៍",

    # Acronyms & Brands
    "ai": "អេអាយ",
    "api": "អេភីអាយ",
    "cpu": "ស៊ីភីយូ",
    "gpu": "ជីភីយូ",
    "ram": "រ៉េម",
    "rom": "រ៉ូម",
    "vram": "វីរ៉េម",
    "os": "អូអេស",
    "ios": "អាយអូអេស",
    "mac": "ម៉េក",
    "macos": "ម៉េកអូអេស",
    "linux": "លីនុច",
    "ubuntu": "អ៊ូប៊ុនទូ",
    "debian": "ដេបៀន",
    "android": "អេនដ្រយ",
    "google": "ហ្គូហ្គល",
    "meta": "មេតា",
    "facebook": "ហ្វេសប៊ុក",
    "youtube": "យូធូប",
    "tiktok": "ធីកថុក",
    "telegram": "តេឡេក្រាម",
    "chatgpt": "ឆាតជីភីធី",
    "python": "ផាយថុន",
    "html": "អេចធីអិមអែល",
    "css": "ស៊ីអេសអេស",
    "js": "ជេអេស",
    "javascript": "ចាវ៉ាស្គ្រីប",
    "react": "រីអាក់",
    "node": "ណូត",
    "ffmpeg": "អែហ្វអែហ្វអិមភីក",
    "tts": "ធីធីអេស",
    "asr": "អេអេសអា",
    "vits": "វីតស៍",
    "mms": "អិមអិមអេស",
    "hf": "អេចអែហ្វ",
    "huggingface": "ហាក់ហ្គីងហ្វេស",
    "torch": "ថច",
    "pytorch": "ផាយថច",
    "cuda": "ឃូដា",
    "pc": "ភីស៊ី",
    "tv": "ធីវី",
    "hd": "អេចឌី",
    "4k": "ហ្វ័រខេ",
    "sdk": "អេសឌីខេ",
    "cli": "ស៊ីអិលអាយ",
    "gui": "ជីយូអាយ",
    "url": "យូអ័រអែល",
    "http": "អេចធីធីភី",
    "https": "អេចធីធីភីអេស",
    "ip": "អាយភី",
    "lan": "ឡែន",
    "vpn": "វីភីអិន",
    "id": "អាយឌី",
    "pdf": "ភីឌីអែហ្វ",
    "sms": "អេសអិមអេស",
    "qr": "ឃ្យូអា",
    "sim": "ស៊ីម",

    # Web Development, Backend & Database
    "php": "ភីអេចភី",
    "backend": "ប៊ែកអ៊ែន",
    "frontend": "ហ្វ្រុនអ៊ែន",
    "fullstack": "ហ្វូលស្តេក",
    "website": "វេបសាយ",
    "web": "វេប",
    "database": "ដាតាបេស",
    "register": "រ៉េជីស្ទ័រ",
    "registration": "រ៉េជីស្ដ្រេសិន",
    "login": "ឡុកអ៊ិន",
    "logout": "ឡុកអាវត",
    "signup": "សាញអាប់",
    "signin": "សាញអ៊ិន",
    "signout": "សាញអាវត",
    "system": "ស៊ីស្ទឹម",
    "systems": "ស៊ីស្ទឹម",
    "programming": "ប្រូក្រាមមីង",
    "program": "ប្រូក្រាម",
    "programs": "ប្រូក្រាម",
    "language": "ឡេងហ្គ្វិច",
    "languages": "ឡេងហ្គ្វិច",
    "code": "កូដ",
    "coding": "កូដឌីង",
    "developer": "ឌីវេឡុបភ័រ",
    "developers": "ឌីវេឡុបភ័រ",
    "development": "ឌីវេឡុបមិន",
    "software": "សូហ្វវែរ",
    "hardware": "ហាតវែរ",
    "engineer": "អ៊ិនជីនៀ",
    "engineering": "អ៊ិនជីនៀររីង",
    "framework": "ហ្វ្រេមវើក",
    "library": "ឡាយប្រឺរី",
    "libraries": "ឡាយប្រឺរី",
    "server": "ស៊ើវើ",
    "servers": "ស៊ើវើ",
    "client": "ខ្លាយអិន",
    "clients": "ខ្លាយអិន",
    "cloud": "ខ្លោដ",
    "account": "អាខោន",
    "accounts": "អាខោន",
    "profile": "ប្រូហ្វាល់",
    "profiles": "ប្រូហ្វាល់",
    "password": "ផាសវើត",
    "user": "យូស៊ើ",
    "users": "យូស៊ើ",
    "admin": "អាតមីន",
    "page": "ផេក",
    "pages": "ផេក",
    "dashboard": "ដាសបត",
    "settings": "សេតធីង",
    "token": "ថូខិន",
    "session": "សេសសិន",
    "cookie": "ឃុកឃី",
    "cache": "ខាស",
    "api": "អេភីអាយ",
    "apis": "អេភីអាយ",
    "sql": "អេសឃ្យូអែល",
    "mysql": "ម៉ាយអេសឃ្យូអែល",
    "postgresql": "ភូសហ្គ្រេសអេសឃ្យូអែល",
    "mongodb": "ម៉ុងហ្គោឌីប៊ី",
    "sqlite": "អេសឃ្យូឡាយ",
    "redis": "រ៉េឌីស",
    "git": "ហ្គីត",
    "github": "ហ្គីតហាប់",
    "gitlab": "ហ្គីតឡាប",
    "branch": "ប្រេនឆ៍",
    "commit": "ខមមីត",
    "push": "ភូស",
    "pull": "ភូល",
    "merge": "មឺច",
    "repository": "រីផូស៊ីថូរី",
    "repo": "រីផូ",
    "rest": "រ៉េស",
    "json": "ជេសុន",
    "ajax": "អេជែក",
    "xml": "អិចអិមអែល",
    "java": "ចាវ៉ា",
    "c++": "ស៊ីផ្លាស់ផ្លាស់",
    "c#": "ស៊ីសាប",
    "typescript": "ថាយស្គ្រីប",
    "docker": "ដុកឃ័រ",
    "kubernetes": "គូបឺណេធីស",
    "nginx": "អ៊ិនជីនអិច",
    "apache": "អាប៉ាឈី",
    "function": "ហ្វាំងសិន",
    "functions": "ហ្វាំងសិន",
    "variable": "វ៉ារៀរបល",
    "variables": "វ៉ារៀរបល",
    "class": "ខ្លាស",
    "classes": "ខ្លាស",
    "object": "អបជិក",
    "objects": "អបជិក",
    "array": "អារេ",
    "arrays": "អារេ",
    "string": "ស្ត្រីង",
    "strings": "ស្ត្រីង",
    "boolean": "ប៊ូលីន",
    "loop": "លូប",
    "condition": "ខុនឌីសិន",
    "error": "អ៊ែរ័រ",
    "errors": "អ៊ែរ័រ",
    "bug": "បាក់",
    "bugs": "បាក់",
    "debug": "ឌីបាក់",
    "test": "ថេស",
    "testing": "ថេសធីង",
    "deploy": "ឌីផ្លយ",
    "deployment": "ឌីផ្លយមិន",
    "table": "ថេបល",
    "tables": "ថេបល",
    "column": "ខូឡាំ",
    "columns": "ខូឡាំ",
    "row": "រ៉ូ",
    "rows": "រ៉ូ",
    "input": "អ៊ិនភុត",
    "output": "អាវតភុត",
    "button": "ប៊ូតុង",
    "buttons": "ប៊ូតុង",
    "form": "ហ្វម",
    "forms": "ហ្វម",
    "click": "ឃ្លីក",
    "submit": "សាប់មីត",
    "cancel": "ខេនសល",
    "save": "សេវ",
    "edit": "អេឌីត",
    "delete": "ឌីលីត",
    "update": "អាប់ដេត",
    "create": "គ្រីអេត",
    "search": "សឺច",
    "filter": "ហ្វីលធ័រ",
    "upload": "អាប់ឡូត",
    "download": "ដោនឡូត",
    "file": "ហ្វាល់",
    "files": "ហ្វាល់",
    "image": "អ៊ីមេក",
    "images": "អ៊ីមេក",
    "video": "វីដេអូ",
    "audio": "អូឌីយ៉ូ",
    "media": "មេឌា",
    "message": "មេសសេក",
    "messages": "មេសសេក",
    "chat": "ឆាត",
    "notification": "ណូធីហ្វីខេសិន",
    "notifications": "ណូធីហ្វីខេសិន",
    "security": "សេឃ្យូរីធី",
    "auth": "អូត",
    "authentication": "អូតែនធីខេសិន",
    "authorization": "អូថូរ៉ាយសេសិន",
    "permission": "ភើមីសិន",
    "role": "រ៉ូល",
    "roles": "រ៉ូល",
    "access": "អាក់សេស",
    "hash": "ហាស",
    "jwt": "ជេដាប់ប៊លយូធី",
}

# Pre-compile regex for dictionary loanwords (longest phrases and words matched first)
_SORTED_LOANWORDS = sorted(TECH_LOANWORDS.keys(), key=lambda k: (len(k.split()), len(k)), reverse=True)
_LOANWORDS_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _SORTED_LOANWORDS) + r")\b",
    re.IGNORECASE
)

# Khmer vowel mapping for initial dependent vowels to avoid illegal Unicode sequences
_INITIAL_VOWEL_MAP = {
    "ា": "អា",
    "ិ": "អ៊ិ",
    "ី": "អ៊ី",
    "ឹ": "អ៊ឹ",
    "ឺ": "អ៊ឺ",
    "ុ": "អ៊ុ",
    "ូ": "អ៊ូ",
    "ួ": "អួ",
    "ើ": "អើ",
    "ឿ": "អឿ",
    "ៀ": "អៀ",
    "េ": "អេ",
    "ែ": "អែ",
    "ៃ": "អៃ",
    "ោ": "អោ",
    "ៅ": "អៅ",
    "ាយ": "អាយ",
}

# G2P Rules for unknown English words
_CONSONANT_RULES: List[Tuple[str, str]] = [
    # Silent onsets
    ("kn", "ន"),
    ("wr", "រ"),
    ("ps", "ស"),
    # Trigraphs & Digraphs
    ("tch", "ច"),
    ("dge", "ជ"),
    ("str", "ស្ត្រ"),
    ("spr", "ស្ព្រ"),
    ("scr", "ស្គ្រ"),
    ("spl", "ស្ភ្ល"),
    ("chr", "គ្រ"),
    ("sch", "ស្ក"),
    ("sh", "ស"),
    ("ch", "ឆ"),
    ("th", "ដ"),
    ("ph", "ហ្វ"),
    ("wh", "វ"),
    ("qu", "ខ្វ"),
    ("ck", "ក"),
    ("ng", "ង"),
    ("gh", ""),
    # Blends
    ("sk", "ស្ក"),
    ("sc", "ស្ក"),
    ("sp", "ស្ព"),
    ("st", "ស្ត"),
    ("sm", "ស្ម"),
    ("sn", "ស្ន"),
    ("sl", "ស្ល"),
    ("sw", "ស្វ"),
    ("pr", "ព្រ"),
    ("br", "ប្រ"),
    ("tr", "ត្រ"),
    ("dr", "ដ្រ"),
    ("cr", "គ្រ"),
    ("gr", "ក្រ"),
    ("fr", "ហ្វ្រ"),
    ("pl", "ផ្ល"),
    ("bl", "ប្ល"),
    ("cl", "ក្ល"),
    ("gl", "ក្ល"),
    ("fl", "ហ្ល"),
    # Single Consonants
    ("b", "ប"),
    ("c", "ក"),
    ("d", "ដ"),
    ("f", "ហ្វ"),
    ("g", "ហ្គ"),
    ("h", "ហ"),
    ("j", "ជ"),
    ("k", "ខ"),
    ("l", "ល"),
    ("m", "ម"),
    ("n", "ន"),
    ("p", "ផ"),
    ("q", "ក"),
    ("r", "រ"),
    ("s", "ស"),
    ("t", "ថ"),
    ("v", "វ"),
    ("w", "វ"),
    ("x", "កស"),
    ("y", "យ"),
    ("z", "ហ្ស"),
]

_VOWEL_RULES: List[Tuple[str, str]] = [
    ("tion", "សិន"),
    ("sion", "សិន"),
    ("ment", "មិន"),
    ("ness", "ណេស"),
    ("able", "អេបល"),
    ("ible", "អេបល"),
    ("ight", "ាយ"),
    ("igh", "ាយ"),
    ("all", "អល"),
    ("ing", "អ៊ីង"),
    ("ee", "ី"),
    ("ea", "ី"),
    ("oo", "ូ"),
    ("ou", "ៅ"),
    ("ow", "ៅ"),
    ("ai", "េ"),
    ("ay", "េ"),
    ("oa", "ោ"),
    ("oi", "អយ"),
    ("oy", "អយ"),
    ("au", "អ"),
    ("aw", "អ"),
    ("ar", "អា"),
    ("er", "អ័រ"),
    ("ir", "អើ"),
    ("ur", "អើ"),
    ("or", "អ័រ"),
    ("a", "ា"),
    ("e", "េ"),
    ("i", "ី"),
    ("o", "ោ"),
    ("u", "៊ូ"),
]


def _ensure_initial_consonant(text: str) -> str:
    """
    Prevents invalid Khmer Unicode sequences where a dependent vowel (e.g. ី, េ, ា)
    appears without a base consonant. If found, attaches 'អ' as the base consonant.
    """
    if not text:
        return text
    for dep, indep in _INITIAL_VOWEL_MAP.items():
        if text.startswith(dep):
            return indep + text[len(dep):]
    return text


def transliterate_unknown_english_word(word: str) -> str:
    """
    Intelligent G2P phonetic transliteration of an unknown English word to Khmer script.
    Handles:
    - Acronyms (e.g. 'API' -> 'អេភីអាយ')
    - Magic Silent 'E' (e.g. 'like' -> 'ឡាយខ៍', 'make' -> 'មេក', 'time' -> 'ថាម')
    - Suffixes (-tion, -ment, -ing, -ed, -er, -ly)
    - Consonant digraphs & blends
    - Base consonant anchoring for initial vowels
    """
    cleaned = word.strip()
    if not cleaned:
        return ""

    # Acronyms (2 to 4 uppercase letters, e.g. SDK, LAN, RAM)
    if cleaned.isupper() and 2 <= len(cleaned) <= 4:
        spelled = [LETTER_NAMES.get(c.lower(), c) for c in cleaned]
        return "".join(spelled)

    lower = cleaned.lower()

    # Dictionary lookup (case-insensitive)
    if lower in TECH_LOANWORDS:
        return TECH_LOANWORDS[lower]

    # Handle Magic Silent 'E' (Vowel + Consonant + 'e' at end of word, e.g., 'like', 'make', 'time')
    # a_e -> េ, i_e -> ាយ, o_e -> ោ, u_e -> យូ
    m_cvce = re.match(r"^([bcdfghjklmnpqrstvwxyz]{0,3})([aeiou])([bcdfghjklmnpqrstvwxyz])e$", lower)
    if m_cvce:
        onset, v, coda = m_cvce.groups()
        onset_khmer = ""
        if onset:
            # Match onset consonant rules
            for rule_c, k_c in _CONSONANT_RULES:
                if onset == rule_c:
                    onset_khmer = k_c
                    break
            if not onset_khmer:
                onset_khmer = "".join(_CONSONANT_RULES[0][1] for _ in onset)  # fallback
        coda_khmer = ""
        for rule_c, k_c in _CONSONANT_RULES:
            if coda == rule_c:
                coda_khmer = k_c
                break

        if v == "a":
            res = (onset_khmer or "អ") + "េ" + coda_khmer
            return res
        elif v == "i":
            res = (onset_khmer or "អ") + "ាយ" + coda_khmer
            return res
        elif v == "o":
            res = (onset_khmer or "អ") + "ោ" + coda_khmer
            return res
        elif v == "u":
            res = (onset_khmer or "អ") + "យូ" + coda_khmer
            return res

    # Suffix extraction
    suffix_khmer = ""
    for suffix, k_rep in [
        ("tion", "សិន"), ("sion", "សិន"), ("ment", "មិន"), ("ness", "ណេស"),
        ("able", "អេបល"), ("ible", "អេបល"), ("ing", "អ៊ីង"), ("ed", "ដ៍"),
        ("ful", "ហ្វូល"), ("less", "ឡេស"), ("ly", "លី"), ("er", "អ័រ")
    ]:
        if lower.endswith(suffix) and len(lower) > len(suffix) + 1:
            stem = lower[:-len(suffix)]
            if stem in TECH_LOANWORDS:
                return TECH_LOANWORDS[stem] + k_rep
            suffix_khmer = k_rep
            lower = stem
            break

    # Grapheme-to-Phoneme sequential mapping
    res = ""
    i = 0
    n = len(lower)

    while i < n:
        matched = False
        # Try multi-char then single-char patterns
        for l_chars, k_char in _CONSONANT_RULES + _VOWEL_RULES:
            if lower.startswith(l_chars, i):
                res += k_char
                i += len(l_chars)
                matched = True
                break
        if not matched:
            i += 1

    full_res = res + suffix_khmer if res else word
    return _ensure_initial_consonant(full_res)


def normalize_khmer_typos(text: str) -> str:
    """
    Normalizes common Khmer keyboard typos and Unicode anomalies:
    1. Legacy Limon 'To + Coeng Ba' (\\u1791\\u17d2\\u1794) -> 'Lo' (\\u17a1).
       e.g. ស្រទ្បាញ់ -> ស្រឡាញ់, ឡាន -> ទ្បាន, ឡើង -> ទ្បើង.
    2. Consolidates duplicate diacritics / vowels (bantoc, nikahit, coeng).
    3. Normalizes zero-width spaces (\\u200b) around punctuation marks.
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


def normalize_numbers(text: str) -> str:
    """
    Converts Arabic numerals (0-9) and Khmer numerals (០-៩) into spoken Khmer words.
    Crucial for Meta MMS-TTS, which only has the '1' token and silently drops all other digits.
    """
    # 1. Convert Khmer digits ០-៩ to Arabic digits for uniform processing
    khmer_digits = "០១២៣៤៥៦៧៨៩"
    for i, kd in enumerate(khmer_digits):
        text = text.replace(kd, str(i))

    # 2. Convert numbers to spoken Khmer words
    def _sub_num(match: re.Match) -> str:
        num_str = match.group(0)
        return " " + number_to_khmer(num_str) + " "

    return re.sub(r"\b\d+\b", _sub_num, text)


def prepare_text_for_mms_khmer(text: str) -> str:
    """
    Prepares text for Meta MMS-TTS Khmer synthesis by:
    1. Normalizing Khmer keyboard typos and Unicode anomalies.
    2. Expanding numbers into spoken Khmer words.
    3. Transliterating English loanwords, conversational phrases, and acronyms
       into natural, phonetically accurate Khmer script.
    4. Ensuring seamless word boundaries and vowel anchoring so that
       English and Khmer speech mix together smoothly and naturally.
    """
    if not text:
        return ""

    # Step 0: Normalize Khmer keyboard typos
    text = normalize_khmer_typos(text)

    # Step 1: Normalize numbers to spoken Khmer
    text = normalize_numbers(text)

    # Step 2: Replace known dictionary loanwords and phrases (case-insensitive)
    def _loanword_sub(match: re.Match) -> str:
        key = match.group(0).lower()
        return TECH_LOANWORDS.get(key, match.group(0))

    text_transformed = _LOANWORDS_PATTERN.sub(_loanword_sub, text)

    # Step 3: Catch any remaining isolated English words or contractions
    def _fallback_sub(match: re.Match) -> str:
        w = match.group(0)
        # If already Khmer, leave untouched
        if re.search(r"[\u1780-\u17FF]", w):
            return w
        transliterated = transliterate_unknown_english_word(w)
        return transliterated if transliterated else w

    # Matches any remaining sequence of Latin letters or contractions (e.g. word's, user-friendly)
    text_transformed = re.sub(r"\b[A-Za-z]+(?:'[A-Za-z]+)?\b", _fallback_sub, text_transformed)

    # Step 4: Ensure clean spacing around Khmer text transitions
    # Insert clean space between Khmer character and transliterated word if missing
    text_transformed = re.sub(r"([\u1780-\u17FF])([A-Za-z])", r"\1 \2", text_transformed)
    text_transformed = re.sub(r"([A-Za-z])([\u1780-\u17FF])", r"\1 \2", text_transformed)
    # Collapse duplicate spaces
    text_transformed = re.sub(r"[ \t]+", " ", text_transformed).strip()

    return text_transformed


def split_bilingual_segments(text: str) -> List[Tuple[str, str]]:
    """
    Intelligently segments text into language-coherent blocks: list of (segment_text, 'km' | 'en').
    - Khmer text (with Khmer Unicode) is labeled 'km' (voiced natively by Meta MMS-TTS Khmer).
    - English text (with Latin letters) is labeled 'en' (voiced natively by Meta MMS-TTS English).
    Zero translation or transliteration needed: each language sounds 100% authentic and natural.
    """
    if not text or not text.strip():
        return []

    # Speakable Khmer characters: consonants \u1780-\u17A2, independent vowels \u17A3-\u17B3,
    # dependent vowels \u17B6-\u17C5, diacritics \u17C6-\u17D3, Khmer digits \u17E0-\u17E9
    khmer_speakable_pattern = r'[\u1780-\u17D3\u17E0-\u17E9]'
    has_km = bool(re.search(khmer_speakable_pattern, text))
    has_en = bool(re.search(r'[A-Za-z]', text))

    if has_km and not has_en:
        return [(text.strip(), "km")]
    if has_en and not has_km:
        return [(text.strip(), "en")]

    # Mixed text: split along language boundaries while preserving words & punctuation
    raw_tokens = re.findall(r'[\u1780-\u17FF\u19E0-\u19FF\u200b]+|[A-Za-z0-9\x27]+|[^\s\w]+|\s+', text)
    
    chunks = []
    curr_lang = None
    curr_buf = []

    for tok in raw_tokens:
        if not tok:
            continue
        is_km = bool(re.search(khmer_speakable_pattern, tok))
        is_en = bool(re.search(r'[A-Za-z]', tok))

        if is_km:
            target_lang = "km"
        elif is_en:
            target_lang = "en"
        else:
            # Punctuation / space / number -> associate with current active language
            target_lang = curr_lang or ("km" if has_km else "en")

        if curr_lang is None or target_lang == curr_lang:
            curr_buf.append(tok)
            curr_lang = target_lang
        else:
            chunk_str = "".join(curr_buf).strip()
            if chunk_str:
                chunks.append((chunk_str, curr_lang))
            curr_buf = [tok]
            curr_lang = target_lang

    if curr_buf:
        chunk_str = "".join(curr_buf).strip()
        if chunk_str:
            chunks.append((chunk_str, curr_lang))

    # Merge adjacent segments of the same language, and filter out any silent/empty chunks
    speakable_any_pattern = r'[\u1780-\u17D3\u17E0-\u17E9A-Za-z0-9]'
    merged: List[Tuple[str, str]] = []

    for s, l in chunks:
        s = s.strip()
        if not s:
            continue
        # If segment contains no speakable letters or digits, attach to previous chunk if possible
        if not re.search(speakable_any_pattern, s):
            if merged:
                merged[-1] = (merged[-1][0] + " " + s, merged[-1][1])
            continue

        if merged and merged[-1][1] == l:
            merged[-1] = (merged[-1][0] + " " + s, l)
        else:
            merged.append((s, l))

    return merged
