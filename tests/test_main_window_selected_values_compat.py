"""Testes de compatibilidade para _get_selected_values e _selected_main_values.

Cobre:
- ClientesV2Frame._get_selected_values() retorna corretamente quando há seleção.
- ClientesV2Frame._get_selected_values() retorna None sem seleção.
- MainWindow._selected_main_values() não lança AttributeError quando o frame
  não implementa _get_selected_values (blindagem via getattr).
"""

from __future__ import annotations

import types
import unittest
from typing import Any
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cliente_row(client_id: str, razao_social: str) -> Any:
    """Cria um ClienteRow simples usando SimpleNamespace (evita importar Tk)."""
    return types.SimpleNamespace(
        id=client_id,
        razao_social=razao_social,
        cnpj="00.000.000/0001-00",
        nome="Teste",
        whatsapp="",
        observacoes="",
        status="ativo",
        ultima_alteracao="",
        search_norm="",
        raw={},
        ultima_alteracao_ts=None,
    )


def _make_frame_stub(**attrs: Any) -> Any:
    """Cria um objeto simples simulando ClientesV2Frame sem instanciar Tk."""
    ns = types.SimpleNamespace(**attrs)
    return ns


def _make_main_window_stub(frame: Any) -> Any:
    """Cria um MainWindow mínimo cujo _main_screen_frame retorna frame."""

    class _MainWindowStub:
        def _main_screen_frame(self) -> Any:  # noqa: ANN001
            return frame

        def _selected_main_values(self) -> tuple | None:  # type: ignore[return]
            frame = self._main_screen_frame()
            if frame is None:
                return None
            fn = getattr(frame, "_get_selected_values", None) or getattr(frame, "get_selected_values", None)
            if not callable(fn):
                return None
            values = fn()
            if values is None:
                return None
            return tuple(values)

    return _MainWindowStub()


# ---------------------------------------------------------------------------
# Classe alvo: _get_selected_values
# ---------------------------------------------------------------------------


class TestGetSelectedValuesLogic(unittest.TestCase):
    """Testa a lógica de _get_selected_values sem instanciar Tk."""

    def _make_frame_with_selection(
        self,
        client_id: int,
        row_map: dict | None = None,
        tree_values: tuple | None = None,
    ) -> Any:
        """Constrói frame stub e adiciona _get_selected_values da implementação real."""
        from src.modules.clientes.ui.view import ClientesV2Frame  # noqa: PLC0415

        frame = object.__new__(ClientesV2Frame)
        # Inicializa os atributos mínimos necessários
        frame._selected_client_id = client_id
        frame._row_data_map = row_map or {}

        # Mock da Treeview se tree_values fornecido
        if tree_values is not None:
            mock_tree = MagicMock()
            mock_tree.selection.return_value = ["item1"]
            mock_tree.item.return_value = tree_values
            frame.tree = mock_tree
        else:
            frame.tree = None

        return frame

    # --- cenários sem seleção -----------------------------------------------

    def test_returns_none_when_no_selection(self) -> None:
        """Sem cliente selecionado (_selected_client_id=None), deve retornar None."""
        from src.modules.clientes.ui.view import ClientesV2Frame  # noqa: PLC0415

        frame = object.__new__(ClientesV2Frame)
        frame._selected_client_id = None
        frame._row_data_map = {}
        frame.tree = None

        result = frame._get_selected_values()
        self.assertIsNone(result)

    def test_returns_none_when_selection_is_zero(self) -> None:
        """_selected_client_id=0 (falsy) → retorna None."""
        from src.modules.clientes.ui.view import ClientesV2Frame  # noqa: PLC0415

        frame = object.__new__(ClientesV2Frame)
        frame._selected_client_id = 0
        frame._row_data_map = {}
        frame.tree = None

        result = frame._get_selected_values()
        self.assertIsNone(result)

    # --- via Treeview --------------------------------------------------------

    def test_returns_tree_values_when_tree_has_selection(self) -> None:
        """Quando a Treeview tem seleção ativa, deve retornar os valores da linha."""
        tree_values = ("42", "Acme Corp", "00.000.000/0001-00")
        frame = self._make_frame_with_selection(client_id=42, tree_values=tree_values)

        result = frame._get_selected_values()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "42")
        self.assertEqual(result[1], "Acme Corp")

    def test_tree_values_castable_to_int(self) -> None:
        """values[0] retornado deve ser conversível para int (contrato _excluir_cliente)."""
        tree_values = ("123", "Beta SA")
        frame = self._make_frame_with_selection(client_id=123, tree_values=tree_values)

        result = frame._get_selected_values()
        self.assertIsNotNone(result)
        self.assertEqual(int(result[0]), 123)

    # --- fallback via _row_data_map -----------------------------------------

    def test_fallback_row_data_map_when_tree_is_none(self) -> None:
        """Sem tree disponível, usa _row_data_map para reconstruir tupla."""
        row = _make_cliente_row("7", "Delta Ltda")
        from src.modules.clientes.ui.view import ClientesV2Frame  # noqa: PLC0415

        frame = object.__new__(ClientesV2Frame)
        frame._selected_client_id = 7
        frame._row_data_map = {"iid1": row}
        frame.tree = None

        result = frame._get_selected_values()
        self.assertIsNotNone(result)
        self.assertEqual(int(result[0]), 7)
        self.assertEqual(result[1], "Delta Ltda")

    def test_fallback_returns_minimal_tuple_when_row_not_in_map(self) -> None:
        """Se o ID não está no map, retorna tupla mínima com o ID."""
        from src.modules.clientes.ui.view import ClientesV2Frame  # noqa: PLC0415

        frame = object.__new__(ClientesV2Frame)
        frame._selected_client_id = 99
        frame._row_data_map = {}  # mapa vazio
        frame.tree = None

        result = frame._get_selected_values()
        self.assertIsNotNone(result)
        self.assertEqual(int(result[0]), 99)

    def test_fallback_tree_no_selection(self) -> None:
        """Se tree existe mas sem seleção ativa, deve cair no fallback do mapa."""
        row = _make_cliente_row("5", "Epsilon Eireli")
        from src.modules.clientes.ui.view import ClientesV2Frame  # noqa: PLC0415

        frame = object.__new__(ClientesV2Frame)
        frame._selected_client_id = 5
        frame._row_data_map = {"iid1": row}

        mock_tree = MagicMock()
        mock_tree.selection.return_value = []  # nada selecionado na Treeview
        frame.tree = mock_tree

        result = frame._get_selected_values()
        self.assertIsNotNone(result)
        self.assertEqual(int(result[0]), 5)
        self.assertEqual(result[1], "Epsilon Eireli")


