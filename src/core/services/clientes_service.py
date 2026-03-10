# -*- coding: utf-8 -*-
# core/services/clientes_service.py – versão Supabase (libera Nome/Whats; mantém CNPJ/Razão)
from __future__ import annotations

import logging
import os
import shutil
import threading
from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

from src.infra.supabase_client import exec_postgrest, supabase
from src.core.app_utils import safe_base_from_fields
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
from src.utils.formatters import format_cnpj
from src.utils.phone_utils import format_phone_br

from src.core.cnpj_norm import normalize_cnpj as normalize_cnpj_norm
from src.utils.phone_utils import only_phone_digits

log = logging.getLogger(__name__)


# BUG-002: Cache thread-safe com dataclass
@dataclass
class ClientsCache:
    """Cache thread-safe para contagem de clientes."""

    count: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


_clients_cache = ClientsCache()


def _count_clients_raw() -> int:
    """
    Executa a contagem real de clientes no Supabase.
    Código original extraído para isolamento de retry.
    """
    resp = exec_postgrest(supabase.table("clients").select("id", count="exact").is_("deleted_at", "null"))
    return resp.count or 0


def count_clients(*, max_retries: int = 2, base_delay: float = 0.2) -> int:
    """
    Conta clientes ativos do Supabase com retry via retry_policy e tratamento resiliente.

    - Erros transitórios (WinError 10035 etc.) são retentados por exec_postgrest.
    - Se falhar, retorna o último valor conhecido sem quebrar a UI.
    - Mantém cache thread-safe em _clients_cache para evitar race conditions.
    """
    global _clients_cache

    try:
        total: int = _count_clients_raw()
        with _clients_cache.lock:
            _clients_cache.count = int(total)
            return _clients_cache.count
    except Exception as e:
        log.warning(
            "Clientes: erro ao contar; usando last-known=%s (%r)",
            _clients_cache.count,
            e,
        )
        with _clients_cache.lock:
            return _clients_cache.count


def _normalize_payload(valores: dict[str, Any]) -> Tuple[str, str, str, str, str, str]:
    """
    Normaliza campos vindos da UI/tabela para uso interno no serviço.
    Retorna tupla (razao, cnpj_formatado, cnpj_norm, nome, numero_formatado, obs).

    IMPORTANTE:
    - cnpj é salvo FORMATADO (00.000.000/0000-00)
    - cnpj_norm é calculado apenas com dígitos (para checagem de duplicidade)
    - numero (WhatsApp) é salvo FORMATADO (+55 DD XXXXX-XXXX)
    """

    def _v(d: dict[str, Any], *keys: str) -> str:
        for k in keys:
            v: Any = d.get(k)
            if isinstance(v, str):
                v = v.strip()
                if v:
                    return v
        return ""

    razao: str = _v(valores, "Razão Social", "Razao Social", "razao_social")
    cnpj_raw: str = _v(valores, "CNPJ", "cnpj")
    nome: str = _v(valores, "Nome", "nome")
    numero_raw: str = _v(valores, "WhatsApp", "Whatsapp", "whatsapp", "Telefone", "telefone", "numero")
    obs: str = _v(valores, "Observações", "Observacoes", "observacoes", "Obs", "obs")

    # CNPJ: formatar para exibição, calcular norm para duplicidade
    cnpj_formatado = format_cnpj(cnpj_raw) if cnpj_raw else cnpj_raw
    # Se format_cnpj retornar o original (inválido), manter original
    if not cnpj_formatado or cnpj_formatado == cnpj_raw:
        cnpj_formatado = cnpj_raw
    cnpj_norm: str = normalize_cnpj_norm(cnpj_raw)

    # WhatsApp: formatar para padrão +55 DD XXXXX-XXXX
    numero_formatado = format_phone_br(numero_raw) if numero_raw else numero_raw
    # Se format_phone_br retornar vazio (inválido), manter original
    if not numero_formatado:
        numero_formatado = numero_raw

    return razao, cnpj_formatado, cnpj_norm, nome, numero_formatado, obs


