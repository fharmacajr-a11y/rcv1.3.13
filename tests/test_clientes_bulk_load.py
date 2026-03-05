# -*- coding: utf-8 -*-
"""Teste de carga / smoke para o módulo de Clientes.

Valida:
  a) Inserção em lote de N clientes sem exception
  b) Listagem retorna N registros
  c) Ordenação por Nome A→Z e Z→A funciona sem erro
  d) Ordenação por Telefone DDD asc/desc funciona sem erro
  e) Abrir 5 clientes aleatórios no editor → campos preenchidos corretamente
  f) Deduplicação por CNPJ funciona
  g) normalize_br_whatsapp e format_phone_br não quebram com dados variados

Execução:
  pytest tests/test_clientes_bulk_load.py -v
"""

from __future__ import annotations

import random
import string
import sys
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Minimal stubs to avoid importing full app dependencies
# ---------------------------------------------------------------------------


def _mk_mod(name: str, **attrs: Any) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# ---------------------------------------------------------------------------
# Test helpers — synthetic client generation
# ---------------------------------------------------------------------------

_FIRST_NAMES = [
    "Ana",
    "Bruno",
    "Carlos",
    "Diana",
    "Eduardo",
    "Fernanda",
    "Gabriel",
    "Helena",
    "Igor",
    "Juliana",
    "Kaique",
    "Larissa",
    "Marcos",
    "Natália",
    "Otávio",
    "Patrícia",
    "Rafael",
    "Sandra",
    "Thiago",
    "Vanessa",
    "Wagner",
    "Xavier",
    "Yara",
    "Zélia",
    "José",
    "Maria",
    "João",
    "Antônio",
    "Paulo",
    "Roberto",
]

_LAST_NAMES = [
    "Silva",
    "Santos",
    "Oliveira",
    "Souza",
    "Rodrigues",
    "Ferreira",
    "Alves",
    "Pereira",
    "Lima",
    "Gomes",
    "Costa",
    "Ribeiro",
    "Martins",
    "Carvalho",
    "Almeida",
    "Lopes",
    "Barros",
    "Araújo",
    "Nascimento",
    "Mendes",
    "Monteiro",
    "Freitas",
    "Barbosa",
    "Moura",
]

_DDDS = [
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "17",
    "18",
    "19",
    "21",
    "22",
    "24",
    "27",
    "28",
    "31",
    "32",
    "33",
    "34",
    "35",
    "37",
    "38",
    "41",
    "42",
    "43",
    "44",
    "45",
    "46",
    "47",
    "48",
    "49",
    "51",
    "53",
    "54",
    "55",
    "61",
    "62",
    "63",
    "64",
    "65",
    "66",
    "67",
    "68",
    "69",
    "71",
    "73",
    "74",
    "75",
    "77",
    "79",
    "81",
    "82",
    "83",
    "84",
    "85",
    "86",
    "87",
    "88",
    "89",
    "91",
    "92",
    "93",
    "94",
    "95",
    "96",
    "97",
    "98",
    "99",
]


def _random_cnpj_digits() -> str:
    """Gera 14 dígitos aleatórios (sem validação de check-digit)."""
    return "".join(random.choices(string.digits, k=14))


def _random_phone(ddd: str | None = None) -> str:
    """Gera telefone celular BR no formato DDXXXXXXXXX (11 dígitos)."""
    ddd = ddd or random.choice(_DDDS)
    # Celular começa com 9
    rest = "9" + "".join(random.choices(string.digits, k=8))
    return f"{ddd}{rest}"


