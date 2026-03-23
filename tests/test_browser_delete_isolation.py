# -*- coding: utf-8 -*-
"""Testes de regressão — bug: Delete no browser excluía o cliente.

Garante (via AST + lógica) que os três invariantes do patch estão presentes:

  1. FileList.<Delete> retorna "break" para impedir propagação ao editor pai.
  2. browser_v2: on_delete wired para _delete_selected (não no-op).
  3. browser_v2: binding <Delete> no nível da janela.
  4. view.py: _on_delete_client guarda contra editor aberto.
  5. _editor_actions_mixin: focus_force() chamado após abrir browser.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import unittest

_SRC = Path(__file__).resolve().parent.parent / "src"
_FILE_LIST = _SRC / "modules" / "uploads" / "views" / "file_list.py"
_BROWSER_V2 = _SRC / "modules" / "uploads" / "views" / "browser_v2.py"
_VIEW = _SRC / "modules" / "clientes" / "ui" / "view.py"
_EDITOR_ACTIONS = _SRC / "modules" / "clientes" / "ui" / "views" / "_editor_actions_mixin.py"


# ---------------------------------------------------------------------------
# Helpers de AST
# ---------------------------------------------------------------------------


def _src(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ===========================================================================
# 1) FileList: <Delete> NÃO usa lambda que ignora retorno
# ===========================================================================


class TestFileListDeleteBreak(unittest.TestCase):
    """FileList deve retornar 'break' nos bindings de Delete/BackSpace."""

    def test_delete_binding_not_plain_lambda_none(self) -> None:
        """A lambda antiga `lambda _event: self._handle_delete()` não deve existir.

        Ela retornava None → evento propagava para o editor pai.
        """
        source = _src(_FILE_LIST)
        # A forma antiga sem retorno "break" não deve estar presente
        assert "lambda _event: self._handle_delete()" not in source, (
            "file_list.py: binding <Delete> retorna None (propaga para editor pai). "
            "Deve retornar 'break' para isolar o browser."
        )

    def test_delete_binding_produces_break(self) -> None:
        """O binding <Delete> deve conter 'break' para parar propagação."""
        source = _src(_FILE_LIST)
        # Apenas linhas de código real (não comentários) que contenham bind + <Delete>
        delete_lines = [
            ln for ln in source.splitlines() if "<Delete>" in ln and "bind" in ln and not ln.lstrip().startswith("#")
        ]
        assert delete_lines, "file_list.py: nenhuma linha bind <Delete> encontrada"
        for line in delete_lines:
            assert "break" in line, (
                f"file_list.py: linha bind <Delete> não contém 'break': {line!r}. "
                "O evento propagaria para o editor pai e excluiria o cliente."
            )

    def test_backspace_binding_produces_break(self) -> None:
        """O binding <BackSpace> deve conter 'break' para parar propagação."""
        source = _src(_FILE_LIST)
        backspace_lines = [ln for ln in source.splitlines() if "<BackSpace>" in ln and "bind" in ln]
        assert backspace_lines, "file_list.py: nenhuma linha bind <BackSpace> encontrada"
        for line in backspace_lines:
            assert "break" in line, f"file_list.py: linha bind <BackSpace> não contém 'break': {line!r}."


# ===========================================================================
# 2) browser_v2: on_delete não é no-op
# ===========================================================================


class TestBrowserV2OnDelete(unittest.TestCase):
    """browser_v2 não deve passar on_delete=lambda: None ao FileList."""

    def test_on_delete_not_lambda_none(self) -> None:
        """'on_delete=lambda: None' não deve existir em browser_v2.py.

        Quando era no-op, Delete key e menu contexto não faziam nada no browser,
        mas o evento ainda propagava para cima.
        """
        source = _src(_BROWSER_V2)
        assert "on_delete=lambda: None" not in source, (
            "browser_v2.py: on_delete=lambda: None encontrado. "
            "FileList ficaria sem handler para Delete, "
            "e o menu de contexto 'Excluir' seria inoperante."
        )

    def test_on_delete_wired_to_delete_selected(self) -> None:
        """on_delete deve ser wired para _delete_selected."""
        source = _src(_BROWSER_V2)
        assert "on_delete=self._delete_selected" in source, (
            "browser_v2.py: on_delete não está wired para _delete_selected. "
            "Delete key e menu contexto não excluiriam o item selecionado."
        )


# ===========================================================================
# 3) browser_v2: binding <Delete> no nível da janela
# ===========================================================================


class TestBrowserV2WindowDeleteBinding(unittest.TestCase):
    """browser_v2 deve ter binding <Delete> no nível da janela."""

    def test_window_level_delete_binding_exists(self) -> None:
        """self.bind('<Delete>', ...) deve existir em browser_v2.py.

        Garante que mesmo se o foco estiver no browser toplevel (não em um widget
        filho), Delete acione _delete_selected e não vaze para o editor pai.
        """
        source = _src(_BROWSER_V2)
        delete_window_bindings = [ln for ln in source.splitlines() if "self.bind" in ln and "<Delete>" in ln]
        assert delete_window_bindings, (
            "browser_v2.py: nenhum self.bind('<Delete>', ...) no nível da janela. "
            "Delete no browser toplevel (sem widget filho focado) não seria bloqueado."
        )


# ===========================================================================
# 4) view.py: _on_delete_client guarda contra editor aberto
# ===========================================================================


class TestViewDeleteClientGuard(unittest.TestCase):
    """_on_delete_client em view.py deve verificar _editor_dialog antes de agir."""

    def test_guard_editor_dialog_present_in_source(self) -> None:
        """_on_delete_client deve checar self._editor_dialog antes de prosseguir."""
        source = _src(_VIEW)
        # Localizar a função _on_delete_client
        start = source.find("def _on_delete_client(")
        assert start >= 0, "view.py: _on_delete_client não encontrada"
        # Pegar trecho generoso da função (1000 chars cobre o guard)
        snippet = source[start : start + 1000]
        assert "_editor_dialog" in snippet, (
            "view.py: _on_delete_client não verifica _editor_dialog. "
            "Delete pode excluir o cliente mesmo com browser aberto."
        )
        # O guard de liveness pode ser feito diretamente com winfo_exists()
        # OU via helper editor_dialog_is_live (padrão atual — FASE 7B.8).
        assert "winfo_exists" in snippet or "editor_dialog_is_live" in snippet, (
            "view.py: _on_delete_client não valida a existência do dialog. "
            "O guard deve usar winfo_exists() ou editor_dialog_is_live()."
        )

    def test_on_delete_client_returns_break_when_editor_open(self) -> None:
        """_on_delete_client deve retornar 'break' quando o editor está aberto."""
        from src.modules.clientes.ui.view import ClientesV2Frame

        # Simular instância com editor aberto
        view = MagicMock(spec=ClientesV2Frame)
        view._selected_client_id = 42
        mock_dialog = MagicMock()
        mock_dialog.winfo_exists.return_value = True
        view._editor_dialog = mock_dialog

        # Chamar o handler
        result = ClientesV2Frame._on_delete_client(view, event=MagicMock())

        # Deve retornar break sem deletar o cliente
        assert result == "break", (
            f"_on_delete_client retornou {result!r} com editor aberto. "
            "Deve retornar 'break' para não excluir o cliente."
        )

    def test_on_delete_client_does_not_call_service_when_editor_open(self) -> None:
        """mover_cliente_para_lixeira NÃO deve ser chamado com editor aberto."""
        from src.modules.clientes.ui.view import ClientesV2Frame

        view = MagicMock(spec=ClientesV2Frame)
        view._selected_client_id = 99
        mock_dialog = MagicMock()
        mock_dialog.winfo_exists.return_value = True
        view._editor_dialog = mock_dialog

        with patch(
            "src.modules.clientes.ui.view.ClientesV2Frame._on_delete_client", wraps=ClientesV2Frame._on_delete_client
        ):
            with patch("src.modules.clientes.core.service.mover_cliente_para_lixeira") as mock_trash:
                ClientesV2Frame._on_delete_client(view, event=MagicMock())
                mock_trash.assert_not_called()


# ===========================================================================
# 5) _editor_actions_mixin: focus_force() após abrir browser
# ===========================================================================


class TestEditorActionsFocusForce(unittest.TestCase):
    """_editor_actions_mixin deve chamar focus_force() no browser após criação."""

    def test_focus_force_called_after_browser_open(self) -> None:
        """focus_force() deve ser chamado após open_files_browser_v2 bem-sucedido.

        Sem isso, o foco pode retornar ao treeview de clientes (janela principal)
        durante a janela entre grab_release() e browser.grab_set() (~10ms),
        e Delete excluiria o cliente.
        """
        source = _src(_EDITOR_ACTIONS)
        # Buscar a ocorrência de dlg = open_files_browser_v2 (a chamada real)
        start = source.find("dlg = open_files_browser_v2(")
        assert start >= 0, "_editor_actions_mixin.py: open_files_browser_v2 não encontrado"
        # Pegar trecho generoso após a chamada (1500 chars cobre todo o bloco)
        snippet = source[start : start + 1500]
        assert "focus_force" in snippet, (
            "_editor_actions_mixin.py: focus_force() não chamado após open_files_browser_v2. "
            "Sem isso, o foco pode permanecer no treeview de clientes durante o grab race."
        )


# ===========================================================================
# 6) Thread-safety do _touch_and_refresh (hardening do bugfix "Última alteração")
# ===========================================================================


class TestTouchAndRefreshThreadSafety(unittest.TestCase):
    """Garante que _touch_and_refresh não chama Tk fora do main thread.

    Invariantes verificados por inspeção de fonte:
      a) _bg() NÃO chama winfo_exists() diretamente (operação Tk não-thread-safe).
      b) _bg() retorna ao main thread via self.after(0, ...) antes de qualquer Tk.
      c) _notify_main() (main thread) é quem chama winfo_exists() e on_save.
      d) self.after(100, _touch_and_refresh) em _on_browser_close está dentro de try/except.
    """

    def _extract_bg_body(self, source: str) -> str:
        """Extrai o corpo de _bg() delimitado por _notify_main()."""
        bg_marker = "def _bg() -> None:"
        notify_marker = "def _notify_main() -> None:"
        start = source.find(bg_marker)
        assert start >= 0, "_editor_actions_mixin.py: def _bg() não encontrado"
        end = source.find(notify_marker, start)
        assert end >= 0, "_editor_actions_mixin.py: def _notify_main() não encontrado após _bg()"
        return source[start:end]

    def test_bg_does_not_call_winfo_exists(self) -> None:
        """_bg() não deve chamar winfo_exists() — chamada Tk fora do main thread."""
        source = _src(_EDITOR_ACTIONS)
        bg_body = self._extract_bg_body(source)
        assert "winfo_exists" not in bg_body, (
            "_editor_actions_mixin.py: _bg() chama winfo_exists() fora do main thread. "
            "Isso é thread-unsafe. A verificação deve estar em _notify_main()."
        )

    def test_bg_schedules_notify_via_after(self) -> None:
        """_bg() deve agendar o retorno ao main thread via self.after(0, ...)."""
        source = _src(_EDITOR_ACTIONS)
        bg_body = self._extract_bg_body(source)
        assert "self.after(0," in bg_body, (
            "_editor_actions_mixin.py: _bg() não agenda retorno ao main thread via "
            "self.after(0, ...). Qualquer chamada Tk após I/O seria thread-unsafe."
        )

    def test_notify_main_checks_winfo_exists(self) -> None:
        """_notify_main() deve verificar winfo_exists() antes de chamar on_save."""
        source = _src(_EDITOR_ACTIONS)
        # Encontrar _notify_main
        marker = "def _notify_main() -> None:"
        start = source.find(marker)
        assert start >= 0, "_editor_actions_mixin.py: def _notify_main() não encontrado"
        snippet = source[start : start + 400]
        assert "winfo_exists" in snippet, (
            "_editor_actions_mixin.py: _notify_main() não checa winfo_exists() antes de "
            "chamar on_save. Pode chamar callback em widget já destruído."
        )
        assert "on_save" in snippet, (
            "_editor_actions_mixin.py: _notify_main() não chama on_save. " "O refresh da lista não será disparado."
        )

    def test_browser_close_after_touch_wrapped_in_try(self) -> None:
        """self.after(100, _touch_and_refresh) deve estar dentro de try/except."""
        source = _src(_EDITOR_ACTIONS)
        # Encontrar o bloco de _on_browser_close e checar que o after(100 está protegido
        marker = "def _on_browser_close"
        start = source.find(marker)
        assert start >= 0, "_editor_actions_mixin.py: _on_browser_close não encontrado"
        snippet = source[start : start + 900]
        # O after(100, _touch_and_refresh) deve estar em try
        idx_after100 = snippet.find("self.after(100, _touch_and_refresh)")
        assert idx_after100 >= 0, (
            "_editor_actions_mixin.py: self.after(100, _touch_and_refresh) não encontrado " "em _on_browser_close."
        )
        # Verificar que existe um 'try:' antes do after(100 dentro do mesmo bloco
        before = snippet[:idx_after100]
        # Último 'try:' antes da linha deve estar presente
        assert "try:" in before, (
            "_editor_actions_mixin.py: self.after(100, _touch_and_refresh) não está "
            "dentro de try/except. Se self já foi destruído, levanta exceção não tratada."
        )

    def test_on_mutation_callback_wires_files_mutated(self) -> None:
        """open_files_browser_v2 deve receber on_mutation que marca _files_mutated."""
        source = _src(_EDITOR_ACTIONS)
        # Verificar que on_mutation= é passado à chamada de open_files_browser_v2
        start = source.find("dlg = open_files_browser_v2(")
        assert start >= 0, "_editor_actions_mixin.py: open_files_browser_v2 não encontrado"
        snippet = source[start : start + 400]
        assert "on_mutation=" in snippet, (
            "_editor_actions_mixin.py: on_mutation não é passado para open_files_browser_v2. "
            "_files_mutated nunca será marcado True e o refresh não disparará."
        )

    def test_browser_v2_on_mutation_param_in_init(self) -> None:
        """UploadsBrowserWindowV2.__init__ deve aceitar on_mutation."""
        source = _src(_BROWSER_V2)
        init_start = source.find("def __init__(")
        assert init_start >= 0
        init_snippet = source[init_start : init_start + 600]
        assert "on_mutation" in init_snippet, (
            "browser_v2.py: __init__ não aceita on_mutation. " "O callback de mutação não pode ser wired."
        )

    def test_browser_v2_on_mutation_called_after_upload(self) -> None:
        """browser_v2 deve chamar _on_mutation após upload bem-sucedido."""
        source = _src(_BROWSER_V2)
        handle_upload_start = source.find("def _handle_upload(")
        assert handle_upload_start >= 0
        # Próxima def (breadcrumb) delimita o fim do método
        next_def = source.find("\n    def ", handle_upload_start + 1)
        snippet = (
            source[handle_upload_start:next_def]
            if next_def > 0
            else source[handle_upload_start : handle_upload_start + 2500]
        )
        assert "_on_mutation" in snippet, (
            "browser_v2.py: _handle_upload não invoca _on_mutation. " "Upload não atualizará 'Última alteração'."
        )

    def test_browser_v2_on_mutation_called_after_delete(self) -> None:
        """browser_v2 deve chamar _on_mutation após exclusão bem-sucedida."""
        source = _src(_BROWSER_V2)
        delete_start = source.find("def _delete_selected(")
        assert delete_start >= 0
        # Próxima def delimita o fim do método
        next_def = source.find("\n    def ", delete_start + 1)
        snippet = source[delete_start:next_def] if next_def > 0 else source[delete_start : delete_start + 3000]
        assert "_on_mutation" in snippet, (
            "browser_v2.py: _delete_selected não invoca _on_mutation. "
            "Exclusão de arquivo não atualizará 'Última alteração'."
        )


if __name__ == "__main__":
    unittest.main()
