# -*- coding: utf-8 -*-

"""Orchestration helpers for HubScreen polling and realtime updates."""

from __future__ import annotations

import threading
from tkinter import messagebox
from typing import Any, Dict, List

from src.core.logger import get_logger
from src.modules.hub.colors import _ensure_author_tag
from src.modules.hub.services.authors_service import get_author_display_name
from src.modules.hub.format import _format_note_line, _format_timestamp
from src.modules.hub.state import ensure_state as _ensure_hub_state
from src.modules.hub.utils import _normalize_note
from src.modules.notas import service as notes_service

logger = get_logger(__name__)

log = logger


def _ensure_poll_attrs(screen):
    hub_state = _ensure_hub_state(screen)

    if hub_state.author_tags is None:
        hub_state.author_tags = {}

    if not hasattr(screen, "_last_render_hash"):
        screen._last_render_hash = None

    return hub_state


def schedule_poll(screen, ms: int = 6000) -> None:
    """Program the next polling cycle.

    BUG-007: Thread-safe scheduling com lock para evitar race condition.
    """
    hub_state = _ensure_poll_attrs(screen)

    # BUG-007: Lock para operações atômicas
    if not hasattr(hub_state, "poll_lock"):
        hub_state.poll_lock = threading.Lock()

    with hub_state.poll_lock:
        if not screen.state.live_sync_on:
            return

        try:
            if hub_state.poll_job:
                screen.after_cancel(hub_state.poll_job)

        except Exception as exc:  # noqa: BLE001
            log.debug("after_cancel failed in schedule_poll: %s", exc)

        hub_state.poll_job = screen.after(ms, lambda: poll_notes_if_needed(screen))


def cancel_poll(screen) -> None:
    """Cancel any pending polling callback.

    BUG-007: Thread-safe cancellation com lock.
    """
    hub_state = _ensure_poll_attrs(screen)

    # BUG-007: Lock para operações atômicas
    if not hasattr(hub_state, "poll_lock"):
        hub_state.poll_lock = threading.Lock()

    with hub_state.poll_lock:
        if hub_state.poll_job:
            try:
                screen.after_cancel(hub_state.poll_job)

            except Exception as exc:  # noqa: BLE001
                log.debug("after_cancel failed in cancel_poll: %s", exc)

            hub_state.poll_job = None


def poll_notes_if_needed(screen) -> None:
    """Fallback polling when realtime does not deliver updates.

    BUG-005: Verifica estado antes de reagendar para evitar loop infinito.
    """
    _ensure_poll_attrs(screen)

    # BUG-005: Verificação early return antes de qualquer processamento
    if not screen.state.live_sync_on:
        return

    try:
        org_id = screen.state.live_org_id

        if org_id is None:
            return  # org_id obrigatório para polling

        since = screen.state.live_last_ts

        new_notes = notes_service.list_notes_since(org_id, since)

        if new_notes:
            for note in new_notes:
                append_note_incremental(screen, note)

            try:
                max_ts = max(
                    [
                        screen.state.live_last_ts or "",
                        *[n.get("created_at") or "" for n in new_notes],
                    ]
                )
                screen.update_live_last_ts(max_ts)

            except Exception as exc:  # noqa: BLE001
                log.debug("Failed to update live_last_ts: %s", exc)

    except Exception as exc:  # noqa: BLE001
        log.debug("poll_notes_if_needed error: %s", exc)

    finally:
        # BUG-005: Verificação de estado antes de reagendar
        if screen.state.live_sync_on:
            schedule_poll(screen)
        else:
            log.debug("Polling interrompido: live_sync_on=False")


def on_realtime_note(screen, payload: Dict[str, Any]) -> None:
    """Handle realtime payload on the UI thread."""

    try:
        screen.after(0, lambda: append_note_incremental(screen, payload))

    except Exception as exc:  # noqa: BLE001
        log.debug("on_realtime_note failed: %s", exc)


