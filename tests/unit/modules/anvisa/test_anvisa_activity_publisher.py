"""Testes unitários para AnvisaActivityPublisher.

Testa o publisher de activity com mocks, sem acesso real ao Supabase/Hub.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.modules.anvisa.controllers.anvisa_activity_publisher import (
    AnvisaActivityPublisher,
)


class TestPublish:
    """Testes para o método publish."""

    def test_publish_calls_activity_store_add_event(self) -> None:
        """Deve chamar get_recent_activity_store().add_event() com persist=True."""
        mock_store = MagicMock()
        mock_runner_class = MagicMock()
        mock_runner_instance = MagicMock()
        mock_runner_class.return_value = mock_runner_instance

        mock_user = MagicMock()
        mock_user.email = "user@test.com"
        mock_user.uid = "user-123"

        # Patch nos módulos de origem (não no publisher que faz lazy import)
        with (
            patch(
                "src.modules.hub.recent_activity_store.get_recent_activity_store",
                return_value=mock_store,
            ),
            patch(
                "src.modules.hub.async_runner.HubAsyncRunner",
                mock_runner_class,
            ),
            patch(
                "src.core.session.get_current_user",
                return_value=mock_user,
            ),
            patch("src.modules.hub.recent_activity_store.ActivityEvent") as mock_event_class,
        ):
            publisher = AnvisaActivityPublisher()
            mock_tk_root = MagicMock()

            publisher.publish(
                tk_root=mock_tk_root,
                org_id="org-123",
                action="Concluída",
                message="Demanda concluída: Registro",
                client_id="100",
                cnpj="12.345.678/0001-90",
                request_id="req-456",
                request_type="Registro",
                due_date="2025-01-15",
                razao_social="Empresa Teste",
            )

            # Verificar que ActivityEvent foi criado
            mock_event_class.assert_called_once()
            call_kwargs = mock_event_class.call_args.kwargs
            assert call_kwargs["org_id"] == "org-123"
            assert call_kwargs["module"] == "ANVISA"
            assert call_kwargs["action"] == "Concluída"
            assert call_kwargs["message"] == "Demanda concluída: Registro"
            assert call_kwargs["client_id"] == 100
            assert call_kwargs["cnpj"] == "12.345.678/0001-90"
            assert call_kwargs["request_id"] == "req-456"
            assert call_kwargs["request_type"] == "Registro"
            assert call_kwargs["due_date"] == "2025-01-15"
            assert call_kwargs["actor_email"] == "user@test.com"
            assert call_kwargs["actor_user_id"] == "user-123"
            assert call_kwargs["metadata"] == {"razao_social": "Empresa Teste"}

            # Verificar que HubAsyncRunner foi criado
            mock_runner_class.assert_called_once()

            # Verificar que add_event foi chamado com persist=True
            mock_store.add_event.assert_called_once()
            add_event_kwargs = mock_store.add_event.call_args.kwargs
            assert add_event_kwargs["persist"] is True
            assert add_event_kwargs["runner"] is mock_runner_instance

    def test_publish_handles_none_client_id(self) -> None:
        """Deve tratar client_id=None corretamente."""
        mock_store = MagicMock()
        mock_runner_class = MagicMock()
        mock_user = MagicMock()
        mock_user.email = None
        mock_user.uid = None

        with (
            patch(
                "src.modules.hub.recent_activity_store.get_recent_activity_store",
                return_value=mock_store,
            ),
            patch(
                "src.modules.hub.async_runner.HubAsyncRunner",
                mock_runner_class,
            ),
            patch(
                "src.core.session.get_current_user",
                return_value=mock_user,
            ),
            patch("src.modules.hub.recent_activity_store.ActivityEvent") as mock_event_class,
        ):
            publisher = AnvisaActivityPublisher()

            publisher.publish(
                tk_root=MagicMock(),
                org_id="org-123",
                action="Excluída",
                message="Demanda excluída",
                client_id=None,
                cnpj=None,
                request_id="req-789",
                request_type="Licença",
                due_date=None,
                razao_social=None,
            )

            # Verificar que ActivityEvent foi criado com client_id=None
            call_kwargs = mock_event_class.call_args.kwargs
            assert call_kwargs["client_id"] is None
            assert call_kwargs["cnpj"] is None
            assert call_kwargs["due_date"] is None
            assert call_kwargs["actor_email"] is None
            assert call_kwargs["actor_user_id"] is None
            assert call_kwargs["metadata"] == {"razao_social": ""}

    def test_publish_handles_exception_gracefully(self) -> None:
        """Deve logar warning e não propagar exceção."""
        mock_logger = MagicMock()

        with patch(
            "src.modules.hub.recent_activity_store.get_recent_activity_store",
            side_effect=Exception("Store error"),
        ):
            publisher = AnvisaActivityPublisher(logger=mock_logger)

            # Não deve levantar exceção
            publisher.publish(
                tk_root=MagicMock(),
                org_id="org-123",
                action="Concluída",
                message="Teste",
                client_id="100",
                cnpj=None,
                request_id="req-123",
                request_type="Registro",
                due_date=None,
                razao_social=None,
            )

            # Verificar que warning foi logado
            mock_logger.warning.assert_called_once()
            assert "Falha ao registrar evento" in mock_logger.warning.call_args[0][0]

            # Verificar que warning foi logado
            mock_logger.warning.assert_called_once()
            assert "Falha ao registrar evento" in mock_logger.warning.call_args[0][0]


class TestPublisherInit:
    """Testes para inicialização do publisher."""

    def test_publisher_accepts_custom_logger(self) -> None:
        """Publisher deve aceitar logger customizado."""
        custom_logger = MagicMock()
        publisher = AnvisaActivityPublisher(logger=custom_logger)

        assert publisher._log is custom_logger

    def test_publisher_uses_default_logger_when_none(self) -> None:
        """Publisher deve usar logger padrão quando não especificado."""
        publisher = AnvisaActivityPublisher()

        assert publisher._log is not None
        assert "anvisa_activity_publisher" in publisher._log.name