def generate_synthetic_clients(n: int) -> list[dict[str, str]]:
    """Gera N clientes sintéticos com variação de dados."""
    clients: list[dict[str, str]] = []
    for i in range(n):
        first = random.choice(_FIRST_NAMES)
        last = random.choice(_LAST_NAMES)
        razao = f"{first} {last} {'ME' if i % 3 == 0 else 'LTDA' if i % 3 == 1 else 'S/A'}"
        cnpj = _random_cnpj_digits()
        nome = f"{first} {last[0]}."
        ddd = random.choice(_DDDS)
        phone = _random_phone(ddd)
        # Variações de formato de telefone
        if i % 5 == 0:
            phone_fmt = phone  # raw digits
        elif i % 5 == 1:
            phone_fmt = f"+55{phone}"  # com prefixo
        elif i % 5 == 2:
            phone_fmt = f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"  # formatado
        elif i % 5 == 3:
            phone_fmt = f"55 {phone[:2]} {phone[2:]}"  # espaços
        else:
            phone_fmt = ""  # vazio (sem telefone)

        obs_choices = ["", "[Ativo] Cliente ativo", "[Inativo] Sem contato", "Sem observações"]
        obs = random.choice(obs_choices)

        clients.append(
            {
                "razao_social": razao,
                "cnpj": cnpj,
                "nome": nome,
                "numero": phone_fmt,
                "obs": obs,
            }
        )
    return clients


# ---------------------------------------------------------------------------
# Test: phone_utils não quebra com entradas variadas
# ---------------------------------------------------------------------------
class TestPhoneUtilsRobustness(unittest.TestCase):
    """Verifica que normalize_br_whatsapp e format_phone_br não quebram."""

    def test_normalize_br_whatsapp_varied_inputs(self) -> None:
        from src.utils.phone_utils import normalize_br_whatsapp

        test_cases = [
            None,
            "",
            "abc",
            "123",
            "11987654321",
            "5511987654321",
            "+55 11 98765-4321",
            "(11) 98765-4321",
            "0800 123 4567",
            "55 11 98765 4321",
            "11 3456-7890",
            "+551134567890",
            "99",
            "1198765",
            "  ",
            "11 9 8765-4321",
        ]
        for raw in test_cases:
            result = normalize_br_whatsapp(raw)
            self.assertIsInstance(result, dict, f"Failed for input: {raw!r}")
            self.assertIn("display", result)
            self.assertIn("e164", result)
            self.assertIn("ddd", result)

    def test_format_phone_br_varied_inputs(self) -> None:
        from src.utils.phone_utils import format_phone_br

        # Nenhuma dessas deve levantar exception
        test_cases = [
            None,
            "",
            "abc",
            "123",
            "11987654321",
            "5511987654321",
            "+55 11 98765-4321",
            "(11) 98765-4321",
            "0800 123 4567",
        ]
        for raw in test_cases:
            result = format_phone_br(raw)
            self.assertIsInstance(result, str, f"Failed for input: {raw!r}")

    def test_empty_whatsapp_no_crash_on_sort(self) -> None:
        """Vazio no WhatsApp não deve quebrar a ordenação."""
        from src.utils.phone_utils import normalize_br_whatsapp

        items = [
            normalize_br_whatsapp("11987654321"),
            normalize_br_whatsapp(""),
            normalize_br_whatsapp(None),
            normalize_br_whatsapp("21999998888"),
        ]
        # Ordenar por display — não deve levantar
        sorted_items = sorted(items, key=lambda x: x["display"])
        self.assertEqual(len(sorted_items), 4)


