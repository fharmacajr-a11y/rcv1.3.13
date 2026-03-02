# -*- coding: utf-8 -*-
"""Diálogos modais padronizados do RC Gestor.

Substitui tkinter.messagebox nos fluxos do app para garantir:
- Ícone do app desde o primeiro frame visível (sem flash)
- Visual consistente com CustomTkinter

API pública:
    ask_yes_no(parent, title, message) -> bool
    ask_ok_cancel(parent, title, message) -> bool
    ask_retry_cancel(parent, title, message) -> bool
    show_info(parent, title, message) -> None
    show_warning(parent, title, message) -> None
    show_error(parent, title, message) -> None
"""
from __future__ import annotations

import tkinter as tk
from typing import Any

from src.ui.ctk_config import ctk
from src.ui.dialog_icons import make_icon_label
from src.ui.ui_tokens import APP_BG, BUTTON_RADIUS, DIALOG_BTN_W, DIALOG_BTN_H
from src.ui.window_utils import apply_window_icon


def _center_on_parent(dlg: Any, parent: Any, w: int, h: int | None = None) -> None:
    """Posiciona dlg centralizado sobre parent.

    Se h=None, usa winfo_reqheight() + margem para ajustar ao conteúdo.
    """
    try:
        if h is None:
            dlg.update_idletasks()
            h = dlg.winfo_reqheight() + 10
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = max(0, px + (pw - w) // 2)
        y = max(0, py + (ph - h) // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        dlg.geometry(f"{w}x{h}")


def _make_dialog(parent: Any, title: str) -> Any:
    """Cria CTkToplevel oculto, com ícone RC, transient e configurado."""
    dlg = ctk.CTkToplevel(parent)
    dlg.withdraw()  # type: ignore[attr-defined]  # ocultar ANTES de qualquer draw
    dlg.title(title)
    dlg.resizable(False, False)
    dlg.configure(fg_color=APP_BG)
    apply_window_icon(dlg)      # ícone RC antes de deiconify
    try:
        dlg.transient(parent)
    except Exception:
        pass
    return dlg


def _deferred_show(dlg: Any, parent: Any) -> None:
    """Exibe dlg imediatamente (alpha=0) e revela após o timer interno do CTkToplevel (220ms)."""
    try:
        dlg.attributes("-alpha", 0.0)
    except Exception:
        pass
    dlg.deiconify()
    dlg.lift()
    dlg.grab_set()
    dlg.focus_force()

    def _reveal() -> None:
        if not dlg.winfo_exists():
            return
        apply_window_icon(dlg)  # reaplicar: CTk sobrescreve o ícone em t=200ms
        try:
            dlg.attributes("-alpha", 1.0)
        except Exception:
            pass
        dlg.lift()
        dlg.focus_force()

    dlg.after(220, _reveal)


def ask_yes_no(parent: Any, title: str, message: str) -> bool:
    """Diálogo modal de confirmação Sim/Não com ícone RC.

    Args:
        parent:  Widget pai (janela ou frame).
        title:   Título da janela.
        message: Mensagem exibida ao usuário.

    Returns:
        True se o usuário clicou em "Sim", False caso contrário.
    """
    result: dict[str, bool] = {"ok": False}

    dlg = _make_dialog(parent, title)

    frame = ctk.CTkFrame(dlg, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=24, pady=20)

    make_icon_label(frame, "warning", size=44).pack(pady=(0, 6))

    ctk.CTkLabel(
        frame,
        text=message,
        font=("Segoe UI", 12),
        wraplength=300,
        justify="center",
    ).pack(pady=(0, 14))

    btn_row = ctk.CTkFrame(frame, fg_color="transparent")
    btn_row.pack()

    def _yes() -> None:
        result["ok"] = True
        dlg.destroy()

    def _no() -> None:
        dlg.destroy()

    ctk.CTkButton(
        btn_row,
        text="Sim",
        width=DIALOG_BTN_W,
        height=DIALOG_BTN_H,
        corner_radius=BUTTON_RADIUS,
        fg_color=("#dc2626", "#ef4444"),
        hover_color=("#b91c1c", "#dc2626"),
        command=_yes,
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        btn_row,
        text="Não",
        width=DIALOG_BTN_W,
        height=DIALOG_BTN_H,
        corner_radius=BUTTON_RADIUS,
        fg_color=("#6b7280", "#4b5563"),
        hover_color=("#4b5563", "#374151"),
        command=_no,
    ).pack(side="left")

    dlg.bind("<Return>", lambda _e: _yes())
    dlg.bind("<Escape>", lambda _e: _no())
    dlg.protocol("WM_DELETE_WINDOW", _no)

    dlg.update_idletasks()
    _center_on_parent(dlg, parent, 360)
    _deferred_show(dlg, parent)

    try:
        parent.wait_window(dlg)
    except Exception:
        pass

    return result["ok"]


def show_info(parent: Any, title: str, message: str) -> None:
    """Diálogo modal informativo (OK) com ícone RC.

    Args:
        parent:  Widget pai.
        title:   Título da janela.
        message: Mensagem exibida ao usuário.
    """
    dlg = _make_dialog(parent, title)

    frame = ctk.CTkFrame(dlg, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=24, pady=20)

    make_icon_label(frame, "success", size=44).pack(pady=(0, 6))

    ctk.CTkLabel(
        frame,
        text=message,
        font=("Segoe UI", 12),
        wraplength=300,
        justify="center",
    ).pack(pady=(0, 14))

    def _ok() -> None:
        dlg.destroy()

    ctk.CTkButton(
        frame,
        text="OK",
        width=DIALOG_BTN_W,
        height=DIALOG_BTN_H,
        corner_radius=BUTTON_RADIUS,
        fg_color=("#2563eb", "#3b82f6"),
        hover_color=("#1d4ed8", "#2563eb"),
        command=_ok,
    ).pack()

    dlg.bind("<Return>", lambda _e: _ok())
    dlg.bind("<Escape>", lambda _e: _ok())
    dlg.protocol("WM_DELETE_WINDOW", _ok)

    dlg.update_idletasks()
    _center_on_parent(dlg, parent, 360)
    _deferred_show(dlg, parent)

    try:
        parent.wait_window(dlg)
    except Exception:
        pass

def ask_ok_cancel(parent: Any, title: str, message: str) -> bool:
    """Diálogo modal de confirmação OK/Cancelar com ícone RC.

    Args:
        parent:  Widget pai (janela ou frame).
        title:   Título da janela.
        message: Mensagem exibida ao usuário.

    Returns:
        True se o usuário clicou em "OK", False caso contrário.
    """
    result: dict[str, bool] = {"ok": False}

    dlg = _make_dialog(parent, title)

    frame = ctk.CTkFrame(dlg, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=24, pady=20)

    make_icon_label(frame, "warning", size=44).pack(pady=(0, 6))

    ctk.CTkLabel(
        frame,
        text=message,
        font=("Segoe UI", 12),
        wraplength=300,
        justify="center",
    ).pack(pady=(0, 14))

    btn_row = ctk.CTkFrame(frame, fg_color="transparent")
    btn_row.pack()

    def _ok() -> None:
        result["ok"] = True
        dlg.destroy()

    def _cancel() -> None:
        dlg.destroy()

    ctk.CTkButton(
        btn_row,
        text="OK",
        width=DIALOG_BTN_W,
        height=DIALOG_BTN_H,
        corner_radius=BUTTON_RADIUS,
        fg_color=("#2563eb", "#3b82f6"),
        hover_color=("#1d4ed8", "#2563eb"),
        command=_ok,
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        btn_row,
        text="Cancelar",
        width=DIALOG_BTN_W,
        height=DIALOG_BTN_H,
        corner_radius=BUTTON_RADIUS,
        fg_color=("#6b7280", "#4b5563"),
        hover_color=("#4b5563", "#374151"),
        command=_cancel,
    ).pack(side="left")

    dlg.bind("<Return>", lambda _e: _ok())
    dlg.bind("<Escape>", lambda _e: _cancel())
    dlg.protocol("WM_DELETE_WINDOW", _cancel)

    dlg.update_idletasks()
    _center_on_parent(dlg, parent, 360)
    _deferred_show(dlg, parent)

    try:
        parent.wait_window(dlg)
    except Exception:
        pass

    return result["ok"]


def ask_retry_cancel(parent: Any, title: str, message: str) -> bool:
    """Diálogo modal Tentar novamente / Cancelar com ícone RC.

    Args:
        parent:  Widget pai (janela ou frame).
        title:   Título da janela.
        message: Mensagem exibida ao usuário.

    Returns:
        True se o usuário clicou em "Tentar novamente", False caso contrário.
    """
    result: dict[str, bool] = {"ok": False}

    dlg = _make_dialog(parent, title)

    frame = ctk.CTkFrame(dlg, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=24, pady=20)

    make_icon_label(frame, "warning", size=44).pack(pady=(0, 6))

    ctk.CTkLabel(
        frame,
        text=message,
        font=("Segoe UI", 12),
        wraplength=300,
        justify="center",
    ).pack(pady=(0, 14))

    btn_row = ctk.CTkFrame(frame, fg_color="transparent")
    btn_row.pack()

    def _retry() -> None:
        result["ok"] = True
        dlg.destroy()

    def _cancel() -> None:
        dlg.destroy()

    ctk.CTkButton(
        btn_row,
        text="Tentar novamente",
        width=DIALOG_BTN_W + 30,
        height=DIALOG_BTN_H,
        corner_radius=BUTTON_RADIUS,
        fg_color=("#2563eb", "#3b82f6"),
        hover_color=("#1d4ed8", "#2563eb"),
        command=_retry,
    ).pack(side="left", padx=(0, 8))

    ctk.CTkButton(
        btn_row,
        text="Cancelar",
        width=DIALOG_BTN_W,
        height=DIALOG_BTN_H,
        corner_radius=BUTTON_RADIUS,
        fg_color=("#6b7280", "#4b5563"),
        hover_color=("#4b5563", "#374151"),
        command=_cancel,
    ).pack(side="left")

    dlg.bind("<Return>", lambda _e: _retry())
    dlg.bind("<Escape>", lambda _e: _cancel())
    dlg.protocol("WM_DELETE_WINDOW", _cancel)

    dlg.update_idletasks()
    _center_on_parent(dlg, parent, 360)
    _deferred_show(dlg, parent)

    try:
        parent.wait_window(dlg)
    except Exception:
        pass

    return result["ok"]

def show_error(parent: Any, title: str, message: str) -> None:
    """Diálogo modal de erro (OK) com ícone RC.

    Args:
        parent:  Widget pai.
        title:   Título da janela.
        message: Mensagem exibida ao usuário.
    """
    dlg = _make_dialog(parent, title)

    frame = ctk.CTkFrame(dlg, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=24, pady=20)

    make_icon_label(frame, "error", size=44).pack(pady=(0, 6))

    ctk.CTkLabel(
        frame,
        text=message,
        font=("Segoe UI", 12),
        wraplength=300,
        justify="center",
    ).pack(pady=(0, 14))

    def _ok() -> None:
        dlg.destroy()

    ctk.CTkButton(
        frame,
        text="OK",
        width=DIALOG_BTN_W,
        height=DIALOG_BTN_H,
        corner_radius=BUTTON_RADIUS,
        fg_color=("#dc2626", "#ef4444"),
        hover_color=("#b91c1c", "#dc2626"),
        command=_ok,
    ).pack()

    dlg.bind("<Return>", lambda _e: _ok())
    dlg.bind("<Escape>", lambda _e: _ok())
    dlg.protocol("WM_DELETE_WINDOW", _ok)

    dlg.update_idletasks()
    _center_on_parent(dlg, parent, 360)
    _deferred_show(dlg, parent)

    try:
        parent.wait_window(dlg)
    except Exception:
        pass


def show_warning(parent: Any, title: str, message: str) -> None:
    """Diálogo modal de aviso (OK) com ícone RC.

    Args:
        parent:  Widget pai.
        title:   Título da janela.
        message: Mensagem exibida ao usuário.
    """
    dlg = _make_dialog(parent, title)

    frame = ctk.CTkFrame(dlg, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=24, pady=20)

    make_icon_label(frame, "warning", size=44).pack(pady=(0, 6))

    ctk.CTkLabel(
        frame,
        text=message,
        font=("Segoe UI", 12),
        wraplength=300,
        justify="center",
    ).pack(pady=(0, 14))

    def _ok() -> None:
        dlg.destroy()

    ctk.CTkButton(
        frame,
        text="OK",
        width=DIALOG_BTN_W,
        height=DIALOG_BTN_H,
        corner_radius=BUTTON_RADIUS,
        fg_color=("#d97706", "#f59e0b"),
        hover_color=("#b45309", "#d97706"),
        command=_ok,
    ).pack()

    dlg.bind("<Return>", lambda _e: _ok())
    dlg.bind("<Escape>", lambda _e: _ok())
    dlg.protocol("WM_DELETE_WINDOW", _ok)

    dlg.update_idletasks()
    _center_on_parent(dlg, parent, 360)
    _deferred_show(dlg, parent)

    try:
        parent.wait_window(dlg)
    except Exception:
        pass
