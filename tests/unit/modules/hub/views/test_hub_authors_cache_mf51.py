# -*- coding: utf-8 -*-
"""
MF-51: Testes para hub_authors_cache.py (100% coverage).

Testa:
- should_skip_refresh_by_cooldown (todos os branches)
- refresh_author_names_cache (happy path, cooldown, reentrância, mudança de org)
- calculate_cache_hash (hash SHA256)
- Logger fallback
"""

from __future__ import annotations

import hashlib
import json
import time
from unittest.mock import MagicMock, patch


class TestShouldSkipRefreshByCooldown:
    """Testes para should_skip_refresh_by_cooldown."""

    def test_skip_refresh_force_true(self):
        """Testa que force=True nunca pula refresh."""
        from src.modules.hub.views.hub_authors_cache import (
            should_skip_refresh_by_cooldown,
        )

        # Mesmo com cooldown ativo, force=True retorna False (não pula)
        result = should_skip_refresh_by_cooldown(
            last_refresh=time.time() - 1,  # 1 segundo atrás
            cooldown_seconds=30,
            force=True,
        )
        assert result is False

    def test_skip_refresh_last_refresh_none(self):
        """Testa que last_refresh=None não pula refresh."""
        from src.modules.hub.views.hub_authors_cache import (
            should_skip_refresh_by_cooldown,
        )

        result = should_skip_refresh_by_cooldown(
            last_refresh=None,
            cooldown_seconds=30,
            force=False,
        )
        assert result is False

    def test_skip_refresh_cooldown_active(self):
        """Testa que cooldown ativo pula refresh."""
        from src.modules.hub.views.hub_authors_cache import (
            should_skip_refresh_by_cooldown,
        )

        # 1 segundo atrás, cooldown de 30 segundos -> deve pular
        result = should_skip_refresh_by_cooldown(
            last_refresh=time.time() - 1,
            cooldown_seconds=30,
            force=False,
        )
        assert result is True

    def test_skip_refresh_cooldown_expired(self):
        """Testa que cooldown expirado não pula refresh."""
        from src.modules.hub.views.hub_authors_cache import (
            should_skip_refresh_by_cooldown,
        )

        # 31 segundos atrás, cooldown de 30 segundos -> não pula
        result = should_skip_refresh_by_cooldown(
            last_refresh=time.time() - 31,
            cooldown_seconds=30,
            force=False,
        )
        assert result is False


