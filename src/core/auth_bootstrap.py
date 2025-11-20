from __future__ import annotations

import logging
from typing import Any, Optional

from data.auth_bootstrap import _get_access_token
from src.modules.login.view import LoginDialog

try:  # pragma: no cover - fallback for environments without Supabase
    from infra.supabase_client import bind_postgrest_auth_if_any, get_supabase
except Exception:  # pragma: no cover
    bind_postgrest_auth_if_any = None  # type: ignore[assignment]
    get_supabase = None  # type: ignore[assignment]

log = logging.getLogger(__name__)


def _supabase_client():
    if callable(get_supabase):
        try:
            return get_supabase()
        except Exception:
            return None
    return None


def _bind_postgrest(client) -> None:
    if bind_postgrest_auth_if_any:
        try:
            bind_postgrest_auth_if_any(client)
        except Exception:
            pass


def _destroy_splash(splash: Any) -> None:
    if splash is None:
        return
    try:
        if splash.winfo_exists():
            splash.destroy()
    except Exception:
        pass


def _ensure_session(app: Any, logger: Optional[logging.Logger]) -> bool:
    client = _supabase_client()
    if not client:
        (logger or log).warning("Cliente Supabase não disponível.")
        return False

    _bind_postgrest(client)

    if _get_access_token(client):
        (logger or log).info("Sessão já existente no boot.")
        return True

    (logger or log).info("Sem sessão inicial - abrindo login...")
    dlg = LoginDialog(app)
    app.wait_window(dlg)

    _bind_postgrest(client)
    return bool(getattr(dlg, "login_success", False))


def _log_session_state(logger: Optional[logging.Logger]) -> None:
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


def _update_footer_email(app: Any) -> None:
    client = _supabase_client()
    if not client:
        return
    try:
        sess = client.auth.get_session()
        email = getattr(getattr(sess, "user", None), "email", None)
        if hasattr(app, "footer") and email:
            app.footer.set_user(email)
    except Exception:
        pass


def _mark_app_online(app: Any, logger: Optional[logging.Logger]) -> None:
    try:
        app.deiconify()
    except Exception:
        pass

    try:
        status_monitor = getattr(app, "_status_monitor", None)
        if status_monitor is not None:
            status_monitor.set_cloud_status(True)
    except Exception:
        pass

    try:
        app._update_user_status()
    except Exception as exc:
        (logger or log).warning("Falha ao atualizar status do usuário: %s", exc)

    _update_footer_email(app)


def ensure_logged(app: Any, *, splash: Any = None, logger: Optional[logging.Logger] = None) -> bool:
    """Coordenar splash/login e devolver True quando a sessão estiver pronta."""
    _destroy_splash(splash)

    login_ok = _ensure_session(app, logger)
    _log_session_state(logger)

    if not login_ok:
        (logger or log).info("Login cancelado ou falhou. Encerrando aplicação.")
        return False

    _mark_app_online(app, logger)
    return True


__all__ = ["ensure_logged"]
