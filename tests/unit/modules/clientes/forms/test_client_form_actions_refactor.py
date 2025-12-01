# -*- coding: utf-8 -*-
"""
Testes para o módulo client_form_actions.py - lógica headless do formulário de clientes.

Este módulo testa a lógica de negócio extraída do client_form.py,
sem depender de Tkinter ou outras bibliotecas de UI.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, Mock, patch

from src.modules.clientes.forms import client_form_actions as actions


# -----------------------------------------------------------------------------
# Fixtures e Helpers
# -----------------------------------------------------------------------------


class FakeMessages:
    """Implementação fake de MessageSink para testes."""

    def __init__(self) -> None:
        self.warn_calls: list[tuple[str, str]] = []
        self.ask_calls: list[tuple[str, str]] = []
        self.error_calls: list[tuple[str, str]] = []
        self.info_calls: list[tuple[str, str]] = []
        self.ask_answers: list[bool] = []

    def warn(self, title: str, message: str) -> None:
        self.warn_calls.append((title, message))

    def ask_yes_no(self, title: str, message: str) -> bool:
        self.ask_calls.append((title, message))
        return self.ask_answers.pop(0) if self.ask_answers else False

    def show_error(self, title: str, message: str) -> None:
        self.error_calls.append((title, message))

    def show_info(self, title: str, message: str) -> None:
        self.info_calls.append((title, message))


class FakeDataCollector:
    """Implementação fake de FormDataCollector para testes."""

    def __init__(
        self,
        values: dict[str, str] | None = None,
        status: str = "",
    ) -> None:
        self.values = values or {}
        self.status = status

    def collect(self) -> dict[str, str]:
        return self.values.copy()

    def get_status(self) -> str:
        return self.status


def make_ctx(**overrides: Any) -> actions.ClientFormContext:
    """Helper para criar contexto com valores padrão."""
    base = actions.ClientFormContext(is_new=True, client_id=None)
    for key, val in overrides.items():
        setattr(base, key, val)
    return base


def make_deps(
    messages: actions.MessageSink | None = None,
    collector: actions.FormDataCollector | None = None,
    **kwargs: Any,
) -> actions.ClientFormDeps:
    """Helper para criar dependências com valores padrão."""
    return actions.ClientFormDeps(
        messages=messages or FakeMessages(),
        data_collector=collector or FakeDataCollector(),
        **kwargs,
    )


# -----------------------------------------------------------------------------
# Testes: perform_save - Happy Path
# -----------------------------------------------------------------------------


@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
def test_perform_save_happy_path(
    mock_salvar: MagicMock,
    mock_checar: MagicMock,
) -> None:
    """Testa fluxo completo de salvar sem conflitos."""
    # Arrange
    ctx = make_ctx()
    msgs = FakeMessages()
    collector = FakeDataCollector(
        values={"Razão Social": "Empresa X", "CNPJ": "123", "Observações": "teste"},
        status="ATIVO",
    )
    deps = make_deps(messages=msgs, collector=collector)

    # Simular sem conflitos
    mock_checar.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (42, None)

    # Act
    result_ctx = actions.perform_save(ctx, deps, show_success=False)

    # Assert
    assert result_ctx.abort is False
    assert result_ctx.saved_id == 42
    assert result_ctx.client_id == 42
    assert result_ctx.error_message is None

    # Verifica que duplicatas foi chamado
    mock_checar.assert_called_once()

    # Verifica que salvar foi chamado
    mock_salvar.assert_called_once()

    # Não deve ter mensagens (show_success=False)
    assert len(msgs.info_calls) == 0


@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
def test_perform_save_with_success_message(
    mock_salvar: MagicMock,
    mock_checar: MagicMock,
) -> None:
    """Testa fluxo de salvar com mensagem de sucesso."""
    # Arrange
    ctx = make_ctx()
    msgs = FakeMessages()
    collector = FakeDataCollector(
        values={"Razão Social": "Empresa Y", "CNPJ": "456"},
        status="",
    )
    deps = make_deps(messages=msgs, collector=collector)

    mock_checar.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (99, None)

    # Act
    result_ctx = actions.perform_save(ctx, deps, show_success=True)

    # Assert
    assert result_ctx.abort is False
    assert result_ctx.saved_id == 99

    # Deve ter mostrado mensagem de sucesso
    assert len(msgs.info_calls) == 1
    assert msgs.info_calls[0][0] == "Sucesso"


# -----------------------------------------------------------------------------
# Testes: Conflitos de Duplicidade
# -----------------------------------------------------------------------------


@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.show_cnpj_warning_and_abort")
def test_perform_save_cnpj_conflict_aborts(
    mock_show_warning: MagicMock,
    mock_checar: MagicMock,
) -> None:
    """Testa que conflito de CNPJ aborta o salvamento."""
    # Arrange
    ctx = make_ctx()
    msgs = FakeMessages()
    collector = FakeDataCollector(
        values={"Razão Social": "Empresa Z", "CNPJ": "789"},
    )
    deps = make_deps(messages=msgs, collector=collector)

    # Simular conflito de CNPJ
    mock_checar.return_value = {
        "cnpj_conflict": {"id": 10, "razao_social": "Empresa Existente", "cnpj": "789"},
        "razao_conflicts": [],
    }
    mock_show_warning.return_value = False

    # Act
    result_ctx = actions.perform_save(ctx, deps)

    # Assert
    assert result_ctx.abort is True
    assert result_ctx.saved_id is None

    # Verifica que a mensagem de warning foi chamada
    mock_show_warning.assert_called_once()

    # Não deve ter tentado salvar
    assert mock_checar.call_count == 1


@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.ask_razao_confirm")
@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
def test_perform_save_razao_conflict_user_cancels(
    mock_salvar: MagicMock,
    mock_ask_razao: MagicMock,
    mock_checar: MagicMock,
) -> None:
    """Testa que conflito de razão social + usuário cancela = aborta."""
    # Arrange
    ctx = make_ctx()
    msgs = FakeMessages()
    collector = FakeDataCollector(
        values={"Razão Social": "Empresa ABC", "CNPJ": "111"},
    )
    deps = make_deps(messages=msgs, collector=collector)

    # Simular conflito de razão social
    mock_checar.return_value = {
        "cnpj_conflict": None,
        "razao_conflicts": [{"id": 20, "razao_social": "Empresa ABC", "cnpj": "222"}],
    }

    # Usuário cancela
    mock_ask_razao.return_value = False

    # Act
    result_ctx = actions.perform_save(ctx, deps)

    # Assert
    assert result_ctx.abort is True
    assert result_ctx.saved_id is None

    # Verifica que perguntou ao usuário
    mock_ask_razao.assert_called_once()

    # Não deve ter salvado
    mock_salvar.assert_not_called()


@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.ask_razao_confirm")
@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
def test_perform_save_razao_conflict_user_confirms(
    mock_salvar: MagicMock,
    mock_ask_razao: MagicMock,
    mock_checar: MagicMock,
) -> None:
    """Testa que conflito de razão social + usuário confirma = prossegue."""
    # Arrange
    ctx = make_ctx()
    msgs = FakeMessages()
    collector = FakeDataCollector(
        values={"Razão Social": "Empresa DEF", "CNPJ": "333"},
    )
    deps = make_deps(messages=msgs, collector=collector)

    mock_checar.return_value = {
        "cnpj_conflict": None,
        "razao_conflicts": [{"id": 30, "razao_social": "Empresa DEF", "cnpj": "444"}],
    }

    # Usuário confirma
    mock_ask_razao.return_value = True
    mock_salvar.return_value = (50, None)

    # Act
    result_ctx = actions.perform_save(ctx, deps)

    # Assert
    assert result_ctx.abort is False
    assert result_ctx.saved_id == 50

    # Verifica que perguntou e salvou
    mock_ask_razao.assert_called_once()
    mock_salvar.assert_called_once()


# -----------------------------------------------------------------------------
# Testes: Tratamento de Erros
# -----------------------------------------------------------------------------


@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
def test_perform_save_handles_save_error(
    mock_salvar: MagicMock,
    mock_checar: MagicMock,
) -> None:
    """Testa que erros ao salvar são capturados e reportados."""
    # Arrange
    ctx = make_ctx()
    msgs = FakeMessages()
    collector = FakeDataCollector(
        values={"Razão Social": "Empresa Erro", "CNPJ": "555"},
    )
    deps = make_deps(messages=msgs, collector=collector)

    mock_checar.return_value = {"cnpj_conflict": None, "razao_conflicts": []}

    # Simular erro ao salvar
    mock_salvar.side_effect = RuntimeError("Banco de dados indisponível")

    # Act
    result_ctx = actions.perform_save(ctx, deps)

    # Assert
    assert result_ctx.abort is True
    assert result_ctx.saved_id is None
    assert "Banco de dados indisponível" in (result_ctx.error_message or "")

    # Deve ter mostrado erro ao usuário
    assert len(msgs.error_calls) == 1
    assert "Erro" in msgs.error_calls[0][0]


def test_perform_save_handles_collector_error() -> None:
    """Testa que erros ao coletar dados são capturados."""
    # Arrange
    ctx = make_ctx()
    msgs = FakeMessages()

    # Collector que falha
    collector = Mock(spec=actions.FormDataCollector)
    collector.collect.side_effect = ValueError("Widget inválido")

    deps = make_deps(messages=msgs, collector=collector)

    # Act
    result_ctx = actions.perform_save(ctx, deps)

    # Assert
    assert result_ctx.abort is True
    assert result_ctx.saved_id is None
    assert "Widget inválido" in (result_ctx.error_message or "")


# -----------------------------------------------------------------------------
# Testes: Wrappers salvar, salvar_silencioso, salvar_e_enviar
# -----------------------------------------------------------------------------


@patch("src.modules.clientes.forms.client_form_actions.perform_save")
def test_salvar_calls_perform_save_with_success(
    mock_perform: MagicMock,
) -> None:
    """Testa que salvar() chama perform_save com show_success=True."""
    # Arrange
    ctx = make_ctx()
    deps = make_deps()

    mock_perform.return_value = ctx

    # Act
    actions.salvar(ctx, deps)

    # Assert
    mock_perform.assert_called_once_with(ctx, deps, show_success=True)


@patch("src.modules.clientes.forms.client_form_actions.perform_save")
def test_salvar_silencioso_calls_perform_save_without_success(
    mock_perform: MagicMock,
) -> None:
    """Testa que salvar_silencioso() chama perform_save com show_success=False."""
    # Arrange
    ctx = make_ctx()
    deps = make_deps()

    mock_perform.return_value = ctx

    # Act
    actions.salvar_silencioso(ctx, deps)

    # Assert
    mock_perform.assert_called_once_with(ctx, deps, show_success=False)


@patch("src.modules.clientes.forms.client_form_actions.salvar_silencioso")
def test_salvar_e_enviar_creates_new_client(
    mock_salvar_silencioso: MagicMock,
) -> None:
    """Testa que salvar_e_enviar() salva antes de enviar se cliente for novo."""
    # Arrange
    ctx = make_ctx(client_id=None)
    deps = make_deps()

    ctx_resultado = make_ctx(client_id=100, saved_id=100)
    mock_salvar_silencioso.return_value = ctx_resultado

    # Act
    result = actions.salvar_e_enviar(ctx, deps)

    # Assert
    mock_salvar_silencioso.assert_called_once_with(ctx, deps)
    assert result.client_id == 100


def test_salvar_e_enviar_skips_save_if_client_exists() -> None:
    """Testa que salvar_e_enviar() não salva se cliente já existe."""
    # Arrange
    ctx = make_ctx(client_id=200)
    deps = make_deps()

    # Act
    with patch("src.modules.clientes.forms.client_form_actions.salvar_silencioso") as mock_save:
        result = actions.salvar_e_enviar(ctx, deps)

        # Assert
        mock_save.assert_not_called()
        assert result.client_id == 200


# -----------------------------------------------------------------------------
# Testes: Aplicação de Status
# -----------------------------------------------------------------------------


@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_perform_save_applies_status_prefix(
    mock_apply_status: MagicMock,
    mock_salvar: MagicMock,
    mock_checar: MagicMock,
) -> None:
    """Testa que o status é aplicado às observações antes de salvar."""
    # Arrange
    ctx = make_ctx()
    msgs = FakeMessages()
    collector = FakeDataCollector(
        values={"Razão Social": "Empresa Status", "CNPJ": "777", "Observações": "Obs originais"},
        status="INATIVO",
    )
    deps = make_deps(messages=msgs, collector=collector)

    mock_checar.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_apply_status.return_value = "[INATIVO] Obs originais"
    mock_salvar.return_value = (88, None)

    # Act
    actions.perform_save(ctx, deps)

    # Assert
    mock_apply_status.assert_called_once_with("Obs originais", "INATIVO")

    # Verifica que o valor foi passado para salvar_cliente
    called_values = mock_salvar.call_args[0][1]
    assert called_values["Observações"] == "[INATIVO] Obs originais"


# -----------------------------------------------------------------------------
# Testes: Contexto e Estado
# -----------------------------------------------------------------------------


@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
def test_perform_save_updates_context_state(
    mock_salvar: MagicMock,
    mock_checar: MagicMock,
) -> None:
    """Testa que o contexto é atualizado corretamente após salvar."""
    # Arrange
    ctx = make_ctx(
        is_new=True,
        client_id=None,
        row=None,
    )
    msgs = FakeMessages()
    collector = FakeDataCollector(
        values={"Razão Social": "Empresa Nova", "CNPJ": "999"},
    )
    deps = make_deps(messages=msgs, collector=collector)

    mock_checar.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (150, None)

    # Act
    result_ctx = actions.perform_save(ctx, deps)

    # Assert
    assert result_ctx.saved_id == 150
    assert result_ctx.client_id == 150
    assert result_ctx.abort is False
    assert result_ctx.is_new is True  # Não modificado
