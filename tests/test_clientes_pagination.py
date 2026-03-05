# -*- coding: utf-8 -*-
"""PR5 – Testes de paginação na listagem de clientes.

Valida que:
  a) search_clientes repassa range(offset, offset+limit-1) ao Supabase
  b) search_clientes sempre aplica order("id") para paginação estável
  c) O caminho padrão NÃO faz fetch-all (limit é sempre fornecido)
  d) ViewModel.load_next_page acumula registros
  e) ViewModel.has_more reflete se há mais páginas
"""

from __future__ import annotations

import os
import sys
import types
from unittest.mock import MagicMock, call, patch

os.environ.setdefault("RC_TESTING", "1")


# ---------------------------------------------------------------------------
# Stub mínimo para sys.modules (caso rode isolado, sem Supabase real)
# ---------------------------------------------------------------------------


def _ensure_fake_module(name: str, **attrs: object) -> types.ModuleType:
    if name not in sys.modules:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod
    return sys.modules[name]


_ensure_fake_module("src.infra.supabase", db_client=MagicMock())
_ensure_fake_module("src.infra.supabase.db_client", get_supabase=MagicMock())
_ensure_fake_module("src.infra.supabase.auth_client", bind_postgrest_auth_if_any=MagicMock())
_ensure_fake_module("src.infra.supabase.http_client", HTTPX_CLIENT=MagicMock(), HTTPX_TIMEOUT=30)
_ensure_fake_module(
    "src.infra.supabase.storage_client",
    DownloadCancelledError=type("DownloadCancelledError", (Exception,), {}),
    baixar_pasta_zip=MagicMock(),
)
_ensure_fake_module(
    "src.infra.supabase_client",
    get_supabase=MagicMock(),
    supabase=MagicMock(),
    exec_postgrest=MagicMock(),
    is_supabase_online=MagicMock(return_value=True),
    get_supabase_state=MagicMock(),
    is_really_online=MagicMock(return_value=False),
    get_cloud_status_for_ui=MagicMock(),
    bind_postgrest_auth_if_any=MagicMock(),
    HTTPX_CLIENT=MagicMock(),
    HTTPX_TIMEOUT=30,
    DownloadCancelledError=type("DownloadCancelledError", (Exception,), {}),
    baixar_pasta_zip=MagicMock(),
)

# Caminhos para patch
_PATCH_SUPABASE = "src.core.search.search.supabase"
_PATCH_EXEC = "src.core.search.search.exec_postgrest"
_PATCH_IS_ONLINE = "src.core.search.search.is_supabase_online"
_PATCH_GET_USER = "src.core.search.search.get_current_user"

# Importação após stubs
from src.core.search.search import search_clientes  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_user(org_id: str = "org-1") -> MagicMock:
    user = MagicMock()
    user.org_id = org_id
    return user


def _make_rows(n: int) -> list[dict]:
    """Gera n rows falsas com schema CLIENT_COLUMNS."""
    return [
        {
            "id": i + 1,
            "numero": f"{i + 1:04d}",
            "nome": f"Cliente {i + 1}",
            "razao_social": f"Empresa {i + 1} Ltda",
            "cnpj": f"{11111111000100 + i}",
            "cnpj_norm": f"{11111111000100 + i}",
            "ultima_alteracao": "2026-01-01T00:00:00",
            "ultima_por": "user@test.com",
            "obs": "",
            "org_id": "org-1",
            "deleted_at": None,
        }
        for i in range(n)
    ]


# ===========================================================================
# Testes de search_clientes (camada de dados)
# ===========================================================================


