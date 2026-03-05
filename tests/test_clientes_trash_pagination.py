# -*- coding: utf-8 -*-
"""Testes de paginação, busca normalizada e ordenação para modo LIXEIRA.

Valida que:
  a) search_clientes_lixeira aplica range, order e ilike igual a search_clientes
  b) ViewModel com trash=True usa search_clientes_lixeira
  c) cap_hit funciona na lixeira (1000-limit)
  d) Busca normalizada (acentos/diacríticos) funciona na lixeira
  e) order_label atual é corretamente convertido (sem fallback por labels antigos)
  f) load_next_page funciona na lixeira
  g) status "[LIXEIRA]" é aplicado automaticamente em rows sem status
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
from src.core.search.search import search_clientes_lixeira  # noqa: E402
from src.core.models import Cliente  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_user(org_id: str = "org-1") -> MagicMock:
    user = MagicMock()
    user.org_id = org_id
    return user


def _make_trash_rows(n: int, *, obs_prefix: str = "") -> list[dict]:
    """Gera n rows falsas de clientes deletados."""
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
            "obs": f"{obs_prefix}Obs {i + 1}" if obs_prefix else "",
            "org_id": "org-1",
            "deleted_at": "2026-02-01T00:00:00",
        }
        for i in range(n)
    ]


def _make_clientes(n: int, *, obs: str = "") -> list[Cliente]:
    """Gera n instâncias Cliente fake."""
    return [
        Cliente(
            id=i + 1,
            numero=f"{i + 1:04d}",
            nome=f"Cliente {i + 1}",
            razao_social=f"Empresa {i + 1} Ltda",
            cnpj=f"{11111111000100 + i}",
            cnpj_norm=f"{11111111000100 + i}",
            ultima_alteracao="2026-01-01T00:00:00",
            obs=obs,
            ultima_por="user@test.com",
        )
        for i in range(n)
    ]


def _make_vm(page_size: int = 5):
    from src.modules.clientes.core.viewmodel import ClientesViewModel
    from src.modules.clientes.core.ui_helpers import ORDER_CHOICES, DEFAULT_ORDER_LABEL

    vm = ClientesViewModel(order_choices=ORDER_CHOICES, default_order_label=DEFAULT_ORDER_LABEL)
    vm._page_size = page_size
    return vm


# ===========================================================================
# A) search_clientes_lixeira — server-side (PostgREST)
# ===========================================================================


class TestSearchClientesLixeira:
    """Verifica que search_clientes_lixeira aplica range, order e deleted_at filter."""

    def _call_with_mock(
        self,
        *,
        term: str = "",
        order_by: str | None = None,
        limit: int | None = 200,
        offset: int = 0,
        rows: list[dict] | None = None,
    ) -> MagicMock:
        if rows is None:
            rows = _make_trash_rows(5)

        mock_supabase = MagicMock()
        qb = mock_supabase.table.return_value.select.return_value
        qb.not_ = MagicMock()
        qb.not_.is_.return_value = qb
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
            search_clientes_lixeira(term, order_by, limit=limit, offset=offset)

        return qb

    def test_deleted_at_not_null_filter(self):
        """Usa .not_.is_('deleted_at', 'null') para filtrar apenas deletados."""
        qb = self._call_with_mock()
        qb.not_.is_.assert_called_with("deleted_at", "null")

    def test_range_applied(self):
        """range é chamado com offset e limit corretos."""
        qb = self._call_with_mock(limit=200, offset=100)
        qb.range.assert_called_once_with(100, 299)

    def test_stable_tiebreaker_by_id(self):
        """order('id') é sempre aplicado como tiebreaker."""
        qb = self._call_with_mock(order_by="-ultima_alteracao", limit=200)
        order_calls = qb.order.call_args_list
        id_calls = [c for c in order_calls if c[0][0] == "id"]
        assert id_calls, f"Tiebreaker por id não encontrado: {order_calls}"

    def test_ilike_applied_with_term(self):
        """Quando term não é vazio, or_ com ilike é aplicado."""
        qb = self._call_with_mock(term="farmácia")
        qb.or_.assert_called()

    def test_no_range_when_limit_none(self):
        """Sem limit, range NÃO é chamado."""
        qb = self._call_with_mock(limit=None)
        qb.range.assert_not_called()


# ===========================================================================
# B) ViewModel — trash=True usa search_clientes_lixeira
# ===========================================================================


class TestViewModelTrashMode:
    """ViewModel com trash=True delega para search_clientes_lixeira."""

    def test_refresh_trash_calls_search_lixeira(self):
        """refresh_from_service(trash=True) chama search_clientes_lixeira."""
        vm = _make_vm()
        mock_search = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock_search):
            vm.refresh_from_service(trash=True)
        mock_search.assert_called_once()

    def test_refresh_trash_does_not_call_search_clientes(self):
        """refresh_from_service(trash=True) NÃO chama search_clientes."""
        vm = _make_vm()
        mock_search = MagicMock(return_value=[])
        mock_search_normal = MagicMock(return_value=[])
        with (
            patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock_search),
            patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search_normal),
        ):
            vm.refresh_from_service(trash=True)
        mock_search_normal.assert_not_called()

    def test_refresh_normal_does_not_call_lixeira(self):
        """refresh_from_service(trash=False) NÃO chama search_clientes_lixeira."""
        vm = _make_vm()
        mock_search_lixeira = MagicMock(return_value=[])
        mock_search = MagicMock(return_value=[])
        with (
            patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock_search_lixeira),
            patch("src.modules.clientes.core.viewmodel.search_clientes", mock_search),
        ):
            vm.refresh_from_service(trash=False)
        mock_search_lixeira.assert_not_called()

    def test_trash_mode_persists_for_load_next_page(self):
        """load_next_page usa search_clientes_lixeira se o refresh anterior era trash=True."""
        vm = _make_vm(page_size=3)
        # Criar clientes fake que preenchem exatamente page_size para has_more=True
        fake_page = _make_clientes(3)
        mock_lixeira = MagicMock(side_effect=[fake_page, []])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock_lixeira):
            vm.refresh_from_service(trash=True)
            assert vm.has_more is True
            vm.load_next_page()
        # Ambas as chamadas devem usar search_clientes_lixeira
        assert mock_lixeira.call_count == 2

    def test_trash_mode_property(self):
        """Propriedade trash_mode reflete o último refresh."""
        vm = _make_vm()
        mock = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(trash=True)
        assert vm.trash_mode is True

        mock_normal = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock_normal):
            vm.refresh_from_service(trash=False)
        assert vm.trash_mode is False


# ===========================================================================
# C) Ordenação — labels atuais convertidos corretamente para trash
# ===========================================================================


class TestTrashOrderLabelMapping:
    """order_label atual gera o order_by canônico correto no modo trash.

    Garante que não há fallback por labels antigos (bug 2.3 corrigido).
    """

    def _get_order_by_for_label(self, label: str) -> str | None:
        """Helper: retorna o order_by que seria passado ao backend."""
        vm = _make_vm()
        mock = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(order_label=label, trash=True)
        return mock.call_args[0][1]  # 2o arg posicional = order_by

    def test_id_asc(self):
        assert self._get_order_by_for_label("ID (1→9)") == "+id"

    def test_id_desc(self):
        assert self._get_order_by_for_label("ID (9→1)") == "-id"

    def test_razao_asc(self):
        assert self._get_order_by_for_label("Razão Social (A→Z)") == "+razao_social"

    def test_razao_desc(self):
        assert self._get_order_by_for_label("Razão Social (Z→A)") == "-razao_social"

    def test_ultima_alteracao_recente(self):
        assert self._get_order_by_for_label("Última Alteração (mais recente)") == "-ultima_alteracao"

    def test_ultima_alteracao_antiga(self):
        assert self._get_order_by_for_label("Última Alteração (mais antiga)") == "+ultima_alteracao"

    def test_cnpj_asc(self):
        assert self._get_order_by_for_label("CNPJ (A→Z)") == "+cnpj"


# ===========================================================================
# D) Paginação + cap_hit na lixeira
# ===========================================================================


class TestTrashPaginationCapHit:
    """Paginação e cap_hit funcionam no modo lixeira."""

    def test_trash_has_more_true(self):
        """has_more=True quando lixeira retorna page_size registros."""
        vm = _make_vm(page_size=5)
        mock = MagicMock(return_value=_make_clientes(5))
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(trash=True)
        assert vm.has_more is True

    def test_trash_has_more_false(self):
        """has_more=False quando lixeira retorna menos que page_size."""
        vm = _make_vm(page_size=10)
        mock = MagicMock(return_value=_make_clientes(3))
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(trash=True)
        assert vm.has_more is False

    def test_trash_load_next_page_accumulates(self):
        """load_next_page acumula registros no modo lixeira."""
        vm = _make_vm(page_size=3)
        p1 = _make_clientes(3)
        # Create distinct page2 to avoid dedup issues
        p2 = [
            Cliente(
                id=i + 100,
                numero=str(i + 100),
                nome=f"D{i}",
                razao_social=f"Del{i}",
                cnpj="",
                cnpj_norm="",
                ultima_alteracao="",
                obs="",
                ultima_por="",
            )
            for i in range(3)
        ]
        mock = MagicMock(side_effect=[p1, p2])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(trash=True)
            count1 = len(vm._clientes_raw)
            vm.load_next_page()
        assert len(vm._clientes_raw) == count1 + 3

    def test_trash_cap_hit_at_1000(self):
        """cap_hit=True quando fetch_all retorna 1000 registros na lixeira."""
        vm = _make_vm(page_size=5)
        fake_1000 = _make_clientes(1000)
        mock = MagicMock(return_value=fake_1000)
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(term="ab", fetch_all=True, trash=True)
        assert vm.cap_hit is True
        assert vm.has_more is True

    def test_trash_cap_hit_false_below_1000(self):
        """cap_hit=False quando fetch_all retorna < 1000 registros."""
        vm = _make_vm(page_size=5)
        mock = MagicMock(return_value=_make_clientes(500))
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(term="ab", fetch_all=True, trash=True)
        assert vm.cap_hit is False
        assert vm.has_more is False

    def test_trash_load_next_page_after_cap_clears_cap(self):
        """load_next_page após cap_hit com lixeira limpa cap_hit quando esgota."""
        vm = _make_vm(page_size=5)
        fake_1000 = _make_clientes(1000)
        mock = MagicMock(side_effect=[fake_1000, _make_clientes(2)])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(term="ab", fetch_all=True, trash=True)
            assert vm.cap_hit is True
            vm.load_next_page()
        # Menos que page_size → has_more=False → cap_hit limpo
        assert vm.cap_hit is False
        assert vm.has_more is False


# ===========================================================================
# E) Busca normalizada na lixeira (acentos/diacríticos)
# ===========================================================================


class TestTrashNormalizedSearch:
    """Busca na lixeira usa normalização de acentos via ViewModel._rebuild_rows."""

    def test_acucar_finds_acucar_with_accent(self):
        """Busca 'acucar' (sem acento) encontra 'Açúcar' via normalização."""
        vm = _make_vm()
        # Create a cliente with accented name
        cli = Cliente(
            id=1,
            numero="001",
            nome="Farmácia Açúcar",
            razao_social="Açúcar Ltda",
            cnpj="11111111000100",
            cnpj_norm="11111111000100",
            ultima_alteracao="",
            obs="",
            ultima_por="",
        )
        mock = MagicMock(return_value=[cli])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(trash=True)
        # Apply in-memory search filter (simulates what the view does)
        vm.set_search_text("acucar")
        rows = vm.get_rows()
        assert len(rows) == 1
        assert "Açúcar" in rows[0].razao_social

    def test_farmacia_finds_farmacia_with_accent(self):
        """Busca 'farmacia' encontra 'Farmácia'."""
        vm = _make_vm()
        cli = Cliente(
            id=1,
            numero="001",
            nome="Farmácia Central",
            razao_social="Farmácia Central Ltda",
            cnpj="11111111000100",
            cnpj_norm="11111111000100",
            ultima_alteracao="",
            obs="",
            ultima_por="",
        )
        mock = MagicMock(return_value=[cli])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(trash=True)
        vm.set_search_text("farmacia")
        rows = vm.get_rows()
        assert len(rows) == 1

    def test_empty_search_returns_all(self):
        """Busca vazia retorna todos os registros da lixeira."""
        vm = _make_vm()
        mock = MagicMock(return_value=_make_clientes(5))
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(trash=True)
        vm.set_search_text("")
        assert len(vm.get_rows()) == 5


# ===========================================================================
# F) Status "[LIXEIRA]" automático
# ===========================================================================


class TestTrashLixeiraStatusTag:
    """Rows sem status recebem '[LIXEIRA]' automaticamente no modo trash."""

    def test_empty_status_gets_lixeira_tag(self):
        """Cliente sem status na obs recebe status='[LIXEIRA]'."""
        vm = _make_vm()
        cli = Cliente(
            id=1,
            numero="001",
            nome="C1",
            razao_social="RS1",
            cnpj="",
            cnpj_norm="",
            ultima_alteracao="",
            obs="",  # sem prefixo [status]
            ultima_por="",
        )
        mock = MagicMock(return_value=[cli])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(trash=True)
        rows = vm.get_rows()
        assert len(rows) == 1
        assert rows[0].status == "[LIXEIRA]"

    def test_existing_status_preserved(self):
        """Cliente COM status na obs mantém o status original."""
        vm = _make_vm()
        cli = Cliente(
            id=1,
            numero="001",
            nome="C1",
            razao_social="RS1",
            cnpj="",
            cnpj_norm="",
            ultima_alteracao="",
            obs="[Pendente] Aguardando documentos",
            ultima_por="",
        )
        mock = MagicMock(return_value=[cli])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(trash=True)
        rows = vm.get_rows()
        assert len(rows) == 1
        assert rows[0].status == "Pendente"

    def test_active_mode_no_lixeira_tag(self):
        """No modo ativos (trash=False), status vazio permanece vazio."""
        vm = _make_vm()
        cli = Cliente(
            id=1,
            numero="001",
            nome="C1",
            razao_social="RS1",
            cnpj="",
            cnpj_norm="",
            ultima_alteracao="",
            obs="",
            ultima_por="",
        )
        mock = MagicMock(return_value=[cli])
        with patch("src.modules.clientes.core.viewmodel.search_clientes", mock):
            vm.refresh_from_service(trash=False)
        rows = vm.get_rows()
        assert len(rows) == 1
        assert rows[0].status == ""


# ===========================================================================
# G) Offset transferido entre refresh e load_next_page (trash)
# ===========================================================================


class TestTrashOffsetTracking:
    """Verifica que offset é corretamente propagado ao search_clientes_lixeira."""

    def test_refresh_passes_offset_0(self):
        """refresh_from_service(trash=True) passa offset=0."""
        vm = _make_vm(page_size=5)
        mock = MagicMock(return_value=[])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(trash=True)
        mock.assert_called_once_with("", None, limit=5, offset=0)

    def test_load_next_page_passes_correct_offset(self):
        """load_next_page passa offset correto para search_clientes_lixeira."""
        vm = _make_vm(page_size=5)
        fake_page = _make_clientes(5)
        mock = MagicMock(side_effect=[fake_page, []])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(trash=True)
            vm.load_next_page()
        assert mock.call_args_list[1] == call("", None, limit=5, offset=5)

    def test_order_by_propagated_to_load_next_page(self):
        """load_next_page reutiliza order_by salvo pelo refresh."""
        vm = _make_vm(page_size=3)
        fake_page = _make_clientes(3)
        mock = MagicMock(side_effect=[fake_page, []])
        with patch("src.modules.clientes.core.viewmodel.search_clientes_lixeira", mock):
            vm.refresh_from_service(order_label="Última Alteração (mais recente)", trash=True)
            vm.load_next_page()
        assert mock.call_args_list[1] == call("", "-ultima_alteracao", limit=3, offset=3)
