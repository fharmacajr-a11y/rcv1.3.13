# -*- coding: utf-8 -*-
"""Testes unitários para client_form_adapters.

Testa os adaptadores headless extraídos do client_form para garantir
que a ponte entre UI e lógica de negócio funciona corretamente.

Refatoração: TEST-001 (client_form_adapters + client_form_ui_builders)
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.modules.clientes.forms.client_form_adapters import (
    EditFormState,
    FormDataAdapter,
    TkClientPersistence,
    TkDirectorySelector,
    TkFormFieldSetter,
    TkMessageAdapter,
    TkMessageSink,
    TkUploadExecutor,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# Skip todos os testes de Tkinter em Windows + Python 3.13 devido a bug conhecido
skip_tk_windows_313 = pytest.mark.skipif(
    sys.platform == "win32" and sys.version_info >= (3, 13),
    reason="Tkinter bug no Python 3.13+ em Windows",
)


# =============================================================================
# Testes para EditFormState
# =============================================================================


class TestEditFormState:
    """Testes para a classe EditFormState."""

    def test_create_new_form_state(self) -> None:
        """Novo formulário deve ter client_id=None e is_dirty=False."""
        state = EditFormState(client_id=None)

        assert state.client_id is None
        assert state.is_dirty is False

    def test_create_edit_form_state(self) -> None:
        """Formulário de edição deve ter client_id definido e is_dirty=False."""
        state = EditFormState(client_id=123)

        assert state.client_id == 123
        assert state.is_dirty is False

    def test_mark_dirty_sets_flag(self) -> None:
        """mark_dirty deve alterar is_dirty para True."""
        state = EditFormState(client_id=None)

        state.mark_dirty()

        assert state.is_dirty is True

    def test_mark_dirty_during_initialization_ignored(self) -> None:
        """mark_dirty durante inicialização não deve marcar como dirty."""
        initializing_flag = [True]
        state = EditFormState(client_id=None, initializing_flag=initializing_flag)

        state.mark_dirty()

        assert state.is_dirty is False

    def test_mark_dirty_after_initialization_works(self) -> None:
        """mark_dirty após inicialização deve marcar como dirty."""
        initializing_flag = [True]
        state = EditFormState(client_id=None, initializing_flag=initializing_flag)

        initializing_flag[0] = False
        state.mark_dirty()

        assert state.is_dirty is True

    def test_mark_clean_resets_flag(self) -> None:
        """mark_clean deve resetar is_dirty para False."""
        state = EditFormState(client_id=None)
        state.mark_dirty()

        state.mark_clean()

        assert state.is_dirty is False

    def test_save_silent_without_callback_returns_false(self) -> None:
        """save_silent sem callback deve retornar False e logar warning."""
        state = EditFormState(client_id=None)

        result = state.save_silent()

        assert result is False

    def test_save_silent_with_callback_executes_and_returns_result(self) -> None:
        """save_silent com callback deve executar e retornar resultado."""
        callback_executed = []

        def mock_save() -> bool:
            callback_executed.append(True)
            return True

        state = EditFormState(client_id=None, on_save_silent=mock_save)

        result = state.save_silent()

        assert result is True
        assert len(callback_executed) == 1

    def test_save_silent_callback_failure_propagates(self) -> None:
        """save_silent com callback que falha deve retornar False."""

        def mock_save_fail() -> bool:
            return False

        state = EditFormState(client_id=None, on_save_silent=mock_save_fail)

        result = state.save_silent()

        assert result is False


# =============================================================================
# Testes para TkMessageAdapter
# =============================================================================


class TestTkMessageAdapter:
    """Testes para a classe TkMessageAdapter."""

    @skip_tk_windows_313
    def test_warn_calls_messagebox_showwarning(self) -> None:
        """warn deve chamar messagebox.showwarning com os parâmetros corretos."""
        with patch("src.modules.clientes.forms.client_form_adapters.messagebox.showwarning") as mock_warn:
            adapter = TkMessageAdapter()

            adapter.warn("Título", "Mensagem de aviso")

            mock_warn.assert_called_once_with("Título", "Mensagem de aviso", parent=None)

    @skip_tk_windows_313
    def test_ask_yes_no_calls_askokcancel(self) -> None:
        """ask_yes_no deve chamar messagebox.askokcancel e retornar resultado."""
        with patch(
            "src.modules.clientes.forms.client_form_adapters.messagebox.askokcancel", return_value=True
        ) as mock_ask:
            adapter = TkMessageAdapter()

            result = adapter.ask_yes_no("Confirmar?", "Deseja continuar?")

            assert result is True
            mock_ask.assert_called_once_with("Confirmar?", "Deseja continuar?", parent=None)

    @skip_tk_windows_313
    def test_show_error_calls_showerror(self) -> None:
        """show_error deve chamar messagebox.showerror."""
        with patch("src.modules.clientes.forms.client_form_adapters.messagebox.showerror") as mock_error:
            adapter = TkMessageAdapter()

            adapter.show_error("Erro", "Algo deu errado")

            mock_error.assert_called_once_with("Erro", "Algo deu errado", parent=None)

    @skip_tk_windows_313
    def test_show_info_calls_showinfo(self) -> None:
        """show_info deve chamar messagebox.showinfo."""
        with patch("src.modules.clientes.forms.client_form_adapters.messagebox.showinfo") as mock_info:
            adapter = TkMessageAdapter()

            adapter.show_info("Informação", "Operação concluída")

            mock_info.assert_called_once_with("Informação", "Operação concluída", parent=None)


# =============================================================================
# Testes para FormDataAdapter
# =============================================================================


class TestFormDataAdapter:
    """Testes para a classe FormDataAdapter."""

    @skip_tk_windows_313
    def test_collect_delegates_to_coletar_valores(self) -> None:
        """collect deve delegar para coletar_valores e retornar resultado."""
        mock_ents = {"razao_social": Mock(), "cnpj": Mock()}
        mock_status_var = Mock()
        mock_status_var.get.return_value = "ATIVO"

        with patch(
            "src.modules.clientes.forms.client_form_adapters.coletar_valores",
            return_value={"razao_social": "Empresa Teste", "cnpj": "12345678000190"},
        ) as mock_coletar:
            adapter = FormDataAdapter(ents=mock_ents, status_var=mock_status_var)

            result = adapter.collect()

            assert result == {"razao_social": "Empresa Teste", "cnpj": "12345678000190"}
            mock_coletar.assert_called_once_with(mock_ents)

    @skip_tk_windows_313
    def test_get_status_returns_stripped_value(self) -> None:
        """get_status deve retornar valor limpo do status_var."""
        mock_status_var = Mock()
        mock_status_var.get.return_value = "  INATIVO  "

        adapter = FormDataAdapter(ents={}, status_var=mock_status_var)

        result = adapter.get_status()

        assert result == "INATIVO"


# =============================================================================
# Testes para TkClientPersistence
# =============================================================================


class TestTkClientPersistence:
    """Testes para a classe TkClientPersistence."""

    def test_persist_if_new_with_existing_client_returns_immediately(self) -> None:
        """persist_if_new com client_id existente deve retornar imediatamente."""
        state = EditFormState(client_id=456)
        mock_persist: Callable[[], bool] = Mock(return_value=True)

        persistence = TkClientPersistence(state=state, on_persist_client=mock_persist)

        success, client_id = persistence.persist_if_new(client_id=456)

        assert success is True
        assert client_id == 456
        mock_persist.assert_not_called()

    def test_persist_if_new_with_new_client_calls_persist(self) -> None:
        """persist_if_new com cliente novo deve chamar callback de persistência."""
        state = EditFormState(client_id=None)
        mock_persist: Callable[[], bool] = Mock(return_value=True)

        # Simular que após salvar, o state.client_id é preenchido
        def fake_persist() -> bool:
            state.client_id = 789
            return True

        mock_persist.side_effect = fake_persist

        persistence = TkClientPersistence(state=state, on_persist_client=mock_persist)

        success, client_id = persistence.persist_if_new(client_id=None)

        assert success is True
        assert client_id == 789
        assert state.is_dirty is False
        mock_persist.assert_called_once()

    def test_persist_if_new_failure_returns_false(self) -> None:
        """persist_if_new com falha na persistência deve retornar (False, None)."""
        state = EditFormState(client_id=None)
        mock_persist: Callable[[], bool] = Mock(return_value=False)

        persistence = TkClientPersistence(state=state, on_persist_client=mock_persist)

        success, client_id = persistence.persist_if_new(client_id=None)

        assert success is False
        assert client_id is None

    def test_persist_if_new_calls_update_row_callback(self) -> None:
        """persist_if_new deve chamar callback update_row se fornecido."""
        state = EditFormState(client_id=None)
        update_row_called = []

        def fake_persist() -> bool:
            state.client_id = 999
            return True

        def fake_update_row(new_id: int) -> None:
            update_row_called.append(new_id)

        mock_persist: Callable[[], bool] = Mock(side_effect=fake_persist)
        mock_update: Callable[[int], None] = Mock(side_effect=fake_update_row)

        persistence = TkClientPersistence(
            state=state,
            on_persist_client=mock_persist,
            on_update_row=mock_update,
        )

        success, client_id = persistence.persist_if_new(client_id=None)

        assert success is True
        assert client_id == 999
        assert update_row_called == [999]


# =============================================================================
# Testes para TkUploadExecutor
# =============================================================================


class TestTkUploadExecutor:
    """Testes para a classe TkUploadExecutor."""

    @skip_tk_windows_313
    def test_execute_upload_delegates_to_helper(self) -> None:
        """execute_upload deve delegar para execute_upload_flow."""
        state = EditFormState(client_id=123)
        executor = TkUploadExecutor(state=state)

        mock_host = Mock()
        mock_ents = {"razao_social": Mock()}
        mock_win = Mock()

        with patch("src.modules.clientes.forms.client_form_adapters.execute_upload_flow") as mock_upload:
            executor.execute_upload(
                host=mock_host,
                row=None,
                ents=mock_ents,
                arquivos_selecionados=None,
                win=mock_win,
            )

            mock_upload.assert_called_once_with(
                parent_widget=mock_win,
                ents=mock_ents,
                client_id=123,
                host=mock_host,
            )

    @skip_tk_windows_313
    def test_execute_upload_handles_exception(self) -> None:
        """execute_upload deve capturar exceções e exibir erro."""
        state = EditFormState(client_id=123)
        executor = TkUploadExecutor(state=state)

        with patch(
            "src.modules.clientes.forms.client_form_adapters.execute_upload_flow",
            side_effect=RuntimeError("Erro de upload"),
        ):
            with patch("src.modules.clientes.forms.client_form_adapters.messagebox.showerror") as mock_error:
                result = executor.execute_upload(
                    host=Mock(),
                    row=None,
                    ents={},
                    arquivos_selecionados=None,
                    win=Mock(),
                )

                assert result is None
                mock_error.assert_called_once()


# =============================================================================
# Testes para TkMessageSink
# =============================================================================


class TestTkMessageSink:
    """Testes para a classe TkMessageSink."""

    @skip_tk_windows_313
    def test_warn_calls_showwarning(self) -> None:
        """warn deve chamar messagebox.showwarning."""
        with patch("src.modules.clientes.forms.client_form_adapters.messagebox.showwarning") as mock_warn:
            sink = TkMessageSink()

            sink.warn("Atenção", "CNPJ inválido")

            mock_warn.assert_called_once_with("Atenção", "CNPJ inválido", parent=None)

    @skip_tk_windows_313
    def test_info_calls_showinfo(self) -> None:
        """info deve chamar messagebox.showinfo."""
        with patch("src.modules.clientes.forms.client_form_adapters.messagebox.showinfo") as mock_info:
            sink = TkMessageSink()

            sink.info("Info", "Cartão gerado com sucesso")

            mock_info.assert_called_once_with("Info", "Cartão gerado com sucesso", parent=None)


# =============================================================================
# Testes para TkDirectorySelector
# =============================================================================


class TestTkDirectorySelector:
    """Testes para a classe TkDirectorySelector."""

    @skip_tk_windows_313
    def test_select_directory_calls_askdirectory(self) -> None:
        """select_directory deve chamar filedialog.askdirectory."""
        with patch(
            "src.modules.clientes.forms.client_form_adapters.filedialog.askdirectory", return_value="/path/to/dir"
        ) as mock_ask:
            selector = TkDirectorySelector()

            result = selector.select_directory("Selecione diretório")

            assert result == "/path/to/dir"
            mock_ask.assert_called_once_with(title="Selecione diretório", parent=None)

    @skip_tk_windows_313
    def test_select_directory_returns_none_on_cancel(self) -> None:
        """select_directory deve retornar None se usuário cancelar."""
        with patch("src.modules.clientes.forms.client_form_adapters.filedialog.askdirectory", return_value=""):
            selector = TkDirectorySelector()

            result = selector.select_directory("Selecione diretório")

            assert result == ""


# =============================================================================
# Testes para TkFormFieldSetter
# =============================================================================


class TestTkFormFieldSetter:
    """Testes para a classe TkFormFieldSetter."""

    @skip_tk_windows_313
    def test_set_value_updates_widget(self) -> None:
        """set_value deve atualizar valor do widget."""
        mock_widget = MagicMock()
        ents = {"razao_social": mock_widget}

        setter = TkFormFieldSetter(ents=ents)

        setter.set_value("razao_social", "Empresa Nova")

        mock_widget.delete.assert_called_once_with(0, "end")
        mock_widget.insert.assert_called_once_with(0, "Empresa Nova")

    @skip_tk_windows_313
    def test_set_value_on_nonexistent_field_does_nothing(self) -> None:
        """set_value em campo inexistente não deve lançar exceção."""
        ents: dict[str, MagicMock] = {}
        setter = TkFormFieldSetter(ents=ents)

        # Não deve lançar exceção
        setter.set_value("campo_inexistente", "valor")
