"""
TEST-001 Fase 29 – Cobertura de src/core/commands.py

Objetivo:
    Aumentar cobertura de core/commands.py de 0% para ≥70-85%, testando:
    - Registro/desregistro de comandos
    - Execução de comandos com defaults e kwargs
    - Listagem de comandos
    - Tratamento de erros (comando não encontrado, falha na execução)
    - Comandos built-in bootstrapped automaticamente

Escopo:
    - Não altera lógica de produção
    - Usa mocks para isolar dependências externas (api, theme, upload, etc.)
    - Testa registry pattern e orquestração de operações
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core import commands


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset command registry before each test to avoid pollution."""
    # Save original registry
    original = commands._REGISTRY.copy()
    yield
    # Restore original registry
    commands._REGISTRY.clear()
    commands._REGISTRY.update(original)


@pytest.fixture
def dummy_command():
    """Simple command function for testing."""

    def _cmd(arg1: str, arg2: int = 42) -> dict[str, Any]:
        return {"arg1": arg1, "arg2": arg2}

    return _cmd


@pytest.fixture
def failing_command():
    """Command that raises exception."""

    def _cmd(should_fail: bool = True) -> None:
        if should_fail:
            raise ValueError("Command execution failed")

    return _cmd


# ============================================================================
# TEST: register
# ============================================================================


class TestRegister:
    """Tests for commands.register()"""

    def test_register_command_basic(self, dummy_command):
        """Register a simple command without defaults."""
        commands.register("test:basic", dummy_command, help="Test command")

        assert "test:basic" in commands._REGISTRY
        func, help_text, defaults = commands._REGISTRY["test:basic"]
        assert func == dummy_command
        assert help_text == "Test command"
        assert defaults == {}

    def test_register_command_with_defaults(self, dummy_command):
        """Register command with default kwargs."""
        commands.register("test:defaults", dummy_command, help="With defaults", arg2=100)

        _, _, defaults = commands._REGISTRY["test:defaults"]
        assert defaults == {"arg2": 100}

    def test_register_command_overwrites_existing(self, dummy_command, caplog):
        """Registering same name should overwrite and log warning."""
        commands.register("test:overwrite", dummy_command, help="First")
        commands.register("test:overwrite", lambda: None, help="Second")

        func, help_text, _ = commands._REGISTRY["test:overwrite"]
        assert help_text == "Second"
        assert "already registered" in caplog.text.lower()

    def test_register_command_empty_help(self, dummy_command):
        """Register command with empty help text."""
        commands.register("test:no_help", dummy_command)

        _, help_text, _ = commands._REGISTRY["test:no_help"]
        assert help_text == ""


# ============================================================================
# TEST: unregister
# ============================================================================


class TestUnregister:
    """Tests for commands.unregister()"""

    def test_unregister_existing_command(self, dummy_command):
        """Unregister a command that exists."""
        commands.register("test:remove", dummy_command)
        assert "test:remove" in commands._REGISTRY

        result = commands.unregister("test:remove")

        assert result is True
        assert "test:remove" not in commands._REGISTRY

    def test_unregister_nonexistent_command(self):
        """Unregister a command that doesn't exist."""
        result = commands.unregister("test:nonexistent")

        assert result is False


# ============================================================================
# TEST: run
# ============================================================================


class TestRun:
    """Tests for commands.run()"""

    def test_run_command_basic(self, dummy_command):
        """Run a command with minimal args."""
        commands.register("test:run", dummy_command)

        result = commands.run("test:run", arg1="hello")

        assert result == {"arg1": "hello", "arg2": 42}

    def test_run_command_with_kwargs(self, dummy_command):
        """Run command with custom kwargs."""
        commands.register("test:run", dummy_command)

        result = commands.run("test:run", arg1="world", arg2=999)

        assert result == {"arg1": "world", "arg2": 999}

    def test_run_command_merges_defaults_and_kwargs(self, dummy_command):
        """Run command where defaults are overridden by kwargs."""
        commands.register("test:run", dummy_command, arg2=200)

        # kwargs should override defaults
        result = commands.run("test:run", arg1="test", arg2=300)
        assert result["arg2"] == 300

        # defaults should be used when not provided
        result = commands.run("test:run", arg1="test")
        assert result["arg2"] == 200

    def test_run_nonexistent_command_raises_keyerror(self):
        """Run a command that doesn't exist."""
        with pytest.raises(KeyError, match="Command 'test:missing' not found"):
            commands.run("test:missing")

    def test_run_failing_command_propagates_exception(self, failing_command):
        """Run a command that raises an exception."""
        commands.register("test:fail", failing_command)

        with pytest.raises(ValueError, match="Command execution failed"):
            commands.run("test:fail", should_fail=True)

    def test_run_command_returns_none(self):
        """Run a command that returns None."""

        def _none_cmd() -> None:
            return None

        commands.register("test:none", _none_cmd)

        result = commands.run("test:none")
        assert result is None


