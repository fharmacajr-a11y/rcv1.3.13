# -*- coding: utf-8 -*-
"""Testes de regressão para os 3 bugs corrigidos na v1.5.99.

1) Hub: _get_app delega para _get_main_app
2) Lixeira: carregar/restaurar rodam em worker thread
3) Upload: UploadDuplicateError categorizado separadamente de UploadServerError
"""

from __future__ import annotations

import threading
import unittest
from unittest.mock import MagicMock, patch


# ===========================================================================
# 1) HUB — HubScreenView._get_app delegation
# ===========================================================================


class TestHubScreenViewGetApp(unittest.TestCase):
    """Garante que _get_app() encontra _get_main_app no HubScreen."""

    def _make_view(self, hub_screen: MagicMock) -> MagicMock:
        from src.modules.hub.views.hub_screen_view import HubScreenView

        view = MagicMock(spec=[])
        view._hub_screen = hub_screen
        view._get_app = HubScreenView._get_app.__get__(view, type(view))
        return view

    def test_delegates_to_get_main_app(self) -> None:
        """Deve chamar _get_main_app (nome atual no HubScreen)."""
        hub = MagicMock(spec=[])
        hub._get_main_app = MagicMock(return_value="<app>")
        view = self._make_view(hub)

        result = view._get_app()

        hub._get_main_app.assert_called_once()
        self.assertEqual(result, "<app>")

    def test_fallback_to_get_app(self) -> None:
        """Se _get_main_app não existir, deve tentar _get_app legado."""
        hub = MagicMock(spec=[])
        hub._get_app = MagicMock(return_value="<legacy>")
        view = self._make_view(hub)

        result = view._get_app()

        hub._get_app.assert_called_once()
        self.assertEqual(result, "<legacy>")

    def test_returns_none_when_neither(self) -> None:
        """Retorna None se hub_screen não tem nenhum dos métodos."""
        hub = MagicMock(spec=[])
        view = self._make_view(hub)

        result = view._get_app()
        self.assertIsNone(result)

    def test_returns_none_when_no_hub_screen(self) -> None:
        """Retorna None se _hub_screen é None."""
        from src.modules.hub.views.hub_screen_view import HubScreenView

        view = MagicMock(spec=[])
        view._hub_screen = None
        view._get_app = HubScreenView._get_app.__get__(view, type(view))

        self.assertIsNone(view._get_app())


# ===========================================================================
# 2) LIXEIRA — carregar/restaurar executam em worker thread
# ===========================================================================


class TestLixeiraAsync(unittest.TestCase):
    """Valida que carregar() e on_restore() usam threading."""

    @patch("src.modules.lixeira.views.lixeira.listar_clientes_na_lixeira")
    def test_carregar_runs_in_thread(self, mock_listar: MagicMock) -> None:
        """carregar() deve disparar thread, não bloquear main thread."""
        mock_listar.return_value = []

        captured_threads: list[threading.Thread] = []
        orig_thread_init = threading.Thread.__init__

        def spy_init(self_t, *a, **kw):
            orig_thread_init(self_t, *a, **kw)
            captured_threads.append(self_t)

        # Mock mínimo da janela
        win = MagicMock()
        win.winfo_exists.return_value = True
        win.after = MagicMock(side_effect=lambda _, cb: cb())  # executa callback inline

        # Importar e montar o contexto
        import src.modules.lixeira.views.lixeira as lmod

        # Capturar chamadas a Thread para verificar que é usado
        with patch.object(threading, "Thread") as mock_thread_cls:
            mock_thread_inst = MagicMock()
            mock_thread_cls.return_value = mock_thread_inst

            # Precisamos chamar o carregar "de dentro" de abrir_lixeira
            # Mas é mais simples testar via o padrão: montar mocks e chamar
            # ação diretamente. Vamos verificar que abrir_lixeira cria thread.
            with (
                patch.object(lmod, "show_centered"),
                patch.object(lmod, "show_info"),
                patch.object(lmod, "show_error"),
                patch.object(lmod, "show_warning"),
                patch.object(lmod, "ask_yes_no"),
                patch.object(lmod, "make_btn", return_value=MagicMock()),
                patch.object(lmod, "make_btn_icon", return_value=MagicMock()),
                patch.object(lmod, "CTkTableView", return_value=MagicMock()),
                patch.object(lmod.ctk, "CTkToplevel", return_value=win),
                patch.object(lmod.ctk, "CTkFrame", return_value=MagicMock()),
                patch.object(lmod.ctk, "CTkLabel", return_value=MagicMock()),
            ):
                lmod._OPEN_WINDOW = None
                lmod.abrir_lixeira(MagicMock())

            # Thread deve ter sido criada com daemon=True
            mock_thread_cls.assert_called()
            call_kw = mock_thread_cls.call_args
            self.assertTrue(call_kw.kwargs.get("daemon", False))
            mock_thread_inst.start.assert_called_once()


