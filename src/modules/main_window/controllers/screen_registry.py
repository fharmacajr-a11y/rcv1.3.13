# -*- coding: utf-8 -*-
"""Screen Registry para MainWindow - centraliza registro de todas as telas.

REFATORAÇÃO P2-MF3B:
- Extração do método _register_screens() do MainWindow
- Centraliza factories de telas em módulo próprio
- Mantém comportamento idêntico, sem recursão
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.modules.main_window.controllers import ScreenRouter
    from src.modules.main_window.views.main_window import App

_log = logging.getLogger(__name__)


def register_main_window_screens(router: ScreenRouter, app: App) -> None:
    """Registra todas as telas do MainWindow no router.

    Args:
        router: ScreenRouter onde as telas serão registradas
        app: Instância do MainWindow para callbacks e referências

    Nota:
        Factories NÃO devem chamar show_* ou navigate_to para evitar recursão.
        Usam router.show() diretamente quando necessário.
    """
    from src.modules.anvisa import AnvisaScreen
    from src.modules.auditoria import AuditoriaFrame
    from src.modules.cashflow import CashflowFrame
    from src.modules.clientes_v2 import ClientesV2Frame
    from src.modules.notas import HubFrame
    from src.modules.passwords import PasswordsFrame
    from src.modules.sites import SitesScreen
    from src.ui.placeholders import ComingSoonScreen

    # Hub (singleton cacheado)
    def _create_hub() -> Any:
        frame = HubFrame(
            app._content_container,
            open_clientes=app.show_main_screen,
            open_anvisa=lambda: router.show("anvisa"),
            open_auditoria=lambda: router.show("auditoria"),
            open_sngpc=lambda: app.show_placeholder_screen("SNGPC"),
            open_senhas=app.show_passwords_screen,
            open_cashflow=app.show_cashflow_screen,
            open_sites=app.show_sites_screen,
        )
        app._hub_screen_instance = frame  # Manter referência legacy

        # BUGFIX-UX-STARTUP-HUB-001 (C2): after_idle para on_show evitar travar primeiro paint
        # Em vez de chamar on_show() sincronamente, agendamos para após o frame estar pronto
        try:
            frame.after_idle(frame.on_show)
        except Exception as exc:
            _log.warning("Erro ao agendar on_show do Hub: %s", exc)
        return frame

    router.register("hub", _create_hub, cache=True)

    # Main (Clientes) - ClientesV2 moderna (cache=True)
    def _create_main() -> Any:
        _log.info("🆕 [ClientesV2] Carregando tela Clientes (versão moderna)")
        frame = ClientesV2Frame(
            master=app._content_container,
            app=app,  # FIX P0 #4: Injetar referência ao MainWindow para ações funcionarem
        )
        app._main_frame_ref = frame  # Manter referência legacy
        app.force_redraw = frame.force_redraw  # Registrar callback de redesenho
        return frame

    router.register("main", _create_main, cache=True)

    # Passwords (singleton cacheado)
    def _create_passwords() -> Any:
        if app._passwords_screen_instance is None:
            app._passwords_screen_instance = PasswordsFrame(
                app._content_container,
                main_window=app,
            )
        frame = app._passwords_screen_instance
        try:
            frame.on_show()
        except Exception:
            _log.exception("Erro ao chamar on_show da tela de senhas")
        return frame

    router.register("passwords", _create_passwords, cache=True)

    # Cashflow (criar nova sempre)
    def _create_cashflow() -> Any:
        return CashflowFrame(app._content_container, app=app)

    router.register("cashflow", _create_cashflow, cache=False)

    # Sites (criar nova sempre)
    def _create_sites() -> Any:
        return SitesScreen(app._content_container)

    router.register("sites", _create_sites, cache=False)

    # ANVISA (singleton cacheado)
    def _create_anvisa() -> Any:
        if not hasattr(app, "_anvisa_screen_instance") or app._anvisa_screen_instance is None:
            app._anvisa_screen_instance = AnvisaScreen(
                app._content_container,
                main_window=app,
                on_back=app.show_hub_screen,
            )
        return app._anvisa_screen_instance

    router.register("anvisa", _create_anvisa, cache=True)

    # Auditoria (criar nova sempre)
    def _create_auditoria() -> Any:
        return AuditoriaFrame(
            app._content_container,
            go_back=app.show_hub_screen,
        )

    router.register("auditoria", _create_auditoria, cache=False)

    # Placeholder (criar nova sempre, lê title de app._placeholder_title)
    def _create_placeholder() -> Any:
        title = getattr(app, "_placeholder_title", None) or "Em Desenvolvimento"
        return ComingSoonScreen(
            app._content_container,
            title=title,
            on_back=app.show_hub_screen,
        )

    router.register("placeholder", _create_placeholder, cache=False)

    _log.debug("Registradas 8 telas no ScreenRouter")
