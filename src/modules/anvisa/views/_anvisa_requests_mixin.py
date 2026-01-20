"""Mixin para operações de cache e carregamento de demandas ANVISA."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, Optional

from tkinter import messagebox

from src.modules.anvisa.constants import (
    DEFAULT_CREATE_STATUS,
)

if TYPE_CHECKING:
    from ..controllers.anvisa_requests_controller import AnvisaRequestsController

log = logging.getLogger(__name__)


class AnvisaRequestsMixin:
    """Mixin com métodos de cache, helpers e load de requests."""

    def _get_requests_controller(self) -> AnvisaRequestsController:
        """Retorna (ou cria) o controller de requests ANVISA.

        Returns:
            Instância de AnvisaRequestsController
        """
        from ..controllers.anvisa_requests_controller import AnvisaRequestsController

        ctrl = getattr(self, "_requests_controller", None)
        if isinstance(ctrl, AnvisaRequestsController):
            return ctrl
        ctrl = AnvisaRequestsController(logger=log)
        setattr(self, "_requests_controller", ctrl)
        return ctrl

    def _resolve_org_id(self) -> Optional[str]:
        """Resolve o org_id do usuário logado.

        Returns:
            org_id se encontrado, None caso contrário
        """
        try:
            org_id = self._get_requests_controller().resolve_org_id()
            return org_id
        except Exception as e:
            log.exception("Erro ao resolver org_id")
            messagebox.showerror(
                "Erro de Autenticação",
                f"Não foi possível obter organização do usuário.\n\nFaça login novamente.\n\nDetalhes: {e}",
            )
            return None

    def _load_requests_from_cloud(self) -> None:
        """Carrega demandas ANVISA do Supabase e preenche Treeview.

        Agrupa demandas por cliente (1 linha por cliente na tabela principal).
        A coluna 'Demanda' mostra um resumo: tipo único ou "X demandas (Y em aberto)".
        """
        org_id = self._resolve_org_id()
        if not org_id:
            self.last_action.set("Erro: sem sessão ativa")  # type: ignore[attr-defined]
            return

        try:
            log.info("[ANVISA] Carregando demandas do Supabase...")
            requests = self._get_requests_controller().list_requests(org_id)

            # Limpar Treeview antes de popular
            self.tree_requests.clear()  # type: ignore[attr-defined]

            # Service prepara dados prontos para renderização (agrupamento + sumário)
            self._requests_by_client, rows = self._service.build_main_rows(requests)  # type: ignore[attr-defined]

            # Popular Treeview: 1 linha por cliente (já ordenado por razão social)
            for row in rows:
                client_id = row["client_id"]
                razao = row["razao_social"]
                cnpj = row["cnpj"]
                demanda_label = row["demanda_label"]

                # Usar last_update_display pronto do service (com tracinho e inicial)
                last_update_fmt = row.get("last_update_display", "")

                # Formatar CNPJ com máscara
                cnpj_fmt = self._format_cnpj(cnpj)

                # Inserir linha no Treeview
                self.tree_requests.insert(  # type: ignore[attr-defined]
                    "",
                    "end",
                    iid=client_id,
                    values=[client_id, razao, cnpj_fmt, demanda_label, last_update_fmt],
                )

            count = len(rows)
            total_demands = len(requests)
            self.last_action.set(f"{count} cliente(s) com {total_demands} demanda(s) carregada(s)")  # type: ignore[attr-defined]
            log.info(f"[ANVISA] {count} cliente(s) com {total_demands} demanda(s) carregada(s)")

        except Exception as e:
            log.exception("Erro ao carregar demandas do Supabase")
            self.last_action.set(f"Erro ao carregar: {e}")  # type: ignore[attr-defined]
            messagebox.showerror(
                "Erro ao Carregar",
                f"Não foi possível carregar demandas do Supabase.\n\nDetalhes: {e}",
            )

    def _norm_tipo(self, s: str) -> str:
        """Normaliza tipo de demanda para comparação.

        Args:
            s: String do tipo

        Returns:
            Tipo normalizado (uppercase, sem espaços extras)
        """
        return s.strip().upper()

    def _is_open_status(self, status: str) -> bool:
        """Verifica se status indica demanda aberta/em andamento.

        Args:
            status: Status da demanda (banco ou legado)

        Returns:
            True se status é aberto/em andamento (draft, submitted, in_progress)
        """
        from ..constants import STATUS_OPEN, STATUS_CLOSED, STATUS_ALIASES

        status_norm = status.strip().lower()

        # Normalizar usando aliases se necessário
        normalized = STATUS_ALIASES.get(status_norm, status_norm)

        # Verificar se está nos status fechados
        if normalized in STATUS_CLOSED:
            return False

        # Verificar se está nos status abertos
        return normalized in STATUS_OPEN

    def _human_status(self, status: str) -> str:
        """Converte status técnico para texto legível.

        Args:
            status: Status da demanda

        Returns:
            "Em aberto" para status abertos, "Finalizado" para fechados
        """
        if self._is_open_status(status):
            return "Em aberto"
        return "Finalizado"

    def _load_demandas_for_cliente(self, client_id: str) -> list[dict[str, Any]]:
        """Carrega demandas de um cliente específico (com cache).

        Args:
            client_id: ID do cliente

        Returns:
            Lista de demandas do cliente
        """
        # Verificar cache
        if client_id in self._demandas_cache:  # type: ignore[attr-defined]
            return self._demandas_cache[client_id]  # type: ignore[attr-defined]

        org_id = self._resolve_org_id()
        if not org_id:
            return []

        try:
            # Carregar todas as demandas da org via controller
            all_requests = self._get_requests_controller().list_requests(org_id)

            # Filtrar por client_id
            client_requests = [req for req in all_requests if str(req.get("client_id", "")) == client_id]

            # Armazenar no cache
            self._demandas_cache[client_id] = client_requests  # type: ignore[attr-defined]

            return client_requests

        except Exception:
            log.exception(f"Erro ao carregar demandas do cliente {client_id}")
            return []

    def _summarize_demands_for_main(self, demandas: list[dict[str, Any]]) -> tuple[str, str]:
        """Resume demandas de um cliente para exibição na tabela principal.

        DEPRECATED: Use AnvisaService.summarize_demands() para nova implementação.
        Mantido apenas para retrocompatibilidade com testes existentes.

        Cria um label resumido baseado na quantidade e status das demandas.

        Args:
            demandas: Lista de demandas do cliente

        Returns:
            Tupla (demanda_label, last_update_str)
            - demanda_label: Resumo das demandas (ex: "2 demandas (1 em aberto)")
            - last_update_str: Data da última atualização formatada
        """
        total = len(demandas)

        if total == 0:
            return "", ""

        # Encontrar data mais recente (comparando datetime, não string)
        last_update_dt = None
        last_update_str = ""

        for dem in demandas:
            updated = dem.get("updated_at") or dem.get("created_at", "")
            if updated:
                dt = self._to_local_dt(updated)
                if dt and (last_update_dt is None or dt > last_update_dt):
                    last_update_dt = dt
                    last_update_str = updated

        last_update_fmt = self._format_datetime(last_update_str)

        # Se apenas 1 demanda: mostrar tipo
        if total == 1:
            request_type = demandas[0].get("request_type", "")
            return request_type, last_update_fmt

        # Contar demandas em aberto
        open_count = sum(1 for dem in demandas if self._is_open_status(dem.get("status", "")))

        # Criar label resumido
        if open_count > 0:
            label = f"{total} demandas ({open_count} em aberto)"
        else:
            label = f"{total} demandas (finalizadas)"

        return label, last_update_fmt

    def _format_cnpj(self, value: object) -> str:
        """Formata CNPJ com máscara 00.000.000/0000-00.

        Args:
            value: CNPJ em qualquer formato (com ou sem máscara)

        Returns:
            CNPJ formatado ou valor original se inválido
        """
        if value is None:
            return ""
        raw = str(value)
        digits = re.sub(r"\D", "", raw)
        if len(digits) != 14:
            return raw
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"

    def _to_local_dt(self, dt_str: str):
        """Converte string ISO datetime UTC para datetime local.

        Args:
            dt_str: String ISO datetime (ex: "2025-12-19T22:41:00+00:00" ou "...Z")

        Returns:
            datetime object no timezone local ou None se falhar
        """
        if not dt_str:
            return None

        try:
            from datetime import datetime, timezone, timedelta

            # Normalizar Z para +00:00
            dt_str_clean = dt_str.replace("Z", "+00:00")

            # Parse ISO format
            dt = datetime.fromisoformat(dt_str_clean)

            # Se vier naive (sem timezone), assumir UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # Converter para timezone local (UTC-3 fixo para São Paulo)
            # Usando offset fixo para evitar dependência de zoneinfo
            local_tz = timezone(timedelta(hours=-3))
            dt_local = dt.astimezone(local_tz)

            return dt_local

        except Exception:
            log.exception(f"Erro ao converter timezone: {dt_str}")
            return None

    def _to_local_dt_from_utc(self, dt_utc: Any) -> Any:
        """Converte datetime UTC para timezone local (São Paulo).

        Args:
            dt_utc: datetime object em UTC

        Returns:
            datetime object no timezone local ou None se falhar
        """
        try:
            from datetime import timezone, timedelta

            # Timezone local (UTC-3 fixo para São Paulo)
            local_tz = timezone(timedelta(hours=-3))
            dt_local = dt_utc.astimezone(local_tz)

            return dt_local

        except Exception:
            log.exception("Erro ao converter UTC para local")
            return None

    def _format_datetime(self, dt_str: str) -> str:
        """Formata datetime ISO UTC para DD/MM/YYYY HH:MM no timezone local.

        Wrapper que delega para service.format_dt_local (fonte única de verdade).

        Args:
            dt_str: String de data/hora no formato ISO (ex: "2025-12-19T22:41:00+00:00")

        Returns:
            String formatada no timezone local ou string original se falhar
        """
        if not dt_str:
            return ""

        try:
            from datetime import timezone

            # Parse ISO string para datetime UTC
            dt_local = self._to_local_dt(dt_str)
            if dt_local:
                # Converter para UTC se não tiver timezone
                if dt_local.tzinfo is None:
                    dt_utc = dt_local.replace(tzinfo=timezone.utc)
                else:
                    dt_utc = dt_local.astimezone(timezone.utc)

                # Usar service como fonte única
                return self._service.format_dt_local(dt_utc)

            return ""

        except Exception:
            log.exception(f"Erro ao formatar datetime: {dt_str}")
            return ""

    def _persist_request_cloud(self, request: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Persiste demanda ANVISA no Supabase.

        Args:
            request: Dict com dados da demanda (client_id, request_type, status)

        Returns:
            Dict com registro criado se sucesso, None caso contrário
        """
        org_id = self._resolve_org_id()
        if not org_id:
            return None

        try:
            # Converter client_id para int (BIGINT no DB)
            client_id_int = int(request["client_id"])
            request_type = request["request_type"]
            status = request.get("status", DEFAULT_CREATE_STATUS)

            log.info(f"[ANVISA] Inserindo no Supabase: client_id={client_id_int}, tipo={request_type}")

            created = self._get_requests_controller().create_request(
                org_id=org_id,
                client_id=client_id_int,
                request_type=request_type,
                status=status,
            )

            log.info(f"[ANVISA] Demanda criada no Supabase: id={created.get('id')}")
            return created

        except Exception as e:
            log.exception("Erro ao persistir demanda no Supabase")
            messagebox.showerror(
                "Erro ao Salvar",
                f"Não foi possível salvar demanda no Supabase.\n\nDetalhes: {e}",
            )
            return None

    def _append_request_row(self, client_data: dict[str, Any], request_type: str) -> None:
        """Adiciona linha na Treeview com nova demanda ANVISA.

        Args:
            client_data: Dict com dados do cliente
            request_type: Tipo da demanda
        """
        client_id = str(client_data.get("id", ""))
        razao = client_data.get("razao_social", "")
        cnpj = client_data.get("cnpj", "")

        # Data/hora atual formatada via service
        from datetime import datetime, timezone

        now_utc = datetime.now(timezone.utc)
        updated_at_fmt = self._service.format_dt_local(now_utc)

        # Inserir na Treeview (sem iid pois não temos request_id ainda)
        # Será atualizado no próximo refresh
        item_id = self.tree_requests.insert(  # type: ignore[attr-defined]
            "",
            "end",
            values=[client_id, razao, cnpj, request_type, updated_at_fmt],
        )

        # Selecionar a linha recém-criada
        self.tree_requests.selection_set(item_id)  # type: ignore[attr-defined]

        log.info(f"[ANVISA] Linha adicionada na Treeview: {client_id} - {razao}")

    def _render_history(self, demandas: list[dict[str, Any]]) -> None:
        """Método mantido por compatibilidade. Histórico agora é popup.

        Args:
            demandas: Lista de demandas (ignorado)
        """
        pass

    def _clear_history(self) -> None:
        """Método mantido por compatibilidade. Histórico agora é popup."""
        pass
