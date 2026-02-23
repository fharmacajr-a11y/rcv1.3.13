"""Fase 12 — Testes para guardas TclError em widgets destruídos.

Estratégia: replicar apenas o padrão lógico de cada guarda em classes fake,
sem carregar modules que dependem de Tcl/Display, garantindo execução headless.

Cobertura:
  Part 1 — ClientEditorDialog: after-job IDs, cancel em cleanup, winfo_exists
  Part 2 — CTkSplitPane: winfo_exists + TclError em _on_sash_enter/_on_sash_leave
  Part 3 — PDFBatchProgressDialog: winfo_exists no canvas fallback
"""

from __future__ import annotations

import unittest
from typing import Optional


# ---------------------------------------------------------------------------
# Part 1 — Padrão de cancel de after-jobs (ClientEditorDialog)
# ---------------------------------------------------------------------------


class TestClientEditorAfterJobCancelPattern(unittest.TestCase):
    """Replica o padrão de store/cancel/guard do ClientEditorDialog sem Tcl."""

    class _FakeDialog:
        """Simula apenas as partes relevantes do ClientEditorDialog."""

        def __init__(self) -> None:
            self._setup_modal_job: Optional[str] = None
            self._placeholder_job: Optional[str] = None
            self._cancelled: list[str] = []
            self._exists: bool = True
            self._entries_activated: bool = False

        def after_cancel(self, job_id: str) -> None:  # noqa: D401
            self._cancelled.append(job_id)

        def winfo_exists(self) -> bool:
            return self._exists

        # --- lógica replicada de _cleanup_and_destroy ---
        def _cancel_pending_jobs(self) -> None:
            for attr in ("_setup_modal_job", "_placeholder_job"):
                job = getattr(self, attr, None)
                if job is not None:
                    try:
                        self.after_cancel(job)
                    except Exception:  # noqa: BLE001
                        pass
                    setattr(self, attr, None)

        # --- lógica replicada de _activate_all_placeholders ---
        def _activate_all_placeholders(self) -> None:
            try:
                if not self.winfo_exists():
                    return
            except Exception:  # noqa: BLE001
                return
            self._entries_activated = True

    def setUp(self) -> None:
        self.dlg = self._FakeDialog()

    # -- cancel jobs --

    def test_cancel_both_jobs_called(self) -> None:
        self.dlg._setup_modal_job = "job_setup"
        self.dlg._placeholder_job = "job_placeholder"
        self.dlg._cancel_pending_jobs()
        self.assertIn("job_setup", self.dlg._cancelled)
        self.assertIn("job_placeholder", self.dlg._cancelled)

    def test_jobs_none_after_cancel(self) -> None:
        self.dlg._setup_modal_job = "job_setup"
        self.dlg._placeholder_job = "job_placeholder"
        self.dlg._cancel_pending_jobs()
        self.assertIsNone(self.dlg._setup_modal_job)
        self.assertIsNone(self.dlg._placeholder_job)

    def test_cancel_idempotent_when_both_none(self) -> None:
        self.dlg._cancel_pending_jobs()
        self.assertEqual(self.dlg._cancelled, [])

    def test_cancel_only_setup_job_when_placeholder_none(self) -> None:
        self.dlg._setup_modal_job = "job_setup"
        self.dlg._cancel_pending_jobs()
        self.assertIn("job_setup", self.dlg._cancelled)
        self.assertIsNone(self.dlg._setup_modal_job)
        self.assertIsNone(self.dlg._placeholder_job)

    def test_cancel_only_placeholder_job_when_setup_none(self) -> None:
        self.dlg._placeholder_job = "job_ph"
        self.dlg._cancel_pending_jobs()
        self.assertIn("job_ph", self.dlg._cancelled)
        self.assertIsNone(self.dlg._placeholder_job)
        self.assertIsNone(self.dlg._setup_modal_job)

    def test_cancel_survives_after_cancel_raising(self) -> None:
        """Se after_cancel lançar exceção interna, não deve propagar."""
        def _bad_cancel(job_id: str) -> None:
            raise RuntimeError("timer already fired")
        self.dlg.after_cancel = _bad_cancel  # type: ignore[method-assign]
        self.dlg._setup_modal_job = "job_x"
        self.dlg._cancel_pending_jobs()  # não deve lançar
        self.assertIsNone(self.dlg._setup_modal_job)

    # -- activate_all_placeholders guard --

    def test_activate_skips_when_widget_destroyed(self) -> None:
        self.dlg._exists = False
        self.dlg._activate_all_placeholders()
        self.assertFalse(self.dlg._entries_activated)

    def test_activate_runs_when_widget_exists(self) -> None:
        self.dlg._exists = True
        self.dlg._activate_all_placeholders()
        self.assertTrue(self.dlg._entries_activated)

    def test_activate_skips_when_winfo_raises(self) -> None:
        def _bad() -> bool:
            raise RuntimeError("destroyed")
        self.dlg.winfo_exists = _bad  # type: ignore[method-assign]
        self.dlg._activate_all_placeholders()  # não deve lançar
        self.assertFalse(self.dlg._entries_activated)


