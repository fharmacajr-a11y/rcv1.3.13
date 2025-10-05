"""SQLite helpers para RC v1.5.6 (com Lixeira / soft-delete)."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Iterable, Sequence, Any, Optional, Callable

from config.paths import DB_PATH

# -------------------------------------------------------------------
# Tipagem opcional do dataclass Cliente
# - Em tempo de análise (mypy): só expõe o símbolo para hints.
# - Em runtime: tenta importar; se não existir, seguimos sem ele.
# -------------------------------------------------------------------
if TYPE_CHECKING:
    pass  # apenas para hints

try:
    import core.models as _models
except Exception:
    _models = None  # type: ignore[assignment]

# Definido uma única vez; Callable para o mypy saber que é "chamável" quando não for None.
ClienteRuntime: Callable[..., Any] | None
if _models is not None and hasattr(_models, "Cliente"):
    ClienteRuntime = _models.Cliente  # type: ignore[attr-defined]
else:
    ClienteRuntime = None

# ----------------------------
# Conexão e utilidades básicas
# ----------------------------
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _colunas_tabela(conn: sqlite3.Connection, tabela: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info({tabela})")
    return [row["name"] for row in cur.fetchall()]


def _add_coluna_se_nao_existir(
    conn: sqlite3.Connection, tabela: str, coluna: str, tipo_sql: str
) -> None:
    colunas = _colunas_tabela(conn, tabela)
    if coluna not in colunas:
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo_sql}")
        conn.commit()

# ----------------------------
# Inicialização / Migrações
# ----------------------------
def init_db() -> None:
    """Garante a existência da tabela e colunas principais (inclui DELETED_AT) e índices."""
    conn = get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                NUMERO TEXT,
                NOME TEXT,
                RAZAO_SOCIAL TEXT,
                CNPJ TEXT,
                ULTIMA_ALTERACAO TEXT,
                OBS TEXT
            )
            """
        )
        conn.commit()

        # Soft-delete
        _add_coluna_se_nao_existir(conn, "clientes", "DELETED_AT", "TEXT")

        # Índices importantes para performance
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cnpj ON clientes(CNPJ)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_numero ON clientes(NUMERO)")
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()


def init_or_upgrade() -> None:
    """Alias para compatibilidade; hoje só chama init_db()."""
    init_db()

# ----------------------------
# Conversões (opcional)
# ----------------------------
def _row_to_cliente(row: sqlite3.Row) -> Any:
    """
    Converte sqlite3.Row para:
      - dict (fallback) quando o dataclass Cliente não estiver presente, ou
      - instância de Cliente (quando presente em runtime).
    """
    if ClienteRuntime is None:
        # Retorna um dict se o dataclass não existir (compatibilidade).
        return {
            "id": row["ID"],
            "numero": row["NUMERO"],
            "nome": row["NOME"],
            "razao_social": row["RAZAO_SOCIAL"],
            "cnpj": row["CNPJ"],
            "ultima_alteracao": row["ULTIMA_ALTERACAO"],
            "obs": row["OBS"],
        }
    # Se tiver dataclass Cliente em runtime, mapeia nele
    return ClienteRuntime(
        id=row["ID"],
        numero=row["NUMERO"],
        nome=row["NOME"],
        razao_social=row["RAZAO_SOCIAL"],
        cnpj=row["CNPJ"],
        ultima_alteracao=row["ULTIMA_ALTERACAO"],
        obs=row["OBS"],
    )


# ----------------------------
# CRUD básico
# ----------------------------
def insert_cliente(
    numero: str,
    nome: str,
    razao_social: str,
    cnpj: str,
    obs: str = "",
) -> int:
    agora = datetime.now().isoformat()
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO clientes (NUMERO, NOME, RAZAO_SOCIAL, CNPJ, ULTIMA_ALTERACAO, OBS, DELETED_AT)
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            """,
            (numero, nome, razao_social, cnpj, agora, obs),
        )
        conn.commit()
        # lastrowid pode ser Optional[int] — normalize
        return int(cur.lastrowid) if cur.lastrowid is not None else 0
    finally:
        conn.close()


def update_cliente(
    cliente_id: int,
    numero: str,
    nome: str,
    razao_social: str,
    cnpj: str,
    obs: str,
) -> None:
    agora = datetime.now().isoformat()
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE clientes
               SET NUMERO=?,
                   NOME=?,
                   RAZAO_SOCIAL=?,
                   CNPJ=?,
                   ULTIMA_ALTERACAO=?,
                   OBS=?
             WHERE ID=?
            """,
            (numero, nome, razao_social, cnpj, agora, obs, cliente_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_cliente(cliente_ids: Sequence[int]) -> int:
    """APAGA DEFINITIVAMENTE do banco (use com cuidado)."""
    ids = list(cliente_ids)
    if not ids:
        return 0
    conn = get_conn()
    try:
        qmarks = ",".join("?" for _ in ids)
        cur = conn.execute(f"DELETE FROM clientes WHERE ID IN ({qmarks})", ids)
        conn.commit()
        rc = cur.rowcount if cur.rowcount is not None else 0
        return int(rc)
    finally:
        conn.close()


def get_cliente(cliente_id: int) -> Any | None:
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT ID, NUMERO, NOME, RAZAO_SOCIAL, CNPJ, ULTIMA_ALTERACAO, OBS FROM clientes WHERE ID=?",
            (cliente_id,),
        )
        row = cur.fetchone()
        return _row_to_cliente(row) if row else None
    finally:
        conn.close()