class TestSearchClientesPagination:
    """Verifica que search_clientes aplica range e order estável."""

    def _call_with_mock(
        self,
        *,
        limit: int | None = 200,
        offset: int = 0,
        rows: list[dict] | None = None,
    ) -> MagicMock:
        """Helper: chama search_clientes com mocks e retorna o query builder."""
        if rows is None:
            rows = _make_rows(5)

        mock_supabase = MagicMock()
        # Encadear fluent API
        qb = mock_supabase.table.return_value.select.return_value
        qb.is_.return_value = qb
        qb.eq.return_value = qb
        qb.or_.return_value = qb
        qb.order.return_value = qb
        qb.range.return_value = qb

        resp = MagicMock()
        resp.data = rows

        mock_exec = MagicMock(return_value=resp)

        with (
            patch(_PATCH_SUPABASE, mock_supabase),
            patch(_PATCH_EXEC, mock_exec),
            patch(_PATCH_IS_ONLINE, return_value=True),
            patch(_PATCH_GET_USER, return_value=_fake_user()),
        ):
            search_clientes("", None, limit=limit, offset=offset)

        return qb

    def test_range_applied_when_limit_set(self):
        """range(offset, offset+limit-1) é chamado quando limit é fornecido."""
        qb = self._call_with_mock(limit=200, offset=0)
        qb.range.assert_called_once_with(0, 199)

    def test_range_with_offset(self):
        """Offset é repassado corretamente ao range."""
        qb = self._call_with_mock(limit=200, offset=400)
        qb.range.assert_called_once_with(400, 599)

    def test_stable_order_by_id(self):
        """order('id') é sempre aplicado para paginação estável."""
        qb = self._call_with_mock(limit=200)
        # Deve ter ao menos uma chamada order("id")
        order_calls = qb.order.call_args_list
        id_order = [c for c in order_calls if c[0][0] == "id"]
        assert id_order, f"order('id') não encontrado em {order_calls}"

    def test_no_range_when_limit_none(self):
        """Sem limit, range NÃO é chamado (fetch-all, só para fallback)."""
        qb = self._call_with_mock(limit=None)
        qb.range.assert_not_called()

    def test_default_path_uses_limit(self):
        """O caminho padrão (ViewModel.refresh_from_service) passa limit.

        Verifica indiretamente que nenhum caminho faz fetch-all sem intenção.
        """
        from src.modules.clientes.core.viewmodel import PAGE_SIZE

        assert PAGE_SIZE > 0, "PAGE_SIZE deve ser positivo"
        # O valor padrão é 200 — confirmado na constante
        assert PAGE_SIZE == 200


# ===========================================================================
# Testes do ViewModel (paginação)
# ===========================================================================


class TestViewModelPagination:
    """Verifica estado de paginação no ClientesViewModel."""

    def _make_vm(self, page_size: int = 5):
        from src.modules.clientes.core.viewmodel import ClientesViewModel

        vm = ClientesViewModel()
        vm._page_size = page_size
        return vm

    def _patch_search(self, rows_per_call: list[list[dict]]):
        """Retorna context manager que faz search_clientes retornar rows_per_call sequencialmente."""
        call_idx = {"i": 0}

        def _fake_search(*args, **kwargs):
            from src.core.models import Cliente

            idx = call_idx["i"]
            call_idx["i"] += 1
            rows = rows_per_call[idx] if idx < len(rows_per_call) else []
            return [
                Cliente(
                    id=r["id"],
                    numero=r.get("numero"),
                    nome=r.get("nome"),
                    razao_social=r.get("razao_social"),
                    cnpj=r.get("cnpj"),
                    cnpj_norm=r.get("cnpj_norm"),
                    ultima_alteracao=r.get("ultima_alteracao"),
                    obs=r.get("obs"),
                    ultima_por=r.get("ultima_por"),
                )
                for r in rows
            ]

        return patch("src.modules.clientes.core.viewmodel.search_clientes", side_effect=_fake_search)

    def test_refresh_sets_has_more_true(self):
        """has_more=True quando primeira página retorna page_size registros."""
        vm = self._make_vm(page_size=5)
        with self._patch_search([_make_rows(5)]):
            vm.refresh_from_service()
        assert vm.has_more is True
        assert vm._current_offset == 5

    def test_refresh_sets_has_more_false(self):
        """has_more=False quando retorna menos que page_size."""
        vm = self._make_vm(page_size=10)
        with self._patch_search([_make_rows(3)]):
            vm.refresh_from_service()
        assert vm.has_more is False
        assert vm._current_offset == 3

    def test_load_next_page_appends(self):
        """load_next_page acrescenta registros, não substitui."""
        vm = self._make_vm(page_size=3)
        page1 = _make_rows(3)
        page2 = _make_rows(3)
        with self._patch_search([page1, page2]):
            vm.refresh_from_service()
            count_after_p1 = len(vm._clientes_raw)
            vm.load_next_page()
        assert len(vm._clientes_raw) == count_after_p1 + 3

    def test_load_next_page_returns_false_when_empty(self):
        """load_next_page retorna False quando não há dados."""
        vm = self._make_vm(page_size=5)
        with self._patch_search([_make_rows(5), []]):
            vm.refresh_from_service()
            result = vm.load_next_page()
        assert result is False
        assert vm.has_more is False

    def test_load_next_page_returns_false_when_no_more(self):
        """load_next_page retorna False se has_more já é False."""
        vm = self._make_vm(page_size=10)
        with self._patch_search([_make_rows(2)]):
            vm.refresh_from_service()
        assert vm.has_more is False
        result = vm.load_next_page()
        assert result is False

    def test_offset_accumulates(self):
        """Offset incrementa a cada página carregada."""
        vm = self._make_vm(page_size=3)
        p1 = _make_rows(3)
        p2 = _make_rows(3)
        p3 = _make_rows(1)
        with self._patch_search([p1, p2, p3]):
            vm.refresh_from_service()
            assert vm._current_offset == 3
            vm.load_next_page()
            assert vm._current_offset == 6
            vm.load_next_page()
            assert vm._current_offset == 7
            assert vm.has_more is False

    def test_refresh_resets_pagination(self):
        """refresh_from_service reseta offset para 0."""
        vm = self._make_vm(page_size=3)
        p1 = _make_rows(3)
        p2 = _make_rows(3)
        p3 = _make_rows(3)  # novo refresh
        with self._patch_search([p1, p2, p3]):
            vm.refresh_from_service()
            vm.load_next_page()
            assert vm._current_offset == 6
            # Refresh reseta
            vm.refresh_from_service()
            assert vm._current_offset == 3
            assert len(vm._clientes_raw) == 3  # Substituiu, não acumulou

    def test_search_clientes_called_with_limit_offset(self):
        """refresh_from_service passa limit e offset=0 para search_clientes."""
        vm = self._make_vm(page_size=7)
        mock_search = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service()
        mock_search.assert_called_once_with("", None, limit=7, offset=0)

    def test_load_next_page_passes_correct_offset(self):
        """load_next_page passa offset correto para search_clientes."""
        vm = self._make_vm(page_size=5)
        from src.core.models import Cliente

        fake_clientes = [
            Cliente(
                id=i,
                numero=str(i),
                nome=f"C{i}",
                razao_social=f"RS{i}",
                cnpj="",
                cnpj_norm="",
                ultima_alteracao="",
                obs="",
                ultima_por="",
            )
            for i in range(5)
        ]
        mock_search = MagicMock(side_effect=[fake_clientes, []])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service()
            vm.load_next_page()
        assert mock_search.call_args_list[1] == call("", None, limit=5, offset=5)


