"""
Testes para src/modules/auditoria/viewmodel.py (Microfase 7).

Foco: Aumentar cobertura de ~53.8% para ≥95%

Cenários testados:
- Transformação de dados (DB → UI)
- Formatação de status, datas, CNPJ
- Filtragem de clientes (busca por texto, CNPJ)
- Construção de rows de auditoria
- Helpers de normalização
- Edge cases (None, strings vazias, dados ausentes)
"""

from __future__ import annotations

from unittest.mock import MagicMock


from src.modules.auditoria.viewmodel import (
    DEFAULT_AUDITORIA_STATUS,
    STATUS_LABELS,
    AuditoriaRow,
    AuditoriaViewModel,
    canonical_status,
    status_to_label,
)


# --- Testes de canonical_status ---


def test_canonical_status_with_valid_status():
    """Testa que status válido é retornado normalizado."""
    assert canonical_status("Em Andamento") == "em_andamento"
    assert canonical_status("PENDENTE") == "pendente"
    assert canonical_status("Finalizado") == "finalizado"


def test_canonical_status_with_alias():
    """Testa que alias 'em_processo' é convertido para 'em_andamento'."""
    assert canonical_status("em_processo") == "em_andamento"
    assert canonical_status("Em Processo") == "em_andamento"


def test_canonical_status_with_none():
    """Testa que None retorna status padrão."""
    assert canonical_status(None) == DEFAULT_AUDITORIA_STATUS


def test_canonical_status_with_empty_string():
    """Testa que string vazia retorna status padrão."""
    assert canonical_status("") == DEFAULT_AUDITORIA_STATUS
    assert canonical_status("   ") == DEFAULT_AUDITORIA_STATUS


def test_canonical_status_with_spaces():
    """Testa que espaços são substituídos por underscore."""
    assert canonical_status("Em andamento") == "em_andamento"
    assert canonical_status("EM ANDAMENTO") == "em_andamento"


# --- Testes de status_to_label ---


def test_status_to_label_with_known_status():
    """Testa conversão de status para label conhecida."""
    assert status_to_label("em_andamento") == "Em andamento"
    assert status_to_label("pendente") == "Pendente"
    assert status_to_label("finalizado") == "Finalizado"
    assert status_to_label("cancelado") == "Cancelado"


def test_status_to_label_with_alias():
    """Testa que alias é convertido antes da busca de label."""
    assert status_to_label("em_processo") == "Em andamento"


def test_status_to_label_with_unknown_status():
    """Testa que status desconhecido é capitalizado."""
    result = status_to_label("novo_status")
    assert result == "Novo status"


def test_status_to_label_with_none():
    """Testa que None retorna label do status padrão."""
    assert status_to_label(None) == STATUS_LABELS[DEFAULT_AUDITORIA_STATUS]


def test_status_to_label_with_empty_string():
    """Testa que string vazia retorna label do status padrão."""
    assert status_to_label("") == STATUS_LABELS[DEFAULT_AUDITORIA_STATUS]


# --- Testes de AuditoriaViewModel.__init__ ---


def test_viewmodel_init():
    """Testa inicialização do viewmodel."""
    vm = AuditoriaViewModel()
    assert vm._clientes == []
    assert vm._auditorias == []
    assert vm._cliente_display_map == {}
    assert vm._clientes_rows_map == {}
    assert vm._aud_index == {}
    assert vm._filtered_clientes == []
    assert vm._search_text == ""
    assert vm._selected_cliente_id is None


# --- Testes de refresh_clientes ---


def test_refresh_clientes_with_valid_data():
    """Testa refresh_clientes com dados válidos."""
    vm = AuditoriaViewModel()
    mock_fetcher = MagicMock()
    mock_fetcher.return_value = [
        {"id": 1, "razao_social": "Empresa A", "cnpj": "12345678000190"},
        {"id": 2, "razao_social": "Empresa B", "cnpj": "98765432000100"},
    ]

    vm.refresh_clientes(fetcher=mock_fetcher)

    assert len(vm._clientes) == 2
    assert "1" in vm._cliente_display_map
    assert "2" in vm._cliente_display_map
    assert "Empresa A" in vm._cliente_display_map["1"]
    assert len(vm._filtered_clientes) == 2


