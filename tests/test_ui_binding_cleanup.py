"""Fase 13 — Testes de cleanup de bindings (BindingTracker + padrões de uso).

Todos os testes são headless: sem Tcl/Display.
Usa FakeWidget para simular a API de bind/unbind do Tkinter.

Cobertura:
  Part 1 — BindingTracker: bind / bind_all / bind_class / unbind_all / idempotência
  Part 2 — Padrão ScrollableFrame: destroy chama _on_leave (cleanup bind_all)
  Part 3 — Padrão Placeholder: bind_all → unbind_all no destroy
  Part 4 — Padrão CTkSplitPane: sash binds → unbind no destroy
  Part 5 — Padrão CTkAutocompleteEntry: entry binds → unbind no destroy
"""

from __future__ import annotations

import unittest
from typing import Any


class FakeTclError(Exception):
    """Substituto de tk.TclError nos testes."""


class FakeWidget:
    """Simula a API de bind/unbind do Tkinter sem Tcl."""

    def __init__(self, name: str = "widget") -> None:
        self.name = name
        self._id_counter = 0
        # sequência → lista de funcids ativos
        self._bindings: dict[str, list[str]] = {}
        # registro histórico de unbinds para assertions
        self.unbind_calls: list[tuple[str, str | None]] = []
        self.unbind_all_calls: list[str] = []
        self.unbind_class_calls: list[tuple[str, str]] = []

    def bind(self, sequence: str, func: Any, add: Any = None) -> str:
        self._id_counter += 1
        funcid = f"id{self._id_counter}"
        self._bindings.setdefault(sequence, []).append(funcid)
        return funcid

    def bind_all(self, sequence: str, func: Any, add: Any = None) -> str:
        self._id_counter += 1
        funcid = f"gid{self._id_counter}"
        return funcid

    def bind_class(self, classname: str, sequence: str, func: Any, add: Any = None) -> str:
        self._id_counter += 1
        funcid = f"cid{self._id_counter}"
        return funcid

    def unbind(self, sequence: str, funcid: str | None = None) -> None:
        self.unbind_calls.append((sequence, funcid))
        if sequence in self._bindings and funcid in self._bindings[sequence]:
            self._bindings[sequence].remove(funcid)

    def unbind_all(self, sequence: str) -> None:
        self.unbind_all_calls.append(sequence)

    def unbind_class(self, classname: str, sequence: str) -> None:
        self.unbind_class_calls.append((classname, sequence))

    def active_bindings(self, sequence: str) -> list[str]:
        return list(self._bindings.get(sequence, []))


# ---------------------------------------------------------------------------
# Import BindingTracker (sem stub de tkinter — usa installação real)
# ---------------------------------------------------------------------------

from src.ui.utils.binding_tracker import BindingTracker  # noqa: E402


# ---------------------------------------------------------------------------
# Part 1 — BindingTracker unit tests
# ---------------------------------------------------------------------------


