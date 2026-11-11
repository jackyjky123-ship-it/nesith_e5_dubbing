"""
KhmerTTS - Comprehensive 50+ Benchmark Sentences & Automated Test Suite.
Validates English pronunciation improvements, language-aware preprocessing,
custom pronunciation dictionary overrides, and synthesis stability with Meta MMS-TTS Khmer.
Categories:
1. Pure Khmer (10 sentences) - verifies zero alteration of native Khmer text.
2. Pure English (10 sentences) - verifies phonetic conversion into authentic Khmer script.
3. Khmer with English technical words (10 sentences) - verifies code-switching and IT terminology.
4. Khmer with abbreviations & acronyms (10 sentences) - verifies letter-by-letter acronym voicing.
5. Khmer with numbers and brand names (10 sentences) - verifies alphanumeric, currency, and brand names.
"""

import os
import sys
import unittest
import numpy as np
import soundfile as sf

# Enforce offscreen Qt platform for testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from core.config import (
    MODELS_DIR, TEMP_DIR, EXPORTS_DIR, load_config
)
from core.pronunciation_dict import (
    load_user_dictionary, save_user_dictionary, add_user_pronunciation,
    remove_user_pronunciation, get_user_dictionary_path
)
from core.khmer_phonetics import (
    prepare_text_for_mms_khmer, transliterate_unknown_english_word,
    normalize_khmer_typos, normalize_numbers, TECH_LOANWORDS
)
from core.tts_engine import tts_manager, TTSResult, is_khmer_text

BENCHMARK_CATEGORIES = {
    "1_pure_khmer": [
        "សួស្តីបងប្អូនទាំងអស់គ្នា សូមស្វាគមន៍មកកាន់កម្មវិធីរបស់យើង។",
        "ថ្ងៃនេះអាកាសធាតុល្អណាស់ នៅរាជធានីភ្នំពេញ។",
        "ការអប់រំគឺជាគ្រឹះដ៏រឹងមាំបំផុតសម្រាប់ការអភិវឌ្ឍប្រទេសជាតិ។",
        "ខ្ញុំចូលចិត្តអានសៀវភៅ និងស្ដាប់តន្ត្រីនៅពេលទំនេរ។",
        "ប្រាសាទអង្គរវត្តជាសម្បត្តិបេតិកភណ្ឌពិភពលោកដ៏ល្បីល្បាញ។",
        "ទន្លេមេគង្គហូរកាត់ប្រទេសកម្ពុជាផ្តល់នូវធនធានធម្មជាតិយ៉ាងច្រើន។",
        "ម្ហូបខ្មែរមានរសជាតិឆ្ងាញ់និងមានប្រវត្តិយូរលង់ណាស់មកហើយ។",
        "យើងត្រូវរួមគ្នាថែរក្សាបរិស្ថាននិងដាំដើមឈើឱ្យបានច្រើន។",
        "សូមជូនពរឱ្យអ្នកទទួលបានជោគជ័យគ្រប់ភារកិច្ច។",
        "ភាសាខ្មែរជាអត្តសញ្ញាណជាតិដែលយើងទាំងអស់គ្នាត្រូវការពារ។"
    ],
    "2_pure_english": [
        "Artificial Intelligence and Machine Learning are revolutionizing modern computer science.",
        "Welcome to the text to speech synthesis studio.",
        "React is a popular framework for building user interfaces.",
        "Python is an intuitive programming language for data analysis.",
        "Cloud computing provides scalable infrastructure for modern applications.",
        "Good morning and have a wonderful day.",
        "Thank you very much for your kind support.",
        "Software engineering requires continuous learning and problem solving.",
        "Docker simplifies software deployment across different servers.",
        "Cybersecurity is essential for protecting sensitive information."
    ],
    "3_khmer_technical_words": [
        "ថ្ងៃនេះខ្ញុំចង់រៀនអំពី Artificial Intelligence។",
        "កុំព្យូទ័រនេះប្រើ Framework React ជាមួយ JavaScript និង TypeScript។",
        "ប្រព័ន្ធ AI ដំណើរការលើ Cloud ដោយប្រើ Docker និង Kubernetes។",
        "គាត់ជា Senior Full Stack Developer ជំនាញ Backend Python និង FastAPI។",
        "ទិន្នន័យត្រូវបានរក្សាទុកក្នុង Database PostgreSQL និង MongoDB។",
        "យើងប្រើ Git សម្រាប់ Version Control និងគ្រប់គ្រង Source Code។",
        "ការរចនា UI និង UX ដ៏ល្អជួយឱ្យអ្នកប្រើប្រាស់ងាយស្រួលធ្វើការ។",
        "ម៉ូដែល Deep Learning នេះត្រូវការ Training នៅលើ Dataset ធំ។",
        "គេប្រើ Microservices Architecture ដើម្បីបង្កើតប្រព័ន្ធធំៗ។",
        "កម្មវិធីនេះដំណើរការ Asynchronous ដោយប្រើ Promise និង Async Await។"
    ],
    "4_khmer_abbreviations": [
        "ម៉ូដែល AI នេះប្រើ GPU និង CPU ល្បឿនលឿន។",
        "ប្រព័ន្ធ TTS នេះដំណើរការលើ PC ដោយមិនបាច់ភ្ជាប់ Internet។",
        "API និង SDK នេះគាំទ្រ HTTP, HTTPS និងទិន្នន័យ JSON។",
        "កុំព្យូទ័ររបស់ខ្ញុំមាន RAM 32GB និង SSD ប្រភេទ NVMe។",
        "សូមផ្ញើឯកសារជាទម្រង់ PDF ឬ PNG មកកាន់ Email របស់ខ្ញុំ។",
        "បច្ចេកវិទ្យា NLP ជួយឱ្យកុំព្យូទ័រយល់ភាសាមនុស្ស។",
        "ការតភ្ជាប់ប្រើខ្សែ HDMI និងរន្ធ USB Type C។",
        "គេប្រើ SSH និង VPN ដើម្បីចូលទៅកាន់ Remote Server។",
        "ប្រព័ន្ធនេះគាំទ្រទាំង IPv4 និង IPv6 តាមស្តង់ដារ TCP IP។",
        "ការងារ DevOps ផ្តោតលើ CI CD Pipeline និង Cloud Infrastructure។"
    ],
    "5_khmer_numbers_and_brands": [
        "គាត់បានទិញ iPhone 15 Pro Max នៅដើមឆ្នាំ 2024។",
        "ក្រុមហ៊ុន Google, Microsoft និង OpenAI កំពុងប្រកួតប្រជែងគ្នាលើ AI។",
        "ទូរស័ព្ទ Samsung Galaxy នេះគាំទ្រប្រព័ន្ធ 5G និង Wi-Fi 6។",
        "តម្លៃកុំព្យូទ័រ MacBook Pro នេះគឺ $1850 នៅលើទីផ្សារ។",
        "កុំព្យូទ័រ Dell និង Asus នេះមាន RAM 16GB និង SSD 512GB។",
        "ម៉ាស៊ីនបម្រើការនេះដំណើរការលើ Ubuntu 22.04 LTS។",
        "វីដេអូកម្រិត 4K និង 8K ត្រូវការ Memory Bandwidth ធំ។",
        "គាត់រៀន C++, C#, .NET, Node.js និង Next.js ជាមួយ Tailwind CSS។",
        "ការឆ្លងមេរោគ COVID-19 បានថយចុះយ៉ាងខ្លាំងនៅទូទាំងពិភពលោក។",
        "ក្រុមហ៊ុន Intel និង AMD បញ្ចេញបន្ទះឈីបជំនាន់ថ្មីដែលមាន 16 Cores។"
    ]
}


