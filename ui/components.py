"""Reusable Tkinter component helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence
import logging
import os
import re
import webbrowser

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

import ttkbootstrap as tb
from PIL import Image, ImageOps, ImageTk

from config.constants import (
    COL_CNPJ_WIDTH,
    COL_ID_WIDTH,
    COL_NOME_WIDTH,
    COL_OBS_WIDTH,
    COL_RAZAO_WIDTH,
    COL_ULTIMA_WIDTH,
    COL_WHATSAPP_WIDTH,
)

logger = logging.getLogger(__name__)
log = logger

STATUS_DOT = "\u25CF"
OBS_FG = "#0d6efd"


@dataclass(slots=True)
class MenuComponents:
    menu: tk.Menu
    theme_var: tk.StringVar
    tema_menu: tk.Menu


@dataclass(slots=True)
class SearchControls:
    frame: tb.Frame
    search_var: tk.StringVar
    order_var: tk.StringVar
    entry: tb.Entry
    search_button: tb.Button
    clear_button: tb.Button
    order_combobox: tb.Combobox


@dataclass(slots=True)
class FooterButtons:
    frame: tb.Frame
    novo: tb.Button
    editar: tb.Button
    subpastas: tb.Button
    enviar: tb.Button
    lixeira: tb.Button


@dataclass(slots=True)
class StatusIndicators:
    frame: tb.Frame
    count_var: tk.StringVar
    status_dot_var: tk.StringVar
    status_text_var: tk.StringVar
    status_dot: tb.Label
    status_label: tb.Label


def toolbar_button(parent: tk.Misc, text: str, command: Callable[[], Any]) -> ttk.Button:
    """Create a standard toolbar button and return it."""
    return ttk.Button(parent, text=text, command=command)


def labeled_entry(parent: tk.Misc, label_text: str) -> tuple[ttk.Label, ttk.Entry]:
    """Return a label/entry pair for uniform forms."""
    label = ttk.Label(parent, text=label_text)
    entry = ttk.Entry(parent, width=50)
    return label, entry


def create_menubar(
    root: tk.Misc,
    theme_name: str,
    on_set_theme: Callable[[str], None],
    on_show_changelog: Callable[[], None],
    on_exit: Callable[[], None],
) -> MenuComponents:
    """Create and attach the application menubar."""
    theme_var = tk.StringVar(master=root, value=theme_name or "flatly")
    menubar = tk.Menu(root)
    menu_arquivo = tk.Menu(menubar, tearoff=0)

    def _apply_theme(valor: str) -> None:
        if not valor:
            return
        on_set_theme(valor)

    tema_menu = tk.Menu(menu_arquivo, tearoff=0)
    tema_menu.add_radiobutton(
        label="Tema claro",
        variable=theme_var,
        value="flatly",
        command=lambda: _apply_theme("flatly"),
    )
    tema_menu.add_radiobutton(
        label="Tema escuro",
        variable=theme_var,
        value="darkly",
        command=lambda: _apply_theme("darkly"),
    )
    menu_arquivo.add_cascade(label="Tema", menu=tema_menu)

    menu_ajuda = tk.Menu(menu_arquivo, tearoff=0)
    menu_ajuda.add_command(label="Sobre/Changelog", command=on_show_changelog)
    menu_arquivo.add_cascade(label="Ajuda", menu=menu_ajuda)

    menu_arquivo.add_separator()
    menu_arquivo.add_command(label="Sair", command=on_exit)

    menubar.add_cascade(label="Arquivo", menu=menu_arquivo)
    try:
        root.config(menu=menubar)
    except Exception as exc:
        log.exception("Falha ao anexar menubar", exc_info=exc)

    return MenuComponents(menu=menubar, theme_var=theme_var, tema_menu=tema_menu)


def create_search_controls(
    parent: tk.Misc,
    *,
    order_choices: Iterable[str],
    default_order: str,
    on_search: Callable[[Any | None], Any] | None,
    on_clear: Callable[[], Any] | None,
    on_order_change: Callable[[], Any] | None,
    search_var: tk.StringVar | None = None,
    order_var: tk.StringVar | None = None,
    entry_width: int = 40,
) -> SearchControls:
    """Build the search + ordering toolbar."""
    frame = tb.Frame(parent)

    search_var = search_var or tk.StringVar(master=parent)
    order_var = order_var or tk.StringVar(master=parent, value=default_order)

    tb.Label(frame, text="Pesquisar:").pack(side="left", padx=5)

    def _trigger_search(event: Any | None = None) -> None:
        if on_search:
            on_search(event)

    entry = tb.Entry(frame, textvariable=search_var, width=entry_width)
    entry.pack(side="left", padx=5)
    entry.bind("<KeyRelease>", _trigger_search, add="+")

    search_button = tb.Button(frame, text="Buscar", command=_trigger_search)
    search_button.pack(side="left", padx=5)

    clear_button = tb.Button(
        frame,
        text="Limpar",
        command=lambda: on_clear() if on_clear else None,
    )
    clear_button.pack(side="left", padx=5)

    tb.Label(frame, text="Ordenar por:").pack(side="left", padx=5)

    def _order_changed(_event: Any | None = None) -> None:
        if on_order_change:
            on_order_change()

    order_combobox = tb.Combobox(
        frame,
        textvariable=order_var,
        values=list(order_choices),
        state="readonly",
        width=28,
    )
    order_combobox.pack(side="left", padx=5)
    order_combobox.bind("<<ComboboxSelected>>", _order_changed, add="+")

    return SearchControls(
        frame=frame,
        search_var=search_var,
        order_var=order_var,
        entry=entry,
        search_button=search_button,
        clear_button=clear_button,
        order_combobox=order_combobox,
    )


def create_clients_treeview(
    parent: tk.Misc,
    *,
    on_double_click: Callable[[Any], Any] | None,
    on_select: Callable[[Any], Any] | None,
    on_delete: Callable[[Any], Any] | None,
    on_click: Callable[[Any], Any] | None,
) -> tb.Treeview:
    """Create the main clients Treeview configured with column widths and bindings."""
    columns = (
        ("ID", "ID", COL_ID_WIDTH, False),
        ("Razao Social", "Razão Social", COL_RAZAO_WIDTH, True),
        ("CNPJ", "CNPJ", COL_CNPJ_WIDTH, False),
        ("Nome", "Nome", COL_NOME_WIDTH, False),
        ("WhatsApp", "WhatsApp", COL_WHATSAPP_WIDTH, False),
        ("Observacoes", "Observações", COL_OBS_WIDTH, True),
        ("Ultima Alteracao", "Última Alteração", COL_ULTIMA_WIDTH, False),
    )

    tree = tb.Treeview(parent, columns=[c[0] for c in columns], show="headings")

    for key, heading, _, _ in columns:
        tree.heading(key, text=heading, anchor="center")

    for key, _, width, can_stretch in columns:
        tree.column(key, width=width, minwidth=width, anchor="center", stretch=can_stretch)

    def _block_header_resize(event: Any) -> str | None:
        if tree.identify_region(event.x, event.y) == "separator":
            return "break"
        return None

    tree.bind("<Button-1>", _block_header_resize, add="+")

    try:
        default_font = tkfont.nametofont("TkDefaultFont")
        bold_font = default_font.copy()
        bold_font.configure(weight="bold")
        tree.tag_configure("has_obs", font=bold_font, foreground=OBS_FG)
    except Exception as exc:
        log.debug("Falha ao configurar fonte em negrito: %s", exc)

    if on_double_click:
        tree.bind("<Double-1>", on_double_click, add="+")
    if on_select:
        tree.bind("<<TreeviewSelect>>", on_select, add="+")
    if on_delete:
        tree.bind("<Delete>", on_delete, add="+")
    if on_click:
        tree.bind("<ButtonRelease-1>", on_click, add="+")

    def _on_motion_hand_cursor(event: Any) -> None:
        try:
            col = tree.identify_column(event.x)
            tree.configure(cursor="hand2" if col == "#5" else "")
        except Exception:
            tree.configure(cursor="")

    tree.bind("<Motion>", _on_motion_hand_cursor, add="+")
    tree.bind("<Leave>", lambda _e: tree.configure(cursor=""), add="+")

    return tree


def create_footer_buttons(
    parent: tk.Misc,
    *,
    on_novo: Callable[[], Any],
    on_editar: Callable[[], Any],
    on_subpastas: Callable[[], Any],
    on_enviar: Callable[[], Any],
    on_lixeira: Callable[[], Any],
) -> FooterButtons:
    """Create the footer buttons frame used on the main window."""
    frame = tb.Frame(parent)

    btn_novo = tb.Button(frame, text="Novo Cliente", command=on_novo, bootstyle="success")
    btn_editar = tb.Button(frame, text="Editar", command=on_editar, bootstyle="primary")
    btn_subpastas = tb.Button(frame, text="Ver Subpastas", command=on_subpastas, bootstyle="secondary")
    btn_enviar = tb.Button(frame, text="Enviar Para SupaBase", command=on_enviar, bootstyle="success")
    btn_lixeira = tb.Button(frame, text="Lixeira", command=on_lixeira, bootstyle="warning")

    btn_novo.pack(side="left", padx=5)
    btn_editar.pack(side="left", padx=5)
    btn_subpastas.pack(side="left", padx=5)
    btn_enviar.pack(side="left", padx=5)
    btn_lixeira.pack(side="right", padx=5)

    return FooterButtons(
        frame=frame,
        novo=btn_novo,
        editar=btn_editar,
        subpastas=btn_subpastas,
        enviar=btn_enviar,
        lixeira=btn_lixeira,
    )


def create_status_bar(
    parent: tk.Misc,
    *,
    count_var: tk.StringVar | None = None,
    status_dot_var: tk.StringVar | None = None,
    status_text_var: tk.StringVar | None = None,
    default_status_text: str = "LOCAL",
) -> StatusIndicators:
    """Create the status bar used on the bottom of the main window."""
    frame = tb.Frame(parent)

    count_var = count_var or tk.StringVar(master=parent, value="0 clientes")
    status_dot_var = status_dot_var or tk.StringVar(master=parent, value=STATUS_DOT)
    status_text_var = status_text_var or tk.StringVar(master=parent, value=default_status_text)

    tb.Label(frame, textvariable=count_var).pack(side="left")

    right_box = tb.Frame(frame)
    right_box.pack(side="right")

    status_dot = tb.Label(right_box, textvariable=status_dot_var, bootstyle="warning")
    status_dot.configure(font=("", 14))
    status_dot.pack(side="left", padx=(0, 6))

    status_label = tb.Label(right_box, textvariable=status_text_var, bootstyle="inverse")
    status_label.pack(side="left")

    return StatusIndicators(
        frame=frame,
        count_var=count_var,
        status_dot_var=status_dot_var,
        status_text_var=status_text_var,
        status_dot=status_dot,
        status_label=status_label,
    )


# --- WhatsApp Icon helper ---------------------------------------------------
_ICON_CACHE: dict[tuple[str, int], ImageTk.PhotoImage] = {}


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
            path = os.path.join(assets, cand)
            if os.path.exists(path):
                base = path
                break
        if not base:
            return None
        img = Image.open(base).convert("RGBA")
        if img.size != (size, size):
            img = ImageOps.contain(img, (size, size), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        _ICON_CACHE[key] = photo
        return photo
    except Exception as exc:
        log.debug("Nao foi possivel carregar o ícone do WhatsApp: %s", exc)
        return None


def draw_whatsapp_overlays(tree: tk.Widget, column: str, size: int = 15) -> None:
    """Desenha ícones do WhatsApp sobre a coluna especificada em um Treeview."""
    if not hasattr(tree, "_wa_overlays"):
        tree._wa_overlays = []

    for widget in getattr(tree, "_wa_overlays", []):
        try:
            widget.destroy()
        except Exception:
            pass
    tree._wa_overlays = []

    icon = get_whatsapp_icon(size)
    if not icon:
        return

    try:
        for iid in tree.get_children(""):
            bbox = tree.bbox(iid, column)
            if not bbox:
                continue
            x, y, _w, h = bbox
            numero = tree.set(iid, column)
            if not numero:
                continue
            lbl = tk.Label(tree, image=icon, borderwidth=0, cursor="hand2")
            lbl.place(x=x + 2, y=y + (h // 2), anchor="w")
            lbl.bind("<Button-1>", lambda _e, n=numero: _abrir_whatsapp(n))
            tree._wa_overlays.append(lbl)
    except Exception as exc:
        log.debug("Falha ao desenhar ícones do WhatsApp: %s", exc)


def _abrir_whatsapp(numero: str) -> None:
    digitos = re.sub(r"\D", "", numero or "")
    if not digitos:
        return
    if not digitos.startswith("55"):
        digitos = "55" + digitos
    try:
        webbrowser.open_new(f"https://web.whatsapp.com/send?phone={digitos}")
    except Exception as exc:
        log.debug("Falha ao abrir WhatsApp: %s", exc)


__all__ = [
    "MenuComponents",
    "SearchControls",
    "FooterButtons",
    "StatusIndicators",
    "toolbar_button",
    "labeled_entry",
    "create_menubar",
    "create_search_controls",
    "create_clients_treeview",
    "create_footer_buttons",
    "create_status_bar",
    "get_whatsapp_icon",
    "draw_whatsapp_overlays",
]
