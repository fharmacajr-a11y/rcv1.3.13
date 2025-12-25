from __future__ import annotations

from dataclasses import dataclass
import tkinter
from tkinter import messagebox
from typing import Callable, Optional, TYPE_CHECKING

import logging

if TYPE_CHECKING:
    from .main_screen import MainScreenFrame

from src.modules.clientes.views.main_screen_helpers import validate_single_selection

PickCallback = Callable[[dict], None]

log = logging.getLogger("app_gui")


@dataclass
class PickModeController:
    """Orquestra o modo seleção (“pick”) da tela de Clientes."""

    frame: "MainScreenFrame"
    _active: bool = False
    _callback: Optional[PickCallback] = None
    _return_to: Optional[Callable[[], None]] = None

    def start_pick(
        self,
        on_pick: PickCallback,
        return_to: Optional[Callable[[], None]] = None,
        banner_text: Optional[str] = None,
    ) -> None:
        """Entra em modo pick e recarrega a lista.

        MS-21: Refatorado para usar API pública da MainScreenFrame.
        """
        self._active = True
        self._callback = on_pick
        self._return_to = return_to
        # MS-21: Manter _pick_mode para compatibilidade com código legacy
        self.frame._pick_mode = True
        self.frame._on_pick = on_pick
        self.frame._return_to = return_to
        self._update_banner_text(banner_text=banner_text)
        # MS-21: Usar API pública em vez de chamar método privado
        self._ensure_pick_ui(True)
        self.frame.carregar()

    def confirm_pick(self, *_: object) -> None:
        """Confirma seleção e dispara callback."""
        if not self._active:
            return

        # Obter IDs selecionados usando helper validate_single_selection
        try:
            sel = self.frame.client_list.selection()
            selected_ids = set(sel) if sel else set()
        except Exception:
            selected_ids = set()

        # Validar que exatamente 1 cliente está selecionado
        is_valid, client_id, error_key = validate_single_selection(selected_ids)

        if not is_valid:
            messagebox.showwarning("Atenção", "Selecione um cliente primeiro.", parent=self.frame)
            return

        # Obter dados completos do cliente selecionado
        info = self._get_selected_client_dict()
        if not info:
            # Fallback: se não conseguiu obter dados, exibe aviso
            messagebox.showwarning("Atenção", "Erro ao obter dados do cliente.", parent=self.frame)
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
        """Sai de pick mode e executa callback de retorno se necessário.

        MS-21: Refatorado para usar API pública da MainScreenFrame.
        """
        self._active = False
        # FIX-CLIENTES-007: Manter _pick_mode=True durante _ensure_pick_ui(False)
        # para que _update_main_buttons_state() não sobrescreva o estado restaurado da Lixeira
        self._ensure_pick_ui(False)
        # MS-21: Manter _pick_mode para compatibilidade com código legacy
        self.frame._pick_mode = False  # Resetar apenas APÓS restaurar a UI

        if call_return and callable(self._return_to):
            try:
                self._return_to()
            except Exception as exc:  # noqa: BLE001
                log.debug("Falha ao executar retorno do modo pick: %s", exc)

        self._callback = None
        self._return_to = None
        self.frame._on_pick = None
        self.frame._return_to = None

    def _ensure_pick_ui(self, enable: bool) -> None:
        """Exibe ou oculta UI específica do modo pick.

        MS-21: Refatorado para usar APIs públicas da MainScreenFrame.
        """
        frame = self.frame
        if not hasattr(frame, "_saved_toolbar_state"):
            frame._saved_toolbar_state = {}

        if enable:
            # MS-21: Usar API pública para entrar em modo pick UI
            if hasattr(frame, "enter_pick_mode"):
                try:
                    frame.enter_pick_mode()
                except Exception as exc:  # noqa: BLE001
                    log.debug("Falha ao entrar no modo pick UI: %s", exc)

            if hasattr(frame, "_pick_banner_frame"):
                self._position_pick_banner()

            # Coletar botões CRUD do footer (exceto Lixeira que é controlada pela MainScreenFrame)
            footer = getattr(frame, "footer", None)
            crud_buttons = []

            # Botões do footer (dentro de frame.footer)
            if footer:
                crud_buttons.extend(
                    [
                        getattr(footer, "btn_novo", None),
                        getattr(footer, "btn_editar", None),
                        getattr(footer, "btn_subpastas", None),
                    ]
                )

            # Lixeira NÃO é incluída - ela fica visível mas desabilitada
            # O estado visual da Lixeira é controlado por _enter_pick_mode_ui / _leave_pick_mode_ui

            for btn in crud_buttons:
                if btn:
                    is_mapped = btn.winfo_ismapped()
                    manager = btn.winfo_manager() if is_mapped else "none"

                    if is_mapped:
                        # Salvar info do gerenciador apropriado
                        if manager == "pack":
                            info = ("pack", btn.pack_info())
                        elif manager == "grid":
                            info = ("grid", btn.grid_info())
                        else:
                            info = ("unknown", None)

                        frame._saved_toolbar_state[btn] = info

                        # Ocultar usando o método apropriado
                        if manager == "pack":
                            btn.pack_forget()
                        elif manager == "grid":
                            btn.grid_forget()

            try:
                frame.client_list.unbind("<Double-1>")
                frame.client_list.bind("<Double-1>", self.confirm_pick)
                frame.client_list.bind("<Return>", self.confirm_pick)
                frame.bind_all("<Escape>", self.cancel_pick)
            except Exception as exc:
                log.debug("Falha ao configurar binds do modo pick: %s", exc)
        else:
            # Sair do modo pick UI
            if hasattr(frame, "_pick_banner_frame"):
                frame._pick_banner_frame.pack_forget()

            for btn, info in list(frame._saved_toolbar_state.items()):
                if info:
                    manager_type, manager_info = info
                    try:
                        if manager_type == "pack" and manager_info:
                            # Remover 'in' - tkinter não aceita como parâmetro
                            pack_opts = {k: v for k, v in manager_info.items() if k != "in"}
                            btn.pack(**pack_opts)
                            log.debug(f"    OK - btn.pack({pack_opts})")
                        elif manager_type == "grid" and manager_info:
                            # Remover 'in' - tkinter não aceita como parâmetro
                            grid_opts = {k: v for k, v in manager_info.items() if k != "in"}
                            btn.grid(**grid_opts)
                            log.debug(f"    OK - btn.grid({grid_opts})")
                    except Exception as exc:  # noqa: BLE001
                        log.warning(f"Falha ao restaurar {btn.winfo_name()}: {exc}")
            frame._saved_toolbar_state.clear()

            try:
                frame.client_list.unbind("<Double-1>")
                frame.client_list.unbind("<Return>")
                frame.unbind_all("<Escape>")
                frame.client_list.bind("<Double-1>", lambda _event: frame._invoke_safe(frame.on_edit))
            except Exception as exc:
                log.debug("Falha ao restaurar binds do modo pick: %s", exc)

            # MS-21: Usar API pública para sair do modo pick UI
            if hasattr(frame, "exit_pick_mode"):
                try:
                    frame.exit_pick_mode()
                except Exception as exc:  # noqa: BLE001
                    log.debug("Falha ao sair do modo pick UI: %s", exc)

        try:
            frame._update_main_buttons_state()
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar botoes no modo pick: %s", exc)

    def _update_banner_text(self, banner_text: Optional[str]) -> None:
        """Atualiza texto do banner conforme o contexto fornecido."""
        frame = self.frame
        label = getattr(frame, "_pick_label", None)
        if label is None:
            return

        default_text = getattr(frame, "_pick_banner_default_text", None)
        text = banner_text or default_text
        if not text:
            return

        try:
            if hasattr(label, "configure") and callable(label.configure):
                label.configure(text=text)
            elif hasattr(label, "config") and callable(label.config):
                label.config(text=text)
            else:
                label["text"] = text  # type: ignore[index]
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao atualizar texto do banner do pick mode: %s", exc)

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

    def _position_pick_banner(self) -> None:
        """Posiciona o banner de pick mode usando o gerenciador apropriado."""
        frame = self.frame
        banner = frame._pick_banner_frame

        try:
            # Detecta qual gerenciador está sendo usado pelo client_list
            manager = frame.client_list.winfo_manager()

            if manager == "grid":
                # client_list está em grid, usar grid para o banner
                # O client_list_container é packeado, então precisamos trabalhar com o container
                # Vamos inserir o banner antes do container usando pack
                if hasattr(frame, "client_list_container"):
                    container = frame.client_list_container
                    container_manager = container.winfo_manager()

                    if container_manager == "pack":
                        # Posiciona o banner antes do container da lista
                        banner.pack(fill="x", padx=10, pady=(0, 10), before=container)
                    else:
                        # Fallback: pack no topo sem before
                        banner.pack(fill="x", padx=10, pady=(0, 10))
                else:
                    # Sem container, usar pack simples
                    banner.pack(fill="x", padx=10, pady=(0, 10))

            elif manager == "pack":
                # client_list está em pack, usar pack com before
                banner.pack(fill="x", padx=10, pady=(0, 10), before=frame.client_list)
            else:
                # Gerenciador desconhecido ou vazio, usar pack simples
                banner.pack(fill="x", padx=10, pady=(0, 10))

        except (tkinter.TclError, AttributeError) as exc:
            log.exception("Erro ao posicionar banner do modo pick: %s", exc)
            # Fallback seguro: tentar pack simples
            try:
                banner.pack(fill="x", padx=10, pady=(0, 10))
            except tkinter.TclError:
                log.error("Falha crítica ao posicionar banner do modo pick")

    @staticmethod
    def _format_cnpj_for_pick(cnpj: str | None) -> str:
        """Formata CNPJ para exibição (##.###.###/####-##).

        Wrapper para compatibilidade. Delega para src.helpers.formatters.format_cnpj.
        """
        from src.helpers.formatters import format_cnpj as _format_cnpj_canonical

        return _format_cnpj_canonical(cnpj)
