# -*- coding: utf-8 -*-
"""INTERNAL: implementação particionada do pipeline de clientes; API pública exposta por pipeline.py."""

from __future__ import annotations

from typing import Any, Dict

try:
    from tkinter import Text
except Exception:  # pragma: no cover
    Text = None  # type: ignore[assignment]


def _get_widget_value(w: Any) -> str:
    """Retorna string de Entry/Combobox (get) ou Text (1.0 .. end), sempre strip."""
    try:
        if Text is not None and isinstance(w, Text):
            return (w.get("1.0", "end") or "").strip()
    except Exception:
        pass
    try:
        return (w.get() or "").strip()
    except Exception:
        return (str(w) or "").strip()


def _val(ents: Dict[str, Any], *keys: str) -> str:
    """Busca a primeira chave disponível em ents, tolerando variações de rótulo."""
    for k in keys:
        if k in ents:
            return _get_widget_value(ents[k])
    return ""


def coletar_valores(ents: Dict[str, Any]) -> Dict[str, str]:
    razao = _val(ents, "Razão Social", "Razao Social", "Razao", "razao", "razao_social")
    cnpj = _val(ents, "CNPJ", "cnpj")
    nome = _val(ents, "Nome", "nome")
    numero = _val(ents, "WhatsApp", "whatsapp", "Telefone", "numero")
    obs = _val(ents, "Observações", "Observacoes", "Observa??es", "Obs", "obs")

    out = {
        "Razão Social": razao,
        "CNPJ": cnpj,
        "Nome": nome,
        "WhatsApp": numero,
        "Observações": obs,
    }

    if any(k in ents for k in ("Status do Cliente", "Status", "status")):
        out["Status do Cliente"] = _val(ents, "Status do Cliente", "Status", "status")

    return out


__all__ = ["coletar_valores"]
