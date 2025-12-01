from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Protocol

from data.auth_bootstrap import _get_access_token
from src.modules.login.view import LoginDialog
from src.core.session.session import refresh_current_user_from_supabase
from src.utils import prefs as prefs_utils

try:  # pragma: no cover - fallback for environments without Supabase
    from infra.supabase_client import bind_postgrest_auth_if_any, get_supabase
except Exception:  # pragma: no cover
    bind_postgrest_auth_if_any = None  # type: ignore[assignment]
    get_supabase = None  # type: ignore[assignment]

log = logging.getLogger(__name__)
KEEP_LOGGED_DAYS: int = 7


class SplashLike(Protocol):
    """Interface mínima esperada de uma splash screen Tk."""

    def winfo_exists(self) -> bool: ...

    def destroy(self) -> None: ...

    def close(self, on_closed: Optional[Callable[[], None]] = None) -> None:  # pragma: no cover - implementações Tk
        ...


class SupabaseAuthApi(Protocol):
    """Subconjunto das operações de auth utilizadas pelo bootstrap."""

    def get_session(self) -> Any: ...

    def set_session(self, access_token: str, refresh_token: str) -> None: ...


class SupabaseClient(Protocol):
    """Cliente Supabase com operações de auth."""

    auth: SupabaseAuthApi


class AppProtocol(Protocol):
    """Operações do app principal usadas durante o bootstrap."""

    footer: Any
    _status_monitor: Any

    def wait_window(self, window: Any) -> None: ...

    def deiconify(self) -> None: ...

    def _update_user_status(self) -> None: ...


def _supabase_client() -> Optional[SupabaseClient]:
    """Retorna o cliente Supabase se disponível."""
    if callable(get_supabase):
        try:
            return get_supabase()
        except Exception:
            return None
    return None


def _bind_postgrest(client: Any) -> None:
    """Configura o PostgREST com tokens atuais, ignorando falhas."""
    if bind_postgrest_auth_if_any:
        try:
            bind_postgrest_auth_if_any(client)
        except Exception as exc:
            log.debug("Falha ao bind_postgrest_auth_if_any", exc_info=exc)


def _destroy_splash(splash: SplashLike | None, on_closed: Optional[Callable[[], None]] = None) -> None:
    """Fecha a splash screen, chamando callback ao final se fornecido."""
    if splash is None:
        if on_closed is not None:
            try:
                on_closed()
            except Exception as exc:
                log.debug("Erro ao executar callback de splash inexistente", exc_info=exc)
        return
    try:
        close_fn = getattr(splash, "close", None)
        if callable(close_fn):
            close_fn(on_closed=on_closed)
            return
        if splash.winfo_exists():
            splash.destroy()
        if on_closed is not None:
            try:
                on_closed()
            except Exception as exc:
                log.debug("Erro ao executar callback pós-destroy", exc_info=exc)
    except Exception as exc:
        log.debug("Erro ao destruir splash", exc_info=exc)


def _refresh_session_state(client: SupabaseClient, logger: Optional[logging.Logger]) -> None:
    """Sincroniza cache local (org_id, usuário) após restaurar sessão."""
    try:
        refresh_current_user_from_supabase()
    except Exception as exc:
        (logger or log).warning("Falha ao hidratar org_id/usuário após sessão restaurada: %s", exc)


AuthSessionData = Mapping[str, Any]


def is_persisted_auth_session_valid(
    data: AuthSessionData,
    now: datetime | None = None,
    max_age_days: int = KEEP_LOGGED_DAYS,
) -> bool:
    """Valida payload persistido de auth (tokens + created_at)."""
    if not data:
        return False

    access_token = str(data.get("access_token") or "").strip()
    refresh_token = str(data.get("refresh_token") or "").strip()
    created_at_raw = str(data.get("created_at") or "").strip()
    keep_logged = bool(data.get("keep_logged", False))

    if not keep_logged or not access_token or not refresh_token or not created_at_raw:
        return False

    if now is None:
        now = datetime.now(timezone.utc)

    try:
        created_at = datetime.fromisoformat(created_at_raw)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
    except Exception:
        return False

    max_age = timedelta(days=max_age_days)
    return now - created_at <= max_age


