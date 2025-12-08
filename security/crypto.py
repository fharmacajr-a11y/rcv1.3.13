# security/crypto.py
# CORREÇÃO CIRÚRGICA: Cache de Fernet + validação de chave na primeira inicialização
"""Criptografia local para senhas usando Fernet (symmetric encryption)."""

from __future__ import annotations

import os
import logging

from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

# CORREÇÃO CIRÚRGICA: Singleton interno para cache da instância Fernet
_fernet_instance: Fernet | None = None


def _reset_fernet_cache() -> None:
    """
    Limpa o cache singleton da instância Fernet.
    USO EXCLUSIVO PARA TESTES.
    """
    global _fernet_instance
    _fernet_instance = None


def _get_fernet() -> Fernet:
    """
    Obtém (ou cria) a instância Fernet singleton com validação de chave.
    A chave RC_CLIENT_SECRET_KEY é lida do ambiente apenas uma vez.

    Raises:
        RuntimeError: Se a chave estiver ausente ou tiver formato inválido.
    """
    global _fernet_instance

    if _fernet_instance is not None:
        return _fernet_instance

    # CORREÇÃO CIRÚRGICA: Leitura e validação na primeira chamada
    key_str = os.getenv("RC_CLIENT_SECRET_KEY")
    if not key_str:
        raise RuntimeError("RC_CLIENT_SECRET_KEY não encontrada no .env. Defina uma chave Fernet válida (base64).")

    try:
        key_bytes = key_str.encode("utf-8")
        _fernet_instance = Fernet(key_bytes)
        return _fernet_instance
    except Exception as e:
        raise RuntimeError(
            f"RC_CLIENT_SECRET_KEY tem formato inválido para Fernet (deve ser base64 de 44 caracteres): {e}"
        )


def encrypt_text(plain: str | None) -> str:
    """
    Criptografa um texto usando Fernet.
    Retorna o token criptografado em base64 (str).
    Se plain for None ou vazio, retorna string vazia.
    """
    if not plain:
        return ""
    try:
        f = _get_fernet()
        encrypted = f.encrypt(plain.encode("utf-8"))
        return encrypted.decode("utf-8")
    except Exception as e:
        log.exception("Erro ao criptografar texto")
        raise RuntimeError(f"Falha na criptografia: {e}")


def decrypt_text(token: str | None) -> str:
    """
    Descriptografa um token Fernet.
    Retorna o texto original (str).
    Se token for None ou vazio, retorna string vazia.
    """
    if not token:
        return ""
    try:
        f = _get_fernet()
        decrypted = f.decrypt(token.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception as e:
        log.exception("Erro ao descriptografar token")
        raise RuntimeError(f"Falha na descriptografia: {e}")
