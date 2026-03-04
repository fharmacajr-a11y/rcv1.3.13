# -*- coding: utf-8 -*-
"""SEC-004: Testes de política de senha na criação de usuário.

Valida que:
  - Senha é obrigatória (None, vazia, whitespace → ValueError)
  - Senhas triviais bloqueadas ("admin123" etc.) → ValueError
  - Senha válida → cria usuário com sucesso (retorna int)
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# ── Configuração de ambiente para testes ──────────────────────────────────
os.environ.setdefault("RC_TESTING", "1")
os.environ.setdefault("RC_PBKDF2_ITERS", "1000")  # PERF: reduz iterações


def _import_create_user():
    """Importa create_user com USERS_DB_PATH apontando para um tempdir."""
    # Criar DB temporário para isolar testes
    tmp = tempfile.mkdtemp()
    tmp_db = Path(tmp) / "users_test.db"

    with patch("src.core.auth.auth.USERS_DB_PATH", tmp_db):
        from src.core.auth.auth import _BLOCKED_PASSWORDS, create_user

    return create_user, _BLOCKED_PASSWORDS, tmp_db


create_user, _BLOCKED_PASSWORDS, _tmp_db = _import_create_user()


# ── Fixture: DB limpo por teste ───────────────────────────────────────────
@pytest.fixture(autouse=True)
def _clean_db():
    """Garante DB fresco para cada teste."""
    if _tmp_db.exists():
        _tmp_db.unlink()
    yield
    if _tmp_db.exists():
        _tmp_db.unlink()


# ── Testes: senha obrigatória ─────────────────────────────────────────────
class TestPasswordRequired:
    """Senha não pode ser None, vazia ou apenas espaços."""

    def test_none_password_raises(self):
        with patch("src.core.auth.auth.USERS_DB_PATH", _tmp_db):
            with pytest.raises(ValueError, match="[Ss]enha.*obrigatória"):
                create_user("testuser", None)  # type: ignore[arg-type]

    def test_empty_password_raises(self):
        with patch("src.core.auth.auth.USERS_DB_PATH", _tmp_db):
            with pytest.raises(ValueError, match="[Ss]enha.*obrigatória"):
                create_user("testuser", "")

    def test_whitespace_only_password_raises(self):
        with patch("src.core.auth.auth.USERS_DB_PATH", _tmp_db):
            with pytest.raises(ValueError, match="[Ss]enha.*obrigatória"):
                create_user("testuser", "   ")


# ── Testes: senhas triviais bloqueadas ────────────────────────────────────
class TestBlockedPasswords:
    """Senhas na denylist são rejeitadas."""

    def test_admin123_blocked(self):
        with patch("src.core.auth.auth.USERS_DB_PATH", _tmp_db):
            with pytest.raises(ValueError, match="[Ss]enha.*fraca|conhecida"):
                create_user("testuser", "admin123")

    def test_password_blocked(self):
        with patch("src.core.auth.auth.USERS_DB_PATH", _tmp_db):
            with pytest.raises(ValueError, match="[Ss]enha.*fraca|conhecida"):
                create_user("testuser", "password")

    def test_123456_blocked(self):
        with patch("src.core.auth.auth.USERS_DB_PATH", _tmp_db):
            with pytest.raises(ValueError, match="[Ss]enha.*fraca|conhecida"):
                create_user("testuser", "123456")

    def test_12345678_blocked(self):
        with patch("src.core.auth.auth.USERS_DB_PATH", _tmp_db):
            with pytest.raises(ValueError, match="[Ss]enha.*fraca|conhecida"):
                create_user("testuser", "12345678")

    def test_blocked_list_has_admin123(self):
        assert "admin123" in _BLOCKED_PASSWORDS


# ── Testes: senha válida → sucesso ────────────────────────────────────────
class TestValidPassword:
    """Com senha válida, create_user deve retornar um ID (int > 0)."""

    def test_create_with_valid_password(self):
        with patch("src.core.auth.auth.USERS_DB_PATH", _tmp_db):
            uid = create_user("newuser", "MyS3cur3P@ss!")
        assert isinstance(uid, int)
        assert uid > 0

    def test_create_returns_different_ids(self):
        with patch("src.core.auth.auth.USERS_DB_PATH", _tmp_db):
            uid1 = create_user("user_a", "ValidPass1!")
            uid2 = create_user("user_b", "ValidPass2!")
        assert uid1 != uid2

    def test_update_existing_user_returns_same_id(self):
        with patch("src.core.auth.auth.USERS_DB_PATH", _tmp_db):
            uid1 = create_user("sameuser", "FirstPass1!")
            uid2 = create_user("sameuser", "SecondPass2!")
        assert uid1 == uid2
