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

# Reexport da classe App (migrado de shim para módulo real)
from src.modules.main_window.views.main_window import App

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

    # Cleanup de arquivos temporários antigos no startup
    try:
        from src.modules.uploads.temp_files import cleanup_on_startup

        cleanup_on_startup()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao executar cleanup de temporários: %s", exc)

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

    # PERF-001: Criar app oculto para startup rápida
    # Health check será agendado APÓS login bem-sucedido
    app: App = App(start_hidden=True)

    # Show splash unless --no-splash flag is set
    if not app_args.no_splash:
        splash = show_splash(app)
    else:
        splash = None
        if log:
            log.info("Splash screen skipped (--no-splash)")

    def _continue_after_splash() -> None:
        from src.core.auth_bootstrap import AppProtocol, SplashLike

        # Callback executado APÓS splash fechar e login concluir
        def _on_splash_and_login_done() -> None:
            login_ok = ensure_logged(
                cast(AppProtocol, app),
                splash=cast("SplashLike | None", splash),
                logger=log,
            )
            if login_ok:
                # Só mostrar a janela principal APÓS login bem-sucedido
                try:
                    app.deiconify()  # Torna a janela principal visível
                    app._maximize_window()  # Maximiza a janela
                    if log:
                        log.info("MainWindow exibida e maximizada após login bem-sucedido")
                except Exception as exc:
                    if log:
                        log.debug("Falha ao exibir/maximizar MainWindow: %s", exc)

                # PERF-001: Agendar health check em background APÓS login bem-sucedido
                try:
                    bootstrap.schedule_healthcheck_after_gui(app, logger=log, delay_ms=500)
                except Exception as exc:
                    if log:
                        log.warning("Falha ao agendar healthcheck após login: %s", exc)

                # Agora sim criar/mostrar o Hub
                try:
                    app.show_hub_screen()
                except Exception as exc:
                    if log:
                        log.error("Erro ao carregar UI: %s", exc)
                    app.destroy()
            else:
                # Login cancelado ou falhou (usuário já foi informado via messagebox se foi erro técnico)
                if log:
                    log.info("Encerrando aplicação: login não completado")
                app.destroy()

        _on_splash_and_login_done()

    app.after(1250, _continue_after_splash)
    app.mainloop()
