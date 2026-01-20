# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import tkinter as tk
from dataclasses import dataclass

from typing import Any, Callable, Iterable

from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
from src.utils.resource_path import resource_path

log = logging.getLogger(__name__)

PLACEHOLDER_TEXT = "Digite aqui para pesquisar..."
PLACEHOLDER_FG = "#C3C3C3"
NORMAL_TEXT_FG = "black"


def _clear_combobox_selection(combo: tk.Widget) -> None:
    """Remove selecao visual (texto marcado) de um Combobox.

    Aceita ctk.CTkComboBox ou ttkbootstrap.Combobox (ambos derivam de tk.Widget).
    """
    try:
        combo.selection_clear()  # type: ignore[attr-defined]
    except Exception:
        # Toleramos falhas silenciosas para combos que não suportam essa operação
        log.debug("Falha ao limpar seleção do combobox", exc_info=True)
    try:
        combo.icursor(tk.END)  # type: ignore[attr-defined]
    except Exception:
        log.debug("Falha ao mover cursor do combobox para o final", exc_info=True)


@dataclass(slots=True)
class SearchControls:
    frame: Any  # CTkFrame | tk.Frame
    search_var: tk.StringVar
    order_var: tk.StringVar
    status_var: tk.StringVar
    entry: Any  # CTkEntry | tk.Entry
    search_button: Any  # CTkButton | tk.Button
    clear_button: Any  # CTkButton | tk.Button
    order_combobox: Any  # CTkOptionMenu | ctk.CTkComboBox
    status_combobox: Any  # CTkOptionMenu | ctk.CTkComboBox
    lixeira_button: Any  # CTkButton | tk.Button
    obrigacoes_button: Any | None = None
    search_container: tk.Frame | None = None
    placeholder_label: tk.Label | None = None
    search_icon: tk.PhotoImage | None = None
    placeholder_updater: Callable[[], None] | None = None


__all__ = ["SearchControls", "labeled_entry", "create_search_controls"]


def labeled_entry(parent: tk.Misc, label_text: str) -> tuple[ctk.CTkLabel, ctk.CTkEntry]:
    """Return a label/entry pair for uniform forms."""
    label = ctk.CTkLabel(parent, text=label_text)
    entry = ctk.CTkEntry(parent, width=50)
    return label, entry


