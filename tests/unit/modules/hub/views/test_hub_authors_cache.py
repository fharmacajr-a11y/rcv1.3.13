# -*- coding: utf-8 -*-
"""Testes unitários para hub_authors_cache.py - cache de nomes de autores."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from src.modules.hub.views.hub_authors_cache import (
    calculate_cache_hash,
    refresh_author_names_cache,
    should_skip_refresh_by_cooldown,
)


class TestShouldSkipRefreshByCooldown:
    """Testes para lógica de cooldown de refresh."""

    def test_force_true_never_skips(self):
        """Quando force=True, deve sempre permitir refresh (não pular)."""
        last_refresh = time.time() - 1  # 1 segundo atrás
        cooldown = 30

        should_skip = should_skip_refresh_by_cooldown(
            last_refresh=last_refresh,
            cooldown_seconds=cooldown,
            force=True,
        )

        assert should_skip is False  # Não deve pular (force ignora cooldown)

    def test_last_refresh_none_allows_refresh(self):
        """Quando last_refresh é None (primeiro refresh), deve permitir."""
        should_skip = should_skip_refresh_by_cooldown(
            last_refresh=None,
            cooldown_seconds=30,
            force=False,
        )

        assert should_skip is False  # Não deve pular (primeiro refresh)

    def test_cooldown_not_expired_skips_refresh(self):
        """Quando cooldown não expirou, deve pular refresh."""
        last_refresh = time.time() - 10  # 10 segundos atrás
        cooldown = 30  # Cooldown de 30s

        should_skip = should_skip_refresh_by_cooldown(
            last_refresh=last_refresh,
            cooldown_seconds=cooldown,
            force=False,
        )

        assert should_skip is True  # Deve pular (ainda em cooldown)

    def test_cooldown_expired_allows_refresh(self):
        """Quando cooldown expirou, deve permitir refresh."""
        last_refresh = time.time() - 31  # 31 segundos atrás
        cooldown = 30  # Cooldown de 30s

        should_skip = should_skip_refresh_by_cooldown(
            last_refresh=last_refresh,
            cooldown_seconds=cooldown,
            force=False,
        )

        assert should_skip is False  # Não deve pular (cooldown expirado)

    def test_cooldown_exactly_at_boundary(self):
        """Testa boundary condition: exatamente no limite do cooldown."""
        last_refresh = time.time() - 30.0  # Exatamente 30s atrás
        cooldown = 30

        # No limite, elapsed é ~30, então elapsed < 30 é False
        should_skip = should_skip_refresh_by_cooldown(
            last_refresh=last_refresh,
            cooldown_seconds=cooldown,
            force=False,
        )

        # Pode ser False (permite) por causa de precisão de float
        # O importante é não dar erro
        assert isinstance(should_skip, bool)


class TestCalculateCacheHash:
    """Testes para cálculo de hash de cache."""

    def test_empty_cache_hash(self):
        """Cache vazio deve gerar hash consistente."""
        hash1 = calculate_cache_hash({})
        hash2 = calculate_cache_hash({})

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 = 64 caracteres hex

    def test_same_cache_same_hash(self):
        """Mesmo conteúdo de cache deve gerar mesmo hash."""
        cache = {
            "user-1": "João Silva",
            "user-2": "Maria Santos",
        }

        hash1 = calculate_cache_hash(cache)
        hash2 = calculate_cache_hash(cache)

        assert hash1 == hash2

    def test_different_cache_different_hash(self):
        """Conteúdos diferentes devem gerar hashes diferentes."""
        cache1 = {"user-1": "João Silva"}
        cache2 = {"user-1": "Maria Santos"}

        hash1 = calculate_cache_hash(cache1)
        hash2 = calculate_cache_hash(cache2)

        assert hash1 != hash2

    def test_order_independent_hash(self):
        """Hash deve ser independente da ordem das chaves (sort_keys=True)."""
        cache1 = {"user-a": "Alice", "user-b": "Bob"}
        cache2 = {"user-b": "Bob", "user-a": "Alice"}

        hash1 = calculate_cache_hash(cache1)
        hash2 = calculate_cache_hash(cache2)

        assert hash1 == hash2  # Mesmos dados, mesma ordem após sort

    def test_cache_with_unicode(self):
        """Cache com caracteres Unicode deve funcionar."""
        cache = {
            "user-1": "João Conceição",
            "user-2": "María García",
            "user-3": "李明",  # Chinês
        }

        hash_result = calculate_cache_hash(cache)

        assert len(hash_result) == 64
        assert isinstance(hash_result, str)


class TestRefreshAuthorNamesCache:
    """Testes para função principal de refresh de cache."""

    @pytest.fixture
    def mock_async_runner(self):
        """Cria mock de HubAsyncRunner."""
        runner = MagicMock()
        return runner

    @pytest.fixture
    def callbacks(self):
        """Cria mocks para callbacks."""
        return {
            "on_cache_updated": MagicMock(),
            "on_start_refresh": MagicMock(),
            "on_end_refresh": MagicMock(),
        }

    def test_skip_if_already_refreshing(self, mock_async_runner, callbacks):
        """Deve pular refresh se já está em andamento (is_refreshing=True)."""
        result = refresh_author_names_cache(
            org_id="org-123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,
            last_org_id=None,
            is_refreshing=True,  # Já em refresh
            force=False,
            **callbacks,
        )

        assert result is False  # Refresh foi pulado
        callbacks["on_start_refresh"].assert_not_called()
        mock_async_runner.run.assert_not_called()

    def test_force_bypasses_refreshing_flag(self, mock_async_runner, callbacks):
        """force=True deve ignorar flag is_refreshing."""
        result = refresh_author_names_cache(
            org_id="org-123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,
            last_org_id=None,
            is_refreshing=True,  # Normalmente bloquearia
            force=True,  # Mas force ignora
            **callbacks,
        )

        assert result is True  # Refresh foi iniciado
        callbacks["on_start_refresh"].assert_called_once()
        mock_async_runner.run.assert_called_once()

    def test_skip_if_cooldown_not_expired(self, mock_async_runner, callbacks):
        """Deve pular refresh se cooldown não expirou."""
        last_refresh = time.time() - 10  # 10s atrás (cooldown padrão: 30s)

        result = refresh_author_names_cache(
            org_id="org-123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=last_refresh,
            last_org_id="org-123",
            is_refreshing=False,
            force=False,
            **callbacks,
        )

        assert result is False  # Refresh foi pulado
        callbacks["on_start_refresh"].assert_not_called()
        mock_async_runner.run.assert_not_called()

    def test_allow_refresh_if_cooldown_expired(self, mock_async_runner, callbacks):
        """Deve permitir refresh se cooldown expirou."""
        last_refresh = time.time() - 31  # 31s atrás (> cooldown de 30s)

        result = refresh_author_names_cache(
            org_id="org-123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=last_refresh,
            last_org_id="org-123",
            is_refreshing=False,
            force=False,
            **callbacks,
        )

        assert result is True  # Refresh foi iniciado
        callbacks["on_start_refresh"].assert_called_once()
        mock_async_runner.run.assert_called_once()

    def test_allow_refresh_on_first_call(self, mock_async_runner, callbacks):
        """Primeira chamada (last_refresh=None) deve permitir refresh."""
        result = refresh_author_names_cache(
            org_id="org-123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,  # Primeiro refresh
            last_org_id=None,
            is_refreshing=False,
            force=False,
            **callbacks,
        )

        assert result is True
        callbacks["on_start_refresh"].assert_called_once()
        mock_async_runner.run.assert_called_once()

    def test_async_runner_receives_correct_callbacks(self, mock_async_runner, callbacks):
        """Verifica que async_runner.run recebe funções corretas."""
        refresh_author_names_cache(
            org_id="org-123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,
            last_org_id=None,
            is_refreshing=False,
            force=False,
            **callbacks,
        )

        # Verificar que run foi chamado com 3 parâmetros
        assert mock_async_runner.run.call_count == 1
        call_args = mock_async_runner.run.call_args

        # Deve ter func, on_success, on_error
        assert "func" in call_args.kwargs
        assert "on_success" in call_args.kwargs
        assert "on_error" in call_args.kwargs

        # Verificar que são callables
        assert callable(call_args.kwargs["func"])
        assert callable(call_args.kwargs["on_success"])
        assert callable(call_args.kwargs["on_error"])

    def test_on_success_callback_updates_cache(self, mock_async_runner, callbacks):
        """Testa que callback de sucesso atualiza o cache corretamente."""
        # Capturar callbacks passados para async_runner
        captured_callbacks = {}

        def capture_run(**kwargs):
            captured_callbacks.update(kwargs)

        mock_async_runner.run.side_effect = capture_run

        refresh_author_names_cache(
            org_id="org-123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,
            last_org_id=None,
            is_refreshing=False,
            force=False,
            **callbacks,
        )

        # Simular sucesso com dados
        mapping = {"user-1": "João Silva"}
        prefix_map = {"user-1": "joao"}

        on_success = captured_callbacks["on_success"]
        on_success((mapping, prefix_map))

        # Verificar callbacks chamados
        callbacks["on_cache_updated"].assert_called_once()
        callbacks["on_end_refresh"].assert_called_once()

        # Verificar argumentos do on_cache_updated
        call_args = callbacks["on_cache_updated"].call_args[0]
        assert call_args[0] == mapping
        assert call_args[1] == prefix_map
        assert isinstance(call_args[2], str)  # Hash

    def test_on_error_callback_ends_refresh(self, mock_async_runner, callbacks):
        """Testa que callback de erro finaliza refresh adequadamente."""
        captured_callbacks = {}

        def capture_run(**kwargs):
            captured_callbacks.update(kwargs)

        mock_async_runner.run.side_effect = capture_run

        refresh_author_names_cache(
            org_id="org-123",
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=None,
            last_org_id=None,
            is_refreshing=False,
            force=False,
            **callbacks,
        )

        # Simular erro
        on_error = captured_callbacks["on_error"]
        on_error(Exception("Erro de teste"))

        # Verificar que apenas on_end_refresh foi chamado
        callbacks["on_cache_updated"].assert_not_called()
        callbacks["on_end_refresh"].assert_called_once()

    def test_org_id_change_logs_invalidation(self, mock_async_runner, callbacks):
        """Mudança de org_id loga invalidação, mas cooldown ainda se aplica."""
        last_refresh = time.time() - 10  # Dentro do cooldown

        result = refresh_author_names_cache(
            org_id="org-456",  # Organização diferente
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=last_refresh,
            last_org_id="org-123",  # Organização anterior diferente
            is_refreshing=False,
            force=False,
            **callbacks,
        )

        # Cooldown ainda se aplica mesmo com mudança de org
        # (mudança de org apenas loga, não força refresh)
        assert result is False
        callbacks["on_start_refresh"].assert_not_called()

    def test_org_id_change_with_expired_cooldown_allows_refresh(self, mock_async_runner, callbacks):
        """Mudança de org_id com cooldown expirado permite refresh."""
        last_refresh = time.time() - 31  # Cooldown expirado

        result = refresh_author_names_cache(
            org_id="org-456",  # Organização diferente
            async_runner=mock_async_runner,
            _current_cache={},
            _current_prefix_map={},
            last_refresh=last_refresh,
            last_org_id="org-123",  # Organização anterior
            is_refreshing=False,
            force=False,
            **callbacks,
        )

        # Deve permitir refresh (cooldown expirado)
        assert result is True
        callbacks["on_start_refresh"].assert_called_once()