# ---------------------------------------------------------------------------
# Test: ViewModel — ordering and filtering with synthetic data
# ---------------------------------------------------------------------------
class TestViewModelBulkOrdering(unittest.TestCase):
    """Testa ordenação e filtro do ViewModel com dados em massa (sem I/O)."""

    def _make_vm(self, clients: list[dict[str, str]]) -> Any:
        """Cria ViewModel e injeta clientes fake via load_from_iterable."""
        from src.modules.clientes.core.viewmodel import ClientesViewModel
        from src.modules.clientes.core.ui_helpers import ORDER_CHOICES, DEFAULT_ORDER_LABEL
        from src.core.models import Cliente

        vm = ClientesViewModel(
            order_choices=ORDER_CHOICES,
            default_order_label=DEFAULT_ORDER_LABEL,
        )
        # Converter dicts para objetos Cliente
        objs = [
            Cliente(
                id=i + 1,
                numero=c.get("numero"),
                nome=c.get("nome"),
                razao_social=c.get("razao_social"),
                cnpj=c.get("cnpj"),
                cnpj_norm=c.get("cnpj_norm", ""),
                ultima_alteracao=None,
                obs=c.get("obs"),
                ultima_por=None,
                created_at=None,
            )
            for i, c in enumerate(clients)
        ]
        vm.load_from_iterable(objs)
        return vm

    def test_bulk_1000_no_exception(self) -> None:
        """Inserir 1000 clientes no ViewModel não levanta exception."""
        clients = generate_synthetic_clients(1000)
        vm = self._make_vm(clients)
        rows = vm.get_rows()
        self.assertEqual(len(rows), 1000)

    def test_sort_nome_az(self) -> None:
        """Ordenação por Nome A→Z funciona com 1000 clientes."""
        clients = generate_synthetic_clients(1000)
        vm = self._make_vm(clients)
        vm.set_order_label("Nome (A→Z)")
        rows = vm.get_rows()
        self.assertEqual(len(rows), 1000)
        # Verificar que nomes não-vazios estão em ordem case-insensitive
        nomes = [r.nome for r in rows if r.nome.strip()]
        for i in range(len(nomes) - 1):
            self.assertLessEqual(
                nomes[i].casefold(), nomes[i + 1].casefold(), f"Ordem incorreta: {nomes[i]!r} > {nomes[i+1]!r}"
            )

    def test_sort_nome_za(self) -> None:
        """Ordenação por Nome Z→A funciona com 1000 clientes."""
        clients = generate_synthetic_clients(1000)
        vm = self._make_vm(clients)
        vm.set_order_label("Nome (Z→A)")
        rows = vm.get_rows()
        self.assertEqual(len(rows), 1000)
        nomes = [r.nome for r in rows if r.nome.strip()]
        for i in range(len(nomes) - 1):
            self.assertGreaterEqual(
                nomes[i].casefold(), nomes[i + 1].casefold(), f"Ordem incorreta: {nomes[i]!r} < {nomes[i+1]!r}"
            )

    def test_sort_telefone_ddd_asc(self) -> None:
        """Ordenação por WhatsApp DDD asc não gera exception."""
        clients = generate_synthetic_clients(500)
        vm = self._make_vm(clients)
        vm.set_order_label("WhatsApp DDD (↑)")
        rows = vm.get_rows()
        self.assertEqual(len(rows), 500)

    def test_sort_telefone_ddd_desc(self) -> None:
        """Ordenação por WhatsApp DDD desc não gera exception."""
        clients = generate_synthetic_clients(500)
        vm = self._make_vm(clients)
        vm.set_order_label("WhatsApp DDD (↓)")
        rows = vm.get_rows()
        self.assertEqual(len(rows), 500)

    def test_sort_razao_social_az(self) -> None:
        """Ordenação por Razão Social A→Z."""
        clients = generate_synthetic_clients(500)
        vm = self._make_vm(clients)
        vm.set_order_label("Razão Social (A→Z)")
        rows = vm.get_rows()
        self.assertEqual(len(rows), 500)
        razoes = [r.razao_social for r in rows if r.razao_social.strip()]
        for i in range(len(razoes) - 1):
            self.assertLessEqual(
                razoes[i].casefold(), razoes[i + 1].casefold(), f"Ordem incorreta: {razoes[i]!r} > {razoes[i+1]!r}"
            )

    def test_sort_razao_social_za(self) -> None:
        """Ordenação por Razão Social Z→A."""
        clients = generate_synthetic_clients(500)
        vm = self._make_vm(clients)
        vm.set_order_label("Razão Social (Z→A)")
        rows = vm.get_rows()
        self.assertEqual(len(rows), 500)

    def test_search_filter(self) -> None:
        """Filtro de busca retorna subconjunto correto."""
        clients = generate_synthetic_clients(200)
        vm = self._make_vm(clients)
        # Buscar por "Silva"
        vm.set_search_text("Silva")
        rows = vm.get_rows()
        for r in rows:
            self.assertIn("silva", r.search_norm.lower())

    def test_status_filter(self) -> None:
        """Filtro de status funciona."""
        clients = generate_synthetic_clients(200)
        vm = self._make_vm(clients)
        vm.set_status_filter("Ativo")
        rows = vm.get_rows()
        for r in rows:
            self.assertEqual(r.status.strip().lower(), "ativo")

    def test_empty_fields_no_crash(self) -> None:
        """Clientes com campos totalmente vazios não quebram o ViewModel."""
        clients = [
            {"razao_social": "", "cnpj": "", "nome": "", "numero": "", "obs": ""},
            {"razao_social": "Teste", "cnpj": "", "nome": "", "numero": "", "obs": ""},
            {"razao_social": "", "cnpj": "12345678901234", "nome": "", "numero": "", "obs": ""},
        ]
        vm = self._make_vm(clients)
        rows = vm.get_rows()
        self.assertEqual(len(rows), 3)


