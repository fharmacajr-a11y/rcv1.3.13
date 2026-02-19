"""Shutdown utilities - clean app termination without after() script errors.

PROBLEMA RESOLVIDO:
Ao fechar o app, aparecem erros do tipo:
    invalid command name "139827463824after#..."
    invalid command name "139827463824check_dpi_scaling"
    ("after" script error)

CAUSA:
- Jobs agendados com .after() continuam ativos após janelas serem destruídas
- Tk tenta executar callbacks em widgets já destruídos
- HubScreen, polling, theme checks, DPI scaling usam after() loops

SOLUÇÃO:
- Cancelar todos os after jobs pendentes ANTES de destruir root
- Setar flag _closing para prevenir novos after() jobs
- Ordem segura: cancel_after → quit() → destroy()

EXEMPLO DE USO:
    from src.ui.shutdown import install_clean_shutdown

    # No main_window.py ou app.py:
    def _on_closing():
        # 1) Setar flag de fechamento
        self._closing = True

        # 2) Cancelar all after jobs
        from src.ui.shutdown import cancel_all_after_jobs
        cancel_all_after_jobs(self.root)

        # 3) Fechar normalmente
        self.root.quit()
        self.root.destroy()

    self.root.protocol("WM_DELETE_WINDOW", _on_closing)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk

log = logging.getLogger(__name__)


def cancel_all_after_jobs(root: tk.Tk | tk.Toplevel) -> int:
    """Cancela todos os jobs after() pendentes para evitar 'invalid command name' errors.

    Args:
        root: Janela raiz ou Toplevel do Tkinter/CTk

    Returns:
        Número de jobs cancelados

    Exemplo:
        >>> from src.ui.shutdown import cancel_all_after_jobs
        >>> cancelled = cancel_all_after_jobs(self.root)
        >>> print(f"Cancelados {cancelled} jobs")
    """
    cancelled = 0
    try:
        # Tcl command: after info retorna lista de IDs de after jobs pendentes
        after_ids = root.tk.call("after", "info")

        if not after_ids:
            log.debug("Nenhum after job pendente para cancelar")
            return 0

        # after_ids pode ser string ou tupla, normalizar para lista
        if isinstance(after_ids, str):
            if not after_ids.strip():
                return 0
            after_ids = [after_ids]
        elif isinstance(after_ids, tuple):
            after_ids = list(after_ids)

        for after_id in after_ids:
            try:
                root.after_cancel(after_id)
                cancelled += 1
            except Exception as e:  # noqa: BLE001
                # Ignore errors - job pode já ter sido cancelado ou executado
                log.debug("Falha ao cancelar after job %s: %s", after_id, e)

        log.info("Cancelados %d after jobs pendentes", cancelled)

    except Exception as e:  # noqa: BLE001
        # Nunca quebrar o shutdown por falha ao cancelar after jobs
        log.warning("Erro ao cancelar after jobs: %s", e)

    return cancelled


def safe_quit(root: tk.Tk | tk.Toplevel) -> None:
    """Quit seguro que cancela after jobs primeiro.

    Args:
        root: Janela raiz ou Toplevel

    Exemplo:
        >>> from src.ui.shutdown import safe_quit
        >>> safe_quit(self.root)
    """
    try:
        cancel_all_after_jobs(root)
    except Exception as e:  # noqa: BLE001
        log.warning("Erro ao cancelar after jobs no shutdown: %s", e)

    try:
        root.quit()
    except Exception as e:  # noqa: BLE001
        log.warning("Erro em root.quit(): %s", e)


def safe_destroy(root: tk.Tk | tk.Toplevel) -> None:
    """Destroy seguro que cancela after jobs primeiro.

    Args:
        root: Janela raiz ou Toplevel

    Exemplo:
        >>> from src.ui.shutdown import safe_destroy
        >>> safe_destroy(self.root)
    """
    try:
        cancel_all_after_jobs(root)
    except Exception as e:  # noqa: BLE001
        log.warning("Erro ao cancelar after jobs no shutdown: %s", e)

    try:
        root.quit()
    except Exception as e:  # noqa: BLE001
        log.warning("Erro em root.quit(): %s", e)

    try:
        root.destroy()
    except Exception as e:  # noqa: BLE001
        log.warning("Erro em root.destroy(): %s", e)


def install_clean_shutdown(root: tk.Tk | tk.Toplevel, on_closing: callable | None = None) -> None:
    """Instala handler de shutdown limpo no WM_DELETE_WINDOW protocol.

    Args:
        root: Janela raiz
        on_closing: Callback opcional chamado ANTES do shutdown
                   Se retornar False, cancela o shutdown

    Exemplo:
        >>> from src.ui.shutdown import install_clean_shutdown
        >>>
        >>> def my_cleanup():
        >>>     print("Salvando dados...")
        >>>     return True  # Continuar com shutdown
        >>>
        >>> install_clean_shutdown(root, my_cleanup)
    """

    def _handle_close():
        try:
            # 1) Callback customizado (pode cancelar)
            if on_closing:
                try:
                    result = on_closing()
                    if result is False:
                        log.info("Shutdown cancelado pelo callback")
                        return
                except Exception as e:  # noqa: BLE001
                    log.error("Erro no callback on_closing: %s", e)
                    # Continua com shutdown mesmo com erro no callback

            # 2) Setar flag se app tem esse atributo
            if hasattr(root, "_closing"):
                root._closing = True

            # 3) Cancelar after jobs
            cancel_all_after_jobs(root)

            # 4) Quit e destroy
            root.quit()
            root.destroy()

        except Exception as e:  # noqa: BLE001
            log.error("Erro crítico no shutdown: %s", e)
            # Tentar fechar de qualquer forma
            try:
                root.destroy()
            except Exception:  # noqa: BLE001, S110
                pass

    root.protocol("WM_DELETE_WINDOW", _handle_close)
    log.debug("Clean shutdown handler instalado em %s", root)


__all__ = [
    "cancel_all_after_jobs",
    "safe_quit",
    "safe_destroy",
    "install_clean_shutdown",
]
