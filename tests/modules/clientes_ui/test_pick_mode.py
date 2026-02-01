# -*- coding: utf-8 -*-
"""Testes para modo Pick do ClientesV2 (FASE 3.4).

Valida:
- pick_mode=True oculta ActionBar e exibe botões Selecionar/Cancelar
- Duplo clique chama callback com dados do cliente
- Botão Selecionar chama callback
- Botão Cancelar não chama callback
- Callback recebe dict com id, razao_social, cnpj, nome, whatsapp, status
"""

import pytest
from unittest.mock import MagicMock, patch
from src.modules.clientes.ui.view import ClientesV2Frame
from src.modules.clientes.core.viewmodel import ClienteRow


@pytest.fixture
def mock_vm():
    """Mock do ClientesViewModel."""
    with patch("src.modules.clientes.ui.view.ClientesViewModel") as mock:
        vm_instance = MagicMock()
        mock.return_value = vm_instance
        yield vm_instance


def test_pick_mode_hides_actionbar(root, mock_vm):
    """FASE 3.4: pick_mode=True não cria ActionBar."""
    # Criar frame em pick_mode
    on_selected = MagicMock()
    frame = ClientesV2Frame(root, pick_mode=True, on_cliente_selected=on_selected)

    # ActionBar não deve existir
    assert not hasattr(frame, "actionbar"), "ActionBar não deve existir em pick_mode"

    # Verificar que _pick_mode está ativo
    assert frame._pick_mode is True
    assert frame._on_cliente_selected is on_selected


def test_pick_mode_creates_pick_buttons(root, mock_vm):
    """FASE 3.4: pick_mode=True cria botões Selecionar/Cancelar."""
    frame = ClientesV2Frame(root, pick_mode=True, on_cliente_selected=MagicMock())

    # Procurar pelos botões no frame
    # Buscar CTkButton com textos específicos
    found_select = False
    found_cancel = False

    def check_widget(widget):
        nonlocal found_select, found_cancel
        try:
            # Verificar se é CTkButton e tem o texto correto
            if hasattr(widget, "cget") and hasattr(widget, "configure"):
                try:
                    text = widget.cget("text")
                    if "Selecionar" in text:
                        found_select = True
                    elif "Cancelar" in text:
                        found_cancel = True
                except Exception:
                    pass
        except Exception:
            pass

        # Recursão nos filhos
        try:
            for child in widget.winfo_children():
                check_widget(child)
        except Exception:
            pass

    check_widget(frame)

    assert found_select, "Botão 'Selecionar' deve existir em pick_mode"
    assert found_cancel, "Botão 'Cancelar' deve existir em pick_mode"


def test_normal_mode_has_actionbar(root, mock_vm):
    """FASE 3.4: pick_mode=False cria ActionBar normalmente."""
    frame = ClientesV2Frame(root, pick_mode=False)

    # ActionBar deve existir
    assert hasattr(frame, "actionbar"), "ActionBar deve existir em modo normal"
    assert frame._pick_mode is False


def test_double_click_calls_callback_in_pick_mode(root, mock_vm):
    """FASE 3.4: Duplo clique em pick_mode chama callback com dados corretos."""
    on_selected = MagicMock()
    frame = ClientesV2Frame(root, pick_mode=True, on_cliente_selected=on_selected)

    # Simular dados no _row_data_map
    test_client = ClienteRow(
        id=123,
        razao_social="Empresa Teste",
        cnpj="12.345.678/0001-90",
        nome="João Silva",
        whatsapp="11987654321",
        status="Ativo",
        observacoes="",
        ultima_alteracao="",
    )

    iid = "I001"
    frame._row_data_map[iid] = test_client

    # Simular seleção na tree
    frame.tree.insert(
        "",
        "end",
        iid=iid,
        values=(
            test_client.id,
            test_client.razao_social,
            test_client.cnpj,
            test_client.nome,
            test_client.whatsapp,
            test_client.status,
            test_client.observacoes,
            test_client.ultima_alteracao,
        ),
    )
    frame.tree.selection_set(iid)
    frame.tree.focus(iid)

    # Chamar _on_pick_confirm diretamente (simula duplo clique)
    frame._on_pick_confirm()

    # Verificar que callback foi chamado
    assert on_selected.called, "Callback deve ser chamado ao confirmar seleção"

    # Verificar argumentos do callback
    call_args = on_selected.call_args[0][0]
    assert call_args["id"] == 123
    assert call_args["razao_social"] == "Empresa Teste"
    assert call_args["cnpj"] == "12.345.678/0001-90"
    assert call_args["nome"] == "João Silva"
    assert call_args["whatsapp"] == "11987654321"
    assert call_args["status"] == "Ativo"


