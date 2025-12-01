"""Utilitarios de texto: sanitizacao basica e extracao de CNPJ/razao social."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Sequence

log: logging.Logger = logging.getLogger(__name__)

# -------- regex padrões --------
# Aceita "11.222.333/0001-44" ou "11222333000144" sem grudar em dígitos vizinhos.
RE_CNPJ: re.Pattern[str] = re.compile(r"(?<!\d)(?:\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14})(?!\d)")

# Como normalizamos para ASCII em _match_label, podemos simplificar os acentos aqui
LABEL_PATTERN: re.Pattern[str] = re.compile(
    r"(?<!\w)("
    r"razao\s*/?\s*nome\s*empresarial|"
    r"razao\s*social|"
    r"nome\s*/?\s*razao\s*social|"
    r"denominacao\s*social|"
    r"nome\s*empresarial|"
    r"empresa"
    r")(?!\w)",
    flags=re.IGNORECASE,
)

LABEL_ONLY_VALUES: set[str] = {
    "razao social",
    "razao nome empresarial",
    "razao/nome empresarial",
    "nome razao social",
    "denominacao social",
    "nome empresarial",
    "empresa",
}

# Linhas que não devem ser tratadas como valor de nome
SKIP_VALUE_TOKENS: set[str] = {"matriz", "filial"}


# -------- utilitários básicos --------


def fix_mojibake(s: str | None) -> str | None:
    # Detecta padrões comuns 'Ã' e tenta reverter latin1->utf8
    if s and ("Ã" in s or "Â" in s):
        try:
            return s.encode("latin1").decode("utf-8")
        except Exception as e:
            log.exception("Erro ao corrigir mojibake em '%s': %s", s[:50], e)
    return s


def normalize_ascii(s: str | None) -> str:
    """Remove acentos e retorna string ASCII simples."""
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))


def clean_text(s: str | None) -> str:
    """Remove espacos extras, quebras e tabs, colapsando para unico espaco."""
    return re.sub(r"\s+", " ", (s or "").strip())


def only_digits(s: str | None) -> str:
    """Remove todos os caracteres nao numericos."""
    return re.sub(r"\D", "", s or "")


def cnpj_is_valid(cnpj: str | None) -> bool:
    """Checa se tem 14 dígitos numéricos (validação simples)."""
    return len(only_digits(cnpj or "")) == 14


def format_cnpj(digits14: str | None) -> str | None:
    """Formata string de 14 digitos como CNPJ; retorna entrada original se invalida."""
    d: str = only_digits(digits14)
    if len(d) != 14:
        return digits14
    return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


# -------- normalização de nome empresarial --------
def _clean_company_name(raw: str | None) -> str | None:
    """Limpa nome empresarial mantendo hifen/en-dash e colapsando espacos."""
    if not raw:
        return None
    candidate = clean_text(raw)
    if not candidate:
        return None
    # preserva hífen/en-dash; só colapsa espaços extras
    candidate = re.sub(r"\s{2,}", " ", candidate).strip()
    return candidate or None


# -------- detecção de labels --------
def _match_label(line: str | None) -> tuple[int, int] | None:
    if not line:
        return None
    normalized: str = normalize_ascii(line).lower()
    match = LABEL_PATTERN.search(normalized)
    return (match.start(1), match.end(1)) if match else None


def _is_label_only(line: str | None) -> bool:
    if not line:
        return False
    normalized = normalize_ascii(line).lower()
    normalized = re.sub(r"[:\-\u2013\u2014\.]", " ", normalized)  # inclui ponto final
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized in LABEL_ONLY_VALUES


def _is_skip_value(line: str | None) -> bool:
    norm = normalize_ascii(line).lower().strip()
    return norm in SKIP_VALUE_TOKENS


def _next_nonempty_value(lines: Sequence[str], idx: int) -> str | None:
    """Pega o próximo valor não vazio após uma label."""
    pos = idx + 1
    while pos < len(lines) and not lines[pos].strip():
        pos += 1
    if pos >= len(lines):
        return None
    candidate = lines[pos].strip()
    if RE_CNPJ.search(candidate):
        return None
    if re.search(r"\bCNPJ\b", candidate, flags=re.IGNORECASE):
        return None
    if _is_label_only(candidate) or _is_skip_value(candidate):
        return None
    return _clean_company_name(candidate)


# -------- extração de Razão Social --------
def _extract_razao_by_label(lines: Sequence[str]) -> str | None:
    for idx, line in enumerate(lines):
        match_pos = _match_label(line)
        if not match_pos:
            continue
        _, end = match_pos
        value_part = line[end:].lstrip(" :;–—-")
        value_part = re.split(r"\bCNPJ\b", value_part, flags=re.IGNORECASE)[0]
        razao: str | None = _clean_company_name(value_part)
        if not razao:
            razao = _next_nonempty_value(lines, idx)
        if razao:
            return razao
    return None


def _extract_razao_near_cnpj(lines: Sequence[str], cnpj_idx: int) -> str | None:
    """Se não encontrar label, tenta achar uma linha de nome perto do CNPJ (acima e abaixo)."""
    start = max(0, cnpj_idx - 3)
    end = min(len(lines), cnpj_idx + 3)  # olha também 2 linhas abaixo (cnpj_idx+1, +2)
    window: list[str] = []
    for i in range(start, end):
        if i == cnpj_idx:
            continue
        candidate = lines[i].strip()
        if not candidate:
            continue
        if RE_CNPJ.search(candidate):
            continue
        if re.search(r"\bCNPJ\b", candidate, flags=re.IGNORECASE):
            continue
        if _is_label_only(candidate) or _is_skip_value(candidate):
            continue
        window.append(candidate)
    if not window:
        return None
    return _clean_company_name(max(window, key=len))


# -------- API pública --------
def extract_company_fields(text: str | None) -> dict[str, str | None]:
    """Extrai CNPJ e Razão Social/Nome Empresarial do texto OCR."""
    if not text:
        return {"cnpj": None, "razao_social": None}

    processed = text.replace("\r", "")
    lines: list[str] = processed.split("\n")

    # procurar CNPJ
    cnpj: str | None = None
    cnpj_idx: int | None = None
    for idx, line in enumerate(lines):
        match = RE_CNPJ.search(line)
        if match:
            digits: str = only_digits(match.group(0))
            cnpj = format_cnpj(digits)
            cnpj_idx = idx
            break
    if cnpj is None:
        match = RE_CNPJ.search(processed)
        if match:
            digits: str = only_digits(match.group(0))
            cnpj = format_cnpj(digits)
            # índice aproximado da linha do CNPJ no texto inteiro
            cnpj_idx = processed[: match.start()].count("\n")

    # procurar Razão Social
    razao: str | None = _extract_razao_by_label(lines)
    if not razao and cnpj_idx is not None:
        razao = _extract_razao_near_cnpj(lines, cnpj_idx)

    return {"cnpj": cnpj, "razao_social": razao}


def extract_cnpj_razao(text: str | None) -> tuple[str | None, str | None]:
    fields: dict[str, str | None] = extract_company_fields(text)
    return fields.get("cnpj"), fields.get("razao_social")


__all__ = [
    "fix_mojibake",
    "normalize_ascii",
    "clean_text",
    "cnpj_is_valid",
    "only_digits",
    "format_cnpj",
    "extract_company_fields",
    "extract_cnpj_razao",
]
