# core/services/clientes_service.py � vers�o Supabase (libera Nome/Whats; mant�m CNPJ/Raz�o)
from __future__ import annotations

import logging
import os
import shutil
import threading
import time
from typing import Optional, Tuple

from infra.supabase_client import exec_postgrest, supabase
from src.app_utils import safe_base_from_fields
from src.config.paths import CLOUD_ONLY, DOCS_DIR
from src.core.db_manager import (
    find_cliente_by_cnpj_norm,
    insert_cliente,
    list_clientes,
    update_cliente,
)
from src.core.logs.audit import log_client_action
from src.core.session.session import get_current_user
from src.utils.file_utils import ensure_subpastas, write_marker
from src.utils.validators import normalize_text

from src.core.cnpj_norm import normalize_cnpj as normalize_cnpj_norm

log = logging.getLogger(__name__)

# Valor em mem�ria para exibir se a rede falhar momentaneamente
_LAST_CLIENTS_COUNT = 0
_clients_lock = threading.Lock()


def _count_clients_raw() -> int:
    """
    Executa a contagem real de clientes no Supabase.
    C�digo original extra�do para isolamento de retry.
    """
    resp = exec_postgrest(supabase.table("clients").select("id", count="exact").is_("deleted_at", "null"))
    return resp.count or 0


def count_clients(*, max_retries: int = 2, base_delay: float = 0.2) -> int:
    """
    Conta clientes ativos do Supabase com retry leve e tratamento resiliente.

    - Se der WSAEWOULDBLOCK (WinError 10035), faz alguns retries com backoff leve.
    - Se falhar, retorna o �ltimo valor conhecido sem quebrar a UI.
    - Mant�m cache em mem�ria (_LAST_CLIENTS_COUNT) para resili�ncia.
    """
    global _LAST_CLIENTS_COUNT

    attempt = 0
    while True:
        try:
            # Chamada real (sem englobar lock para n�o bloquear outras threads)
            total = _count_clients_raw()

            # Atualiza o cache com lock
            with _clients_lock:
                _LAST_CLIENTS_COUNT = int(total)
                return _LAST_CLIENTS_COUNT

        except OSError as e:
            # WinError 10035 = WSAEWOULDBLOCK (socket non-blocking)
            if getattr(e, "winerror", 0) == 10035:
                if attempt < max_retries:
                    delay = base_delay * (attempt + 1)
                    log.warning("Clientes: socket ocupada (10035); retry em %.1fs...", delay)
                    time.sleep(delay)
                    attempt += 1
                    continue

                # Devolve o �ltimo valor conhecido com lock
                with _clients_lock:
                    log.info("Clientes: usando last-known=%s ap�s 10035", _LAST_CLIENTS_COUNT)
                    return _LAST_CLIENTS_COUNT

            # Outros erros de rede -> warning + last-known
            log.warning(
                "Clientes: erro de rede ao contar; usando last-known=%s (%r)",
                _LAST_CLIENTS_COUNT,
                e,
            )
            with _clients_lock:
                return _LAST_CLIENTS_COUNT

        except Exception as e:
            # �ltimo guarda-chuva: n�o quebrar UI por causa do contador
            log.warning(
                "Clientes: falha inesperada ao contar; usando last-known=%s (%r)",
                _LAST_CLIENTS_COUNT,
                e,
            )
            with _clients_lock:
                return _LAST_CLIENTS_COUNT


def _normalize_payload(valores: dict) -> Tuple[str, str, str, str, str, str]:
    """
    Normaliza campos vindos da UI/tabela para uso interno no serviço.
    Retorna tupla (razao, cnpj, cnpj_norm, nome, numero, obs).
    """

    def _v(d: dict, *keys: str) -> str:
        for k in keys:
            v = d.get(k)
            if isinstance(v, str):
                v = v.strip()
                if v:
                    return v
        return ""

    razao = _v(valores, "Razão Social", "Razao Social", "razao_social")
    cnpj = _v(valores, "CNPJ", "cnpj")
    nome = _v(valores, "Nome", "nome")
    numero = _v(valores, "WhatsApp", "Whatsapp", "whatsapp", "Telefone", "telefone", "numero")
    obs = _v(valores, "Observações", "Observacoes", "observacoes", "Obs", "obs")

    cnpj_norm = normalize_cnpj_norm(cnpj)
    return razao, cnpj, cnpj_norm, nome, numero, obs


