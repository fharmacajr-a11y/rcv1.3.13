# -*- coding: utf-8 -*-
"""Entry-point fino que reexporta a janela principal."""
import os

# Configuração cloud-only
os.environ.setdefault("RC_NO_LOCAL_FS", "1")
try:
    pass  # ensures cloud-only paths
except Exception:
    pass

# -------- Loader de .env (suporta PyInstaller onefile) --------
try:
    from src.utils.resource_path import resource_path
    from dotenv import load_dotenv

    load_dotenv(resource_path(".env"), override=False)  # empacotado
    load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)  # externo sobrescreve
except Exception:
    pass
# --------------------------------------------------------------

# Configurar logging
try:
    from src.core.logs.configure import configure_logging

    configure_logging()
except Exception:
    pass

# Reexport da classe App
from src.ui.main_window import App

__all__ = ["App"]


if __name__ == "__main__":
    import logging
    from src.ui.splash import show_splash
    from src.ui.login_dialog import LoginDialog  # Novo diálogo simplificado
    # [startup-fix] import seguro do supabase
    try:
        from infra.supabase_client import get_supabase as _get_supabase
        from infra.supabase_client import bind_postgrest_auth_if_any
    except Exception:
        _get_supabase = None
        bind_postgrest_auth_if_any = None
    
    from data.auth_bootstrap import _get_access_token

    def _sb():
        """[startup-fix] helper para obter o client sem estourar escopo"""
        return _get_supabase() if _get_supabase else None

    # Configurar HiDPI no Windows ANTES de criar qualquer Tk
    # Referência: https://ttkbootstrap.readthedocs.io/en/latest/api/utility/enable_high_dpi_awareness/
    try:
        from src.utils.helpers import configure_hidpi_support

        configure_hidpi_support()  # Windows: chamar sem parâmetros antes do Tk
    except Exception:
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log = logging.getLogger("startup")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    # Log timezone local detectado
    try:
        import tzlocal  # type: ignore[import-not-found]
        from datetime import datetime
        tz = tzlocal.get_localzone()
        log.info("Timezone local detectado: %s (agora: %s)", tz, datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        log.info("Timezone local não detectado; usando hora do sistema.")

    def _ensure_logged_ui(root):
        """Garante que existe sessão válida, abrindo login se necessário."""
        # [startup-fix] usa helper _sb() ao invés de get_supabase direto
        client = _sb()
        if not client:
            log.warning("Cliente Supabase não disponível.")
            return False
        
        if bind_postgrest_auth_if_any:
            bind_postgrest_auth_if_any(client)
        
        if _get_access_token(client):
            log.info("Sessão já existente no boot.")
            return True
        
        # Abre diálogo de login
        log.info("Sem sessão inicial - abrindo login...")
        dlg = LoginDialog(root)
        root.wait_window(dlg)
        
        if bind_postgrest_auth_if_any:
            bind_postgrest_auth_if_any(client)
        
        return getattr(dlg, "login_success", False)

    app = App(start_hidden=True)

    splash = show_splash(app, min_ms=1200)

    def _open_login_after_splash():
        try:
            if splash.winfo_exists():
                splash.destroy()
        except Exception:
            pass

        # Garantir login antes de mostrar a app
        login_ok = _ensure_logged_ui(app)
        
        # Log da sessão após login
        try:
            # [startup-fix] usa helper _sb() ao invés de get_supabase direto
            client = _sb()
            if client:
                sess = client.auth.get_session()
                uid = getattr(sess, "user", None) and getattr(sess.user, "id", None)
                token_status = "presente" if _get_access_token(client) else "ausente"
                log.info("Sessão inicial: uid=%s, token=%s", uid, token_status)
        except Exception as e:
            log.warning("Erro ao verificar sessão inicial: %s", e)

        if login_ok:
            # Login bem-sucedido: exibir janela principal
            app.deiconify()
            try:
                # Atualizar status de nuvem (online) - e-mail aparece via _user_status_suffix()
                if hasattr(app, "_status_monitor"):
                    app._status_monitor.set_cloud_status(True)
                
                app._update_user_status()
                
                # Atualizar email no rodapé
                try:
                    # [startup-fix] usa helper _sb() ao invés de get_supabase direto
                    client = _sb()
                    if client:
                        sess = client.auth.get_session()
                        email = getattr(getattr(sess, "user", None), "email", None)
                        if hasattr(app, "footer") and email:
                            app.footer.set_user(email)
                except Exception:
                    pass
                
                app.show_hub_screen()
            except Exception as e:
                log.error("Erro ao carregar UI: %s", e)
                app.destroy()
        else:
            # Login cancelado ou falhou: NÃO permite app sem autenticação
            log.info("Login cancelado ou falhou. Encerrando aplicação.")
            app.destroy()

    app.after(1250, _open_login_after_splash)
    app.mainloop()