class TestPronunciationBenchmarks(unittest.TestCase):
    """Test suite covering the 50+ benchmark sentences and pronunciation pipeline."""

    def test_pure_khmer_preservation(self):
        """Verifies that pure Khmer sentences remain 100% unaltered."""
        for sentence in BENCHMARK_CATEGORIES["1_pure_khmer"]:
            prepared = prepare_text_for_mms_khmer(sentence)
            # Typos normalization may only clean ZWSP or consolidate diacritics
            expected = normalize_khmer_typos(sentence)
            self.assertEqual(
                prepared.replace(" ", ""),
                expected.replace(" ", ""),
                f"Pure Khmer text was modified: '{sentence}' -> '{prepared}'"
            )
            # Ensure no Latin letters were introduced
            import re
            self.assertFalse(bool(re.search(r"[a-zA-Z]", prepared)))

    def test_user_pronunciation_dictionary_overrides(self):
        """Verifies that custom user dictionary overrides take highest priority."""
        test_word = "XylophoneTesting"
        custom_pron = "ស៊ីឡូហ្វូន ថេសធីង"

        # Add custom pronunciation
        success = add_user_pronunciation(test_word, custom_pron)
        self.assertTrue(success)

        try:
            # Check custom pronunciation is applied
            test_phrase = f"ខ្ញុំចង់រៀនលេង {test_word} ណាស់។"
            prepared = prepare_text_for_mms_khmer(test_phrase)
            self.assertIn(custom_pron, prepared)
            self.assertNotIn(test_word, prepared)

            # Test case insensitivity
            test_phrase_lower = f"ខ្ញុំចង់រៀនលេង {test_word.lower()} ណាស់។"
            prepared_lower = prepare_text_for_mms_khmer(test_phrase_lower)
            self.assertIn(custom_pron, prepared_lower)

        finally:
            # Cleanup user pronunciation
            remove_user_pronunciation(test_word)

    def test_technical_terms_transliteration(self):
        """Verifies exact Khmer phonetic equivalents for mandated technical terms."""
        terms_map = {
            "Artificial Intelligence": "អាធីហ្វីសល អ៊ិនធែលលីជិន",
            "Computer": "កុំព្យូទ័រ",
            "Framework": "ហ្វ្រេមវើក",
            "JavaScript": "ចាវ៉ាស្គ្រីប",
            "React": "រីអាក់",
            "Machine Learning": "ម៉ាស៊ីន លើននីង",
            "Deep Learning": "ឌីប លើននីង",
            "Neural Network": "ញូរ៉ល ណេតវើក",
        }
        for eng, khmer_approx in terms_map.items():
            prep = prepare_text_for_mms_khmer(f"រៀន {eng} ថ្ងៃនេះ")
            self.assertIn(
                khmer_approx, prep,
                f"Expected '{khmer_approx}' in transliteration of '{eng}', got: '{prep}'"
            )

    def test_abbreviations_and_acronyms(self):
        """Verifies spelled-out phonetic pronunciation for common acronyms."""
        acronyms = {
            "AI": "អេអាយ",
            "CPU": "ស៊ីភីយូ",
            "GPU": "ជីភីយូ",
            "RAM": "រ៉េម",
            "TTS": "ធីធីអេស",
            "NLP": "អិនអែលភី",
            "API": "អេភីអាយ",
            "HTTP": "អេចធីធីភី",
            "JSON": "ជេសុន",
        }
        for acr, expected_khmer in acronyms.items():
            prep = prepare_text_for_mms_khmer(f"ប្រើប្រាស់ {acr}")
            self.assertIn(
                expected_khmer, prep,
                f"Expected '{expected_khmer}' for '{acr}', got: '{prep}'"
            )

    def test_numbers_and_brands(self):
        """Verifies proper expansion of alphanumeric patterns, brands, and currency."""
        samples = [
            ("ទិញ iPhone 15 Pro", ["អាយហ្វូន", "ដប់ប្រាំ", "ប្រូ"]),
            ("បច្ចេកវិទ្យា 5G និង Wi-Fi 6", ["ប្រាំ ជី", "វ៉ាយហ្វាយ", "ប្រាំមួយ"]),
            ("តម្លៃ $250", ["ពីររយ", "ហាសិប", "ដុល្លារ"]),
            ("មាន RAM 16GB", ["រ៉េម", "ដប់ប្រាំមួយ", "ជីហ្គាបៃត៍"]),
            ("ប្រើ GPT-4", ["ជីភីធី", "បួន"]),
            ("កូដ C++ និង Node.js", ["ស៊ី ផ្លាស ផ្លាស", "ណូដ ជេអេស"]),
        ]
        for input_text, expected_tokens in samples:
            prep = prepare_text_for_mms_khmer(input_text)
            for token in expected_tokens:
                self.assertIn(
                    token, prep,
                    f"Expected token '{token}' in '{prep}' for input '{input_text}'"
                )

    def test_all_50_sentences_transliteration(self):
        """Validates that all 50 benchmark sentences are completely transliterated into Khmer script."""
        import re
        total_count = 0
        for category, sentences in BENCHMARK_CATEGORIES.items():
            for s in sentences:
                total_count += 1
                prep = prepare_text_for_mms_khmer(s)
                self.assertIsNotNone(prep)
                self.assertGreater(len(prep), 0)
                # Assert NO English Latin characters remain in the preprocessed output
                latin_matches = re.findall(r"[a-zA-Z]", prep)
                self.assertEqual(
                    len(latin_matches), 0,
                    f"Untransliterated Latin letters {latin_matches} found in [{category}]: '{s}' -> '{prep}'"
                )
        self.assertEqual(total_count, 50, f"Expected exactly 50 benchmark sentences, got {total_count}")

    def test_synthesis_stability(self):
        """Verifies end-to-end synthesis stability on representative sentences across all categories."""
        test_samples = [
            BENCHMARK_CATEGORIES["1_pure_khmer"][0],
            BENCHMARK_CATEGORIES["2_pure_english"][0],
            BENCHMARK_CATEGORIES["3_khmer_technical_words"][0],
            BENCHMARK_CATEGORIES["4_khmer_abbreviations"][0],
            BENCHMARK_CATEGORIES["5_khmer_numbers_and_brands"][0],
        ]
        tts_manager._load_mms_khmer()
        bench_export_dir = os.path.join(EXPORTS_DIR, "benchmark_audio")
        os.makedirs(bench_export_dir, exist_ok=True)

        for i, sample in enumerate(test_samples, 1):
            res = tts_manager.synthesize(sample, keep_warm=True)
            self.assertIsInstance(res, TTSResult)
            self.assertGreater(res.duration_seconds, 0.5)
            self.assertEqual(res.sample_rate, 16000)
            self.assertGreater(len(res.audio_np), 8000)

            # Check no clipping
            max_amp = np.max(np.abs(res.audio_np))
            self.assertLessEqual(max_amp, 1.0)

            # Export audio
            out_file = os.path.join(bench_export_dir, f"category_{i}_sample.wav")
            success = tts_manager.export_audio(res.temp_wav_path, out_file, fmt="wav")
            self.assertTrue(success)
            self.assertTrue(os.path.exists(out_file))


if __name__ == "__main__":
    unittest.main()
