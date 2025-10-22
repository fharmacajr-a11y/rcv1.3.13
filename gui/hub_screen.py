# -*- coding: utf-8 -*-
"""Tela Hub: menu vertical + bloco de notas compartilhado (append-only via Supabase)."""

from __future__ import annotations

import tkinter as tk
import threading
import hashlib
import re
import time
from datetime import datetime, timezone
from typing import Callable, Optional, List, Dict, Any
from tkinter import messagebox

import ttkbootstrap as tb

from core.logger import get_logger
from ui.hub.constants import PAD_OUTER
from ui.hub.layout import apply_hub_notes_right
from gui.hub.utils import (
    _hsl_to_hex,
    _hash_dict,
    _normalize_note,
    _to_local_str,
    _format_note_line,
)
from gui.hub.colors import _author_color, _ensure_author_tag
from gui.hub.authors import _author_display_name, _debug_resolve_author

# Import do erro transitÃ³rio
from core.services.notes_service import NotesTransientError

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

logger = get_logger(__name__)
log = logger

# Constantes para retry de autenticaÃ§Ã£o
AUTH_RETRY_MS = 2000  # 2 segundos

# Mapa de e-mail -> nome curto preferido (sempre em minÃºsculas)
# Cooldown para refresh de nomes (evitar chamadas duplicadas)
_NAMES_REFRESH_COOLDOWN_S = 30


