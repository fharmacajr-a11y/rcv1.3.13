from __future__ import annotations

import io
import mimetypes
import os
import shutil
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from collections import OrderedDict
from typing import TYPE_CHECKING, Optional, Tuple, List, cast

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from PIL import Image, ImageTk  # opcional
except Exception:
    Image = ImageTk = None

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage
    from PIL.ImageTk import PhotoImage as PILPhotoImage

from src.ui.wheel_windows import wheel_steps
from src.ui.search_nav import SearchNavigator


GAP = 16  # espaço entre páginas


class LRUCache:
    def __init__(self, capacity=12):
        self.capacity = capacity
        self.data = OrderedDict()

    def get(self, key):
        if key in self.data:
            self.data.move_to_end(key)
            return self.data[key]
        return None

    def put(self, key, value):
        self.data[key] = value
        self.data.move_to_end(key)
        while len(self.data) > self.capacity:
            self.data.popitem(last=False)

    def clear(self):
        self.data.clear()


class PdfViewerWin(tk.Toplevel):
    def __init__(
        self,
        master,
        pdf_path: str | None = None,
        display_name: str | None = None,
        data_bytes: bytes | None = None,
    ):
        super().__init__(master)
        self._src_pdf_path = pdf_path or ""
        self._display_name = display_name or (os.path.basename(pdf_path) if pdf_path else "Documento")
        self.title(f"Visualizar: {self._display_name}")
        self.geometry("1200x800")
        self.zoom = 1.0
        self._img_refs = {}          # id_canvas -> PhotoImage
        self._items = []             # ids de imagens por página
        self._page_tops = []         # y de cada página
        self._page_sizes = []        # (w,h) em 1.0
        self.cache = LRUCache(12)
        self._pan_active = False
        self._closing = False
        self._fit_mode = False
        self._shortcut_sequences = []
        self._page_label_suffix = ""
        self._has_text = False
        self._ocr_loaded = False

        # Controle para modo de imagem
        self._is_pdf: bool = False
        self.page_count: int = 1  # evita AttributeError antes do carregamento
        self._img_pil: Optional[Image.Image] = None  # type: ignore[name-defined]
        self._img_ref: Optional[ImageTk.PhotoImage] = None  # type: ignore[name-defined]  # manter referência viva

        # Top bar
        top = ttk.Frame(self)
        top.pack(side="top", fill="x")
        ttk.Button(top, text="\u2212", width=3, command=lambda: self._zoom_by(-1)).pack(side="left", padx=(8, 0), pady=6)
        ttk.Button(top, text="100%", command=lambda: self._set_zoom_exact(1.0)).pack(side="left", padx=4, pady=6)
        ttk.Button(top, text="+", width=3, command=lambda: self._zoom_by(+1)).pack(side="left", padx=4, pady=6)
        ttk.Button(top, text="Largura", command=self._set_zoom_fit_width).pack(side="left", padx=8, pady=6)
        self.lbl_page = ttk.Label(top, text="Página 1/1")
        self.lbl_page.pack(side="left", padx=12)
        self.lbl_zoom = ttk.Label(top, text="100%")
        self.lbl_zoom.pack(side="left", padx=6)
        self.lbl_zoom.bind("<Button-1>", lambda e: self._toggle_fit_100())
        self.var_show_text = tk.BooleanVar(value=False)
        self.chk_text = ttk.Checkbutton(
            top,
            text="Texto",
            variable=self.var_show_text,
            command=self._toggle_text,
        )
        self.chk_text.pack(side="left", padx=12)
        ttk.Button(top, text="Baixar PDF", command=self._download_pdf).pack(side="right", padx=8, pady=6)

        # Paned layout (canvas | text)
        pane = ttk.Panedwindow(self, orient="horizontal")
        pane.pack(side="top", fill="both", expand=True)

        # Canvas com scrollbar
        left = ttk.Frame(pane)
        self.canvas = tk.Canvas(left, background="#f3f3f3", highlightthickness=0)
        vs = ttk.Scrollbar(left, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vs.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        pane.add(left, weight=4)

        # Painel de texto (OCR)
        right = ttk.Frame(pane)
        self.ocr_text = ScrolledText(right, wrap="word", height=10)
        self.ocr_text.pack(side="top", fill="both", expand=True)
        self._ocr_menu = tk.Menu(self, tearoff=0)
        self._ocr_menu.add_command(label="Copiar", command=self._ocr_copy)
        self._ocr_menu.add_command(label="Selecionar tudo", command=self._ocr_select_all)
        self.ocr_text.bind("<Button-3>", self._show_ocr_menu)
        self._pane = pane
        self._pane_right = right
        self._pane.add(self._pane_right, weight=2)
        self._pane.forget(self._pane_right)
        self._pane_right_added = False

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
            ("<Control-plus>",  lambda e: (self._zoom_by(+1, e), "break")),
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

        # Busca (F3/Shift+F3) para o painel de texto
        self.search_nav = SearchNavigator(self.ocr_text)
        self.ocr_text.bind("<F3>",       lambda e: (self.search_nav.next(), "break"))
        self.ocr_text.bind("<Shift-F3>", lambda e: (self.search_nav.prev(), "break"))
        self.ocr_text.tag_raise("sel")

        # Carrega conteúdo
        if data_bytes:
            # Se veio bytes, detecta o tipo e abre
            self.open_bytes(data_bytes, self._display_name)
        elif pdf_path:
            # Se veio caminho, carrega PDF tradicional
            self._load_pdf(pdf_path)

    # ======== PDF load / render ========
    def _load_pdf(self, path):
        self.doc = None
        self.page_count = 0
        self._text_buffer = []
        if fitz is not None:
            try:
                self.doc = fitz.open(path)
                self.page_count = self.doc.page_count
                # medidas base (em 1.0) via page.rect
                self._page_sizes = [(int(p.rect.width), int(p.rect.height)) for p in self.doc]
                self._text_buffer = [p.get_text("text") for p in self.doc]
            except Exception:
                pass
        if self.doc is None:
            # degrade: 1 página placeholder
            self.page_count = 1
            self._page_sizes = [(800, 1100)]
            self._text_buffer = ["Texto indisponível (PyMuPDF não detectado)."]

        # Garantir que _text_buffer contém apenas strings
        safe_text_buffer: List[str] = []
        for t in self._text_buffer:
            if isinstance(t, (bytes, bytearray)):
                safe_text_buffer.append(t.decode("utf-8", "ignore"))
            elif t is None:
                safe_text_buffer.append("")
            else:
                safe_text_buffer.append(str(t))
        self._text_buffer = safe_text_buffer
        
        self._has_text = any((t or "").strip() for t in self._text_buffer)
        self._page_label_suffix = "\u2022  OCR: OK" if self._has_text else "\u2022  OCR: vazio"
        self._ocr_loaded = False
        self.var_show_text.set(False)

        self._reflow_pages()

        self.ocr_text.delete("1.0", "end")
        if not self._has_text:
            self.ocr_text.insert("1.0", "Nenhum texto/OCR foi encontrado para este documento.")
            try:
                self._pane.forget(self._pane_right)
            except Exception:
                pass
            self._pane_right_added = False
            self.var_show_text.set(False)
            self.chk_text.state(["disabled"])
        else:
            self.chk_text.state(["!disabled"])
        self._update_page_label(0)

    def _reflow_pages(self):
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
        for (w1, h1) in self._page_sizes:
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

    def _on_canvas_configure(self, event):
        # manter scrollregion atualizada
        if self._is_pdf:
            self._render_visible_pages()
            self._update_scrollregion()
        else:
            # re-renderiza a IMAGEM para o novo tamanho do canvas
            if self._img_pil is not None:
                self._render_image(self._img_pil)

    def _render_visible_pages(self):
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

    def _ensure_page_rendered(self, i):
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

    def _render_page_image(self, index, zoom):
        w1, h1 = self._page_sizes[index]
        if fitz is None or self.doc is None:
            # placeholder
            ph = tk.PhotoImage(width=max(200, int(w1 * zoom)), height=max(200, int(h1 * zoom)))
            return ph
        page = self.doc.load_page(index)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        if Image is not None and ImageTk is not None:
            mode = "RGB" if pix.n < 4 else "RGBA"
            # Converter list para tuple[int, int] para Image.frombytes
            size_tuple: Tuple[int, int] = (int(pix.width), int(pix.height))
            img = Image.frombytes(mode, size_tuple, pix.samples)
            return ImageTk.PhotoImage(img)
        # fallback sem Pillow (ppm)
        data = pix.tobytes("ppm")
        return tk.PhotoImage(data=data)

    def _update_page_label(self, index):
        total = max(1, getattr(self, "page_count", 1))
        clamped = max(0, min(index, total - 1))
        zoom_pct = int(round(self.zoom * 100))
        suffix = f"  {self._page_label_suffix}" if self._page_label_suffix else ""
        try:
            self.lbl_page.config(text=f"Página {clamped + 1}/{total}{suffix}")
            self.lbl_zoom.config(text=f"{zoom_pct}%")
        except Exception:
            pass

    # ======== Wheel / Zoom ========
    def _on_wheel_scroll(self, event):
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

    def _on_wheel_zoom(self, event):
        if not self.canvas.winfo_exists():
            return "break"
        steps = wheel_steps(event)
        if steps:
            self._zoom_by(steps, event)
        return "break"

    def _zoom_by(self, wheel_steps_count, event=None):
        Z_MIN, Z_MAX, Z_STEP = 0.2, 6.0, 0.1
        old = self.zoom
        new = max(Z_MIN, min(Z_MAX, round(old + wheel_steps_count * Z_STEP, 2)))
        if abs(new - old) < 1e-9:
            return
        self._fit_mode = False

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

    def _set_zoom_fit_width(self):
        cwidth = max(1, self.canvas.winfo_width() - 2 * GAP)
        base_w = max(w for (w, h) in self._page_sizes)
        target = max(0.2, min(6.0, round(cwidth / base_w, 2)))
        self._set_zoom_exact(target, fit_mode=True)

    def _set_zoom_exact(self, value, *, fit_mode: bool = False):
        self._fit_mode = fit_mode
        self.zoom = max(0.2, min(6.0, float(value)))
        self._reflow_pages()
        self._render_visible_pages()
        self._update_scrollregion()

    def _toggle_fit_100(self):
        if self._fit_mode:
            self._set_zoom_exact(1.0, fit_mode=False)
        else:
            self._set_zoom_fit_width()

    # ======== Texto / Busca ========
    def _toggle_text(self):
        if not self._has_text and self.var_show_text.get():
            self.var_show_text.set(False)
            return
        show = self.var_show_text.get()
        if show and not self._pane_right_added:
            self._pane.add(self._pane_right, weight=2)
            self._pane_right_added = True
            if self._has_text and not self._ocr_loaded:
                self._populate_ocr_text()
        elif (not show) and self._pane_right_added:
            self._pane.forget(self._pane_right)
            self._pane_right_added = False

    def _populate_ocr_text(self):
        sep = "\n" + ("\u2014" * 40) + "\n"
        self.ocr_text.delete("1.0", "end")
        # _text_buffer já foi normalizado para List[str] em _load_pdf
        text_buffer_str: List[str] = cast(List[str], self._text_buffer)
        self.ocr_text.insert("1.0", sep.join(text_buffer_str))
        self._ocr_loaded = True

    def focus_canvas(self):
        self.canvas.focus_set()

    def _update_scrollregion(self):
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)

    def _get_downloads_dir(self):
        try:
            import ctypes
            import ctypes.wintypes
            import uuid

            folder_id_downloads = uuid.UUID("{374DE290-123F-4565-9164-39C4925E467B}")
            SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
            SHGetKnownFolderPath.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_wchar_p),
            ]
            p_path = ctypes.c_wchar_p()
            # Converter bytes_le para int via int.from_bytes
            guid_bytes = folder_id_downloads.bytes_le
            guid_int = int.from_bytes(guid_bytes, byteorder="little")
            hr = SHGetKnownFolderPath(
                ctypes.c_void_p(guid_int),
                0,
                None,
                ctypes.byref(p_path),
            )
            if hr == 0 and p_path.value:
                return p_path.value
        except Exception:
            pass
        return os.path.join(os.path.expanduser("~"), "Downloads")

    def _download_pdf(self):
        src = getattr(self, "_src_pdf_path", None)
        if not src or not os.path.exists(src):
            return
        downloads = self._get_downloads_dir()
        base = self._display_name if getattr(self, "_display_name", None) else os.path.basename(src)
        name = base if base.lower().endswith(".pdf") else f"{base}.pdf"
        dst = os.path.join(downloads, name)
        root, ext = os.path.splitext(dst)
        counter = 1
        while os.path.exists(dst):
            dst = f"{root} ({counter}){ext}"
            counter += 1
        shutil.copy2(src, dst)
        try:
            from tkinter import messagebox

            messagebox.showinfo("Baixar PDF", f"Salvo em:\n{dst}", parent=self)
        except Exception:
            pass

    def _on_close(self):
        if self._closing:
            return
        self._closing = True
        try:
            doc = getattr(self, "doc", None)
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass
        finally:
            self.destroy()

    def _on_destroy(self, event=None):
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
        except Exception:
            pass

    def _bind_shortcuts(self):
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

    def _handle_zoom_key(self, step, event):
        if event.state & 0x0004:  # ignore when Ctrl is held (handled elsewhere)
            return None
        self.focus_canvas()
        self._zoom_by(step)
        return "break"

    def _on_zoom_reset(self, event):
        if event.state & 0x0004:
            return None
        self.focus_canvas()
        self._set_zoom_exact(1.0)
        return "break"

    def _on_zoom_fit(self, event):
        if event.state & 0x0004:
            return None
        self.focus_canvas()
        self._set_zoom_fit_width()
        return "break"

    def _on_save_shortcut(self, event):
        self._download_pdf()
        return "break"

    def _on_find_shortcut(self, event):
        if self._ensure_text_panel():
            self.ocr_text.focus_set()
        return "break"

    def _on_escape(self, event):
        self._on_close()
        return "break"

    def _on_page_up(self, event):
        self.focus_canvas()
        self.canvas.yview_scroll(-1, "pages")
        self._render_visible_pages()
        return "break"

    def _on_page_down(self, event):
        self.focus_canvas()
        self.canvas.yview_scroll(1, "pages")
        self._render_visible_pages()
        return "break"

    def _on_home(self, event):
        self.focus_canvas()
        self.canvas.yview_moveto(0.0)
        self._render_visible_pages()
        return "break"

    def _on_end(self, event):
        self.focus_canvas()
        self.canvas.yview_moveto(1.0)
        self._render_visible_pages()
        return "break"

    def _on_space_press(self, event):
        if not self._pan_active:
            self._pan_active = True
            self.canvas.configure(cursor="hand2")
        self.focus_canvas()
        return "break"

    def _on_space_release(self, event):
        if self._pan_active:
            self._pan_active = False
            self.canvas.configure(cursor="")
        return "break"

    def _on_pan_button_press(self, event):
        if not self._pan_active:
            return None
        self.focus_canvas()
        self.canvas.scan_mark(event.x, event.y)
        return "break"

    def _on_pan_motion(self, event):
        if not self._pan_active:
            return None
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self._render_visible_pages()
        return "break"

    def _on_pan_button_release(self, event):
        if not self._pan_active:
            return None
        return "break"

    def _ensure_text_panel(self):
        if not self._has_text:
            return False
        if not self.var_show_text.get():
            self.var_show_text.set(True)
            self._toggle_text()
        return True

    def _first_visible_page(self):
        if not self._page_tops:
            return 0
        y0 = self.canvas.canvasy(0)
        for idx, top in enumerate(self._page_tops):
            height = int(self._page_sizes[idx][1] * self.zoom)
            if y0 < top + height:
                return idx
        return len(self._page_tops) - 1

    def _ocr_copy(self):
        try:
            self.ocr_text.event_generate("<<Copy>>")
        except Exception:
            pass

    def _ocr_select_all(self):
        self.ocr_text.event_generate("<<SelectAll>>")

    def _show_ocr_menu(self, event):
        self.ocr_text.focus_set()
        try:
            self._ocr_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._ocr_menu.grab_release()
        return "break"

    # ======== Unified viewer: PDF + Image ========
    def open_bytes(self, data: bytes, filename: str) -> bool:
        """
        Abre arquivo a partir de bytes. Detecta automaticamente se é PDF ou imagem.
        Retorna True se abriu com sucesso.
        """
        # Detecta tipo MIME
        mime, _ = mimetypes.guess_type(filename or "")
        self._is_pdf = bool(mime == "application/pdf" or filename.lower().endswith(".pdf"))

        # alterna os controles específicos de PDF (paginação, OCR, etc.)
        self._toggle_pdf_controls(self._is_pdf)

        if self._is_pdf:
            # evita label quebrar antes de setar contagem real
            self.page_count = 1
            return self._open_pdf_bytes(data, filename)

        # IMAGEM
        if Image is None or ImageTk is None:
            return False
        
        try:
            bio = io.BytesIO(data)
            self._img_pil = Image.open(bio)
            self.page_count = 1
            if self._img_pil:
                self._render_image(self._img_pil)
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

            # Limpa arquivo temporário ao fechar
            def _cleanup(_event=None):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

            self.bind("<Destroy>", _cleanup, add="+")
            return True
        except Exception:
            return False

    def _render_image(self, pil_img: Image.Image) -> None:  # type: ignore[name-defined]
        """Renderiza uma imagem PIL no canvas."""
        if Image is None or ImageTk is None:
            return

        # Garante canvas com tamanho válido (ao abrir, pode ser 1x1)
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            self.after(20, lambda: self._render_image(pil_img))
            return

        img = pil_img.copy()
        # Encaixa mantendo proporção; margenzinha pro visual
        img.thumbnail((max(32, w - 24), max(32, h - 24)))
        self._img_ref = ImageTk.PhotoImage(img)  # type: ignore[union-attr]  # manter referência viva!
        self.canvas.delete("all")
        self.canvas.create_image(w // 2, h // 2, image=self._img_ref, anchor="center")
        # Atualiza label como "1/1"
        self._update_page_label(1)

    def _toggle_pdf_controls(self, enabled: bool) -> None:
        """Habilita/desabilita controles específicos de PDF."""
        # Ex.: desabilita paginação/OCR quando for imagem
        state = "normal" if enabled else "disabled"
        
        for btn in getattr(self, "pdf_nav_buttons", []):
            try:
                btn.configure(state=state)
            except Exception:
                pass
        
        if hasattr(self, "chk_text"):
            try:
                self.chk_text.configure(state=state)
            except Exception:
                pass
        
        # Atualizar texto do botão de download se existir
        # (assumindo que não temos referência direta ao botão)


# Helper para abrir a janela (ex.: integrar ao seu app principal)
def open_pdf_viewer(
    master,
    pdf_path: str | None = None,
    display_name: str | None = None,
    data_bytes: bytes | None = None,
):
    """
    Abre visualizador unificado de PDF/imagem.

    Args:
        master: widget pai
        pdf_path: caminho do arquivo (se disponível)
        display_name: nome para exibição
        data_bytes: bytes do arquivo (alternativa a pdf_path)
    """
    win = PdfViewerWin(
        master,
        pdf_path=pdf_path,
        display_name=display_name,
        data_bytes=data_bytes,
    )
    win.focus_canvas()
    return win
