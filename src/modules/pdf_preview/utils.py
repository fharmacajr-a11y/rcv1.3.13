"""Utilitários para o módulo de preview de PDF."""

from __future__ import annotations

import tkinter as tk
from collections import OrderedDict
from typing import Any, Optional, Tuple

try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None  # type: ignore


class LRUCache:
    """Cache LRU (Least Recently Used) genérico."""

    def __init__(self, capacity: int = 12) -> None:
        self.capacity = capacity
        self.data: OrderedDict[Any, Any] = OrderedDict()

    def get(self, key: Any) -> Any:
        """Retorna valor associado à chave, movendo para o final (mais recente)."""
        if key in self.data:
            self.data.move_to_end(key)
            return self.data[key]
        return None

    def put(self, key: Any, value: Any) -> None:
        """Insere ou atualiza valor, removendo itens antigos se exceder capacidade."""
        self.data[key] = value
        self.data.move_to_end(key)
        while len(self.data) > self.capacity:
            self.data.popitem(last=False)

    def clear(self) -> None:
        """Limpa todo o cache."""
        self.data.clear()


def pixmap_to_photoimage(pixmap: Any) -> Optional[tk.PhotoImage]:
    """
    Converte um fitz.Pixmap (PyMuPDF) para tk.PhotoImage.

    Args:
        pixmap: Objeto Pixmap do PyMuPDF (fitz)

    Returns:
        tk.PhotoImage ou None se falhar
    """
    if pixmap is None:
        return None

    try:
        # Tenta usar PIL se disponível (melhor qualidade)
        if Image is not None and ImageTk is not None:
            mode = "RGB" if pixmap.n < 4 else "RGBA"
            # Converter para tuple para Image.frombytes
            size_tuple: Tuple[int, int] = (int(pixmap.width), int(pixmap.height))
            img = Image.frombytes(mode, size_tuple, pixmap.samples)
            return ImageTk.PhotoImage(img)  # type: ignore

        # Fallback sem PIL (formato PPM)
        data = pixmap.tobytes("ppm")
        return tk.PhotoImage(data=data)
    except Exception:
        return None
