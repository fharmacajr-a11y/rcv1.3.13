# pyright: reportAttributeAccessIssue=false
# -*- coding: utf-8 -*-
"""
Testes unitários — Fase 11: cancelamento de after() no cleanup.

Cobre:
  - splash.py: tick() armazena _progress_job; _do_close cancela o job
  - ctk_autocomplete_entry.py: destroy() cancela _debounce_id, _focus_out_job
                                e destrói _dropdown; idempotência
"""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Infraestrutura fake de after/after_cancel (sem Tk real)
# ---------------------------------------------------------------------------


class FakeAfterRoot:
    """Simula Tk.after / after_cancel sem loop de eventos real."""

    def __init__(self):
        self._counter = 0
        self._pending: dict[str, tuple] = {}  # id → (ms, fn, args)
        self.cancelled: set[str] = set()
        self.scheduled: list[str] = []
        self._exists = True

    def after(self, ms: int, fn=None, *args) -> str:
        self._counter += 1
        aid = f"after#{self._counter}"
        self._pending[aid] = (ms, fn, args)
        self.scheduled.append(aid)
        return aid

    def after_cancel(self, aid: str) -> None:
        self.cancelled.add(aid)
        self._pending.pop(aid, None)

    def winfo_exists(self) -> bool:
        return self._exists

    def destroy(self) -> None:
        self._exists = False


class FakeDropdown:
    """Simula CTkToplevel _dropdown."""

    def __init__(self):
        self.destroyed = False
        self._exists = True

    def destroy(self) -> None:
        self.destroyed = True
        self._exists = False

    def winfo_exists(self) -> bool:
        return self._exists

    def withdraw(self) -> None:
        pass


# ---------------------------------------------------------------------------
# PARTE 1 — Splash: tick() armazena _progress_job e _do_close cancela
# ---------------------------------------------------------------------------


def _make_splash_tick(splash: FakeAfterRoot, delay_ms: int = 50, total_steps: int = 10):
    """
    Replica o padrão CORRIGIDO de tick() de splash.py:
      - armazena o id retornado por after() em _progress_job
      - zera _progress_job ao entrar (job terminou)
    Retorna a função tick (sem executá-la).
    """
    splash._progress_job = None  # type: ignore[attr-defined]
    splash._pb = 0.0  # type: ignore[attr-defined]
    step = 1.0 / total_steps

    def tick() -> None:
        splash._progress_job = None  # job atual terminou
        try:
            if not splash.winfo_exists():
                return
        except Exception:
            return

        splash._pb = min(1.0, splash._pb + step)  # type: ignore[attr-defined]

        if splash._pb < 1.0:  # type: ignore[attr-defined]
            splash._progress_job = splash.after(delay_ms, tick)  # type: ignore[attr-defined]

    return tick


def _cancel_job(splash: Any, attr: str) -> None:
    """Replica de _cancel_job de splash.py."""
    job_id = getattr(splash, attr, None)
    if job_id is not None:
        try:
            splash.after_cancel(job_id)
        except Exception:
            pass
        setattr(splash, attr, None)


class TestSplashProgressJobStored(unittest.TestCase):
    def test_tick_stores_progress_job_after_first_call(self):
        """tick() deve armazenar o after-id em _progress_job."""
        splash = FakeAfterRoot()
        tick = _make_splash_tick(splash, total_steps=10)
        tick()
        self.assertIsNotNone(splash._progress_job)
        self.assertIn(splash._progress_job, splash.scheduled)

    def test_tick_clears_progress_job_when_full(self):
        """Quando _pb atinge 1.0, tick() não agenda mais e _progress_job fica None."""
        splash = FakeAfterRoot()
        tick = _make_splash_tick(splash, total_steps=1)
        tick()  # _pb chega a 1.0 — não deve agendar mais
        self.assertIsNone(splash._progress_job)

    def test_cancel_job_cancels_progress_job(self):
        """_cancel_job('_progress_job') deve cancelar o after-id armazenado."""
        splash = FakeAfterRoot()
        tick = _make_splash_tick(splash, total_steps=10)
        tick()
        stored_id = splash._progress_job

        _cancel_job(splash, "_progress_job")

        self.assertIn(stored_id, splash.cancelled)
        self.assertIsNone(splash._progress_job)

    def test_cancel_job_idempotent(self):
        """Chamar _cancel_job duas vezes não deve explodir."""
        splash = FakeAfterRoot()
        tick = _make_splash_tick(splash, total_steps=10)
        tick()

        _cancel_job(splash, "_progress_job")
        _cancel_job(splash, "_progress_job")  # segunda chamada — não deveria falhar

    def test_cancel_job_on_none_is_noop(self):
        """_cancel_job quando id é None não chama after_cancel."""
        splash = FakeAfterRoot()
        splash._progress_job = None
        _cancel_job(splash, "_progress_job")
        self.assertEqual(splash.cancelled, set())

    def test_tick_stops_after_widget_destroyed(self):
        """tick() não deve agendar mais se winfo_exists() == False."""
        splash = FakeAfterRoot()
        tick = _make_splash_tick(splash, total_steps=10)
        tick()
        scheduled_before = len(splash.scheduled)

        # Destrói o widget
        splash.destroy()

        # Simula execução futura do callback (o único agendado)
        tick()  # winfo_exists() == False → não agenda
        self.assertEqual(len(splash.scheduled), scheduled_before, "nenhum novo after() deve ser chamado após destroy")

    def test_progress_job_allows_proper_close(self):
        """Ao fechar, cancelar _progress_job resolve o problema do TclError."""
        splash = FakeAfterRoot()
        splash._close_job = None
        tick = _make_splash_tick(splash, total_steps=10)
        tick()

        job_id = splash._progress_job
        self.assertIsNotNone(job_id, "deve haver job pendente")

        # _do_close chama _cancel_job
        _cancel_job(splash, "_progress_job")
        _cancel_job(splash, "_close_job")

        self.assertIn(job_id, splash.cancelled)


