# -*- coding: utf-8 -*-
"""Tela Hub: menu vertical + bloco de notas compartilhado (append-only via Supabase)."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from tkinter import messagebox
from typing import Any, Callable, Dict, List, Optional

import ttkbootstrap as tb

try:
    from src.core.logger import get_logger
except Exception:
    import logging

    def get_logger(name: str | None = None):
        return logging.getLogger(name or __name__)


logger = get_logger(__name__)
log = logger
from src.ui.hub.actions import on_add_note_clicked as actions_on_add_note_clicked
from src.ui.hub.actions import on_show as actions_on_show
from src.ui.hub.authors import _author_display_name, _debug_resolve_author
from src.ui.hub.colors import _ensure_author_tag
from src.ui.hub.constants import MODULES_TITLE, PAD_OUTER
from src.ui.hub.controller import append_note_incremental as controller_append_note_incremental
from src.ui.hub.controller import cancel_poll as controller_cancel_poll
from src.ui.hub.controller import on_realtime_note as controller_on_realtime_note
from src.ui.hub.controller import poll_notes_if_needed as controller_poll_notes_if_needed
from src.ui.hub.controller import refresh_notes_async as controller_refresh_notes_async
from src.ui.hub.controller import retry_after_table_missing as controller_retry_after_table_missing
from src.ui.hub.controller import schedule_poll as controller_schedule_poll
from src.ui.hub.format import _format_note_line, _format_timestamp
from src.ui.hub.layout import apply_hub_notes_right
from src.ui.hub.panels import build_notes_panel
from src.ui.hub.state import HubState
from src.ui.hub.state import ensure_hub_state as ensure_state
from src.ui.hub.utils import (
    _normalize_note,
)

# --- Módulo Fluxo de Caixa (import opcional; não quebra se faltar) ---
_open_cashflow_window = None
try:
    # novo caminho (sem 'src.')
    from features.cashflow.ui import open_cashflow_window as _open_cashflow_window
except Exception as e1:
    try:
        # caminho antigo (com 'src.')
        from src.features.cashflow.ui import open_cashflow_window as _open_cashflow_window
    except Exception as e2:
        _open_cashflow_window = None
        try:
            logger.warning("Fluxo de Caixa indisponível: %s | %s", repr(e1), repr(e2))
        except Exception:
            pass

# Import do erro transitório
# Timezone handling com fallback (mantido para compatibilidade)
try:
    import tzlocal  # type: ignore[import-not-found]

    LOCAL_TZ = tzlocal.get_localzone()
except Exception:
    # Fallback: usa tzinfo do sistema
    try:
        LOCAL_TZ = datetime.now().astimezone().tzinfo
    except Exception:
        LOCAL_TZ = timezone.utc

# logger disponível desde o topo do módulo

# Constantes para retry de autenticação
AUTH_RETRY_MS = 2000  # 2 segundos

# Mapa de e-mail -> nome curto preferido (sempre em minúsculas)
# Cooldown para refresh de nomes (evitar chamadas duplicadas)
_NAMES_REFRESH_COOLDOWN_S = 30


class HubScreen(tb.Frame):
    """
    Hub: menu vertical à esquerda + bloco de notas à direita.
    Sem conteúdo central. Sem painel de login/status (a StatusBar global já existe).
    """

    DEBUG_NOTES = False  # mude pra True se quiser logs

    def _dlog(self, tag, **kw):
        if not getattr(self, "DEBUG_NOTES", self.DEBUG_NOTES):
            return
        try:
            import json
            import time

            line = {"t": int(time.time() * 1000), "tag": tag, **kw}
            logger.info("[HUB] %s", json.dumps(line, ensure_ascii=False))
        except Exception:
            pass

    def __init__(
        self,
        master,
        *,
        open_clientes: Optional[Callable[[], None]] = None,
        open_sifap: Optional[Callable[[], None]] = None,
        open_anvisa: Optional[Callable[[], None]] = None,
        open_auditoria: Optional[Callable[[], None]] = None,
        open_farmacia_popular: Optional[Callable[[], None]] = None,
        open_sngpc: Optional[Callable[[], None]] = None,  # Corrigido: snjpc -> sngpc
        open_senhas: Optional[Callable[[], None]] = None,
        open_mod_sifap: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        # Compatibilidade com kwargs antigos (mantém snjpc para retrocompatibilidade)
        open_clientes = open_clientes or kwargs.pop("on_open_clientes", None) or open_sifap or kwargs.pop("on_open_sifap", None)
        open_anvisa = open_anvisa or kwargs.pop("on_open_anvisa", None)
        open_auditoria = open_auditoria or kwargs.pop("on_open_auditoria", None)
        open_farmacia_popular = open_farmacia_popular or kwargs.pop("on_open_farmacia_popular", None)
        open_sngpc = open_sngpc or kwargs.pop("on_open_sngpc", None) or kwargs.pop("on_open_snjpc", None)
        open_senhas = open_senhas or kwargs.pop("on_open_passwords", None) or kwargs.pop("on_open_senhas", None)
        open_mod_sifap = open_mod_sifap or kwargs.pop("on_open_mod_sifap", None)

        super().__init__(master, padding=0, **kwargs)
        self.AUTH_RETRY_MS = AUTH_RETRY_MS
        s = ensure_state(self)
        s.auth_retry_ms = AUTH_RETRY_MS
        self._hub_state: HubState = s

        # Armazenar callbacks
        self.open_clientes = open_clientes
        self.open_anvisa = open_anvisa
        self.open_auditoria = open_auditoria
        self.open_farmacia_popular = open_farmacia_popular
        self.open_sngpc = open_sngpc  # Corrigido: snjpc -> sngpc
        self.open_senhas = open_senhas
        self.open_mod_sifap = open_mod_sifap

        # --- MENU VERTICAL (coluna 0) ---
        self.modules_panel = tb.Labelframe(self, text=MODULES_TITLE, padding=PAD_OUTER)
        modules_panel = self.modules_panel

        def mk_btn(
            text: str,
            cmd: Optional[Callable] = None,
            highlight: bool = False,
            yellow: bool = False,
        ) -> tb.Button:
            """Cria um botão. Se highlight=True, aplica estilo de sucesso (verde). Se yellow=True, aplica estilo warning (amarelo)."""
            # RC: senhas-yellow-only (escolha de cor)
            if yellow:
                b = tb.Button(
                    modules_panel,
                    text=text,
                    command=(cmd or self._noop),
                    bootstyle="warning",
                )
            elif highlight:
                b = tb.Button(
                    modules_panel,
                    text=text,
                    command=(cmd or self._noop),
                    bootstyle="success",
                )
            else:
                b = tb.Button(
                    modules_panel,
                    text=text,
                    command=(cmd or self._noop),
                    bootstyle="secondary",
                )
            b.pack(fill="x", pady=4)
            return b

        # Ordem e rótulos padronizados (primeira letra maiúscula)
        # Botão "Clientes" destacado em verde
        mk_btn("Clientes", self.open_clientes, highlight=True)
        # RC: senhas-yellow-only (cor amarela no botão Senhas)
        mk_btn("Senhas", self.open_senhas, yellow=True)
        mk_btn("Anvisa", self.open_anvisa)
        mk_btn("Auditoria", self.open_auditoria)
        mk_btn("Farmácia Popular", self.open_farmacia_popular)
        mk_btn("Sngpc", self.open_sngpc)  # Corrigido: SNJPC -> SNGPC (callback)
        mk_btn("Sifap", self.open_mod_sifap)
        # --- Fluxo de Caixa (novo módulo) ---
        if _open_cashflow_window:
            mk_btn("Fluxo de Caixa", lambda: _open_cashflow_window(self), yellow=True)
        else:
            _btn_cf = mk_btn("Fluxo de Caixa", None, yellow=True)
            _btn_cf.configure(state="disabled")

        # --- ESPAÇO CENTRAL VAZIO (coluna 1) ---
        self.center_spacer = tb.Frame(self)

        # --- LATERAL DIREITA (coluna 2) - Notas Compartilhadas ---
        self.notes_panel = build_notes_panel(self, parent=self)

        widgets = {
            "modules_panel": self.modules_panel,
            "spacer": self.center_spacer,
            "notes_panel": self.notes_panel,
        }
        apply_hub_notes_right(self, widgets)

        # Estado de polling
        self._notes_poll_ms = 10000  # 10 segundos
        self._notes_last_snapshot: Optional[List[tuple]] = None  # snapshot (id, ts) para detectar mudanças
        self._notes_last_data: Optional[List[Dict[str, Any]]] = None  # dados completos normalizados
        self._polling_active = False
        self._notes_after_handle = None
        self._clients_after_handle = None

        # Estado de erro de tabela ausente
        self._notes_table_missing = False
        self._notes_table_missing_notified = False
        self._notes_retry_ms = 60000  # 60 segundos antes de tentar novamente

        # Cache de nomes de autores (email lowercase -> display_name)
        self._author_names_cache: Dict[str, str] = {}
        self._email_prefix_map: Dict[str, str] = {}  # {prefixo: email_completo} para notas legadas
        self._names_cache_loaded = False
        self._names_refreshing = False
        self._names_last_refresh = 0.0
        self._last_org_for_names: Optional[str] = None
        self._pending_name_fetch: set = set()  # controle de fetch on-demand
        # Debounce de re-render
        self._last_names_cache_hash = None  # md5 do cache de nomes
        self._last_render_hash = None  # md5 do conteúdo renderizado
        self._names_cache_loading = False  # trava anti reentrância

        # Live sync
        self._live_channel = None
        self._live_org_id = None
        self._live_sync_on = False
        self._live_last_ts = None  # ISO da última nota conhecida

        # Configurar atalhos (apenas uma vez)
        self._binds_ready = getattr(self, "_binds_ready", False)
        if not self._binds_ready:
            # Ctrl+D para diagnóstico
            self.bind_all("<Control-d>", self._show_debug_info)
            self.bind_all("<Control-D>", self._show_debug_info)

            # Ctrl+L para recarregar cache de nomes (teste)
            self.bind_all(
                "<Control-l>",
                lambda e: self._refresh_author_names_cache_async(force=True),
            )
            self.bind_all(
                "<Control-L>",
                lambda e: self._refresh_author_names_cache_async(force=True),
            )
            self._binds_ready = True

        # Iniciar timers com gate de autenticação
        self.after(500, self._start_home_timers_safely)

    # -------------------- Helpers de Autenticação Segura --------------------

    def _auth_ready(self) -> bool:
        """Verifica se autenticação está pronta (sem levantar exceção)."""
        try:
            app = self._get_app()
            return app and hasattr(app, "auth") and app.auth and app.auth.is_authenticated
        except Exception:
            return False

    def _get_org_id_safe(self) -> Optional[str]:
        """Obtém org_id de forma segura (sem exceção)."""
        try:
            app = self._get_app()
            if not app or not hasattr(app, "auth") or not app.auth:
                return None

            # Tentar via accessor seguro
            org_id = app.auth.get_org_id()
            if org_id:
                return org_id

            # Fallback: usar método antigo se disponível
            if hasattr(app, "_get_org_id_cached"):
                user_id = app.auth.get_user_id()
                if user_id:
                    return app._get_org_id_cached(user_id)

            return None
        except Exception as e:
            log.debug("Não foi possível obter org_id: %s", e)
            return None

    def _get_email_safe(self) -> Optional[str]:
        """Obtém email de forma segura (sem exceção)."""
        try:
            app = self._get_app()
            if not app or not hasattr(app, "auth") or not app.auth:
                return None
            return app.auth.get_email()
        except Exception as e:
            log.debug("Não foi possível obter email: %s", e)
            return None

    def _get_user_id_safe(self) -> Optional[str]:
        """Obtém user_id de forma segura (sem exceção)."""
        try:
            app = self._get_app()
            if not app or not hasattr(app, "auth") or not app.auth:
                return None
            return app.auth.get_user_id()
        except Exception as e:
            log.debug("Não foi possível obter user_id: %s", e)
            return None

    def _start_home_timers_safely(self) -> None:
        """Inicia timers apenas quando autenticação estiver pronta."""
        if not self._auth_ready():
            log.debug("HubScreen: Autenticação ainda não pronta, aguardando...")
            self.after(AUTH_RETRY_MS, self._start_home_timers_safely)
            return

        log.debug("HubScreen: Autenticação pronta, iniciando timers.")

        # Forçar recarga do cache de nomes ao trocar de conta/login
        self._names_cache_loaded = False
        self._author_names_cache = {}
        self._email_prefix_map = {}  # limpar mapa de prefixos também
        self._last_org_for_names = None  # força recarga mesmo se org for igual

        self._update_notes_ui_state()  # Atualizar estado do botão/placeholder
        self._start_notes_polling()

    def _update_notes_ui_state(self) -> None:
        """Atualiza estado do botão e placeholder baseado em org_id."""
        org_id = self._get_org_id_safe()

        if org_id:
            # Sessão válida - habilitar botão
            self.btn_add_note.configure(state="normal")
            self.new_note.delete("1.0", "end")
            # Sem placeholder (widget Text não tem atributo 'placeholder')
        else:
            # Sessão sem organização - desabilitar botão
            self.btn_add_note.configure(state="disabled")
            # Mostrar mensagem no campo de texto
            self.new_note.delete("1.0", "end")
            self.new_note.insert("1.0", "Sessão sem organização. Faça login novamente.")
            self.new_note.configure(state="disabled")

    # -------------------- Polling e Cache --------------------

    def _start_notes_polling(self) -> None:
        """Inicia o polling de atualizações de notas."""
        if not self._polling_active:
            self._polling_active = True
            # Carregar cache de nomes na primeira vez
            self._refresh_author_names_cache_async(force=True)
            self.refresh_notes_async(force=True)

    def _refresh_author_names_cache_async(self, force: bool = False) -> None:
        """
        Atualiza cache de nomes de autores (profiles.display_name) de forma assíncrona.

        Args:
            force: Se True, ignora cooldown e força atualização
        """
        # Evitar reentrância (exceto se force=True)
        if getattr(self, "_names_cache_loading", False) and not force:
            return
        self._names_cache_loading = True

        # Evitar chamadas duplicadas
        if self._names_refreshing:
            self._names_cache_loading = False
            return

        # Cooldown de 30 segundos (exceto se force=True)
        now = time.time()
        if not force and (now - self._names_last_refresh) < _NAMES_REFRESH_COOLDOWN_S:
            self._names_cache_loading = False
            return

        org_id = self._get_org_id_safe()
        if not org_id:
            self._names_cache_loading = False
            return

        # Se organização mudou, invalidar cache
        if self._last_org_for_names and self._last_org_for_names != org_id:
            self._author_names_cache = {}
            self._email_prefix_map = {}  # invalidar mapa de prefixos também
            self._names_cache_loaded = False
            log.info("Cache de nomes invalidado (mudança de organização)")

        self._names_refreshing = True

        def _work():
            mapping = {}
            prefix_map = {}
            try:
                from src.core.services.profiles_service import (
                    get_display_names_map,
                    get_email_prefix_map,
                )

                mapping = get_display_names_map(org_id)
                prefix_map = get_email_prefix_map(org_id)
            except Exception as e:
                log.debug("Erro ao carregar nomes de autores: %s", e)

            def _ui():
                try:
                    old_hash = getattr(self, "_last_names_cache_hash", None)
                    self._author_names_cache = mapping or {}
                    self._email_prefix_map = prefix_map or {}

                    import hashlib
                    import json

                    cache_json = json.dumps(self._author_names_cache, sort_keys=True, ensure_ascii=False)
                    new_hash = hashlib.md5(cache_json.encode("utf-8")).hexdigest()
                    self._last_names_cache_hash = new_hash
                    self._names_cache_loaded = True

                    self._names_refreshing = False
                    self._names_last_refresh = time.time()
                    self._last_org_for_names = org_id
                    log.debug(
                        "Cache de nomes carregado: %d entradas",
                        len(self._author_names_cache),
                    )
                    log.debug(
                        "Mapa de prefixos carregado: %d entradas",
                        len(self._email_prefix_map),
                    )

                    if new_hash != old_hash:
                        # força um único re-render
                        self._last_render_hash = None
                        if getattr(self, "_notes_last_data", None):
                            self.render_notes(self._notes_last_data)
                        elif getattr(self, "_notes_last_snapshot", None):
                            self.render_notes(self._notes_last_snapshot)
                finally:
                    self._names_cache_loading = False

            try:
                self.after(0, _ui)
            except Exception:
                self._names_cache_loading = False

        threading.Thread(target=_work, daemon=True).start()

    # -------------------- Live Sync de Notas em Tempo Real --------------------

    def _start_live_sync(self):
        """Inicia sync de notas da org atual: Realtime + fallback polling."""
        if self._live_sync_on:
            return
        org_id = self._get_org_id_safe()
        if not org_id:
            return
        self._live_org_id = org_id
        self._live_sync_on = True

        # 1) marcar timestamp da última nota já renderizada (para polling)
        try:
            notes = getattr(self, "_notes_last_data", None) or []
            if notes:
                self._live_last_ts = max((n.get("created_at") or "") for n in notes)
        except Exception:
            self._live_last_ts = None

        # 2) tentar Realtime
        try:
            # [finalize-notes] import seguro dentro de função
            from infra.supabase_client import get_supabase  # usar cliente existente

            client = get_supabase()
            channel_name = f"rc_notes_org_{org_id}"
            ch = client.realtime.channel(channel_name)

            # INSERTs da organização atual
            ch.on(
                "postgres_changes",
                {
                    "event": "INSERT",
                    "schema": "public",
                    "table": "rc_notes",
                    "filter": f"org_id=eq.{org_id}",
                },
                lambda payload: self._on_realtime_note(payload.get("new") or {}),
            )

            ch.subscribe()
            self._live_channel = ch
        except Exception:
            self._live_channel = None

        # 3) fallback por polling a cada 6s
        self._schedule_poll()

    def _stop_live_sync(self):
        """Para sync (sair do Hub, logout)."""
        self._live_sync_on = False
        self._live_org_id = None
        try:
            if self._live_channel:
                self._live_channel.unsubscribe()
        except Exception:
            pass
        self._live_channel = None
        controller_cancel_poll(self)

    def on_show(self):
        actions_on_show(self)

    def _schedule_poll(self, delay_ms: int = 6000):
        controller_schedule_poll(self, delay_ms)

    def _poll_notes_if_needed(self):
        controller_poll_notes_if_needed(self)

    def _on_realtime_note(self, row: dict):
        controller_on_realtime_note(self, row)

    def _append_note_incremental(self, row: dict):
        controller_append_note_incremental(self, row)

    # -------------------- Utilitários de Nome e Cor --------------------

    def _collect_notes_debug(self) -> dict:
        """
        Coleta informações de debug sobre notas e resolução de autores.
        """
        notes = getattr(self, "_notes_last_data", None) or getattr(self, "_notes_last_snapshot", None) or []
        out = {
            "org_id": (self._get_org_id_safe() if hasattr(self, "_get_org_id_safe") else None),
            "current_user": (getattr(self, "_current_user_email", None) or self._get_email_safe() if hasattr(self, "_get_email_safe") else ""),
            "names_cache_size": len(getattr(self, "_author_names_cache", {}) or {}),
            "prefix_map_size": len(getattr(self, "_email_prefix_map", {}) or {}),
            "names_cache": dict(getattr(self, "_author_names_cache", {}) or {}),
            "prefix_map": dict(getattr(self, "_email_prefix_map", {}) or {}),
            "samples": [],
        }

        # normaliza entrada (se for tupla/lista)
        def _author_of(n):
            if isinstance(n, dict):
                return n.get("author_email") or n.get("author") or n.get("email") or ""
            if isinstance(n, (tuple, list)):
                if len(n) >= 2:  # (ts, author, body) ou (author, body)
                    return str(n[1])
                if len(n) == 1:
                    return str(n[0])
            return str(n)

        for n in list(notes)[:20]:
            out["samples"].append(_debug_resolve_author(self, _author_of(n)))
        return out

    # -------------------- Fim DEBUG --------------------

    # -------------------- Formatação e Renderização --------------------

    def render_notes(self, notes: List[Dict[str, Any]], force: bool = False) -> None:
        """Renderiza lista de notas no histórico com nomes coloridos e timezone local.

        Args:
            notes: Lista de dicionários com dados das notas
            force: Se True, ignora cache de hash e força re-renderização
        """
        # Verificação defensiva: garantir que cache de tags existe
        s = ensure_state(self)
        author_tags = s.author_tags
        if author_tags is None:
            s.author_tags = {}
            author_tags = s.author_tags

        # Normalizar entrada: converter tuplas/listas para dicts
        notes = [_normalize_note(x) for x in (notes or [])]

        # NÃO apaga se vier vazio/None (evita 'branco' e piscas)
        if not notes:
            self._dlog("render_skip_empty")
            return

        # Hash de conteúdo pra evitar re-render desnecessário
        sig_items = []
        for n in notes:
            em = (n.get("author_email") or "").strip().lower()
            ts = n.get("created_at") or ""
            ln = len((n.get("body") or ""))
            # se existir author_name já no dado, inclua na assinatura
            nm = n.get("author_name") or ""
            sig_items.append((em, ts, ln, nm))

        import hashlib
        import json

        render_hash = hashlib.md5(json.dumps(sig_items, ensure_ascii=False).encode("utf-8")).hexdigest()

        # Se não forçado, verificar se hash é igual (skip re-render)
        if not force:
            if render_hash == getattr(self, "_last_render_hash", None):
                self._dlog("render_skip_samehash")
                return

        self._last_render_hash = render_hash

        try:
            self.notes_history.configure(state="normal")
            self.notes_history.delete("1.0", "end")

            for n in notes:
                email = (n.get("author_email") or "").strip().lower()
                name = (n.get("author_name") or "").strip()

                if not name:
                    # usar cache → mapa local → fetch → placeholder
                    name = _author_display_name(self, email)

                # Aplicar tag de cor com fallback defensivo
                tag = None
                try:
                    tag = _ensure_author_tag(self.notes_history, email, author_tags)
                except Exception:
                    logger.exception("Hub: falha ao aplicar estilo/tag do autor; renderizando sem cor.")
                    tag = None  # segue sem tag

                created_at = n.get("created_at")
                ts = _format_timestamp(created_at)
                body = (n.get("body") or "").rstrip("\n")

                # Inserir: [data] <nome colorido>: corpo
                if tag:
                    self.notes_history.insert("end", f"[{ts}] ")
                    self.notes_history.insert("end", name, (tag,))
                    self.notes_history.insert("end", f": {body}\n")
                else:
                    line = _format_note_line(created_at, name or email, body)
                    self.notes_history.insert("end", f"{line}\n")

            self.notes_history.configure(state="disabled")
            # Scrollar para o fim (mais recente)
            self.notes_history.see("end")
            self.notes_history.see("end")
        except Exception:
            logger.exception("Hub: erro crítico ao renderizar lista de notas.")
            try:
                self.notes_history.configure(state="disabled")
            except Exception:
                pass

    def refresh_notes_async(self, force: bool = False) -> None:
        controller_refresh_notes_async(self, force)

    def _retry_after_table_missing(self) -> None:
        controller_retry_after_table_missing(self)

    def _on_add_note_clicked(self) -> None:
        actions_on_add_note_clicked(self)

    def _get_app(self):
        """Obtém referência para a janela principal (App)."""
        try:
            # Subir na hierarquia até encontrar a janela raiz
            widget = self.master
            while widget:
                if hasattr(widget, "auth") or hasattr(widget, "_org_id_cache"):
                    return widget
                widget = getattr(widget, "master", None)
        except Exception:
            pass
        return None

    def _is_online(self, app) -> bool:
        """Verifica se está online."""
        try:
            if hasattr(app, "_net_is_online"):
                return bool(app._net_is_online)
        except Exception:
            pass
        return True  # Assume online se não conseguir verificar

    def stop_polling(self) -> None:
        """Para o polling de notas e cancela timers pendentes."""
        self._polling_active = False

        # Cancelar timers pendentes
        if self._notes_after_handle:
            try:
                self.after_cancel(self._notes_after_handle)
            except Exception:
                pass
            self._notes_after_handle = None

        if self._clients_after_handle:
            try:
                self.after_cancel(self._clients_after_handle)
            except Exception:
                pass
            self._clients_after_handle = None

        controller_cancel_poll(self)

    @property
    def state(self) -> HubState:
        """Read-only access to the HubState container."""
        if not isinstance(getattr(self, "_hub_state", None), HubState):
            self._hub_state = ensure_state(self)
        return self._hub_state

    @property
    def _author_tags(self):
        s = ensure_state(self)
        if s.author_tags is None:
            s.author_tags = {}
        return s.author_tags

    @_author_tags.setter
    def _author_tags(self, value):
        s = ensure_state(self)
        s.author_tags = value or {}

    @property
    def _poll_job(self):
        return ensure_state(self).poll_job

    @_poll_job.setter
    def _poll_job(self, value):
        ensure_state(self).poll_job = value

    @property
    def _is_refreshing(self):
        return ensure_state(self).is_refreshing

    @_is_refreshing.setter
    def _is_refreshing(self, value):
        ensure_state(self).is_refreshing = bool(value)

    def hub_state(self) -> HubState:
        """Convenience accessor for the HubState container."""
        return self.state

    def destroy(self) -> None:
        """Override destroy para parar polling."""
        self.stop_polling()
        super().destroy()

    def _noop(self) -> None:
        """Placeholder para botões sem ação."""
        pass

    def _show_debug_info(self, event=None) -> None:
        """Gera relatório JSON de diagnóstico (atalho Ctrl+D)."""
        import json
        import os
        from datetime import datetime

        try:
            # Coleta informações de debug
            debug_data = self._collect_notes_debug()

            # Gera nome do arquivo com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_notes_report_{timestamp}.json"

            # Salva no diretório de trabalho
            filepath = os.path.abspath(filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)

            # Mostra mensagem com o caminho do arquivo
            messagebox.showinfo(
                "Relatório de Debug Gerado",
                f"Relatório salvo em:\n{filepath}",
                parent=self,
            )

            # Imprime no console como backup
            logger.info("\n=== DEBUG NOTES REPORT ===")
            logger.info(json.dumps(debug_data, ensure_ascii=False, indent=2))
            logger.info("=== Salvo em: %s ===\n", filepath)

        except Exception as e:
            log.error("Erro ao gerar relatório de debug: %s", e)
            messagebox.showerror("Erro", f"Erro ao gerar relatório: {e}", parent=self)
