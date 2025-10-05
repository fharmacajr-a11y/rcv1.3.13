# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
import os
import webbrowser
import re
import logging

from core.search import search_clientes
from core.search.pagination import search_clientes_paged, count_clientes
from app_utils import fmt_data
import app_core, app_status
from utils import themes
from utils.theme_manager import theme_manager  # <-- ThemeManager (hook mínimo)
from ui.components import draw_whatsapp_overlays
from config.constants import (
    ICON_SIZE_WHATS,
    COL_ID_WIDTH, COL_RAZAO_WIDTH, COL_CNPJ_WIDTH, COL_NOME_WIDTH,
    COL_WHATSAPP_WIDTH, COL_OBS_WIDTH, COL_ULTIMA_WIDTH,
)
from core.services import lixeira_service  # chamaremos direto p/ evitar modal duplicado no core

logger = logging.getLogger("app_gui")
log = logger


class App(tb.Window):
    def __init__(self, start_hidden: bool = False):
        # Carrega o tema UMA vez (evita I/O repetido em disco)
        _theme_name = themes.load_theme()
        super().__init__(themename=_theme_name)

        # === Menubar ===
        try:
            import tkinter as _tk
            _menubar = _tk.Menu(self)

            _file = _tk.Menu(_menubar, tearoff=0)
            _file.add_command(label="Sair", command=self.destroy)
            _menubar.add_cascade(label="Arquivo", menu=_file)

            _admin = _tk.Menu(_menubar, tearoff=0)
            _admin.add_command(label="Gerenciar Usuários", command=self._open_user_manager)
            _menubar.add_cascade(label="Admin", menu=_admin)

            _help = _tk.Menu(_menubar, tearoff=0)
            _help.add_command(label="Sobre/Changelog", command=self._show_changelog)
            _menubar.add_cascade(label="Ajuda", menu=_help)

            self.config(menu=_menubar)
        except Exception as _e:
            log.exception("Falha ao criar Menubar", exc_info=_e)

        if start_hidden:
            self.withdraw()

        # Aplica o tema também no Style global (usando o mesmo nome já carregado)
        try:
            tb.Style().theme_use(_theme_name)
        except Exception:
            pass

        # Captura exceções de callbacks do Tk e escreve no log
        def _tk_report(exc, val, tb_):
            log.exception("Exceção no Tkinter callback", exc_info=(exc, val, tb_))
        self.report_callback_exception = _tk_report

        self.title('RC - v1.2.1.8')
        self.geometry("1200x640")
        self.tema_atual = _theme_name
        self._net_timer = None
        self._restarting = False

        # Debounce para overlays do WhatsApp
        self._whats_overlay_after = None

        # --- ThemeManager: registra janela e cria listener p/ estilos de botões ---
        try:
            theme_manager.register_window(self)
            self._theme_listener = lambda t: themes.apply_button_styles(self, theme=t)
            theme_manager.add_listener(self._theme_listener)
        except Exception:
            self._theme_listener = None

        log.info("App iniciado com tema: %s", self.tema_atual)

        # ---------------- BARRA DE BUSCA ----------------
        top = tb.Frame(self)
        top.pack(fill="x", padx=6, pady=6)

        tb.Label(top, text="Pesquisar:").pack(side="left")

        self.ent_pesq = tb.Entry(top, width=50)
        self.ent_pesq.pack(side="left", padx=6)
        self.ent_pesq.bind("<Return>", lambda e: self.buscar())
        self.ent_pesq.bind("<KeyRelease>", lambda e: self.carregar() if not self.ent_pesq.get().strip() else None)

        self.btn_buscar = tb.Button(top, text="Buscar", command=self.buscar, bootstyle="secondary")
        self.btn_buscar.pack(side="left", padx=3)

        self.btn_limpar = tb.Button(top, text="Limpar", command=self.carregar, bootstyle="secondary")
        self.btn_limpar.pack(side="left", padx=3)

        self.btn_refresh = tb.Button(top, text="↻", command=self._on_refresh, bootstyle="secondary")
        self.btn_refresh.pack(side="left", padx=3)

        self.btn_lixeira = tb.Button(
            top, text="Lixeira", width=8,
            command=lambda: self._safe_call(app_core.abrir_lixeira_ui, self),
            bootstyle="warning"
        )
        self.btn_lixeira.pack(side="right", padx=6)

        # ---------------- ORDENACAO ----------------
        ord_frame = tb.Frame(self)
        ord_frame.pack(fill="x", padx=6, pady=(0, 6))

        tb.Label(ord_frame, text="Ordenar por:").pack(side="left")

        self.ord_opcao = tb.Combobox(
            ord_frame, state="readonly",
            values=["Razão Social (A->Z)", "CNPJ (A->Z)", "Nome (A->Z)", "Ultima Alteracao (Recente)"],
            width=28,
        )
        self.ord_opcao.current(0)
        self.ord_opcao.pack(side="left", padx=6)

        self.btn_aplicar = tb.Button(ord_frame, text="Aplicar", command=self.aplicar_ordenacao, bootstyle="secondary")
        self.btn_aplicar.pack(side="left", padx=3)

        # ---------------- PAGINACAO (estado) ----------------
        self._page = 0
        self._page_size = 50
        self._total = 0

        # ---------------- TABELA ----------------
        cols = ("id", "razao", "cnpj", "nome", "whatsapp", "obs", "ultima")
        self.tree = tb.Treeview(self, columns=cols, show="headings", selectmode="extended")

        # ---- Barra de paginação ----
        pag = tb.Frame(self)
        pag.pack(fill="x", padx=6, pady=(6, 6))

        self.btn_prev = tb.Button(pag, text="⟨ Anterior", command=self._go_prev, bootstyle="secondary")
        self.btn_prev.pack(side="left")

        self.lbl_page = tb.Label(pag, text="Página 1 — 0 de 0")
        self.lbl_page.pack(side="left", padx=8)

        self.btn_next = tb.Button(pag, text="Próxima ⟩", command=self._go_next, bootstyle="secondary")
        self.btn_next.pack(side="left")

        headers = {
            "id": "ID", "razao": "Razão Social", "cnpj": "CNPJ", "nome": "Nome",
            "whatsapp": "WhatsApp", "obs": "Observações", "ultima": "Última Alteração"
        }
        for c in cols:
            self.tree.heading(c, text=headers[c])

        # Redesenho de ícones com debounce para evitar flicker em grids grandes
        self.tree.bind('<Configure>',   lambda e: self._schedule_whats_overlays())
        self.tree.bind('<MouseWheel>',  lambda e: self._schedule_whats_overlays())
        self.tree.bind('<<TreeviewSelect>>', lambda e: self._schedule_whats_overlays())
        # abrir WhatsApp ao clicar na coluna correspondente
        self.tree.bind('<ButtonRelease-1>', self._on_tree_click)

        # Larguras usando constantes (centraliza ajustes)
        self.tree.column("id",        width=COL_ID_WIDTH,        anchor="center")
        self.tree.column("razao",     width=COL_RAZAO_WIDTH,     anchor="center")
        self.tree.column("cnpj",      width=COL_CNPJ_WIDTH,      anchor="center")
        self.tree.column("nome",      width=COL_NOME_WIDTH,      anchor="center")
        self.tree.column("whatsapp",  width=COL_WHATSAPP_WIDTH,  anchor="center")
        self.tree.column("obs",       width=COL_OBS_WIDTH,       anchor="center")
        self.tree.column("ultima",    width=COL_ULTIMA_WIDTH,    anchor="center", stretch=True, minwidth=COL_ULTIMA_WIDTH)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        # ---------------- RODAPÉ ----------------
        bottom = tb.Frame(self)
        bottom.pack(fill="x", pady=6)

        self.status_var_dot = tk.StringVar(value="●")
        self.status_var_text = tk.StringVar(value="LOCAL")

        status_box = tb.Frame(bottom)
        status_box.pack(side="right", padx=6)
        self.status_dot = tb.Label(
            status_box, textvariable=self.status_var_dot,
            bootstyle="warning", font=("Segoe UI", 16)
        )
        self.status_txt = tb.Label(status_box, textvariable=self.status_var_text, font=("Segoe UI", 9))
        self.status_dot.grid(row=0, column=0, sticky="e")
        self.status_txt.grid(row=0, column=1, sticky="w", padx=(6, 0), pady=(2, 0))

        # Atualiza o rodapé com usuário assim que o login concluir
        try:
            self._schedule_user_status_refresh()
        except Exception:
            pass

        self.btn_novo = tb.Button(
            bottom, text="Novo Cliente",
            command=lambda: self._safe_call(app_core.novo_cliente, self),
            bootstyle="success"
        )
        self.btn_novo.pack(side="left", padx=5)

        self.btn_editar = tb.Button(bottom, text="Editar", command=self.editar_cliente, bootstyle="info")
        self.btn_editar.pack(side="left", padx=5)

        self.btn_abrir = tb.Button(bottom, text="Abrir Pasta", command=self.abrir_pasta, bootstyle="secondary")
        self.btn_abrir.pack(side="left", padx=5)

        self.btn_subpastas = tb.Button(
            bottom, text="Ver Subpastas", command=self.ver_subpastas, bootstyle="secondary"
        )
        self.btn_subpastas.pack(side="left", padx=5)

        # Botão de tema usa o ThemeManager (aplica a todas as janelas registradas)
        self.btn_tema = tb.Button(
            bottom, text="Trocar Tema",
            command=lambda: theme_manager.toggle(),  # <-- mudou
            bootstyle="secondary"
        )
        self.btn_tema.pack(side="right", padx=5)

        # binds
        self.tree.bind("<Delete>", lambda e: self.confirmar_e_enviar_para_lixeira())  # usa wrapper da UI
        self.tree.bind("<Button-3>", self._abrir_menu_contexto)
        self.bind("<Control-f>", lambda e: (self.ent_pesq.focus_set(), "break"))
        self.bind("<Control-r>", lambda e: (self.carregar(), "break"))
        self.bind("<F5>",         lambda e: (self.carregar(), "break"))

        self._menu = tk.Menu(self.tree, tearoff=0)
        self._menu.add_command(label="Editar ficha", command=self.editar_cliente)
        self._menu.add_command(
            label="Enviar para Lixeira",
            command=self.confirmar_e_enviar_para_lixeira  # usa wrapper da UI
        )

        # aplica estilos de botões conforme tema atual (sem reler JSON)
        themes.apply_button_styles(self, theme=_theme_name)

        # carrega dados
        self.carregar()
        app_status.update_net_status(self)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -------- utilitário seguro --------
    def _safe_call(self, func, *a, **kw):
        try:
            return func(*a, **kw)
        except Exception:
            log.exception("Erro ao executar ação: %s", getattr(func, "__name__", func))
            messagebox.showerror("Erro", "Ocorreu um erro. Veja o console para detalhes.")

    # -------- wrapper UI: confirmar + enviar para Lixeira (com logs) --------
    def confirmar_e_enviar_para_lixeira(self, ids: list[int] | None = None):
        """
        Wrapper da UI para mover para Lixeira com confirmação e logs.
        - UI pergunta; service executa; UI mostra resultado.
        - Chama lixeira_service direto para evitar qualquer modal duplicado dentro do app_core.
        """
        # Coleta seleção se não veio lista explícita
        if ids is None:
            ids = self._get_selected_pks()

        # Normaliza e deduplica mantendo ordem
        norm, seen = [], set()
        for x in ids or []:
            try:
                v = int(x)
            except Exception:
                continue
            if v not in seen:
                seen.add(v)
                norm.append(v)
        ids = norm

        if not ids:
            messagebox.showinfo("Aviso", "Selecione um ou mais clientes.", parent=self)
            log.info("UI: enviar para Lixeira abortado (sem seleção).")
            return

        if not messagebox.askokcancel("Confirmar", f"Enviar {len(ids)} cliente(s) para a Lixeira?", parent=self):
            log.info("UI: envio para Lixeira cancelado pelo usuário. ids=%s", ids)
            return

        log.info("UI: enviar para Lixeira -> %d id(s): %s", len(ids), ids)
        try:
            result = lixeira_service.enviar_para_lixeira(ids)
        except Exception:
            log.exception("UI: falha ao enviar para Lixeira (chamada service).")
            messagebox.showerror("Erro", "Falha ao enviar para a Lixeira. Veja os logs.", parent=self)
            return

        # Normaliza retorno para ambas as assinaturas
        ok_count = 0
        falhas_count = 0
        if isinstance(result, tuple) and len(result) == 2:
            a, b = result
            if isinstance(a, int) and isinstance(b, int):
                # nova API -> inteiros (ex.: ok_db, falhas ou ok_db, pastas_movidas)
                ok_count, falhas_count = a, b
            else:
                # API antiga -> listas (ok_list, falhas)
                ok_list, falhas = a, b
                ok_count = len(ok_list or [])
                falhas_count = len(falhas or [])
        else:
            ok_count = int(result or 0)
            falhas_count = 0

        # feedback
        if falhas_count:
            messagebox.showwarning("Parcial", f"{ok_count} enviado(s), {falhas_count} falhou(aram).", parent=self)
        else:
            messagebox.showinfo("Sucesso", f"{ok_count} cliente(s) enviados para a Lixeira.", parent=self)

        # refresh principal
        try:
            self.carregar()
        except Exception:
            log.exception("UI: falha ao atualizar lista principal após envio")

        # refresh imediato da janela da Lixeira se estiver aberta
        try:
            if hasattr(self, "lixeira_win") and self.lixeira_win and self.lixeira_win.winfo_exists():
                log.info("UI: atualizando Lixeira imediatamente após envio")
                if hasattr(self.lixeira_win, "carregar_func"):
                    self.lixeira_win.carregar_func()
        except Exception:
            log.exception("UI: falha ao sinalizar Lixeira para recarregar")

    # -------- ações / dados --------
    def _on_close(self):
        # Desregistra do ThemeManager e remove listener antes de destruir
        try:
            if self._theme_listener:
                theme_manager.remove_listener(self._theme_listener)
            theme_manager.unregister_window(self)
        except Exception:
            pass
        try:
            self.quit()
            self.destroy()
        except Exception:
            pass

    def _abrir_whatsapp(self, numero: str):
        dig = re.sub(r'\D', '', numero or '')
        if not dig:
            return
        if not dig.startswith('55'):
            dig = '55' + dig
        webbrowser.open_new(f'https://web.whatsapp.com/send?phone={dig}')

    def _on_tree_click(self, event):
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        try:
            cols = list(self.tree["columns"])
            if int(col.replace('#',''))-1 < len(cols):
                colname = cols[int(col.replace('#',''))-1]
            else:
                colname = None
        except Exception:
            colname = None
        if row and colname == 'whatsapp':
            numero = self.tree.set(row, 'whatsapp')
            log.info("UI: abrir WhatsApp para número '%s'", numero)
            self._abrir_whatsapp(numero)
        return None

    def _popular(self, rows) -> None:
        # Limpa a árvore
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        # --- tenta buscar últimas atividades em lote (evita N+1) ---
        ids = [int(r[0]) for r in rows if r and len(r) >= 1]
        last_by_id = {}
        try:
            from core.logs.audit import last_client_activity_many as _last_many
            if ids and callable(_last_many):
                last_by_id = _last_many(ids) or {}
        except Exception:
            last_by_id = {}

        # Fallback para função antiga (apenas p/ ids não cobertos)
        try:
            from core.logs.audit import last_client_activity as _last_one
        except Exception:
            _last_one = None

        for idx, r in enumerate(rows, start=1):
            pk, numero, nome, razao, cnpj, ult, obs = r

            last = last_by_id.get(pk)
            if (last is None) and _last_one:
                try:
                    last = _last_one(pk)
                except Exception:
                    last = None

            if last:
                ts, by = (last[0], last[1]) if isinstance(last, (list, tuple)) and len(last) >= 2 else (None, None)
                ultima_txt = f"{fmt_data(ts)} ({by})" if ts else (fmt_data(ult) or "")
            else:
                ultima_txt = fmt_data(ult)

            obs_txt = f"⚠ {obs}" if (obs and str(obs).strip()) else (obs or "")

            # mantém o ID real (pk) na primeira coluna
            values = (pk, razao or "", cnpj or "", nome or "", (numero or ""), obs_txt, ultima_txt)
            self.tree.insert("", "end", iid=str(pk), values=values)

        # agenda desenho dos overlays com debounce
        self._schedule_whats_overlays()

        # autoajuste largura da coluna 'Última Alteração'
        try:
            from tkinter import font as tkfont
            fnt = tkfont.nametofont('TkDefaultFont')
            header = 'Última Alteração'
            maxw = fnt.measure(header)
            for iid in self.tree.get_children(''):
                val = str(self.tree.set(iid, 'ultima') or '')
                w = fnt.measure(val)
                if w > maxw:
                    maxw = w
            maxw = maxw + 24
            if maxw < COL_ULTIMA_WIDTH:
                maxw = COL_ULTIMA_WIDTH
            if maxw > 240:
                maxw = 240
            self.tree.column('ultima', width=int(maxw), stretch=True, minwidth=COL_ULTIMA_WIDTH)
        except Exception:
            pass

    def _schedule_whats_overlays(self):
        """Debounce: evita churn de labels durante scroll/redimensionamento."""
        try:
            if self._whats_overlay_after is not None:
                self.after_cancel(self._whats_overlay_after)
        except Exception:
            pass
        try:
            self._whats_overlay_after = self.after(
                180,
                lambda: (
                    draw_whatsapp_overlays(self.tree, "whatsapp", ICON_SIZE_WHATS),
                    setattr(self, "_whats_overlay_after", None),
                ),
            )
        except Exception:
            # Em último caso, tenta direto (não quebra a UI)
            try:
                draw_whatsapp_overlays(self.tree, "whatsapp", ICON_SIZE_WHATS)
            except Exception:
                pass

    def _refresh_tree(self, term: str | None = None) -> None:
        busca = (term if term is not None else (self.ent_pesq.get() or "")).strip()
        try:
            ordem = self.ord_opcao.get()
        except Exception:
            ordem = "Razão Social (A->Z)"
        log.info("Atualizando lista (busca='%s', ordem='%s')", busca, ordem)

        total = count_clientes(busca)
        self._total = total
        offset = max(0, self._page) * self._page_size
        clientes = search_clientes_paged(busca, ordem, self._page_size, offset)
        # Atualiza label de paginação
        inicio = (self._page * self._page_size) + 1 if total else 0
        fim = min(total, (self._page + 1) * self._page_size)
        getattr(self, 'lbl_page', None) and self.lbl_page.configure(text=f"{inicio}–{fim} de {total}")
        rows = [
            (c.id or 0, c.numero, c.nome, c.razao_social, c.cnpj, c.ultima_alteracao, c.obs)
            for c in clientes
        ]
        self._popular(rows)

    def carregar(self) -> None:
        log.info("Atualizar lista (carregar)")
        self._page = 0  # garante volta p/ página 1
        self._refresh_tree(term="")

    def aplicar_ordenacao(self) -> None:
        log.info("Aplicar (click)")
        self._page = 0  # ao mudar ordenação, volta p/ página 1
        self._refresh_tree()

    def buscar(self) -> None:
        log.info("Buscar (click)")
        termo = (self.ent_pesq.get() or "").strip()
        if not termo:
            self.carregar()
            return
        log.info("Buscar acionado: '%s'", termo)
        self._page = 0  # nova busca → página 1
        self._refresh_tree(term=termo)

    def _get_selected_pks(self) -> list[int]:
        sels = list(self.tree.selection())
        return [int(i) for i in sels] if sels else []

    def editar_cliente(self, event=None) -> None:
        pks = self._get_selected_pks()
        if not pks:
            messagebox.showwarning("Aviso", "Selecione ao menos 1 cliente.", parent=self)
            return
        if len(pks) > 1:
            messagebox.showwarning("Aviso", "Selecione apenas 1 cliente para editar.", parent=self)
            return
        log.info("Editar cliente id=%s", pks[0])
        self._safe_call(app_core.editar_cliente, self, pks[0])

    def abrir_pasta(self) -> None:
        pks = self._get_selected_pks()
        if not pks:
            messagebox.showwarning("Aviso", "Selecione ao menos 1 cliente.", parent=self)
            return
        log.info("Abrir pasta do cliente id=%s", pks[0])
        self._safe_call(app_core.abrir_pasta, self, pks[0])

    def ver_subpastas(self) -> None:
        pks = self._get_selected_pks()
        if not pks:
            messagebox.showwarning("Aviso", "Selecione ao menos 1 cliente.", parent=self)
            return
        log.info("Ver subpastas do cliente id=%s", pks[0])
        self._safe_call(app_core.ver_subpastas, self, pks[0])

    def _abrir_menu_contexto(self, event):
        sel = self.tree.identify_row(event.y)
        if sel:
            self.tree.selection_set(sel)
            try:
                self._menu.tk_popup(event.x_root, event.y_root)
            finally:
                self._menu.grab_release()

    def form_cliente(self, *a, **kw):
        from ui.forms import form_cliente
        return form_cliente(self, *a, **kw)

    def _report_callback_exception(self, exc, val, tb_):
        log.exception("Exceção no Tkinter callback", exc_info=(exc, val, tb_))
        messagebox.showerror("Erro", "Ocorreu um erro inesperado. Veja os logs.", parent=self)

    def _on_refresh(self):
        log.info("Refresh manual (↻)")
        self.carregar()

    # -------- métodos extras --------
    def _open_user_manager(self):
        from tkinter import messagebox
        from core import session
        from ui.users import UserManagerDialog
        user = (session.get_current_user() or "")
        role = "admin" if user.lower() == "admin" else "user"
        if role != "admin":
            messagebox.showwarning("Acesso restrito", "Somente admin pode gerenciar usuários.", parent=self)
            return
        dlg = UserManagerDialog(self, current_role=role)
        self.wait_window(dlg)
        # recompor rodapé ao fechar o diálogo
        self._update_user_status()

    def _show_changelog(self):
        from tkinter import messagebox
        try:
            with open("CHANGELOG.md", "r", encoding="utf-8") as f:
                conteudo = f.read()
            preview = "\n".join(conteudo.splitlines()[:20])
            messagebox.showinfo("Changelog", preview, parent=self)
        except Exception:
            messagebox.showinfo("Changelog", "Arquivo CHANGELOG.md não encontrado.", parent=self)

    def _get_env_text(self) -> str:
        """Extrai só a parte do ambiente (ex.: LOCAL/ONLINE) do status atual."""
        try:
            txt = (self.status_var_text.get() or "")
            base = txt.split(" | Usuário:", 1)[0].strip()
            return base or "LOCAL"
        except Exception:
            return "LOCAL"

    def _merge_status_text(self, env_text: str | None = None):
        """Monta 'ENV | Usuário: nome (role)' preservando o ambiente."""
        if env_text is None:
            env_text = self._get_env_text()
        try:
            from core import session
            user = (session.get_current_user() or "")
            role = "admin" if user.lower() == "admin" else "user"
            self.status_var_text.set(f"{env_text} | Usuário: {user} ({role})" if user else env_text)
        except Exception:
            self.status_var_text.set(env_text if env_text else "LOCAL")

    def _update_user_status(self):
        """Reaplica o sufixo do usuário no rodapé."""
        self._merge_status_text()

    def _schedule_user_status_refresh(self):
        """Tenta atualizar; se login ainda não gravou usuário, tenta de novo em 300ms."""
        self._update_user_status()
        try:
            txt = (self.status_var_text.get() or "")
        except Exception:
            txt = ""
        if "Usuário:" not in txt:
            try:
                self.after(300, self._schedule_user_status_refresh)
            except Exception:
                pass
        # reforça quando a janela volta a ter foco (ex.: após fechar diálogos)
        try:
            self.bind("<FocusIn>", lambda e: self._update_user_status(), add="+")
        except Exception:
            pass

    def _go_prev(self):
        if self._page > 0:
            self._page -= 1
            self._refresh_tree()

    def _go_next(self):
        max_pages = (self._total + self._page_size - 1) // self._page_size
        if self._page + 1 < max_pages:
            self._page += 1
            self._refresh_tree()
