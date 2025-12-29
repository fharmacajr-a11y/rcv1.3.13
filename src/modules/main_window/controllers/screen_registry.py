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
    from src.modules.clientes import ClientesFrame, DEFAULT_ORDER_LABEL, ORDER_CHOICES
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

    # Main (Clientes) - criar nova instância sempre
    def _create_main() -> Any:
        frame = ClientesFrame(
            app._content_container,
            app=app,
            on_new=app.novo_cliente,
            on_edit=app.editar_cliente,
            on_delete=app._excluir_cliente,
            on_upload=app.enviar_para_supabase,
            on_open_subpastas=app.open_client_storage_subfolders,
            on_open_lixeira=app.abrir_lixeira,
            on_obrigacoes=app.abrir_obrigacoes_cliente,
            order_choices=ORDER_CHOICES,
            default_order_label=DEFAULT_ORDER_LABEL,
            on_upload_folder=app.enviar_pasta_supabase,
        )
        app._main_frame_ref = frame  # Manter referência legacy

        # FIX: Carregamento assíncrono para evitar travamento da UI
        # Agenda com after(1) para garantir que o primeiro paint aconteça
        def _safe_load_async() -> None:
            try:
                if not frame.winfo_exists():
                    return
                # Usar carregar_async() que não trava a UI
                frame.carregar_async()
            except AttributeError:
                # Fallback se carregar_async não existir (backwards compatibility)
                _log.warning("carregar_async não disponível, usando carregar() síncrono")
                try:
                    frame.carregar()
                except Exception:
                    _log.exception("Clientes: erro em carregar() (fallback).")
            except Exception:
                _log.exception("Clientes: erro em carregar_async().")

        # Agendar para após o primeiro paint (after(1) garante que UI seja mostrada primeiro)
        try:
            frame.after(1, _safe_load_async)
        except Exception:
            # Fallback ultra seguro (se after falhar)
            _log.exception("Clientes: falha ao agendar carregamento; usando fallback síncrono.")
            try:
                frame.carregar()
            except Exception:
                _log.exception("Clientes: erro ao carregar lista (fallback).")

        return frame

    router.register("main", _create_main, cache=False)

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
