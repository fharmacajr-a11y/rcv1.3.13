# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional

import ttkbootstrap as tb

from src.utils.resource_path import resource_path

_log = logging.getLogger(__name__)

# Constantes de espaçamento compacto
BTN_PADX = 4
BTN_PADY = 4


class TopBar(tb.Frame):
    """Barra superior simples com botoes principais."""

    def __init__(
        self,
        master=None,
        on_home: Optional[Callable[[], None]] = None,
        on_pdf_converter: Optional[Callable[[], None]] = None,
        on_pdf_viewer: Optional[Callable[[], None]] = None,
        on_chatgpt: Optional[Callable[[], None]] = None,
        on_sites: Optional[Callable[[], None]] = None,
        on_notifications_clicked: Optional[Callable[[], None]] = None,
        on_mark_all_read: Optional[Callable[[], bool]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._on_home = on_home
        self._on_pdf_converter = on_pdf_converter
        self._on_pdf_viewer = on_pdf_viewer
        self._on_chatgpt = on_chatgpt
        self._on_sites = on_sites
        self._on_notifications_clicked = on_notifications_clicked
        self._on_mark_all_read = on_mark_all_read

        # Estado interno de notificações
        self._notifications_data: list[dict[str, Any]] = []
        self._notifications_by_id: dict[str, dict[str, Any]] = {}  # Mapeia iid -> notif
        self._notifications_popup: tk.Toplevel | None = None
        self._notifications_tree_popup: ttk.Treeview | None = None
        self._mute_callback: Any = None
        self._mute_var: tk.BooleanVar | None = None
        self._unread_count: int = 0

        # Variáveis de notificações
        self._notifications_popup: tk.Toplevel | None = None
        self._notifications_tree: ttk.Treeview | None = None
        self._notifications_data: list[dict[str, Any]] = []
        self._unread_count: int = 0

        self._sites_image = None
        self._chatgpt_image = None
        try:
            icon_path = resource_path("assets/topbar/sites.png")
            if os.path.exists(icon_path):
                self._sites_image = tk.PhotoImage(file=icon_path)
            else:
                _log.warning("Icone do Sites nao encontrado: %s", icon_path)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao carregar icone do Sites: %s", exc)

        try:
            chatgpt_icon_path = resource_path("assets/topbar/chatgpt.png")
            if os.path.exists(chatgpt_icon_path):
                img = tk.PhotoImage(file=chatgpt_icon_path)
                max_size = 16
                width, height = img.width(), img.height()
                if width > max_size or height > max_size:
                    scale_x = max(1, (width + max_size - 1) // max_size)
                    scale_y = max(1, (height + max_size - 1) // max_size)
                    img = img.subsample(scale_x, scale_y)
                self._chatgpt_image = img
            else:
                _log.warning("Icone do ChatGPT nao encontrado: %s", chatgpt_icon_path)
        except Exception as exc:  # noqa: BLE001
            _log.debug("Falha ao carregar icone do ChatGPT: %s", exc)

        container = ttk.Frame(self)
        container.pack(fill="x", expand=True)

        # Estilos para botão Início
        self._home_bootstyle_inactive = "info"
        self._home_bootstyle_active = "info"

        # Botão Início
        self.btn_home = tb.Button(
            container,
            text="Inicio",
            command=self._handle_home,
            bootstyle=self._home_bootstyle_inactive,
        )
        self.btn_home.pack(side="left", padx=(6, BTN_PADX), pady=BTN_PADY)

        # Botão Visualizador PDF
        self.btn_pdf_viewer = tb.Button(
            container,
            text="Visualizador PDF",
            command=self._handle_pdf_viewer,
            bootstyle="info",
        )
        self.btn_pdf_viewer.pack(side="left", padx=(BTN_PADX, BTN_PADX), pady=BTN_PADY)

        # Botão ChatGPT
        self.btn_chatgpt = tb.Button(
            container,
            text="ChatGPT",
            image=self._chatgpt_image,
            compound="left" if self._chatgpt_image else None,
            command=self._handle_chatgpt,
            bootstyle="info",
        )
        self.btn_chatgpt.pack(side="left", padx=(BTN_PADX, BTN_PADX), pady=BTN_PADY)

        # Botão Sites
        self.btn_sites = tb.Button(
            container,
            text="Sites",
            image=self._sites_image,
            compound="left" if self._sites_image else None,
            command=self._handle_sites,
            bootstyle="info",
        )
        self.btn_sites.pack(side="left", padx=(BTN_PADX, 0), pady=BTN_PADY)

        self.right_container = ttk.Frame(container)
        self.right_container.pack(side="right")

        # Botão de notificações (sininho)
        self._notifications_frame = ttk.Frame(self.right_container)
        self._notifications_frame.pack(side="right", padx=(0, 6))

        self.btn_notifications = tb.Button(
            self._notifications_frame,
            text="🔔",
            command=self._toggle_notifications_popup,
            bootstyle="info",
            width=3,
        )
        self.btn_notifications.pack(side="left")

        # Badge com contador
        self._lbl_badge = ttk.Label(
            self._notifications_frame,
            text="",
            foreground="white",
            background="#dc3545",
            font=("Arial", 8, "bold"),
            padding=(4, 0),
        )
        # Badge começa oculto
        self._lbl_badge.pack_forget()

    def _handle_home(self) -> None:
        """Handler para o botão Início."""
        if callable(self._on_home):
            try:
                self._on_home()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_home: %s", exc)

    def _handle_pdf_converter(self) -> None:
        """NO-OP seguro - botão removido mas mantém compatibilidade."""
        if callable(self._on_pdf_converter):
            try:
                self._on_pdf_converter()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_pdf_converter: %s", exc)

    def _handle_pdf_viewer(self) -> None:
        if callable(self._on_pdf_viewer):
            try:
                self._on_pdf_viewer()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_pdf_viewer: %s", exc)

    def _handle_chatgpt(self) -> None:
        if callable(self._on_chatgpt):
            try:
                self._on_chatgpt()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_chatgpt: %s", exc)

    def _handle_sites(self) -> None:
        if callable(self._on_sites):
            try:
                self._on_sites()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar on_sites: %s", exc)

    def set_is_hub(self, is_hub: bool) -> None:
        """Atualiza estado do botão Início conforme contexto Hub."""
        try:
            target_style = self._home_bootstyle_active if is_hub else self._home_bootstyle_inactive
            self.btn_home.configure(bootstyle=target_style)
        except Exception:
            _log.debug("Falha ao aplicar estilo no botão Home da topbar", exc_info=True)
        try:
            if is_hub:
                self.btn_home.state(["disabled"])
            else:
                self.btn_home.state(["!disabled"])
        except Exception:
            try:
                self.btn_home["state"] = "disabled" if is_hub else "normal"
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao atualizar estado do botão Home: %s", exc)

    def set_pick_mode_active(self, active: bool) -> None:
        """Desabilita/habilita botões durante modo seleção de clientes (FIX-CLIENTES-005)."""
        # Atualizar todos os botões do topbar
        buttons = [self.btn_home, self.btn_pdf_viewer, self.btn_chatgpt, self.btn_sites]
        for btn in buttons:
            try:
                if active:
                    btn.state(["disabled"])
                else:
                    btn.state(["!disabled"])
            except Exception:
                try:
                    btn["state"] = "disabled" if active else "normal"
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao atualizar estado do botão %s: %s", btn, exc)

    def set_notifications_count(self, count: int) -> None:
        """Atualiza contador de notificações não lidas.

        Args:
            count: Número de notificações não lidas
        """
        self._unread_count = count

        if count > 0:
            # Mostrar badge com número
            self._lbl_badge.configure(text=str(count))
            self._lbl_badge.pack(side="left", padx=(2, 0))
        else:
            # Ocultar badge
            self._lbl_badge.pack_forget()

    def set_notifications_data(self, notifications: list[dict[str, Any]], mute_callback: Any = None) -> None:
        """Atualiza dados das notificações.

        Args:
            notifications: Lista de notificações
            mute_callback: Callback para toggle de mute (recebe bool)
        """
        self._notifications_data = notifications
        self._mute_callback = mute_callback

        # Abrir popup se ainda não estiver aberto
        if not self._notifications_popup or not self._notifications_popup.winfo_exists():
            self._open_notifications_popup()
        else:
            # Apenas atualizar a Treeview
            self._refresh_notifications_tree()

    def _toggle_notifications_popup(self) -> None:
        """Abre/fecha popup de notificações."""
        if self._notifications_popup and self._notifications_popup.winfo_exists():
            # Fechar popup
            self._notifications_popup.destroy()
            self._notifications_popup = None
            self._notifications_tree = None
        else:
            # Abrir popup
            self._open_notifications_popup()

            # Callback para controller buscar notificações
            if callable(self._on_notifications_clicked):
                try:
                    self._on_notifications_clicked()
                except Exception as exc:  # noqa: BLE001
                    _log.debug("Falha ao executar on_notifications_clicked: %s", exc)

    def _open_notifications_popup(self) -> None:
        """Cria e exibe popup de notificações."""
        from src.ui.window_utils import prepare_hidden_window, show_centered_no_flash

        # Criar popup
        popup = tk.Toplevel(self)
        popup.title("Notificações")
        popup.geometry("600x400")
        popup.transient(self.winfo_toplevel())

        # Aplicar ícone do app
        try:
            icon_path = resource_path("rc.ico")
            if os.path.exists(icon_path):
                popup.iconbitmap(icon_path)
        except Exception:
            # Fallback para PNG com iconphoto
            try:
                png_path = resource_path("rc.png")
                if os.path.exists(png_path):
                    icon_img = tk.PhotoImage(file=png_path)
                    popup.iconphoto(True, icon_img)
                    # Guardar referência para evitar garbage collection
                    popup._icon_img = icon_img  # type: ignore[attr-defined]
            except Exception:
                pass  # Sem ícone, continua sem problemas

        # Preparar janela oculta para evitar flash
        prepare_hidden_window(popup)

        # Container principal
        main_frame = ttk.Frame(popup, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Título
        title_label = ttk.Label(
            main_frame,
            text="Notificações Recentes",
            font=("Arial", 12, "bold"),
        )
        title_label.pack(anchor="w", pady=(0, 10))

        # Frame da Treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")

        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        # Treeview
        columns = ("data", "mensagem", "por")
        tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=12,
        )

        tree.heading("data", text="Data/Hora", anchor="center")
        tree.heading("mensagem", text="Mensagem", anchor="center")
        tree.heading("por", text="Por", anchor="center")

        tree.column("data", width=120, anchor="center", stretch=False)
        tree.column("mensagem", width=420, anchor="center", stretch=True)
        tree.column("por", width=140, anchor="center", stretch=False)

        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)

        tree.pack(fill="both", expand=True)

        # Adicionar handler de duplo clique para mostrar detalhes
        tree.bind("<Double-Button-1>", lambda e: self._show_notification_details(tree))

        self._notifications_tree = tree

        # Botões
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(10, 0))

        btn_mark_read = tb.Button(
            buttons_frame,
            text="Marcar Tudo como Lido",
            command=self._mark_all_read,
            bootstyle="success",
        )
        btn_mark_read.pack(side="left", padx=(0, 10))

        # Checkbutton para silenciar notificações
        self._mute_var = tk.BooleanVar(value=False)
        chk_mute = ttk.Checkbutton(
            buttons_frame,
            text="🔕 Silenciar",
            variable=self._mute_var,
            command=self._on_mute_toggled,
            bootstyle="round-toggle",
        )
        chk_mute.pack(side="left")

        btn_close = tb.Button(
            buttons_frame,
            text="Fechar",
            command=popup.destroy,
            bootstyle="secondary",
        )
        btn_close.pack(side="right")

        # Preencher dados
        self._refresh_notifications_tree()

        # Guardar referência
        self._notifications_popup = popup

        # Mostrar janela centralizada
        show_centered_no_flash(popup, parent=self.winfo_toplevel())

        # Fechar ao clicar fora (opcional)
        popup.bind("<FocusOut>", lambda e: None)  # Removido auto-close

    def _refresh_notifications_tree(self) -> None:
        """Atualiza conteúdo da Treeview com notificações."""
        if not self._notifications_tree:
            return

        # Limpar árvore e dicionário
        for item in self._notifications_tree.get_children():
            self._notifications_tree.delete(item)
        self._notifications_by_id.clear()

        # Preencher com dados
        if not self._notifications_data:
            # Sem notificações
            self._notifications_tree.insert(
                "",
                "end",
                values=("--", "Nenhuma notificação recente", "--"),
            )
        else:
            for idx, notif in enumerate(self._notifications_data):
                # Usar created_at_local_str se disponível (já formatado pelo service)
                date_str = notif.get("created_at_local_str", "--")

                # Mensagem
                message = notif.get("message", "")
                is_read = notif.get("is_read", False)

                # Adicionar prefixo se não lida
                if not is_read:
                    message = "\u25cf " + message  # Bullet point

                # Autor (nome completo, fallback para inicial)
                por = (notif.get("actor_display_name") or "").strip()
                if not por or por == "?":
                    por = notif.get("actor_initial", "") or "\u2014"

                # Usar ID da notificação como iid (ou fallback para índice)
                notif_id = notif.get("id")
                if notif_id:
                    iid = str(notif_id)
                else:
                    iid = f"notif_{idx}"

                # Inserir com iid específico (3 valores agora)
                self._notifications_tree.insert(
                    "",
                    "end",
                    iid=iid,
                    values=(date_str, message, por),
                )

                # Mapear iid -> notificação completa
                self._notifications_by_id[iid] = notif

    def _show_notification_details(self, tree: ttk.Treeview) -> None:
        """Mostra detalhes completos de uma notificação ao dar duplo clique.

        Args:
            tree: Treeview com notificações
        """
        from tkinter import messagebox

        # Obter item selecionado
        selection = tree.selection()
        if not selection:
            return

        iid = selection[0]

        # Buscar notificação pelo iid no dicionário
        notif = self._notifications_by_id.get(iid)
        if not notif:
            return

        # Montar mensagem de detalhes
        message = notif.get("message", "")
        request_id = notif.get("request_id", "--")
        actor_email = notif.get("actor_email", "--")
        actor_display_name = notif.get("actor_display_name", "")
        created_at = notif.get("created_at_local_str", "--")
        module = notif.get("module", "--")
        event = notif.get("event", "--")

        # Formatar usuário (nome + email se disponível)
        if actor_display_name and actor_display_name != "?" and actor_email and actor_email != "--":
            user_info = f"{actor_display_name} <{actor_email}>"
        elif actor_email and actor_email != "--":
            user_info = actor_email
        else:
            user_info = "--"

        details = (
            f"Data/Hora: {created_at}\n"
            f"Módulo: {module}\n"
            f"Evento: {event}\n"
            f"Mensagem: {message}\n\n"
            f"Request ID: {request_id}\n"
            f"Usuário: {user_info}"
        )

        messagebox.showinfo("Detalhes da Notificação", details, parent=self._notifications_popup)

    def _on_mute_toggled(self) -> None:
        """Callback quando usuário alterna o estado de silenciar."""
        if not self._mute_var:
            return

        is_muted = self._mute_var.get()

        # Chamar callback do MainWindow para atualizar flag
        if callable(self._mute_callback):
            try:
                self._mute_callback(is_muted)
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao executar mute_callback: %s", exc)

    def _mark_all_read(self) -> None:
        """Marca todas notificações como lidas."""
        from tkinter import messagebox

        # Chamar callback do MainWindow para executar mark_all_read
        if callable(self._on_mark_all_read):
            try:
                success = self._on_mark_all_read()
                if not success:
                    messagebox.showerror(
                        "Erro",
                        "Falha ao marcar notificações como lidas. Tente novamente.",
                        parent=self._notifications_popup,
                    )
                    return
            except Exception as exc:  # noqa: BLE001
                _log.exception("Falha ao executar on_mark_all_read: %s", exc)
                messagebox.showerror(
                    "Erro",
                    f"Erro ao marcar notificações como lidas: {exc}",
                    parent=self._notifications_popup,
                )
                return

        # Sucesso: zerar badge imediatamente
        self.set_notifications_count(0)

        # Recarregar lista (callback do MainWindow irá atualizar)
        if callable(self._on_notifications_clicked):
            try:
                self._on_notifications_clicked()
            except Exception as exc:  # noqa: BLE001
                _log.debug("Falha ao recarregar notificações: %s", exc)
