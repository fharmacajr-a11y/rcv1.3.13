# -*- coding: utf-8 -*-
"""Tela Hub: menu vertical + bloco de notas compartilhado (append-only via Supabase)."""

from __future__ import annotations

import tkinter as tk
import threading
import hashlib
import re
import colorsys
import time
from datetime import datetime, timezone
from typing import Callable, Optional, List, Dict, Any
from tkinter import messagebox

import ttkbootstrap as tb

from core.logger import get_logger
from ui.hub.constants import PAD_OUTER
from ui.hub.layout import apply_hub_notes_right

# Import do erro transitório
from core.services.notes_service import NotesTransientError

# Timezone handling com fallback
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

# Constantes para retry de autenticação
AUTH_RETRY_MS = 2000  # 2 segundos

# Mapa de e-mail -> nome curto preferido (sempre em minúsculas)
AUTHOR_NAMES = {
    "farmacajr@gmail.com": "Junior",
    # "maria@empresa.com": "Maria",
    # "ana@empresa.com": "Ana",
}

# Cooldown para refresh de nomes (evitar chamadas duplicadas)
_NAMES_REFRESH_COOLDOWN_S = 30


# -------------------- Funções Auxiliares de Cor --------------------

def _hsl_to_hex(h: float, s: float, l: float) -> str:
    """Converte HSL para HEX. h: 0..360, s/l: 0..1"""
    r, g, b = colorsys.hls_to_rgb(h/360.0, l, s)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

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
        # Compatibilidade com kwargs antigos (mantém snjpc para retrocompatibilidade)
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
        self.modules_panel = tb.Labelframe(self, text="Módulos", padding=PAD_OUTER)
        modules_panel = self.modules_panel

        def mk_btn(text: str, cmd: Optional[Callable] = None, highlight: bool = False) -> tb.Button:
            """Cria um botão. Se highlight=True, aplica estilo de sucesso (verde)."""
            if highlight:
                b = tb.Button(modules_panel, text=text, command=(cmd or self._noop), bootstyle="success")
            else:
                b = tb.Button(modules_panel, text=text, command=(cmd or self._noop), bootstyle="secondary")
            b.pack(fill="x", pady=4)
            return b

        # Ordem e rótulos padronizados (primeira letra maiúscula)
        # Botão "Clientes" destacado em verde
        mk_btn("Clientes", self.open_clientes, highlight=True)
        mk_btn("Senhas", self.open_senhas)
        mk_btn("Anvisa", self.open_anvisa)
        mk_btn("Auditoria", self.open_auditoria)
        mk_btn("Farmácia Popular", self.open_farmacia_popular)
        mk_btn("Sngpc", self.open_sngpc)  # Corrigido: SNJPC -> SNGPC (callback)
        mk_btn("Sifap", self.open_mod_sifap)

        # --- ESPAÇO CENTRAL VAZIO (coluna 1) ---
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
        self._last_render_hash = None       # md5 do conteúdo renderizado
        self._names_cache_loading = False   # trava anti reentrância

        # Live sync
        self._live_channel = None
        self._live_org_id = None
        self._live_sync_on = False
        self._live_last_ts = None  # ISO da última nota conhecida
        self._live_poll_job = None

        # Configurar atalhos (apenas uma vez)
        self._binds_ready = getattr(self, "_binds_ready", False)
        if not self._binds_ready:
            # Ctrl+D para diagnóstico
            self.bind_all("<Control-d>", self._show_debug_info)
            self.bind_all("<Control-D>", self._show_debug_info)
            
            # Ctrl+L para recarregar cache de nomes (teste)
            self.bind_all("<Control-l>", lambda e: self._refresh_author_names_cache_async(force=True))
            self.bind_all("<Control-L>", lambda e: self._refresh_author_names_cache_async(force=True))
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

    def _build_notes_panel(self) -> None:
        """Constrói o painel de notas compartilhadas (append-only)."""
        self.notes_panel = tb.Labelframe(self, text="Anotações Compartilhadas", padding=PAD_OUTER)
        right = self.notes_panel
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)  # histórico expande

        # --- Histórico (somente leitura) ---
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

        # --- Entrada nova anotação ---
        entry_frame = tb.Frame(right)
        entry_frame.grid(row=1, column=0, sticky="ew", pady=(0, 0))
        entry_frame.columnconfigure(0, weight=1)

        tb.Label(entry_frame, text="Nova anotação:", font=("", 9)).grid(
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

    # -------------------- Utilitários de Hash --------------------
    
    def _hash_dict(self, d: dict) -> str:
        """Calcula hash MD5 de um dicionário para comparação."""
        import hashlib, json
        try:
            payload = json.dumps(d or {}, sort_keys=True, ensure_ascii=False)
        except Exception:
            payload = str(sorted((d or {}).items()))
        return hashlib.md5(payload.encode("utf-8", errors="ignore")).hexdigest()

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
        Chamado sempre que a tela do Hub fica visível (navegação de volta).
        Garante renderização imediata dos dados em cache e mantém live-sync ativo.
        """
        # 1) Iniciar live-sync caso ainda não esteja (idempotente)
        try:
            self._start_live_sync()
        except Exception as e:
            log.warning("Erro ao iniciar live-sync no on_show: %s", e)

        # 2) Se a Text está vazia mas já temos dados em memória, renderizar JÁ
        try:
            is_empty = (self.notes_history.index("end-1c") == "1.0")
        except Exception:
            is_empty = True

        if is_empty and getattr(self, "_notes_last_data", None):
            # Render forçado ignora o hash para não 'pular'
            try:
                self.render_notes(self._notes_last_data, force=True)
            except Exception as e:
                log.warning("Erro ao renderizar notas no on_show: %s", e)
        
        # 3) Forçar recarga do cache de nomes (garante nomes atualizados)
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
        """Se Realtime não chegou, busca apenas notas novas (desde _live_last_ts)."""
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
            # se não existir, faça um normalize mínimo:
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
            note = self._normalize_note(row)

        # se já temos essa nota na memória, ignore
        notes = getattr(self, "_notes_last_data", None) or []
        if any(str(n.get("id")) == str(note.get("id")) for n in notes if n.get("id") is not None):
            return

        # append em memória
        notes = notes + [note]
        self._notes_last_data = notes
        try:
            # manter snapshot de comparação simples (id+ts)
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
                name = self._author_display_name(email)  # usa cache → fetch de fundo

            ts_local = self._to_local_str(note.get("created_at"))
            body = (note.get("body") or "").rstrip("\n")
            tag = self._ensure_author_tag(email)

            self.notes_history.insert("end", f"[{ts_local}] ")
            self.notes_history.insert("end", name, (tag,))
            self.notes_history.insert("end", f": {body}\n")
            
            self.notes_history.configure(state="disabled")
            self.notes_history.see("end")
        except Exception:
            pass

        # garantir que não haverá "pisca": invalida o hash só para a linha nova
        self._last_render_hash = None

    # -------------------- Utilitário de Normalização de Notas --------------------

    def _normalize_note(self, n):
        """
        Converte diferentes formatos de nota para dict:
        {'id': str, 'created_at': str, 'author_email': str, 'body': str}
        Aceita: dict, tuple/list (nas formas mais comuns).
        Nunca quebra: sempre devolve um dict seguro.
        """
        # Dict já no formato esperado
        if isinstance(n, dict):
            out = {
                "id": n.get("id") or "",
                "created_at": n.get("created_at") or n.get("ts") or n.get("timestamp") or "",
                "author_email": n.get("author_email") or n.get("author") or n.get("email") or "",
                "body": n.get("body") or n.get("text") or n.get("message") or "",
            }
            return out

        # Tupla/Lista: tentar mapeamentos mais comuns
        if isinstance(n, (tuple, list)):
            note_id = ts = author = body = ""
            L = len(n)
            # (id, ts, author, body)
            if L >= 4:
                note_id, ts, author, body = n[0], n[1], n[2], n[3]
            # (ts, author, body) – sem id
            elif L >= 3:
                ts, author, body = n[0], n[1], n[2]
            # (author, body) – sem ts
            elif L == 2:
                author, body = n[0], n[1]
            # (body,) – fallback
            elif L == 1:
                body = n[0]
            return {
                "id": str(note_id or ""),
                "created_at": str(ts or ""),
                "author_email": str(author or ""),
                "body": str(body or ""),
            }

        # Qualquer outro tipo: stringify como corpo
        return {"id": "", "created_at": "", "author_email": "", "body": str(n)}

    # -------------------- Utilitários de Nome e Cor --------------------

    def _author_display_name(self, email: str) -> str:
        """
        Retorna nome do autor com prioridade otimizada e fetch on-demand.
        """
        key = (email or "").strip().lower()
        if not key:
            return "?"

        # 0) se vier só prefixo, resolver via mapa de prefixos (se você já tem)
        if "@" not in key:
            resolved = (getattr(self, "_email_prefix_map", {}) or {}).get(key)
            if resolved:
                key = resolved

        # 1) cache do Supabase
        dn = (getattr(self, "_author_names_cache", {}) or {}).get(key)
        if dn:
            return dn

        # 2) mapa local AUTHOR_NAMES
        if "AUTHOR_NAMES" in globals() and key in AUTHOR_NAMES:
            return AUTHOR_NAMES[key]

        # 3) fetch on-demand (apenas UMA thread por e-mail)
        if not hasattr(self, "_pending_name_fetch"):
            self._pending_name_fetch = set()
        if "@" in key and key not in self._pending_name_fetch:
            self._pending_name_fetch.add(key)
            def _work():
                resolved = None
                try:
                    from core.services.profiles_service import get_display_name_by_email
                    resolved = get_display_name_by_email(key)
                finally:
                    def _ui():
                        try:
                            if resolved:
                                (self._author_names_cache or {}).update({key: resolved})
                                # força re-render UMA vez
                                self._last_render_hash = None
                                if getattr(self, "_notes_last_data", None):
                                    self.render_notes(self._notes_last_data)
                                elif getattr(self, "_notes_last_snapshot", None):
                                    self.render_notes(self._notes_last_snapshot)
                        finally:
                            try: self._pending_name_fetch.remove(key)
                            except KeyError: pass
                    try: self.after(0, _ui)
                    except Exception: pass
            import threading
            threading.Thread(target=_work, daemon=True).start()

        # 4) placeholder (último recurso)
        return key.split("@", 1)[0].replace(".", " ").title()

    def _author_color(self, email: str) -> str:
        """
        Cor estável por autor com alto contraste (S=90%, L=28%).
        """
        key = (email or "").strip().lower()
        if not key:
            return "#3a3a3a"
        d = hashlib.md5(key.encode("utf-8")).hexdigest()
        hue = int(d[:2], 16) * (360/255.0)  # 0..360
        return _hsl_to_hex(hue, 0.90, 0.28)

    def _ensure_author_tag(self, email: str) -> str:
        """
        Cria (se ainda não existir) uma tag de cor para esse autor no Text.
        """
        name = f"author::{(email or '').strip().lower()}"
        if not hasattr(self, "_author_tags"):
            self._author_tags = set()
        if name in self._author_tags:
            return name
        color = self._author_color(email)
        try:
            # fonte negrito e tamanho 10 no nome do autor
            self.notes_history.tag_configure(name, foreground=color, font=("TkDefaultFont", 10, "bold"))
        except Exception:
            # fallback sem negrito
            try:
                self.notes_history.tag_configure(name, foreground=color)
            except Exception:
                pass
        self._author_tags.add(name)
        return name

    # -------------------- DEBUG: Diagnóstico de Resolução de Autores --------------------

    def _debug_resolve_author(self, email: str) -> dict:
        """
        Resolve um email de autor e retorna informações de debug sobre o processo.
        """
        raw = email or ""
        key = raw.strip().lower()
        alias_applied = False
        resolved_email = key
        source = "placeholder"
        name = None

        prefix_map = getattr(self, "_email_prefix_map", {}) or {}
        author_cache = getattr(self, "_author_names_cache", {}) or {}

        # aliases opcionais
        try:
            from core.services.profiles_service import EMAIL_PREFIX_ALIASES
        except Exception:
            EMAIL_PREFIX_ALIASES = {}

        # Se veio só o prefixo, tenta corrigir alias e resolver no mapa de prefixos
        if key and "@" not in key:
            alias = EMAIL_PREFIX_ALIASES.get(key, key)
            alias_applied = (alias != key)
            resolved_email = prefix_map.get(alias) or prefix_map.get(key) or alias
        else:
            resolved_email = key

        # 1) cache Supabase (por org)
        dn = author_cache.get(resolved_email)
        if dn:
            name = dn
            source = "names_cache"

        # 2) mapa local AUTHOR_NAMES
        if name is None and "AUTHOR_NAMES" in globals():
            dn = (AUTHOR_NAMES or {}).get(resolved_email)
            if dn:
                name = dn
                source = "AUTHOR_NAMES"

        # 3) fetch direto por e-mail
        fetched = None
        if name is None and "@" in resolved_email:
            try:
                from core.services.profiles_service import get_display_name_by_email
                fetched = get_display_name_by_email(resolved_email)
                if fetched:
                    name = fetched
                    source = "fetch_by_email"
            except Exception as e:
                fetched = f"ERR:{e!r}"

        # 4) fallback: prefixo formatado
        if name is None:
            name = resolved_email.split("@", 1)[0].replace(".", " ").title()

        return {
            "input": raw,
            "normalized": key,
            "alias_applied": alias_applied,
            "resolved_email": resolved_email,
            "name": name,
            "source": source,
            "cache_hit": resolved_email in author_cache,
            "prefix_map_hit": (key in prefix_map) or (resolved_email in prefix_map.values()),
        }

    def _collect_notes_debug(self) -> dict:
        """
        Coleta informações de debug sobre notas e resolução de autores.
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
            out["samples"].append(self._debug_resolve_author(_author_of(n)))
        return out

    # -------------------- Fim DEBUG --------------------

    def _to_local_str(self, ts_iso: str) -> str:
        """
        Converte ISO UTC do Supabase para string no fuso local do sistema.
        """
        try:
            if not ts_iso:
                return "?"
            # garante tzinfo UTC
            if ts_iso.endswith("Z"):
                dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(ts_iso)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            dt_local = dt.astimezone(LOCAL_TZ)
            return dt_local.strftime("%d/%m/%Y - %H:%M")
        except Exception:
            return ts_iso or "?"

    # -------------------- Formatação e Renderização --------------------

    def _format_note_line(self, note: Dict[str, Any]) -> str:
        """Formata uma nota para exibição: [dd/mm/yyyy - HH:MM] autor: texto"""
        ts = note.get("created_at", "")
        try:
            # Supabase retorna ISO 8601 (ex: 2025-10-19T15:30:00+00:00)
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            ts_str = dt.strftime("%d/%m/%Y - %H:%M")
        except Exception:
            ts_str = ts or "?"
        
        author = note.get("author_email", "?")
        body = note.get("body", "")
        return f"[{ts_str}] {author}: {body}"

    def render_notes(self, notes: List[Dict[str, Any]], force: bool = False) -> None:
        """Renderiza lista de notas no histórico com nomes coloridos e timezone local.
        
        Args:
            notes: Lista de dicionários com dados das notas
            force: Se True, ignora cache de hash e força re-renderização
        """
        # Normalizar entrada: converter tuplas/listas para dicts
        notes = [self._normalize_note(x) for x in (notes or [])]
        
        # NÃO apaga se vier vazio/None (evita 'branco' e piscas)
        if not notes:
            self._dlog("render_skip_empty")
            return
        
        # Hash de conteúdo pra evitar re-render desnecessário
        sig_items = []
        for n in notes:
            em = (n.get("author_email") or "").strip().lower()
            ts = (n.get("created_at") or "")
            ln = len((n.get("body") or ""))
            # se existir author_name já no dado, inclua na assinatura
            nm = (n.get("author_name") or "")
            sig_items.append((em, ts, ln, nm))

        import hashlib, json
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
                name  = (n.get("author_name") or "").strip()

                if not name:
                    # usar cache → mapa local → fetch → placeholder
                    name = self._author_display_name(email)
                
                tag = self._ensure_author_tag(email)
                ts = self._to_local_str(n.get("created_at"))
                body = (n.get("body") or "").rstrip("\n")

                # Inserir: [data] <nome colorido>: corpo
                self.notes_history.insert("end", f"[{ts}] ")
                self.notes_history.insert("end", name, (tag,))
                self.notes_history.insert("end", f": {body}\n")
            
            self.notes_history.configure(state="disabled")
            # Scrollar para o fim (mais recente)
            self.notes_history.see("end")
            self.notes_history.see("end")
        except Exception as e:
            log.error("Erro ao renderizar notas: %s", e)

    def refresh_notes_async(self, force: bool = False) -> None:
        """Atualiza notas de forma assíncrona (thread separada)."""
        if not self._polling_active:
            return
        
        # Se tabela ausente, aguardar retry period
        if self._notes_table_missing:
            log.debug("HubScreen: Tabela rc_notes ausente, aguardando retry period...")
            self._notes_after_handle = self.after(self._notes_retry_ms, lambda: self._retry_after_table_missing())
            return
        
        # Gate de autenticação
        if not self._auth_ready():
            log.debug("HubScreen: Autenticação não pronta para refresh_notes, aguardando...")
            self._notes_after_handle = self.after(AUTH_RETRY_MS, lambda: self.refresh_notes_async(force))
            return
        
        org_id = self._get_org_id_safe()
        if not org_id:
            log.debug("HubScreen: org_id não disponível para refresh_notes, aguardando...")
            self._notes_after_handle = self.after(AUTH_RETRY_MS, lambda: self.refresh_notes_async(force))
            return

        def _work():
            notes = []
            table_missing = False
            auth_error = False
            transient_error = False
            
            try:
                # Importar serviço aqui para evitar import circular
                from core.services.notes_service import list_notes, NotesTableMissingError, NotesAuthError
                notes = list_notes(org_id, limit=500)
            except NotesTransientError:
                # Erro transitório de rede - reagendar retry mais curto sem popup
                transient_error = True
                log.debug("HubScreen: Erro transitório ao listar notas, retry em 2s")
                
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
                # Tabela ausente - notificar usuário uma vez
                table_missing = True
                log.warning("HubScreen: %s", e)
                
                def _notify_table_missing():
                    self._notes_table_missing = True
                    if not self._notes_table_missing_notified:
                        self._notes_table_missing_notified = True
                        try:
                            messagebox.showwarning(
                                "Anotações Indisponíveis",
                                "Bloco de anotações indisponível:\n\n"
                                f"A tabela 'rc_notes' não existe no Supabase.\n"
                                f"Execute a migração em: infra/db/rc_notes_migration.sql\n\n"
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
                # Erro de permissão RLS - mostrar toast
                auth_error = True
                log.warning("HubScreen: %s", e)
                
                def _notify_auth_error():
                    try:
                        messagebox.showwarning(
                            "Sem Permissão",
                            "Sem permissão para anotar nesta organização.\n"
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
                notes = [self._normalize_note(x) for x in notes]
                
                # Snapshot para detectar mudanças (apenas id + timestamp)
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
        """Tenta novamente após período de espera quando tabela estava ausente."""
        log.info("HubScreen: Tentando novamente após período de espera (tabela ausente).")
        # Resetar flags e tentar novamente
        self._notes_table_missing = False
        self._notes_table_missing_notified = False
        # Forçar refresh
        self.refresh_notes_async(force=True)

    def _on_add_note_clicked(self) -> None:
        """Handler do botão "Adicionar" anotação."""
        # [finalize-notes] evita vazio e spam
        text = self.new_note.get("1.0", "end").strip()
        if not text:
            return
        
        # Gate de autenticação
        if not self._auth_ready():
            messagebox.showerror(
                "Não autenticado",
                "Você precisa estar autenticado para adicionar uma anotação.",
                parent=self
            )
            return

        # Verificar se está online
        app = self._get_app()
        if not app or not self._is_online(app):
            messagebox.showerror(
                "Sem conexão",
                "Não é possível adicionar anotações sem conexão com a internet.",
                parent=self
            )
            return

        # Usar acessores seguros
        org_id = self._get_org_id_safe()
        user_email = self._get_email_safe()
        
        if not org_id or not user_email:
            messagebox.showerror(
                "Erro",
                "Sessão incompleta (organização/usuário não identificados). Tente novamente após o login.",
                parent=self
            )
            return

        # [finalize-notes] Desabilitar botão durante operação (anti-spam)
        self.btn_add_note.configure(state="disabled")

        def _work():
            ok = True
            error_msg = ""
            table_missing = False
            auth_error = False
            transient_error = False
            
            try:
                from core.services.notes_service import add_note, NotesTableMissingError, NotesAuthError
                # [finalize-notes] Única inserção permitida: clique explícito do usuário no botão
                add_note(org_id, user_email, text)
            except NotesTransientError:
                # Erro transitório de rede - alerta suave sem stacktrace
                transient_error = True
                error_msg = "Conexão instável, tentando novamente…"
                log.debug("HubScreen: Erro transitório ao adicionar nota")
            except NotesTableMissingError as e:
                # Tabela ausente
                table_missing = True
                error_msg = "Tabela de anotações não encontrada no Supabase."
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
                # Erro de permissão RLS
                auth_error = True
                error_msg = str(e)
                log.warning("HubScreen: %s", e)
            except Exception as e:
                ok = False
                error_msg = str(e)
                log.error("Erro ao adicionar nota: %s", e)

            def _ui():
                if transient_error:
                    # Erro transitório - alerta suave sem stacktrace
                    messagebox.showwarning(
                        "Conexão instável",
                        "Não foi possível salvar agora; tentando novamente…\n\n"
                        "A anotação será salva assim que a conexão estabilizar.",
                        parent=self
                    )
                elif table_missing:
                    # Erro de tabela ausente
                    messagebox.showerror(
                        "Anotações Indisponíveis",
                        "Bloco de anotações indisponível:\n\n"
                        "A tabela 'rc_notes' não existe no Supabase.\n"
                        "Execute a migração em: infra/db/rc_notes_migration.sql\n\n"
                        "Tentaremos novamente em 60 segundos.",
                        parent=self
                    )
                elif auth_error:
                    # Erro de permissão RLS
                    messagebox.showerror(
                        "Sem Permissão",
                        "Sem permissão para anotar nesta organização.\n"
                        "Verifique seu cadastro em 'profiles'.\n\n"
                        f"Detalhes: {error_msg}",
                        parent=self
                    )
                elif ok:
                    self.new_note.delete("1.0", "end")
                    # Forçar atualização imediata
                    self.refresh_notes_async(force=True)
                    # Atualizar cache de nomes após adicionar nota
                    self._refresh_author_names_cache_async(force=False)
                    try:
                        messagebox.showinfo(
                            "Sucesso",
                            "Anotação adicionada com sucesso!",
                            parent=self
                        )
                    except Exception:
                        pass
                else:
                    messagebox.showerror(
                        "Erro",
                        f"Falha ao adicionar anotação: {error_msg}",
                        parent=self
                    )
                self.btn_add_note.configure(state="normal")

            try:
                self.after(0, _ui)
            except Exception:
                pass

        threading.Thread(target=_work, daemon=True).start()

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
                parent=self
            )
            
            # Imprime no console como backup
            logger.info("\n=== DEBUG NOTES REPORT ===")
            logger.info(json.dumps(debug_data, ensure_ascii=False, indent=2))
            logger.info("=== Salvo em: %s ===\n", filepath)
            
        except Exception as e:
            log.error("Erro ao gerar relatório de debug: %s", e)
            messagebox.showerror(
                "Erro",
                f"Erro ao gerar relatório: {e}",
                parent=self
            )
