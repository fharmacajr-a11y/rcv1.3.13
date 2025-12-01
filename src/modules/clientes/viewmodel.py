from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import os
from typing import Any, Callable, Collection, Dict, Iterable, List, Optional

from src.core.search import search_clientes
from src.core.textnorm import join_and_normalize
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
    """Carrega dados de clientes do backend e mantém _clientes_raw.

    Responsabilidades:
    - Carregar dados brutos do backend via search_clientes
    - Converter dados para ClienteRow
    - Fornecer lista de status únicos
    - Operações em batch (exclusão, restauração, exportação)

    Filtros, ordenação e seleção da tela principal são responsabilidade
    do main_screen_controller (headless), não deste ViewModel.
    """

    def __init__(
        self,
        *,
        author_resolver: Optional[Callable[[str], str]] = None,
    ) -> None:
        self._clientes_raw: List[Any] = []
        self._status_choices: List[str] = []
        self._author_resolver = author_resolver

    # ------------------------------------------------------------------ #
    # Carregamento de dados
    # ------------------------------------------------------------------ #

    def refresh_from_service(self) -> None:
        """Carrega clientes via search_clientes sem aplicar filtros/ordenação.
        
        MS-4: Simplificado para ser apenas um loader de dados brutos.
        Filtros e ordenação são responsabilidade do controller headless.
        """
        try:
            # Carregar todos os clientes sem filtro de busca
            clientes = search_clientes("", None)
        except Exception as exc:  # pragma: no cover - erros propagados
            raise ClientesViewModelError(str(exc)) from exc

        self._clientes_raw = list(clientes)
        self._update_status_choices()

    def load_from_iterable(self, clientes: Iterable[Any]) -> None:
        """Utilitário para testes: injeta dados fake."""
        self._clientes_raw = list(clientes)
        self._update_status_choices()

    def _update_status_choices(self) -> None:
        """Extrai opções únicas de status dos clientes carregados."""
        statuses: Dict[str, str] = {}
        
        for cliente in self._clientes_raw:
            row = self._build_row_from_cliente(cliente)
            status_key = row.status.strip().lower()
            if row.status and status_key not in statuses:
                statuses[status_key] = row.status
        
        self._status_choices = sorted(statuses.values(), key=lambda s: s.lower())

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

    def get_status_choices(self) -> List[str]:
        """Retorna lista de status únicos disponíveis nos clientes carregados."""
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
    # Construção de ClienteRow
    # ------------------------------------------------------------------ #

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