# ---------------------------------------------------------------------------
# Test: Editor data extraction (field mapping)
# ---------------------------------------------------------------------------
class TestEditorFieldMapping(unittest.TestCase):
    """Verifica que fetch_cliente_by_id retorna todas as chaves esperadas pelo editor."""

    def test_fallback_dict_has_all_editor_keys(self) -> None:
        """O dict de fallback do fetch_cliente_by_id contém todas as chaves que o editor espera."""
        from src.core.models import Cliente

        # Simular um Cliente retornado pelo core
        fake_cliente = Cliente(
            id=42,
            numero="+55 11 98765-4321",
            nome="João Silva",
            razao_social="João Silva LTDA",
            cnpj="12.345.678/0001-90",
            cnpj_norm="12345678000190",
            ultima_alteracao="2025-01-01T00:00:00Z",
            obs="[Ativo] Cliente fidelizado",
            ultima_por="admin@test.com",
            created_at="2024-06-01T00:00:00Z",
        )

        # Mock do core para retornar nosso fake
        with patch("src.modules.clientes.core.service.core_get_cliente_by_id", return_value=fake_cliente):
            from src.modules.clientes.core.service import fetch_cliente_by_id

            result = fetch_cliente_by_id(42)

        self.assertIsNotNone(result)
        assert result is not None  # narrow type for Pylance
        # Chaves que _load_client_data espera
        expected_keys = [
            "id",
            "razao_social",
            "cnpj",
            "numero",
            "nome",
            "observacoes",
            "endereco",
            "bairro",
            "cidade",
            "cep",
        ]
        for key in expected_keys:
            self.assertIn(key, result, f"Chave '{key}' ausente no dict do fetch_cliente_by_id")

        # Verificar valores
        self.assertEqual(result["id"], 42)
        self.assertEqual(result["razao_social"], "João Silva LTDA")
        self.assertEqual(result["nome"], "João Silva")
        self.assertEqual(result["numero"], "+55 11 98765-4321")
        # obs -> observacoes no fallback
        self.assertIn("Ativo", result.get("observacoes", "") or result.get("obs", ""))


