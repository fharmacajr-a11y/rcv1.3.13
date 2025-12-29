"""Serviço de negócio para operações com demandas ANVISA.

Camada headless (sem UI) que centraliza regras de negócio:
- Validação de duplicados
- Listagem e filtragem de demandas
- Agrupamento por cliente
- Summarização de demandas
- Lógica de status e normalização

Segue padrão Strangler Fig: extrai lógica gradualmente das Views.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Protocol, TypedDict, cast

from ..constants import (
    REQUEST_TYPES,
    STATUS_ALIASES,
    STATUS_CLOSED,
    STATUS_OPEN,
    StatusType,
)

log = logging.getLogger(__name__)

# Type aliases
DemandaDict = dict[str, Any]  # Estrutura de demanda do banco (flexível)


class ClientRowDict(TypedDict, total=False):
    """Estrutura de row para tabela principal (UI)."""

    client_id: str
    razao_social: str
    cnpj: str
    demanda_label: str
    last_update_dt: datetime | None
    last_update_display: str


class HistoryRowDict(TypedDict):
    """Estrutura de row para histórico de demandas (UI)."""

    request_id: str
    tipo: str
    status_humano: str
    status_raw: StatusType
    actions: dict[str, bool]
    criada_em: str
    atualizada_em: str
    updated_dt_utc: datetime | None
    prazo: str
    observacoes: str


class AnvisaRequestsRepository(Protocol):
    """Protocol para repositório de demandas ANVISA (duck typing)."""

    def list_requests(self, org_id: str) -> list[DemandaDict]:
        """Lista todas as demandas de uma organização.

        Args:
            org_id: ID da organização

        Returns:
            Lista de demandas (dicts)
        """
        ...


class AnvisaService:
    """Serviço headless para operações com demandas ANVISA.

    Centraliza lógica de negócio extraída das Views:
    - Validação de duplicados (mesmo tipo + status aberto)
    - Filtragem e agrupamento de demandas
    - Normalização de tipos e status

    Attributes:
        repository: Repositório de demandas (injetado via DI)
    """

    def __init__(self, repository: AnvisaRequestsRepository) -> None:
        """Inicializa service com repositório injetado.

        Args:
            repository: Repositório de demandas ANVISA (Protocol)
        """
        self.repository = repository

    def list_requests_for_client(self, org_id: str, client_id: str) -> list[DemandaDict]:
        """Lista demandas de um cliente específico.

        Args:
            org_id: ID da organização
            client_id: ID do cliente (farmácia)

        Returns:
            Lista de demandas filtradas por client_id
        """
        try:
            all_requests = self.repository.list_requests(org_id)

            # Filtrar por client_id
            # Converte ambos para string para comparação (DB pode retornar int ou str)
            client_id_str = str(client_id)
            filtered = [req for req in all_requests if str(req.get("client_id", "")) == client_id_str]

            log.debug(f"[ANVISA Service] Listou {len(filtered)} demandas para client_id={client_id}")
            return filtered

        except Exception as e:
            log.error(f"[ANVISA Service] Erro ao listar demandas: {e}", exc_info=True)
            return []

    def check_duplicate_open_request(self, org_id: str, client_id: str, request_type: str) -> DemandaDict | None:
        """Verifica se existe demanda aberta duplicada do mesmo tipo.

        Regra de negócio:
        - Duplicado = mesmo request_type (normalizado) + status aberto
        - Status aberto = draft, submitted, in_progress (via STATUS_OPEN)
        - Normalização: strip + uppercase

        Args:
            org_id: ID da organização
            client_id: ID do cliente
            request_type: Tipo da demanda a verificar

        Returns:
            Dict da demanda duplicada encontrada, ou None se não há duplicado
        """
        try:
            # Listar demandas do cliente
            demandas = self.list_requests_for_client(org_id, client_id)

            # Normalizar tipo procurado
            tipo_norm = self._normalize_type(request_type)

            # Buscar duplicado: mesmo tipo + status aberto
            for demanda in demandas:
                demanda_tipo = str(demanda.get("request_type", ""))
                demanda_status = str(demanda.get("status", ""))

                # Comparar tipos normalizados
                if self._normalize_type(demanda_tipo) != tipo_norm:
                    continue

                # Verificar se status é aberto
                if self._is_open_status(demanda_status):
                    log.info(
                        f"[ANVISA Service] Duplicado encontrado: "
                        f"tipo={request_type}, status={demanda_status}, id={demanda.get('id')}"
                    )
                    return demanda

            # Nenhum duplicado encontrado
            log.debug(f"[ANVISA Service] Nenhum duplicado para tipo={request_type}")
            return None

        except Exception as e:
            log.error(f"[ANVISA Service] Erro ao verificar duplicado: {e}", exc_info=True)
            return None

    def _normalize_type(self, request_type: str) -> str:
        """Normaliza tipo de demanda para comparação case-insensitive.

        Args:
            request_type: Tipo da demanda

        Returns:
            Tipo normalizado (uppercase, sem espaços extras)
        """
        return request_type.strip().upper()

    def _is_open_status(self, status: str) -> bool:
        """Verifica se status indica demanda aberta/em andamento.

        Usa STATUS_OPEN, STATUS_CLOSED e STATUS_ALIASES de constants.py

        Args:
            status: Status da demanda (banco ou legado)

        Returns:
            True se status é aberto (draft, submitted, in_progress), False se fechado
        """
        status_norm = status.strip().lower()

        # Normalizar usando aliases se necessário
        # Ex: "aberta" → "draft", "em andamento" → "in_progress"
        normalized = STATUS_ALIASES.get(status_norm, status_norm)

        # Verificar se está nos status fechados
        if normalized in STATUS_CLOSED:
            return False

        # Verificar se está nos status abertos
        return normalized in STATUS_OPEN

    def group_by_client(self, requests: list[DemandaDict]) -> dict[str, list[DemandaDict]]:
        """Agrupa demandas por client_id.

        Args:
            requests: Lista de demandas (flat)

        Returns:
            Dicionário {client_id: [demandas]}
        """
        grouped: dict[str, list[DemandaDict]] = {}

        for req in requests:
            client_id = str(req.get("client_id", ""))
            if client_id not in grouped:
                grouped[client_id] = []
            grouped[client_id].append(req)

        return grouped

    def check_duplicate_open_in_memory(self, demandas: list[DemandaDict], request_type: str) -> DemandaDict | None:
        """Verifica duplicado em lista já carregada (sem consultar repository).

        Útil quando a View já tem as demandas em cache/memória.

        Args:
            demandas: Lista de demandas do cliente (já filtradas)
            request_type: Tipo da demanda a verificar

        Returns:
            Dict da demanda duplicada encontrada, ou None
        """
        tipo_norm = self._normalize_type(request_type)

        for demanda in demandas:
            demanda_tipo = str(demanda.get("request_type", ""))
            demanda_status = str(demanda.get("status", ""))

            # Comparar tipos normalizados
            if self._normalize_type(demanda_tipo) != tipo_norm:
                continue

            # Verificar se status é aberto
            if self._is_open_status(demanda_status):
                log.debug(f"[ANVISA Service] Duplicado in-memory: tipo={request_type}, status={demanda_status}")
                return demanda

        return None

    def summarize_demands(self, demandas: list[DemandaDict]) -> tuple[str, datetime | None]:
        """Resume demandas de um cliente para exibição.

        Regras:
        - 0 demandas: ("", None)
        - 1 demanda: (request_type, last_update_dt)
        - 2+ demandas: ("X demandas (Y em aberto)", last_update_dt) ou
                       ("X demandas (finalizadas)", last_update_dt)

        Args:
            demandas: Lista de demandas do cliente

        Returns:
            Tupla (label, last_update_dt)
            - label: Resumo das demandas
            - last_update_dt: datetime da última atualização (UTC) ou None
        """
        total = len(demandas)

        if total == 0:
            return "", None

        # Encontrar data mais recente
        last_update_dt: datetime | None = None

        for dem in demandas:
            updated = dem.get("updated_at") or dem.get("created_at", "")
            if updated:
                dt = self._parse_iso_datetime(updated)
                if dt and (last_update_dt is None or dt > last_update_dt):
                    last_update_dt = dt

        # Se apenas 1 demanda: mostrar tipo
        if total == 1:
            request_type = demandas[0].get("request_type", "")
            return request_type, last_update_dt

        # Contar demandas em aberto
        open_count = sum(1 for dem in demandas if self._is_open_status(dem.get("status", "")))

        # Criar label resumido
        if open_count > 0:
            label = f"{total} demandas ({open_count} em aberto)"
        else:
            label = f"{total} demandas (finalizadas)"

        return label, last_update_dt

    def _parse_iso_datetime(self, dt_str: str) -> datetime | None:
        """Parse ISO datetime string para datetime object (UTC).

        Args:
            dt_str: String ISO datetime (ex: "2025-12-19T22:41:00+00:00" ou "...Z")

        Returns:
            datetime object em UTC ou None se falhar
        """
        if not dt_str:
            return None

        try:
            # Normalizar Z para +00:00
            dt_str_clean = dt_str.replace("Z", "+00:00")

            # Parse ISO format
            dt = datetime.fromisoformat(dt_str_clean)

            # Se vier naive (sem timezone), assumir UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # Converter para UTC se não estiver
            dt_utc = dt.astimezone(timezone.utc)

            return dt_utc

        except Exception as e:
            log.debug(f"[ANVISA Service] Erro ao parsear datetime: {dt_str} - {e}")
            return None

    def build_main_rows(self, requests: list[DemandaDict]) -> tuple[dict[str, list[DemandaDict]], list[ClientRowDict]]:
        """Constrói dados prontos para renderização na tabela principal.

        Agrupa demandas por cliente, calcula resumo e prepara rows para a View.
        A View só precisa renderizar os dados retornados.

        Args:
            requests: Lista flat de todas as demandas

        Returns:
            Tupla (requests_by_client, rows):
            - requests_by_client: Dict {client_id: [demandas]} para cache
            - rows: Lista de dicts prontos para inserir no Treeview, ordenados por razao_social

        Exemplo de row:
            {
                "client_id": "123",
                "razao_social": "Farmácia ABC",
                "cnpj": "12345678000190",
                "demanda_label": "2 demandas (1 em aberto)",
                "last_update_dt": datetime(2024, 1, 16, 13, 0, 0, tzinfo=UTC),
                "last_update_display": "16/01/2024 - 10:00 (J)",
            }
        """
        # Agrupar por cliente
        requests_by_client = self.group_by_client(requests)

        # Construir rows
        rows: list[ClientRowDict] = []

        for client_id, demandas in requests_by_client.items():
            # Extrair info do cliente da primeira demanda
            first_req = demandas[0] if demandas else {}
            clients_data = first_req.get("clients", {})

            if clients_data:
                razao = clients_data.get("razao_social", "")
                cnpj = clients_data.get("cnpj", "")
            else:
                razao = "[Dados não disponíveis]"
                cnpj = ""

            # Resumir demandas
            demanda_label, last_update_dt = self.summarize_demands(demandas)

            # Calcular last_update_display com tracinho e inicial do autor
            last_update_display = ""
            last_update_by_email = ""

            # Encontrar demanda mais recente e seu autor
            most_recent_dt: datetime | None = None
            for dem in demandas:
                updated = dem.get("updated_at") or dem.get("created_at") or ""
                dt = self._parse_iso_datetime(updated) if updated else None
                if dt and (most_recent_dt is None or dt > most_recent_dt):
                    most_recent_dt = dt
                    # Capturar email do autor da demanda mais recente
                    payload_raw = dem.get("payload") or {}
                    payload = payload_raw if isinstance(payload_raw, dict) else {}
                    last_update_by_email = str(payload.get("updated_by") or payload.get("created_by") or "").strip()

            # Formatar display com tracinho e inicial
            if most_recent_dt:
                base = self.format_dt_local_dash(most_recent_dt)
                if base and last_update_by_email:
                    initial = self.resolve_initial_from_email(last_update_by_email)
                    if initial:
                        base = f"{base} ({initial})"
                last_update_display = base

            # Montar row
            row: ClientRowDict = {
                "client_id": client_id,
                "razao_social": razao,
                "cnpj": cnpj,
                "demanda_label": demanda_label,
                "last_update_dt": last_update_dt,
                "last_update_display": last_update_display,
            }
            rows.append(row)

        # Ordenar por razão social (A→Z)
        rows.sort(key=lambda r: r.get("razao_social", "").upper())

        log.debug(f"[ANVISA Service] Construídos {len(rows)} rows para {len(requests)} demandas")
        return requests_by_client, rows

    def format_dt_local(self, dt_utc: datetime | None, tz_name: str = "America/Sao_Paulo") -> str:
        """Formata datetime UTC para string no timezone local.

        Args:
            dt_utc: datetime em UTC ou None
            tz_name: Nome do timezone (IANA timezone database)

        Returns:
            String formatada "DD/MM/YYYY HH:MM" ou "" se None
        """
        if not dt_utc:
            return ""

        try:
            from zoneinfo import ZoneInfo

            # Converter para timezone local
            local_tz = ZoneInfo(tz_name)
            dt_local = dt_utc.astimezone(local_tz)

            # Formatar
            return dt_local.strftime("%d/%m/%Y %H:%M")

        except Exception as e:
            log.debug(f"[ANVISA Service] Erro ao formatar datetime: {e}")
            # Fallback: usar offset fixo UTC-3
            try:
                from datetime import timedelta

                local_tz_fallback = timezone(timedelta(hours=-3))
                dt_local_fallback = dt_utc.astimezone(local_tz_fallback)
                return dt_local_fallback.strftime("%d/%m/%Y %H:%M")
            except Exception:
                return ""

    def normalize_request_type(self, request_type: str) -> str:
        """Normaliza tipo de demanda para formato oficial.

        Compara o tipo fornecido com os tipos oficiais do constants.REQUEST_TYPES,
        ignorando case e espaços extras.

        Args:
            request_type: Tipo da demanda (pode ter case/espaços diferentes)

        Returns:
            Tipo oficial se encontrado, ou string vazia se inválido

        Example:
            >>> service.normalize_request_type("  alteração de rt  ")
            "Alteração de RT"
            >>> service.normalize_request_type("tipo_invalido")
            ""
        """

        # Normalizar: trim + casefold (case-insensitive)
        normalized_input = request_type.strip().casefold()

        # Buscar correspondência nos tipos oficiais
        for official_type in REQUEST_TYPES:
            if official_type.casefold() == normalized_input:
                return official_type

        # Não encontrado
        log.warning(f"[ANVISA Service] Tipo de demanda inválido: '{request_type}'")
        return ""

    def validate_new_request_in_memory(
        self,
        demandas_cliente: list[DemandaDict],
        request_type: str,
    ) -> tuple[bool, DemandaDict | None, str]:
        """Valida criação de nova demanda usando cache em memória.

        Verifica:
        1. Tipo de demanda é válido (existe em REQUEST_TYPES)
        2. Não existe duplicado aberto do mesmo tipo

        Args:
            demandas_cliente: Lista de demandas do cliente (cache)
            request_type: Tipo da demanda a criar

        Returns:
            Tupla com (ok, duplicate_request, msg):
            - ok: True se validação passou, False caso contrário
            - duplicate_request: Dict da demanda duplicada (se existir), ou None
            - msg: Mensagem amigável para a UI

        Example:
            >>> ok, dup, msg = service.validate_new_request_in_memory(demandas, "Alteração de RT")
            >>> if not ok:
            ...     print(msg)
        """
        # 1) Validar tipo
        normalized_type = self.normalize_request_type(request_type)
        if not normalized_type:
            return (
                False,
                None,
                f"Tipo de demanda inválido: '{request_type}'.\n\nEscolha um tipo válido.",
            )

        # 2) Verificar duplicado aberto
        duplicado = self.check_duplicate_open_in_memory(demandas_cliente, normalized_type)

        if duplicado:
            dup_status = duplicado.get("status", "")
            return (
                False,
                duplicado,
                f"Já existe uma demanda ABERTA desse tipo para esta farmácia.\n\n"
                f"Tipo: {normalized_type}\n"
                f"Status: {dup_status}\n\n"
                f"Finalize ou cancele a demanda existente antes de criar uma nova.",
            )

        # Validação passou
        return (True, None, "")

    def human_status(self, status: str) -> str:
        """Converte status técnico para texto legível.

        Diferencia status finalizados: done → "Concluída", canceled → "Cancelada"

        Args:
            status: Status da demanda (banco ou legado)

        Returns:
            "Em aberto" para status abertos, "Concluída"/"Cancelada" para fechados

        Example:
            >>> service.human_status("draft")
            "Em aberto"
            >>> service.human_status("done")
            "Concluída"
            >>> service.human_status("canceled")
            "Cancelada"
        """
        # Normalizar para status canônico
        norm = self.normalize_status(status)

        # Status abertos
        if norm in STATUS_OPEN:
            return "Em aberto"

        # Status fechados específicos
        if norm == "done":
            return "Concluída"
        if norm == "canceled":
            return "Cancelada"

        # Fallback genérico
        return "Finalizado"

    def normalize_status(self, status: str) -> StatusType:
        """Normaliza status usando aliases para formato canônico.

        Converte status legado ou variações para status oficial do banco.

        Args:
            status: Status da demanda (pode ser legado, ex: "aberta", "finalizada")

        Returns:
            Status normalizado (ex: "draft", "done", "canceled")

        Example:
            >>> service.normalize_status("aberta")
            "draft"
            >>> service.normalize_status("cancelada")
            "canceled"
            >>> service.normalize_status("draft")  # Já normalizado
            "draft"
        """
        status_norm = status.strip().lower()
        # Usar aliases ou retornar o próprio status normalizado
        # cast: em runtime assumimos que o status é válido (StatusType)
        return cast(StatusType, STATUS_ALIASES.get(status_norm, status_norm))

    def can_close(self, status: str) -> bool:
        """Verifica se demanda pode ser finalizada.

        Apenas demandas "Em aberto" podem ser finalizadas.

        Args:
            status: Status da demanda

        Returns:
            True se pode finalizar, False caso contrário

        Example:
            >>> service.can_close("draft")
            True
            >>> service.can_close("done")
            False
        """
        return self._is_open_status(status)

    def can_cancel(self, status: str) -> bool:
        """Verifica se demanda pode ser cancelada.

        Apenas demandas "Em aberto" podem ser canceladas.

        Args:
            status: Status da demanda

        Returns:
            True se pode cancelar, False caso contrário

        Example:
            >>> service.can_cancel("in_progress")
            True
            >>> service.can_cancel("canceled")
            False
        """
        return self._is_open_status(status)

    def allowed_actions(self, status: str) -> dict[str, bool]:
        """Retorna ações permitidas para uma demanda baseado no status.

        Centraliza regras de negócio para habilitar/desabilitar botões na UI.

        Args:
            status: Status da demanda

        Returns:
            Dicionário com ações e se são permitidas:
            - close: pode finalizar
            - cancel: pode cancelar
            - delete: pode excluir (sempre True)

        Example:
            >>> service.allowed_actions("draft")
            {"close": True, "cancel": True, "delete": True}
            >>> service.allowed_actions("done")
            {"close": False, "cancel": False, "delete": True}
        """
        is_open = self._is_open_status(status)
        return {
            "close": is_open,
            "cancel": is_open,
            "delete": True,  # Sempre pode excluir
        }

    def build_history_rows(self, demandas: list[DemandaDict]) -> list[HistoryRowDict]:
        """Prepara dados do histórico de demandas para renderização.

        Extrai e formata informações de cada demanda para exibição no popup.
        Ordena por data de atualização (mais recente primeiro).
        Inclui status canônico e ações permitidas calculadas.

        Args:
            demandas: Lista de demandas do cliente

        Returns:
            Lista de dicts com campos prontos para render:
            - request_id: UUID da demanda (string)
            - tipo: Tipo da demanda
            - status_humano: "Em aberto" ou "Finalizado"
            - status_raw: Status canônico (draft/submitted/in_progress/done/canceled)
            - actions: Dict com ações permitidas {"close": bool, "cancel": bool, "delete": bool}
            - criada_em: Data formatada DD/MM/YYYY HH:MM
            - atualizada_em: Data formatada DD/MM/YYYY HH:MM
            - updated_dt_utc: datetime UTC para ordenação (uso interno)

        Example:
            >>> rows = service.build_history_rows(demandas)
            >>> for row in rows:
            ...     print(row["tipo"], row["status_humano"], row["actions"])
        """
        if not demandas:
            return []

        rows: list[HistoryRowDict] = []

        for dem in demandas:
            # Extrair campos básicos
            request_id = str(dem.get("id", ""))
            tipo = dem.get("request_type", "")
            status_original = dem.get("status", "")

            # Normalizar status para canônico
            status_raw: StatusType = self.normalize_status(status_original)

            # Status legível
            status_humano = self.human_status(status_raw)

            # Calcular ações permitidas
            actions = self.allowed_actions(status_raw)

            # Datas
            created_at = dem.get("created_at", "")
            updated_at = dem.get("updated_at", "") or created_at

            # Parse para datetime UTC (para ordenação)
            updated_dt_utc = self._parse_iso_datetime(updated_at)
            created_dt_utc = self._parse_iso_datetime(created_at)

            # Formatar datas com tracinho
            criada_em = self.format_dt_local_dash(created_dt_utc) if created_dt_utc else ""
            atualizada_em = self.format_dt_local_dash(updated_dt_utc) if updated_dt_utc else ""

            # Extrair payload (prazo, observações e autores)
            payload_raw = dem.get("payload") or {}
            payload = payload_raw if isinstance(payload_raw, dict) else {}

            due_iso = str(payload.get("due_date") or "").strip()
            notes = str(payload.get("notes") or "").strip()

            prazo = self.format_due_date_iso_to_br(due_iso)
            observacoes = notes

            # Adicionar inicial do usuário em criada_em (se disponível)
            created_by = str(payload.get("created_by") or "").strip()
            if criada_em and created_by:
                initial = self.resolve_initial_from_email(created_by)
                if initial:
                    criada_em = f"{criada_em} ({initial})"

            # Adicionar inicial do usuário em atualizada_em (com fallback para created_by)
            updated_by = str(payload.get("updated_by") or "").strip()
            author = updated_by or created_by
            if atualizada_em and author:
                initial = self.resolve_initial_from_email(author)
                if initial:
                    atualizada_em = f"{atualizada_em} ({initial})"

            # Montar row
            row: HistoryRowDict = {
                "request_id": request_id,
                "tipo": tipo,
                "status_humano": status_humano,
                "status_raw": status_raw,
                "actions": actions,
                "criada_em": criada_em,
                "atualizada_em": atualizada_em,
                "updated_dt_utc": updated_dt_utc,
                "prazo": prazo,
                "observacoes": observacoes,
            }

            rows.append(row)

        # Ordenar por updated_dt_utc desc (mais recente primeiro)
        rows.sort(key=lambda r: r["updated_dt_utc"] or datetime.min, reverse=True)

        return rows

    # ========== HELPERS PARA PAYLOAD DE NOVA DEMANDA ==========

    def format_due_date_iso_to_br(self, iso: str) -> str:
        """Converte data ISO para formato brasileiro.

        Aceita:
        - "" -> ""
        - "aaaa-mm-dd" -> "dd/mm/aaaa"

        Se formato inválido, retorna "".

        Args:
            iso: String de data no formato ISO (aaaa-mm-dd)

        Returns:
            String brasileira (dd/mm/aaaa) ou "" se vazio/inválido
        """
        s = (iso or "").strip()
        if not s:
            return ""
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return ""

    def format_dt_local_dash(self, dt_utc: datetime | None) -> str:
        """Formata datetime UTC para string local com tracinho.

        Formato: "DD/MM/AAAA - HH:MM"

        Args:
            dt_utc: datetime em UTC ou None

        Returns:
            String formatada "DD/MM/AAAA - HH:MM" ou "" se None
        """
        base = self.format_dt_local(dt_utc)
        if " " in base:
            return base.replace(" ", " - ", 1)
        return base

    def resolve_initial_from_email(self, email: str) -> str:
        """Resolve inicial do usuário a partir do email.

        Usa RC_INITIALS_MAP do .env se disponível, senão
        retorna a primeira letra do email (uppercase).

        Args:
            email: Email do usuário

        Returns:
            Inicial do usuário (1 caractere) ou "" se email vazio
        """
        email_clean = (email or "").strip().lower()
        if not email_clean:
            return ""

        # Tentar carregar do RC_INITIALS_MAP
        try:
            from src.modules.hub.services.authors_service import load_env_author_names

            env_map = load_env_author_names()
            if email_clean in env_map:
                name = env_map[email_clean]
                if name:
                    return name[0].upper()
        except Exception:  # noqa: BLE001  # nosec B110 - Safe fallback para inicial
            pass

        # Fallback: primeira letra do email
        return email_clean[0].upper() if email_clean else ""

    def parse_due_date_br(self, value: str) -> str | None:
        """Converte data no formato brasileiro para ISO.

        Aceita:
        - "" -> None
        - "dd/mm/aaaa" -> "aaaa-mm-dd"

        Se formato inválido, retorna None.

        Args:
            value: String de data no formato brasileiro (dd/mm/aaaa)

        Returns:
            String ISO (aaaa-mm-dd) ou None se vazio/inválido
        """
        s = (value or "").strip()
        if not s:
            return None
        try:
            dt = datetime.strptime(s, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None

    def request_type_check_daily(self, request_type: str) -> bool:
        """Verifica se o tipo de demanda precisa de acompanhamento diário no Solicita.

        Regras:
        - Tipos "instantâneos" (não precisam acompanhamento): retorna False
          * Alteração do Responsável Legal
          * Alteração do Responsável Técnico
          * Associação ao SNGPC
          * Importação de Cannabidiol

        - Todos os outros tipos precisam: retorna True
          (Ex: AFE, AE Manipulação, Alteração de Nome Fantasia, etc.)

        Args:
            request_type: Tipo de demanda ANVISA

        Returns:
            True se precisa acompanhar diariamente, False caso contrário
        """
        instant_types = {
            "Alteração do Responsável Legal",
            "Alteração do Responsável Técnico",
            "Associação ao SNGPC",
            "Importação de Cannabidiol",
        }
        return request_type not in instant_types

    def default_due_date_iso_for_type(self, request_type: str, today: date) -> str:
        """Calcula data de prazo padrão conforme tipo de demanda.

        Regras:
        - Tipos que precisam acompanhamento (check_daily=True):
          prazo = hoje + 1 dia (protocolo costuma sair ~24h após pagamento)

        - Tipos instantâneos (check_daily=False):
          prazo = hoje (não há protocolo a consultar)

        Args:
            request_type: Tipo de demanda ANVISA
            today: Data de referência (normalmente date.today())

        Returns:
            String ISO (YYYY-MM-DD) com prazo sugerido
        """
        if self.request_type_check_daily(request_type):
            return (today + timedelta(days=1)).isoformat()
        return today.isoformat()

    def build_payload_for_new_request(
        self,
        *,
        request_type: str,
        due_date_iso: str,
        notes: str,
    ) -> dict[str, object]:
        """Constrói payload JSON para nova demanda ANVISA.

        Args:
            request_type: Tipo de demanda (para determinar check_daily)
            due_date_iso: Data de prazo ISO obrigatória (YYYY-MM-DD)
            notes: Observações (texto livre), ou vazio

        Returns:
            Dict com due_date (sempre), check_daily (sempre), notes (opcional)
        """
        payload: dict[str, object] = {
            "due_date": due_date_iso,
            "check_daily": self.request_type_check_daily(request_type),
        }

        clean_notes = (notes or "").strip()
        if clean_notes:
            payload["notes"] = clean_notes[:500]

        return payload
