# -*- coding: utf-8 -*-
"""Tela da Lixeira (clientes deletados via Supabase - soft delete)."""

from __future__ import annotations

import json
import logging
import os
import threading
import tkinter as tk
from tkinter import messagebox as tkmsg
from tkinter import ttk
from typing import Iterable

import ttkbootstrap as tb

from src.modules.clientes.service import (
    excluir_clientes_definitivamente,
    listar_clientes_na_lixeira,
    restaurar_clientes_da_lixeira,
)
from src.ui.utils import center_window

# ui/lixeira/lixeira.py


logger = logging.getLogger(__name__)
log = logger

# ---------- Singleton da janela ----------
_OPEN_WINDOW: tb.Toplevel | None = None


def _is_open() -> bool:
    try:
        return _OPEN_WINDOW is not None and int(_OPEN_WINDOW.winfo_exists()) == 1
    except Exception:
        return False


def refresh_if_open() -> None:
    """Recarrega a listagem se a janela estiver aberta (usado por fora)."""
    if not _is_open():
        return
    try:
        _OPEN_WINDOW._carregar()  # type: ignore[attr-defined]
    except Exception:
        log.exception("Falha ao recarregar Lixeira aberta.")


# ---------------- helpers UI ----------------
def _set_busy(win: tb.Toplevel, buttons: Iterable[tb.Widget], busy: bool) -> None:
    try:
        win.configure(cursor=("watch" if busy else ""))
    except Exception:
        pass
    for btn in buttons or []:
        try:
            btn.configure(state=("disabled" if busy else "normal"))
        except Exception:
            try:
                btn["state"] = "disabled" if busy else "normal"
            except Exception:
                pass
    try:
        win.update_idletasks()
    except Exception:
        pass


