# -*- coding: utf-8 -*-

"""Testes core do main_screen_controller.

Testes headless da lógica de negócio da tela principal de clientes.
Sem dependências do Tkinter.
"""

from __future__ import annotations

from src.modules.clientes.viewmodel import ClienteRow
from src.modules.clientes.views import main_screen_controller as ctrl
from tests.unit.modules.clientes.views.factories_main_screen_state import (
    make_main_screen_state,
)


# ============================================================================
# Fixtures e Helpers
# ============================================================================


def make_client(
    *,
    id: str,
    razao_social: str = "Cliente",
    cnpj: str = "12.345.678/0001-99",
    nome: str = "",
    whatsapp: str = "",
    observacoes: str = "",
    status: str = "Ativo",
    ultima_alteracao: str = "",
    search_norm: str | None = None,
) -> ClienteRow:
    """Factory para criar ClienteRow de teste."""
    if search_norm is None:
        # Gerar search_norm automaticamente
        parts = [id, razao_social, cnpj, nome, whatsapp, observacoes, status]
        search_norm = " ".join(str(p).lower() for p in parts if p)

    return ClienteRow(
        id=id,
        razao_social=razao_social,
        cnpj=cnpj,
        nome=nome,
        whatsapp=whatsapp,
        observacoes=observacoes,
        status=status,
        ultima_alteracao=ultima_alteracao,
        search_norm=search_norm,
        raw={},
    )


# ============================================================================
# Testes de Ordenação
# ============================================================================


def test_order_clients_by_razao_social_asc():
    """Testa ordenação por Razão Social (A→Z)."""
    clients = [
        make_client(id="3", razao_social="Zeta Corp"),
        make_client(id="1", razao_social="Acme Inc"),
        make_client(id="2", razao_social="Beta Ltd"),
    ]

    ordered = ctrl.order_clients(clients, order_label="Razão Social (A→Z)")

    assert len(ordered) == 3
    assert ordered[0].razao_social == "Acme Inc"
    assert ordered[1].razao_social == "Beta Ltd"
    assert ordered[2].razao_social == "Zeta Corp"


def test_order_clients_by_razao_social_asc_places_empty_names_last():
    """Garante que Razão Social A→Z mantém vazios nas últimas posições."""
    clients = [
        make_client(id="1", razao_social="Ana"),
        make_client(id="2", razao_social="beta"),
        make_client(id="3", razao_social="Zeca"),
        make_client(id="4", razao_social=""),
        make_client(id="5", razao_social="   "),
    ]

    ordered = ctrl.order_clients(clients, order_label="Razǜo Social (A��'Z)")

    assert [c.razao_social for c in ordered[:3]] == ["Ana", "beta", "Zeca"]
    assert all((c.razao_social or "").strip() == "" for c in ordered[-2:])


def test_order_clients_by_razao_social_desc_places_empty_names_last(monkeypatch):
    """Garante que Razão Social Z→A mantém vazios nas últimas posições."""
    label_desc = "Razão Social (Z→A)"
    custom_choices = dict(ctrl.ORDER_CHOICES)
    custom_choices[label_desc] = ("razao_social", True)
    monkeypatch.setattr(ctrl, "ORDER_CHOICES", custom_choices)

    clients = [
        make_client(id="1", razao_social="Ana"),
        make_client(id="2", razao_social="beta"),
        make_client(id="3", razao_social="Zeca"),
        make_client(id="4", razao_social=""),
        make_client(id="5", razao_social="   "),
    ]

    ordered = ctrl.order_clients(clients, order_label=label_desc)

    assert [c.razao_social for c in ordered[:3]] == ["Zeca", "beta", "Ana"]
    assert all((c.razao_social or "").strip() == "" for c in ordered[-2:])


def test_order_clients_by_cnpj_asc():
    """Testa ordenação por CNPJ (A→Z)."""
    clients = [
        make_client(id="3", cnpj="33.333.333/0001-33"),
        make_client(id="1", cnpj="11.111.111/0001-11"),
        make_client(id="2", cnpj="22.222.222/0001-22"),
    ]

    ordered = ctrl.order_clients(clients, order_label="CNPJ (A→Z)")

    assert len(ordered) == 3
    assert ordered[0].cnpj == "11.111.111/0001-11"
    assert ordered[1].cnpj == "22.222.222/0001-22"
    assert ordered[2].cnpj == "33.333.333/0001-33"


def test_order_clients_by_nome_asc():
    """Testa ordenação por Nome (A→Z)."""
    clients = [
        make_client(id="3", nome="Zuleica"),
        make_client(id="1", nome="Ana"),
        make_client(id="2", nome="Bruno"),
    ]

    ordered = ctrl.order_clients(clients, order_label="Nome (A→Z)")

    assert len(ordered) == 3
    assert ordered[0].nome == "Ana"
    assert ordered[1].nome == "Bruno"
    assert ordered[2].nome == "Zuleica"


