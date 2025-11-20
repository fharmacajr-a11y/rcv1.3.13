# -*- coding: utf-8 -*-
"""Entry-point fino que reexporta a janela principal."""

from src.core import bootstrap
from src.version import get_version

APP_VERSION = get_version()

bootstrap.configure_environment()
bootstrap.configure_logging(preload=True)

# Reexport da classe App
from src.ui.main_window import App

__all__ = ["App"]


if __name__ == "__main__":
    # Install global exception hook early
    try:
        from src.utils.errors import install_global_exception_hook

        install_global_exception_hook()
    except Exception:
        pass  # Don't fail startup if hook installation fails

    # Parse CLI arguments
    try:
        from src.cli import get_args

        app_args = get_args()
    except Exception:
        # Fallback if CLI parsing fails
        from src.cli import AppArgs

        app_args = AppArgs()

    from src.modules.login.view import show_splash  # Novo diálogo simplificado

    from src.core.auth_bootstrap import ensure_logged

    bootstrap.configure_hidpi()

    log = bootstrap.configure_logging()

    import sys

    if not bootstrap.run_initial_healthcheck(logger=log):
        sys.exit(1)

    app = App(start_hidden=True)

    # Show splash unless --no-splash flag is set
    if not app_args.no_splash:
        splash = show_splash(app, min_ms=1200)
    else:
        splash = None
        log.info("Splash screen skipped (--no-splash)")

    def _continue_after_splash():
        login_ok = ensure_logged(app, splash=splash, logger=log)
        if login_ok:
            try:
                app.show_hub_screen()
            except Exception as exc:
                log.error("Erro ao carregar UI: %s", exc)
                app.destroy()
        else:
            app.destroy()

    app.after(1250, _continue_after_splash)
    app.mainloop()
