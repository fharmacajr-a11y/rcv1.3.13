# -*- coding: utf-8 -*-
"""Testes unitários do TopbarNotificationsController (headless)."""

from __future__ import annotations

import pytest

from src.ui.controllers import NotificationVM, TopbarNotificationsController


@pytest.fixture
def controller() -> TopbarNotificationsController:
    """Fixture de controller com preview padrão (120 chars)."""
    return TopbarNotificationsController(preview_max=120)


@pytest.fixture
def sample_notifications() -> list[dict]:
    """Fixture com notificações de exemplo."""
    return [
        {
            "id": "notif-1",
            "created_at": "2025-01-15T10:30:00Z",
            "created_at_local_str": "15/01/2025 10:30",
            "message": "Solicitação de acesso aprovada",
            "actor_display_name": "João Silva",
            "actor_initial": "JS",
            "actor_email": "joao@example.com",
            "is_read": False,
            "module": "Auth",
            "event": "access_granted",
            "request_id": "req-123",
        },
        {
            "id": "notif-2",
            "created_at": "2025-01-14T14:20:00Z",
            "created_at_local_str": "14/01/2025 14:20",
            "message": "Backup concluído com sucesso",
            "actor_display_name": "Sistema",
            "actor_initial": "SYS",
            "actor_email": "system@example.com",
            "is_read": True,
            "module": "Backup",
            "event": "backup_completed",
            "request_id": "req-456",
        },
        {
            "id": "notif-3",
            "created_at": "2025-01-13T09:00:00Z",
            "created_at_local_str": "13/01/2025 09:00",
            "message": "Nova versão disponível",
            "actor_display_name": "",  # Empty -> fallback to initial
            "actor_initial": "ADM",
            "actor_email": "",
            "is_read": False,
            "module": "Updates",
            "event": "version_available",
            "request_id": None,
        },
    ]


