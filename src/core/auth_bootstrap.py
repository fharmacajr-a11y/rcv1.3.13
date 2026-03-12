from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Protocol

from src.db.auth_bootstrap import _get_access_token
from src.modules.login.view import LoginDialog
from src.core.session.session import refresh_current_user_from_supabase
from src.utils import prefs as prefs_utils

try:  # pragma: no cover - fallback for environments without Supabase
    from src.infra.supabase_client import bind_postgrest_auth_if_any, get_supabase
except Exception:  # pragma: no cover
    bind_postgrest_auth_if_any = None  # type: ignore[assignment]
    get_supabase = None  # type: ignore[assignment]

log = logging.getLogger(__name__)
KEEP_LOGGED_DAYS: int = 7

# Flag de boot: sinaliza que a sessão persistida foi invalidada nesta inicialização.
# Garante que o aviso UX seja exibido no máximo uma vez por execução.
_session_invalidated_this_boot: bool = False


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
    layout_refs: Any

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


def _is_network_error(exc: Exception) -> bool:
    """
    Verifica se a exceção é um erro de rede.

    OFFLINE-SUPABASE-UX-001 (Parte B): Helper para detectar erros de conectividade.

    Args:
        exc: Exceção a verificar

    Returns:
        True se for erro de rede (OSError, URLError, ConnectionError, etc.)
    """
    from urllib.error import URLError

    # Verifica tipos de exceção de rede
    if isinstance(exc, (OSError, ConnectionError, TimeoutError)):
        return True

    if isinstance(exc, URLError):
        return True

    # Verifica mensagens comuns de erro de rede
    msg = str(exc).lower()
    network_keywords = [
        "getaddrinfo",
        "connection",
        "timeout",
        "network",
        "unreachable",
        "refused",
        "reset",
        "nodename",
        "temporary failure",
    ]

    return any(keyword in msg for keyword in network_keywords)


def _is_invalid_token_error(exc: Exception) -> bool:
    """
    Detecta erros de refresh token inválido, expirado, revogado ou já usado.

    Palavras-chave baseadas nas mensagens padrão do GoTrue/Supabase.
    """
    msg = str(exc).lower()
    keywords = (
        "refresh token",
        "invalid_grant",
        "token expired",
        "already used",
        "revoked",
        "invalid refresh",
        "token has expired",
        "refresh_token_not_found",
    )
    return any(kw in msg for kw in keywords)


def _refresh_session_state(client: SupabaseClient, logger: Optional[logging.Logger]) -> None:
    """Sincroniza cache local (org_id, usuário) após restaurar sessão."""
    try:
        refresh_current_user_from_supabase()
    except Exception as exc:
        (logger or log).warning("Falha ao hidratar org_id/usuário após sessão restaurada: %s", exc, exc_info=True)


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
        # OFFLINE-SUPABASE-UX-001 (Parte B): Preserva sessão em erros de rede
        if _is_network_error(exc):
            log.warning(
                "Falha ao validar sessão persistida remotamente [network]: %s " "(sessão preservada no storage)",
                exc,
                exc_info=True,
            )
            return False
        # Refresh token inválido/expirado/revogado/já usado: sinaliza UX amigável
        global _session_invalidated_this_boot
        if _is_invalid_token_error(exc):
            _session_invalidated_this_boot = True
        # Erro de autenticação ou desconhecido: limpa sessão
        error_class = "auth" if "invalid" in str(exc).lower() or "expired" in str(exc).lower() else "unknown"
        log.warning(
            "Falha ao validar sessão persistida remotamente [%s]: %s " "(sessão removida do storage)",
            error_class,
            exc,
            exc_info=True,
        )
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
        # UX: Informar usuário sobre problema técnico
        try:
            from tkinter import messagebox

            messagebox.showerror(
                "Erro de Conexão",
                "Não foi possível conectar ao serviço de autenticação.\n\n"
                "Verifique sua conexão com a internet e tente novamente.",
            )
        except Exception as exc:
            (logger or log).debug("Falha ao exibir messagebox de erro: %s", exc)
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

    # OFFLINE-SUPABASE-UX-001 (Parte A): Verifica internet antes de abrir login em cloud-only
    import os
    from src.utils.network import check_internet_connectivity

    is_cloud_only = os.getenv("RC_NO_LOCAL_FS") == "1"
    is_testing = os.getenv("RC_TESTING") == "1" or os.getenv("PYTEST_CURRENT_TEST") is not None

    if is_cloud_only and not is_testing:
        (logger or log).info("Verificando conectividade antes de abrir login (cloud-only)...")
        while not check_internet_connectivity(timeout=1.0):
            (logger or log).warning("Sem internet em modo cloud-only. Exibindo diálogo ao usuário.")
            try:
                from tkinter import messagebox

                retry = messagebox.askretrycancel(
                    "Sem Conexão",
                    "O aplicativo está no modo cloud-only e requer conexão com a internet.\n\n"
                    "Verifique sua conexão e tente novamente.",
                    icon="warning",
                )
                if not retry:
                    (logger or log).info("Usuário cancelou diálogo de reconexão. Encerrando.")
                    return False
                (logger or log).info("Usuário solicitou nova tentativa de conexão (retry).")
            except Exception as exc:
                (logger or log).debug("Falha ao exibir messagebox de offline: %s", exc)
                return False

    # EXPIRED-SESSION-UX: aviso amigável exibido no máximo uma vez por boot
    if _session_invalidated_this_boot:
        (logger or log).info("Sessão persistida invalidada — exibindo aviso de sessão expirada ao usuário.")
        try:
            from tkinter import messagebox

            messagebox.showwarning(
                "Sessão Expirada",
                "Sua sessão expirou ou ficou inválida.\nFaça login novamente.",
            )
        except Exception as _warn_exc:
            (logger or log).debug("Falha ao exibir aviso de sessão expirada: %s", _warn_exc)

    (logger or log).info("Nenhum access_token em memória. Abrindo diálogo de login...")
    dlg = LoginDialog(app)
    app.wait_window(dlg)

    _bind_postgrest(client)
    success = bool(getattr(dlg, "login_success", False))
    if success:
        _refresh_session_state(client, logger)
    return success