def test_order_clients_by_id_asc():
    """Testa ordenação por ID (1→9)."""
    clients = [
        make_client(id="30"),
        make_client(id="5"),
        make_client(id="100"),
    ]

    ordered = ctrl.order_clients(clients, order_label="ID (1→9)")

    assert len(ordered) == 3
    assert ordered[0].id == "5"
    assert ordered[1].id == "30"
    assert ordered[2].id == "100"


def test_order_clients_by_id_desc():
    """Testa ordenação por ID (9→1)."""
    clients = [
        make_client(id="5"),
        make_client(id="30"),
        make_client(id="100"),
    ]

    ordered = ctrl.order_clients(clients, order_label="ID (9→1)")

    assert len(ordered) == 3
    assert ordered[0].id == "100"
    assert ordered[1].id == "30"
    assert ordered[2].id == "5"


def test_order_clients_with_empty_list():
    """Testa ordenação com lista vazia."""
    ordered = ctrl.order_clients([], order_label="Razão Social (A→Z)")

    assert len(ordered) == 0


def test_order_clients_with_unknown_label():
    """Testa ordenação com label desconhecido (deve manter ordem original)."""
    clients = [
        make_client(id="2", razao_social="Beta"),
        make_client(id="1", razao_social="Acme"),
    ]

    ordered = ctrl.order_clients(clients, order_label="Label Inexistente")

    # Deve manter ordem original
    assert len(ordered) == 2
    assert ordered[0].id == "2"
    assert ordered[1].id == "1"


# ============================================================================
# Testes de Filtro por Status
# ============================================================================


def test_filter_clients_by_status_ativo():
    """Testa filtro por status 'Ativo'."""
    clients = [
        make_client(id="1", status="Ativo"),
        make_client(id="2", status="Inativo"),
        make_client(id="3", status="Ativo"),
    ]

    filtered = ctrl.filter_clients(clients, filter_label="Ativo")

    assert len(filtered) == 2
    assert all(c.status == "Ativo" for c in filtered)


def test_filter_clients_by_status_todos():
    """Testa filtro por status 'Todos' (sem filtro)."""
    clients = [
        make_client(id="1", status="Ativo"),
        make_client(id="2", status="Inativo"),
        make_client(id="3", status="Novo cliente"),
    ]

    filtered = ctrl.filter_clients(clients, filter_label="Todos")

    assert len(filtered) == 3


def test_filter_clients_by_search_text():
    """Testa filtro por texto de busca."""
    clients = [
        make_client(id="1", razao_social="Acme Corporation", search_norm="acme corporation"),
        make_client(id="2", razao_social="Beta Industries", search_norm="beta industries"),
        make_client(id="3", razao_social="Acme Widgets", search_norm="acme widgets"),
    ]

    filtered = ctrl.filter_clients(clients, filter_label="Todos", search_text="acme")

    assert len(filtered) == 2
    assert all("acme" in c.razao_social.lower() for c in filtered)


def test_filter_clients_combined():
    """Testa filtro combinado (status + texto de busca)."""
    clients = [
        make_client(id="1", razao_social="Acme Corp", status="Ativo", search_norm="acme corp ativo"),
        make_client(id="2", razao_social="Beta Corp", status="Inativo", search_norm="beta corp inativo"),
        make_client(id="3", razao_social="Acme Ltd", status="Ativo", search_norm="acme ltd ativo"),
        make_client(id="4", razao_social="Acme Industries", status="Inativo", search_norm="acme industries inativo"),
    ]

    filtered = ctrl.filter_clients(clients, filter_label="Ativo", search_text="acme")

    assert len(filtered) == 2
    assert all(c.status == "Ativo" and "acme" in c.razao_social.lower() for c in filtered)


# ============================================================================
# Testes de Batch Flags
# ============================================================================


def test_batch_flags_no_selection():
    """Testa flags de batch com nenhum selecionado."""
    can_delete, can_restore, can_export = ctrl.compute_batch_flags(
        [],
        is_online=True,
        is_trash_screen=False,
    )

    assert can_delete is False
    assert can_restore is False
    assert can_export is False


def test_batch_flags_single_selection_main_screen():
    """Testa flags de batch com um selecionado na tela principal."""
    can_delete, can_restore, can_export = ctrl.compute_batch_flags(
        ["1"],
        is_online=True,
        is_trash_screen=False,
    )

    assert can_delete is True
    assert can_restore is False  # Restaurar só na lixeira
    assert can_export is True


