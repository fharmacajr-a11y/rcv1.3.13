# -*- coding: utf-8 -*-

"""Orchestration helpers for HubScreen polling and realtime updates."""

from __future__ import annotations


import threading

from tkinter import messagebox

from typing import Any, Dict, List


from src.core.logger import get_logger

from src.modules.notas import service as notes_service

from src.modules.hub.authors import _author_display_name

from src.modules.hub.colors import _ensure_author_tag

from src.modules.hub.format import _format_note_line, _format_timestamp

from src.modules.hub.state import ensure_state as _ensure_hub_state

from src.modules.hub.utils import _normalize_note


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
    """Program the next polling cycle."""

    hub_state = _ensure_poll_attrs(screen)

    if not getattr(screen, "_live_sync_on", False):
        return

    try:
        if hub_state.poll_job:
            screen.after_cancel(hub_state.poll_job)

    except Exception:
        pass

    hub_state.poll_job = screen.after(ms, lambda: poll_notes_if_needed(screen))


def cancel_poll(screen) -> None:
    """Cancel any pending polling callback."""

    hub_state = _ensure_poll_attrs(screen)

    if hub_state.poll_job:
        try:
            screen.after_cancel(hub_state.poll_job)

        except Exception:
            pass

        hub_state.poll_job = None


def poll_notes_if_needed(screen) -> None:
    """Fallback polling when realtime does not deliver updates."""

    _ensure_poll_attrs(screen)

    if not getattr(screen, "_live_sync_on", False):
        return

    try:
        org_id = getattr(screen, "_live_org_id", None)

        if org_id is None:
            return  # org_id obrigat├│rio para polling

        since = getattr(screen, "_live_last_ts", None)

        new_notes = notes_service.list_notes_since(org_id, since)

        if new_notes:
            for note in new_notes:
                append_note_incremental(screen, note)

            try:
                screen._live_last_ts = max(
                    [
                        screen._live_last_ts or "",
                        *[n.get("created_at") or "" for n in new_notes],
                    ]
                )

            except Exception:
                pass

    except Exception:
        pass

    finally:
        schedule_poll(screen)


def on_realtime_note(screen, payload: Dict[str, Any]) -> None:
    """Handle realtime payload on the UI thread."""

    try:
        screen.after(0, lambda: append_note_incremental(screen, payload))

    except Exception:
        pass


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

    notes = getattr(screen, "_notes_last_data", None) or []

    if any(str(n.get("id")) == str(note.get("id")) for n in notes if n.get("id") is not None):
        return

    notes = notes + [note]

    screen._notes_last_data = notes

    try:
        screen._notes_last_snapshot = [(n.get("id"), n.get("created_at")) for n in notes]

    except Exception:
        pass

    ts_value = note.get("created_at") or ""

    if ts_value and (getattr(screen, "_live_last_ts", "") or "") < ts_value:
        screen._live_last_ts = ts_value

    try:
        screen.notes_history.configure(state="normal")

        email = (note.get("author_email") or "").strip().lower()

        name = (note.get("author_name") or "").strip()

        if not name:
            name = _author_display_name(screen, email)

        tag = None

        try:
            tag = _ensure_author_tag(screen.notes_history, email, hub_state.author_tags)

        except Exception:
            logger.exception("Hub: falha ao aplicar estilo/tag do autor; renderizando sem cor.")

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

    except Exception:
        logger.exception("Hub: falha cr├¡tica ao inserir nota, restaurando estado do widget.")

        try:
            screen.notes_history.configure(state="disabled")

        except Exception:
            pass

    screen._last_render_hash = None


def refresh_notes_async(screen, force: bool = False) -> None:
    """Refresh notes asynchronously using the worker thread."""

    if not getattr(screen, "_polling_active", False):
        return

    if getattr(screen, "_notes_table_missing", False):
        log.debug("HubScreen: Tabela rc_notes ausente, aguardando retry period...")

        screen._notes_after_handle = screen.after(
            getattr(screen, "_notes_retry_ms", 60000),
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
                if getattr(screen, "_polling_active", False):
                    try:
                        screen._notes_after_handle = screen.after(2000, lambda: refresh_notes_async(screen))

                    except Exception:
                        pass

            try:
                screen.after(0, _schedule_transient_retry)

            except Exception:
                pass

            return

        except notes_service.NotesTableMissingError as exc:
            table_missing = True

            log.warning("HubScreen: %s", exc)

            def _notify_table_missing():
                screen._notes_table_missing = True

                if not getattr(screen, "_notes_table_missing_notified", False):
                    screen._notes_table_missing_notified = True

                    try:
                        messagebox.showwarning(
                            "Anota├º├Áes Indispon├¡veis",
                            "Bloco de anota├º├Áes indispon├¡vel:\n\n"
                            "A tabela 'rc_notes' n├úo existe no Supabase.\n"
                            "Execute a migra├º├úo em: migrations/rc_notes_migration.sql\n\n"
                            "Tentaremos novamente em 60 segundos.",
                            parent=screen,
                        )

                    except Exception:
                        pass

            try:
                screen.after(0, _notify_table_missing)

            except Exception:
                pass

            return

        except notes_service.NotesAuthError as exc:
            auth_error = True

            log.warning("HubScreen: %s", exc)

            def _notify_auth_error():
                try:
                    messagebox.showwarning(
                        "Sem Permiss├úo",
                        "Sem permiss├úo para anotar nesta organiza├º├úo.\nVerifique seu cadastro em 'profiles'.",
                        parent=screen,
                    )

                except Exception:
                    pass

            try:
                screen.after(0, _notify_auth_error)

            except Exception:
                pass

            return

        except Exception as exc:
            log.warning("HubScreen: Falha ao listar notas: %s", exc)

        if not table_missing and not auth_error:
            notes = [_normalize_note(x) for x in notes]

            snapshot = [(n.get("id"), n.get("created_at")) for n in notes]

            changed = (snapshot != getattr(screen, "_notes_last_snapshot", None)) or force

            if changed:
                screen._notes_last_snapshot = snapshot

                screen._notes_last_data = notes

                try:
                    screen.after(0, lambda: screen.render_notes(notes))

                except Exception:
                    pass

            if not getattr(screen, "_names_cache_loaded", False):
                screen._names_cache_loaded = True

                try:
                    screen.after(0, screen._refresh_author_names_cache_async)

                except Exception:
                    pass

        if getattr(screen, "_polling_active", False):
            try:
                screen._notes_after_handle = screen.after(
                    getattr(screen, "_notes_poll_ms", 10000),
                    lambda: refresh_notes_async(screen),
                )

            except Exception:
                pass

    threading.Thread(target=_work, daemon=True).start()


def retry_after_table_missing(screen) -> None:
    """Retry refresh after the table was missing previously."""

    log.info("HubScreen: Tentando novamente ap├│s per├¡odo de espera (tabela ausente).")

    screen._notes_table_missing = False

    screen._notes_table_missing_notified = False

    refresh_notes_async(screen, force=True)