def checar_duplicatas_info(
    numero: str,
    cnpj: str,
    nome: str,
    razao: str,
    *,
    exclude_id: int | None = None,
) -> dict[str, object]:
    """
    Retorna informações de possíveis duplicatas.

    PERF-001: Otimizado para usar queries diretas no Supabase ao invés de iterar list_clientes().
    - ``cnpj_conflict``: cliente com mesmo ``cnpj_norm`` (None se não houver).
    - ``razao_conflicts``: lista de clientes com mesma razão social mas CNPJ distinto.
    """

    cnpj_norm: str = normalize_cnpj_norm(cnpj)
    cnpj_conflict: Any = find_cliente_by_cnpj_norm(cnpj_norm, exclude_id=exclude_id) if cnpj_norm else None

    razao_norm: str = normalize_text(razao or "")
    razao_conflicts: list[Any] = []

    if razao_norm and CLOUD_ONLY:
        # PERF-001: Query direta no Supabase usando filtros
        try:
            query = supabase.table("clients").select("*").is_("deleted_at", "null")

            if exclude_id:
                query = query.neq("id", exclude_id)

            if cnpj_norm:
                # Apenas conflitos com CNPJ diferente
                query = query.neq("cnpj_norm", cnpj_norm)

            resp = exec_postgrest(query)
            if resp.data:
                for cliente_data in resp.data:
                    cliente_razao = normalize_text(cliente_data.get("razao_social") or "")
                    if cliente_razao == razao_norm:
                        # Converte dict para objeto para compatibilidade
                        from types import SimpleNamespace

                        razao_conflicts.append(SimpleNamespace(**cliente_data))
        except Exception as exc:
            log.warning("Falha ao buscar conflitos de razão social no Supabase: %s", exc)
            # Fallback para método local
            for cliente in list_clientes(limit=None):
                if exclude_id and cliente.id == exclude_id:
                    continue
                if normalize_text(cliente.razao_social or "") != razao_norm:
                    continue
                cliente_norm: str = (
                    (cliente.cnpj_norm or "")
                    if getattr(cliente, "cnpj_norm", None) is not None
                    else normalize_cnpj_norm(cliente.cnpj or "")
                )
                if cnpj_norm:
                    if cliente_norm == cnpj_norm:
                        continue
                elif not cliente_norm:
                    continue
                razao_conflicts.append(cliente)
    elif razao_norm:
        # Modo local: usa list_clientes()
        for cliente in list_clientes(limit=None):
            if exclude_id and cliente.id == exclude_id:
                continue
            if normalize_text(cliente.razao_social or "") != razao_norm:
                continue
            cliente_norm: str = (
                (cliente.cnpj_norm or "")
                if getattr(cliente, "cnpj_norm", None) is not None
                else normalize_cnpj_norm(cliente.cnpj or "")
            )
            if cnpj_norm:
                if cliente_norm == cnpj_norm:
                    continue
            elif not cliente_norm:
                continue
            razao_conflicts.append(cliente)

    # P1-1: Detecção de conflitos por número/telefone (digits-only match)
    numero_digits = only_phone_digits(numero) if numero else ""
    # Normalizar: remover prefixo 55 (código BR) quando presente
    if numero_digits.startswith("55") and len(numero_digits) > 11:
        numero_digits = numero_digits[2:]
    numero_conflicts: list[Any] = []
    if numero_digits and len(numero_digits) >= 10:
        try:
            if CLOUD_ONLY:
                q = supabase.table("clients").select("id,razao_social,cnpj,numero").is_("deleted_at", "null")
                if exclude_id:
                    q = q.neq("id", exclude_id)
                resp_num = exec_postgrest(q)
                for row in resp_num.data or []:
                    row_digits = only_phone_digits(row.get("numero") or "")
                    if row_digits.startswith("55") and len(row_digits) > 11:
                        row_digits = row_digits[2:]
                    if row_digits and row_digits == numero_digits:
                        from types import SimpleNamespace

                        numero_conflicts.append(SimpleNamespace(**row))
            else:
                for cliente in list_clientes(limit=None):
                    if exclude_id and cliente.id == exclude_id:
                        continue
                    cliente_digits = only_phone_digits(getattr(cliente, "numero", "") or "")
                    if cliente_digits.startswith("55") and len(cliente_digits) > 11:
                        cliente_digits = cliente_digits[2:]
                    if cliente_digits and cliente_digits == numero_digits:
                        numero_conflicts.append(cliente)
        except Exception as exc:
            log.warning("Falha ao buscar conflitos de numero no Supabase: %s", exc)

    return {
        "cnpj_conflict": cnpj_conflict,
        "razao_conflicts": razao_conflicts,
        "numero_conflicts": numero_conflicts,
        "cnpj_norm": cnpj_norm,
        "razao_norm": razao_norm,
    }


def _pasta_do_cliente(pk: int, cnpj: str, numero: str, razao: str) -> str:
    """Resolve and prepare the filesystem path for the given cliente."""
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


def salvar_cliente(row: tuple[Any, ...] | None, valores: dict[str, Any]) -> tuple[int, str]:
    """Create or update a client, enforcing basic validation and CNPJ uniqueness."""
    razao: str
    cnpj: str
    cnpj_norm: str
    nome: str
    numero: str
    obs: str
    razao, cnpj, cnpj_norm, nome, numero, obs = _normalize_payload(valores)
    # Bloco de notas é salvo na tabela cliente_bloco_notas via RPC rc_save_cliente_bloco_notas.
    if not (razao or cnpj or nome or numero):
        raise ValueError("Preencha pelo menos Razão Social, CNPJ, Nome ou WhatsApp.")

    current_id: int | None = int(row[0]) if row else None
    if cnpj_norm:
        conflict: Any = find_cliente_by_cnpj_norm(cnpj_norm, exclude_id=current_id)
        if conflict:
            raiser: str = conflict.razao_social or "-"
            stored_cnpj: str = conflict.cnpj or "-"
            raise ValueError(f'CNPJ já cadastrado para o cliente ID {conflict.id} — "{raiser}". CNPJ: {stored_cnpj}.')

    real_pk: int
    old_path: str | None
    if row:
        pk: int = int(row[0])
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
        user: Any = get_current_user() or ""
        log_client_action(user, int(real_pk), "edicao" if row else "criacao")  # pyright: ignore[reportArgumentType]
    except Exception as exc:
        log.debug("Falha ao registrar auditoria do cliente %s", real_pk, exc_info=exc)

    # Pasta local (opcional)
    pasta: str = _pasta_do_cliente(real_pk, cnpj, numero, razao)
    _migrar_pasta_se_preciso(old_path, pasta)
    return real_pk, pasta
