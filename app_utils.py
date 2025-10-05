import re
from datetime import datetime as dt

RESERVED_WIN_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
RESERVED_WIN_NAMES = {s.upper() for s in RESERVED_WIN_NAMES}

def fmt_data(iso: str) -> str:
    if not iso:
        return ""
    try:
        return dt.fromisoformat(iso).strftime("%d/%m/%Y - %H:%M:%S")
    except Exception:
        return iso

def only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")

def slugify_name(s: str) -> str:
    if not s:
        return ""
    slug = re.sub(r"[^A-Za-z0-9_]+", "_", s.strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:60]

def safe_base_from_fields(cnpj: str, numero: str, razao: str, pk: int) -> str:
    cnpj_digits = only_digits(cnpj)
    if len(cnpj_digits) == 14:
        base = cnpj_digits
    else:
        num_digits = only_digits(numero)
        if len(num_digits) >= 10:
            base = num_digits
        else:
            base = slugify_name(razao) or f"id_{pk}"
    if base.upper() in RESERVED_WIN_NAMES:
        base = f"id_{pk}_{base}"
    return base

def split_meta(resto: str) -> tuple[str, str]:
    if not resto:
        return "", ""
    partes = [p.strip() for p in re.split(r"\s*[-–—_|]\s*", resto) if p.strip()]
    razao = partes[0] if len(partes) >= 1 else ""
    nome = partes[1] if len(partes) >= 2 else ""
    return razao, nome

def parse_pasta(nome: str) -> dict[str, str]:
    base = nome.strip()
    dig = only_digits(base)

    if len(dig) == 14:
        import re
        m = re.search(r"^\D*(\d{14})\D*(.*)$", base)
        resto = (m.group(2) if m else "").strip()
        razao, pessoa = split_meta(resto)
        return {"cnpj": dig, "numero": "", "razao": razao, "pessoa": pessoa}

    if 10 <= len(dig) <= 15:
        import re
        m = re.search(r"^\D*(\d{10,15})\D*(.*)$", base)
        resto = (m.group(2) if m else "").strip()
        razao, pessoa = split_meta(resto)
        return {"cnpj": "", "numero": dig, "razao": razao, "pessoa": pessoa}

    razao, pessoa = split_meta(base)
    return {"cnpj": "", "numero": "", "razao": razao, "pessoa": pessoa}
