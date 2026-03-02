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
    win = ctk.CTkToplevel(parent)
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

    # Garante que tamanho final foi calculado
    try:
        window.update_idletasks()
    except tk.TclError as e:
        log.warning("[SHOW_CENTERED] Falha em update_idletasks para '%s': %s", window_title, e)
        return

    # Coleta dimensões iniciais para o log consolidado de debug
    _dbg: dict = {"title": window_title}
    if log.isEnabledFor(logging.DEBUG):
        try:
            _dbg["state_before"] = window.state()
        except Exception:
            pass
        try:
            _dbg["winfo"] = "%dx%d" % (window.winfo_width(), window.winfo_height())
            _dbg["req"] = "%dx%d" % (window.winfo_reqwidth(), window.winfo_reqheight())
        except Exception:
            pass

    # Para janelas Toplevel (diálogos), centraliza na TELA para melhor UX
    # Para janelas Tk (principal), centraliza no parent se houver
    # FIX-TESTS-002: Proteger isinstance() contra TypeError em cenários de teste
    try:
        is_toplevel = isinstance(window, tk.Toplevel)
    except TypeError:
        # Em cenários de teste (monkeypatch ou stubs), tk.Toplevel pode não ser um tipo real
        # Nesses casos, tratamos como não-Toplevel para evitar quebra
        is_toplevel = False

    if is_toplevel:
        center_on_screen(window)
        _dbg["center"] = "screen"
    else:
        centered_on_parent = center_on_parent(window)
        _dbg["center"] = "parent" if centered_on_parent else "screen(fallback)"
        if not centered_on_parent:
            center_on_screen(window)

    # Captura geometry calculada APÓS centralização para reaplicar depois do deiconify
    target_geometry = ""
    try:
        target_geometry = window.geometry()
        _dbg["geo_after_center"] = target_geometry
    except Exception:
        pass

    # Garante que a janela sai do estado withdrawn/iconic e fica visível
    try:
        window.state("normal")
    except tk.TclError:
        pass

    try:
        window.deiconify()
    except tk.TclError as e:
        log.warning("[SHOW_CENTERED] Falha em deiconify() para '%s': %s", window_title, e)

    # CRÍTICO: Reaplicar geometry APÓS deiconify para garantir posição correta
    # O Tkinter pode ignorar a posição se aplicada antes do deiconify
    if target_geometry:
        try:
            window.geometry(target_geometry)
        except Exception:
            pass

    # Verifica estado APÓS deiconify; força novamente se necessário
    try:
        final_state = window.state()
        if final_state != "normal":
            log.warning(
                "[SHOW_CENTERED] Estado não é 'normal' (é '%s') para '%s', forçando...",
                final_state,
                window_title,
            )
            window.state("normal")
            window.deiconify()
        _dbg["state_after"] = final_state
    except Exception:
        pass

    # Garante que aparece em cima de outras janelas e recebe foco
    try:
        window.lift()
        window.focus_set()
    except tk.TclError as e:
        log.debug("[SHOW_CENTERED] Falha em lift/focus para '%s': %s", window_title, e)

    # Log único consolidado com todo contexto relevante (só avaliado se DEBUG ligado)
    if log.isEnabledFor(logging.DEBUG):
        try:
            _dbg["final_pos"] = "%dx%d+%d+%d" % (
                window.winfo_width(),
                window.winfo_height(),
                window.winfo_x(),
                window.winfo_y(),
            )
        except Exception:
            pass
        log.debug("[SHOW_CENTERED] %s", _dbg)


def recenter_after_layout(*args: object, **kwargs: object) -> None:
    """
    [DEPRECATED] Mantido apenas para compatibilidade com imports antigos.
    Nao faz nada.
    """
    return


# ============================================================================
# Helpers anti-flash para janelas Toplevel (usado por ANVISA e outros módulos)
# ============================================================================


# Module-level cache for PhotoImage to prevent garbage collection
_icon_photo_cache: tk.PhotoImage | None = None
_icon_png_path: str | None = None
_icon_ico_path: str | None = None


def _load_icon_paths() -> None:
    """Load and cache icon paths on first use."""
    global _icon_png_path, _icon_ico_path

    if _icon_png_path is not None or _icon_ico_path is not None:
        return  # Already loaded

    try:
        from src.utils.paths import resource_path
        import os

        ico_path = resource_path("rc.ico")
        if os.path.exists(ico_path):
            _icon_ico_path = ico_path
            log.debug(f"[WindowIcon] Found rc.ico: {ico_path}")

        png_path = resource_path("rc.png")
        if os.path.exists(png_path):
            _icon_png_path = png_path
            log.debug(f"[WindowIcon] Found rc.png: {png_path}")
    except Exception as e:
        log.debug(f"[WindowIcon] Error loading icon paths: {e}")