# ---------------- janela principal da Lixeira (com Treeview) ----------------
def abrir_lixeira(parent, app=None):
    """Abre a Lixeira em modo singleton: se já estiver aberta, só foca e recarrega."""
    global _OPEN_WINDOW

    # Se já existe: traz pra frente, foca e recarrega
    if _is_open():
        w = _OPEN_WINDOW  # type: ignore[assignment]
        if w is None:
            return None
        try:
            w.deiconify()
            w.lift()
            w.focus_force()
            # truque para garantir foco em algumas janelas
            w.attributes("-topmost", True)
            w.after(120, lambda: w.attributes("-topmost", False))
            if hasattr(w, "_carregar"):
                w._carregar()  # type: ignore[attr-defined]
        except Exception:
            log.exception("Falha ao focar janela da Lixeira existente.")
        return w

    # Criar nova janela
    win = tb.Toplevel(parent)
    win.title("Lixeira de Clientes")
    try:
        win.minsize(900, 520)
    except Exception:
        pass

    container = tb.Frame(win, padding=10)
    container.pack(fill="both", expand=True)

    tb.Label(container, text="Clientes na Lixeira", font=("", 12, "bold")).pack(anchor="center", pady=(0, 8))  # pyright: ignore[reportArgumentType]

    # Treeview
    cols = ("id", "razao_social", "cnpj", "nome", "whatsapp", "obs", "ultima_alteracao")
    tree = ttk.Treeview(container, show="headings", columns=cols, height=16)
    tree.pack(fill="both", expand=True)

    headings = {
        "id": "ID",
        "razao_social": "Razão Social",
        "cnpj": "CNPJ",
        "nome": "Nome",
        "whatsapp": "WhatsApp",
        "obs": "Observações",
        "ultima_alteracao": "Última Alteração",
    }
    widths = {
        "id": 60,
        "razao_social": 240,
        "cnpj": 140,
        "nome": 180,
        "whatsapp": 120,
        "obs": 260,
        "ultima_alteracao": 180,
    }
    for c in cols:
        tree.heading(c, text=headings[c])
        tree.column(c, width=widths[c], anchor="w")

    # Toolbar inferior
    toolbar = tb.Frame(container)
    toolbar.pack(fill="x", pady=(8, 0))

    btn_restore = tb.Button(toolbar, text="Restaurar Selecionados", bootstyle="success")
    btn_purge = tb.Button(toolbar, text="Apagar Selecionados", bootstyle="danger")
    btn_refresh = tb.Button(toolbar, text="⟳", width=3)
    btn_close = tb.Button(toolbar, text="Fechar", bootstyle="secondary", command=win.destroy)

    btn_restore.pack(side="left")
    tb.Separator(toolbar, orient="vertical").pack(side="left", padx=6, fill="y")
    btn_purge.pack(side="left")
    btn_refresh.pack(side="right", padx=(0, 6))
    btn_close.pack(side="right")

    status = tb.Label(container, text="", anchor="w")
    status.pack(fill="x", pady=(6, 0))

    # -------- helpers locais (com parent=win) --------
    def _info(title, msg):
        try:
            tkmsg.showinfo(title, msg, parent=win)
        except Exception:
            tkmsg.showinfo(title, msg)

    def _warn(title, msg):
        try:
            tkmsg.showwarning(title, msg, parent=win)
        except Exception:
            tkmsg.showwarning(title, msg)

    def _err(title, msg):
        try:
            tkmsg.showerror(title, msg, parent=win)
        except Exception:
            tkmsg.showerror(title, msg)

    def _ask_yesno(title, msg) -> bool:
        try:
            return tkmsg.askyesno(title, msg, parent=win)
        except Exception:
            return tkmsg.askyesno(title, msg)

    def get_selected_ids():
        ids = []
        for iid in tree.selection():
            try:
                ids.append(int(tree.set(iid, "id")))
            except Exception:
                pass
        return ids

    # -------- carregar lista --------
    def carregar():
        def _get_val(obj, *names):
            for name in names:
                if hasattr(obj, name):
                    try:
                        val = getattr(obj, name)
                    except Exception:
                        val = None
                    if val is not None:
                        return val
                if isinstance(obj, dict) and name in obj:
                    val = obj.get(name)
                    if val is not None:
                        return val
            return None

        tree.delete(*tree.get_children())
        try:
            rows = listar_clientes_na_lixeira(order_by="id", descending=True)
        except Exception as e:
            log.exception("Falha ao buscar lixeira no Supabase")
            _err("Lixeira", f"Erro ao carregar lixeira: {e}")
            return

        for r in rows:
            r_id = _get_val(r, "id") or ""
            razao_social = _get_val(r, "razao_social") or ""
            cnpj = _get_val(r, "cnpj") or ""
            nome = _get_val(r, "nome") or ""
            whatsapp = _get_val(r, "whatsapp", "numero") or ""
            obs = _get_val(r, "obs", "observacoes", "Observacoes") or ""
            ultima_raw = _get_val(r, "ultima_alteracao", "updated_at") or ""
            if ultima_raw:
                try:
                    from src.app_utils import fmt_data

                    ultima_fmt = fmt_data(ultima_raw)
                except Exception:
                    ultima_fmt = str(ultima_raw)
            else:
                ultima_fmt = ""

            by = (_get_val(r, "ultima_por") or "").strip()
            initial = ""
            if by:
                try:
                    mapping_raw = os.getenv("RC_INITIALS_MAP", "")
                    try:
                        mapping = json.loads(mapping_raw) if mapping_raw else {}
                    except Exception:
                        mapping = {}
                    alias = ""
                    if isinstance(mapping, dict):
                        alias = str(mapping.get(by, "") or "")
                    if alias:
                        initial = (alias[:1] or "").upper()
                    else:
                        from src.ui.hub.authors import _author_display_name as _author_name

                        display = _author_name(app, by) if app is not None else ""
                        if not display:
                            display = by
                        initial = (display[:1] or by[:1] or "").upper()
                except Exception:
                    initial = (by[:1] or "").upper()
            if ultima_fmt and initial:
                ultima_fmt = f"{ultima_fmt} ({initial})"

            tree.insert(
                "",
                "end",
                values=(
                    r_id,
                    razao_social,
                    cnpj,
                    nome,
                    whatsapp,
                    obs,
                    ultima_fmt,
                ),
            )
        status.config(text=f"{len(rows)} item(ns) na lixeira")
        log.info("Lixeira carregada com %d clientes", len(rows))

    # -------- ações --------
    def on_restore():
        ids = get_selected_ids()
        if not ids:
            _warn("Lixeira", "Selecione pelo menos um registro para restaurar.")
            return
        if not _ask_yesno("Restaurar", f"Restaurar {len(ids)} registro(s) para a lista principal?"):
            return

        _set_busy(win, [btn_restore, btn_purge, btn_refresh, btn_close], True)
        try:
            ok, errs = restaurar_clientes_da_lixeira(ids, parent=win)
            if errs:
                msg = "\n".join([f"ID {cid}: {err}" for cid, err in errs])
                _err("Falha parcial", f"{ok} restaurado(s), erros:\n{msg}")
            else:
                _info("Pronto", f"{ok} registro(s) restaurado(s).")
                # As subpastas obrigatórias são garantidas no serviço (_ensure_mandatory_subfolders).
        except Exception as e:
            log.exception("Falha ao restaurar")
            _err("Lixeira", f"Erro ao restaurar: {e}")
        finally:
            _set_busy(win, [btn_restore, btn_purge, btn_refresh, btn_close], False)
            carregar()

    def on_purge():
        ids = get_selected_ids()
        if not ids:
            _warn(
                "Lixeira",
                "Selecione pelo menos um registro para apagar definitivamente.",
            )
            return
        if not _ask_yesno(
            "Apagar",
            f"APAGAR DEFINITIVAMENTE {len(ids)} registro(s)? Esta ação não pode ser desfeita.",
        ):
            return

        def _show_wait_dialog(count: int):
            dlg = tk.Toplevel(win)
            try:
                dlg.title("Aguarde")
                dlg.transient(win)
                dlg.grab_set()
                dlg.resizable(False, False)
            except Exception:
                pass

            label = ttk.Label(dlg, text=f"Apagando 0/{count} registro(s)... Aguarde.")
            label.pack(padx=20, pady=(15, 5))
            bar = ttk.Progressbar(dlg, mode="determinate", maximum=max(count, 1), value=0)
            bar.pack(fill="x", padx=20, pady=(0, 15))

            try:
                dlg.update_idletasks()
                x = win.winfo_rootx() + (win.winfo_width() // 2 - dlg.winfo_width() // 2)
                y = win.winfo_rooty() + (win.winfo_height() // 2 - dlg.winfo_height() // 2)
                dlg.geometry(f"+{x}+{y}")
            except Exception:
                pass

            try:
                dlg.protocol("WM_DELETE_WINDOW", lambda: None)
            except Exception:
                pass

            return dlg, label, bar

        def _make_purge_progress_cb(bar: ttk.Progressbar, label: ttk.Label):
            def progress_cb(idx: int, total: int, client_id: int) -> None:
                def _update():
                    try:
                        bar["maximum"] = max(total, 1)
                        bar["value"] = idx
                        label.configure(text=f"Apagando {idx}/{total} registro(s)... Aguarde.")
                    except Exception:
                        pass

                win.after(0, _update)

            return progress_cb

        def _on_purge_finished(wait_dlg: tk.Toplevel, ok_count: int, errs_list, total: int):
            try:
                wait_dlg.destroy()
            except Exception:
                pass

            _set_busy(win, [btn_restore, btn_purge, btn_refresh, btn_close], False)

            errs = errs_list or []
            if errs:
                if isinstance(errs, (list, tuple)):
                    formatted = []
                    for item in errs:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            formatted.append(f"ID {item[0]}: {item[1]}")
                        else:
                            formatted.append(str(item))
                    msg = "\n".join(formatted)
                else:
                    msg = str(errs)
                log.warning("Falha ao apagar definitivamente: %s", msg)
                _err("Falha parcial", f"{ok_count} apagado(s), erros:\n{msg}")
            else:
                _info("Pronto", f"{ok_count} registro(s) apagado(s) para sempre.")
            carregar()

        _set_busy(win, [btn_restore, btn_purge, btn_refresh, btn_close], True)
        wait, progress_label, progress_bar = _show_wait_dialog(len(ids))
        progress_cb = _make_purge_progress_cb(progress_bar, progress_label)

        def worker():
            try:
                ok, errs = excluir_clientes_definitivamente(ids, progress_cb=progress_cb)  # DB + Storage
            except Exception as e:  # pragma: no cover - proteção extra
                log.exception("Falha ao apagar definitivamente (thread)")
                ok, errs = 0, [str(e)]
            win.after(0, lambda: _on_purge_finished(wait, ok, errs, len(ids)))

        threading.Thread(target=worker, daemon=True).start()

    btn_restore.configure(command=on_restore)
    btn_purge.configure(command=on_purge)
    btn_refresh.configure(command=carregar)

    # expõe carregar para refresh externo e registra singleton
    win._carregar = carregar  # type: ignore[attr-defined]
    _OPEN_WINDOW = win

    # close handler limpa o singleton
    def _on_close():
        global _OPEN_WINDOW
        try:
            _OPEN_WINDOW = None
        except Exception:
            pass
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _on_close)

    # primeira carga e centralização
    carregar()
    try:
        center_window(win)
    except Exception:
        pass

    return win
