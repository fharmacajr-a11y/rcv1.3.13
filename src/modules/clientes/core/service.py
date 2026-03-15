"""Servicos de dominio para o modulo de clientes.

Concentra regras reutilizaveis por views/forms para manter a UI
desacoplada de chamadas diretas ao core.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Tuple, cast

from src.adapters.storage.api import (
    delete_file as storage_delete_file,
    list_files as storage_list_files,
    using_storage_backend,
)
from src.adapters.storage.supabase_storage import SupabaseStorageAdapter
from src.infra.db_schemas import MEMBERSHIPS_SELECT_ORG_ID
from src.infra.supabase_client import exec_postgrest, supabase
from src.core.cnpj_norm import normalize_cnpj as normalize_cnpj_norm
from src.core.db_manager import (
    find_cliente_by_cnpj_norm,
    get_cliente_by_id as core_get_cliente_by_id,
    list_clientes_deletados as _list_clientes_deletados_core,
    update_status_only as _update_status_only,
)
from src.core.services import clientes_service as _legacy_clientes_service
from src.core.session.session import get_current_user as _get_current_user
from ..core.constants import STATUS_PREFIX_RE

RowData = Tuple[Any, ...]
FormValues = Mapping[str, Any]

__all__ = [
    "ClienteCNPJDuplicadoError",
    "ClienteStorageRemovalError",
    "checar_duplicatas_para_form",
    "extrair_dados_cartao_cnpj_em_pasta",
    "mover_cliente_para_lixeira",
    "restaurar_clientes_da_lixeira",
    "excluir_clientes_definitivamente",
    "listar_clientes_na_lixeira",
    "excluir_cliente_simples",
    "get_cliente_by_id",
    "fetch_cliente_by_id",
    "update_cliente_status_and_observacoes",
    "salvar_cliente_a_partir_do_form",
]

count_clients = _legacy_clientes_service.count_clients
checar_duplicatas_info = _legacy_clientes_service.checar_duplicatas_info
salvar_cliente = _legacy_clientes_service.salvar_cliente

log = logging.getLogger(__name__)


class ClienteServiceError(Exception):
    """Erro base para servicos do dominio de clientes."""


class ClienteCNPJDuplicadoError(ClienteServiceError):
    """Indica que o CNPJ informado ja existe para outro cliente."""

    def __init__(self, cliente: Any) -> None:
        self.cliente = cliente
        super().__init__(
            f"CNPJ duplicado para ID {getattr(cliente, 'id', '?')} - {getattr(cliente, 'razao_social', '') or '-'}"
        )


class ClienteStorageRemovalError(ClienteServiceError):
    """Falha ao remover arquivos do storage; exclusao do cliente abortada."""


def _current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_user_label() -> str:
    """Retorna e-mail (ou identificador) do usuário autenticado atual.

    Usado para preencher app-side o campo 'ultima_por' (texto) em operacoes
    de lixeira/restauracao.  As colunas UUID de auditoria (updated_by,
    deleted_by, restored_by) SAO preenchidas automaticamente pelo trigger
    DB-side fn_clients_audit_trail() e NAO devem ser gravadas pelo app.
    """
    try:
        cu = _get_current_user()
        return (getattr(cu, "email", "") or "").strip()
    except Exception as exc:
        log.debug(
            "_current_user_label: falha ao obter usuário autenticado; " "campo 'ultima_por' ficará vazio. Detalhe: %s",
            exc,
        )
        return ""


def _extract_cliente_id(row: RowData | None) -> int | None:
    if not row:
        return None
    try:
        return int(row[0])
    except (TypeError, ValueError, IndexError) as exc:
        log.warning(
            "_extract_cliente_id: valor inesperado em row[0]=%r — %s",
            row[0],
            exc,
        )
        return None


def _ensure_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _resolve_current_id(row: RowData | None, exclude_id: int | None) -> int | None:
    return exclude_id if exclude_id is not None else _extract_cliente_id(row)


def _conflict_id(entry: Any) -> int | None:
    if entry is None:
        return None
    if isinstance(entry, Mapping):
        raw = entry.get("id")
    else:
        raw = getattr(entry, "id", None)
    try:
        return int(raw) if raw is not None else None
    except Exception:
        return None


def _filter_self(entries: Iterable[Any], current_id: int | None) -> list[Any]:
    filtered: list[Any] = []
    for entry in entries or []:
        cid = _conflict_id(entry)
        if cid is not None and current_id is not None and cid == current_id:
            continue
        filtered.append(entry)
    return filtered


def _build_conflict_ids(
    cnpj_conflict: Any, razao_conflicts: Iterable[Any], numero_conflicts: Iterable[Any]
) -> dict[str, list[int]]:
    return {
        "cnpj": [cid] if (cid := _conflict_id(cnpj_conflict)) is not None else [],
        "razao": [cid for cid in (_conflict_id(entry) for entry in razao_conflicts) if cid is not None],
        "numero": [cid for cid in (_conflict_id(entry) for entry in numero_conflicts) if cid is not None],
    }


def extrair_dados_cartao_cnpj_em_pasta(base_dir: str) -> dict[str, str | None]:
    """
    Varre a pasta informada em busca de um Cartão CNPJ e retorna os dados estruturados.

    Este service implementa a lógica de negócio (sem UI) para:
    1. Listar e classificar PDFs na pasta
    2. Localizar Cartão CNPJ via tipo "cnpj_card"
    3. Fallback: localizar PDF de cartão manualmente e extrair texto
    4. Extrair campos CNPJ e Razão Social

    Parâmetros:
        base_dir: str - Caminho absoluto da pasta a ser varrida

    Retorna:
        dict com:
            {
                "cnpj": str | None,
                "razao_social": str | None,
            }

    BUG-008: Valida se base_dir existe e é um diretório válido.
    """
    from pathlib import Path
    from src.utils.file_utils import find_cartao_cnpj_pdf, list_and_classify_pdfs
    from src.utils.paths import ensure_str_path
    from src.utils.pdf_reader import read_pdf_text
    from src.utils.text_utils import extract_company_fields

    # BUG-008: Validação de diretório
    base_path = Path(base_dir)
    if not base_path.exists():
        log.warning("extrair_dados_cartao_cnpj_em_pasta: diretório não existe: %s", base_dir)
        return {"cnpj": None, "razao_social": None}

    if not base_path.is_dir():
        log.warning("extrair_dados_cartao_cnpj_em_pasta: caminho não é um diretório: %s", base_dir)
        return {"cnpj": None, "razao_social": None}

    # 1) Primeiro tenta via list_and_classify_pdfs (aceita "cnpj_card" e "cartao_cnpj")
    docs = list_and_classify_pdfs(base_dir)
    cnpj: str | None = None
    razao: str | None = None
    candidate_pdf: str | None = None

    for d in docs:
        # Aceita tanto "type" quanto "kind" para compatibilidade com classificadores
        doc_type = d.get("type") or d.get("kind")
        if doc_type in ("cnpj_card", "cartao_cnpj"):
            # Se já tem meta com cnpj/razao (caso legado), usa direto
            meta = d.get("meta") or {}
            cnpj = meta.get("cnpj")
            razao = meta.get("razao_social")

            # Se achou meta completo, retorna sem ler PDF
            if cnpj and razao:
                break

            # Se não tem meta completo, guarda caminho do PDF candidato
            if not candidate_pdf and d.get("path"):
                candidate_pdf = d.get("path")

    # 2) Se achou candidato mas não tem meta, extrai texto desse PDF primeiro
    if not (cnpj and razao) and candidate_pdf:
        text = read_pdf_text(ensure_str_path(candidate_pdf)) or ""
        if text:
            fields = extract_company_fields(text)
            cnpj = cnpj or fields.get("cnpj")
            razao = razao or fields.get("razao_social")

    # 3) Fallback: se ainda não achou, varre a pasta inteira
    if not (cnpj or razao):
        pdf = find_cartao_cnpj_pdf(base_dir)
        if pdf:
            # Normalize Path to str for read_pdf_text (PEP 519)
            text = read_pdf_text(ensure_str_path(pdf)) or ""
            if text:
                fields = extract_company_fields(text)
                cnpj = fields.get("cnpj")
                razao = fields.get("razao_social")

    log.debug(
        "extrair_dados_cartao_cnpj_em_pasta: base_dir=%s -> cnpj=%s razao=%s",
        base_dir,
        cnpj or "(não encontrado)",
        razao or "(não encontrado)",
    )

    return {"cnpj": cnpj, "razao_social": razao}


def checar_duplicatas_para_form(
    valores: FormValues,
    row: RowData | None = None,
    *,
    exclude_id: int | None = None,
) -> dict[str, Any]:
    """
    Executa a mesma logica de checar_duplicatas_info mas escondendo detalhes do core.
    """

    current_id = _resolve_current_id(row, exclude_id)

    razao_val = valores.get("Razão Social") or valores.get("Razao Social") or valores.get("razao_social") or ""
    info = checar_duplicatas_info(
        cnpj=_ensure_str(valores.get("CNPJ")),
        razao=_ensure_str(razao_val),
        numero=_ensure_str(valores.get("WhatsApp")),
        nome=_ensure_str(valores.get("Nome")),
        exclude_id=current_id,
    )

    cnpj_conflict = info.get("cnpj_conflict")
    if _conflict_id(cnpj_conflict) == current_id:
        cnpj_conflict = None

    # Cast para list porque sabemos que vem do DB/Supabase como array
    razao_conflicts = _filter_self(cast(list, info.get("razao_conflicts") or []), current_id)
    numero_conflicts = _filter_self(cast(list, info.get("numero_conflicts") or []), current_id)

    conflict_ids = _build_conflict_ids(cnpj_conflict, razao_conflicts, numero_conflicts)

    return {
        "cnpj_conflict": cnpj_conflict,
        "razao_conflicts": razao_conflicts,
        "numero_conflicts": numero_conflicts,
        "blocking_fields": {
            "cnpj": bool(cnpj_conflict),
            "razao": bool(razao_conflicts),
        },
        "conflict_ids": conflict_ids,
    }


def salvar_cliente_a_partir_do_form(row: RowData | None, valores: FormValues) -> Tuple[Any, Any]:
    """
    Normaliza dados basicos do formulario e delega para o core persistir o cliente.

    Retorna a mesma tupla entregue por src.core.services.clientes_service.salvar_cliente.
    """

    current_id = _extract_cliente_id(row)
    cnpj_val = valores.get("CNPJ")
    cnpj_src = cnpj_val if isinstance(cnpj_val, str) else ""
    cnpj_norm = normalize_cnpj_norm(cnpj_src)
    if cnpj_norm:
        dup = find_cliente_by_cnpj_norm(cnpj_norm, exclude_id=current_id)
        if dup:
            raise ClienteCNPJDuplicadoError(dup)

    return salvar_cliente(row, dict(valores))


# ---------------------------------------------------------------------------
# Helpers internos para inserção em lote
# ---------------------------------------------------------------------------
_CNPJ_CHECK_BATCH = 150  # Tamanho padrão de cada lote IN(...) para checar duplicatas
_CNPJ_CHECK_MIN = 25  # Tamanho mínimo antes de desistir no fallback


def _is_uri_too_long(exc: BaseException) -> bool:
    """Detecta erro 414 URI Too Long ou mensagem equivalente do PostgREST."""
    msg = str(exc).lower()
    return "uri too long" in msg or "414" in msg or "request-uri too large" in msg


def _fetch_existing_cnpjs(cnpjs: list[str]) -> set[str]:
    """Consulta CNPJs já cadastrados no banco, com fallback para URI Too Long.

    Busca em lotes de ``_CNPJ_CHECK_BATCH``.  Se o PostgREST retornar
    414 (URI Too Long), reduz o lote pela metade e retenta, até um mínimo
    de ``_CNPJ_CHECK_MIN``.
    """
    found: set[str] = set()
    chunk = _CNPJ_CHECK_BATCH

    i = 0
    while i < len(cnpjs):
        batch = cnpjs[i : i + chunk]
        try:
            resp = exec_postgrest(
                supabase.table("clients").select("cnpj_norm").is_("deleted_at", "null").in_("cnpj_norm", batch)
            )
            for row in resp.data or []:
                cn = row.get("cnpj_norm")
                if cn:
                    found.add(cn)
            i += chunk  # avança
        except Exception as exc:
            if _is_uri_too_long(exc) and chunk > _CNPJ_CHECK_MIN:
                new_chunk = max(chunk // 2, _CNPJ_CHECK_MIN)
                log.warning(
                    "salvar_clientes_em_lote: URI Too Long com batch=%d; reduzindo para %d.",
                    chunk,
                    new_chunk,
                )
                chunk = new_chunk
                # NÃO avança i — retenta o mesmo trecho com batch menor
            else:
                log.warning("salvar_clientes_em_lote: falha ao checar CNPJs existentes: %s", exc)
                break  # desiste, prossegue sem filtro completo

    return found


def salvar_clientes_em_lote(
    lista: list[dict[str, Any]],
    *,
    skip_duplicados: bool = True,
    batch_size: int = 200,
    progress_cb: Callable[[int, int], None] | None = None,
) -> tuple[list[int], list[dict[str, Any]]]:
    """Insere múltiplos clientes via batch HTTP (muito mais rápido que um-a-um).

    Fluxo:
      1. Normaliza payloads (CNPJ, telefone)
      2. Remove duplicados internos (mesmo cnpj_norm) se skip_duplicados=True
      3. Consulta CNPJ existentes no banco e filtra conflitos
      4. Insere em lotes via insert_clientes_batch

    Args:
        lista: Lista de dicts com campos do cliente.
               Chaves aceitas: Razão Social/razao_social, CNPJ/cnpj,
               Nome/nome, WhatsApp/whatsapp/numero, Observações/obs.
        skip_duplicados: Se True, pula clientes com CNPJ já no banco ou repetidos na lista.
        batch_size: Tamanho de cada lote HTTP.
        progress_cb: Callback(inseridos_ate_agora, total) para UI progress.

    Returns:
        (ids_inseridos, lista_de_skipped_dicts_com_motivo)
    """
    from src.core.db_manager import insert_clientes_batch
    from src.core.db_manager.db_manager import BatchInsertPartialError
    from src.utils.formatters import format_cnpj
    from src.utils.phone_utils import format_phone_br

    if not lista:
        return [], []

    # 1. Normalizar payloads
    normalized: list[dict[str, Any]] = []
    seen_cnpj: set[str] = set()
    skipped: list[dict[str, Any]] = []

    for item in lista:
        razao = (item.get("Razão Social") or item.get("Razao Social") or item.get("razao_social") or "").strip()
        cnpj_raw = (item.get("CNPJ") or item.get("cnpj") or "").strip()
        nome = (item.get("Nome") or item.get("nome") or "").strip()
        whatsapp_raw = (
            item.get("WhatsApp")
            or item.get("Whatsapp")
            or item.get("whatsapp")
            or item.get("numero")
            or item.get("Telefone")
            or item.get("telefone")
            or ""
        ).strip()
        obs = (item.get("Observações") or item.get("Observacoes") or item.get("obs") or "").strip()

        cnpj_fmt = format_cnpj(cnpj_raw) if cnpj_raw else ""
        cnpj_norm = normalize_cnpj_norm(cnpj_raw)
        numero_fmt = format_phone_br(whatsapp_raw) if whatsapp_raw else whatsapp_raw

        # Validação mínima
        if not (razao or cnpj_raw or nome or whatsapp_raw):
            skipped.append({**item, "_motivo": "Todos os campos vazios"})
            continue

        # Duplicidade interna (mesmo CNPJ na lista)
        if skip_duplicados and cnpj_norm:
            if cnpj_norm in seen_cnpj:
                skipped.append({**item, "_motivo": f"CNPJ duplicado na lista ({cnpj_raw})"})
                continue
            seen_cnpj.add(cnpj_norm)

        normalized.append(
            {
                "razao_social": razao,
                "cnpj": cnpj_fmt or cnpj_raw,
                "cnpj_norm": cnpj_norm,
                "nome": nome,
                "numero": numero_fmt or whatsapp_raw,
                "obs": obs,
            }
        )

    # 2. Consultar CNPJs existentes no banco (um SELECT com IN)
    if skip_duplicados:
        cnpjs_to_check = [c["cnpj_norm"] for c in normalized if c["cnpj_norm"]]
        existing_cnpjs: set[str] = set()
        if cnpjs_to_check:
            existing_cnpjs = _fetch_existing_cnpjs(cnpjs_to_check)

        # Filtrar os que já existem
        filtered: list[dict[str, Any]] = []
        for c in normalized:
            if c["cnpj_norm"] and c["cnpj_norm"] in existing_cnpjs:
                skipped.append({**c, "_motivo": f"CNPJ já cadastrado ({c['cnpj']})"})
                continue
            filtered.append(c)
        normalized = filtered

    if not normalized:
        return [], skipped

    # 3. Inserir em lotes (com progress_cb por batch)
    total_to_insert = len(normalized)
    inserted_ids: list[int] = []
    for i in range(0, total_to_insert, batch_size):
        batch = normalized[i : i + batch_size]
        try:
            batch_ids = insert_clientes_batch(batch, batch_size=batch_size)
            inserted_ids.extend(batch_ids)
        except BatchInsertPartialError as exc:
            # Recuperar IDs parciais inseridos antes da falha
            inserted_ids.extend(exc.inserted_ids)
            log.warning(
                "salvar_clientes_em_lote: falha parcial no lote %d/%d – %d inseridos, erro: %s",
                exc.failed_batch_index + 1,
                exc.total_batches,
                len(exc.inserted_ids),
                exc.original_error,
            )
            # Registrar os restantes como skipped
            remaining = normalized[i + len(exc.inserted_ids) :]
            for r in remaining:
                skipped.append({**r, "_motivo": f"Falha de lote: {exc.original_error}"})
            break
        if progress_cb:
            try:
                progress_cb(len(inserted_ids), len(lista))
            except Exception:  # noqa: BLE001
                pass

    log.info(
        "salvar_clientes_em_lote: %d inseridos, %d pulados (de %d total).",
        len(inserted_ids),
        len(skipped),
        len(lista),
    )
    return inserted_ids, skipped


def mover_cliente_para_lixeira(cliente_id: int) -> None:
    """
    Marca o cliente como deletado (soft delete) atualizando os campos
    deleted_at / ultima_alteracao / ultima_por.

    As colunas UUID de auditoria (deleted_by, updated_by) SAO preenchidas
    automaticamente pelo trigger trg_clients_audit_trail (DB-side).
    """
    deleted_at = _current_utc_iso()
    payload: dict[str, Any] = {
        "deleted_at": deleted_at,
        "ultima_alteracao": deleted_at,
        "ultima_por": _current_user_label(),
    }
    try:
        exec_postgrest(supabase.table("clients").update(payload).eq("id", cliente_id))
    except Exception:
        # Compatibilidade: ambientes antigos sem a coluna ultima_por
        payload.pop("ultima_por", None)
        exec_postgrest(supabase.table("clients").update(payload).eq("id", cliente_id))


def restaurar_clientes_da_lixeira(ids: Iterable[int]) -> None:
    """
    Restaura clientes da lixeira (remove marcacao de deleted_at).

    As colunas UUID de auditoria (restored_by, updated_by) SAO preenchidas
    automaticamente pelo trigger trg_clients_audit_trail (DB-side).
    """
    now = _current_utc_iso()
    payload: dict[str, Any] = {
        "deleted_at": None,
        "ultima_alteracao": now,
        "ultima_por": _current_user_label(),
    }
    ids_list = list(ids)
    if not ids_list:
        return
    try:
        exec_postgrest(supabase.table("clients").update(payload).in_("id", ids_list))
    except Exception:
        # Compatibilidade: ambientes antigos sem a coluna ultima_por
        payload.pop("ultima_por", None)
        exec_postgrest(supabase.table("clients").update(payload).in_("id", ids_list))


def _resolve_current_org_id() -> str:
    try:
        resp = supabase.auth.get_user()
        user = getattr(resp, "user", None) or resp
        uid = getattr(user, "id", None)
        if not uid and isinstance(resp, dict):
            data = resp.get("data") or {}
            u_dict = resp.get("user") or data.get("user") or {}
            uid = u_dict.get("id") or u_dict.get("uid")
        if not uid:
            raise RuntimeError("Usuário não autenticado no Supabase.")
        res = exec_postgrest(
            supabase.table("memberships").select(MEMBERSHIPS_SELECT_ORG_ID).eq("user_id", uid).limit(1)
        )
        _rows: list = res.data if isinstance(getattr(res, "data", None), list) else []
        if not _rows:
            log.debug("_resolve_current_org_id: nenhuma membership para uid=%s", uid)
            raise RuntimeError("Organização não encontrada para o usuário atual.")
        row = _rows[0]
        org_id = row.get("org_id") if isinstance(row, dict) else None
        if not org_id:
            raise RuntimeError("Organização não encontrada para o usuário atual.")
        return str(org_id)
    except Exception as e:
        raise RuntimeError(f"Falha ao resolver organização atual: {e}")


def _gather_paths(bucket: str, root_prefix: str) -> list[str]:
    paths: list[str] = []
    adapter = SupabaseStorageAdapter(bucket=bucket)
    with using_storage_backend(adapter):
        stack = [root_prefix]
        while stack:
            prefix = stack.pop()
            try:
                items = storage_list_files(prefix) or []
            except Exception:
                items = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                name = it.get("name")
                if not name:
                    continue
                meta = it.get("metadata")
                if meta is None:
                    stack.append(f"{prefix}/{name}")
                else:
                    paths.append(f"{prefix}/{name}")
    return paths


def _remove_cliente_storage(bucket: str, org_id: str, cid_int: int) -> None:
    """Remove todos os arquivos do cliente no storage.

    Raises:
        ClienteStorageRemovalError: se qualquer arquivo nao puder ser removido
            ou se ocorrer erro ao listar/acessar o storage.  Nao silencia falhas;
            o chamador e responsavel por decidir se aborta a delecao no banco.
    """
    prefix = f"{org_id}/{cid_int}"
    try:
        paths = _gather_paths(bucket, prefix)
        failed: list[str] = []
        removed = 0
        for key in paths:
            try:
                if storage_delete_file(key):
                    removed += 1
                else:
                    failed.append(key)
            except Exception as e:
                failed.append(f"{key}: {e}")
        if removed:
            log.info("Storage: removidos %s objeto(s) de %s", removed, prefix)
        if failed:
            raise ClienteStorageRemovalError(
                f"Falha ao remover {len(failed)} arquivo(s) do storage para cliente {cid_int}: {failed}"
            )
    except ClienteStorageRemovalError:
        raise
    except Exception as e:
        raise ClienteStorageRemovalError(f"Erro ao acessar storage para cliente {cid_int}: {e}") from e


def excluir_clientes_definitivamente(
    ids: Iterable[int],
    progress_cb: Callable[[int, int, int], None] | None = None,
) -> tuple[int, list[tuple[int, str]]]:
    """
    Exclui definitivamente clientes do banco e limpa arquivos no Storage.

    Retorna (qtd_ok, erros_por_id).
    """

    ids_list = [int(i) for i in ids]
    if not ids_list:
        return 0, []

    try:
        org_id = _resolve_current_org_id()
    except Exception as exc:
        return 0, [(0, str(exc))]

    ok = 0
    errs: list[tuple[int, str]] = []
    bucket = "rc-docs"

    adapter = SupabaseStorageAdapter(bucket=bucket)
    with using_storage_backend(adapter):
        total = len(ids_list)
        for idx, cid in enumerate(ids_list, start=1):
            cid_int = int(cid)

            # --- 1) Remover storage PRIMEIRO; abortar banco se falhar ---
            try:
                _remove_cliente_storage(bucket, org_id, cid_int)
            except ClienteStorageRemovalError as exc:
                msg = f"Falha ao remover arquivos do storage; exclusao cancelada. ({exc})"
                log.error("[excluir_clientes_definitivamente] cliente=%s: %s", cid_int, msg)
                errs.append((cid_int, msg))
                if progress_cb is not None:
                    try:
                        progress_cb(idx, total, cid_int)
                    except Exception:
                        log.exception("Erro no callback de progresso em excluir_clientes_definitivamente")
                continue  # NAO remove do banco — evita arquivo orfao

            # --- 2) Storage ok: remover do banco ---
            try:
                exec_postgrest(supabase.table("clients").delete().eq("id", cid_int))
                ok += 1
            except Exception as e:
                errs.append((cid_int, str(e)))

            if progress_cb is not None:
                try:
                    progress_cb(idx, total, cid_int)
                except Exception:
                    log.exception("Erro no callback de progresso em excluir_clientes_definitivamente")

    return ok, errs


def excluir_cliente_simples(cliente_id: int) -> None:
    """
    Exclui fisicamente um cliente (sem passar pela lixeira e sem limpar storage).
    Uso restrito: rollback de criacao cancelada antes de upload.
    """

    exec_postgrest(supabase.table("clients").delete().eq("id", int(cliente_id)))


def listar_clientes_na_lixeira(
    *,
    order_by: str | None = "id",
    descending: bool | None = True,
) -> list[Any]:
    """
    Retorna lista simplificada de clientes marcados como deletados (para exibicao na Lixeira).
    """

    try:
        return _list_clientes_deletados_core(order_by=order_by, descending=descending, limit=None) or []
    except Exception:
        # fallback direto ao Supabase para manter compatibilidade se o core mudar
        col = order_by or "id"
        desc = True if descending is None else bool(descending)
        query = (
            supabase.table("clients")
            .select("id,razao_social,cnpj,nome,numero,obs,ultima_alteracao,ultima_por")
            .not_.is_("deleted_at", "null")
            .order(col, desc=desc)
        )
        resp = exec_postgrest(query)
        data = getattr(resp, "data", None)
        if data is None and isinstance(resp, dict):
            data = resp.get("data")
        return data or []


def get_cliente_by_id(cliente_id: int) -> Any:
    """
    Wrapper simples para o core, para evitar importacoes diretas na UI.
    Retorna Cliente (objeto do core) ou None.
    """
    return core_get_cliente_by_id(cliente_id)


def fetch_cliente_by_id(cliente_id: int) -> dict[str, Any] | None:
    """
    Versao que sempre devolve dict, para uso em views (sem objetos ORM).
    """
    out = get_cliente_by_id(cliente_id)
    if out is None:
        return None
    if isinstance(out, dict):
        return out
    # fallback generico: tenta mapear atributos conhecidos
    return {
        "id": getattr(out, "id", None),
        "razao_social": getattr(out, "razao_social", None),
        "cnpj": getattr(out, "cnpj", None),
        "cnpj_norm": getattr(out, "cnpj_norm", None),
        "numero": getattr(out, "numero", None),
        # FIX: campo 'nome' (nome usado no dia-a-dia) estava ausente no fallback
        "nome": getattr(out, "nome", None) or getattr(out, "contato", None),
        "observacoes": getattr(out, "observacoes", None) or getattr(out, "obs", None),
        "obs": getattr(out, "obs", None) or getattr(out, "observacoes", None),
        "ultima_alteracao": getattr(out, "ultima_alteracao", None),
        "ultima_por": getattr(out, "ultima_por", None),
        "created_at": getattr(out, "created_at", None),
        "status_anvisa": getattr(out, "status_anvisa", None),
        "status_farmacia_popular": getattr(out, "status_farmacia_popular", None),
        # Campos de endereço (podem existir no modelo)
        "endereco": getattr(out, "endereco", None),
        "bairro": getattr(out, "bairro", None),
        "cidade": getattr(out, "cidade", None),
        "cep": getattr(out, "cep", None),
    }


def update_cliente_status_and_observacoes(cliente: Mapping[str, Any] | int, novo_status: str | None) -> None:
    """
    Atualiza apenas o campo 'observacoes' com o prefixo de status, preservando o restante do texto.
    """

    if isinstance(cliente, int):
        cliente_id = cliente
        cli_dict = fetch_cliente_by_id(cliente_id) or {}
    else:
        raw_id = getattr(cliente, "id", None) or cliente.get("id")
        if raw_id is None:
            raise ValueError("Cliente deve ter um campo 'id' válido")
        cliente_id = int(raw_id)
        cli_dict = dict(cliente)

    raw_obs = (
        cli_dict.get("observacoes")
        or cli_dict.get("obs")
        or getattr(cliente, "observacoes", None)
        or getattr(cliente, "obs", None)
        or getattr(cliente, "Observacoes", None)
        or ""
    )
    body = STATUS_PREFIX_RE.sub("", raw_obs, count=1).strip()
    new_obs = f"[{novo_status}] {body}".strip() if novo_status else body

    # Delega para o core (update_status_only já trata coluna 'obs' + fallback ultima_por)
    _update_status_only(cliente_id, new_obs)
