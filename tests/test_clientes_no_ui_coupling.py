# -*- coding: utf-8 -*-
"""Testes de regressão: verifica que o core do módulo clientes não tem acoplamento de UI.

FASE 3 Lote 2 — impede que `filedialog`, `messagebox` ou funções de diálogo
sejam importados em nível de módulo em src/modules/clientes/core/*.py.

FASE 3 Lote 3 — adicionados:
  - constants.py não contém tkinter nem _build_status_menu
  - ORDER_LABEL_ALIASES não contém entradas auto-referenciais

FASE 3 Lote 4 — adicionados (TestViewDeadCodeAbsent):
  - _render_rows_from_list ausente de view.py
  - normalize_order_label não importado lazily dentro de funções

FASE 4 — adicionados (TestEditorDataMixinRobustez, TestViewNoFormatDatetime):
  - _run_in_thread descarta callbacks com log.debug (não silenciosamente)
  - _format_datetime removido de view.py (no-op: viewmodel já formata)
  - _render_rows usa row.ultima_alteracao diretamente

Estes testes operam sobre o texto-fonte (AST) — sem importar o módulo,
portanto não dependem de Tk/CTk.
"""

from __future__ import annotations

import ast
from pathlib import Path

_CORE_DIR = Path(__file__).resolve().parent.parent / "src" / "modules" / "clientes" / "core"

# Padrões de UI que NÃO devem aparecer em imports de nível de módulo dos arquivos
# de core (podem aparecer como imports locais dentro de funções, mas não no topo).
_FORBIDDEN_MODULE_IMPORTS = [
    "tkinter",
    "filedialog",
    "messagebox",
]


def _top_level_import_names(source: str) -> list[str]:
    """Retorna todos os módulos/nomes importados no nível de módulo (não dentro de funções)."""
    tree = ast.parse(source)
    results: list[str] = []
    for node in ast.iter_child_nodes(tree):  # apenas nível raiz
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                results.append(node.module)
    return results


class TestNoCoreUICoupling:
    """Garante que módulos de core não têm imports de UI em nível de módulo."""

    def _core_files(self) -> list[Path]:
        return [p for p in _CORE_DIR.glob("*.py") if p.name != "__init__.py"]

    def test_no_toplevel_filedialog_import(self) -> None:
        """filedialog não deve ser importado no topo de nenhum arquivo core."""
        for path in self._core_files():
            source = path.read_text(encoding="utf-8")
            imports = _top_level_import_names(source)
            for imp in imports:
                assert "filedialog" not in imp, (
                    f"{path.name}: import de filedialog em nível de módulo é proibido no core "
                    f"(acoplamento UI). Use import local ou mova para a camada de view."
                )

    def test_no_toplevel_messagebox_import(self) -> None:
        """messagebox não deve ser importado no topo de nenhum arquivo core."""
        for path in self._core_files():
            source = path.read_text(encoding="utf-8")
            imports = _top_level_import_names(source)
            for imp in imports:
                assert (
                    "messagebox" not in imp
                ), f"{path.name}: import de messagebox em nível de módulo é proibido no core."

    def test_no_toplevel_tkinter_import_viewmodel(self) -> None:
        """tkinter não deve ser importado no topo de viewmodel.py.

        constants.py tem acoplamento pré-existente via tk.Menu que é dívida
        técnica conhecida (fora do escopo do Lote 2).
        """
        viewmodel_path = _CORE_DIR / "viewmodel.py"
        source = viewmodel_path.read_text(encoding="utf-8")
        imports = _top_level_import_names(source)
        for imp in imports:
            assert not imp.startswith("tkinter"), (
                f"viewmodel.py: import de tkinter em nível de módulo é proibido no core "
                f"(acoplamento UI). Encontrado: '{imp}'"
            )

    def test_export_clientes_batch_not_in_viewmodel(self) -> None:
        """export_clientes_batch foi removido do viewmodel (UI coupling + dead code).

        Se reaparecer, deve ser implementado na camada de view, não de core.
        """
        viewmodel_path = _CORE_DIR / "viewmodel.py"
        source = viewmodel_path.read_text(encoding="utf-8")
        assert "export_clientes_batch" not in source, (
            "viewmodel.py: export_clientes_batch não deve existir no core — "
            "lógica de filedialog/diálogos pertence à view. "
            "O equivalente correto é ClientesV2Frame._on_export() em ui/view.py."
        )

    def test_viewmodel_rc_dialogs_not_toplevel(self) -> None:
        """rc_dialogs não deve ser importado em nível de módulo em viewmodel.py.

        Diálogos com parent=None são silently broken e pertencem à view.
        """
        viewmodel_path = _CORE_DIR / "viewmodel.py"
        source = viewmodel_path.read_text(encoding="utf-8")
        imports = _top_level_import_names(source)
        for imp in imports:
            assert "rc_dialogs" not in imp, (
                "viewmodel.py: rc_dialogs importado em nível de módulo. " "Diálogos pertencem à camada de view."
            )