class TestBindingTrackerBind(unittest.TestCase):
    """Testa BindingTracker.bind()."""

    def setUp(self) -> None:
        self.w = FakeWidget()
        self.bt = BindingTracker()

    def test_bind_returns_funcid(self) -> None:
        fid = self.bt.bind(self.w, "<KeyPress>", lambda e: None)
        self.assertTrue(fid.startswith("id"))

    def test_bind_increments_len(self) -> None:
        self.bt.bind(self.w, "<KeyPress>", lambda e: None)
        self.bt.bind(self.w, "<Return>", lambda e: None)
        self.assertEqual(len(self.bt), 2)

    def test_unbind_all_calls_unbind_with_funcid(self) -> None:
        fid = self.bt.bind(self.w, "<KeyPress>", lambda e: None)
        self.bt.unbind_all()
        self.assertIn(("<KeyPress>", fid), self.w.unbind_calls)

    def test_unbind_all_clears_entries(self) -> None:
        self.bt.bind(self.w, "<KeyPress>", lambda e: None)
        self.bt.unbind_all()
        self.assertEqual(len(self.bt), 0)

    def test_multiple_bindings_all_unbound(self) -> None:
        _fid1 = self.bt.bind(self.w, "<KeyPress>", lambda e: None)
        _fid2 = self.bt.bind(self.w, "<Return>", lambda e: None)
        _fid3 = self.bt.bind(self.w, "<Escape>", lambda e: None)
        self.bt.unbind_all()
        seqs = [seq for seq, _ in self.w.unbind_calls]
        self.assertIn("<KeyPress>", seqs)
        self.assertIn("<Return>", seqs)
        self.assertIn("<Escape>", seqs)

    def test_unbind_order_reversed(self) -> None:
        """Unbind deve acontecer em ordem inversa ao bind."""
        recorded: list[str] = []
        w1 = FakeWidget("w1")
        w2 = FakeWidget("w2")
        self.bt.bind(w1, "<A>", lambda e: None)
        self.bt.bind(w2, "<B>", lambda e: None)

        orig_w1 = w1.unbind
        orig_w2 = w2.unbind

        def _track_w1(seq, fid=None):
            recorded.append("w1")
            orig_w1(seq, fid)

        def _track_w2(seq, fid=None):
            recorded.append("w2")
            orig_w2(seq, fid)

        w1.unbind = _track_w1  # type: ignore[method-assign]
        w2.unbind = _track_w2  # type: ignore[method-assign]
        self.bt.unbind_all()
        self.assertEqual(recorded, ["w2", "w1"])


class TestBindingTrackerIdempotence(unittest.TestCase):
    def test_unbind_all_twice_no_error(self) -> None:
        w = FakeWidget()
        bt = BindingTracker()
        bt.bind(w, "<KeyPress>", lambda e: None)
        bt.unbind_all()
        bt.unbind_all()  # segunda chamada não deve lançar

    def test_empty_unbind_all_no_error(self) -> None:
        bt = BindingTracker()
        bt.unbind_all()  # nunca teve nada registrado

    def test_unbind_all_survives_tclerror(self) -> None:
        w = FakeWidget()
        bt = BindingTracker()
        bt.bind(w, "<KeyPress>", lambda e: None)

        # Simular widget destruído: unbind lança TclError
        def _bad_unbind(seq, fid=None):
            raise FakeTclError("widget destroyed")

        w.unbind = _bad_unbind  # type: ignore[method-assign]
        bt.unbind_all()  # não deve propagar
        self.assertEqual(len(bt), 0)


class TestBindingTrackerBindAll(unittest.TestCase):
    def setUp(self) -> None:
        self.w = FakeWidget()
        self.bt = BindingTracker()

    def test_bind_all_stored(self) -> None:
        self.bt.bind_all(self.w, "<MouseWheel>", lambda e: None)
        self.assertEqual(len(self.bt), 1)

    def test_bind_all_unbind_all_calls_unbind_all_on_widget(self) -> None:
        self.bt.bind_all(self.w, "<MouseWheel>", lambda e: None)
        self.bt.unbind_all()
        self.assertIn("<MouseWheel>", self.w.unbind_all_calls)

    def test_bind_all_cleared_after_unbind(self) -> None:
        self.bt.bind_all(self.w, "<MouseWheel>", lambda e: None)
        self.bt.unbind_all()
        self.assertEqual(len(self.bt), 0)


class TestBindingTrackerBindClass(unittest.TestCase):
    def setUp(self) -> None:
        self.w = FakeWidget()
        self.bt = BindingTracker()

    def test_bind_class_stored(self) -> None:
        self.bt.bind_class(self.w, "Entry", "<Tab>", lambda e: None)
        self.assertEqual(len(self.bt), 1)

    def test_bind_class_cleanup_calls_unbind_class(self) -> None:
        self.bt.bind_class(self.w, "Entry", "<Tab>", lambda e: None)
        self.bt.unbind_all()
        self.assertIn(("Entry", "<Tab>"), self.w.unbind_class_calls)

    def test_bind_class_cleared_after_unbind(self) -> None:
        self.bt.bind_class(self.w, "Entry", "<Tab>", lambda e: None)
        self.bt.unbind_all()
        self.assertEqual(len(self.bt), 0)


# ---------------------------------------------------------------------------
# Part 2 — ScrollableFrame: destroy chama _on_leave (cleanup bind_all)
# ---------------------------------------------------------------------------


