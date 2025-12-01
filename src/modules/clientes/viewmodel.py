from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import os
from typing import Any, Callable, Collection, Dict, Iterable, List, Optional, Tuple

from src.core.search import search_clientes
from src.core.textnorm import join_and_normalize, normalize_search
from src.utils.phone_utils import normalize_br_whatsapp

from .components import helpers as status_helpers

logger = logging.getLogger(__name__)


class ClientesViewModelError(Exception):
    """Erro base para o viewmodel de clientes."""


@dataclass
class ClienteRow:
    """Representa um cliente normalizado para exibição."""

    id: str
    razao_social: str
    cnpj: str
    nome: str
    whatsapp: str
    observacoes: str
    status: str
    ultima_alteracao: str
    search_norm: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


class ClientesViewModel:
    """
    Centraliza carregamento, filtros e ordenação da lista de clientes.
    Mantém cache local e expõe linhas prontas para a Treeview.
    """

    def __init__(
        self,
        *,
        order_choices: Optional[Dict[str, Tuple[Optional[str], bool]]] = None,
        default_order_label: str = "",
        author_resolver: Optional[Callable[[str], str]] = None,
    ) -> None:
        self._order_choices = order_choices or {}
        self._order_label = default_order_label or ""
        self._clientes_raw: List[Any] = []
        self._rows: List[ClienteRow] = []
        self._status_choices: List[str] = []
        self._search_text_raw: str = ""
        self._search_text_norm: str = ""
        self._status_filter: Optional[str] = None
        self._status_filter_norm: Optional[str] = None
        self._author_resolver = author_resolver

    # ------------------------------------------------------------------ #
    # Carregamento de dados
    # ------------------------------------------------------------------ #

    def refresh_from_service(self) -> None:
        """Carrega clientes via search_clientes e reconstrói o cache."""
        column, reverse_after = self._resolve_order_preferences()
        try:
            clientes = search_clientes(self._search_text_raw, column)
        except Exception as exc:  # pragma: no cover - erros propagados
            raise ClientesViewModelError(str(exc)) from exc

        if reverse_after:
            clientes = list(reversed(clientes))

        self._clientes_raw = list(clientes)
        self._rebuild_rows()

    def load_from_iterable(self, clientes: Iterable[Any]) -> None:
        """Utilitário para testes: injeta dados fake."""
        self._clientes_raw = list(clientes)
        self._rebuild_rows()

    # ------------------------------------------------------------------ #
    # Filtros públicos
    # ------------------------------------------------------------------ #

    def set_search_text(self, text: str, *, rebuild: bool = True) -> None:
        self._search_text_raw = (text or "").strip()
        self._search_text_norm = normalize_search(text or "")
        if rebuild:
            self._rebuild_rows()

    def set_status_filter(self, status: Optional[str], *, rebuild: bool = True) -> None:
        raw = (status or "").strip()
        self._status_filter = raw or None
        self._status_filter_norm = raw.lower() or None
        if rebuild:
            self._rebuild_rows()

    def set_order_label(self, label: str, *, rebuild: bool = True) -> None:
        if label:
            self._order_label = label
        if rebuild:
            self._rebuild_rows()

    # ------------------------------------------------------------------ #
    # STATUS em Observações
    # ------------------------------------------------------------------ #

    def extract_status_and_observacoes(self, observacoes: str) -> tuple[str, str]:
        text = observacoes or ""
        match = status_helpers.STATUS_PREFIX_RE.match(text)
        if not match:
            return ("", text.strip())
        status = (match.group("st") or "").strip()
        cleaned = status_helpers.STATUS_PREFIX_RE.sub("", text, count=1).strip()
        return (status, cleaned)

    def apply_status_to_observacoes(self, status: str, texto: str) -> str:
        status_clean = (status or "").strip()
        body = (texto or "").strip()
        if status_clean:
            return f"[{status_clean}] {body}".strip()
        return body

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #

    def get_rows(self) -> List[ClienteRow]:
        return list(self._rows)

    def get_status_choices(self) -> List[str]:
        return list(self._status_choices)

    # ------------------------------------------------------------------ #
    # Operações em batch (Fase 07)
    # ------------------------------------------------------------------ #

    def delete_clientes_batch(self, ids: Collection[str]) -> tuple[int, list[tuple[int, str]]]:
        """Exclui definitivamente uma coleção de clientes.

        Delega para o serviço de clientes, que cuida da lógica de
        exclusão física + limpeza de storage.

        Retorna (qtd_ok, erros_por_id).
        """
        from .service import excluir_clientes_definitivamente

        ids_int = [int(id_str) for id_str in ids]
        return excluir_clientes_definitivamente(ids_int)

    def restore_clientes_batch(self, ids: Collection[str]) -> None:
        """Restaura uma coleção de clientes da lixeira."""
        from .service import restaurar_clientes_da_lixeira

        ids_int = [int(id_str) for id_str in ids]
        restaurar_clientes_da_lixeira(ids_int)

    def export_clientes_batch(self, ids: Collection[str]) -> None:
        """Exporta dados dos clientes selecionados.

        Fase 07: Implementação placeholder - apenas loga os IDs.
        Fase futura pode implementar export real (CSV/Excel).
        """
        logger.info("Export batch solicitado para %d cliente(s): %s", len(ids), ids)
        # TODO: Implementar exportação real (CSV/Excel) em fase futura

    # ------------------------------------------------------------------ #
    # Implementação interna
    # ------------------------------------------------------------------ #

    def _resolve_order_preferences(self) -> tuple[Optional[str], bool]:
        column = None
        reverse = False
        if self._order_label and self._order_label in self._order_choices:
            column, reverse = self._order_choices[self._order_label]
        return column, bool(reverse)

    def _rebuild_rows(self) -> None:
        rows: list[ClienteRow] = []
        statuses: Dict[str, str] = {}
        search_norm = self._search_text_norm
        status_filter = self._status_filter_norm

        for cliente in self._clientes_raw:
            row = self._build_row_from_cliente(cliente)
            status_key = row.status.strip().lower()
            if row.status and status_key not in statuses:
                statuses[status_key] = row.status

            if status_filter and status_key != status_filter:
                continue
            if search_norm and search_norm not in row.search_norm:
                continue
            rows.append(row)

        self._rows = self._sort_rows(rows)
        self._status_choices = sorted(statuses.values(), key=lambda s: s.lower())

    def _sort_rows(self, rows: List[ClienteRow]) -> List[ClienteRow]:
        column, reverse_after = self._resolve_order_preferences()
        if not column or not rows:
            return rows

        def sort_key(key_func: Callable[[ClienteRow], Tuple[bool, Any]]) -> List[ClienteRow]:
            non_empty: list[tuple[Any, ClienteRow]] = []
            empties: list[ClienteRow] = []
            for row in rows:
                is_empty, key = key_func(row)
                if is_empty:
                    empties.append(row)
                else:
                    non_empty.append((key, row))
            non_empty.sort(key=lambda item: item[0], reverse=reverse_after)
            ordered = [row for _, row in non_empty]
            ordered.extend(empties)
            return ordered

        if column == "razao_social":
            return sort_key(lambda row: self._key_nulls_last(row.razao_social, str.casefold))
        if column == "nome":
            return sort_key(lambda row: self._key_nulls_last(row.nome, str.casefold))
        if column == "cnpj":
            return sort_key(lambda row: self._key_nulls_last(self._only_digits(row.cnpj), lambda x: x))
        if column == "id":
            numeric: list[tuple[int, ClienteRow]] = []
            invalid: list[ClienteRow] = []
            for row in rows:
                try:
                    value = int(row.id)
                    numeric.append((value, row))
                except (TypeError, ValueError):
                    invalid.append(row)
            numeric.sort(key=lambda item: item[0], reverse=reverse_after)
            ordered = [row for _, row in numeric]
            ordered.extend(invalid)
            return ordered

        return rows

    @staticmethod
    def _key_nulls_last(value: str | None, transform: Callable[[str], Any]) -> tuple[bool, Any]:
        s = "" if value is None else str(value).strip()
        return (s == "", transform(s))

    @staticmethod
    def _only_digits(value: str) -> str:
        return "".join(ch for ch in str(value) if ch.isdigit())

    def _build_row_from_cliente(self, cliente: Any) -> ClienteRow:
        whatsapp = normalize_br_whatsapp(str(self._value_from_cliente(cliente, "whatsapp", "numero", "telefone") or ""))

        cnpj_raw = str(self._value_from_cliente(cliente, "cnpj") or "")
        cnpj_fmt = cnpj_raw
        try:
            from src.utils.text_utils import format_cnpj

            cnpj_fmt = format_cnpj(cnpj_raw) or cnpj_raw
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao formatar CNPJ no ClientesViewModel: %s", exc)

        updated_raw = self._value_from_cliente(cliente, "ultima_alteracao", "updated_at")
        updated_fmt = ""
        if updated_raw:
            try:
                from src.app_utils import fmt_data

                updated_fmt = fmt_data(updated_raw)
            except Exception:
                updated_fmt = str(updated_raw)

        by = str(self._value_from_cliente(cliente, "ultima_por") or "").strip()
        initial = ""
        if by:
            aliases_raw = os.getenv("RC_INITIALS_MAP", "")
            alias = ""
            try:
                mapping = json.loads(aliases_raw) if aliases_raw else {}
            except Exception:
                mapping = {}
            if isinstance(mapping, dict):
                alias = str(mapping.get(by, "") or "")
            if alias:
                initial = (alias[:1] or "").upper()
            elif self._author_resolver:
                try:
                    initial = (self._author_resolver(by) or "").strip()
                except Exception:
                    initial = ""
                if not initial:
                    initial = (by[:1] or "").upper()
            else:
                initial = (by[:1] or "").upper()

        if updated_fmt and initial:
            updated_fmt = f"{updated_fmt} ({initial[:1]})"

        razao = self._value_from_cliente(cliente, "razao_social", "razao")
        nome = self._value_from_cliente(cliente, "nome", "contato")

        obs_raw = str(self._value_from_cliente(cliente, "observacoes", "obs") or "")
        status, obs_body = self.extract_status_and_observacoes(obs_raw)

        row = ClienteRow(
            id=str(self._value_from_cliente(cliente, "id", "pk", "client_id") or ""),
            razao_social=str(razao or ""),
            cnpj=cnpj_fmt,
            nome=str(nome or ""),
            whatsapp=whatsapp["display"],
            observacoes=obs_body,
            status=status,
            ultima_alteracao=updated_fmt,
            raw={"cliente": cliente},
        )
        row.search_norm = join_and_normalize(
            row.id,
            row.razao_social,
            row.cnpj,
            row.nome,
            row.whatsapp,
            row.observacoes,
            row.status,
        )
        return row

    @staticmethod
    def _value_from_cliente(cliente: Any, *names: str) -> Any:
        for name in names:
            value = getattr(cliente, name, None)
            if value not in (None, ""):
                return value
            if isinstance(cliente, dict):
                value = cliente.get(name)
                if value not in (None, ""):
                    return value
        return ""
