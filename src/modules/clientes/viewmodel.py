from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import json
import logging
import os
from typing import TYPE_CHECKING, Any, Collection, Dict, Iterable, List

if TYPE_CHECKING:
    pass  # Imports apenas para type checking, se necessário

from src.core.search import search_clientes
from src.core.string_utils import only_digits
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
    ultima_alteracao_ts: Any = None  # Timestamp para ordenação (datetime ou None)


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
        order_choices: dict[str, tuple[str | None, bool]] | None = None,
        default_order_label: str | None = None,
        author_resolver: Callable[[str], str] | None = None,
    ) -> None:
        """Inicializa o ViewModel de clientes.

        Args:
            order_choices: Dicionário de opções de ordenação (chave=label, valor=(campo, reverse)).
                          Se None, não afeta o comportamento (ordenação é responsabilidade do controller).
            default_order_label: Label padrão de ordenação. Se None, usa o primeiro de order_choices se disponível.
            author_resolver: Função opcional para resolver iniciais de autor a partir de email/nome.
                            Se None, usa lógica padrão (primeira letra do email).
        """
        self._clientes_raw: List[Any] = []
        self._status_choices: List[str] = []

        # Armazenar parâmetros de ordenação (para compatibilidade com Main Screen)
        # Nota: A ordenação real é feita pelo controller, não pelo ViewModel.
        # Estes parâmetros são armazenados para possível uso futuro ou para manter
        # compatibilidade com a interface esperada pela Main Screen.
        self._order_choices: dict[str, tuple[str | None, bool]] = order_choices or {}

        # Determinar label padrão de ordenação
        if default_order_label:
            self._default_order_label: str = default_order_label
        elif self._order_choices:
            self._default_order_label = next(iter(self._order_choices.keys()))
        else:
            self._default_order_label = ""

        # Resolver de autor (usado na formatação de ClienteRow)
        self._author_resolver = author_resolver

        # Estado de filtros e ordenação (Round 15)
        self._search_text_raw: str | None = None
        self._status_filter: str | None = None
        self._current_order_label: str = self._default_order_label

        # Cache de rows processadas (após filtros e ordenação)
        self._rows: List[ClienteRow] = []

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
        self._rebuild_rows()

    def load_from_iterable(self, clientes: Iterable[Any]) -> None:
        """Utilitário para testes: injeta dados fake."""
        self._clientes_raw = list(clientes)
        self._update_status_choices()
        self._rebuild_rows()

    def _rebuild_rows(self) -> None:
        """Reconstrói lista de rows aplicando filtros e ordenação.

        Round 15: Método interno que aplica filtros de busca e status,
        depois ordena conforme label de ordenação atual.
        """
        from src.core.textnorm import normalize_search

        # 1. Construir rows brutas de todos os clientes
        all_rows = [self._build_row_from_cliente(c) for c in self._clientes_raw]

        # 2. Aplicar filtro de busca
        if self._search_text_raw:
            search_norm = normalize_search(self._search_text_raw.strip())
            if search_norm:
                all_rows = [r for r in all_rows if search_norm in r.search_norm]

        # 3. Aplicar filtro de status
        if self._status_filter:
            status_norm = self._status_filter.strip().lower()
            if status_norm:
                all_rows = [r for r in all_rows if r.status.strip().lower() == status_norm]

        # 4. Aplicar ordenação
        all_rows = self._sort_rows(all_rows)

        # 5. Atualizar cache
        self._rows = all_rows

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
    # Filtros e ordenação (Round 15)
    # ------------------------------------------------------------------ #

    def set_search_text(self, text: str | None, rebuild: bool = True) -> None:
        """Define texto de busca e opcionalmente reconstrói rows.

        Args:
            text: Texto de busca (busca em todos os campos normalizados).
                  None ou string vazia remove o filtro.
            rebuild: Se True, reconstrói rows imediatamente.
                    Se False, apenas armazena o filtro (útil para aplicar múltiplos filtros).
        """
        self._search_text_raw = text
        if rebuild:
            self._rebuild_rows()

    def set_status_filter(self, status: str | None, rebuild: bool = True) -> None:
        """Define filtro de status e opcionalmente reconstrói rows.

        Args:
            status: Status para filtrar (case-insensitive).
                   None ou string vazia remove o filtro.
            rebuild: Se True, reconstrói rows imediatamente.
                    Se False, apenas armazena o filtro.
        """
        self._status_filter = status
        if rebuild:
            self._rebuild_rows()

    def set_order_label(self, label: str, rebuild: bool = True) -> None:
        """Define label de ordenação e opcionalmente reconstrói rows.

        Args:
            label: Label da ordenação (deve existir em order_choices).
            rebuild: Se True, reconstrói rows imediatamente.
                    Se False, apenas armazena a ordenação.
        """
        self._current_order_label = label
        if rebuild:
            self._rebuild_rows()

    def get_rows(self) -> List[ClienteRow]:
        """Retorna lista de rows processadas (filtradas e ordenadas).

        Returns:
            Lista de ClienteRow após aplicação de filtros e ordenação.
        """
        return list(self._rows)

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
        """Exporta dados dos clientes selecionados para CSV ou Excel.

        Abre diálogo para escolher destino e formato de exportação.
        Suporta CSV (padrão) e XLSX (se openpyxl disponível).

        Args:
            ids: Coleção de IDs dos clientes a exportar.

        Note:
            - Em modo cloud-only (RC_NO_LOCAL_FS=1), exportação é bloqueada.
            - Se nenhum cliente selecionado, mostra aviso.
            - CSV usa encoding utf-8-sig para compatibilidade com Excel PT-BR.
        """
        from pathlib import Path
        from tkinter import filedialog, messagebox

        from src.utils.helpers.cloud_guardrails import check_cloud_only_block

        from .export import export_clients_to_csv, export_clients_to_xlsx, is_xlsx_available

        # Verificar cloud-only
        if check_cloud_only_block("Exportação de clientes"):
            return

        # Validar seleção
        if not ids:
            messagebox.showwarning("Exportar Clientes", "Nenhum cliente selecionado para exportação.")
            return

        logger.info("Export batch solicitado para %d cliente(s): %s", len(ids), ids)

        # Filtrar rows dos clientes selecionados
        ids_set = set(ids)
        selected_rows = [row for row in self._rows if row.id in ids_set]

        if not selected_rows:
            messagebox.showwarning("Exportar Clientes", "Clientes selecionados não encontrados.")
            return

        # Determinar tipos de arquivo suportados
        xlsx_available = is_xlsx_available()
        if xlsx_available:
            filetypes = [
                ("Arquivos CSV", "*.csv"),
                ("Arquivos Excel", "*.xlsx"),
                ("Todos os arquivos", "*.*"),
            ]
            default_ext = ".csv"
        else:
            filetypes = [
                ("Arquivos CSV", "*.csv"),
                ("Todos os arquivos", "*.*"),
            ]
            default_ext = ".csv"

        # Abrir diálogo de salvamento
        output_path = filedialog.asksaveasfilename(
            title="Exportar Clientes",
            defaultextension=default_ext,
            filetypes=filetypes,
            initialfile=f"clientes_export_{len(selected_rows)}",
        )

        if not output_path:
            logger.info("Exportação cancelada pelo usuário")
            return

        # Determinar formato baseado na extensão
        output_path_obj = Path(output_path)
        extension = output_path_obj.suffix.lower()

        try:
            if extension == ".xlsx":
                if not xlsx_available:
                    messagebox.showerror(
                        "Erro de Exportação",
                        "Exportação XLSX não disponível.\n\n"
                        "Instale openpyxl com: pip install openpyxl\n"
                        "Ou use formato CSV.",
                    )
                    return
                export_clients_to_xlsx(selected_rows, output_path_obj)
                messagebox.showinfo(
                    "Exportação Concluída",
                    f"{len(selected_rows)} cliente(s) exportado(s) para:\n{output_path}",
                )
            else:
                # Default para CSV
                export_clients_to_csv(selected_rows, output_path_obj)
                messagebox.showinfo(
                    "Exportação Concluída",
                    f"{len(selected_rows)} cliente(s) exportado(s) para:\n{output_path}",
                )

        except Exception as exc:
            logger.error("Erro ao exportar clientes: %s", exc)
            messagebox.showerror(
                "Erro de Exportação",
                f"Falha ao exportar clientes:\n{exc}",
            )

    # ------------------------------------------------------------------ #
    # Ordenação (Round 15)
    # ------------------------------------------------------------------ #
    # Ordenação e chaves de sort
    # ------------------------------------------------------------------ #

    # _only_digits agora usa src.core.string_utils.only_digits
    # Mantido como método estático por compatibilidade com testes existentes
    @staticmethod
    def _only_digits(value: str) -> str:
        """Remove tudo que não for dígito.

        Usado para ordenação numérica de campos como CNPJ e ID.

        Args:
            value: String com possível formatação (pontos, barras, etc).

        Returns:
            String contendo apenas dígitos.

        Note:
            Esta é uma função wrapper. A implementação canônica está em
            src.core.string_utils.only_digits
        """
        return only_digits(value)

    @staticmethod
    def _key_nulls_last(value: str | None, key_func: Callable[[str], str]) -> tuple[bool, str]:
        """Gera chave de ordenação que move valores vazios/None para o final.

        Args:
            value: Valor a ser ordenado.
            key_func: Função para transformar o valor (ex: str.casefold).

        Returns:
            Tupla (is_empty, transformed_value) onde is_empty=True para valores vazios.
            Tuplas com is_empty=True são ordenadas depois das com is_empty=False.
        """
        if value is None:
            return (True, "")

        value_stripped = value.strip()
        if not value_stripped:
            return (True, "")

        return (False, key_func(value_stripped))

    def _sort_rows(self, rows: List[ClienteRow]) -> List[ClienteRow]:
        """Ordena rows conforme label de ordenação atual.

        Args:
            rows: Lista de ClienteRow a ordenar.

        Returns:
            Lista ordenada de ClienteRow.
        """
        if not self._current_order_label or self._current_order_label not in self._order_choices:
            # Sem ordenação configurada ou label inválida: retorna sem ordenar
            return rows

        field, reverse = self._order_choices[self._current_order_label]

        if field is None:
            # Ordem sem campo específico: retorna sem ordenar
            return rows

        # Definir função de chave conforme o campo
        key_func: Callable[[ClienteRow], tuple[bool, Any]]
        if field == "id":
            # Ordenação numérica por ID
            def key_func_id(row: ClienteRow) -> tuple[bool, int]:
                try:
                    return (False, int(self._only_digits(row.id)))
                except (ValueError, TypeError):
                    # IDs inválidos vão para o final
                    return (True, 0)

            key_func = key_func_id  # type: ignore[assignment]

        elif field == "cnpj":
            # Ordenação numérica por CNPJ (apenas dígitos)
            def key_func_cnpj(row: ClienteRow) -> tuple[bool, str]:
                return self._key_nulls_last(self._only_digits(row.cnpj), str.casefold)

            key_func = key_func_cnpj

        elif field == "ultima_alteracao":
            # Ordenação por timestamp de última alteração
            from datetime import datetime

            def key_func_ts(row: ClienteRow) -> tuple[int | bool, Any]:
                ts = row.ultima_alteracao_ts
                if ts is None:
                    # Clientes sem data vão para o final sempre
                    # Quando reverse=False (crescente), grupo 1 vai pro final
                    # Quando reverse=True (decrescente), grupo 0 vai pro final, então invertemos
                    grupo = 0 if reverse else 1
                    return (grupo, datetime.min)

                # Clientes com data ficam no outro grupo
                grupo = 1 if reverse else 0
                if isinstance(ts, datetime):
                    return (grupo, ts)

                # Se for string, tentar converter
                if isinstance(ts, str):
                    try:
                        # Tentar parsear ISO 8601 com datetime.fromisoformat
                        return (grupo, datetime.fromisoformat(ts.replace("Z", "+00:00")))
                    except (ValueError, AttributeError):
                        # Se falhar, tentar outros formatos comuns
                        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                            try:
                                return (grupo, datetime.strptime(ts, fmt))
                            except ValueError:
                                continue

                # Se falhar o parsing, vai pro final
                grupo_final = 0 if reverse else 1
                return (grupo_final, datetime.min)

            key_func = key_func_ts  # type: ignore[assignment]  # Pyright não consegue inferir união de int|bool

        else:
            # Ordenação alfabética por campo genérico
            def key_func_generic(row: ClienteRow) -> tuple[bool, str]:
                value = getattr(row, field, "")
                return self._key_nulls_last(str(value), str.casefold)

            key_func = key_func_generic

        try:
            return sorted(rows, key=key_func, reverse=reverse)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao ordenar rows por %s: %s", field, exc)
            return rows

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
                from src.helpers.formatters import fmt_datetime_br

                updated_fmt = fmt_datetime_br(updated_raw)
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
            ultima_alteracao_ts=updated_raw,  # Guardar o valor bruto para ordenação
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
