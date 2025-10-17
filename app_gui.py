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
    from utils.resource_path import resource_path
    from dotenv import load_dotenv

    load_dotenv(resource_path(".env"), override=False)  # empacotado
    load_dotenv(os.path.join(os.getcwd(), ".env"), override=True)  # externo sobrescreve
except Exception:
    pass
# --------------------------------------------------------------

# Configurar logging
try:
    from shared.logging.configure import configure_logging

    configure_logging()
except Exception:
    pass

# Reexport da classe App
from gui.main_window import App

__all__ = ["App"]


if __name__ == "__main__":
    import logging
    from gui.splash import show_splash
    from ui.login import LoginDialog

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    log = logging.getLogger("startup")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    app = App(start_hidden=True)

    splash = show_splash(app, min_ms=1200)

    def _open_login_after_splash():
        try:
            if splash.winfo_exists():
                splash.destroy()
        except Exception:
            pass

        dlg = LoginDialog(app)
        app.wait_window(dlg)

        if getattr(dlg, "result", None):
            app.deiconify()
            try:
                app._update_user_status()
                app.show_hub_screen()
            except Exception as e:
                log.error("Erro ao carregar UI: %s", e)
        else:
            app.destroy()

    app.after(1250, _open_login_after_splash)
    app.mainloop()
