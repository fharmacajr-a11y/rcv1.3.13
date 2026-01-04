"""Lightweight controller/viewmodel for the Auditoria screen."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, TypedDict

from src.utils.formatters import format_cnpj, fmt_datetime_br

from . import service as auditoria_service

DEFAULT_AUDITORIA_STATUS = "em_andamento"
STATUS_LABELS = {
    "em_andamento": "Em andamento",
    "pendente": "Pendente",
    "finalizado": "Finalizado",
    "cancelado": "Cancelado",
}
STATUS_ALIASES = {"em_processo": DEFAULT_AUDITORIA_STATUS}


def canonical_status(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return DEFAULT_AUDITORIA_STATUS
    normalized = raw.lower().replace(" ", "_")
    return STATUS_ALIASES.get(normalized, normalized)


def status_to_label(value: str | None) -> str:
    canon = canonical_status(value)
    label = STATUS_LABELS.get(canon)
    if label:
        return label
    safe = canon.replace("_", " ").strip()
    return safe.capitalize() if safe else ""


@dataclass
class AuditoriaRow:
    iid: str
    db_id: str
    cliente_id: Optional[int]
    cliente_display: str
    cliente_nome: str
    cliente_cnpj: str
    status: str
    status_display: str
    created_at: str
    created_at_iso: str | None
    updated_at: str
    updated_at_iso: str | None
    raw: dict[str, Any] = field(default_factory=dict)


class AuditoriaViewModel:
    """Encapsulates caching, filtering and list building for the Auditoria UI."""

    def __init__(self) -> None:
        self._clientes: list[dict[str, Any]] = []
        self._auditorias: list[dict[str, Any]] = []
        self._cliente_display_map: dict[str, str] = {}
        self._clientes_rows_map: dict[str, dict[str, Any]] = {}
        self._aud_index: dict[str, AuditoriaRow] = {}
        self._filtered_clientes: list[dict[str, Any]] = []

        self._search_text: str = ""
        self._selected_cliente_id: Optional[int] = None

    # --- Data loading -------------------------------------------------
    def refresh_clientes(self, *, fetcher: Callable[[], Iterable[dict[str, Any]]] | None = None) -> None:
        fetch_func = fetcher or auditoria_service.fetch_clients
        rows = fetch_func()
        self._clientes = [row for row in rows if isinstance(row, dict)]
        self._cliente_display_map.clear()
        self._clientes_rows_map.clear()
        for row in self._clientes:
            raw_id = row.get("id")
            ident_int = _safe_int(raw_id)
            razao = _cliente_razao_from_row(row)
            cnpj_raw = _cliente_cnpj_from_row(row)
            ident = ident_int if ident_int is not None else raw_id
            display = _cliente_display_id_first(ident, razao, cnpj_raw)
            if raw_id is not None:
                key = str(raw_id)
                self._cliente_display_map[key] = display
                self._clientes_rows_map[key] = row
            if ident_int is not None:
                key_int = str(ident_int)
                self._cliente_display_map[key_int] = display
                self._clientes_rows_map[key_int] = row
        self._apply_client_filter()

    def refresh_auditorias(
        self, *, fetcher: Callable[[], Iterable[dict[str, Any]]] | None = None
    ) -> list[AuditoriaRow]:
        fetch_func = fetcher or auditoria_service.fetch_auditorias
        rows = fetch_func()
        self._auditorias = [row for row in rows if isinstance(row, dict)]
        return self._build_aud_rows()

    # --- Filtering ----------------------------------------------------
    def set_search_text(self, text: str | None) -> None:
        self._search_text = text or ""
        self._apply_client_filter()

    def set_selected_cliente_id(self, cliente_id: Optional[int]) -> None:
        self._selected_cliente_id = cliente_id

    def get_filtered_clientes(self) -> list[dict[str, Any]]:
        return list(self._filtered_clientes)

    def get_cliente_display_map(self) -> dict[str, str]:
        return dict(self._cliente_display_map)

    # --- Tree rows ----------------------------------------------------
    def get_auditoria_rows(self) -> list[AuditoriaRow]:
        if not self._aud_index:
            self._build_aud_rows()
        return list(self._aud_index.values())

    def get_row(self, iid: str) -> Optional[AuditoriaRow]:
        return self._aud_index.get(iid)

    # --- Internals ----------------------------------------------------
    def _apply_client_filter(self) -> None:
        q_text = _norm_text(self._search_text)
        q_digits = _digits(self._search_text)
        if not q_text and not q_digits:
            self._filtered_clientes = list(self._clientes)
            return

        filtrados: list[dict[str, Any]] = []
        for cli in self._clientes:
            idx = _build_search_index(cli)
            if len(q_digits) >= 5 and q_digits in idx["cnpj"]:
                filtrados.append(cli)
                continue
            if q_text and (q_text in idx["razao"] or any(q_text in nome for nome in idx["nomes"])):
                filtrados.append(cli)
        self._filtered_clientes = filtrados

    def _build_aud_rows(self) -> list[AuditoriaRow]:
        self._aud_index.clear()
        result: list[AuditoriaRow] = []
        for r in self._auditorias:
            aud_id = r.get("id")
            if aud_id is None:
                continue
            iid = str(aud_id)
            raw_cliente_id = r.get("cliente_id")
            cliente_row = self._resolve_cliente_row(raw_cliente_id)
            cliente_id_int = _safe_int(raw_cliente_id)
            razao = _cliente_razao_from_row(cliente_row) or _cliente_razao_from_row(r)
            cnpj_raw = _cliente_cnpj_from_row(cliente_row)
            cliente_ident = cliente_id_int if cliente_id_int is not None else raw_cliente_id
            cliente_txt = _cliente_display_id_first(cliente_ident, razao, cnpj_raw)
            if not cliente_txt and raw_cliente_id is not None:
                cliente_txt = self._cliente_display_map.get(str(raw_cliente_id), "")
            status_raw = r.get("status") or DEFAULT_AUDITORIA_STATUS
            status_db = canonical_status(status_raw)
            status_display = status_to_label(status_db)
            created_iso = r.get("created_at") or r.get("criado")
            updated_iso = r.get("updated_at") or r.get("atualizado")
            created_br = fmt_datetime_br(created_iso)
            updated_br = fmt_datetime_br(updated_iso)
            cliente_cnpj_fmt = format_cnpj(cnpj_raw)
            row = AuditoriaRow(
                iid=iid,
                db_id=str(aud_id),
                cliente_id=cliente_id_int,
                cliente_display=cliente_txt,
                cliente_nome=razao or cliente_txt,
                cliente_cnpj=cliente_cnpj_fmt,
                status=status_db,
                status_display=status_display,
                created_at=created_br,
                created_at_iso=created_iso,
                updated_at=updated_br,
                updated_at_iso=updated_iso,
                raw=r,
            )
            self._aud_index[iid] = row
            result.append(row)
        return result

    def _resolve_cliente_row(self, raw_cliente_id: Any) -> Optional[dict[str, Any]]:
        if raw_cliente_id in (None, ""):
            return None
        key = str(raw_cliente_id)
        row = self._clientes_rows_map.get(key)
        if row is not None:
            return row
        as_int = _safe_int(raw_cliente_id)
        if as_int is not None:
            return self._clientes_rows_map.get(str(as_int))
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        return None


def _cliente_razao_from_row(row: Any) -> str:
    if not isinstance(row, dict):
        return ""
    return (
        row.get("display_name")
        or row.get("razao_social")
        or row.get("Razao Social")
        or row.get("legal_name")
        or row.get("name")
        or ""
    ).strip()


def _cliente_cnpj_from_row(row: Any) -> str:
    if not isinstance(row, dict):
        return ""
    return (row.get("cnpj") or row.get("tax_id") or "").strip()


def _cliente_display_id_first(cliente_id, razao, cnpj) -> str:
    parts: list[str] = []
    if cliente_id not in (None, "", 0):
        parts.append(f"ID {cliente_id}")
    if razao:
        parts.append(str(razao).strip())
    c = format_cnpj(cnpj or "")
    if c:
        parts.append(c)
    return " — ".join(parts)


def _norm_text(s: str | None) -> str:
    import unicodedata

    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.casefold().strip()


def _digits(value: str | None) -> str:
    return "".join(filter(str.isdigit, value or ""))


class ClienteSearchIndex(TypedDict):
    razao: str
    nomes: list[str]
    cnpj: str


def _build_search_index(cliente: dict[str, Any]) -> ClienteSearchIndex:
    nomes: list[str] = []
    for key in ("contact_name", "responsavel", "representante", "responsible_name"):
        raw = cliente.get(key)
        if raw:
            nomes.append(_norm_text(str(raw)))
    return {
        "razao": _norm_text(_cliente_razao_from_row(cliente)),
        "nomes": nomes,
        "cnpj": _digits(_cliente_cnpj_from_row(cliente)),
    }
