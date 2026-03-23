# -*- coding: utf-8 -*-
"""FASE 7B.1 — Testes de proteção do módulo de clientes (view.py).

Estratégia de cobertura sem display real:

    1. TestViewStructureAST     — análise de fonte via AST (sem importar Tk/CTk).
    2. TestColumnResizeAlgorithm— testa _compute_column_widths via extract_functions_from_source.
    3. TestPickModeBehavior     — testa _on_pick_confirm via extract_functions_from_source.
    4. TestDeleteBehavior       — testa _on_delete_client via extract_functions_from_source.
    5. TestEditorOpenGuards     — testa os guards de _open_client_editor via AST + extract.

Nenhum destes testes instancia ClientesV2Frame nem cria janela Tk.
"""

from __future__ import annotations

import ast
import logging
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from conftest import extract_functions_from_source

# ---------------------------------------------------------------------------
# Localização do arquivo-fonte
# ---------------------------------------------------------------------------

_VIEW_FILE = Path(__file__).resolve().parent.parent / "src" / "modules" / "clientes" / "ui" / "view.py"
_VIEW_SOURCE = _VIEW_FILE.read_text(encoding="utf-8")
_VIEW_AST = ast.parse(_VIEW_SOURCE)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers AST
# ---------------------------------------------------------------------------


def _class_node() -> ast.ClassDef:
    """Retorna o nó AST de ClientesV2Frame."""
    for node in ast.iter_child_nodes(_VIEW_AST):
        if isinstance(node, ast.ClassDef) and node.name == "ClientesV2Frame":
            return node
    raise RuntimeError("ClientesV2Frame não encontrado no AST de view.py")


def _method_node(method_name: str) -> ast.FunctionDef:
    """Retorna o nó AST de um método de ClientesV2Frame."""
    cls = _class_node()
    for node in ast.iter_child_nodes(cls):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    raise RuntimeError(f"{method_name} não encontrado em ClientesV2Frame")


def _source_of(node: ast.AST) -> str:
    """Retorna o trecho de código-fonte de um nó AST usando as linhas do arquivo."""
    lines = _VIEW_SOURCE.splitlines(keepends=True)
    start = node.lineno - 1  # type: ignore[attr-defined]
    end = node.end_lineno  # type: ignore[attr-defined]
    return "".join(lines[start:end])


def _all_calls_in(node: ast.AST) -> list[str]:
    """Retorna nomes de todas as funções/atributos chamados na sub-árvore AST."""
    calls = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                calls.append(n.func.id)
            elif isinstance(n.func, ast.Attribute):
                calls.append(n.func.attr)
    return calls


def _all_assigns_in(node: ast.AST) -> list[str]:
    """Retorna atributos `self.X = ...` e `self.X: T = ...` dentro do nó."""
    names = []
    for n in ast.walk(node):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                    names.append(t.attr)
        elif isinstance(n, ast.AnnAssign):
            # self.x: Type = value  →  n.target é Attribute
            t = n.target
            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                names.append(t.attr)
    return names


# ---------------------------------------------------------------------------
# 1. Testes estruturais via AST
# ---------------------------------------------------------------------------


class TestViewStructureAST:
    """Verifica que ClientesV2Frame mantém a estrutura esperada.

    Zero dependência de Tk — todos os testes usam apenas o AST.
    """

    def test_class_exists(self) -> None:
        """ClientesV2Frame está definida em view.py."""
        _class_node()  # lança RuntimeError se não encontrar

    def test_init_sets_opening_editor_false(self) -> None:
        """__init__ inicializa _opening_editor = False (guard de reentrância)."""
        init = _method_node("__init__")
        assigns = _all_assigns_in(init)
        assert (
            "_opening_editor" in assigns
        ), "_opening_editor deve ser inicializado em __init__ para proteger contra abertura dupla de editor"

    def test_init_stores_pick_mode(self) -> None:
        """__init__ armazena o parâmetro pick_mode em self._pick_mode."""
        init = _method_node("__init__")
        assigns = _all_assigns_in(init)
        assert "_pick_mode" in assigns, "_pick_mode deve ser armazenado em __init__ para que o fluxo ANVISA funcione"

    def test_init_stores_load_gen(self) -> None:
        """__init__ inicializa _load_gen para proteger contra race conditions no load."""
        init = _method_node("__init__")
        assigns = _all_assigns_in(init)
        assert (
            "_load_gen" in assigns
        ), "_load_gen deve ser inicializado em __init__ — protege contra resultados obsoletos de threads"

    def test_delete_has_trash_mode_conditional(self) -> None:
        """_on_delete_client possui branch `if self._trash_mode:` (hard delete vs soft delete)."""
        delete_fn = _method_node("_on_delete_client")
        src = _source_of(delete_fn)
        assert "self._trash_mode" in src, (
            "_on_delete_client deve verificar self._trash_mode para escolher entre "
            "exclusão definitiva e envio para lixeira"
        )

    def test_delete_calls_hard_delete_in_trash_mode(self) -> None:
        """_on_delete_client delega para _execute_hard_delete (actions.py) no modo LIXEIRA."""
        delete_fn = _method_node("_on_delete_client")
        src = _source_of(delete_fn)
        assert "_execute_hard_delete" in src, "_on_delete_client deve delegar para _execute_hard_delete no modo LIXEIRA"

    def test_delete_calls_soft_delete_in_normal_mode(self) -> None:
        """_on_delete_client delega para _execute_soft_delete (actions.py) no modo ATIVOS."""
        delete_fn = _method_node("_on_delete_client")
        src = _source_of(delete_fn)
        assert "_execute_soft_delete" in src, "_on_delete_client deve delegar para _execute_soft_delete no modo ATIVOS"

    def test_delete_guard_editor_dialog(self) -> None:
        """_on_delete_client verifica se há editor aberto antes de excluir."""
        delete_fn = _method_node("_on_delete_client")
        src = _source_of(delete_fn)
        assert "self._editor_dialog" in src, (
            "_on_delete_client deve conferir _editor_dialog antes de excluir "
            "(evita Delete vazando do browser de arquivos)"
        )

    def test_open_editor_has_opening_guard(self) -> None:
        """_open_client_editor verifica self._opening_editor (impede abertura dupla)."""
        fn = _method_node("_open_client_editor")
        src = _source_of(fn)
        assert (
            "self._opening_editor" in src
        ), "_open_client_editor deve checar _opening_editor para prevenir editor duplicado"

    def test_open_editor_has_dialog_guard(self) -> None:
        """_open_client_editor verifica self._editor_dialog (reutiliza dialog existente)."""
        fn = _method_node("_open_client_editor")
        src = _source_of(fn)
        assert (
            "self._editor_dialog is not None" in src or "self._editor_dialog" in src
        ), "_open_client_editor deve checar _editor_dialog para não criar janela dupla"

    def test_pick_mode_creates_pick_bar(self) -> None:
        """_build_footer_bar chama _create_pick_bar quando pick_mode=True."""
        fn = _method_node("_build_footer_bar")
        src = _source_of(fn)
        assert (
            "_create_pick_bar" in src
        ), "_build_footer_bar deve chamar _create_pick_bar para criar a barra de botões do modo ANVISA"

    def test_pick_confirm_checks_pick_mode(self) -> None:
        """_on_pick_confirm verifica self._pick_mode antes de agir."""
        fn = _method_node("_on_pick_confirm")
        src = _source_of(fn)
        assert "self._pick_mode" in src, "_on_pick_confirm deve checar _pick_mode para não agir fora do contexto ANVISA"

    def test_pick_confirm_calls_callback(self) -> None:
        """_on_pick_confirm chama self._on_cliente_selected com os dados do cliente."""
        fn = _method_node("_on_pick_confirm")
        src = _source_of(fn)
        assert (
            "_on_cliente_selected" in src
        ), "_on_pick_confirm deve chamar _on_cliente_selected para integração com módulo ANVISA"

    def test_compute_column_widths_in_column_layout(self) -> None:
        """compute_column_widths, COLUMN_SPECS_DEFAULTS e COLUMNS existem em column_layout.py."""
        from src.modules.clientes.ui.column_layout import (
            compute_column_widths,
            COLUMN_SPECS_DEFAULTS,
            COLUMNS,
        )

        assert callable(compute_column_widths)
        assert isinstance(COLUMN_SPECS_DEFAULTS, dict)
        assert len(COLUMNS) == 8, f"Esperado 8 colunas, obtido {len(COLUMNS)}"

    def test_actions_module_exists(self) -> None:
        """actions.py exporte os helpers principais: executores de ação e resolvedores."""
        from src.modules.clientes.ui.actions import (
            resolve_client_label,
            client_row_to_dict,
            execute_soft_delete,
            execute_hard_delete,
            execute_restore,
            execute_export,
        )

        assert callable(resolve_client_label)
        assert callable(client_row_to_dict)
        assert callable(execute_soft_delete)
        assert callable(execute_hard_delete)
        assert callable(execute_restore)
        assert callable(execute_export)

    def test_resize_columns_calls_compute(self) -> None:
        """_resize_columns delega o cálculo a _compute_column_widths (alias de column_layout)."""
        fn = _method_node("_resize_columns")
        src = _source_of(fn)
        assert (
            "_compute_column_widths" in src
        ), "_resize_columns deve usar _compute_column_widths (importado de column_layout)"

    def test_on_new_client_delegates_to_open_client_editor(self) -> None:
        """_on_new_client delega para _open_client_editor(new_client=True) sem duplicar guards."""
        fn = _method_node("_on_new_client")
        src = _source_of(fn)
        assert "_open_client_editor" in src, "_on_new_client deve delegar para _open_client_editor"
        assert (
            "new_client=True" in src
        ), "_on_new_client deve passar new_client=True para pular a verificação de seleção"

    def test_open_editor_supports_new_client_mode(self) -> None:
        """_open_client_editor aceita parâmetro new_client para criar novo cliente."""
        fn = _method_node("_open_client_editor")
        src = _source_of(fn)
        assert "new_client" in src, "_open_client_editor deve suportar o parâmetro new_client"

    def test_on_tree_click_delegates_to_resolve_whatsapp_click(self) -> None:
        """_on_tree_click delega decisão de clique para resolve_whatsapp_click."""
        fn = _method_node("_on_tree_click")
        src = _source_of(fn)
        assert "resolve_whatsapp_click" in src, "_on_tree_click deve usar resolve_whatsapp_click de actions.py"

    def test_on_enviar_documentos_uses_trigger_dialog_upload(self) -> None:
        """_on_enviar_documentos delega o auto-disparo para trigger_dialog_upload."""
        fn = _method_node("_on_enviar_documentos")
        src = _source_of(fn)
        assert "trigger_dialog_upload" in src, "_on_enviar_documentos deve usar trigger_dialog_upload de actions.py"

    def test_on_delete_client_uses_editor_dialog_is_live(self) -> None:
        """_on_delete_client usa editor_dialog_is_live para o guard do diálogo."""
        fn = _method_node("_on_delete_client")
        src = _source_of(fn)
        assert "editor_dialog_is_live" in src, "_on_delete_client deve usar editor_dialog_is_live de actions.py"

    def test_open_client_editor_uses_editor_dialog_is_live(self) -> None:
        """_open_client_editor usa editor_dialog_is_live para o guard do diálogo."""
        fn = _method_node("_open_client_editor")
        src = _source_of(fn)
        assert "editor_dialog_is_live" in src, "_open_client_editor deve usar editor_dialog_is_live de actions.py"

    def test_on_restore_client_uses_execute_restore(self) -> None:
        """_on_restore_client delega o fluxo de restauração para execute_restore."""
        fn = _method_node("_on_restore_client")
        src = _source_of(fn)
        assert "execute_restore" in src, "_on_restore_client deve usar execute_restore de actions.py"

    def test_on_export_uses_execute_export(self) -> None:
        """_on_export delega fluxo de exportação para execute_export de actions.py."""
        fn = _method_node("_on_export")
        src = _source_of(fn)
        assert "execute_export" in src, "_on_export deve usar execute_export de actions.py"

    def test_on_toggle_trash_calls_load_async(self) -> None:
        """_on_toggle_trash deve acionar load_async para recarregar com o modo correto."""
        fn = _method_node("_on_toggle_trash")
        src = _source_of(fn)
        assert "load_async" in src, "_on_toggle_trash deve chamar load_async para atualizar a listagem"

    def test_on_tree_double_click_uses_identify_clicked_row(self) -> None:
        """_on_tree_double_click usa identify_clicked_row de actions.py."""
        fn = _method_node("_on_tree_double_click")
        src = _source_of(fn)
        assert "identify_clicked_row" in src, "_on_tree_double_click deve usar identify_clicked_row de actions.py"

    def test_on_tree_select_uses_resolve_selection_id(self) -> None:
        """_on_tree_select usa resolve_selection_id de actions.py."""
        fn = _method_node("_on_tree_select")
        src = _source_of(fn)
        assert "resolve_selection_id" in src, "_on_tree_select deve usar resolve_selection_id de actions.py"

    def test_on_order_changed_uses_normalize_order_label(self) -> None:
        """_on_order_changed normaliza o label via normalize_order_label antes de load_async."""
        fn = _method_node("_on_order_changed")
        src = _source_of(fn)
        assert "normalize_order_label" in src, (
            "_on_order_changed deve normalizar o order_label via normalize_order_label "
            "(import top-level de ui_helpers) antes de repassar para load_async"
        )

    def test_on_column_lock_uses_handle_column_lock_region(self) -> None:
        """_on_column_lock delega a decisão para handle_column_lock_region de actions.py."""
        fn = _method_node("_on_column_lock")
        src = _source_of(fn)
        assert "handle_column_lock_region" in src, (
            "_on_column_lock deve usar handle_column_lock_region de actions.py "
            "para isolar a lógica de bloqueio de região"
        )

    def test_on_theme_changed_has_duplicate_guard(self) -> None:
        """_on_theme_changed possui guard de modo duplicado via _last_applied_mode."""
        fn = _method_node("_on_theme_changed")
        src = _source_of(fn)
        assert "_last_applied_mode" in src, (
            "_on_theme_changed deve verificar _last_applied_mode para evitar "
            "double-apply do tema (otimização intencional documentada)"
        )

    def test_get_selected_values_has_row_data_map_fallback(self) -> None:
        """_get_selected_values preserva fallback via _row_data_map (contrato legado)."""
        fn = _method_node("_get_selected_values")
        src = _source_of(fn)
        assert "_row_data_map" in src, (
            "_get_selected_values deve preservar o fallback via _row_data_map "
            "para quando a Treeview perde o estado de seleção"
        )


# ---------------------------------------------------------------------------
# 2. Testes do algoritmo puro de layout de colunas
# ---------------------------------------------------------------------------

# Importar diretamente do módulo de produção (sem necessidade de extração AST)
from src.modules.clientes.ui.column_layout import (  # noqa: E402
    compute_column_widths as _compute_column_widths,
    COLUMN_SPECS_DEFAULTS as _REAL_SPECS,
)

# _TOTAL_MIN calculado a partir das specs de produção (detecta drift automático)
_TOTAL_MIN = sum(v[1] for v in _REAL_SPECS.values())


class TestColumnResizeAlgorithm:
    """Testa _compute_column_widths sem display ou widget real.

    Estas specs são extraídas do código-fonte e representam o contrato
    visual da tabela de clientes. Se o algoritmo mudar, estes testes falham —
    protegendo o layout durante refatoração.
    """

    def test_returns_min_widths_when_clamped(self) -> None:
        """Quando tree_width <= total_min, retorna os mínimos e is_clamped=True."""
        widths, clamped = _compute_column_widths(_TOTAL_MIN - 1, _REAL_SPECS)
        assert clamped is True
        for col, specs in _REAL_SPECS.items():
            assert widths[col] == specs[1], f"col {col}: esperado min_width={specs[1]}, obtido={widths[col]}"

    def test_exact_min_is_clamped(self) -> None:
        """tree_width == total_min também clampa (≤ inclui igual)."""
        widths, clamped = _compute_column_widths(_TOTAL_MIN, _REAL_SPECS)
        assert clamped is True

    def test_flex_cols_grow_with_extra_space(self) -> None:
        """Com espaço extra, colunas flex (stretch=True) crescem acima do mínimo."""
        tree_width = _TOTAL_MIN + 400
        widths, clamped = _compute_column_widths(tree_width, _REAL_SPECS)
        assert clamped is False
        assert (
            widths["razao_social"] > _REAL_SPECS["razao_social"][1]
        ), "razao_social deve crescer além do mínimo quando há espaço disponível"
        assert widths["nome"] > _REAL_SPECS["nome"][1], "nome deve crescer além do mínimo quando há espaço disponível"

    def test_flex_weights_respected(self) -> None:
        """razao_social (80%) cresce mais que nome (20%) com espaço extra."""
        tree_width = _TOTAL_MIN + 400
        widths, _ = _compute_column_widths(tree_width, _REAL_SPECS)
        extra_razao = widths["razao_social"] - _REAL_SPECS["razao_social"][1]
        extra_nome = widths["nome"] - _REAL_SPECS["nome"][1]
        assert (
            extra_razao > extra_nome
        ), "razao_social (weight=0.80) deve receber mais espaço extra do que nome (weight=0.20)"

    def test_fixed_cols_fill_up_to_base_width(self) -> None:
        """Colunas fixas crescem até base_width (mas não além) quando há espaço."""
        tree_width = _TOTAL_MIN + 400
        widths, _ = _compute_column_widths(tree_width, _REAL_SPECS)
        for col, (base_w, min_w, stretch, _) in _REAL_SPECS.items():
            if not stretch:
                assert (
                    widths[col] <= base_w
                ), f"Coluna fixa '{col}' não deve ultrapassar base_width={base_w}, obtido={widths[col]}"

    def test_no_column_below_min_width(self) -> None:
        """Nenhuma coluna fica abaixo do min_width em nenhuma condição."""
        for tree_width in [500, _TOTAL_MIN, _TOTAL_MIN + 1, 1920, 2560]:
            widths, _ = _compute_column_widths(tree_width, _REAL_SPECS)
            for col, (_, min_w, _, _) in _REAL_SPECS.items():
                assert (
                    widths[col] >= min_w
                ), f"tree_width={tree_width}: col '{col}' abaixo do mínimo: {widths[col]} < {min_w}"

    def test_sum_does_not_exceed_tree_width_when_ample(self) -> None:
        """A soma das larguras não ultrapassa tree_width quando há espaço amplo."""
        tree_width = _TOTAL_MIN + 500
        widths, _ = _compute_column_widths(tree_width, _REAL_SPECS)
        total = sum(widths.values())
        assert (
            total <= tree_width
        ), f"sum(widths)={total} ultrapassa tree_width={tree_width} — causaria scroll horizontal indesejado"

    def test_single_flex_col_absorbs_all_extra(self) -> None:
        """Com uma única coluna flex, ela absorve todo o espaço restante."""
        specs = {
            "id": (70, 60, False, 0),
            "nome": (300, 200, True, 1.0),
            "status": (150, 100, False, 0),
        }
        total_min = 60 + 200 + 100
        tree_width = total_min + 200
        widths, clamped = _compute_column_widths(tree_width, specs)
        assert clamped is False
        assert sum(widths.values()) == tree_width, f"Com 1 coluna flex, sum deve igualar tree_width={tree_width}"


# ---------------------------------------------------------------------------
# 3. Comportamento de pick mode
# ---------------------------------------------------------------------------

# Stubs de módulos com dependências de UI para o namespace do exec
_mock_log_pick = logging.getLogger("test.pick")
_mock_show_warning = MagicMock()  # _show_warning

_pick_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_pick_confirm",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": _mock_log_pick,
        "_show_warning": _mock_show_warning,
        "Any": Any,
    },
)
_on_pick_confirm = _pick_fns["_on_pick_confirm"]


def _make_client_row(client_id: str = "42", razao: str = "Empresa Teste Ltda") -> object:
    """Cria um ClienteRow fake com os campos mínimos necessários."""
    row = MagicMock()
    row.id = client_id
    row.razao_social = razao
    row.cnpj = "12.345.678/0001-90"
    row.nome = "Contato Teste"
    row.whatsapp = "(11) 99999-0000"
    row.status = "Ativo"
    return row


