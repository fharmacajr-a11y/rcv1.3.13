from __future__ import annotations

import logging
from typing import Any

from tkinter import messagebox

log = logging.getLogger("app_gui")

__all__ = ["navigate_to"]


def _forget_widget(widget: Any) -> None:
    if widget is None:
        return
    try:
        widget.pack_forget()
    except Exception:
        try:
            widget.place_forget()
        except Exception:
            pass


def _place_or_pack(widget: Any) -> None:
    try:
        widget.place(relx=0, rely=0, relwidth=1, relheight=1)
    except Exception:
        try:
            widget.pack(fill="both", expand=True)
        except Exception:
            pass


def _show_hub(app: Any) -> Any:
    from gui.hub_screen import HubScreen

    frame = app.show_frame(
        HubScreen,
        open_clientes=lambda: navigate_to(app, "main"),
        open_anvisa=lambda: navigate_to(app, "placeholder", title="Anvisa"),
        open_auditoria=lambda: navigate_to(app, "placeholder", title="Auditoria"),
        open_farmacia_popular=lambda: navigate_to(app, "placeholder", title="Farmcia Popular"),
        open_sngpc=lambda: navigate_to(app, "placeholder", title="Sngpc"),
        open_senhas=lambda: navigate_to(app, "passwords"),
        open_mod_sifap=lambda: navigate_to(app, "placeholder", title="Sifap"),
    )

    try:
        app.refresh_clients_count_async()
    except Exception:
        pass

    if isinstance(frame, HubScreen):
        try:
            frame.on_show()
        except Exception as exc:
            log.warning("Erro ao chamar on_show do Hub: %s", exc)

    return frame


def _show_main(app: Any) -> Any:
    from gui.main_screen import MainScreenFrame, DEFAULT_ORDER_LABEL, ORDER_CHOICES

    frame = app.show_frame(
        MainScreenFrame,
        app=app,
        on_new=app.novo_cliente,
        on_edit=app.editar_cliente,
        on_delete=app._excluir_cliente,
        on_upload=app.enviar_para_supabase,
        on_open_subpastas=app.ver_subpastas,
        on_open_lixeira=app.abrir_lixeira,
        order_choices=ORDER_CHOICES,
        default_order_label=DEFAULT_ORDER_LABEL,
    )
    if isinstance(frame, MainScreenFrame):
        app._main_frame_ref = frame
    app._main_loaded = True
    try:
        frame.carregar()
    except Exception:
        log.exception("Erro ao carregar lista na tela principal.")
    return frame


def _show_placeholder(app: Any, title: str) -> Any:
    from gui.placeholders import ComingSoonScreen

    return app.show_frame(
        ComingSoonScreen,
        title=title,
        on_back=lambda: navigate_to(app, "hub"),
    )


def _show_passwords(app: Any) -> Any:
    from gui.passwords_screen import PasswordsScreen

    if getattr(app, "_passwords_screen_instance", None) is None:
        app._passwords_screen_instance = PasswordsScreen(app._content_container, main_window=app)
        _place_or_pack(app._passwords_screen_instance)

    frame = app._passwords_screen_instance
    current = app.nav.current()

    if current is not None and current is not frame:
        _forget_widget(current)

    try:
        frame.lift()
    except Exception:
        pass

    try:
        app.nav._current = frame
    except Exception:
        pass

    try:
        frame.on_show()
    except Exception:
        log.exception("Erro ao chamar on_show da tela de senhas")

    try:
        app._update_topbar_state(frame)
    except Exception:
        pass

    return frame


def _open_clients_picker(app: Any, on_pick) -> None:
    def _return_to_passwords():
        navigate_to(app, "passwords")

    navigate_to(app, "main")

    frame = getattr(app, "_main_frame_ref", None)
    if frame is not None and hasattr(frame, "start_pick"):
        frame.start_pick(on_pick=on_pick, return_to=_return_to_passwords)
    else:
        messagebox.showwarning("Ateno", "Tela de clientes no est disponvel.")


def navigate_to(app: Any, target: str, **kwargs) -> Any:
    handlers = {
        "hub": _show_hub,
        "main": _show_main,
        "placeholder": _show_placeholder,
        "passwords": _show_passwords,
        "clients_picker": _open_clients_picker,
    }

    handler = handlers.get(target)
    if handler is None:
        raise ValueError(f"Destino de navegao desconhecido: {target}")

    return handler(app, **kwargs)