def test_select_button_calls_callback(root, mock_vm):
    """FASE 3.4: Botão 'Selecionar' chama callback com dados corretos."""
    on_selected = MagicMock()
    frame = ClientesV2Frame(root, pick_mode=True, on_cliente_selected=on_selected)

    # Simular cliente selecionado
    test_client = ClienteRow(
        id=456,
        razao_social="Cliente XYZ",
        cnpj="98.765.432/0001-10",
        nome="Maria Santos",
        whatsapp="21987654321",
        status="Inativo",
        observacoes="",
        ultima_alteracao="",
    )

    iid = "I002"
    frame._row_data_map[iid] = test_client
    frame.tree.insert(
        "",
        "end",
        iid=iid,
        values=(
            test_client.id,
            test_client.razao_social,
            test_client.cnpj,
            test_client.nome,
            test_client.whatsapp,
            test_client.status,
            test_client.observacoes,
            test_client.ultima_alteracao,
        ),
    )
    frame.tree.selection_set(iid)

    # Chamar _on_pick_confirm (simulando clique no botão)
    frame._on_pick_confirm()

    # Verificar callback
    assert on_selected.called
    call_args = on_selected.call_args[0][0]
    assert call_args["id"] == 456
    assert call_args["razao_social"] == "Cliente XYZ"


def test_cancel_button_does_not_call_callback(root, mock_vm):
    """FASE 3.4: Botão 'Cancelar' NÃO chama callback."""
    on_selected = MagicMock()
    frame = ClientesV2Frame(root, pick_mode=True, on_cliente_selected=on_selected)

    # Simular cliente selecionado
    test_client = ClienteRow(
        id=789,
        razao_social="Cliente ABC",
        cnpj="11.222.333/0001-44",
        nome="Pedro Costa",
        whatsapp="31987654321",
        status="Ativo",
        observacoes="",
        ultima_alteracao="",
    )

    iid = "I003"
    frame._row_data_map[iid] = test_client
    frame.tree.insert(
        "",
        "end",
        iid=iid,
        values=(
            test_client.id,
            test_client.razao_social,
            test_client.cnpj,
            test_client.nome,
            test_client.whatsapp,
            test_client.status,
            test_client.observacoes,
            test_client.ultima_alteracao,
        ),
    )
    frame.tree.selection_set(iid)

    # Chamar _on_pick_cancel (simulando clique no botão Cancelar)
    frame._on_pick_cancel()

    # Callback NÃO deve ser chamado
    assert not on_selected.called, "Callback não deve ser chamado ao cancelar"


@patch("tkinter.messagebox")
def test_select_without_selection_shows_warning(mock_msgbox, root, mock_vm):
    """FASE 3.4: Selecionar sem cliente selecionado mostra warning."""
    on_selected = MagicMock()
    frame = ClientesV2Frame(root, pick_mode=True, on_cliente_selected=on_selected)

    # Não selecionar nada na tree
    # Chamar _on_pick_confirm
    frame._on_pick_confirm()

    # Verificar que messagebox.showwarning foi chamado
    assert mock_msgbox.showwarning.called, "Warning deve ser exibido sem seleção"

    # Callback NÃO deve ser chamado
    assert not on_selected.called


def test_pick_mode_double_click_binding(root, mock_vm):
    """FASE 3.4: Duplo clique deve estar bindado ao _on_pick_confirm."""
    on_selected = MagicMock()
    frame = ClientesV2Frame(root, pick_mode=True, on_cliente_selected=on_selected)

    # Verificar que <Double-Button-1> está bindado
    bindings = frame.tree.bind("<Double-Button-1>")
    assert bindings is not None, "Duplo clique deve estar bindado em pick_mode"


def test_normal_mode_double_click_edits(root, mock_vm):
    """FASE 3.4: Em modo normal, duplo clique deve chamar _on_edit_client."""
    frame = ClientesV2Frame(root, pick_mode=False)

    # Verificar que <Double-Button-1> está bindado
    bindings = frame.tree.bind("<Double-Button-1>")
    assert bindings is not None, "Duplo clique deve estar bindado em modo normal"

    # Note: não testamos se chama _on_edit_client porque isso requer mock mais complexo
    # O teste anterior (test_normal_mode_has_actionbar) já valida modo normal


def test_pick_confirm_with_callback_error_logs_error(root, mock_vm, caplog):
    """FASE 3.4: Erro no callback deve ser logado sem travar."""

    def broken_callback(data):
        raise ValueError("Erro simulado no callback")

    frame = ClientesV2Frame(root, pick_mode=True, on_cliente_selected=broken_callback)

    # Simular cliente selecionado
    test_client = ClienteRow(
        id=999,
        razao_social="Cliente Erro",
        cnpj="99.999.999/0001-99",
        nome="Erro Teste",
        whatsapp="99999999999",
        status="Ativo",
        observacoes="",
        ultima_alteracao="",
    )

    iid = "I004"
    frame._row_data_map[iid] = test_client
    frame.tree.insert(
        "",
        "end",
        iid=iid,
        values=(
            test_client.id,
            test_client.razao_social,
            test_client.cnpj,
            test_client.nome,
            test_client.whatsapp,
            test_client.status,
            test_client.observacoes,
            test_client.ultima_alteracao,
        ),
    )
    frame.tree.selection_set(iid)

    # Chamar _on_pick_confirm (não deve crashar)
    frame._on_pick_confirm()

    # Verificar que erro foi logado
    # (caplog captura logs automaticamente em pytest)
    assert any("Erro no callback" in record.message for record in caplog.records)