class TestPickModeBehavior:
    """Verifica comportamento de _on_pick_confirm sem display real.

    Proteção para a integração com o módulo ANVISA:
    se o callback parar de ser chamado, o fluxo de seleção de empresa
    no ANVISA quebra silenciosamente.
    """

    def _make_fake(
        self,
        *,
        pick_mode: bool = True,
        iid: str = "item1",
        client_row: Any = None,
        callback: Any = None,
    ) -> MagicMock:
        fake = MagicMock()
        fake._pick_mode = pick_mode
        fake._on_cliente_selected = callback
        client_row = client_row or _make_client_row()
        fake._row_data_map = {iid: client_row}
        fake.tree.selection.return_value = (iid,)
        fake.winfo_toplevel.return_value = MagicMock()
        return fake

    def test_callback_called_with_client_data(self) -> None:
        """Confirmação no pick_mode chama o callback com dict do cliente."""
        cb = MagicMock()
        row = _make_client_row(client_id="99", razao="Farmácia Modelo")
        fake = self._make_fake(callback=cb, client_row=row)

        _on_pick_confirm(fake)

        cb.assert_called_once()
        data = cb.call_args[0][0]
        assert data["id"] == "99"
        assert data["razao_social"] == "Farmácia Modelo"

    def test_no_callback_when_no_selection(self) -> None:
        """Sem item selecionado, o callback NÃO é chamado."""
        cb = MagicMock()
        fake = self._make_fake(callback=cb)
        fake.tree.selection.return_value = ()  # nada selecionado

        _on_pick_confirm(fake)

        cb.assert_not_called()

    def test_disabled_outside_pick_mode(self) -> None:
        """_on_pick_confirm não faz nada se pick_mode=False."""
        cb = MagicMock()
        fake = self._make_fake(pick_mode=False, callback=cb)

        _on_pick_confirm(fake)

        cb.assert_not_called()

    def test_callback_client_data_has_required_keys(self) -> None:
        """O dict passado ao callback contém as chaves esperadas pelo módulo ANVISA."""
        cb = MagicMock()
        fake = self._make_fake(callback=cb)

        _on_pick_confirm(fake)

        cb.assert_called_once()
        data = cb.call_args[0][0]
        required = {"id", "razao_social", "cnpj", "nome", "whatsapp", "status"}
        missing = required - set(data.keys())
        assert not missing, f"Chaves faltando no dict do callback: {missing}"


# ---------------------------------------------------------------------------
# 4. Comportamento do fluxo de delete
# ---------------------------------------------------------------------------

# Namespace global compartilhado para _on_delete_client extraído
_mock_log_del = logging.getLogger("test.delete")
_mock_ask_yes_no = MagicMock(return_value=True)
_mock_ask_yes_no_danger = MagicMock(return_value=True)
_mock_show_info = MagicMock()
_mock_show_error_del = MagicMock()

_del_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_delete_client",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": _mock_log_del,
        "_ask_yes_no": _mock_ask_yes_no,
        "_ask_yes_no_danger": _mock_ask_yes_no_danger,
        "_show_info": _mock_show_info,
        "_show_error": _mock_show_error_del,
        "Any": Any,
    },
)
_on_delete_client = _del_fns["_on_delete_client"]


def _make_delete_fake(
    client_id: int = 42,
    trash_mode: bool = False,
    razao: str = "Empresa X",
    editor_dialog: Any = None,
) -> MagicMock:
    """Cria um stub de ClientesV2Frame para testes de _on_delete_client."""
    fake = MagicMock()
    fake._selected_client_id = client_id
    fake._trash_mode = trash_mode
    fake._editor_dialog = editor_dialog

    # Criar um ClienteRow fake no _row_data_map
    row = MagicMock()
    row.id = client_id
    row.razao_social = razao
    fake._row_data_map = {"iid1": row}

    # winfo_toplevel retorna um MagicMock (substituto de janela Tk)
    fake.winfo_toplevel.return_value = MagicMock()

    return fake


def _make_service_mock(
    hard_delete_result: tuple = (True, []),
) -> MagicMock:
    """Cria um mock do service com retornos configuráveis."""
    svc = MagicMock()
    svc.excluir_clientes_definitivamente = MagicMock(return_value=hard_delete_result)
    svc.mover_cliente_para_lixeira = MagicMock()
    return svc


class TestDeleteBehavior:
    """Verifica o roteamento de _on_delete_client para o serviço correto.

    Se estas proteções quebrarem:
    - modo normal poderia chamar hard-delete acidentalmente
    - modo lixeira poderia apenas mover em vez de excluir
    - editor aberto não bloquearia o Delete key
    """

    def setup_method(self) -> None:
        """Reinicia mocks de diálogo antes de cada teste."""
        _mock_ask_yes_no.reset_mock()
        _mock_ask_yes_no.return_value = True
        _mock_ask_yes_no_danger.reset_mock()
        _mock_ask_yes_no_danger.return_value = True
        _mock_show_info.reset_mock()
        _mock_show_error_del.reset_mock()

    def test_no_client_selected_returns_early(self) -> None:
        """Sem cliente selecionado, nenhum serviço é chamado."""
        fake = _make_delete_fake(client_id=0)
        fake._selected_client_id = None
        svc = _make_service_mock()

        with _patch_service(svc):
            result = _on_delete_client(fake)

        assert result is None
        svc.mover_cliente_para_lixeira.assert_not_called()
        svc.excluir_clientes_definitivamente.assert_not_called()

    def test_normal_mode_calls_soft_delete(self) -> None:
        """No modo ATIVOS, confirmar chama mover_cliente_para_lixeira."""
        fake = _make_delete_fake(client_id=42, trash_mode=False)
        svc = _make_service_mock()
        _mock_ask_yes_no.return_value = True

        with _patch_service(svc):
            _on_delete_client(fake)

        svc.mover_cliente_para_lixeira.assert_called_once_with(42)
        svc.excluir_clientes_definitivamente.assert_not_called()

    def test_trash_mode_calls_hard_delete(self) -> None:
        """No modo LIXEIRA, confirmar chama excluir_clientes_definitivamente."""
        fake = _make_delete_fake(client_id=77, trash_mode=True)
        svc = _make_service_mock(hard_delete_result=(True, []))
        _mock_ask_yes_no_danger.return_value = True

        with _patch_service(svc):
            _on_delete_client(fake)

        svc.excluir_clientes_definitivamente.assert_called_once_with([77])
        svc.mover_cliente_para_lixeira.assert_not_called()

    def test_user_cancel_normal_mode_no_service_call(self) -> None:
        """Se usuário cancelar o diálogo (modo ATIVOS), nenhum serviço é chamado."""
        fake = _make_delete_fake(client_id=55, trash_mode=False)
        svc = _make_service_mock()
        _mock_ask_yes_no.return_value = False  # usuário cancela

        with _patch_service(svc):
            _on_delete_client(fake)

        svc.mover_cliente_para_lixeira.assert_not_called()
        svc.excluir_clientes_definitivamente.assert_not_called()

    def test_user_cancel_trash_mode_no_service_call(self) -> None:
        """Se usuário cancelar (modo LIXEIRA), nenhum serviço é chamado."""
        fake = _make_delete_fake(client_id=55, trash_mode=True)
        svc = _make_service_mock()
        _mock_ask_yes_no_danger.return_value = False  # usuário cancela

        with _patch_service(svc):
            _on_delete_client(fake)

        svc.excluir_clientes_definitivamente.assert_not_called()
        svc.mover_cliente_para_lixeira.assert_not_called()

    def test_editor_dialog_open_blocks_delete(self) -> None:
        """Se _editor_dialog estiver aberto, _on_delete_client não exclui."""
        # Simular diálogo aberto e existente
        dialog = MagicMock()
        dialog.winfo_exists.return_value = True

        fake = _make_delete_fake(client_id=33, trash_mode=False, editor_dialog=dialog)
        svc = _make_service_mock()
        _mock_ask_yes_no.return_value = True

        with _patch_service(svc):
            _on_delete_client(fake)

        svc.mover_cliente_para_lixeira.assert_not_called()
        svc.excluir_clientes_definitivamente.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Guards de abertura do editor
# ---------------------------------------------------------------------------

_mock_log_editor = logging.getLogger("test.editor")
_mock_show_warning_editor = MagicMock()
_mock_show_error_editor = MagicMock()

_editor_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_open_client_editor",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": _mock_log_editor,
        "_show_warning": _mock_show_warning_editor,
        "_show_error": _mock_show_error_editor,
        "Any": Any,
    },
)
_open_client_editor = _editor_fns["_open_client_editor"]


def _make_editor_fake(
    client_id: int | None = 42,
    opening_editor: bool = False,
    editor_dialog: Any = None,
    has_app: bool = True,
) -> MagicMock:
    fake = MagicMock()
    fake._selected_client_id = client_id
    fake._opening_editor = opening_editor
    fake._editor_dialog = editor_dialog
    fake.app = MagicMock() if has_app else None
    fake.winfo_toplevel.return_value = MagicMock()
    return fake


def _make_fake_editor_dialog() -> MagicMock:
    """Mock de ClientEditorDialog para capturar construção."""
    dialog = MagicMock()
    dialog.winfo_exists.return_value = True
    return dialog


class TestEditorOpenGuards:
    """Verifica que os guards de _open_client_editor funcionam corretamente.

    Estes guards são a principal proteção contra editor duplicado — um dos
    bugs mais reportados antes de sua implementação.
    """

    def setup_method(self) -> None:
        _mock_show_warning_editor.reset_mock()
        _mock_show_error_editor.reset_mock()
        _mock_log_editor.handlers.clear()

    def test_opening_editor_flag_blocks_reentry(self) -> None:
        """Se _opening_editor=True, _open_client_editor retorna sem criar novo dialog."""
        fake = _make_editor_fake(opening_editor=True)

        # Stub ClientEditorDialog para detectar se seria criado
        stub_dialog_cls = MagicMock()
        with _patch_editor_dialog(stub_dialog_cls):
            _open_client_editor(fake)

        stub_dialog_cls.assert_not_called()

    def test_existing_dialog_gets_focus_instead_of_new(self) -> None:
        """Se _editor_dialog existe e está visível, recebe foco sem criar novo."""
        existing = MagicMock()
        existing.winfo_exists.return_value = True
        fake = _make_editor_fake(editor_dialog=existing)

        stub_dialog_cls = MagicMock()
        with _patch_editor_dialog(stub_dialog_cls):
            _open_client_editor(fake)

        # Nenhum novo dialog criado
        stub_dialog_cls.assert_not_called()
        # Dialog existente recebeu foco
        existing.lift.assert_called()
        existing.focus_force.assert_called()

    def test_no_client_selected_shows_warning(self) -> None:
        """Sem cliente selecionado, mostra aviso e não cria dialog."""
        fake = _make_editor_fake(client_id=None)

        stub_dialog_cls = MagicMock()
        with _patch_editor_dialog(stub_dialog_cls):
            _open_client_editor(fake)

        stub_dialog_cls.assert_not_called()
        _mock_show_warning_editor.assert_called()

    def test_editor_created_when_valid_selection(self) -> None:
        """Com cliente selecionado e guards limpos, ClientEditorDialog é construído."""
        fake = _make_editor_fake(client_id=123, opening_editor=False, editor_dialog=None)

        stub_dialog_cls = MagicMock(return_value=_make_fake_editor_dialog())
        with _patch_editor_dialog(stub_dialog_cls):
            _open_client_editor(fake)

        stub_dialog_cls.assert_called_once()
        kwargs = stub_dialog_cls.call_args.kwargs
        assert kwargs.get("client_id") == 123, f"ClientEditorDialog deve ser criado com client_id=123, obtido: {kwargs}"

    def test_new_client_mode_skips_selection_check(self) -> None:
        """Com new_client=True, cria dialog mesmo sem _selected_client_id."""
        fake = _make_editor_fake(client_id=None)  # sem seleção

        stub_dialog_cls = MagicMock(return_value=_make_fake_editor_dialog())
        with _patch_editor_dialog(stub_dialog_cls):
            _open_client_editor(fake, new_client=True)

        stub_dialog_cls.assert_called_once()
        kwargs = stub_dialog_cls.call_args.kwargs
        assert kwargs.get("client_id") is None, f"Em new_client=True, client_id deve ser None, obtido: {kwargs}"

    def test_new_client_mode_calls_focus_on_dialog(self) -> None:
        """Com new_client=True, chama focus() no dialog criado."""
        fake = _make_editor_fake(client_id=None)
        dialog_instance = _make_fake_editor_dialog()

        stub_dialog_cls = MagicMock(return_value=dialog_instance)
        with _patch_editor_dialog(stub_dialog_cls):
            _open_client_editor(fake, new_client=True)

        dialog_instance.focus.assert_called()


# ---------------------------------------------------------------------------
# Context managers auxiliares
# ---------------------------------------------------------------------------

from contextlib import contextmanager  # noqa: E402


@contextmanager
def _patch_service(svc_mock: MagicMock):
    """Injeta mock do service e do lixeira no sys.modules durante o contexto.

    O stub de lixeira é necessário porque _on_delete_client faz
    `from src.modules.lixeira import refresh_if_open`, e o __init__.py
    desse pacote importa CTk via .view — incompatível com ambiente headless.
    O stub é removido ao sair do contexto, evitando poluição de sys.modules.
    """
    # ---------- service ----------
    core_mock = sys.modules.get("src.modules.clientes.core")
    _had_service = "src.modules.clientes.core.service" in sys.modules
    _old_service = sys.modules.get("src.modules.clientes.core.service")
    _old_core_service = getattr(core_mock, "service", None) if core_mock else None

    # ---------- lixeira ----------
    _had_lixeira = "src.modules.lixeira" in sys.modules
    _old_lixeira = sys.modules.get("src.modules.lixeira")
    _lixeira_tmp = types.ModuleType("src.modules.lixeira")
    setattr(_lixeira_tmp, "refresh_if_open", MagicMock())

    sys.modules["src.modules.clientes.core.service"] = svc_mock  # type: ignore[assignment]
    if core_mock is not None:
        setattr(core_mock, "service", svc_mock)
    if not _had_lixeira:
        sys.modules["src.modules.lixeira"] = _lixeira_tmp  # type: ignore[assignment]
    try:
        yield svc_mock
    finally:
        # Restaurar service
        if _had_service and _old_service is not None:
            sys.modules["src.modules.clientes.core.service"] = _old_service
        elif "src.modules.clientes.core.service" in sys.modules:
            del sys.modules["src.modules.clientes.core.service"]
        if core_mock is not None and _old_core_service is not None:
            setattr(core_mock, "service", _old_core_service)
        # Restaurar lixeira
        if not _had_lixeira and "src.modules.lixeira" in sys.modules:
            del sys.modules["src.modules.lixeira"]


@contextmanager
def _patch_editor_dialog(dialog_cls_mock: MagicMock):
    """Injeta mock de ClientEditorDialog no sys.modules durante o contexto."""
    _dialog_mod_name = "src.modules.clientes.ui.views.client_editor_dialog"
    _had = _dialog_mod_name in sys.modules
    _old = sys.modules.get(_dialog_mod_name)

    mod = types.ModuleType(_dialog_mod_name)
    mod.ClientEditorDialog = dialog_cls_mock  # type: ignore[attr-defined]
    sys.modules[_dialog_mod_name] = mod
    try:
        yield dialog_cls_mock
    finally:
        if _had and _old is not None:
            sys.modules[_dialog_mod_name] = _old
        elif _dialog_mod_name in sys.modules:
            del sys.modules[_dialog_mod_name]


# ---------------------------------------------------------------------------
# 6. Testes diretos das funções puras de actions.py
# ---------------------------------------------------------------------------


class TestActionsHelpers:
    """Testa as funções puras de actions.py diretamente, sem dependência de UI.

    Estas funções são a base extrapolada de ClientesV2Frame;
    se mudarem de comportamento, estes testes falham antes que qualquer
    integração seja exercitada.
    """

    def test_resolve_client_label_with_razao(self) -> None:
        """resolve_client_label retorna '{razao} (ID {n})' quando razao_social está preenchida."""
        from src.modules.clientes.ui.actions import resolve_client_label

        row = MagicMock()
        row.id = "42"
        row.razao_social = "Farmácia Modelo"
        result = resolve_client_label(42, {"iid1": row})
        assert result == "Farmácia Modelo (ID 42)"

    def test_resolve_client_label_without_razao(self) -> None:
        """resolve_client_label retorna 'ID {n}' quando razao_social está vazia."""
        from src.modules.clientes.ui.actions import resolve_client_label

        row = MagicMock()
        row.id = "99"
        row.razao_social = ""
        result = resolve_client_label(99, {"iid1": row})
        assert result == "ID 99"

    def test_resolve_client_label_not_found(self) -> None:
        """resolve_client_label retorna 'ID {n}' se cliente não está no mapa."""
        from src.modules.clientes.ui.actions import resolve_client_label

        result = resolve_client_label(55, {})
        assert result == "ID 55"

    def test_client_row_to_dict_structure(self) -> None:
        """client_row_to_dict produz o dict com todas as chaves esperadas pelo ANVISA."""
        from src.modules.clientes.ui.actions import client_row_to_dict

        row = MagicMock()
        row.id = "7"
        row.razao_social = "Empresa X"
        row.cnpj = "12.345.678/0001-90"
        row.nome = "Contato Y"
        row.whatsapp = "(11) 99999-0000"
        row.status = "Ativo"
        result = client_row_to_dict(row)
        assert result == {
            "id": "7",
            "razao_social": "Empresa X",
            "cnpj": "12.345.678/0001-90",
            "nome": "Contato Y",
            "whatsapp": "(11) 99999-0000",
            "status": "Ativo",
        }

    def test_client_row_to_dict_none_fields_become_empty(self) -> None:
        """client_row_to_dict converte None em string vazia para cnpj/nome/whatsapp/status."""
        from src.modules.clientes.ui.actions import client_row_to_dict

        row = MagicMock()
        row.id = "1"
        row.razao_social = "Z"
        row.cnpj = None
        row.nome = None
        row.whatsapp = None
        row.status = None
        result = client_row_to_dict(row)
        assert result["cnpj"] == ""
        assert result["nome"] == ""
        assert result["whatsapp"] == ""
        assert result["status"] == ""

    def test_execute_hard_delete_calls_service(self) -> None:
        """execute_hard_delete chama excluir_clientes_definitivamente quando confirmado."""
        from src.modules.clientes.ui.actions import execute_hard_delete

        svc = MagicMock()
        svc.excluir_clientes_definitivamente.return_value = (True, [])
        on_success = MagicMock()
        ask_fn = MagicMock(return_value=True)
        show_info = MagicMock()
        show_error = MagicMock()

        result = execute_hard_delete(
            client_id=10,
            label_cli="Empresa (ID 10)",
            top=MagicMock(),
            service=svc,
            on_success=on_success,
            ask_danger_fn=ask_fn,
            show_info_fn=show_info,
            show_error_fn=show_error,
        )

        assert result is True
        svc.excluir_clientes_definitivamente.assert_called_once_with([10])
        on_success.assert_called_once()

    def test_execute_soft_delete_calls_service(self) -> None:
        """execute_soft_delete chama mover_cliente_para_lixeira quando confirmado."""
        from src.modules.clientes.ui.actions import execute_soft_delete

        svc = MagicMock()
        on_success = MagicMock()
        refresh = MagicMock()
        ask_fn = MagicMock(return_value=True)
        show_info = MagicMock()
        show_error = MagicMock()

        result = execute_soft_delete(
            client_id=20,
            label_cli="Empresa (ID 20)",
            top=MagicMock(),
            service=svc,
            refresh_lixeira=refresh,
            on_success=on_success,
            ask_fn=ask_fn,
            show_info_fn=show_info,
            show_error_fn=show_error,
        )

        assert result is True
        svc.mover_cliente_para_lixeira.assert_called_once_with(20)
        on_success.assert_called_once()
        refresh.assert_called_once()


# ---------------------------------------------------------------------------
# 7. Testes dos helpers de WhatsApp (normalize_phone_for_whatsapp / whatsapp_url)
# ---------------------------------------------------------------------------