def _get_cached_photo(window: tk.Misc) -> tk.PhotoImage | None:
    """Get or create cached PhotoImage for icon.

    Args:
        window: A Tk window (needed to create PhotoImage)

    Returns:
        Cached PhotoImage or None if rc.png not available
    """
    global _icon_photo_cache, _icon_png_path

    _load_icon_paths()

    if _icon_png_path is None:
        return None

    if _icon_photo_cache is None:
        try:
            _icon_photo_cache = tk.PhotoImage(file=_icon_png_path)
            log.debug(f"[WindowIcon] Created PhotoImage from: {_icon_png_path}")
        except Exception as e:
            log.debug(f"[WindowIcon] Failed to create PhotoImage: {e}")
            return None

    return _icon_photo_cache


def apply_window_icon(window: tk.Toplevel | tk.Tk) -> None:
    """Apply app icon to window with CTkToplevel override protection.

    This improved version:
    1. Tries iconbitmap(rc.ico) for Windows
    2. Uses iconphoto with cached PhotoImage (prevents GC)
    3. For root (Tk/CTk): iconphoto(True, ...) to set default for child windows
    4. For Toplevel: iconphoto(False, ...)
    5. Schedules a re-apply after 250ms to defeat CTkToplevel icon override

    Args:
        window: Janela para aplicar ícone (Tk, Toplevel, or CTkToplevel)
    """
    _load_icon_paths()

    def _apply_icon_impl() -> None:
        """Internal implementation that applies the icon."""
        try:
            if not window.winfo_exists():
                return
        except Exception:
            return

        # Try iconbitmap first (works best on Windows with .ico)
        if _icon_ico_path:
            try:
                window.iconbitmap(_icon_ico_path)
                log.debug(f"[WindowIcon] Applied iconbitmap to {type(window).__name__}")
            except Exception as e:
                log.debug(f"[WindowIcon] iconbitmap failed: {e}")
            # iconbitmap(default=) define ícone padrão para novas janelas filhas
            try:
                window.iconbitmap(default=_icon_ico_path)
            except Exception:
                pass

        # Also apply iconphoto for better cross-platform support
        photo = _get_cached_photo(window)
        if photo is not None:
            try:
                # Determine if this is a root window (Tk/CTk) or child (Toplevel)
                is_root = False
                try:
                    # Root window has no master or master is empty string
                    master = getattr(window, "master", None)
                    if master is None or (isinstance(master, str) and master == ""):
                        is_root = True
                    # Also check if it's the main CTk instance
                    if hasattr(window, "_current_width"):  # CTk attribute
                        is_root = True
                except Exception:
                    pass

                if is_root:
                    window.iconphoto(True, photo)  # True = default for child windows
                    log.debug("[WindowIcon] Applied iconphoto(True) to root window")
                else:
                    window.iconphoto(False, photo)  # False = only this window
                    log.debug("[WindowIcon] Applied iconphoto(False) to child window")
            except Exception as e:
                log.debug(f"[WindowIcon] iconphoto failed: {e}")

    # Apply immediately
    _apply_icon_impl()

    # Schedule re-apply after 250ms to defeat CTkToplevel icon override
    def _reapply_icon() -> None:
        """Re-apply icon after delay to defeat CTkToplevel override."""
        try:
            if window.winfo_exists():
                _apply_icon_impl()
                log.debug("[WindowIcon] Reapplied icon after 250ms delay")
        except Exception:
            pass  # Window may have been destroyed

    try:
        window.after(250, _reapply_icon)
    except Exception:
        pass  # Window may not support after()


def prepare_hidden_window(win: tk.Toplevel) -> None:
    """Prepara janela Toplevel para ser construída sem flash/splash.

    Deve ser chamado IMEDIATAMENTE após criar o Toplevel.
    NÃO usa alpha (causa black frames no Windows).

    Usa virtual root (winfo_vrootx/y) para calcular posição offscreen
    que funciona em setups multi-monitor.

    Args:
        win: Janela Toplevel recém criada
    """
    win.withdraw()

    # Calcular posição offscreen usando virtual root (multi-monitor safe)
    # Virtual root representa o desktop virtual completo (todos os monitores)
    try:
        vrootx = win.winfo_vrootx()
        vrooty = win.winfo_vrooty()
    except Exception:
        vrootx, vrooty = 0, 0

    # Posicionar à ESQUERDA e ACIMA do desktop virtual
    # Usa margem grande para garantir que não apareça em nenhum monitor
    off_x = vrootx - 5000
    off_y = vrooty - 5000

    # Geometry mínima offscreen (será redimensionada depois)
    win.geometry(f"1x1+{off_x}+{off_y}")
    log.debug(f"[window_utils] prepare_hidden_window: offscreen=({off_x}, {off_y})")