class TestScrollableFrameDestroyPattern(unittest.TestCase):
    """Testa o padrão onde <Destroy> do canvas chama _on_leave para remover bind_all."""

    class _FakeCanvas(FakeWidget):
        pass

    class _FakeScrollableFrame:
        def __init__(self) -> None:
            self.canvas = TestScrollableFrameDestroyPattern._FakeCanvas("canvas")
            self._mousewheel_bound = False
            # Registrar destroy handler (replica do código real)
            self.canvas.bind("<Destroy>", self._on_canvas_destroy)

        def _on_enter(self, event=None) -> None:
            self._mousewheel_bound = True

        def _on_leave(self, event=None) -> None:
            if self._mousewheel_bound:
                self.canvas.unbind_all("<MouseWheel>")
                self.canvas.unbind_all("<Button-4>")
                self.canvas.unbind_all("<Button-5>")
                self._mousewheel_bound = False

        def _on_canvas_destroy(self, event=None) -> None:
            self._on_leave()

        def simulate_destroy(self) -> None:
            """Simula o evento Destroy chegando no canvas."""
            self._on_canvas_destroy()

    def test_destroy_calls_on_leave(self) -> None:
        sf = self._FakeScrollableFrame()
        sf._on_enter()  # ativar mousewheel
        sf.simulate_destroy()
        self.assertIn("<MouseWheel>", sf.canvas.unbind_all_calls)
        self.assertIn("<Button-4>", sf.canvas.unbind_all_calls)
        self.assertIn("<Button-5>", sf.canvas.unbind_all_calls)

    def test_destroy_without_enter_is_noop(self) -> None:
        sf = self._FakeScrollableFrame()
        sf.simulate_destroy()  # nenhum bind_all ativo — não deve lançar
        self.assertEqual(sf.canvas.unbind_all_calls, [])

    def test_destroy_idempotent(self) -> None:
        sf = self._FakeScrollableFrame()
        sf._on_enter()
        sf.simulate_destroy()
        sf.simulate_destroy()  # segunda vez sem erros
        # Deve ter chamado unbind_all apenas uma vez (mousewheel_bound resetado)
        self.assertEqual(sf.canvas.unbind_all_calls.count("<MouseWheel>"), 1)


# ---------------------------------------------------------------------------
# Part 3 — Placeholder: bind_all + cleanup no destroy
# ---------------------------------------------------------------------------


class TestPlaceholderBindAllPattern(unittest.TestCase):
    """Testa o padrão bind_all(<Escape>) com cleanup via BindingTracker."""

    class _FakePlaceholderFrame:
        def __init__(self, root_widget: FakeWidget) -> None:
            self._bt = BindingTracker()
            self._root = root_widget
            self._on_back_called = False

        def setup_escape(self) -> None:
            self._bt.bind_all(self._root, "<Escape>", lambda e: self._on_back())

        def _on_back(self) -> None:
            self._on_back_called = True

        def on_destroy(self) -> None:
            self._bt.unbind_all()

    def test_on_destroy_unbinds_escape(self) -> None:
        root = FakeWidget("root")
        ph = self._FakePlaceholderFrame(root)
        ph.setup_escape()
        ph.on_destroy()
        self.assertIn("<Escape>", root.unbind_all_calls)

    def test_bt_empty_after_destroy(self) -> None:
        root = FakeWidget("root")
        ph = self._FakePlaceholderFrame(root)
        ph.setup_escape()
        ph.on_destroy()
        self.assertEqual(len(ph._bt), 0)

    def test_double_destroy_no_error(self) -> None:
        root = FakeWidget("root")
        ph = self._FakePlaceholderFrame(root)
        ph.setup_escape()
        ph.on_destroy()
        ph.on_destroy()  # idempotente

    def test_destroy_without_setup_no_error(self) -> None:
        root = FakeWidget("root")
        ph = self._FakePlaceholderFrame(root)
        ph.on_destroy()  # sem setup — não deve lançar


# ---------------------------------------------------------------------------
# Part 4 — CTkSplitPane: sash binds via BindingTracker + cleanup on destroy
# ---------------------------------------------------------------------------


