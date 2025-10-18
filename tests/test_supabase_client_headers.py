"""
Testes para infra/supabase_client.py - _pick_name_from_cd()
"""

from infra.supabase_client import _pick_name_from_cd


def test_pick_name_simple():
    """Header Content-Disposition simples"""
    cd = 'attachment; filename="relatorio.pdf"'
    assert _pick_name_from_cd(cd, "fallback.zip") == "relatorio.pdf"


def test_pick_name_utf8():
    """Header Content-Disposition com UTF-8 encoding"""
    cd = "attachment; filename*=UTF-8''relat%C3%B3rio.pdf"
    assert _pick_name_from_cd(cd, "fallback.zip") == "relatório.pdf"


def test_pick_name_missing():
    """Content-Disposition ausente (None)"""
    fallback = "default.zip"
    assert _pick_name_from_cd(None, fallback) == fallback


def test_pick_name_empty():
    """Content-Disposition vazio"""
    fallback = "default.zip"
    assert _pick_name_from_cd("", fallback) == fallback


def test_pick_name_no_filename():
    """Content-Disposition sem filename"""
    cd = "attachment"
    fallback = "default.zip"
    result = _pick_name_from_cd(cd, fallback)
    assert result == fallback
