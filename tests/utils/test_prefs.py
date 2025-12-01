# -*- coding: utf-8 -*-
"""
Testes consolidados e expandidos para src/utils/prefs.py
Cobertura: TEST-001 + QA-003
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils import prefs as prefs_module

# Verificar se filelock está disponível
try:
    import filelock  # noqa: F401

    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False


@pytest.fixture
def temp_prefs_dir(isolated_prefs_dir: Path) -> Path:
    """
    Reutiliza a fixture autouse isolated_prefs_dir do conftest.
    """
    return isolated_prefs_dir


# ============================================================================
# Testes para _get_base_dir
# ============================================================================


def test_get_base_dir_uses_appdata_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que _get_base_dir usa APPDATA no Windows."""
    import importlib

    appdata = tmp_path / "appdata"
    appdata.mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))

    # Recarregar módulo para forçar re-execução de _get_base_dir
    importlib.reload(prefs_module)

    base_dir = prefs_module._get_base_dir()
    expected = appdata / prefs_module.APP_FOLDER_NAME
    assert Path(base_dir) == expected
    assert expected.is_dir()


def test_get_base_dir_fallback_unix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa fallback para home directory em sistemas Unix-like."""
    import importlib

    monkeypatch.delenv("APPDATA", raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(os.path, "expanduser", lambda _: str(home))

    importlib.reload(prefs_module)

    base_dir = prefs_module._get_base_dir()
    expected = home / f".{prefs_module.APP_FOLDER_NAME.lower()}"
    assert Path(base_dir) == expected
    assert expected.is_dir()


# ============================================================================
# Testes para load_columns_visibility e save_columns_visibility
# ============================================================================


def test_save_and_load_columns_visibility_basic(temp_prefs_dir: Path) -> None:
    """Testa salvar e carregar preferências de colunas básicas."""
    user_key = "user@test.com"
    prefs = {"col1": True, "col2": False, "col3": True}

    prefs_module.save_columns_visibility(user_key, prefs)
    loaded = prefs_module.load_columns_visibility(user_key)

    assert loaded == prefs


def test_load_columns_visibility_no_file(temp_prefs_dir: Path) -> None:
    """Testa carregar preferências quando arquivo não existe."""
    loaded = prefs_module.load_columns_visibility("nonexistent@test.com")
    assert loaded == {}


def test_load_columns_visibility_empty_user_key(temp_prefs_dir: Path) -> None:
    """Testa carregar preferências para usuário que não está no arquivo."""
    user1 = "user1@test.com"
    prefs_module.save_columns_visibility(user1, {"col1": True})

    loaded = prefs_module.load_columns_visibility("other@test.com")
    assert loaded == {}


def test_save_columns_visibility_preserves_other_users(temp_prefs_dir: Path) -> None:
    """Testa que salvar preferências de um usuário preserva dados de outros."""
    user1 = "user1@test.com"
    user2 = "user2@test.com"
    prefs1 = {"col_a": True, "col_b": False}
    prefs2 = {"col_x": True, "col_y": True}

    prefs_module.save_columns_visibility(user1, prefs1)
    prefs_module.save_columns_visibility(user2, prefs2)

    loaded1 = prefs_module.load_columns_visibility(user1)
    loaded2 = prefs_module.load_columns_visibility(user2)

    assert loaded1 == prefs1
    assert loaded2 == prefs2


def test_load_columns_visibility_corrupted_json(temp_prefs_dir: Path) -> None:
    """Testa que arquivo JSON corrompido retorna {} sem crashar."""
    prefs_path = temp_prefs_dir / "columns_visibility.json"
    prefs_path.write_text("{ invalid json }", encoding="utf-8")

    loaded = prefs_module.load_columns_visibility("any@test.com")
    assert loaded == {}


def test_save_columns_visibility_without_filelock(temp_prefs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa salvamento sem filelock disponível."""
    monkeypatch.setattr("src.utils.prefs.HAS_FILELOCK", False)

    user_key = "user@test.com"
    mapping = {"col1": True, "col2": False}

    prefs_module.save_columns_visibility(user_key, mapping)

    saved = json.loads((temp_prefs_dir / "columns_visibility.json").read_text(encoding="utf-8"))
    assert saved[user_key] == mapping


