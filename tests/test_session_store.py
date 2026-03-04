# -*- coding: utf-8 -*-
"""Testes para src/utils/session_store.py (PR7 — sessão criptografada)."""

from __future__ import annotations

import base64
import json
import os
import tempfile
from typing import Any
from unittest import mock

import pytest

from src.utils.session_store import (
    ENC_FILENAME,
    LEGACY_FILENAME,
    _VERSION_PREFIX,
    atomic_write,
    decrypt_session_payload,
    encrypt_session_payload,
    encrypted_file_clear,
    encrypted_file_load,
    encrypted_file_save,
    migrate_legacy_file,
    restrict_file_permissions,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _fake_dpapi_encrypt(plaintext: bytes) -> bytes:
    """Simula DPAPI: simplesmente inverte os bytes (reversível)."""
    return plaintext[::-1]


def _fake_dpapi_decrypt(ciphertext: bytes) -> bytes:
    """Inverso de _fake_dpapi_encrypt."""
    return ciphertext[::-1]


SAMPLE_SESSION: dict[str, Any] = {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
    "refresh_token": "dGVzdC1yZWZyZXNoLXRva2VuLXZhbHVl",
    "created_at": "2026-03-03T10:00:00+00:00",
    "keep_logged": True,
}


# ═══════════════════════════════════════════════════════════════════════════
# Encrypt / decrypt roundtrip
# ═══════════════════════════════════════════════════════════════════════════


class TestEncryptDecryptRoundtrip:
    """Garante que encrypt → decrypt retorna o payload original."""

    @mock.patch("src.utils.session_store.dpapi_decrypt", side_effect=_fake_dpapi_decrypt)
    @mock.patch("src.utils.session_store.dpapi_encrypt", side_effect=_fake_dpapi_encrypt)
    def test_roundtrip_basic(self, _enc: mock.MagicMock, _dec: mock.MagicMock) -> None:
        blob = encrypt_session_payload(SAMPLE_SESSION)
        result = decrypt_session_payload(blob)
        assert result == SAMPLE_SESSION

    @mock.patch("src.utils.session_store.dpapi_decrypt", side_effect=_fake_dpapi_decrypt)
    @mock.patch("src.utils.session_store.dpapi_encrypt", side_effect=_fake_dpapi_encrypt)
    def test_blob_starts_with_version_prefix(self, _enc: mock.MagicMock, _dec: mock.MagicMock) -> None:
        blob = encrypt_session_payload(SAMPLE_SESSION)
        assert blob.startswith(_VERSION_PREFIX)

    @mock.patch("src.utils.session_store.dpapi_decrypt", side_effect=_fake_dpapi_decrypt)
    @mock.patch("src.utils.session_store.dpapi_encrypt", side_effect=_fake_dpapi_encrypt)
    def test_blob_base64_portion_is_valid(self, _enc: mock.MagicMock, _dec: mock.MagicMock) -> None:
        blob = encrypt_session_payload(SAMPLE_SESSION)
        b64_part = blob[len(_VERSION_PREFIX) :]
        # Deve ser base64 decodificável
        decoded = base64.b64decode(b64_part)
        assert len(decoded) > 0

    @mock.patch("src.utils.session_store.dpapi_decrypt", side_effect=_fake_dpapi_decrypt)
    @mock.patch("src.utils.session_store.dpapi_encrypt", side_effect=_fake_dpapi_encrypt)
    def test_plaintext_not_visible_in_blob(self, _enc: mock.MagicMock, _dec: mock.MagicMock) -> None:
        blob = encrypt_session_payload(SAMPLE_SESSION)
        # Tokens NÃO devem aparecer em texto plano no blob
        assert b"eyJhbGci" not in blob
        assert b"access_token" not in blob

    def test_decrypt_rejects_unknown_version(self) -> None:
        with pytest.raises(ValueError, match="versão desconhecido"):
            decrypt_session_payload(b"v99:AAAA")

    def test_decrypt_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="versão desconhecido"):
            decrypt_session_payload(b"")


# ═══════════════════════════════════════════════════════════════════════════
# Fallback path: save → load (arquivo criptografado)
# ═══════════════════════════════════════════════════════════════════════════