# ---------------------------------------------------------------------------
# Test: update_cliente_status_and_observacoes uses correct column name
# ---------------------------------------------------------------------------
class TestUpdateStatusColumn(unittest.TestCase):
    """Verifica que update_cliente_status_and_observacoes delega para update_status_only do core."""

    @patch("src.modules.clientes.core.service._update_status_only")
    def test_delegates_to_update_status_only(self, mock_upd: MagicMock) -> None:
        """Deve chamar _update_status_only(cliente_id, new_obs) em vez de exec_postgrest direto."""
        from src.modules.clientes.core.service import update_cliente_status_and_observacoes

        fake_dict = {
            "id": 1,
            "observacoes": "[Ativo] Texto existente",
            "obs": "[Ativo] Texto existente",
        }

        with patch("src.modules.clientes.core.service.fetch_cliente_by_id", return_value=fake_dict):
            update_cliente_status_and_observacoes(1, "Inativo")

        mock_upd.assert_called_once()
        call_args = mock_upd.call_args
        self.assertEqual(call_args[0][0], 1)  # cliente_id
        self.assertIn("[Inativo]", call_args[0][1])  # new_obs contém o novo status
        self.assertIn("Texto existente", call_args[0][1])  # preserva o corpo

    @patch("src.modules.clientes.core.service._update_status_only")
    def test_mapping_input_compat(self, mock_upd: MagicMock) -> None:
        """Funciona quando 'cliente' é um Mapping (não apenas int)."""
        from src.modules.clientes.core.service import update_cliente_status_and_observacoes

        cliente_map = {"id": 7, "obs": "[Ativo] Antigo", "observacoes": "[Ativo] Antigo"}
        update_cliente_status_and_observacoes(cliente_map, "Novo Cliente")

        mock_upd.assert_called_once()
        self.assertEqual(mock_upd.call_args[0][0], 7)
        self.assertIn("[Novo Cliente]", mock_upd.call_args[0][1])

    @patch("src.modules.clientes.core.service._update_status_only")
    def test_no_direct_exec_postgrest(self, mock_upd: MagicMock) -> None:
        """Não deve chamar exec_postgrest/supabase.table diretamente."""
        from src.modules.clientes.core.service import update_cliente_status_and_observacoes

        fake_dict = {"id": 2, "obs": "Texto"}

        with (
            patch("src.modules.clientes.core.service.fetch_cliente_by_id", return_value=fake_dict),
            patch("src.modules.clientes.core.service.exec_postgrest") as mock_exec,
            patch("src.modules.clientes.core.service.supabase") as mock_supa,
        ):
            update_cliente_status_and_observacoes(2, "Ativo")

        # exec_postgrest e supabase.table NÃO devem ter sido chamados nesta função
        mock_exec.assert_not_called()
        mock_supa.table.assert_not_called()
        # Mas update_status_only SIM
        mock_upd.assert_called_once()


# ---------------------------------------------------------------------------
# Test: batch insert deduplication
# ---------------------------------------------------------------------------
class TestBatchInsertDedup(unittest.TestCase):
    """Testa que salvar_clientes_em_lote deduplica CNPJs internos."""

    @patch("src.modules.clientes.core.service._fetch_existing_cnpjs", return_value=set())
    def test_internal_cnpj_dedup(self, _mock_fetch: MagicMock) -> None:
        """CNPJs repetidos na mesma lista são pulados."""
        from src.modules.clientes.core.service import salvar_clientes_em_lote

        clients = [
            {"razao_social": "Empresa A", "cnpj": "12345678000190"},
            {"razao_social": "Empresa B", "cnpj": "12345678000190"},  # duplicado
            {"razao_social": "Empresa C", "cnpj": "98765432000100"},
        ]

        with patch("src.core.db_manager.db_manager.insert_clientes_batch", return_value=[1, 2]) as mock_batch:
            with patch("src.core.db_manager.insert_clientes_batch", mock_batch):
                ids, skipped = salvar_clientes_em_lote(clients)

        self.assertEqual(len(skipped), 1)
        self.assertIn("duplicado", skipped[0].get("_motivo", "").lower())
        if mock_batch.called:
            batch_arg = mock_batch.call_args[0][0]
            self.assertEqual(len(batch_arg), 2)

    @patch("src.modules.clientes.core.service._fetch_existing_cnpjs")
    def test_existing_cnpj_filtered(self, mock_fetch: MagicMock) -> None:
        """CNPJs já cadastrados no banco são filtrados e adicionados a skipped."""
        mock_fetch.return_value = {"12345678000190"}

        from src.modules.clientes.core.service import salvar_clientes_em_lote

        clients = [
            {"razao_social": "Existente", "cnpj": "12345678000190"},
            {"razao_social": "Novo", "cnpj": "98765432000100"},
        ]

        with patch("src.core.db_manager.db_manager.insert_clientes_batch", return_value=[1]) as mock_batch:
            with patch("src.core.db_manager.insert_clientes_batch", mock_batch):
                ids, skipped = salvar_clientes_em_lote(clients)

        self.assertEqual(len(skipped), 1)
        self.assertIn("já cadastrado", skipped[0].get("_motivo", "").lower())
        if mock_batch.called:
            batch_arg = mock_batch.call_args[0][0]
            self.assertEqual(len(batch_arg), 1)

    @patch("src.modules.clientes.core.service._fetch_existing_cnpjs", return_value=set())
    def test_progress_cb_called_per_batch(self, _mock_fetch: MagicMock) -> None:
        """progress_cb deve ser chamado a cada batch inserido."""
        from src.modules.clientes.core.service import salvar_clientes_em_lote

        clients = [{"razao_social": f"Emp {i}", "cnpj": f"{i:014d}"} for i in range(5)]
        cb = MagicMock()

        with patch("src.core.db_manager.db_manager.insert_clientes_batch", side_effect=[[1, 2], [3, 4], [5]]) as mb:
            with patch("src.core.db_manager.insert_clientes_batch", mb):
                salvar_clientes_em_lote(clients, batch_size=2, progress_cb=cb)

        self.assertEqual(cb.call_count, 3)  # 3 batches de tamanho 2, 2, 1


