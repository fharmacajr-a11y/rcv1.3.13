# -*- coding: utf-8 -*-
"""
Testes para AuditoriaViewModel - FASE 2 TEST-001.

Cobertura:
- Refresh de clientes e auditorias
- Filtragem por texto/CNPJ
- Construção de rows de auditoria
- Normalização de status
- Formatação de display de cliente
"""

from __future__ import annotations


import pytest

from src.modules.auditoria.viewmodel import (
    AuditoriaRow,
    AuditoriaViewModel,
    canonical_status,
    status_to_label,
    _safe_int,
    _cliente_razao_from_row,
    _cliente_cnpj_from_row,
    _cliente_display_id_first,
    _norm_text,
    _digits,
    _build_search_index,
)


# ============================================================================
# TESTES DE FUNÇÕES AUXILIARES
# ============================================================================


class TestCanonicalStatus:
    """Testes para canonical_status()."""

    def test_em_andamento(self):
        """Status 'em_andamento' é preservado."""
        assert canonical_status("em_andamento") == "em_andamento"

    def test_pendente(self):
        """Status 'pendente' é preservado."""
        assert canonical_status("pendente") == "pendente"

    def test_finalizado(self):
        """Status 'finalizado' é preservado."""
        assert canonical_status("finalizado") == "finalizado"

    def test_cancelado(self):
        """Status 'cancelado' é preservado."""
        assert canonical_status("cancelado") == "cancelado"

    def test_alias_em_processo(self):
        """Alias 'em_processo' é convertido para 'em_andamento'."""
        assert canonical_status("em_processo") == "em_andamento"
        assert canonical_status("Em Processo") == "em_andamento"

    def test_none_returns_default(self):
        """None retorna status padrão."""
        assert canonical_status(None) == "em_andamento"

    def test_empty_returns_default(self):
        """String vazia retorna status padrão."""
        assert canonical_status("") == "em_andamento"
        assert canonical_status("   ") == "em_andamento"

    def test_case_insensitive(self):
        """Conversão é case-insensitive."""
        assert canonical_status("EM_ANDAMENTO") == "em_andamento"
        assert canonical_status("Pendente") == "pendente"
        assert canonical_status("FINALIZADO") == "finalizado"

    def test_spaces_to_underscores(self):
        """Espaços são convertidos em underscores."""
        assert canonical_status("Em Andamento") == "em_andamento"
        assert canonical_status("em andamento") == "em_andamento"

    def test_unknown_status_preserved(self):
        """Status desconhecido é normalizado mas preservado."""
        assert canonical_status("custom_status") == "custom_status"
        assert canonical_status("Novo Status") == "novo_status"


class TestStatusToLabel:
    """Testes para status_to_label()."""

    def test_known_labels(self):
        """Status conhecidos retornam labels corretos."""
        assert status_to_label("em_andamento") == "Em andamento"
        assert status_to_label("pendente") == "Pendente"
        assert status_to_label("finalizado") == "Finalizado"
        assert status_to_label("cancelado") == "Cancelado"

    def test_alias_converted(self):
        """Alias é convertido antes de buscar label."""
        assert status_to_label("em_processo") == "Em andamento"

    def test_unknown_capitalized(self):
        """Status desconhecido é capitalizado."""
        assert status_to_label("custom_status") == "Custom status"
        assert status_to_label("outro_qualquer") == "Outro qualquer"

    def test_none_returns_default_label(self):
        """None retorna label do status padrão."""
        assert status_to_label(None) == "Em andamento"

    def test_empty_returns_default_label(self):
        """String vazia retorna label do status padrão."""
        assert status_to_label("") == "Em andamento"


class TestSafeInt:
    """Testes para _safe_int()."""

    def test_valid_int(self):
        """Valor int retorna int."""
        assert _safe_int(42) == 42

    def test_valid_str_int(self):
        """String numérica retorna int."""
        assert _safe_int("123") == 123

    def test_none_returns_none(self):
        """None retorna None."""
        assert _safe_int(None) is None

    def test_empty_str_returns_none(self):
        """String vazia retorna None."""
        assert _safe_int("") is None

    def test_invalid_str_returns_none(self):
        """String inválida retorna None."""
        assert _safe_int("abc") is None
        assert _safe_int("12.5") is None