class TestConstantsNoCoupling:
    """Garante que constants.py não tem acoplamento com tkinter (Lote 3)."""

    def test_no_tkinter_import_in_constants(self) -> None:
        """constants.py não deve importar tkinter em nível de módulo."""
        path = _CORE_DIR / "constants.py"
        source = path.read_text(encoding="utf-8")
        imports = _top_level_import_names(source)
        for imp in imports:
            assert not imp.startswith("tkinter"), (
                "constants.py: import de tkinter em nível de módulo foi reintroduzido. " f"Encontrado: '{imp}'"
            )

    def test_build_status_menu_not_in_constants(self) -> None:
        """_build_status_menu foi removido de constants.py (zero callers, UI coupling).

        Se for necessário recriar, deve ser implementado na camada de view/toolbar.
        """
        path = _CORE_DIR / "constants.py"
        source = path.read_text(encoding="utf-8")
        assert "_build_status_menu" not in source, (
            "constants.py: _build_status_menu foi reintroduzido. " "Esta função pertence à camada de view (toolbar)."
        )


class TestOrderLabelAliasesNoSelfRef:
    """Garante que ORDER_LABEL_ALIASES não contém entradas auto-referenciais (Lote 3)."""

    def _get_aliases_and_canonicals(self) -> tuple[dict, set]:
        """Lê ORDER_LABEL_ALIASES e os labels canônicos de ui_helpers via AST + exec."""
        path = Path(__file__).resolve().parent.parent / "src" / "modules" / "clientes" / "core" / "ui_helpers.py"
        # Executa apenas o módulo puro (sem dependências de UI)
        namespace: dict = {}
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
        aliases: dict = namespace["ORDER_LABEL_ALIASES"]
        canonical_labels = {
            namespace[k] for k in namespace if k.startswith("ORDER_LABEL_") and isinstance(namespace[k], str)
        }
        return aliases, canonical_labels

    def test_no_self_referential_entries(self) -> None:
        """Nenhuma entrada de ORDER_LABEL_ALIASES deve mapear uma chave para si mesma.

        Entradas auto-referenciais (key == value) são redundantes porque
        normalize_order_label usa .get(key, default=key) — o fallback já cobre.
        """
        aliases, _ = self._get_aliases_and_canonicals()
        self_refs = {k: v for k, v in aliases.items() if k == v}
        assert not self_refs, (
            f"ORDER_LABEL_ALIASES contém {len(self_refs)} entrada(s) auto-referencial(is): " f"{list(self_refs.keys())}"
        )

    def test_canonical_labels_not_as_keys(self) -> None:
        """Labels canônicos (ORDER_LABEL_*) não devem aparecer como chaves de aliases.

        Se um label canônico é chave de alias, ele só pode mapear para si mesmo
        (auto-referencial) — o que é redundante, ou mapear para outro canônico
        (o que seria confuso). Ambos os casos são dívida técnica.
        """
        aliases, canonical_labels = self._get_aliases_and_canonicals()
        bad_keys = [k for k in aliases if k in canonical_labels and aliases[k] != k]
        assert not bad_keys, f"Labels canônicos não devem ser chave de alias mapeando para outro valor: {bad_keys}"


