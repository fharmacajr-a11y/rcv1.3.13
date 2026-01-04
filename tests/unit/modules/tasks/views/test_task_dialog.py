# -*- coding: utf-8 -*-
"""Unit tests for NovaTarefaDialog.

Testes de UI que requerem Tk/display gráfico.
"""

from __future__ import annotations

import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests in this module if Tk is not available (headless environment)
pytest.importorskip("tkinter")

import ttkbootstrap as tb  # noqa: E402

from src.db.domain_types import ClientRow, RCTaskRow  # noqa: E402
from src.modules.tasks.views.task_dialog import NovaTarefaDialog  # noqa: E402


pytestmark = pytest.mark.skipif(
    sys.platform == "win32" and sys.version_info >= (3, 13),
    reason=(
        "Tkinter/ttkbootstrap em Python 3.13 no Windows pode causar "
        "'Windows fatal exception: access violation' durante os testes "
        "(bug conhecido da runtime, ver CPython #118973 e #125179)."
    ),
)


@pytest.fixture(scope="function")
def tk_root():
    """Cria uma root Tk para testes de UI."""
    try:
        root = tb.Window()
        root.withdraw()  # Não mostrar janela durante testes
        yield root
        root.destroy()
    except Exception as e:
        pytest.skip(f"Tk não disponível: {e}")


@pytest.fixture
def mock_clients() -> list[ClientRow]:
    """Lista mock de clientes."""
    return [
        {
            "id": "client-1",
            "org_id": "org-123",
            "razao_social": "Farmácia ABC",
            "cnpj": "12.345.678/0001-90",
            "nome_fantasia": "ABC",
            "nome": "João",
            "numero": "123",
            "obs": "",
            "cnpj_norm": "12345678000190",
        },
        {
            "id": "client-2",
            "org_id": "org-123",
            "razao_social": "Drogaria XYZ",
            "cnpj": "98.765.432/0001-10",
            "nome_fantasia": "XYZ",
            "nome": "Maria",
            "numero": "456",
            "obs": "",
            "cnpj_norm": "98765432000110",
        },
    ]


def test_dialog_creates_successfully(tk_root, mock_clients):
    """Testa que o diálogo é criado com sucesso."""
    on_success = MagicMock()

    dialog = NovaTarefaDialog(
        parent=tk_root,
        org_id="org-123",
        user_id="user-456",
        on_success=on_success,
        clients=mock_clients,
    )

    # Verifica que os widgets principais existem
    assert dialog.title_entry is not None
    assert dialog.description_text is not None
    assert dialog.priority_combo is not None
    assert dialog.date_entry is not None
    assert dialog.client_combo is not None
    assert dialog.ok_button is not None
    assert dialog.cancel_button is not None

    dialog.destroy()


def test_dialog_populates_clients_combo(tk_root, mock_clients):
    """Testa que o combo de clientes é populado corretamente."""
    on_success = MagicMock()

    dialog = NovaTarefaDialog(
        parent=tk_root,
        org_id="org-123",
        user_id="user-456",
        on_success=on_success,
        clients=mock_clients,
    )

    # Verifica valores do combo
    combo_values = dialog.client_combo["values"]
    assert len(combo_values) == 3  # "(Nenhum)" + 2 clientes
    assert combo_values[0] == "(Nenhum)"
    assert "Farmácia ABC" in combo_values[1]
    assert "Drogaria XYZ" in combo_values[2]

    # Verifica seleção padrão
    assert dialog.client_var.get() == "(Nenhum)"

    dialog.destroy()


def test_dialog_default_values(tk_root):
    """Testa valores padrão do diálogo."""
    on_success = MagicMock()

    dialog = NovaTarefaDialog(
        parent=tk_root,
        org_id="org-123",
        user_id="user-456",
        on_success=on_success,
    )

    # Prioridade padrão deve ser "Normal"
    assert dialog.priority_var.get() == "Normal"

    # Data padrão deve ser hoje
    assert dialog.date_var.get() == date.today().strftime("%Y-%m-%d")

    # Título vazio
    assert dialog.title_var.get() == ""

    dialog.destroy()


def test_dialog_validation_empty_title(tk_root):
    """Testa que título vazio não permite criar tarefa."""
    on_success = MagicMock()

    with patch("src.modules.tasks.views.task_dialog.Messagebox") as mock_msgbox:
        dialog = NovaTarefaDialog(
            parent=tk_root,
            org_id="org-123",
            user_id="user-456",
            on_success=on_success,
        )

        # Deixar título vazio e clicar OK
        dialog.title_var.set("")
        dialog._on_ok()

        # Verifica que erro foi mostrado
        mock_msgbox.show_error.assert_called_once()
        assert "título" in mock_msgbox.show_error.call_args[0][0].lower()

        # Verifica que on_success não foi chamado
        on_success.assert_not_called()

        dialog.destroy()


