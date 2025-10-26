# -*- coding: utf-8 -*-
"""Entry point script for the application."""

if __name__ == "__main__":
    from src.app_gui import App
    import logging
    from src.ui.splash import show_splash
    from src.ui.login_dialog import LoginDialog
    
    # Configuração cloud-only
    import os
    os.environ.setdefault("RC_NO_LOCAL_FS", "1")
    
    # Importações conforme app_gui.py
    try:
        from infra.supabase_client import get_supabase as _get_supabase
        from infra.supabase_client import bind_postgrest_auth_if_any
    except Exception:
        _get_supabase = None
        bind_postgrest_auth_if_any = None
    
    from data.auth_bootstrap import _get_access_token

    def _sb():
        """Helper para obter o client sem estourar escopo"""
        return _get_supabase() if _get_supabase else None

    # Configurar HiDPI no Windows ANTES de criar qualquer Tk
    try:
        from src.utils.helpers import configure_hidpi_support
        configure_hidpi_support()
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
        
        # Verifica se login foi bem-sucedido
        if _get_access_token(client):
            log.info("Login bem-sucedido!")
            return True
        else:
            log.warning("Falha no login ou cancelado pelo usuário.")
            return False

    root = show_splash(
        duration_ms=0,
        wait_for_login=True,
        login_callback=_ensure_logged_ui,
    )
    if root:
        log.info("Iniciando aplicação principal...")
        app = App(root)
        root.mainloop()
    else:
        log.warning("Aplicação não iniciou (splash retornou None).")
