# -*- coding: utf-8 -*-
"""Armazenamento seguro de sessão em arquivo criptografado (fallback DPAPI).

Quando o keyring do SO não está disponível, esta camada garante que tokens
de sessão (access_token / refresh_token) **nunca** fiquem em texto plano no
disco.

* **Windows** — usa CryptProtectData / CryptUnprotectData (DPAPI) via
  ``ctypes``.  A chave de criptografia é derivada das credenciais do
  usuário logado no Windows; nenhum segredo extra é necessário.
* **Outras plataformas** — fallback criptografado não é suportado; a
  sessão simplesmente não é persistida (keyring é obrigatório).

O arquivo resultante tem formato ``v1:<base64(dpapi_blob)>`` — nunca JSON
legível.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import stat
import subprocess
import sys
import tempfile
from typing import Any

log = logging.getLogger(__name__)

_IS_WINDOWS: bool = sys.platform == "win32"

ENC_FILENAME: str = "auth_session.enc"
LEGACY_FILENAME: str = "auth_session.json"
_VERSION_PREFIX: bytes = b"v1:"


# ═══════════════════════════════════════════════════════════════════════════
# DPAPI helpers  (Windows only, via ctypes — sem dependência extra)
# ═══════════════════════════════════════════════════════════════════════════


def dpapi_encrypt(plaintext: bytes) -> bytes:
    """Cifra *plaintext* com Windows DPAPI (escopo do usuário corrente).

    Raises ``OSError`` em plataformas não-Windows ou se a API falhar.
    """
    if not _IS_WINDOWS:
        raise OSError("DPAPI disponível apenas no Windows")

    import ctypes  # noqa: E402
    import ctypes.wintypes as wt  # noqa: E402

    class _Blob(ctypes.Structure):
        _fields_ = [
            ("cbData", wt.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    buf = ctypes.create_string_buffer(plaintext, len(plaintext))
    blob_in = _Blob(len(plaintext), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _Blob()

    ok: bool = ctypes.windll.crypt32.CryptProtectData(  # type: ignore[union-attr]
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    )
    if not ok:
        raise OSError("CryptProtectData falhou")

    result = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)  # type: ignore[union-attr]
    return result


def dpapi_decrypt(ciphertext: bytes) -> bytes:
    """Decifra *ciphertext* com Windows DPAPI (escopo do usuário corrente).

    Raises ``OSError`` em plataformas não-Windows ou se a API falhar.
    """
    if not _IS_WINDOWS:
        raise OSError("DPAPI disponível apenas no Windows")

    import ctypes  # noqa: E402
    import ctypes.wintypes as wt  # noqa: E402

    class _Blob(ctypes.Structure):
        _fields_ = [
            ("cbData", wt.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    buf = ctypes.create_string_buffer(ciphertext, len(ciphertext))
    blob_in = _Blob(len(ciphertext), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _Blob()

    ok: bool = ctypes.windll.crypt32.CryptUnprotectData(  # type: ignore[union-attr]
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    )
    if not ok:
        raise OSError("CryptUnprotectData falhou")

    result = bytes(ctypes.string_at(blob_out.pbData, blob_out.cbData))
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)  # type: ignore[union-attr]
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Serialização: session dict ↔ blob versionado
# ═══════════════════════════════════════════════════════════════════════════


def encrypt_session_payload(session_dict: dict[str, Any]) -> bytes:
    """``dict`` → JSON UTF-8 → DPAPI encrypt → ``v1:<base64>``."""
    plaintext = json.dumps(session_dict, ensure_ascii=False).encode("utf-8")
    encrypted = dpapi_encrypt(plaintext)
    return _VERSION_PREFIX + base64.b64encode(encrypted)


def decrypt_session_payload(blob: bytes) -> dict[str, Any]:
    """Inverso de :func:`encrypt_session_payload`."""
    if not blob.startswith(_VERSION_PREFIX):
        raise ValueError("Formato de versão desconhecido no arquivo de sessão")
    b64_part = blob[len(_VERSION_PREFIX) :]
    encrypted = base64.b64decode(b64_part)
    plaintext = dpapi_decrypt(encrypted)
    data: Any = json.loads(plaintext.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Payload de sessão não é um dict JSON")
    return data


# ═══════════════════════════════════════════════════════════════════════════
# Escrita atômica + permissões restritas
# ═══════════════════════════════════════════════════════════════════════════


def restrict_file_permissions(path: str) -> None:
    """Aplica permissões restritas (best-effort).

    * **Windows** — ``icacls`` remove herança e garante acesso apenas
      ao usuário corrente.  DPAPI já é a camada principal de proteção.
    * **POSIX** — ``chmod 600``.
    """
    if _IS_WINDOWS:
        try:
            uname = os.getenv("USERNAME", "")
            if uname:
                subprocess.run(  # noqa: S603, S607
                    ["icacls", path, "/inheritance:r", "/grant:r", f"{uname}:(R,W,D)"],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
        except Exception:
            pass  # DPAPI é a proteção primária
    else:
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError:
            pass


def atomic_write(path: str, data: bytes) -> None:
    """Grava *data* em *path* atomicamente (temp → ``os.replace``).

    Também aplica :func:`restrict_file_permissions` após a escrita.
    """
    dir_name = os.path.dirname(path) or "."
    os.makedirs(dir_name, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dir_name, prefix=".session_", suffix=".tmp")
    try:
        os.write(fd, data)
        os.close(fd)
        fd = -1
        os.replace(tmp, path)
        restrict_file_permissions(path)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ═══════════════════════════════════════════════════════════════════════════
# API pública: save / load / clear / migrate
# ═══════════════════════════════════════════════════════════════════════════


def encrypted_file_save(base_dir: str, session_dict: dict[str, Any]) -> None:
    """Criptografa e salva sessão em ``auth_session.enc`` (atômico)."""
    path = os.path.join(base_dir, ENC_FILENAME)
    blob = encrypt_session_payload(session_dict)
    atomic_write(path, blob)
    log.debug("Sessão salva em arquivo criptografado (DPAPI), token_present=True")


def encrypted_file_load(base_dir: str) -> dict[str, Any] | None:
    """Carrega e decripta ``auth_session.enc``.  Retorna *None* em qualquer falha."""
    path = os.path.join(base_dir, ENC_FILENAME)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as fh:
            blob = fh.read()
        return decrypt_session_payload(blob)
    except Exception as exc:
        log.warning("Falha ao ler sessão criptografada: %s", exc)
        try:
            os.unlink(path)
        except OSError:
            pass
        return None


def encrypted_file_clear(base_dir: str) -> None:
    """Remove arquivos de sessão criptografado **e** legado (best-effort)."""
    for name in (ENC_FILENAME, LEGACY_FILENAME):
        fpath = os.path.join(base_dir, name)
        try:
            if os.path.exists(fpath):
                os.unlink(fpath)
        except OSError as exc:
            log.debug("Não foi possível remover %s: %s", name, exc)


def migrate_legacy_file(base_dir: str) -> dict[str, Any] | None:
    """Lê ``auth_session.json`` (plain), re-criptografa, apaga o original.

    Retorna o dict de sessão se a migração teve sucesso, senão *None*.
    """
    legacy_path = os.path.join(base_dir, LEGACY_FILENAME)
    if not os.path.isfile(legacy_path):
        return None

    try:
        with open(legacy_path, "r", encoding="utf-8") as fh:
            data: Any = json.load(fh)
        if not isinstance(data, dict):
            return None
        if not data.get("access_token") or not data.get("refresh_token"):
            return None

        # Re-encrypt no Windows; em outros SOs apenas apaga o plain-text.
        if _IS_WINDOWS:
            encrypted_file_save(base_dir, data)
            log.info("Sessão legada migrada de JSON plain para DPAPI-encrypted")

        # Sempre apagar o arquivo legado em plain-text
        try:
            os.unlink(legacy_path)
            log.info("Arquivo legado auth_session.json removido após migração")
        except OSError:
            pass

        return data
    except Exception as exc:
        log.warning("Falha ao migrar sessão legada: %s", exc)
        return None