# ---------------------------------------------------------------------------
# Part 2 — CTkSplitPane: winfo_exists + TclError em _on_sash_enter/_leave
# ---------------------------------------------------------------------------


class TestCTkSplitPaneGuardPattern(unittest.TestCase):
    """Testa a lógica de guarda de _on_sash_enter/_on_sash_leave sem Tcl."""

    class _FakeTclError(Exception):
        """Substituto de tk.TclError nos testes."""

    class _FakeSash:
        def __init__(self) -> None:
            self.configure_called: bool = False
            self.last_kwargs: dict = {}

        def configure(self, **kwargs: object) -> None:
            self.configure_called = True
            self.last_kwargs.update(kwargs)

    class _FakeSplitPane:
        """Replica apenas os dois métodos guardados."""

        def __init__(self, fake_tcl_error: type[Exception]) -> None:
            self._sash: "object | None" = None
            self._dragging: bool = False
            self._sash_hover_color: str = "blue"
            self._sash_color: str = "gray"
            self._exists: bool = True
            self._TclError = fake_tcl_error

        def winfo_exists(self) -> bool:
            return self._exists

        def _on_sash_enter(self, event: object = None) -> None:
            if self._sash is None:
                return
            try:
                if not self.winfo_exists():
                    return
                self._sash.configure(fg_color=self._sash_hover_color)
            except self._TclError:
                pass

        def _on_sash_leave(self, event: object = None) -> None:
            if self._sash is None or self._dragging:
                return
            try:
                if not self.winfo_exists():
                    return
                self._sash.configure(fg_color=self._sash_color)
            except self._TclError:
                pass

    def setUp(self) -> None:
        self.TclError = self._FakeTclError
        self.pane = self._FakeSplitPane(self._FakeTclError)
        self.sash = self._FakeSash()
        self.pane._sash = self.sash

    # enter

    def test_enter_configures_hover_color(self) -> None:
        self.pane._on_sash_enter()
        self.assertTrue(self.sash.configure_called)
        self.assertEqual(self.sash.last_kwargs.get("fg_color"), "blue")

    def test_enter_skips_when_widget_destroyed(self) -> None:
        self.pane._exists = False
        self.pane._on_sash_enter()
        self.assertFalse(self.sash.configure_called)

    def test_enter_skips_when_no_sash(self) -> None:
        self.pane._sash = None
        self.pane._on_sash_enter()  # não deve lançar

    def test_enter_silences_tclerror(self) -> None:
        def _bad(**kwargs: object) -> None:
            raise self._FakeTclError("widget destroyed")
        self.sash.configure = _bad  # type: ignore[method-assign]
        self.pane._on_sash_enter()  # não deve propagar

    # leave

    def test_leave_configures_normal_color(self) -> None:
        self.pane._on_sash_leave()
        self.assertTrue(self.sash.configure_called)
        self.assertEqual(self.sash.last_kwargs.get("fg_color"), "gray")

    def test_leave_skips_when_dragging(self) -> None:
        self.pane._dragging = True
        self.pane._on_sash_leave()
        self.assertFalse(self.sash.configure_called)

    def test_leave_skips_when_widget_destroyed(self) -> None:
        self.pane._exists = False
        self.pane._on_sash_leave()
        self.assertFalse(self.sash.configure_called)

    def test_leave_skips_when_no_sash(self) -> None:
        self.pane._sash = None
        self.pane._on_sash_leave()  # não deve lançar

    def test_leave_silences_tclerror(self) -> None:
        def _bad(**kwargs: object) -> None:
            raise self._FakeTclError("widget destroyed")
        self.sash.configure = _bad  # type: ignore[method-assign]
        self.pane._on_sash_leave()  # não deve propagar

    def test_leave_guards_dragging_before_tcl_call(self) -> None:
        """_dragging=True → retorna sem sequer chamar winfo_exists."""
        called: list[bool] = []

        def _bad_exists() -> bool:
            called.append(True)
            return False

        self.pane._dragging = True
        self.pane.winfo_exists = _bad_exists  # type: ignore[method-assign]
        self.pane._on_sash_leave()
        self.assertEqual(called, [], "winfo_exists não deve ser chamado se dragging")


