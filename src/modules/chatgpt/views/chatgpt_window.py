from __future__ import annotations

from src.ui.ctk_config import ctk
from src.ui.widgets.button_factory import make_btn

import logging
import threading
import tkinter as tk
from typing import Callable

from src.modules.chatgpt.service import send_chat_completion
from src.ui.window_utils import show_centered

log = logging.getLogger(__name__)


class ChatGPTWindow(tk.Toplevel):
    """Janela de chat simples integrada a API da OpenAI."""

    def __init__(
        self,
        parent: tk.Misc,
        send_fn: Callable[[list[dict[str, str]]], str] | None = None,
        on_close_callback: Callable[[], None] | None = None,
    ) -> None:
        try:
            master = parent.winfo_toplevel()
        except Exception:
            master = parent
        super().__init__(master)
        self.withdraw()

        self.title("ChatGPT")
        # REMOVIDO: self.transient(parent) - impede uso de iconify()
        # REMOVIDO: self.grab_set() - causava travamento do app

        self._on_close_callback = on_close_callback

        try:
            from src.core.app import apply_rc_icon  # type: ignore

            apply_rc_icon(self)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao aplicar icone RC na janela do ChatGPT: %s", exc)

        self._send_fn = send_fn or (lambda msgs: send_chat_completion(msgs))

        self._system_message = {
            "role": "system",
            "content": (
                "Voce e um assistente integrado ao RC Gestor. "
                "Responda de forma clara e objetiva sobre escritorio, farmacias, documentos, etc."
            ),
        }
        self._messages: list[dict[str, str]] = [self._system_message.copy()]

        self._build_ui()
        self._build_custom_header()

        width = 700
        height = 500
        self.minsize(width, height)

        # Centraliza apenas uma vez, após todo o layout estar montado
        log.debug("[CHATGPT_WINDOW] Antes de update_idletasks()")
        self.update_idletasks()
        log.debug("[CHATGPT_WINDOW] Antes de show_centered()")
        show_centered(self)
        log.debug("[CHATGPT_WINDOW] Após show_centered()")

        # Verifica estado da janela
        try:
            window_state = self.state()
            geometry = self.geometry()
            log.debug(f"[CHATGPT_WINDOW] Janela exibida: state={window_state}, geometry={geometry}")
        except Exception as exc:  # noqa: BLE001
            log.warning(f"[CHATGPT_WINDOW] Não foi possível verificar estado: {exc}")

    def _build_ui(self) -> None:
        main = ctk.CTkFrame(self)  # TODO: padding=10 -> usar padx/pady no pack/grid
        main.pack(fill="both", expand=True)

        self._history = tk.Text(main, wrap="word", state="disabled", height=20)
        scroll = ctk.CTkScrollbar(main, command=self._history.yview)
        self._history.configure(yscrollcommand=scroll.set)

        self._history.grid(row=0, column=0, columnspan=3, sticky="nsew")
        scroll.grid(row=0, column=3, sticky="ns")

        self._input_var = tk.StringVar()
        self._entry = ctk.CTkEntry(main, textvariable=self._input_var)
        self._entry.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self._entry.bind("<Return>", self._on_send_event)

        send_btn = make_btn(main, text="Enviar", command=self._on_send_clicked)
        send_btn.grid(row=1, column=1, padx=(8, 0), pady=(8, 0), sticky="e")

        new_chat_btn = make_btn(main, text="Nova conversa", command=self.new_conversation)
        new_chat_btn.grid(row=1, column=2, padx=(8, 0), pady=(8, 0), sticky="e")

        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

    def _build_custom_header(self) -> None:
        """Constrói cabeçalho customizado com título."""
        # Header simples com apenas o título
        # Os botões de minimizar/fechar são os nativos da barra do Windows

        header = ctk.CTkFrame(self)
        header.pack(side="top", fill="x", before=self.winfo_children()[0] if self.winfo_children() else None)

        title_label = ctk.CTkLabel(header, text="ChatGPT", font=("Segoe UI", 10, "bold"))
        title_label.pack(side="left", padx=8, pady=4)

    def _on_close_clicked(self) -> None:
        """Fecha a janela (acionado pelo botão X)."""
        if self._on_close_callback:
            try:
                self._on_close_callback()
            except Exception as exc:  # noqa: BLE001
                log.debug("Erro ao executar callback de fechamento: %s", exc)
        self.destroy()

    def on_minimize(self) -> None:
        """Minimiza a janela sem destruí-la."""
        # Usar iconify() ao invés de withdraw() para minimizar corretamente
        self.iconify()

    def show(self) -> None:
        """Mostra a janela e traz para frente."""
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def new_conversation(self) -> None:
        """Inicia uma nova conversa, limpando o histórico."""
        # Limpar widget de texto
        self._history.configure(state="normal")
        self._history.delete("1.0", "end")
        self._history.insert("1.0", "— Nova conversa iniciada —\n\n")
        self._history.configure(state="disabled")

        # Resetar mensagens (manter apenas system message)
        self._messages = [self._system_message.copy()]

    def _append_to_history(self, prefix: str, text: str) -> None:
        self._history.configure(state="normal")
        self._history.insert("end", f"{prefix}: {text}\n\n")
        self._history.see("end")
        self._history.configure(state="disabled")

    def _on_send_event(self, event: tk.Event | None = None) -> None:
        self._on_send_clicked()

    def _on_send_clicked(self) -> None:
        user_text = self._input_var.get().strip()
        if not user_text:
            return

        self._input_var.set("")
        self._append_to_history("Voce", user_text)
        self._messages.append({"role": "user", "content": user_text})

        threading.Thread(target=self._background_request, daemon=True).start()

    def _background_request(self) -> None:
        try:
            result = self._send_fn(self._messages.copy())
        except RuntimeError as exc:
            self.after(0, self._append_response, str(exc))
            return
        except Exception as exc:
            result = f"[Erro ao chamar ChatGPT: {exc}]"

        self.after(0, self._append_response, result)

    def _append_response(self, answer: str) -> None:
        if not answer:
            return
        self._messages.append({"role": "assistant", "content": answer})
        self._append_to_history("ChatGPT", answer)