def test_refresh_clientes_filters_non_dict():
    """Testa que refresh_clientes filtra itens não-dict."""
    vm = AuditoriaViewModel()
    mock_fetcher = MagicMock()
    mock_fetcher.return_value = [
        {"id": 1, "razao_social": "Empresa A"},
        "invalid",
        None,
        {"id": 2, "razao_social": "Empresa B"},
    ]

    vm.refresh_clientes(fetcher=mock_fetcher)

    assert len(vm._clientes) == 2
    assert all(isinstance(c, dict) for c in vm._clientes)


def test_refresh_clientes_with_int_and_str_ids():
    """Testa que refresh_clientes indexa por id int e str."""
    vm = AuditoriaViewModel()
    mock_fetcher = MagicMock()
    mock_fetcher.return_value = [
        {"id": 123, "razao_social": "Empresa X"},
    ]

    vm.refresh_clientes(fetcher=mock_fetcher)

    # Deve estar indexado tanto por "123" (str original) quanto "123" (int convertido)
    assert "123" in vm._cliente_display_map
    assert "123" in vm._clientes_rows_map


def test_refresh_clientes_without_fetcher_uses_service():
    """Testa que refresh_clientes sem fetcher usa service padrão."""
    vm = AuditoriaViewModel()

    # Mock do service
    import src.modules.auditoria.viewmodel as viewmodel_module

    original_fetch = viewmodel_module.auditoria_service.fetch_clients
    viewmodel_module.auditoria_service.fetch_clients = MagicMock(return_value=[])

    try:
        vm.refresh_clientes()
        viewmodel_module.auditoria_service.fetch_clients.assert_called_once()
    finally:
        viewmodel_module.auditoria_service.fetch_clients = original_fetch


# --- Testes de refresh_auditorias ---


def test_refresh_auditorias_with_valid_data():
    """Testa refresh_auditorias com dados válidos."""
    vm = AuditoriaViewModel()
    vm._clientes = [{"id": 10, "razao_social": "Cliente Teste", "cnpj": "12345678000190"}]
    vm._cliente_display_map = {"10": "ID 10 — Cliente Teste — 12.345.678/0001-90"}
    vm._clientes_rows_map = {"10": vm._clientes[0]}

    mock_fetcher = MagicMock()
    mock_fetcher.return_value = [
        {
            "id": 1,
            "cliente_id": 10,
            "status": "em_andamento",
            "created_at": "2024-01-15T10:30:00",
            "updated_at": "2024-01-20T14:45:00",
        }
    ]

    rows = vm.refresh_auditorias(fetcher=mock_fetcher)

    assert len(rows) == 1
    assert rows[0].iid == "1"
    assert rows[0].cliente_id == 10
    assert rows[0].status == "em_andamento"


def test_refresh_auditorias_filters_non_dict():
    """Testa que refresh_auditorias filtra itens não-dict."""
    vm = AuditoriaViewModel()
    mock_fetcher = MagicMock()
    mock_fetcher.return_value = [
        {"id": 1, "cliente_id": 10, "status": "pendente"},
        "invalid",
        None,
    ]

    rows = vm.refresh_auditorias(fetcher=mock_fetcher)

    assert len(rows) == 1
    assert len(vm._auditorias) == 1


def test_refresh_auditorias_skips_rows_without_id():
    """Testa que auditorias sem id são ignoradas."""
    vm = AuditoriaViewModel()
    mock_fetcher = MagicMock()
    mock_fetcher.return_value = [
        {"cliente_id": 10, "status": "pendente"},  # Sem id
        {"id": 2, "cliente_id": 10, "status": "em_andamento"},
    ]

    rows = vm.refresh_auditorias(fetcher=mock_fetcher)

    assert len(rows) == 1
    assert rows[0].iid == "2"


def test_refresh_auditorias_without_fetcher_uses_service():
    """Testa que refresh_auditorias sem fetcher usa service padrão."""
    vm = AuditoriaViewModel()

    import src.modules.auditoria.viewmodel as viewmodel_module

    original_fetch = viewmodel_module.auditoria_service.fetch_auditorias
    viewmodel_module.auditoria_service.fetch_auditorias = MagicMock(return_value=[])

    try:
        vm.refresh_auditorias()
        viewmodel_module.auditoria_service.fetch_auditorias.assert_called_once()
    finally:
        viewmodel_module.auditoria_service.fetch_auditorias = original_fetch


# --- Testes de set_search_text e filtragem ---