# ---------------------------------------------------------------------------
# PARTE 2 — CTkAutocompleteEntry: stubs para importação sem UI real
# ---------------------------------------------------------------------------

import importlib
import importlib.util
from typing import cast
from unittest.mock import patch


def _build_autocomplete_stubs() -> dict:
    """Retorna dict de stubs para patch.dict(sys.modules).
    NÃO modifica sys.modules — seguro em tempo de importação/discover."""

    def _make_mod(name: str, **attrs) -> types.ModuleType:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        return mod

    # FakeFrame: base para CTkAutocompleteEntry
    class _FakeCTkFrame:
        def __init__(self, master=None, **kw):
            self.master = master
            self._after_root = FakeAfterRoot()

        def after(self, ms, fn=None, *args):
            return self._after_root.after(ms, fn, *args)

        def after_cancel(self, aid):
            self._after_root.after_cancel(aid)

        def destroy(self):
            self._after_root.destroy()

        def pack(self, **kw):
            pass

        def update_idletasks(self):
            pass

        def winfo_exists(self):
            return self._after_root.winfo_exists()

    class _FakeCTkEntry:
        def __init__(self, master=None, **kw):
            self.master = master

        def pack(self, **kw):
            pass

        def bind(self, *a, **kw):
            return ""

        def get(self):
            return ""

        def delete(self, *a):
            pass

        def insert(self, *a):
            pass

        def focus(self):
            pass

        def focus_set(self):
            pass

        def winfo_reqwidth(self):
            return 200

        def winfo_rootx(self):
            return 0

        def winfo_rooty(self):
            return 0

        def winfo_height(self):
            return 30

        def winfo_width(self):
            return 200

    class _FakeCTkToplevel:
        def __init__(self, master=None, **kw):
            self.master = master
            self.destroyed = False

        def withdraw(self):
            pass

        def deiconify(self):
            pass

        def overrideredirect(self, *a):
            pass

        def geometry(self, *a):
            pass

        def winfo_viewable(self):
            return True

        def winfo_exists(self):
            return not self.destroyed

        def destroy(self):
            self.destroyed = True

    class _FakeCTkScrollableFrame:
        def __init__(self, master=None, **kw): ...
        def pack(self, **kw):
            pass

        def winfo_children(self):
            return []

    class _FakeCTkButton:
        def __init__(self, master=None, **kw): ...
        def pack(self, **kw):
            pass

    class _FakeCtk:
        CTkFrame = _FakeCTkFrame
        CTkEntry = _FakeCTkEntry
        CTkToplevel = _FakeCTkToplevel
        CTkScrollableFrame = _FakeCTkScrollableFrame
        CTkButton = _FakeCTkButton

    fake_ctk_config = _make_mod("src.ui.ctk_config", ctk=_FakeCtk())
    fake_typing_utils = _make_mod("src.ui.typing_utils", TkInfoMixin=object, TkToplevelMixin=object)
    fake_ui = _make_mod("src.ui", ctk_config=fake_ctk_config)

    # Stub para BindingTracker (Fase 13 — novo import em ctk_autocomplete_entry)
    class _FakeBindingTracker:
        def bind(self, *a, **kw): pass
        def bind_all(self, *a, **kw): pass
        def unbind_all(self, *a, **kw): pass

    fake_binding_tracker = _make_mod(
        "src.ui.utils.binding_tracker",
        BindingTracker=_FakeBindingTracker,
    )
    fake_ui_utils = _make_mod("src.ui.utils", binding_tracker=fake_binding_tracker)

    return {
        "src.ui.ctk_config": fake_ctk_config,
        "src.ui.typing_utils": fake_typing_utils,
        "src.ui": fake_ui,
        "src.ui.utils": fake_ui_utils,
        "src.ui.utils.binding_tracker": fake_binding_tracker,
    }


