"""Encryption helpers for secrets persisted in the database."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


PREFIX = "enc:v1:"


def _fernet_for(secret):
    if not secret or secret == "development-secret-key":
        raise RuntimeError("A strong TOKEN_ENCRYPTION_KEY or SECRET_KEY is required.")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def _encryption_fernet(config):
    return _fernet_for(config.get("TOKEN_ENCRYPTION_KEY") or config.get("SECRET_KEY"))


def _decryption_fernets(config):
    values = [config.get("TOKEN_ENCRYPTION_KEY"), config.get("SECRET_KEY")]
    return [_fernet_for(value) for index, value in enumerate(values) if value and value not in values[:index]]


def encrypt_secret(config, value):
    if not value:
        return value
    if value.startswith(PREFIX):
        return value
    return PREFIX + _encryption_fernet(config).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(config, value):
    if not value or not value.startswith(PREFIX):
        # Backward compatibility: existing plaintext is encrypted on the next save.
        return value
    payload = value[len(PREFIX):].encode("ascii")
    for fernet in _decryption_fernets(config):
        try:
            return fernet.decrypt(payload).decode("utf-8")
        except InvalidToken:
            continue
    raise RuntimeError("Stored credential cannot be decrypted with the configured key.")
