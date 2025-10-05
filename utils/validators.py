# utils/validators.py
from __future__ import annotations

import re
import sqlite3
from typing import Optional, Iterable, Dict, Any, Tuple

# -------------------------- helpers básicos --------------------------

_ONLY_DIGITS = re.compile(r"\D+")

def only_digits(s: Optional[str]) -> str:
    return _ONLY_DIGITS.sub("", s or "")


def normalize_text(s: Optional[str]) -> str:
    return (s or "").strip()


# -------------------------- WhatsApp (BR) --------------------------

def normalize_whatsapp(num: Optional[str], country_code: str = "55") -> str:
    """
    Normaliza número para dígitos, preferindo prefixo do país (BR: '55').
    Regras simples:
      - remove tudo que não é dígito;
      - se não começar com country_code, prefixa;
      - mantém assim mesmo se já vier com 55.
    """
    d = only_digits(num)
    if not d:
        return ""
    if not d.startswith(country_code):
        d = country_code + d
    return d


def is_valid_whatsapp_br(num: Optional[str]) -> bool:
    """
    Validação leve para BR:
      - Aceita 13 dígitos ('55' + 11 dígitos, DDI + DDD + 9xxxxx-xxxx).
      - Também aceita 12 ('55' + 10) em casos antigos (fixos/DDD).
    """
    d = normalize_whatsapp(num)
    return len(d) in (12, 13)


# -------------------------- CNPJ --------------------------

def normalize_cnpj(cnpj: Optional[str]) -> str:
    return only_digits(cnpj)


def is_valid_cnpj(cnpj: Optional[str]) -> bool:
    """
    Valida CNPJ pelos dígitos verificadores.
    """
    c = normalize_cnpj(cnpj)
    if len(c) != 14:
        return False
    # rejeita sequências óbvias
    if c == c[0] * 14:
        return False

    def dv_calc(base: str) -> str:
        pesos = [6,5,4,3,2,9,8,7,6,5,4,3,2]
        soma = sum(int(d)*pesos[i+1] for i, d in enumerate(base))
        r = soma % 11
        dv = 0 if r < 2 else 11 - r
        return str(dv)

    d1 = dv_calc(c[:12])
    d2 = dv_calc(c[:12] + d1)
    return (c[-2:] == d1 + d2)


# -------------------------- campos requeridos --------------------------

def validate_required_fields(data: Dict[str, Any], required: Iterable[str]) -> Dict[str, str]:
    """
    Retorna dict de erros {campo: 'mensagem'} para os campos vazios.
    """
    errors: Dict[str, str] = {}
    for key in required:
        val = data.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors[key] = "Campo obrigatório."
    return errors


# -------------------------- duplicatas --------------------------

def check_duplicates(
    *,
    cnpj: Optional[str] = None,
    numero: Optional[str] = None,
    razao_social: Optional[str] = None,
    exclude_id: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
    existing: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Checa duplicatas por CNPJ / WhatsApp (NUMERO) / Razão Social.

    Use UMA fonte:
      - conn: consulta SQL (recomendado p/ produção), OU
      - existing: lista de registros já carregados (fallback em memória).

    Retorna:
      {
        'duplicates': { 'CNPJ': [ids...], 'NUMERO': [ids...], 'RAZAO_SOCIAL': [ids...] },
        'has_any': bool
      }

    Exemplo (SQL):
      res = check_duplicates(
          cnpj="12.345.678/0001-90",
          numero="(11) 99999-0000",
          razao_social="Farmácia Exemplo LTDA",
          exclude_id=42,
          conn=my_conn,
      )
    """
    dup: Dict[str, list] = {"CNPJ": [], "NUMERO": [], "RAZAO_SOCIAL": []}

    cnpj_d = normalize_cnpj(cnpj)
    numero_d = only_digits(numero)
    razao_n = normalize_text(razao_social)

    if conn is not None:
        try:
            conn.row_factory = sqlite3.Row
            clauses = []
            params = []

            # Construímos uma única UNION ALL para evitar múltiplas idas ao banco
            union_sql = []

            if cnpj_d:
                union_sql.append(
                    "SELECT 'CNPJ' AS K, ID FROM clientes WHERE DELETED_AT IS NULL AND CNPJ = ?"
                )
                params.append(cnpj_d)

            if numero_d:
                union_sql.append(
                    "SELECT 'NUMERO' AS K, ID FROM clientes WHERE DELETED_AT IS NULL AND NUMERO = ?"
                )
                params.append(numero_d)

            if razao_n:
                # COLLATE NOCASE para case-insensitive; acentos ficam conforme DB
                union_sql.append(
                    "SELECT 'RAZAO_SOCIAL' AS K, ID FROM clientes WHERE DELETED_AT IS NULL AND RAZAO_SOCIAL = ? COLLATE NOCASE"
                )
                params.append(razao_n)

            if not union_sql:
                return {"duplicates": dup, "has_any": False}

            q = " UNION ALL ".join(union_sql)
            if exclude_id is not None:
                q = f"SELECT K, ID FROM ({q}) WHERE ID <> ?"
                params.append(int(exclude_id))

            cur = conn.execute(q, tuple(params))
            for row in cur.fetchall():
                k = row["K"]
                idv = int(row["ID"])
                if exclude_id is not None and idv == exclude_id:
                    continue
                if k in dup:
                    dup[k].append(idv)
        except Exception:
            # Em caso de erro de conexão/SQL, devolvemos vazio (não quebrar fluxo)
            pass
    elif existing is not None:
        try:
            for row in existing:
                rid = int(row.get("ID") or row.get("id") or 0)
                if exclude_id and rid == exclude_id:
                    continue
                if cnpj_d and normalize_cnpj(row.get("CNPJ") or row.get("cnpj")) == cnpj_d:
                    dup["CNPJ"].append(rid)
                if numero_d and only_digits(row.get("NUMERO") or row.get("numero")) == numero_d:
                    dup["NUMERO"].append(rid)
                if razao_n and normalize_text(row.get("RAZAO_SOCIAL") or row.get("razao_social")).lower() == razao_n.lower():
                    dup["RAZAO_SOCIAL"].append(rid)
        except Exception:
            pass

    has_any = any(dup.values())
    return {"duplicates": dup, "has_any": has_any}


# -------------------------- pacote de validação de formulário --------------------------

def validate_cliente_payload(
    *,
    nome: Optional[str],
    razao_social: Optional[str],
    cnpj: Optional[str],
    numero: Optional[str],
) -> Dict[str, Any]:
    """
    Valida e normaliza dados principais de cliente (sem side-effects).
    Retorna:
      {
        'ok': bool,
        'errors': {campo: msg...},
        'clean': { 'nome': ..., 'razao_social': ..., 'cnpj': ..., 'numero': ... }
      }
    """
    clean = {
        "nome": normalize_text(nome),
        "razao_social": normalize_text(razao_social),
        "cnpj": normalize_cnpj(cnpj),
        "numero": normalize_whatsapp(numero) if numero else "",
    }

    errors: Dict[str, str] = {}
    errors.update(validate_required_fields(clean, ("razao_social", "cnpj")))

    if clean["cnpj"] and not is_valid_cnpj(clean["cnpj"]):
        errors["cnpj"] = "CNPJ inválido."

    if clean["numero"] and not is_valid_whatsapp_br(clean["numero"]):
        errors["numero"] = "WhatsApp inválido."

    ok = not errors
    return {"ok": ok, "errors": errors, "clean": clean}
