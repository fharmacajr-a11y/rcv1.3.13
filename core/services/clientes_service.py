# core/services/clientes_service.py
from __future__ import annotations

from utils.validators import only_digits, normalize_text
import os
import shutil
import sqlite3
import logging
from datetime import datetime as dt

from config.paths import DB_PATH, DOCS_DIR
from app_utils import safe_base_from_fields
from utils.file_utils import ensure_subpastas, write_marker
from core.logs.audit import log_client_action
from core.session.session import get_current_user

log = logging.getLogger(__name__)
MARKER_NAME = ".rc_client_id"




def _normalize_payload(data: dict) -> dict:
    """Normaliza campos-chave do cliente sem alterar a API pública."""
    out = dict(data or {})
    if 'CNPJ' in out and out['CNPJ'] is not None:
        out['CNPJ'] = only_digits(str(out['CNPJ']))
    if 'NUMERO' in out and out['NUMERO'] is not None:
        out['NUMERO'] = only_digits(str(out['NUMERO']))
    if 'NOME' in out and out['NOME'] is not None:
        out['NOME'] = normalize_text(str(out['NOME']))
    if 'RAZAO_SOCIAL' in out and out['RAZAO_SOCIAL'] is not None:
        out['RAZAO_SOCIAL'] = normalize_text(str(out['RAZAO_SOCIAL']))
    return out

def _checar_duplicatas(conn, numero, cnpj, nome, razao) -> list[int]:
    """Checa duplicatas em uma ida ao banco (UNION ALL). Ignora soft-delete."""
    cur = conn.cursor()
    parts, params = [], []

    cnpj_d = only_digits(cnpj or "")
    numero_d = only_digits(numero or "")
    nome_n = normalize_text(nome or "")
    razao_n = normalize_text(razao or "")

    if cnpj_d:
        parts.append("SELECT ID FROM clientes WHERE DELETED_AT IS NULL AND CNPJ = ?")
        params.append(cnpj_d)
    if numero_d:
        parts.append("SELECT ID FROM clientes WHERE DELETED_AT IS NULL AND NUMERO = ?")
        params.append(numero_d)
    if nome_n:
        parts.append("SELECT ID FROM clientes WHERE DELETED_AT IS NULL AND NOME = ? COLLATE NOCASE")
        params.append(nome_n)
    if razao_n:
        parts.append("SELECT ID FROM clientes WHERE DELETED_AT IS NULL AND RAZAO_SOCIAL = ? COLLATE NOCASE")
        params.append(razao_n)

    if not parts:
        return []

    sql = " UNION ALL ".join(parts)
    rows = cur.execute(sql, params).fetchall()
    return sorted(set(int(r[0]) for r in rows or []))


