# infra/healthcheck.py
from __future__ import annotations
from typing import Dict, Any, Tuple
from infra.supabase_client import get_supabase
from core.session.session_guard import SessionGuard

DEFAULT_BUCKET = "rc-docs"  # altere se seu bucket tiver outro nome


def check_tesseract() -> Tuple[bool, str]:
    """
    Verifica se Tesseract OCR está disponível.

    Retorna:
        (ok, message): tupla com status e versão/erro

    Referência:
        - pytesseract: https://pypi.org/project/pytesseract/
        - Tesseract instalação Windows: https://github.com/UB-Mannheim/tesseract/wiki
    """
    try:
        import pytesseract

        version = pytesseract.get_tesseract_version()
        return True, f"v{version}"
    except ImportError:
        return False, "pytesseract não instalado"
    except Exception as e:
        return False, f"Tesseract não encontrado: {e}"


def healthcheck(bucket: str = DEFAULT_BUCKET) -> Dict[str, Any]:
    """
    Verifica:
      - Sessão válida (get_session/refresh).
      - Leitura do Storage (listagem no bucket).
      - Tesseract OCR disponível (opcional).
    Retorna dict com 'ok' e itens detalhados.
    """
    sb = get_supabase()
    items = {}
    ok = True

    # 1) Sessão
    alive = SessionGuard.ensure_alive()
    items["session"] = {"ok": bool(alive)}
    ok = ok and bool(alive)

    # 2) Storage (lista raiz do bucket)
    try:
        resp = sb.storage.from_(bucket).list()
        # supabase-py retorna lista; qualquer retorno sem exceção já validou acesso
        items["storage"] = {
            "ok": True,
            "count": len(resp) if isinstance(resp, list) else None,
        }
    except Exception as e:
        items["storage"] = {"ok": False, "error": str(e)}
        ok = False

    # 3) Tesseract OCR (opcional - não afeta status geral 'ok')
    tesseract_ok, tesseract_msg = check_tesseract()
    items["tesseract"] = {"ok": tesseract_ok, "version": tesseract_msg}

    return {"ok": ok, "items": items, "bucket": bucket}
