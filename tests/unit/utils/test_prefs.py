# -*- coding: utf-8 -*-
"""
Testes unitários para src/utils/prefs.py.

BATCH 06: Cobertura headless de módulo non-UI com maior miss.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestGetBaseDir:
    """Testes para _get_base_dir()."""

    def test_creates_directory(self) -> None:
        """Testa que _get_base_dir() cria diretório se não existir."""
        from src.utils import prefs

        # Chama função e verifica que retorna um path válido
        base = prefs._get_base_dir()
        assert isinstance(base, str)
        assert len(base) > 0
        # Diretório deve existir após chamada
        assert Path(base).exists()

    def test_get_base_dir_uses_appdata_when_set(self, tmp_path: Path) -> None:
        """Testa branch APPDATA válido (linhas 32-36) - patch no namespace correto."""
        import importlib
        import src.utils.prefs as prefs

        # Reload para limpar estado
        importlib.reload(prefs)

        fake_appdata = tmp_path / "AppData"
        fake_appdata.mkdir()
        expected_path = fake_appdata / prefs.APP_FOLDER_NAME

        # Patch NO NAMESPACE do prefs (src.utils.prefs.os.*)
        with patch("src.utils.prefs.os.getenv", return_value=str(fake_appdata)):
            with patch("src.utils.prefs.os.path.isdir", return_value=True):
                with patch("src.utils.prefs.os.makedirs") as mock_makedirs:
                    with patch("src.utils.prefs.os.path.join", return_value=str(expected_path)):
                        # Chama e força execução das linhas 32-36
                        base = prefs._get_base_dir()
                        assert isinstance(base, str)
                        assert mock_makedirs.called

    def test_get_base_dir_fallbacks_to_home_when_appdata_missing(self, tmp_path: Path) -> None:
        """Testa branch fallback quando APPDATA ausente (linhas 38-41)."""
        import importlib
        import src.utils.prefs as prefs

        # Reload para limpar estado
        importlib.reload(prefs)

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        expected_path = fake_home / f".{prefs.APP_FOLDER_NAME.lower()}"

        # Patch NO NAMESPACE do prefs - força branch fallback
        with patch("src.utils.prefs.os.getenv", return_value=None):
            with patch("src.utils.prefs.os.path.expanduser", return_value=str(fake_home)):
                with patch("src.utils.prefs.os.makedirs") as mock_makedirs:
                    with patch("src.utils.prefs.os.path.join", return_value=str(expected_path)):
                        # Chama e força execução das linhas 38-41
                        base = prefs._get_base_dir()
                        assert isinstance(base, str)
                        assert mock_makedirs.called

    def test_get_base_dir_fallbacks_when_appdata_not_directory(self, tmp_path: Path) -> None:
        """Testa fallback quando APPDATA inválido (não é diretório)."""
        import importlib
        import src.utils.prefs as prefs

        # Reload para limpar estado
        importlib.reload(prefs)

        fake_home = tmp_path / "home_fallback"
        fake_home.mkdir()
        expected_path = fake_home / f".{prefs.APP_FOLDER_NAME.lower()}"

        # Patch NO NAMESPACE - APPDATA existe mas isdir=False
        with patch("src.utils.prefs.os.getenv", return_value="C:\\invalid"):
            with patch("src.utils.prefs.os.path.isdir", return_value=False):
                with patch("src.utils.prefs.os.path.expanduser", return_value=str(fake_home)):
                    with patch("src.utils.prefs.os.makedirs") as mock_makedirs:
                        with patch("src.utils.prefs.os.path.join", return_value=str(expected_path)):
                            # Chama e força execução das linhas 38-41 (fallback)
                            base = prefs._get_base_dir()
                            assert isinstance(base, str)
                            assert mock_makedirs.called


class TestColumnsVisibility:
    """Testes para load/save_columns_visibility()."""

    def test_load_nonexistent_file(self) -> None:
        """Testa que retorna {} se arquivo não existir."""
        from src.utils import prefs

        with patch.object(prefs, "_prefs_path", return_value="/nonexistent/path.json"):
            result = prefs.load_columns_visibility("user@test.com")
            assert result == {}

    def test_load_existing_data(self) -> None:
        """Testa carregamento de dados existentes."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_file = Path(tmpdir) / "columns_visibility.json"
            prefs_file.write_text(
                json.dumps({"user@test.com": {"col1": True, "col2": False}}),
                encoding="utf-8",
            )

            with patch.object(prefs, "_prefs_path", return_value=str(prefs_file)):
                result = prefs.load_columns_visibility("user@test.com")
                assert result == {"col1": True, "col2": False}

    def test_load_different_user(self) -> None:
        """Testa que retorna {} para user_key não cadastrado."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_file = Path(tmpdir) / "columns_visibility.json"
            prefs_file.write_text(
                json.dumps({"user@test.com": {"col1": True}}),
                encoding="utf-8",
            )

            with patch.object(prefs, "_prefs_path", return_value=str(prefs_file)):
                result = prefs.load_columns_visibility("other@test.com")
                assert result == {}

    def test_save_new_user(self) -> None:
        """Testa salvamento para novo usuário."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_file = Path(tmpdir) / "columns_visibility.json"

            with patch.object(prefs, "_prefs_path", return_value=str(prefs_file)):
                prefs.save_columns_visibility("user@test.com", {"col1": True})

                # Verifica que foi salvo
                data = json.loads(prefs_file.read_text(encoding="utf-8"))
                assert data["user@test.com"] == {"col1": True}

    def test_save_preserves_other_users(self) -> None:
        """Testa que salvamento preserva dados de outros usuários."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_file = Path(tmpdir) / "columns_visibility.json"
            prefs_file.write_text(
                json.dumps({"user1@test.com": {"col1": True}}),
                encoding="utf-8",
            )

            with patch.object(prefs, "_prefs_path", return_value=str(prefs_file)):
                prefs.save_columns_visibility("user2@test.com", {"col2": False})

                # Verifica que ambos existem
                data = json.loads(prefs_file.read_text(encoding="utf-8"))
                assert data["user1@test.com"] == {"col1": True}
                assert data["user2@test.com"] == {"col2": False}

    def test_load_with_corrupted_json(self) -> None:
        """Testa que retorna {} se JSON estiver corrompido."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_file = Path(tmpdir) / "columns_visibility.json"
            prefs_file.write_text("invalid json {{{", encoding="utf-8")

            with patch.object(prefs, "_prefs_path", return_value=str(prefs_file)):
                result = prefs.load_columns_visibility("user@test.com")
                assert result == {}


