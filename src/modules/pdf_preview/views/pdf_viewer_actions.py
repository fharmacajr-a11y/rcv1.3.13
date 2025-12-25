# -*- coding: utf-8 -*-
"""
PDF Viewer Actions - Ações de alto nível (download, toggle, converter, etc).

Extrai métodos de ação de main_window.py para:
- Reduzir LOC da view principal
- Separar lógica de negócio de UI
- Facilitar testes
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main_window import PdfViewerWin

    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:
        Image = None  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)

__all__ = [
    "download_pdf",
    "download_image",
    "toggle_text_panel",
    "populate_ocr_text",
    "reveal_window",
    "close_viewer",
    "open_pdf_converter",
]


# ═══════════════════════════════════════════════════════════════════════════
# DOWNLOAD ACTIONS
# ═══════════════════════════════════════════════════════════════════════════


def download_pdf(viewer: PdfViewerWin) -> None:
    """Download do PDF atual para disco.

    Args:
        viewer: Instância do PdfViewerWin
    """
    from tkinter import messagebox
    from src.modules.pdf_preview.download_service import (
        DownloadContext,
        get_default_download_dir,
        save_pdf,
    )

    try:
        base = (getattr(viewer, "_display_name", "") or "arquivo").rsplit(".", 1)[0]
        ctx = DownloadContext(
            base_name=base,
            default_dir=get_default_download_dir(),
            extension=".pdf",
        )

        pdf_bytes = getattr(viewer, "_pdf_bytes", None)
        pdf_path = getattr(viewer, "_pdf_path", None)

        if not pdf_bytes and not (pdf_path and os.path.exists(pdf_path)):
            messagebox.showwarning("Baixar PDF", "Nenhum PDF carregado.", parent=viewer)
            return

        dst = save_pdf(pdf_bytes, pdf_path, ctx)
        messagebox.showinfo("Baixar PDF", f"Salvo em:\n{dst}", parent=viewer)

    except Exception as e:
        try:
            messagebox.showerror("Baixar PDF", f"Erro ao salvar: {e}", parent=viewer)
        except Exception as exc:
            logger.debug("Falha ao exibir erro ao salvar PDF: %s", exc)


def download_image(viewer: PdfViewerWin) -> None:
    """Download da imagem atual para disco.

    Args:
        viewer: Instância do PdfViewerWin
    """
    from tkinter import messagebox
    from src.modules.pdf_preview.download_service import (
        DownloadContext,
        get_default_download_dir,
        save_image,
    )

    pil = getattr(viewer, "_img_pil", None)
    if pil is None:
        return

    base = getattr(viewer, "_display_name", "") or "Imagem"
    base = os.path.splitext(base)[0]

    # Extensão: tenta manter tipo original; fallback .png
    ext = ".png"
    try:
        fmt = (pil.format or "").upper()  # ex.: "JPEG", "PNG"
        if fmt in ("JPEG", "JPG"):
            ext = ".jpg"
        elif fmt in ("PNG", "WEBP", "BMP", "TIFF"):
            ext = f".{fmt.lower()}"
    except Exception as exc:
        logger.debug("Falha ao detectar formato da imagem para download: %s", exc)

    ctx = DownloadContext(
        base_name=base,
        default_dir=get_default_download_dir(),
        extension=ext,
    )

    try:
        dst = save_image(pil, ctx)
        messagebox.showinfo("Baixar imagem", f"Salvo em:\n{dst}", parent=viewer)
    except Exception as exc:  # noqa: BLE001
        # Salvar pode falhar - mostra erro ao usuário
        logger.debug("Falha ao salvar imagem: %s", type(exc).__name__)
        try:
            messagebox.showerror("Baixar imagem", "Erro ao salvar a imagem.", parent=viewer)
        except Exception as msg_exc:
            logger.debug("Falha ao exibir erro ao salvar imagem: %s", msg_exc)


# ═══════════════════════════════════════════════════════════════════════════
# TEXT PANEL ACTIONS
# ═══════════════════════════════════════════════════════════════════════════


def toggle_text_panel(viewer: PdfViewerWin, show: bool) -> None:
    """Mostra/esconde painel de texto OCR.

    Args:
        viewer: Instância do PdfViewerWin
        show: Se True, mostra painel; se False, esconde
    """
    if not viewer._has_text:
        return

    try:
        if show and not getattr(viewer, "_pane_right_added", False):
            # Adiciona painel de texto
            viewer._pane.add(viewer._pane_right, weight=1)
            viewer._pane_right_added = True

            # Popula texto se ainda não foi feito
            if not viewer._ocr_loaded:
                populate_ocr_text(viewer)

        elif not show and getattr(viewer, "_pane_right_added", False):
            # Remove painel de texto
            viewer._pane.forget(viewer._pane_right)
            viewer._pane_right_added = False

    except Exception as exc:
        logger.debug("Erro ao toggle painel de texto: %s", exc)


def populate_ocr_text(viewer: PdfViewerWin) -> None:
    """Popula painel de texto com conteúdo OCR.

    Args:
        viewer: Instância do PdfViewerWin
    """
    if viewer._ocr_loaded:
        return

    try:
        text_buffer = getattr(viewer, "_text_buffer", [])
        if not text_buffer:
            viewer.text_panel.set_text("Nenhum texto disponível.")
            viewer._ocr_loaded = True
            return

        # Concatena texto de todas as páginas
        full_text = "\n\n".join(
            f"--- Página {i + 1} ---\n{txt}" for i, txt in enumerate(text_buffer) if txt and txt.strip()
        )

        viewer.text_panel.set_text(full_text or "Nenhum texto disponível.")
        viewer._ocr_loaded = True

    except Exception as exc:
        logger.debug("Erro ao popular texto OCR: %s", exc)
        viewer.text_panel.set_text("Erro ao carregar texto.")
        viewer._ocr_loaded = True


# ═══════════════════════════════════════════════════════════════════════════
# WINDOW LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════


def reveal_window(viewer: PdfViewerWin) -> None:
    """Revela janela após carregamento (restaura alpha e deiconify).

    Args:
        viewer: Instância do PdfViewerWin
    """
    if not viewer.winfo_exists():
        return

    logger.debug("PDF VIEWER: revelando janela - id=%s state=%s", id(viewer), viewer.state())

    try:
        viewer.deiconify()
    except Exception as exc:
        logger.debug("Falha em deiconify: %s", exc)

    try:
        viewer.lift()
    except Exception as exc:
        logger.debug("Falha em lift: %s", exc)

    # Restaura alpha se estava escondido via alpha
    if getattr(viewer, "_alpha_hidden", False):
        try:
            viewer.attributes("-alpha", 1.0)
            logger.debug("PDF VIEWER: alpha 1.0 restaurado - id=%s", id(viewer))
        except Exception as exc:
            logger.debug("Falha em restaurar alpha: %s", exc)


def close_viewer(viewer: PdfViewerWin) -> None:
    """Fecha o viewer de forma limpa.

    Args:
        viewer: Instância do PdfViewerWin
    """
    if viewer._closing:
        return

    viewer._closing = True

    try:
        # Limpa controller do PDF
        controller = getattr(viewer, "_controller", None)
        if controller is not None:
            try:
                controller.close()
            except Exception as exc:
                logger.debug("Erro ao fechar controller do PDF: %s", exc)

    except Exception as exc:
        logger.debug("Erro ao limpar recursos do viewer: %s", exc)

    try:
        viewer.destroy()
    except Exception as exc:
        logger.debug("Erro ao destruir janela do viewer: %s", exc)


# ═══════════════════════════════════════════════════════════════════════════
# PDF CONVERTER
# ═══════════════════════════════════════════════════════════════════════════


def open_pdf_converter(viewer: PdfViewerWin) -> None:
    """Abre conversor de PDF (se disponível no contexto).

    Args:
        viewer: Instância do PdfViewerWin
    """
    cb = viewer._resolve_pdf_converter_callback()
    if not cb:
        return

    # Libera grab para evitar conflitos com o conversor
    try:
        viewer.grab_release()
    except Exception as exc:  # noqa: BLE001
        # Janela pode estar destruída
        logger.debug("grab_release falhou: %s", type(exc).__name__)

    try:
        cb()
    finally:
        # Restaura grab se a janela ainda existir
        try:
            if viewer.winfo_exists():
                viewer.grab_set()
        except Exception as exc:  # noqa: BLE001
            # Janela pode estar destruída
            logger.debug("grab_set falhou: %s", type(exc).__name__)