# ===========================================================================
# Testes da propagação server-side (order_label + term)
# ===========================================================================


class TestViewModelServerSide:
    """Verifica que refresh_from_service propaga term e order_by ao backend."""

    def _make_vm(self, page_size: int = 5):
        from src.modules.clientes.core.viewmodel import ClientesViewModel
        from src.modules.clientes.core.ui_helpers import ORDER_CHOICES, DEFAULT_ORDER_LABEL

        vm = ClientesViewModel(order_choices=ORDER_CHOICES, default_order_label=DEFAULT_ORDER_LABEL)
        vm._page_size = page_size
        return vm

    def test_order_label_ultima_alteracao_recente(self):
        """Quando order_label='Última Alteração (mais recente)', search_clientes recebe '-ultima_alteracao'."""
        vm = self._make_vm()
        mock_search = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(order_label="Última Alteração (mais recente)")
        mock_search.assert_called_once_with("", "-ultima_alteracao", limit=5, offset=0)

    def test_order_label_id_desc(self):
        """order_label='ID (9→1)' → '-id'."""
        vm = self._make_vm()
        mock_search = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(order_label="ID (9→1)")
        mock_search.assert_called_once_with("", "-id", limit=5, offset=0)

    def test_order_label_razao_asc(self):
        """order_label='Razão Social (A→Z)' → '+razao_social'."""
        vm = self._make_vm()
        mock_search = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(order_label="Razão Social (A→Z)")
        mock_search.assert_called_once_with("", "+razao_social", limit=5, offset=0)

    def test_term_propagated(self):
        """Termo de busca é passado ao search_clientes."""
        vm = self._make_vm()
        mock_search = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(term="farmácia")
        assert mock_search.call_args[0][0] == "farmácia"

    def test_fetch_all_sends_limit_1000(self):
        """fetch_all=True chama search_clientes com limit=1000 (safety cap)."""
        vm = self._make_vm()
        mock_search = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(term="abc", fetch_all=True)
        assert mock_search.call_args == call("abc", None, limit=1000, offset=0)
        assert vm.has_more is False
        assert vm._fetch_all is True

    def test_fetch_all_blocks_load_next_page(self):
        """Quando fetch_all=True, load_next_page retorna False imediatamente."""
        vm = self._make_vm()
        mock_search = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(term="abc", fetch_all=True)
        result = vm.load_next_page()
        assert result is False

    def test_clear_search_resets_to_paged(self):
        """Após búsqueda com fetch_all, um refresh sem term volta ao modo paginado."""
        from src.core.models import Cliente

        vm = self._make_vm(page_size=5)
        fake5 = [
            Cliente(
                id=i,
                numero=str(i),
                nome=f"C{i}",
                razao_social=f"RS{i}",
                cnpj="",
                cnpj_norm="",
                ultima_alteracao="",
                obs="",
                ultima_por="",
            )
            for i in range(5)
        ]
        mock_search = MagicMock(side_effect=[[], fake5])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(term="busca", fetch_all=True)
            assert vm._fetch_all is True
            # Limpar búsqueda
            vm.refresh_from_service()
        assert vm._fetch_all is False
        assert mock_search.call_args == call("", None, limit=5, offset=0)

    def test_fetch_all_short_term_fallback_to_paged(self):
        """Termo com menos de 2 caracteres desativa fetch_all."""
        vm = self._make_vm(page_size=5)
        mock_search = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(term="x", fetch_all=True)
        # Deve ter feito fallback para paginação normal (page_size)
        assert mock_search.call_args == call("x", None, limit=5, offset=0)
        assert vm._fetch_all is False

    def test_fetch_all_empty_term_fallback_to_paged(self):
        """Termo vazio desativa fetch_all."""
        vm = self._make_vm(page_size=5)
        mock_search = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(term="", fetch_all=True)
        assert mock_search.call_args == call("", None, limit=5, offset=0)
        assert vm._fetch_all is False

    def test_fetch_all_cap_has_more_when_limit_reached(self):
        """Quando fetch_all retorna exatamente 1000 registros, has_more=True e cap_hit=True."""
        from src.core.models import Cliente

        vm = self._make_vm(page_size=5)
        fake_1000 = [
            Cliente(
                id=i,
                numero=str(i),
                nome=f"C{i}",
                razao_social=f"RS{i}",
                cnpj="",
                cnpj_norm="",
                ultima_alteracao="",
                obs="",
                ultima_por="",
            )
            for i in range(1000)
        ]
        mock_search = MagicMock(return_value=fake_1000)
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(term="ab", fetch_all=True)
        assert vm.has_more is True
        assert vm.cap_hit is True
        assert vm._current_offset == 1000

    def test_load_next_page_uses_saved_order(self):
        """load_next_page reutiliza _server_order_by e _server_term salvos."""
        from src.core.models import Cliente

        vm = self._make_vm(page_size=3)
        page = [
            Cliente(
                id=i,
                numero=str(i),
                nome=f"C{i}",
                razao_social=f"RS{i}",
                cnpj="",
                cnpj_norm="",
                ultima_alteracao="",
                obs="",
                ultima_por="",
            )
            for i in range(3)
        ]
        mock_search = MagicMock(side_effect=[page, []])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(order_label="Última Alteração (mais recente)")
            vm.load_next_page()
        # Segunda chamada deve usar mesmos params
        assert mock_search.call_args_list[1] == call("", "-ultima_alteracao", limit=3, offset=3)

    def test_load_next_page_works_after_cap_hit(self):
        """load_next_page funciona após cap_hit e limpa cap_hit quando acabar."""
        from src.core.models import Cliente

        vm = self._make_vm(page_size=5)
        # Primeira chamada: 1000 resultados → cap_hit
        fake_1000 = [
            Cliente(
                id=i,
                numero=str(i),
                nome=f"C{i}",
                razao_social=f"RS{i}",
                cnpj="",
                cnpj_norm="",
                ultima_alteracao="",
                obs="",
                ultima_por="",
            )
            for i in range(1000)
        ]
        # Segunda chamada: apenas 3 resultados → não há mais
        fake_3 = [
            Cliente(
                id=i,
                numero=str(i),
                nome=f"C{i}",
                razao_social=f"RS{i}",
                cnpj="",
                cnpj_norm="",
                ultima_alteracao="",
                obs="",
                ultima_por="",
            )
            for i in range(1000, 1003)
        ]
        mock_search = MagicMock(side_effect=[fake_1000, fake_3])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(term="ab", fetch_all=True)
            assert vm.cap_hit is True
            assert vm.has_more is True

            result = vm.load_next_page()

        assert result is True
        assert vm.cap_hit is False
        assert vm.has_more is False
        assert vm._current_offset == 1003
        assert len(vm._clientes_raw) == 1003

    def test_cap_hit_false_below_limit(self):
        """cap_hit é False quando fetch_all retorna menos de 1000."""
        from src.core.models import Cliente

        vm = self._make_vm(page_size=5)
        fake_50 = [
            Cliente(
                id=i,
                numero=str(i),
                nome=f"C{i}",
                razao_social=f"RS{i}",
                cnpj="",
                cnpj_norm="",
                ultima_alteracao="",
                obs="",
                ultima_por="",
            )
            for i in range(50)
        ]
        mock_search = MagicMock(return_value=fake_50)
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service(term="ab", fetch_all=True)
        assert vm.cap_hit is False
        assert vm.has_more is False

    def test_cap_hit_false_in_normal_pagination(self):
        """cap_hit permanece False em modo paginado normal."""
        vm = self._make_vm(page_size=5)
        mock_search = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search):
            vm.refresh_from_service()
        assert vm.cap_hit is False

    def test_no_order_choices_defaults_none(self):
        """VM sem order_choices: _label_to_server_order retorna None."""
        from src.modules.clientes.core.viewmodel import ClientesViewModel

        vm = ClientesViewModel()
        assert vm._label_to_server_order("anything") is None


