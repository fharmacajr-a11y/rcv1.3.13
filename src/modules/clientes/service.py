"""Servicos de dominio para o modulo de clientes.

Concentra regras reutilizaveis por views/forms para manter a UI
desacoplada de chamadas diretas ao core.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Optional, Tuple, cast

from adapters.storage.api import (
    delete_file as storage_delete_file,
    list_files as storage_list_files,
    using_storage_backend,
)
from adapters.storage.supabase_storage import SupabaseStorageAdapter
from infra.supabase_client import exec_postgrest, supabase
from src.core.cnpj_norm import normalize_cnpj as normalize_cnpj_norm
from src.core.db_manager import (
    find_cliente_by_cnpj_norm,
    get_cliente_by_id as core_get_cliente_by_id,
    list_clientes_deletados as _list_clientes_deletados_core,
)
from src.core.services import clientes_service as _legacy_clientes_service
from src.modules.clientes.components.helpers import STATUS_PREFIX_RE

RowData = Tuple[Any, ...]
FormValues = Mapping[str, Any]

__all__ = [
    "ClienteCNPJDuplicadoError",
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
        super().__init__(f"CNPJ duplicado para ID {getattr(cliente, 'id', '?')} " f"- {getattr(cliente, 'razao_social', '') or '-'}")


def _current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_cliente_id(row: RowData | None) -> Optional[int]:
    try:
        return int(row[0]) if row else None
    except Exception:
        return None


def extrair_dados_cartao_cnpj_em_pasta(base_dir: str) -> dict[str, Optional[str]]:
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
    """
    from src.utils.file_utils import find_cartao_cnpj_pdf, list_and_classify_pdfs
    from src.utils.paths import ensure_str_path
    from src.utils.pdf_reader import read_pdf_text
    from src.utils.text_utils import extract_company_fields

    # 1) Primeiro tenta via list_and_classify_pdfs (type == "cnpj_card")
    docs = list_and_classify_pdfs(base_dir)
    cnpj: Optional[str] = None
    razao: Optional[str] = None

    for d in docs:
        if d.get("type") == "cnpj_card":
            meta = d.get("meta") or {}
            cnpj = meta.get("cnpj")
            razao = meta.get("razao_social")
            break

    # 2) Fallback: se não achou, tenta localizar um PDF de cartão de CNPJ e extrair texto
    if not (cnpj or razao):
        pdf = find_cartao_cnpj_pdf(base_dir)
        if pdf:
            # Normalize Path to str for read_pdf_text (PEP 519)
            text = read_pdf_text(ensure_str_path(pdf)) or ""
            if text:
                fields = extract_company_fields(text)
                cnpj = fields.get("cnpj")
                razao = fields.get("razao_social")

    log.debug("extrair_dados_cartao_cnpj_em_pasta: base_dir=%s -> cnpj=%s razao=%s", base_dir, cnpj or "(não encontrado)", razao or "(não encontrado)")

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

    current_id = exclude_id if exclude_id is not None else _extract_cliente_id(row)

    def _ensure_str(value: Any) -> str:
        return value if isinstance(value, str) else ""

    razao_val = valores.get("Raz?o Social") or valores.get("Razao Social") or ""
    info = checar_duplicatas_info(
        cnpj=_ensure_str(valores.get("CNPJ")),
        razao=_ensure_str(razao_val),
        numero=_ensure_str(valores.get("WhatsApp")),
        nome=_ensure_str(valores.get("Nome")),
        exclude_id=current_id,
    )

    def _conflict_id(entry: Any) -> Optional[int]:
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

    def _filter_self(entries: Iterable[Any]) -> list[Any]:
        filtered: list[Any] = []
        for entry in entries or []:
            cid = _conflict_id(entry)
            if cid is not None and current_id is not None and cid == current_id:
                continue
            filtered.append(entry)
        return filtered

    cnpj_conflict = info.get("cnpj_conflict")
    if _conflict_id(cnpj_conflict) == current_id:
        cnpj_conflict = None

    # Cast para list porque sabemos que vem do DB/Supabase como array
    razao_conflicts = _filter_self(cast(list, info.get("razao_conflicts") or []))
    numero_conflicts = _filter_self(cast(list, info.get("numero_conflicts") or []))

    conflict_ids = {
        "cnpj": [cid] if (cid := _conflict_id(cnpj_conflict)) is not None else [],
        "razao": [cid for cid in (_conflict_id(entry) for entry in razao_conflicts) if cid is not None],
        "numero": [cid for cid in (_conflict_id(entry) for entry in numero_conflicts) if cid is not None],
    }

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


def mover_cliente_para_lixeira(cliente_id: int) -> None:
    """
    Marca o cliente como deletado (soft delete) atualizando os campos deleted_at/ultima_alteracao.
    """

    deleted_at = _current_utc_iso()
    payload = {"deleted_at": deleted_at, "ultima_alteracao": deleted_at}
    exec_postgrest(supabase.table("clients").update(payload).eq("id", cliente_id))


def restaurar_clientes_da_lixeira(ids: Iterable[int]) -> None:
    """
    Restaura clientes da lixeira (remove marcacao de deleted_at).
    """

    now = _current_utc_iso()
    payload = {"deleted_at": None, "ultima_alteracao": now}
    ids_list = list(ids)
    if not ids_list:
        return

    exec_postgrest(supabase.table("clients").update(payload).in_("id", ids_list))


def excluir_clientes_definitivamente(
    ids: Iterable[int],
    progress_cb: Optional[Callable[[int, int, int], None]] = None,
) -> tuple[int, list[tuple[int, str]]]:
    """
    Exclui definitivamente clientes do banco e limpa arquivos no Storage.

    Retorna (qtd_ok, erros_por_id).
    """

    def _current_org_id() -> str:
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
            res = exec_postgrest(supabase.table("memberships").select("org_id").eq("user_id", uid).limit(1))
            org_id = res.data[0]["org_id"] if getattr(res, "data", None) else None
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

    ids_list = [int(i) for i in ids]
    if not ids_list:
        return 0, []

    try:
        org_id = _current_org_id()
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
            prefix = f"{org_id}/{cid_int}"
            try:
                paths = _gather_paths(bucket, prefix)
                removed = 0
                for key in paths:
                    try:
                        if storage_delete_file(key):
                            removed += 1
                    except Exception as e:
                        errs.append((cid_int, f"Storage: {e}"))
                if removed:
                    log.info("Storage: removidos %s objeto(s) de %s", removed, prefix)
            except Exception as e:
                errs.append((cid_int, f"Storage: {e}"))

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
        return _list_clientes_deletados_core(order_by=order_by, descending=descending) or []
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


def fetch_cliente_by_id(cliente_id: int) -> Optional[dict[str, Any]]:
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
        "numero": getattr(out, "numero", None),
        "observacoes": getattr(out, "observacoes", None),
    }


def update_cliente_status_and_observacoes(cliente: Mapping[str, Any] | int, novo_status: Optional[str]) -> None:
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

    raw_obs = cli_dict.get("observacoes") or getattr(cliente, "observacoes", None) or getattr(cliente, "Observacoes", None) or ""
    body = STATUS_PREFIX_RE.sub("", raw_obs, count=1).strip()
    new_obs = f"[{novo_status}] {body}".strip() if novo_status else body

    exec_postgrest(supabase.table("clients").update({"observacoes": new_obs}).eq("id", cliente_id))