class TestWhatsAppHelpers:
    """Testa as funções puras de WhatsApp extraídas para actions.py.

    Preserva o comportamento exato que existia em ClientesV2Frame
    como @staticmethod — se a lógica mudar, estes testes falham primeiro.
    """

    def test_normalize_formated_number(self) -> None:
        """Número formatado com parênteses e hífen é normalizado corretamente."""
        from src.modules.clientes.ui.actions import normalize_phone_for_whatsapp

        assert normalize_phone_for_whatsapp("(11) 98765-4321") == "5511987654321"

    def test_normalize_with_country_code_plus(self) -> None:
        """Número com +55 já presente é normalizado sem duplicar o prefixo."""
        from src.modules.clientes.ui.actions import normalize_phone_for_whatsapp

        assert normalize_phone_for_whatsapp("+55 11 98765-4321") == "5511987654321"

    def test_normalize_plain_digits_adds_country_code(self) -> None:
        """Número sem código do país recebe o prefixo 55."""
        from src.modules.clientes.ui.actions import normalize_phone_for_whatsapp

        assert normalize_phone_for_whatsapp("11987654321") == "5511987654321"

    def test_normalize_already_has_55_not_duplicated(self) -> None:
        """Número que já inicia com 55 não recebe segundo prefixo."""
        from src.modules.clientes.ui.actions import normalize_phone_for_whatsapp

        result = normalize_phone_for_whatsapp("5511987654321")
        assert result == "5511987654321"

    def test_normalize_empty_string_returns_none(self) -> None:
        """String vazia retorna None."""
        from src.modules.clientes.ui.actions import normalize_phone_for_whatsapp

        assert normalize_phone_for_whatsapp("") is None

    def test_normalize_whitespace_only_returns_none(self) -> None:
        """String só com espaços retorna None."""
        from src.modules.clientes.ui.actions import normalize_phone_for_whatsapp

        assert normalize_phone_for_whatsapp("   ") is None

    def test_normalize_non_digit_only_returns_none(self) -> None:
        """String sem nenhum dígito (ex: 'N/A') retorna None."""
        from src.modules.clientes.ui.actions import normalize_phone_for_whatsapp

        assert normalize_phone_for_whatsapp("N/A") is None

    def test_normalize_too_short_returns_none(self) -> None:
        """Número com menos de 12 dígitos após prefixo retorna None."""
        from src.modules.clientes.ui.actions import normalize_phone_for_whatsapp

        # 5511 = 4 dígitos → com 55 fica 5555 11 que pode ter < 12 dígitos
        assert normalize_phone_for_whatsapp("9999") is None

    def test_whatsapp_url_format(self) -> None:
        """URL gerada tem formato wa.me correto."""
        from src.modules.clientes.ui.actions import whatsapp_url

        assert whatsapp_url("5511987654321") == "https://wa.me/5511987654321"

    def test_whatsapp_url_uses_digits_as_is(self) -> None:
        """whatsapp_url não modifica o argumento — usa exatamente os dígitos fornecidos."""
        from src.modules.clientes.ui.actions import whatsapp_url

        assert whatsapp_url("5521999990000") == "https://wa.me/5521999990000"


# ---------------------------------------------------------------------------
# 8. Testes de resolve_whatsapp_click (guards do clique na Treeview)
# ---------------------------------------------------------------------------


class TestTreeClickResolver:
    """Testa resolve_whatsapp_click — função pura que decide se um clique na Treeview
    deve acionar a ação de WhatsApp, sem depêndência de widget Tkinter.
    """

    def _resolve(self, region: str, row_id: str, column_id: str, values: tuple):
        from src.modules.clientes.ui.actions import resolve_whatsapp_click

        return resolve_whatsapp_click(region, row_id, column_id, values)

    def test_non_cell_region_returns_none(self) -> None:
        """Clique em heading ou separator retorna None."""
        assert self._resolve("heading", "I001", "#5", ("A", "B", "C", "D", "11999990000")) is None

    def test_empty_region_returns_none(self) -> None:
        """Região vazia retorna None."""
        assert self._resolve("", "I001", "#5", ("A", "B", "C", "D", "11999990000")) is None

    def test_empty_row_id_returns_none(self) -> None:
        """row_id vazio retorna None mesmo com região cell."""
        assert self._resolve("cell", "", "#5", ("A", "B", "C", "D", "11999990000")) is None

    def test_empty_column_id_returns_none(self) -> None:
        """column_id vazio retorna None."""
        assert self._resolve("cell", "I001", "", ("A", "B", "C", "D", "11999990000")) is None

    def test_wrong_column_returns_none(self) -> None:
        """Clique em coluna diferente de #5 retorna None."""
        assert self._resolve("cell", "I001", "#1", ("A", "B", "C", "D", "11999990000")) is None
        assert self._resolve("cell", "I001", "#3", ("A", "B", "C", "D", "11999990000")) is None

    def test_values_too_short_returns_none(self) -> None:
        """Tupla com menos de 5 elementos retorna None."""
        assert self._resolve("cell", "I001", "#5", ("A", "B", "C")) is None

    def test_empty_whatsapp_value_returns_none(self) -> None:
        """Valor do WhatsApp vazio retorna None."""
        assert self._resolve("cell", "I001", "#5", ("A", "B", "C", "D", "")) is None

    def test_whitespace_whatsapp_value_returns_none(self) -> None:
        """Valor do WhatsApp com só espaços retorna None."""
        assert self._resolve("cell", "I001", "#5", ("A", "B", "C", "D", "   ")) is None

    def test_valid_click_returns_raw_value(self) -> None:
        """Clique válido na coluna #5 retorna o valor bruto do WhatsApp."""
        result = self._resolve("cell", "I001", "#5", ("A", "B", "C", "D", "(11) 99999-0000"))
        assert result == "(11) 99999-0000"

    def test_valid_click_with_plain_digits_returns_raw_value(self) -> None:
        """Dígitos puros são retornados sem modificação."""
        result = self._resolve("cell", "I001", "#5", ("A", "B", "C", "D", "11987654321"))
        assert result == "11987654321"

    def test_empty_values_tuple_returns_none(self) -> None:
        """Tupla vazia retorna None sem levantar excessão."""
        assert self._resolve("cell", "I001", "#5", ()) is None


# ---------------------------------------------------------------------------
# 9. Testes de trigger_dialog_upload (auto-disparo de upload)
# ---------------------------------------------------------------------------


class TestTriggerDialogUpload:
    """Testa trigger_dialog_upload — função pura que age sobre um dialog duck-typed."""

    def test_calls_on_enviar_documentos_when_present(self) -> None:
        """Chama _on_enviar_documentos() se o dialog implementar o método."""
        from src.modules.clientes.ui.actions import trigger_dialog_upload

        dialog = MagicMock()
        trigger_dialog_upload(dialog)
        dialog._on_enviar_documentos.assert_called_once()

    def test_does_nothing_when_method_absent(self) -> None:
        """Não levanta exceção quando dialog não tem _on_enviar_documentos."""
        from src.modules.clientes.ui.actions import trigger_dialog_upload

        dialog = MagicMock(spec=[])  # sem nenhum atributo
        # Não deve levantar
        trigger_dialog_upload(dialog)

    def test_swallows_exception_from_on_enviar_documentos(self) -> None:
        """Exceção dentro de _on_enviar_documentos é silenciada sem propagar."""
        from src.modules.clientes.ui.actions import trigger_dialog_upload

        dialog = MagicMock()
        dialog._on_enviar_documentos.side_effect = RuntimeError("falha simulada")
        # Não deve propagar
        trigger_dialog_upload(dialog)


# ---------------------------------------------------------------------------
# 10. Testes de editor_dialog_is_live
# ---------------------------------------------------------------------------


class TestEditorDialogIsLive:
    """Testa editor_dialog_is_live — função pura que verifica liveness do dialog."""

    def test_none_returns_false(self) -> None:
        """None retorna False imediatamente sem chamar winfo_exists."""
        from src.modules.clientes.ui.actions import editor_dialog_is_live

        assert editor_dialog_is_live(None) is False

    def test_existing_dialog_returns_true(self) -> None:
        """Dialog com winfo_exists()=True retorna True."""
        from src.modules.clientes.ui.actions import editor_dialog_is_live

        dialog = MagicMock()
        dialog.winfo_exists.return_value = True
        assert editor_dialog_is_live(dialog) is True

    def test_closed_dialog_returns_false(self) -> None:
        """Dialog com winfo_exists()=False (fechado) retorna False."""
        from src.modules.clientes.ui.actions import editor_dialog_is_live

        dialog = MagicMock()
        dialog.winfo_exists.return_value = False
        assert editor_dialog_is_live(dialog) is False

    def test_destroyed_dialog_raises_returns_false(self) -> None:
        """Dialog cujo winfo_exists() levanta exceção retorna False sem propagar."""
        from src.modules.clientes.ui.actions import editor_dialog_is_live

        dialog = MagicMock()
        dialog.winfo_exists.side_effect = RuntimeError("widget destroyed")
        assert editor_dialog_is_live(dialog) is False


# ---------------------------------------------------------------------------
# 11. Testes de execute_restore
# ---------------------------------------------------------------------------

_mock_log_restore = logging.getLogger("test.restore")
_mock_ask_yes_no_restore = MagicMock(return_value=True)
_mock_show_info_restore = MagicMock()
_mock_show_error_restore = MagicMock()

_restore_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_restore_client",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": _mock_log_restore,
        "_ask_yes_no": _mock_ask_yes_no_restore,
        "_show_info": _mock_show_info_restore,
        "_show_error": _mock_show_error_restore,
        "Any": Any,
    },
)
_on_restore_client = _restore_fns["_on_restore_client"]


def _make_restore_fake(
    client_id: int | None = 42,
    trash_mode: bool = True,
    razao: str = "Empresa Restaurada",
) -> MagicMock:
    """Cria um stub de ClientesV2Frame para testes de _on_restore_client."""
    fake = MagicMock()
    fake._selected_client_id = client_id
    fake._trash_mode = trash_mode
    row = MagicMock()
    row.id = client_id
    row.razao_social = razao
    fake._row_data_map = {"iid1": row}
    fake.winfo_toplevel.return_value = MagicMock()
    return fake


def _make_restore_service_mock() -> MagicMock:
    svc = MagicMock()
    svc.restaurar_clientes_da_lixeira = MagicMock()
    return svc


class TestRestoreClientBehavior:
    """Verifica o comportamento de _on_restore_client via extract_functions_from_source."""

    def setup_method(self) -> None:
        _mock_ask_yes_no_restore.reset_mock()
        _mock_ask_yes_no_restore.return_value = True
        _mock_show_info_restore.reset_mock()
        _mock_show_error_restore.reset_mock()

    def test_no_client_selected_returns_early(self) -> None:
        """Sem cliente selecionado, nenhum serviço é chamado."""
        fake = _make_restore_fake(client_id=None)
        svc = _make_restore_service_mock()

        with _patch_service(svc):
            _on_restore_client(fake)

        svc.restaurar_clientes_da_lixeira.assert_not_called()

    def test_not_trash_mode_returns_early(self) -> None:
        """Em modo ATIVOS (não é lixeira), nenhum serviço é chamado."""
        fake = _make_restore_fake(client_id=42, trash_mode=False)
        svc = _make_restore_service_mock()

        with _patch_service(svc):
            _on_restore_client(fake)

        svc.restaurar_clientes_da_lixeira.assert_not_called()

    def test_user_cancel_no_service_call(self) -> None:
        """Usuário cancela diálogo de confirmação: nenhum serviço chamado."""
        fake = _make_restore_fake(client_id=55, trash_mode=True)
        svc = _make_restore_service_mock()
        _mock_ask_yes_no_restore.return_value = False

        with _patch_service(svc):
            _on_restore_client(fake)

        svc.restaurar_clientes_da_lixeira.assert_not_called()

    def test_confirm_calls_service(self) -> None:
        """Usuário confirma: restaurar_clientes_da_lixeira é chamado com o ID correto."""
        fake = _make_restore_fake(client_id=77, trash_mode=True)
        svc = _make_restore_service_mock()
        _mock_ask_yes_no_restore.return_value = True

        with _patch_service(svc):
            _on_restore_client(fake)

        svc.restaurar_clientes_da_lixeira.assert_called_once_with([77])

    def test_success_shows_info(self) -> None:
        """Após restauração bem-sucedida, show_info é chamado."""
        fake = _make_restore_fake(client_id=12, trash_mode=True)
        svc = _make_restore_service_mock()

        with _patch_service(svc):
            _on_restore_client(fake)

        _mock_show_info_restore.assert_called_once()

    def test_service_error_shows_error(self) -> None:
        """Se o serviço lançar exceção, show_error é chamado."""
        fake = _make_restore_fake(client_id=99, trash_mode=True)
        svc = _make_restore_service_mock()
        svc.restaurar_clientes_da_lixeira.side_effect = RuntimeError("DB offline")

        with _patch_service(svc):
            _on_restore_client(fake)

        _mock_show_error_restore.assert_called_once()


# ---------------------------------------------------------------------------
# 12. Testes de execute_export (ações de exportação)
# ---------------------------------------------------------------------------

_mock_show_info_export_guard = MagicMock()
_mock_show_error_export_guard = MagicMock()

_export_view_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_export",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": logging.getLogger("test.export_guard"),
        "_show_info": _mock_show_info_export_guard,
        "_show_error": _mock_show_error_export_guard,
        "Any": Any,
    },
)
_on_export_view = _export_view_fns["_on_export"]


class TestExportBehavior:
    """Testa execute_export (actions.py) diretamente e guards de _on_export."""

    def setup_method(self) -> None:
        _mock_show_info_export_guard.reset_mock()
        _mock_show_error_export_guard.reset_mock()

    # -- guards em _on_export (view) --

    def test_empty_row_data_map_shows_info_and_returns(self) -> None:
        """Com _row_data_map vazio, _on_export mostra info e retorna sem exportar."""
        fake = MagicMock()
        fake._row_data_map = {}
        fake.winfo_toplevel.return_value = MagicMock()

        _on_export_view(fake)

        _mock_show_info_export_guard.assert_called_once()

    # -- execute_export direto --

    def test_cancelled_dialog_no_export_called(self) -> None:
        """ask_save_fn retornando '' não chama nenhum método de exportação."""
        from src.modules.clientes.ui.actions import execute_export

        mock_export = MagicMock()
        mock_export.is_xlsx_available.return_value = False
        mock_show_info = MagicMock()

        execute_export(
            rows_to_export=[MagicMock()],
            top=MagicMock(),
            ask_save_fn=MagicMock(return_value=""),
            show_info_fn=mock_show_info,
            show_error_fn=MagicMock(),
            export_module=mock_export,
        )

        mock_export.export_clients_to_csv.assert_not_called()
        mock_export.export_clients_to_xlsx.assert_not_called()
        mock_show_info.assert_not_called()

    def test_csv_path_calls_csv_export_and_shows_info(self) -> None:
        """Caminho .csv chama export_clients_to_csv e mostra mensagem de sucesso."""
        from src.modules.clientes.ui.actions import execute_export

        mock_export = MagicMock()
        mock_export.is_xlsx_available.return_value = False
        mock_show_info = MagicMock()

        execute_export(
            rows_to_export=[MagicMock(), MagicMock()],
            top=MagicMock(),
            ask_save_fn=MagicMock(return_value="/tmp/saida.csv"),
            show_info_fn=mock_show_info,
            show_error_fn=MagicMock(),
            export_module=mock_export,
        )

        mock_export.export_clients_to_csv.assert_called_once()
        mock_export.export_clients_to_xlsx.assert_not_called()
        mock_show_info.assert_called_once()

    def test_xlsx_path_calls_xlsx_export(self) -> None:
        """Caminho .xlsx chama export_clients_to_xlsx (não csv)."""
        from src.modules.clientes.ui.actions import execute_export

        mock_export = MagicMock()
        mock_export.is_xlsx_available.return_value = True

        execute_export(
            rows_to_export=[MagicMock()],
            top=MagicMock(),
            ask_save_fn=MagicMock(return_value="/tmp/saida.xlsx"),
            show_info_fn=MagicMock(),
            show_error_fn=MagicMock(),
            export_module=mock_export,
        )

        mock_export.export_clients_to_xlsx.assert_called_once()
        mock_export.export_clients_to_csv.assert_not_called()

    def test_export_runtime_error_shows_error(self) -> None:
        """RuntimeError no módulo de exportação chama show_error sem propagar."""
        from src.modules.clientes.ui.actions import execute_export

        mock_export = MagicMock()
        mock_export.is_xlsx_available.return_value = False
        mock_export.export_clients_to_csv.side_effect = RuntimeError("disco cheio")
        mock_show_error = MagicMock()

        execute_export(
            rows_to_export=[MagicMock()],
            top=MagicMock(),
            ask_save_fn=MagicMock(return_value="/tmp/saida.csv"),
            show_info_fn=MagicMock(),
            show_error_fn=mock_show_error,
            export_module=mock_export,
        )

        mock_show_error.assert_called_once()

    def test_import_error_shows_library_error(self) -> None:
        """ImportError chama show_error com mensagem de biblioteca ausente."""
        from src.modules.clientes.ui.actions import execute_export

        mock_export = MagicMock()
        mock_export.is_xlsx_available.side_effect = ImportError("openpyxl ausente")
        mock_show_error = MagicMock()

        execute_export(
            rows_to_export=[MagicMock()],
            top=MagicMock(),
            ask_save_fn=MagicMock(return_value="/tmp/saida.xlsx"),
            show_info_fn=MagicMock(),
            show_error_fn=mock_show_error,
            export_module=mock_export,
        )

        mock_show_error.assert_called_once()
        assert "Biblioteca" in mock_show_error.call_args[0][2]


# ---------------------------------------------------------------------------
# 13. Testes de _on_toggle_trash
# ---------------------------------------------------------------------------

_mock_time_toggle = MagicMock()
_mock_time_toggle.perf_counter.return_value = 0.0

_toggle_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_toggle_trash",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": logging.getLogger("test.toggle_trash"),
        "time": _mock_time_toggle,
        "Any": Any,
    },
)
_on_toggle_trash = _toggle_fns["_on_toggle_trash"]


def _make_toggle_fake(trash_mode: bool = False) -> MagicMock:
    """Stub de ClientesV2Frame para testes de _on_toggle_trash."""
    fake = MagicMock()
    fake._trash_mode = trash_mode
    fake.toolbar = MagicMock()
    fake.toolbar.status_var = MagicMock()
    fake.toolbar.get_search_text.return_value = ""
    fake.toolbar.get_order.return_value = ""
    fake.toolbar.get_status.return_value = ""
    fake.actionbar = MagicMock()
    return fake


class TestToggleTrashBehavior:
    """Protege o comportamento de _on_toggle_trash — sem extracção (puro glue de widgets)."""

    def test_mode_toggles_false_to_true(self) -> None:
        """Partindo de False, _trash_mode vira True."""
        fake = _make_toggle_fake(trash_mode=False)
        _on_toggle_trash(fake)
        assert fake._trash_mode is True

    def test_mode_toggles_true_to_false(self) -> None:
        """Partindo de True, _trash_mode vira False."""
        fake = _make_toggle_fake(trash_mode=True)
        _on_toggle_trash(fake)
        assert fake._trash_mode is False

    def test_status_reset_when_entering_trash(self) -> None:
        """Ao entrar na lixeira, status_var é resetado para 'Todos'."""
        fake = _make_toggle_fake(trash_mode=False)
        _on_toggle_trash(fake)
        fake.toolbar.status_var.set.assert_called_once_with("Todos")

    def test_status_not_reset_when_leaving_trash(self) -> None:
        """Ao sair da lixeira, status_var NÃO é resetado."""
        fake = _make_toggle_fake(trash_mode=True)
        _on_toggle_trash(fake)
        fake.toolbar.status_var.set.assert_not_called()

    def test_load_async_called_with_show_trash_true(self) -> None:
        """Ao entrar na lixeira, load_async recebe show_trash=True."""
        fake = _make_toggle_fake(trash_mode=False)
        _on_toggle_trash(fake)
        fake.load_async.assert_called_once()
        kwargs = fake.load_async.call_args[1]
        assert kwargs.get("show_trash") is True

    def test_load_async_called_with_show_trash_false(self) -> None:
        """Ao sair da lixeira, load_async recebe show_trash=False."""
        fake = _make_toggle_fake(trash_mode=True)
        _on_toggle_trash(fake)
        fake.load_async.assert_called_once()
        kwargs = fake.load_async.call_args[1]
        assert kwargs.get("show_trash") is False

    def test_actionbar_delete_label_in_trash_mode(self) -> None:
        """Entrando na lixeira: actionbar recebe label 'Excluir definitivamente'."""
        fake = _make_toggle_fake(trash_mode=False)
        _on_toggle_trash(fake)
        fake.actionbar.set_delete_label.assert_called_once_with("Excluir definitivamente")

    def test_actionbar_delete_label_in_normal_mode(self) -> None:
        """Saindo da lixeira: actionbar recebe label 'Excluir'."""
        fake = _make_toggle_fake(trash_mode=True)
        _on_toggle_trash(fake)
        fake.actionbar.set_delete_label.assert_called_once_with("Excluir")


# ---------------------------------------------------------------------------
# 14. Testes de identify_clicked_row + _on_tree_double_click
# ---------------------------------------------------------------------------


class TestIdentifyClickedRow:
    """Testa a função pura identify_clicked_row de actions.py."""

    def _tree(self, region: str, row_id: str) -> MagicMock:
        t = MagicMock()
        t.identify.return_value = region
        t.identify_row.return_value = row_id
        return t

    def _event(self, x: int = 10, y: int = 20) -> MagicMock:
        e = MagicMock()
        e.x = x
        e.y = y
        return e

    def test_cell_with_row_returns_item_id(self) -> None:
        """Clique em célula com linha válida retorna item_id."""
        from src.modules.clientes.ui.actions import identify_clicked_row

        tree = self._tree(region="cell", row_id="I001")
        assert identify_clicked_row(tree, self._event()) == "I001"

    def test_heading_returns_none(self) -> None:
        """Clique no cabeçalho retorna None."""
        from src.modules.clientes.ui.actions import identify_clicked_row

        tree = self._tree(region="heading", row_id="")
        assert identify_clicked_row(tree, self._event()) is None

    def test_separator_returns_none(self) -> None:
        """Clique no separador retorna None."""
        from src.modules.clientes.ui.actions import identify_clicked_row

        tree = self._tree(region="separator", row_id="")
        assert identify_clicked_row(tree, self._event()) is None

    def test_cell_with_empty_row_returns_none(self) -> None:
        """Célula sem linha (fora das linhas) retorna None."""
        from src.modules.clientes.ui.actions import identify_clicked_row

        tree = self._tree(region="cell", row_id="")
        assert identify_clicked_row(tree, self._event()) is None