def checar_duplicatas_info(numero: str, cnpj: str, nome: str, razao: str) -> dict[str, list]:
    """
    Utilitário para a UI: retorna {'ids': [...], 'campos': ['CNPJ','WhatsApp',...]}
    dos registros ATIVOS que colidem com os valores informados.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ids = set()
    campos: list[str] = []

    def run(label: str, sql: str, val: str):
        if not val:
            return
        try:
            cur.execute(sql, (val,))
            rows = [r[0] for r in cur.fetchall()]
            if rows:
                campos.append(label)
                ids.update(rows)
        except Exception:
            pass

    run('CNPJ',        "SELECT ID FROM clientes WHERE CNPJ=? AND (DELETED_AT IS NULL OR DELETED_AT='')", cnpj)
    run('WhatsApp',    "SELECT ID FROM clientes WHERE NUMERO=? AND (DELETED_AT IS NULL OR DELETED_AT='')", numero)
    run('Nome',        "SELECT ID FROM clientes WHERE NOME=? AND (DELETED_AT IS NULL OR DELETED_AT='')", nome)
    run('Razão Social',"SELECT ID FROM clientes WHERE RAZAO_SOCIAL=? AND (DELETED_AT IS NULL OR DELETED_AT='')", razao)

    try:
        conn.close()
    except Exception:
        pass

    return {'ids': sorted(ids), 'campos': campos}


def _pasta_do_cliente(pk: int, cnpj: str, numero: str, razao: str) -> str:
    base = safe_base_from_fields(cnpj or "", numero or "", razao or "", pk)
    pasta = os.path.join(DOCS_DIR, base)
    os.makedirs(pasta, exist_ok=True)
    ensure_subpastas(pasta)
    write_marker(pasta, pk)
    return pasta


def _migrar_pasta_se_preciso(old_path: str | None, nova_pasta: str) -> None:
    if not old_path or not os.path.isdir(old_path):
        return
    try:
        ensure_subpastas(old_path)
        for item in os.listdir(old_path):
            src = os.path.join(old_path, item)
            dst = os.path.join(nova_pasta, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
    except Exception:
        log.exception("Falha ao migrar pasta antiga para a nova (%s -> %s)", old_path, nova_pasta)


def salvar_cliente(row, valores: dict) -> tuple[int, str]:
    """
    Persiste cliente (cria/edita), audita, garante estrutura de pasta e
    retorna (id, caminho_da_pasta).
    """
    razao  = (valores.get("Razão Social") or "").strip()
    cnpj   = (valores.get("CNPJ") or "").strip()
    nome   = (valores.get("Nome") or "").strip()
    numero = (valores.get("WhatsApp") or "").strip()
    obs    = (valores.get("Observações") or "").strip()

    if not (razao or cnpj or nome or numero):
        raise ValueError("Preencha pelo menos Razão Social, CNPJ, Nome ou WhatsApp.")

    pk = None
    orig_numero = orig_razao = orig_cnpj = None
    if row:
        pk, numero_old, nome_old, razao_old, cnpj_old, ult, obs_old = row
        orig_numero, orig_razao, orig_cnpj = numero_old, razao_old, cnpj_old

    old_path = None
    if pk and (orig_numero is not None or orig_razao is not None or orig_cnpj is not None):
        old_base = safe_base_from_fields(orig_cnpj or "", orig_numero or "", orig_razao or "", pk)
        old_path = os.path.join(DOCS_DIR, old_base)

    agora = dt.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if pk:
        # edição
        cur.execute(
            """
            UPDATE clientes
               SET NUMERO=?,NOME=?,RAZAO_SOCIAL=?,CNPJ=?,ULTIMA_ALTERACAO=?,OBS=?
             WHERE ID=?
            """,
            (numero, nome, razao, cnpj, agora, obs, pk),
        )
        real_pk = pk
    else:
        # criação: checar duplicatas e anotar IDs (únicos, ordenados)
        try:
            ids_dup = _checar_duplicatas(conn, numero, cnpj, nome, razao)
        except Exception:
            ids_dup = []
        if ids_dup:
            ids_str = ",".join(str(i) for i in sorted(set(ids_dup)))
            marcador = f"[DUPLICATA de IDs: {ids_str}]"
            obs = marcador if not obs else marcador + "\n" + obs

        cur.execute(
            """
            INSERT INTO clientes
                  (NUMERO,NOME,RAZAO_SOCIAL,CNPJ,ULTIMA_ALTERACAO,OBS)
            VALUES (?,?,?,?,?,?)
            """,
            (numero, nome, razao, cnpj, agora, obs),
        )
        real_pk = cur.lastrowid
        pk = real_pk

    conn.commit()
    conn.close()

    # Auditoria
    try:
        user = get_current_user() or ""
        log_client_action(user, int(real_pk), "edição" if row else "criação")
    except Exception:
        pass

    # Pasta
    pasta = _pasta_do_cliente(real_pk, cnpj, numero, razao)
    _migrar_pasta_se_preciso(old_path, pasta)
    return real_pk, pasta