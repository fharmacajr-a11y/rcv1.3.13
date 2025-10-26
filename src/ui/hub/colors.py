# -*- coding: utf-8 -*-
"""
Helpers de cor e tags de autor para a tela do Hub.

Funções puras de coloração por email (hashing estável) e configuração
de tags tkinter para destaque visual dos autores.
"""

import hashlib
from typing import Optional, Dict
from src.ui.hub.utils import _hsl_to_hex
from src.core.logger import get_logger

logger = get_logger(__name__)


def _author_color(email: str) -> str:
    """
    Cor estável por autor com alto contraste (S=90%, L=28%).
    """
    key = (email or "").strip().lower()
    if not key:
        return "#3a3a3a"
    d = hashlib.md5(key.encode("utf-8")).hexdigest()
    hue = int(d[:2], 16) * (360/255.0)  # 0..360
    return _hsl_to_hex(hue, 0.90, 0.28)


def _ensure_author_tag(text_widget, email: str, tag_cache: Optional[Dict[str, str]] = None) -> str:
    """
    Garante que exista uma tag de estilo para o autor e retorna o nome da tag.
    
    Args:
        text_widget: Widget Text do tkinter onde configurar a tag
        email: Email do autor para gerar cor e nome da tag
        tag_cache: Dict opcional mapeando email -> nome_da_tag (para reuso)
                   Se não for passado, um cache é armazenado no próprio widget
        
    Returns:
        Nome da tag configurada (formato "author:<email>")
    """
    # 1) Cache: externo, interno no widget, ou novo
    if tag_cache is None:
        # Tenta reaproveitar cache interno do widget
        cache = getattr(text_widget, "_author_tags", None)
        if cache is None:
            cache = {}
            try:
                setattr(text_widget, "_author_tags", cache)
            except Exception:
                # Se o widget bloquear setattr, segue sem cache persistente
                logger.debug("Hub: widget não aceita atributo _author_tags; usando cache efêmero.")
        tag_cache = cache
    
    # 2) Já existe no cache?
    if email in tag_cache:
        return tag_cache[email]
    
    # 3) Cria uma tag nova
    # Nome de tag estável por autor
    tag_name = f"author:{email or 'unknown'}"
    
    try:
        # Se já existir no widget, não recrie — apenas reutilize
        if tag_name not in text_widget.tag_names():
            color = _author_color(email)
            # Aplica foreground com fonte padrão
            text_widget.tag_configure(tag_name, foreground=color, font=("TkDefaultFont", 10, "bold"))
    except Exception:
        logger.exception("Hub: falha ao configurar tag do autor '%s'.", email)
        # Fallback: retorna um nome simples para não quebrar o fluxo
        tag_name = "author:default"
    
    # 4) Atualiza cache (se existir)
    try:
        tag_cache[email] = tag_name
    except Exception:
        pass
    
    return tag_name