def test_batch_flags_multiple_selection_main_screen():
    """Testa flags de batch com vários selecionados na tela principal."""
    can_delete, can_restore, can_export = ctrl.compute_batch_flags(
        ["1", "2", "3"],
        is_online=True,
        is_trash_screen=False,
    )

    assert can_delete is True
    assert can_restore is False
    assert can_export is True


def test_batch_flags_single_selection_trash_screen():
    """Testa flags de batch com um selecionado na tela de lixeira."""
    can_delete, can_restore, can_export = ctrl.compute_batch_flags(
        ["1"],
        is_online=True,
        is_trash_screen=True,
    )

    assert can_delete is True
    assert can_restore is True  # Restaurar disponível na lixeira
    assert can_export is True


def test_batch_flags_offline():
    """Testa flags de batch offline (ações desabilitadas)."""
    can_delete, can_restore, can_export = ctrl.compute_batch_flags(
        ["1", "2"],
        is_online=False,
        is_trash_screen=False,
    )

    assert can_delete is False  # Delete requer online
    assert can_restore is False  # Restore requer online
    assert can_export is True  # Export não requer online


# ============================================================================
# Testes de compute_main_screen_state (Integração)
# ============================================================================


def test_compute_main_screen_state_basic():
    """Testa computação completa do estado da tela."""
    clients = [
        make_client(id="1", razao_social="Acme", status="Ativo"),
        make_client(id="2", razao_social="Beta", status="Inativo"),
        make_client(id="3", razao_social="Gamma", status="Ativo"),
    ]

    state = make_main_screen_state(
        clients=clients,
        filter_label="Ativo",
        selected_ids=["1"],
    )

    result = ctrl.compute_main_screen_state(state)

    # Verifica filtro (só ativos)
    assert len(result.visible_clients) == 2
    assert all(c.status == "Ativo" for c in result.visible_clients)

    # Verifica ordenação
    assert result.visible_clients[0].razao_social == "Acme"
    assert result.visible_clients[1].razao_social == "Gamma"

    # Verifica seleção
    assert result.selection_count == 1
    assert result.has_selection is True

    # Verifica batch flags
    assert result.can_batch_delete is True
    assert result.can_batch_restore is False
    assert result.can_batch_export is True


def test_compute_main_screen_state_with_search():
    """Testa computação do estado com busca de texto."""
    clients = [
        make_client(id="1", razao_social="Acme Corp", status="Ativo", search_norm="acme corp ativo"),
        make_client(id="2", razao_social="Beta Corp", status="Ativo", search_norm="beta corp ativo"),
        make_client(id="3", razao_social="Acme Ltd", status="Ativo", search_norm="acme ltd ativo"),
    ]

    state = make_main_screen_state(
        clients=clients,
        search_text="acme",
    )

    result = ctrl.compute_main_screen_state(state)

    # Verifica filtro de busca
    assert len(result.visible_clients) == 2
    assert all("acme" in c.razao_social.lower() for c in result.visible_clients)

    # Verifica seleção
    assert result.selection_count == 0
    assert result.has_selection is False
    assert result.can_batch_delete is False


def test_compute_main_screen_state_trash_screen():
    """Testa computação do estado na tela de lixeira."""
    clients = [
        make_client(id="1", razao_social="Cliente Deletado", status="Inativo"),
    ]

    state = make_main_screen_state(
        clients=clients,
        selected_ids=["1"],
        is_trash_screen=True,
    )

    result = ctrl.compute_main_screen_state(state)

    # Na lixeira, restore deve estar disponível
    assert result.can_batch_restore is True
    assert result.can_batch_delete is True
    assert result.can_batch_export is True


def test_compute_main_screen_state_empty_list():
    """Testa computação do estado com lista vazia."""
    state = make_main_screen_state()

    result = ctrl.compute_main_screen_state(state)

    assert len(result.visible_clients) == 0
    assert result.selection_count == 0
    assert result.has_selection is False
    assert result.can_batch_delete is False
    assert result.can_batch_restore is False
    assert result.can_batch_export is False


def test_compute_main_screen_state_multiple_selection():
    """Testa computação do estado com múltiplos clientes selecionados."""
    clients = [
        make_client(id="1", razao_social="Acme"),
        make_client(id="2", razao_social="Beta"),
        make_client(id="3", razao_social="Gamma"),
    ]

    state = make_main_screen_state(
        clients=clients,
        selected_ids=["1", "2", "3"],
    )

    result = ctrl.compute_main_screen_state(state)

    assert result.selection_count == 3
    assert result.has_selection is True
    assert result.can_batch_delete is True
    assert result.can_batch_export is True