class TestClienteHelpers:
    """Testes para helpers de formatação de cliente."""

    def test_razao_from_row_display_name(self):
        """display_name tem prioridade."""
        row = {"display_name": "Nome Display", "razao_social": "Razão"}
        assert _cliente_razao_from_row(row) == "Nome Display"

    def test_razao_from_row_razao_social(self):
        """razao_social é fallback."""
        row = {"razao_social": "Razão Social"}
        assert _cliente_razao_from_row(row) == "Razão Social"

    def test_razao_from_row_none(self):
        """None retorna string vazia."""
        assert _cliente_razao_from_row(None) == ""

    def test_razao_from_row_empty_dict(self):
        """Dict vazio retorna string vazia."""
        assert _cliente_razao_from_row({}) == ""

    def test_cnpj_from_row(self):
        """CNPJ é extraído corretamente."""
        row = {"cnpj": "12345678901234"}
        assert _cliente_cnpj_from_row(row) == "12345678901234"

    def test_cnpj_from_row_tax_id(self):
        """tax_id é fallback para CNPJ."""
        row = {"tax_id": "98765432109876"}
        assert _cliente_cnpj_from_row(row) == "98765432109876"

    def test_cnpj_from_row_none(self):
        """None retorna string vazia."""
        assert _cliente_cnpj_from_row(None) == ""

    def test_display_id_first_all_parts(self):
        """Display com todas as partes."""
        result = _cliente_display_id_first(123, "Empresa ABC", "12345678901234")
        assert "ID 123" in result
        assert "Empresa ABC" in result

    def test_display_id_first_no_id(self):
        """Display sem ID."""
        result = _cliente_display_id_first(None, "Empresa XYZ", "")
        assert "ID" not in result
        assert "Empresa XYZ" in result

    def test_display_id_first_only_id(self):
        """Display apenas com ID."""
        result = _cliente_display_id_first(999, "", "")
        assert "ID 999" in result


class TestNormText:
    """Testes para _norm_text()."""

    def test_basic_normalization(self):
        """Texto básico é normalizado."""
        assert _norm_text("Hello World") == "hello world"

    def test_accents_removed(self):
        """Acentos são removidos."""
        assert _norm_text("Ação") == "acao"
        assert _norm_text("Café") == "cafe"
        assert _norm_text("Ñoño") == "nono"

    def test_none_returns_empty(self):
        """None retorna string vazia."""
        assert _norm_text(None) == ""

    def test_empty_returns_empty(self):
        """String vazia retorna vazia."""
        assert _norm_text("") == ""

    def test_whitespace_stripped(self):
        """Espaços são removidos das pontas."""
        assert _norm_text("  teste  ") == "teste"


class TestDigits:
    """Testes para _digits()."""

    def test_extract_digits(self):
        """Apenas dígitos são extraídos."""
        assert _digits("12.345.678/0001-90") == "12345678000190"

    def test_no_digits(self):
        """Sem dígitos retorna vazio."""
        assert _digits("abc") == ""

    def test_none_returns_empty(self):
        """None retorna vazio."""
        assert _digits(None) == ""


class TestBuildSearchIndex:
    """Testes para _build_search_index()."""

    def test_basic_index(self):
        """Índice básico é construído."""
        cliente = {
            "razao_social": "Empresa ABC",
            "cnpj": "12.345.678/0001-90",
            "contact_name": "João Silva",
        }
        idx = _build_search_index(cliente)
        assert "empresa abc" in idx["razao"]
        assert "12345678000190" == idx["cnpj"]
        assert "joao silva" in idx["nomes"]

    def test_empty_client(self):
        """Cliente vazio gera índice vazio."""
        idx = _build_search_index({})
        assert idx["razao"] == ""
        assert idx["cnpj"] == ""
        assert idx["nomes"] == []


# ============================================================================
# TESTES DO VIEWMODEL
# ============================================================================


