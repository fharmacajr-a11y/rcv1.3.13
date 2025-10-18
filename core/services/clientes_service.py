# core/services/clientes_service.py — versão Supabase (libera Nome/Whats; mantém CNPJ/Razão)
from __future__ import annotations

import os
import shutil
import logging

from utils.validators import only_digits, normalize_text
from config.paths import DOCS_DIR, CLOUD_ONLY
from app_utils import safe_base_from_fields
from utils.file_utils import ensure_subpastas, write_marker
from core.logs.audit import log_client_action
from core.session.session import get_current_user
from core.db_manager import insert_cliente, update_cliente, list_clientes

log = logging.getLogger(__name__)


def _normalize_payload(valores: dict) -> tuple[str, str, str, str, str]:
    razao = (valores.get("Razão Social") or "").strip()
    cnpj = (valores.get("CNPJ") or "").strip()
    nome = (valores.get("Nome") or "").strip()
    numero = (valores.get("WhatsApp") or "").strip()
    obs = (valores.get("Observações") or "").strip()
    return razao, cnpj, nome, numero, obs


def _exists_duplicate(
    numero: str, cnpj: str, nome: str, razao: str, *, skip_id: int | None = None
) -> list[int]:
    """
    Retorna IDs de possíveis duplicatas considerando **apenas**:
      - CNPJ (somente dígitos)
      - Razão Social (normalizada/trim)

    OBS: Nome e WhatsApp (numero) **não** entram mais no critério de duplicidade.
    """
    cnpj_d = only_digits(cnpj or "")
    razao_n = normalize_text(razao or "")

    ids: list[int] = []
    for c in list_clientes():
        if skip_id and c.id == skip_id:
            continue

        # CNPJ único
        if cnpj_d and only_digits(c.cnpj or "") == cnpj_d:
            ids.append(int(c.id))
            continue

        # Razão Social única (case/trim insensível conforme normalize_text)
        if razao_n and normalize_text(c.razao_social or "") == razao_n:
            ids.append(int(c.id))
            continue

        # Nome / Número (WhatsApp) foram propositalmente ignorados

    return sorted(set(ids))


def checar_duplicatas_info(
    numero: str, cnpj: str, nome: str, razao: str
) -> dict[str, list]:
    """
    Mantida a assinatura por compatibilidade.
    Retorna {"ids": [...]} considerando só CNPJ/Razão.
    """
    ids = _exists_duplicate(numero, cnpj, nome, razao)
    return {"ids": ids}


def _pasta_do_cliente(pk: int, cnpj: str, numero: str, razao: str) -> str:
    base = safe_base_from_fields(cnpj, numero, razao, pk)
    pasta = os.path.join(str(DOCS_DIR), base)
    if not CLOUD_ONLY:
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
        log.exception("Falha ao migrar pasta (%s -> %s)", old_path, nova_pasta)


def salvar_cliente(row, valores: dict) -> tuple[int, str]:
    """
    Cria/atualiza cliente.
    - Permite duplicatas de Nome e WhatsApp.
    - Bloqueia quando CNPJ **ou** Razão Social já existirem (IDs retornados).
    """
    razao, cnpj, nome, numero, obs = _normalize_payload(valores)
    if not (razao or cnpj or nome or numero):
        raise ValueError("Preencha pelo menos Razão Social, CNPJ, Nome ou WhatsApp.")

    # Checagem de duplicatas (apenas CNPJ/Razão)
    current_id = int(row[0]) if row else None
    dups = _exists_duplicate(numero, cnpj, nome, razao, skip_id=current_id)

    # Se criando e bateu CNPJ/Razão, bloqueia
    if dups and not row:
        raise ValueError(f"Já existe cliente com algum desses dados (IDs: {dups}).")

    if row:
        pk = int(row[0])
        update_cliente(
            pk, numero=numero, nome=nome, razao_social=razao, cnpj=cnpj, obs=obs
        )
        real_pk = pk
        old_path = None
    else:
        real_pk = insert_cliente(
            numero=numero, nome=nome, razao_social=razao, cnpj=cnpj, obs=obs
        )
        old_path = None

    # Auditoria
    try:
        user = get_current_user() or ""
        log_client_action(user, int(real_pk), "edição" if row else "criação")
    except Exception:
        pass

    # Pasta local (opcional)
    pasta = _pasta_do_cliente(real_pk, cnpj, numero, razao)
    _migrar_pasta_se_preciso(old_path, pasta)
    return real_pk, pasta
