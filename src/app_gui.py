# -*- coding: utf-8 -*-
"""Entry-point fino que reexporta a janela principal."""

import logging
import tkinter as tk
from typing import Optional, cast

from src.core import bootstrap
from src.version import get_version

logger = logging.getLogger(__name__)

APP_VERSION: str = get_version()

bootstrap.configure_environment()
bootstrap.configure_logging(preload=True)

# Reexport da classe App
from src.ui.main_window import App

__all__ = ["App", "apply_rc_icon"]


def apply_rc_icon(window: tk.Misc) -> None:
    """Aplica o mesmo ícone RC usado na janela principal em um Toplevel.

    Seguro de chamar várias vezes. Em caso de erro, não quebra a janela.
    Copia a mesma lógica de main_window.py para garantir consistência.
    """
    import os

    try:
        from src.modules.main_window.views.constants import APP_ICON_PATH
        from src.modules.main_window.views.helpers import resource_path

        icon_path = resource_path(APP_ICON_PATH)
        if os.path.exists(icon_path):
            try:
                window.iconbitmap(icon_path)  # type: ignore[attr-defined]
                # FIX-SENHAS-013: Também define como default para messageboxes
                try:
                    window.iconbitmap(default=icon_path)  # type: ignore[attr-defined]
                except Exception:
                    logger.debug("Falha ao configurar ícone como default para messageboxes", exc_info=True)
            except Exception:
                try:
                    img = tk.PhotoImage(file=icon_path)
                    window.iconphoto(True, img)  # type: ignore[attr-defined]
                    # Manter referência para evitar garbage collection
                    window._rc_icon_img = img  # type: ignore[attr-defined]
                except Exception:
                    logger.debug("Falha ao carregar ícone PNG como fallback", exc_info=True)
    except Exception:
        # Não queremos quebrar a UI porque o ícone falhou
        logger.debug("Falha geral ao aplicar ícone RC", exc_info=True)


if __name__ == "__main__":
    # Install global exception hook early
    try:
        from src.utils.errors import install_global_exception_hook

        install_global_exception_hook()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao instalar global exception hook: %s", exc)

    # Parse CLI arguments
    try:
        from src.cli import get_args

        app_args = get_args()
    except Exception as exc:  # noqa: BLE001
        # Fallback if CLI parsing fails
        from src.cli import AppArgs

        app_args = AppArgs()
        logger.warning("Falha ao processar argumentos de linha de comando: %s", exc)

    from src.modules.login.view import show_splash  # Novo diálogo simplificado

    from src.core.auth_bootstrap import ensure_logged

    bootstrap.configure_hidpi()

    log: Optional[logging.Logger] = bootstrap.configure_logging()

    # PERF-001: Criar app ANTES do health check para startup rápida
    app: App = App(start_hidden=True)

    # PERF-001: Health check em background (não bloqueia startup)
    bootstrap.schedule_healthcheck_after_gui(app, logger=log, delay_ms=500)

    # Show splash unless --no-splash flag is set
    if not app_args.no_splash:
        splash = show_splash(app)
    else:
        splash = None
        if log:
            log.info("Splash screen skipped (--no-splash)")

    def _continue_after_splash() -> None:
        from src.core.auth_bootstrap import AppProtocol, SplashLike

        login_ok = ensure_logged(
            cast(AppProtocol, app),
            splash=cast("SplashLike | None", splash),
            logger=log,
        )
        if login_ok:
            try:
                app.show_hub_screen()
            except Exception as exc:
                if log:
                    log.error("Erro ao carregar UI: %s", exc)
                app.destroy()
        else:
            app.destroy()

    app.after(1250, _continue_after_splash)
    app.mainloop()
