# security/crypto.py
# CORREÇÃO CIRÚRGICA: Cache de Fernet + validação de chave na primeira inicialização
"""Criptografia local para senhas usando Fernet (symmetric encryption)."""

from __future__ import annotations

import gc
import os
import logging

from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

# CORREÇÃO CIRÚRGICA: Singleton interno para cache da instância Fernet
_fernet_instance: Fernet | None = None


def _secure_delete(data: bytes) -> None:
    """
    Limpa referências a bytes sensíveis para permitir coleta de lixo.

    SEC-001: Previne key material de permanecer em memória indefinidamente.
    CORREÇÃO: Removida tentativa insegura de sobrescrever memória imutável com ctypes.
    Python bytes são imutáveis e id(obj) não é um ponteiro seguro para o buffer.
    Apenas limpamos a referência e forçamos GC.

    Args:
        data: Bytes a serem descartados (não usado diretamente)
    """
    if not data:
        return
    try:
        # Força coleta de lixo para liberar memória de objetos não referenciados
        # Nota: Para zeros reais, usaríamos bytearray + memoryview, mas aqui
        # a chave já está em bytes imutáveis do Fernet, então apenas liberamos
        del data
        gc.collect()
    except Exception as exc:
        log.warning("Falha ao liberar memória sensível: %s", exc)


def _reset_fernet_cache() -> None:
    """
    Limpa o cache singleton da instância Fernet.
    USO EXCLUSIVO PARA TESTES.
    """
    global _fernet_instance
    if _fernet_instance is not None:
        # Tenta limpar key material antes de descartar
        try:
            key_bytes = _fernet_instance._signing_key + _fernet_instance._encryption_key
            _secure_delete(key_bytes)
        except Exception as exc:  # noqa: BLE001
            # Logging mínimo: falha na limpeza de memória não é crítica
            log.debug("Falha ao limpar key material do Fernet: %s", type(exc).__name__)
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
        # SEC-007: Mascara chave na mensagem de erro (com proteção para objetos sem len)
        try:
            masked_key = "***" if not key_str else f"{key_str[:4]}...{key_str[-4:]}" if len(key_str) > 12 else "***"
        except (TypeError, AttributeError):
            masked_key = "***"

        raise RuntimeError(
            f"RC_CLIENT_SECRET_KEY tem formato inválido para Fernet (deve ser base64 de 44 caracteres). "
            f"Chave fornecida (mascarada): {masked_key}"
        ) from e


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
    Se token for None, vazio ou inválido, retorna string vazia.

    TEST-001: Retorna "" para tokens malformados ao invés de lançar exceção.
    """
    if not token:
        return ""
    try:
        f = _get_fernet()
        decrypted = f.decrypt(token.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception as e:
        log.warning("Token inválido ou corrompido: %s", e)
        return ""