# ---------------------------------------------------------------------------
# Test: _initial_load now runs in background thread (not blocking UI)
# ---------------------------------------------------------------------------
class TestInitialLoadAsync(unittest.TestCase):
    """Verifica que _initial_load não bloqueia a thread principal."""

    def test_initial_load_uses_thread(self) -> None:
        """_initial_load deve disparar uma thread em vez de fazer I/O síncrono."""
        import ast

        view_path = PROJECT_ROOT / "src" / "modules" / "clientes" / "ui" / "view.py"
        source = view_path.read_text(encoding="utf-8")

        # Verificar que _initial_load contém threading.Thread
        tree = ast.parse(source)
        found_thread_in_initial_load = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_initial_load":
                body_text = ast.get_source_segment(source, node) or ""
                if "Thread" in body_text:
                    found_thread_in_initial_load = True
                break

        self.assertTrue(found_thread_in_initial_load, "_initial_load deve usar Thread para não bloquear a UI")


# ---------------------------------------------------------------------------
# Test: insert_clientes_batch exists and handles batching
# ---------------------------------------------------------------------------
class TestInsertClientesBatchExists(unittest.TestCase):
    """Verifica que insert_clientes_batch foi adicionado corretamente."""

    def test_function_exists(self) -> None:
        """insert_clientes_batch deve ser importável do db_manager."""
        from src.core.db_manager import insert_clientes_batch

        self.assertTrue(callable(insert_clientes_batch))

    def test_empty_list_returns_empty(self) -> None:
        """Lista vazia retorna lista vazia sem chamar o Supabase."""
        from src.core.db_manager.db_manager import insert_clientes_batch

        result = insert_clientes_batch([])
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Test: cap_hit quando fetch_all atinge limite de 1000
# ---------------------------------------------------------------------------
class TestCapHitDetection(unittest.TestCase):
    """Verifica que cap_hit=True quando len(resultados)==1000."""

    def _make_vm(self) -> Any:
        from src.modules.clientes.core.viewmodel import ClientesViewModel
        from src.modules.clientes.core.ui_helpers import ORDER_CHOICES, DEFAULT_ORDER_LABEL

        return ClientesViewModel(
            order_choices=ORDER_CHOICES,
            default_order_label=DEFAULT_ORDER_LABEL,
        )

    @patch("src.modules.clientes.core.viewmodel.search_clientes")
    def test_cap_hit_true_when_1000(self, mock_search: MagicMock) -> None:
        """cap_hit deve ser True quando fetch_all retorna exatamente 1000."""
        mock_search.return_value = [MagicMock() for _ in range(1000)]
        vm = self._make_vm()
        vm.refresh_from_service(term="teste", fetch_all=True)

        self.assertTrue(vm.cap_hit)
        self.assertTrue(vm.has_more)

    @patch("src.modules.clientes.core.viewmodel.search_clientes")
    def test_cap_hit_false_when_under_1000(self, mock_search: MagicMock) -> None:
        """cap_hit deve ser False quando fetch_all retorna menos de 1000."""
        mock_search.return_value = [MagicMock() for _ in range(500)]
        vm = self._make_vm()
        vm.refresh_from_service(term="teste", fetch_all=True)

        self.assertFalse(vm.cap_hit)
        self.assertFalse(vm.has_more)

    @patch("src.modules.clientes.core.viewmodel.search_clientes")
    def test_cap_hit_false_on_normal_pagination(self, mock_search: MagicMock) -> None:
        """cap_hit deve ser False em paginação normal (fetch_all=False)."""
        mock_search.return_value = [MagicMock() for _ in range(200)]
        vm = self._make_vm()
        vm.refresh_from_service(term="teste", fetch_all=False)

        self.assertFalse(vm.cap_hit)

    @patch("src.modules.clientes.core.viewmodel.search_clientes")
    def test_load_more_works_after_cap_hit(self, mock_search: MagicMock) -> None:
        """load_next_page deve funcionar quando cap_hit=True."""
        mock_search.return_value = [MagicMock() for _ in range(1000)]
        vm = self._make_vm()
        vm.refresh_from_service(term="teste", fetch_all=True)

        self.assertTrue(vm.cap_hit)
        # Simular próxima página com menos de PAGE_SIZE → sem mais resultados
        mock_search.return_value = [MagicMock() for _ in range(50)]
        result = vm.load_next_page()
        self.assertTrue(result)
        self.assertFalse(vm.cap_hit)
        self.assertFalse(vm.has_more)