_mock_log_dblclick = logging.getLogger("test.double_click")

_dblclick_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_tree_double_click",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": _mock_log_dblclick,
        "tk": MagicMock(),
        "Any": Any,
    },
)
_on_tree_double_click = _dblclick_fns["_on_tree_double_click"]


def _make_dblclick_fake(
    has_tree: bool = True,
    row_id: str = "I001",
    region: str = "cell",
    client_id: int = 42,
) -> MagicMock:
    """Stub de ClientesV2Frame para testes de _on_tree_double_click."""
    fake = MagicMock()
    if not has_tree:
        fake.tree = None
    else:
        tree = MagicMock()
        tree.identify.return_value = region
        tree.identify_row.return_value = row_id
        fake.tree = tree
    row = MagicMock()
    row.id = client_id
    fake._row_data_map = {row_id: row} if row_id else {}
    fake._selected_client_id = None
    return fake


class TestDoubleClickBehavior:
    """Protege o comportamento de _on_tree_double_click."""

    def test_no_tree_returns_break(self) -> None:
        """Sem tree, retorna 'break' imediatamente."""
        fake = _make_dblclick_fake(has_tree=False)
        result = _on_tree_double_click(fake, MagicMock(x=5, y=10))
        assert result == "break"
        fake._open_client_editor.assert_not_called()

    def test_click_on_heading_returns_break_no_editor(self) -> None:
        """Clique no heading retorna 'break' sem abrir editor."""
        fake = _make_dblclick_fake(region="heading", row_id="")
        result = _on_tree_double_click(fake, MagicMock(x=5, y=10))
        assert result == "break"
        fake._open_client_editor.assert_not_called()

    def test_cell_click_opens_editor(self) -> None:
        """Clique em célula válida chama _open_client_editor com source='doubleclick'."""
        fake = _make_dblclick_fake(region="cell", row_id="I001")
        _on_tree_double_click(fake, MagicMock(x=5, y=10))
        fake._open_client_editor.assert_called_once_with(source="doubleclick")

    def test_cell_click_updates_selected_id(self) -> None:
        """Clique em célula válida atualiza _selected_client_id."""
        fake = _make_dblclick_fake(region="cell", row_id="I001", client_id=99)
        _on_tree_double_click(fake, MagicMock(x=5, y=10))
        assert fake._selected_client_id == 99

    def test_cell_click_selects_tree_row(self) -> None:
        """Clique em célula válida chama selection_set e focus na tree."""
        fake = _make_dblclick_fake(region="cell", row_id="I001")
        _on_tree_double_click(fake, MagicMock(x=5, y=10))
        fake.tree.selection_set.assert_called_once_with("I001")
        fake.tree.focus.assert_called_once_with("I001")

    def test_always_returns_break(self) -> None:
        """Independente do resultado, sempre retorna 'break'."""
        fake = _make_dblclick_fake(region="cell", row_id="I001")
        result = _on_tree_double_click(fake, MagicMock(x=5, y=10))
        assert result == "break"


# ---------------------------------------------------------------------------
# 15. Testes de resolve_selection_id + _on_tree_select
# ---------------------------------------------------------------------------


class TestResolveSelectionId:
    """Testa a função pura resolve_selection_id de actions.py."""

    def _tree(self, selection: list, values: tuple = ()) -> MagicMock:
        t = MagicMock()
        t.selection.return_value = selection
        t.item.return_value = {"values": values}
        # tree.item(item_id, "values") — chamado com dois args
        t.item.side_effect = lambda item_id, key: values if key == "values" else {}
        return t

    def test_empty_selection_returns_none(self) -> None:
        """Seleção vazia retorna None."""
        from src.modules.clientes.ui.actions import resolve_selection_id

        tree = self._tree(selection=[])
        assert resolve_selection_id(tree) is None

    def test_selection_with_valid_id_returns_int(self) -> None:
        """Seleção com valor numérico retorna int."""
        from src.modules.clientes.ui.actions import resolve_selection_id

        tree = self._tree(selection=["I001"], values=("42", "Empresa X"))
        assert resolve_selection_id(tree) == 42

    def test_selection_with_empty_values_returns_none(self) -> None:
        """Seleção com valores vazios retorna None."""
        from src.modules.clientes.ui.actions import resolve_selection_id

        tree = self._tree(selection=["I001"], values=())
        assert resolve_selection_id(tree) is None

    def test_selection_with_non_numeric_id_returns_none(self) -> None:
        """Primeiro valor não numérico retorna None."""
        from src.modules.clientes.ui.actions import resolve_selection_id

        tree = self._tree(selection=["I001"], values=("abc", "Empresa X"))
        assert resolve_selection_id(tree) is None


_mock_log_select = logging.getLogger("test.tree_select")
_mock_apply_selected_tag = MagicMock()

_select_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_tree_select",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": _mock_log_select,
        "apply_selected_tag": _mock_apply_selected_tag,
        "Any": Any,
    },
)
_on_tree_select = _select_fns["_on_tree_select"]


def _make_select_fake(
    selection: list = (),
    values: tuple = ("42", "Empresa X"),
    has_actionbar: bool = True,
    has_tree_colors: bool = False,
) -> MagicMock:
    """Stub de ClientesV2Frame para testes de _on_tree_select."""
    fake = MagicMock()
    tree = MagicMock()
    tree.selection.return_value = list(selection)
    tree.item.side_effect = lambda item_id, key: values if key == "values" else {}
    fake.tree = tree
    fake._selected_client_id = None
    fake._tree_colors = MagicMock() if has_tree_colors else None
    if has_actionbar:
        fake.actionbar = MagicMock()
    else:
        del fake.actionbar  # garante que hasattr retorna False
    return fake


class TestTreeSelectBehavior:
    """Protege o comportamento de _on_tree_select."""

    def setup_method(self) -> None:
        _mock_apply_selected_tag.reset_mock()

    def test_empty_selection_sets_id_none(self) -> None:
        """Seleção vazia define _selected_client_id como None."""
        fake = _make_select_fake(selection=[])
        _on_tree_select(fake)
        assert fake._selected_client_id is None

    def test_empty_selection_disables_actionbar(self) -> None:
        """Seleção vazia chama actionbar.set_selection_state(False)."""
        fake = _make_select_fake(selection=[])
        _on_tree_select(fake)
        fake.actionbar.set_selection_state.assert_called_once_with(False)

    def test_valid_selection_sets_client_id(self) -> None:
        """Seleção válida atualiza _selected_client_id com o valor correto."""
        fake = _make_select_fake(selection=["I001"], values=("99", "Empresa Y"))
        _on_tree_select(fake)
        assert fake._selected_client_id == 99

    def test_valid_selection_enables_actionbar(self) -> None:
        """Seleção válida chama actionbar.set_selection_state(True)."""
        fake = _make_select_fake(selection=["I001"], values=("99", "Empresa Y"))
        _on_tree_select(fake)
        fake.actionbar.set_selection_state.assert_called_once_with(True)

    def test_selection_with_empty_values_sets_id_none(self) -> None:
        """Valores vazios na seleção define _selected_client_id como None."""
        fake = _make_select_fake(selection=["I001"], values=())
        _on_tree_select(fake)
        assert fake._selected_client_id is None

    def test_apply_selected_tag_called_when_tree_colors_set(self) -> None:
        """apply_selected_tag é chamado quando _tree_colors não é None."""
        fake = _make_select_fake(selection=["I001"], values=("1", "X"), has_tree_colors=True)
        _on_tree_select(fake)
        _mock_apply_selected_tag.assert_called_once()

    def test_apply_selected_tag_not_called_without_colors(self) -> None:
        """apply_selected_tag NÃO é chamado quando _tree_colors é None."""
        fake = _make_select_fake(selection=["I001"], values=("1", "X"), has_tree_colors=False)
        _on_tree_select(fake)
        _mock_apply_selected_tag.assert_not_called()


# ---------------------------------------------------------------------------
# Helpers para TestGetSelectedValuesBehavior
# ---------------------------------------------------------------------------


def _make_gsv_frame(
    client_id: int | None,
    tree_selection: list | None = None,
    tree_values: tuple | None = None,
    row_map: dict | None = None,
) -> Any:
    """Stub de ClientesV2Frame com atributos mínimos para _get_selected_values."""
    from src.modules.clientes.ui.view import ClientesV2Frame  # noqa: PLC0415

    frame = object.__new__(ClientesV2Frame)
    frame._selected_client_id = client_id
    frame._row_data_map = row_map or {}
    if tree_selection is not None:
        mock_t = MagicMock()
        mock_t.selection.return_value = tree_selection
        if tree_selection and tree_values is not None:
            mock_t.item.return_value = tree_values
        elif tree_selection:
            mock_t.item.return_value = ()
        frame.tree = mock_t
    else:
        setattr(frame, "tree", None)
    return frame


class TestGetSelectedValuesBehavior:
    """Proteção dos três caminhos de resolução de _get_selected_values."""

    def test_returns_none_when_no_client_id(self) -> None:
        """Sem _selected_client_id (falsy), retorna None imediatamente."""
        frame = _make_gsv_frame(client_id=None)
        assert frame._get_selected_values() is None

    def test_returns_tree_values_when_treeview_has_selection(self) -> None:
        """Caminho primário: Treeview com seleção ativa retorna tupla completa."""
        frame = _make_gsv_frame(
            client_id=42,
            tree_selection=["I001"],
            tree_values=("42", "Acme Corp", "00.000.000/0001-00"),
        )
        result = frame._get_selected_values()
        assert result is not None
        assert result[0] == "42"
        assert result[1] == "Acme Corp"

    def test_fallback_to_row_map_when_tree_empty(self) -> None:
        """Caminho fallback: sem seleção na Treeview, usa _row_data_map."""
        row = types.SimpleNamespace(id="7", razao_social="Delta Ltda")
        frame = _make_gsv_frame(
            client_id=7,
            tree_selection=[],  # seleção vazia
            row_map={"iid1": row},
        )
        result = frame._get_selected_values()
        assert result is not None
        assert int(result[0]) == 7
        assert result[1] == "Delta Ltda"

    def test_minimal_tuple_when_id_not_in_map(self) -> None:
        """Fallback final: ID conhecido mas fora do mapa → tupla mínima com ID."""
        frame = _make_gsv_frame(client_id=99, row_map={})
        result = frame._get_selected_values()
        assert result is not None
        assert int(result[0]) == 99

    def test_tree_path_first_column_castable_to_int(self) -> None:
        """Primeiro elemento da tupla via Treeview deve ser conversível a int."""
        frame = _make_gsv_frame(
            client_id=55,
            tree_selection=["I002"],
            tree_values=("55", "Beta SA"),
        )
        result = frame._get_selected_values()
        assert result is not None
        assert int(result[0]) == 55


# ---------------------------------------------------------------------------
# 16. Testes dos handlers leves de filtro/pesquisa
# ---------------------------------------------------------------------------

_mock_normalize_order = MagicMock(return_value="normalized_test_order")

_filter_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_search",
    "_on_clear_search",
    "_on_order_changed",
    "_on_status_changed",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": logging.getLogger("test.filter_handlers"),
        "normalize_order_label": _mock_normalize_order,
        "Any": Any,
    },
)
_on_search_fn = _filter_fns["_on_search"]
_on_clear_search_fn = _filter_fns["_on_clear_search"]
_on_order_changed_fn = _filter_fns["_on_order_changed"]
_on_status_changed_fn = _filter_fns["_on_status_changed"]


def _make_filter_fake(
    search_text: str = "test_search",
    order: str = "test_order",
    status: str = "test_status",
) -> MagicMock:
    """Stub de ClientesV2Frame para testes dos handlers de filtro."""
    fake = MagicMock()
    fake.toolbar = MagicMock()
    fake.toolbar.get_search_text.return_value = search_text
    fake.toolbar.get_order.return_value = order
    fake.toolbar.get_status.return_value = status
    return fake


class TestFilterHandlersBehavior:
    """Proteção dos handlers _on_search, _on_clear_search, _on_order_changed, _on_status_changed."""

    def setup_method(self) -> None:
        _mock_normalize_order.reset_mock()
        _mock_normalize_order.return_value = "normalized_test_order"

    # --- _on_search ---------------------------------------------------------

    def test_search_delegates_to_carregar(self) -> None:
        """_on_search deve delegar o recarregamento para self.carregar()."""
        fake = _make_filter_fake()
        _on_search_fn(fake, "qualquer")
        fake.carregar.assert_called_once_with()

    def test_search_does_not_bypass_carregar(self) -> None:
        """_on_search não deve chamar load_async diretamente — deve passar por carregar()."""
        fake = _make_filter_fake()
        _on_search_fn(fake, "qualquer")
        fake.load_async.assert_not_called()

    # --- _on_clear_search ---------------------------------------------------

    def test_clear_search_clears_toolbar(self) -> None:
        """_on_clear_search chama toolbar.clear_search()."""
        fake = _make_filter_fake()
        _on_clear_search_fn(fake)
        fake.toolbar.clear_search.assert_called_once()

    def test_clear_search_calls_load_async_with_no_filter_args(self) -> None:
        """_on_clear_search chama load_async() sem argumentos de filtro."""
        fake = _make_filter_fake()
        _on_clear_search_fn(fake)
        fake.load_async.assert_called_once_with()

    # --- _on_order_changed --------------------------------------------------

    def test_order_changed_calls_normalize_order_label(self) -> None:
        """_on_order_changed chama normalize_order_label com o parâmetro recebido."""
        fake = _make_filter_fake()
        _on_order_changed_fn(fake, "Razao Social (A->Z)")
        _mock_normalize_order.assert_called_once_with("Razao Social (A->Z)")

    def test_order_changed_passes_normalized_label_to_load_async(self) -> None:
        """_on_order_changed usa o valor normalizado como order_label no load_async."""
        fake = _make_filter_fake()
        _on_order_changed_fn(fake, "qualquer_ordem")
        kwargs = fake.load_async.call_args[1]
        assert kwargs["order_label"] == "normalized_test_order"

    # --- _on_status_changed -------------------------------------------------

    def test_status_changed_delegates_to_carregar(self) -> None:
        """_on_status_changed deve delegar o recarregamento para self.carregar()."""
        fake = _make_filter_fake()
        _on_status_changed_fn(fake, "qualquer")
        fake.carregar.assert_called_once_with()

    def test_status_changed_does_not_bypass_carregar(self) -> None:
        """_on_status_changed não deve chamar load_async diretamente — deve passar por carregar()."""
        fake = _make_filter_fake()
        _on_status_changed_fn(fake, "qualquer")
        fake.load_async.assert_not_called()

    def test_order_changed_reads_search_and_status_from_toolbar(self) -> None:
        """_on_order_changed lê search_text e status da toolbar (não de parâmetros)."""
        fake = _make_filter_fake(search_text="my_query", status="inativo")
        _on_order_changed_fn(fake, "qualquer")
        kwargs = fake.load_async.call_args[1]
        assert kwargs["search"] == "my_query"
        assert kwargs["status"] == "inativo"


# ---------------------------------------------------------------------------
# 17. Testes de handle_column_lock_region + _on_column_lock
# ---------------------------------------------------------------------------


class TestHandleColumnLockRegion:
    """Testa a função pura handle_column_lock_region de actions.py."""

    def _fn(self):  # type: ignore[return]
        from src.modules.clientes.ui.actions import handle_column_lock_region

        return handle_column_lock_region

    def test_separator_returns_break(self) -> None:
        """Região 'separator' deve retornar 'break' (bloqueia resize)."""
        assert self._fn()("separator") == "break"

    def test_heading_returns_break(self) -> None:
        """Região 'heading' deve retornar 'break' (bloqueia reordenação)."""
        assert self._fn()("heading") == "break"

    def test_cell_returns_none(self) -> None:
        """Região 'cell' deve retornar None (permite seleção de linha)."""
        assert self._fn()("cell") is None

    def test_nothing_returns_none(self) -> None:
        """Região 'nothing' (fora das linhas) deve retornar None."""
        assert self._fn()("nothing") is None

    def test_empty_string_returns_none(self) -> None:
        """String vazia não é região bloqueável — retorna None."""
        assert self._fn()("") is None


_mock_log_column_lock = logging.getLogger("test.column_lock")

_column_lock_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_column_lock",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": _mock_log_column_lock,
        "Any": Any,
    },
)
_on_column_lock_fn = _column_lock_fns["_on_column_lock"]


def _make_column_lock_fake(region: str) -> MagicMock:
    """Stub de ClientesV2Frame para testes de _on_column_lock."""
    fake = MagicMock()
    fake.tree = MagicMock()
    fake.tree.identify_region.return_value = region
    return fake


class TestColumnLockHandlerBehavior:
    """Protege o comportamento do wrapper _on_column_lock em view.py."""

    def test_separator_region_returns_break(self) -> None:
        """Com região 'separator', _on_column_lock deve retornar 'break'."""
        fake = _make_column_lock_fake("separator")
        result = _on_column_lock_fn(fake, MagicMock(x=5, y=10))
        assert result == "break"

    def test_heading_region_returns_break(self) -> None:
        """Com região 'heading', _on_column_lock deve retornar 'break'."""
        fake = _make_column_lock_fake("heading")
        result = _on_column_lock_fn(fake, MagicMock(x=5, y=10))
        assert result == "break"

    def test_cell_region_returns_none(self) -> None:
        """Com região 'cell', _on_column_lock deve retornar None."""
        fake = _make_column_lock_fake("cell")
        result = _on_column_lock_fn(fake, MagicMock(x=5, y=10))
        assert result is None

    def test_exception_returns_none(self) -> None:
        """Se identify_region lançar, _on_column_lock deve retornar None (sem crash)."""
        fake = MagicMock()
        fake.tree.identify_region.side_effect = RuntimeError("boom")
        result = _on_column_lock_fn(fake, MagicMock(x=0, y=0))
        assert result is None


# ---------------------------------------------------------------------------
# 18. Testes de _on_theme_changed
# ---------------------------------------------------------------------------

_theme_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_theme_changed",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": logging.getLogger("test.theme_changed"),
        "Any": Any,
    },
)
_on_theme_changed_fn = _theme_fns["_on_theme_changed"]


def _make_theme_fake(
    exists: bool = True,
    last_mode: str | None = None,
    has_toolbar: bool = True,
    has_actionbar: bool = True,
) -> MagicMock:
    """Stub de ClientesV2Frame para testes de _on_theme_changed."""
    fake = MagicMock()
    fake.winfo_exists.return_value = exists
    if last_mode is not None:
        fake._last_applied_mode = last_mode
    else:
        # Sem atributo: simula primeira execução
        del fake._last_applied_mode
    fake.toolbar = MagicMock() if has_toolbar else None
    fake.actionbar = MagicMock() if has_actionbar else None
    return fake


class TestThemeChangedBehavior:
    """Proteção do handler _on_theme_changed — sem extração (puro glue de widget state)."""

    def test_sets_current_mode_and_last_applied(self) -> None:
        """Ao aplicar tema, current_mode e _last_applied_mode devem ser atualizados."""
        fake = _make_theme_fake(last_mode=None)
        _on_theme_changed_fn(fake, "Dark")
        assert fake.current_mode == "Dark"
        assert fake._last_applied_mode == "Dark"

    def test_duplicate_guard_skips_refresh(self) -> None:
        """Se _last_applied_mode já for o mesmo tema, tb.refresh_theme NÃO deve ser chamado."""
        fake = _make_theme_fake(last_mode="Dark")
        _on_theme_changed_fn(fake, "Dark")
        fake.toolbar.refresh_theme.assert_not_called()
        fake.actionbar.refresh_theme.assert_not_called()

    def test_refresh_called_when_mode_differs(self) -> None:
        """Quando o tema muda de fato, toolbar e actionbar devem ser atualizados."""
        fake = _make_theme_fake(last_mode="Light")
        _on_theme_changed_fn(fake, "Dark")
        fake.toolbar.refresh_theme.assert_called_once()
        fake.actionbar.refresh_theme.assert_called_once()

    def test_widget_destroyed_returns_early(self) -> None:
        """Se winfo_exists() retornar False, nada deve ser feito."""
        fake = _make_theme_fake(exists=False, last_mode=None)
        _on_theme_changed_fn(fake, "Dark")
        fake.toolbar.refresh_theme.assert_not_called()

    def test_toolbar_none_does_not_crash(self) -> None:
        """toolbar=None não deve causar AttributeError."""
        fake = _make_theme_fake(last_mode=None, has_toolbar=False)
        _on_theme_changed_fn(fake, "Light")  # não deve lançar
        fake.actionbar.refresh_theme.assert_called_once()

    def test_actionbar_none_does_not_crash(self) -> None:
        """actionbar=None não deve causar AttributeError."""
        fake = _make_theme_fake(last_mode=None, has_actionbar=False)
        _on_theme_changed_fn(fake, "Light")  # não deve lançar
        fake.toolbar.refresh_theme.assert_called_once()


