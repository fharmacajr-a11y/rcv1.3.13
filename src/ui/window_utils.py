# -*- coding: utf-8 -*-
"""
Helpers de centralização alinhados ao comportamento do Splash.

O objetivo é aplicar exatamente a mesma matemática usada pela tela de Splash
para posicionar janelas e diálogos no centro, evitando cálculos diferentes que
resultem em "saltos" ao abrir a UI em setups multi-monitor.

Padrão de uso recomendado para Toplevels:
1. Criar Toplevel
2. Chamar withdraw() para esconder durante construção
3. Montar todo o layout (widgets, frames, etc.)
4. Chamar update_idletasks() para calcular tamanhos finais
5. Chamar show_centered(window) - cuida de geometry, deiconify e foco
6. (Opcional) Chamar grab_set() e/ou focus_force() se for modal

Exemplo:
    win = tk.Toplevel(parent)
    win.withdraw()
    win.transient(parent)
    # ... montar UI completa ...
    win.update_idletasks()
    show_centered(win)
    win.grab_set()  # se for modal
"""

from __future__ import annotations

import logging
import tkinter as tk

log = logging.getLogger(__name__)


def center_on_parent(window: tk.Misc) -> bool:
    """
    Centraliza a janela em relacao ao master (janela principal).
    Retorna True se conseguiu centralizar; False se precisou fallback.

    Usa winfo_reqwidth/reqheight como fonte primária de tamanho, pois
    winfo_width/height pode retornar 200x200 (tamanho padrão) antes
    da janela ser mapeada pela primeira vez.

    Considera o minsize() da janela para garantir que a centralização
    use o tamanho real que a janela terá após deiconify().
    """
    parent = getattr(window, "master", None)

    if parent is None or not isinstance(parent, tk.Misc):
        return False

    try:
        parent.update_idletasks()
        window.update_idletasks()
    except tk.TclError:
        return False

    # Tamanho do parent - preferir reqwidth/reqheight
    pw = parent.winfo_reqwidth()
    ph = parent.winfo_reqheight()
    if pw <= 1 or ph <= 1:
        pw = parent.winfo_width()
        ph = parent.winfo_height()
    if pw <= 1 or ph <= 1:
        return False

    # Posição do parent
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()

    # Tamanho da janela - SEMPRE usar reqwidth/reqheight primeiro
    w = window.winfo_reqwidth()
    h = window.winfo_reqheight()

    # Fallback apenas se reqwidth/reqheight falharem
    if w <= 1 or h <= 1:
        w = window.winfo_width()
        h = window.winfo_height()
    if w <= 1 or h <= 1:
        return False

    # CRÍTICO: Considerar minsize() se existir, pois Tkinter forçará
    # a janela a ter pelo menos esse tamanho ao fazer deiconify()
    try:
        # Pega dimensões através de wm_minsize (mais confiável)
        if hasattr(window, "wm_minsize"):
            try:
                minsize_result = window.wm_minsize()
                if minsize_result and len(minsize_result) == 2:
                    min_from_wm_w, min_from_wm_h = minsize_result
                    # Usar o MAIOR entre reqwidth e minsize
                    w = max(w, min_from_wm_w if min_from_wm_w > 1 else w)
                    h = max(h, min_from_wm_h if min_from_wm_h > 1 else h)
                    log.debug(f"[center_on_parent] Minsize detectado: {min_from_wm_w}x{min_from_wm_h}, usando: {w}x{h}")
            except Exception as e:
                log.debug(f"[center_on_parent] Não foi possível obter minsize: {e}")
    except Exception as e:
        log.debug(f"[center_on_parent] Erro ao processar minsize: {e}")

    # Calcula posição centralizada
    x = px + (pw - w) // 2
    y = py + (ph - h) // 2

    # Garante que não fica fora da tela (valores negativos)
    x = max(0, x)
    y = max(0, y)

    window.geometry(f"{w}x{h}+{x}+{y}")
    window.update_idletasks()  # Força Tkinter a processar a geometry
    log.debug(f"[center_on_parent] Geometry aplicada: {w}x{h}+{x}+{y}")
    return True