def test_set_search_text():
    """Testa set_search_text."""
    vm = AuditoriaViewModel()
    vm._clientes = [{"id": 1, "razao_social": "Empresa A"}]
    vm._cliente_display_map = {"1": "ID 1 — Empresa A"}
    vm._clientes_rows_map = {"1": vm._clientes[0]}

    vm.set_search_text("empresa")

    assert vm._search_text == "empresa"
    assert len(vm._filtered_clientes) == 1


def test_set_search_text_filters_by_razao():
    """Testa filtragem por razão social."""
    vm = AuditoriaViewModel()
    vm._clientes = [
        {"id": 1, "razao_social": "Empresa ABC"},
        {"id": 2, "razao_social": "Companhia XYZ"},
    ]
    for c in vm._clientes:
        vm._cliente_display_map[str(c["id"])] = c["razao_social"]
        vm._clientes_rows_map[str(c["id"])] = c

    vm.set_search_text("ABC")

    assert len(vm._filtered_clientes) == 1
    assert vm._filtered_clientes[0]["id"] == 1


def test_set_search_text_filters_by_cnpj():
    """Testa filtragem por CNPJ (mínimo 5 dígitos)."""
    vm = AuditoriaViewModel()
    vm._clientes = [
        {"id": 1, "razao_social": "Empresa A", "cnpj": "12345678000190"},
        {"id": 2, "razao_social": "Empresa B", "cnpj": "98765432000100"},
    ]
    for c in vm._clientes:
        vm._cliente_display_map[str(c["id"])] = c["razao_social"]
        vm._clientes_rows_map[str(c["id"])] = c

    vm.set_search_text("12345")  # 5 dígitos

    assert len(vm._filtered_clientes) == 1
    assert vm._filtered_clientes[0]["id"] == 1


def test_set_search_text_filters_by_contact_name():
    """Testa filtragem por nome de contato."""
    vm = AuditoriaViewModel()
    vm._clientes = [
        {"id": 1, "razao_social": "Empresa A", "contact_name": "João Silva"},
        {"id": 2, "razao_social": "Empresa B", "contact_name": "Maria Santos"},
    ]
    for c in vm._clientes:
        vm._cliente_display_map[str(c["id"])] = c["razao_social"]
        vm._clientes_rows_map[str(c["id"])] = c

    vm.set_search_text("joão")

    assert len(vm._filtered_clientes) == 1
    assert vm._filtered_clientes[0]["id"] == 1


def test_set_search_text_with_empty_string_shows_all():
    """Testa que busca vazia mostra todos."""
    vm = AuditoriaViewModel()
    vm._clientes = [{"id": 1}, {"id": 2}]
    for c in vm._clientes:
        vm._cliente_display_map[str(c["id"])] = f"Cliente {c['id']}"
        vm._clientes_rows_map[str(c["id"])] = c

    vm.set_search_text("")

    assert len(vm._filtered_clientes) == 2


def test_set_search_text_with_none_shows_all():
    """Testa que busca None mostra todos."""
    vm = AuditoriaViewModel()
    vm._clientes = [{"id": 1}, {"id": 2}]
    for c in vm._clientes:
        vm._cliente_display_map[str(c["id"])] = f"Cliente {c['id']}"
        vm._clientes_rows_map[str(c["id"])] = c

    vm.set_search_text(None)

    assert len(vm._filtered_clientes) == 2


def test_set_search_text_cnpj_less_than_5_digits_ignored():
    """Testa que CNPJ com menos de 5 dígitos não é usado como filtro."""
    vm = AuditoriaViewModel()
    vm._clientes = [
        {"id": 1, "razao_social": "Empresa 123", "cnpj": "12345678000190"},
    ]
    for c in vm._clientes:
        vm._cliente_display_map[str(c["id"])] = c.get("razao_social", "")
        vm._clientes_rows_map[str(c["id"])] = c

    vm.set_search_text("123")  # Apenas 3 dígitos - deve buscar na razão

    assert len(vm._filtered_clientes) == 1  # Encontra "Empresa 123"


# --- Testes de set_selected_cliente_id ---


def test_set_selected_cliente_id():
    """Testa set_selected_cliente_id."""
    vm = AuditoriaViewModel()

    vm.set_selected_cliente_id(10)
    assert vm._selected_cliente_id == 10

    vm.set_selected_cliente_id(None)
    assert vm._selected_cliente_id is None


# --- Testes de get_filtered_clientes ---