class TestAuditoriaViewModelRefreshClientes:
    """Testes para refresh_clientes()."""

    def test_refresh_with_valid_data(self):
        """Refresh com dados válidos popula mapa."""
        vm = AuditoriaViewModel()
        clientes = [
            {"id": 1, "razao_social": "Cliente A", "cnpj": "11111111111111"},
            {"id": 2, "razao_social": "Cliente B", "cnpj": "22222222222222"},
        ]

        vm.refresh_clientes(fetcher=lambda: clientes)

        assert len(vm.get_filtered_clientes()) == 2
        display_map = vm.get_cliente_display_map()
        assert "1" in display_map
        assert "2" in display_map

    def test_refresh_filters_non_dict(self):
        """Refresh filtra elementos não-dict."""
        vm = AuditoriaViewModel()
        data = [{"id": 1, "razao_social": "Valid"}, "invalid", None, 123]

        vm.refresh_clientes(fetcher=lambda: data)

        assert len(vm.get_filtered_clientes()) == 1

    def test_refresh_empty_list(self):
        """Refresh com lista vazia limpa dados."""
        vm = AuditoriaViewModel()
        vm.refresh_clientes(fetcher=lambda: [{"id": 1}])
        assert len(vm.get_filtered_clientes()) == 1

        vm.refresh_clientes(fetcher=lambda: [])
        assert len(vm.get_filtered_clientes()) == 0


class TestAuditoriaViewModelFiltering:
    """Testes para filtragem de clientes."""

    @pytest.fixture
    def vm_with_data(self):
        """ViewModel com dados de teste."""
        vm = AuditoriaViewModel()
        clientes = [
            {"id": 1, "razao_social": "Farmácia ABC", "cnpj": "11111111111111"},
            {"id": 2, "razao_social": "Drogaria XYZ", "cnpj": "22222222222222"},
            {"id": 3, "razao_social": "Supermercado", "cnpj": "33333333333333"},
        ]
        vm.refresh_clientes(fetcher=lambda: clientes)
        return vm

    def test_filter_by_razao(self, vm_with_data):
        """Filtro por razão social."""
        vm_with_data.set_search_text("Farmácia")
        result = vm_with_data.get_filtered_clientes()
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_filter_by_cnpj(self, vm_with_data):
        """Filtro por CNPJ (5+ dígitos)."""
        vm_with_data.set_search_text("22222222222222")
        result = vm_with_data.get_filtered_clientes()
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_filter_case_insensitive(self, vm_with_data):
        """Filtro é case-insensitive."""
        vm_with_data.set_search_text("DROGARIA")
        result = vm_with_data.get_filtered_clientes()
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_filter_empty_returns_all(self, vm_with_data):
        """Filtro vazio retorna todos."""
        vm_with_data.set_search_text("")
        result = vm_with_data.get_filtered_clientes()
        assert len(result) == 3

    def test_filter_no_match(self, vm_with_data):
        """Filtro sem match retorna vazio."""
        vm_with_data.set_search_text("NãoExiste")
        result = vm_with_data.get_filtered_clientes()
        assert len(result) == 0


