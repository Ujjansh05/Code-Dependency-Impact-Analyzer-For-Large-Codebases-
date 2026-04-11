"""API Key encryption using fernet/AES-128-CBC."""

import os
from pathlib import Path

try:
    from cryptography.fernet import Fernet
except ImportError:
    # If cryptography is not installed (e.g. basic install), just pass through.
    Fernet = None

KEY_DIR = os.path.join(Path.home(), ".graphxploit")
KEY_FILE = os.path.join(KEY_DIR, "master.key")

_fernet: Fernet | None = None
_fernet_initialized = False


def _init_fernet():
    global _fernet, _fernet_initialized
    if _fernet_initialized:
        return
    _fernet_initialized = True

    if Fernet is None:
        return

    os.makedirs(KEY_DIR, exist_ok=True)
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        # Secure the file as much as possible on creation
        try:
            fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(key)
        except Exception:
            with open(KEY_FILE, "wb") as f:
                f.write(key)

    try:
        with open(KEY_FILE, "rb") as f:
            key = f.read().strip()
        _fernet = Fernet(key)
    except Exception:
        pass


def encrypt(plain_text: str) -> str:
    """Encrypt a string. If crypto is not available, returns the input."""
    if not plain_text:
        return ""
    _init_fernet()
    if _fernet is None:
        return plain_text

    try:
        # Check if already encrypted to avoid double encryption.
        if plain_text.startswith("ENC:"):
            return plain_text
        encrypted = _fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")
        return f"ENC:{encrypted}"
    except Exception:
        return plain_text


def decrypt(cipher_text: str) -> str:
    """Decrypt a string. If crypto is not available or it's unencrypted, returns input."""
    if not cipher_text:
        return ""
    
    if not cipher_text.startswith("ENC:"):
        return cipher_text

    _init_fernet()
    if _fernet is None:
        return cipher_text

    try:
        raw = cipher_text[4:]
        decrypted = _fernet.decrypt(raw.encode("utf-8")).decode("utf-8")
        return decrypted
    except Exception:
        # If decryption fails (e.g., key changed), it might return the garbled/empty or crash.
        # We will just return empty to prevent returning raw encrypted string.
        return ""