class TestRefreshAuthorNamesCache:
    """Testes para refresh_author_names_cache."""

    def test_refresh_author_names_cache_success(self):
        """Testa refresh bem-sucedido com carregamento de nomes."""
        from src.modules.hub.views.hub_authors_cache import (
            refresh_author_names_cache,
        )

        # Mock do async_runner
        mock_async_runner = MagicMock()

        # Capturar callbacks
        captured_func = None
        captured_on_success = None
        captured_on_error = None

        def capture_run(func, on_success, on_error):
            nonlocal captured_func, captured_on_success, captured_on_error
            captured_func = func
            captured_on_success = on_success
            captured_on_error = on_error

        mock_async_runner.run.side_effect = capture_run

        # Mock dos callbacks
        mock_on_cache_updated = MagicMock()
        mock_on_start_refresh = MagicMock()
        mock_on_end_refresh = MagicMock()

        # Executar refresh
        result = refresh_author_names_cache(
            org_id="org123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,
            last_org_id=None,
            is_refreshing=False,
            force=False,
            on_cache_updated=mock_on_cache_updated,
            on_start_refresh=mock_on_start_refresh,
            on_end_refresh=mock_on_end_refresh,
        )

        # Deve ter iniciado refresh
        assert result is True
        mock_on_start_refresh.assert_called_once()
        mock_async_runner.run.assert_called_once()

        # Simular execução da função de carregamento
        with (
            patch("src.core.services.profiles_service.get_display_names_map") as mock_get_names,
            patch("src.core.services.profiles_service.get_email_prefix_map") as mock_get_prefix,
        ):
            mock_get_names.return_value = {"user1": "John Doe"}
            mock_get_prefix.return_value = {"user1": "john"}

            # Executar load_names
            assert captured_func is not None
            mapping, prefix_map = captured_func()  # type: ignore[misc]
            assert mapping == {"user1": "John Doe"}
            assert prefix_map == {"user1": "john"}

            # Executar on_success
            assert captured_on_success is not None
            captured_on_success((mapping, prefix_map))

            # Verificar que cache foi atualizado
            mock_on_cache_updated.assert_called_once()
            args = mock_on_cache_updated.call_args[0]
            assert args[0] == {"user1": "John Doe"}
            assert args[1] == {"user1": "john"}
            assert isinstance(args[2], str)  # hash

            mock_on_end_refresh.assert_called_once()

    def test_refresh_author_names_cache_is_refreshing(self):
        """Testa que refresh não ocorre se já está em progresso."""
        from src.modules.hub.views.hub_authors_cache import (
            refresh_author_names_cache,
        )

        mock_async_runner = MagicMock()

        result = refresh_author_names_cache(
            org_id="org123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,
            last_org_id=None,
            is_refreshing=True,  # Já está em progresso
            force=False,
            on_cache_updated=MagicMock(),
            on_start_refresh=MagicMock(),
            on_end_refresh=MagicMock(),
        )

        # Deve ter pulado refresh
        assert result is False
        mock_async_runner.run.assert_not_called()

    def test_refresh_author_names_cache_is_refreshing_force(self):
        """Testa que force=True ignora is_refreshing."""
        from src.modules.hub.views.hub_authors_cache import (
            refresh_author_names_cache,
        )

        mock_async_runner = MagicMock()
        mock_on_start_refresh = MagicMock()

        result = refresh_author_names_cache(
            org_id="org123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,
            last_org_id=None,
            is_refreshing=True,  # Já está em progresso
            force=True,  # Mas force=True
            on_cache_updated=MagicMock(),
            on_start_refresh=mock_on_start_refresh,
            on_end_refresh=MagicMock(),
        )

        # Deve ter iniciado refresh (force ignora is_refreshing)
        assert result is True
        mock_async_runner.run.assert_called_once()
        mock_on_start_refresh.assert_called_once()

    def test_refresh_author_names_cache_cooldown_active(self):
        """Testa que cooldown ativo impede refresh."""
        from src.modules.hub.views.hub_authors_cache import (
            refresh_author_names_cache,
        )

        mock_async_runner = MagicMock()

        result = refresh_author_names_cache(
            org_id="org123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=time.time() - 1,  # 1 segundo atrás (cooldown ativo)
            last_org_id="org123",
            is_refreshing=False,
            force=False,
            on_cache_updated=MagicMock(),
            on_start_refresh=MagicMock(),
            on_end_refresh=MagicMock(),
        )

        # Deve ter pulado refresh
        assert result is False
        mock_async_runner.run.assert_not_called()

    def test_refresh_author_names_cache_org_changed(self):
        """Testa que mudança de organização é detectada."""
        from src.modules.hub.views.hub_authors_cache import (
            refresh_author_names_cache,
        )

        mock_async_runner = MagicMock()
        mock_on_start_refresh = MagicMock()

        with patch("src.modules.hub.views.hub_authors_cache.logger") as mock_logger:
            result = refresh_author_names_cache(
                org_id="org456",  # Nova org
                async_runner=mock_async_runner,
                _current_cache={},
                _current_prefix_map={},
                last_refresh=None,
                last_org_id="org123",  # Org anterior diferente
                is_refreshing=False,
                force=False,
                on_cache_updated=MagicMock(),
                on_start_refresh=mock_on_start_refresh,
                on_end_refresh=MagicMock(),
            )

            # Deve ter iniciado refresh e logado mudança
            assert result is True
            mock_logger.info.assert_called_once()
            assert "mudança de organização" in mock_logger.info.call_args[0][0].lower()

    def test_refresh_author_names_cache_load_names_error(self):
        """Testa tratamento de erro no carregamento de nomes."""
        from src.modules.hub.views.hub_authors_cache import (
            refresh_author_names_cache,
        )

        mock_async_runner = MagicMock()

        captured_func = None
        captured_on_error = None

        def capture_run(func, on_success, on_error):
            nonlocal captured_func, captured_on_error
            captured_func = func
            captured_on_error = on_error

        mock_async_runner.run.side_effect = capture_run

        mock_on_end_refresh = MagicMock()

        result = refresh_author_names_cache(
            org_id="org123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,
            last_org_id=None,
            is_refreshing=False,
            force=False,
            on_cache_updated=MagicMock(),
            on_start_refresh=MagicMock(),
            on_end_refresh=mock_on_end_refresh,
        )

        assert result is True

        # Simular erro no carregamento
        with patch("src.core.services.profiles_service.get_display_names_map") as mock_get_names:
            mock_get_names.side_effect = RuntimeError("Database error")

            # Executar load_names (deve retornar dicts vazios)
            assert captured_func is not None
            mapping, prefix_map = captured_func()  # type: ignore[misc]
            assert mapping == {}
            assert prefix_map == {}

        # Simular erro no callback
        test_error = RuntimeError("Async error")
        assert captured_on_error is not None
        captured_on_error(test_error)
        mock_on_end_refresh.assert_called_once()

    def test_refresh_author_names_cache_empty_results(self):
        """Testa carregamento com resultados vazios."""
        from src.modules.hub.views.hub_authors_cache import (
            refresh_author_names_cache,
        )

        mock_async_runner = MagicMock()

        captured_func = None
        captured_on_success = None

        def capture_run(func, on_success, on_error):
            nonlocal captured_func, captured_on_success
            captured_func = func
            captured_on_success = on_success

        mock_async_runner.run.side_effect = capture_run

        mock_on_cache_updated = MagicMock()
        mock_on_end_refresh = MagicMock()

        result = refresh_author_names_cache(
            org_id="org123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,
            last_org_id=None,
            is_refreshing=False,
            force=False,
            on_cache_updated=mock_on_cache_updated,
            on_start_refresh=MagicMock(),
            on_end_refresh=mock_on_end_refresh,
        )

        assert result is True

        # Simular carregamento vazio
        with (
            patch("src.core.services.profiles_service.get_display_names_map") as mock_get_names,
            patch("src.core.services.profiles_service.get_email_prefix_map") as mock_get_prefix,
        ):
            mock_get_names.return_value = {}
            mock_get_prefix.return_value = {}

            assert captured_func is not None
            mapping, prefix_map = captured_func()  # type: ignore[misc]
            assert captured_on_success is not None
            captured_on_success((mapping, prefix_map))

            # Cache atualizado com valores vazios
            mock_on_cache_updated.assert_called_once()
            args = mock_on_cache_updated.call_args[0]
            assert args[0] == {}
            assert args[1] == {}

    def test_refresh_author_names_cache_none_results(self):
        """Testa carregamento com resultados None."""
        from src.modules.hub.views.hub_authors_cache import (
            refresh_author_names_cache,
        )

        mock_async_runner = MagicMock()

        captured_func = None

        def capture_run(func, on_success, on_error):
            nonlocal captured_func
            captured_func = func

        mock_async_runner.run.side_effect = capture_run

        result = refresh_author_names_cache(
            org_id="org123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,
            last_org_id=None,
            is_refreshing=False,
            force=False,
            on_cache_updated=MagicMock(),
            on_start_refresh=MagicMock(),
            on_end_refresh=MagicMock(),
        )

        assert result is True

        # Simular retorno None (tratado como {})
        with (
            patch("src.core.services.profiles_service.get_display_names_map") as mock_get_names,
            patch("src.core.services.profiles_service.get_email_prefix_map") as mock_get_prefix,
        ):
            mock_get_names.return_value = None
            mock_get_prefix.return_value = None

            assert captured_func is not None
            mapping, prefix_map = captured_func()  # type: ignore[misc]
            assert mapping == {}
            assert prefix_map == {}


