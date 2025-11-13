# -*- coding: utf-8 -*-
"""Tela da Lixeira (clientes deletados via Supabase - soft delete)."""

from __future__ import annotations

import json
import logging
import os
from tkinter import messagebox as tkmsg
from tkinter import ttk

import ttkbootstrap as tb

from src.core.db_manager import list_clientes_deletados
from src.core.services import (  # ações: restore_clients / hard_delete_clients
    lixeira_service,
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


def refresh_if_open():
    """Recarrega a listagem se a janela estiver aberta (usado por fora)."""
    if _is_open():
        try:
            _OPEN_WINDOW._carregar()  # type: ignore[attr-defined]
        except Exception:
            log.exception("Falha ao recarregar Lixeira aberta.")


# ---------------- helpers UI ----------------
def _set_busy(win, buttons, busy: bool):
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

    tb.Label(container, text="Clientes na Lixeira", font=("", 12, "bold")).pack(anchor="center", pady=(0, 8))

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
        tree.delete(*tree.get_children())
        try:
            rows = list_clientes_deletados(order_by="id", descending=True)
        except Exception as e:
            log.exception("Falha ao buscar lixeira no Supabase")
            _err("Lixeira", f"Erro ao carregar lixeira: {e}")
            return

        for r in rows:
            whatsapp = getattr(r, "whatsapp", "") if hasattr(r, "whatsapp") else ""
            obs = getattr(r, "obs", "") or ""
            ultima_raw = getattr(r, "ultima_alteracao", "") or getattr(r, "updated_at", "") or ""
            if ultima_raw:
                try:
                    from src.app_utils import fmt_data

                    ultima_fmt = fmt_data(ultima_raw)
                except Exception:
                    ultima_fmt = str(ultima_raw)
            else:
                ultima_fmt = ""

            by = (getattr(r, "ultima_por", "") or "").strip()
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
                    r.id,
                    r.razao_social or "",
                    r.cnpj or "",
                    r.nome or "",
                    whatsapp,
                    obs,
                    ultima_fmt,
                ),
            )
        status.config(text=f"{len(rows)} item(ns) na lixeira")
        log.info("Lixeira carregada: %s itens", len(rows))

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
            ok, errs = lixeira_service.restore_clients(ids, parent=win)
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

        _set_busy(win, [btn_restore, btn_purge, btn_refresh, btn_close], True)
        try:
            ok, errs = lixeira_service.hard_delete_clients(ids, parent=win)  # DB + Storage
            if errs:
                msg = "\n".join([f"ID {cid}: {err}" for cid, err in errs])
                _err("Falha parcial", f"{ok} apagado(s), erros:\n{msg}")
            else:
                _info("Pronto", f"{ok} registro(s) apagado(s) para sempre.")
        except Exception as e:
            log.exception("Falha ao apagar definitivamente")
            _err("Lixeira", f"Erro ao apagar: {e}")
        finally:
            _set_busy(win, [btn_restore, btn_purge, btn_refresh, btn_close], False)
            carregar()

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