def test_get_filtered_clientes():
    """Testa get_filtered_clientes retorna cópia."""
    vm = AuditoriaViewModel()
    vm._filtered_clientes = [{"id": 1}, {"id": 2}]

    result = vm.get_filtered_clientes()

    assert result == vm._filtered_clientes
    assert result is not vm._filtered_clientes  # Deve ser cópia


# --- Testes de get_cliente_display_map ---


def test_get_cliente_display_map():
    """Testa get_cliente_display_map retorna cópia."""
    vm = AuditoriaViewModel()
    vm._cliente_display_map = {"1": "Cliente A", "2": "Cliente B"}

    result = vm.get_cliente_display_map()

    assert result == vm._cliente_display_map
    assert result is not vm._cliente_display_map  # Deve ser cópia


# --- Testes de get_auditoria_rows ---


def test_get_auditoria_rows():
    """Testa get_auditoria_rows."""
    vm = AuditoriaViewModel()
    vm._auditorias = [{"id": 1, "cliente_id": 10, "status": "pendente"}]

    rows = vm.get_auditoria_rows()

    assert len(rows) == 1
    assert isinstance(rows[0], AuditoriaRow)


def test_get_auditoria_rows_builds_if_empty():
    """Testa que get_auditoria_rows reconstrói se vazio."""
    vm = AuditoriaViewModel()
    vm._auditorias = [{"id": 1, "cliente_id": 10, "status": "pendente"}]
    vm._aud_index = {}  # Vazio

    rows = vm.get_auditoria_rows()

    assert len(rows) == 1
    assert len(vm._aud_index) == 1


# --- Testes de get_row ---


def test_get_row_existing():
    """Testa get_row com iid existente."""
    vm = AuditoriaViewModel()
    vm._auditorias = [{"id": 1, "cliente_id": 10, "status": "pendente"}]
    vm._build_aud_rows()

    row = vm.get_row("1")

    assert row is not None
    assert row.iid == "1"


def test_get_row_non_existing():
    """Testa get_row com iid não existente."""
    vm = AuditoriaViewModel()

    row = vm.get_row("999")

    assert row is None


# --- Testes de _build_aud_rows (edge cases) ---


def test_build_aud_rows_with_alternative_date_fields():
    """Testa que _build_aud_rows usa campos alternativos de data."""
    vm = AuditoriaViewModel()
    vm._auditorias = [
        {
            "id": 1,
            "cliente_id": 10,
            "status": "pendente",
            "criado": "2024-01-15T10:30:00",  # Campo alternativo
            "atualizado": "2024-01-20T14:45:00",  # Campo alternativo
        }
    ]

    rows = vm._build_aud_rows()

    assert rows[0].created_at_iso == "2024-01-15T10:30:00"
    assert rows[0].updated_at_iso == "2024-01-20T14:45:00"


def test_build_aud_rows_with_alternative_cliente_fields():
    """Testa extração de razão social de campos alternativos."""
    vm = AuditoriaViewModel()
    vm._auditorias = [{"id": 1, "cliente_id": 10, "status": "pendente", "Razao Social": "Empresa da Auditoria"}]

    rows = vm._build_aud_rows()

    assert "Empresa da Auditoria" in rows[0].cliente_nome


def test_build_aud_rows_uses_display_map_fallback():
    """Testa que _build_aud_rows usa display_map quando cliente_txt está vazio."""
    vm = AuditoriaViewModel()
    # display_map só é usado quando cliente_txt está vazio (sem ID, razão, CNPJ)
    # Isso ocorre quando temos cliente_id mas sem dados resolvidos
    vm._cliente_display_map = {"10": "Cliente Fallback"}
    vm._auditorias = [{"id": 1, "cliente_id": 10, "status": "pendente"}]

    rows = vm._build_aud_rows()

    # Como cliente_id=10 existe, gera "ID 10", não usa fallback
    # O fallback só é usado quando cliente_txt está completamente vazio
    assert "ID 10" in rows[0].cliente_display


def test_build_aud_rows_uses_display_map_when_empty():
    """Testa que display_map é usado quando cliente_txt fica vazio."""
    vm = AuditoriaViewModel()
    vm._cliente_display_map = {"xyz": "Cliente String ID"}
    # Auditoria com cliente_id string não numérico, sem dados no row
    # cliente_ident será "xyz", mas sem razão/CNPJ → cliente_txt vazio → usa display_map
    vm._auditorias = [{"id": 1, "cliente_id": "xyz", "status": "pendente"}]

    rows = vm._build_aud_rows()

    # Como não há razão/CNPJ, cliente_txt de _cliente_display_id_first só tem "ID xyz"
    # Mas se forçarmos caso sem ID válido (0), o display_map é usado
    assert "ID xyz" in rows[0].cliente_display