def center_on_screen(window: tk.Misc) -> None:
    """
    Centraliza a janela no centro da tela inteira.
    Usado como fallback quando nao ha parent visivel.

    Usa winfo_reqwidth/reqheight como fonte primária de tamanho, pois
    winfo_width/height pode retornar 200x200 (tamanho padrão) antes
    da janela ser mapeada pela primeira vez.

    Considera o minsize() da janela para garantir que a centralização
    use o tamanho real que a janela terá após deiconify().
    """
    try:
        window.update_idletasks()
    except tk.TclError:
        return

    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()

    # Tamanho da janela - SEMPRE usar reqwidth/reqheight primeiro
    w = window.winfo_reqwidth()
    h = window.winfo_reqheight()

    # Fallback apenas se reqwidth/reqheight falharem
    if w <= 1 or h <= 1:
        w = window.winfo_width()
        h = window.winfo_height()
    if w <= 1 or h <= 1:
        return

    # CRÍTICO: Considerar minsize() se existir
    try:
        if hasattr(window, "wm_minsize"):
            try:
                minsize_result = window.wm_minsize()
                if minsize_result and len(minsize_result) == 2:
                    min_from_wm_w, min_from_wm_h = minsize_result
                    # Usar o MAIOR entre reqwidth e minsize
                    w = max(w, min_from_wm_w if min_from_wm_w > 1 else w)
                    h = max(h, min_from_wm_h if min_from_wm_h > 1 else h)
                    log.debug(f"[center_on_screen] Minsize detectado: {min_from_wm_w}x{min_from_wm_h}, usando: {w}x{h}")
            except Exception as e:
                log.debug(f"[center_on_screen] Não foi possível obter minsize: {e}")
    except Exception as e:
        log.debug(f"[center_on_screen] Erro ao processar minsize: {e}")

    # Calcula posição centralizada
    x = (screen_w - w) // 2
    y = (screen_h - h) // 2

    # Garante que não fica fora da tela (valores negativos)
    x = max(0, x)
    y = max(0, y)

    window.geometry(f"{w}x{h}+{x}+{y}")
    window.update_idletasks()  # Força Tkinter a processar a geometry
    log.debug(f"[center_on_screen] Geometry aplicada: {w}x{h}+{x}+{y}")


def show_centered(window: tk.Toplevel | tk.Tk) -> None:
    """
    Exibe a janela centralizada em relacao ao parent (se possivel) ou
    ao centro da tela. Pressupoe que o layout ja foi montado.

    Esta função:
    - Garante que o layout foi calculado (update_idletasks)
    - Centraliza a janela (em relação ao parent ou tela)
    - Torna a janela visível (deiconify)
    - Coloca a janela em foco (lift + focus_set)

    Use esta função como ponto único de exibição de Toplevels para
    garantir comportamento consistente em todo o app.
    """
    window_title = getattr(window, "title", lambda: "Unknown")()
    log.debug(f"[SHOW_CENTERED] Iniciando para janela: {window_title}")

    # Garante que tamanho final foi calculado
    try:
        window.update_idletasks()
    except tk.TclError as e:
        log.warning(f"[SHOW_CENTERED] Falha em update_idletasks: {e}")
        return

    # Log do estado inicial
    try:
        initial_state = window.state()
        log.debug(f"[SHOW_CENTERED] Estado inicial: {initial_state}")
    except Exception as e:
        log.debug(f"[SHOW_CENTERED] Não foi possível obter estado inicial: {e}")

    # Log das dimensões ANTES da centralização
    try:
        w_before = window.winfo_width()
        h_before = window.winfo_height()
        req_w = window.winfo_reqwidth()
        req_h = window.winfo_reqheight()
        log.debug(f"[SHOW_CENTERED] Dimensões: winfo={w_before}x{h_before}, req={req_w}x{req_h}")
    except Exception as e:
        log.debug(f"[SHOW_CENTERED] Não foi possível obter dimensões: {e}")

    # Para janelas Toplevel (diálogos), centraliza na TELA para melhor UX
    # Para janelas Tk (principal), centraliza no parent se houver
    # FIX-TESTS-002: Proteger isinstance() contra TypeError em cenários de teste
    try:
        is_toplevel = isinstance(window, tk.Toplevel)
    except TypeError:
        # Em cenários de teste (monkeypatch ou stubs), tk.Toplevel pode não ser um tipo real
        # Nesses casos, tratamos como não-Toplevel para evitar quebra
        log.debug(
            "[SHOW_CENTERED] isinstance(window, tk.Toplevel) lançou TypeError; "
            "tratando como não-Toplevel para evitar falha em testes."
        )
        is_toplevel = False

    if is_toplevel:
        center_on_screen(window)
        log.debug("[SHOW_CENTERED] Centralizado na tela (Toplevel)")
    else:
        centered_on_parent = center_on_parent(window)
        log.debug(f"[SHOW_CENTERED] Centralizado no parent: {centered_on_parent}")

        if not centered_on_parent:
            center_on_screen(window)
            log.debug("[SHOW_CENTERED] Fallback para centralização na tela")

    # Log da geometria aplicada APÓS a centralização - DEVE SER LIDO AQUI, APÓS center_on_parent/screen
    target_geometry = ""
    try:
        target_geometry = window.geometry()
        log.debug(f"[SHOW_CENTERED] Geometry final após centralização: {target_geometry}")
    except Exception as e:
        log.debug(f"[SHOW_CENTERED] Não foi possível obter geometry: {e}")

    # Garante que a janela sai do estado withdrawn/iconic e fica visível
    try:
        # Força estado normal ANTES de deiconify para garantir
        window.state("normal")
        log.debug("[SHOW_CENTERED] Estado forçado para 'normal'")
    except tk.TclError as e:
        log.debug(f"[SHOW_CENTERED] Não foi possível forçar estado normal: {e}")

    try:
        window.deiconify()
        log.debug("[SHOW_CENTERED] deiconify() executado")
    except tk.TclError as e:
        log.warning(f"[SHOW_CENTERED] Falha em deiconify(): {e}")

    # CRÍTICO: Reaplicar geometry APÓS deiconify para garantir posição correta
    # O Tkinter pode ignorar a posição se aplicada antes do deiconify
    if target_geometry:
        try:
            window.geometry(target_geometry)
            log.debug(f"[SHOW_CENTERED] Geometry reaplicada após deiconify: {target_geometry}")
        except Exception as e:
            log.debug(f"[SHOW_CENTERED] Não foi possível reaplicar geometry: {e}")

    # Verifica estado APÓS deiconify
    try:
        final_state = window.state()
        log.debug(f"[SHOW_CENTERED] Estado após deiconify: {final_state}")

        # Se não ficou normal, força novamente
        if final_state != "normal":
            log.warning(f"[SHOW_CENTERED] Estado não é 'normal' (é '{final_state}'), forçando...")
            window.state("normal")
            window.deiconify()
    except Exception as e:
        log.debug(f"[SHOW_CENTERED] Não foi possível verificar estado final: {e}")

    # Garante que aparece em cima de outras janelas e recebe foco
    try:
        window.lift()
        window.focus_set()
        log.debug("[SHOW_CENTERED] lift() e focus_set() executados")
    except tk.TclError as e:
        log.debug(f"[SHOW_CENTERED] Falha em lift/focus: {e}")

    # Log final de confirmação
    try:
        x = window.winfo_x()
        y = window.winfo_y()
        w = window.winfo_width()
        h = window.winfo_height()
        log.debug(f"[SHOW_CENTERED] Janela '{window_title}' exibida em: x={x}, y={y}, size={w}x{h}")
    except Exception as e:
        log.debug(f"[SHOW_CENTERED] Não foi possível obter posição final: {e}")


