# -*- coding: utf-8 -*-
"""Testes unitários para ColumnControlsLayout.

Este módulo testa o gerenciador de layout de controles de coluna de forma headless,
sem depender de Tkinter real. Foca na lógica matemática de cálculo de geometria
e posicionamento dos controles.

Cobertura esperada: >= 90% do arquivo column_controls_layout.py
"""

from __future__ import annotations

import pytest

from src.modules.clientes.controllers.column_controls_layout import (
    ColumnControlsLayout,
    ColumnGeometry,
    ControlPlacement,
)


@pytest.fixture
def layout_manager() -> ColumnControlsLayout:
    """Cria uma instância do ColumnControlsLayout."""
    return ColumnControlsLayout()


# ============================================================================
# TESTES DE DATA STRUCTURES
# ============================================================================


class TestColumnGeometry:
    """Testes da estrutura ColumnGeometry."""

    def test_column_geometry_criacao(self) -> None:
        """ColumnGeometry deve ser criado com left, right, width."""
        geom = ColumnGeometry(left=0, right=100, width=100)

        assert geom.left == 0
        assert geom.right == 100
        assert geom.width == 100

    def test_column_geometry_frozen(self) -> None:
        """ColumnGeometry deve ser imutável (frozen dataclass)."""
        geom = ColumnGeometry(left=50, right=150, width=100)

        with pytest.raises(AttributeError):
            geom.left = 60  # type: ignore

    def test_column_geometry_valores_negativos(self) -> None:
        """ColumnGeometry deve permitir valores negativos se necessário."""
        geom = ColumnGeometry(left=-10, right=90, width=100)

        assert geom.left == -10
        assert geom.right == 90
        assert geom.width == 100


class TestControlPlacement:
    """Testes da estrutura ControlPlacement."""

    def test_control_placement_criacao(self) -> None:
        """ControlPlacement deve ser criado com x e width."""
        placement = ControlPlacement(x=25, width=80)

        assert placement.x == 25
        assert placement.width == 80

    def test_control_placement_frozen(self) -> None:
        """ControlPlacement deve ser imutável (frozen dataclass)."""
        placement = ControlPlacement(x=10, width=100)

        with pytest.raises(AttributeError):
            placement.x = 20  # type: ignore

    def test_control_placement_valores_zero(self) -> None:
        """ControlPlacement deve aceitar valores zero."""
        placement = ControlPlacement(x=0, width=0)

        assert placement.x == 0
        assert placement.width == 0


# ============================================================================
# TESTES DO MÉTODO COMPUTE_COLUMN_GEOMETRIES
# ============================================================================


