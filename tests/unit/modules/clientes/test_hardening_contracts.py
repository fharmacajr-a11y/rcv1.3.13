# -*- coding: utf-8 -*-
"""Testes de contrato de hardening do módulo de clientes.

Validações simples para evitar regressão de performance e UX:
- Style exclusivo "Clientes.Treeview" (não polui global)
- style.map para seleção (garante legibilidade sobre zebra)
- build_row_tags retorna tupla de tags
"""

from __future__ import annotations

import inspect

import pytest

# Razão para skip dos contratos obsoletos
_SKIP_CTK = "Contrato obsoleto: migrado para CustomTkinter (sem ttk style / controllers movidos)"


class TestTreeviewStyleContract:
    """Verifica que o Treeview de clientes usa style exclusivo."""

    def test_clients_treeview_style_constant_exists(self) -> None:
        """Constante CLIENTS_TREEVIEW_STYLE deve existir e não ser 'Treeview' global."""
        from src.ui.components.lists import CLIENTS_TREEVIEW_STYLE

        assert CLIENTS_TREEVIEW_STYLE is not None
        assert CLIENTS_TREEVIEW_STYLE != "Treeview", "Style deve ser exclusivo, não o global 'Treeview'"
        assert "Clientes" in CLIENTS_TREEVIEW_STYLE, "Style deve conter 'Clientes' no nome"

    @pytest.mark.skip(reason=_SKIP_CTK)
    def test_clients_treeview_uses_style_in_code(self) -> None:
        """create_clients_treeview deve referenciar CLIENTS_TREEVIEW_STYLE no código."""
        from src.ui.components.lists import create_clients_treeview

        source = inspect.getsource(create_clients_treeview)

        # Verifica que o style é passado ao criar o Treeview
        assert "style=" in source, "Treeview deve receber parâmetro style="
        assert "CLIENTS_TREEVIEW_STYLE" in source, "Deve usar a constante CLIENTS_TREEVIEW_STYLE"


class TestSelectionStyleMap:
    """Verifica que style.map é configurado para seleção legível."""

    @pytest.mark.skip(reason=_SKIP_CTK)
    def test_style_map_exists_in_configure_function(self) -> None:
        """_configure_clients_treeview_style deve chamar style.map para seleção."""
        from src.ui.components.lists import _configure_clients_treeview_style

        source = inspect.getsource(_configure_clients_treeview_style)

        # Verifica que style.map é chamado
        assert "style.map" in source, "Deve chamar style.map para configurar estados"

        # Verifica que configura o estado selected
        assert '"selected"' in source or "'selected'" in source, "style.map deve configurar estado 'selected'"

        # Verifica que configura background
        assert "background" in source, "style.map deve configurar background"


class TestRowTagsContract:
    """Verifica contrato de build_row_tags."""

    @pytest.mark.skip(reason=_SKIP_CTK)
    def test_build_row_tags_returns_tuple(self) -> None:
        """build_row_tags deve retornar tupla de strings."""
        from src.modules.clientes.controllers.rendering_adapter import build_row_tags
        from src.modules.clientes.core.viewmodel import ClienteRow

        row = ClienteRow(
            id="1",
            razao_social="Test",
            cnpj="12345678901234",
            nome="Test",
            whatsapp="",
            observacoes="",
            status="Ativo",
            ultima_alteracao="2025-01-01",
            raw={},
        )

        tags = build_row_tags(row)

        assert isinstance(tags, tuple), "build_row_tags deve retornar tupla"
        assert all(isinstance(t, str) for t in tags), "Todos os elementos devem ser strings"

    @pytest.mark.skip(reason=_SKIP_CTK)
    def test_build_row_tags_with_obs_includes_has_obs(self) -> None:
        """build_row_tags deve incluir 'has_obs' se observacoes não vazia."""
        from src.modules.clientes.controllers.rendering_adapter import build_row_tags
        from src.modules.clientes.core.viewmodel import ClienteRow

        row = ClienteRow(
            id="1",
            razao_social="Test",
            cnpj="12345678901234",
            nome="Test",
            whatsapp="",
            observacoes="[ATIVO] Alguma observação",
            status="Ativo",
            ultima_alteracao="2025-01-01",
            raw={},
        )

        tags = build_row_tags(row)

        assert "has_obs" in tags, "build_row_tags deve incluir 'has_obs' para linhas com observações"

    @pytest.mark.skip(reason=_SKIP_CTK)
    def test_zebra_tags_are_valid_strings(self) -> None:
        """Tags de zebra ('even', 'odd') devem ser strings válidas para concatenação."""
        # Simula o padrão usado no código
        zebra_even = "even"
        zebra_odd = "odd"

        from src.modules.clientes.controllers.rendering_adapter import build_row_tags
        from src.modules.clientes.core.viewmodel import ClienteRow

        row = ClienteRow(
            id="1",
            razao_social="Test",
            cnpj="",
            nome="",
            whatsapp="",
            observacoes="",
            status="",
            ultima_alteracao="",
            raw={},
        )

        base_tags = build_row_tags(row)

        # Deve ser possível concatenar com zebra tag
        combined_even = base_tags + (zebra_even,)
        combined_odd = base_tags + (zebra_odd,)

        assert isinstance(combined_even, tuple)
        assert isinstance(combined_odd, tuple)
        assert zebra_even in combined_even
        assert zebra_odd in combined_odd


class TestDestroyCleanupContract:
    """Verifica que destroy tem cleanup de after/timers documentado."""

    @pytest.mark.skip(reason=_SKIP_CTK)
    def test_main_screen_frame_has_destroy_method(self) -> None:
        """MainScreenFrame deve ter método destroy customizado."""
        from src.modules.clientes.views.main_screen_frame import MainScreenFrame

        assert hasattr(MainScreenFrame, "destroy"), "MainScreenFrame deve ter método destroy"

        # Verificar que não é apenas o herdado
        import inspect

        source = inspect.getsource(MainScreenFrame.destroy)

        # Deve conter cleanup de after
        assert (
            "after_cancel" in source or "_connectivity" in source
        ), "destroy() deve fazer cleanup de after pendentes ou connectivity"