class TestSplitPaneSashBindPattern(unittest.TestCase):
    """Testa o padrão de bind do sash com rastreamento e cleanup."""

    class _FakeSplitPane:
        def __init__(self) -> None:
            self._sash = FakeWidget("sash")
            self._bt = BindingTracker()
            self._setup_sash_binds()

        def _setup_sash_binds(self) -> None:
            self._bt.bind(self._sash, "<ButtonPress-1>", lambda e: None)
            self._bt.bind(self._sash, "<B1-Motion>", lambda e: None)
            self._bt.bind(self._sash, "<ButtonRelease-1>", lambda e: None)
            self._bt.bind(self._sash, "<Enter>", lambda e: None)
            self._bt.bind(self._sash, "<Leave>", lambda e: None)

        def on_destroy(self) -> None:
            self._bt.unbind_all()

    def test_five_binds_registered(self) -> None:
        sp = self._FakeSplitPane()
        self.assertEqual(len(sp._bt), 5)

    def test_destroy_unbinds_all_sash_sequences(self) -> None:
        sp = self._FakeSplitPane()
        sp.on_destroy()
        unbound_seqs = {seq for seq, _ in sp._sash.unbind_calls}
        self.assertIn("<ButtonPress-1>", unbound_seqs)
        self.assertIn("<B1-Motion>", unbound_seqs)
        self.assertIn("<ButtonRelease-1>", unbound_seqs)
        self.assertIn("<Enter>", unbound_seqs)
        self.assertIn("<Leave>", unbound_seqs)

    def test_bt_empty_after_destroy(self) -> None:
        sp = self._FakeSplitPane()
        sp.on_destroy()
        self.assertEqual(len(sp._bt), 0)

    def test_double_destroy_no_error(self) -> None:
        sp = self._FakeSplitPane()
        sp.on_destroy()
        sp.on_destroy()  # idempotente

    def test_destroy_survives_sash_already_gone(self) -> None:
        sp = self._FakeSplitPane()

        def _raise(*args, **kwargs):
            raise FakeTclError("sash already destroyed")

        sp._sash.unbind = _raise  # type: ignore[method-assign]
        sp.on_destroy()  # TclError deve ser silenciado


# ---------------------------------------------------------------------------
# Part 5 — CTkAutocompleteEntry: entry binds + cleanup no destroy
# ---------------------------------------------------------------------------


class TestAutocompleteEntryBindPattern(unittest.TestCase):
    """Testa o padrão de bind do entry interno com rastreamento e cleanup."""

    _SEQUENCES = ("<KeyRelease>", "<Down>", "<Up>", "<Return>", "<Escape>", "<FocusOut>")

    class _FakeAutocompleteEntry:
        def __init__(self) -> None:
            self.entry = FakeWidget("entry")
            self._bt = BindingTracker()
            for seq in TestAutocompleteEntryBindPattern._SEQUENCES:
                self._bt.bind(self.entry, seq, lambda e: None)

        def destroy(self) -> None:
            self._bt.unbind_all()

    def test_six_binds_registered(self) -> None:
        w = self._FakeAutocompleteEntry()
        self.assertEqual(len(w._bt), 6)

    def test_destroy_unbinds_all_sequences(self) -> None:
        w = self._FakeAutocompleteEntry()
        w.destroy()
        unbound_seqs = {seq for seq, _ in w.entry.unbind_calls}
        for seq in self._SEQUENCES:
            self.assertIn(seq, unbound_seqs, f"Sequência {seq} não foi desfeita")

    def test_bt_empty_after_destroy(self) -> None:
        w = self._FakeAutocompleteEntry()
        w.destroy()
        self.assertEqual(len(w._bt), 0)

    def test_double_destroy_no_error(self) -> None:
        w = self._FakeAutocompleteEntry()
        w.destroy()
        w.destroy()  # idempotente

    def test_funcid_used_in_unbind(self) -> None:
        """Verifica que o funcid correto é passado para unbind (não None)."""
        w = self._FakeAutocompleteEntry()
        w.destroy()
        for seq, fid in w.entry.unbind_calls:
            self.assertIsNotNone(fid, f"unbind({seq!r}) chamado sem funcid")


if __name__ == "__main__":
    unittest.main(verbosity=2)