# ============================================================================
# TEST: list_commands
# ============================================================================


class TestListCommands:
    """Tests for commands.list_commands()"""

    def test_list_commands_empty_registry(self):
        """List commands when registry is empty."""
        commands._REGISTRY.clear()

        result = commands.list_commands()

        assert result == {}

    def test_list_commands_returns_name_help_mapping(self, dummy_command):
        """List commands returns dict of name -> help."""
        commands._REGISTRY.clear()
        commands.register("cmd1", dummy_command, help="First command")
        commands.register("cmd2", dummy_command, help="Second command")

        result = commands.list_commands()

        assert result == {
            "cmd1": "First command",
            "cmd2": "Second command",
        }

    def test_list_commands_includes_bootstrapped_commands(self):
        """List commands includes built-in bootstrapped commands."""
        result = commands.list_commands()

        # Should include at least some built-in commands
        assert "theme:switch" in result
        assert "upload:folder" in result
        assert "client:search" in result
        assert len(result) >= 8  # 8 built-in commands


# ============================================================================
# TEST: get_command_info
# ============================================================================


class TestGetCommandInfo:
    """Tests for commands.get_command_info()"""

    def test_get_command_info_existing_command(self, dummy_command):
        """Get info for an existing command."""
        commands.register("test:info", dummy_command, help="Info test", arg2=999)

        info = commands.get_command_info("test:info")

        assert info is not None
        assert info["name"] == "test:info"
        assert info["func"] == "_cmd"  # function name
        assert info["help"] == "Info test"
        assert info["defaults"] == {"arg2": 999}

    def test_get_command_info_nonexistent_command(self):
        """Get info for a command that doesn't exist."""
        info = commands.get_command_info("test:missing")

        assert info is None

    def test_get_command_info_lambda_function(self):
        """Get info for a command using lambda."""
        commands.register("test:lambda", lambda x: x * 2, help="Lambda cmd")

        info = commands.get_command_info("test:lambda")

        assert info is not None
        assert info["func"] == "<lambda>"


# ============================================================================
# TEST: Built-in Commands (Bootstrap)
# ============================================================================


class TestBootstrapCommands:
    """Tests for built-in commands registered in _bootstrap_commands()"""

    def test_bootstrap_registers_theme_switch(self):
        """Bootstrap registers theme:switch command."""
        assert "theme:switch" in commands._REGISTRY
        _, help_text, _ = commands._REGISTRY["theme:switch"]
        assert "theme" in help_text.lower()

    def test_bootstrap_registers_upload_folder(self):
        """Bootstrap registers upload:folder command."""
        assert "upload:folder" in commands._REGISTRY
        _, help_text, defaults = commands._REGISTRY["upload:folder"]
        assert "upload" in help_text.lower()
        assert defaults.get("subdir") == "GERAL"

    def test_bootstrap_registers_download_zip(self):
        """Bootstrap registers download:zip command."""
        assert "download:zip" in commands._REGISTRY
        _, help_text, _ = commands._REGISTRY["download:zip"]
        assert "download" in help_text.lower() or "zip" in help_text.lower()

    def test_bootstrap_registers_trash_commands(self):
        """Bootstrap registers all trash commands."""
        assert "trash:list" in commands._REGISTRY
        assert "trash:restore" in commands._REGISTRY
        assert "trash:purge" in commands._REGISTRY

    def test_bootstrap_registers_asset_path(self):
        """Bootstrap registers asset:path command."""
        assert "asset:path" in commands._REGISTRY

    def test_bootstrap_registers_client_search(self):
        """Bootstrap registers client:search command."""
        assert "client:search" in commands._REGISTRY

    def test_theme_switch_command_calls_api(self):
        """theme:switch command calls switch_theme from api."""
        with patch("src.core.api.switch_theme") as mock_switch:
            mock_root = MagicMock()

            commands.run("theme:switch", root=mock_root, theme_name="darkly")

            mock_switch.assert_called_once_with(mock_root, "darkly")

    def test_upload_folder_command_calls_api(self):
        """upload:folder command calls upload_folder from api."""
        with patch("src.core.api.upload_folder") as mock_upload:
            mock_upload.return_value = {"status": "ok"}

            result = commands.run(
                "upload:folder",
                local_dir="/path",
                org_id="org123",
                client_id="client456",
            )

            mock_upload.assert_called_once_with("/path", "org123", "client456", "GERAL")
            assert result == {"status": "ok"}

    def test_download_zip_command_calls_api(self):
        """download:zip command calls download_folder_zip from api."""
        with patch("src.core.api.download_folder_zip") as mock_download:
            mock_download.return_value = "/tmp/download.zip"

            result = commands.run(
                "download:zip",
                bucket="my-bucket",
                prefix="folder/",
                dest="/tmp",
            )

            mock_download.assert_called_once_with("my-bucket", "folder/", "/tmp")
            assert result == "/tmp/download.zip"

    def test_trash_list_command_calls_api(self):
        """trash:list command calls list_trash_clients from api."""
        with patch("src.core.api.list_trash_clients") as mock_list:
            mock_list.return_value = [{"id": "1", "name": "Client A"}]

            result = commands.run("trash:list", org_id="org123")

            mock_list.assert_called_once_with("org123")
            assert len(result) == 1

    def test_trash_restore_command_calls_api(self):
        """trash:restore command calls restore_from_trash from api."""
        with patch("src.core.api.restore_from_trash") as mock_restore:
            mock_restore.return_value = True

            result = commands.run(
                "trash:restore",
                org_id="org123",
                client_ids=["id1", "id2"],
            )

            mock_restore.assert_called_once_with("org123", ["id1", "id2"])
            assert result is True

    def test_trash_purge_command_calls_api(self):
        """trash:purge command calls purge_from_trash from api."""
        with patch("src.core.api.purge_from_trash") as mock_purge:
            mock_purge.return_value = True

            result = commands.run(
                "trash:purge",
                org_id="org123",
                client_ids=["id1"],
            )

            mock_purge.assert_called_once_with("org123", ["id1"])
            assert result is True

    def test_asset_path_command_exists(self):
        """asset:path command is registered (testing directly avoided due to 'name' param conflict)."""
        # Note: Can't easily test run("asset:path", name="...") due to conflict with run(name, **kwargs)
        # This is a design limitation of the commands module where 'name' is both:
        # 1. First positional arg of run()
        # 2. Required kwarg for _asset_path()
        assert "asset:path" in commands._REGISTRY
        _, help_text, _ = commands._REGISTRY["asset:path"]
        assert "asset" in help_text.lower()

        # Verify the function signature at least
        info = commands.get_command_info("asset:path")
        assert info is not None
        assert info["func"] == "_asset_path"

    def test_client_search_command_calls_api(self):
        """client:search command calls search_clients from api."""
        with patch("src.core.api.search_clients") as mock_search:
            mock_search.return_value = [{"id": "1", "name": "John"}]

            result = commands.run("client:search", query="John", org_id="org123")

            mock_search.assert_called_once_with("John", "org123")
            assert len(result) == 1

    def test_client_search_command_without_org_id(self):
        """client:search command works without org_id (uses None)."""
        with patch("src.core.api.search_clients") as mock_search:
            mock_search.return_value = []

            result = commands.run("client:search", query="test")

            mock_search.assert_called_once_with("test", None)
            assert result == []


