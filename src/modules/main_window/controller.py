from __future__ import annotations

import logging
from tkinter import messagebox
from typing import Any, Callable, Optional

import time

from src.modules.notas import HubFrame

log = logging.getLogger("app_gui")

__all__ = ["create_frame", "navigate_to", "tk_report", "start_client_pick_mode"]

LEGACY_PICK_MODE_BANNER_TEXT = "Modo seleção: escolha um cliente para continuar"


def _forget_widget(widget: Optional[Any]) -> None:
    """Remove widget do layout usando o geometry manager correto.

    Detecta automaticamente se widget usa pack, place ou grid
    e chama o método _forget() apropriado.
    """
    if widget is None:
        return

    try:
        mgr = widget.winfo_manager()
    except Exception as exc:  # noqa: BLE001
        log.debug("winfo_manager() failed: %s", exc)
        mgr = ""

    # Usar o método correto baseado no manager detectado
    if mgr == "pack":
        try:
            widget.pack_forget()
            log.debug("pack_forget() succeeded")
            return
        except Exception as exc:  # noqa: BLE001
            log.debug("pack_forget() failed: %s", exc)
    elif mgr == "place":
        try:
            widget.place_forget()
            log.debug("place_forget() succeeded")
            return
        except Exception as exc:  # noqa: BLE001
            log.debug("place_forget() failed: %s", exc)
    elif mgr == "grid":
        try:
            widget.grid_forget()
            log.debug("grid_forget() succeeded")
            return
        except Exception as exc:  # noqa: BLE001
            log.debug("grid_forget() failed: %s", exc)
    elif mgr == "":
        log.debug("widget already forgotten (no manager)")
        return

    # Fallback: tentar pack_forget e place_forget (segurança)
    try:
        widget.pack_forget()
        log.debug("fallback pack_forget() succeeded")
    except Exception as exc:  # noqa: BLE001
        log.debug("fallback pack_forget() failed: %s", exc)
        try:
            widget.place_forget()
            log.debug("fallback place_forget() succeeded")
        except Exception as exc2:  # noqa: BLE001
            log.debug("fallback place_forget() also failed: %s", exc2)


def _lift_widget(widget: Any) -> None:
    try:
        widget.lift()
    except Exception as exc:  # noqa: BLE001
        log.debug("widget.lift() failed: %s", exc)


def _place_or_pack(widget: Any) -> None:
    try:
        widget.place(relx=0, rely=0, relwidth=1, relheight=1)
    except Exception as exc:  # noqa: BLE001
        log.debug("widget.place() failed, trying pack: %s", exc)
        try:
            widget.pack(fill="both", expand=True)
        except Exception as exc2:  # noqa: BLE001
            log.debug("widget.pack() also failed: %s", exc2)


def create_frame(app: Any, frame_cls: Any, options: Optional[dict[str, Any]]) -> Any:
    """Replica a antiga logica de _frame_factory mantendo comportamento."""
    options = options or {}
    current = getattr(app.nav, "current", lambda: None)()

    if frame_cls is HubFrame:
        if getattr(app, "_hub_screen_instance", None) is None:
            app._hub_screen_instance = HubFrame(app._content_container, **options)
            _place_or_pack(app._hub_screen_instance)

        frame = app._hub_screen_instance

        if current is not None and current is not frame:
            _forget_widget(current)

        _lift_widget(frame)

        try:
            frame.on_show()
        except Exception as exc:
            log.warning("Erro ao chamar on_show do Hub: %s", exc)

        return frame

    try:
        if callable(frame_cls) and not isinstance(frame_cls, type):
            frame = frame_cls(app._content_container)
        else:
            frame = frame_cls(app._content_container, **options)
    except Exception as exc:  # noqa: BLE001
        log.warning("Falha ao instanciar frame %s: %s", frame_cls, exc)
        return None

    if current is not None and current is not frame:
        _forget_widget(current)

    try:
        frame.pack(fill="both", expand=True)
    except Exception as exc:  # noqa: BLE001
        log.debug("frame.pack() failed in create_frame: %s", exc)

    return frame


def _show_hub(app: Any) -> Any:
    frame = app.show_frame(
        HubFrame,
        open_clientes=lambda: navigate_to(app, "main"),
        open_farmacia_popular=lambda: navigate_to(app, "placeholder", title="Farmcia Popular"),
        open_sngpc=lambda: navigate_to(app, "placeholder", title="Sngpc"),
        open_mod_sifap=lambda: navigate_to(app, "placeholder", title="Sifap"),
        open_cashflow=lambda: navigate_to(app, "cashflow"),
        open_sites=lambda: navigate_to(app, "sites"),
    )

    try:
        app.refresh_clients_count_async()
    except Exception as exc:  # noqa: BLE001
        log.debug("refresh_clients_count_async failed in hub: %s", exc)

    if isinstance(frame, HubFrame):
        try:
            frame.on_show()
        except Exception as exc:
            log.warning("Erro ao chamar on_show do Hub: %s", exc)

    return frame