# ---------------------------------------------------------------------------
# 19. Testes de auditoria de _on_tree_right_click (AST + comportamento mínimo)
# ---------------------------------------------------------------------------
# Estrutura de _on_tree_right_click (103 linhas, start=532):
#   A) Resolução de linha — tree.identify_row(event.y)   → widget
#   B) Guard / early return — if not item_id: return      → extraível (pure)
#   C) Seleção da linha    — selection_set + focus + _on_tree_select → widget
#   D) Criação do popup    — CTkToplevel + frame + btn_width/height   → widget
#   E) Definição dos itens — lista de botões make_btn(...) → semi-puro (texto=dado puro)
#   F) Condicional trash   — delete_text + botão Restaurar condicional → extraível
#   G) Posicionamento      — geometry(+x+y) via event.x_root/y_root    → widget
#   H) Foco/lift           — deiconify() + lift() + focus_force()      → widget
#   I) Fechamento          — close_on_focus_out (FocusOut + Escape)     → widget


class TestRightClickAuditAST:
    """Testes AST de auditoria de _on_tree_right_click — sem instanciar widget."""

    def test_has_early_return_when_no_item(self) -> None:
        """Guard: se identify_row retornar vazio, o método deve retornar cedo."""
        fn = _method_node("_on_tree_right_click")
        src = _source_of(fn)
        assert "identify_row" in src, "_on_tree_right_click deve usar identify_row para localizar a linha clicada"
        assert "return" in src, "_on_tree_right_click deve ter early-return quando não há linha"

    def test_conditionally_shows_restore_button(self) -> None:
        """O botão Restaurar só aparece quando _trash_mode é True."""
        fn = _method_node("_on_tree_right_click")
        src = _source_of(fn)
        assert "self._trash_mode" in src, "_on_tree_right_click deve condicionar o botão Restaurar a self._trash_mode"
        assert "Restaurar" in src, "O texto 'Restaurar' deve existir no método para aparecer no menu de lixeira"

    def test_delete_text_depends_on_trash_mode(self) -> None:
        """O texto do botão de exclusão muda com base em _trash_mode."""
        fn = _method_node("_on_tree_right_click")
        src = _source_of(fn)
        assert "Excluir definitivamente" in src, "Texto 'Excluir definitivamente' deve aparecer no menu em modo lixeira"
        assert "Enviar para Lixeira" in src, "Texto 'Enviar para Lixeira' deve aparecer no menu em modo normal"


_mock_log_right_click = logging.getLogger("test.right_click")

_right_click_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_tree_right_click",
    "_build_menu_btn",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": _mock_log_right_click,
        "Any": Any,
        # Substituição pesada de widgets por MagicMock
        "ctk": MagicMock(),
        "make_btn": MagicMock(return_value=MagicMock()),
        "SURFACE_DARK": "#1a1a1a",
        "BORDER": "#333333",
        "TEXT_PRIMARY": "#ffffff",
    },
)
_on_tree_right_click_fn = _right_click_fns["_on_tree_right_click"]
_build_menu_btn_fn = _right_click_fns["_build_menu_btn"]


def _make_right_click_fake(item_id: str, trash_mode: bool = False) -> MagicMock:
    """Stub de ClientesV2Frame para testes de _on_tree_right_click."""
    fake = MagicMock()
    fake.tree = MagicMock()
    fake.tree.identify_row.return_value = item_id
    fake._trash_mode = trash_mode
    fake._on_tree_select = MagicMock()
    fake._on_edit_client = MagicMock()
    fake._on_enviar_documentos = MagicMock()
    fake._on_delete_client = MagicMock()
    fake._on_restore_client = MagicMock()
    return fake


class TestRightClickBehavior:
    """Comportamento observável de _on_tree_right_click sem instanciar widget real."""

    def test_early_return_when_no_item(self) -> None:
        """Se identify_row retornar string vazia, o método deve retornar sem criar popup."""
        fake = _make_right_click_fake(item_id="")
        event = MagicMock(y=10, x_root=100, y_root=200)
        _on_tree_right_click_fn(fake, event)
        # Sem item → não deve selecionar nem chamar _on_tree_select
        fake.tree.selection_set.assert_not_called()
        fake._on_tree_select.assert_not_called()

    def test_selects_row_when_item_found(self) -> None:
        """Se identify_row retornar um item_id, a linha deve ser selecionada."""
        fake = _make_right_click_fake(item_id="I001")
        event = MagicMock(y=10, x_root=100, y_root=200)
        _on_tree_right_click_fn(fake, event)
        fake.tree.selection_set.assert_called_once_with("I001")
        fake.tree.focus.assert_called_once_with("I001")

    def test_on_tree_select_called_after_selection(self) -> None:
        """Após selecionar a linha, _on_tree_select deve ser invocado para atualizar estado."""
        fake = _make_right_click_fake(item_id="I002")
        event = MagicMock(y=20, x_root=50, y_root=80)
        _on_tree_right_click_fn(fake, event)
        fake._on_tree_select.assert_called_once()

    def test_exception_does_not_propagate(self) -> None:
        """Se identify_row lançar, o método deve capturar e não propagar exceção."""
        fake = MagicMock()
        fake.tree.identify_row.side_effect = RuntimeError("boom")
        event = MagicMock(y=0, x_root=0, y_root=0)
        _on_tree_right_click_fn(fake, event)  # não deve lançar


# ── SEÇÃO 20: _build_menu_btn — helper local de context menu (FASE 7B.19) ─────────


class TestBuildMenuBtnAST:
    """Testes AST que verificam o helper _build_menu_btn introduzido na FASE 7B.19."""

    def test_helper_method_exists_in_class(self) -> None:
        """_build_menu_btn deve existir como método de ClientesV2Frame."""
        node = _method_node("_build_menu_btn")
        assert node is not None, "_build_menu_btn não encontrado em ClientesV2Frame"

    def test_right_click_delegates_to_helper(self) -> None:
        """_on_tree_right_click deve usar _build_menu_btn para criar botões."""
        fn = _method_node("_on_tree_right_click")
        src = _source_of(fn)
        assert "_build_menu_btn" in src, "_on_tree_right_click deve delegar criação de botões a _build_menu_btn"

    def test_helper_encapsulates_fixed_kwargs(self) -> None:
        """_build_menu_btn deve conter os kwargs fixos que eram repetidos."""
        fn = _method_node("_build_menu_btn")
        src = _source_of(fn)
        assert "width=180" in src, "_build_menu_btn deve fixar width=180"
        assert "height=32" in src, "_build_menu_btn deve fixar height=32"
        assert 'fg_color="transparent"' in src, "_build_menu_btn deve fixar fg_color transparente"
        assert "hover_color=BORDER" in src, "_build_menu_btn deve usar BORDER como hover_color"
        assert "text_color=TEXT_PRIMARY" in src, "_build_menu_btn deve usar TEXT_PRIMARY como text_color"

    def test_obsolete_btn_variables_removed_from_right_click(self) -> None:
        """btn_width e btn_height não devem mais aparecer em _on_tree_right_click."""
        fn = _method_node("_on_tree_right_click")
        src = _source_of(fn)
        assert "btn_width" not in src, "btn_width (obsoleto) não deve existir em _on_tree_right_click"
        assert "btn_height" not in src, "btn_height (obsoleto) não deve existir em _on_tree_right_click"


class TestBuildMenuBtnBehavior:
    """Testes de comportamento de _build_menu_btn."""

    def test_returns_make_btn_result(self) -> None:
        """_build_menu_btn deve retornar o widget criado por make_btn (não None)."""
        fake = MagicMock()
        container = MagicMock()
        result = _build_menu_btn_fn(fake, container, "✏️ Editar", lambda: None)
        assert result is not None

    def test_text_is_forwarded_to_make_btn(self) -> None:
        """_build_menu_btn deve repassar o parâmetro text ao make_btn."""
        fn = _method_node("_build_menu_btn")
        src = _source_of(fn)
        assert "text=text" in src, "_build_menu_btn deve passar text=text para make_btn"

    def test_command_is_forwarded_to_make_btn(self) -> None:
        """_build_menu_btn deve repassar o parâmetro command ao make_btn."""
        fn = _method_node("_build_menu_btn")
        src = _source_of(fn)
        assert "command=command" in src, "_build_menu_btn deve passar command=command para make_btn"


# ── SEÇÃO 21: carregar — auditoria e proteção (FASE 7B.20) ──────────────────

_mock_log_carregar = logging.getLogger("test.carregar")

_carregar_fns = extract_functions_from_source(
    _VIEW_FILE,
    "carregar",
    class_name="ClientesV2Frame",
    extra_namespace={
        "Any": Any,
    },
)
_carregar_fn = _carregar_fns["carregar"]


def _make_carregar_fake(
    search: str = "João",
    order: str = "Nome ↑",
    status: str = "Ativo",
    trash_mode: bool = False,
) -> MagicMock:
    """Stub de ClientesV2Frame para testes de carregar."""
    fake = MagicMock()
    fake.toolbar = MagicMock()
    fake.toolbar.get_search_text.return_value = search
    fake.toolbar.get_order.return_value = order
    fake.toolbar.get_status.return_value = status
    fake._trash_mode = trash_mode
    fake.load_async = MagicMock()
    return fake


class TestCarregarAST:
    """Testes AST de carregar — verificações estruturais sem widget real."""

    def test_reads_search_from_toolbar(self) -> None:
        """carregar deve ler search via toolbar.get_search_text()."""
        fn = _method_node("carregar")
        src = _source_of(fn)
        assert "get_search_text" in src, "carregar deve ler search_text da toolbar"

    def test_reads_order_from_toolbar(self) -> None:
        """carregar deve ler order via toolbar.get_order()."""
        fn = _method_node("carregar")
        src = _source_of(fn)
        assert "get_order" in src, "carregar deve ler order da toolbar"

    def test_reads_status_from_toolbar(self) -> None:
        """carregar deve ler status via toolbar.get_status()."""
        fn = _method_node("carregar")
        src = _source_of(fn)
        assert "get_status" in src, "carregar deve ler status da toolbar"

    def test_delegates_to_load_async(self) -> None:
        """carregar deve delegar a execução para load_async."""
        fn = _method_node("carregar")
        src = _source_of(fn)
        assert "load_async" in src, "carregar deve chamar load_async"

    def test_passes_trash_mode_to_load_async(self) -> None:
        """carregar deve repassar self._trash_mode para load_async como show_trash."""
        fn = _method_node("carregar")
        src = _source_of(fn)
        assert "show_trash" in src, "carregar deve passar show_trash a load_async"
        assert "_trash_mode" in src, "carregar deve usar self._trash_mode como show_trash"


class TestCarregarBehavior:
    """Testes comportamentais de carregar — verificam a delegação correta a load_async."""

    def test_calls_load_async_with_toolbar_values(self) -> None:
        """carregar deve chamar load_async com os valores lidos da toolbar."""
        fake = _make_carregar_fake(search="Ana", order="Nome ↑", status="Ativo")
        _carregar_fn(fake)
        fake.load_async.assert_called_once_with(
            search="Ana",
            order_label="Nome ↑",
            status="Ativo",
            show_trash=False,
        )

    def test_respects_trash_mode_true(self) -> None:
        """Em modo lixeira, carregar deve passar show_trash=True a load_async."""
        fake = _make_carregar_fake(trash_mode=True)
        _carregar_fn(fake)
        _, kwargs = fake.load_async.call_args
        assert kwargs["show_trash"] is True

    def test_respects_trash_mode_false(self) -> None:
        """Em modo normal, carregar deve passar show_trash=False a load_async."""
        fake = _make_carregar_fake(trash_mode=False)
        _carregar_fn(fake)
        _, kwargs = fake.load_async.call_args
        assert kwargs["show_trash"] is False

    def test_toolbar_methods_called_once_each(self) -> None:
        """carregar deve consultar cada método da toolbar exatamente uma vez."""
        fake = _make_carregar_fake()
        _carregar_fn(fake)
        fake.toolbar.get_search_text.assert_called_once()
        fake.toolbar.get_order.assert_called_once()
        fake.toolbar.get_status.assert_called_once()


# ── SEÇÃO 21B: _build_load_controls — microextração de _build_ui ─────────────

_VIEW_BLC_PATH = Path(_VIEW_FILE)