def append_note_incremental(screen, row: Dict[str, Any]) -> None:
    """Append a single note without repainting the whole widget."""

    hub_state = _ensure_poll_attrs(screen)

    if not hasattr(screen, "_normalize_note"):

        def _normalize_local(data: Dict[str, Any]) -> Dict[str, Any]:
            email = (data.get("author_email") or "").strip().lower()

            return {
                "id": data.get("id"),
                "created_at": data.get("created_at") or data.get("ts") or "",
                "author_email": email,
                "author_name": (data.get("author_name") or "").strip(),
                "body": (data.get("body") or ""),
            }

        note = _normalize_local(row)

    else:
        note = _normalize_note(row)

    notes = screen.state.notes_last_data or []

    if any(str(n.get("id")) == str(note.get("id")) for n in notes if n.get("id") is not None):
        return

    notes = notes + [note]

    # MF-19: Usar método público do HubScreen (que usa StateManager)
    screen.update_notes_data(notes, update_snapshot=True)

    try:
        pass  # snapshot já foi atualizado em update_notes_data

    except Exception as exc:  # noqa: BLE001
        log.debug("Failed to update _notes_last_snapshot: %s", exc)

    ts_value = note.get("created_at") or ""

    if ts_value and (screen.state.live_last_ts or "") < ts_value:
        # MF-19: Usar método público do HubScreen (que usa StateManager)
        screen.set_live_last_ts(ts_value)

    try:
        screen.notes_history.configure(state="normal")

        email = (note.get("author_email") or "").strip().lower()

        name = (note.get("author_name") or "").strip()

        if not name:
            name = get_author_display_name(screen, email, start_async_fetch=True)

        tag = None

        try:
            tag = _ensure_author_tag(screen.notes_history, email, hub_state.author_tags)

        except Exception as exc:  # noqa: BLE001
            logger.exception("Hub: falha ao aplicar estilo/tag do autor; renderizando sem cor: %s", exc)

            tag = None

        created_at = note.get("created_at")

        if not isinstance(created_at, str):
            created_at = ""  # fallback para string vazia se tipo inesperado

        ts_local = _format_timestamp(created_at)

        body = (note.get("body") or "").rstrip("\n")

        if tag:
            screen.notes_history.insert("end", f"[{ts_local}] ")

            screen.notes_history.insert("end", name, (tag,))

            screen.notes_history.insert("end", f": {body}\n")

        else:
            line = _format_note_line(created_at, name or email, body)

            screen.notes_history.insert("end", f"{line}\n")

        screen.notes_history.configure(state="disabled")

        screen.notes_history.see("end")

    except Exception as exc:  # noqa: BLE001
        logger.exception("Hub: falha crítica ao inserir nota, restaurando estado do widget: %s", exc)

        try:
            screen.notes_history.configure(state="disabled")

        except Exception as exc2:  # noqa: BLE001
            log.debug("configure(state=disabled) failed: %s", exc2)

    screen._last_render_hash = None