class TestColumnControlsLayoutComputeColumnGeometries:
    """Testes do método compute_column_geometries()."""

    def test_compute_column_geometries_basico(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_column_geometries deve calcular geometria de colunas simples."""
        col_order = ["col1", "col2", "col3"]
        column_widths = {"col1": 100, "col2": 150, "col3": 200}

        geoms = layout_manager.compute_column_geometries(col_order, column_widths)

        assert len(geoms) == 3

        # col1: left=0, right=100, width=100
        assert geoms["col1"].left == 0
        assert geoms["col1"].right == 100
        assert geoms["col1"].width == 100

        # col2: left=100, right=250, width=150
        assert geoms["col2"].left == 100
        assert geoms["col2"].right == 250
        assert geoms["col2"].width == 150

        # col3: left=250, right=450, width=200
        assert geoms["col3"].left == 250
        assert geoms["col3"].right == 450
        assert geoms["col3"].width == 200

    def test_compute_column_geometries_lista_vazia(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_column_geometries deve retornar dict vazio para lista vazia."""
        col_order: list[str] = []
        column_widths: dict[str, int] = {}

        geoms = layout_manager.compute_column_geometries(col_order, column_widths)

        assert geoms == {}

    def test_compute_column_geometries_coluna_sem_largura(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_column_geometries deve usar largura 0 se coluna não está no dict."""
        col_order = ["col1", "col2", "col3"]
        column_widths = {"col1": 100, "col3": 200}  # col2 falta

        geoms = layout_manager.compute_column_geometries(col_order, column_widths)

        assert len(geoms) == 3

        # col1: normal
        assert geoms["col1"].left == 0
        assert geoms["col1"].width == 100

        # col2: largura 0 (ausente no dict)
        assert geoms["col2"].left == 100
        assert geoms["col2"].right == 100
        assert geoms["col2"].width == 0

        # col3: começa após col2
        assert geoms["col3"].left == 100
        assert geoms["col3"].width == 200

    def test_compute_column_geometries_larguras_zero(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_column_geometries deve lidar com larguras zero."""
        col_order = ["col1", "col2", "col3"]
        column_widths = {"col1": 0, "col2": 0, "col3": 0}

        geoms = layout_manager.compute_column_geometries(col_order, column_widths)

        assert len(geoms) == 3
        assert all(g.width == 0 for g in geoms.values())
        assert all(g.left == g.right for g in geoms.values())

    def test_compute_column_geometries_larguras_diferentes(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_column_geometries deve calcular corretamente com larguras variadas."""
        col_order = ["id", "razao_social", "cnpj", "status"]
        column_widths = {
            "id": 50,
            "razao_social": 300,
            "cnpj": 150,
            "status": 100,
        }

        geoms = layout_manager.compute_column_geometries(col_order, column_widths)

        assert geoms["id"].left == 0
        assert geoms["id"].right == 50

        assert geoms["razao_social"].left == 50
        assert geoms["razao_social"].right == 350

        assert geoms["cnpj"].left == 350
        assert geoms["cnpj"].right == 500

        assert geoms["status"].left == 500
        assert geoms["status"].right == 600

    def test_compute_column_geometries_ordem_diferente(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_column_geometries deve respeitar a ordem fornecida."""
        col_order = ["col3", "col1", "col2"]
        column_widths = {"col1": 100, "col2": 150, "col3": 200}

        geoms = layout_manager.compute_column_geometries(col_order, column_widths)

        # col3 vem primeiro
        assert geoms["col3"].left == 0
        assert geoms["col3"].width == 200

        # col1 vem em segundo
        assert geoms["col1"].left == 200
        assert geoms["col1"].width == 100

        # col2 vem por último
        assert geoms["col2"].left == 300
        assert geoms["col2"].width == 150

    def test_compute_column_geometries_uma_coluna(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_column_geometries deve funcionar com apenas uma coluna."""
        col_order = ["unica"]
        column_widths = {"unica": 500}

        geoms = layout_manager.compute_column_geometries(col_order, column_widths)

        assert len(geoms) == 1
        assert geoms["unica"].left == 0
        assert geoms["unica"].right == 500
        assert geoms["unica"].width == 500


# ============================================================================
# TESTES DO MÉTODO COMPUTE_CONTROL_PLACEMENTS
# ============================================================================


class TestColumnControlsLayoutComputeControlPlacements:
    """Testes do método compute_control_placements()."""

    def test_compute_control_placements_basico(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements deve calcular placements com valores padrão."""
        geoms = {
            "col1": ColumnGeometry(left=0, right=100, width=100),
            "col2": ColumnGeometry(left=100, right=250, width=150),
        }
        required_widths = {"col1": 80, "col2": 120}

        placements = layout_manager.compute_control_placements(geoms, required_widths)

        assert len(placements) == 2
        assert "col1" in placements
        assert "col2" in placements

        # Verificar que x e width foram calculados
        assert placements["col1"].x >= 0
        assert placements["col1"].width > 0
        assert placements["col2"].x >= 100
        assert placements["col2"].width > 0

    def test_compute_control_placements_centralizado(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements deve centralizar controles na coluna."""
        geoms = {
            "col": ColumnGeometry(left=0, right=200, width=200),
        }
        required_widths = {"col": 100}

        placements = layout_manager.compute_control_placements(
            geoms, required_widths, min_width=70, max_width=160, padding=2
        )

        # width = 100 (req_w)
        # available = 200 - 4 = 196
        # gw = max(70, min(160, min(100, 196))) = 100
        # gx = 0 + (200 - 100) // 2 = 50

        assert placements["col"].width == 100
        assert placements["col"].x == 50

    def test_compute_control_placements_min_width(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements deve respeitar largura mínima."""
        geoms = {
            "col": ColumnGeometry(left=0, right=100, width=100),
        }
        required_widths = {"col": 30}  # Menor que min_width

        placements = layout_manager.compute_control_placements(
            geoms, required_widths, min_width=70, max_width=160, padding=2
        )

        # gw = max(70, min(160, min(30, 96))) = max(70, 30) = 70
        assert placements["col"].width == 70

    def test_compute_control_placements_max_width(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements deve respeitar largura máxima."""
        geoms = {
            "col": ColumnGeometry(left=0, right=500, width=500),
        }
        required_widths = {"col": 300}  # Maior que max_width

        placements = layout_manager.compute_control_placements(
            geoms, required_widths, min_width=70, max_width=160, padding=2
        )

        # available = 500 - 4 = 496
        # gw = max(70, min(160, min(300, 496))) = max(70, min(160, 300)) = max(70, 160) = 160
        assert placements["col"].width == 160

    def test_compute_control_placements_coluna_estreita(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements deve lidar com colunas muito estreitas."""
        geoms = {
            "col": ColumnGeometry(left=0, right=50, width=50),
        }
        required_widths = {"col": 100}

        placements = layout_manager.compute_control_placements(
            geoms, required_widths, min_width=70, max_width=160, padding=2
        )

        # available = 50 - 4 = 46
        # gw = max(70, min(160, min(100, 46))) = max(70, 46) = 70
        # gx = 0 + (50 - 70) // 2 = -10
        # gx < 0 + 2, então gx = 0 + 2 = 2
        # gx + 70 = 72 > 50 - 2 = 48, então gx = max(2, 50 - 70 - 2) = max(2, -22) = 2

        assert placements["col"].width == 70
        assert placements["col"].x == 2

    def test_compute_control_placements_sem_padding(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements deve funcionar com padding zero."""
        geoms = {
            "col": ColumnGeometry(left=0, right=100, width=100),
        }
        required_widths = {"col": 80}

        placements = layout_manager.compute_control_placements(
            geoms, required_widths, min_width=70, max_width=160, padding=0
        )

        # available = 100 - 0 = 100
        # gw = max(70, min(160, min(80, 100))) = 80
        # gx = 0 + (100 - 80) // 2 = 10

        assert placements["col"].width == 80
        assert placements["col"].x == 10

    def test_compute_control_placements_padding_grande(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements deve lidar com padding grande."""
        geoms = {
            "col": ColumnGeometry(left=0, right=100, width=100),
        }
        required_widths = {"col": 80}

        placements = layout_manager.compute_control_placements(
            geoms, required_widths, min_width=70, max_width=160, padding=20
        )

        # available = 100 - 40 = 60
        # gw = max(70, min(160, min(80, 60))) = max(70, 60) = 70
        # gx = 0 + (100 - 70) // 2 = 15
        # 15 < 0 + 20? Não
        # 15 + 70 = 85 > 100 - 20 = 80? Sim
        # gx = max(20, 100 - 70 - 20) = max(20, 10) = 20

        assert placements["col"].width == 70
        assert placements["col"].x == 20

    def test_compute_control_placements_multiplas_colunas(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements deve calcular placements para múltiplas colunas."""
        geoms = {
            "col1": ColumnGeometry(left=0, right=100, width=100),
            "col2": ColumnGeometry(left=100, right=250, width=150),
            "col3": ColumnGeometry(left=250, right=400, width=150),
        }
        required_widths = {"col1": 80, "col2": 120, "col3": 90}

        placements = layout_manager.compute_control_placements(
            geoms, required_widths, min_width=70, max_width=160, padding=2
        )

        assert len(placements) == 3

        # Cada coluna deve ter placement válido
        for col_id, placement in placements.items():
            geom = geoms[col_id]
            assert placement.x >= geom.left
            assert placement.x + placement.width <= geom.right or placement.width >= geom.width - 4

    def test_compute_control_placements_required_width_ausente(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements deve usar 0 se required_width ausente."""
        geoms = {
            "col1": ColumnGeometry(left=0, right=100, width=100),
            "col2": ColumnGeometry(left=100, right=200, width=100),
        }
        required_widths = {"col1": 80}  # col2 ausente

        placements = layout_manager.compute_control_placements(
            geoms, required_widths, min_width=70, max_width=160, padding=2
        )

        # col2: req_w = 0
        # available = 100 - 4 = 96
        # gw = max(70, min(160, min(0, 96))) = max(70, 0) = 70

        assert placements["col2"].width == 70

    def test_compute_control_placements_dict_vazio(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements deve retornar dict vazio para geometrias vazias."""
        geoms: dict[str, ColumnGeometry] = {}
        required_widths: dict[str, int] = {}

        placements = layout_manager.compute_control_placements(geoms, required_widths)

        assert placements == {}

    def test_compute_control_placements_borda_esquerda_limite(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements não deve vazar borda esquerda."""
        geoms = {
            "col": ColumnGeometry(left=50, right=150, width=100),
        }
        required_widths = {"col": 80}

        placements = layout_manager.compute_control_placements(
            geoms, required_widths, min_width=70, max_width=160, padding=2
        )

        # gw = 80
        # gx = 50 + (100 - 80) // 2 = 60
        # 60 >= 50 + 2 = 52? Sim, não precisa ajustar

        assert placements["col"].x >= geoms["col"].left + 2

    def test_compute_control_placements_borda_direita_limite(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements não deve vazar borda direita."""
        geoms = {
            "col": ColumnGeometry(left=0, right=100, width=100),
        }
        required_widths = {"col": 95}

        placements = layout_manager.compute_control_placements(
            geoms, required_widths, min_width=70, max_width=160, padding=2
        )

        # available = 100 - 4 = 96
        # gw = max(70, min(160, min(95, 96))) = 95
        # gx = 0 + (100 - 95) // 2 = 2
        # 2 >= 2? Sim
        # 2 + 95 = 97 > 100 - 2 = 98? Não

        assert placements["col"].x + placements["col"].width <= geoms["col"].right - 2 + 1  # Permite 1px de tolerância

    def test_compute_control_placements_valores_customizados(self, layout_manager: ColumnControlsLayout) -> None:
        """compute_control_placements deve aceitar valores customizados de min/max/padding."""
        geoms = {
            "col": ColumnGeometry(left=0, right=300, width=300),
        }
        required_widths = {"col": 150}

        placements = layout_manager.compute_control_placements(
            geoms,
            required_widths,
            min_width=100,
            max_width=200,
            padding=10,
        )

        # available = 300 - 20 = 280
        # gw = max(100, min(200, min(150, 280))) = 150
        # gx = 0 + (300 - 150) // 2 = 75

        assert placements["col"].width == 150
        assert placements["col"].x == 75