class TestBuildItems:
    """Testes do método build_items."""

    def test_build_items_retorna_viewmodels(
        self,
        controller: TopbarNotificationsController,
        sample_notifications: list[dict],
    ):
        """build_items deve retornar lista de NotificationVM."""
        items = controller.build_items(sample_notifications)

        assert len(items) == 3
        assert all(isinstance(vm, NotificationVM) for vm in items)

    def test_build_items_ordenacao_por_data_desc(
        self,
        controller: TopbarNotificationsController,
        sample_notifications: list[dict],
    ):
        """build_items deve ordenar por created_at (mais recente primeiro)."""
        items = controller.build_items(sample_notifications)

        # Ordem esperada: notif-1 (15/01), notif-2 (14/01), notif-3 (13/01)
        assert items[0].id == "notif-1"
        assert items[1].id == "notif-2"
        assert items[2].id == "notif-3"

    def test_build_items_message_display_com_bullet_se_nao_lida(
        self,
        controller: TopbarNotificationsController,
        sample_notifications: list[dict],
    ):
        """message_display deve ter bullet (\u25cf) se is_read=False."""
        items = controller.build_items(sample_notifications)

        # notif-1: não lida -> bullet
        assert items[0].message_display.startswith("\u25cf ")
        assert "Solicitação de acesso aprovada" in items[0].message_display

        # notif-2: lida -> sem bullet
        assert not items[1].message_display.startswith("\u25cf ")
        assert items[1].message_display == "Backup concluído com sucesso"

        # notif-3: não lida -> bullet
        assert items[2].message_display.startswith("\u25cf ")

    def test_build_items_message_display_trunca_em_preview_max(
        self,
        controller: TopbarNotificationsController,
    ):
        """message_display deve truncar se len > preview_max."""
        long_message = "A" * 200  # 200 chars
        notifs = [
            {
                "id": "long",
                "created_at": "2025-01-01T00:00:00Z",
                "created_at_local_str": "01/01/2025 00:00",
                "message": long_message,
                "is_read": True,
            },
        ]

        items = controller.build_items(notifs)

        # 120 chars - 3 ("...") = 117 chars + "..."
        assert len(items[0].message_display) == 120
        assert items[0].message_display.endswith("...")

    def test_build_items_message_display_substitui_quebras_por_espaco(
        self,
        controller: TopbarNotificationsController,
    ):
        """message_display deve substituir \\r\\n por espaço."""
        notifs = [
            {
                "id": "multiline",
                "created_at": "2025-01-01T00:00:00Z",
                "created_at_local_str": "01/01/2025 00:00",
                "message": "Linha 1\r\nLinha 2\nLinha 3",
                "is_read": True,
            },
        ]

        items = controller.build_items(notifs)

        # Quebras devem virar espaços
        assert "\r" not in items[0].message_display
        assert "\n" not in items[0].message_display
        assert items[0].message_display == "Linha 1 Linha 2 Linha 3"

    def test_build_items_actor_display_fallback_chain(
        self,
        controller: TopbarNotificationsController,
    ):
        """actor_display deve seguir fallback: display_name → initial → em-dash."""
        notifs = [
            {
                "id": "n1",
                "created_at": "2025-01-01T00:00:00Z",
                "created_at_local_str": "01/01/2025 00:00",
                "message": "Msg 1",
                "actor_display_name": "Nome Completo",
                "actor_initial": "NC",
                "is_read": True,
            },
            {
                "id": "n2",
                "created_at": "2025-01-01T00:00:00Z",
                "created_at_local_str": "01/01/2025 00:00",
                "message": "Msg 2",
                "actor_display_name": "",  # Empty -> use initial
                "actor_initial": "INI",
                "is_read": True,
            },
            {
                "id": "n3",
                "created_at": "2025-01-01T00:00:00Z",
                "created_at_local_str": "01/01/2025 00:00",
                "message": "Msg 3",
                "actor_display_name": "?",  # "?" -> use initial
                "actor_initial": "QM",
                "is_read": True,
            },
            {
                "id": "n4",
                "created_at": "2025-01-01T00:00:00Z",
                "created_at_local_str": "01/01/2025 00:00",
                "message": "Msg 4",
                "actor_display_name": "",
                "actor_initial": "",  # Empty -> em-dash
                "is_read": True,
            },
        ]

        items = controller.build_items(notifs)

        assert items[0].actor_display == "Nome Completo"
        assert items[1].actor_display == "INI"
        assert items[2].actor_display == "QM"
        assert items[3].actor_display == "\u2014"  # Em-dash

    def test_build_items_pula_notificacoes_sem_id(
        self,
        controller: TopbarNotificationsController,
    ):
        """build_items deve pular notificações sem ID."""
        notifs = [
            {
                "id": "valid",
                "created_at": "2025-01-01T00:00:00Z",
                "created_at_local_str": "01/01/2025 00:00",
                "message": "Valid",
                "is_read": True,
            },
            {
                # Sem ID
                "created_at": "2025-01-01T00:00:00Z",
                "created_at_local_str": "01/01/2025 00:00",
                "message": "Invalid (no ID)",
                "is_read": True,
            },
        ]

        items = controller.build_items(notifs)

        assert len(items) == 1
        assert items[0].id == "valid"

    def test_build_items_resolve_actor_callback(
        self,
        controller: TopbarNotificationsController,
    ):
        """build_items deve usar resolve_actor callback se fornecido."""

        def mock_resolver(email: str) -> str:
            # Mock: mapear email para nome
            return f"Resolved({email})"

        notifs = [
            {
                "id": "n1",
                "created_at": "2025-01-01T00:00:00Z",
                "created_at_local_str": "01/01/2025 00:00",
                "message": "Msg",
                "actor_email": "user@example.com",
                "actor_display_name": "",
                "actor_initial": "",
                "is_read": True,
            },
        ]

        items = controller.build_items(notifs, resolve_actor=mock_resolver)

        assert items[0].actor_display == "Resolved(user@example.com)"


