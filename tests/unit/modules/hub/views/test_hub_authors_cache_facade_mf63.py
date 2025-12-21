# -*- coding: utf-8 -*-
"""MF-63: Testes headless para hub_authors_cache_facade.py.

Testa HubAuthorsCacheFacade com mocks, sem dependências reais.
Meta: 100% coverage (statements + branches).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_polling_service() -> MagicMock:
    """Serviço de polling mock."""
    return MagicMock()


@pytest.fixture
def mock_state_manager() -> MagicMock:
    """State manager mock."""
    return MagicMock()


@pytest.fixture
def mock_get_org_id() -> MagicMock:
    """Callback get_org_id mock."""
    callback = MagicMock()
    callback.return_value = "org-123"
    return callback


@pytest.fixture
def mock_auth_ready() -> MagicMock:
    """Callback auth_ready mock."""
    callback = MagicMock()
    callback.return_value = True
    return callback


@pytest.fixture
def facade_no_debug(
    mock_polling_service: MagicMock,
    mock_state_manager: MagicMock,
    mock_get_org_id: MagicMock,
    mock_auth_ready: MagicMock,
) -> Any:
    """Facade sem debug_logger."""
    from src.modules.hub.views.hub_authors_cache_facade import HubAuthorsCacheFacade

    return HubAuthorsCacheFacade(
        polling_service=mock_polling_service,
        state_manager=mock_state_manager,
        get_org_id=mock_get_org_id,
        auth_ready_callback=mock_auth_ready,
        debug_logger=None,
    )


@pytest.fixture
def facade_with_debug(
    mock_polling_service: MagicMock,
    mock_state_manager: MagicMock,
    mock_get_org_id: MagicMock,
    mock_auth_ready: MagicMock,
) -> tuple[Any, MagicMock]:
    """Facade com debug_logger, retorna (facade, debug_logger_mock)."""
    from src.modules.hub.views.hub_authors_cache_facade import HubAuthorsCacheFacade

    debug_logger = MagicMock()
    facade = HubAuthorsCacheFacade(
        polling_service=mock_polling_service,
        state_manager=mock_state_manager,
        get_org_id=mock_get_org_id,
        auth_ready_callback=mock_auth_ready,
        debug_logger=debug_logger,
    )
    return facade, debug_logger


# =============================================================================
# TEST: __init__
# =============================================================================


class TestInit:
    """Testes de inicialização."""

    def test_init_stores_dependencies(
        self,
        mock_polling_service: MagicMock,
        mock_state_manager: MagicMock,
        mock_get_org_id: MagicMock,
        mock_auth_ready: MagicMock,
    ) -> None:
        """__init__ armazena todas as dependências corretamente."""
        from src.modules.hub.views.hub_authors_cache_facade import HubAuthorsCacheFacade

        debug_logger = MagicMock()
        facade = HubAuthorsCacheFacade(
            polling_service=mock_polling_service,
            state_manager=mock_state_manager,
            get_org_id=mock_get_org_id,
            auth_ready_callback=mock_auth_ready,
            debug_logger=debug_logger,
        )

        assert facade._polling_service is mock_polling_service
        assert facade._state_manager is mock_state_manager
        assert facade._get_org_id is mock_get_org_id
        assert facade._auth_ready_callback is mock_auth_ready
        assert facade._debug_logger is debug_logger

    def test_init_with_none_debug_logger(
        self,
        mock_polling_service: MagicMock,
        mock_state_manager: MagicMock,
        mock_get_org_id: MagicMock,
        mock_auth_ready: MagicMock,
    ) -> None:
        """__init__ aceita debug_logger=None."""
        from src.modules.hub.views.hub_authors_cache_facade import HubAuthorsCacheFacade

        facade = HubAuthorsCacheFacade(
            polling_service=mock_polling_service,
            state_manager=mock_state_manager,
            get_org_id=mock_get_org_id,
            auth_ready_callback=mock_auth_ready,
            debug_logger=None,
        )

        assert facade._debug_logger is None


# =============================================================================
# TEST: refresh_author_names_cache (sem debug)
# =============================================================================


class TestRefreshAuthorNamesCacheNoDebug:
    """Testes de refresh_author_names_cache sem debug_logger."""

    def test_refresh_calls_polling_service_with_force_false(
        self, facade_no_debug: Any, mock_polling_service: MagicMock
    ) -> None:
        """refresh_author_names_cache() chama polling_service.refresh_authors_cache(force=False)."""
        facade_no_debug.refresh_author_names_cache(force=False)

        mock_polling_service.refresh_authors_cache.assert_called_once_with(force=False)

    def test_refresh_calls_polling_service_with_force_true(
        self, facade_no_debug: Any, mock_polling_service: MagicMock
    ) -> None:
        """refresh_author_names_cache(force=True) chama polling_service com force=True."""
        facade_no_debug.refresh_author_names_cache(force=True)

        mock_polling_service.refresh_authors_cache.assert_called_once_with(force=True)

    def test_refresh_default_force_is_false(self, facade_no_debug: Any, mock_polling_service: MagicMock) -> None:
        """refresh_author_names_cache() sem argumentos usa force=False."""
        facade_no_debug.refresh_author_names_cache()

        mock_polling_service.refresh_authors_cache.assert_called_once_with(force=False)

    def test_refresh_swallows_exception_and_logs(self, facade_no_debug: Any, mock_polling_service: MagicMock) -> None:
        """refresh_author_names_cache() engole exceção e loga."""
        mock_polling_service.refresh_authors_cache.side_effect = RuntimeError("Boom!")

        # Não deve propagar exceção
        facade_no_debug.refresh_author_names_cache()

        # Deve ter tentado chamar
        mock_polling_service.refresh_authors_cache.assert_called_once()


# =============================================================================
# TEST: refresh_author_names_cache (com debug)
# =============================================================================


class TestRefreshAuthorNamesCacheWithDebug:
    """Testes de refresh_author_names_cache com debug_logger."""

    def test_refresh_logs_to_debug_logger_on_success(
        self, facade_with_debug: tuple[Any, MagicMock], mock_polling_service: MagicMock
    ) -> None:
        """refresh_author_names_cache() loga no debug_logger em caso de sucesso."""
        facade, debug_logger = facade_with_debug

        facade.refresh_author_names_cache(force=True)

        # Verifica que debug_logger foi chamado pelo menos 1x
        assert debug_logger.call_count >= 1
        # Verifica conteúdo (contains force=True)
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("force=True" in args for args in call_args_list)

        # Verifica que polling_service foi chamado
        mock_polling_service.refresh_authors_cache.assert_called_once_with(force=True)

    def test_refresh_logs_to_debug_logger_on_exception(
        self, facade_with_debug: tuple[Any, MagicMock], mock_polling_service: MagicMock
    ) -> None:
        """refresh_author_names_cache() loga exceção no debug_logger."""
        facade, debug_logger = facade_with_debug
        mock_polling_service.refresh_authors_cache.side_effect = RuntimeError("Test error")

        facade.refresh_author_names_cache()

        # Debug_logger deve ter sido chamado (com mensagem de erro)
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("Erro" in args or "erro" in args for args in call_args_list)


# =============================================================================
# TEST: clear_author_cache (sem debug)
# =============================================================================


class TestClearAuthorCacheNoDebug:
    """Testes de clear_author_cache sem debug_logger."""

    def test_clear_calls_state_manager(self, facade_no_debug: Any, mock_state_manager: MagicMock) -> None:
        """clear_author_cache() chama state_manager.clear_author_cache()."""
        facade_no_debug.clear_author_cache()

        mock_state_manager.clear_author_cache.assert_called_once()

    def test_clear_swallows_exception_and_logs(self, facade_no_debug: Any, mock_state_manager: MagicMock) -> None:
        """clear_author_cache() engole exceção e loga."""
        mock_state_manager.clear_author_cache.side_effect = RuntimeError("Boom!")

        # Não deve propagar exceção
        facade_no_debug.clear_author_cache()

        # Deve ter tentado chamar
        mock_state_manager.clear_author_cache.assert_called_once()


# =============================================================================
# TEST: clear_author_cache (com debug)
# =============================================================================


class TestClearAuthorCacheWithDebug:
    """Testes de clear_author_cache com debug_logger."""

    def test_clear_logs_to_debug_logger_on_success(
        self, facade_with_debug: tuple[Any, MagicMock], mock_state_manager: MagicMock
    ) -> None:
        """clear_author_cache() loga no debug_logger em caso de sucesso."""
        facade, debug_logger = facade_with_debug

        facade.clear_author_cache()

        # Verifica que debug_logger foi chamado
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("limpo" in args or "Cache" in args for args in call_args_list)

        # Verifica que state_manager foi chamado
        mock_state_manager.clear_author_cache.assert_called_once()

    def test_clear_logs_to_debug_logger_on_exception(
        self, facade_with_debug: tuple[Any, MagicMock], mock_state_manager: MagicMock
    ) -> None:
        """clear_author_cache() loga exceção no debug_logger."""
        facade, debug_logger = facade_with_debug
        mock_state_manager.clear_author_cache.side_effect = RuntimeError("Test error")

        facade.clear_author_cache()

        # Debug_logger deve ter sido chamado
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("Erro" in args or "erro" in args for args in call_args_list)


# =============================================================================
# TEST: add_pending_name_fetch (sem debug)
# =============================================================================


class TestAddPendingNameFetchNoDebug:
    """Testes de add_pending_name_fetch sem debug_logger."""

    def test_add_pending_calls_state_manager(self, facade_no_debug: Any, mock_state_manager: MagicMock) -> None:
        """add_pending_name_fetch() chama state_manager.add_pending_name_fetch()."""
        facade_no_debug.add_pending_name_fetch("user@example.com")

        mock_state_manager.add_pending_name_fetch.assert_called_once_with("user@example.com")

    def test_add_pending_swallows_exception_and_logs(self, facade_no_debug: Any, mock_state_manager: MagicMock) -> None:
        """add_pending_name_fetch() engole exceção e loga."""
        mock_state_manager.add_pending_name_fetch.side_effect = RuntimeError("Boom!")

        # Não deve propagar exceção
        facade_no_debug.add_pending_name_fetch("test@test.com")

        # Deve ter tentado chamar
        mock_state_manager.add_pending_name_fetch.assert_called_once_with("test@test.com")


# =============================================================================
# TEST: add_pending_name_fetch (com debug)
# =============================================================================


class TestAddPendingNameFetchWithDebug:
    """Testes de add_pending_name_fetch com debug_logger."""

    def test_add_pending_logs_to_debug_logger_on_success(
        self, facade_with_debug: tuple[Any, MagicMock], mock_state_manager: MagicMock
    ) -> None:
        """add_pending_name_fetch() loga no debug_logger em caso de sucesso."""
        facade, debug_logger = facade_with_debug

        facade.add_pending_name_fetch("user@example.com")

        # Verifica que debug_logger foi chamado
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("user@example.com" in args for args in call_args_list)

        # Verifica que state_manager foi chamado
        mock_state_manager.add_pending_name_fetch.assert_called_once_with("user@example.com")

    def test_add_pending_logs_to_debug_logger_on_exception(
        self, facade_with_debug: tuple[Any, MagicMock], mock_state_manager: MagicMock
    ) -> None:
        """add_pending_name_fetch() loga exceção no debug_logger."""
        facade, debug_logger = facade_with_debug
        mock_state_manager.add_pending_name_fetch.side_effect = RuntimeError("Test error")

        facade.add_pending_name_fetch("test@test.com")

        # Debug_logger deve ter sido chamado
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("Erro" in args or "erro" in args for args in call_args_list)


# =============================================================================
# TEST: remove_pending_name_fetch (sem debug)
# =============================================================================


class TestRemovePendingNameFetchNoDebug:
    """Testes de remove_pending_name_fetch sem debug_logger."""

    def test_remove_pending_calls_state_manager(self, facade_no_debug: Any, mock_state_manager: MagicMock) -> None:
        """remove_pending_name_fetch() chama state_manager.remove_pending_name_fetch()."""
        facade_no_debug.remove_pending_name_fetch("user@example.com")

        mock_state_manager.remove_pending_name_fetch.assert_called_once_with("user@example.com")

    def test_remove_pending_swallows_exception_and_logs(
        self, facade_no_debug: Any, mock_state_manager: MagicMock
    ) -> None:
        """remove_pending_name_fetch() engole exceção e loga."""
        mock_state_manager.remove_pending_name_fetch.side_effect = RuntimeError("Boom!")

        # Não deve propagar exceção
        facade_no_debug.remove_pending_name_fetch("test@test.com")

        # Deve ter tentado chamar
        mock_state_manager.remove_pending_name_fetch.assert_called_once_with("test@test.com")


# =============================================================================
# TEST: remove_pending_name_fetch (com debug)
# =============================================================================


class TestRemovePendingNameFetchWithDebug:
    """Testes de remove_pending_name_fetch com debug_logger."""

    def test_remove_pending_logs_to_debug_logger_on_success(
        self, facade_with_debug: tuple[Any, MagicMock], mock_state_manager: MagicMock
    ) -> None:
        """remove_pending_name_fetch() loga no debug_logger em caso de sucesso."""
        facade, debug_logger = facade_with_debug

        facade.remove_pending_name_fetch("user@example.com")

        # Verifica que debug_logger foi chamado
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("user@example.com" in args for args in call_args_list)

        # Verifica que state_manager foi chamado
        mock_state_manager.remove_pending_name_fetch.assert_called_once_with("user@example.com")

    def test_remove_pending_logs_to_debug_logger_on_exception(
        self, facade_with_debug: tuple[Any, MagicMock], mock_state_manager: MagicMock
    ) -> None:
        """remove_pending_name_fetch() loga exceção no debug_logger."""
        facade, debug_logger = facade_with_debug
        mock_state_manager.remove_pending_name_fetch.side_effect = RuntimeError("Test error")

        facade.remove_pending_name_fetch("test@test.com")

        # Debug_logger deve ter sido chamado
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("Erro" in args or "erro" in args for args in call_args_list)


# =============================================================================
# TEST: set_names_cache_loaded (sem debug)
# =============================================================================


class TestSetNamesCacheLoadedNoDebug:
    """Testes de set_names_cache_loaded sem debug_logger."""

    def test_set_loaded_true_calls_state_manager(self, facade_no_debug: Any, mock_state_manager: MagicMock) -> None:
        """set_names_cache_loaded(True) chama state_manager.set_names_cache_loaded(True)."""
        facade_no_debug.set_names_cache_loaded(True)

        mock_state_manager.set_names_cache_loaded.assert_called_once_with(True)

    def test_set_loaded_false_calls_state_manager(self, facade_no_debug: Any, mock_state_manager: MagicMock) -> None:
        """set_names_cache_loaded(False) chama state_manager.set_names_cache_loaded(False)."""
        facade_no_debug.set_names_cache_loaded(False)

        mock_state_manager.set_names_cache_loaded.assert_called_once_with(False)

    def test_set_loaded_swallows_exception_and_logs(self, facade_no_debug: Any, mock_state_manager: MagicMock) -> None:
        """set_names_cache_loaded() engole exceção e loga."""
        mock_state_manager.set_names_cache_loaded.side_effect = RuntimeError("Boom!")

        # Não deve propagar exceção
        facade_no_debug.set_names_cache_loaded(True)

        # Deve ter tentado chamar
        mock_state_manager.set_names_cache_loaded.assert_called_once_with(True)


# =============================================================================
# TEST: set_names_cache_loaded (com debug)
# =============================================================================


class TestSetNamesCacheLoadedWithDebug:
    """Testes de set_names_cache_loaded com debug_logger."""

    def test_set_loaded_logs_to_debug_logger_on_success(
        self, facade_with_debug: tuple[Any, MagicMock], mock_state_manager: MagicMock
    ) -> None:
        """set_names_cache_loaded() loga no debug_logger em caso de sucesso."""
        facade, debug_logger = facade_with_debug

        facade.set_names_cache_loaded(True)

        # Verifica que debug_logger foi chamado
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("True" in args or "carregado" in args for args in call_args_list)

        # Verifica que state_manager foi chamado
        mock_state_manager.set_names_cache_loaded.assert_called_once_with(True)

    def test_set_loaded_logs_to_debug_logger_on_exception(
        self, facade_with_debug: tuple[Any, MagicMock], mock_state_manager: MagicMock
    ) -> None:
        """set_names_cache_loaded() loga exceção no debug_logger."""
        facade, debug_logger = facade_with_debug
        mock_state_manager.set_names_cache_loaded.side_effect = RuntimeError("Test error")

        facade.set_names_cache_loaded(False)

        # Debug_logger deve ter sido chamado
        assert debug_logger.call_count >= 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("Erro" in args or "erro" in args for args in call_args_list)


# =============================================================================
# TEST: _log_debug
# =============================================================================


class TestLogDebugPrivateMethod:
    """Testes do método privado _log_debug."""

    def test_log_debug_with_debug_logger_calls_it(self, facade_with_debug: tuple[Any, MagicMock]) -> None:
        """_log_debug() chama debug_logger quando ele existe."""
        facade, debug_logger = facade_with_debug

        facade._log_debug("Test message")

        # Debug_logger deve ter sido chamado
        assert debug_logger.call_count == 1
        call_args_list = [str(c) for c in debug_logger.call_args_list]
        assert any("Test message" in args for args in call_args_list)

    def test_log_debug_without_debug_logger_does_not_crash(self, facade_no_debug: Any) -> None:
        """_log_debug() não explode quando debug_logger é None."""
        # Não deve lançar exceção
        facade_no_debug._log_debug("Test message")