def restore_persisted_auth_session_if_any(client: SupabaseClient) -> bool:
    """
    Tenta restaurar sessão Supabase a partir de auth_session.json.
    Retorna True se conseguiu aplicar uma sessão válida; False caso contrário.
    """
    try:
        data = prefs_utils.load_auth_session()
    except Exception as exc:
        log.warning("Falha ao ler sessão persistida: %s", exc, exc_info=True)
        return False

    if not is_persisted_auth_session_valid(data):
        try:
            prefs_utils.clear_auth_session()
        except Exception as exc:
            log.debug("Falha ao limpar sessão inválida", exc_info=exc)
        return False

    access_token = str(data.get("access_token") or "").strip()
    refresh_token = str(data.get("refresh_token") or "").strip()
    if not access_token or not refresh_token:
        try:
            prefs_utils.clear_auth_session()
        except Exception as exc:
            log.debug("Falha ao limpar sessão sem token", exc_info=exc)
        return False

    try:
        client.auth.set_session(access_token, refresh_token)
        return True
    except Exception as exc:
        log.warning("Erro ao restaurar sessão persistida: %s", exc, exc_info=True)
        try:
            prefs_utils.clear_auth_session()
        except Exception as clear_exc:
            log.debug("Falha ao limpar sessão após erro de set_session", exc_info=clear_exc)
        return False


def _ensure_session(app: AppProtocol, logger: Optional[logging.Logger]) -> bool:
    """Garante que exista uma sessão autenticada, abrindo login se necessário."""
    client = _supabase_client()
    if not client:
        (logger or log).warning("Cliente Supabase não disponível.")
        return False

    try:
        restore_persisted_auth_session_if_any(client)
    except Exception as exc:
        (logger or log).debug("Erro ao tentar restaurar sessão persistida", exc_info=exc)

    _bind_postgrest(client)

    if _get_access_token(client):
        (logger or log).info("Sessão já existente no boot.")
        _refresh_session_state(client, logger)
        return True

    (logger or log).info("Sem sessão inicial - abrindo login...")
    dlg = LoginDialog(app)
    app.wait_window(dlg)

    _bind_postgrest(client)
    success = bool(getattr(dlg, "login_success", False))
    if success:
        _refresh_session_state(client, logger)
    return success


def _log_session_state(logger: Optional[logging.Logger]) -> None:
    """Registra informações básicas sobre a sessão ativa (quando houver)."""
    client = _supabase_client()
    if not client:
        return
    try:
        sess = client.auth.get_session()
        uid = getattr(getattr(sess, "user", None), "id", None)
        token_status = "presente" if _get_access_token(client) else "ausente"
        (logger or log).info("Sessão inicial: uid=%s, token=%s", uid, token_status)
    except Exception as exc:
        (logger or log).warning("Erro ao verificar sessão inicial: %s", exc)


def _update_footer_email(app: AppProtocol) -> None:
    """Atualiza o rodapé da UI com o e-mail autenticado."""
    client = _supabase_client()
    if not client:
        return
    try:
        sess = client.auth.get_session()
        email = getattr(getattr(sess, "user", None), "email", None)
        if hasattr(app, "footer") and email:
            app.footer.set_user(email)
    except Exception as exc:
        log.debug("Falha ao atualizar email no rodapé", exc_info=exc)


def _mark_app_online(app: AppProtocol, logger: Optional[logging.Logger]) -> None:
    """Restaura a janela principal e atualiza indicadores visuais."""
    try:
        app.deiconify()
    except Exception as exc:
        (logger or log).debug("Falha ao restaurar janela principal", exc_info=exc)

    try:
        status_monitor = getattr(app, "_status_monitor", None)
        if status_monitor is not None:
            status_monitor.set_cloud_status(True)
    except Exception as exc:
        (logger or log).debug("Erro ao atualizar status de nuvem", exc_info=exc)

    try:
        app._update_user_status()
    except Exception as exc:
        (logger or log).warning("Falha ao atualizar status do usuário: %s", exc)

    _update_footer_email(app)


def ensure_logged(
    app: AppProtocol, *, splash: Optional[SplashLike] = None, logger: Optional[logging.Logger] = None
) -> bool:
    """Fluxo linear: fecha splash (se houver), executa login e marca app online."""
    log_obj = logger or log

    if splash is not None:
        try:
            _destroy_splash(splash)
        except Exception as exc:  # noqa: BLE001
            log_obj.debug("Erro ao solicitar fechamento do splash", exc_info=exc)
        try:
            app.wait_window(splash)
        except Exception as exc:  # noqa: BLE001
            log_obj.debug("Erro ao aguardar splash encerrar", exc_info=exc)

    try:
        login_ok = _ensure_session(app, logger)
    except Exception as exc:  # noqa: BLE001
        log_obj.warning("Erro no fluxo de login: %s", exc)
        login_ok = False

    _log_session_state(logger)

    if login_ok:
        _mark_app_online(app, logger)
    else:
        log_obj.info("Login cancelado ou falhou. Encerrando aplicação.")

    return bool(login_ok)


__all__ = ["ensure_logged", "restore_persisted_auth_session_if_any", "is_persisted_auth_session_valid"]