def create_search_controls(
    parent: tk.Misc,
    *,
    order_choices: Iterable[str],
    default_order: str,
    on_search: Callable[[Any | None], Any] | None,
    on_clear: Callable[[], Any] | None,
    on_order_change: Callable[[], Any] | None,
    on_status_change: Callable[[Any | None], Any] | None = None,
    on_lixeira: Callable[[], Any] | None = None,
    on_obrigacoes: Callable[[], Any] | None = None,
    search_var: tk.StringVar | None = None,
    order_var: tk.StringVar | None = None,
    status_var: tk.StringVar | None = None,
    status_choices: Iterable[str] | None = None,
    entry_width: int = 40,
    theme_palette: dict[str, str] | None = None,
) -> SearchControls:
    """Build the search + ordering toolbar.

    Args:
        theme_palette: Dicionário com cores customizadas para o tema (opcional).
                      Chaves esperadas: entry_bg, entry_fg, entry_border, combo_bg, combo_fg, bg
    """
    # Sempre usar CTkFrame (projeto 100% CustomTkinter agora)
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    style = None  # CTk não usa Style legado

    def _lookup(style_name: str, option: str, default: str) -> str:
        try:
            if hasattr(style, "lookup"):
                return style.lookup(style_name, option) or default
        except Exception:
            return default
        return default

    # Usa palette customizada se fornecida, senão usa lookup do tema
    if theme_palette:
        entry_bg = theme_palette.get("entry_bg", "white")
        entry_fg = theme_palette.get("entry_fg", NORMAL_TEXT_FG)
        border_color = theme_palette.get("entry_border", "#ced4da")
        combo_fg = theme_palette.get("combo_fg", entry_fg)
        frame_bg = theme_palette.get("bg", "")
    else:
        entry_bg = (
            _lookup("TEntry", "fieldbackground", "")
            or _lookup("TEntry", "background", "")
            or _lookup(".", "background", "")
            or "white"
        )
        entry_fg = _lookup("TEntry", "foreground", "") or _lookup(".", "foreground", "") or NORMAL_TEXT_FG
        border_color = _lookup("TEntry", "bordercolor", "") or _lookup("TEntry", "lightcolor", "") or "#ced4da"
        combo_fg = _lookup("TCombobox", "foreground", "") or entry_fg
        frame_bg = _lookup("TFrame", "background", "") or _lookup(".", "background", "") or entry_bg

    combo_style = "Filtro.TCombobox"
    try:
        # Estilo proprio para manter comboboxes de filtro ativas (sem fundo cinza)
        style.configure(
            combo_style,
            fieldbackground=theme_palette.get("combo_bg", entry_bg) if theme_palette else entry_bg,
            background=theme_palette.get("combo_bg", entry_bg) if theme_palette else entry_bg,
            foreground=combo_fg,
            bordercolor=border_color,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao configurar estilo da combobox de filtros: %s", exc)
        combo_style = "TCombobox"

    search_var = search_var or tk.StringVar(master=parent)
    order_var = order_var or tk.StringVar(master=parent, value=default_order)
    status_var = status_var or tk.StringVar(master=parent, value="Todos")

    if HAS_CUSTOMTKINTER and ctk is not None:
        ctk.CTkLabel(frame, text="Pesquisar:").pack(side="left", padx=5)
    else:
        tk.Label(frame, text="Pesquisar:").pack(side="left", padx=5)

    def _trigger_search(event: Any | None = None) -> None:
        if on_search:
            on_search(event)

    # Campo de busca com icone + placeholder (apenas uma caixinha, sem borda externa visivel)
    # O frame container agora e invisivel, sem bordas
    search_container = tk.Frame(
        frame,
        bg=frame_bg,
        bd=0,
        relief="flat",
        highlightthickness=0,
    )
    search_container.pack(side="left", padx=5, pady=0)

    search_icon: tk.PhotoImage | None = None
    try:
        icon_path = resource_path("assets/modulos/clientes/topbar clientes/procurar.png")
        if os.path.exists(icon_path):
            search_icon = tk.PhotoImage(file=icon_path)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao carregar icone de busca: %s", exc)

    # Icone de lupa
    if search_icon is not None:
        try:
            icon_label = tk.Label(search_container, image=search_icon, bg=search_container.cget("bg"), borderwidth=0)
            icon_label.pack(side="left", padx=(0, 4))
            # FIX-TESTS-002: Manter referência forte à PhotoImage para evitar garbage collection
            # Mantem referências em multiplos locais para garantir que a imagem sobreviva
            icon_label.image = search_icon  # type: ignore[attr-defined]
            search_container._search_icon = search_icon  # type: ignore[attr-defined]
            frame._search_icon = search_icon  # type: ignore[attr-defined] - referência no frame retornado
        except tk.TclError as exc:
            # Fix Microfase 19.2: Se TclError (pyimage doesn't exist), continua sem ícone
            log.debug("Falha ao criar label com ícone de busca: %s", exc)
            search_icon = None

    # Entry de busca (a caixinha visivel)
    entry_style = "Search.TEntry"
    try:
        style.configure(
            entry_style,
            padding=(6, 6, 6, 6),
            foreground=entry_fg,
            fieldbackground=entry_bg,
        )
    except Exception:
        entry_style = "TEntry"

    entry = ctk.CTkEntry(
        search_container,
        textvariable=search_var,
        width=entry_width,
        style=entry_style,
    )
    entry.pack(side="left")

    # Configurar cor da selecao (azul claro)
    try:
        entry.configure(
            selectbackground="#5bc0de",
            selectforeground="#000000",
        )
    except tk.TclError:
        # ctk.CTkEntry/ttkbootstrap geralmente nao suportam essas opcoes; ignora.
        pass

    # Placeholder usando Label sobreposto ao Entry
    placeholder_label = tk.Label(
        search_container,
        text=PLACEHOLDER_TEXT,
        background=entry_bg,
        borderwidth=0,
        anchor="w",
    )
    # Forcar a cor do placeholder para evitar override do tema
    try:
        placeholder_label.configure(foreground=PLACEHOLDER_FG)
    except Exception:
        log.debug("Falha ao configurar cor do placeholder", exc_info=True)

    def _place_placeholder() -> None:
        try:
            placeholder_label.place(in_=entry, x=8, rely=0.5, anchor="w")
        except Exception:
            placeholder_label.place_forget()

    def _hide_placeholder(_event: Any | None = None) -> None:
        placeholder_label.place_forget()

    def _update_placeholder(_event: Any | None = None) -> None:
        if entry.get():
            _hide_placeholder()
        else:
            _place_placeholder()

    placeholder_label.bind("<Button-1>", lambda _e: (entry.focus_set(), _hide_placeholder()))

    def _on_key_release(event: Any | None = None) -> None:
        if entry.get():
            _hide_placeholder()
        _trigger_search(event)

    entry.bind("<KeyRelease>", _on_key_release, add="+")
    entry.bind("<FocusIn>", _hide_placeholder, add="+")
    entry.bind("<FocusOut>", _update_placeholder, add="+")
    if search_var is not None:
        search_var.trace_add("write", lambda *_args: _update_placeholder())
    _update_placeholder()

    if HAS_CUSTOMTKINTER and ctk is not None:
        search_button = ctk.CTkButton(
            frame,
            text="Buscar",
            command=_trigger_search,
        )
    else:
        search_button = tk.Button(
            frame,
            text="Buscar",
            command=_trigger_search,
        )
    search_button.pack(side="left", padx=5)

    def _on_clear_pressed() -> None:
        if search_var is not None:
            search_var.set("")
        _update_placeholder()
        if on_clear:
            on_clear()

    # Botao Limpar com estilo especifico para topbar de clientes
    if HAS_CUSTOMTKINTER and ctk is not None:
        clear_button = ctk.CTkButton(
            frame,
            text="Limpar",
            command=_on_clear_pressed,
        )
    else:
        clear_button = tk.Button(
            frame,
            text="Limpar",
            command=_on_clear_pressed,
        )
    clear_button.pack(side="left", padx=5)

    if HAS_CUSTOMTKINTER and ctk is not None:
        ctk.CTkLabel(frame, text="Ordenar por:").pack(side="left", padx=5)
    else:
        tk.Label(frame, text="Ordenar por:").pack(side="left", padx=5)

    def _order_changed(_event: Any | None = None) -> None:
        if on_order_change:
            on_order_change()
        _clear_combobox_selection(order_combobox)

    if HAS_CUSTOMTKINTER and ctk is not None:
        order_combobox = ctk.CTkOptionMenu(
            frame,
            variable=order_var,
            values=list(order_choices),
            width=220,
        )
        # CTkOptionMenu usa command em vez de event binding
        order_combobox.configure(command=lambda _: _order_changed())
    else:
        order_combobox = ctk.CTkComboBox(
            frame,

            values=list(order_choices),
            state="readonly",
            width=28,
        )
    order_combobox.pack(side="left", padx=5)
    try:
        order_combobox.state(["!disabled", "readonly"])
    except Exception:
        order_combobox.configure(state="readonly")
    order_combobox.bind("<<ComboboxSelected>>", _order_changed, add="+")
    # Remove selecao cinza no texto do combobox sempre que o valor muda
    if order_var is not None:
        order_var.trace_add("write", lambda *_args: _clear_combobox_selection(order_combobox))
    _clear_combobox_selection(order_combobox)

    if HAS_CUSTOMTKINTER and ctk is not None:
        ctk.CTkLabel(frame, text="Status:").pack(side="left", padx=5)
    else:
        tk.Label(frame, text="Status:").pack(side="left", padx=5)

    def _status_changed(event: Any | None = None) -> None:
        if on_status_change:
            on_status_change(event)
        _clear_combobox_selection(status_combobox)

    status_values = list(status_choices or [])
    if "Todos" not in status_values:
        status_values.insert(0, "Todos")

    if HAS_CUSTOMTKINTER and ctk is not None:
        status_combobox = ctk.CTkOptionMenu(
            frame,
            variable=status_var,
            values=status_values or ["Todos"],
            width=220,
        )
        status_combobox.configure(command=lambda _: _status_changed())
    else:
        status_combobox = ctk.CTkComboBox(
            frame,
            values=status_values or ["Todos"],
            state="readonly",
            width=28,
        )
    status_combobox.pack(side="left", padx=5)
    try:
        status_combobox.state(["!disabled", "readonly"])
    except Exception:
        status_combobox.configure(state="readonly")
    status_combobox.bind("<<ComboboxSelected>>", _status_changed, add="+")
    # Remove selecao cinza no texto do combobox sempre que o valor muda
    if status_var is not None:
        status_var.trace_add("write", lambda *_args: _clear_combobox_selection(status_combobox))
    _clear_combobox_selection(status_combobox)

    # Separator e botão Obrigações (se callback fornecido)
    obrigacoes_button: Any = None
    if on_obrigacoes is not None:
        # Separator visual
        sep = ctk.CTkFrame(frame, width=2)  # Separador vertical
        sep.pack(side="left", fill="y", padx=(8, 4))

        # Botão Obrigações
        if HAS_CUSTOMTKINTER and ctk is not None:
            obrigacoes_button = ctk.CTkButton(
                frame,
                text="Obrigações",
                command=on_obrigacoes,
                width=120,
            )
        else:
            obrigacoes_button = tk.Button(
                frame,
                text="Obrigações",
                command=on_obrigacoes,
                width=12,
            )
        obrigacoes_button.pack(side="left", padx=(0, 4))

    # Botão Lixeira à direita
    if HAS_CUSTOMTKINTER and ctk is not None:
        lixeira_button = ctk.CTkButton(
            frame,
            text="Lixeira",
            command=on_lixeira,
            fg_color="#ffc107",
            hover_color="#e0a800",
            text_color="black",
        )
    else:
        lixeira_button = tk.Button(
            frame,
            text="Lixeira",
            command=on_lixeira,
            bg="#ffc107",
            fg="black",
        )
    lixeira_button.pack(side="right", padx=5)

    return SearchControls(
        frame=frame,
        search_var=search_var,
        order_var=order_var,
        status_var=status_var,
        entry=entry,
        search_button=search_button,
        clear_button=clear_button,
        order_combobox=order_combobox,
        status_combobox=status_combobox,
        lixeira_button=lixeira_button,
        obrigacoes_button=obrigacoes_button,
        search_container=search_container,
        placeholder_label=placeholder_label,
        search_icon=search_icon,
        placeholder_updater=lambda: _update_placeholder(),
    )
