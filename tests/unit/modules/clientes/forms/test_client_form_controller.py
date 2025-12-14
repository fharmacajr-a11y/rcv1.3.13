# -*- coding: utf-8 -*-
"""Testes unitários para ClientFormController.

Testa a orquestração headless do formulário de clientes, usando mocks
para View e serviços (save/upload).

Refatoração: MICROFASE-12
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.modules.clientes.forms.client_form_controller import (
    ClientFormController,
)
from src.modules.clientes.forms.client_form_state import ClientFormState


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_view() -> Mock:
    """Cria mock de ClientFormView."""
    view = Mock()
    view.update_title = Mock()
    view.set_upload_button_enabled = Mock()
    view.set_cartao_cnpj_button_enabled = Mock()
    view.close = Mock()
    return view


@pytest.fixture
def mock_save_service() -> Mock:
    """Cria mock de SaveService."""
    return Mock(return_value=True)


@pytest.fixture
def mock_upload_service() -> Mock:
    """Cria mock de UploadFlowService."""
    return Mock(return_value=(True, False, None))


@pytest.fixture
def state_new_client() -> ClientFormState:
    """Cria estado para novo cliente."""
    state = ClientFormState()
    state.data.razao_social = "Empresa Teste LTDA"
    state.data.cnpj = "12.345.678/0001-90"
    return state


@pytest.fixture
def state_existing_client() -> ClientFormState:
    """Cria estado para cliente existente."""
    state = ClientFormState(client_id=123, is_new=False)
    state.data.razao_social = "Empresa Teste LTDA"
    state.data.cnpj = "12.345.678/0001-90"
    return state


@pytest.fixture
def controller_new_client(
    state_new_client: ClientFormState,
    mock_save_service: Mock,
    mock_upload_service: Mock,
    mock_view: Mock,
) -> ClientFormController:
    """Cria controller para novo cliente."""
    return ClientFormController(
        state=state_new_client,
        save_service=mock_save_service,
        upload_flow_service=mock_upload_service,
        view=mock_view,
    )


@pytest.fixture
def controller_existing_client(
    state_existing_client: ClientFormState,
    mock_save_service: Mock,
    mock_upload_service: Mock,
    mock_view: Mock,
) -> ClientFormController:
    """Cria controller para cliente existente."""
    return ClientFormController(
        state=state_existing_client,
        save_service=mock_save_service,
        upload_flow_service=mock_upload_service,
        view=mock_view,
    )


# =============================================================================
# Testes de Propriedades e Configuração
# =============================================================================


def test_controller_state_property(controller_new_client: ClientFormController) -> None:
    """Testa acesso à propriedade state."""
    assert controller_new_client.state is not None
    assert isinstance(controller_new_client.state, ClientFormState)


def test_controller_view_property(controller_new_client: ClientFormController, mock_view: Mock) -> None:
    """Testa acesso à propriedade view."""
    assert controller_new_client.view is mock_view


def test_controller_set_view(state_new_client: ClientFormState, mock_save_service: Mock) -> None:
    """Testa configuração de view após inicialização."""
    controller = ClientFormController(
        state=state_new_client,
        save_service=mock_save_service,
    )

    assert controller.view is None

    new_view = Mock()
    controller.set_view(new_view)

    assert controller.view is new_view


# =============================================================================
# Testes de handle_save - Cenários de Sucesso
# =============================================================================


def test_handle_save_success_no_close(
    controller_new_client: ClientFormController,
    mock_save_service: Mock,
    mock_view: Mock,
) -> None:
    """Testa salvamento com sucesso sem fechar formulário."""
    mock_save_service.return_value = True

    result = controller_new_client.handle_save(
        show_success=True,
        close_form=False,
        refresh_list=True,
    )

    # Verificar resultado
    assert result.success is True
    assert result.close_form is False

    # Verificar chamada ao save_service
    mock_save_service.assert_called_once_with(
        show_success=True,
        close_window=False,
        refresh_list=True,
        update_row=True,
    )

    # Verificar que view.close NÃO foi chamado
    mock_view.close.assert_not_called()

    # Verificar que título foi atualizado (success + view + not close_form)
    mock_view.update_title.assert_called_once()


def test_handle_save_success_with_close(
    controller_new_client: ClientFormController,
    mock_save_service: Mock,
    mock_view: Mock,
) -> None:
    """Testa salvamento com sucesso fechando formulário."""
    mock_save_service.return_value = True

    result = controller_new_client.handle_save(
        show_success=True,
        close_form=True,
        refresh_list=True,
    )

    # Verificar resultado
    assert result.success is True
    assert result.close_form is True

    # Verificar chamada ao save_service
    mock_save_service.assert_called_once_with(
        show_success=True,
        close_window=True,
        refresh_list=True,
        update_row=True,
    )

    # Verificar que título NÃO foi atualizado (porque vai fechar)
    mock_view.update_title.assert_not_called()


def test_handle_save_updates_client_id(
    controller_new_client: ClientFormController,
    mock_save_service: Mock,
) -> None:
    """Testa que handle_save retorna client_id do estado."""
    mock_save_service.return_value = True
    controller_new_client.state.client_id = 456  # Simula ID atribuído

    result = controller_new_client.handle_save(
        show_success=False,
        close_form=False,
        refresh_list=False,
    )

    assert result.client_id == 456


# =============================================================================
# Testes de handle_save - Cenários de Falha
# =============================================================================


def test_handle_save_failure(
    controller_new_client: ClientFormController,
    mock_save_service: Mock,
    mock_view: Mock,
) -> None:
    """Testa salvamento com falha."""
    mock_save_service.return_value = False

    result = controller_new_client.handle_save(
        show_success=True,
        close_form=True,
        refresh_list=True,
    )

    # Verificar resultado
    assert result.success is False
    assert result.close_form is False  # Não fecha se falhou

    # Verificar que view.close NÃO foi chamado
    mock_view.close.assert_not_called()

    # Verificar que título NÃO foi atualizado
    mock_view.update_title.assert_not_called()


def test_handle_save_no_view(
    state_new_client: ClientFormState,
    mock_save_service: Mock,
) -> None:
    """Testa salvamento sem view configurada."""
    controller = ClientFormController(
        state=state_new_client,
        save_service=mock_save_service,
        view=None,
    )

    mock_save_service.return_value = True

    result = controller.handle_save(
        show_success=False,
        close_form=False,
        refresh_list=False,
    )

    # Deve funcionar sem erros
    assert result.success is True


def test_handle_save_view_update_title_fails(
    controller_new_client: ClientFormController,
    mock_save_service: Mock,
    mock_view: Mock,
) -> None:
    """Testa que falha em update_title não quebra o salvamento."""
    mock_save_service.return_value = True
    mock_view.update_title.side_effect = Exception("Erro no título")

    result = controller_new_client.handle_save(
        show_success=False,
        close_form=False,
        refresh_list=False,
    )

    # Salvamento deve ter sucesso mesmo com erro no título
    assert result.success is True


# =============================================================================
# Testes de handle_save_and_upload - Cenários de Sucesso
# =============================================================================


def test_handle_save_and_upload_success_new_client(
    controller_new_client: ClientFormController,
    mock_upload_service: Mock,
    mock_view: Mock,
) -> None:
    """Testa upload com sucesso para novo cliente."""
    mock_upload_service.return_value = (True, True, None)

    result = controller_new_client.handle_save_and_upload()

    # Verificar resultado
    assert result.success is True
    assert result.newly_created is True
    assert result.message is None

    # Verificar chamada ao upload_service
    mock_upload_service.assert_called_once()

    # Verificar que título foi atualizado (success + view)
    mock_view.update_title.assert_called_once()


def test_handle_save_and_upload_success_existing_client(
    controller_existing_client: ClientFormController,
    mock_upload_service: Mock,
    mock_view: Mock,
) -> None:
    """Testa upload com sucesso para cliente existente."""
    mock_upload_service.return_value = (True, False, None)

    result = controller_existing_client.handle_save_and_upload()

    # Verificar resultado
    assert result.success is True
    assert result.newly_created is False
    assert result.message is None


# =============================================================================
# Testes de handle_save_and_upload - Cenários de Falha
# =============================================================================


def test_handle_save_and_upload_no_upload_service(
    state_new_client: ClientFormState,
    mock_save_service: Mock,
) -> None:
    """Testa upload sem upload_service configurado."""
    controller = ClientFormController(
        state=state_new_client,
        save_service=mock_save_service,
        upload_flow_service=None,
    )

    result = controller.handle_save_and_upload()

    # Verificar resultado
    assert result.success is False
    assert result.message is not None
    assert "não disponível" in result.message.lower()


def test_handle_save_and_upload_upload_fails(
    controller_new_client: ClientFormController,
    mock_upload_service: Mock,
    mock_view: Mock,
) -> None:
    """Testa falha no upload."""
    mock_upload_service.return_value = (False, False, "Erro no upload")

    result = controller_new_client.handle_save_and_upload()

    # Verificar resultado
    assert result.success is False
    assert result.message == "Erro no upload"

    # Verificar que título NÃO foi atualizado (falha)
    mock_view.update_title.assert_not_called()


def test_handle_save_and_upload_no_view(
    state_new_client: ClientFormState,
    mock_save_service: Mock,
    mock_upload_service: Mock,
) -> None:
    """Testa upload sem view configurada."""
    controller = ClientFormController(
        state=state_new_client,
        save_service=mock_save_service,
        upload_flow_service=mock_upload_service,
        view=None,
    )

    mock_upload_service.return_value = (True, False, None)

    result = controller.handle_save_and_upload()

    # Deve funcionar sem erros
    assert result.success is True


# =============================================================================
# Testes de handle_cancel
# =============================================================================


def test_handle_cancel_with_view(
    controller_new_client: ClientFormController,
    mock_view: Mock,
) -> None:
    """Testa cancelamento com view configurada."""
    controller_new_client.handle_cancel()

    # Verificar que view.close foi chamado
    mock_view.close.assert_called_once()


def test_handle_cancel_no_view(
    state_new_client: ClientFormState,
    mock_save_service: Mock,
) -> None:
    """Testa cancelamento sem view configurada."""
    controller = ClientFormController(
        state=state_new_client,
        save_service=mock_save_service,
        view=None,
    )

    # Deve funcionar sem erros
    controller.handle_cancel()


# =============================================================================
# Testes de mark_dirty e mark_clean
# =============================================================================


def test_mark_dirty(controller_new_client: ClientFormController) -> None:
    """Testa marcação de dirty state."""
    state = controller_new_client.state
    state.initializing = False  # Desabilita inicialização
    state.is_dirty = False

    controller_new_client.mark_dirty()

    assert state.is_dirty is True


def test_mark_clean(controller_new_client: ClientFormController) -> None:
    """Testa marcação de clean state."""
    state = controller_new_client.state
    state.is_dirty = True

    controller_new_client.mark_clean()

    assert state.is_dirty is False


# =============================================================================
# Testes de update_title
# =============================================================================


def test_update_title_new_client(
    controller_new_client: ClientFormController,
    mock_view: Mock,
) -> None:
    """Testa atualização de título para novo cliente."""
    controller_new_client.update_title()

    # Verificar que view.update_title foi chamado
    mock_view.update_title.assert_called_once()

    # Verificar formato do título
    call_args = mock_view.update_title.call_args[0][0]
    assert "Editar Cliente" in call_args
    assert "Empresa Teste LTDA" in call_args
    assert "12.345.678/0001-90" in call_args


def test_update_title_existing_client(
    controller_existing_client: ClientFormController,
    mock_view: Mock,
) -> None:
    """Testa atualização de título para cliente existente."""
    controller_existing_client.update_title()

    # Verificar que view.update_title foi chamado
    mock_view.update_title.assert_called_once()

    # Verificar que ID está no título
    call_args = mock_view.update_title.call_args[0][0]
    assert "123" in call_args


def test_update_title_no_view(
    state_new_client: ClientFormState,
    mock_save_service: Mock,
) -> None:
    """Testa atualização de título sem view."""
    controller = ClientFormController(
        state=state_new_client,
        save_service=mock_save_service,
        view=None,
    )

    # Deve funcionar sem erros
    controller.update_title()


def test_update_title_view_fails(
    controller_new_client: ClientFormController,
    mock_view: Mock,
) -> None:
    """Testa que falha em view.update_title não quebra."""
    mock_view.update_title.side_effect = Exception("Erro no título")

    # Deve funcionar sem erros
    controller_new_client.update_title()


def test_update_title_empty_data(
    state_new_client: ClientFormState,
    mock_save_service: Mock,
    mock_view: Mock,
) -> None:
    """Testa atualização de título com dados vazios."""
    state_new_client.data.razao_social = ""
    state_new_client.data.cnpj = ""

    controller = ClientFormController(
        state=state_new_client,
        save_service=mock_save_service,
        view=mock_view,
    )

    controller.update_title()

    # Deve funcionar sem erros
    mock_view.update_title.assert_called_once()
    call_args = mock_view.update_title.call_args[0][0]
    assert "Editar Cliente" in call_args


# =============================================================================
# Testes de set_upload_button_enabled
# =============================================================================


def test_set_upload_button_enabled_true(
    controller_new_client: ClientFormController,
    mock_view: Mock,
) -> None:
    """Testa habilitação do botão de upload."""
    controller_new_client.set_upload_button_enabled(True)

    mock_view.set_upload_button_enabled.assert_called_once_with(True)


def test_set_upload_button_enabled_false(
    controller_new_client: ClientFormController,
    mock_view: Mock,
) -> None:
    """Testa desabilitação do botão de upload."""
    controller_new_client.set_upload_button_enabled(False)

    mock_view.set_upload_button_enabled.assert_called_once_with(False)


def test_set_upload_button_enabled_no_view(
    state_new_client: ClientFormState,
    mock_save_service: Mock,
) -> None:
    """Testa habilitação de botão sem view."""
    controller = ClientFormController(
        state=state_new_client,
        save_service=mock_save_service,
        view=None,
    )

    # Deve funcionar sem erros
    controller.set_upload_button_enabled(True)


def test_set_upload_button_enabled_view_fails(
    controller_new_client: ClientFormController,
    mock_view: Mock,
) -> None:
    """Testa que falha em view não quebra."""
    mock_view.set_upload_button_enabled.side_effect = Exception("Erro no botão")

    # Deve funcionar sem erros
    controller_new_client.set_upload_button_enabled(True)


# =============================================================================
# Testes de set_cartao_cnpj_button_enabled
# =============================================================================


def test_set_cartao_cnpj_button_enabled_true(
    controller_new_client: ClientFormController,
    mock_view: Mock,
) -> None:
    """Testa habilitação do botão Cartão CNPJ."""
    controller_new_client.set_cartao_cnpj_button_enabled(True)

    mock_view.set_cartao_cnpj_button_enabled.assert_called_once_with(True)


def test_set_cartao_cnpj_button_enabled_false(
    controller_new_client: ClientFormController,
    mock_view: Mock,
) -> None:
    """Testa desabilitação do botão Cartão CNPJ."""
    controller_new_client.set_cartao_cnpj_button_enabled(False)

    mock_view.set_cartao_cnpj_button_enabled.assert_called_once_with(False)


def test_set_cartao_cnpj_button_enabled_no_view(
    state_new_client: ClientFormState,
    mock_save_service: Mock,
) -> None:
    """Testa habilitação de botão sem view."""
    controller = ClientFormController(
        state=state_new_client,
        save_service=mock_save_service,
        view=None,
    )

    # Deve funcionar sem erros
    controller.set_cartao_cnpj_button_enabled(True)


def test_set_cartao_cnpj_button_enabled_view_fails(
    controller_new_client: ClientFormController,
    mock_view: Mock,
) -> None:
    """Testa que falha em view não quebra."""
    mock_view.set_cartao_cnpj_button_enabled.side_effect = Exception("Erro no botão")

    # Deve funcionar sem erros
    controller_new_client.set_cartao_cnpj_button_enabled(True)


# =============================================================================
# Testes de Integração (Fluxos Completos)
# =============================================================================


def test_integration_save_then_dirty_then_save_again(
    controller_new_client: ClientFormController,
    mock_save_service: Mock,
    mock_view: Mock,
) -> None:
    """Testa fluxo: save → modificação → save novamente."""
    mock_save_service.return_value = True
    state = controller_new_client.state
    state.initializing = False

    # 1. Salvar primeira vez
    result1 = controller_new_client.handle_save(
        show_success=True,
        close_form=False,
        refresh_list=True,
    )
    assert result1.success is True

    # 2. Modificar formulário
    controller_new_client.mark_dirty()
    assert state.is_dirty is True

    # 3. Salvar novamente
    state.client_id = 999  # Simula ID atribuído
    result2 = controller_new_client.handle_save(
        show_success=True,
        close_form=True,
        refresh_list=True,
    )
    assert result2.success is True
    assert result2.client_id == 999

    # Verificar que save_service foi chamado 2 vezes
    assert mock_save_service.call_count == 2


def test_integration_new_client_save_and_upload(
    controller_new_client: ClientFormController,
    mock_save_service: Mock,
    mock_upload_service: Mock,
    mock_view: Mock,
) -> None:
    """Testa fluxo completo: novo cliente → save+upload."""
    mock_save_service.return_value = True
    mock_upload_service.return_value = (True, True, None)

    # Executar save+upload
    result = controller_new_client.handle_save_and_upload()

    # Verificar resultado
    assert result.success is True
    assert result.newly_created is True

    # Verificar que upload_service foi chamado
    mock_upload_service.assert_called_once()

    # Verificar que título foi atualizado
    mock_view.update_title.assert_called_once()