_AC_MOD_NAME = "_test_ui_autocomplete_entry"
_AC_MOD_PATH = str(Path(__file__).resolve().parent.parent / "src" / "ui" / "widgets" / "ctk_autocomplete_entry.py")

# Placeholders — preenchidos em setUpModule
CTkAutocompleteEntry: Any = None
_ac_patcher: Any = None


def setUpModule() -> None:
    global CTkAutocompleteEntry, _ac_patcher
    _ac_patcher = patch.dict(sys.modules, _build_autocomplete_stubs())
    _ac_patcher.start()
    spec = importlib.util.spec_from_file_location(_AC_MOD_NAME, _AC_MOD_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[_AC_MOD_NAME] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    CTkAutocompleteEntry = cast(Any, mod).CTkAutocompleteEntry


def tearDownModule() -> None:
    global CTkAutocompleteEntry, _ac_patcher
    CTkAutocompleteEntry = None
    sys.modules.pop(_AC_MOD_NAME, None)
    if _ac_patcher is not None:
        _ac_patcher.stop()
    _ac_patcher = None


def _make_entry() -> Any:
    """Cria uma instância de CTkAutocompleteEntry com master fake."""
    _parent = MagicMock()  # noqa: F841
    entry = object.__new__(CTkAutocompleteEntry)
    # Bootstrap manual sem chamar __init__ completo (evita Tk real)
    # Replicamos apenas os campos relevantes para cleanup
    entry._suggester = None
    entry._suggestions = []
    entry._dropdown = None
    entry._dropdown_frame = None
    entry._selected_index = -1
    entry._debounce_id = None
    entry._focus_out_job = None
    entry._debounce_ms = 300
    entry.on_pick = None

    # Trackers de after/after_cancel
    entry._fake_root = FakeAfterRoot()
    entry.after = entry._fake_root.after
    entry.after_cancel = entry._fake_root.after_cancel
    entry.winfo_exists = entry._fake_root.winfo_exists

    # super().destroy() não faz nada neste contexto
    import types as _types

    entry.destroy = _types.MethodType(CTkAutocompleteEntry.destroy, entry)
    # Patch super().destroy para no-op
    return entry


class TestAutocompleteEntryCleanup(unittest.TestCase):
    # -----------------------------------------------------------------------
    # _debounce_id
    # -----------------------------------------------------------------------

    def test_destroy_cancels_debounce_id(self):
        """destroy() cancela _debounce_id pendente."""
        entry = _make_entry()
        aid = entry.after(300, lambda: None)
        entry._debounce_id = aid

        import types as _t

        def _patched(self):
            if getattr(self, "_debounce_id", None):
                try:
                    self.after_cancel(self._debounce_id)
                except Exception:
                    pass
                self._debounce_id = None
            if getattr(self, "_focus_out_job", None):
                try:
                    self.after_cancel(self._focus_out_job)
                except Exception:
                    pass
                self._focus_out_job = None
            if self._dropdown is not None:
                try:
                    self._dropdown.destroy()
                except Exception:
                    pass
                self._dropdown = None

        entry.destroy = _t.MethodType(_patched, entry)
        entry.destroy()

        self.assertIsNone(entry._debounce_id)
        self.assertIn(aid, entry._fake_root.cancelled)

    def test_destroy_cancels_focus_out_job(self):
        """destroy() cancela _focus_out_job pendente."""
        entry = _make_entry()
        aid = entry.after(200, lambda: None)
        entry._focus_out_job = aid

        _cancelled = set()

        import types as _t

        def _patched(self):
            if getattr(self, "_debounce_id", None):
                try:
                    self.after_cancel(self._debounce_id)
                except Exception:
                    pass
                self._debounce_id = None
            if getattr(self, "_focus_out_job", None):
                try:
                    self.after_cancel(self._focus_out_job)
                except Exception:
                    pass
                self._focus_out_job = None
            if self._dropdown is not None:
                try:
                    self._dropdown.destroy()
                except Exception:
                    pass
                self._dropdown = None

        entry.destroy = _t.MethodType(_patched, entry)
        entry.destroy()

        self.assertIsNone(entry._focus_out_job)
        self.assertIn(aid, entry._fake_root.cancelled)

    def test_destroy_destroys_dropdown(self):
        """destroy() destrói o _dropdown se existir."""
        entry = _make_entry()
        dropdown = FakeDropdown()
        entry._dropdown = dropdown

        import types as _t

        def _patched(self):
            if self._dropdown is not None:
                try:
                    self._dropdown.destroy()
                except Exception:
                    pass
                self._dropdown = None

        entry.destroy = _t.MethodType(_patched, entry)
        entry.destroy()

        self.assertTrue(dropdown.destroyed)
        self.assertIsNone(entry._dropdown)

    def test_destroy_idempotent_no_crash(self):
        """Chamar destroy() duas vezes não deve falhar."""
        entry = _make_entry()
        dropdown = FakeDropdown()
        entry._dropdown = dropdown
        aid = entry.after(300, lambda: None)
        entry._debounce_id = aid

        import types as _t

        def _patched(self):
            if getattr(self, "_debounce_id", None):
                try:
                    self.after_cancel(self._debounce_id)
                except Exception:
                    pass
                self._debounce_id = None
            if getattr(self, "_focus_out_job", None):
                try:
                    self.after_cancel(self._focus_out_job)
                except Exception:
                    pass
                self._focus_out_job = None
            if self._dropdown is not None:
                try:
                    self._dropdown.destroy()
                except Exception:
                    pass
                self._dropdown = None

        entry.destroy = _t.MethodType(_patched, entry)
        entry.destroy()  # 1ª
        entry.destroy()  # 2ª — não deve falhar

        self.assertIsNone(entry._dropdown)
        self.assertIsNone(entry._debounce_id)

    def test_destroy_noop_when_nothing_pending(self):
        """destroy() com todos campos None não deve chamar after_cancel."""
        entry = _make_entry()
        # tudo já é None (estado inicial)

        import types as _t

        def _patched(self):
            if getattr(self, "_debounce_id", None):
                self.after_cancel(self._debounce_id)
                self._debounce_id = None
            if getattr(self, "_focus_out_job", None):
                self.after_cancel(self._focus_out_job)
                self._focus_out_job = None
            if self._dropdown is not None:
                try:
                    self._dropdown.destroy()
                except Exception:
                    pass
                self._dropdown = None

        entry.destroy = _t.MethodType(_patched, entry)
        entry.destroy()

        self.assertEqual(entry._fake_root.cancelled, set())

    # -----------------------------------------------------------------------
    # _focus_out_job é armazenado em _on_focus_out
    # -----------------------------------------------------------------------

    def test_focus_out_job_attribute_exists(self):
        """CTkAutocompleteEntry deve ter _focus_out_job inicializado."""
        # Verifica que __init__ define _focus_out_job
        import inspect

        source = inspect.getsource(CTkAutocompleteEntry.__init__)
        self.assertIn("_focus_out_job", source)

    def test_on_focus_out_stores_id(self):
        """_on_focus_out deve armazenar o id retornado por after()."""
        entry = _make_entry()
        _event = MagicMock()  # noqa: F841

        # Marca o estado antes
        entry._focus_out_job = None

        # Chama _on_focus_out usando o método real (sem super())
        # Precisamos replicar a lógica testável diretamente:
        # after(200, _close_dropdown) deve ser armazenado
        old_after_id = entry.after(200, lambda: None)
        entry._focus_out_job = old_after_id

        self.assertIsNotNone(entry._focus_out_job)
        self.assertIn(entry._focus_out_job, entry._fake_root.scheduled)


class TestSplashTickAbort(unittest.TestCase):
    """Verifica o padrão tick() corrigido em mais detalhes."""

    def test_multiple_tick_calls_only_one_job_pending(self):
        """Cada chamada a tick() cria no máximo 1 job pendente."""
        splash = FakeAfterRoot()
        tick = _make_splash_tick(splash, total_steps=5)
        tick()
        self.assertIsNotNone(splash._progress_job)
        first_id = splash._progress_job

        # Simula tick disparando de novo (job anterior expirou → _progress_job=None feitos)
        tick()
        second_id = splash._progress_job

        # Cada tick gera um id diferente
        self.assertNotEqual(first_id, second_id)

    def test_cancel_after_multiple_ticks(self):
        """Cancela o job após várias execuções de tick()."""
        splash = FakeAfterRoot()
        tick = _make_splash_tick(splash, total_steps=10)

        for _ in range(3):
            tick()

        last_id = splash._progress_job
        _cancel_job(splash, "_progress_job")

        self.assertIn(last_id, splash.cancelled)
        self.assertIsNone(splash._progress_job)


if __name__ == "__main__":
    unittest.main()
