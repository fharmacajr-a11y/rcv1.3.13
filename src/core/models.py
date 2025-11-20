from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Cliente:
    id: Optional[int]
    numero: Optional[str]
    nome: Optional[str]
    razao_social: Optional[str]
    cnpj: Optional[str]
    cnpj_norm: Optional[str]
    ultima_alteracao: Optional[str]
    obs: Optional[str]
    ultima_por: Optional[str]
    created_at: Optional[str] = None
