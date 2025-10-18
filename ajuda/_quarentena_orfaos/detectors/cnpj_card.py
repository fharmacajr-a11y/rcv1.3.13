# detectors/cnpj_card.py
import re

# Mantém o padrão do seu projeto: detectar CNPJ no formato oficial
_CNPJ_RE = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")


def detect_and_extract(path: str) -> dict | None:
    """
    Detecta se o PDF é Cartão CNPJ pelo conteúdo.
    Retorna {"type": "cnpj_card", "cnpj": "...", "razao_social": "..."}
    ou None se não for.
    """
    # Lazy import: só carrega o leitor de PDF quando realmente precisar
    from utils.pdf_reader import read_pdf_text

    text = read_pdf_text(path)
    up = text.upper()

    # Heurística simples: cabeçalho típico do Cartão CNPJ
    if "CADASTRO NACIONAL DA PESSOA JURÍDICA" not in up:
        return None

    m = _CNPJ_RE.search(text)
    cnpj = m.group(0) if m else None
    razao = _extract_razao_social(text)

    if cnpj and razao:
        return {"type": "cnpj_card", "cnpj": cnpj, "razao_social": razao}
    return None


def _extract_razao_social(text: str) -> str | None:
    """
    Tenta extrair a razão social do bloco do Cartão CNPJ.
    Procura pelo rótulo 'NOME EMPRESARIAL' e pega o valor na mesma
    linha (após ':'), ou, se não houver, na linha de baixo.
    """
    lines = text.splitlines()
    for i, raw in enumerate(lines):
        line = raw.strip()
        if "NOME EMPRESARIAL" in line.upper():
            parts = line.split(":", 1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()
            if i + 1 < len(lines) and lines[i + 1].strip():
                return lines[i + 1].strip()
    return None
