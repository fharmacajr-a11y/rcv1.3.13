# -*- coding: utf-8 -*-
"""Store singleton para histórico de atividades recentes.

Mantém eventos em memória e persiste no Supabase. Notifica observers para atualização em tempo real.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from src.modules.hub.async_runner import HubAsyncRunner

log = logging.getLogger(__name__)

# Máximo de eventos mantidos em memória
MAX_EVENTS = 200


@dataclass
class ActivityEvent:
    """Representa um evento de atividade estruturado.

    Attributes:
        org_id: ID da organização
        module: Módulo que gerou o evento (ex: "ANVISA", "SIFAP")
        action: Ação executada (ex: "Concluída", "Cancelada", "Excluída")
        message: Mensagem formatada do evento
        client_id: ID do cliente relacionado (opcional)
        cnpj: CNPJ do cliente (opcional)
        request_id: ID da demanda/request (opcional)
        request_type: Tipo da demanda (opcional)
        due_date: Prazo no formato YYYY-MM-DD (opcional)
        actor_email: Email do usuário que executou (opcional)
        actor_user_id: ID do usuário que executou (opcional)
        created_at: Timestamp do evento (gerado automaticamente se None)
        metadata: Dados adicionais em formato dict (opcional)
    """

    org_id: str
    module: str
    action: str
    message: str
    client_id: int | None = None
    cnpj: str | None = None
    request_id: str | None = None
    request_type: str | None = None
    due_date: str | None = None
    actor_email: str | None = None
    actor_user_id: str | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte para dict para inserção no Supabase."""
        return {
            "org_id": self.org_id,
            "module": self.module,
            "action": self.action,
            "message": self.message,
            "client_id": self.client_id,
            "cnpj": self.cnpj,
            "request_id": self.request_id,
            "request_type": self.request_type,
            "due_date": self.due_date,
            "actor_email": self.actor_email,
            "actor_user_id": self.actor_user_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActivityEvent:
        """Cria ActivityEvent a partir de dict do Supabase."""
        # Converter created_at string ISO para datetime se necessário
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except Exception:
                created_at = None

        return cls(
            org_id=data["org_id"],
            module=data["module"],
            action=data["action"],
            message=data["message"],
            client_id=data.get("client_id"),
            cnpj=data.get("cnpj"),
            request_id=data.get("request_id"),
            request_type=data.get("request_type"),
            due_date=data.get("due_date"),
            actor_email=data.get("actor_email"),
            actor_user_id=data.get("actor_user_id"),
            created_at=created_at,
            metadata=data.get("metadata") or {},
        )


class RecentActivityStore:
    """Store singleton para atividades recentes.

    Thread-safe, mantém eventos em memória e persiste no Supabase.
    """

    def __init__(self) -> None:
        """Inicializa o store."""
        self._events: deque[str] = deque(maxlen=MAX_EVENTS)
        self._observers: list[Callable[[], None]] = []
        self._lock = RLock()
        self._bootstrapped = False

    def add_event(
        self,
        event: ActivityEvent | str,
        *,
        persist: bool = True,
        runner: HubAsyncRunner | None = None,
    ) -> None:
        """Adiciona um evento ao histórico e notifica observers.

        Args:
            event: ActivityEvent estruturado ou string formatada (legado)
            persist: Se True, persiste no Supabase (requer runner)
            runner: HubAsyncRunner para operações assíncronas
        """
        # Converter para string se for ActivityEvent
        if isinstance(event, ActivityEvent):
            event_str = format_activity_event(event)

            # Persistir no Supabase se solicitado
            if persist and runner:
                self._persist_event_async(event, runner)
        else:
            event_str = event

        # Adicionar ao deque imediatamente (otimista)
        with self._lock:
            self._events.append(event_str)
            log.debug(f"[RecentActivityStore] Evento adicionado: {event_str[:100]}")

            # Notificar observers
            for callback in self._observers[:]:
                try:
                    callback()
                except Exception as exc:
                    log.warning(f"[RecentActivityStore] Erro ao notificar observer: {exc}")

    def _persist_event_async(self, event: ActivityEvent, runner: HubAsyncRunner) -> None:
        """Persiste evento no Supabase em background."""
        from src.infra.repositories import activity_events_repository

        def persist() -> bool:
            """Função executada em background."""
            return activity_events_repository.insert_event(event.to_dict())

        def on_success(success: bool) -> None:
            """Callback de sucesso."""
            if success:
                log.debug(f"[RecentActivityStore] Evento persistido: {event.module} - {event.action}")
            else:
                log.warning(f"[RecentActivityStore] Falha ao persistir evento: {event.module} - {event.action}")

        def on_error(exc: Exception) -> None:
            """Callback de erro."""
            log.warning(f"[RecentActivityStore] Erro ao persistir evento: {exc}")

        runner.run(persist, on_success, on_error)

    def _enrich_events_with_client_info(self, events: list[ActivityEvent], org_id: str) -> list[ActivityEvent]:
        """Enriquece eventos antigos com razão social via bulk query.

        Args:
            events: Lista de eventos carregados do Supabase
            org_id: ID da organização

        Returns:
            Lista de eventos enriquecidos (mesma lista, modificada in-place)
        """
        # 1) Identificar eventos que precisam de enriquecimento
        missing_client_ids = set()
        for ev in events:
            if ev.client_id:
                # Verificar se não tem razão social em metadata
                has_razao = False
                if ev.metadata:
                    has_razao = bool(
                        ev.metadata.get("razao_social") or ev.metadata.get("client_name") or ev.metadata.get("razao")
                    )

                if not has_razao:
                    missing_client_ids.add(ev.client_id)

        # 2) Se não há eventos para enriquecer, retornar
        if not missing_client_ids:
            log.debug("[RecentActivityStore] Nenhum evento antigo precisa de enriquecimento")
            return events

        log.info(f"[RecentActivityStore] Enriquecendo {len(missing_client_ids)} clientes com razão social")

        # 3) Bulk query na tabela clients
        try:
            from src.infra.supabase_client import get_supabase

            sb = get_supabase()
            client_ids_list = list(missing_client_ids)

            # Query: select id, cnpj, razao_social where org_id = X and id in (...)
            resp = (
                sb.table("clients")
                .select("id,cnpj,razao_social")
                .eq("org_id", org_id)
                .in_("id", client_ids_list)
                .execute()
            )

            if not resp.data:
                log.warning("[RecentActivityStore] Bulk query retornou 0 clientes")
                return events

            # 4) Montar map: {client_id: {"cnpj": ..., "razao_social": ...}}
            client_info_map = {}
            for row in resp.data:
                client_id = row.get("id")
                if client_id:
                    client_info_map[client_id] = {
                        "cnpj": row.get("cnpj") or "",
                        "razao_social": row.get("razao_social") or "",
                    }

            log.info(f"[RecentActivityStore] Encontrados {len(client_info_map)} clientes no banco")

            # 5) Enriquecer eventos
            for ev in events:
                if ev.client_id and ev.client_id in client_info_map:
                    info = client_info_map[ev.client_id]

                    # Preencher CNPJ se vazio
                    if not ev.cnpj and info["cnpj"]:
                        ev.cnpj = info["cnpj"]

                    # HARDENING: Corrigir CNPJ inconsistente (normalizar para dígitos)
                    def _cnpj_digits(cnpj_str: str | None) -> str:
                        """Extrai apenas dígitos do CNPJ."""
                        if not cnpj_str:
                            return ""
                        return "".join(c for c in cnpj_str if c.isdigit())

                    ev_cnpj_digits = _cnpj_digits(ev.cnpj)
                    info_cnpj_digits = _cnpj_digits(info["cnpj"])

                    if ev_cnpj_digits and info_cnpj_digits and ev_cnpj_digits != info_cnpj_digits:
                        log.warning(
                            f"[RecentActivityStore] CNPJ inconsistente corrigido: "
                            f"client_id={ev.client_id} evento_cnpj={ev.cnpj} -> correto_cnpj={info['cnpj']}"
                        )
                        ev.cnpj = info["cnpj"]

                    # Garantir metadata é dict
                    if ev.metadata is None:
                        ev.metadata = {}

                    # Preencher razao_social se não existir
                    has_razao = bool(
                        ev.metadata.get("razao_social") or ev.metadata.get("client_name") or ev.metadata.get("razao")
                    )

                    if not has_razao and info["razao_social"]:
                        ev.metadata["razao_social"] = info["razao_social"]

                    # HARDENING: Corrigir razão social inconsistente
                    current_razao = (
                        ev.metadata.get("razao_social")
                        or ev.metadata.get("client_name")
                        or ev.metadata.get("razao")
                        or ""
                    )

                    if current_razao and info["razao_social"] and current_razao != info["razao_social"]:
                        log.warning(
                            f"[RecentActivityStore] Razão social inconsistente corrigida: "
                            f"client_id={ev.client_id} evento_razao='{current_razao}' -> "
                            f"correto_razao='{info['razao_social']}'"
                        )
                        ev.metadata["razao_social"] = info["razao_social"]

            log.info("[RecentActivityStore] Enriquecimento concluído")

        except Exception as exc:
            log.warning(f"[RecentActivityStore] Erro ao enriquecer eventos: {exc}")
            # Continuar mesmo com erro - eventos aparecem sem razão social

        return events

    def bootstrap_from_db(self, org_id: str, runner: HubAsyncRunner) -> None:
        """Carrega eventos do Supabase e popula o store.

        Hardening: Em caso de erro, marca como bootstrapped com store vazio
        para não bloquear a UI. Observers são notificados normalmente.

        Args:
            org_id: ID da organização
            runner: HubAsyncRunner para operações assíncronas
        """
        from src.core.utils.perf_timer import perf_timer
        
        if self._bootstrapped:
            log.debug("[RecentActivityStore] Já foi carregado do DB, ignorando")
            return

        from src.infra.repositories import activity_events_repository

        def load_events() -> list[dict[str, Any]]:
            """Função executada em background."""
            with perf_timer("hub.recent_activity.load_from_db", log, threshold_ms=500):
                return activity_events_repository.list_recent(org_id, limit=MAX_EVENTS)

        def on_success(rows: list[dict[str, Any]]) -> None:
            """Callback de sucesso - popula deque."""
            with self._lock:
                self._events.clear()

                # Se rows estiver vazio (por erro no repo), store fica vazio
                # e UI mostra "Nenhuma atividade recente."
                if not rows:
                    log.info("[RecentActivityStore] Nenhum evento retornado do Supabase (erro ou vazio)")
                else:
                    # Converter rows para ActivityEvent
                    events = []
                    for row in rows:
                        try:
                            event = ActivityEvent.from_dict(row)
                            events.append(event)
                        except Exception as exc:
                            log.warning(f"[RecentActivityStore] Erro ao converter evento do DB: {exc}")

                    # Enriquecer eventos antigos com razão social (bulk query)
                    events = self._enrich_events_with_client_info(events, org_id)

                    # Formatar e adicionar (reverter para mais antigo ao mais novo)
                    for event in reversed(events):
                        try:
                            event_str = format_activity_event(event)
                            self._events.append(event_str)
                        except Exception as exc:
                            log.warning(f"[RecentActivityStore] Erro ao formatar evento: {exc}")

                    log.info(f"[RecentActivityStore] Carregados {len(self._events)} eventos do Supabase")

                self._bootstrapped = True

                # Notificar observers (mesmo se store vazio)
                for callback in self._observers[:]:
                    try:
                        callback()
                    except Exception as exc:
                        log.warning(f"[RecentActivityStore] Erro ao notificar observer após bootstrap: {exc}")

        def on_error(exc: Exception) -> None:
            """Callback de erro - marcar como bootstrapped para não travar UI."""
            log.warning(
                f"[RecentActivityStore] Erro ao carregar eventos do Supabase: {exc}. "
                "Store permanece vazio (UI mostra 'Nenhuma atividade recente.')"
            )
            # Hardening: marcar como bootstrapped mesmo em erro para não bloquear UI
            with self._lock:
                self._bootstrapped = True
                # Notificar observers para atualizar UI
                for callback in self._observers[:]:
                    try:
                        callback()
                    except Exception as exc:
                        log.warning(f"[RecentActivityStore] Erro ao notificar observer após erro: {exc}")

        runner.run(load_events, on_success, on_error)

    def get_lines(self) -> list[str]:
        """Retorna lista de eventos (mais recente primeiro).

        Returns:
            Lista de strings de eventos.
        """
        with self._lock:
            # Retornar em ordem reversa (mais recente no topo)
            return list(reversed(self._events))

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Inscreve um observer para receber notificações.

        Args:
            callback: Função a ser chamada quando houver novos eventos.

        Returns:
            Função unsubscribe para remover o observer.
        """
        with self._lock:
            self._observers.append(callback)
            log.debug(f"[RecentActivityStore] Observer inscrito. Total: {len(self._observers)}")

        def unsubscribe() -> None:
            """Remove o observer."""
            with self._lock:
                try:
                    self._observers.remove(callback)
                    log.debug(f"[RecentActivityStore] Observer removido. Total: {len(self._observers)}")
                except ValueError:
                    pass

        return unsubscribe

    def clear(self) -> None:
        """Limpa todos os eventos (útil para testes)."""
        with self._lock:
            self._events.clear()
            log.debug("[RecentActivityStore] Eventos limpos")


# Singleton global
_store_instance: RecentActivityStore | None = None


def get_recent_activity_store() -> RecentActivityStore:
    """Retorna instância singleton do store.

    Returns:
        Instância do RecentActivityStore.
    """
    global _store_instance
    if _store_instance is None:
        _store_instance = RecentActivityStore()
    return _store_instance


def _resolve_actor_name(event: ActivityEvent) -> str:
    """Resolve nome do autor de forma canônica.

    Prioridades:
    1. metadata['user_name'] ou metadata['display_name'] (testes/legacy)
    2. RC_INITIALS_MAP do .env (via authors_service)
    3. AUTHOR_NAMES do authors_service
    4. Prefixo do email (antes do @)
    5. "—" se nada disponível

    Args:
        event: Evento com informações do autor

    Returns:
        Nome formatado do autor
    """
    # 1) metadata user_name / display_name (compatibilidade)
    if event.metadata:
        user_name = event.metadata.get("user_name") or event.metadata.get("display_name")
        if user_name:
            return user_name

    # 2) Se tiver actor_email, resolver via authors_service
    if event.actor_email:
        from src.modules.hub.services.authors_service import load_env_author_names, AUTHOR_NAMES

        key = event.actor_email.strip().lower()

        # Prioridade: RC_INITIALS_MAP do .env
        env_map = load_env_author_names()
        if key in env_map:
            return env_map[key]

        # Fallback: AUTHOR_NAMES hardcoded
        if key in AUTHOR_NAMES:
            return AUTHOR_NAMES[key]

        # Fallback final: prefixo do email
        prefix = key.split("@", 1)[0]
        if prefix:
            return prefix

    # 3) Nada disponível
    return "—"


def format_activity_event(event: ActivityEvent) -> str:
    """Formata ActivityEvent para exibição no mini-histórico.

    Formato em 2 linhas:
    Linha 1: "28/12 - 21:37 (ANVISA) — Cliente | ID: 312 — 07.816.095/0001-65 — AMAFARMA LTDA"
    Linha 2: "REGULARIZAÇÃO CANCELADA — Cancelamento de AFE — por: Júnior"

    Args:
        event: Evento estruturado

    Returns:
        String formatada com 2 linhas (separadas por \n)
    """
    # 1) Data/hora: "28/12 - 21:37" (converter UTC -> local)
    if event.created_at:
        # Converter de UTC para timezone local
        try:
            from datetime import timezone

            # Se created_at já tem tzinfo, usar; senão assumir UTC
            if event.created_at.tzinfo is None:
                dt_utc = event.created_at.replace(tzinfo=timezone.utc)
            else:
                dt_utc = event.created_at

            # Converter para timezone local
            try:
                from zoneinfo import ZoneInfo

                tz_local = ZoneInfo("America/Sao_Paulo")
                dt_local = dt_utc.astimezone(tz_local)
            except Exception:
                # Fallback: usar timezone do sistema
                dt_local = dt_utc.astimezone()

            timestamp = dt_local.strftime("%d/%m - %H:%M")
        except Exception as exc:
            log.debug(f"[format_activity_event] Erro ao converter timezone: {exc}")
            timestamp = event.created_at.strftime("%d/%m - %H:%M")
    else:
        timestamp = datetime.now().strftime("%d/%m - %H:%M")

    # 2) Módulo: "(ANVISA)"
    module = f"({event.module})"

    # 3) Cliente: "Cliente | ID: 312 — 07.816.095/0001-65"
    client_parts = []
    if event.client_id:
        from src.utils.formatters import format_cnpj

        client_id_str = str(event.client_id)
        cnpj_fmt = format_cnpj(event.cnpj) if event.cnpj else ""

        if cnpj_fmt:
            client_parts.append(f"Cliente | ID: {client_id_str} — {cnpj_fmt}")
        else:
            client_parts.append(f"Cliente | ID: {client_id_str}")

    # 4) Razão social (de metadata - leitura robusta)
    razao = ""
    if event.metadata:
        razao = (
            event.metadata.get("razao_social") or event.metadata.get("client_name") or event.metadata.get("razao") or ""
        )

    if razao:
        razao = str(razao).strip()

    # 5) Linha 1: timestamp + módulo + cliente + cnpj + razão
    line1_parts = [timestamp, module]
    if client_parts:
        line1_parts.append(client_parts[0])
    if razao:
        line1_parts.append(razao)

    line1 = " — ".join(line1_parts)

    # 6) Extrair tipo da regularização (após ":")
    base_message = event.message
    if not base_message and event.metadata:
        base_message = event.metadata.get("text") or event.metadata.get("title")
    if not base_message:
        base_message = "—"

    # Extrair tipo após ":"
    if ":" in base_message:
        tipo = base_message.split(":", 1)[1].strip()
    else:
        tipo = base_message.strip()

    if not tipo:
        tipo = "—"

    # 7) Rótulo da ação (para fechadas)
    if event.action == "Cancelada":
        action_label = "REGULARIZAÇÃO CANCELADA"
    elif event.action == "Concluída":
        action_label = "REGULARIZAÇÃO CONCLUÍDA"
    elif event.action == "Excluída":
        action_label = "REGULARIZAÇÃO EXCLUÍDA"
    else:
        action_label = event.action.upper()

    # 8) Autor: "por: Júnior"
    who = _resolve_actor_name(event)

    # 9) Linha 2: ação — tipo — por: autor (trocar ":" por "—")
    line2 = f"{action_label} — {tipo} — por: {who}"

    # 10) Retornar 2 linhas
    return f"{line1}\n{line2}"


def format_anvisa_event(
    action: str,
    client_id: str | None = None,
    cnpj: str | None = None,
    request_type: str | None = None,
    due_date: str | None = None,
    user_name: str | None = None,
) -> str:
    """Formata evento ANVISA para o histórico (legado - mantido para compatibilidade).

    Args:
        action: Ação realizada ("Concluída", "Cancelada", "Excluída")
        client_id: ID do cliente (opcional)
        cnpj: CNPJ do cliente (opcional)
        request_type: Tipo da demanda (opcional)
        due_date: Prazo da demanda (opcional)
        user_name: Nome do usuário que executou a ação (opcional)

    Returns:
        String formatada para o histórico.
    """
    # Timestamp atual
    now = datetime.now()
    timestamp = now.strftime("%d/%m %H:%M")

    # Componentes da linha
    parts = [f"[{timestamp}]", "ANVISA", "—", action]

    # Cliente
    if client_id:
        parts.extend(["—", f"Cliente {client_id}"])

    # CNPJ
    if cnpj:
        parts.extend(["—", f"CNPJ {cnpj}"])

    # Tipo da demanda
    if request_type:
        parts.extend(["—", request_type])

    # Prazo
    if due_date:
        parts.extend(["—", f"Prazo {due_date}"])

    # Usuário
    if user_name:
        parts.extend(["—", f"por {user_name}"])
    else:
        parts.extend(["—", "por —"])

    return " ".join(parts)
