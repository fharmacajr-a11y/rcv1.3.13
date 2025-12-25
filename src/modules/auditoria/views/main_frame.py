"""View principal do módulo Auditoria."""

from __future__ import annotations

import logging
import re
import tkinter as tk
import unicodedata
from tkinter import messagebox, ttk
from typing import Any, Callable, Dict, Literal, Optional

from src.helpers.formatters import fmt_datetime_br
from src.modules.auditoria.service import AuditoriaServiceError
from src.modules.auditoria.viewmodel import AuditoriaViewModel
from ..application import AuditoriaApplication, AuditoriaApplicationConfig

from . import layout as auditoria_layout
from .client_helpers import cliente_cnpj_from_row, cliente_display_id_first, cliente_razao_from_row
from .status_helpers import (
    DEFAULT_AUDITORIA_STATUS,
    STATUS_LABELS,
    STATUS_MENU_ITEMS,
    canonical_status,
    is_status_open,
    label_to_status,
    status_to_label,
)
from .storage_actions import AuditoriaStorageActions
from .upload_flow import AuditoriaUploadFlow

logger = logging.getLogger(__name__)

OFFLINE_MSG = "Recurso on-line. Verifique internet e credenciais do Supabase."


class AuditoriaFrame(ttk.Frame):
    """
    Tela de Auditoria:
      - Combobox para escolher Cliente
      - Botão 'Iniciar auditoria' (insere em public.auditorias)
      - Tabela com auditorias (cliente, status, criado/atualizado)

    Não altera nenhuma lógica global; funciona isolada.
    """

    def __init__(self, master: tk.Misc, go_back: Callable[[], None] | None = None, **kwargs) -> None:
        """
        Inicializa a tela de Auditoria.

        Args:
            master: Widget pai (Tk ou Frame)
            go_back: Callback para voltar ao Hub (opcional)
            **kwargs: Argumentos adicionais para ttk.Frame
        """
        super().__init__(master, **kwargs)
        self._go_back: Callable[[], None] | None = go_back

        self._search_var: tk.StringVar = tk.StringVar()
        self._cliente_display_to_id: Dict[str, int] = {}
        self._cliente_var: tk.StringVar = tk.StringVar()
        self._selected_cliente_id: int | None = None

        # Índice de auditorias: {iid: {db_id, auditoria_id, cliente_nome, cnpj, ...}}
        self._aud_index: Dict[str, Dict[str, Any]] = {}

        # Rastreio de janelas "Ver subpastas" abertas por auditoria_id (chave string)
        self._open_browsers: Dict[str, tk.Toplevel] = {}

        # Org ID do usuário logado (cache)
        self._org_id: str = ""
        self._status_menu: tk.Menu | None = None
        self._status_menu_items: tuple[str, ...] = STATUS_MENU_ITEMS
        self._status_click_iid: str | None = None
        self._status_menu_open: bool = False
        self._menu_refresh_added: bool = False
        self._vm: AuditoriaViewModel = AuditoriaViewModel()
        self._controller: AuditoriaApplication = AuditoriaApplication(AuditoriaApplicationConfig(viewmodel=self._vm))

        self._storage_actions: AuditoriaStorageActions = AuditoriaStorageActions(self, self._controller)
        self._upload_flow: AuditoriaUploadFlow = AuditoriaUploadFlow(self, self._controller)

        ui_gap = 6  # espacinho horizontal curto entre botões
        ui_padx = 8
        ui_pady = 6
        self.UI_GAP = ui_gap
        self.UI_PADX = ui_padx
        self.UI_PADY = ui_pady

        self._build_ui()

        try:
            import ttkbootstrap as tb  # type: ignore[import]  # noqa: F401
        except Exception:
            style = ttk.Style(self)
            style.configure("RC.Success.TButton", foreground="white")
            style.map("RC.Success.TButton", background=[("!disabled", "#198754"), ("active", "#157347")])
            self.btn_iniciar.configure(style="RC.Success.TButton")

            style.configure("RC.Danger.TButton", foreground="white")
            style.map("RC.Danger.TButton", background=[("!disabled", "#DC3545"), ("active", "#BB2D3B")])
            self.btn_excluir.configure(style="RC.Danger.TButton")
        else:
            self.btn_iniciar.configure(bootstyle="success")  # type: ignore[arg-type]
            self.btn_excluir.configure(bootstyle="danger")  # type: ignore[arg-type]

        # Deferir load para garantir widgets prontos
        self.after(100, self._lazy_load)

    def _build_ui(self) -> None:
        """Constroi a interface da tela delegando aos helpers de layout."""
        auditoria_layout.build_auditoria_ui(self)

        ui_padx = getattr(self, "UI_PADX", 8)
        ui_pady = getattr(self, "UI_PADY", 6)
        self.lbl_offline = ttk.Label(self, text=OFFLINE_MSG, foreground="#666")
        self.lbl_offline.grid(row=4, column=0, sticky="w", padx=ui_padx, pady=(ui_pady, 0))

    # ---------- Search Helpers ----------
    def _normalize(self, s: str) -> str:
        """Normaliza texto para busca (remove acentos, casefold, só alfanum)."""
        s = s or ""
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = s.casefold()
        return re.sub(r"[^a-z0-9]+", " ", s).strip()

    def _clear_search(self) -> None:
        """Limpa campo de busca."""
        self._search_var.set("")

    def _filtra_clientes(self, query: str) -> None:
        """Atualiza o filtro de clientes via viewmodel."""
        self._vm.set_search_text(query)
        clientes = self._vm.get_filtered_clientes()
        self._fill_clientes_combo(clientes)

        if clientes:
            if hasattr(self, "lbl_notfound"):
                self.lbl_notfound.configure(text="")
        else:
            if hasattr(self, "lbl_notfound"):
                self.lbl_notfound.configure(text="Nenhum cliente encontrado")

    @staticmethod
    def _status_label(status: str) -> str:
        return status_to_label(status)

    def _apply_filter(self) -> None:
        """Aplica filtro de busca nos clientes (compatibilidade)."""
        self._filtra_clientes(self._search_var.get())

    def _fill_clientes_combo(self, clientes: list[dict]) -> None:  # type: ignore[type-arg]
        """Atualiza a combobox com a lista filtrada de clientes."""
        values: list[str] = []
        mapping: dict[str, int] = {}

        for cli in clientes:
            if not isinstance(cli, dict):
                continue
            raw_id = cli.get("id")
            try:
                cid_int = int(raw_id) if raw_id not in (None, "") else None
            except Exception:
                cid_int = None

            razao = cliente_razao_from_row(cli)
            cnpj_raw = cliente_cnpj_from_row(cli)
            ident = cid_int if cid_int is not None else raw_id
            display = cliente_display_id_first(ident, razao, cnpj_raw)
            values.append(display)

            if cid_int is not None:
                mapping[display] = cid_int
            elif raw_id not in (None, ""):
                try:
                    mapping[display] = int(str(raw_id))
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Falha ao mapear cliente_id como int: %s", exc)

        self._cliente_display_to_id = mapping

        try:
            self.combo_cliente.configure(values=values, state="readonly")
        except Exception:
            return

        current = self.cliente_var.get()
        if values and (not current or current not in values):
            self.cliente_var.set(values[0])
        elif not values:
            self.cliente_var.set("")

        self._on_cliente_selected()

    def _get_selected_cliente_id(self) -> int | None:
        """Retorna o cliente_id selecionado na combobox (ou None)."""
        try:
            display = self.cliente_var.get().strip()
        except Exception:
            return None
        if not display:
            return None
        raw = self._cliente_display_to_id.get(display)
        if raw is None:
            return None
        try:
            return int(raw)
        except Exception:
            try:
                return int(str(raw))
            except Exception:
                return None

    def _on_cliente_selected(self) -> None:
        """Atualiza seleção interna e notifica o viewmodel."""
        cliente_id = self._get_selected_cliente_id()
        self._selected_cliente_id = cliente_id
        self._vm.set_selected_cliente_id(cliente_id)

    def _has_open_auditoria_for(self, cliente_id: int | str | None) -> bool:
        """Procura na lista atual se há auditoria 'aberta' para o cliente."""
        if cliente_id in (None, "", 0):
            return False

        target_str = str(cliente_id)
        try:
            target_int = int(cliente_id)
        except Exception:
            target_int = None

        for rec in self._aud_index.values():
            rec_cliente = rec.get("cliente_id")
            if rec_cliente is None:
                continue

            match = False
            if target_int is not None:
                try:
                    match = int(rec_cliente) == target_int
                except Exception:
                    match = False
            if not match and str(rec_cliente) == target_str:
                match = True

            if match and is_status_open(rec.get("status")):
                return True
        return False

    def _do_refresh(self) -> None:
        """Recarrega listas de clientes e auditorias."""
        client_loader = getattr(self, "_load_clientes", None)
        if callable(client_loader):
            client_loader()

        loader = getattr(self, "_load_auditorias", None)
        if callable(loader):
            loader()
            return

        fallback = getattr(self, "load_rows", None)
        if callable(fallback):
            fallback([])

    def _add_refresh_menu_entry(self) -> None:
        """Adiciona a acao de recarregar a barra de menus, se existir."""
        auditoria_layout.add_refresh_menu_entry(self)

    # ---------- Storage Helpers ----------
    def _require_storage_ready(self) -> bool:
        """Valida se storage está configurado/online."""
        try:
            self._controller.ensure_storage_ready()
        except AuditoriaServiceError as exc:
            messagebox.showwarning("Storage", str(exc))
            return False
        return True

    def _selected_client_id(self) -> Optional[int]:
        """Retorna o id do cliente atualmente selecionado no combobox."""
        return self._get_selected_cliente_id()

    # ---------- Loaders ----------
    def _lazy_load(self) -> None:
        """Carrega dados após inicialização da UI."""
        if not self._controller.is_online():
            self._set_offline(True)
            return
        self._set_offline(False)

        try:
            self._search_var.trace_add("write", lambda *args: self._apply_filter())
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao registrar trace de busca em Auditoria: %s", exc)

        self._load_clientes()
        self._load_auditorias()

    def _set_offline(self, is_offline: bool) -> None:
        """Configura estado offline/online da tela."""
        state = "disabled" if is_offline else "normal"
        self.ent_busca.configure(state=state)
        self.cmb_cliente.configure(state="disabled" if is_offline else "readonly")
        self.btn_iniciar.configure(state=state)

        for w in (
            getattr(self, "_btn_h_ver", None),
            getattr(self, "_btn_h_enviar_zip", None),
        ):
            if w:
                w.configure(state=state)

        self.lbl_offline.configure(text=OFFLINE_MSG if is_offline else "")

    def _load_clientes(self) -> None:
        """Carrega lista de clientes via viewmodel."""
        if not self._controller.is_online():
            return

        try:
            self._controller.refresh_clientes()
        except AuditoriaServiceError as exc:
            messagebox.showwarning("Clientes", f"Não foi possível carregar os clientes.\n{exc}")
            return

        self._apply_filter()

    def _load_auditorias(self) -> None:
        """Carrega lista de auditorias via viewmodel e atualiza a treeview."""
        if not self._controller.is_online():
            return

        try:
            rows = self._controller.refresh_auditorias()
        except AuditoriaServiceError as exc:
            messagebox.showwarning("Auditorias", f"Falha ao carregar auditorias.\n{exc}")
            return

        self._aud_index.clear()
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            data = {
                "db_id": row.db_id,
                "cliente_id": row.cliente_id if row.cliente_id is not None else row.raw.get("cliente_id"),
                "cliente_display": row.cliente_display,
                "cliente_nome": row.cliente_nome,
                "cliente_razao": row.cliente_nome,
                "cnpj": row.cliente_cnpj,
                "status": row.status,
                "status_display": row.status_display,
                "created_at": row.created_at,
                "created_at_iso": row.created_at_iso,
                "updated_at": row.updated_at,
                "updated_at_iso": row.updated_at_iso,
            }
            self._aud_index[row.iid] = data
            self.tree.insert(
                "",
                "end",
                iid=row.iid,
                values=(row.cliente_display, row.status_display, row.created_at, row.updated_at),
            )

        self._update_action_buttons_state()

    def _update_action_buttons_state(self) -> None:
        sels = self.tree.selection()
        has_selection = bool(sels)
        try:
            self.btn_subpastas.configure(state="normal" if has_selection else "disabled")
            self.btn_excluir.configure(state="normal" if has_selection else "disabled")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao atualizar botoes de acao na Auditoria: %s", exc)

    def _ensure_status_menu(self) -> tk.Menu:
        if self._status_menu and self._status_menu.winfo_exists():
            return self._status_menu

        menu = tk.Menu(self, tearoff=0)
        for status in self._status_menu_items:
            menu.add_command(
                label=self._status_label(status), command=lambda value=status: self._apply_status_from_menu(value)
            )
        self._status_menu = menu
        return menu

    def _open_status_menu(self, event: tk.Event) -> Literal["break"] | None:  # type: ignore[name-defined]
        """Exibe menu de contexto de status apenas quando o clique for na coluna 'status'."""
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row or col != "#2":
            return "break"

        if self._status_menu_open:
            return "break"

        try:
            self.tree.selection_set(row)
            self.tree.focus(row)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao posicionar selecao do menu de status: %s", exc)

        self._status_click_iid = row
        self._status_menu_open = True
        menu = self._ensure_status_menu()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
            self._status_menu_open = False
        return "break"

    def _apply_status_from_menu(self, new_status: str) -> None:
        iid = self._status_click_iid or next(iter(self.tree.selection()), None)
        self._status_click_iid = None
        if not iid:
            return
        self._set_auditoria_status(iid, new_status)

    def _set_auditoria_status(self, iid: str, new_status: str) -> None:
        row = self._aud_index.get(iid)
        if not row:
            return

        normalized = label_to_status(new_status)
        desired_db = canonical_status(normalized or new_status)
        if desired_db not in STATUS_LABELS:
            messagebox.showerror("Auditoria", "Status selecionado inválido.")
            return

        current = canonical_status(row.get("status"))
        if current == desired_db:
            return

        try:
            update_info = self._controller.update_auditoria_status(str(row["db_id"]), desired_db)
        except (AuditoriaServiceError, ValueError) as exc:
            messagebox.showerror("Auditoria", f"Falha ao atualizar status.\n{exc}")
            return

        updated_iso = update_info.get("updated_at")

        row["status"] = desired_db
        row["status_display"] = status_to_label(desired_db)
        if updated_iso:
            row["updated_at_iso"] = updated_iso
            row["updated_at"] = fmt_datetime_br(updated_iso)

        self.tree.set(iid, "status", row["status_display"])
        if row.get("updated_at"):
            self.tree.set(iid, "atualizado", row["updated_at"])

    # ---------- Actions ----------
    def _on_iniciar(self) -> None:
        """Handler do botão 'Iniciar auditoria'."""
        cliente_id = self._get_selected_cliente_id()
        if not cliente_id:
            messagebox.showwarning("Auditoria", "Selecione um cliente para iniciar a auditoria.")
            return

        if self._has_open_auditoria_for(cliente_id):
            msg = "Já existe uma auditoria em andamento para este cliente.\n\nDeseja iniciar outra auditoria para a mesma farmácia?"
            if not messagebox.askyesno("Confirmar", msg):
                return

        try:
            self._controller.start_auditoria(cliente_id, status=DEFAULT_AUDITORIA_STATUS)
        except AuditoriaServiceError as exc:
            messagebox.showerror("Auditoria", f"Não foi possível iniciar a auditoria.\n{exc}")
            return

        self._load_auditorias()
        messagebox.showinfo("Auditoria", "Auditoria iniciada com sucesso.")

    def _on_auditoria_select(self, event=None) -> None:  # type: ignore[no-untyped-def]
        """Handler de seleção na Treeview de auditorias. Habilita/desabilita botões Ver subpastas e Excluir."""
        sel = self.tree.selection()
        if sel and sel[0] in self._aud_index:
            self._btn_h_ver.configure(state="normal")
        else:
            self._btn_h_ver.configure(state="disabled")

        if sel:
            self._btn_h_delete.configure(state="normal")
        else:
            self._btn_h_delete.configure(state="disabled")

    def _delete_auditorias(self) -> None:
        self._storage_actions.delete_auditorias()

    def _open_subpastas(self) -> None:
        self._storage_actions.open_subpastas()

    def _create_auditoria_folder(self) -> None:
        self._storage_actions.create_auditoria_folder()

    def _upload_archive_to_auditoria(self) -> None:
        self._upload_flow.upload_archive_to_auditoria()
