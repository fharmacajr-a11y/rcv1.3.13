# -*- coding: utf-8 -*-
"""Visualizador de imagens com zoom e pan."""
from __future__ import annotations

import io
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional, TYPE_CHECKING

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None  # type: ignore[assignment, misc]
    ImageTk = None  # type: ignore[assignment, misc]

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage
    from PIL.ImageTk import PhotoImage as PILPhotoImage


class ImageViewer(tk.Toplevel):
    """Janela para visualizar imagens com zoom e pan."""

    def __init__(
        self,
        parent: tk.Misc,
        image_data: bytes,
        display_name: str = "Imagem"
    ):
        """
        Args:
            parent: Janela pai
            image_data: Bytes da imagem (JPEG, PNG, GIF)
            display_name: Nome para exibir no título
        """
        super().__init__(parent)
        self.title(f"Visualizar: {display_name}")
        self.geometry("900x700")

        if Image is None or ImageTk is None:
            messagebox.showerror(
                "Erro",
                "Pillow não instalado. Instale com: pip install Pillow",
                parent=parent
            )
            self.destroy()
            return

        # Estado
        self.image_data = image_data
        self.display_name = display_name
        self.original_image: Optional["PILImage"] = None
        self.current_image: Optional["PILImage"] = None
        self.photo: Optional["PILPhotoImage"] = None
        self.zoom_level = 1.0
        self.pan_start: Optional[tuple[int, int]] = None
        self.canvas_image_id: Optional[int] = None

        # Carregar imagem
        try:
            img = Image.open(io.BytesIO(image_data))  # type: ignore[union-attr]
            self.original_image = img
            self.current_image = img.copy()
        except Exception as e:
            messagebox.showerror(
                "Erro ao carregar imagem",
                f"Não foi possível abrir a imagem:\n{e}",
                parent=parent
            )
            self.destroy()
            return

        # Canvas com scrollbars
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.canvas = tk.Canvas(canvas_frame, bg="#2b2b2b", highlightthickness=0)
        scroll_y = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        scroll_x = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        # Barra de ferramentas
        toolbar = ttk.Frame(self)
        toolbar.pack(side="bottom", fill="x", padx=8, pady=(0, 8))

        ttk.Button(toolbar, text="Ajustar à largura", command=self._fit_to_width).pack(side="left", padx=2)
        ttk.Button(toolbar, text="100%", command=self._reset_zoom).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Salvar como...", command=self._save_as).pack(side="left", padx=2)

        self.zoom_label = ttk.Label(toolbar, text="100%")
        self.zoom_label.pack(side="left", padx=12)

        ttk.Button(toolbar, text="Fechar", command=self.destroy).pack(side="right", padx=2)

        # Binds
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self._on_pan_start)
        self.canvas.bind("<B1-Motion>", self._on_pan_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_pan_end)
        self.bind("<Escape>", lambda e: self.destroy())

        # Exibir imagem inicial
        self._fit_to_width()

    def _update_canvas(self):
        """Atualiza o canvas com a imagem atual."""
        if self.current_image is None or ImageTk is None:
            return

        # Converter para PhotoImage
        self.photo = ImageTk.PhotoImage(self.current_image)  # type: ignore[union-attr]

        # Atualizar canvas
        if self.canvas_image_id is None:
            self.canvas_image_id = self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        else:
            self.canvas.itemconfig(self.canvas_image_id, image=self.photo)

        # Atualizar scrollregion
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        # Atualizar label de zoom
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")

    def _apply_zoom(self, new_zoom: float):
        """Aplica um novo nível de zoom."""
        if self.original_image is None or Image is None:
            return

        self.zoom_level = max(0.1, min(new_zoom, 10.0))  # Limita entre 10% e 1000%

        # Redimensionar imagem
        w, h = self.original_image.size
        new_w = int(w * self.zoom_level)
        new_h = int(h * self.zoom_level)

        # Usar LANCZOS se disponível, senão BICUBIC
        try:
            resample = Image.Resampling.LANCZOS  # type: ignore[union-attr]
        except AttributeError:
            resample = Image.BICUBIC  # type: ignore[union-attr]

        self.current_image = self.original_image.resize((new_w, new_h), resample)
        self._update_canvas()

    def _on_mousewheel(self, event):
        """Zoom com roda do mouse."""
        if event.delta > 0:
            self._apply_zoom(self.zoom_level * 1.1)
        else:
            self._apply_zoom(self.zoom_level / 1.1)

    def _on_pan_start(self, event):
        """Inicia pan (arrastar)."""
        self.canvas.scan_mark(event.x, event.y)
        self.pan_start = (event.x, event.y)

    def _on_pan_move(self, event):
        """Move com pan."""
        if self.pan_start:
            self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_pan_end(self, _event):
        """Finaliza pan."""
        self.pan_start = None

    def _fit_to_width(self):
        """Ajusta imagem à largura do canvas."""
        if self.original_image is None:
            return

        self.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        img_width = self.original_image.size[0]

        if img_width > 0:
            zoom = (canvas_width - 20) / img_width  # -20 para margem
            self._apply_zoom(zoom)

    def _reset_zoom(self):
        """Reseta zoom para 100%."""
        self._apply_zoom(1.0)

    def _save_as(self):
        """Salva imagem em disco."""
        if self.original_image is None:
            return

        # Sugerir nome com extensão
        ext = Path(self.display_name).suffix or ".png"
        suggested = Path(self.display_name).stem + ext

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar imagem como",
            initialfile=suggested,
            defaultextension=ext,
            filetypes=[
                ("Imagem PNG", "*.png"),
                ("Imagem JPEG", "*.jpg *.jpeg"),
                ("Imagem GIF", "*.gif"),
                ("Todos os arquivos", "*.*")
            ]
        )

        if path:
            try:
                self.original_image.save(path)
                messagebox.showinfo("Salvo", f"Imagem salva em:\n{path}", parent=self)
            except Exception as e:
                messagebox.showerror("Erro ao salvar", f"Falha ao salvar imagem:\n{e}", parent=self)


def open_image_viewer(parent: tk.Misc, image_data: bytes, display_name: str = "Imagem") -> Optional[ImageViewer]:
    """
    Abre o visualizador de imagens.

    Args:
        parent: Janela pai
        image_data: Bytes da imagem
        display_name: Nome para exibir no título

    Returns:
        Janela ImageViewer ou None se falhou
    """
    try:
        viewer = ImageViewer(parent, image_data, display_name)
        return viewer
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível abrir o visualizador:\n{e}", parent=parent)
        return None