class TestTreeRow:
    """Testes do método tree_row."""

    def test_tree_row_retorna_tupla_3_elementos(
        self,
        controller: TopbarNotificationsController,
    ):
        """tree_row deve retornar tupla (data, mensagem, por)."""
        vm = NotificationVM(
            id="test",
            created_at_raw="2025-01-01T00:00:00Z",
            created_at_display="01/01/2025 00:00",
            message_display="Mensagem formatada",
            actor_display="Autor",
            is_read=True,
            module=None,
            event=None,
            request_id=None,
            actor_email=None,
            actor_display_name=None,
            raw={},
        )

        row = controller.tree_row(vm)

        assert isinstance(row, tuple)
        assert len(row) == 3
        assert row == ("01/01/2025 00:00", "Mensagem formatada", "Autor")


class TestDetailPayload:
    """Testes do método detail_payload."""

    def test_detail_payload_retorna_dict_com_campos_obrigatorios(
        self,
        controller: TopbarNotificationsController,
    ):
        """detail_payload deve retornar dict com campos esperados."""
        vm = NotificationVM(
            id="test",
            created_at_raw="2025-01-01T00:00:00Z",
            created_at_display="01/01/2025 00:00",
            message_display="Preview...",
            actor_display="Autor",
            is_read=False,
            module="TestModule",
            event="test_event",
            request_id="req-999",
            actor_email="autor@example.com",
            actor_display_name="Autor Completo",
            raw={"message": "Mensagem completa sem truncar"},
        )

        payload = controller.detail_payload(vm)

        assert "created_at" in payload
        assert "module" in payload
        assert "event" in payload
        assert "message" in payload
        assert "request_id" in payload
        assert "user" in payload

        assert payload["created_at"] == "01/01/2025 00:00"
        assert payload["module"] == "TestModule"
        assert payload["event"] == "test_event"
        assert payload["message"] == "Mensagem completa sem truncar"
        assert payload["request_id"] == "req-999"
        assert payload["user"] == "Autor Completo <autor@example.com>"

    def test_detail_payload_user_apenas_email_se_sem_display_name(
        self,
        controller: TopbarNotificationsController,
    ):
        """user deve ser só email se display_name vazio."""
        vm = NotificationVM(
            id="test",
            created_at_raw=None,
            created_at_display="--",
            message_display="Msg",
            actor_display="ADM",
            is_read=True,
            module=None,
            event=None,
            request_id=None,
            actor_email="email@example.com",
            actor_display_name="",  # Empty
            raw={"message": "Msg completa"},
        )

        payload = controller.detail_payload(vm)

        assert payload["user"] == "email@example.com"

    def test_detail_payload_user_fallback_para_tracos_se_sem_dados(
        self,
        controller: TopbarNotificationsController,
    ):
        """user deve ser '--' se sem email e display_name."""
        vm = NotificationVM(
            id="test",
            created_at_raw=None,
            created_at_display="--",
            message_display="Msg",
            actor_display="\u2014",
            is_read=True,
            module=None,
            event=None,
            request_id=None,
            actor_email="",
            actor_display_name="",
            raw={"message": "Msg"},
        )

        payload = controller.detail_payload(vm)

        assert payload["user"] == "--"

    def test_detail_payload_campos_none_viram_tracos(
        self,
        controller: TopbarNotificationsController,
    ):
        """Campos None devem virar '--'."""
        vm = NotificationVM(
            id="test",
            created_at_raw=None,
            created_at_display="01/01/2025",
            message_display="Msg",
            actor_display="Autor",
            is_read=True,
            module=None,  # None
            event=None,  # None
            request_id=None,  # None
            actor_email=None,
            actor_display_name=None,
            raw={"message": "Msg"},
        )

        payload = controller.detail_payload(vm)

        assert payload["module"] == "--"
        assert payload["event"] == "--"
        assert payload["request_id"] == "--"