def recenter_after_layout(*args: object, **kwargs: object) -> None:
    """
    [DEPRECATED] Mantido apenas para compatibilidade com imports antigos.
    Nao faz nada.
    """
    return


# ============================================================================
# Helpers anti-flash para janelas Toplevel (usado por ANVISA e outros módulos)
# ============================================================================


def apply_window_icon(window: tk.Toplevel | tk.Tk) -> None:
    """Aplica ícone do app em janela Toplevel ou Tk.

    Args:
        window: Janela para aplicar ícone
    """
    try:
        from src.utils.paths import resource_path

        window.iconbitmap(resource_path("rc.ico"))
    except Exception as exc:  # noqa: BLE001
        # Ícone pode não estar disponível
        log.debug("iconbitmap falhou: %s", type(exc).__name__)


def prepare_hidden_window(win: tk.Toplevel) -> None:
    """Prepara janela Toplevel para ser construída sem flash/splash.

    Deve ser chamado IMEDIATAMENTE após criar o Toplevel.

    Args:
        win: Janela Toplevel recém criada
    """
    win.withdraw()
    win.attributes("-alpha", 0.0)
    win.geometry("1x1+10000+10000")


def show_centered_no_flash(
    win: tk.Toplevel,
    parent: tk.Misc,
    *,
    width: int | None = None,
    height: int | None = None,
) -> None:
    """Mostra janela Toplevel já centralizada, sem flash/splash.

    Deve ser chamado DEPOIS de construir todos os widgets.

    Args:
        win: Janela Toplevel preparada com prepare_hidden_window
        parent: Widget pai para calcular centro
        width: Largura desejada (ou None para usar winfo_reqwidth)
        height: Altura desejada (ou None para usar winfo_reqheight)
    """
    # Atualizar para medir tamanho real
    win.update_idletasks()

    # Medir tamanho
    w = width if width is not None else win.winfo_reqwidth()
    h = height if height is not None else win.winfo_reqheight()

    # Calcular centro relativo ao parent
    parent.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()

    x = px + (pw - w) // 2
    y = py + (ph - h) // 2

    # Aplicar geometria final
    win.geometry(f"{w}x{h}+{x}+{y}")

    # Mostrar janela já no lugar certo
    win.deiconify()
    win.lift()
    win.focus_force()

    # Restaurar alpha após desenhar
    win.after(0, lambda: win.attributes("-alpha", 1.0))


def center_window_simple(window: tk.Toplevel, parent: tk.Misc) -> None:
    """Centraliza janela Toplevel em relação ao parent (versão simplificada).

    Args:
        window: Janela a ser centralizada
        parent: Widget pai para calcular centro
    """
    window.update_idletasks()

    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()

    ww = window.winfo_width()
    wh = window.winfo_height()

    # Se width/height ainda são 1, usar reqwidth/reqheight
    if ww <= 1:
        ww = window.winfo_reqwidth()
    if wh <= 1:
        wh = window.winfo_reqheight()

    x = px + (pw - ww) // 2
    y = py + (ph - wh) // 2

    # Garantir que não fica fora da tela
    if x < 0:
        x = 0
    if y < 0:
        y = 0

    window.geometry(f"+{x}+{y}")