# ============================================================================
# TEST: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Edge cases and error scenarios."""

    def test_run_command_with_extra_kwargs_not_in_signature(self):
        """Run command with extra kwargs that function doesn't accept."""

        def _strict_cmd(arg1: str) -> str:
            return arg1

        commands.register("test:strict", _strict_cmd)

        # Should raise TypeError from function call
        with pytest.raises(TypeError):
            commands.run("test:strict", arg1="test", arg2="extra")

    def test_register_command_multiple_times_last_wins(self, dummy_command):
        """Register same command name multiple times - last registration wins."""
        commands.register("test:multi", lambda: "first", help="First")
        commands.register("test:multi", lambda: "second", help="Second")
        commands.register("test:multi", lambda: "third", help="Third")

        result = commands.run("test:multi")
        assert result == "third"

    def test_list_commands_after_unregister(self, dummy_command):
        """List commands after unregistering some."""
        commands._REGISTRY.clear()
        commands.register("cmd1", dummy_command)
        commands.register("cmd2", dummy_command)
        commands.register("cmd3", dummy_command)

        commands.unregister("cmd2")

        result = commands.list_commands()
        assert "cmd1" in result
        assert "cmd2" not in result
        assert "cmd3" in result

    def test_run_command_logs_success(self, dummy_command, caplog):
        """Run command logs success message."""
        import logging

        caplog.set_level(logging.INFO, logger="src.core.commands")
        commands.register("test:log", dummy_command)

        commands.run("test:log", arg1="test")

        assert "executing command" in caplog.text.lower()
        assert "completed successfully" in caplog.text.lower()

    def test_run_command_logs_failure(self, failing_command, caplog):
        """Run command logs failure message."""
        import logging

        caplog.set_level(logging.ERROR, logger="src.core.commands")
        commands.register("test:fail", failing_command)

        with pytest.raises(ValueError):
            commands.run("test:fail")

        assert "failed" in caplog.text.lower()

    def test_keyerror_shows_available_commands(self, dummy_command):
        """KeyError when running nonexistent command shows available commands."""
        commands._REGISTRY.clear()
        commands.register("cmd1", dummy_command)
        commands.register("cmd2", dummy_command)

        with pytest.raises(KeyError, match="Available.*cmd1.*cmd2"):
            commands.run("cmd_missing")
