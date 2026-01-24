# -*- coding: utf-8 -*-
"""Serviço de tarefas assíncronas do Hub.

MF-31: Extrai lógica assíncrona de carregamento de dados do HubScreenController,
mantendo o controller como orquestrador fino.

MF-32: Service focado em decisão de cenários; toda renderização UI na view.

MF-33: Service usa helpers de formatação de notas e cache de autores,
sem duplicar regras de apresentação.

Responsabilidades:
- Carregar dados do dashboard via ViewModel
- Carregar dados de notas via ViewModel
- Atualizar cache de autores usando helpers dedicados
- Executar em background via HubAsyncRunner
- Decidir cenário (erro/vazio/dados) e delegar renderização para view
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

# ORG-003: Helpers consolidados em hub/helpers/
from src.modules.hub.helpers.notes import (
    bulk_update_author_cache,
    should_refresh_author_cache,
)

if TYPE_CHECKING:
    from src.modules.hub.hub_screen_controller import HubScreenController

logger = logging.getLogger(__name__)


def load_dashboard_data_async(controller: "HubScreenController") -> None:
    """Carrega dados do dashboard de forma assíncrona via DashboardViewModel.

    MF-31: Extraído de HubScreenController.load_dashboard_data_async.

    Args:
        controller: HubScreenController com acesso a state, VM, async_runner, view
    """
    # Sincronizar org_id do state (pode vir do auth)
    # MF-15-B: view pode ser HubScreen (duck typing), que tem _get_org_id_safe()
    if hasattr(controller.view, "_get_org_id_safe"):
        controller.state.org_id = controller.view._get_org_id_safe()  # type: ignore

    org_id = controller.state.org_id
    if not org_id:
        controller.logger.debug("org_id não disponível, aguardando para carregar dashboard...")
        # Mostrar mensagem de aguardando autenticação no dashboard
        try:
            if hasattr(controller.view, "_dashboard_view") and controller.view._dashboard_view:
                # Criar uma mensagem temporária
                import tkinter as tk

                dashboard_view = controller.view._dashboard_view
                if dashboard_view.dashboard_scroll:
                    for widget in dashboard_view.dashboard_scroll.content.winfo_children():
                        widget.destroy()
                    waiting_label = tk.Label(
                        dashboard_view.dashboard_scroll.content,
                        text="Aguardando autenticação...",
                        font=("Segoe UI", 12),
                    )
                    waiting_label.pack(pady=50)
        except Exception as e:
            controller.logger.debug(f"Erro ao mostrar mensagem de aguardo: {e}")
        return

    def on_success(state: Any) -> None:  # DashboardViewState
        """Atualiza UI com estado de sucesso."""
        _update_dashboard_ui_from_state(controller, state)

    def on_error(exc: Exception) -> None:
        """Atualiza UI com estado de erro."""
        controller.logger.error(f"Erro ao carregar dashboard: {exc}")
        error_state = controller.dashboard_vm.from_error(
            "Não foi possível carregar o dashboard. Tente novamente mais tarde."
        )
        _update_dashboard_ui_from_state(controller, error_state)

    # Executar carregamento em background via HubAsyncRunner
    controller.async_runner.run(
        func=lambda: controller.dashboard_vm.load(org_id=org_id, today=None),
        on_success=on_success,
        on_error=on_error,
    )


def _update_dashboard_ui_from_state(controller: "HubScreenController", state: Any) -> None:
    """Atualiza a UI do dashboard baseado no estado do ViewModel.

    MF-31: Helper interno extraído de HubScreenController._update_dashboard_ui_from_state.
    MF-32: Service decide cenário (erro/vazio/dados); view renderiza UI.

    Args:
        controller: HubScreenController com acesso a view, state, logger
        state: DashboardViewState com snapshot e cards formatados
    """
    controller.logger.debug(
        f"[HUB] Atualizando dashboard UI - Erro: {bool(state.error_message)}, Snapshot: {bool(state.snapshot)}"
    )

    # Decisão: cenário de erro
    if state.error_message:
        controller.logger.error(f"Dashboard em estado de erro: {state.error_message}")
        controller.view.update_dashboard(state)  # View decide como renderizar erro
        return

    # Decisão: cenário vazio/inválido
    if not state.snapshot:
        controller.logger.warning("Dashboard sem snapshot disponível")
        # Criar estado de erro para exibir mensagem ao usuário
        error_state = controller.dashboard_vm.from_error(
            "Não foi possível carregar dados do dashboard. Verifique sua conexão e tente novamente."
        )
        controller.view.update_dashboard(error_state)
        return

    # Decisão: cenário com dados
    controller.view.update_dashboard(state)  # View renderiza dados
    controller.state.is_dashboard_loaded = True
    controller.logger.debug("Dashboard UI atualizado com sucesso")


def load_notes_data_async(controller: "HubScreenController") -> None:
    """Carrega dados de notas de forma assíncrona via NotesViewModel.

    MF-31: Extraído de HubScreenController.load_notes_data_async.

    Args:
        controller: HubScreenController com acesso a state, VM, async_runner, view
    """
    # Sincronizar org_id do state
    if hasattr(controller.view, "_get_org_id_safe"):
        controller.state.org_id = controller.view._get_org_id_safe()  # type: ignore

    org_id = controller.state.org_id
    if not org_id:
        controller.logger.debug("org_id não disponível, aguardando para carregar notas...")
        return

    def on_success(state: Any) -> None:
        """Atualiza UI com estado de sucesso."""
        _update_notes_ui_from_state(controller, state)

    def on_error(exc: Exception) -> None:
        """Atualiza UI com estado de erro."""
        controller.logger.error(f"Erro ao carregar notas: {exc}")
        # Renderizar estado de erro na view
        try:
            if hasattr(controller.view, "_notes_view") and controller.view._notes_view:
                controller.view._notes_view.render_error("Erro ao carregar notas. Tente novamente mais tarde.")
        except Exception as render_exc:
            controller.logger.error(f"Erro ao renderizar erro de notas: {render_exc}")

    # Executar carregamento em background via HubAsyncRunner
    controller.async_runner.run(
        func=lambda: controller.notes_vm.load(
            org_id=org_id,
            author_names_cache=controller.state.cached_authors,
        ),
        on_success=on_success,
        on_error=on_error,
    )


def _update_notes_ui_from_state(controller: "HubScreenController", state: Any) -> None:
    """Atualiza a UI de notas baseado no estado do ViewModel.

    MF-31: Helper interno extraído de HubScreenController._update_notes_ui_from_state.

    Args:
        controller: HubScreenController com acesso a view, state, logger
        state: NotesViewState com lista de notas
    """
    # Se houver erro no estado, renderizar erro
    if hasattr(state, "error_message") and state.error_message:
        controller.logger.error(f"Erro no estado de notas: {state.error_message}")
        try:
            if hasattr(controller.view, "_notes_view") and controller.view._notes_view:
                controller.view._notes_view.render_error(state.error_message)
        except Exception as exc:
            controller.logger.error(f"Erro ao renderizar erro de notas: {exc}")
        return

    # Se houver notas, atualizar state e view
    if hasattr(state, "notes"):
        notes = state.notes
        controller.state.cached_notes = notes  # type: ignore[assignment]

        # Atualizar hash de conteúdo
        if notes:
            controller.state.update_notes_hash(notes)  # type: ignore[arg-type]

        # Renderizar via view (se view tiver método render_notes)
        try:
            if hasattr(controller.view, "render_notes"):
                if notes:  # Se há notas, renderizar
                    controller.view.render_notes(notes, force=False)  # type: ignore
                else:  # Se não há notas, mostrar mensagem de vazio
                    if hasattr(controller.view, "_notes_view") and controller.view._notes_view:
                        controller.view._notes_view.render_empty("Nenhuma anotação compartilhada ainda.")
        except Exception as exc:
            controller.logger.error(f"Erro ao renderizar notas: {exc}")

        controller.state.is_notes_loaded = True
        controller.logger.debug("Notes UI atualizado com sucesso")


def refresh_author_names_cache_async(controller: "HubScreenController", *, force: bool = False) -> None:
    """Atualiza cache de nomes de autores de forma assíncrona.

    MF-31: Extraído de HubScreenController.refresh_author_names_cache_async.
    MF-33: Usa helper should_refresh_author_cache para decisão de cooldown.

    Args:
        controller: HubScreenController com acesso a state, async_runner
        force: Se True, ignora cooldown
    """
    # MF-33: Usar helper para verificar se deve fazer refresh
    if not force:
        now_ts = time.time()
        # Usar last_author_cache_refresh do state (já existe)
        last_refresh_ts = controller.state.last_author_cache_refresh

        if not should_refresh_author_cache(
            last_refresh_ts=last_refresh_ts,
            now_ts=now_ts,
            cooldown_seconds=300.0,  # 5 minutos
        ):
            return

    if controller.state.names_refreshing:
        return

    # Sincronizar org_id
    if hasattr(controller.view, "_get_org_id_safe"):
        controller.state.org_id = controller.view._get_org_id_safe()  # type: ignore

    org_id = controller.state.org_id
    if not org_id:
        return

    controller.state.names_refreshing = True

    def on_success(authors_map: dict[str, str]) -> None:
        """Callback de sucesso - usa helper para atualizar cache."""
        now_ts = time.time()

        # MF-33: Usar helper bulk_update_author_cache
        # Converter cached_authors para formato AuthorCache (dict[str, tuple[str, float]])
        # ORG-003: Helper movido para hub/helpers/
        from src.modules.hub.helpers.notes import AuthorCache

        # Se cached_authors for dict[str, str], converter para AuthorCache
        cache: AuthorCache = {}
        for email, value in controller.state.cached_authors.items():
            if isinstance(value, tuple):
                cache[email] = value
            else:
                cache[email] = (str(value), now_ts)

        # Atualizar cache usando helper
        bulk_update_author_cache(
            cache=cache,
            authors_map=authors_map,
            now_ts=now_ts,
        )

        # Escrever de volta ao state (mantém formato original por compatibilidade)
        controller.state.cached_authors = {k: v[0] for k, v in cache.items()}

        controller.state.mark_authors_refresh()
        controller.state.names_refreshing = False
        controller.logger.debug(f"Author names cache atualizado ({len(authors_map)} autores)")

    def on_error(exc: Exception) -> None:
        """Callback de erro."""
        controller.logger.error(f"Erro ao atualizar cache de autores: {exc}")
        controller.state.names_refreshing = False

    # MF-15-C: Buscar autores ausentes via NotesViewModel
    # Identificar emails cujos nomes estão faltando
    missing_emails: list[str] = []
    for email, value in controller.state.cached_authors.items():
        # Se value é string simples (não tupla), o nome está ausente
        if isinstance(value, str):
            missing_emails.append(email)

    # Se não há emails ou notes_vm, executar callback imediatamente
    if not missing_emails or not hasattr(controller, "notes_vm"):
        on_success({})
        return

    # Buscar via NotesViewModel em thread separada
    def _fetch_missing_authors() -> None:
        """Thread target: busca nomes de autores ausentes."""
        try:
            authors_map = controller.notes_vm.fetch_missing_authors(missing_emails)
            controller.view.after(0, lambda: on_success(authors_map))
        except Exception as exc:
            # Capturar exceção para usar no lambda (closure)
            error = exc
            controller.view.after(0, lambda: on_error(error))

    import threading

    thread = threading.Thread(target=_fetch_missing_authors, daemon=True, name="AuthorCacheRefresh")
    thread.start()