def show_centered_no_flash(
    win: tk.Toplevel,
    parent: tk.Misc,
    *,
    width: int | None = None,
    height: int | None = None,
) -> None:
    """Mostra janela Toplevel já centralizada, sem flash/splash.

    Estratégia anti-flash (NOVA):
    1. Calcula tamanho e posição final ENQUANTO janela está withdraw
    2. Seta geometry final (ainda invisível)
    3. Deiconify UMA ÚNICA VEZ já no lugar certo
    4. NÃO usa win.update() após deiconify (evita flash)

    Multi-monitor safe: usa virtual root para clamping correto.
    NÃO usa alpha (causa black frames no Windows).

    Deve ser chamado DEPOIS de construir todos os widgets.

    Args:
        win: Janela Toplevel preparada com prepare_hidden_window
        parent: Widget pai para calcular centro
        width: Largura desejada (ou None para usar winfo_reqwidth)
        height: Altura desejada (ou None para usar winfo_reqheight)
    """
    # Step 1: Atualizar geometria para medir tamanho real (janela ainda withdraw)
    win.update_idletasks()

    # Step 2: Medir tamanho desejado
    w = width if width is not None else win.winfo_reqwidth()
    h = height if height is not None else win.winfo_reqheight()

    # Step 3: Calcular posição CENTRALIZADA no parent (MULTI-MONITOR SAFE)
    try:
        parent.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()

        # Obter bounds do desktop virtual (multi-monitor)
        try:
            vroot_x = win.winfo_vrootx()
            vroot_y = win.winfo_vrooty()
            vroot_w = win.winfo_vrootwidth()
            vroot_h = win.winfo_vrootheight()
            log.debug(f"[show_centered_no_flash] Virtual root: x={vroot_x}, y={vroot_y}, w={vroot_w}, h={vroot_h}")
        except Exception as e:
            # Fallback: usar screenwidth/height se vrootx/y falharem
            log.debug(f"[show_centered_no_flash] vroot* não disponível: {e}, usando screen*")
            vroot_x = 0
            vroot_y = 0
            vroot_w = win.winfo_screenwidth()
            vroot_h = win.winfo_screenheight()

        # Fallback: se parent ainda está "cru" (geometry incompleto), usar tela
        if pw < 50 or ph < 50:
            log.debug(f"[show_centered_no_flash] Parent muito pequeno ({pw}x{ph}), usando bounds do virtual root")
            px = vroot_x
            py = vroot_y
            pw = vroot_w
            ph = vroot_h

        # Centro do parent
        center_x = px + (pw // 2)
        center_y = py + (ph // 2)

        # Posição da janela para ficar centralizada
        final_x = center_x - (w // 2)
        final_y = center_y - (h // 2)

        # MULTI-MONITOR FIX: Clampar usando bounds do virtual root (NÃO usar 0!)
        # Permite coordenadas negativas em setups multi-monitor
        min_x = vroot_x
        min_y = vroot_y
        max_x = vroot_x + vroot_w - w
        max_y = vroot_y + vroot_h - h

        final_x = max(min_x, min(final_x, max_x))
        final_y = max(min_y, min(final_y, max_y))

        log.debug(
            f"[show_centered_no_flash] Posição calculada: ({final_x}, {final_y}), bounds: x[{min_x},{max_x}] y[{min_y},{max_y}]"
        )

    except Exception as e:
        # Fallback: centralizar na tela principal
        log.warning(f"[show_centered_no_flash] Erro ao calcular posição: {e}")
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        final_x = (screen_w - w) // 2
        final_y = (screen_h - h) // 2

    # Step 4: Setar geometry FINAL (janela ainda withdraw - NÃO VISÍVEL)
    win.geometry(f"{w}x{h}+{final_x}+{final_y}")

    # Step 5: Tornar janela invisível (alpha=0) antes do deiconify
    # Isso permite que CustomTkinter desenhe tudo sem mostrar frames intermediários
    try:
        win.attributes("-alpha", 0.0)
    except Exception:
        pass  # Algumas plataformas não suportam alpha

    # Step 6: Deiconify e forçar renderização COMPLETA do CustomTkinter
    # IMPORTANTE: win.update() aqui é INTENCIONAL para forçar CTk desenhar tudo
    # enquanto alpha=0 (invisível). Isso evita o "frame cinza" inicial.
    win.deiconify()
    win.update_idletasks()
    try:
        win.update()  # Forçar renderização completa dos widgets CustomTkinter
    except tk.TclError:
        pass  # Janela pode ter sido destruída

    # Step 7: Revelar janela com delay (após CustomTkinter terminar de desenhar)
    # Delay de 60ms garante que:
    # - CustomTkinter terminou de renderizar todos os widgets
    # - set_win_dark_titlebar foi aplicado (se chamado após show_centered_no_flash)
    # - Titlebar escura não causa repaint visível
    def _reveal() -> None:
        """Revela janela após renderização completa."""
        try:
            win.attributes("-alpha", 1.0)
        except Exception:
            pass
        try:
            win.lift()
            win.focus_force()
        except Exception:
            pass

    win.after(60, _reveal)

    log.info(
        f"[show_centered_no_flash] Janela preparada (alpha=0): "
        f"posição=({final_x}, {final_y}), size={w}x{h}, reveal em 60ms"
    )


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