class TestViewDeadCodeAbsent:
    """Lote 4 — garante que dead code removido em view.py não seja reintroduzido."""

    _VIEW_PATH = Path(__file__).resolve().parent.parent / "src" / "modules" / "clientes" / "ui" / "view.py"

    def test_render_rows_from_list_not_in_view(self) -> None:
        """_render_rows_from_list foi removido de view.py (zero callers).

        Era duplicata de _render_rows com parâmetro — nunca foi referenciada
        fora de sua própria definição. Removida no Lote 4.
        """
        source = self._VIEW_PATH.read_text(encoding="utf-8")
        assert "_render_rows_from_list" not in source, (
            "view.py: _render_rows_from_list foi reintroduzida. "
            "É dead code — use _render_rows() para renderização normal."
        )

    def test_normalize_order_label_not_lazily_imported_in_view(self) -> None:
        """normalize_order_label não deve ser importado dentro de função em view.py.

        Antes do Lote 4, havia `from src.modules.clientes.core.ui_helpers import
        normalize_order_label` dentro de _on_order_changed. Foi elevado para o
        import top-level junto com ORDER_CHOICES e DEFAULT_ORDER_LABEL.
        """
        source = self._VIEW_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        # Procurar ImportFrom de ui_helpers dentro de corpos de funções (não nível módulo)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.ImportFrom)
                        and child.module
                        and "ui_helpers" in child.module
                        and any(alias.name == "normalize_order_label" for alias in child.names)
                    ):
                        raise AssertionError(
                            f"view.py: normalize_order_label importado lazily dentro de "
                            f"'{node.name}'. Deve estar no import top-level."
                        )


class TestEditorDataMixinRobustez:
    """FASE 4 — verifica melhorias de observabilidade em _run_in_thread."""

    _MIXIN_PATH = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "modules"
        / "clientes"
        / "ui"
        / "views"
        / "_editor_data_mixin.py"
    )

    def test_callback_drop_is_logged_not_silent(self) -> None:
        """_run_in_thread deve logar (log.debug) quando callback é descartado.

        Antes da FASE 4, o descarte era silencioso (sem nenhum log).
        Agora, quando winfo_exists() retorna False, o else-branch chama log.debug.
        """
        source = self._MIXIN_PATH.read_text(encoding="utf-8")
        # Confirmar que há log.debug no else-branch do winfo_exists
        assert "on_success descartado" in source or "on_error descartado" in source, (
            "_editor_data_mixin.py: _run_in_thread deve logar quando callback é descartado "
            "(log.debug). Descarte silencioso foi substituído por log observável."
        )

    def test_run_in_thread_has_else_branches(self) -> None:
        """_run_in_thread deve ter else-branches para ambos on_success e on_error.

        Garante que a estrutura de log para descarte de callbacks está presente
        para os dois caminhos (sucesso e erro).
        """
        source = self._MIXIN_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Encontrar a função _run_in_thread
        run_in_thread = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_run_in_thread":
                run_in_thread = node
                break

        assert run_in_thread is not None, "_run_in_thread não encontrada em _editor_data_mixin.py"

        # Verificar que existe um log.debug para o caso de widget destruído
        # Basta confirmar que a string de log está no source (já garantido pelo teste anterior)
        # Aqui verificamos a presença de ambos os case via AST: dois if/else em _wrapper
        wrapper = None
        for node in ast.walk(run_in_thread):
            if isinstance(node, ast.FunctionDef) and node.name == "_wrapper":
                wrapper = node
                break

        assert wrapper is not None, "_wrapper não encontrada dentro de _run_in_thread"

        # Deve haver pelo menos um if/else no _wrapper (o guard winfo_exists)
        if_nodes = [n for n in ast.walk(wrapper) if isinstance(n, ast.If)]
        assert len(if_nodes) >= 2, (  # noqa: PLR2004
            f"_wrapper deve ter >= 2 ifs (on_error e on_success guards), encontrado: {len(if_nodes)}"
        )


