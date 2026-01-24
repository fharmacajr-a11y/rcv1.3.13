# -*- coding: utf-8 -*-
"""Tela da Lixeira (clientes deletados via Supabase - soft delete)."""

from __future__ import annotations

import json
import logging
import os
import threading
import tkinter as tk
from tkinter import messagebox as tkmsg
from typing import Any, Callable, Iterable, List, Optional, Tuple

from src.ui.ctk_config import ctk
from src.ui.widgets import CTkTableView

from src.modules.clientes.service import (
    excluir_clientes_definitivamente,
    listar_clientes_na_lixeira,
    restaurar_clientes_da_lixeira,
)
from src.ui.window_utils import show_centered

# ui/lixeira/lixeira.py


logger = logging.getLogger(__name__)
log = logger


def _log_ui_issue(context: str, exc: Exception, *, level: str = "debug") -> None:
    """Unified logging for best-effort UI operations in the trash screen."""
    if level == "warning":
        log.warning("[Lixeira] %s: %s", context, exc)
    else:
        log.debug("[Lixeira] %s: %s", context, exc)


# ---------- Singleton da janela ----------
_OPEN_WINDOW: ctk.CTkToplevel | None = None


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
def _set_busy(win: ctk.CTkToplevel, buttons: Iterable, busy: bool) -> None:
    try:
        win.configure(cursor=("watch" if busy else ""))
    except Exception as exc:  # noqa: BLE001
        _log_ui_issue("Falha ao aplicar cursor busy", exc)
    for btn in buttons or []:
        try:
            btn.configure(state=("disabled" if busy else "normal"))
        except Exception:
            try:
                btn["state"] = "disabled" if busy else "normal"
            except Exception as exc:  # noqa: BLE001
                _log_ui_issue("Falha ao atualizar estado de botao na Lixeira", exc)
    try:
        win.update_idletasks()
    except Exception as exc:  # noqa: BLE001
        _log_ui_issue("Falha ao atualizar idletasks na Lixeira", exc)


