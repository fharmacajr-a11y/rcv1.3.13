from __future__ import annotations

import logging
import tkinter as tk

from src.modules.pdf_preview.views.main_window import PdfViewerWin

_log = logging.getLogger(__name__)


_singleton_viewer: PdfViewerWin | None = None


def open_pdf_viewer(
    master: tk.Misc,
    pdf_path: str | None = None,
    display_name: str | None = None,
    data_bytes: bytes | None = None,
) -> PdfViewerWin:
    """
    Abre visualizador unificado de PDF/imagem.

    Args:
        master: widget pai
        pdf_path: caminho do arquivo (se disponível)
        display_name: nome para exibição
        data_bytes: bytes do arquivo (alternativa a pdf_path)
    """
    global _singleton_viewer

    # Se já existe e está viva, reutiliza
    if _singleton_viewer and _singleton_viewer.winfo_exists():
        win = _singleton_viewer
        _log.info(
            "PDF VIEWER: reutilizando janela existente - display_name=%r has_new_content=%s",
            display_name,
            bool(pdf_path or data_bytes),
        )
        try:
            # Atualiza contexto do master antes de carregar conteúdo
            win.set_context_master(master)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao atualizar contexto do PDF viewer no reuso: %s", exc)
        try:
            # Se veio com conteúdo novo, carrega
            if pdf_path or data_bytes:
                win.open_document(pdf_path=pdf_path, data_bytes=data_bytes, display_name=display_name)
            # Apenas foca e levanta a janela existente
            win.lift()
            win.focus_set()
            win.focus_canvas()
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao reutilizar viewer existente: %s", exc)
        return win

    # Cria nova janela
    win = PdfViewerWin(
        master,
        pdf_path=pdf_path,
        display_name=display_name,
        data_bytes=data_bytes,
    )
    _singleton_viewer = win

    # Configurar janela como transiente ao master e com grab
    try:
        win.transient(master)
        win.grab_set()
    except Exception as exc:  # noqa: BLE001
        _log.debug("Falha ao configurar transient/grab: %s", exc)

    win.focus_canvas()

    # Quando a janela é destruída, resetar singleton
    def _on_destroy(event):
        global _singleton_viewer
        if event.widget is win:
            _singleton_viewer = None
            _log.debug("PDF VIEWER: singleton resetado após destruição")

    try:
        win.bind("<Destroy>", _on_destroy, add="+")
    except Exception as exc:  # noqa: BLE001
        _log.debug("Falha ao bind Destroy para resetar singleton: %s", exc)

    return win