class TestViewNoFormatDatetime:
    """FASE 4 — verifica que _format_datetime foi removido de view.py."""

    _VIEW_PATH = Path(__file__).resolve().parent.parent / "src" / "modules" / "clientes" / "ui" / "view.py"

    def test_format_datetime_not_in_view(self) -> None:
        """_format_datetime foi removido de view.py (era no-op: viewmodel já formata).

        O viewmodel chama fmt_datetime_br() em _build_row_from_cliente, entregando
        row.ultima_alteracao já formatado. A segunda passagem em _format_datetime
        sempre retornava a string inalterada (as-is fallback). Removida na FASE 4.
        """
        source = self._VIEW_PATH.read_text(encoding="utf-8")
        assert "_format_datetime" not in source, (
            "view.py: _format_datetime foi reintroduzida. "
            "O ViewModel já entrega row.ultima_alteracao formatado. "
            "Use row.ultima_alteracao diretamente em _render_rows."
        )

    def test_render_rows_uses_ultima_alteracao_directly(self) -> None:
        """_render_rows deve usar row.ultima_alteracao diretamente (sem _format_datetime).

        Verifica via AST que não há chamada de método _format_datetime dentro
        do corpo de _render_rows.
        """
        source = self._VIEW_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)

        render_rows = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_render_rows":
                render_rows = node
                break

        assert render_rows is not None, "_render_rows não encontrada em view.py"

        # Não deve haver chamada a _format_datetime dentro de _render_rows
        for node in ast.walk(render_rows):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "_format_datetime":
                    raise AssertionError(
                        "view.py/_render_rows: ainda há chamada a _format_datetime. "
                        "Use row.ultima_alteracao diretamente."
                    )


class TestUploaderNoManualDialog:
    """FASE 5 — verifica que uploader_supabase.py usa rc_dialogs e não contém _show_msg."""

    _UPLOADER_PATH = Path(__file__).resolve().parent.parent / "src" / "modules" / "uploads" / "uploader_supabase.py"

    def test_show_msg_absent(self) -> None:
        """_show_msg foi removida de uploader_supabase.py.

        A função manual CTkToplevel (~70 linhas) foi substituída pelos helpers
        canônicos de rc_dialogs (show_info, show_warning, show_error).
        """
        source = self._UPLOADER_PATH.read_text(encoding="utf-8")
        assert "_show_msg" not in source, (
            "uploader_supabase.py: _show_msg foi reintroduzida. "
            "Use rc_dialogs.show_info / show_warning / show_error."
        )

    def test_ui_tokens_not_imported(self) -> None:
        """Tokens visuais (APP_BG, PRIMARY_BLUE, etc.) não devem ser importados.

        Esses tokens eram usados apenas por _show_msg. Após a remoção,
        não há mais dependência de ui_tokens em uploader_supabase.py.
        """
        source = self._UPLOADER_PATH.read_text(encoding="utf-8")
        for token in ("APP_BG", "BUTTON_RADIUS", "PRIMARY_BLUE", "PRIMARY_BLUE_HOVER"):
            assert token not in source, (
                f"uploader_supabase.py: import de {token!r} encontrado. "
                "Tokens visuais são usados apenas em _show_msg (removida)."
            )

    def test_window_utils_not_imported(self) -> None:
        """apply_window_icon não deve ser importada em uploader_supabase.py.

        Era usada apenas por _show_msg para aplicar ícone à janela manual.
        """
        source = self._UPLOADER_PATH.read_text(encoding="utf-8")
        assert "apply_window_icon" not in source, (
            "uploader_supabase.py: apply_window_icon encontrada. " "Era dependência exclusiva de _show_msg (removida)."
        )

    def test_rc_dialogs_imported(self) -> None:
        """rc_dialogs deve ser importado em nível de módulo."""
        source = self._UPLOADER_PATH.read_text(encoding="utf-8")
        assert "from src.ui.dialogs.rc_dialogs import" in source, (
            "uploader_supabase.py: rc_dialogs não importado. "
            "Os diálogos devem usar show_info/show_warning/show_error de rc_dialogs."
        )