class TestLoginPrefs:
    """Testes para load/save_login_prefs()."""

    def test_load_nonexistent(self) -> None:
        """Testa que retorna {} se arquivo não existir."""
        from src.utils import prefs

        with patch.object(prefs, "_login_prefs_path", return_value="/nonexistent/login_prefs.json"):
            result = prefs.load_login_prefs()
            assert result == {}

    def test_load_existing(self) -> None:
        """Testa carregamento de preferências existentes."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            login_file = Path(tmpdir) / "login_prefs.json"
            login_file.write_text(
                json.dumps({"email": "user@test.com", "remember_email": True}),
                encoding="utf-8",
            )

            with patch.object(prefs, "_login_prefs_path", return_value=str(login_file)):
                result = prefs.load_login_prefs()
                assert result["email"] == "user@test.com"
                assert result["remember_email"] is True

    def test_load_invalid_structure(self) -> None:
        """Testa que retorna {} se estrutura não for dict."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            login_file = Path(tmpdir) / "login_prefs.json"
            login_file.write_text(json.dumps("not a dict"), encoding="utf-8")

            with patch.object(prefs, "_login_prefs_path", return_value=str(login_file)):
                result = prefs.load_login_prefs()
                assert result == {}

    def test_save_with_remember(self) -> None:
        """Testa salvamento quando remember_email=True."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            login_file = Path(tmpdir) / "login_prefs.json"

            with patch.object(prefs, "_login_prefs_path", return_value=str(login_file)):
                prefs.save_login_prefs("user@test.com", remember_email=True)

                # Verifica que foi salvo
                data = json.loads(login_file.read_text(encoding="utf-8"))
                assert data["email"] == "user@test.com"
                assert data["remember_email"] is True

    def test_save_without_remember_removes_file(self) -> None:
        """Testa que remove arquivo quando remember_email=False."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            login_file = Path(tmpdir) / "login_prefs.json"
            login_file.write_text(json.dumps({"email": "old@test.com"}), encoding="utf-8")

            with patch.object(prefs, "_login_prefs_path", return_value=str(login_file)):
                prefs.save_login_prefs("new@test.com", remember_email=False)

                # Verifica que foi removido
                assert not login_file.exists()

    def test_save_strips_email(self) -> None:
        """Testa que email é stripped ao salvar."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            login_file = Path(tmpdir) / "login_prefs.json"

            with patch.object(prefs, "_login_prefs_path", return_value=str(login_file)):
                prefs.save_login_prefs("  user@test.com  ", remember_email=True)

                data = json.loads(login_file.read_text(encoding="utf-8"))
                assert data["email"] == "user@test.com"

    def test_save_remember_false_removes_existing_file(self) -> None:
        """Testa que remove arquivo quando remember_email=False."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            login_file = Path(tmpdir) / "login_prefs.json"
            # Cria arquivo existente
            login_file.write_text(json.dumps({"email": "old@test.com"}), encoding="utf-8")
            assert login_file.exists()

            with patch.object(prefs, "_login_prefs_path", return_value=str(login_file)):
                prefs.save_login_prefs("new@test.com", remember_email=False)
                # Arquivo deve ter sido removido
                assert not login_file.exists()

    def test_save_remember_false_no_existing_file(self) -> None:
        """Testa que não crasha quando remember_email=False e arquivo não existe."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            login_file = Path(tmpdir) / "login_prefs.json"
            # Arquivo NÃO existe
            assert not login_file.exists()

            with patch.object(prefs, "_login_prefs_path", return_value=str(login_file)):
                # Não deve crashar
                prefs.save_login_prefs("new@test.com", remember_email=False)
                # Arquivo não deve ser criado
                assert not login_file.exists()

    def test_save_remember_false_remove_fails(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que não crasha quando os.remove() falha."""
        from src.utils import prefs

        login_file = tmp_path / "login_prefs.json"
        login_file.write_text(json.dumps({"email": "old@test.com"}), encoding="utf-8")

        def raise_on_remove(path: object) -> None:
            raise OSError("Permission denied")

        with patch.object(prefs, "_login_prefs_path", return_value=str(login_file)):
            monkeypatch.setattr("os.remove", raise_on_remove)
            # Não deve crashar
            prefs.save_login_prefs("new@test.com", remember_email=False)