# ===========================================================================
# Testes de _normalize_order estendido
# ===========================================================================


class TestNormalizeOrderExtended:
    """Testa os novos formatos aceitos por _normalize_order."""

    def test_prefix_minus(self):
        from src.core.search.search import _normalize_order

        assert _normalize_order("-id") == ("id", True)

    def test_prefix_plus(self):
        from src.core.search.search import _normalize_order

        assert _normalize_order("+razao_social") == ("razao_social", False)

    def test_suffix_desc(self):
        from src.core.search.search import _normalize_order

        assert _normalize_order("ultima_alteracao_desc") == ("ultima_alteracao", True)

    def test_suffix_asc(self):
        from src.core.search.search import _normalize_order

        assert _normalize_order("ultima_alteracao_asc") == ("ultima_alteracao", False)

    def test_legacy_still_works(self):
        from src.core.search.search import _normalize_order

        assert _normalize_order("ultima_alteracao") == ("ultima_alteracao", True)
        assert _normalize_order("nome") == ("nome", False)

    def test_none_returns_none(self):
        from src.core.search.search import _normalize_order

        assert _normalize_order(None) == (None, False)

    def test_empty_returns_none(self):
        from src.core.search.search import _normalize_order

        assert _normalize_order("") == (None, False)


# ===========================================================================
# Testes de desempate (tiebreaker) estável por id
# ===========================================================================