class TestEncryptedFileSaveLoad:
    """Salvar e carregar sessão via arquivo criptografado."""

    @mock.patch("src.utils.session_store.dpapi_decrypt", side_effect=_fake_dpapi_decrypt)
    @mock.patch("src.utils.session_store.dpapi_encrypt", side_effect=_fake_dpapi_encrypt)
    def test_save_and_load_roundtrip(self, _enc: mock.MagicMock, _dec: mock.MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            encrypted_file_save(tmpdir, SAMPLE_SESSION)
            result = encrypted_file_load(tmpdir)
            assert result == SAMPLE_SESSION

    @mock.patch("src.utils.session_store.dpapi_decrypt", side_effect=_fake_dpapi_decrypt)
    @mock.patch("src.utils.session_store.dpapi_encrypt", side_effect=_fake_dpapi_encrypt)
    def test_file_content_is_not_readable_json(self, _enc: mock.MagicMock, _dec: mock.MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            encrypted_file_save(tmpdir, SAMPLE_SESSION)
            path = os.path.join(tmpdir, ENC_FILENAME)
            with open(path, "rb") as f:
                raw = f.read()
            # Não pode ser JSON legível — deve começar com v1:
            assert raw.startswith(_VERSION_PREFIX)
            # Tentar parsear como JSON deve falhar
            with pytest.raises(Exception):
                json.loads(raw)

    def test_load_returns_none_when_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            assert encrypted_file_load(tmpdir) is None

    @mock.patch("src.utils.session_store.dpapi_decrypt", side_effect=_fake_dpapi_decrypt)
    @mock.patch("src.utils.session_store.dpapi_encrypt", side_effect=_fake_dpapi_encrypt)
    def test_load_returns_none_on_corrupt_file(self, _enc: mock.MagicMock, _dec: mock.MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, ENC_FILENAME)
            with open(path, "wb") as f:
                f.write(b"v1:INVALID_BASE64!!!")
            result = encrypted_file_load(tmpdir)
            assert result is None
            # Arquivo corrompido deve ter sido removido
            assert not os.path.exists(path)


# ═══════════════════════════════════════════════════════════════════════════
# Escrita atômica: verifica temp + replace
# ═══════════════════════════════════════════════════════════════════════════


class TestAtomicWrite:
    """Testa que a escrita usa tempfile + os.replace."""

    def test_atomic_write_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "test.bin")
            atomic_write(target, b"hello")
            assert os.path.exists(target)
            with open(target, "rb") as f:
                assert f.read() == b"hello"

    @mock.patch("src.utils.session_store.os.replace", wraps=os.replace)
    def test_atomic_write_calls_os_replace(self, mock_replace: mock.MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "test.bin")
            atomic_write(target, b"data")
            mock_replace.assert_called_once()
            # Primeiro arg é o temp, segundo é o target
            args = mock_replace.call_args[0]
            assert args[1] == target

    def test_atomic_write_no_leftover_temp_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "test.bin")
            atomic_write(target, b"data")
            files = os.listdir(tmpdir)
            # Apenas o arquivo final deve existir
            assert files == ["test.bin"]

    @mock.patch("src.utils.session_store.os.replace", side_effect=OSError("boom"))
    def test_atomic_write_cleans_temp_on_failure(self, _mock: mock.MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "test.bin")
            with pytest.raises(OSError, match="boom"):
                atomic_write(target, b"data")
            # Não deve deixar arquivo temporário
            remaining = [f for f in os.listdir(tmpdir) if f.startswith(".session_")]
            assert remaining == []


# ═══════════════════════════════════════════════════════════════════════════
# Permissões restritas
# ═══════════════════════════════════════════════════════════════════════════


class TestRestrictPermissions:
    """Testa que restrict_file_permissions tenta aplicar restrições."""

    @mock.patch("src.utils.session_store._IS_WINDOWS", False)
    @mock.patch("src.utils.session_store.os.chmod")
    def test_posix_applies_chmod_600(self, mock_chmod: mock.MagicMock) -> None:
        restrict_file_permissions("/tmp/test.enc")
        mock_chmod.assert_called_once_with("/tmp/test.enc", 0o600)

    @mock.patch("src.utils.session_store._IS_WINDOWS", True)
    @mock.patch("src.utils.session_store.subprocess.run")
    def test_windows_calls_icacls(self, mock_run: mock.MagicMock) -> None:
        with mock.patch.dict(os.environ, {"USERNAME": "TestUser"}):
            restrict_file_permissions("C:\\test.enc")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "icacls"
        assert "TestUser:(R,W,D)" in cmd


