from __future__ import annotations

import re
import unicodedata

# -------- regex padrões --------
RE_CNPJ = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b")

LABEL_PATTERN = re.compile(
    r"(?<!\w)(raz[a\u00e3]o\s*/?\s*nome\s*empresarial|raz[a\u00e3]o\s*social|nome\s*empresarial|empresa)(?!\w)",
    flags=re.IGNORECASE,
)

LABEL_ONLY_VALUES = {
    "razao social",
    "razao nome empresarial",
    "razao/nome empresarial",
    "nome empresarial",
    "empresa",
}


# -------- utilitários básicos --------
def normalize_ascii(s: str) -> str:
    """Remove acentos e retorna string ASCII simples."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)
    )


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def cnpj_is_valid(cnpj: str) -> bool:
    """Checa se tem 14 dígitos numéricos (validação simples)."""
    return len(only_digits(cnpj or "")) == 14


def format_cnpj(digits14: str) -> str:
    d = only_digits(digits14)
    if len(d) != 14:
        return digits14
    return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


# -------- normalização de nome empresarial --------
def _clean_company_name(raw: str | None) -> str | None:
    if not raw:
        return None
    candidate = clean_text(raw)
    if not candidate:
        return None

    # ✅ Ajuste final: preserva hífen e en-dash, apenas normaliza espaços extras
    candidate = re.sub(r"\s{2,}", " ", candidate).strip()

    return candidate or None


# -------- detecção de labels --------
def _match_label(line: str) -> tuple[int, int] | None:
    if not line:
        return None
    normalized = normalize_ascii(line).lower()
    match = LABEL_PATTERN.search(normalized)
    return (match.start(1), match.end(1)) if match else None


def _is_label_only(line: str) -> bool:
    if not line:
        return False
    normalized = normalize_ascii(line).lower()
    normalized = re.sub(r"[:\-\u2013\u2014]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized in LABEL_ONLY_VALUES


def _next_nonempty_value(lines: list[str], idx: int) -> str | None:
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
    if _is_label_only(candidate):
        return None
    return _clean_company_name(candidate)


# -------- extração de Razão Social --------
def _extract_razao_by_label(lines: list[str]) -> str | None:
    for idx, line in enumerate(lines):
        match_pos = _match_label(line)
        if not match_pos:
            continue
        _, end = match_pos
        value_part = line[end:].lstrip(" :;–—-")
        value_part = re.split(r"\bCNPJ\b", value_part, flags=re.IGNORECASE)[0]
        razao = _clean_company_name(value_part)
        if not razao:
            razao = _next_nonempty_value(lines, idx)
        if razao:
            return razao
    return None


def _extract_razao_near_cnpj(lines: list[str], cnpj_idx: int) -> str | None:
    """Se não encontrar label, tenta achar uma linha de nome perto do CNPJ."""
    start = max(0, cnpj_idx - 3)
    window: list[str] = []
    for line in lines[start:cnpj_idx]:
        candidate = line.strip()
        if not candidate:
            continue
        if RE_CNPJ.search(candidate):
            continue
        if re.search(r"\bCNPJ\b", candidate, flags=re.IGNORECASE):
            continue
        if _is_label_only(candidate):
            continue
        window.append(candidate)
    if not window:
        return None
    return _clean_company_name(max(window, key=len))


# -------- API pública --------
def extract_company_fields(text: str) -> dict[str, str | None]:
    """Extrai CNPJ e Razão Social/Nome Empresarial do texto OCR."""
    if not text:
        return {"cnpj": None, "razao_social": None}

    processed = text.replace("\r", "")
    lines = processed.split("\n")

    # procurar CNPJ
    cnpj: str | None = None
    cnpj_idx: int | None = None
    for idx, line in enumerate(lines):
        match = RE_CNPJ.search(line)
        if match:
            digits = only_digits(match.group(0))
            cnpj = format_cnpj(digits)
            cnpj_idx = idx
            break
    if cnpj is None:
        match = RE_CNPJ.search(processed)
        if match:
            digits = only_digits(match.group(0))
            cnpj = format_cnpj(digits)
            cnpj_idx = processed[: match.start()].count("\n")

    # procurar Razão Social
    razao = _extract_razao_by_label(lines)
    if not razao and cnpj_idx is not None:
        razao = _extract_razao_near_cnpj(lines, cnpj_idx)

    return {"cnpj": cnpj, "razao_social": razao}


def extract_cnpj_razao(text: str) -> tuple[str | None, str | None]:
    fields = extract_company_fields(text)
    return fields.get("cnpj"), fields.get("razao_social")


__all__ = [
    "normalize_ascii",
    "clean_text",
    "cnpj_is_valid",
    "only_digits",
    "format_cnpj",
    "extract_company_fields",
    "extract_cnpj_razao",
]
