# -*- coding: utf-8 -*-
"""Testes para funcionalidade de Lixeira do ClientesV2 (FASE 3.6).

Valida:
- Excluir chama mover_cliente_para_lixeira com client_id correto
- Excluir sem seleção não chama service
- Cancelar confirmação não exclui
- Botão Lixeira alterna modo trash
- Restaurar cliente da lixeira (via toggle)
"""

import pytest
from unittest.mock import MagicMock, patch, call
from src.modules.clientes.ui.view import ClientesV2Frame
from src.modules.clientes.core.viewmodel import ClienteRow


@pytest.fixture
def mock_vm():
    """Mock do ClientesViewModel."""
    with patch("src.modules.clientes.ui.view.ClientesViewModel") as mock:
        vm_instance = MagicMock()
        mock.return_value = vm_instance
        yield vm_instance


@pytest.fixture
def sample_clients():
    """Dados de exemplo para testes."""
    return [
        ClienteRow(
            id=1,
            razao_social="Empresa Alpha LTDA",
            cnpj="11.111.111/0001-11",
            nome="Alpha",
            whatsapp="11987654321",
            status="Ativo",
            observacoes="Cliente VIP",
            ultima_alteracao="2024-01-15",
        ),
        ClienteRow(
            id=2,
            razao_social="Beta Comércio SA",
            cnpj="22.222.222/0001-22",
            nome="Beta",
            whatsapp="21987654321",
            status="Inativo",
            observacoes="",
            ultima_alteracao="2024-02-10",
        ),
    ]


@patch("src.modules.clientes.core.service.mover_cliente_para_lixeira")
@patch("src.modules.lixeira.refresh_if_open")
@patch("tkinter.messagebox.askyesno")
@patch("tkinter.messagebox.showinfo")
def test_delete_calls_service_with_correct_id(
    mock_showinfo, mock_askyesno, mock_refresh, mock_mover, root, mock_vm, sample_clients
):
    """FASE 3.6: Excluir chama mover_cliente_para_lixeira com client_id correto."""
    frame = ClientesV2Frame(root)
    frame.app = MagicMock()  # Mock do app

    # Simular cliente selecionado
    client = sample_clients[0]
    iid = "I001"
    frame._row_data_map[iid] = client
    frame._selected_client_id = client.id

    frame.tree.insert(
        "",
        "end",
        iid=iid,
        values=(
            client.id,
            client.razao_social,
            client.cnpj,
            client.nome,
            client.whatsapp,
            client.status,
            client.observacoes,
            client.ultima_alteracao,
        ),
    )
    frame.tree.selection_set(iid)

    # Simular confirmação
    mock_askyesno.return_value = True

    # Chamar delete
    frame._on_delete_client()

    # Verificar que service foi chamado com ID correto
    mock_mover.assert_called_once_with(1)

    # Verificar que lixeira foi atualizada
    mock_refresh.assert_called_once()

    # Verificar que mensagem de sucesso foi exibida
    assert mock_showinfo.called


@patch("tkinter.messagebox.askyesno")
def test_delete_without_selection_does_nothing(mock_askyesno, root, mock_vm):
    """FASE 3.6: Excluir sem seleção não chama service nem mostra dialog."""
    frame = ClientesV2Frame(root)

    # Não selecionar nada
    frame._selected_client_id = None

    # Chamar delete
    frame._on_delete_client()

    # Verificar que messagebox NÃO foi chamado
    assert not mock_askyesno.called, "Não deve mostrar confirmação sem seleção"


@patch("src.modules.clientes.core.service.mover_cliente_para_lixeira")
@patch("tkinter.messagebox.askyesno")
def test_delete_cancel_does_not_call_service(mock_askyesno, mock_mover, root, mock_vm, sample_clients):
    """FASE 3.6: Cancelar confirmação não exclui cliente."""
    frame = ClientesV2Frame(root)
    frame.app = MagicMock()  # Mock do app

    # Simular cliente selecionado
    client = sample_clients[0]
    iid = "I001"
    frame._row_data_map[iid] = client
    frame._selected_client_id = client.id

    frame.tree.insert(
        "",
        "end",
        iid=iid,
        values=(
            client.id,
            client.razao_social,
            client.cnpj,
            client.nome,
            client.whatsapp,
            client.status,
            client.observacoes,
            client.ultima_alteracao,
        ),
    )

    # Simular cancelamento (usuário clica "Não")
    mock_askyesno.return_value = False

    # Chamar delete
    frame._on_delete_client()

    # Verificar que service NÃO foi chamado
    assert not mock_mover.called, "Service não deve ser chamado ao cancelar"


@patch("src.modules.clientes.core.service.mover_cliente_para_lixeira")
@patch("tkinter.messagebox.askyesno")
@patch("tkinter.messagebox.showerror")
def test_delete_handles_service_error(mock_showerror, mock_askyesno, mock_mover, root, mock_vm, sample_clients):
    """FASE 3.6: Erro no service é tratado e exibe mensagem."""
    frame = ClientesV2Frame(root)
    frame.app = MagicMock()  # Mock do app

    # Simular cliente selecionado
    client = sample_clients[0]
    iid = "I001"
    frame._row_data_map[iid] = client
    frame._selected_client_id = client.id

    frame.tree.insert(
        "",
        "end",
        iid=iid,
        values=(
            client.id,
            client.razao_social,
            client.cnpj,
            client.nome,
            client.whatsapp,
            client.status,
            client.observacoes,
            client.ultima_alteracao,
        ),
    )

    # Simular confirmação
    mock_askyesno.return_value = True

    # Simular erro no service
    mock_mover.side_effect = Exception("Erro ao mover para lixeira")

    # Chamar delete
    frame._on_delete_client()

    # Verificar que erro foi exibido
    assert mock_showerror.called, "Deve exibir erro ao falhar"