def checar_duplicatas_info(
    numero: str,
    cnpj: str,
    nome: str,
    razao: str,
    *,
    exclude_id: int | None = None,
) -> dict[str, object]:
    """Retorna informações de possíveis duplicatas.

    - ``cnpj_conflict``: cliente com mesmo ``cnpj_norm`` (None se não houver).
    - ``razao_conflicts``: lista de clientes com mesma razão social mas CNPJ distinto.
    """

    cnpj_norm = normalize_cnpj_norm(cnpj)
    cnpj_conflict = find_cliente_by_cnpj_norm(cnpj_norm, exclude_id=exclude_id) if cnpj_norm else None

    razao_norm = normalize_text(razao or "")
    razao_conflicts: list = []
    if razao_norm:
        for cliente in list_clientes():
            if exclude_id and cliente.id == exclude_id:
                continue
            if normalize_text(cliente.razao_social or "") != razao_norm:
                continue
            cliente_norm = (cliente.cnpj_norm or "") if getattr(cliente, "cnpj_norm", None) is not None else normalize_cnpj_norm(cliente.cnpj or "")
            if cnpj_norm:
                if cliente_norm == cnpj_norm:
                    continue
            elif not cliente_norm:
                # se ambos estão sem CNPJ normalizado, não alerta
                continue
            razao_conflicts.append(cliente)

    return {
        "cnpj_conflict": cnpj_conflict,
        "razao_conflicts": razao_conflicts,
        "numero_conflicts": [],
        "cnpj_norm": cnpj_norm,
        "razao_norm": razao_norm,
    }


def _pasta_do_cliente(pk: int, cnpj: str, numero: str, razao: str) -> str:
    base = safe_base_from_fields(cnpj, numero, razao, pk)
    pasta = os.path.join(str(DOCS_DIR), base)
    if not CLOUD_ONLY:
        ensure_subpastas(pasta)
        write_marker(pasta, pk)
    return pasta


def _migrar_pasta_se_preciso(old_path: Optional[str], nova_pasta: str) -> None:
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
    - Bloqueia somente quando houver CNPJ duplicado (mesmo ``cnpj_norm``).
    """
    razao, cnpj, cnpj_norm, nome, numero, obs = _normalize_payload(valores)
    if not (razao or cnpj or nome or numero):
        raise ValueError("Preencha pelo menos Raz�o Social, CNPJ, Nome ou WhatsApp.")

    current_id = int(row[0]) if row else None
    if cnpj_norm:
        conflict = find_cliente_by_cnpj_norm(cnpj_norm, exclude_id=current_id)
        if conflict:
            raiser = conflict.razao_social or "-"
            stored_cnpj = conflict.cnpj or "-"
            raise ValueError(f'CNPJ j� cadastrado para o cliente ID {conflict.id} �?" {raiser}. CNPJ: {stored_cnpj}.')

    if row:
        pk = int(row[0])
        update_cliente(
            pk,
            numero=numero,
            nome=nome,
            razao_social=razao,
            cnpj=cnpj,
            obs=obs,
            cnpj_norm=cnpj_norm,
        )
        real_pk = pk
        old_path = None
    else:
        real_pk = insert_cliente(
            numero=numero,
            nome=nome,
            razao_social=razao,
            cnpj=cnpj,
            obs=obs,
            cnpj_norm=cnpj_norm,
        )
        old_path = None

    # Auditoria
    try:
        user = get_current_user() or ""
        log_client_action(user, int(real_pk), "edi��o" if row else "cria��o")  # pyright: ignore[reportArgumentType]
    except Exception:
        pass

    # Pasta local (opcional)
    pasta = _pasta_do_cliente(real_pk, cnpj, numero, razao)
    _migrar_pasta_se_preciso(old_path, pasta)
    return real_pk, pasta