def _show_main(app: Any) -> Any:
    from src.modules.clientes.ui import ClientesV2Frame

    # ClientesV2 não precisa de todos esses callbacks (auto-contido)
    frame = app.show_frame(ClientesV2Frame)

    if isinstance(frame, ClientesV2Frame):
        app._main_frame_ref = frame
        app.force_redraw = getattr(frame, "force_redraw", None)

    app._main_loaded = True
    # ClientesV2 carrega automaticamente na inicialização
    return frame


def _show_cashflow(app: Any) -> Any:
    from src.modules.cashflow import CashflowFrame

    return app.show_frame(CashflowFrame, app=app)


def _show_sites(app: Any) -> Any:
    from src.modules.sites import SitesScreen

    return app.show_frame(SitesScreen)


def _show_placeholder(app: Any, title: str) -> Any:
    from src.ui.placeholders import ComingSoonScreen

    return app.show_frame(
        ComingSoonScreen,
        title=title,
        on_back=lambda: navigate_to(app, "hub"),
    )


def _show_passwords(app: Any) -> Any:
    from src.modules.passwords import PasswordsFrame

    t0 = time.perf_counter()
    if getattr(app, "_passwords_screen_instance", None) is None:
        app._passwords_screen_instance = PasswordsFrame(app._content_container, main_window=app)
        _place_or_pack(app._passwords_screen_instance)
        created = True
    else:
        created = False

    frame = app._passwords_screen_instance
    current = app.nav.current()

    if current is not None and current is not frame:
        _forget_widget(current)

    try:
        frame.lift()
    except Exception as exc:  # noqa: BLE001
        log.debug("passwords frame.lift() failed: %s", exc)

    try:
        app.nav._current = frame
    except Exception as exc:  # noqa: BLE001
        log.debug("set app.nav._current failed: %s", exc)

    try:
        frame.on_show()
    except Exception:
        log.exception("Erro ao chamar on_show da tela de senhas")

    try:
        frame.update_idletasks()
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao dar update_idletasks em tela de senhas: %s", exc)

    try:
        t1 = time.perf_counter()
        log.info("Senhas: janela aberta em %.3fs (created=%s)", t1 - t0, created)
    except Exception as exc:  # noqa: BLE001
        log.debug("Falha ao registrar tempo de abertura das Senhas: %s", exc)

    try:
        app._update_topbar_state(frame)
    except Exception as exc:  # noqa: BLE001
        log.debug("_update_topbar_state failed: %s", exc)

    return frame


def _open_clients_picker(app: Any, on_pick, return_to=None, banner_text: Optional[str] = None) -> None:
    """
    Entrada legada para o modo seleção de clientes.

    DEPRECATED: Prefer start_client_pick_mode() em novos fluxos. Esta função existe
    apenas para manter compatibilidade com chamadas antigas de navigate_to(..., "clients_picker").
    """
    if return_to is None:

        def _return_to_hub() -> None:
            navigate_to(app, "hub")

        return_to = _return_to_hub

    effective_banner = banner_text or LEGACY_PICK_MODE_BANNER_TEXT
    start_client_pick_mode(
        app,
        on_client_picked=on_pick,
        banner_text=effective_banner,
        return_to=return_to,
    )


def start_client_pick_mode(
    app: Any,
    on_client_picked: Callable[[dict[str, Any]], None],
    banner_text: str,
    return_to: Optional[Callable[[], None]] = None,
) -> None:
    """
    API pública para iniciar modo seleção de clientes com callback customizado.

    Args:
        app: Instância do aplicativo principal
        on_client_picked: Callback chamado quando cliente é selecionado
        banner_text: Texto do banner exibido no modo seleção
        return_to: Callback opcional para retornar após seleção/cancelamento

    Uso:
        # Para Obrigações:
        start_client_pick_mode(
            app,
            on_client_picked=self._handle_client_picked_for_obligations,
            banner_text="Modo seleção: escolha um cliente para gerenciar obrigações",
            return_to=lambda: navigate_to(app, "hub")
        )
    """
    # Navegar para tela de clientes
    navigate_to(app, "main")

    # Obter frame de clientes
    frame = getattr(app, "_main_frame_ref", None)
    if frame is None or not hasattr(frame, "start_pick"):
        messagebox.showwarning("Atenção", "Tela de clientes não está disponível.")
        return

    # Iniciar modo pick com callback customizado
    frame.start_pick(on_pick=on_client_picked, return_to=return_to, banner_text=banner_text)


def navigate_to(app: Any, target: str, **kwargs) -> Any:
    handlers = {
        "hub": _show_hub,
        "main": _show_main,
        "placeholder": _show_placeholder,
        "clients_picker": _open_clients_picker,
        "cashflow": _show_cashflow,
        "sites": _show_sites,
    }

    handler = handlers.get(target)
    if handler is None:
        raise ValueError(f"Destino de navegao desconhecido: {target}")

    return handler(app, **kwargs)


def tk_report(exc: Any, val: Any, tb_: Any) -> None:
    log.exception("Excecao no Tkinter callback", exc_info=(exc, val, tb_))
