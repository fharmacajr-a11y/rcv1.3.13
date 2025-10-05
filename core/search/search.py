"""High-level search helpers for Cliente records (SQL + fallback)."""
from __future__ import annotations

import sqlite3
import unicodedata
from datetime import datetime
from typing import Optional

from core.db_manager import list_clientes, get_conn  # get_conn já existe no projeto
from core.models import Cliente


def _normalize_order(order_by: Optional[str]) -> tuple[Optional[str], bool]:
    """Map GUI labels to database columns and whether sorting is descending."""
    if not order_by:
        return None, False

    normalized = unicodedata.normalize("NFKD", order_by)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    sanitized = "".join(ch for ch in normalized.lower() if ch.isalnum())

    if "ultima" in sanitized and "alteracao" in sanitized:
        return "ULTIMA_ALTERACAO", True
    if "razao" in sanitized:
        return "RAZAO_SOCIAL", False
    if "cnpj" in sanitized:
        return "CNPJ", False
    if "nome" in sanitized:
        return "NOME", False

    upper = (order_by or "").upper()
    valid = {"ID", "NUMERO", "NOME", "RAZAO_SOCIAL", "CNPJ", "ULTIMA_ALTERACAO"}
    return (upper if upper in valid else None), False


def _parse_timestamp(value: Optional[str]) -> datetime:
    if not value:
        return datetime.min
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.min


# ---------------- helpers comuns (fallback) ----------------
def _strip_accents(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _fallback_python(term: str, order_by: str | None) -> list[Cliente]:
    """Versão Python (a mesma que você já recebeu), usada como fallback seguro."""
    column, descending = _normalize_order(order_by)
    clientes = list_clientes(order_by=column)

    raw = (term or "").strip()
    t_text = _strip_accents(raw).casefold()
    t_digits = _digits(raw)

    if t_text:
        out: list[Cliente] = []
        for c in clientes:
            nome = _strip_accents(getattr(c, "nome", "")).casefold()
            razao = _strip_accents(getattr(c, "razao_social", "")).casefold()
            cnpj = (getattr(c, "cnpj", "") or "").casefold()
            numero_digits = _digits(getattr(c, "numero", ""))

            if t_text in nome or t_text in razao:
                out.append(c); continue
            if t_text in _strip_accents(cnpj).casefold():
                out.append(c); continue
            if t_digits and (t_digits in _digits(cnpj) or (numero_digits and t_digits in numero_digits)):
                out.append(c)
        clientes = out

    if descending and column == "ULTIMA_ALTERACAO":
        clientes.sort(key=lambda c: _parse_timestamp(c.ultima_alteracao), reverse=True)
    return clientes


# ---------------- busca SQL com unaccent ----------------
def _sqlite_unaccent(s: Optional[str]) -> str:
    if s is None:
        return ""
    return _strip_accents(str(s))


def _sqlite_digits(s: Optional[str]) -> str:
    if s is None:
        return ""
    return _digits(str(s))


def _sql_order(order_by: Optional[str]) -> str:
    col, desc = _normalize_order(order_by)
    if not col:
        return "ORDER BY ID ASC"
    if col == "ULTIMA_ALTERACAO":
        return f"ORDER BY {col} {'DESC' if desc else 'ASC'}"
    return f"ORDER BY {col} {'DESC' if desc else 'ASC'}"


def _rows_to_clientes(rows: list[sqlite3.Row]) -> list[Cliente]:
    out: list[Cliente] = []
    for r in rows:
        try:
            # Ajuste para os nomes reais de colunas no seu schema
            out.append(
                Cliente(
                    id=r["ID"],
                    numero=r["NUMERO"],
                    nome=r["NOME"],
                    razao_social=r["RAZAO_SOCIAL"],
                    cnpj=r["CNPJ"],
                    ultima_alteracao=r["ULTIMA_ALTERACAO"],
                    obs=r["OBS"] if "OBS" in r.keys() else None,  # tolerante
                    deleted_at=r["DELETED_AT"] if "DELETED_AT" in r.keys() else None,
                )
            )
        except Exception:
            # Se o construtor for diferente, tente criar parcial
            try:
                c = Cliente()
                setattr(c, "id", r["ID"])
                setattr(c, "numero", r["NUMERO"])
                setattr(c, "nome", r["NOME"])
                setattr(c, "razao_social", r["RAZAO_SOCIAL"])
                setattr(c, "cnpj", r["CNPJ"])
                setattr(c, "ultima_alteracao", r["ULTIMA_ALTERACAO"])
                out.append(c)
            except Exception:
                # Em último caso, ignora a linha problemática
                continue
    return out


def _search_sql(term: str, order_by: str | None) -> list[Cliente]:
    raw = (term or "").strip()
    if not raw:
        # Sem termo -> delega para listagem padrão
        col, _ = _normalize_order(order_by)
        return list_clientes(order_by=col)

    t_txt = _strip_accents(raw).lower()
    t_dig = _digits(raw)

    sql = [
        "SELECT ID, NUMERO, NOME, RAZAO_SOCIAL, CNPJ, ULTIMA_ALTERACAO, OBS, DELETED_AT",
        "FROM clientes",
        "WHERE DELETED_AT IS NULL",
        "AND (",
        # texto acento-insensível
        "LOWER(unaccent(NOME)) LIKE :pat_txt",
        "OR LOWER(unaccent(RAZAO_SOCIAL)) LIKE :pat_txt",
        # também aceita texto no CNPJ como string
        "OR LOWER(unaccent(CNPJ)) LIKE :pat_txt",
    ]
    params = {"pat_txt": f"%{t_txt}%"}

    if t_dig:
        sql += [
            "OR digits(CNPJ) LIKE :pat_dig",
            "OR digits(NUMERO) LIKE :pat_dig",
        ]
        params["pat_dig"] = f"%{t_dig}%"

    sql.append(")")
    sql.append(_sql_order(order_by))
    q = " ".join(sql)

    conn = get_conn()
    try:
        # registra funções auxiliares (idempotente por conexão)
        conn.create_function("unaccent", 1, _sqlite_unaccent)
        conn.create_function("digits", 1, _sqlite_digits)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(q, params)
        rows = cur.fetchall()
        return _rows_to_clientes(rows)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def search_clientes(term: str, order_by: str | None = None) -> list[Cliente]:
    """
    Prioriza SQL (com unaccent + digits) e, se houver qualquer erro,
    volta para o filtro Python (seguro).
    """
    try:
        return _search_sql(term, order_by)
    except Exception:
        # Segurança acima de tudo: não quebrar a busca
        return _fallback_python(term, order_by)


__all__ = ["search_clientes"]