class TestStableTiebreaker:
    """Verifica que o desempate por ``id`` acompanha a direção do sort principal."""

    def _call_and_get_qb(self, order_by: str | None) -> MagicMock:
        """Chama search_clientes com mocks e retorna o query builder."""
        mock_supabase = MagicMock()
        qb = mock_supabase.table.return_value.select.return_value
        qb.is_.return_value = qb
        qb.eq.return_value = qb
        qb.or_.return_value = qb
        qb.order.return_value = qb
        qb.range.return_value = qb

        resp = MagicMock()
        resp.data = _make_rows(3)

        mock_exec = MagicMock(return_value=resp)

        with (
            patch(_PATCH_SUPABASE, mock_supabase),
            patch(_PATCH_EXEC, mock_exec),
            patch(_PATCH_IS_ONLINE, return_value=True),
            patch(_PATCH_GET_USER, return_value=_fake_user()),
        ):
            search_clientes("", order_by, limit=200, offset=0)

        return qb

    def test_tiebreaker_desc_when_primary_desc(self):
        """Quando primary sort é DESC, order('id', desc=True) é chamado."""
        qb = self._call_and_get_qb("-ultima_alteracao")
        order_calls = qb.order.call_args_list
        # Segundo .order() é o tiebreaker
        assert len(order_calls) >= 2
        tiebreaker = order_calls[-1]
        assert tiebreaker == call("id", desc=True)

    def test_tiebreaker_asc_when_primary_asc(self):
        """Quando primary sort é ASC, order('id', desc=False) é chamado."""
        qb = self._call_and_get_qb("+nome")
        order_calls = qb.order.call_args_list
        assert len(order_calls) >= 2
        tiebreaker = order_calls[-1]
        assert tiebreaker == call("id", desc=False)

    def test_tiebreaker_asc_when_no_primary_sort(self):
        """Sem sort explícito (order_by=None), tiebreaker é id ASC (desc=False)."""
        qb = self._call_and_get_qb(None)
        order_calls = qb.order.call_args_list
        # Apenas 1 chamada: order("id", desc=False)
        assert len(order_calls) == 1
        assert order_calls[0] == call("id", desc=False)

    def test_primary_and_tiebreaker_both_present(self):
        """Dois order() calls são feitos: campo principal + id."""
        qb = self._call_and_get_qb("-cnpj")
        order_calls = qb.order.call_args_list
        assert order_calls[0] == call("cnpj", desc=True)
        assert order_calls[1] == call("id", desc=True)
