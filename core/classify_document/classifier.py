# core/classifier.py
from pathlib import Path
from detectors.cnpj_card import detect_and_extract


def classify_document(path: str) -> dict:
    """
    Classifica um arquivo PDF.
    Retorna:
      {"type": "<tipo>", "meta": {...}}
    """
    # 1) Detecção por CONTEÚDO (Cartão CNPJ)
    data = detect_and_extract(path)
    if data:
        return {
            "type": "cnpj_card",
            "meta": {
                "cnpj": data["cnpj"],
                "razao_social": data["razao_social"],
                "source": "content",
            },
        }

    # 2) Fallback por NOME (mantém compatibilidade)
    name = Path(path).name.lower()
    if "cnpj" in name:
        return {"type": "cnpj_card", "meta": {"source": "filename"}}

    # 3) Desconhecido
    return {"type": "desconhecido", "meta": {}}
