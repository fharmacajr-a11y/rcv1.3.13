# -*- coding: utf-8 -*-
# core/classify_document.py
from __future__ import annotations
from pathlib import Path
import re
from typing import Dict, Any

# Heurísticas simples por nome (sem OCR)
_PATTERNS = [
    (r'\bcnpj\b|\bcart(ao|ão)?\s*cnpj\b', 'cartao_cnpj'),
    (r'\bcontrato\b|\brequerimento\s+de\s+empres[aá]rio\b', 'ato_constitutivo'),
    (r'\balvar[aá]\b', 'alvara_funcionamento'),
    (r'\bcrf\b|\bconselho\s+regional\s+de\s+farm[aá]cia\b', 'crf_regularidade'),
    (r'\bextrato\b.*\bcaixa\b', 'extrato_caixa'),
    (r'\bcomprovante\b.*\bendere[cç]o\b|\bconta\b.*\b(água|agua|luz|energia|saae|copasa|cemig|enel)\b',
     'endereco_empresa'),
]

def _guess_by_name(path: Path) -> tuple[str, float]:
    name = re.sub(r'[_\-]+', ' ', path.name.lower())
    for pat, label in _PATTERNS:
        if re.search(pat, name):
            return label, 0.9
    return 'desconhecido', 0.2

def classify_document(file_path: str) -> Dict[str, Any]:
    """Classifica um PDF pelo nome do arquivo sem OCR (fallback seguro)."""
    p = Path(file_path)
    label, score = _guess_by_name(p)
    titles = {
        'cartao_cnpj': 'Cartão CNPJ',
        'ato_constitutivo': 'Ato Constitutivo',
        'alvara_funcionamento': 'Alvará de Funcionamento',
        'crf_regularidade': 'Certidão CRF',
        'extrato_caixa': 'Extrato CAIXA',
        'endereco_empresa': 'Comprovante de Endereço',
        'desconhecido': 'Documento não identificado'
    }
    return {
        "path": str(p),
        "kind": label,
        "title": titles.get(label, 'Documento'),
        "confidence": score,
        "source": "filename"
    }
