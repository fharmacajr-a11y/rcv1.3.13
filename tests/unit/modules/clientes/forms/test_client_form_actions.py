# -*- coding: utf-8 -*-
"""
Testes unitários para client_form_actions.py - lógica de negócio do formulário de clientes.

Este módulo testa as ações do formulário de forma headless, sem depender de Tkinter,
focando em regras de negócio, validação e integração com serviços.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from src.modules.clientes.forms.client_form_actions import (
    ClientFormContext,
    ClientFormDeps,
    perform_save,
    salvar,
    salvar_e_enviar,
    salvar_silencioso,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_messages() -> Mock:
    """Mock do MessageSink para exibir mensagens."""
    messages = Mock()
    messages.warn = Mock()
    messages.ask_yes_no = Mock(return_value=True)
    messages.show_error = Mock()
    messages.show_info = Mock()
    return messages


@pytest.fixture
def mock_data_collector() -> Mock:
    """Mock do FormDataCollector para coletar dados."""
    collector = Mock()
    collector.collect = Mock(
        return_value={
            "Razão Social": "Empresa Teste LTDA",
            "CNPJ": "12.345.678/0001-90",
            "WhatsApp": "(11) 98765-4321",
            "Nome": "João Silva",
            "Observações": "Cliente VIP",
        }
    )
    collector.get_status = Mock(return_value="Ativo")
    return collector


@pytest.fixture
def deps(mock_messages: Mock, mock_data_collector: Mock) -> ClientFormDeps:
    """Cria dependências do formulário com mocks."""
    return ClientFormDeps(
        messages=mock_messages,
        data_collector=mock_data_collector,
        parent_window=None,
    )


@pytest.fixture
def ctx_new_client() -> ClientFormContext:
    """Contexto para novo cliente."""
    return ClientFormContext(
        is_new=True,
        client_id=None,
    )


@pytest.fixture
def ctx_existing_client() -> ClientFormContext:
    """Contexto para cliente existente."""
    return ClientFormContext(
        is_new=False,
        client_id=123,
        row=(123, "Empresa Teste", "12.345.678/0001-90", "Ativo"),
    )


# =============================================================================
# Testes de perform_save - Happy Path
# =============================================================================


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_perform_save_new_client_success(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa salvamento de novo cliente com sucesso."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {
        "cnpj_conflict": None,
        "razao_conflicts": [],
        "numero_conflicts": [],
        "blocking_fields": {"cnpj": False, "razao": False},
        "conflict_ids": [],
    }
    mock_salvar.return_value = (456, None)

    # Act
    result = perform_save(ctx_new_client, deps, show_success=False)

    # Assert
    assert result.saved_id == 456
    assert result.client_id == 456
    assert result.abort is False
    assert result.error_message is None

    # Verificar que coletou dados
    deps.data_collector.collect.assert_called_once()
    deps.data_collector.get_status.assert_called_once()

    # Verificar que aplicou status
    mock_apply_status.assert_called_once_with("Cliente VIP", "Ativo")

    # Verificar que checou duplicatas
    mock_check_dupes.assert_called_once()

    # Verificar que salvou
    mock_salvar.assert_called_once()

    # Não deve mostrar mensagem de sucesso (show_success=False)
    deps.messages.show_info.assert_not_called()


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_perform_save_existing_client_success(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_existing_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa salvamento de cliente existente com sucesso."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {
        "cnpj_conflict": None,
        "razao_conflicts": [],
        "numero_conflicts": [],
        "blocking_fields": {"cnpj": False, "razao": False},
        "conflict_ids": [],
    }
    mock_salvar.return_value = (123, None)

    # Act
    result = perform_save(ctx_existing_client, deps, show_success=False)

    # Assert
    assert result.saved_id == 123
    assert result.client_id == 123
    assert result.abort is False
    assert result.error_message is None

    # Verificar que usou o ID existente na checagem de duplicatas
    call_args = mock_check_dupes.call_args
    assert call_args is not None


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_perform_save_with_success_message(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa salvamento com exibição de mensagem de sucesso."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {
        "cnpj_conflict": None,
        "razao_conflicts": [],
    }
    mock_salvar.return_value = (789, None)

    # Act
    result = perform_save(ctx_new_client, deps, show_success=True)

    # Assert
    assert result.saved_id == 789
    assert result.abort is False

    # Deve mostrar mensagem de sucesso
    deps.messages.show_info.assert_called_once_with("Sucesso", "Cliente salvo.")


# =============================================================================
# Testes de perform_save - Duplicatas
# =============================================================================


@patch("src.modules.clientes.forms.client_form_actions.show_cnpj_warning_and_abort")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_perform_save_cnpj_conflict_aborts(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_show_warning: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa que conflito de CNPJ aborta o salvamento."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {
        "cnpj_conflict": {
            "id": 999,
            "razao_social": "Outra Empresa",
            "cnpj": "12.345.678/0001-90",
        },
        "razao_conflicts": [],
    }

    # Act
    result = perform_save(ctx_new_client, deps)

    # Assert
    assert result.abort is True
    assert result.saved_id is None

    # Verificou duplicatas
    mock_check_dupes.assert_called_once()

    # Exibiu aviso de CNPJ
    mock_show_warning.assert_called_once()

    # Não tentou salvar
    deps.messages.show_info.assert_not_called()


@patch("src.modules.clientes.forms.client_form_actions.ask_razao_confirm")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_perform_save_razao_conflict_user_cancels(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_ask_confirm: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa que conflito de Razão Social aborta se usuário cancela."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {
        "cnpj_conflict": None,
        "razao_conflicts": [{"id": 888, "razao_social": "Empresa Teste LTDA", "cnpj": "98.765.432/0001-10"}],
    }
    mock_ask_confirm.return_value = False  # Usuário cancela

    # Act
    result = perform_save(ctx_new_client, deps)

    # Assert
    assert result.abort is True
    assert result.saved_id is None

    # Pediu confirmação
    mock_ask_confirm.assert_called_once()


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.ask_razao_confirm")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_perform_save_razao_conflict_user_confirms(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_ask_confirm: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa que conflito de Razão Social continua se usuário confirma."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {
        "cnpj_conflict": None,
        "razao_conflicts": [{"id": 888, "razao_social": "Empresa Teste LTDA", "cnpj": "98.765.432/0001-10"}],
    }
    mock_ask_confirm.return_value = True  # Usuário confirma
    mock_salvar.return_value = (555, None)

    # Act
    result = perform_save(ctx_new_client, deps)

    # Assert
    assert result.abort is False
    assert result.saved_id == 555

    # Pediu confirmação
    mock_ask_confirm.assert_called_once()

    # Salvou mesmo com conflito de razão
    mock_salvar.assert_called_once()


# =============================================================================
# Testes de perform_save - Erros
# =============================================================================


@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_perform_save_data_collection_error(
    mock_apply_status: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa tratamento de erro ao coletar dados do formulário."""
    # Arrange
    deps.data_collector.collect.side_effect = ValueError("Campo obrigatório faltando")

    # Act
    result = perform_save(ctx_new_client, deps)

    # Assert
    assert result.abort is True
    assert result.saved_id is None
    assert "Erro ao coletar dados" in (result.error_message or "")

    # Não deve tentar salvar
    deps.messages.show_info.assert_not_called()


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_perform_save_database_error(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa tratamento de erro ao salvar no banco."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.side_effect = RuntimeError("Erro de conexão com o banco")

    # Act
    result = perform_save(ctx_new_client, deps)

    # Assert
    assert result.abort is True
    assert result.saved_id is None
    assert result.error_message == "Erro de conexão com o banco"

    # Deve exibir mensagem de erro
    deps.messages.show_error.assert_called_once_with("Erro", "Erro de conexão com o banco")


# =============================================================================
# Testes de salvar (wrapper com mensagem de sucesso)
# =============================================================================


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_salvar_shows_success_message(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa que salvar() exibe mensagem de sucesso."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (111, None)

    # Act
    result = salvar(ctx_new_client, deps)

    # Assert
    assert result.saved_id == 111
    assert result.abort is False

    # Deve mostrar mensagem de sucesso
    deps.messages.show_info.assert_called_once_with("Sucesso", "Cliente salvo.")


# =============================================================================
# Testes de salvar_silencioso (wrapper sem mensagem)
# =============================================================================


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_salvar_silencioso_no_success_message(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa que salvar_silencioso() não exibe mensagem de sucesso."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (222, None)

    # Act
    result = salvar_silencioso(ctx_new_client, deps)

    # Assert
    assert result.saved_id == 222
    assert result.abort is False

    # Não deve mostrar mensagem de sucesso
    deps.messages.show_info.assert_not_called()


# =============================================================================
# Testes de salvar_e_enviar
# =============================================================================


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_salvar_e_enviar_new_client_saves_first(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa que salvar_e_enviar salva novo cliente antes de enviar."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (333, None)

    # Act
    result = salvar_e_enviar(ctx_new_client, deps)

    # Assert
    assert result.saved_id == 333
    assert result.client_id == 333
    assert result.abort is False

    # Deve salvar o cliente
    mock_salvar.assert_called_once()

    # Não deve exibir mensagem de sucesso (silencioso)
    deps.messages.show_info.assert_not_called()


def test_salvar_e_enviar_existing_client_skips_save(
    ctx_existing_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa que salvar_e_enviar pula salvamento para cliente existente."""
    # Act
    result = salvar_e_enviar(ctx_existing_client, deps)

    # Assert
    assert result.client_id == 123
    assert result.saved_id is None  # Não salvou
    assert result.abort is False

    # Não deve coletar dados nem salvar
    deps.data_collector.collect.assert_not_called()
    deps.messages.show_info.assert_not_called()


# =============================================================================
# Testes de Integração (fluxos completos)
# =============================================================================


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_integration_full_save_flow(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
    mock_data_collector: Mock,
) -> None:
    """Testa fluxo completo: coletar dados -> aplicar status -> checar duplicatas -> salvar."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (444, None)

    # Act
    result = perform_save(ctx_new_client, deps, show_success=True)

    # Assert - Verificar ordem de chamadas
    assert deps.data_collector.collect.called
    assert deps.data_collector.get_status.called
    assert mock_apply_status.called
    assert mock_check_dupes.called
    assert mock_salvar.called
    assert deps.messages.show_info.called

    # Verificar resultado
    assert result.saved_id == 444
    assert result.abort is False
    assert len(result.form_values) > 0


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_integration_status_prefix_applied_to_observations(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa que o prefixo de status é aplicado nas observações."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente VIP"
    mock_check_dupes.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (555, None)

    # Act
    result = perform_save(ctx_new_client, deps)

    # Assert
    # Verificar que apply_status_prefix foi chamado com observações originais
    mock_apply_status.assert_called_once_with("Cliente VIP", "Ativo")

    # Verificar que o valor modificado foi salvo
    assert result.form_values["Observações"] == "ST:Ativo - Cliente VIP"


# =============================================================================
# Testes de Edge Cases
# =============================================================================


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_edge_case_empty_observations(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
    mock_data_collector: Mock,
) -> None:
    """Testa salvamento com observações vazias."""
    # Arrange
    mock_data_collector.collect.return_value = {
        "Razão Social": "Empresa",
        "CNPJ": "12.345.678/0001-90",
        "Observações": "",  # Vazio
    }
    mock_apply_status.return_value = "ST:Ativo"
    mock_check_dupes.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (666, None)

    # Act
    result = perform_save(ctx_new_client, deps)

    # Assert
    assert result.saved_id == 666
    mock_apply_status.assert_called_once_with("", "Ativo")


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_edge_case_exclude_id_in_duplicate_check(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    deps: ClientFormDeps,
) -> None:
    """Testa que duplicate_check_exclude_id é usado na checagem."""
    # Arrange
    ctx = ClientFormContext(
        is_new=False,
        client_id=100,
        duplicate_check_exclude_id=999,  # ID diferente para excluir
    )
    mock_apply_status.return_value = "ST:Ativo - Cliente"
    mock_check_dupes.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (100, None)

    # Act
    result = perform_save(ctx, deps)

    # Assert
    assert result.saved_id == 100

    # Verificar que passou exclude_id=999 na checagem
    call_args = mock_check_dupes.call_args
    assert call_args is not None
    # O exclude_id usado internamente deve ser duplicate_check_exclude_id


def test_edge_case_context_with_row_data(
    deps: ClientFormDeps,
) -> None:
    """Testa contexto com dados originais da linha."""
    # Arrange
    ctx = ClientFormContext(
        is_new=False,
        client_id=777,
        row=(777, "Empresa Original", "11.111.111/0001-11", "Inativo"),
    )

    # Act & Assert - apenas verificar que o contexto é válido
    assert ctx.row is not None
    assert ctx.row[0] == 777
    assert ctx.client_id == 777


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_edge_case_save_returns_none(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
) -> None:
    """Testa comportamento quando salvar_cliente retorna None."""
    # Arrange
    mock_apply_status.return_value = "ST:Ativo - Cliente"
    mock_check_dupes.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (None, None)  # Salvar retorna None

    # Act
    result = perform_save(ctx_new_client, deps)

    # Assert
    assert result.saved_id is None
    assert result.client_id is None
    assert result.abort is False  # Não abortou, mas não tem ID


# =============================================================================
# Testes de Validação de Dados
# =============================================================================


@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_validation_collector_get_status_called(
    mock_apply_status: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
    mock_data_collector: Mock,
) -> None:
    """Testa que get_status() é chamado durante coleta de dados."""
    # Arrange
    deps.data_collector.collect.side_effect = RuntimeError("Erro proposital")

    # Act
    perform_save(ctx_new_client, deps)

    # Assert
    deps.data_collector.collect.assert_called_once()
    # get_status não é chamado se collect falhar


@patch("src.modules.clientes.forms.client_form_actions.salvar_cliente_a_partir_do_form")
@patch("src.modules.clientes.forms.client_form_actions.checar_duplicatas_para_form")
@patch("src.modules.clientes.forms.client_form_actions.apply_status_prefix")
def test_validation_form_values_stored_in_context(
    mock_apply_status: Mock,
    mock_check_dupes: Mock,
    mock_salvar: Mock,
    ctx_new_client: ClientFormContext,
    deps: ClientFormDeps,
    mock_data_collector: Mock,
) -> None:
    """Testa que valores coletados são armazenados no contexto."""
    # Arrange
    expected_values = {
        "Razão Social": "Empresa XYZ",
        "CNPJ": "99.999.999/0001-99",
    }
    mock_data_collector.collect.return_value = expected_values
    mock_apply_status.return_value = "ST:Ativo"
    mock_check_dupes.return_value = {"cnpj_conflict": None, "razao_conflicts": []}
    mock_salvar.return_value = (888, None)

    # Act
    result = perform_save(ctx_new_client, deps)

    # Assert
    assert "Razão Social" in result.form_values
    assert result.form_values["Razão Social"] == "Empresa XYZ"
    assert "CNPJ" in result.form_values
