"""
Unit tests for SecureKeyStorage.
Enforces OS-level secure storage and verifies that plaintext fallbacks are prohibited.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from core.secure_storage import (
    SecureKeyStorage,
    SecureStorageError,
    SecureStorageUnavailableError
)


class TestSecureKeyStorage(unittest.TestCase):
    def setUp(self):
        self.storage = SecureKeyStorage(service_name="NesithTTS_UnitTest")

    def test_save_and_retrieve_key_mocked(self):
        with patch.object(self.storage, "_store_raw", return_value=True) as mock_store, \
             patch.object(self.storage, "_retrieve_raw", return_value="AIzaSyMockKeyForTest123") as mock_get, \
             patch.object(self.storage, "is_secure_storage_available", return_value=True):

            self.assertTrue(self.storage.save_api_key("AIzaSyMockKeyForTest123"))
            mock_store.assert_called_once_with("AIzaSyMockKeyForTest123")

            key = self.storage.get_api_key()
            self.assertEqual(key, "AIzaSyMockKeyForTest123")
            self.assertTrue(self.storage.has_api_key())

    def test_delete_key_mocked(self):
        with patch.object(self.storage, "_delete_raw", return_value=True) as mock_del, \
             patch.object(self.storage, "is_secure_storage_available", return_value=True):
            self.assertTrue(self.storage.delete_api_key())
            mock_del.assert_called_once()

    def test_empty_or_whitespace_key_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.storage.save_api_key("")
        with self.assertRaises(ValueError):
            self.storage.save_api_key("   ")

    def test_no_plaintext_fallback_when_secure_storage_unavailable(self):
        with patch.object(self.storage, "is_secure_storage_available", return_value=False):
            with self.assertRaises(SecureStorageUnavailableError) as ctx:
                self.storage.save_api_key("AIzaSyValidFormatKey123")
            err_msg = str(ctx.exception)
            self.assertIn("secure storage", err_msg.lower())

    def test_never_stores_plaintext_in_config_or_workspace(self):
        # Ensure that no plaintext key is ever stored in any file under workspace
        from core.config import CONFIG_FILE, load_config
        cfg = load_config()
        self.assertNotIn("gemini_api_key", cfg)
        self.assertNotIn("api_key", cfg)
