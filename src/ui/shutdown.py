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
import os
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    import tkinter as tk

log = logging.getLogger(__name__)

_DEBUG_AFTER = os.getenv("RC_DEBUG_AFTER", "0") == "1"


def _tcl_after_ids(root: "tk.Tk | tk.Toplevel") -> list[str]:
    """Retorna lista de after IDs pendentes via Tcl."""
    try:
        raw = root.tk.call("after", "info")
    except Exception:
        return []
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, tuple):
        return list(raw)
    return []


def _tcl_after_detail(root: "tk.Tk | tk.Toplevel", after_id: str) -> tuple[str, str]:
    """Retorna (script_tcl, tipo) para um after ID.  tipo = 'timer' | 'idle'."""
    try:
        info = root.tk.call("after", "info", after_id)
        if isinstance(info, tuple) and len(info) >= 2:
            return (str(info[0])[:120], str(info[1]))
        return (str(info)[:120], "?")
    except Exception:
        return ("?", "?")


# ---------------------------------------------------------------------------
# Padrões conhecidos de after jobs internos do CustomTkinter
# ---------------------------------------------------------------------------

_CTK_OWNER_CLASSES: frozenset[str] = frozenset(
    {
        "AppearanceModeTracker",
        "ScalingTracker",
        "CTkButton",
        "CTkTextbox",
        "CTkScrollbar",
        "CTkFrame",
        "CTkEntry",
        "CTkLabel",
        "CTkToplevel",
        "CTk",
    }
)

_CTK_CALLBACK_NAMES: frozenset[str] = frozenset(
    {
        "_click_animation",
        "update",
        "check_dpi_scaling",
        "_check_if_scrollbars_needed",
    }
)


def _is_ctk_internal(meta: dict[str, Any] | None, tcl_script: str) -> bool:
    """Heurística para classificar um after job como interno do CustomTkinter.

    Prioridade 1: metadados do tracker (caller_file contém 'customtkinter').
    Prioridade 2: owner_class + callback em listas conhecidas.
    Prioridade 3: sem tracker — Tcl script não ajuda, retorna False (conservador).
    """
    if meta is None:
        return False

    # Via caller_file — mais confiável
    caller = str(meta.get("caller_file", "")).replace("\\", "/").lower()
    if "customtkinter" in caller:
        return True

    # Via owner_class + callback — fallback
    owner = str(meta.get("owner_class", ""))
    cb = str(meta.get("callback", ""))
    if owner in _CTK_OWNER_CLASSES and cb in _CTK_CALLBACK_NAMES:
        return True

    return False


def cancel_ctk_internal_jobs(root: "tk.Tk | tk.Toplevel") -> int:
    """Cancela after jobs identificados como internos do CustomTkinter.

    Usa metadados do AfterTracker (se instalado) para classificar.
    Apenas jobs CTk conhecidos são cancelados — app jobs NÃO são tocados.

    Returns:
        Número de jobs CTk cancelados.
    """
    ids = _tcl_after_ids(root)
    if not ids:
        return 0

    tracker: dict[str, Any] = {}
    try:
        from diag_after_jobs import get_registry  # noqa: PLC0415

        tracker = get_registry()
    except Exception:
        pass

    cancelled = 0
    for aid in ids:
        tcl_script, _tcl_type = _tcl_after_detail(root, aid)
        meta = tracker.get(aid)

        if _is_ctk_internal(meta, tcl_script):
            try:
                root.after_cancel(aid)
                cancelled += 1
                if _DEBUG_AFTER:
                    cb_name = meta.get("callback", "?") if meta else "?"
                    owner = meta.get("owner_class", "?") if meta else "?"
                    log.debug("  CTk cancel id=%s owner=%s cb=%s", aid, owner, cb_name)
            except Exception:  # noqa: BLE001
                pass

    if cancelled:
        log.debug("Cancelados %d after jobs internos do CTk", cancelled)
    return cancelled


def cancel_all_after_jobs(root: "tk.Tk | tk.Toplevel") -> int:
    """Cancela todos os jobs after() pendentes para evitar 'invalid command name' errors.

    Args:
        root: Janela raiz ou Toplevel do Tkinter/CTk

    Returns:
        Número de jobs cancelados
    """
    cancelled = 0
    try:
        after_ids = _tcl_after_ids(root)

        if not after_ids:
            log.debug("Nenhum after job pendente para cancelar")
            return 0

        for after_id in after_ids:
            try:
                root.after_cancel(after_id)
                cancelled += 1
            except Exception as e:  # noqa: BLE001
                log.debug("Falha ao cancelar after job %s: %s", after_id, e)

        if cancelled:
            log.debug("Cancelados %d after jobs remanescentes", cancelled)

    except Exception as e:  # noqa: BLE001
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


def install_clean_shutdown(root: tk.Tk | tk.Toplevel, on_closing: Callable[..., Any] | None = None) -> None:
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
                root._closing = True  # pyright: ignore[reportAttributeAccessIssue]

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