# ----------------------------
# Listagens
# ----------------------------
_ORDER_MAP: dict[Optional[str], str] = {
    None: "RAZAO_SOCIAL COLLATE NOCASE ASC",
    "RAZAO_SOCIAL": "RAZAO_SOCIAL COLLATE NOCASE ASC",
    "NOME": "NOME COLLATE NOCASE ASC",
    "CNPJ": "CNPJ COLLATE NOCASE ASC",
    "ULTIMA_ALTERACAO": "ULTIMA_ALTERACAO DESC",
}


def list_clientes(order_by: str | None = None) -> list[Any]:
    """Lista SOMENTE os clientes ativos (DELETED_AT IS NULL)."""
    order_sql = _ORDER_MAP.get(order_by or None, _ORDER_MAP[None])
    conn = get_conn()
    try:
        cur = conn.execute(
            f"""
            SELECT ID, NUMERO, NOME, RAZAO_SOCIAL, CNPJ, ULTIMA_ALTERACAO, OBS
              FROM clientes
             WHERE DELETED_AT IS NULL
             ORDER BY {order_sql}
            """
        )
        rows = cur.fetchall()
        return [_row_to_cliente(r) for r in rows]
    finally:
        conn.close()


def list_clientes_deletados(order_by: str | None = None) -> list[sqlite3.Row]:
    """Retorna linhas dos clientes na Lixeira (inclui DELETED_AT)."""
    order_sql = _ORDER_MAP.get(order_by or None, _ORDER_MAP["ULTIMA_ALTERACAO"])
    conn = get_conn()
    try:
        cur = conn.execute(
            f"""
            SELECT ID, NUMERO, NOME, RAZAO_SOCIAL, CNPJ, ULTIMA_ALTERACAO, OBS, DELETED_AT
              FROM clientes
             WHERE DELETED_AT IS NOT NULL
             ORDER BY {order_sql}
            """
        )
        return list(cur.fetchall())
    finally:
        conn.close()


# ----------------------------
# Soft-delete (Lixeira)
# ----------------------------
def soft_delete_clientes(ids: Iterable[int]) -> int:
    """Marca clientes como deletados (DELETED_AT = agora)."""
    ids_list = [int(i) for i in ids]
    if not ids_list:
        return 0
    agora = datetime.now().isoformat()
    conn = get_conn()
    try:
        qmarks = ",".join("?" for _ in ids_list)
        cur = conn.execute(
            f"UPDATE clientes SET DELETED_AT=? WHERE ID IN ({qmarks}) AND DELETED_AT IS NULL",
            (agora, *ids_list),
        )
        conn.commit()
        rc = cur.rowcount if cur.rowcount is not None else 0
        return int(rc)
    finally:
        conn.close()


def restore_clientes(ids: Iterable[int]) -> int:
    """Restaura clientes da Lixeira (DELETED_AT = NULL)."""
    ids_list = [int(i) for i in ids]
    if not ids_list:
        return 0
    conn = get_conn()
    try:
        qmarks = ",".join("?" for _ in ids_list)
        cur = conn.execute(
            f"UPDATE clientes SET DELETED_AT=NULL, ULTIMA_ALTERACAO=? WHERE ID IN ({qmarks})",
            (datetime.now().isoformat(), *ids_list),
        )
        conn.commit()
        rc = cur.rowcount if cur.rowcount is not None else 0
        return int(rc)
    finally:
        conn.close()


def purge_clientes(ids: Iterable[int]) -> int:
    """Apaga definitivamente do banco (sem mexer nos arquivos)."""
    return delete_cliente(list(ids))


__all__ = [
    "get_conn",
    "init_db",
    "init_or_upgrade",
    "insert_cliente",
    "update_cliente",
    "delete_cliente",
    "get_cliente",
    "list_clientes",
    # Lixeira
    "soft_delete_clientes",
    "list_clientes_deletados",
    "restore_clientes",
    "purge_clientes",
]
