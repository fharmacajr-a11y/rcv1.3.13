# -*- coding: utf-8 -*-
"""Teste de regressão: modo lixeira persiste ao mudar ordenação/status/limpar busca.

Bug original: _on_order_changed / _on_status_changed / _on_clear_search chamavam
load_async() sem show_trash, que tinha default False — perdendo o modo lixeira.

Fix: load_async agora usa show_trash: bool | None = None e resolve para
self._trash_mode quando omitido.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class _FakeToolbar:
    """Stub mínimo para toolbar."""

    def get_search_text(self) -> str:
        return ""

    def get_order(self) -> str:
        return "Razão Social (A→Z)"

    def get_status(self) -> str:
        return ""

    def clear_search(self) -> None:
        pass


class TestTrashFilterPersistence(unittest.TestCase):
    """Valida que load_async preserva _trash_mode quando show_trash não é passado."""

    def _make_view(self, trash_mode: bool = True) -> MagicMock:
        """Cria um MagicMock que simula ClientesV2Frame com os atributos necessários."""
        from src.modules.clientes.ui.view import ClientesV2Frame

        view = MagicMock(spec=[])
        view._trash_mode = trash_mode
        view._load_job = None
        view._load_gen = 0
        view._vm = MagicMock()
        view.toolbar = _FakeToolbar()
        view.after = MagicMock()  # Tk.after — não executa callbacks no teste
        view.after_cancel = MagicMock()
        # Bind dos métodos reais que queremos testar
        view.load_async = ClientesV2Frame.load_async.__get__(view, type(view))
        view._on_order_changed = ClientesV2Frame._on_order_changed.__get__(view, type(view))
        view._on_status_changed = ClientesV2Frame._on_status_changed.__get__(view, type(view))
        view._on_clear_search = ClientesV2Frame._on_clear_search.__get__(view, type(view))
        view._on_search = ClientesV2Frame._on_search.__get__(view, type(view))
        return view

    @patch("threading.Thread")
    def test_order_change_preserves_trash_mode(self, mock_thread_cls: MagicMock) -> None:
        """Mudar ordenação no modo lixeira deve manter show_trash=True."""
        mock_thread_cls.return_value = MagicMock()
        view = self._make_view(trash_mode=True)

        view._on_order_changed("Nome (Z→A)")

        # A thread foi criada — capturar o target e executar
        thread_call = mock_thread_cls.call_args
        fetch_fn = thread_call.kwargs.get("target") or thread_call[1].get("target")
        fetch_fn()

        # Verificar que refresh_from_service foi chamado com trash=True
        view._vm.refresh_from_service.assert_called_once()
        call_kwargs = view._vm.refresh_from_service.call_args
        self.assertTrue(
            call_kwargs.kwargs.get("trash", call_kwargs[1].get("trash") if len(call_kwargs) > 1 else None),
            "refresh_from_service deve receber trash=True quando _trash_mode=True",
        )

    @patch("threading.Thread")
    def test_status_change_preserves_trash_mode(self, mock_thread_cls: MagicMock) -> None:
        """Mudar filtro de status no modo lixeira deve manter show_trash=True."""
        mock_thread_cls.return_value = MagicMock()
        view = self._make_view(trash_mode=True)

        view._on_status_changed("Novo Cliente")

        thread_call = mock_thread_cls.call_args
        fetch_fn = thread_call.kwargs.get("target") or thread_call[1].get("target")
        fetch_fn()

        view._vm.refresh_from_service.assert_called_once()
        call_kwargs = view._vm.refresh_from_service.call_args
        self.assertTrue(
            call_kwargs.kwargs.get("trash", call_kwargs[1].get("trash") if len(call_kwargs) > 1 else None),
            "refresh_from_service deve receber trash=True quando _trash_mode=True",
        )

    @patch("threading.Thread")
    def test_clear_search_preserves_trash_mode(self, mock_thread_cls: MagicMock) -> None:
        """Limpar busca no modo lixeira deve manter show_trash=True."""
        mock_thread_cls.return_value = MagicMock()
        view = self._make_view(trash_mode=True)

        view._on_clear_search()

        thread_call = mock_thread_cls.call_args
        fetch_fn = thread_call.kwargs.get("target") or thread_call[1].get("target")
        fetch_fn()

        view._vm.refresh_from_service.assert_called_once()
        call_kwargs = view._vm.refresh_from_service.call_args
        self.assertTrue(
            call_kwargs.kwargs.get("trash", call_kwargs[1].get("trash") if len(call_kwargs) > 1 else None),
            "refresh_from_service deve receber trash=True quando _trash_mode=True",
        )

    @patch("threading.Thread")
    def test_active_mode_stays_active(self, mock_thread_cls: MagicMock) -> None:
        """No modo ativo (_trash_mode=False), load_async deve passar trash=False."""
        mock_thread_cls.return_value = MagicMock()
        view = self._make_view(trash_mode=False)

        view._on_order_changed("Nome (A→Z)")

        thread_call = mock_thread_cls.call_args
        fetch_fn = thread_call.kwargs.get("target") or thread_call[1].get("target")
        fetch_fn()

        view._vm.refresh_from_service.assert_called_once()
        call_kwargs = view._vm.refresh_from_service.call_args
        self.assertFalse(
            call_kwargs.kwargs.get("trash", call_kwargs[1].get("trash") if len(call_kwargs) > 1 else None),
            "refresh_from_service deve receber trash=False quando _trash_mode=False",
        )

    @patch("threading.Thread")
    def test_search_preserves_trash_mode(self, mock_thread_cls: MagicMock) -> None:
        """Buscar no modo lixeira deve manter show_trash=True."""
        mock_thread_cls.return_value = MagicMock()
        view = self._make_view(trash_mode=True)

        view._on_search("farmacia")

        thread_call = mock_thread_cls.call_args
        fetch_fn = thread_call.kwargs.get("target") or thread_call[1].get("target")
        fetch_fn()

        view._vm.refresh_from_service.assert_called_once()
        call_kwargs = view._vm.refresh_from_service.call_args
        self.assertTrue(
            call_kwargs.kwargs.get("trash", call_kwargs[1].get("trash") if len(call_kwargs) > 1 else None),
            "refresh_from_service deve receber trash=True quando _trash_mode=True",
        )


if __name__ == "__main__":
    unittest.main()