# ═══════════════════════════════════════════════════════════════════════════
# Migração de arquivo legado
# ═══════════════════════════════════════════════════════════════════════════


class TestMigrateLegacyFile:
    """Testa migração de auth_session.json plain → auth_session.enc."""

    @mock.patch("src.utils.session_store.dpapi_decrypt", side_effect=_fake_dpapi_decrypt)
    @mock.patch("src.utils.session_store.dpapi_encrypt", side_effect=_fake_dpapi_encrypt)
    @mock.patch("src.utils.session_store._IS_WINDOWS", True)
    def test_migrates_plain_json_to_encrypted(self, _enc: mock.MagicMock, _dec: mock.MagicMock) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Criar arquivo legado em plain JSON
            legacy = os.path.join(tmpdir, LEGACY_FILENAME)
            with open(legacy, "w", encoding="utf-8") as f:
                json.dump(SAMPLE_SESSION, f)

            result = migrate_legacy_file(tmpdir)

            # Deve retornar a sessão
            assert result is not None
            assert result["access_token"] == SAMPLE_SESSION["access_token"]
            # Arquivo legado deve ter sido removido
            assert not os.path.exists(legacy)
            # Arquivo criptografado deve existir
            enc_path = os.path.join(tmpdir, ENC_FILENAME)
            assert os.path.exists(enc_path)

    def test_returns_none_when_no_legacy_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            assert migrate_legacy_file(tmpdir) is None

    @mock.patch("src.utils.session_store._IS_WINDOWS", True)
    def test_returns_none_for_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy = os.path.join(tmpdir, LEGACY_FILENAME)
            with open(legacy, "w") as f:
                f.write("not json{{{")
            assert migrate_legacy_file(tmpdir) is None

    @mock.patch("src.utils.session_store._IS_WINDOWS", True)
    def test_returns_none_when_missing_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy = os.path.join(tmpdir, LEGACY_FILENAME)
            with open(legacy, "w", encoding="utf-8") as f:
                json.dump({"access_token": "", "refresh_token": ""}, f)
            assert migrate_legacy_file(tmpdir) is None


# ═══════════════════════════════════════════════════════════════════════════
# Clear
# ═══════════════════════════════════════════════════════════════════════════


class TestEncryptedFileClear:
    """Testa remoção de arquivos de sessão."""

    def test_clears_both_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            enc = os.path.join(tmpdir, ENC_FILENAME)
            legacy = os.path.join(tmpdir, LEGACY_FILENAME)
            with open(enc, "w") as f:
                f.write("enc")
            with open(legacy, "w") as f:
                f.write("legacy")

            encrypted_file_clear(tmpdir)

            assert not os.path.exists(enc)
            assert not os.path.exists(legacy)

    def test_clear_ignores_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Não deve levantar exceção
            encrypted_file_clear(tmpdir)


# ═══════════════════════════════════════════════════════════════════════════
# Integração prefs.py: _validate_session_dict
# ═══════════════════════════════════════════════════════════════════════════


class TestValidateSessionDict:
    """Testa o helper _validate_session_dict de prefs.py."""

    def test_valid_session(self) -> None:
        from src.utils.prefs import _validate_session_dict

        result = _validate_session_dict(SAMPLE_SESSION)
        assert result is not None
        assert result["access_token"] == SAMPLE_SESSION["access_token"]

    def test_missing_access_token(self) -> None:
        from src.utils.prefs import _validate_session_dict

        data = {**SAMPLE_SESSION, "access_token": ""}
        assert _validate_session_dict(data) is None

    def test_missing_refresh_token(self) -> None:
        from src.utils.prefs import _validate_session_dict

        data = {**SAMPLE_SESSION, "refresh_token": ""}
        assert _validate_session_dict(data) is None

    def test_missing_created_at(self) -> None:
        from src.utils.prefs import _validate_session_dict

        data = {**SAMPLE_SESSION, "created_at": ""}
        assert _validate_session_dict(data) is None
