# -*- coding: utf-8 -*-
"""Testes unitários para hub_debug_helpers.py (MF-55).

Cobre:
- hub_dlog (logging estruturado)
- collect_notes_debug_data (coleta base de dados)
- show_debug_info (geração de relatório)
- collect_full_notes_debug (coleta completa com samples)
- Logger fallback

Estratégia:
- Headless (patch de messagebox, file I/O)
- Mock de callables (get_org_id, debug_resolve_author_fn)
- Cobertura de branches (enabled/disabled, exceptions, tipos de dados)
- Logger fallback via importlib.reload
"""

from __future__ import annotations

import importlib
import json
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import src.modules.hub.views.hub_debug_helpers as hub_debug_helpers
from src.modules.hub.views.hub_debug_helpers import (
    collect_full_notes_debug,
    collect_notes_debug_data,
    hub_dlog,
    show_debug_info,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: hub_dlog
# ═══════════════════════════════════════════════════════════════════════════════


class TestHubDlog:
    """Testes para hub_dlog (logger estruturado)."""

    def test_hub_dlog_enabled_logs_json_payload(self) -> None:
        """hub_dlog com enabled=True deve logar payload JSON."""
        with patch.object(hub_debug_helpers, "logger") as mock_logger:
            with patch("src.modules.hub.helpers.debug.time") as mock_time:
                mock_time.time.return_value = 1234567890.123

                hub_dlog("test_event", enabled=True, extra={"key": "value"})

                mock_logger.info.assert_called_once()
                args = mock_logger.info.call_args[0]
                assert args[0] == "[HUB] %s"
                payload = json.loads(args[1])
                assert payload["t"] == 1234567890123  # ms
                assert payload["tag"] == "test_event"
                assert payload["key"] == "value"

    def test_hub_dlog_disabled_does_not_log(self) -> None:
        """hub_dlog com enabled=False não deve logar nada."""
        with patch.object(hub_debug_helpers, "logger") as mock_logger:
            hub_dlog("ignored_event", enabled=False, extra={"key": "value"})

            mock_logger.info.assert_not_called()
            mock_logger.debug.assert_not_called()

    def test_hub_dlog_no_extra_logs_minimal_payload(self) -> None:
        """hub_dlog sem extra deve logar apenas t e tag."""
        with patch.object(hub_debug_helpers, "logger") as mock_logger:
            with patch("src.modules.hub.helpers.debug.time") as mock_time:
                mock_time.time.return_value = 9999999999.999

                hub_dlog("minimal", enabled=True)

                args = mock_logger.info.call_args[0]
                payload = json.loads(args[1])
                assert payload == {"t": 9999999999999, "tag": "minimal"}

    def test_hub_dlog_exception_during_logging_is_silenced(self) -> None:
        """hub_dlog deve suprimir exceções durante logging."""
        with patch.object(hub_debug_helpers, "logger") as mock_logger:
            mock_logger.info.side_effect = RuntimeError("JSON encoding failed")

            # Não deve propagar exceção
            hub_dlog("failing_event", enabled=True, extra={"bad": object()})

            mock_logger.debug.assert_called_once()
            assert "Falha ao logar debug" in mock_logger.debug.call_args[0][0]


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: collect_notes_debug_data
# ═══════════════════════════════════════════════════════════════════════════════


class TestCollectNotesDebugData:
    """Testes para collect_notes_debug_data."""

    def test_collect_notes_debug_data_with_org_id(self) -> None:
        """collect_notes_debug_data deve retornar estrutura completa com org_id."""
        get_org_id = MagicMock(return_value="org_123")
        notes_last_data = [{"body": "note1"}, {"body": "note2"}]
        notes_last_snapshot = [("ts1", "author1", "body1")]
        author_names_cache = {"user@example.com": "User Name"}
        email_prefix_map = {"user": "user@example.com"}

        result = collect_notes_debug_data(
            get_org_id=get_org_id,
            notes_last_data=notes_last_data,
            notes_last_snapshot=notes_last_snapshot,
            author_names_cache=author_names_cache,
            email_prefix_map=email_prefix_map,
            notes_cache_loaded=True,
            notes_last_refresh=1234567890.5,
            polling_active=True,
            live_sync_on=False,
        )

        assert result["org_id"] == "org_123"
        assert result["state"]["polling_active"] is True
        assert result["state"]["live_sync_on"] is False
        assert result["state"]["cache_loaded"] is True
        assert result["state"]["last_refresh"].startswith("2009-02-13")
        assert result["cache"]["author_names_count"] == 1
        assert result["cache"]["email_prefix_count"] == 1
        assert result["notes"]["last_data_count"] == 2
        assert result["notes"]["last_snapshot_count"] == 1
        assert result["notes"]["last_data_type"] == "list"

    def test_collect_notes_debug_data_without_org_id(self) -> None:
        """collect_notes_debug_data com org_id=None."""
        get_org_id = MagicMock(return_value=None)

        result = collect_notes_debug_data(
            get_org_id=get_org_id,
            notes_last_data=[],
            notes_last_snapshot=[],
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=False,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=False,
        )

        assert result["org_id"] is None
        assert result["state"]["last_refresh"] is None
        assert result["cache"]["author_names_count"] == 0
        assert result["notes"]["last_data_count"] == 0

    def test_collect_notes_debug_data_with_non_list_notes(self) -> None:
        """collect_notes_debug_data com notes_last_data não sendo list."""
        get_org_id = MagicMock(return_value="org_456")

        result = collect_notes_debug_data(
            get_org_id=get_org_id,
            notes_last_data=None,
            notes_last_snapshot="not_a_list",
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=False,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=True,
        )

        assert result["notes"]["last_data_count"] == 0
        assert result["notes"]["last_snapshot_count"] == 0
        assert result["notes"]["last_data_type"] == "NoneType"
        assert result["notes"]["last_snapshot_type"] == "str"

    def test_collect_notes_debug_data_timestamp_format_exception(self) -> None:
        """collect_notes_debug_data com timestamp inválido deve usar fallback."""
        get_org_id = MagicMock(return_value="org_789")

        with patch("datetime.datetime") as mock_datetime_cls:
            mock_datetime_cls.fromtimestamp.side_effect = Exception("Invalid timestamp")
            mock_datetime_cls.now.return_value.isoformat.return_value = "2025-01-01T00:00:00"

            result = collect_notes_debug_data(
                get_org_id=get_org_id,
                notes_last_data=[],
                notes_last_snapshot=[],
                author_names_cache={},
                email_prefix_map={},
                notes_cache_loaded=False,
                notes_last_refresh=9999999999999999.9,
                polling_active=False,
                live_sync_on=False,
            )

        # Fallback: converte para string (notação científica é aceita)
        assert result["state"]["last_refresh"] in ("9999999999999999.9", "1e+16")


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: show_debug_info
# ═══════════════════════════════════════════════════════════════════════════════


class TestShowDebugInfo:
    """Testes para show_debug_info."""

    def test_show_debug_info_creates_file_and_shows_messagebox(self) -> None:
        """show_debug_info deve criar arquivo JSON e mostrar messagebox de sucesso."""
        parent = MagicMock()
        collect_debug_data = MagicMock(return_value={"test": "data", "count": 42})

        with patch("builtins.open", mock_open()) as mock_file:
            with patch("src.modules.hub.helpers.debug.messagebox") as mock_messagebox:
                with patch.object(hub_debug_helpers, "logger") as mock_logger:
                    with patch("src.modules.hub.helpers.debug.datetime") as mock_datetime:
                        mock_now_instance = MagicMock()
                        mock_now_instance.strftime.return_value = "20250101_120000"
                        mock_datetime.now.return_value = mock_now_instance

                        show_debug_info(parent, collect_debug_data)

                        # Verificar criação do arquivo
                        expected_filename = "debug_notes_report_20250101_120000.json"
                        mock_file.assert_called_once()
                        call_args = mock_file.call_args
                        assert expected_filename in call_args[0][0]
                        assert call_args[1] == {"encoding": "utf-8"}

                        # Verificar messagebox de sucesso
                        mock_messagebox.showinfo.assert_called_once()
                        info_args = mock_messagebox.showinfo.call_args[0]
                        assert "Relatório de Debug Gerado" in info_args[0]
                        assert expected_filename in info_args[1]

                        # Verificar logging no console
                        assert mock_logger.info.call_count == 3

    def test_show_debug_info_exception_shows_error_messagebox(self) -> None:
        """show_debug_info deve mostrar messagebox de erro em caso de exceção."""
        parent = MagicMock()
        collect_debug_data = MagicMock(side_effect=RuntimeError("Collection failed"))

        with patch("src.modules.hub.helpers.debug.messagebox") as mock_messagebox:
            with patch.object(hub_debug_helpers, "logger") as mock_logger:
                show_debug_info(parent, collect_debug_data)

                # Verificar messagebox de erro
                mock_messagebox.showerror.assert_called_once()
                error_args = mock_messagebox.showerror.call_args[0]
                assert error_args[0] == "Erro"
                assert "Collection failed" in error_args[1]

                # Verificar logging do erro
                mock_logger.error.assert_called_once()
                assert "Erro ao gerar relatório" in mock_logger.error.call_args[0][0]

    def test_show_debug_info_file_write_exception(self) -> None:
        """show_debug_info deve tratar exceção durante escrita do arquivo."""
        parent = MagicMock()
        collect_debug_data = MagicMock(return_value={"data": "ok"})

        with patch("builtins.open", side_effect=IOError("Disk full")):
            with patch("src.modules.hub.helpers.debug.messagebox") as mock_messagebox:
                with patch.object(hub_debug_helpers, "logger"):
                    show_debug_info(parent, collect_debug_data)

                    # Verificar tratamento de erro
                    mock_messagebox.showerror.assert_called_once()
                    error_msg = mock_messagebox.showerror.call_args[0][1]
                    assert "Disk full" in error_msg


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: collect_full_notes_debug
# ═══════════════════════════════════════════════════════════════════════════════


class TestCollectFullNotesDebug:
    """Testes para collect_full_notes_debug."""

    def test_collect_full_notes_debug_with_dict_notes(self) -> None:
        """collect_full_notes_debug com notas no formato dict."""
        get_org_id = MagicMock(return_value="org_full")
        notes_last_data = [
            {"author_email": "alice@example.com", "body": "Note 1"},
            {"author": "bob@example.com", "body": "Note 2"},
            {"email": "charlie@example.com", "body": "Note 3"},
        ]
        debug_resolve_author_fn = MagicMock(side_effect=lambda n, email: {"resolved": email, "note": n["body"]})

        result = collect_full_notes_debug(
            get_org_id=get_org_id,
            notes_last_data=notes_last_data,
            notes_last_snapshot=None,
            author_names_cache={"alice@example.com": "Alice"},
            email_prefix_map={},
            notes_cache_loaded=True,
            notes_last_refresh=1234567890.0,
            polling_active=True,
            live_sync_on=False,
            current_user_email="alice@example.com",
            debug_resolve_author_fn=debug_resolve_author_fn,
        )

        # Verificar dados base
        assert result["org_id"] == "org_full"
        assert result["current_user"] == "alice@example.com"

        # Verificar samples
        assert len(result["samples"]) == 3
        assert result["samples"][0] == {"resolved": "alice@example.com", "note": "Note 1"}
        assert result["samples"][1] == {"resolved": "bob@example.com", "note": "Note 2"}
        assert result["samples"][2] == {"resolved": "charlie@example.com", "note": "Note 3"}

    def test_collect_full_notes_debug_with_tuple_notes(self) -> None:
        """collect_full_notes_debug com notas no formato tuple."""
        get_org_id = MagicMock(return_value="org_tuple")
        notes_last_snapshot = [
            ("2025-01-01T00:00:00", "user1@example.com", "Body 1"),
            ("2025-01-02T00:00:00", "user2@example.com", "Body 2"),
        ]
        debug_resolve_author_fn = MagicMock(side_effect=lambda n, email: {"author": email, "tuple_len": len(n)})

        result = collect_full_notes_debug(
            get_org_id=get_org_id,
            notes_last_data=None,
            notes_last_snapshot=notes_last_snapshot,
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=False,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=True,
            current_user_email="",
            debug_resolve_author_fn=debug_resolve_author_fn,
        )

        assert len(result["samples"]) == 2
        assert result["samples"][0]["author"] == "user1@example.com"
        assert result["samples"][1]["author"] == "user2@example.com"

    def test_collect_full_notes_debug_limits_samples_to_20(self) -> None:
        """collect_full_notes_debug deve limitar samples a 20."""
        get_org_id = MagicMock(return_value="org_limit")
        notes_last_data = [{"author_email": f"user{i}@example.com"} for i in range(50)]
        debug_resolve_author_fn = MagicMock(return_value={"ok": True})

        result = collect_full_notes_debug(
            get_org_id=get_org_id,
            notes_last_data=notes_last_data,
            notes_last_snapshot=None,
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=False,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=False,
            current_user_email=None,
            debug_resolve_author_fn=debug_resolve_author_fn,
        )

        # Deve processar apenas 20 samples
        assert len(result["samples"]) == 20

    def test_collect_full_notes_debug_exception_in_resolve_author(self) -> None:
        """collect_full_notes_debug deve capturar exceções em debug_resolve_author_fn."""
        get_org_id = MagicMock(return_value="org_error")
        notes_last_data = [
            {"author_email": "good@example.com", "body": "OK"},
            {"author_email": "bad@example.com", "body": "Fail"},
        ]

        def resolve_with_error(n: Any, _email: str) -> dict[str, Any]:
            if "bad" in n.get("author_email", ""):
                raise ValueError("Cannot resolve bad user")
            return {"status": "ok"}

        debug_resolve_author_fn = MagicMock(side_effect=resolve_with_error)

        with patch.object(hub_debug_helpers, "logger"):
            result = collect_full_notes_debug(
                get_org_id=get_org_id,
                notes_last_data=notes_last_data,
                notes_last_snapshot=None,
                author_names_cache={},
                email_prefix_map={},
                notes_cache_loaded=False,
                notes_last_refresh=None,
                polling_active=False,
                live_sync_on=False,
                current_user_email="test@example.com",
                debug_resolve_author_fn=debug_resolve_author_fn,
            )

        # Primeira nota OK, segunda com erro
        assert len(result["samples"]) == 2
        assert result["samples"][0] == {"status": "ok"}
        assert "error" in result["samples"][1]
        assert "Cannot resolve bad user" in result["samples"][1]["error"]

    def test_collect_full_notes_debug_author_of_edge_cases(self) -> None:
        """collect_full_notes_debug _author_of deve tratar casos edge."""
        get_org_id = MagicMock(return_value="org_edge")
        notes_last_data = [
            ("single_element",),  # tuple com 1 elemento
            ["two", "elements"],  # list com 2 elementos
            "plain_string",  # string direta
            123,  # número
            None,  # None
        ]
        debug_resolve_author_fn = MagicMock(side_effect=lambda _n, email: {"email": email})

        result = collect_full_notes_debug(
            get_org_id=get_org_id,
            notes_last_data=notes_last_data,
            notes_last_snapshot=None,
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=False,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=False,
            current_user_email="",
            debug_resolve_author_fn=debug_resolve_author_fn,
        )

        # Verificar extração de emails
        assert result["samples"][0]["email"] == "single_element"  # tuple[0]
        assert result["samples"][1]["email"] == "elements"  # list[1]
        assert result["samples"][2]["email"] == "plain_string"  # str(n)
        assert result["samples"][3]["email"] == "123"  # str(n)
        assert result["samples"][4]["email"] == "None"  # str(None)

    def test_collect_full_notes_debug_empty_notes(self) -> None:
        """collect_full_notes_debug com notes vazias."""
        get_org_id = MagicMock(return_value="org_empty")
        debug_resolve_author_fn = MagicMock()

        result = collect_full_notes_debug(
            get_org_id=get_org_id,
            notes_last_data=None,
            notes_last_snapshot=None,
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=False,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=False,
            current_user_email="",
            debug_resolve_author_fn=debug_resolve_author_fn,
        )

        assert result["samples"] == []
        debug_resolve_author_fn.assert_not_called()

    def test_collect_full_notes_debug_sets_current_user_when_email_is_truthy(self) -> None:
        """collect_full_notes_debug com current_user_email não-vazio."""
        get_org_id = MagicMock(return_value="org-1")

        result = collect_full_notes_debug(
            get_org_id=get_org_id,
            notes_last_data=[],
            notes_last_snapshot=None,
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=False,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=False,
            current_user_email="user@example.com",
            debug_resolve_author_fn=MagicMock(),
        )

        assert result["current_user"] == "user@example.com"


# ═══════════════════════════════════════════════════════════════════════════════
# TESTES: Logger Fallback
# ═══════════════════════════════════════════════════════════════════════════════


class TestLoggerFallback:
    """Testes para fallback de logger."""

    def test_logger_fallback_on_import_error(self) -> None:
        """Deve usar logging.getLogger quando src.core.logger falha."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name: str, *args: Any, **kwargs: Any):
            if name == "src.core.logger":
                raise ImportError("src.core.logger not found")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            # Recarregar o módulo de implementação real
            import src.modules.hub.helpers.debug as hub_debug_impl

            importlib.reload(hub_debug_impl)

            # Após reload, get_logger deve ser o fallback
            logger_instance = hub_debug_impl.get_logger("test_fallback")
            assert logger_instance.name == "test_fallback"

        # Restaurar módulo
        import src.modules.hub.helpers.debug as hub_debug_impl

        importlib.reload(hub_debug_impl)
