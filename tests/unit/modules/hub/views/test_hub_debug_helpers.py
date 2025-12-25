# -*- coding: utf-8 -*-
"""Testes unitários para hub_debug_helpers.py - helpers de debug."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.modules.hub.views.hub_debug_helpers import (
    collect_notes_debug_data,
    show_debug_info,
)


class TestCollectNotesDebugData:
    """Testes para coleta de dados de debug do sistema de notas."""

    @pytest.fixture
    def get_org_id(self):
        """Mock de getter de org_id."""
        return MagicMock(return_value="org-test-123")

    def test_collects_basic_state_info(self, get_org_id):
        """Deve coletar informações básicas de estado."""
        debug_data = collect_notes_debug_data(
            get_org_id=get_org_id,
            notes_last_data=[],
            notes_last_snapshot=[],
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=True,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=True,
        )

        assert "timestamp" in debug_data
        assert "org_id" in debug_data
        assert "state" in debug_data
        assert debug_data["org_id"] == "org-test-123"
        assert debug_data["state"]["polling_active"] is False
        assert debug_data["state"]["live_sync_on"] is True
        assert debug_data["state"]["cache_loaded"] is True

    def test_formats_timestamp_correctly(self, get_org_id):
        """Deve formatar timestamp do último refresh corretamente."""
        import time

        last_refresh = time.time()

        debug_data = collect_notes_debug_data(
            get_org_id=get_org_id,
            notes_last_data=[],
            notes_last_snapshot=[],
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=True,
            notes_last_refresh=last_refresh,
            polling_active=True,
            live_sync_on=False,
        )

        # Deve ter timestamp formatado em ISO
        last_refresh_str = debug_data["state"]["last_refresh"]
        assert last_refresh_str is not None
        assert isinstance(last_refresh_str, str)
        # ISO format contém "T" entre data e hora
        assert "T" in last_refresh_str or "-" in last_refresh_str

    def test_handles_none_last_refresh(self, get_org_id):
        """Deve lidar com last_refresh=None."""
        debug_data = collect_notes_debug_data(
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

        assert debug_data["state"]["last_refresh"] is None

    def test_counts_author_names_cache(self, get_org_id):
        """Deve contar corretamente entradas no cache de nomes."""
        author_cache = {
            "user-1": "João Silva",
            "user-2": "Maria Santos",
            "user-3": "Pedro Costa",
        }

        debug_data = collect_notes_debug_data(
            get_org_id=get_org_id,
            notes_last_data=[],
            notes_last_snapshot=[],
            author_names_cache=author_cache,
            email_prefix_map={},
            notes_cache_loaded=True,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=False,
        )

        assert debug_data["cache"]["author_names_count"] == 3
        assert debug_data["cache"]["author_names"] == author_cache

    def test_counts_email_prefix_map(self, get_org_id):
        """Deve contar corretamente entradas no mapa de prefixos."""
        prefix_map = {
            "user-1": "joao.silva",
            "user-2": "maria.santos",
        }

        debug_data = collect_notes_debug_data(
            get_org_id=get_org_id,
            notes_last_data=[],
            notes_last_snapshot=[],
            author_names_cache={},
            email_prefix_map=prefix_map,
            notes_cache_loaded=True,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=False,
        )

        assert debug_data["cache"]["email_prefix_count"] == 2
        assert debug_data["cache"]["email_prefixes"] == prefix_map

    def test_counts_notes_in_list(self, get_org_id):
        """Deve contar corretamente número de notas quando é lista."""
        notes_data = [
            {"id": 1, "content": "Nota 1"},
            {"id": 2, "content": "Nota 2"},
            {"id": 3, "content": "Nota 3"},
        ]

        debug_data = collect_notes_debug_data(
            get_org_id=get_org_id,
            notes_last_data=notes_data,
            notes_last_snapshot=notes_data[:2],  # Apenas 2
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=True,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=False,
        )

        assert debug_data["notes"]["last_data_count"] == 3
        assert debug_data["notes"]["last_snapshot_count"] == 2
        assert debug_data["notes"]["last_data_type"] == "list"
        assert debug_data["notes"]["last_snapshot_type"] == "list"

    def test_handles_non_list_notes_data(self, get_org_id):
        """Deve lidar com notes_data que não é lista."""
        debug_data = collect_notes_debug_data(
            get_org_id=get_org_id,
            notes_last_data=None,  # Não é lista
            notes_last_snapshot={},  # Não é lista
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=True,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=False,
        )

        # Count deve ser 0 para não-listas
        assert debug_data["notes"]["last_data_count"] == 0
        assert debug_data["notes"]["last_snapshot_count"] == 0
        assert debug_data["notes"]["last_data_type"] == "NoneType"
        assert debug_data["notes"]["last_snapshot_type"] == "dict"

    def test_includes_timestamp_in_output(self, get_org_id):
        """Deve incluir timestamp atual no output."""
        before = datetime.now()

        debug_data = collect_notes_debug_data(
            get_org_id=get_org_id,
            notes_last_data=[],
            notes_last_snapshot=[],
            author_names_cache={},
            email_prefix_map={},
            notes_cache_loaded=True,
            notes_last_refresh=None,
            polling_active=False,
            live_sync_on=False,
        )

        after = datetime.now()

        # Timestamp deve estar entre before e after
        timestamp_str = debug_data["timestamp"]
        timestamp = datetime.fromisoformat(timestamp_str)

        assert before <= timestamp <= after

    def test_handles_empty_caches(self, get_org_id):
        """Deve lidar corretamente com caches vazios."""
        debug_data = collect_notes_debug_data(
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

        assert debug_data["cache"]["author_names_count"] == 0
        assert debug_data["cache"]["email_prefix_count"] == 0
        assert debug_data["notes"]["last_data_count"] == 0
        assert debug_data["notes"]["last_snapshot_count"] == 0


class TestShowDebugInfo:
    """Testes para função de exibição de debug."""

    @pytest.fixture
    def mock_parent(self):
        """Mock do widget pai."""
        return MagicMock()

    @pytest.fixture
    def collect_debug_data(self):
        """Mock de função de coleta de dados."""
        return MagicMock(
            return_value={
                "timestamp": "2025-12-08T10:00:00",
                "org_id": "org-123",
                "state": {"polling_active": True},
                "cache": {"author_names_count": 5},
                "notes": {"last_data_count": 10},
            }
        )

    @patch("src.modules.hub.helpers.debug.messagebox")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.modules.hub.helpers.debug.os.path.abspath")
    def test_saves_debug_report_to_file(
        self,
        mock_abspath,
        mock_file,
        mock_messagebox,
        mock_parent,
        collect_debug_data,
    ):
        """Deve salvar relatório de debug em arquivo JSON."""
        mock_abspath.return_value = "/path/to/debug_report.json"

        show_debug_info(
            parent=mock_parent,
            collect_debug_data=collect_debug_data,
        )

        # Verificar que arquivo foi aberto para escrita
        assert mock_file.called
        # Nome do arquivo deve conter "debug_notes_report"
        _ = mock_file.call_args[0][0]  # Filename is generated
        # O abspath altera o nome, então vamos verificar antes do abspath
        # OU verificar que showinfo foi chamado com o path correto
        # Verificar na mensagem showinfo
        call_args = mock_messagebox.showinfo.call_args
        assert "/path/to/debug_report.json" in call_args[0][1]

    @patch("src.modules.hub.helpers.debug.messagebox")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.modules.hub.helpers.debug.os.path.abspath")
    def test_shows_success_message_with_filepath(
        self,
        mock_abspath,
        mock_file,
        mock_messagebox,
        mock_parent,
        collect_debug_data,
    ):
        """Deve mostrar mensagem de sucesso com caminho do arquivo."""
        expected_path = "/absolute/path/to/report.json"
        mock_abspath.return_value = expected_path

        show_debug_info(
            parent=mock_parent,
            collect_debug_data=collect_debug_data,
        )

        # Verificar que showinfo foi chamado
        mock_messagebox.showinfo.assert_called_once()
        call_args = mock_messagebox.showinfo.call_args

        assert "Relatório de Debug Gerado" in call_args[0][0]
        assert expected_path in call_args[0][1]

    @patch("src.modules.hub.helpers.debug.messagebox")
    @patch("builtins.open", new_callable=mock_open)
    def test_writes_valid_json_to_file(
        self,
        mock_file,
        mock_messagebox,
        mock_parent,
        collect_debug_data,
    ):
        """Deve escrever JSON válido no arquivo."""
        show_debug_info(
            parent=mock_parent,
            collect_debug_data=collect_debug_data,
        )

        # Obter o que foi escrito
        handle = mock_file()
        written_calls = handle.write.call_args_list

        # Concatenar todas as escritas
        written_data = "".join(call[0][0] for call in written_calls)

        # Verificar que é JSON válido
        parsed = json.loads(written_data)
        assert "timestamp" in parsed
        assert "org_id" in parsed

    @patch("src.modules.hub.helpers.debug.messagebox")
    @patch("builtins.open", side_effect=IOError("Disk full"))
    def test_shows_error_on_file_write_failure(
        self,
        mock_file,
        mock_messagebox,
        mock_parent,
        collect_debug_data,
    ):
        """Deve mostrar erro se falhar ao escrever arquivo."""
        show_debug_info(
            parent=mock_parent,
            collect_debug_data=collect_debug_data,
        )

        # Deve ter mostrado erro
        mock_messagebox.showerror.assert_called_once()
        call_args = mock_messagebox.showerror.call_args
        assert "Erro" in call_args[0][0]

    @patch("src.modules.hub.helpers.debug.messagebox")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.modules.hub.helpers.debug.logger")
    def test_logs_debug_info_to_console(
        self,
        mock_logger,
        mock_file,
        mock_messagebox,
        mock_parent,
        collect_debug_data,
    ):
        """Deve logar informações de debug no console."""
        show_debug_info(
            parent=mock_parent,
            collect_debug_data=collect_debug_data,
        )

        # Verificar que logger.info foi chamado
        assert mock_logger.info.called

        # Verificar que JSON foi logado
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        log_output = "".join(log_calls)

        assert "DEBUG NOTES REPORT" in log_output

    @patch("src.modules.hub.helpers.debug.messagebox")
    @patch("builtins.open", new_callable=mock_open)
    def test_filename_includes_timestamp(
        self,
        mock_file,
        mock_messagebox,
        mock_parent,
        collect_debug_data,
    ):
        """Deve incluir timestamp no nome do arquivo."""
        show_debug_info(
            parent=mock_parent,
            collect_debug_data=collect_debug_data,
        )

        # Obter nome do arquivo
        filename = mock_file.call_args[0][0]

        # Deve ter padrão debug_notes_report_YYYYMMDD_HHMMSS.json
        assert "debug_notes_report_" in filename
        assert ".json" in filename

        # Extrair timestamp do nome
        parts = filename.split("_")
        # Deve ter pelo menos data e hora
        assert len(parts) >= 4

    @patch("src.modules.hub.helpers.debug.messagebox")
    def test_handles_exception_in_collect_debug_data(
        self,
        mock_messagebox,
        mock_parent,
    ):
        """Deve lidar com exceção ao coletar dados de debug."""
        collect_debug_data = MagicMock(side_effect=Exception("Data collection failed"))

        show_debug_info(
            parent=mock_parent,
            collect_debug_data=collect_debug_data,
        )

        # Deve ter mostrado erro
        mock_messagebox.showerror.assert_called_once()

    @patch("src.modules.hub.helpers.debug.messagebox")
    @patch("builtins.open", new_callable=mock_open)
    def test_json_is_formatted_with_indent(
        self,
        mock_file,
        mock_messagebox,
        mock_parent,
        collect_debug_data,
    ):
        """Deve formatar JSON com indentação para legibilidade."""
        show_debug_info(
            parent=mock_parent,
            collect_debug_data=collect_debug_data,
        )

        # Obter dados escritos
        handle = mock_file()
        written_calls = handle.write.call_args_list
        written_data = "".join(call[0][0] for call in written_calls)

        # JSON indentado deve conter múltiplas linhas
        assert "\n" in written_data
        # Deve conter espaços de indentação
        assert "  " in written_data or "\t" in written_data