class HubScreen(tb.Frame):
    """
    Hub: menu vertical Ã  esquerda + bloco de notas Ã  direita.
    Sem conteÃºdo central. Sem painel de login/status (a StatusBar global jÃ¡ existe).
    """

    DEBUG_NOTES = False  # mude pra True se quiser logs

    def _dlog(self, tag, **kw):
        if not getattr(self, "DEBUG_NOTES", self.DEBUG_NOTES):
            return
        try:
            import json, time
            line = {"t": int(time.time()*1000), "tag": tag, **kw}
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
        # Compatibilidade com kwargs antigos (mantÃ©m snjpc para retrocompatibilidade)
        open_clientes = open_clientes or kwargs.pop("on_open_clientes", None) or open_sifap or kwargs.pop("on_open_sifap", None)
        open_anvisa = open_anvisa or kwargs.pop("on_open_anvisa", None)
        open_auditoria = open_auditoria or kwargs.pop("on_open_auditoria", None)
        open_farmacia_popular = open_farmacia_popular or kwargs.pop("on_open_farmacia_popular", None)
        open_sngpc = open_sngpc or kwargs.pop("on_open_sngpc", None) or kwargs.pop("on_open_snjpc", None)
        open_senhas = open_senhas or kwargs.pop("on_open_passwords", None) or kwargs.pop("on_open_senhas", None)
        open_mod_sifap = open_mod_sifap or kwargs.pop("on_open_mod_sifap", None)

        super().__init__(master, padding=0, **kwargs)

        # Armazenar callbacks
        self.open_clientes = open_clientes
        self.open_anvisa = open_anvisa
        self.open_auditoria = open_auditoria
        self.open_farmacia_popular = open_farmacia_popular
        self.open_sngpc = open_sngpc  # Corrigido: snjpc -> sngpc
        self.open_senhas = open_senhas
        self.open_mod_sifap = open_mod_sifap

        # --- MENU VERTICAL (coluna 0) ---
        self.modules_panel = tb.Labelframe(self, text="MÃ³dulos", padding=PAD_OUTER)
        modules_panel = self.modules_panel

        def mk_btn(text: str, cmd: Optional[Callable] = None, highlight: bool = False) -> tb.Button:
            """Cria um botÃ£o. Se highlight=True, aplica estilo de sucesso (verde)."""
            if highlight:
                b = tb.Button(modules_panel, text=text, command=(cmd or self._noop), bootstyle="success")
            else:
                b = tb.Button(modules_panel, text=text, command=(cmd or self._noop), bootstyle="secondary")
            b.pack(fill="x", pady=4)
            return b

        # Ordem e rÃ³tulos padronizados (primeira letra maiÃºscula)
        # BotÃ£o "Clientes" destacado em verde
        mk_btn("Clientes", self.open_clientes, highlight=True)
        mk_btn("Senhas", self.open_senhas)
        mk_btn("Anvisa", self.open_anvisa)
        mk_btn("Auditoria", self.open_auditoria)
        mk_btn("FarmÃ¡cia Popular", self.open_farmacia_popular)
        mk_btn("Sngpc", self.open_sngpc)  # Corrigido: SNJPC -> SNGPC (callback)
        mk_btn("Sifap", self.open_mod_sifap)

        # --- ESPAÃ‡O CENTRAL VAZIO (coluna 1) ---
        self.center_spacer = tb.Frame(self)

        # --- LATERAL DIREITA (coluna 2) - Notas Compartilhadas ---
        self._build_notes_panel()

        widgets = {
            "modules_panel": self.modules_panel,
            "spacer": self.center_spacer,
            "notes_panel": self.notes_panel,
        }
        apply_hub_notes_right(self, widgets)

        # Estado de polling
        self._notes_poll_ms = 10000  # 10 segundos
        self._notes_last_snapshot: Optional[List[tuple]] = None  # snapshot (id, ts) para detectar mudanÃ§as
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
        
        # Cache de tags de autor (email lowercase -> nome_da_tag)
        self._author_tags: Dict[str, str] = {}
        
        # Debounce de re-render
        self._last_names_cache_hash = None  # md5 do cache de nomes
        self._last_render_hash = None       # md5 do conteÃºdo renderizado
        self._names_cache_loading = False   # trava anti reentrÃ¢ncia

        # Live sync
        self._live_channel = None
        self._live_org_id = None
        self._live_sync_on = False
        self._live_last_ts = None  # ISO da Ãºltima nota conhecida
        self._live_poll_job = None

        # Configurar atalhos (apenas uma vez)
        self._binds_ready = getattr(self, "_binds_ready", False)
        if not self._binds_ready:
            # Ctrl+D para diagnÃ³stico
            self.bind_all("<Control-d>", self._show_debug_info)
            self.bind_all("<Control-D>", self._show_debug_info)
            
            # Ctrl+L para recarregar cache de nomes (teste)
            self.bind_all("<Control-l>", lambda e: self._refresh_author_names_cache_async(force=True))
            self.bind_all("<Control-L>", lambda e: self._refresh_author_names_cache_async(force=True))
            self._binds_ready = True

        # Iniciar timers com gate de autenticaÃ§Ã£o
        self.after(500, self._start_home_timers_safely)

    # -------------------- Helpers de AutenticaÃ§Ã£o Segura --------------------
    
    def _auth_ready(self) -> bool:
        """Verifica se autenticaÃ§Ã£o estÃ¡ pronta (sem levantar exceÃ§Ã£o)."""
        try:
            app = self._get_app()
            return app and hasattr(app, "auth") and app.auth and app.auth.is_authenticated
        except Exception:
            return False

    def _get_org_id_safe(self) -> Optional[str]:
        """ObtÃ©m org_id de forma segura (sem exceÃ§Ã£o)."""
        try:
            app = self._get_app()
            if not app or not hasattr(app, "auth") or not app.auth:
                return None
            
            # Tentar via accessor seguro
            org_id = app.auth.get_org_id()
            if org_id:
                return org_id
            
            # Fallback: usar mÃ©todo antigo se disponÃ­vel
            if hasattr(app, "_get_org_id_cached"):
                user_id = app.auth.get_user_id()
                if user_id:
                    return app._get_org_id_cached(user_id)
            
            return None
        except Exception as e:
            log.debug("NÃ£o foi possÃ­vel obter org_id: %s", e)
            return None

    def _get_email_safe(self) -> Optional[str]:
        """ObtÃ©m email de forma segura (sem exceÃ§Ã£o)."""
        try:
            app = self._get_app()
            if not app or not hasattr(app, "auth") or not app.auth:
                return None
            return app.auth.get_email()
        except Exception as e:
            log.debug("NÃ£o foi possÃ­vel obter email: %s", e)
            return None

    def _get_user_id_safe(self) -> Optional[str]:
        """ObtÃ©m user_id de forma segura (sem exceÃ§Ã£o)."""
        try:
            app = self._get_app()
            if not app or not hasattr(app, "auth") or not app.auth:
                return None
            return app.auth.get_user_id()
        except Exception as e:
            log.debug("NÃ£o foi possÃ­vel obter user_id: %s", e)
            return None

    def _start_home_timers_safely(self) -> None:
        """Inicia timers apenas quando autenticaÃ§Ã£o estiver pronta."""
        if not self._auth_ready():
            log.debug("HubScreen: AutenticaÃ§Ã£o ainda nÃ£o pronta, aguardando...")
            self.after(AUTH_RETRY_MS, self._start_home_timers_safely)
            return
        
        log.debug("HubScreen: AutenticaÃ§Ã£o pronta, iniciando timers.")
        
        # ForÃ§ar recarga do cache de nomes ao trocar de conta/login
        self._names_cache_loaded = False
        self._author_names_cache = {}
        self._email_prefix_map = {}  # limpar mapa de prefixos tambÃ©m
        self._last_org_for_names = None  # forÃ§a recarga mesmo se org for igual
        
        self._update_notes_ui_state()  # Atualizar estado do botÃ£o/placeholder
        self._start_notes_polling()

    def _update_notes_ui_state(self) -> None:
        """Atualiza estado do botÃ£o e placeholder baseado em org_id."""
        org_id = self._get_org_id_safe()
        
        if org_id:
            # SessÃ£o vÃ¡lida - habilitar botÃ£o
            self.btn_add_note.configure(state="normal")
            self.new_note.delete("1.0", "end")
            # Sem placeholder (widget Text nÃ£o tem atributo 'placeholder')
        else:
            # SessÃ£o sem organizaÃ§Ã£o - desabilitar botÃ£o
            self.btn_add_note.configure(state="disabled")
            # Mostrar mensagem no campo de texto
            self.new_note.delete("1.0", "end")
            self.new_note.insert("1.0", "SessÃ£o sem organizaÃ§Ã£o. FaÃ§a login novamente.")
            self.new_note.configure(state="disabled")

    def _build_notes_panel(self) -> None:
        """ConstrÃ³i o painel de notas compartilhadas (append-only)."""
        # Reset do cache de tags (widget sendo recriado)
        self._author_tags = {}
        
        self.notes_panel = tb.Labelframe(self, text="AnotaÃ§Ãµes Compartilhadas", padding=PAD_OUTER)
        right = self.notes_panel
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)  # histÃ³rico expande

        # --- HistÃ³rico (somente leitura) ---
        history_frame = tb.Frame(right)
        history_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        self.notes_history = tk.Text(
            history_frame, 
            width=48, 
            height=20, 
            wrap="word",
            state="disabled"  # somente leitura
        )
        self.notes_history.grid(row=0, column=0, sticky="nsew")
        
        sb = tb.Scrollbar(history_frame, command=self.notes_history.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.notes_history.configure(yscrollcommand=sb.set)

        # --- Entrada nova anotaÃ§Ã£o ---
        entry_frame = tb.Frame(right)
        entry_frame.grid(row=1, column=0, sticky="ew", pady=(0, 0))
        entry_frame.columnconfigure(0, weight=1)

        tb.Label(entry_frame, text="Nova anotaÃ§Ã£o:", font=("", 9)).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )

        self.new_note = tk.Text(entry_frame, height=3, wrap="word")
        self.new_note.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        self.btn_add_note = tb.Button(
            entry_frame, 
            text="Adicionar", 
            command=self._on_add_note_clicked,
            bootstyle="primary"
        )
        self.btn_add_note.grid(row=2, column=0, sticky="e")

    # -------------------- Polling e Cache --------------------

    def _start_notes_polling(self) -> None:
        """Inicia o polling de atualizaÃ§Ãµes de notas."""
        if not self._polling_active:
            self._polling_active = True
            # Carregar cache de nomes na primeira vez
            self._refresh_author_names_cache_async(force=True)
            self.refresh_notes_async(force=True)

    def _refresh_author_names_cache_async(self, force: bool = False) -> None:
        """
        Atualiza cache de nomes de autores (profiles.display_name) de forma assÃ­ncrona.
        
        Args:
            force: Se True, ignora cooldown e forÃ§a atualizaÃ§Ã£o
        """
        # Evitar reentrÃ¢ncia (exceto se force=True)
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
        
        # Se organizaÃ§Ã£o mudou, invalidar cache
        if self._last_org_for_names and self._last_org_for_names != org_id:
            self._author_names_cache = {}
            self._email_prefix_map = {}  # invalidar mapa de prefixos tambÃ©m
            self._names_cache_loaded = False
            log.info("Cache de nomes invalidado (mudanÃ§a de organizaÃ§Ã£o)")
        
        self._names_refreshing = True
        
        def _work():
            mapping = {}
            prefix_map = {}
            try:
                from core.services.profiles_service import get_display_names_map, get_email_prefix_map
                mapping = get_display_names_map(org_id)
                prefix_map = get_email_prefix_map(org_id)
            except Exception as e:
                log.debug("Erro ao carregar nomes de autores: %s", e)
            
            def _ui():
                try:
                    old_hash = getattr(self, "_last_names_cache_hash", None)
                    self._author_names_cache = mapping or {}
                    self._email_prefix_map = prefix_map or {}

                    import hashlib, json
                    new_hash = hashlib.md5(json.dumps(self._author_names_cache, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
                    self._last_names_cache_hash = new_hash
                    self._names_cache_loaded = True
                    
                    self._names_refreshing = False
                    self._names_last_refresh = time.time()
                    self._last_org_for_names = org_id
                    log.debug("Cache de nomes carregado: %d entradas", len(self._author_names_cache))
                    log.debug("Mapa de prefixos carregado: %d entradas", len(self._email_prefix_map))

                    if new_hash != old_hash:
                        # forÃ§a um Ãºnico re-render
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

        # 1) marcar timestamp da Ãºltima nota jÃ¡ renderizada (para polling)
        try:
            notes = getattr(self, "_notes_last_data", None) or []
            if notes:
                self._live_last_ts = max((n.get("created_at") or "") for n in notes)
        except Exception:
            self._live_last_ts = None

        # 2) tentar Realtime
        try:
            # [finalize-notes] import seguro dentro de funÃ§Ã£o
            from infra.supabase_client import get_supabase  # usar cliente existente
            client = get_supabase()
            channel_name = f"rc_notes_org_{org_id}"
            ch = client.realtime.channel(channel_name)

            # INSERTs da organizaÃ§Ã£o atual
            ch.on(
                "postgres_changes",
                {"event": "INSERT", "schema": "public", "table": "rc_notes", "filter": f"org_id=eq.{org_id}"},
                lambda payload: self._on_realtime_note(payload.get("new") or {})
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
        if self._live_poll_job:
            try:
                self.after_cancel(self._live_poll_job)
            except Exception:
                pass
            self._live_poll_job = None

    def on_show(self):
        """
        Chamado sempre que a tela do Hub fica visÃ­vel (navegaÃ§Ã£o de volta).
        Garante renderizaÃ§Ã£o imediata dos dados em cache e mantÃ©m live-sync ativo.
        """
        # 1) Iniciar live-sync caso ainda nÃ£o esteja (idempotente)
        try:
            self._start_live_sync()
        except Exception as e:
            log.warning("Erro ao iniciar live-sync no on_show: %s", e)

        # 2) Se a Text estÃ¡ vazia mas jÃ¡ temos dados em memÃ³ria, renderizar JÃ
        try:
            is_empty = (self.notes_history.index("end-1c") == "1.0")
        except Exception:
            is_empty = True

        if is_empty and getattr(self, "_notes_last_data", None):
            # Render forÃ§ado ignora o hash para nÃ£o 'pular'
            try:
                self.render_notes(self._notes_last_data, force=True)
            except Exception as e:
                log.warning("Erro ao renderizar notas no on_show: %s", e)
        
        # 3) ForÃ§ar recarga do cache de nomes (garante nomes atualizados)
        try:
            self._author_names_cache = {}
            self._email_prefix_map = {}
            self._names_cache_loaded = False
            self._last_org_for_names = None
            self._refresh_author_names_cache_async(force=True)
        except Exception as e:
            log.warning("Erro ao atualizar cache de nomes no on_show: %s", e)

    def _schedule_poll(self, delay_ms: int = 6000):
        if not self._live_sync_on:
            return
        try:
            if self._live_poll_job:
                self.after_cancel(self._live_poll_job)
        except Exception:
            pass
        self._live_poll_job = self.after(delay_ms, self._poll_notes_if_needed)

    def _poll_notes_if_needed(self):
        """Se Realtime nÃ£o chegou, busca apenas notas novas (desde _live_last_ts)."""
        if not self._live_sync_on:
            return
        try:
            from core.services.notes_service import list_notes_since
            org_id = self._live_org_id
            since = self._live_last_ts
            new_notes = list_notes_since(org_id, since)  # implemente no service (abaixo)
            if new_notes:
                for n in new_notes:
                    self._append_note_incremental(n)
                # atualizar last_ts
                try:
                    self._live_last_ts = max([self._live_last_ts or "", *[n.get("created_at") or "" for n in new_notes]])
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self._schedule_poll()

    def _on_realtime_note(self, row: dict):
        """Callback do Realtime (executa fora da thread UI)"""
        try:
            self.after(0, lambda: self._append_note_incremental(row))
        except Exception:
            pass

    def _append_note_incremental(self, row: dict):
        """Adiciona UMA nota nova sem repintar tudo, sem limpar a tela."""
        # normalizar
        if not hasattr(self, "_normalize_note"):
            # se nÃ£o existir, faÃ§a um normalize mÃ­nimo:
            def _normalize_note(n):
                em = (n.get("author_email") or "").strip().lower()
                return {
                    "id": n.get("id"),
                    "created_at": n.get("created_at") or n.get("ts") or "",
                    "author_email": em,
                    "author_name": (n.get("author_name") or "").strip(),
                    "body": (n.get("body") or ""),
                }
            note = _normalize_note(row)
        else:
            note = _normalize_note(row)

        # se jÃ¡ temos essa nota na memÃ³ria, ignore
        notes = getattr(self, "_notes_last_data", None) or []
        if any(str(n.get("id")) == str(note.get("id")) for n in notes if n.get("id") is not None):
            return

        # append em memÃ³ria
        notes = notes + [note]
        self._notes_last_data = notes
        try:
            # manter snapshot de comparaÃ§Ã£o simples (id+ts)
            self._notes_last_snapshot = [(n.get("id"), n.get("created_at")) for n in notes]
        except Exception:
            pass

        # atualizar last_ts do live
        ts = note.get("created_at") or ""
        if ts and (self._live_last_ts or "") < ts:
            self._live_last_ts = ts

        # inserir na UI sem apagar a Text
        try:
            self.notes_history.configure(state="normal")
            
            email = (note.get("author_email") or "").strip().lower()
            name  = (note.get("author_name") or "").strip()
            if not name:
                name = _author_display_name(self, email)  # usa cache â†’ fetch de fundo

            ts_local = _to_local_str(note.get("created_at"))
            body = (note.get("body") or "").rstrip("\n")
            
            # Aplicar tag de cor com fallback defensivo
            tag = None
            try:
                tag = _ensure_author_tag(self.notes_history, email, self._author_tags)
            except Exception as exc:
                logger.exception("Hub: falha ao aplicar estilo/tag do autor; renderizando sem cor.")
                tag = None  # segue sem tag

            self.notes_history.insert("end", f"[{ts_local}] ")
            if tag:
                self.notes_history.insert("end", name, (tag,))
            else:
                self.notes_history.insert("end", name)  # sem tag/cor
            self.notes_history.insert("end", f": {body}\n")
            
            self.notes_history.configure(state="disabled")
            self.notes_history.see("end")
        except Exception as e:
            logger.exception("Hub: falha crÃ­tica ao inserir nota, restaurando estado do widget.")
            try:
                self.notes_history.configure(state="disabled")
            except Exception:
                pass

        # garantir que nÃ£o haverÃ¡ "pisca": invalida o hash sÃ³ para a linha nova
        self._last_render_hash = None

    # -------------------- UtilitÃ¡rios de Nome e Cor --------------------

    def _collect_notes_debug(self) -> dict:
        """
        Coleta informaÃ§Ãµes de debug sobre notas e resoluÃ§Ã£o de autores.
        """
        notes = getattr(self, "_notes_last_data", None) or getattr(self, "_notes_last_snapshot", None) or []
        out = {
            "org_id": self._get_org_id_safe() if hasattr(self, "_get_org_id_safe") else None,
            "current_user": getattr(self, "_current_user_email", None) or self._get_email_safe() if hasattr(self, "_get_email_safe") else "",
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

    # -------------------- FormataÃ§Ã£o e RenderizaÃ§Ã£o --------------------

    def render_notes(self, notes: List[Dict[str, Any]], force: bool = False) -> None:
        """Renderiza lista de notas no histÃ³rico com nomes coloridos e timezone local.
        
        Args:
            notes: Lista de dicionÃ¡rios com dados das notas
            force: Se True, ignora cache de hash e forÃ§a re-renderizaÃ§Ã£o
        """
        # VerificaÃ§Ã£o defensiva: garantir que cache de tags existe
        if not hasattr(self, "_author_tags") or self._author_tags is None:
            self._author_tags = {}
        
        # Normalizar entrada: converter tuplas/listas para dicts
        notes = [_normalize_note(x) for x in (notes or [])]
        
        # NÃƒO apaga se vier vazio/None (evita 'branco' e piscas)
        if not notes:
            self._dlog("render_skip_empty")
            return
        
        # Hash de conteÃºdo pra evitar re-render desnecessÃ¡rio
        sig_items = []
        for n in notes:
            em = (n.get("author_email") or "").strip().lower()
            ts = (n.get("created_at") or "")
            ln = len((n.get("body") or ""))
            # se existir author_name jÃ¡ no dado, inclua na assinatura
            nm = (n.get("author_name") or "")
            sig_items.append((em, ts, ln, nm))

        import hashlib, json
        render_hash = hashlib.md5(json.dumps(sig_items, ensure_ascii=False).encode("utf-8")).hexdigest()
        
        # Se nÃ£o forÃ§ado, verificar se hash Ã© igual (skip re-render)
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
                name  = (n.get("author_name") or "").strip()

                if not name:
                    # usar cache â†’ mapa local â†’ fetch â†’ placeholder
                    name = _author_display_name(self, email)
                
                # Aplicar tag de cor com fallback defensivo
                tag = None
                try:
                    tag = _ensure_author_tag(self.notes_history, email, self._author_tags)
                except Exception as exc:
                    logger.exception("Hub: falha ao aplicar estilo/tag do autor; renderizando sem cor.")
                    tag = None  # segue sem tag
                
                ts = _to_local_str(n.get("created_at"))
                body = (n.get("body") or "").rstrip("\n")

                # Inserir: [data] <nome colorido>: corpo
                self.notes_history.insert("end", f"[{ts}] ")
                if tag:
                    self.notes_history.insert("end", name, (tag,))
                else:
                    self.notes_history.insert("end", name)  # sem tag/cor
                self.notes_history.insert("end", f": {body}\n")
            
            self.notes_history.configure(state="disabled")
            # Scrollar para o fim (mais recente)
            self.notes_history.see("end")
            self.notes_history.see("end")
        except Exception as e:
            logger.exception("Hub: erro crÃ­tico ao renderizar lista de notas.")
            try:
                self.notes_history.configure(state="disabled")
            except Exception:
                pass

    def refresh_notes_async(self, force: bool = False) -> None:
        """Atualiza notas de forma assÃ­ncrona (thread separada)."""
        if not self._polling_active:
            return
        
        # Se tabela ausente, aguardar retry period
        if self._notes_table_missing:
            log.debug("HubScreen: Tabela rc_notes ausente, aguardando retry period...")
            self._notes_after_handle = self.after(self._notes_retry_ms, lambda: self._retry_after_table_missing())
            return
        
        # Gate de autenticaÃ§Ã£o
        if not self._auth_ready():
            log.debug("HubScreen: AutenticaÃ§Ã£o nÃ£o pronta para refresh_notes, aguardando...")
            self._notes_after_handle = self.after(AUTH_RETRY_MS, lambda: self.refresh_notes_async(force))
            return
        
        org_id = self._get_org_id_safe()
        if not org_id:
            log.debug("HubScreen: org_id nÃ£o disponÃ­vel para refresh_notes, aguardando...")
            self._notes_after_handle = self.after(AUTH_RETRY_MS, lambda: self.refresh_notes_async(force))
            return

        def _work():
            notes = []
            table_missing = False
            auth_error = False
            transient_error = False
            
            try:
                # Importar serviÃ§o aqui para evitar import circular
                from core.services.notes_service import list_notes, NotesTableMissingError, NotesAuthError
                notes = list_notes(org_id, limit=500)
            except NotesTransientError:
                # Erro transitÃ³rio de rede - reagendar retry mais curto sem popup
                transient_error = True
                log.debug("HubScreen: Erro transitÃ³rio ao listar notas, retry em 2s")
                
                def _schedule_transient_retry():
                    if self._polling_active:
                        try:
                            self._notes_after_handle = self.after(2000, self.refresh_notes_async)
                        except Exception:
                            pass
                
                try:
                    self.after(0, _schedule_transient_retry)
                except Exception:
                    pass
                return
            except NotesTableMissingError as e:
                # Tabela ausente - notificar usuÃ¡rio uma vez
                table_missing = True
                log.warning("HubScreen: %s", e)
                
                def _notify_table_missing():
                    self._notes_table_missing = True
                    if not self._notes_table_missing_notified:
                        self._notes_table_missing_notified = True
                        try:
                            messagebox.showwarning(
                                "AnotaÃ§Ãµes IndisponÃ­veis",
                                "Bloco de anotaÃ§Ãµes indisponÃ­vel:\n\n"
                                f"A tabela 'rc_notes' nÃ£o existe no Supabase.\n"
                                f"Execute a migraÃ§Ã£o em: infra/db/rc_notes_migration.sql\n\n"
                                f"Tentaremos novamente em 60 segundos.",
                                parent=self
                            )
                        except Exception:
                            pass
                
                try:
                    self.after(0, _notify_table_missing)
                except Exception:
                    pass
                return
            except NotesAuthError as e:
                # Erro de permissÃ£o RLS - mostrar toast
                auth_error = True
                log.warning("HubScreen: %s", e)
                
                def _notify_auth_error():
                    try:
                        messagebox.showwarning(
                            "Sem PermissÃ£o",
                            "Sem permissÃ£o para anotar nesta organizaÃ§Ã£o.\n"
                            "Verifique seu cadastro em 'profiles'.",
                            parent=self
                        )
                    except Exception:
                        pass
                
                try:
                    self.after(0, _notify_auth_error)
                except Exception:
                    pass
                return
            except Exception as e:
                log.warning("HubScreen: Falha ao listar notas: %s", e)
            
            if not table_missing and not auth_error:
                # Normalizar notas antes de processar
                notes = [_normalize_note(x) for x in notes]
                
                # Snapshot para detectar mudanÃ§as (apenas id + timestamp)
                snapshot = [(n.get("id"), n.get("created_at")) for n in notes]
                changed = (snapshot != self._notes_last_snapshot) or force
                
                if changed:
                    self._notes_last_snapshot = snapshot
                    self._notes_last_data = notes  # salvar notas normalizadas completas
                    try:
                        self.after(0, lambda: self.render_notes(notes))
                    except Exception:
                        pass
                
                # Carregar cache de nomes no primeiro sucesso
                if not getattr(self, "_names_cache_loaded", False):
                    self._names_cache_loaded = True
                    try:
                        self.after(0, self._refresh_author_names_cache_async)
                    except Exception:
                        pass
            
            # Reagendar polling se ainda ativo
            if self._polling_active:
                try:
                    self._notes_after_handle = self.after(self._notes_poll_ms, self.refresh_notes_async)
                except Exception:
                    pass

        threading.Thread(target=_work, daemon=True).start()

    def _retry_after_table_missing(self) -> None:
        """Tenta novamente apÃ³s perÃ­odo de espera quando tabela estava ausente."""
        log.info("HubScreen: Tentando novamente apÃ³s perÃ­odo de espera (tabela ausente).")
        # Resetar flags e tentar novamente
        self._notes_table_missing = False
        self._notes_table_missing_notified = False
        # ForÃ§ar refresh
        self.refresh_notes_async(force=True)

    def _on_add_note_clicked(self) -> None:
        """Handler do botÃ£o "Adicionar" anotaÃ§Ã£o."""
        # [finalize-notes] evita vazio e spam
        text = self.new_note.get("1.0", "end").strip()
        if not text:
            return
        
        # Gate de autenticaÃ§Ã£o
        if not self._auth_ready():
            messagebox.showerror(
                "NÃ£o autenticado",
                "VocÃª precisa estar autenticado para adicionar uma anotaÃ§Ã£o.",
                parent=self
            )
            return

        # Verificar se estÃ¡ online
        app = self._get_app()
        if not app or not self._is_online(app):
            messagebox.showerror(
                "Sem conexÃ£o",
                "NÃ£o Ã© possÃ­vel adicionar anotaÃ§Ãµes sem conexÃ£o com a internet.",
                parent=self
            )
            return

        # Usar acessores seguros
        org_id = self._get_org_id_safe()
        user_email = self._get_email_safe()
        
        if not org_id or not user_email:
            messagebox.showerror(
                "Erro",
                "SessÃ£o incompleta (organizaÃ§Ã£o/usuÃ¡rio nÃ£o identificados). Tente novamente apÃ³s o login.",
                parent=self
            )
            return

        # [finalize-notes] Desabilitar botÃ£o durante operaÃ§Ã£o (anti-spam)
        self.btn_add_note.configure(state="disabled")

        def _work():
            ok = True
            error_msg = ""
            table_missing = False
            auth_error = False
            transient_error = False
            
            try:
                from core.services.notes_service import add_note, NotesTableMissingError, NotesAuthError
                # [finalize-notes] Ãšnica inserÃ§Ã£o permitida: clique explÃ­cito do usuÃ¡rio no botÃ£o
                add_note(org_id, user_email, text)
            except NotesTransientError:
                # Erro transitÃ³rio de rede - alerta suave sem stacktrace
                transient_error = True
                error_msg = "ConexÃ£o instÃ¡vel, tentando novamenteâ€¦"
                log.debug("HubScreen: Erro transitÃ³rio ao adicionar nota")
            except NotesTableMissingError as e:
                # Tabela ausente
                table_missing = True
                error_msg = "Tabela de anotaÃ§Ãµes nÃ£o encontrada no Supabase."
                log.warning("HubScreen: %s", e)
                
                # Marcar flag para silenciar polling
                def _mark_table_missing():
                    self._notes_table_missing = True
                    if not self._notes_table_missing_notified:
                        self._notes_table_missing_notified = True
                
                try:
                    self.after(0, _mark_table_missing)
                except Exception:
                    pass
            except NotesAuthError as e:
                # Erro de permissÃ£o RLS
                auth_error = True
                error_msg = str(e)
                log.warning("HubScreen: %s", e)
            except Exception as e:
                ok = False
                error_msg = str(e)
                log.error("Erro ao adicionar nota: %s", e)

            def _ui():
                if transient_error:
                    # Erro transitÃ³rio - alerta suave sem stacktrace
                    messagebox.showwarning(
                        "ConexÃ£o instÃ¡vel",
                        "NÃ£o foi possÃ­vel salvar agora; tentando novamenteâ€¦\n\n"
                        "A anotaÃ§Ã£o serÃ¡ salva assim que a conexÃ£o estabilizar.",
                        parent=self
                    )
                elif table_missing:
                    # Erro de tabela ausente
                    messagebox.showerror(
                        "AnotaÃ§Ãµes IndisponÃ­veis",
                        "Bloco de anotaÃ§Ãµes indisponÃ­vel:\n\n"
                        "A tabela 'rc_notes' nÃ£o existe no Supabase.\n"
                        "Execute a migraÃ§Ã£o em: infra/db/rc_notes_migration.sql\n\n"
                        "Tentaremos novamente em 60 segundos.",
                        parent=self
                    )
                elif auth_error:
                    # Erro de permissÃ£o RLS
                    messagebox.showerror(
                        "Sem PermissÃ£o",
                        "Sem permissÃ£o para anotar nesta organizaÃ§Ã£o.\n"
                        "Verifique seu cadastro em 'profiles'.\n\n"
                        f"Detalhes: {error_msg}",
                        parent=self
                    )
                elif ok:
                    self.new_note.delete("1.0", "end")
                    # ForÃ§ar atualizaÃ§Ã£o imediata
                    self.refresh_notes_async(force=True)
                    # Atualizar cache de nomes apÃ³s adicionar nota
                    self._refresh_author_names_cache_async(force=False)
                    try:
                        messagebox.showinfo(
                            "Sucesso",
                            "AnotaÃ§Ã£o adicionada com sucesso!",
                            parent=self
                        )
                    except Exception:
                        pass
                else:
                    messagebox.showerror(
                        "Erro",
                        f"Falha ao adicionar anotaÃ§Ã£o: {error_msg}",
                        parent=self
                    )
                self.btn_add_note.configure(state="normal")

            try:
                self.after(0, _ui)
            except Exception:
                pass

        threading.Thread(target=_work, daemon=True).start()

    def _get_app(self):
        """ObtÃ©m referÃªncia para a janela principal (App)."""
        try:
            # Subir na hierarquia atÃ© encontrar a janela raiz
            widget = self.master
            while widget:
                if hasattr(widget, "auth") or hasattr(widget, "_org_id_cache"):
                    return widget
                widget = getattr(widget, "master", None)
        except Exception:
            pass
        return None

    def _is_online(self, app) -> bool:
        """Verifica se estÃ¡ online."""
        try:
            if hasattr(app, "_net_is_online"):
                return bool(app._net_is_online)
        except Exception:
            pass
        return True  # Assume online se nÃ£o conseguir verificar

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

    def destroy(self) -> None:
        """Override destroy para parar polling."""
        self.stop_polling()
        super().destroy()

    def _noop(self) -> None:
        """Placeholder para botÃµes sem aÃ§Ã£o."""
        pass

    def _show_debug_info(self, event=None) -> None:
        """Gera relatÃ³rio JSON de diagnÃ³stico (atalho Ctrl+D)."""
        import json
        import os
        from datetime import datetime
        
        try:
            # Coleta informaÃ§Ãµes de debug
            debug_data = self._collect_notes_debug()
            
            # Gera nome do arquivo com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_notes_report_{timestamp}.json"
            
            # Salva no diretÃ³rio de trabalho
            filepath = os.path.abspath(filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)
            
            # Mostra mensagem com o caminho do arquivo
            messagebox.showinfo(
                "RelatÃ³rio de Debug Gerado",
                f"RelatÃ³rio salvo em:\n{filepath}",
                parent=self
            )
            
            # Imprime no console como backup
            logger.info("\n=== DEBUG NOTES REPORT ===")
            logger.info(json.dumps(debug_data, ensure_ascii=False, indent=2))
            logger.info("=== Salvo em: %s ===\n", filepath)
            
        except Exception as e:
            log.error("Erro ao gerar relatÃ³rio de debug: %s", e)
            messagebox.showerror(
                "Erro",
                f"Erro ao gerar relatÃ³rio: {e}",
                parent=self
            )