# ---------------------------------------------------------------------------
# Classe alvo: _selected_main_values (blindagem)
# ---------------------------------------------------------------------------


class TestSelectedMainValuesHardening(unittest.TestCase):
    """Testa que _selected_main_values não levanta AttributeError."""

    def test_no_error_when_frame_lacks_method(self) -> None:
        """Frame sem _get_selected_values nem get_selected_values → retorna None sem crash."""
        frame = _make_frame_stub()  # sem nenhum método de seleção
        mw = _make_main_window_stub(frame)

        result = mw._selected_main_values()
        self.assertIsNone(result)

    def test_uses_underscore_variant(self) -> None:
        """Frame com _get_selected_values deve ser chamado corretamente."""
        frame = _make_frame_stub(_get_selected_values=lambda: ("10", "Zeta Corp"))
        mw = _make_main_window_stub(frame)

        result = mw._selected_main_values()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "10")
        self.assertEqual(result[1], "Zeta Corp")

    def test_uses_public_variant_as_fallback(self) -> None:
        """Frame com get_selected_values (sem underscore) também é aceito."""
        frame = _make_frame_stub(get_selected_values=lambda: ("20", "Eta Inc"))
        mw = _make_main_window_stub(frame)

        result = mw._selected_main_values()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "20")

    def test_returns_none_when_frame_is_none(self) -> None:
        """_main_screen_frame() retornando None → _selected_main_values retorna None."""
        mw = _make_main_window_stub(None)

        result = mw._selected_main_values()
        self.assertIsNone(result)

    def test_returns_none_when_fn_returns_none(self) -> None:
        """Se a função existe mas retorna None, _selected_main_values retorna None."""
        frame = _make_frame_stub(_get_selected_values=lambda: None)
        mw = _make_main_window_stub(frame)

        result = mw._selected_main_values()
        self.assertIsNone(result)

    def test_result_is_tuple(self) -> None:
        """O resultado deve sempre ser uma tuple (não lista ou outro iterável)."""
        frame = _make_frame_stub(_get_selected_values=lambda: ["30", "Theta SA"])
        mw = _make_main_window_stub(frame)

        result = mw._selected_main_values()
        self.assertIsInstance(result, tuple)

    def test_priority_underscore_over_public(self) -> None:
        """Quando ambos existem, _get_selected_values tem prioridade."""
        frame = _make_frame_stub(
            _get_selected_values=lambda: ("1", "priority"),
            get_selected_values=lambda: ("2", "fallback"),
        )
        mw = _make_main_window_stub(frame)

        result = mw._selected_main_values()
        self.assertEqual(result[1], "priority")


if __name__ == "__main__":
    unittest.main()
