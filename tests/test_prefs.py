"""
Testes para src/utils/prefs.py - persistência de preferências.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from src.utils.prefs import load_columns_visibility, save_columns_visibility


@pytest.fixture
def temp_prefs_dir(monkeypatch, tmp_path):
    """Configura diretório temporário para preferências."""
    prefs_dir = tmp_path / "test_prefs"
    prefs_dir.mkdir()

    # Mock do _get_base_dir para usar nosso temp dir
    monkeypatch.setattr("src.utils.prefs._get_base_dir", lambda: str(prefs_dir))

    return prefs_dir


def test_save_and_load_prefs(temp_prefs_dir):
    """Testa salvar e carregar preferências básicas."""
    user_key = "user@test.com"
    prefs = {"col1": True, "col2": False, "col3": True}

    # Salvar
    save_columns_visibility(user_key, prefs)

    # Carregar
    loaded = load_columns_visibility(user_key)

    assert loaded == prefs


def test_load_nonexistent_user(temp_prefs_dir):
    """Testa carregar preferências de usuário inexistente."""
    loaded = load_columns_visibility("nonexistent@test.com")
    assert loaded == {}


def test_concurrent_save_different_users(temp_prefs_dir):
    """
    Testa salvar preferências de múltiplos usuários preservando dados.
    Simula race condition sem threading real (teste unitário).
    """
    user1 = "user1@test.com"
    user2 = "user2@test.com"

    prefs1 = {"col_a": True, "col_b": False}
    prefs2 = {"col_x": True, "col_y": True}

    # Salvar user1
    save_columns_visibility(user1, prefs1)

    # Salvar user2 (deve preservar user1)
    save_columns_visibility(user2, prefs2)

    # Verificar ambos existem
    loaded1 = load_columns_visibility(user1)
    loaded2 = load_columns_visibility(user2)

    assert loaded1 == prefs1
    assert loaded2 == prefs2


def test_corrupted_prefs_file_returns_empty(temp_prefs_dir):
    """Testa que arquivo corrompido retorna dict vazio sem crashar."""
    prefs_path = temp_prefs_dir / "columns_visibility.json"

    # Criar arquivo JSON inválido
    prefs_path.write_text("{ invalid json }", encoding="utf-8")

    # Deve retornar {} sem erro
    loaded = load_columns_visibility("user@test.com")
    assert loaded == {}


@pytest.mark.skipif(
    not os.getenv("TEST_FILELOCK"),
    reason="Requer filelock instalado. Execute: pip install filelock"
)
def test_filelock_integration(temp_prefs_dir):
    """
    Testa integração com filelock (requer filelock instalado).
    Skip se filelock não disponível.
    """
    user_key = "locked@test.com"
    prefs = {"locked_col": True}

    save_columns_visibility(user_key, prefs)
    loaded = load_columns_visibility(user_key)

    assert loaded == prefs

    # Verificar que arquivo .lock foi criado/removido
    lock_path = temp_prefs_dir / "columns_visibility.json.lock"
    # Lock deve ser liberado após operação
    assert not lock_path.exists() or os.path.getsize(lock_path) == 0