# ---------------- janela principal da Lixeira (com Treeview) ----------------
def abrir_lixeira(parent: tk.Misc, app: Any | None = None) -> Optional[ctk.CTkToplevel]:
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
    win = ctk.CTkToplevel(parent)
    win.withdraw()
    win.title("Lixeira de Clientes")
    try:
        win.minsize(900, 520)
    except Exception as exc:  # noqa: BLE001
        _log_ui_issue("Falha ao aplicar tamanho minimo na Lixeira", exc)

    container = ctk.CTkFrame(win)
    container.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(container, text="Clientes na Lixeira", font=("Arial", 12, "bold")).pack(anchor="center", pady=(0, 8))

    # CTkTableView (substitui Treeview legado)
    cols = ["id", "razao_social", "cnpj", "nome", "whatsapp", "obs", "ultima_alteracao"]
    tree = CTkTableView(container, columns=cols, height=16, zebra=True)
    tree.pack(fill="both", expand=True)

    headings = [
        "ID",
        "Razão Social",
        "CNPJ",
        "Nome",
        "WhatsApp",
        "Observações",
        "Última Alteração",
    ]
    tree.set_columns(headings)

    # Toolbar inferior
    toolbar = ctk.CTkFrame(container)
    toolbar.pack(fill="x", pady=(8, 0))

    btn_restore = ctk.CTkButton(
        toolbar, text="Restaurar Selecionados", fg_color=("#2E7D32", "#1B5E20"), hover_color=("#1B5E20", "#0D4A11")
    )
    btn_purge = ctk.CTkButton(
        toolbar, text="Apagar Selecionados", fg_color=("#D32F2F", "#B71C1C"), hover_color=("#B71C1C", "#8B0000")
    )
    btn_refresh = ctk.CTkButton(toolbar, text="⟳", width=40)
    btn_close = ctk.CTkButton(
        toolbar, text="Fechar", fg_color=("#757575", "#616161"), hover_color=("#616161", "#424242"), command=win.destroy
    )

    btn_restore.pack(side="left", padx=5)
    btn_purge.pack(side="left", padx=5)
    btn_refresh.pack(side="right", padx=5)
    btn_close.pack(side="right", padx=5)

    status = ctk.CTkLabel(container, text="", anchor="w")
    status.pack(fill="x", pady=(6, 0))

    # -------- helpers locais (com parent=win) --------
    def _info(title: str, msg: str) -> None:
        try:
            tkmsg.showinfo(title, msg, parent=win)
        except Exception:
            tkmsg.showinfo(title, msg)

    def _warn(title: str, msg: str) -> None:
        try:
            tkmsg.showwarning(title, msg, parent=win)
        except Exception:
            tkmsg.showwarning(title, msg)

    def _err(title: str, msg: str) -> None:
        try:
            tkmsg.showerror(title, msg, parent=win)
        except Exception:
            tkmsg.showerror(title, msg)

    def _ask_yesno(title: str, msg: str) -> bool:
        try:
            return tkmsg.askyesno(title, msg, parent=win)
        except Exception:
            return tkmsg.askyesno(title, msg)

    def get_selected_ids() -> List[int]:
        ids: List[int] = []
        selected_row = tree.get_selected_row()
        if selected_row:
            try:
                # ID é a primeira coluna
                ids.append(int(selected_row[0]))
            except Exception as exc:  # noqa: BLE001
                _log_ui_issue("Falha ao coletar ID selecionado na Lixeira", exc)
        return ids

    def carregar() -> None:
        def _get_val(obj: Any, *names: str):
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

        tree.clear()
        try:
            rows = listar_clientes_na_lixeira(order_by="id", descending=True)
        except Exception as e:
            log.exception("Falha ao buscar lixeira no Supabase")
            _err("Lixeira", f"Erro ao carregar lixeira: {e}")
            return

        table_rows = []
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
                    from src.utils.formatters import fmt_datetime_br

                    ultima_fmt = fmt_datetime_br(ultima_raw)
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
                        from src.modules.hub.services.authors_service import get_author_display_name

                        display = get_author_display_name(app, by, start_async_fetch=False) if app is not None else ""
                        if not display:
                            display = by
                        initial = (display[:1] or by[:1] or "").upper()
                except Exception:
                    initial = (by[:1] or "").upper()
            if ultima_fmt and initial:
                ultima_fmt = f"{ultima_fmt} ({initial})"

            table_rows.append(
                [
                    str(r_id),
                    razao_social,
                    cnpj,
                    nome,
                    whatsapp,
                    obs,
                    ultima_fmt,
                ]
            )

        tree.set_rows(table_rows)
        status.configure(text=f"{len(rows)} item(ns) na lixeira")
        log.info("Lixeira carregada com %d clientes", len(rows))

    # -------- ações --------
    def on_restore() -> None:
        ids = get_selected_ids()
        if not ids:
            _warn("Lixeira", "Selecione pelo menos um registro para restaurar.")
            return
        if not _ask_yesno("Restaurar", f"Restaurar {len(ids)} registro(s) para a lista principal?"):
            return

        _set_busy(win, [btn_restore, btn_purge, btn_refresh, btn_close], True)
        try:
            restaurar_clientes_da_lixeira(ids)
            ok = len(ids)
            errs = []
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

    def on_purge() -> None:
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

        def _show_wait_dialog(count: int) -> Tuple[tk.Toplevel, ctk.CTkLabel, ctk.CTkProgressBar]:
            dlg = tk.Toplevel(win)
            dlg.withdraw()
            try:
                dlg.title("Aguarde")
                dlg.transient(win)
                dlg.resizable(False, False)
            except Exception as exc:  # noqa: BLE001
                _log_ui_issue("Falha ao configurar dialogo de aguardando", exc)

            label = ctk.CTkLabel(dlg, text=f"Apagando 0/{count} registro(s)... Aguarde.")
            label.pack(padx=20, pady=(15, 5))
            bar = ctk.CTkProgressBar(dlg, mode="determinate")
            bar.set(0)
            bar.pack(fill="x", padx=20, pady=(0, 15))

            try:
                dlg.protocol("WM_DELETE_WINDOW", lambda: None)
            except Exception as exc:  # noqa: BLE001
                _log_ui_issue("Falha ao bloquear fechamento do dialogo de aguardando", exc)

            try:
                dlg.update_idletasks()
                show_centered(dlg)
                dlg.grab_set()
                dlg.focus_force()
            except Exception as exc:  # noqa: BLE001
                _log_ui_issue("Falha ao exibir dialogo de aguardando", exc)

            return dlg, label, bar

        def _make_purge_progress_cb(bar: ctk.CTkProgressBar, label: ctk.CTkLabel) -> Callable[[int, int, int], None]:
            def progress_cb(idx: int, total: int, client_id: int) -> None:
                def _update():
                    try:
                        progress = idx / max(total, 1)
                        bar.set(progress)
                        label.configure(text=f"Apagando {idx}/{total} registro(s)... Aguarde.")
                    except Exception as exc:  # noqa: BLE001
                        _log_ui_issue("Falha ao atualizar barra de progresso da Lixeira", exc)

                win.after(0, _update)

            return progress_cb

        def _on_purge_finished(wait_dlg: tk.Toplevel, ok_count: int, errs_list: Any, total: int) -> None:
            try:
                wait_dlg.destroy()
            except Exception as exc:  # noqa: BLE001
                _log_ui_issue("Falha ao fechar dialogo de aguardando na Lixeira", exc)

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

        def worker() -> None:
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
    try:
        win.update_idletasks()
        show_centered(win)
        win.focus_force()
    except Exception as exc:  # noqa: BLE001
        _log_ui_issue("Falha ao exibir janela da Lixeira", exc)

    win._carregar = carregar  # type: ignore[attr-defined]
    _OPEN_WINDOW = win

    # close handler limpa o singleton
    def _on_close():
        global _OPEN_WINDOW
        try:
            _OPEN_WINDOW = None
        except Exception as exc:  # noqa: BLE001
            _log_ui_issue("Falha ao limpar singleton da Lixeira", exc)
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _on_close)

    # primeira carga e centralização
    carregar()
    try:
        show_centered(win)
    except Exception as exc:  # noqa: BLE001
        _log_ui_issue("Falha ao centralizar janela da Lixeira", exc)

    return win