def test_build_aud_rows_display_map_fallback_when_empty_txt():
    """Testa linha 157: display_map usado quando cliente_txt vazio E raw_cliente_id existe."""
    vm = AuditoriaViewModel()
    # Mock _cliente_display_id_first para retornar vazio
    import src.modules.auditoria.viewmodel as vm_module

    original_func = vm_module._cliente_display_id_first
    vm_module._cliente_display_id_first = lambda *_args, **_kwargs: ""  # Força cliente_txt vazio

    try:
        vm._cliente_display_map = {"999": "Cliente do Display Map"}
        vm._auditorias = [{"id": 1, "cliente_id": 999, "status": "pendente"}]

        rows = vm._build_aud_rows()

        # Linha 157 deve ser executada: if not cliente_txt and raw_cliente_id is not None
        assert rows[0].cliente_display == "Cliente do Display Map"
    finally:
        vm_module._cliente_display_id_first = original_func


def test_build_aud_rows_with_default_status():
    """Testa que status ausente usa padrão."""
    vm = AuditoriaViewModel()
    vm._auditorias = [{"id": 1, "cliente_id": 10}]  # Sem status

    rows = vm._build_aud_rows()

    assert rows[0].status == DEFAULT_AUDITORIA_STATUS


# --- Testes de _resolve_cliente_row ---


def test_resolve_cliente_row_with_none():
    """Testa que _resolve_cliente_row retorna None para None."""
    vm = AuditoriaViewModel()

    result = vm._resolve_cliente_row(None)

    assert result is None


def test_resolve_cliente_row_with_empty_string():
    """Testa que _resolve_cliente_row retorna None para string vazia."""
    vm = AuditoriaViewModel()

    result = vm._resolve_cliente_row("")

    assert result is None


def test_resolve_cliente_row_with_str_id():
    """Testa resolução com id string."""
    vm = AuditoriaViewModel()
    cliente = {"id": 10, "razao_social": "Empresa X"}
    vm._clientes_rows_map = {"10": cliente}

    result = vm._resolve_cliente_row("10")

    assert result == cliente


def test_resolve_cliente_row_with_int_id():
    """Testa resolução com id int."""
    vm = AuditoriaViewModel()
    cliente = {"id": 10, "razao_social": "Empresa X"}
    vm._clientes_rows_map = {"10": cliente}

    result = vm._resolve_cliente_row(10)

    assert result == cliente


def test_resolve_cliente_row_converts_int_fallback():
    """Testa linha 195: segunda busca após conversão para int."""
    vm = AuditoriaViewModel()
    cliente = {"id": 10, "razao_social": "Empresa X"}
    vm._clientes_rows_map = {"10": cliente}

    # Passar float: str(10.5) = "10.5" não encontrado
    # Mas _safe_int(10.5) = 10, str(10) = "10" encontrado na linha 195
    result = vm._resolve_cliente_row(10.5)
    assert result == cliente


def test_refresh_clientes_indexes_both_str_and_int():
    """Testa que refresh_clientes indexa por id string E int (linhas 84-91)."""
    vm = AuditoriaViewModel()
    mock_fetcher = MagicMock()
    # ID como string numérica para garantir ident_int is not None
    mock_fetcher.return_value = [{"id": "999", "razao_social": "Teste Duplo"}]

    vm.refresh_clientes(fetcher=mock_fetcher)

    # Deve ter indexado por "999" (raw_id) e "999" (ident_int convertido)
    # Ambos são a mesma chave, mas testamos que ambos os blocos executam
    assert "999" in vm._cliente_display_map
    assert "999" in vm._clientes_rows_map


# --- Testes de funções helper ---


def test_safe_int_with_int():
    """Testa _safe_int com int."""
    from src.modules.auditoria.viewmodel import _safe_int

    assert _safe_int(123) == 123


def test_safe_int_with_str():
    """Testa _safe_int com string numérica."""
    from src.modules.auditoria.viewmodel import _safe_int

    assert _safe_int("456") == 456


def test_safe_int_with_none():
    """Testa _safe_int com None."""
    from src.modules.auditoria.viewmodel import _safe_int

    assert _safe_int(None) is None


