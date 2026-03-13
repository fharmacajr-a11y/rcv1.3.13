from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Iterable, List

from src.core.search import search_clientes, search_clientes_lixeira
from src.core.string_utils import only_digits
from src.core.textnorm import join_and_normalize
from src.utils.phone_utils import normalize_br_whatsapp

from . import constants as status_helpers

if TYPE_CHECKING:
    pass  # Imports apenas para type checking, se necessário

log = logging.getLogger(__name__)

#: Tamanho padrão de página para busca paginada no Supabase.
PAGE_SIZE: int = 200


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

        # Estado de paginação (PR5)
        self._page_size: int = PAGE_SIZE
        self._current_offset: int = 0
        self._has_more: bool = False

        # Estado server-side (query propagada ao Supabase)
        self._server_term: str = ""
        self._server_order_by: str | None = None
        self._fetch_all: bool = False
        self._cap_hit: bool = False
        self._trash_mode: bool = False

    # ------------------------------------------------------------------ #
    # Carregamento de dados
    # ------------------------------------------------------------------ #

    # Mapeamento de labels de UI → order_by server-side.
    # Labels cujo campo só faz sentido em sort local (telefone_ddd, nome_asc…)
    # são mapeados para o equivalente canônico mais próximo, ou None.
    _LABEL_TO_SERVER: dict[str, str | None] = {
        "razao_social": "razao_social",
        "cnpj": "cnpj",
        "id": "id",
        "ultima_alteracao": "ultima_alteracao",
        # campos locais — mapeados para coluna DB mais próxima
        "nome_asc": "nome",
        "nome_desc": "-nome",
        "telefone_ddd_asc": None,  # sem coluna server-side
        "telefone_ddd_desc": None,
        "telefone_ddd": None,
    }

    def _label_to_server_order(self, order_label: str | None) -> str | None:
        """Converte o order_label da UI (ex: ``ORDER_CHOICES`` field) em string para ``search_clientes``.

        Retorna ``None`` quando a ordenação só faz sentido localmente.
        Para campos com *reverse=True* no ``ORDER_CHOICES``, adiciona prefixo ``-``.
        """
        if not order_label or order_label not in self._order_choices:
            return None

        field, reverse = self._order_choices[order_label]
        if field is None:
            return None

        # Verificar se tem mapeamento explícito
        server_col = self._LABEL_TO_SERVER.get(field, field)
        if server_col is None:
            return None

        # Se o mapeamento já contém prefixo (-), respeitar
        if server_col.startswith("-") or server_col.startswith("+"):
            return server_col

        # Aplicar flag de reverse do ORDER_CHOICES
        if reverse:
            return f"-{server_col}"
        return f"+{server_col}"

    def refresh_from_service(
        self,
        term: str | None = None,
        order_label: str | None = None,
        *,
        fetch_all: bool = False,
        trash: bool = False,
    ) -> None:
        """Carrega primeira página de clientes via search_clientes.

        Args:
            term: Termo de busca server-side (passado ao Supabase ``ilike``).
                  ``None`` ou ``""`` = sem filtro textual.
            order_label: Label de ordenação da UI.  Convertido para
                         ``order_by`` server-side via ``_label_to_server_order``.
            fetch_all: Se ``True``, busca **todos** os registros (``limit=None``)
                       — usado quando o usuário pesquisa para não perder resultados.
            trash: Se ``True``, busca na lixeira (``deleted_at IS NOT NULL``).
        """
        # Persistir estado para load_next_page
        self._server_term = (term or "").strip()
        self._server_order_by = self._label_to_server_order(order_label)
        self._fetch_all = fetch_all
        self._trash_mode = trash

        # Termo muito curto não justifica fetch_all — fallback para paginação normal
        if fetch_all and len(self._server_term) < 2:
            self._fetch_all = False
            fetch_all = False

        fetch_all_limit = 1000

        self._current_offset = 0
        lim: int | None = fetch_all_limit if fetch_all else self._page_size
        _search_fn = search_clientes_lixeira if self._trash_mode else search_clientes
        try:
            clientes = _search_fn(
                self._server_term,
                self._server_order_by,
                limit=lim,
                offset=0,
            )
        except Exception as exc:  # pragma: no cover - erros propagados
            raise ClientesViewModelError(str(exc)) from exc

        if fetch_all:
            self._cap_hit = len(clientes) >= fetch_all_limit
            self._has_more = self._cap_hit
            if self._cap_hit:
                log.warning(
                    "fetch_all atingiu o limite de %d registros para term=%r; resultados podem estar incompletos",
                    fetch_all_limit,
                    self._server_term,
                )
            self._current_offset = len(clientes)
        else:
            self._cap_hit = False
            self._has_more = len(clientes) >= self._page_size
            self._current_offset = len(clientes)

        self._clientes_raw = list(clientes)
        self._update_status_choices()
        self._rebuild_rows()

    def load_next_page(self) -> bool:
        """Carrega próxima página e acrescenta aos dados existentes.

        Reutiliza ``_server_term`` e ``_server_order_by`` salvos por
        ``refresh_from_service`` para manter ordenação/filtro consistentes.

        Returns:
            True se novos registros foram carregados, False se não há mais.
        """
        if not self._has_more:
            return False

        _search_fn = search_clientes_lixeira if self._trash_mode else search_clientes
        try:
            clientes = _search_fn(
                self._server_term,
                self._server_order_by,
                limit=self._page_size,
                offset=self._current_offset,
            )
        except Exception as exc:  # pragma: no cover
            raise ClientesViewModelError(str(exc)) from exc

        if not clientes:
            self._has_more = False
            self._cap_hit = False
            return False

        self._has_more = len(clientes) >= self._page_size
        if not self._has_more:
            self._cap_hit = False
        self._current_offset += len(clientes)
        self._clientes_raw.extend(clientes)
        self._update_status_choices()
        self._rebuild_rows()
        return True

    @property
    def has_more(self) -> bool:  # noqa: D401
        """True se há mais páginas a carregar do servidor."""
        return self._has_more

    @property
    def cap_hit(self) -> bool:  # noqa: D401
        """True se fetch_all atingiu o limite de 1000 registros."""
        return self._cap_hit

    @property
    def trash_mode(self) -> bool:  # noqa: D401
        """True se o último fetch foi na lixeira."""
        return self._trash_mode

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

        # 1b. No modo lixeira, marcar clientes sem status como "[LIXEIRA]"
        if self._trash_mode:
            for row in all_rows:
                if not row.status:
                    row.status = "[LIXEIRA]"

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

        elif field in ("telefone_ddd", "telefone_ddd_asc", "telefone_ddd_desc"):
            # Ordenação numérica por DDD e depois pelo restante do número
            _desc_tel = field == "telefone_ddd_desc"

            def key_func_telefone(row: ClienteRow, _desc: bool = _desc_tel) -> tuple[int, int, int]:
                # Pegar telefone de whatsapp (preferido) ou numero
                raw = (row.whatsapp or "").strip()
                if not raw:
                    raw = getattr(row, "numero", "") or ""
                    raw = raw.strip()

                # Extrair somente dígitos
                digits = "".join(c for c in raw if c.isdigit())

                # Remover prefixo internacional "55" do Brasil se necessário
                if digits.startswith("55") and len(digits) > 11:
                    digits = digits[2:]

                # Válido: mínimo 10 dígitos (DDD + 8 dig) ou 11 (DDD + 9 dig)
                if len(digits) < 10:
                    # Inválido/vazio: vai para o final
                    return (1, 0, 0)

                # DDD = primeiros 2 dígitos, resto = demais
                try:
                    ddd = int(digits[:2])
                    resto = int(digits[2:])
                    if _desc:
                        # Negamos para ordem decrescente sem usar reverse=True
                        # (garante que vazios is_empty=1 ficam no fim)
                        return (0, -ddd, -resto)
                    return (0, ddd, resto)
                except (ValueError, TypeError):
                    return (1, 0, 0)

            key_func = key_func_telefone  # type: ignore[assignment]

        elif field in ("nome_asc", "nome_desc", "nome"):
            # Ordenação alfabética pelo nome (campo 'nome' do cliente)
            # Vazios sempre no fim em ambas as direções (sem depender de reverse)
            _desc_nome = field == "nome_desc"
            _max_cp = 0x10FFFF

            def key_func_nome(row: ClienteRow, _desc: bool = _desc_nome, _mx: int = _max_cp) -> tuple[int, str]:
                val = (getattr(row, "nome", "") or "").strip()
                if not val:
                    return (1, "")
                if _desc:
                    # Inverter codepoints para ordem descend. sem usar reverse
                    return (0, "".join(chr(_mx - ord(c)) for c in val.casefold()))
                return (0, val.casefold())

            key_func = key_func_nome  # type: ignore[assignment]

        else:
            # Ordenação alfabética por campo genérico
            def key_func_generic(row: ClienteRow) -> tuple[bool, str]:
                value = getattr(row, field, "")
                return self._key_nulls_last(str(value), str.casefold)

            key_func = key_func_generic

        try:
            return sorted(rows, key=key_func, reverse=reverse)
        except Exception as exc:  # noqa: BLE001
            log.debug("Falha ao ordenar rows por %s: %s", field, exc)
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
            log.debug("Falha ao formatar CNPJ no ClientesViewModel: %s", exc)

        updated_raw = self._value_from_cliente(cliente, "ultima_alteracao", "updated_at")
        updated_fmt = ""
        if updated_raw:
            try:
                from src.utils.formatters import fmt_datetime_br

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
