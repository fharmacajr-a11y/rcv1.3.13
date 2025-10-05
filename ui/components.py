"""Reusable Tkinter component helpers."""
from __future__ import annotations

from tkinter import ttk

def toolbar_button(parent, text, command):
    """Create a standard toolbar button and return it."""
    return ttk.Button(parent, text=text, command=command)


def labeled_entry(parent, label_text):
    """Return a label/entry pair for uniform forms."""
    label = ttk.Label(parent, text=label_text)
    entry = ttk.Entry(parent, width=50)
    return label, entry


# --- WhatsApp Icon helper ---------------------------------------------------
import os, re, webbrowser
import tkinter as tk
from PIL import Image, ImageTk, ImageOps

_ICON_CACHE: dict[tuple[str,int], ImageTk.PhotoImage] = {}

def get_whatsapp_icon(size: int = 15) -> ImageTk.PhotoImage | None:
    """Retorna PhotoImage do WhatsApp redimensionado com cache."""
    key = ("whatsapp.png", size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    try:
        assets = os.path.join(os.path.dirname(__file__), "..", "assets")
        assets = os.path.normpath(assets)
        base = None
        for cand in (f"whatsapp_{size}.png", "whatsapp.webp", "whatsapp.png"):
            p = os.path.join(assets, cand)
            if os.path.exists(p):
                base = p; break
        if not base:
            return None
        img = Image.open(base).convert("RGBA")
        if img.size != (size, size):
            img = ImageOps.contain(img, (size, size), Image.Resampling.LANCZOS)
        ph = ImageTk.PhotoImage(img)
        _ICON_CACHE[key] = ph
        return ph
    except Exception:
        return None


def draw_whatsapp_overlays(tree: tk.Widget, column: str, size: int = 15):
    """Desenha ícones do WhatsApp sobre a coluna especificada em um Treeview."""
    if not hasattr(tree, "_wa_overlays"):
        tree._wa_overlays = []
    # limpar
    for w in getattr(tree, "_wa_overlays", []):
        try: w.destroy()
        except: pass
    tree._wa_overlays = []

    icon = get_whatsapp_icon(size)
    if not icon: return

    try:
        for iid in tree.get_children(""):
            bbox = tree.bbox(iid, column)
            if not bbox: continue
            x,y,w,h = bbox
            numero = tree.set(iid, column)
            if not numero: continue
            lbl = tk.Label(tree, image=icon, borderwidth=0, cursor="hand2")
            lbl.place(x=x+2, y=y+(h//2), anchor="w")
            lbl.bind("<Button-1>", lambda e,n=numero: _abrir_whatsapp(n))
            tree._wa_overlays.append(lbl)
    except Exception:
        pass


def _abrir_whatsapp(numero: str):
    dig = re.sub(r"\D", "", numero or "")
    if not dig: return
    if not dig.startswith("55"):
        dig = "55" + dig
    try:
        webbrowser.open_new(f"https://web.whatsapp.com/send?phone={dig}")
    except Exception:
        pass


__all__ = [
    "toolbar_button",
    "labeled_entry",
    "get_whatsapp_icon",
    "draw_whatsapp_overlays",
]