def test_trash_toggle_changes_mode(root, mock_vm):
    """FASE 3.6: Botão Lixeira alterna entre modo normal e trash."""
    frame = ClientesV2Frame(root)

    # Estado inicial: modo normal
    assert frame._trash_mode is False, "Deve iniciar em modo normal"

    # Mock do load_async para não fazer chamadas reais
    with patch.object(frame, "load_async") as mock_load:
        # Alternar para modo lixeira
        frame._on_toggle_trash()

        # Verificar que modo mudou
        assert frame._trash_mode is True, "Deve alternar para modo lixeira"

        # Verificar que load_async foi chamado com show_trash=True
        assert mock_load.called
        call_kwargs = mock_load.call_args[1]
        assert call_kwargs.get("show_trash") is True

        # Alternar de volta para modo normal
        frame._on_toggle_trash()

        # Verificar que voltou ao normal
        assert frame._trash_mode is False, "Deve voltar ao modo normal"


@patch("src.modules.clientes.core.service.mover_cliente_para_lixeira")
@patch("tkinter.messagebox.askyesno")
def test_delete_confirmation_message_includes_client_name(mock_askyesno, mock_mover, root, mock_vm, sample_clients):
    """FASE 3.6: Mensagem de confirmação inclui nome do cliente."""
    frame = ClientesV2Frame(root)
    frame.app = MagicMock()  # Mock do app

    # Simular cliente selecionado
    client = sample_clients[0]
    iid = "I001"
    frame._row_data_map[iid] = client
    frame._selected_client_id = client.id

    frame.tree.insert(
        "",
        "end",
        iid=iid,
        values=(
            client.id,
            client.razao_social,
            client.cnpj,
            client.nome,
            client.whatsapp,
            client.status,
            client.observacoes,
            client.ultima_alteracao,
        ),
    )

    # Simular cancelamento
    mock_askyesno.return_value = False

    # Chamar delete
    frame._on_delete_client()

    # Verificar que messagebox foi chamado com nome do cliente
    assert mock_askyesno.called
    call_args = mock_askyesno.call_args[0]
    message = call_args[1]

    assert "Empresa Alpha LTDA" in message or "ID 1" in message, "Mensagem deve incluir identificação do cliente"


@patch("src.modules.clientes.core.service.mover_cliente_para_lixeira")
@patch("src.modules.lixeira.refresh_if_open")
@patch("tkinter.messagebox.askyesno")
@patch("tkinter.messagebox.showinfo")
def test_delete_clears_selection_after_success(
    mock_showinfo, mock_askyesno, mock_refresh, mock_mover, root, mock_vm, sample_clients
):
    """FASE 3.6: Após exclusão bem-sucedida, seleção é limpa."""
    frame = ClientesV2Frame(root)
    frame.app = MagicMock()  # Mock do app

    # Simular cliente selecionado
    client = sample_clients[0]
    iid = "I001"
    frame._row_data_map[iid] = client
    frame._selected_client_id = client.id

    frame.tree.insert(
        "",
        "end",
        iid=iid,
        values=(
            client.id,
            client.razao_social,
            client.cnpj,
            client.nome,
            client.whatsapp,
            client.status,
            client.observacoes,
            client.ultima_alteracao,
        ),
    )

    # Simular confirmação
    mock_askyesno.return_value = True

    # Mock do load_async para não fazer chamadas reais
    with patch.object(frame, "load_async"):
        # Chamar delete
        frame._on_delete_client()

    # Verificar que seleção foi limpa
    assert frame._selected_client_id is None, "Seleção deve ser limpa após excluir"


def test_trash_mode_initial_state(root, mock_vm):
    """FASE 3.6: Estado inicial é modo normal (não trash)."""
    frame = ClientesV2Frame(root)

    assert frame._trash_mode is False, "Deve iniciar em modo normal"
    assert hasattr(frame, "_trash_mode"), "Deve ter atributo _trash_mode"


@patch("src.modules.clientes.core.service.mover_cliente_para_lixeira")
@patch("tkinter.messagebox.askyesno")
@patch("tkinter.messagebox.showinfo")
def test_delete_multiple_clients_sequentially(mock_showinfo, mock_askyesno, mock_mover, root, mock_vm, sample_clients):
    """FASE 3.6: Pode excluir múltiplos clientes sequencialmente."""
    frame = ClientesV2Frame(root)
    frame.app = MagicMock()  # Mock do app

    # Simular confirmação sempre
    mock_askyesno.return_value = True

    # Mock do load_async
    with patch.object(frame, "load_async"):
        # Excluir primeiro cliente
        client1 = sample_clients[0]
        frame._row_data_map["I001"] = client1
        frame._selected_client_id = client1.id
        frame._on_delete_client()

        # Excluir segundo cliente
        client2 = sample_clients[1]
        frame._row_data_map["I002"] = client2
        frame._selected_client_id = client2.id
        frame._on_delete_client()

    # Verificar que service foi chamado 2 vezes com IDs diferentes
    assert mock_mover.call_count == 2
    assert call(1) in mock_mover.call_args_list
    assert call(2) in mock_mover.call_args_list