class TestAuditoriaViewModelAuditorias:
    """Testes para refresh/build de auditorias."""

    @pytest.fixture
    def vm_with_clientes(self):
        """ViewModel com clientes carregados."""
        vm = AuditoriaViewModel()
        clientes = [
            {"id": 1, "razao_social": "Cliente A", "cnpj": "11111111111111"},
            {"id": 2, "razao_social": "Cliente B", "cnpj": "22222222222222"},
        ]
        vm.refresh_clientes(fetcher=lambda: clientes)
        return vm

    def test_refresh_auditorias_basic(self, vm_with_clientes):
        """Refresh de auditorias retorna rows."""
        auditorias = [
            {"id": "aud-1", "cliente_id": 1, "status": "em_andamento"},
            {"id": "aud-2", "cliente_id": 2, "status": "finalizado"},
        ]

        rows = vm_with_clientes.refresh_auditorias(fetcher=lambda: auditorias)

        assert len(rows) == 2
        assert rows[0].db_id == "aud-1"
        assert rows[0].status == "em_andamento"
        assert rows[1].db_id == "aud-2"
        assert rows[1].status == "finalizado"

    def test_refresh_auditorias_status_normalized(self, vm_with_clientes):
        """Status é normalizado na construção."""
        auditorias = [
            {"id": "aud-1", "cliente_id": 1, "status": "Em Processo"},
        ]

        rows = vm_with_clientes.refresh_auditorias(fetcher=lambda: auditorias)

        assert rows[0].status == "em_andamento"
        assert rows[0].status_display == "Em andamento"

    def test_refresh_auditorias_cliente_display(self, vm_with_clientes):
        """Display do cliente é preenchido corretamente."""
        auditorias = [
            {"id": "aud-1", "cliente_id": 1, "status": "pendente"},
        ]

        rows = vm_with_clientes.refresh_auditorias(fetcher=lambda: auditorias)

        assert "Cliente A" in rows[0].cliente_display or "ID 1" in rows[0].cliente_display

    def test_refresh_auditorias_unknown_cliente(self, vm_with_clientes):
        """Cliente desconhecido não quebra."""
        auditorias = [
            {"id": "aud-1", "cliente_id": 999, "status": "pendente"},
        ]

        rows = vm_with_clientes.refresh_auditorias(fetcher=lambda: auditorias)

        assert len(rows) == 1
        assert rows[0].cliente_id == 999

    def test_refresh_auditorias_filters_invalid(self, vm_with_clientes):
        """Auditorias sem ID são filtradas."""
        auditorias = [
            {"id": "aud-1", "cliente_id": 1},
            {"cliente_id": 2},  # Sem ID
            {"id": None, "cliente_id": 1},  # ID None
        ]

        rows = vm_with_clientes.refresh_auditorias(fetcher=lambda: auditorias)

        assert len(rows) == 1

    def test_get_row_by_iid(self, vm_with_clientes):
        """get_row() retorna row pelo iid."""
        auditorias = [{"id": "aud-123", "cliente_id": 1}]
        vm_with_clientes.refresh_auditorias(fetcher=lambda: auditorias)

        row = vm_with_clientes.get_row("aud-123")

        assert row is not None
        assert row.db_id == "aud-123"

    def test_get_row_not_found(self, vm_with_clientes):
        """get_row() retorna None se não encontrado."""
        vm_with_clientes.refresh_auditorias(fetcher=lambda: [])

        row = vm_with_clientes.get_row("nonexistent")

        assert row is None


class TestAuditoriaViewModelDates:
    """Testes para formatação de datas."""

    def test_dates_formatted(self):
        """Datas são formatadas para BR."""
        vm = AuditoriaViewModel()
        vm.refresh_clientes(fetcher=lambda: [{"id": 1}])

        auditorias = [
            {
                "id": "aud-1",
                "cliente_id": 1,
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-16T14:45:00Z",
            }
        ]

        rows = vm.refresh_auditorias(fetcher=lambda: auditorias)

        # Verifica que datas ISO são preservadas
        assert rows[0].created_at_iso == "2025-01-15T10:30:00Z"
        assert rows[0].updated_at_iso == "2025-01-16T14:45:00Z"

    def test_dates_alternative_keys(self):
        """Chaves alternativas para datas funcionam."""
        vm = AuditoriaViewModel()
        vm.refresh_clientes(fetcher=lambda: [{"id": 1}])

        auditorias = [
            {
                "id": "aud-1",
                "cliente_id": 1,
                "criado": "2025-01-01T00:00:00Z",
                "atualizado": "2025-01-02T00:00:00Z",
            }
        ]

        rows = vm.refresh_auditorias(fetcher=lambda: auditorias)

        assert rows[0].created_at_iso == "2025-01-01T00:00:00Z"
        assert rows[0].updated_at_iso == "2025-01-02T00:00:00Z"


class TestAuditoriaRowDataclass:
    """Testes para AuditoriaRow dataclass."""

    def test_row_creation(self):
        """Row pode ser criada com todos os campos."""
        row = AuditoriaRow(
            iid="1",
            db_id="aud-1",
            cliente_id=123,
            cliente_display="Cliente Teste",
            cliente_nome="Teste",
            cliente_cnpj="12.345.678/0001-90",
            status="em_andamento",
            status_display="Em andamento",
            created_at="15/01/2025",
            created_at_iso="2025-01-15T00:00:00Z",
            updated_at="16/01/2025",
            updated_at_iso="2025-01-16T00:00:00Z",
        )

        assert row.iid == "1"
        assert row.cliente_id == 123
        assert row.status == "em_andamento"

    def test_row_raw_default(self):
        """Campo raw tem default vazio."""
        row = AuditoriaRow(
            iid="1",
            db_id="1",
            cliente_id=None,
            cliente_display="",
            cliente_nome="",
            cliente_cnpj="",
            status="",
            status_display="",
            created_at="",
            created_at_iso=None,
            updated_at="",
            updated_at_iso=None,
        )

        assert row.raw == {}
