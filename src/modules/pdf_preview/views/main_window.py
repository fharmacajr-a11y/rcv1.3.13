from __future__ import annotations

import io
import logging
import os
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, cast

try:
    from PIL import Image, ImageTk  # opcional
except Exception:
    Image = ImageTk = None

from src.ui.wheel_windows import wheel_steps
from src.modules.pdf_preview.controller import PdfPreviewController, PageRenderData
from src.modules.pdf_preview.download_service import (
    DownloadContext,
    get_default_download_dir,
    save_image,
    save_pdf,
)
from src.modules.pdf_preview.utils import LRUCache, pixmap_to_photoimage
from src.modules.pdf_preview.views.page_view import PdfPageView
from src.modules.pdf_preview.views.text_panel import PdfTextPanel
from src.modules.pdf_preview.views.toolbar import PdfToolbar
from src.modules.pdf_preview.views.view_helpers import (
    calculate_button_states,
    find_first_visible_page,
    format_page_label,
    is_pdf_or_image,
)

logger = logging.getLogger(__name__)


GAP = 16  # espaço entre páginas

TkBindReturn = Literal["break"] | None
TkCallback = Callable[..., TkBindReturn]


class PdfViewerWin(tk.Toplevel):
    def __init__(
        self,
        master: tk.Misc,
        pdf_path: str | None = None,
        display_name: str | None = None,
        data_bytes: bytes | None = None,
    ) -> None:
        super().__init__(master)
        self._display_name: str = display_name or (os.path.basename(pdf_path) if pdf_path else "Documento")
        self.title(f"Visualizar: {self._display_name}")
        self.geometry("1200x800")
        self.zoom: float = 1.0
        self._img_refs: Dict[int, tk.PhotoImage] = {}  # id_canvas -> PhotoImage
        self._items: List[int] = []  # ids de imagens por página
        self._page_tops: List[int] = []  # y de cada página
        self._page_sizes: List[Tuple[int, int]] = []  # (w,h) em 1.0
        self.cache: LRUCache = LRUCache(12)
        self._pan_active: bool = False
        self._closing: bool = False
        self._fit_mode: bool = False
        self._shortcut_sequences: List[str] = []
        self._page_label_suffix: str = ""
        self._has_text: bool = False
        self._ocr_loaded: bool = False

        # Controle para modo de imagem
        self._is_pdf: bool = False
        self.page_count: int = 1  # evita AttributeError antes do carregamento
        self._img_pil: Optional[Image.Image] = None  # type: ignore[name-defined]
        self._img_ref: Optional[tk.PhotoImage] = None  # type: ignore[name-defined]  # manter referência viva
        self._img_zoom: float = 1.0
        self.btn_download_pdf: Optional[ttk.Button] = None
        self.btn_download_img: Optional[ttk.Button] = None
        # --- hotfix 02: origem do PDF (arquivo ou bytes) ---
        self._pdf_bytes: bytes | None = None
        self._pdf_path: str | None = None
        self._controller: Optional[PdfPreviewController] = None
        self._text_buffer: List[str] = []
        # ---------------------------------------------------

        # Top bar
        self.toolbar: PdfToolbar = PdfToolbar(
            self,
            on_zoom_in=lambda: self._zoom_by(+1),
            on_zoom_out=lambda: self._zoom_by(-1),
            on_zoom_100=lambda: self._set_zoom_exact(1.0),
            on_fit_width=self._set_zoom_fit_width,
            on_toggle_text=self._on_toggle_text_toolbar,
            on_download_pdf=self._download_pdf,
            on_download_image=self._download_img,
        )
        self.toolbar.pack(side="top", fill="x")
        self.lbl_page: ttk.Label = self.toolbar.lbl_page
        self.lbl_zoom: ttk.Label = self.toolbar.lbl_zoom
        self.lbl_zoom.bind("<Button-1>", lambda e: self._toggle_fit_100())
        self.var_show_text: tk.BooleanVar = self.toolbar.var_text
        self.chk_text: ttk.Checkbutton = self.toolbar.chk_text
        self.btn_download_pdf = self.toolbar.btn_download_pdf
        self.btn_download_img = self.toolbar.btn_download_img
        self._update_download_buttons(is_pdf=False, is_image=False)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=8, pady=(0, 8))

        # Paned layout (canvas | text)
        pane: ttk.Panedwindow = ttk.Panedwindow(self, orient="horizontal")
        pane.pack(side="top", fill="both", expand=True)

        self.page_view: PdfPageView = PdfPageView(
            pane,
            on_page_up=self._on_page_up,
            on_page_down=self._on_page_down,
            on_page_first=self._on_home,
            on_page_last=self._on_end,
        )
        pane.add(self.page_view, weight=4)

        self.text_panel: PdfTextPanel = PdfTextPanel(
            pane,
            on_search_next=self._on_search_next,
            on_search_prev=self._on_search_prev,
        )
        self._pane: ttk.Panedwindow = pane
        self._pane_right: PdfTextPanel = self.text_panel
        self._pane.add(self._pane_right, weight=2)
        self._pane.forget(self._pane_right)
        self._pane_right_added: bool = False

        # Aliases para compatibilidade interna
        self.canvas: tk.Canvas = self.page_view.canvas
        self.ocr_text: tk.Text = self.text_panel.text
        self.text: tk.Text = self.ocr_text
        self.search_nav = self.text_panel.search_nav

        # Bindings (Windows)
        self.bind("<MouseWheel>", self._on_wheel_scroll)
        self.bind("<Control-MouseWheel>", self._on_wheel_zoom)
        self.canvas.bind("<Enter>", lambda e: self.focus_set())
        self.canvas.bind("<KeyPress-space>", self._on_space_press)
        self.canvas.bind("<KeyRelease-space>", self._on_space_release)
        self.canvas.bind("<ButtonPress-1>", self._on_pan_button_press)
        self.canvas.bind("<B1-Motion>", self._on_pan_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_pan_button_release)

        control_bindings = [
            ("<Control-0>", lambda e: (self._set_zoom_fit_width(), "break")),
            ("<Control-1>", lambda e: (self._set_zoom_exact(1.0), "break")),
            ("<Control-plus>", lambda e: (self._zoom_by(+1, e), "break")),
            ("<Control-equal>", lambda e: (self._zoom_by(+1, e), "break")),
            ("<Control-minus>", lambda e: (self._zoom_by(-1, e), "break")),
        ]
        for sequence, handler in control_bindings:
            self.bind(sequence, handler)
            self._shortcut_sequences.append(sequence)
        self._bind_shortcuts()

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Destroy>", self._on_destroy)

        # Carrega conteúdo
        if data_bytes:
            # Se veio bytes, detecta o tipo e abre
            self.open_bytes(data_bytes, self._display_name)
        elif pdf_path:
            # Se veio caminho, carrega PDF tradicional
            self._load_pdf(pdf_path)
        else:
            self._controller = None

    # ======== PDF load / render ========
    def _load_pdf(self, path: str) -> None:
        self._pdf_path = path
        self._pdf_bytes = None
        self._is_pdf = True
        self._update_download_buttons(source=path, is_pdf=True, is_image=False)
        try:
            self._controller = PdfPreviewController(pdf_path=path)
        except Exception:
            self._controller = None

        if self._controller is not None:
            self.page_count = self._controller.state.page_count
            self._page_sizes = self._controller.page_sizes
            self._text_buffer = self._controller.text_buffer
            self.zoom = self._controller.state.zoom
        else:
            self.page_count = 1
            self._page_sizes = [(800, 1100)]
            self._text_buffer = ["Texto indisponível (PyMuPDF não detectado)."]
            self.zoom = 1.0

        self._has_text = any((t or "").strip() for t in self._text_buffer)
        self._page_label_suffix = "•  OCR: OK" if self._has_text else "•  OCR: vazio"
        self._ocr_loaded = False
        self.var_show_text.set(False)

        self._reflow_pages()

        self.text_panel.clear()
        if not self._has_text:
            self.text_panel.set_text("Nenhum texto/OCR foi encontrado para este documento.")
            try:
                self._pane.forget(self._pane_right)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao esconder painel de texto no PDF viewer: %s", exc)
            self._pane_right_added = False
            self.var_show_text.set(False)
            self.chk_text.state(["disabled"])
        else:
            self.chk_text.state(["!disabled"])
        self._update_page_label(0)

    def _reflow_pages(self) -> None:
        if self._closing or not self.canvas.winfo_exists():
            return

        # Limpa canvas
        for it in self._items:
            self.canvas.delete(it)
        self._items.clear()
        self._img_refs.clear()
        self.cache.clear()

        # calcula alturas na escala atual e topos
        self._page_tops = []
        y = GAP
        cw = 0
        for w1, h1 in self._page_sizes:
            w = int(w1 * self.zoom)
            h = int(h1 * self.zoom)
            self._page_tops.append(y)
            # cria item imagem vazio
            it = self.canvas.create_image(GAP, y, anchor="nw")
            self._items.append(it)
            y += h + GAP
            cw = max(cw, w + GAP * 2)
        self.canvas.configure(scrollregion=(0, 0, cw, y))
        self._render_visible_pages()
        self._update_scrollregion()

    def _on_canvas_configure(self, event: Any) -> None:
        # manter scrollregion atualizada
        if self._is_pdf:
            self._render_visible_pages()
            self._update_scrollregion()
        else:
            # re-renderiza a IMAGEM para o novo tamanho do canvas
            if self._img_pil is not None:
                self._render_image(self._img_pil)

    def _render_visible_pages(self) -> None:
        if self._closing or not self.canvas.winfo_exists():
            return

        # faixa visível
        y0 = self.canvas.canvasy(0)
        y1 = y0 + self.canvas.winfo_height()
        margin = 2 * GAP
        for i, top in enumerate(self._page_tops):
            h = int(self._page_sizes[i][1] * self.zoom)
            if top > y1 + margin or (top + h) < y0 - margin:
                continue
            self._ensure_page_rendered(i)
        self._update_page_label(self._first_visible_page())
        self._update_scrollregion()

    def _ensure_page_rendered(self, i: int) -> None:
        key = (i, round(self.zoom, 2))
        img = self.cache.get(key)
        if img is None:
            img = self._render_page_image(i, self.zoom)
            if img is None:
                return
            self.cache.put(key, img)
        it = self._items[i]
        # posiciona pela esquerda com GAP
        self.canvas.itemconfig(it, image=img)
        self._img_refs[it] = img  # manter referência viva

    def _render_page_image(self, index: int, zoom: float) -> tk.PhotoImage:
        """Renderiza uma página do PDF como PhotoImage."""
        w1, h1 = self._page_sizes[index]

        # Obtém pixmap do controller
        if self._controller is not None:
            render: Optional[PageRenderData] = self._controller.get_page_pixmap(page_index=index, zoom=zoom)
            pix = render.pixmap if render is not None else None
        else:
            pix = None

        # Fallback: imagem vazia se não houver pixmap
        if pix is None:
            ph = tk.PhotoImage(width=max(200, int(w1 * zoom)), height=max(200, int(h1 * zoom)))
            return ph

        # Converte pixmap para PhotoImage usando helper
        photo = pixmap_to_photoimage(pix)
        return photo if photo is not None else tk.PhotoImage(width=200, height=200)

    def _update_page_label(self, index: int) -> None:
        total = max(1, getattr(self, "page_count", 1))
        clamped = max(0, min(index, total - 1))
        if self._controller is not None:
            self._controller.go_to_page(clamped)
            label = f"{self._controller.get_page_label(prefix='Página')}"
            zoom_pct = int(round(self._controller.state.zoom * 100))
        else:
            zoom_pct = int(round(self.zoom * 100))
            # Usa helper para formatação
            page_label, zoom_label = format_page_label(
                current_page=clamped,
                total_pages=total,
                zoom_percent=zoom_pct,
                suffix=self._page_label_suffix,
            )
            label = page_label
        try:
            self.lbl_page.config(text=label)
            self.lbl_zoom.config(text=f"{zoom_pct}%")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao atualizar rotulos de pagina/zoom: %s", exc)

    # ======== Wheel / Zoom ========
    def _on_wheel_scroll(self, event: Any) -> TkBindReturn:
        if not self.canvas.winfo_exists():
            return "break"
        # se Ctrl está pressionado, deixa o handler de zoom cuidar
        if (event.state & 0x0004) != 0:
            return "break"
        steps = wheel_steps(event)
        if steps:
            if self._is_pdf:
                self.canvas.yview_scroll(-steps, "units")
                self._render_visible_pages()
            else:
                # scrolling em imagem: re-render se quiser zoom sob roda
                if self._img_pil is not None:
                    self._render_image(self._img_pil)
        return "break"

    def _on_wheel_zoom(self, event: Any) -> TkBindReturn:
        if not self.canvas.winfo_exists():
            return "break"
        steps = wheel_steps(event)
        if steps:
            if self._is_pdf:
                self._zoom_by(steps, event)
            else:
                # Zoom para imagem
                self._zoom_image_by(steps)
        return "break"

    def _zoom_by(self, wheel_steps_count: int | float, event: Any | None = None) -> None:
        Z_MIN, Z_MAX, Z_STEP = 0.2, 6.0, 0.1
        old = self.zoom
        new = max(Z_MIN, min(Z_MAX, round(old + wheel_steps_count * Z_STEP, 2)))
        if abs(new - old) < 1e-9:
            return
        self._fit_mode = False

        if self._controller is not None:
            self._controller.set_zoom(new, fit_mode="custom")
            new = self._controller.state.zoom

        # âncora do ponteiro no canvas
        if event is not None:
            cx = self.canvas.canvasx(event.x)
            cy = self.canvas.canvasy(event.y)
            x0, y0, x1, y1 = self.canvas.bbox("all") or (0, 0, 1, 1)
            fx = 0 if x1 == x0 else (cx - x0) / (x1 - x0)
            fy = 0 if y1 == y0 else (cy - y0) / (y1 - y0)
        else:
            fx = fy = 0.5

        self.zoom = new
        self._reflow_pages()

        # reposiciona mantendo o ponto sob o cursor
        x0, y0, x1, y1 = self.canvas.bbox("all") or (0, 0, 1, 1)
        nx = x0 + fx * (x1 - x0)
        ny = y0 + fy * (y1 - y0)
        if x1 != x0:
            self.canvas.xview_moveto((nx - (x1 - x0) * fx) / (x1 - x0))
        if y1 != y0:
            self.canvas.yview_moveto((ny - (y1 - y0) * fy) / (y1 - y0))
        self._render_visible_pages()
        self._update_scrollregion()

    def _zoom_image_by(self, wheel_steps_count: int | float) -> None:
        """Ajusta zoom da imagem com Ctrl+MouseWheel."""
        Z_MIN, Z_MAX, Z_STEP = 0.1, 5.0, 0.1
        old = self._img_zoom
        new = max(Z_MIN, min(Z_MAX, round(old + wheel_steps_count * Z_STEP, 2)))
        if abs(new - old) < 1e-9:
            return
        self._img_zoom = new
        if self._img_pil is not None:
            self._render_image(self._img_pil)

    def _set_zoom_fit_width(self) -> None:
        if not self._is_pdf and self._img_pil is not None:
            # Modo imagem: ajusta zoom baseado na largura
            cwidth = max(1, self.canvas.winfo_width() - 2 * GAP)
            img_width = self._img_pil.width
            if img_width > 0:
                self._img_zoom = max(0.1, min(5.0, round(cwidth / img_width, 2)))
                self._render_image(self._img_pil)
            return
        # Modo PDF
        if not self._page_sizes:
            return
        cwidth = max(1, self.canvas.winfo_width() - 2 * GAP)
        base_w = max(w for (w, h) in self._page_sizes)
        target = max(0.2, min(6.0, round(cwidth / base_w, 2)))
        if self._controller is not None:
            self._controller.set_zoom(target, fit_mode="width")
            target = self._controller.state.zoom
        self._set_zoom_exact(target, fit_mode=True)

    def _set_zoom_exact(self, value: float, *, fit_mode: bool = False) -> None:
        self._fit_mode = fit_mode
        if self._controller is not None:
            self._controller.set_zoom(max(0.2, min(6.0, float(value))), fit_mode=("width" if fit_mode else "custom"))
            self.zoom = self._controller.state.zoom
        else:
            self.zoom = max(0.2, min(6.0, float(value)))
        self._reflow_pages()
        self._render_visible_pages()
        self._update_scrollregion()

    def _toggle_fit_100(self) -> None:
        if self._fit_mode:
            self._set_zoom_exact(1.0, fit_mode=False)
        else:
            self._set_zoom_fit_width()

    def _on_toggle_text_toolbar(self, show: bool) -> None:
        self.var_show_text.set(show)
        self._toggle_text()

    # ======== Texto / Busca ========
    def _toggle_text(self) -> None:
        if not self._has_text and self.var_show_text.get():
            self.var_show_text.set(False)
            return
        show = self.var_show_text.get()
        if self._controller is not None:
            self._controller.state.show_text = bool(show)
        if show and not self._pane_right_added:
            self._pane.add(self._pane_right, weight=2)
            self._pane_right_added = True
            if self._has_text and not self._ocr_loaded:
                self._populate_ocr_text()
        elif (not show) and self._pane_right_added:
            self._pane.forget(self._pane_right)
            self._pane_right_added = False

    def _populate_ocr_text(self) -> None:
        sep = "\n" + ("\u2014" * 40) + "\n"
        # _text_buffer j? foi normalizado para List[str] em _load_pdf
        text_buffer_str: List[str] = cast(List[str], self._text_buffer)
        self.text_panel.set_text(sep.join(text_buffer_str))
        self._ocr_loaded = True

    def _on_search_next(self, _query: str) -> None:
        return None

    def _on_search_prev(self, _query: str) -> None:
        return None

    def focus_canvas(self) -> None:
        self.canvas.focus_set()

    def _update_scrollregion(self) -> None:
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)

    def _download_img(self) -> None:
        # S? dispon?vel quando estamos em modo imagem
        pil = getattr(self, "_img_pil", None)
        if pil is None:
            return
        base = getattr(self, "_display_name", "") or "Imagem"
        base = os.path.splitext(base)[0]

        # Extens?o: tenta manter tipo original; fallback .png
        ext = ".png"
        try:
            fmt = (pil.format or "").upper()  # ex.: "JPEG", "PNG"
            if fmt in ("JPEG", "JPG"):
                ext = ".jpg"
            elif fmt in ("PNG", "WEBP", "BMP", "TIFF"):
                ext = f".{fmt.lower()}"
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao detectar formato da imagem para download: %s", exc)

        ctx = DownloadContext(
            base_name=base,
            default_dir=get_default_download_dir(),
            extension=ext,
        )

        try:
            dst = save_image(pil, ctx)
            from tkinter import messagebox

            messagebox.showinfo("Baixar imagem", f"Salvo em:\\n{dst}", parent=self)
        except Exception:
            try:
                from tkinter import messagebox

                messagebox.showerror("Baixar imagem", "Erro ao salvar a imagem.", parent=self)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao exibir erro ao salvar imagem: %s", exc)

    def _download_pdf(self) -> None:
        from tkinter import messagebox

        try:
            base = (getattr(self, "_display_name", "") or "arquivo").rsplit(".", 1)[0]
            ctx = DownloadContext(
                base_name=base,
                default_dir=get_default_download_dir(),
                extension=".pdf",
            )
            if not self._pdf_bytes and not (self._pdf_path and os.path.exists(self._pdf_path)):
                messagebox.showwarning("Baixar PDF", "Nenhum PDF carregado.", parent=self)
                return

            dst = save_pdf(self._pdf_bytes, self._pdf_path, ctx)
            messagebox.showinfo("Baixar PDF", f"Salvo em:\\n{dst}", parent=self)
        except Exception as e:
            try:
                messagebox.showerror("Baixar PDF", f"Erro ao salvar: {e}", parent=self)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao exibir erro ao salvar PDF: %s", exc)

    def _on_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        try:
            if self._controller is not None:
                self._controller.close()
        finally:
            try:
                self.grab_release()
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao liberar grab no fechamento do PDF viewer: %s", exc)
            self.destroy()

    def _on_destroy(self, event: Any | None = None) -> None:
        # Only run once for the window itself
        if event is not None and event.widget is not self:
            return
        try:
            self.unbind("<MouseWheel>")
            self.unbind("<Control-MouseWheel>")
            for sequence in getattr(self, "_shortcut_sequences", []):
                self.unbind(sequence)
            if hasattr(self, "canvas") and self.canvas.winfo_exists():
                self.canvas.unbind("<Configure>")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao remover bindings do PDF viewer: %s", exc)

    def _bind_shortcuts(self) -> None:
        bindings = [
            ("<KeyPress-plus>", lambda e: self._handle_zoom_key(+1, e)),
            ("<KeyPress-equal>", lambda e: self._handle_zoom_key(+1, e)),
            ("<KeyPress-KP_Add>", lambda e: self._handle_zoom_key(+1, e)),
            ("<KeyPress-minus>", lambda e: self._handle_zoom_key(-1, e)),
            ("<KeyPress-KP_Subtract>", lambda e: self._handle_zoom_key(-1, e)),
            ("<KeyPress-1>", self._on_zoom_reset),
            ("<KeyPress-KP_1>", self._on_zoom_reset),
            ("<KeyPress-0>", self._on_zoom_fit),
            ("<KeyPress-KP_0>", self._on_zoom_fit),
            ("<Control-s>", self._on_save_shortcut),
            ("<Control-f>", self._on_find_shortcut),
            ("<Escape>", self._on_escape),
            ("<Prior>", self._on_page_up),
            ("<Next>", self._on_page_down),
            ("<Home>", self._on_home),
            ("<End>", self._on_end),
        ]
        for sequence, handler in bindings:
            self.bind(sequence, handler)
            self._shortcut_sequences.append(sequence)

    def _handle_zoom_key(self, step: int, event: Any) -> TkBindReturn:
        if event.state & 0x0004:  # ignore when Ctrl is held (handled elsewhere)
            return None
        self.focus_canvas()
        self._zoom_by(step)
        return "break"

    def _on_zoom_reset(self, event: Any) -> TkBindReturn:
        if event.state & 0x0004:
            return None
        self.focus_canvas()
        self._set_zoom_exact(1.0)
        return "break"

    def _on_zoom_fit(self, event: Any) -> TkBindReturn:
        if event.state & 0x0004:
            return None
        self.focus_canvas()
        self._set_zoom_fit_width()
        return "break"

    def _on_save_shortcut(self, event: Any) -> TkBindReturn:
        self._download_pdf()
        return "break"

    def _on_find_shortcut(self, event: Any) -> TkBindReturn:
        if self._ensure_text_panel():
            try:
                self.text_panel.focus_text()
            except Exception:
                self.ocr_text.focus_set()
        return "break"

    def _on_escape(self, event: Any) -> TkBindReturn:
        self._on_close()
        return "break"

    def _on_page_up(self, event: Any | None = None) -> TkBindReturn:
        self.focus_canvas()
        self.canvas.yview_scroll(-1, "pages")
        self._render_visible_pages()
        return "break"

    def _on_page_down(self, event: Any | None = None) -> TkBindReturn:
        self.focus_canvas()
        self.canvas.yview_scroll(1, "pages")
        self._render_visible_pages()
        return "break"

    def _on_home(self, event: Any | None = None) -> TkBindReturn:
        self.focus_canvas()
        self.canvas.yview_moveto(0.0)
        self._render_visible_pages()
        return "break"

    def _on_end(self, event: Any | None = None) -> TkBindReturn:
        self.focus_canvas()
        self.canvas.yview_moveto(1.0)
        self._render_visible_pages()
        return "break"

    def _on_space_press(self, event: Any) -> TkBindReturn:
        if not self._pan_active:
            self._pan_active = True
            self.canvas.configure(cursor="hand2")
        self.focus_canvas()
        return "break"

    def _on_space_release(self, event: Any) -> TkBindReturn:
        if self._pan_active:
            self._pan_active = False
            self.canvas.configure(cursor="")
        return "break"

    def _on_pan_button_press(self, event: Any) -> TkBindReturn:
        if not self._pan_active:
            return None
        self.focus_canvas()
        self.canvas.scan_mark(event.x, event.y)
        return "break"

    def _on_pan_motion(self, event: Any) -> TkBindReturn:
        if not self._pan_active:
            return None
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self._render_visible_pages()
        return "break"

    def _on_pan_button_release(self, event: Any) -> TkBindReturn:
        if not self._pan_active:
            return None
        return "break"

    def _ensure_text_panel(self) -> bool:
        if not self._has_text:
            return False
        if not self.var_show_text.get():
            self.var_show_text.set(True)
            self._toggle_text()
        return True

    def _first_visible_page(self) -> int:
        if not self._page_tops:
            return 0
        y0 = self.canvas.canvasy(0)
        page_heights = [int(self._page_sizes[idx][1] * self.zoom) for idx in range(len(self._page_tops))]
        return find_first_visible_page(
            canvas_y=y0,
            page_tops=self._page_tops,
            page_heights=page_heights,
        )

    def _ocr_copy(self):
        try:
            self.text_panel.text.event_generate("<<Copy>>")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao copiar texto OCR: %s", exc)

    def _ocr_select_all(self):
        try:
            self.text_panel.text.event_generate("<<SelectAll>>")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao selecionar texto OCR: %s", exc)

    def _show_ocr_menu(self, event):
        try:
            return self.text_panel._show_menu(event)
        except Exception:
            return "break"

    # ======== Unified viewer: PDF + Image ========
    def open_bytes(self, data: bytes, filename: str) -> bool:
        """
        Abre arquivo a partir de bytes. Detecta automaticamente se é PDF ou imagem.
        Retorna True se abriu com sucesso.
        """
        name = filename or ""
        guess_pdf, guess_image = is_pdf_or_image(name)
        lower_name = name.lower()
        self._is_pdf = bool(guess_pdf or lower_name.endswith(".pdf"))

        # alterna os controles específicos de PDF (paginação, OCR, etc.)
        self._toggle_pdf_controls(self._is_pdf)
        self._update_download_buttons(source=name, is_pdf=self._is_pdf, is_image=guess_image)

        if self._is_pdf:
            # evita label quebrar antes de setar contagem real
            self.page_count = 1
            self._pdf_bytes = data
            self._pdf_path = None
            self._update_download_buttons(is_pdf=True, is_image=False)
            return self._open_pdf_bytes(data, filename)

        # IMAGEM
        if Image is None or ImageTk is None:
            return False

        try:
            bio = io.BytesIO(data)
            self._img_pil = Image.open(bio)
            self._img_zoom = 1.0
            self.page_count = 1
            self._pdf_bytes = None
            self._pdf_path = None
            self._controller = None
            if self._img_pil:
                self._render_image(self._img_pil)
            self._update_download_buttons(source=name, is_pdf=False, is_image=True)
            return True
        except Exception:
            return False

    def _open_pdf_bytes(self, data: bytes, filename: str = "") -> bool:
        """Abre PDF a partir de bytes."""
        import tempfile

        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            try:
                tmp.write(data)
                tmp_path = tmp.name
            finally:
                tmp.close()

            # Carrega PDF normalmente
            self._is_pdf = True
            self._load_pdf(tmp_path)
            self._pdf_bytes = data
            self._pdf_path = None
            self._update_download_buttons(is_pdf=True, is_image=False)

            # Limpa arquivo temporário ao fechar
            def _cleanup(_event=None):
                try:
                    os.unlink(tmp_path)
                except OSError as exc:  # noqa: BLE001
                    logger.debug("Falha ao remover arquivo temporario do PDF viewer: %s", exc)

            self.bind("<Destroy>", _cleanup, add="+")
            return True
        except Exception:
            return False

    def _render_image(self, pil_img: Image.Image) -> None:  # type: ignore[name-defined]
        """Renderiza uma imagem PIL no canvas com zoom."""
        if Image is None or ImageTk is None:
            return

        # Garante canvas com tamanho válido (ao abrir, pode ser 1x1)
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            self.after(20, lambda: self._render_image(pil_img))
            return

        # Aplica zoom
        zw = int(pil_img.width * self._img_zoom)
        zh = int(pil_img.height * self._img_zoom)
        img = pil_img.resize((zw, zh), Image.LANCZOS)  # type: ignore[union-attr]
        self._img_ref = ImageTk.PhotoImage(img)  # type: ignore[union-attr]  # manter refer?ncia viva!
        self.page_view.show_image(self._img_ref, zw, zh)
        # Atualiza label como "1/1"
        self._update_page_label(1)

    def _toggle_pdf_controls(self, enabled: bool) -> None:
        """Habilita/desabilita controles específicos de PDF."""
        # Ex.: desabilita paginação/OCR quando for imagem
        state = "normal" if enabled else "disabled"

        for btn in getattr(self, "pdf_nav_buttons", []):
            try:
                btn.configure(state=state)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao alterar estado de botao de navegacao do PDF: %s", exc)

        if hasattr(self, "chk_text"):
            try:
                self.chk_text.configure(state=state)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Falha ao alterar estado do toggle de texto: %s", exc)

        # Atualizar texto do botão de download se existir
        # (assumindo que não temos referência direta ao botão)

    def _update_download_buttons(
        self,
        *,
        source: str | None = None,
        is_pdf: Optional[bool] = None,
        is_image: Optional[bool] = None,
    ) -> None:
        if source is not None:
            guess_pdf, guess_image = is_pdf_or_image(source)
            if is_pdf is None:
                is_pdf = guess_pdf
            if is_image is None:
                is_image = guess_image

        if is_pdf is None:
            is_pdf = False
        if is_image is None:
            is_image = False

        # Usa helper para calcular estados
        pdf_enabled, img_enabled = calculate_button_states(is_pdf=is_pdf, is_image=is_image)

        if self.btn_download_pdf is not None:
            self.btn_download_pdf.state(["!disabled"] if pdf_enabled else ["disabled"])
        if self.btn_download_img is not None:
            self.btn_download_img.state(["!disabled"] if img_enabled else ["disabled"])


# Helper para abrir a janela (ex.: integrar ao seu app principal)