def refresh_notes_async(screen, force: bool = False) -> None:
    """Refresh notes asynchronously using the worker thread."""

    if not screen.state.polling_active:
        return

    if screen.state.notes_table_missing:
        log.debug("HubScreen: Tabela rc_notes ausente, aguardando retry period...")

        screen._notes_after_handle = screen.after(
            screen.state.notes_retry_ms,
            lambda: retry_after_table_missing(screen),
        )

        return

    auth_retry_ms = getattr(screen, "AUTH_RETRY_MS", 2000)

    if not screen._auth_ready():
        log.debug("HubScreen: Autentica├º├úo n├úo pronta para refresh_notes, aguardando...")

        screen._notes_after_handle = screen.after(auth_retry_ms, lambda: refresh_notes_async(screen, force))

        return

    org_id = screen._get_org_id_safe()

    if not org_id:
        log.debug("HubScreen: org_id n├úo dispon├¡vel para refresh_notes, aguardando...")

        screen._notes_after_handle = screen.after(auth_retry_ms, lambda: refresh_notes_async(screen, force))

        return

    def _work():
        notes: List[Dict[str, Any]] = []

        table_missing = False

        auth_error = False

        try:
            notes = notes_service.list_notes(org_id, limit=500)

        except notes_service.NotesTransientError:
            log.debug("HubScreen: Erro transit├│rio ao listar notas, retry em 2s")

            def _schedule_transient_retry():
                if screen.state.polling_active:
                    try:
                        screen._notes_after_handle = screen.after(2000, lambda: refresh_notes_async(screen))

                    except Exception as exc:  # noqa: BLE001
                        log.debug("after() failed for transient retry: %s", exc)

            try:
                screen.after(0, _schedule_transient_retry)

            except Exception as exc:  # noqa: BLE001
                log.debug("after(0) failed for transient retry: %s", exc)

            return

        except notes_service.NotesTableMissingError as exc:
            table_missing = True

            log.warning("HubScreen: %s", exc)

            def _notify_table_missing():
                # MF-19: Usar método público do HubScreen (que usa StateManager)
                screen.set_notes_table_missing(True)

                if not screen.state.notes_table_missing_notified:
                    screen.set_notes_table_missing_notified(True)

                    try:
                        messagebox.showwarning(
                            "Anotações Indisponíveis",
                            "Bloco de anotações indisponível:\n\n"
                            "A tabela 'rc_notes' não existe no Supabase.\n"
                            "Execute a migração em: migrations/rc_notes_migration.sql\n\n"
                            "Tentaremos novamente em 60 segundos.",
                            parent=screen,
                        )

                    except Exception as exc:  # noqa: BLE001
                        log.debug("messagebox.showwarning failed for table missing: %s", exc)

            try:
                screen.after(0, _notify_table_missing)

            except Exception as exc:  # noqa: BLE001
                log.debug("after(0) failed for _notify_table_missing: %s", exc)

            return

        except notes_service.NotesAuthError as exc:
            auth_error = True

            log.warning("HubScreen: %s", exc)

            def _notify_auth_error():
                try:
                    messagebox.showwarning(
                        "Sem Permissão",
                        "Sem permissão para anotar nesta organização.\nVerifique seu cadastro em 'profiles'.",
                        parent=screen,
                    )

                except Exception as exc:  # noqa: BLE001
                    log.debug("messagebox.showwarning failed for auth error: %s", exc)

            try:
                screen.after(0, _notify_auth_error)

            except Exception as exc:  # noqa: BLE001
                log.debug("after(0) failed for _notify_auth_error: %s", exc)

            return

        except Exception as exc:
            log.warning("HubScreen: Falha ao listar notas: %s", exc)

        if not table_missing and not auth_error:
            notes = [_normalize_note(x) for x in notes]

            snapshot = [(n.get("id"), n.get("created_at")) for n in notes]

            changed = (snapshot != screen.state.notes_last_snapshot) or force

            if changed:
                # MF-19: Usar método público do HubScreen (que usa StateManager)
                screen.update_notes_data(notes, update_snapshot=True)

                try:
                    screen.after(0, lambda: screen.render_notes(notes))

                except Exception as exc:  # noqa: BLE001
                    log.debug("after(0) failed for render_notes: %s", exc)

            if not screen.state.names_cache_loaded:
                # MF-19: Usar método público do HubScreen (que usa StateManager)
                screen.set_names_cache_loaded(True)

                try:
                    screen.after(0, screen._refresh_author_names_cache_async)

                except Exception as exc:  # noqa: BLE001
                    log.debug("after(0) failed for _refresh_author_names_cache_async: %s", exc)

        if screen.state.polling_active:
            try:
                screen._notes_after_handle = screen.after(
                    getattr(screen, "_notes_poll_ms", 10000),
                    lambda: refresh_notes_async(screen),
                )

            except Exception as exc:  # noqa: BLE001
                log.debug("after() failed for next poll schedule: %s", exc)

    threading.Thread(target=_work, daemon=True).start()


def retry_after_table_missing(screen) -> None:
    """Retry refresh after the table was missing previously."""

    log.info("HubScreen: Tentando novamente após período de espera (tabela ausente).")

    # MF-19: Usar método público do HubScreen (que usa StateManager)
    screen.set_notes_table_missing(False)

    screen.set_notes_table_missing_notified(False)

    refresh_notes_async(screen, force=True)
