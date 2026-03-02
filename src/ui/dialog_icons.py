# -*- coding: utf-8 -*-
"""Ícones gráficos PIL para diálogos modais do RC Gestor.

Gera ícones desenhados via Pillow (sem assets externos) para os dialogs
de confirmação e resultado, mantendo consistência visual.

API pública:
    make_icon_label(parent, kind, size=44) -> CTkLabel
        kind: "success" | "warning" | "error"

Fallback automático para emoji se Pillow não estiver disponível.
"""
from __future__ import annotations

from typing import Any, Literal

_KIND = Literal["success", "warning", "error"]

# Fallback emoji caso PIL não esteja disponível
_FALLBACK_EMOJI: dict[str, str] = {
    "success": "✅",
    "warning": "⚠️",
    "error": "❌",
}


def _draw_success(size: int) -> Any:
    """Círculo verde (#22c55e) com checkmark branco."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = max(2, size // 14)
    # Círculo preenchido verde
    d.ellipse(
        [pad, pad, size - pad - 1, size - pad - 1],
        fill=(34, 197, 94, 255),
        outline=(22, 163, 74, 255),
        width=2,
    )

    # Checkmark — dois segmentos
    sw = max(2, size // 10)
    s = float(size)
    # Ponto de inflexão: (0.44, 0.68)
    pts = [
        (s * 0.27, s * 0.52),
        (s * 0.44, s * 0.68),
        (s * 0.74, s * 0.35),
    ]
    d.line(pts, fill=(255, 255, 255, 255), width=sw)
    return img


def _draw_warning(size: int) -> Any:
    """Triângulo âmbar (#eab308) com exclamação branca."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = max(2, size // 16)
    half = size // 2

    # Triângulo
    tri = [
        (half, pad + 1),
        (size - pad - 1, size - pad - 1),
        (pad + 1, size - pad - 1),
    ]
    d.polygon(tri, fill=(234, 179, 8, 255), outline=(180, 130, 0, 255))

    # Barra da exclamação
    bw = max(2, size // 10)
    bx = int(half - bw / 2)
    top_bar = int(size * 0.38)
    bot_bar = int(size * 0.62)
    d.rectangle([bx, top_bar, bx + bw, bot_bar], fill=(255, 255, 255, 255))

    # Ponto da exclamação
    dot_t = int(size * 0.68)
    dot_b = int(size * 0.76)
    d.ellipse([bx, dot_t, bx + bw, dot_b], fill=(255, 255, 255, 255))

    return img


def _draw_error(size: int) -> Any:
    """Círculo vermelho (#ef4444) com × branco."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = max(2, size // 14)
    d.ellipse(
        [pad, pad, size - pad - 1, size - pad - 1],
        fill=(220, 38, 38, 255),
        outline=(185, 28, 28, 255),
        width=2,
    )

    sw = max(2, size // 10)
    m = int(size * 0.28)
    M = size - m
    d.line([(m, m), (M, M)], fill=(255, 255, 255, 255), width=sw)
    d.line([(M, m), (m, M)], fill=(255, 255, 255, 255), width=sw)

    return img


_DRAWERS = {
    "success": _draw_success,
    "warning": _draw_warning,
    "error": _draw_error,
}


def make_icon_label(parent: Any, kind: _KIND = "success", size: int = 44) -> Any:
    """Retorna CTkLabel com ícone gráfico PIL desenhado.

    Args:
        parent: Widget pai (CTkFrame ou similar).
        kind:   Tipo de ícone: "success", "warning" ou "error".
        size:   Dimensão em pixels (quadrado). Padrão: 44.

    Returns:
        CTkLabel com image= preenchido. Fallback: CTkLabel com emoji.
    """
    from src.ui.ctk_config import ctk

    try:
        from customtkinter import CTkImage  # type: ignore[import]

        draw_fn = _DRAWERS.get(kind, _draw_success)
        pil_img = draw_fn(size)
        icon = CTkImage(light_image=pil_img, dark_image=pil_img, size=(size, size))
        return ctk.CTkLabel(parent, image=icon, text="")
    except Exception:
        # Fallback seguro se PIL não disponível
        return ctk.CTkLabel(
            parent,
            text=_FALLBACK_EMOJI.get(kind, "ℹ️"),
            font=("Segoe UI Emoji", 28),
        )
