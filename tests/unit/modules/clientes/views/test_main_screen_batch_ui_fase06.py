"""Testes de UI da Fase 06 - Botões de Batch Operations.

Módulo: src.modules.clientes.views.main_screen
Fase: 06 - UI Elements (criação dos botões batch + callbacks)

NOTA (FEATURE-CLIENTES-001): Os botões de batch foram removidos da tela principal.
Este arquivo foi adaptado para testar:
- Signature de create_footer_buttons com callbacks opcionais
- Callbacks batch ainda existem em MainScreenFrame
"""

from __future__ import annotations


import inspect


class TestCreateFooterButtonsSignature:
    """Testes para verificar signature de create_footer_buttons."""

    def test_batch_callbacks_are_optional_in_signature(self) -> None:
        """Callbacks de batch devem ser opcionais na assinatura."""
        from src.ui.components.buttons import create_footer_buttons

        sig = inspect.signature(create_footer_buttons)

        # Batch callbacks devem ter default None
        assert sig.parameters["on_batch_delete"].default is None
        assert sig.parameters["on_batch_restore"].default is None
        assert sig.parameters["on_batch_export"].default is None

    def test_main_callbacks_are_required_in_signature(self) -> None:
        """Callbacks principais devem ser obrigatórios."""
        from src.ui.components.buttons import create_footer_buttons

        sig = inspect.signature(create_footer_buttons)

        # Callbacks principais não devem ter default
        assert sig.parameters["on_novo"].default == inspect.Parameter.empty
        assert sig.parameters["on_editar"].default == inspect.Parameter.empty
        assert sig.parameters["on_subpastas"].default == inspect.Parameter.empty
        assert sig.parameters["on_enviar"].default == inspect.Parameter.empty
        assert sig.parameters["on_enviar_pasta"].default == inspect.Parameter.empty


class TestFooterButtonsDataclass:
    """Testes para verificar dataclass FooterButtons."""

    def test_batch_fields_are_optional_in_dataclass(self) -> None:
        """Campos batch devem ser Optional na dataclass."""
        from src.ui.components.buttons import FooterButtons

        # Verifica que os campos existem e têm type hints
        annotations = FooterButtons.__annotations__

        assert "batch_delete" in annotations
        assert "batch_restore" in annotations
        assert "batch_export" in annotations

        # Verifica valores default (None)
        assert FooterButtons.__dataclass_fields__["batch_delete"].default is None
        assert FooterButtons.__dataclass_fields__["batch_restore"].default is None
        assert FooterButtons.__dataclass_fields__["batch_export"].default is None


class TestBatchCallbacksExistence:
    """Testes para verificar que os callbacks batch existem (mesmo sem botões na UI)."""

    def test_batch_delete_callback_exists_in_mainscreen(self) -> None:
        """Método _on_batch_delete_clicked deve existir em MainScreenFrame."""
        from src.modules.clientes.views.main_screen import MainScreenFrame

        assert hasattr(MainScreenFrame, "_on_batch_delete_clicked")
        assert callable(getattr(MainScreenFrame, "_on_batch_delete_clicked"))

    def test_batch_restore_callback_exists_in_mainscreen(self) -> None:
        """Método _on_batch_restore_clicked deve existir em MainScreenFrame."""
        from src.modules.clientes.views.main_screen import MainScreenFrame

        assert hasattr(MainScreenFrame, "_on_batch_restore_clicked")
        assert callable(getattr(MainScreenFrame, "_on_batch_restore_clicked"))

    def test_batch_export_callback_exists_in_mainscreen(self) -> None:
        """Método _on_batch_export_clicked deve existir em MainScreenFrame."""
        from src.modules.clientes.views.main_screen import MainScreenFrame

        assert hasattr(MainScreenFrame, "_on_batch_export_clicked")
        assert callable(getattr(MainScreenFrame, "_on_batch_export_clicked"))
