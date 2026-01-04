# security/crypto.py
# CORREÇÃO CIRÚRGICA: Cache de Fernet + validação de chave na primeira inicialização
# P1-002: Suporte a keyring para chave única por máquina
"""Criptografia local para senhas usando Fernet (symmetric encryption)."""

from __future__ import annotations

import gc
import os
import logging

from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

# CORREÇÃO CIRÚRGICA: Singleton interno para cache da instância Fernet
_fernet_instance: Fernet | None = None

# P1-002: Constantes para keyring
_KEYRING_SERVICE = "RC-Gestor-Clientes"
_KEYRING_USERNAME = "rc_client_secret_key"


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


def _keyring_is_available() -> bool:
    """
    Verifica se o keyring está disponível e utilizável.

    Retorna False se:
    - Estamos em ambiente de teste (RC_TESTING=1 ou PYTEST_CURRENT_TEST)
    - Import de keyring falha
    - Backend do keyring não está disponível

    Returns:
        bool: True se keyring pode ser usado, False caso contrário.
    """
    # Desabilita keyring em ambiente de teste
    if os.getenv("RC_TESTING") == "1" or "PYTEST_CURRENT_TEST" in os.environ:
        return False

    try:
        import keyring  # noqa: F401
        import keyring.backend

        backend = keyring.get_keyring()
        # Verifica se não é o backend "nulo" (fail/null)
        backend_name = backend.__class__.__name__.lower()
        if "fail" in backend_name or "null" in backend_name:
            log.warning("Keyring backend inválido: %s", backend.__class__.__name__)
            return False

        return True
    except Exception as exc:  # noqa: BLE001
        log.debug("Keyring não disponível: %s", exc)
        return False


def _keyring_get_secret_key() -> str | None:
    """
    Tenta recuperar a chave Fernet do Windows Credential Manager via keyring.

    Returns:
        str | None: Chave Fernet em base64, ou None se não encontrada/erro.
    """
    if not _keyring_is_available():
        return None

    try:
        import keyring

        key = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        if key:
            log.debug("Chave Fernet carregada do keyring com sucesso")
        return key
    except Exception as exc:  # noqa: BLE001
        log.warning("Erro ao ler chave do keyring: %s", exc)
        return None


def _keyring_set_secret_key(key: str) -> bool:
    """
    Armazena a chave Fernet no Windows Credential Manager via keyring.

    Args:
        key: Chave Fernet em base64 para armazenar.

    Returns:
        bool: True se sucesso, False se erro.
    """
    if not _keyring_is_available():
        return False

    try:
        import keyring

        keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, key)
        log.info("Chave Fernet armazenada no keyring com sucesso")
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("Erro ao salvar chave no keyring: %s", exc)
        return False


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

    Ordem de precedência para chave (conforme docs/SECURITY_MODEL.md):
    1. Variável de ambiente RC_CLIENT_SECRET_KEY (prioridade máxima)
    2. Keyring do sistema (Windows Credential Manager)
       - Se encontrada: usa essa chave
       - Se não encontrada: gera nova chave e salva no keyring
    3. Se keyring indisponível: levanta RuntimeError com instruções

    A chave é lida/gerada apenas uma vez e armazenada em _fernet_instance.

    Returns:
        Fernet: Instância configurada para criptografia.

    Raises:
        RuntimeError: Se nenhuma fonte de chave estiver disponível.
    """
    global _fernet_instance

    if _fernet_instance is not None:
        return _fernet_instance

    key_str: str | None = None

    # PRIORIDADE 1: Variável de ambiente (usuário escolheu gestão manual)
    env_key = os.getenv("RC_CLIENT_SECRET_KEY")
    if env_key:
        log.info("Usando RC_CLIENT_SECRET_KEY da variável de ambiente")
        key_str = env_key
    else:
        # PRIORIDADE 2: Keyring (chave única por instalação)
        key_str = _keyring_get_secret_key()

        if not key_str:
            # Nenhuma chave encontrada: gerar nova e tentar salvar
            if _keyring_is_available():
                log.info("Gerando nova chave Fernet e salvando no keyring")
                key_str = Fernet.generate_key().decode("utf-8")
                if not _keyring_set_secret_key(key_str):
                    log.warning("Falha ao salvar nova chave no keyring, mas continuando com chave em memória")
            else:
                # FALLBACK: Keyring indisponível e sem env var
                raise RuntimeError(
                    "RC_CLIENT_SECRET_KEY não encontrada e keyring indisponível.\n"
                    "Para resolver, defina a variável de ambiente:\n"
                    '  Windows PowerShell: $env:RC_CLIENT_SECRET_KEY = "chave-base64"\n'
                    "  CMD: set RC_CLIENT_SECRET_KEY=chave-base64\n"
                    "\nGere uma nova chave com:\n"
                    '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"\n'
                    "\nVeja docs/SECURITY_MODEL.md para detalhes."
                )

    # Validação e criação da instância
    try:
        key_bytes = key_str.encode("utf-8")
        _fernet_instance = Fernet(key_bytes)
        return _fernet_instance
    except Exception as e:
        # SEC-007: Mascara chave na mensagem de erro
        try:
            masked_key = "***" if not key_str else f"{key_str[:4]}...{key_str[-4:]}" if len(key_str) > 12 else "***"
        except (TypeError, AttributeError):
            masked_key = "***"

        raise RuntimeError(
            f"RC_CLIENT_SECRET_KEY tem formato inválido para Fernet (deve ser base64 de 44 caracteres). "
            f"Chave fornecida (mascarada): {masked_key}\n"
            f"Veja docs/SECURITY_MODEL.md para detalhes."
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