def _log_session_snapshot(logger: Optional[logging.Logger]) -> None:
    """Registra snapshot do estado atual da sessão (sem afirmar sucesso/falha)."""
    client = _supabase_client()
    if not client:
        return
    try:
        sess = client.auth.get_session()
        uid = getattr(getattr(sess, "user", None), "id", None)
        has_token = bool(_get_access_token(client))
        token_status = "presente" if has_token else "ausente"
        # Reduzir UUID para prefixo (redação de dados sensíveis)
        uid_prefix = str(uid)[:8] + "..." if uid else "none"
        if has_token:
            (logger or log).info("Sessão ativa: uid=%s, token=%s", uid_prefix, token_status)
        else:
            (logger or log).warning("Nenhuma sessão ativa: uid=%s, token=%s", uid_prefix, token_status)
    except Exception as exc:
        (logger or log).warning("Erro ao verificar estado da sessão: %s", exc, exc_info=True)


def _update_footer_email(app: AppProtocol) -> None:
    """Atualiza o rodapé da UI com o e-mail autenticado (via FooterController)."""
    client = _supabase_client()
    if not client:
        return
    try:
        sess = client.auth.get_session()
        email = getattr(getattr(sess, "user", None), "email", None)
        if not email:
            return

        # FASE 5A FIX: Usar FooterController (sempre existe, aplica via after)
        if hasattr(app, "layout_refs") and app.layout_refs and hasattr(app.layout_refs, "footer_controller"):
            app.layout_refs.footer_controller.set_user(email)
            from src.utils.log_sanitizer import mask_email

            log.info("Footer controller atualizado: %s", mask_email(email))
        elif hasattr(app, "footer") and hasattr(app.footer, "set_user"):
            # Fallback para testes que usam DummyApp com footer direto
            app.footer.set_user(email)
            from src.utils.log_sanitizer import mask_email as _me

            log.debug("Footer direto atualizado: %s", _me(email))
        else:
            log.debug("Footer controller ainda não disponível")
    except Exception as exc:
        log.debug("Falha ao atualizar email no rodapé", exc_info=exc)


def _mark_app_online(app: AppProtocol, logger: Optional[logging.Logger]) -> None:
    """Atualiza indicadores visuais sem exibir a janela (deiconify é responsabilidade do app_gui)."""
    # REMOVIDO: app.deiconify() - isso agora é feito em app_gui.py APÓS ensure_logged retornar True

    try:
        status_monitor = getattr(app, "_status_monitor", None)
        if status_monitor is not None:
            status_monitor.set_cloud_status(True)
    except Exception as exc:
        (logger or log).debug("Erro ao atualizar status de nuvem", exc_info=exc)

    try:
        app._update_user_status()
    except Exception as exc:
        (logger or log).warning("Falha ao atualizar status do usuário: %s", exc, exc_info=True)

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
        log_obj.warning("Erro no fluxo de login: %s", exc, exc_info=True)
        # UX: Informar usuário sobre erro inesperado
        try:
            from tkinter import messagebox

            messagebox.showerror(
                "Erro Inesperado",
                f"Ocorreu um erro durante a autenticação:\n\n{exc}\n\nPor favor, tente novamente ou contate o suporte.",
            )
        except Exception as msg_exc:
            log_obj.debug("Falha ao exibir messagebox de erro inesperado: %s", msg_exc)
        login_ok = False

    _log_session_snapshot(logger)

    if login_ok:
        _mark_app_online(app, logger)
    else:
        # Diferenciar causa do encerramento no log
        log_obj.info("Encerrando aplicação: login não completado.")

    return bool(login_ok)


__all__ = ["ensure_logged", "restore_persisted_auth_session_if_any", "is_persisted_auth_session_valid"]