# ===========================================================================
# 3) UPLOAD — UploadDuplicateError separado de ServerError
# ===========================================================================


class TestUploadDuplicateCategorization(unittest.TestCase):
    """UploadDuplicateError deve ir para categoria 'duplicados', não 'server'."""

    def test_duplicate_not_in_server_errors(self) -> None:
        """Duplicatas devem aparecer na seção específica, não como server error."""
        from src.modules.uploads.exceptions import (
            UploadDuplicateError,
            UploadServerError,
            UploadNetworkError,
        )
        from src.modules.uploads.uploader_supabase import _show_upload_summary

        dup_exc = UploadDuplicateError("already exists")
        srv_exc = UploadServerError("500 internal")
        net_exc = UploadNetworkError("connection lost")

        fake_item_dup = MagicMock()
        fake_item_dup.relative_path = "nota_fiscal.pdf"
        fake_item_srv = MagicMock()
        fake_item_srv.relative_path = "contrato.pdf"
        fake_item_net = MagicMock()
        fake_item_net.relative_path = "laudo.pdf"

        failed = [
            (fake_item_dup, dup_exc),
            (fake_item_srv, srv_exc),
            (fake_item_net, net_exc),
        ]

        # Capturar a mensagem exibida
        shown_messages: list[str] = []

        def capture_msg(parent, title, msg):
            shown_messages.append(msg)

        with (
            patch("src.modules.uploads.uploader_supabase.show_error", side_effect=capture_msg),
            patch("src.modules.uploads.uploader_supabase.show_warning", side_effect=capture_msg),
        ):
            _show_upload_summary(
                ok_count=0,
                failed_items=failed,
                parent=MagicMock(),
            )

        self.assertEqual(len(shown_messages), 1)
        msg = shown_messages[0]

        # Duplicata deve estar na seção de "já existentes"
        self.assertIn("nota_fiscal.pdf", msg)
        self.assertIn("já existentes", msg)

        # Server error NÃO deve conter nota_fiscal
        server_section_start = msg.find("Erro no servidor")
        if server_section_start >= 0:
            server_section = msg[server_section_start:]
            self.assertNotIn("nota_fiscal.pdf", server_section)
            self.assertIn("contrato.pdf", server_section)

        # Network error
        self.assertIn("laudo.pdf", msg)

    def test_only_duplicates_shows_correct_message(self) -> None:
        """Quando só há duplicatas, a mensagem deve mencionar 'já existentes'."""
        from src.modules.uploads.exceptions import UploadDuplicateError
        from src.modules.uploads.uploader_supabase import _show_upload_summary

        dup_exc = UploadDuplicateError("already exists")
        fake_item = MagicMock()
        fake_item.relative_path = "dup.pdf"

        shown: list[str] = []

        def capture(parent, title, msg):
            shown.append(msg)

        with (
            patch("src.modules.uploads.uploader_supabase.show_error", side_effect=capture),
        ):
            _show_upload_summary(ok_count=0, failed_items=[(fake_item, dup_exc)], parent=MagicMock())

        self.assertEqual(len(shown), 1)
        self.assertIn("já existentes", shown[0])
        self.assertNotIn("Erro no servidor", shown[0])


if __name__ == "__main__":
    unittest.main()
