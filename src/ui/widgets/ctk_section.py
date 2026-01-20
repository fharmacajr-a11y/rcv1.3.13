# -*- coding: utf-8 -*-
"""
CTkSection - Componente reutilizável para substituir padrões ttk.LabelFrame.

Este componente cria uma seção com título (CTkLabel) e conteúdo (CTkFrame),
aplicando padding via geometry managers adequados.
"""
from __future__ import annotations

from typing import Any, Union
from src.ui.ctk_config import ctk


class CTkSection(ctk.CTkFrame):
    """Seção CustomTkinter com título e corpo separados.
    
    Substitui padrões como:
    - ttk.LabelFrame com text=
    - CTkFrame com text= (não suportado)
    - CTkFrame com padding= (não suportado)
    
    Usa internamente:
    - CTkLabel para o título
    - CTkFrame interno para o conteúdo
    - Padding via pack/grid ao invés de kwargs
    """
    
    def __init__(
        self,
        master: Any,
        title: str = "",
        title_font: tuple[str, int, str] | None = None,
        padding: Union[int, tuple[int, int], tuple[int, int, int, int]] = 8,
        content_fg_color: str | tuple[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Inicializar CTkSection.
        
        Args:
            master: Widget pai
            title: Texto do título da seção
            title_font: Fonte do título (família, tamanho, peso)
            padding: Padding interno (int ou tupla)
            content_fg_color: Cor de fundo do frame de conteúdo
            **kwargs: Argumentos para o CTkFrame principal
        """
        # Frame principal (sem padding kwargs)
        super().__init__(master, **kwargs)
        
        # Processar padding
        if isinstance(padding, int):
            self._pad_x = self._pad_y = padding
        elif isinstance(padding, tuple) and len(padding) == 2:
            self._pad_x, self._pad_y = padding
        elif isinstance(padding, tuple) and len(padding) == 4:
            # left, top, right, bottom -> usar left/right como padx, top/bottom como pady
            left, top, right, bottom = padding
            self._pad_x = (left, right)
            self._pad_y = (top, bottom)
        else:
            self._pad_x = self._pad_y = 8
        
        # Título (se fornecido)
        if title:
            font = title_font or ("Arial", 12, "bold")
            self.title_label = ctk.CTkLabel(self, text=title, font=font)
            self.title_label.pack(fill="x", padx=self._pad_x, pady=(self._pad_y if isinstance(self._pad_y, int) else self._pad_y[0], 4))
        else:
            self.title_label = None
        
        # Frame de conteúdo (onde widgets filhos são adicionados)
        self.content_frame = ctk.CTkFrame(self, fg_color=content_fg_color or "transparent")
        
        # Pack com padding adequado
        if isinstance(self._pad_y, tuple):
            content_pady = (0 if title else self._pad_y[0], self._pad_y[1])
        else:
            content_pady = (0 if title else self._pad_y, self._pad_y)
            
        self.content_frame.pack(
            fill="both", 
            expand=True, 
            padx=self._pad_x, 
            pady=content_pady
        )
    
    def add_content(self, widget: Any) -> None:
        """Adicionar um widget ao frame de conteúdo.
        
        Args:
            widget: Widget a ser adicionado
        """
        widget.configure(master=self.content_frame)
    
    def get_content_frame(self) -> ctk.CTkFrame:
        """Retornar o frame de conteúdo para adicionar widgets.
        
        Returns:
            Frame interno onde widgets devem ser adicionados
        """
        return self.content_frame