from __future__ import annotations

from src.ui.ctk_config import ctk

"""View principal do módulo Clientes.

Por enquanto este módulo apenas reexporta a tela legada
`MainScreenFrame` como `ClientesFrame`, mantendo 100% de
compatibilidade com o código existente.

A ideia é que, no futuro, qualquer ajuste visual do módulo
Clientes seja feito aqui, sem precisar mexer em `app_gui.py`
ou no roteador.
"""

import logging
import tkinter as tk
from typing import Any, Dict, Optional, Tuple

from src.modules.clientes.views import (
    DEFAULT_ORDER_LABEL as _DEFAULT_ORDER_LABEL,
    ORDER_CHOICES as _ORDER_CHOICES,
    MainScreenFrame,
)

# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

# Importa theme manager (com fallback se customtkinter não estiver disponível)
try:
    from src.modules.clientes.appearance import ClientesThemeManager
except ImportError:
    ClientesThemeManager = None  # type: ignore[assignment,misc]

log = logging.getLogger(__name__)

# Reexporta as constantes usadas pelo roteador / App
DEFAULT_ORDER_LABEL: str = _DEFAULT_ORDER_LABEL
ORDER_CHOICES: Dict[str, Tuple[Optional[str], bool]] = _ORDER_CHOICES


class ClientesFrame(MainScreenFrame):
    """Alias tipado para a tela principal de clientes.

    Adiciona suporte a alternância Light/Dark via CustomTkinter
    sem afetar outros módulos.
    """

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        # Inicializa theme manager ANTES de criar a UI
        self._theme_manager: ClientesThemeManager | None = None
        self._theme_switch: Any = None  # CTkSwitch se disponível
        self._surface_frame: tk.Frame | Any = None  # Surface container (CTkFrame ou tk.Frame)

        if ClientesThemeManager is not None:
            try:
                self._theme_manager = ClientesThemeManager()
                # Carrega modo salvo (não aplicar diretamente)
                mode = self._theme_manager.load_mode()
                log.info(f"Theme manager inicializado: modo {mode}")
                # NÃO usar ctk.set_appearance_mode aqui (viola SSoT)
                # O GlobalThemeManager já inicializou o tema no bootstrap
            except Exception:
                log.exception("Erro ao inicializar theme manager")
                self._theme_manager = None

        # CRITICAL: Cria frame surface ANTES de construir UI para evitar "fundo branco"
        self._create_surface_container(master)

        # Chama __init__ da classe base usando o surface como pai
        # IMPORTANTE: passa self._surface_frame como master para a base class
        super().__init__(self._surface_frame, **kwargs)

        # Após UI construída, aplica estilos e insere toggle
        if self._theme_manager is not None:
            try:
                # MICROFASE 31: Removido Style legado (ZERO em runtime)
                # Insere toggle na toolbar
                self._insert_theme_toggle()
                # Aplica cores aos widgets já criados
                self._apply_theme_to_widgets()
                # Aplica cor de fundo ao surface
                self._apply_surface_colors()
            except Exception:
                log.exception("Erro ao aplicar tema inicial")

    def _insert_theme_toggle(self) -> None:
        """Insere CTkSwitch na toolbar para alternar tema."""
        if not HAS_CUSTOMTKINTER or ctk is None or self._theme_manager is None:
            return

        try:
            # Container para o toggle à direita da toolbar (usa tk.Frame simples)
            toggle_container = tk.Frame(self.toolbar.frame)
            toggle_container.pack(side="right", padx=10)

            # Switch customtkinter
            switch_value = 1 if self._theme_manager.current_mode == "dark" else 0
            self._theme_switch = ctk.CTkSwitch(
                toggle_container,
                text="🌙 Escuro" if self._theme_manager.current_mode == "light" else "☀️ Claro",
                width=100,
                height=24,
                command=self._on_theme_toggle,
            )
            if switch_value:
                self._theme_switch.select()
            else:
                self._theme_switch.deselect()
            self._theme_switch.pack(side="left")

            log.info("Toggle de tema inserido na toolbar")
        except Exception:
            log.exception("Erro ao inserir toggle de tema")

    def _on_theme_toggle(self) -> None:
        """Callback quando usuário alterna o toggle.
        
        MICROFASE 31: Removido Style legado (ZERO em runtime).
        """
        if self._theme_manager is None:
            return

        try:
            # Alterna modo sem Style legado
            new_mode = self._theme_manager.toggle(None)
            log.info(f"Tema alternado para: {new_mode}")

            # Atualiza texto do switch
            if self._theme_switch is not None:
                new_text = "🌙 Escuro" if new_mode == "light" else "☀️ Claro"
                self._theme_switch.configure(text=new_text)

            # Atualiza cores da toolbar CustomTkinter (se aplicável)
            if hasattr(self.toolbar, "refresh_colors"):
                self.toolbar.refresh_colors(self._theme_manager)

            # Atualiza cores da actionbar CustomTkinter (Microfase 3)
            if hasattr(self, "footer") and hasattr(self.footer, "refresh_colors"):
                self.footer.refresh_colors(self._theme_manager)

            # Aplica cor de fundo ao surface container
            self._apply_surface_colors()

            # Aplica aos widgets já criados
            self._apply_theme_to_widgets()

            # Re-aplica zebra na Treeview
            self._reapply_treeview_colors()

        except Exception:
            log.exception("Erro ao alternar tema")

    def _apply_theme_to_widgets(self) -> None:
        """Aplica cores do tema aos widgets tk do módulo.

        IMPORTANTE: Widgets CustomTkinter não suportam 'bg', usam 'fg_color'.
        Este método só atualiza widgets Tk tradicionais.
        Para widgets CTk, use refresh_colors() específico.
        """
        if self._theme_manager is None:
            return

        try:
            palette = self._theme_manager.get_palette()

            # Atualiza backgrounds de frames tk.Frame locais
            # SKIP widgets CustomTkinter (não suportam 'bg')
            for widget_name in dir(self):
                if widget_name.startswith("_"):
                    widget = getattr(self, widget_name, None)
                    if isinstance(widget, tk.Frame):
                        # Skip se for widget CustomTkinter
                        if widget.__class__.__module__.startswith("customtkinter"):
                            continue
                        try:
                            widget.configure(bg=palette["bg"])
                        except (tk.TclError, ValueError, TypeError):
                            # Widget não suporta 'bg', ignora
                            pass

            # Atualiza placeholder label se existir (apenas para toolbar legada)
            # Toolbar CTK usa refresh_colors() chamado em _on_theme_toggle
            if hasattr(self.toolbar, "frame") and self.toolbar.frame is not self.toolbar:
                # Só processa se for toolbar legada (frame é diferente de self)
                controls_frame = self.toolbar.frame
                try:
                    # Procura search_container e placeholder_label
                    for child in controls_frame.winfo_children():
                        # Skip widgets CustomTkinter
                        if child.__class__.__module__.startswith("customtkinter"):
                            continue

                        if isinstance(child, tk.Frame):
                            try:
                                child.configure(bg=palette["bg"])
                            except (tk.TclError, ValueError, TypeError):
                                pass

                            for subchild in child.winfo_children():
                                # Skip widgets CustomTkinter
                                if subchild.__class__.__module__.startswith("customtkinter"):
                                    continue

                                if isinstance(subchild, tk.Label):
                                    try:
                                        # Verifica se é o placeholder (tem texto específico)
                                        text = subchild.cget("text")
                                        if isinstance(text, str) and "pesquisar" in text.lower():
                                            subchild.configure(
                                                bg=palette["entry_bg"],
                                                fg="#C3C3C3",  # Cor do placeholder
                                            )
                                    except (tk.TclError, ValueError, TypeError):
                                        pass
                except Exception:
                    # Falha ao processar toolbar, não é crítico
                    log.debug("Erro ao atualizar cores da toolbar legada", exc_info=True)

        except Exception:
            log.exception("Erro ao aplicar tema aos widgets")

    def _reapply_treeview_colors(self) -> None:
        """Re-aplica cores zebra na Treeview após mudança de tema.
        
        MICROFASE 31: Simplificado - apenas tags, sem Style legado.
        """
        if self._theme_manager is None:
            return

        try:
            from src.ui.components.lists import reapply_clientes_treeview_tags

            # Detectar modo atual e calcular cores zebra
            appearance_mode = ctk.get_appearance_mode()  # "Light" ou "Dark"
            is_dark = appearance_mode == "Dark"
            
            if is_dark:
                even_bg = "#2b2b2b"
                odd_bg = "#3c3c3c"
                fg = "#ffffff"
            else:
                even_bg = "#ffffff"
                odd_bg = "#e8e8e8"
                fg = "#000000"

            # Re-aplica tags
            if hasattr(self, "client_list"):
                reapply_clientes_treeview_tags(
                    self.client_list,
                    even_bg,
                    odd_bg,
                    fg=fg,
                )

        except Exception:
            log.exception("Erro ao reaplicar cores da Treeview")

    def _create_surface_container(self, master: tk.Misc) -> None:
        """Cria frame surface dedicado para evitar 'fundo branco' vazando.

        Este container fica entre o master (app global) e o ClientesFrame,
        garantindo que todo o módulo Clientes tenha fundo da paleta.
        """
        if self._theme_manager is None:
            # Sem theme manager, cria tk.Frame simples
            self._surface_frame = tk.Frame(master)
            self._surface_frame.pack(fill="both", expand=True)
            log.debug("Surface container criado (tk.Frame fallback)")
            return

        palette = self._theme_manager.get_palette()

        if HAS_CUSTOMTKINTER and ctk is not None:
            # Usa CTkFrame com fg_color da paleta
            try:
                surface_color = (palette["bg"], palette["bg"])  # Tupla (light, dark)
                self._surface_frame = ctk.CTkFrame(
                    master,
                    fg_color=surface_color,
                    corner_radius=0,  # Sem bordas arredondadas
                )
                self._surface_frame.pack(fill="both", expand=True)
                log.debug(f"Surface container criado (CTkFrame com fg_color={surface_color})")
            except Exception:
                log.exception("Erro ao criar CTkFrame surface, usando tk.Frame")
                self._surface_frame = tk.Frame(master, bg=palette["bg"])
                self._surface_frame.pack(fill="both", expand=True)
        else:
            # Fallback: tk.Frame com bg da paleta
            self._surface_frame = tk.Frame(master, bg=palette["bg"])
            self._surface_frame.pack(fill="both", expand=True)
            log.debug(f"Surface container criado (tk.Frame com bg={palette['bg']})")

    def _apply_surface_colors(self) -> None:
        """Aplica cores do tema ao surface container."""
        if self._theme_manager is None or self._surface_frame is None:
            return

        try:
            palette = self._theme_manager.get_palette()

            if HAS_CUSTOMTKINTER and isinstance(self._surface_frame, ctk.CTkFrame):
                # CTkFrame: usar configure com fg_color
                surface_color = (palette["bg"], palette["bg"])
                self._surface_frame.configure(fg_color=surface_color)
                log.debug(f"Surface CTkFrame atualizado: fg_color={surface_color}")
            elif isinstance(self._surface_frame, tk.Frame):
                # tk.Frame: usar configure com bg
                self._surface_frame.configure(bg=palette["bg"])
                log.debug(f"Surface tk.Frame atualizado: bg={palette['bg']}")
        except Exception:
            log.exception("Erro ao aplicar cores ao surface container")


__all__ = ["ClientesFrame", "DEFAULT_ORDER_LABEL", "ORDER_CHOICES"]
