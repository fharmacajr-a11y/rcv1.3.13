from __future__ import annotations

from src.ui.ctk_config import ctk
from src.ui.widgets.button_factory import make_btn

import logging
import os
import tkinter as tk
from typing import Optional

from src.ui.window_utils import show_centered
from src.modules.main_window.views.constants import APP_ICON_PATH
from src.modules.main_window.views.helpers import resource_path

logger = logging.getLogger(__name__)


def apply_app_icon(window: tk.Toplevel, parent: tk.Misc | None) -> None:
    """Apply the RC app icon to the given toplevel, mirroring the main window."""
    try:
        icon_path = resource_path(APP_ICON_PATH)
    except Exception:
        icon_path = ""

    if icon_path:
        try:
            window.iconbitmap(icon_path)
            return
        except Exception:  # noqa: BLE001
            # FIX: Fallback deve usar rc.png (PhotoImage não funciona com .ico no Windows)
            try:
                from src.utils.resource_path import resource_path as rp

                png_path = rp("rc.png")
                if os.path.exists(png_path):
                    img = tk.PhotoImage(file=png_path)
                    window.iconphoto(True, img)
                    window._rc_icon_img = img  # type: ignore[attr-defined]
                    return
            except Exception as inner_exc:  # noqa: BLE001
                logger.debug("Falha ao aplicar iconphoto no dialogo PDF: %s", inner_exc)

    try:
        if parent is not None:
            current_icon = parent.iconbitmap()
            if current_icon:
                window.iconbitmap(current_icon)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Falha ao reaproveitar icone do parent no dialogo PDF: %s", exc)


class _BaseDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, title: str) -> None:
        super().__init__(parent)
        self.withdraw()
        self._parent = parent
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)

        try:
            apply_app_icon(self, parent)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao configurar icone no dialogo base: %s", exc)

    def center_on_parent(self) -> None:
        try:
            self.update_idletasks()
            show_centered(self)
            self.grab_set()
            self.focus_force()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao centralizar dialogo PDF: %s", exc)


DELETE_IMAGES_MESSAGE = (
    "Deseja excluir as imagens originais (JPG/JPEG/PNG) de cada subpasta ap\u00f3s gerar os PDFs?\n\n"
    "Se voc\u00ea clicar em 'Sim', os arquivos de imagem ser\u00e3o apagados, deixando apenas o PDF em cada subpasta."
)


class PDFDeleteImagesConfirmDialog(_BaseDialog):
    """Dialogo de confirmacao em linha com os demais dialogs do Conversor PDF."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, "Conversor PDF")
        self._result: Optional[str] = None

        content = ctk.CTkFrame(self)  # TODO: padding=16 -> usar padx/pady no pack/grid
        content.pack(fill="both", expand=True)

        icon_frame = ctk.CTkFrame(content)
        icon_frame.grid(row=0, column=0, padx=(4, 16), pady=(0, 8), sticky="n")

        question_label = ctk.CTkLabel(icon_frame, text="?", font=("Segoe UI", 26, "bold"))
        question_label.pack()

        message_label = ctk.CTkLabel(
            content,
            text=DELETE_IMAGES_MESSAGE,
            wraplength=440,
            anchor="w",
            justify="left",
        )
        message_label.grid(row=0, column=1, padx=(0, 8), pady=(0, 8), sticky="w")
        content.columnconfigure(1, weight=1)

        buttons = ctk.CTkFrame(content)
        buttons.grid(row=1, column=0, columnspan=2, pady=(12, 0), sticky="e")

        btn_cancel = make_btn(buttons, text="Cancelar", command=self.on_cancel)
        btn_cancel.pack(side="left", padx=(0, 8))

        btn_no = make_btn(buttons, text="Não", command=self.on_no)
        btn_no.pack(side="left", padx=(0, 8))

        btn_yes = make_btn(buttons, text="Sim", command=self.on_yes)
        btn_yes.pack(side="left")

        btn_cancel.focus_set()

        self.bind("<Return>", lambda _: self.on_yes())
        self.bind("<Escape>", lambda _: self.on_cancel())
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

        self.center_on_parent()

    def on_yes(self) -> None:
        self._result = "yes"
        self.destroy()

    def on_no(self) -> None:
        self._result = "no"
        self.destroy()

    def on_cancel(self) -> None:
        self._result = "cancel"
        self.destroy()

    def show(self) -> Optional[str]:
        self.wait_window(self)
        return self._result


def ask_delete_images(parent: tk.Misc) -> Optional[str]:
    dialog = PDFDeleteImagesConfirmDialog(parent)
    return dialog.show()


class PDFConversionResultDialog(_BaseDialog):
    def __init__(self, parent: tk.Misc, message: str) -> None:
        super().__init__(parent, "Conversor PDF")

        content = ctk.CTkFrame(self)  # TODO: padding=16 -> usar padx/pady no pack/grid
        content.pack(fill="both", expand=True)

        message_label = ctk.CTkLabel(
            content,
            text=message,
            wraplength=520,
            anchor="w",
            justify="left",
        )
        message_label.pack(fill="both", expand=True, pady=(0, 12))

        button = make_btn(content, text="OK", command=self.on_ok)
        button.pack(side="right")

        self.bind("<Return>", lambda _: self.on_ok())
        self.bind("<Escape>", lambda _: self.on_ok())
        self.protocol("WM_DELETE_WINDOW", self.on_ok)

        self.center_on_parent()

    def on_ok(self) -> None:
        self.destroy()


def show_conversion_result(parent: tk.Misc, message: str) -> None:
    dialog = PDFConversionResultDialog(parent, message)
    parent.wait_window(dialog)
