"""
KhmerTTS / Nesith TTS - Secure Credential Storage.
Provides OS-level secure storage for user Gemini API keys.
Strict security rules:
- Uses Windows DPAPI (CryptProtectData) or Windows Credential Manager / OS keyring.
- Never falls back to plaintext storage in JSON, SQLite, or plain files.
- Raises SecureStorageUnavailableError if secure OS storage cannot be accessed.
"""

import os
import sys
import ctypes
from typing import Optional


class SecureStorageError(Exception):
    """Base exception for secure storage operations."""
    pass


class SecureStorageUnavailableError(SecureStorageError):
    """Raised when no OS-level secure storage mechanism is functional."""
    pass


class WindowsDPAPI:
    """Native Windows Data Protection API (DPAPI) via ctypes."""

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.c_ulong),
            ("pbData", ctypes.POINTER(ctypes.c_byte))
        ]

    @classmethod
    def is_available(cls) -> bool:
        return sys.platform == "win32" and hasattr(ctypes, "windll") and hasattr(ctypes.windll, "crypt32")

    @classmethod
    def encrypt(cls, plaintext: str) -> bytes:
        if not cls.is_available():
            raise SecureStorageUnavailableError("Windows DPAPI is not available on this platform.")

        data_bytes = plaintext.encode("utf-8")
        blob_in = cls.DATA_BLOB()
        blob_in.cbData = len(data_bytes)
        blob_in.pbData = (ctypes.c_byte * len(data_bytes))(*data_bytes)

        blob_out = cls.DATA_BLOB()

        ret = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in),
            "NesithTTS_Gemini_Key",
            None,
            None,
            None,
            0,
            ctypes.byref(blob_out)
        )
        if not ret:
            raise SecureStorageError("Failed to encrypt API key with Windows DPAPI.")

        try:
            encrypted_bytes = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
            return encrypted_bytes
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)

    @classmethod
    def decrypt(cls, encrypted_bytes: bytes) -> str:
        if not cls.is_available():
            raise SecureStorageUnavailableError("Windows DPAPI is not available on this platform.")

        blob_in = cls.DATA_BLOB()
        blob_in.cbData = len(encrypted_bytes)
        blob_in.pbData = (ctypes.c_byte * len(encrypted_bytes))(*encrypted_bytes)

        blob_out = cls.DATA_BLOB()

        ret = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(blob_out)
        )
        if not ret:
            raise SecureStorageError("Failed to decrypt API key with Windows DPAPI.")

        try:
            decrypted_bytes = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
            return decrypted_bytes.decode("utf-8")
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)


class SecureKeyStorage:
    """
    Manages secure persistence of the user's Gemini API key.
    Prioritizes:
    1. Python `keyring` (Windows Credential Manager, SecretService, KWallet, macOS Keychain).
    2. Native Windows DPAPI (if on Windows and keyring is absent).
    Refuses plaintext fallback.
    """

    SERVICE_NAME = "NesithTTS"
    KEY_ACCOUNT = "gemini_api_key"

    def __init__(self, service_name: str = SERVICE_NAME, account_name: str = KEY_ACCOUNT):
        self.service_name = service_name
        self.account_name = account_name
        self._dpapi_file = os.path.expanduser(os.path.join("~", f".{service_name}_gemini.dpapi"))

    def is_secure_storage_available(self) -> bool:
        """Determines if a functional secure credential storage backend is reachable."""
        # 1. Check Python keyring
        try:
            import keyring
            backend = keyring.get_keyring()
            backend_cls = backend.__class__.__name__
            # Reject dummy or fail backends
            if "fail" not in backend_cls.lower() and "dummy" not in backend_cls.lower():
                return True
        except Exception:
            pass

        # 2. Check Windows DPAPI
        if WindowsDPAPI.is_available():
            return True

        return False

    def get_storage_backend_name(self) -> str:
        """Returns the human-readable name of the active secure storage mechanism."""
        try:
            import keyring
            backend = keyring.get_keyring()
            cls_name = backend.__class__.__name__
            if "fail" not in cls_name.lower() and "dummy" not in cls_name.lower():
                return f"OS Keyring ({cls_name})"
        except Exception:
            pass

        if WindowsDPAPI.is_available():
            return "Windows DPAPI (CryptProtectData)"

        return "None (Unavailable)"

    def _store_raw(self, api_key: str) -> bool:
        """Stores the secret into the available secure backend."""
        # Try keyring first
        try:
            import keyring
            backend = keyring.get_keyring()
            if "fail" not in backend.__class__.__name__.lower():
                keyring.set_password(self.service_name, self.account_name, api_key)
                return True
        except Exception:
            pass

        # Try Windows DPAPI
        if WindowsDPAPI.is_available():
            enc_data = WindowsDPAPI.encrypt(api_key)
            with open(self._dpapi_file, "wb") as f:
                f.write(enc_data)
            return True

        raise SecureStorageUnavailableError(
            "OS-level secure credential storage is unavailable on this machine. "
            "To safeguard your secrets, plaintext fallback is disallowed. "
            "Please ensure Windows Credential Manager, DPAPI, or an OS keyring daemon is active."
        )

    def _retrieve_raw(self) -> Optional[str]:
        """Retrieves the secret from the secure backend."""
        # Try keyring first
        try:
            import keyring
            backend = keyring.get_keyring()
            if "fail" not in backend.__class__.__name__.lower():
                val = keyring.get_password(self.service_name, self.account_name)
                if val:
                    return val
        except Exception:
            pass

        # Try Windows DPAPI
        if WindowsDPAPI.is_available() and os.path.exists(self._dpapi_file):
            with open(self._dpapi_file, "rb") as f:
                enc_data = f.read()
            if enc_data:
                return WindowsDPAPI.decrypt(enc_data)

        return None

    def _delete_raw(self) -> bool:
        """Deletes the secret from the secure backend."""
        deleted = False
        try:
            import keyring
            keyring.delete_password(self.service_name, self.account_name)
            deleted = True
        except Exception:
            pass

        if os.path.exists(self._dpapi_file):
            try:
                os.remove(self._dpapi_file)
                deleted = True
            except Exception:
                pass

        return deleted

    def save_api_key(self, api_key: str) -> bool:
        """
        Securely saves the Gemini API key.
        Validates input before saving and strictly avoids plaintext leaks.
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty or whitespace.")

        cleaned_key = api_key.strip().strip('"\'').strip()
        if cleaned_key.startswith("Bearer "):
            cleaned_key = cleaned_key[7:].strip()

        if not self.is_secure_storage_available():
            raise SecureStorageUnavailableError(
                "Secure storage is unavailable on this system. "
                "Storing keys in unencrypted plaintext is strictly disabled."
            )

        return self._store_raw(cleaned_key)

    def get_api_key(self) -> Optional[str]:
        """Retrieves the stored Gemini API key if present."""
        return self._retrieve_raw()

    def has_api_key(self) -> bool:
        """Returns True if a key is stored and non-empty."""
        key = self.get_api_key()
        return bool(key and key.strip())

    def delete_api_key(self) -> bool:
        """Deletes the stored Gemini API key."""
        return self._delete_raw()


# Global default instance
secure_storage = SecureKeyStorage()