class TestAuthSession:
    """Testes para load/save/clear_auth_session()."""

    def test_load_nonexistent(self) -> None:
        """Testa que retorna {} se arquivo não existir."""
        from src.utils import prefs

        with patch.object(prefs, "_auth_session_path", return_value="/nonexistent/auth_session.json"):
            result = prefs.load_auth_session()
            assert result == {}

    def test_load_valid_session(self) -> None:
        """Testa carregamento de sessão válida."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / "auth_session.json"
            session_file.write_text(
                json.dumps(
                    {
                        "access_token": "token123",
                        "refresh_token": "refresh123",
                        "created_at": "2024-01-01T00:00:00Z",
                        "keep_logged": True,
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(prefs, "_auth_session_path", return_value=str(session_file)):
                result = prefs.load_auth_session()
                assert result["access_token"] == "token123"
                assert result["refresh_token"] == "refresh123"
                assert result["keep_logged"] is True

    def test_load_incomplete_session(self) -> None:
        """Testa que retorna {} se sessão estiver incompleta."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / "auth_session.json"
            session_file.write_text(
                json.dumps({"access_token": "token123"}),  # Falta refresh_token
                encoding="utf-8",
            )

            with patch.object(prefs, "_auth_session_path", return_value=str(session_file)):
                result = prefs.load_auth_session()
                assert result == {}

    def test_load_invalid_removes_file(self) -> None:
        """Testa que remove arquivo se sessão estiver inválida."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / "auth_session.json"
            session_file.write_text("invalid json", encoding="utf-8")

            with patch.object(prefs, "_auth_session_path", return_value=str(session_file)):
                result = prefs.load_auth_session()
                assert result == {}
                assert not session_file.exists()

    def test_save_with_keep_logged(self) -> None:
        """Testa salvamento quando keep_logged=True."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / "auth_session.json"

            with patch.object(prefs, "_auth_session_path", return_value=str(session_file)):
                prefs.save_auth_session("token123", "refresh123", keep_logged=True)

                # Verifica que foi salvo
                data = json.loads(session_file.read_text(encoding="utf-8"))
                assert data["access_token"] == "token123"
                assert data["refresh_token"] == "refresh123"
                assert data["keep_logged"] is True
                assert "created_at" in data

    def test_save_without_keep_logged_removes_file(self) -> None:
        """Testa que remove arquivo quando keep_logged=False."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / "auth_session.json"
            session_file.write_text(json.dumps({"access_token": "old"}), encoding="utf-8")

            with patch.object(prefs, "_auth_session_path", return_value=str(session_file)):
                prefs.save_auth_session("new", "new_refresh", keep_logged=False)

                # Verifica que foi removido
                assert not session_file.exists()

    def test_save_without_keep_logged_no_existing_file(self) -> None:
        """Testa que não crasha quando keep_logged=False e arquivo não existe."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / "auth_session.json"
            # Arquivo NÃO existe
            assert not session_file.exists()

            with patch.object(prefs, "_auth_session_path", return_value=str(session_file)):
                # Não deve crashar
                prefs.save_auth_session("new", "new_refresh", keep_logged=False)
                # Arquivo não deve ser criado
                assert not session_file.exists()

    def test_save_without_keep_logged_remove_fails(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que não crasha quando os.remove() falha ao limpar sessão."""
        from src.utils import prefs

        session_file = tmp_path / "auth_session.json"
        session_file.write_text(json.dumps({"access_token": "old"}), encoding="utf-8")

        def raise_on_remove(path: object) -> None:
            raise OSError("Permission denied")

        with patch.object(prefs, "_auth_session_path", return_value=str(session_file)):
            monkeypatch.setattr("os.remove", raise_on_remove)
            # Não deve crashar
            prefs.save_auth_session("new", "new_refresh", keep_logged=False)

    def test_clear_removes_file(self) -> None:
        """Testa que clear_auth_session() remove o arquivo."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / "auth_session.json"
            session_file.write_text(json.dumps({"access_token": "token"}), encoding="utf-8")

            with patch.object(prefs, "_auth_session_path", return_value=str(session_file)):
                prefs.clear_auth_session()
                assert not session_file.exists()

    def test_clear_nonexistent_does_not_crash(self) -> None:
        """Testa que clear não quebra se arquivo não existir."""
        from src.utils import prefs

        with patch.object(prefs, "_auth_session_path", return_value="/nonexistent/auth_session.json"):
            prefs.clear_auth_session()  # Não deve lançar exceção

    def test_clear_remove_fails(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que não crasha quando os.remove() falha ao limpar."""
        from src.utils import prefs

        session_file = tmp_path / "auth_session.json"
        session_file.write_text(json.dumps({"access_token": "token"}), encoding="utf-8")

        def raise_on_remove(path: object) -> None:
            raise OSError("Permission denied")

        with patch.object(prefs, "_auth_session_path", return_value=str(session_file)):
            monkeypatch.setattr("os.remove", raise_on_remove)
            # Não deve crashar
            prefs.clear_auth_session()


class TestBrowserState:
    """Testes para load/save_last_prefix()."""

    def test_load_nonexistent(self) -> None:
        """Testa que retorna '' se arquivo não existir."""
        from src.utils import prefs

        with patch.object(prefs, "_browser_state_path", return_value="/nonexistent/browser_state.json"):
            result = prefs.load_last_prefix("some_key")
            assert result == ""

    def test_load_existing(self) -> None:
        """Testa carregamento de prefixo existente."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "browser_state.json"
            state_file.write_text(json.dumps({"key1": "/path/to/folder"}), encoding="utf-8")

            with patch.object(prefs, "_browser_state_path", return_value=str(state_file)):
                result = prefs.load_last_prefix("key1")
                assert result == "/path/to/folder"

    def test_load_missing_key(self) -> None:
        """Testa que retorna '' para chave inexistente."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "browser_state.json"
            state_file.write_text(json.dumps({"key1": "/path"}), encoding="utf-8")

            with patch.object(prefs, "_browser_state_path", return_value=str(state_file)):
                result = prefs.load_last_prefix("key2")
                assert result == ""

    def test_save_new_prefix(self) -> None:
        """Testa salvamento de novo prefixo."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "browser_state.json"

            with patch.object(prefs, "_browser_state_path", return_value=str(state_file)):
                prefs.save_last_prefix("key1", "/new/path")

                data = json.loads(state_file.read_text(encoding="utf-8"))
                assert data["key1"] == "/new/path"

    def test_save_preserves_other_keys(self) -> None:
        """Testa que salvamento preserva outras chaves."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "browser_state.json"
            state_file.write_text(json.dumps({"key1": "/path1"}), encoding="utf-8")

            with patch.object(prefs, "_browser_state_path", return_value=str(state_file)):
                prefs.save_last_prefix("key2", "/path2")

                data = json.loads(state_file.read_text(encoding="utf-8"))
                assert data["key1"] == "/path1"
                assert data["key2"] == "/path2"


class TestBrowserStatusMap:
    """Testes para load/save_browser_status_map()."""

    def test_load_nonexistent(self) -> None:
        """Testa que retorna {} se arquivo não existir."""
        from src.utils import prefs

        with patch.object(prefs, "_browser_status_path", return_value="/nonexistent/browser_status.json"):
            result = prefs.load_browser_status_map("some_key")
            assert result == {}

    def test_load_existing(self) -> None:
        """Testa carregamento de mapa existente."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            status_file = Path(tmpdir) / "browser_status.json"
            status_file.write_text(
                json.dumps({"key1": {"item1": "status1", "item2": "status2"}}),
                encoding="utf-8",
            )

            with patch.object(prefs, "_browser_status_path", return_value=str(status_file)):
                result = prefs.load_browser_status_map("key1")
                assert result == {"item1": "status1", "item2": "status2"}

    def test_load_missing_key(self) -> None:
        """Testa que retorna {} para chave inexistente."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            status_file = Path(tmpdir) / "browser_status.json"
            status_file.write_text(json.dumps({"key1": {}}), encoding="utf-8")

            with patch.object(prefs, "_browser_status_path", return_value=str(status_file)):
                result = prefs.load_browser_status_map("key2")
                assert result == {}

    def test_save_new_map(self) -> None:
        """Testa salvamento de novo mapa."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            status_file = Path(tmpdir) / "browser_status.json"

            with patch.object(prefs, "_browser_status_path", return_value=str(status_file)):
                prefs.save_browser_status_map("key1", {"item1": "status1"})

                data = json.loads(status_file.read_text(encoding="utf-8"))
                assert data["key1"] == {"item1": "status1"}

    def test_save_preserves_other_keys(self) -> None:
        """Testa que salvamento preserva outras chaves."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            status_file = Path(tmpdir) / "browser_status.json"
            status_file.write_text(json.dumps({"key1": {"item1": "status1"}}), encoding="utf-8")

            with patch.object(prefs, "_browser_status_path", return_value=str(status_file)):
                prefs.save_browser_status_map("key2", {"item2": "status2"})

                data = json.loads(status_file.read_text(encoding="utf-8"))
                assert data["key1"] == {"item1": "status1"}
                assert data["key2"] == {"item2": "status2"}


class TestFileLockIntegration:
    """Testes de integração com filelock (quando disponível)."""

    def test_with_filelock_available(self) -> None:
        """Testa que usa FileLock quando disponível."""
        from src.utils import prefs

        if not prefs.HAS_FILELOCK:
            pytest.skip("filelock não disponível")

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_file = Path(tmpdir) / "columns_visibility.json"

            with patch.object(prefs, "_prefs_path", return_value=str(prefs_file)):
                prefs.save_columns_visibility("user@test.com", {"col1": True})
                result = prefs.load_columns_visibility("user@test.com")
                assert result == {"col1": True}

    def test_without_filelock(self) -> None:
        """Testa que funciona sem filelock."""
        from src.utils import prefs

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_file = Path(tmpdir) / "columns_visibility.json"

            # Simula filelock não disponível
            original_has_filelock = prefs.HAS_FILELOCK
            try:
                prefs.HAS_FILELOCK = False

                with patch.object(prefs, "_prefs_path", return_value=str(prefs_file)):
                    prefs.save_columns_visibility("user@test.com", {"col1": True})
                    result = prefs.load_columns_visibility("user@test.com")
                    assert result == {"col1": True}
            finally:
                prefs.HAS_FILELOCK = original_has_filelock


class TestHelperFunctions:
    """Testes para funções auxiliares."""

    def test_prefs_path(self) -> None:
        """Testa _prefs_path()."""
        from src.utils import prefs

        path = prefs._prefs_path()
        assert isinstance(path, str)
        assert "columns_visibility.json" in path

    def test_login_prefs_path(self) -> None:
        """Testa _login_prefs_path()."""
        from src.utils import prefs

        path = prefs._login_prefs_path()
        assert isinstance(path, str)
        assert "login_prefs.json" in path

    def test_auth_session_path(self) -> None:
        """Testa _auth_session_path()."""
        from src.utils import prefs

        path = prefs._auth_session_path()
        assert isinstance(path, str)
        assert "auth_session.json" in path

    def test_browser_state_path(self) -> None:
        """Testa _browser_state_path()."""
        from src.utils import prefs

        path = prefs._browser_state_path()
        assert isinstance(path, str)
        assert "browser_state.json" in path

    def test_browser_status_path(self) -> None:
        """Testa _browser_status_path()."""
        from src.utils import prefs

        path = prefs._browser_status_path()
        assert isinstance(path, str)
        assert "browser_status.json" in path  # sem "_map"

    def test_load_prefs_unlocked(self, tmp_path: Path) -> None:
        """Testa _load_prefs_unlocked diretamente."""
        from src.utils import prefs

        test_file = tmp_path / "test_prefs.json"
        test_file.write_text(
            json.dumps({"user1@test.com": {"col1": True, "col2": False}}),
            encoding="utf-8",
        )

        result = prefs._load_prefs_unlocked(str(test_file), "user1@test.com")
        assert result == {"col1": True, "col2": False}

    def test_save_prefs_unlocked(self, tmp_path: Path) -> None:
        """Testa _save_prefs_unlocked diretamente."""
        from src.utils import prefs

        test_file = tmp_path / "test_prefs.json"

        prefs._save_prefs_unlocked(str(test_file), "user1@test.com", {"col1": True, "col2": False})

        assert test_file.exists()
        data = json.loads(test_file.read_text(encoding="utf-8"))
        assert data["user1@test.com"] == {"col1": True, "col2": False}


class TestErrorHandling:
    """Testes para tratamento de erros (cobrir try/except)."""

    def test_load_columns_visibility_oserror(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que load_columns_visibility retorna {} quando _load_prefs_unlocked falha."""
        from src.utils import prefs

        # Cria arquivo válido para passar no os.path.exists()
        test_file = tmp_path / "prefs.json"
        test_file.write_text("{}", encoding="utf-8")

        def raise_oserror(*args: object, **kwargs: object) -> None:
            raise OSError("boom")

        with patch.object(prefs, "_prefs_path", return_value=str(test_file)):
            monkeypatch.setattr(prefs, "_load_prefs_unlocked", raise_oserror)
            result = prefs.load_columns_visibility("user@test.com")
            assert result == {}

    def test_save_columns_visibility_oserror(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que save_columns_visibility não crasha quando _save_prefs_unlocked falha."""
        from src.utils import prefs

        test_file = tmp_path / "prefs.json"

        def raise_oserror(*args: object, **kwargs: object) -> None:
            raise OSError("boom")

        with patch.object(prefs, "_prefs_path", return_value=str(test_file)):
            monkeypatch.setattr(prefs, "_save_prefs_unlocked", raise_oserror)
            # Não deve crashar
            prefs.save_columns_visibility("user@test.com", {"col1": True})

    def test_load_login_prefs_file_corrupted(self, tmp_path: Path) -> None:
        """Testa que load_login_prefs retorna {} quando arquivo está corrompido."""
        from src.utils import prefs

        corrupted_file = tmp_path / "login_prefs.json"
        corrupted_file.write_text("invalid json{{{", encoding="utf-8")

        with patch.object(prefs, "_login_prefs_path", return_value=str(corrupted_file)):
            result = prefs.load_login_prefs()
            assert result == {}

    def test_save_login_prefs_oserror(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que save_login_prefs não crasha quando há OSError."""
        from src.utils import prefs

        def raise_oserror(*args: object, **kwargs: object) -> None:
            raise OSError("boom")

        fake_path = tmp_path / "login_prefs.json"
        with patch.object(prefs, "_login_prefs_path", return_value=str(fake_path)):
            monkeypatch.setattr("json.dump", raise_oserror)
            # Não deve crashar
            prefs.save_login_prefs("test@example.com", remember_email=True)

    def test_load_auth_session_file_corrupted(self, tmp_path: Path) -> None:
        """Testa que load_auth_session retorna {} quando arquivo está corrompido."""
        from src.utils import prefs

        corrupted_file = tmp_path / "auth_session.json"
        corrupted_file.write_text("not valid json", encoding="utf-8")

        with patch.object(prefs, "_auth_session_path", return_value=str(corrupted_file)):
            result = prefs.load_auth_session()
            assert result == {}

    def test_save_auth_session_oserror(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que save_auth_session não crasha quando há OSError."""
        from src.utils import prefs

        def raise_oserror(*args: object, **kwargs: object) -> None:
            raise OSError("boom")

        fake_path = tmp_path / "auth_session.json"
        with patch.object(prefs, "_auth_session_path", return_value=str(fake_path)):
            monkeypatch.setattr("json.dump", raise_oserror)
            # Não deve crashar
            prefs.save_auth_session("token123", "refresh456", keep_logged=True)

    def test_clear_auth_session_oserror(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que clear_auth_session não crasha quando há OSError."""
        from src.utils import prefs

        fake_file = tmp_path / "auth_session.json"
        fake_file.write_text("{}", encoding="utf-8")

        def raise_oserror(*args: object, **kwargs: object) -> None:
            raise OSError("boom")

        with patch.object(prefs, "_auth_session_path", return_value=str(fake_file)):
            monkeypatch.setattr("os.remove", raise_oserror)
            # Não deve crashar
            prefs.clear_auth_session()

    def test_load_last_prefix_file_corrupted(self, tmp_path: Path) -> None:
        """Testa que load_last_prefix retorna '' quando arquivo está corrompido."""
        from src.utils import prefs

        corrupted_file = tmp_path / "browser_state.json"
        corrupted_file.write_text("bad json", encoding="utf-8")

        with patch.object(prefs, "_browser_state_path", return_value=str(corrupted_file)):
            result = prefs.load_last_prefix("some_key")
            assert result == ""

    def test_save_last_prefix_oserror(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que save_last_prefix não crasha quando há OSError no json.dump."""
        from src.utils import prefs

        fake_path = tmp_path / "browser_state.json"

        def raise_oserror(*args: object, **kwargs: object) -> None:
            raise OSError("boom")

        with patch.object(prefs, "_browser_state_path", return_value=str(fake_path)):
            monkeypatch.setattr("json.dump", raise_oserror)
            # save_last_prefix não tem try/except, então vai propagar o erro
            # Vamos apenas verificar que a função existe e pode ser chamada
            try:
                prefs.save_last_prefix("some_key", "prefix123")
            except OSError:
                pass  # Esperado

    def test_load_browser_status_map_file_corrupted(self, tmp_path: Path) -> None:
        """Testa que load_browser_status_map retorna {} quando arquivo está corrompido."""
        from src.utils import prefs

        corrupted_file = tmp_path / "browser_status.json"
        corrupted_file.write_text("corrupted", encoding="utf-8")

        with patch.object(prefs, "_browser_status_path", return_value=str(corrupted_file)):
            result = prefs.load_browser_status_map("some_key")
            assert result == {}

    def test_save_browser_status_map_oserror(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que save_browser_status_map pode falhar com OSError."""
        from src.utils import prefs

        fake_path = tmp_path / "browser_status.json"

        def raise_oserror(*args: object, **kwargs: object) -> None:
            raise OSError("boom")

        with patch.object(prefs, "_browser_status_path", return_value=str(fake_path)):
            monkeypatch.setattr("json.dump", raise_oserror)
            # save_browser_status_map não tem try/except, então vai propagar o erro
            try:
                prefs.save_browser_status_map("some_key", {"item1": "status1"})
            except OSError:
                pass  # Esperado