class TestBuildLoadControlsAST:
    """_build_load_controls deve existir e conter os 4 atributos extraídos de _build_ui."""

    def _method_src(self) -> str:
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _build_load_controls(")
        assert start >= 0, "_build_load_controls não encontrado em view.py"
        end = src.find("\n    def ", start + 1)
        return src[start:end] if end > 0 else src[start:]

    def test_method_exists(self) -> None:
        """_build_load_controls deve existir em view.py."""
        self._method_src()  # levanta se não encontrado

    def test_creates_load_more_btn(self) -> None:
        """_build_load_controls deve criar self._load_more_btn."""
        src = self._method_src()
        assert "self._load_more_btn" in src, "_build_load_controls deve atribuir self._load_more_btn."

    def test_sets_load_more_visible_false(self) -> None:
        """_build_load_controls deve inicializar _load_more_visible como False."""
        src = self._method_src()
        assert (
            "self._load_more_visible = False" in src
        ), "_build_load_controls deve inicializar _load_more_visible = False."

    def test_creates_cap_hit_label(self) -> None:
        """_build_load_controls deve criar self._cap_hit_label."""
        src = self._method_src()
        assert "self._cap_hit_label" in src, "_build_load_controls deve atribuir self._cap_hit_label."

    def test_sets_cap_hit_label_visible_false(self) -> None:
        """_build_load_controls deve inicializar _cap_hit_label_visible como False."""
        src = self._method_src()
        assert (
            "self._cap_hit_label_visible = False" in src
        ), "_build_load_controls deve inicializar _cap_hit_label_visible = False."

    def test_build_ui_delegates_to_build_load_controls(self) -> None:
        """_build_ui deve chamar self._build_load_controls()."""
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _build_ui(")
        end = src.find("\n    def ", start + 1)
        body = src[start:end] if end > 0 else src[start:]
        assert "_build_load_controls" in body, (
            "_build_ui deve delegar para _build_load_controls(). "
            "Os controles de carga foram extraídos para esse método."
        )

    def test_build_ui_no_longer_contains_load_more_btn_literal(self) -> None:
        """_build_ui não deve mais conter a criação direta de _load_more_btn."""
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _build_ui(")
        end = src.find("\n    def ", start + 1)
        body = src[start:end] if end > 0 else src[start:]
        assert "make_btn" not in body, (
            "_build_ui ainda contém make_btn() diretamente. "
            "A criação de _load_more_btn deve estar em _build_load_controls."
        )


class TestBuildFooterBarAST:
    """_build_footer_bar deve existir e conter a lógica de rodapé extraída de _build_ui."""

    def _method_src(self) -> str:
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _build_footer_bar(")
        assert start >= 0, "_build_footer_bar não encontrado em view.py"
        end = src.find("\n    def ", start + 1)
        return src[start:end] if end > 0 else src[start:]

    def test_method_exists(self) -> None:
        """_build_footer_bar deve existir em view.py."""
        self._method_src()  # levanta se não encontrado

    def test_pick_mode_creates_pick_bar(self) -> None:
        """_build_footer_bar deve chamar _create_pick_bar no ramo pick_mode."""
        src = self._method_src()
        assert "_create_pick_bar" in src, "_build_footer_bar deve chamar _create_pick_bar para o modo ANVISA."

    def test_normal_mode_creates_action_bar(self) -> None:
        """_build_footer_bar deve instanciar ClientesV2ActionBar no ramo normal."""
        src = self._method_src()
        assert "ClientesV2ActionBar" in src, "_build_footer_bar deve criar ClientesV2ActionBar no modo normal."

    def test_normal_mode_packs_actionbar(self) -> None:
        """_build_footer_bar deve empacotar self.actionbar via pack()."""
        src = self._method_src()
        assert (
            "self.actionbar.pack(" in src
        ), "_build_footer_bar deve chamar self.actionbar.pack() para posicionar a ActionBar."

    def test_build_ui_delegates_to_build_footer_bar(self) -> None:
        """_build_ui deve chamar self._build_footer_bar()."""
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _build_ui(")
        end = src.find("\n    def ", start + 1)
        body = src[start:end] if end > 0 else src[start:]
        assert "_build_footer_bar" in body, (
            "_build_ui deve delegar para _build_footer_bar(). " "O rodapé foi extraído para esse método."
        )

    def test_build_ui_no_longer_contains_pick_mode_literal(self) -> None:
        """_build_ui não deve mais conter lógica de pick_mode diretamente."""
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _build_ui(")
        end = src.find("\n    def ", start + 1)
        body = src[start:end] if end > 0 else src[start:]
        assert "self._pick_mode" not in body, (
            "_build_ui ainda contém self._pick_mode diretamente. "
            "A lógica de pick_mode deve estar em _build_footer_bar."
        )


class TestSetupTreeviewBindingsAST:
    """_setup_treeview_bindings deve existir e conter todos os event handlers extraídos."""

    def _method_src(self) -> str:
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _setup_treeview_bindings(")
        assert start >= 0, "_setup_treeview_bindings não encontrado em view.py"
        end = src.find("\n    def ", start + 1)
        return src[start:end] if end > 0 else src[start:]

    def test_method_exists(self) -> None:
        """_setup_treeview_bindings deve existir em view.py."""
        self._method_src()  # levanta se não encontrado

    def test_binds_treeview_select(self) -> None:
        """_setup_treeview_bindings deve registrar <<TreeviewSelect>>."""
        src = self._method_src()
        assert (
            "<<TreeviewSelect>>" in src
        ), "_setup_treeview_bindings deve ligar <<TreeviewSelect>> ao handler de seleção."

    def test_binds_column_lock_on_button_press(self) -> None:
        """_setup_treeview_bindings deve travar colunas via <ButtonPress-1>."""
        src = self._method_src()
        assert (
            "<ButtonPress-1>" in src and "_on_column_lock" in src
        ), "_setup_treeview_bindings deve ligar <ButtonPress-1> a _on_column_lock."

    def test_binds_column_lock_on_motion(self) -> None:
        """_setup_treeview_bindings deve travar colunas via <B1-Motion>."""
        src = self._method_src()
        assert (
            "<B1-Motion>" in src
        ), "_setup_treeview_bindings deve ligar <B1-Motion> a _on_column_lock para bloquear drag."

    def test_pick_mode_binds_pick_confirm(self) -> None:
        """_setup_treeview_bindings deve ligar duplo clique a _on_pick_confirm no modo pick."""
        src = self._method_src()
        assert (
            "_on_pick_confirm" in src
        ), "_setup_treeview_bindings deve registrar _on_pick_confirm para duplo clique no modo ANVISA."

    def test_normal_mode_binds_double_click_editor(self) -> None:
        """_setup_treeview_bindings deve ligar duplo clique a _on_tree_double_click no modo normal."""
        src = self._method_src()
        assert (
            "_on_tree_double_click" in src
        ), "_setup_treeview_bindings deve registrar _on_tree_double_click para modo normal."

    def test_binds_configure_for_resize(self) -> None:
        """_setup_treeview_bindings deve ligar <Configure> a _resize_columns."""
        src = self._method_src()
        assert (
            "<Configure>" in src and "_resize_columns" in src
        ), "_setup_treeview_bindings deve ligar <Configure> a _resize_columns para layout responsivo."

    def test_schedules_initial_resize(self) -> None:
        """_setup_treeview_bindings deve agendar resize inicial via self.after(50, ...)."""
        src = self._method_src()
        assert (
            "self.after(50," in src
        ), "_setup_treeview_bindings deve agendar o resize inicial com self.after(50, ...)."

    def test_create_treeview_delegates_to_setup_bindings(self) -> None:
        """_create_treeview deve chamar self._setup_treeview_bindings()."""
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _create_treeview(")
        end = src.find("\n    def ", start + 1)
        body = src[start:end] if end > 0 else src[start:]
        assert "_setup_treeview_bindings" in body, (
            "_create_treeview deve delegar para _setup_treeview_bindings(). "
            "Os bindings foram extraídos para esse método."
        )

    def test_create_treeview_no_longer_contains_bind_treeview_select(self) -> None:
        """_create_treeview não deve mais conter <<TreeviewSelect>> diretamente."""
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _create_treeview(")
        end = src.find("\n    def ", start + 1)
        body = src[start:end] if end > 0 else src[start:]
        assert "<<TreeviewSelect>>" not in body, (
            "_create_treeview ainda contém <<TreeviewSelect>> diretamente. "
            "Os bindings devem estar em _setup_treeview_bindings."
        )


class TestSetupColumnSpecsAST:
    """_setup_column_specs deve existir e conter o bloco de specs extraído de _create_treeview."""

    def _method_src(self) -> str:
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _setup_column_specs(")
        assert start >= 0, "_setup_column_specs não encontrado em view.py"
        end = src.find("\n    def ", start + 1)
        return src[start:end] if end > 0 else src[start:]

    def test_method_exists(self) -> None:
        """_setup_column_specs deve existir em view.py."""
        self._method_src()  # levanta se não encontrado

    def test_calculates_ultima_alt_width(self) -> None:
        """_setup_column_specs deve chamar _calculate_ultima_alteracao_width."""
        src = self._method_src()
        assert "_calculate_ultima_alteracao_width" in src, (
            "_setup_column_specs deve chamar _calculate_ultima_alteracao_width "
            "para calcular a largura da coluna ultima_alteracao."
        )

    def test_assigns_column_specs(self) -> None:
        """_setup_column_specs deve atribuir self._column_specs."""
        src = self._method_src()
        assert "self._column_specs" in src, "_setup_column_specs deve montar e atribuir self._column_specs."

    def test_overrides_ultima_alteracao(self) -> None:
        """_setup_column_specs deve sobrescrever spec de ultima_alteracao com largura calculada."""
        src = self._method_src()
        assert '"ultima_alteracao"' in src, (
            "_setup_column_specs deve incluir entrada 'ultima_alteracao' " "com largura calculada ao vivo."
        )

    def test_calls_apply_columns_layout(self) -> None:
        """_setup_column_specs deve chamar _apply_columns_layout() ao final."""
        src = self._method_src()
        assert "_apply_columns_layout" in src, (
            "_setup_column_specs deve chamar _apply_columns_layout() " "para aplicar as specs ao Treeview."
        )

    def test_create_treeview_delegates_to_setup_column_specs(self) -> None:
        """_create_treeview deve chamar self._setup_column_specs()."""
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _create_treeview(")
        end = src.find("\n    def ", start + 1)
        body = src[start:end] if end > 0 else src[start:]
        assert "_setup_column_specs" in body, (
            "_create_treeview deve delegar para _setup_column_specs(). "
            "O bloco de specs foi extraído para esse método."
        )

    def test_create_treeview_no_longer_contains_column_specs_literal(self) -> None:
        """_create_treeview não deve mais conter self._column_specs = diretamente."""
        src = _VIEW_BLC_PATH.read_text(encoding="utf-8")
        start = src.find("def _create_treeview(")
        end = src.find("\n    def ", start + 1)
        body = src[start:end] if end > 0 else src[start:]
        assert "self._column_specs =" not in body, (
            "_create_treeview ainda atribui self._column_specs diretamente. "
            "A montagem das specs deve estar em _setup_column_specs."
        )


# ── SEÇÃO 22: _sync_load_more_btn — auditoria e proteção (FASE 7B.20) ───────

_sync_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_sync_load_more_btn",
    class_name="ClientesV2Frame",
    extra_namespace={
        "Any": Any,
    },
)
_sync_load_more_btn_fn = _sync_fns["_sync_load_more_btn"]


def _make_sync_fake(
    has_more: bool = False,
    fetch_all: bool = False,
    cap_hit: bool = False,
    load_more_visible: bool = False,
    cap_hit_label_visible: bool = False,
) -> MagicMock:
    """Stub de ClientesV2Frame para testes de _sync_load_more_btn."""
    fake = MagicMock()
    vm = MagicMock()
    vm.has_more = has_more
    vm._fetch_all = fetch_all
    vm.cap_hit = cap_hit
    fake._vm = vm
    fake._load_more_visible = load_more_visible
    fake._load_more_btn = MagicMock()
    fake._cap_hit_label_visible = cap_hit_label_visible
    fake._cap_hit_label = MagicMock()
    return fake


class TestSyncLoadMoreBtnAST:
    """Testes AST de _sync_load_more_btn."""

    def test_method_exists_in_class(self) -> None:
        """_sync_load_more_btn deve existir como método de ClientesV2Frame."""
        node = _method_node("_sync_load_more_btn")
        assert node is not None, "_sync_load_more_btn não encontrado em ClientesV2Frame"

    def test_reads_has_more_from_vm(self) -> None:
        """_sync_load_more_btn deve consultar _vm.has_more."""
        fn = _method_node("_sync_load_more_btn")
        src = _source_of(fn)
        assert "has_more" in src

    def test_reads_cap_hit_from_vm(self) -> None:
        """_sync_load_more_btn deve consultar cap_hit no _vm."""
        fn = _method_node("_sync_load_more_btn")
        src = _source_of(fn)
        assert "cap_hit" in src

    def test_exception_is_silenced(self) -> None:
        """_sync_load_more_btn deve silenciar exceções via try/except."""
        fn = _method_node("_sync_load_more_btn")
        src = _source_of(fn)
        assert "except" in src, "_sync_load_more_btn deve ter try/except para robustez"


class TestSyncLoadMoreBtnBehavior:
    """Testes comportamentais de _sync_load_more_btn."""

    def test_shows_load_more_btn_when_should_show_and_not_visible(self) -> None:
        """Deve chamar pack() e setar _load_more_visible=True quando should_show e não visível."""
        # has_more=True, fetch_all=False → should_show=True
        fake = _make_sync_fake(has_more=True, fetch_all=False, load_more_visible=False)
        _sync_load_more_btn_fn(fake)
        fake._load_more_btn.pack.assert_called_once()
        assert fake._load_more_visible is True

    def test_hides_load_more_btn_when_not_should_show_and_visible(self) -> None:
        """Deve chamar pack_forget() e setar _load_more_visible=False quando not should_show e visível."""
        fake = _make_sync_fake(has_more=False, fetch_all=False, load_more_visible=True)
        _sync_load_more_btn_fn(fake)
        fake._load_more_btn.pack_forget.assert_called_once()
        assert fake._load_more_visible is False

    def test_no_op_when_btn_already_hidden_and_should_not_show(self) -> None:
        """Não deve chamar pack nem pack_forget quando estado já está correto (oculto)."""
        fake = _make_sync_fake(has_more=False, load_more_visible=False)
        _sync_load_more_btn_fn(fake)
        fake._load_more_btn.pack.assert_not_called()
        fake._load_more_btn.pack_forget.assert_not_called()

    def test_shows_cap_hit_label_when_cap_and_not_visible(self) -> None:
        """Deve exibir label de cap-hit quando cap=True e ainda não visível."""
        fake = _make_sync_fake(cap_hit=True, has_more=True, cap_hit_label_visible=False)
        _sync_load_more_btn_fn(fake)
        fake._cap_hit_label.pack.assert_called_once()
        assert fake._cap_hit_label_visible is True

    def test_hides_cap_hit_label_when_no_cap_and_was_visible(self) -> None:
        """Deve ocultar label de cap-hit quando cap=False e estava visível."""
        fake = _make_sync_fake(cap_hit=False, cap_hit_label_visible=True)
        _sync_load_more_btn_fn(fake)
        fake._cap_hit_label.pack_forget.assert_called_once()
        assert fake._cap_hit_label_visible is False

    def test_exception_does_not_propagate(self) -> None:
        """Se _vm lançar exceção, _sync_load_more_btn não deve propagar."""
        fake = MagicMock()
        fake._vm.__bool__ = MagicMock(side_effect=RuntimeError("vm explodiu"))
        # Forçar AttributeError via _vm sem atributos
        del fake._vm.has_more
        _sync_load_more_btn_fn(fake)  # não deve lançar


# ── SEÇÃO 23: _on_load_more + _finish_load_more — proteção (FASE 7B.21) ─────

_mock_log_load_more = logging.getLogger("test.load_more")
_mock_threading = MagicMock()

_load_more_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_load_more",
    "_finish_load_more",
    class_name="ClientesV2Frame",
    extra_namespace={
        "threading": _mock_threading,
        "log": _mock_log_load_more,
        "Any": Any,
    },
)
_on_load_more_fn = _load_more_fns["_on_load_more"]
_finish_load_more_fn = _load_more_fns["_finish_load_more"]


def _make_on_load_more_fake() -> MagicMock:
    """Stub de ClientesV2Frame para testes de _on_load_more."""
    fake = MagicMock()
    fake._load_more_btn = MagicMock()
    fake._load_gen = 0
    fake.toolbar = MagicMock()
    fake.toolbar.get_search_text.return_value = ""
    fake.toolbar.get_status.return_value = ""
    fake.toolbar.get_order.return_value = ""
    fake._vm = MagicMock()
    return fake


def _make_finish_fake(
    gen: int = 0,
    load_gen: int = 0,
    had_new: bool = False,
) -> MagicMock:
    """Stub de ClientesV2Frame para testes de _finish_load_more."""
    fake = MagicMock()
    fake._load_gen = load_gen
    fake._load_more_btn = MagicMock()
    fake._render_rows = MagicMock()
    fake._sync_load_more_btn = MagicMock()
    fake._vm = MagicMock()
    fake._vm.get_rows.return_value = []
    return fake


class TestOnLoadMoreAST:
    """Testes AST de _on_load_more — verificações estruturais."""

    def test_method_exists_in_class(self) -> None:
        """_on_load_more deve existir como método de ClientesV2Frame."""
        node = _method_node("_on_load_more")
        assert node is not None

    def test_uses_threading(self) -> None:
        """_on_load_more deve disparar carga em background via Thread."""
        fn = _method_node("_on_load_more")
        src = _source_of(fn)
        assert "threading" in src or "Thread" in src, "_on_load_more deve usar threading.Thread para carga assíncrona"

    def test_increments_load_gen(self) -> None:
        """_on_load_more deve incrementar _load_gen (geração de carga)."""
        fn = _method_node("_on_load_more")
        src = _source_of(fn)
        assert "_load_gen" in src, "_on_load_more deve incrementar _load_gen"

    def test_disables_button(self) -> None:
        """_on_load_more deve desabilitar o botão imediatamente."""
        fn = _method_node("_on_load_more")
        src = _source_of(fn)
        assert "disabled" in src, "_on_load_more deve setar state='disabled' no botão"

    def test_finish_load_more_is_scheduled(self) -> None:
        """_on_load_more deve agendar _finish_load_more na main thread via after()."""
        fn = _method_node("_on_load_more")
        src = _source_of(fn)
        assert "_finish_load_more" in src, "_on_load_more deve agendar _finish_load_more via self.after()"

    def test_finish_load_more_has_gen_guard(self) -> None:
        """_finish_load_more deve ter guarda de geração para descartar resultados obsoletos."""
        fn = _method_node("_finish_load_more")
        src = _source_of(fn)
        assert "_load_gen" in src, "_finish_load_more deve comparar gen com _load_gen"


class TestOnLoadMoreBehavior:
    """Testes comportamentais de _on_load_more — efeitos imediatos antes do thread."""

    def test_button_disabled_before_thread(self) -> None:
        """O botão deve ser desabilitado com 'Carregando…' antes de iniciar o thread."""
        fake = _make_on_load_more_fake()
        _on_load_more_fn(fake)
        fake._load_more_btn.configure.assert_called_once_with(state="disabled", text="Carregando…")

    def test_load_gen_incremented(self) -> None:
        """_load_gen deve ser incrementado em 1 ao chamar _on_load_more."""
        fake = _make_on_load_more_fake()
        fake._load_gen = 3
        _on_load_more_fn(fake)
        assert fake._load_gen == 4

    def test_thread_is_started(self) -> None:
        """Um thread deve ser iniciado após desabilitar o botão."""
        fake = _make_on_load_more_fake()
        _on_load_more_fn(fake)
        # threading está mockado; Thread() retorna MagicMock — .start() deve ter sido chamado
        _mock_threading.Thread.return_value.start.assert_called()


class TestFinishLoadMoreBehavior:
    """Testes comportamentais de _finish_load_more — callback na main thread."""

    def test_stale_gen_skips_render(self) -> None:
        """Geração obsoleta (gen != _load_gen) deve retornar sem chamar _render_rows."""
        fake = _make_finish_fake(gen=1, load_gen=5)
        _finish_load_more_fn(fake, gen=1, had_new=False)
        fake._render_rows.assert_not_called()

    def test_current_gen_calls_render_rows(self) -> None:
        """Geração atual deve acionar _render_rows."""
        fake = _make_finish_fake(gen=2, load_gen=2)
        _finish_load_more_fn(fake, gen=2, had_new=False)
        fake._render_rows.assert_called_once()

    def test_current_gen_re_enables_button(self) -> None:
        """_finish_load_more deve reativar o botão com texto 'Carregar mais…'."""
        fake = _make_finish_fake(gen=0, load_gen=0)
        _finish_load_more_fn(fake, gen=0, had_new=False)
        fake._load_more_btn.configure.assert_called_once_with(state="normal", text="Carregar mais…")

    def test_current_gen_syncs_btn(self) -> None:
        """_finish_load_more deve chamar _sync_load_more_btn para atualizar visibilidade."""
        fake = _make_finish_fake(gen=0, load_gen=0)
        _finish_load_more_fn(fake, gen=0, had_new=False)
        fake._sync_load_more_btn.assert_called_once()

    def test_stale_gen_skips_button_update(self) -> None:
        """Geração obsoleta não deve atualizar o botão."""
        fake = _make_finish_fake(gen=1, load_gen=9)
        _finish_load_more_fn(fake, gen=1, had_new=True)
        fake._load_more_btn.configure.assert_not_called()


# ── SEÇÃO 24: _on_edit_client + _on_new_client — proteção (FASE 7B.22) ──────

_edit_client_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_edit_client",
    "_on_new_client",
    class_name="ClientesV2Frame",
    extra_namespace={"Any": Any},
)
_on_edit_client_fn = _edit_client_fns["_on_edit_client"]
_on_new_client_fn = _edit_client_fns["_on_new_client"]


class TestOnEditClientAST:
    """Testes AST de _on_edit_client."""

    def test_delegates_to_open_client_editor(self) -> None:
        """_on_edit_client deve delegar para _open_client_editor."""
        fn = _method_node("_on_edit_client")
        src = _source_of(fn)
        assert "_open_client_editor" in src

    def test_passes_source_button_without_event(self) -> None:
        """Sem event, source deve ser 'button'."""
        fn = _method_node("_on_edit_client")
        src = _source_of(fn)
        assert '"button"' in src or "'button'" in src

    def test_passes_source_shortcut_with_event(self) -> None:
        """Com event, source deve ser 'shortcut'."""
        fn = _method_node("_on_edit_client")
        src = _source_of(fn)
        assert '"shortcut"' in src or "'shortcut'" in src

    def test_returns_break_when_event_provided(self) -> None:
        """Com event, deve retornar 'break'."""
        fn = _method_node("_on_edit_client")
        src = _source_of(fn)
        assert '"break"' in src or "'break'" in src


class TestOnEditClientBehavior:
    """Comportamento de _on_edit_client."""

    def test_without_event_calls_open_editor_with_button_source(self) -> None:
        """Sem event, deve chamar _open_client_editor(source='button')."""
        fake = MagicMock()
        _on_edit_client_fn(fake, event=None)
        fake._open_client_editor.assert_called_once_with(source="button")

    def test_without_event_returns_none(self) -> None:
        """Sem event, deve retornar None."""
        fake = MagicMock()
        result = _on_edit_client_fn(fake, event=None)
        assert result is None

    def test_with_event_calls_open_editor_with_shortcut_source(self) -> None:
        """Com event, deve chamar _open_client_editor(source='shortcut')."""
        fake = MagicMock()
        event = MagicMock()
        _on_edit_client_fn(fake, event=event)
        fake._open_client_editor.assert_called_once_with(source="shortcut")

    def test_with_event_returns_break(self) -> None:
        """Com event, deve retornar 'break'."""
        fake = MagicMock()
        result = _on_edit_client_fn(fake, event=MagicMock())
        assert result == "break"

    def test_open_client_editor_called_exactly_once(self) -> None:
        """_open_client_editor deve ser chamado exatamente uma vez."""
        fake = MagicMock()
        _on_edit_client_fn(fake, event=None)
        assert fake._open_client_editor.call_count == 1


class TestOnNewClientAST:
    """Testes AST de _on_new_client."""

    def test_delegates_to_open_client_editor_with_new_client_true(self) -> None:
        """_on_new_client deve chamar _open_client_editor(new_client=True)."""
        fn = _method_node("_on_new_client")
        src = _source_of(fn)
        assert "new_client=True" in src

    def test_returns_break_with_event(self) -> None:
        """Com event, deve retornar 'break'."""
        fn = _method_node("_on_new_client")
        src = _source_of(fn)
        assert '"break"' in src or "'break'" in src


class TestOnNewClientBehavior:
    """Comportamento de _on_new_client."""

    def test_without_event_calls_open_editor_new_client(self) -> None:
        """Sem event, deve chamar _open_client_editor(source='new', new_client=True)."""
        fake = MagicMock()
        _on_new_client_fn(fake, event=None)
        fake._open_client_editor.assert_called_once_with(source="new", new_client=True)

    def test_without_event_returns_none(self) -> None:
        """Sem event, retorna None."""
        fake = MagicMock()
        result = _on_new_client_fn(fake, event=None)
        assert result is None

    def test_with_event_returns_break(self) -> None:
        """Com event, retorna 'break'."""
        fake = MagicMock()
        result = _on_new_client_fn(fake, event=MagicMock())
        assert result == "break"


# ── SEÇÃO 25: _open_client_editor guards — proteção comportamental (FASE 7B.22)


class TestOpenClientEditorAST:
    """Testes AST adicionais de _open_client_editor."""

    def test_clears_stale_dialog_reference(self) -> None:
        """Referência obsoleta ao dialog deve ser limpa (atribuir None)."""
        fn = _method_node("_open_client_editor")
        src = _source_of(fn)
        assert "self._editor_dialog = None" in src, "_open_client_editor deve limpar referência obsoleta ao dialog"

    def test_validates_app_before_creating_dialog(self) -> None:
        """Deve verificar self.app antes de criar o diálogo."""
        fn = _method_node("_open_client_editor")
        src = _source_of(fn)
        assert "self.app" in src, "_open_client_editor deve verificar self.app"

    def test_validates_selection_for_edit_mode(self) -> None:
        """Deve verificar _selected_client_id quando não é novo cliente."""
        fn = _method_node("_open_client_editor")
        src = _source_of(fn)
        assert "self._selected_client_id" in src

    def test_resets_opening_editor_flag_on_exception(self) -> None:
        """_opening_editor deve ser resetado em caso de exceção."""
        fn = _method_node("_open_client_editor")
        src = _source_of(fn)
        # Flag deve ser resetada no bloco except
        assert "self._opening_editor = False" in src

    def test_on_saved_callback_calls_load_async(self) -> None:
        """O callback on_saved deve acionar load_async para recarregar a lista."""
        fn = _method_node("_open_client_editor")
        src = _source_of(fn)
        assert "load_async" in src, "on_saved callback deve chamar load_async"

    def test_on_closed_callback_clears_dialog_and_flag(self) -> None:
        """O callback on_closed deve limpar _editor_dialog e _opening_editor."""
        fn = _method_node("_open_client_editor")
        src = _source_of(fn)
        assert "on_closed" in src or "_opening_editor = False" in src


_mock_editor_ns = {
    "Any": Any,
    "log": logging.getLogger("test.open_client_editor"),
    "uuid": MagicMock(uuid4=lambda: type("U", (), {"__str__": lambda s: "abcdef12"})()),
}

_open_editor_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_open_client_editor",
    class_name="ClientesV2Frame",
    extra_namespace=_mock_editor_ns,
)
_open_client_editor_fn = _open_editor_fns["_open_client_editor"]


def _make_open_editor_fake(
    opening_editor: bool = False,
    editor_dialog_live: bool = False,
    has_app: bool = True,
    selected_client_id: int | None = 1,
) -> MagicMock:
    """Stub para _open_client_editor."""
    fake = MagicMock()
    fake._opening_editor = opening_editor
    fake._editor_dialog = MagicMock() if editor_dialog_live else None
    fake.app = MagicMock() if has_app else None
    fake._selected_client_id = selected_client_id
    return fake


class TestOpenClientEditorGuardBehavior:
    """Testes comportamentais dos guards de _open_client_editor."""

    def setup_method(self) -> None:
        _mock_show_error_editor.reset_mock()
        _mock_show_warning_editor.reset_mock()

    def test_guard1_returns_immediately_when_opening_editor(self) -> None:
        """Se _opening_editor=True, deve retornar sem criar dialog."""
        fake = _make_open_editor_fake(opening_editor=True)
        _open_client_editor_fn(fake)
        # Não deve ter tentado criar dialog nem modificado _editor_dialog
        fake.winfo_toplevel.assert_not_called()

    def test_guard1_does_not_call_load_async_on_reentrance(self) -> None:
        """Se _opening_editor=True, load_async não deve ser invocado."""
        fake = _make_open_editor_fake(opening_editor=True)
        _open_client_editor_fn(fake)
        fake.load_async.assert_not_called()

    def test_stale_dialog_ref_cleared_and_creation_proceeds(self) -> None:
        """Guard 2b: referência obsoleta é zerada e criação de novo dialog prossegue."""
        stale = MagicMock()
        stale.winfo_exists.return_value = False  # dialog morto
        fake = _make_editor_fake(client_id=5, editor_dialog=stale)
        mock_new_dialog = MagicMock()
        with _patch_editor_dialog(MagicMock(return_value=mock_new_dialog)):
            _open_client_editor(fake)
        # Novo dialog foi atribuído (referência obsoleta foi sobrescrita)
        assert fake._editor_dialog is mock_new_dialog

    def test_no_app_shows_error_and_does_not_create_dialog(self) -> None:
        """app=None: mostra show_error e retorna sem instanciar ClientEditorDialog."""
        fake = _make_editor_fake(has_app=False, client_id=42)
        stub = MagicMock()
        with _patch_editor_dialog(stub):
            _open_client_editor(fake)
        stub.assert_not_called()
        _mock_show_error_editor.assert_called()

    def test_exception_during_creation_resets_opening_editor_flag(self) -> None:
        """Exceção na criação do dialog: _opening_editor deve ser False ao sair."""
        fake = _make_editor_fake(client_id=42)
        with _patch_editor_dialog(MagicMock(side_effect=RuntimeError("CTk unavailable"))):
            _open_client_editor(fake)
        assert fake._opening_editor is False

    def test_exception_during_creation_clears_editor_dialog(self) -> None:
        """Exceção na criação do dialog: _editor_dialog deve ser None ao sair."""
        fake = _make_editor_fake(client_id=42)
        with _patch_editor_dialog(MagicMock(side_effect=RuntimeError("CTk unavailable"))):
            _open_client_editor(fake)
        assert fake._editor_dialog is None

    def test_on_save_callback_triggers_load_async(self) -> None:
        """Invocar on_save (closure passada ao dialog) deve chamar load_async."""
        fake = _make_editor_fake(client_id=10)
        stub_cls = MagicMock(return_value=MagicMock())
        with _patch_editor_dialog(stub_cls):
            _open_client_editor(fake)
        on_save = stub_cls.call_args.kwargs["on_save"]
        on_save({"data": "qualquer"})
        fake.load_async.assert_called()

    def test_on_close_callback_clears_dialog_and_resets_flag(self) -> None:
        """Invocar on_close (closure passada ao dialog) deve zerar _editor_dialog e _opening_editor."""
        fake = _make_editor_fake(client_id=10)
        stub_cls = MagicMock(return_value=MagicMock())
        with _patch_editor_dialog(stub_cls):
            _open_client_editor(fake)
        on_close = stub_cls.call_args.kwargs["on_close"]
        # Simular estado "durante abertura"
        fake._opening_editor = True
        fake._editor_dialog = MagicMock()
        on_close()
        assert fake._editor_dialog is None
        assert fake._opening_editor is False


# ── SEÇÃO 25B: _deselect_and_reload — microextração (comum a delete/restore) ─

_VIEW_DESELECT_PATH = Path(_VIEW_FILE)


class TestDeselectAndReloadAST:
    """_deselect_and_reload deve existir e conter a lógica extraída dos closures."""

    def _method_src(self) -> str:
        src = _VIEW_DESELECT_PATH.read_text(encoding="utf-8")
        start = src.find("def _deselect_and_reload(")
        assert start >= 0, "_deselect_and_reload não encontrado em view.py"
        end = src.find("\n    def ", start + 1)
        return src[start:end] if end > 0 else src[start:]

    def test_method_exists(self) -> None:
        """_deselect_and_reload deve existir em view.py."""
        self._method_src()  # levanta AssertionError se não encontrado

    def test_clears_selected_client_id(self) -> None:
        """_deselect_and_reload deve zerar _selected_client_id."""
        src = self._method_src()
        assert (
            "self._selected_client_id = None" in src
        ), "_deselect_and_reload deve atribuir None a _selected_client_id."

    def test_calls_carregar(self) -> None:
        """_deselect_and_reload deve chamar self.carregar()."""
        src = self._method_src()
        assert "self.carregar()" in src, "_deselect_and_reload deve chamar carregar() para recarregar a lista."


class TestDeselectAndReloadBehavior:
    """_deselect_and_reload deve limpar seleção e chamar carregar()."""

    def test_clears_selection(self) -> None:
        fake = MagicMock()
        fake._selected_client_id = 42
        # Extrair e executar o método diretamente
        fn = _method_node("_deselect_and_reload")
        src = _source_of(fn)
        exec(compile(f"def _run(self): {src.split(':', 1)[1]}", "<test>", "exec"), {"self": fake})
        # Rota mais simples: chamar o método extraído por reflexão via exec do source
        # A forma mais confiável em testes de comportamento headless é usar extract_functions_from_source
        _fns = extract_functions_from_source(
            _VIEW_FILE,
            "_deselect_and_reload",
            class_name="ClientesV2Frame",
            extra_namespace={"log": logging.getLogger("test.deselect"), "Any": Any},
        )
        _fn = _fns["_deselect_and_reload"]
        fake2 = MagicMock()
        fake2._selected_client_id = 77
        _fn(fake2)
        assert fake2._selected_client_id is None

    def test_calls_carregar_once(self) -> None:
        _fns = extract_functions_from_source(
            _VIEW_FILE,
            "_deselect_and_reload",
            class_name="ClientesV2Frame",
            extra_namespace={"log": logging.getLogger("test.deselect"), "Any": Any},
        )
        _fn = _fns["_deselect_and_reload"]
        fake = MagicMock()
        _fn(fake)
        fake.carregar.assert_called_once()


# ── SEÇÃO 26: _on_delete_client — cobertura complementar (FASE 7B.23) ───────


class TestOnDeleteClientAST:
    """Testes AST adicionais de _on_delete_client — invariantes estruturais."""

    def test_returns_break_conditional_in_source(self) -> None:
        """_on_delete_client deve retornar 'break' condicionalmente com event."""
        fn = _method_node("_on_delete_client")
        src = _source_of(fn)
        assert '"break"' in src or "'break'" in src, "_on_delete_client deve retornar 'break' quando event é fornecido"

    def test_delegates_on_success_to_deselect_and_reload(self) -> None:
        """_on_delete_client deve passar _deselect_and_reload como on_success."""
        fn = _method_node("_on_delete_client")
        src = _source_of(fn)
        assert "_deselect_and_reload" in src, (
            "_on_delete_client deve referenciar _deselect_and_reload. "
            "O closure _on_success foi extraído para um método de classe."
        )

    def test_clears_stale_editor_dialog_in_source(self) -> None:
        """_on_delete_client deve limpar referência obsoleta ao editor dialog."""
        fn = _method_node("_on_delete_client")
        src = _source_of(fn)
        assert "self._editor_dialog = None" in src, "_on_delete_client deve atribuir None ao _editor_dialog obsoleto"


class TestOnDeleteClientReturnValues:
    """Testes dos valores de retorno de _on_delete_client ('break' vs None)."""

    def test_returns_break_with_event_when_no_selection(self) -> None:
        """Com event e sem seleção, deve retornar 'break' no guard 1."""
        fake = _make_delete_fake(client_id=0)
        fake._selected_client_id = None
        result = _on_delete_client(fake, event=MagicMock())
        assert result == "break"

    def test_returns_none_without_event_when_no_selection(self) -> None:
        """Sem event e sem seleção, deve retornar None no guard 1."""
        fake = _make_delete_fake(client_id=0)
        fake._selected_client_id = None
        result = _on_delete_client(fake, event=None)
        assert result is None

    def test_returns_break_with_event_after_soft_delete(self) -> None:
        """Com event e após soft delete confirmado, deve retornar 'break'."""
        fake = _make_delete_fake(client_id=42, trash_mode=False)
        svc = _make_service_mock()
        _mock_ask_yes_no.reset_mock()
        _mock_ask_yes_no.return_value = True
        with _patch_service(svc):
            result = _on_delete_client(fake, event=MagicMock())
        assert result == "break"

    def test_returns_none_without_event_after_soft_delete(self) -> None:
        """Sem event e após soft delete confirmado, deve retornar None."""
        fake = _make_delete_fake(client_id=42, trash_mode=False)
        svc = _make_service_mock()
        _mock_ask_yes_no.reset_mock()
        _mock_ask_yes_no.return_value = True
        with _patch_service(svc):
            result = _on_delete_client(fake, event=None)
        assert result is None


class TestOnDeleteClientSuccessCallback:
    """Testes do callback de sucesso em _on_delete_client."""

    def setup_method(self) -> None:
        _mock_ask_yes_no.reset_mock()
        _mock_ask_yes_no.return_value = True
        _mock_ask_yes_no_danger.reset_mock()
        _mock_ask_yes_no_danger.return_value = True
        _mock_show_info.reset_mock()
        _mock_show_error_del.reset_mock()

    def test_success_calls_deselect_and_reload(self) -> None:
        """Após soft delete bem-sucedido, _deselect_and_reload deve ser chamado uma vez."""
        fake = _make_delete_fake(client_id=42, trash_mode=False)
        svc = _make_service_mock()
        with _patch_service(svc):
            _on_delete_client(fake)
        fake._deselect_and_reload.assert_called_once()


class TestOnDeleteClientStaleDialog:
    """Testa a limpeza da referência obsoleta ao _editor_dialog em _on_delete_client."""

    def setup_method(self) -> None:
        _mock_ask_yes_no.reset_mock()
        _mock_ask_yes_no.return_value = True
        _mock_show_info.reset_mock()
        _mock_show_error_del.reset_mock()

    def test_stale_dialog_cleared_when_not_live(self) -> None:
        """Referência a dialog não-vivo deve ser zerada antes de prosseguir com o delete."""
        stale_dialog = MagicMock()
        stale_dialog.winfo_exists.return_value = False
        fake = _make_delete_fake(client_id=42, trash_mode=False, editor_dialog=stale_dialog)
        svc = _make_service_mock()
        with _patch_service(svc):
            _on_delete_client(fake)
        assert fake._editor_dialog is None


class TestOnDeleteClientEditorLiveGuard:
    """Testa o Guard 2: editor vivo bloqueia _on_delete_client e retorno correto."""

    def setup_method(self) -> None:
        _mock_ask_yes_no.reset_mock()
        _mock_ask_yes_no_danger.reset_mock()
        _mock_show_info.reset_mock()
        _mock_show_error_del.reset_mock()

    def _live_dialog(self) -> MagicMock:
        d = MagicMock()
        d.winfo_exists.return_value = True
        return d

    def test_editor_alive_with_event_returns_break(self) -> None:
        """Guard 2: editor vivo + event deve retornar 'break' imediatamente."""
        fake = _make_delete_fake(client_id=42, trash_mode=False, editor_dialog=self._live_dialog())
        svc = _make_service_mock()
        with _patch_service(svc):
            result = _on_delete_client(fake, event=MagicMock())
        assert result == "break"

    def test_editor_alive_without_event_returns_none(self) -> None:
        """Guard 2: editor vivo sem event deve retornar None imediatamente."""
        fake = _make_delete_fake(client_id=42, trash_mode=False, editor_dialog=self._live_dialog())
        svc = _make_service_mock()
        with _patch_service(svc):
            result = _on_delete_client(fake, event=None)
        assert result is None


class TestOnDeleteClientHardDeleteSuccess:
    """Testa o callback de sucesso no caminho de hard delete (trash_mode=True)."""

    def setup_method(self) -> None:
        _mock_ask_yes_no_danger.reset_mock()
        _mock_ask_yes_no_danger.return_value = True
        _mock_show_info.reset_mock()
        _mock_show_error_del.reset_mock()

    def test_hard_delete_success_calls_deselect_and_reload(self) -> None:
        """Após hard delete bem-sucedido, _deselect_and_reload deve ser chamado uma vez."""
        fake = _make_delete_fake(client_id=77, trash_mode=True)
        svc = _make_service_mock(hard_delete_result=(True, []))
        with _patch_service(svc):
            _on_delete_client(fake)
        fake._deselect_and_reload.assert_called_once()


# ── SEÇÃO 27: _on_restore_client — cobertura complementar (FASE 7B.24) ──────


class TestOnRestoreClientAST:
    """Testes AST de _on_restore_client — invariantes estruturais."""

    def test_guard_requires_selected_client_id(self) -> None:
        """_on_restore_client deve verificar _selected_client_id no guard inicial."""
        fn = _method_node("_on_restore_client")
        src = _source_of(fn)
        assert (
            "self._selected_client_id" in src
        ), "_on_restore_client deve checar _selected_client_id para evitar restore sem seleção"

    def test_guard_requires_trash_mode(self) -> None:
        """_on_restore_client deve verificar _trash_mode no guard inicial."""
        fn = _method_node("_on_restore_client")
        src = _source_of(fn)
        assert (
            "self._trash_mode" in src
        ), "_on_restore_client deve checar _trash_mode — restaurar só faz sentido na lixeira"

    def test_delegates_on_success_to_deselect_and_reload(self) -> None:
        """_on_restore_client deve passar _deselect_and_reload como on_success."""
        fn = _method_node("_on_restore_client")
        src = _source_of(fn)
        assert "_deselect_and_reload" in src, (
            "_on_restore_client deve referenciar _deselect_and_reload. "
            "O closure _on_success foi extraído para um método de classe."
        )

    def test_delegates_to_execute_restore_with_client_id(self) -> None:
        """_on_restore_client deve passar client_id para execute_restore."""
        fn = _method_node("_on_restore_client")
        src = _source_of(fn)
        assert "client_id=" in src, "_on_restore_client deve chamar execute_restore com client_id="


class TestOnRestoreClientSuccessCallback:
    """Testes comportamentais do callback de sucesso de _on_restore_client."""

    def setup_method(self) -> None:
        _mock_ask_yes_no_restore.reset_mock()
        _mock_ask_yes_no_restore.return_value = True
        _mock_show_info_restore.reset_mock()
        _mock_show_error_restore.reset_mock()

    def test_success_calls_deselect_and_reload(self) -> None:
        """Após restauração bem-sucedida, _deselect_and_reload deve ser chamado uma vez."""
        fake = _make_restore_fake(client_id=42, trash_mode=True)
        svc = _make_restore_service_mock()

        with _patch_service(svc):
            _on_restore_client(fake)

        fake._deselect_and_reload.assert_called_once()

    def test_cancelled_does_not_call_deselect_and_reload(self) -> None:
        """Se usuário cancelar, _deselect_and_reload não deve ser chamado."""
        fake = _make_restore_fake(client_id=42, trash_mode=True)
        svc = _make_restore_service_mock()
        _mock_ask_yes_no_restore.return_value = False

        with _patch_service(svc):
            _on_restore_client(fake)

        fake._deselect_and_reload.assert_not_called()

    def test_service_error_does_not_call_deselect_and_reload(self) -> None:
        """Se o serviço lançar excessão, _deselect_and_reload não deve ser chamado."""
        fake = _make_restore_fake(client_id=99, trash_mode=True)
        svc = _make_restore_service_mock()
        svc.restaurar_clientes_da_lixeira.side_effect = RuntimeError("DB offline")

        with _patch_service(svc):
            _on_restore_client(fake)

        fake._deselect_and_reload.assert_not_called()


# ── SEÇÃO 28: _on_enviar_documentos — cobertura (FASE 7B.25) ─────────────────

_mock_log_enviar = logging.getLogger("test.enviar_doc")
_mock_show_warning_enviar = MagicMock()

_enviar_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_on_enviar_documentos",
    class_name="ClientesV2Frame",
    extra_namespace={
        "log": _mock_log_enviar,
        "_show_warning": _mock_show_warning_enviar,
        "Any": Any,
    },
)
_on_enviar_documentos_fn = _enviar_fns["_on_enviar_documentos"]


def _make_enviar_fake(client_id: int | None = 42) -> MagicMock:
    """Stub de ClientesV2Frame para testes de _on_enviar_documentos."""
    fake = MagicMock()
    fake._selected_client_id = client_id
    fake.winfo_toplevel.return_value = MagicMock()
    return fake


@contextmanager
def _patch_client_editor_dialog(raise_on_init: bool = False):
    """Injeta mock de ClientEditorDialog em sys.modules para testes headless."""
    _key = "src.modules.clientes.ui.views.client_editor_dialog"
    _old = sys.modules.get(_key)

    mock_dialog_instance = MagicMock()
    if raise_on_init:
        mock_dialog_class = MagicMock(side_effect=RuntimeError("CTk indisponível"))
    else:
        mock_dialog_class = MagicMock(return_value=mock_dialog_instance)

    stub_module = types.ModuleType(_key)
    setattr(stub_module, "ClientEditorDialog", mock_dialog_class)
    sys.modules[_key] = stub_module

    try:
        yield mock_dialog_class, mock_dialog_instance
    finally:
        if _old is None:
            sys.modules.pop(_key, None)
        else:
            sys.modules[_key] = _old


class TestEnviarDocumentosAST:
    """Testes AST de _on_enviar_documentos — invariantes estruturais."""

    def test_guard_requires_selected_client_id(self) -> None:
        """_on_enviar_documentos deve verificar _selected_client_id no guard inicial."""
        fn = _method_node("_on_enviar_documentos")
        src = _source_of(fn)
        assert (
            "self._selected_client_id" in src
        ), "_on_enviar_documentos deve checar _selected_client_id antes de abrir o diálogo"

    def test_guard_calls_show_warning_on_no_selection(self) -> None:
        """Sem seleção, _on_enviar_documentos deve chamar _show_warning."""
        fn = _method_node("_on_enviar_documentos")
        src = _source_of(fn)
        assert "_show_warning" in src, "_on_enviar_documentos deve avisar o usuário quando não há cliente selecionado"

    def test_delegates_trigger_dialog_upload(self) -> None:
        """_on_enviar_documentos deve agendar trigger_dialog_upload via dialog.after()."""
        fn = _method_node("_on_enviar_documentos")
        src = _source_of(fn)
        assert "trigger_dialog_upload" in src, "_on_enviar_documentos deve usar trigger_dialog_upload de actions.py"

    def test_on_saved_calls_load_async(self) -> None:
        """_on_enviar_documentos deve chamar load_async() no callback on_saved."""
        fn = _method_node("_on_enviar_documentos")
        src = _source_of(fn)
        assert "load_async" in src, "on_saved em _on_enviar_documentos deve chamar load_async() para recarregar a lista"

    def test_exception_is_caught_by_try_except(self) -> None:
        """_on_enviar_documentos deve ter try/except para silenciar falhas de criação do dialog."""
        fn = _method_node("_on_enviar_documentos")
        src = _source_of(fn)
        assert "except" in src, "_on_enviar_documentos deve ter try/except para não propagar erro de CTk"

    def test_schedules_after_200ms(self) -> None:
        """_on_enviar_documentos deve agendar trigger via dialog.after(200, ...)."""
        fn = _method_node("_on_enviar_documentos")
        src = _source_of(fn)
        assert "after(200" in src, "_on_enviar_documentos deve usar .after(200, ...) para agendar o trigger de upload"


class TestEnviarDocumentosBehavior:
    """Testes comportamentais de _on_enviar_documentos — sem display real."""

    def setup_method(self) -> None:
        _mock_show_warning_enviar.reset_mock()

    def test_no_selection_calls_show_warning(self) -> None:
        """Sem cliente selecionado, _show_warning deve ser chamado exatamente uma vez."""
        fake = _make_enviar_fake(client_id=None)
        _on_enviar_documentos_fn(fake)
        _mock_show_warning_enviar.assert_called_once()

    def test_no_selection_does_not_create_dialog(self) -> None:
        """Sem seleção, ClientEditorDialog não deve ser instanciado."""
        fake = _make_enviar_fake(client_id=None)
        with _patch_client_editor_dialog() as (mock_dialog_class, _):
            _on_enviar_documentos_fn(fake)
        mock_dialog_class.assert_not_called()

    def test_with_selection_creates_dialog_with_correct_client_id(self) -> None:
        """Com seleção válida, ClientEditorDialog deve ser criado com o client_id correto."""
        fake = _make_enviar_fake(client_id=42)
        with _patch_client_editor_dialog() as (mock_dialog_class, _):
            _on_enviar_documentos_fn(fake)
        mock_dialog_class.assert_called_once()
        _, kwargs = mock_dialog_class.call_args
        assert kwargs["client_id"] == 42, "ClientEditorDialog deve ser criado com o client_id do cliente selecionado"

    def test_with_selection_schedules_after_200ms(self) -> None:
        """Com seleção válida, dialog.after(200, ...) deve ser agendado."""
        fake = _make_enviar_fake(client_id=42)
        with _patch_client_editor_dialog() as (_, mock_dialog_inst):
            _on_enviar_documentos_fn(fake)
        mock_dialog_inst.after.assert_called_once()
        delay = mock_dialog_inst.after.call_args[0][0]
        assert delay == 200, "O delay do after() deve ser 200ms"

    def test_on_saved_callback_calls_load_async(self) -> None:
        """O callback on_saved passado ao dialog deve chamar load_async() da view."""
        fake = _make_enviar_fake(client_id=42)
        with _patch_client_editor_dialog() as (mock_dialog_class, _):
            _on_enviar_documentos_fn(fake)
        _, kwargs = mock_dialog_class.call_args
        on_save_cb = kwargs["on_save"]
        fake.load_async.reset_mock()
        on_save_cb({"id": 42, "nome": "Teste"})
        fake.load_async.assert_called_once()

    def test_exception_in_dialog_creation_does_not_propagate(self) -> None:
        """Exceção na criação do dialog deve ser silenciada pelo try/except."""
        fake = _make_enviar_fake(client_id=42)
        with _patch_client_editor_dialog(raise_on_init=True):
            # Não deve propagar
            _on_enviar_documentos_fn(fake)


# ── SEÇÃO 28B: Separação semântica — on_saved (upload vs. save) ──────────────

_VIEW_SRC_PATH = Path(_VIEW_FILE)


class TestOnSavedSentinelSource:
    """Garante que on_saved em view.py distingue upload de save real.

    Invariantes:
      1. on_saved em _open_client_editor tem ramo `_source == "upload"`.
      2. on_saved em _open_client_editor tem log "Documentos" no ramo upload.
      3. on_saved em _open_client_editor tem log "salvo com sucesso" no ramo padrão.
      4. on_saved em _on_enviar_documentos tem ramo `_source == "upload"`.
      5. on_saved em _on_enviar_documentos tem log "Documentos" no ramo upload.
      6. Ambos os on_saved chamam load_async().
    """

    def _view_source(self) -> str:
        return _VIEW_SRC_PATH.read_text(encoding="utf-8")

    def _body_open_editor(self) -> str:
        src = self._view_source()
        start = src.find("def _open_client_editor(")
        assert start >= 0
        end = src.find("\n    def ", start + 1)
        return src[start:end] if end > 0 else src[start:]

    def _body_enviar_documentos(self) -> str:
        src = self._view_source()
        start = src.find("def _on_enviar_documentos(")
        assert start >= 0
        end = src.find("\n    def ", start + 1)
        return src[start:end] if end > 0 else src[start:]

    # ── _open_client_editor ──────────────────────────────────────────────────

    def test_open_editor_on_saved_has_upload_source_branch(self) -> None:
        """on_saved em _open_client_editor deve checar `_source == "upload"`."""
        body = self._body_open_editor()
        assert '"upload"' in body or "'upload'" in body, (
            "_open_client_editor.on_saved não tem ramo _source=='upload'. "
            "Upload de arquivo dispararia log 'salvo com sucesso' incorretamente."
        )

    def test_open_editor_on_saved_upload_branch_logs_documentos(self) -> None:
        """Ramo upload em _open_client_editor deve mencionar 'Documentos'."""
        body = self._body_open_editor()
        # Localizar o ramo _source == "upload"
        idx = body.find('"_source"')
        if idx < 0:
            idx = body.find("'_source'")
        assert idx >= 0, "Ramo _source não encontrado em _open_client_editor.on_saved"
        snippet = body[idx : idx + 400]
        assert "Documentos" in snippet, "_open_client_editor.on_saved não loga 'Documentos' no ramo upload."

    def test_open_editor_on_saved_default_branch_logs_salvo(self) -> None:
        """Ramo padrão (save real) em _open_client_editor deve mencionar 'salvo'."""
        body = self._body_open_editor()
        assert "salvo" in body.lower(), "_open_client_editor.on_saved não loga mensagem com 'salvo' no ramo padrão."

    # ── _on_enviar_documentos ────────────────────────────────────────────────

    def test_enviar_docs_on_saved_has_upload_source_branch(self) -> None:
        """on_saved em _on_enviar_documentos deve checar `_source == "upload"`."""
        body = self._body_enviar_documentos()
        assert '"upload"' in body or "'upload'" in body, (
            "_on_enviar_documentos.on_saved não tem ramo _source=='upload'. "
            "Upload dispararia log semântico incorreto."
        )

    def test_enviar_docs_on_saved_upload_branch_logs_documentos(self) -> None:
        """Ramo upload em _on_enviar_documentos deve mencionar 'Documentos'."""
        body = self._body_enviar_documentos()
        idx = body.find('"_source"')
        if idx < 0:
            idx = body.find("'_source'")
        assert idx >= 0, "Ramo _source não encontrado em _on_enviar_documentos.on_saved"
        snippet = body[idx : idx + 400]
        assert "Documentos" in snippet, "_on_enviar_documentos.on_saved não loga 'Documentos' no ramo upload."

    # ── Ambos chamam load_async ──────────────────────────────────────────────

    def test_open_editor_on_saved_calls_load_async_in_all_paths(self) -> None:
        """on_saved em _open_client_editor deve chamar load_async() em qualquer ramo."""
        body = self._body_open_editor()
        on_saved_start = body.find("def on_saved(")
        assert on_saved_start >= 0
        # Pegar o corpo da closure (até próxima def no mesmo nível)
        next_def = body.find("\n            def ", on_saved_start + 1)
        closure = body[on_saved_start:next_def] if next_def > 0 else body[on_saved_start : on_saved_start + 600]
        assert (
            "load_async" in closure
        ), "_open_client_editor.on_saved não chama load_async(). Refresh da lista quebrado."

    def test_enviar_docs_on_saved_calls_load_async_in_all_paths(self) -> None:
        """on_saved em _on_enviar_documentos deve chamar load_async() em qualquer ramo."""
        body = self._body_enviar_documentos()
        on_saved_start = body.find("def on_saved(")
        assert on_saved_start >= 0
        next_def = body.find("\n            def ", on_saved_start + 1)
        closure = body[on_saved_start:next_def] if next_def > 0 else body[on_saved_start : on_saved_start + 600]
        assert (
            "load_async" in closure
        ), "_on_enviar_documentos.on_saved não chama load_async(). Refresh da lista quebrado."


class TestOnSavedSentinelBehavior:
    """Testes comportamentais do sentinel `_source: upload` em on_saved."""

    def test_on_saved_with_upload_source_calls_load_async(self) -> None:
        """on_save({"_source": "upload"}) deve chamar load_async()."""
        fake = _make_enviar_fake(client_id=99)
        with _patch_client_editor_dialog() as (mock_dialog_class, _):
            _on_enviar_documentos_fn(fake)
        _, kwargs = mock_dialog_class.call_args
        on_save_cb = kwargs["on_save"]
        fake.load_async.reset_mock()
        on_save_cb({"_source": "upload"})
        fake.load_async.assert_called_once()

    def test_on_saved_without_source_calls_load_async(self) -> None:
        """on_save({}) (save real) deve chamar load_async() mesmo sem _source."""
        fake = _make_enviar_fake(client_id=99)
        with _patch_client_editor_dialog() as (mock_dialog_class, _):
            _on_enviar_documentos_fn(fake)
        _, kwargs = mock_dialog_class.call_args
        on_save_cb = kwargs["on_save"]
        fake.load_async.reset_mock()
        on_save_cb({})
        fake.load_async.assert_called_once()

    def test_on_saved_with_save_data_calls_load_async(self) -> None:
        """on_save({"id": 42, ...}) (save real com dados) deve chamar load_async()."""
        fake = _make_enviar_fake(client_id=42)
        with _patch_client_editor_dialog() as (mock_dialog_class, _):
            _on_enviar_documentos_fn(fake)
        _, kwargs = mock_dialog_class.call_args
        on_save_cb = kwargs["on_save"]
        fake.load_async.reset_mock()
        on_save_cb({"id": 42, "nome": "Empresa XYZ", "cnpj": "00.000.000/0001-00"})
        fake.load_async.assert_called_once()


# ── SEÇÃO 29: _on_export — cobertura complementar (FASE 7B.26) ────────────────


class _TruthyEmptyRowDataMap:
    """Simula um _row_data_map truthy cujos values() retornam lista vazia.

    Serve para acionar o guard 2 de _on_export sem disparar o guard 1.
    """

    def __bool__(self) -> bool:
        return True

    def values(self):  # noqa: ANN201
        return []


@contextmanager
def _patch_on_export_dispatch():
    """Substitui imports lazy de _on_export por mocks para testes headless.

    Mocks injetados:
      - tkinter.filedialog   → mock_fd
      - src.modules.clientes.core.export → mock_export_mod
      - src.modules.clientes.ui.actions.execute_export → mock_exec

    Yields:
        (mock_exec, mock_fd)
    """
    _sentinel = object()
    import tkinter
    import src.modules.clientes.ui.actions as _act_mod

    # --- filedialog ---
    mock_fd = MagicMock()
    _old_fd_sys = sys.modules.get("tkinter.filedialog")
    _old_fd_attr = getattr(tkinter, "filedialog", _sentinel)
    sys.modules["tkinter.filedialog"] = mock_fd
    tkinter.filedialog = mock_fd  # type: ignore[attr-defined]

    # --- core stub com export ---
    _core_key = "src.modules.clientes.core"
    _core_exp_key = "src.modules.clientes.core.export"
    _old_core_sys = sys.modules.get(_core_key)
    _old_core_exp_sys = sys.modules.get(_core_exp_key)
    mock_export_mod = MagicMock()
    _core_stub = _old_core_sys if _old_core_sys is not None else types.ModuleType(_core_key)
    if _old_core_sys is None:
        sys.modules[_core_key] = _core_stub
    _old_export_on_core = getattr(_core_stub, "export", _sentinel)
    setattr(_core_stub, "export", mock_export_mod)
    sys.modules[_core_exp_key] = mock_export_mod

    # --- execute_export ---
    mock_exec = MagicMock()
    _old_exec = getattr(_act_mod, "execute_export", _sentinel)
    _act_mod.execute_export = mock_exec

    try:
        yield mock_exec, mock_fd
    finally:
        # restore filedialog
        if _old_fd_sys is None:
            sys.modules.pop("tkinter.filedialog", None)
        else:
            sys.modules["tkinter.filedialog"] = _old_fd_sys
        if _old_fd_attr is _sentinel:
            try:
                delattr(tkinter, "filedialog")
            except AttributeError:
                pass
        else:
            tkinter.filedialog = _old_fd_attr  # type: ignore[attr-defined]

        # restore core/export
        if _old_core_sys is None:
            sys.modules.pop(_core_key, None)
        if _old_core_exp_sys is None:
            sys.modules.pop(_core_exp_key, None)
        else:
            sys.modules[_core_exp_key] = _old_core_exp_sys
        if _old_export_on_core is _sentinel:
            try:
                delattr(_core_stub, "export")
            except AttributeError:
                pass
        else:
            setattr(_core_stub, "export", _old_export_on_core)

        # restore execute_export
        if _old_exec is _sentinel:
            try:
                delattr(_act_mod, "execute_export")
            except AttributeError:
                pass
        else:
            _act_mod.execute_export = _old_exec


class TestOnExportAST:
    """Testes AST de _on_export — invariantes estruturais."""

    def test_guard1_checks_row_data_map(self) -> None:
        """_on_export deve verificar `self._row_data_map` como primeira proteção."""
        fn = _method_node("_on_export")
        src = _source_of(fn)
        assert "self._row_data_map" in src, "_on_export deve checar _row_data_map antes de tentar exportar"

    def test_guard1_calls_show_info_on_empty(self) -> None:
        """Sem dados, _on_export deve chamar _show_info para avisar o usuário."""
        fn = _method_node("_on_export")
        src = _source_of(fn)
        assert "_show_info" in src, "_on_export deve chamar _show_info quando não há dados para exportar"

    def test_delegates_to_execute_export(self) -> None:
        """_on_export deve delegar a exportação para execute_export de actions.py."""
        fn = _method_node("_on_export")
        src = _source_of(fn)
        assert (
            "execute_export" in src
        ), "_on_export deve usar execute_export de actions.py — lógica de exportação fora da view"

    def test_uses_filedialog_asksaveasfilename_as_ask_save_fn(self) -> None:
        """_on_export deve usar filedialog.asksaveasfilename como ask_save_fn."""
        fn = _method_node("_on_export")
        src = _source_of(fn)
        assert (
            "filedialog" in src and "asksaveasfilename" in src
        ), "_on_export deve passar filedialog.asksaveasfilename como ask_save_fn"

    def test_guard2_builds_rows_to_export(self) -> None:
        """_on_export deve montar rows_to_export a partir de _row_data_map.values()."""
        fn = _method_node("_on_export")
        src = _source_of(fn)
        assert "rows_to_export" in src, "_on_export deve construir rows_to_export e verificá-lo antes de delegar"


class TestOnExportBehaviorExtra:
    """Testes comportamentais adicionais de _on_export — gaps não cobertos em TestExportBehavior."""

    def setup_method(self) -> None:
        _mock_show_info_export_guard.reset_mock()
        _mock_show_error_export_guard.reset_mock()

    def test_guard2_truthy_map_empty_values_shows_info(self) -> None:
        """Guard 2: _row_data_map truthy mas values() vazio aciona _show_info e retorna."""
        fake = MagicMock()
        fake._row_data_map = _TruthyEmptyRowDataMap()
        fake.winfo_toplevel.return_value = MagicMock()

        _on_export_view(fake)

        _mock_show_info_export_guard.assert_called_once()

    def test_valid_data_execute_export_called_once(self) -> None:
        """Com dados válidos, execute_export deve ser chamado exatamente uma vez."""
        row = MagicMock()
        fake = MagicMock()
        fake._row_data_map = {"iid1": row}
        fake.winfo_toplevel.return_value = MagicMock()

        with _patch_on_export_dispatch() as (mock_exec, _):
            _on_export_view(fake)

        mock_exec.assert_called_once()

    def test_valid_data_passes_correct_rows_to_export(self) -> None:
        """execute_export deve receber exatamente os rows de _row_data_map como rows_to_export."""
        row = MagicMock()
        fake = MagicMock()
        fake._row_data_map = {"iid1": row}
        fake.winfo_toplevel.return_value = MagicMock()

        with _patch_on_export_dispatch() as (mock_exec, _):
            _on_export_view(fake)

        _, kwargs = mock_exec.call_args
        assert kwargs["rows_to_export"] == [
            row
        ], "execute_export deve receber os valores de _row_data_map como rows_to_export"

    def test_valid_data_passes_filedialog_as_ask_save_fn(self) -> None:
        """execute_export deve receber filedialog.asksaveasfilename como ask_save_fn."""
        row = MagicMock()
        fake = MagicMock()
        fake._row_data_map = {"iid1": row}
        fake.winfo_toplevel.return_value = MagicMock()

        with _patch_on_export_dispatch() as (mock_exec, mock_fd):
            _on_export_view(fake)

        _, kwargs = mock_exec.call_args
        assert (
            kwargs["ask_save_fn"] is mock_fd.asksaveasfilename
        ), "execute_export deve receber filedialog.asksaveasfilename como ask_save_fn"


# ── SEÇÃO 30: _compute_status_cell — proteção unitária (FASE 7B.27) ─────────

_compute_status_cell_fns = extract_functions_from_source(
    _VIEW_FILE,
    "_compute_status_cell",
    class_name="ClientesV2Frame",
)
_compute_status_cell_fn = _compute_status_cell_fns["_compute_status_cell"]


class TestComputeStatusCellUnit:
    """Testes unitários de _compute_status_cell.

    Verifica todas as combinações de status principal, ANVISA e Farmácia Popular.
    Zero dependência de UI — função pura extraída via extract_functions_from_source.
    """

    # ── Casos base: tudo inativo ──────────────────────────────────────────

    def test_all_none_returns_empty(self) -> None:
        """Três campos None → célula vazia."""
        assert _compute_status_cell_fn(None, None, None) == ""

    def test_all_empty_string_returns_empty(self) -> None:
        """Três campos string vazia → célula vazia."""
        assert _compute_status_cell_fn("", "", "") == ""

    def test_all_triple_dash_returns_empty(self) -> None:
        """'---' é tratado como inativo → célula vazia."""
        assert _compute_status_cell_fn("---", "---", "---") == ""

    def test_whitespace_only_returns_empty(self) -> None:
        """Espaços em branco são tratados como inativo → célula vazia."""
        assert _compute_status_cell_fn("   ", "   ", "   ") == ""

    # ── Status principal sozinho ──────────────────────────────────────────

    def test_only_status_principal_returned_as_is(self) -> None:
        """Apenas status principal ativo → retorna o status diretamente."""
        assert _compute_status_cell_fn("Ativo", None, None) == "Ativo"

    def test_status_principal_with_inactive_markers_returns_only_status(self) -> None:
        """Status principal ativo + marcadores inativos → somente status."""
        assert _compute_status_cell_fn("Ativo", "---", "") == "Ativo"

    def test_status_principal_triple_dash_is_ignored(self) -> None:
        """Status principal '---' é ignorado → célula vazia."""
        assert _compute_status_cell_fn("---", None, None) == ""

    # ── Marcadores AN e FP sozinhos ───────────────────────────────────────

    def test_only_anvisa_active_returns_an(self) -> None:
        """Apenas ANVISA ativo → 'AN'."""
        assert _compute_status_cell_fn(None, "Ativo", None) == "AN"

    def test_only_fp_active_returns_fp(self) -> None:
        """Apenas Farmácia Popular ativo → 'FP'."""
        assert _compute_status_cell_fn(None, None, "Ativo") == "FP"

    def test_anvisa_and_fp_both_active_returns_an_fp(self) -> None:
        """Ambos ANVISA e FP ativos (sem status principal) → 'AN/FP'."""
        assert _compute_status_cell_fn(None, "Ativo", "Ativo") == "AN/FP"

    def test_anvisa_triple_dash_not_active(self) -> None:
        """ANVISA '---' não é marcador ativo → não inclui 'AN'."""
        assert _compute_status_cell_fn(None, "---", None) == ""

    def test_fp_empty_not_active(self) -> None:
        """FP '' não é marcador ativo → não inclui 'FP'."""
        assert _compute_status_cell_fn(None, None, "") == ""

    # ── Combinações status + marcadores ──────────────────────────────────

    def test_status_plus_anvisa_returns_combined(self) -> None:
        """Status + ANVISA → 'Status + AN'."""
        assert _compute_status_cell_fn("Regular", "Ativo", None) == "Regular + AN"

    def test_status_plus_fp_returns_combined(self) -> None:
        """Status + FP → 'Status + FP'."""
        assert _compute_status_cell_fn("Regular", None, "Ativo") == "Regular + FP"

    def test_status_plus_anvisa_fp_returns_combined(self) -> None:
        """Status + ambos marcadores → 'Status + AN/FP'."""
        assert _compute_status_cell_fn("Regular", "Ativo", "Ativo") == "Regular + AN/FP"

    def test_inactive_status_with_anvisa_only_returns_an(self) -> None:
        """Status inativo + ANVISA ativo → somente 'AN' (sem ' + ')."""
        assert _compute_status_cell_fn("---", "Ativo", None) == "AN"

    def test_inactive_status_with_fp_only_returns_fp(self) -> None:
        """Status inativo + FP ativo → somente 'FP'."""
        assert _compute_status_cell_fn("", None, "Ativo") == "FP"

    def test_inactive_status_with_both_markers_returns_an_fp(self) -> None:
        """Status inativo + ambos ativos → 'AN/FP' sem status."""
        assert _compute_status_cell_fn("---", "Ativo", "Ativo") == "AN/FP"

    # ── Preservação do valor exato ────────────────────────────────────────

    def test_status_value_is_preserved_verbatim(self) -> None:
        """Valor do status é preservado tal como recebido."""
        assert _compute_status_cell_fn("Em espera", None, None) == "Em espera"

    def test_combined_format_uses_plus_with_spaces(self) -> None:
        """Separador entre status e marcador deve ser ' + ' (com espaços)."""
        result = _compute_status_cell_fn("Ativo", "Ativo", None)
        assert " + " in result, f"Separador ' + ' esperado, obtido: {result!r}"

    def test_an_fp_uses_slash_separator(self) -> None:
        """Quando ambos marcadores presentes, usa 'AN/FP' com barra, sem espaços."""
        result = _compute_status_cell_fn(None, "Ativo", "Ativo")
        assert result == "AN/FP"

    def test_whitespace_status_is_treated_as_inactive(self) -> None:
        """Status só com espaços é tratado como inativo e ignorado."""
        assert _compute_status_cell_fn("   ", "Ativo", None) == "AN"
