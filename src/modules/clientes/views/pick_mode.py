from __future__ import annotations

from dataclasses import dataclass
import re
from tkinter import messagebox
from typing import Callable, Optional, TYPE_CHECKING

import logging

if TYPE_CHECKING:
    from .main_screen import MainScreenFrame

PickCallback = Callable[[dict], None]

log = logging.getLogger("app_gui")


@dataclass
class PickModeController:
    """Orquestra o modo seleção (“pick”) da tela de Clientes."""

    frame: "MainScreenFrame"
    _active: bool = False
    _callback: Optional[PickCallback] = None
    _return_to: Optional[Callable[[], None]] = None

    def start_pick(self, on_pick: PickCallback, return_to: Optional[Callable[[], None]] = None) -> None:
        """Entra em modo pick e recarrega a lista."""
        self._active = True
        self._callback = on_pick
        self._return_to = return_to
        self.frame._pick_mode = True
        self.frame._on_pick = on_pick
        self.frame._return_to = return_to
        self._ensure_pick_ui(True)
        self.frame.carregar()

    def confirm_pick(self, *_: object) -> None:
        """Confirma seleção e dispara callback."""
        if not self._active:
            return

        info = self._get_selected_client_dict()
        if not info:
            messagebox.showwarning("Atenção", "Selecione um cliente primeiro.", parent=self.frame)
            return

        cnpj_raw = info.get("cnpj", "")
        info["cnpj"] = self._format_cnpj_for_pick(cnpj_raw)

        try:
            if callable(self._callback):
                self._callback(info)
        finally:
            self._exit(call_return=True)

    def cancel_pick(self, *_: object) -> None:
        """Cancela modo pick sem escolher cliente."""
        if not self._active:
            return
        self._exit(call_return=True)

    def is_active(self) -> bool:
        return self._active

    # ------------------------------------------------------------------ #
    # Internos
    # ------------------------------------------------------------------ #

    def _exit(self, *, call_return: bool) -> None:
        self._active = False
        self.frame._pick_mode = False
        self._ensure_pick_ui(False)

        if call_return and callable(self._return_to):
            try:
                self._return_to()
            except Exception:
                pass

        self._callback = None
        self._return_to = None
        self.frame._on_pick = None
        self.frame._return_to = None

    def _ensure_pick_ui(self, enable: bool) -> None:
        """Exibe ou oculta UI específica do modo pick."""
        frame = self.frame
        if not hasattr(frame, "_saved_toolbar_state"):
            frame._saved_toolbar_state = {}

        if enable:
            if hasattr(frame, "_pick_banner_frame"):
                frame._pick_banner_frame.pack(fill="x", padx=10, pady=(0, 10), before=frame.client_list)

            crud_buttons = [
                getattr(frame, "btn_novo", None),
                getattr(frame, "btn_editar", None),
                getattr(frame, "btn_subpastas", None),
                getattr(frame, "btn_enviar", None),
                getattr(frame, "btn_lixeira", None),
            ]
            for btn in crud_buttons:
                if btn and btn.winfo_ismapped():
                    info = btn.pack_info() if btn.winfo_manager() == "pack" else None
                    frame._saved_toolbar_state[btn] = info
                    btn.pack_forget()

            try:
                frame.client_list.unbind("<Double-1>")
                frame.client_list.bind("<Double-1>", self.confirm_pick)
                frame.client_list.bind("<Return>", self.confirm_pick)
                frame.bind_all("<Escape>", self.cancel_pick)
            except Exception as exc:
                log.debug("Falha ao configurar binds do modo pick: %s", exc)
        else:
            if hasattr(frame, "_pick_banner_frame"):
                frame._pick_banner_frame.pack_forget()

            for btn, pack_info in list(frame._saved_toolbar_state.items()):
                if pack_info:
                    try:
                        btn.pack(**pack_info)
                    except Exception:
                        pass
            frame._saved_toolbar_state.clear()

            try:
                frame.client_list.unbind("<Double-1>")
                frame.client_list.unbind("<Return>")
                frame.unbind_all("<Escape>")
                frame.client_list.bind("<Double-1>", lambda _event: frame._invoke_safe(frame.on_edit))
            except Exception as exc:
                log.debug("Falha ao restaurar binds do modo pick: %s", exc)

        try:
            frame._update_main_buttons_state()
        except Exception:
            pass

    def _get_selected_client_dict(self) -> dict | None:
        """Retorna dict com dados do cliente selecionado."""
        try:
            sel = self.frame.client_list.selection()
        except Exception:
            return None
        if not sel:
            return None
        item_id = sel[0]
        try:
            values = self.frame.client_list.item(item_id, "values")
        except Exception:
            return None
        if not values or len(values) < 3:
            return None

        try:
            return {
                "id": values[0],
                "razao_social": values[1],
                "cnpj": values[2],
            }
        except Exception as exc:
            log.warning("Erro ao obter dados do cliente: %s", exc)
            return None

    @staticmethod
    def _format_cnpj_for_pick(cnpj: str) -> str:
        """Formata CNPJ para exibição (##.###.###/####-##)."""
        digits = re.sub(r"\\D", "", cnpj or "")
        if len(digits) != 14:
            return cnpj or ""
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