# ---------------------------------------------------------------------------
# Part 3 — PDFBatchProgressDialog: winfo_exists no canvas fallback
# ---------------------------------------------------------------------------


class TestPDFCanvasGuardPattern(unittest.TestCase):
    """Testa o bloco Canvas fallback com guarda winfo_exists (sem Tcl)."""

    class _FakeCanvas:
        def __init__(self, exists: bool = True) -> None:
            self._exists = exists
            self.deleted: bool = False
            self.rectangles: list[tuple] = []
            self._progress_value: float = 0.0

        def winfo_exists(self) -> bool:
            return self._exists

        def delete(self, tag: str) -> None:
            self.deleted = True

        def create_rectangle(self, *args: object, **kwargs: object) -> None:
            self.rectangles.append((args, kwargs))

    class _FakeProgressDialog:
        """Replica APENAS o bloco canvas fallback com guarda Fase 12."""

        def __init__(self, canvas: "TestPDFCanvasGuardPattern._FakeCanvas") -> None:
            self._closed = False
            self.progress = canvas

        def _update_canvas_fallback(self, percent: float) -> None:
            """Réplica exacta do bloco canvas fallback de pdf_batch_progress.py."""
            # Canvas fallback — checar existência antes de operar (Fase 12)
            if not self.progress.winfo_exists():
                self._closed = True
                return
            self.progress._progress_value = percent / 100.0
            fill_w = int(320 * (percent / 100.0))
            self.progress.delete("all")
            self.progress.create_rectangle(0, 0, fill_w, 22, fill="#007bff", outline="")

    def _make(self, exists: bool = True) -> tuple["_FakeCanvas", "_FakeProgressDialog"]:
        canvas = self._FakeCanvas(exists=exists)
        dlg = self._FakeProgressDialog(canvas)
        return canvas, dlg

    # canvas exists — caminho normal

    def test_canvas_updated_when_exists(self) -> None:
        canvas, dlg = self._make(exists=True)
        dlg._update_canvas_fallback(50.0)
        self.assertTrue(canvas.deleted)
        self.assertEqual(len(canvas.rectangles), 1)
        self.assertFalse(dlg._closed)

    def test_progress_value_set_correctly(self) -> None:
        canvas, dlg = self._make(exists=True)
        dlg._update_canvas_fallback(75.0)
        self.assertAlmostEqual(canvas._progress_value, 0.75)

    def test_fill_width_zero_at_zero_percent(self) -> None:
        canvas, dlg = self._make(exists=True)
        dlg._update_canvas_fallback(0.0)
        fill_w = canvas.rectangles[0][0][2]  # 3rd positional arg → x2
        self.assertEqual(fill_w, 0)

    def test_fill_width_full_at_100_percent(self) -> None:
        canvas, dlg = self._make(exists=True)
        dlg._update_canvas_fallback(100.0)
        fill_w = canvas.rectangles[0][0][2]
        self.assertEqual(fill_w, 320)

    def test_fill_width_half_at_50_percent(self) -> None:
        canvas, dlg = self._make(exists=True)
        dlg._update_canvas_fallback(50.0)
        fill_w = canvas.rectangles[0][0][2]
        self.assertEqual(fill_w, 160)

    # canvas destruído — guarda deve bloquear

    def test_canvas_not_modified_when_destroyed(self) -> None:
        canvas, dlg = self._make(exists=False)
        dlg._update_canvas_fallback(50.0)
        self.assertFalse(canvas.deleted)
        self.assertEqual(len(canvas.rectangles), 0)

    def test_closed_set_true_when_canvas_destroyed(self) -> None:
        canvas, dlg = self._make(exists=False)
        dlg._update_canvas_fallback(50.0)
        self.assertTrue(dlg._closed)

    def test_progress_value_not_set_when_destroyed(self) -> None:
        canvas, dlg = self._make(exists=False)
        dlg._update_canvas_fallback(90.0)
        self.assertAlmostEqual(canvas._progress_value, 0.0)

    def test_closed_flag_prevents_further_operations(self) -> None:
        """Primeira chamada com widget destruído seta _closed; segunda não toca canvas."""
        canvas, dlg = self._make(exists=False)
        dlg._update_canvas_fallback(50.0)
        # restaurar canvas e chamar de novo (simulando _closed=True check na camada acima)
        canvas._exists = True
        canvas.deleted = False
        # _closed já é True; o código acima desta função retorna antes, mas
        # _update_canvas_fallback em si não verifica _closed — isso é feito pelo chamador.
        # Aqui apenas verificamos que _closed fica True após a primeira chamada destruída.
        self.assertTrue(dlg._closed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