class TestCalculateCacheHash:
    """Testes para calculate_cache_hash."""

    def test_calculate_cache_hash_empty(self):
        """Testa hash de cache vazio."""
        from src.modules.hub.views.hub_authors_cache import calculate_cache_hash

        result = calculate_cache_hash({})

        # Hash esperado de "{}"
        expected = hashlib.sha256(json.dumps({}, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        assert result == expected
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex = 64 chars

    def test_calculate_cache_hash_single_entry(self):
        """Testa hash de cache com uma entrada."""
        from src.modules.hub.views.hub_authors_cache import calculate_cache_hash

        cache = {"user1": "John Doe"}
        result = calculate_cache_hash(cache)

        expected = hashlib.sha256(json.dumps(cache, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        assert result == expected

    def test_calculate_cache_hash_multiple_entries(self):
        """Testa hash de cache com múltiplas entradas."""
        from src.modules.hub.views.hub_authors_cache import calculate_cache_hash

        cache = {
            "user1": "John Doe",
            "user2": "Jane Smith",
            "user3": "Bob Johnson",
        }
        result = calculate_cache_hash(cache)

        expected = hashlib.sha256(json.dumps(cache, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        assert result == expected

    def test_calculate_cache_hash_unicode(self):
        """Testa hash de cache com caracteres Unicode."""
        from src.modules.hub.views.hub_authors_cache import calculate_cache_hash

        cache = {
            "user1": "João da Silva",
            "user2": "Marie Curie",
            "user3": "李明",
        }
        result = calculate_cache_hash(cache)

        expected = hashlib.sha256(json.dumps(cache, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        assert result == expected

    def test_calculate_cache_hash_deterministic(self):
        """Testa que hash é determinístico (mesma entrada = mesmo hash)."""
        from src.modules.hub.views.hub_authors_cache import calculate_cache_hash

        cache = {"user1": "John", "user2": "Jane"}

        hash1 = calculate_cache_hash(cache)
        hash2 = calculate_cache_hash(cache)

        assert hash1 == hash2

    def test_calculate_cache_hash_order_independent(self):
        """Testa que ordem das chaves não afeta hash (sort_keys=True)."""
        from src.modules.hub.views.hub_authors_cache import calculate_cache_hash

        cache1 = {"user1": "John", "user2": "Jane"}
        cache2 = {"user2": "Jane", "user1": "John"}

        hash1 = calculate_cache_hash(cache1)
        hash2 = calculate_cache_hash(cache2)

        assert hash1 == hash2


class TestLoggerFallback:
    """Testes para fallback do logger."""

    def test_logger_fallback_on_import_error(self):
        """Testa que logger fallback funciona quando src.core.logger falha."""
        import sys
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "src.core.logger":
                raise ImportError("Mocked import error")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            # Remover do cache e reimportar
            if "src.modules.hub.views.hub_authors_cache" in sys.modules:
                del sys.modules["src.modules.hub.views.hub_authors_cache"]

            import src.modules.hub.views.hub_authors_cache as reloaded_module

            # Logger deve existir (fallback para logging padrão)
            assert hasattr(reloaded_module, "logger")
            assert reloaded_module.logger is not None

        # Restaurar módulo removendo e reimportando normalmente
        if "src.modules.hub.views.hub_authors_cache" in sys.modules:
            del sys.modules["src.modules.hub.views.hub_authors_cache"]
        import src.modules.hub.views.hub_authors_cache  # noqa: F401