def test_safe_int_with_empty_string():
    """Testa _safe_int com string vazia."""
    from src.modules.auditoria.viewmodel import _safe_int

    assert _safe_int("") is None


def test_safe_int_with_invalid():
    """Testa _safe_int com valor inválido."""
    from src.modules.auditoria.viewmodel import _safe_int

    assert _safe_int("abc") is None


def test_cliente_razao_from_row_with_various_fields():
    """Testa extração de razão de vários campos."""
    from src.modules.auditoria.viewmodel import _cliente_razao_from_row

    assert _cliente_razao_from_row({"display_name": "Nome Display"}) == "Nome Display"
    assert _cliente_razao_from_row({"razao_social": "Razão Social"}) == "Razão Social"
    assert _cliente_razao_from_row({"Razao Social": "Razao Social Alt"}) == "Razao Social Alt"
    assert _cliente_razao_from_row({"legal_name": "Legal Name"}) == "Legal Name"
    assert _cliente_razao_from_row({"name": "Name"}) == "Name"


def test_cliente_razao_from_row_with_none():
    """Testa _cliente_razao_from_row com None."""
    from src.modules.auditoria.viewmodel import _cliente_razao_from_row

    assert _cliente_razao_from_row(None) == ""


def test_cliente_razao_from_row_with_non_dict():
    """Testa _cliente_razao_from_row com não-dict."""
    from src.modules.auditoria.viewmodel import _cliente_razao_from_row

    assert _cliente_razao_from_row("invalid") == ""


def test_cliente_cnpj_from_row():
    """Testa extração de CNPJ."""
    from src.modules.auditoria.viewmodel import _cliente_cnpj_from_row

    assert _cliente_cnpj_from_row({"cnpj": "12345678000190"}) == "12345678000190"
    assert _cliente_cnpj_from_row({"tax_id": "98765432000100"}) == "98765432000100"
    assert _cliente_cnpj_from_row(None) == ""
    assert _cliente_cnpj_from_row("invalid") == ""


def test_cliente_display_id_first():
    """Testa construção de display com ID primeiro."""
    from src.modules.auditoria.viewmodel import _cliente_display_id_first

    result = _cliente_display_id_first(10, "Empresa X", "12345678000190")
    assert "ID 10" in result
    assert "Empresa X" in result
    assert "12.345.678/0001-90" in result


def test_cliente_display_id_first_without_id():
    """Testa display sem ID."""
    from src.modules.auditoria.viewmodel import _cliente_display_id_first

    result = _cliente_display_id_first(None, "Empresa Y", "12345678000190")
    assert "ID" not in result
    assert "Empresa Y" in result


def test_cliente_display_id_first_with_zero_id():
    """Testa que ID 0 é ignorado."""
    from src.modules.auditoria.viewmodel import _cliente_display_id_first

    result = _cliente_display_id_first(0, "Empresa Z", None)
    assert "ID 0" not in result


def test_norm_text():
    """Testa normalização de texto (acentos, casefolding)."""
    from src.modules.auditoria.viewmodel import _norm_text

    assert _norm_text("João") == "joao"
    assert _norm_text("MARIA") == "maria"
    assert _norm_text("São Paulo") == "sao paulo"
    assert _norm_text(None) == ""
    assert _norm_text("") == ""


def test_digits():
    """Testa extração de dígitos."""
    from src.modules.auditoria.viewmodel import _digits

    assert _digits("12.345.678/0001-90") == "12345678000190"
    assert _digits("ABC123XYZ456") == "123456"
    assert _digits(None) == ""
    assert _digits("") == ""


def test_build_search_index():
    """Testa construção de índice de busca."""
    from src.modules.auditoria.viewmodel import _build_search_index

    cliente = {
        "razao_social": "Empresa Teste",
        "cnpj": "12345678000190",
        "contact_name": "João Silva",
        "responsavel": "Maria Santos",
    }

    index = _build_search_index(cliente)

    assert "empresa teste" in index["razao"]
    assert "12345678000190" == index["cnpj"]
    assert "joao silva" in index["nomes"]
    assert "maria santos" in index["nomes"]


def test_build_search_index_with_minimal_data():
    """Testa índice com dados mínimos."""
    from src.modules.auditoria.viewmodel import _build_search_index

    cliente = {"id": 1}

    index = _build_search_index(cliente)

    assert index["razao"] == ""
    assert index["cnpj"] == ""
    assert index["nomes"] == []
