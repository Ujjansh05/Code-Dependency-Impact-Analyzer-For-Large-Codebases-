"""API Key encryption using Fernet (AES-128-CBC).

Encrypts sensitive values (API keys) at rest in ~/.graphxploit/models.json.
If the `cryptography` package is unavailable, values are stored in plaintext
and a visible warning is emitted.
"""

import logging
import os
import warnings
from pathlib import Path

logger = logging.getLogger("graphxploit.crypto")

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    Fernet = None
    InvalidToken = None
    warnings.warn(
        "graphxploit: 'cryptography' package is not installed. "
        "API keys will be stored WITHOUT encryption. "
        "Install it with:  pip install cryptography",
        UserWarning,
        stacklevel=2,
    )

KEY_DIR = os.path.join(Path.home(), ".graphxploit")
KEY_FILE = os.path.join(KEY_DIR, "master.key")

_fernet: "Fernet | None" = None
_fernet_initialized = False

# Tracks whether the user has already been warned about missing encryption
# during this process lifetime (avoids spamming the same warning).
_plaintext_warned = False


def is_encryption_available() -> bool:
    """Return True if encryption is operational."""
    _init_fernet()
    return _fernet is not None


def _init_fernet():
    global _fernet, _fernet_initialized
    if _fernet_initialized:
        return
    _fernet_initialized = True

    if Fernet is None:
        logger.warning("Encryption unavailable: cryptography package not installed")
        return

    os.makedirs(KEY_DIR, exist_ok=True)
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        try:
            fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(key)
        except OSError as e:
            logger.debug("Could not set POSIX permissions on key file: %s", e)
            with open(KEY_FILE, "wb") as f:
                f.write(key)

    try:
        with open(KEY_FILE, "rb") as f:
            key = f.read().strip()
        _fernet = Fernet(key)
    except (ValueError, OSError) as e:
        logger.error("Failed to initialize encryption from %s: %s", KEY_FILE, e)
        _fernet = None


def encrypt(plain_text: str) -> str:
    """Encrypt a string. If crypto is not available, returns the input with a warning."""
    if not plain_text:
        return ""
    _init_fernet()
    if _fernet is None:
        _warn_plaintext()
        return plain_text

    try:
        if plain_text.startswith("ENC:"):
            return plain_text
        encrypted = _fernet.encrypt(plain_text.encode("utf-8")).decode("utf-8")
        return f"ENC:{encrypted}"
    except (ValueError, TypeError) as e:
        logger.error("Encryption failed: %s", e)
        return plain_text


def decrypt(cipher_text: str) -> str:
    """Decrypt a string. If crypto is not available or it's unencrypted, returns input."""
    if not cipher_text:
        return ""

    if not cipher_text.startswith("ENC:"):
        return cipher_text

    _init_fernet()
    if _fernet is None:
        logger.warning("Cannot decrypt: encryption not available")
        return cipher_text

    try:
        raw = cipher_text[4:]
        decrypted = _fernet.decrypt(raw.encode("utf-8")).decode("utf-8")
        return decrypted
    except InvalidToken:
        logger.error(
            "Decryption failed: master key may have changed. "
            "Re-mount affected models with 'graphxploit model mount'."
        )
        return ""
    except (ValueError, TypeError) as e:
        logger.error("Decryption error: %s", e)
        return ""


def _warn_plaintext():
    """Emit a one-time warning that secrets will be stored in plaintext."""
    global _plaintext_warned
    if _plaintext_warned:
        return
    _plaintext_warned = True
    logger.warning(
        "Encryption is not available. API keys are stored in PLAINTEXT "
        "at %s. Install 'cryptography' to enable encryption.",
        os.path.join(KEY_DIR, "models.json"),
    )
