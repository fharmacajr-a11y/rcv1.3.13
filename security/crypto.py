# security/crypto.py
"""Criptografia local para senhas usando Fernet (symmetric encryption)."""

from __future__ import annotations

import os
import logging

from cryptography.fernet import Fernet

log = logging.getLogger(__name__)


def _get_encryption_key() -> bytes:
    """
    Obtém a chave de criptografia do .env (RC_CLIENT_SECRET_KEY).
    A chave deve estar em formato base64 (gerada via Fernet.generate_key()).
    """
    key_str = os.getenv("RC_CLIENT_SECRET_KEY")
    if not key_str:
        raise RuntimeError("RC_CLIENT_SECRET_KEY não encontrada no .env. Defina uma chave Fernet válida (base64).")
    try:
        return key_str.encode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Erro ao processar RC_CLIENT_SECRET_KEY: {e}")


def encrypt_text(plain: str) -> str:
    """
    Criptografa um texto usando Fernet.
    Retorna o token criptografado em base64 (str).
    """
    if not plain:
        return ""
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(plain.encode("utf-8"))
        return encrypted.decode("utf-8")
    except Exception as e:
        log.exception("Erro ao criptografar texto")
        raise RuntimeError(f"Falha na criptografia: {e}")


def decrypt_text(token: str) -> str:
    """
    Descriptografa um token Fernet.
    Retorna o texto original (str).
    """
    if not token:
        return ""
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        decrypted = f.decrypt(token.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception as e:
        log.exception("Erro ao descriptografar token")
        raise RuntimeError(f"Falha na descriptografia: {e}")
