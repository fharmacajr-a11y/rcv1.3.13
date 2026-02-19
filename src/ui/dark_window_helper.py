# -*- coding: utf-8 -*-
"""Helper para criar janelas CTkToplevel sem flash branco no tema escuro.

Funcionalidades:
- Pattern withdraw/deiconify para evitar flash branco
- Titlebar escura no Windows usando DwmSetWindowAttribute
- Configuração completa antes de exibir a janela
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


def set_win_dark_titlebar(window: Any) -> None:
    """Configura titlebar escura no Windows (evita flash branco na barra de título).

    Usa DwmSetWindowAttribute com DWMWA_USE_IMMERSIVE_DARK_MODE para
    forçar a titlebar a usar o tema escuro nativo do Windows 10/11.

    Args:
        window: Janela CTkToplevel ou Tk
    """
    if sys.platform != "win32":
        return

    try:
        import ctypes
        from ctypes import c_int, byref, sizeof

        # Obter HWND da janela
        hwnd = window.winfo_id()

        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11)
        # DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19 (Windows 10 build < 19041)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19

        # Valor 1 = dark mode, 0 = light mode
        use_dark = c_int(1)

        # Tentar Windows 11 primeiro
        try:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(use_dark), sizeof(use_dark)
            )
            log.debug(f"[DarkWindow] Titlebar escura aplicada (Win11 mode) - HWND={hwnd}")
        except Exception:
            # Fallback para Windows 10
            try:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1, byref(use_dark), sizeof(use_dark)
                )
                log.debug(f"[DarkWindow] Titlebar escura aplicada (Win10 mode) - HWND={hwnd}")
            except Exception as e:
                log.debug(f"[DarkWindow] Erro ao aplicar titlebar escura: {e}")

    except Exception as e:
        log.debug(f"[DarkWindow] Erro ao configurar titlebar escura: {e}")


def create_dark_toplevel(
    parent: Any,
    title: str,
    width: int = 800,
    height: int = 600,
    resizable: bool = True,
    center: bool = True,
    modal: bool = True,
    fg_color: Optional[str | tuple[str, str]] = None,
    setup_callback: Optional[Callable[[Any], None]] = None,
) -> Any:
    """Cria CTkToplevel sem flash branco (pattern withdraw/deiconify).

    Evita o flash branco ao abrir janelas modais no tema escuro:
    1. Cria CTkToplevel com withdraw() imediato (não exibe ainda)
    2. Configura title, geometry, cores, ícone
    3. Chama setup_callback para adicionar widgets
    4. update_idletasks() para processar layout
    5. Aplica titlebar escura (Windows)
    6. deiconify() para exibir a janela completa
    7. grab_set() apenas após janela renderizada

    Args:
        parent: Widget pai
        title: Título da janela
        width: Largura da janela
        height: Altura da janela
        resizable: Se permite redimensionar
        center: Se centraliza na tela
        modal: Se torna modal (grab_set)
        fg_color: Cor de fundo (padrão: tema escuro)
        setup_callback: Função para configurar UI (recebe window)

    Returns:
        Instância de CTkToplevel configurada e visível

    Example:
        ```python
        def setup_ui(window):
            label = ctk.CTkLabel(window, text="Conteúdo")
            label.pack()

        dialog = create_dark_toplevel(
            parent=root,
            title="Minha Janela",
            width=600,
            height=400,
            setup_callback=setup_ui
        )
        ```
    """
    try:
        from src.ui.ctk_config import ctk
        from src.ui.ui_tokens import APP_BG
        from src.utils.paths import resource_path
    except ImportError:
        log.error("[DarkWindow] Erro ao importar dependências")
        return None

    # 1. Criar toplevel OCULTA (withdraw imediato)
    window = ctk.CTkToplevel(parent)
    window.withdraw()  # type: ignore[attr-defined]  # CRÍTICO: Oculta antes de configurar

    # 2. Configurações básicas
    window.title(title)
    window.geometry(f"{width}x{height}")

    # 3. Cor de fundo (tema escuro por padrão)
    if fg_color is None:
        fg_color = APP_BG
    window.configure(fg_color=fg_color)

    # 4. Resizable (usar Toplevel.resizable para evitar flicker no CTkToplevel)
    if not resizable:
        try:
            from tkinter import Toplevel

            Toplevel.resizable(window, False, False)
        except Exception:
            window.resizable(False, False)

    # 5. Ícone
    try:
        icon_path = resource_path("rc.ico")
        window.iconbitmap(icon_path)  # type: ignore[attr-defined]
    except Exception:
        pass  # Ignora se falhar

    # 6. Centralizar
    if center:
        window.update_idletasks()  # Necessário para obter dimensões corretas
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")

    # 7. Setup callback (adicionar widgets)
    if setup_callback is not None:
        try:
            setup_callback(window)
        except Exception as e:
            log.error(f"[DarkWindow] Erro no setup_callback: {e}", exc_info=True)

    # 8. Processar layout (ANTES de deiconify)
    window.update_idletasks()

    # 9. Titlebar escura (Windows) - após ter winfo_id()
    try:
        set_win_dark_titlebar(window)
    except Exception as e:
        log.debug(f"[DarkWindow] Erro ao aplicar titlebar escura: {e}")

    # 10. Modal (transient primeiro, grab depois)
    if modal:
        try:
            window.transient(parent)  # Mantém acima do parent
        except Exception:
            pass

    # 11. EXIBIR JANELA (agora sim!)
    window.deiconify()  # type: ignore[attr-defined]

    # 12. grab_set APÓS deiconify (janela já renderizada)
    if modal:
        try:
            window.grab_set()
        except Exception:
            pass

    log.debug(f"[DarkWindow] Janela criada sem flash: {title}")
    return window


def apply_dark_titlebar_to_existing(window: Any) -> None:
    """Aplica titlebar escura em janela já existente.

    Útil para janelas que não foram criadas com create_dark_toplevel.
    Deve ser chamado após a janela ter sido exibida (winfo_id() disponível).

    Args:
        window: Janela CTkToplevel ou Tk
    """
    try:
        # Aguardar janela estar mapeada
        window.update_idletasks()

        # Aplicar titlebar escura
        set_win_dark_titlebar(window)

        log.debug("[DarkWindow] Titlebar escura aplicada retroativamente")
    except Exception as e:
        log.debug(f"[DarkWindow] Erro ao aplicar titlebar: {e}")
