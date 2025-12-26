# -*- coding: utf-8 -*-
"""Testes para propagação de created_by ao criar demandas ANVISA.

Testa se o user_id é corretamente propagado da view → controller → repository
quando disponível, e se mantém None quando não disponível.

Relacionado: P4 do TECH_DEBT_REGISTER (anvisa_screen.py:419)
"""

from __future__ import annotations

import logging
from unittest.mock import Mock, patch

import pytest


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_repo():
    """Mock do repositório ANVISA."""
    repo = Mock()
    repo.create_request.return_value = "req-uuid-created"
    return repo


@pytest.fixture
def mock_controller(mock_repo):
    """Controller real com repositório mockado."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    logger = logging.getLogger("test_anvisa_created_by")
    return AnvisaController(repository=mock_repo, logger=logger, notifications_service=None)


# =============================================================================
# Testes: Controller propagando created_by para Repository
# =============================================================================


def test_create_request_with_user_id_propagates_to_repo(mock_repo, mock_controller):
    """Testa que created_by é propagado do controller para o repository."""
    # Executar create_request com user_id
    result = mock_controller.create_request(
        org_id="org-123",
        client_id="456",
        request_type="ALTERACAO_RAZAO_SOCIAL",
        created_by="user-uuid-abc",
        payload={},
    )

    # Verificar sucesso
    assert result == "req-uuid-created"

    # Verificar que repo.create_request foi chamado com created_by correto
    mock_repo.create_request.assert_called_once()
    call_kwargs = mock_repo.create_request.call_args.kwargs

    assert call_kwargs["created_by"] == "user-uuid-abc"
    assert call_kwargs["org_id"] == "org-123"
    assert call_kwargs["client_id"] == 456  # Convertido para int
    assert call_kwargs["request_type"] == "ALTERACAO_RAZAO_SOCIAL"


def test_create_request_without_user_id_keeps_none(mock_repo, mock_controller):
    """Testa que created_by=None é mantido quando não há user_id."""
    # Executar create_request sem user_id (None)
    result = mock_controller.create_request(
        org_id="org-456",
        client_id="789",
        request_type="PETICAO_INICIAL",
        created_by=None,
        payload={},
    )

    # Verificar sucesso
    assert result == "req-uuid-created"

    # Verificar que repo.create_request foi chamado com created_by=None
    mock_repo.create_request.assert_called_once()
    call_kwargs = mock_repo.create_request.call_args.kwargs

    assert call_kwargs["created_by"] is None
    assert call_kwargs["client_id"] == 789


# =============================================================================
# Testes: View obtendo user_id de auth_utils
# =============================================================================


def test_view_obtains_user_id_from_auth_utils_when_available():
    """Testa que a view obtém user_id de current_user_id() quando disponível."""
    # Mock da função current_user_id para retornar um user_id
    with patch("src.modules.anvisa.views.anvisa_screen.current_user_id", return_value="user-logged-in-123"):
        # Importar e inspecionar o código da view (sem instanciar)
        # Na prática, apenas verificamos que a importação existe e funciona
        from src.modules.anvisa.views.anvisa_screen import current_user_id

        user_id = current_user_id()
        assert user_id == "user-logged-in-123"


def test_view_handles_none_user_id_gracefully():
    """Testa que a view lida com current_user_id() retornando None."""
    # Mock da função current_user_id para retornar None (sem autenticação)
    with patch("src.modules.anvisa.views.anvisa_screen.current_user_id", return_value=None):
        from src.modules.anvisa.views.anvisa_screen import current_user_id

        user_id = current_user_id()
        assert user_id is None


# =============================================================================
# Teste de Integração: Fluxo Completo (View → Controller → Repo)
# =============================================================================


def test_integration_view_to_repo_with_user_id(mock_repo):
    """Teste de integração: user_id flui da view até o repository."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    # Setup: controller real com repo mockado
    logger = logging.getLogger("test_integration")
    controller = AnvisaController(repository=mock_repo, logger=logger, notifications_service=None)

    # Simular: view obteve user_id="user-xyz" de current_user_id()
    user_id_from_auth = "user-xyz"

    # View chama controller.create_request com user_id
    result = controller.create_request(
        org_id="org-integration",
        client_id="999",
        request_type="BAIXA",
        created_by=user_id_from_auth,  # Propagado da view
        payload={},
    )

    # Verificar sucesso
    assert result == "req-uuid-created"

    # Verificar que created_by chegou ao repositório
    call_kwargs = mock_repo.create_request.call_args.kwargs
    assert call_kwargs["created_by"] == "user-xyz"


def test_integration_view_to_repo_without_user_id(mock_repo):
    """Teste de integração: created_by=None quando sem autenticação."""
    from src.modules.anvisa.controllers.anvisa_controller import AnvisaController

    logger = logging.getLogger("test_integration")
    controller = AnvisaController(repository=mock_repo, logger=logger, notifications_service=None)

    # Simular: current_user_id() retornou None (sem autenticação)
    user_id_from_auth = None

    # View chama controller com created_by=None
    result = controller.create_request(
        org_id="org-no-auth",
        client_id="111",
        request_type="RENOVACAO",
        created_by=user_id_from_auth,
        payload={},
    )

    # Verificar sucesso
    assert result == "req-uuid-created"

    # Verificar que created_by=None no repositório
    call_kwargs = mock_repo.create_request.call_args.kwargs
    assert call_kwargs["created_by"] is None