def test_dialog_validation_invalid_date(tk_root):
    """Testa que data inválida não permite criar tarefa."""
    on_success = MagicMock()

    with patch("src.modules.tasks.views.task_dialog.Messagebox") as mock_msgbox:
        dialog = NovaTarefaDialog(
            parent=tk_root,
            org_id="org-123",
            user_id="user-456",
            on_success=on_success,
        )

        # Preencher título mas data inválida
        dialog.title_var.set("Minha tarefa")
        dialog.date_var.set("data-invalida")
        dialog._on_ok()

        # Verifica que erro foi mostrado
        mock_msgbox.show_error.assert_called_once()
        assert "data" in mock_msgbox.show_error.call_args[0][0].lower()

        # Verifica que on_success não foi chamado
        on_success.assert_not_called()

        dialog.destroy()


def test_dialog_creates_task_with_valid_data(tk_root, mock_clients):
    """Testa que tarefa é criada com dados válidos."""
    on_success = MagicMock()

    created_task: RCTaskRow = {
        "id": "task-123",
        "org_id": "org-123",
        "created_by": "user-456",
        "title": "Minha tarefa teste",
        "description": "Descrição detalhada",
        "priority": "high",
        "due_date": date(2024, 12, 31),
        "assigned_to": None,
        "client_id": None,
        "status": "pending",
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-01T10:00:00Z",
        "completed_at": None,
    }

    with patch("src.modules.tasks.views.task_dialog.create_task", return_value=created_task) as mock_create:
        dialog = NovaTarefaDialog(
            parent=tk_root,
            org_id="org-123",
            user_id="user-456",
            on_success=on_success,
            clients=mock_clients,
        )

        # Preencher dados válidos
        dialog.title_var.set("Minha tarefa teste")
        dialog.description_text.insert("1.0", "Descrição detalhada")
        dialog.priority_var.set("Alta")  # Mapeia para "high"
        dialog.date_var.set("2024-12-31")

        # Clicar OK
        dialog._on_ok()

        # Verifica que create_task foi chamado
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs

        assert call_kwargs["org_id"] == "org-123"
        assert call_kwargs["created_by"] == "user-456"
        assert call_kwargs["title"] == "Minha tarefa teste"
        assert call_kwargs["description"] == "Descrição detalhada"
        assert call_kwargs["priority"] == "high"
        assert call_kwargs["due_date"] == date(2024, 12, 31)
        assert call_kwargs.get("client_id") is None

        # Verifica que on_success foi chamado
        on_success.assert_called_once()


def test_dialog_maps_priority_labels_correctly(tk_root):
    """Testa que labels de prioridade são mapeados corretamente."""
    on_success = MagicMock()

    test_cases = [
        ("Baixa", "low"),
        ("Normal", "normal"),
        ("Alta", "high"),
        ("Urgente", "urgent"),
    ]

    for label, expected_value in test_cases:
        created_task: RCTaskRow = {
            "id": "task-test",
            "org_id": "org-test",
            "created_by": "user-test",
            "title": "Test",
            "priority": expected_value,
            "status": "pending",
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z",
        }

        with patch("src.modules.tasks.views.task_dialog.create_task", return_value=created_task) as mock_create:
            dialog = NovaTarefaDialog(
                parent=tk_root,
                org_id="org-test",
                user_id="user-test",
                on_success=on_success,
            )

            dialog.title_var.set("Test")
            dialog.priority_var.set(label)
            dialog._on_ok()

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["priority"] == expected_value, f"Failed for label '{label}', expected '{expected_value}'"

            dialog.destroy()


def test_dialog_cancel_closes_without_creating(tk_root):
    """Testa que cancelar fecha o diálogo sem criar tarefa."""
    on_success = MagicMock()

    with patch("src.modules.tasks.views.task_dialog.create_task") as mock_create:
        dialog = NovaTarefaDialog(
            parent=tk_root,
            org_id="org-123",
            user_id="user-456",
            on_success=on_success,
        )

        # Preencher dados
        dialog.title_var.set("Teste")

        # Clicar em Cancelar (simula destruindo)
        dialog._on_close()

        # Verifica que create_task não foi chamado
        mock_create.assert_not_called()

        # Verifica que on_success não foi chamado
        on_success.assert_not_called()


def test_dialog_handles_create_task_error(tk_root):
    """Testa que erros ao criar tarefa são tratados."""
    on_success = MagicMock()

    with patch("src.modules.tasks.views.task_dialog.create_task") as mock_create:
        with patch("src.modules.tasks.views.task_dialog.Messagebox") as mock_msgbox:
            # Simula erro ao criar tarefa
            mock_create.side_effect = RuntimeError("Database error")

            dialog = NovaTarefaDialog(
                parent=tk_root,
                org_id="org-123",
                user_id="user-456",
                on_success=on_success,
            )

            # Preencher dados válidos
            dialog.title_var.set("Teste")
            dialog._on_ok()

            # Verifica que erro foi mostrado
            mock_msgbox.show_error.assert_called_once()
            assert "erro" in mock_msgbox.show_error.call_args[0][0].lower()

            # Verifica que on_success não foi chamado
            on_success.assert_not_called()

            dialog.destroy()