@pytest.mark.skipif(not HAS_FILELOCK, reason="Requer filelock instalado")
def test_columns_visibility_with_filelock(temp_prefs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa integração com filelock."""
    monkeypatch.setattr("src.utils.prefs.HAS_FILELOCK", True)

    user_key = "locked@test.com"
    prefs = {"locked_col": True}

    prefs_module.save_columns_visibility(user_key, prefs)
    loaded = prefs_module.load_columns_visibility(user_key)

    assert loaded == prefs


def test_save_columns_visibility_exception_handling(temp_prefs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que exceções durante save são capturadas e logadas."""
    user_key = "user@test.com"
    mapping = {"col1": True}

    # Forçar erro ao abrir arquivo para escrita
    original_open = open

    def mock_open(*args, **kwargs):
        if "w" in str(kwargs.get("mode", args[1] if len(args) > 1 else "")):
            raise PermissionError("Mock permission error")
        return original_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    # Não deve crashar
    prefs_module.save_columns_visibility(user_key, mapping)


def test_load_columns_visibility_exception_handling(temp_prefs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que exceções durante load são capturadas e retornam {}."""
    # Criar arquivo primeiro
    prefs_path = temp_prefs_dir / "columns_visibility.json"
    prefs_path.write_text('{"user@test.com": {"col1": true}}', encoding="utf-8")

    # Forçar erro ao abrir arquivo
    def mock_open_error(*args, **kwargs):
        raise OSError("Mock OS error")

    # Usar patch para interceptar abertura do arquivo especificamente em _load_prefs_unlocked
    with patch("builtins.open", side_effect=mock_open_error):
        loaded = prefs_module.load_columns_visibility("user@test.com")
        assert loaded == {}


# ============================================================================
# Testes para login_prefs
# ============================================================================


def test_save_and_load_login_prefs_basic(temp_prefs_dir: Path) -> None:
    """Testa salvar e carregar preferências de login básicas."""
    prefs_module.save_login_prefs("user@test.com", True)
    data = prefs_module.load_login_prefs()

    assert data["email"] == "user@test.com"
    assert data["remember_email"] is True


def test_save_login_prefs_with_whitespace(temp_prefs_dir: Path) -> None:
    """Testa que email com espaços é normalizado."""
    prefs_module.save_login_prefs("  user@test.com  ", True)
    data = prefs_module.load_login_prefs()

    assert data["email"] == "user@test.com"


def test_save_login_prefs_clears_when_not_remember(temp_prefs_dir: Path) -> None:
    """Testa que arquivo é removido quando remember_email=False."""
    prefs_module.save_login_prefs("user@test.com", True)
    assert prefs_module.load_login_prefs()["email"] == "user@test.com"

    prefs_module.save_login_prefs("other@test.com", False)
    data = prefs_module.load_login_prefs()
    assert data == {}


def test_load_login_prefs_no_file(temp_prefs_dir: Path) -> None:
    """Testa carregar login_prefs quando arquivo não existe."""
    data = prefs_module.load_login_prefs()
    assert data == {}


def test_load_login_prefs_corrupted_json(temp_prefs_dir: Path) -> None:
    """Testa que JSON corrompido retorna {} e loga warning."""
    path = Path(prefs_module._login_prefs_path())
    path.write_text("{ invalid json }", encoding="utf-8")

    data = prefs_module.load_login_prefs()
    assert data == {}


def test_load_login_prefs_invalid_structure(temp_prefs_dir: Path) -> None:
    """Testa que estrutura não-dict retorna {}."""
    path = Path(prefs_module._login_prefs_path())
    path.write_text('["not", "a", "dict"]', encoding="utf-8")

    data = prefs_module.load_login_prefs()
    assert data == {}


def test_load_login_prefs_missing_fields(temp_prefs_dir: Path) -> None:
    """Testa que campos ausentes usam valores padrão."""
    path = Path(prefs_module._login_prefs_path())
    path.write_text('{"email": "user@test.com"}', encoding="utf-8")

    data = prefs_module.load_login_prefs()
    assert data["email"] == "user@test.com"
    assert data["remember_email"] is True  # default


def test_save_login_prefs_clear_error_handling(temp_prefs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que erro ao remover arquivo durante clear é tratado."""
    prefs_module.save_login_prefs("user@test.com", True)

    # Mockar os.remove para lançar exceção
    original_remove = os.remove

    def mock_remove(path):
        if "login_prefs" in str(path):
            raise OSError("Mock error")
        return original_remove(path)

    monkeypatch.setattr("os.remove", mock_remove)

    # Não deve crashar
    prefs_module.save_login_prefs("other@test.com", False)


# ============================================================================
# Testes para auth_session
# ============================================================================


def test_save_and_load_auth_session_basic(temp_prefs_dir: Path) -> None:
    """Testa salvar e carregar sessão de autenticação."""
    prefs_module.save_auth_session("access_token_123", "refresh_token_456", keep_logged=True)
    data = prefs_module.load_auth_session()

    assert data["access_token"] == "access_token_123"
    assert data["refresh_token"] == "refresh_token_456"
    assert data["keep_logged"] is True
    assert "created_at" in data
    assert data["created_at"]  # Deve ter timestamp ISO


def test_save_auth_session_clears_when_not_keep_logged(temp_prefs_dir: Path) -> None:
    """Testa que arquivo é removido quando keep_logged=False."""
    prefs_module.save_auth_session("at", "rt", keep_logged=True)
    assert prefs_module.load_auth_session()["access_token"] == "at"

    prefs_module.save_auth_session("ignored", "ignored", keep_logged=False)
    data = prefs_module.load_auth_session()
    assert data == {}


def test_load_auth_session_no_file(temp_prefs_dir: Path) -> None:
    """Testa carregar auth_session quando arquivo não existe."""
    data = prefs_module.load_auth_session()
    assert data == {}


def test_load_auth_session_corrupted_json(temp_prefs_dir: Path) -> None:
    """Testa que JSON corrompido remove arquivo e retorna {}."""
    path = Path(prefs_module._auth_session_path())
    path.write_text("{ invalid json", encoding="utf-8")

    data = prefs_module.load_auth_session()
    assert data == {}
    # Arquivo deve ter sido removido
    assert not path.exists()


def test_load_auth_session_invalid_structure(temp_prefs_dir: Path) -> None:
    """Testa que estrutura não-dict retorna {}."""
    path = Path(prefs_module._auth_session_path())
    path.write_text('"string_not_dict"', encoding="utf-8")

    data = prefs_module.load_auth_session()
    assert data == {}


def test_load_auth_session_missing_required_fields(temp_prefs_dir: Path) -> None:
    """Testa que sessão incompleta (sem tokens) retorna {}."""
    path = Path(prefs_module._auth_session_path())
    # Faltando refresh_token
    path.write_text('{"access_token": "at", "created_at": "2025-01-01T00:00:00Z"}', encoding="utf-8")

    data = prefs_module.load_auth_session()
    assert data == {}


def test_load_auth_session_empty_tokens(temp_prefs_dir: Path) -> None:
    """Testa que tokens vazios retornam {}."""
    path = Path(prefs_module._auth_session_path())
    path.write_text(
        '{"access_token": "", "refresh_token": "rt", "created_at": "2025-01-01T00:00:00Z"}', encoding="utf-8"
    )

    data = prefs_module.load_auth_session()
    assert data == {}


def test_clear_auth_session(temp_prefs_dir: Path) -> None:
    """Testa limpar sessão de autenticação."""
    prefs_module.save_auth_session("at", "rt", keep_logged=True)
    path = Path(prefs_module._auth_session_path())
    assert path.exists()

    prefs_module.clear_auth_session()
    assert not path.exists()


def test_clear_auth_session_no_file(temp_prefs_dir: Path) -> None:
    """Testa que clear_auth_session não falha se arquivo não existe."""
    # Não deve crashar
    prefs_module.clear_auth_session()


def test_clear_auth_session_error_handling(temp_prefs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que erro ao remover arquivo é tratado."""
    prefs_module.save_auth_session("at", "rt", keep_logged=True)

    # Mockar os.remove para lançar exceção
    original_remove = os.remove

    def mock_remove(path):
        if "auth_session" in str(path):
            raise OSError("Mock error")
        return original_remove(path)

    monkeypatch.setattr("os.remove", mock_remove)

    # Não deve crashar
    prefs_module.clear_auth_session()


def test_load_auth_session_remove_error_handling(temp_prefs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que erro ao remover arquivo corrompido é tratado."""
    path = Path(prefs_module._auth_session_path())
    path.write_text("{ invalid", encoding="utf-8")

    # Mockar os.remove para lançar exceção
    original_remove = os.remove

    def mock_remove(path_to_remove):
        if "auth_session" in str(path_to_remove):
            raise OSError("Mock remove error")
        return original_remove(path_to_remove)

    monkeypatch.setattr("os.remove", mock_remove)

    # Não deve crashar
    data = prefs_module.load_auth_session()
    assert data == {}


# ============================================================================
# Testes para browser_state (last_prefix)
# ============================================================================


def test_load_last_prefix_no_file(temp_prefs_dir: Path) -> None:
    """Testa carregar prefixo quando arquivo não existe."""
    result = prefs_module.load_last_prefix("some_key")
    assert result == ""


def test_save_and_load_last_prefix(temp_prefs_dir: Path) -> None:
    """Testa salvar e carregar último prefixo."""
    prefs_module.save_last_prefix("folder_key", "abc/123")
    loaded = prefs_module.load_last_prefix("folder_key")
    assert loaded == "abc/123"


def test_load_last_prefix_numeric_value(temp_prefs_dir: Path) -> None:
    """Testa que valor numérico é convertido para string."""
    path = Path(prefs_module._browser_state_path())
    path.write_text(json.dumps({"k": 123}), encoding="utf-8")

    result = prefs_module.load_last_prefix("k")
    assert result == "123"


def test_load_last_prefix_corrupted_json(temp_prefs_dir: Path) -> None:
    """Testa que JSON corrompido retorna string vazia."""
    path = Path(prefs_module._browser_state_path())
    path.write_text("bad json", encoding="utf-8")

    result = prefs_module.load_last_prefix("k")
    assert result == ""


def test_load_last_prefix_null_value(temp_prefs_dir: Path) -> None:
    """Testa que valor null retorna string vazia."""
    path = Path(prefs_module._browser_state_path())
    path.write_text(json.dumps({"k": None}), encoding="utf-8")

    result = prefs_module.load_last_prefix("k")
    assert result == ""


def test_save_last_prefix_preserves_other_keys(temp_prefs_dir: Path) -> None:
    """Testa que salvar prefixo preserva outras chaves."""
    prefs_module.save_last_prefix("key1", "value1")
    prefs_module.save_last_prefix("key2", "value2")

    assert prefs_module.load_last_prefix("key1") == "value1"
    assert prefs_module.load_last_prefix("key2") == "value2"


# ============================================================================
# Testes para browser_status_map
# ============================================================================


def test_load_browser_status_map_no_file(temp_prefs_dir: Path) -> None:
    """Testa carregar mapa de status quando arquivo não existe."""
    result = prefs_module.load_browser_status_map("key")
    assert result == {}


def test_save_and_load_browser_status_map(temp_prefs_dir: Path) -> None:
    """Testa salvar e carregar mapa de status do browser."""
    mapping = {"root": "ok", "child": "open"}
    prefs_module.save_browser_status_map("key", mapping)

    loaded = prefs_module.load_browser_status_map("key")
    assert loaded == mapping


def test_load_browser_status_map_corrupted_json(temp_prefs_dir: Path) -> None:
    """Testa que JSON corrompido retorna {}."""
    path = Path(prefs_module._browser_status_path())
    path.write_text("{ bad", encoding="utf-8")

    result = prefs_module.load_browser_status_map("k")
    assert result == {}


def test_load_browser_status_map_type_conversion(temp_prefs_dir: Path) -> None:
    """Testa que tipos variados são convertidos para string."""
    path = Path(prefs_module._browser_status_path())
    path.write_text(json.dumps({"k": {"a": 1, 2: 3, "b": True}}), encoding="utf-8")

    result = prefs_module.load_browser_status_map("k")
    assert result == {"a": "1", "2": "3", "b": "True"}


def test_load_browser_status_map_non_dict_value(temp_prefs_dir: Path) -> None:
    """Testa que valor não-dict retorna {}."""
    path = Path(prefs_module._browser_status_path())
    path.write_text(json.dumps({"k": "not_a_dict"}), encoding="utf-8")

    result = prefs_module.load_browser_status_map("k")
    assert result == {}


def test_save_browser_status_map_preserves_other_keys(temp_prefs_dir: Path) -> None:
    """Testa que salvar mapa preserva outras chaves."""
    prefs_module.save_browser_status_map("key1", {"a": "1"})
    prefs_module.save_browser_status_map("key2", {"b": "2"})

    assert prefs_module.load_browser_status_map("key1") == {"a": "1"}
    assert prefs_module.load_browser_status_map("key2") == {"b": "2"}


# ============================================================================
# Testes de integração e edge cases
# ============================================================================


def test_multiple_file_types_coexist(temp_prefs_dir: Path) -> None:
    """Testa que diferentes tipos de arquivos de preferências coexistem."""
    # Salvar diferentes tipos de prefs
    prefs_module.save_columns_visibility("user@test.com", {"col1": True})
    prefs_module.save_login_prefs("user@test.com", True)
    prefs_module.save_auth_session("at", "rt", keep_logged=True)
    prefs_module.save_last_prefix("folder", "abc")
    prefs_module.save_browser_status_map("key", {"status": "ok"})

    # Verificar que todos os arquivos existem
    assert (temp_prefs_dir / "columns_visibility.json").exists()
    assert (temp_prefs_dir / "login_prefs.json").exists()
    assert (temp_prefs_dir / "auth_session.json").exists()
    assert (temp_prefs_dir / "browser_state.json").exists()
    assert (temp_prefs_dir / "browser_status.json").exists()

    # Verificar que todos podem ser lidos corretamente
    assert prefs_module.load_columns_visibility("user@test.com") == {"col1": True}
    assert prefs_module.load_login_prefs()["email"] == "user@test.com"
    assert prefs_module.load_auth_session()["access_token"] == "at"
    assert prefs_module.load_last_prefix("folder") == "abc"
    assert prefs_module.load_browser_status_map("key") == {"status": "ok"}


def test_unicode_handling(temp_prefs_dir: Path) -> None:
    """Testa que caracteres Unicode são tratados corretamente."""
    email = "usuário@tëst.côm"
    prefs_module.save_login_prefs(email, True)

    data = prefs_module.load_login_prefs()
    assert data["email"] == email

    # Testar em columns_visibility também
    prefs_module.save_columns_visibility(email, {"coluna_ação": True})
    loaded = prefs_module.load_columns_visibility(email)
    assert loaded == {"coluna_ação": True}


def test_empty_string_keys_and_values(temp_prefs_dir: Path) -> None:
    """Testa comportamento com strings vazias."""
    prefs_module.save_login_prefs("", True)
    data = prefs_module.load_login_prefs()
    assert data["email"] == ""

    prefs_module.save_last_prefix("", "")
    result = prefs_module.load_last_prefix("")
    assert result == ""


def test_save_auth_session_exception_handling(temp_prefs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa que exceções durante save_auth_session são capturadas."""
    # Forçar erro ao criar diretório
    original_makedirs = os.makedirs

    def mock_makedirs(*args, **kwargs):
        if "auth_session" in str(args[0]):
            raise OSError("Mock makedirs error")
        return original_makedirs(*args, **kwargs)

    monkeypatch.setattr("os.makedirs", mock_makedirs)

    # Não deve crashar
    prefs_module.save_auth_session("at", "rt", keep_logged=True)


@pytest.mark.skipif(not HAS_FILELOCK, reason="Requer filelock instalado")
def test_auth_session_with_filelock(temp_prefs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa salvamento de auth_session com filelock."""
    monkeypatch.setattr("src.utils.prefs.HAS_FILELOCK", True)

    prefs_module.save_auth_session("at", "rt", keep_logged=True)
    data = prefs_module.load_auth_session()

    assert data["access_token"] == "at"
    assert data["refresh_token"] == "rt"


@pytest.mark.skipif(not HAS_FILELOCK, reason="Requer filelock instalado")
def test_login_prefs_with_filelock(temp_prefs_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Testa salvamento de login_prefs com filelock."""
    monkeypatch.setattr("src.utils.prefs.HAS_FILELOCK", True)

    prefs_module.save_login_prefs("user@test.com", True)
    data = prefs_module.load_login_prefs()

    assert data["email"] == "user@test.com"