# ---------------------------------------------------------------------------
# Test: _sync_load_more_btn mostra botão em cap_hit
# ---------------------------------------------------------------------------
class TestSyncLoadMoreBtnCapHit(unittest.TestCase):
    """Verifica que _sync_load_more_btn deixa o botão visível em cap_hit."""

    def test_load_more_visible_when_cap_hit(self) -> None:
        """O botão 'Carregar mais' deve ficar visível quando cap_hit=True."""
        vm = MagicMock()
        vm.has_more = True
        vm.cap_hit = True
        vm._fetch_all = True

        view = MagicMock()
        view._vm = vm
        view._trash_mode = False
        view._load_more_visible = False
        view._cap_hit_label_visible = False

        # Chamar o método real extraido
        from src.modules.clientes.ui.view import ClientesV2Frame

        _sync_load_more_btn = ClientesV2Frame._sync_load_more_btn
        _sync_load_more_btn(view)

        view._load_more_btn.pack.assert_called_once()
        view._cap_hit_label.pack.assert_called_once()

    def test_load_more_hidden_when_no_cap_hit(self) -> None:
        """O botão 'Carregar mais' deve ficar oculto em fetch_all sem cap_hit."""
        vm = MagicMock()
        vm.has_more = False
        vm.cap_hit = False
        vm._fetch_all = True

        view = MagicMock()
        view._vm = vm
        view._trash_mode = False
        view._load_more_visible = True
        view._cap_hit_label_visible = True

        from src.modules.clientes.ui.view import ClientesV2Frame

        _sync_load_more_btn = ClientesV2Frame._sync_load_more_btn
        _sync_load_more_btn(view)

        view._load_more_btn.pack_forget.assert_called_once()
        view._cap_hit_label.pack_forget.assert_called_once()


if __name__ == "__main__":
    unittest.main()
