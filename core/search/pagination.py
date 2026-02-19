from __future__ import annotations

"""
Pagination helpers for clientes search (Sprint 4).
SQL with LIMIT/OFFSET + safe fallbacks, without breaking existing search module.
"""
from typing import Optional, List
import sqlite3
import unicodedata

from config.paths import DB_PATH
from core.models import Cliente


def _unaccent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))


def _digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _ensure_sqlite_functions(conn: sqlite3.Connection) -> None:
    # Idempotent registrations
    try:
        conn.create_function("unaccent", 1, _unaccent)
    except Exception:
        pass
    try:
        conn.create_function("digits", 1, _digits)
    except Exception:
        pass


def _parse_term(term: str) -> tuple[str, str]:
    t = (term or "").strip()
    t_txt = _unaccent(t).upper()
    t_dig = _digits(t)
    return t_txt, t_dig


def _order_from_label(order_label: Optional[str]) -> tuple[str, str]:
    # Map human label -> SQL ORDER BY
    mapping = {
        "Razão Social (A->Z)": ("RAZAO_SOCIAL", "ASC"),
        "CNPJ (A->Z)": ("CNPJ", "ASC"),
        "Nome (A->Z)": ("NOME", "ASC"),
        "Ultima Alteracao (Recente)": ("ULTIMA_ALTERACAO", "DESC"),
    }
    col, dir_ = mapping.get(order_label or "Razão Social (A->Z)", ("RAZAO_SOCIAL", "ASC"))
    return col, dir_


_SQL_BASE_WHERE = """
    FROM clientes
    WHERE (DELETED_AT IS NULL OR DELETED_AT='')
      AND (
            ? = ''
         OR unaccent(upper(NOME))          LIKE '%' || ? || '%'
         OR unaccent(upper(RAZAO_SOCIAL))  LIKE '%' || ? || '%'
         OR digits(NUMERO)                 LIKE '%' || ? || '%'
         OR digits(CNPJ)                   LIKE '%' || ? || '%'
      )
"""


def count_clientes(term: str) -> int:
    t_txt, t_dig = _parse_term(term)
    conn = sqlite3.connect(DB_PATH)
    _ensure_sqlite_functions(conn)
    try:
        cur = conn.execute("SELECT COUNT(*) " + _SQL_BASE_WHERE, (t_txt, t_txt, t_txt, t_dig, t_dig))
        return int(cur.fetchone()[0] or 0)
    finally:
        conn.close()


def search_clientes_paged(term: str, order_label: Optional[str], limit: int, offset: int) -> List[Cliente]:
    t_txt, t_dig = _parse_term(term)
    col, dir_ = _order_from_label(order_label)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_functions(conn)
    try:
        sql = f"""
            SELECT ID, NUMERO, NOME, RAZAO_SOCIAL, CNPJ, ULTIMA_ALTERACAO, OBS
            {_SQL_BASE_WHERE}
            ORDER BY {col} {dir_}
            LIMIT ? OFFSET ?
        """
        params = (t_txt, t_txt, t_txt, t_dig, t_dig, int(limit), int(offset))
        rows = conn.execute(sql, params).fetchall()
        clientes: List[Cliente] = []
        for r in rows:
            try:
                clientes.append(
                    Cliente(
                        id=r["ID"],
                        numero=r["NUMERO"],
                        nome=r["NOME"],
                        razao_social=r["RAZAO_SOCIAL"],
                        cnpj=r["CNPJ"],
                        ultima_alteracao=r["ULTIMA_ALTERACAO"],
                        obs=r["OBS"],
                    )
                )
            except Exception:
                # Construtor diferente? cria parcial
                clientes.append(
                    Cliente(
                        id=r["ID"],
                        numero=r["NUMERO"],
                        nome=r["NOME"],
                        razao_social=r["RAZAO_SOCIAL"],
                        cnpj=r["CNPJ"],
                        ultima_alteracao=r.get("ULTIMA_ALTERACAO") if isinstance(r, dict) else None,
                        obs=None,
                    )
                )
        return clientes
    finally:
        conn.close()
