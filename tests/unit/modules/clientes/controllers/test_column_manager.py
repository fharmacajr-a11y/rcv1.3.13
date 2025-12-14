"""
Testes unitários para column_manager.py (MS-15 Column Management).

Este módulo testa ColumnManager de forma headless, sem dependências do Tkinter.
Segue o padrão estabelecido nas microfases anteriores.

Objetivo: Elevar a cobertura de ~62.3% para ≥85%.
"""

import pytest
from unittest.mock import Mock

from src.modules.clientes.controllers.column_manager import (
    ColumnConfig,
    ColumnManager,
    ColumnManagerState,
    VisibilityValidationResult,
)


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnConfig
# ────────────────────────────────────────────────────────────────────────────────


class TestColumnConfig:
    """Testes do dataclass ColumnConfig."""

    def test_column_config_creation_basic(self):
        """Testa criação de ColumnConfig básica."""
        config = ColumnConfig(name="ID", visible=True)
        assert config.name == "ID"
        assert config.visible is True
        assert config.mandatory is False  # default

    def test_column_config_creation_mandatory(self):
        """Testa criação de ColumnConfig obrigatória."""
        config = ColumnConfig(name="ID", visible=True, mandatory=True)
        assert config.mandatory is True

    def test_column_config_immutability(self):
        """Testa imutabilidade do dataclass frozen."""
        config = ColumnConfig(name="ID", visible=True)
        with pytest.raises(AttributeError):
            config.visible = False  # type: ignore


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnManagerState
# ────────────────────────────────────────────────────────────────────────────────


class TestColumnManagerState:
    """Testes do dataclass ColumnManagerState."""

    def test_state_creation(self):
        """Testa criação de ColumnManagerState."""
        state = ColumnManagerState(
            order=("ID", "Nome", "CNPJ"),
            visibility={"ID": True, "Nome": False, "CNPJ": True},
        )
        assert state.order == ("ID", "Nome", "CNPJ")
        assert state.visibility["ID"] is True
        assert state.visibility["Nome"] is False

    def test_state_immutability(self):
        """Testa imutabilidade do dataclass frozen."""
        state = ColumnManagerState(
            order=("ID", "Nome"),
            visibility={"ID": True, "Nome": True},
        )
        with pytest.raises(AttributeError):
            state.order = ("Nome", "ID")  # type: ignore


# ────────────────────────────────────────────────────────────────────────────────
# Tests: VisibilityValidationResult
# ────────────────────────────────────────────────────────────────────────────────


class TestVisibilityValidationResult:
    """Testes do dataclass VisibilityValidationResult."""

    def test_validation_result_valid(self):
        """Testa resultado de validação válida."""
        result = VisibilityValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.reason == ""  # default

    def test_validation_result_invalid_with_reason(self):
        """Testa resultado de validação inválida com razão."""
        result = VisibilityValidationResult(
            is_valid=False,
            reason="Coluna obrigatória",
        )
        assert result.is_valid is False
        assert result.reason == "Coluna obrigatória"

    def test_validation_result_with_suggested_state(self):
        """Testa resultado com estado sugerido."""
        suggested = {"ID": True, "Nome": False}
        result = VisibilityValidationResult(
            is_valid=False,
            reason="Estado inválido",
            suggested_state=suggested,
        )
        assert result.suggested_state == suggested


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnManager.__init__
# ────────────────────────────────────────────────────────────────────────────────


class TestColumnManagerInit:
    """Testes de inicialização do ColumnManager."""

    def test_init_basic(self):
        """Testa inicialização básica com apenas ordem."""
        manager = ColumnManager(["ID", "Nome"])
        state = manager.get_state()
        assert state.order == ("ID", "Nome")
        assert state.visibility["ID"] is True  # default: todas visíveis
        assert state.visibility["Nome"] is True

    def test_init_with_visibility(self):
        """Testa inicialização com visibilidade customizada."""
        manager = ColumnManager(
            ["ID", "Nome", "CNPJ"],
            initial_visibility={"ID": True, "Nome": False, "CNPJ": True},
        )
        state = manager.get_state()
        assert state.visibility["ID"] is True
        assert state.visibility["Nome"] is False
        assert state.visibility["CNPJ"] is True

    def test_init_with_mandatory_columns(self):
        """Testa inicialização com colunas obrigatórias."""
        manager = ColumnManager(
            ["ID", "Nome"],
            initial_visibility={"ID": False, "Nome": True},
            mandatory_columns={"ID"},
        )
        state = manager.get_state()
        # Coluna obrigatória deve ser forçada a visível
        assert state.visibility["ID"] is True

    def test_init_all_hidden_makes_first_visible(self):
        """Testa que pelo menos uma coluna fica visível se todas estiverem ocultas."""
        manager = ColumnManager(
            ["ID", "Nome", "CNPJ"],
            initial_visibility={"ID": False, "Nome": False, "CNPJ": False},
        )
        state = manager.get_state()
        # Primeira coluna deve ser forçada a visível
        assert state.visibility["ID"] is True

    def test_init_partial_visibility_completes_missing(self):
        """Testa que colunas ausentes em initial_visibility são preenchidas como True."""
        manager = ColumnManager(
            ["ID", "Nome", "CNPJ"],
            initial_visibility={"ID": False},  # Nome e CNPJ faltando
        )
        state = manager.get_state()
        assert state.visibility["ID"] is False
        assert state.visibility["Nome"] is True  # completado
        assert state.visibility["CNPJ"] is True  # completado

    def test_init_empty_columns(self):
        """Testa inicialização com lista vazia de colunas."""
        manager = ColumnManager([])
        state = manager.get_state()
        assert state.order == ()
        assert state.visibility == {}


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnManager.validate_visibility_change
# ────────────────────────────────────────────────────────────────────────────────


class TestValidateVisibilityChange:
    """Testes do método validate_visibility_change."""

    def test_validate_nonexistent_column(self):
        """Testa validação de coluna inexistente."""
        manager = ColumnManager(["ID", "Nome"])
        result = manager.validate_visibility_change("CNPJ", False)
        assert result.is_valid is False
        assert "não existe" in result.reason

    def test_validate_hide_mandatory_column(self):
        """Testa validação ao tentar ocultar coluna obrigatória."""
        manager = ColumnManager(["ID", "Nome"], mandatory_columns={"ID"})
        result = manager.validate_visibility_change("ID", False)
        assert result.is_valid is False
        assert "obrigatória" in result.reason

    def test_validate_hide_last_visible_column(self):
        """Testa validação ao tentar ocultar a última coluna visível."""
        manager = ColumnManager(
            ["ID", "Nome"],
            initial_visibility={"ID": False, "Nome": True},
        )
        result = manager.validate_visibility_change("Nome", False)
        assert result.is_valid is False
        assert "pelo menos uma coluna" in result.reason.lower()
        assert result.suggested_state is not None

    def test_validate_valid_change_hide(self):
        """Testa validação de mudança válida (ocultar)."""
        manager = ColumnManager(["ID", "Nome"], {"ID": True, "Nome": True})
        result = manager.validate_visibility_change("Nome", False)
        assert result.is_valid is True
        assert result.reason == ""

    def test_validate_valid_change_show(self):
        """Testa validação de mudança válida (mostrar)."""
        manager = ColumnManager(["ID", "Nome"], {"ID": True, "Nome": False})
        result = manager.validate_visibility_change("Nome", True)
        assert result.is_valid is True


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnManager.set_visibility
# ────────────────────────────────────────────────────────────────────────────────


class TestSetVisibility:
    """Testes do método set_visibility."""

    def test_set_visibility_hide_column(self):
        """Testa ocultar uma coluna."""
        manager = ColumnManager(["ID", "Nome"])
        state = manager.set_visibility("Nome", False)
        assert state.visibility["Nome"] is False
        assert state.visibility["ID"] is True

    def test_set_visibility_show_column(self):
        """Testa mostrar uma coluna."""
        manager = ColumnManager(["ID", "Nome"], {"ID": True, "Nome": False})
        state = manager.set_visibility("Nome", True)
        assert state.visibility["Nome"] is True

    def test_set_visibility_invalid_returns_current_state(self):
        """Testa que mudança inválida retorna estado atual inalterado."""
        manager = ColumnManager(["ID"], mandatory_columns={"ID"})
        state_before = manager.get_state()
        state_after = manager.set_visibility("ID", False)  # inválido
        assert state_after.visibility["ID"] is True  # inalterado
        assert state_before.visibility == state_after.visibility

    def test_set_visibility_nonexistent_column_no_change(self):
        """Testa que tentar modificar coluna inexistente não altera estado."""
        manager = ColumnManager(["ID"])
        state = manager.set_visibility("CNPJ", False)
        assert "CNPJ" not in state.visibility


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnManager.toggle
# ────────────────────────────────────────────────────────────────────────────────


class TestToggle:
    """Testes do método toggle."""

    def test_toggle_visible_to_hidden(self):
        """Testa alternar de visível para oculto."""
        manager = ColumnManager(["ID", "Nome"])
        state = manager.toggle("Nome")
        assert state.visibility["Nome"] is False

    def test_toggle_hidden_to_visible(self):
        """Testa alternar de oculto para visível."""
        manager = ColumnManager(["ID", "Nome"], {"ID": True, "Nome": False})
        state = manager.toggle("Nome")
        assert state.visibility["Nome"] is True

    def test_toggle_nonexistent_column(self):
        """Testa toggle em coluna inexistente não altera estado."""
        manager = ColumnManager(["ID"])
        state = manager.toggle("CNPJ")
        assert "CNPJ" not in state.visibility

    def test_toggle_respects_validation_rules(self):
        """Testa que toggle respeita regras de validação."""
        manager = ColumnManager(["ID"], mandatory_columns={"ID"})
        state = manager.toggle("ID")  # Tenta ocultar obrigatória
        assert state.visibility["ID"] is True  # Deve permanecer visível


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnManager.get_configs
# ────────────────────────────────────────────────────────────────────────────────


class TestGetConfigs:
    """Testes do método get_configs."""

    def test_get_configs_basic(self):
        """Testa obtenção de configurações básicas."""
        manager = ColumnManager(["ID", "Nome"])
        configs = manager.get_configs()
        assert len(configs) == 2
        assert configs[0].name == "ID"
        assert configs[0].visible is True
        assert configs[0].mandatory is False

    def test_get_configs_with_mandatory(self):
        """Testa obtenção de configurações com colunas obrigatórias."""
        manager = ColumnManager(["ID", "Nome"], mandatory_columns={"ID"})
        configs = manager.get_configs()
        id_config = next(c for c in configs if c.name == "ID")
        assert id_config.mandatory is True

    def test_get_configs_preserves_order(self):
        """Testa que get_configs preserva ordem original."""
        manager = ColumnManager(["CNPJ", "ID", "Nome"])
        configs = manager.get_configs()
        assert [c.name for c in configs] == ["CNPJ", "ID", "Nome"]


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnManager.load_from_prefs
# ────────────────────────────────────────────────────────────────────────────────


class TestLoadFromPrefs:
    """Testes do método load_from_prefs."""

    def test_load_from_prefs_success(self):
        """Testa carregamento bem-sucedido de preferências."""

        def mock_loader(key: str) -> dict[str, bool]:
            return {"ID": True, "Nome": False, "CNPJ": True}

        manager = ColumnManager(["ID", "Nome", "CNPJ"])
        state = manager.load_from_prefs(mock_loader, "user@example.com")
        assert state.visibility["ID"] is True
        assert state.visibility["Nome"] is False
        assert state.visibility["CNPJ"] is True

    def test_load_from_prefs_partial_data(self):
        """Testa carregamento com preferências parciais."""

        def mock_loader(key: str) -> dict[str, bool]:
            return {"ID": False}  # Nome não especificado

        manager = ColumnManager(["ID", "Nome"])
        state = manager.load_from_prefs(mock_loader, "user@example.com")
        assert state.visibility["ID"] is False
        assert state.visibility["Nome"] is True  # mantém valor anterior

    def test_load_from_prefs_respects_validation(self):
        """Testa que load_from_prefs respeita regras de validação."""

        def mock_loader(key: str) -> dict[str, bool]:
            return {"ID": False}  # Tentar ocultar obrigatória

        manager = ColumnManager(["ID", "Nome"], mandatory_columns={"ID"})
        state = manager.load_from_prefs(mock_loader, "user@example.com")
        # ID obrigatória não deve ser ocultada
        assert state.visibility["ID"] is True

    def test_load_from_prefs_ensures_one_visible(self):
        """Testa que load_from_prefs garante pelo menos uma coluna visível."""

        def mock_loader(key: str) -> dict[str, bool]:
            return {"ID": False, "Nome": False}

        manager = ColumnManager(["ID", "Nome"])
        state = manager.load_from_prefs(mock_loader, "user@example.com")
        # Pelo menos uma deve estar visível
        assert state.visibility["ID"] is True or state.visibility["Nome"] is True

    def test_load_from_prefs_exception_returns_current_state(self):
        """Testa que exceção no loader retorna estado atual."""

        def failing_loader(key: str) -> dict[str, bool]:
            raise RuntimeError("Erro ao carregar")

        manager = ColumnManager(["ID", "Nome"])
        state_before = manager.get_state()
        state_after = manager.load_from_prefs(failing_loader, "user@example.com")
        assert state_before.visibility == state_after.visibility


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnManager.save_to_prefs
# ────────────────────────────────────────────────────────────────────────────────


class TestSaveToPrefs:
    """Testes do método save_to_prefs."""

    def test_save_to_prefs_success(self):
        """Testa salvamento bem-sucedido de preferências."""
        saved_data = {}

        def mock_saver(key: str, data: dict[str, bool]) -> None:
            saved_data[key] = data

        manager = ColumnManager(["ID", "Nome"], {"ID": True, "Nome": False})
        manager.save_to_prefs(mock_saver, "user@example.com")

        assert "user@example.com" in saved_data
        assert saved_data["user@example.com"]["ID"] is True
        assert saved_data["user@example.com"]["Nome"] is False

    def test_save_to_prefs_exception_silent_fail(self):
        """Testa que exceção no saver falha silenciosamente."""

        def failing_saver(key: str, data: dict[str, bool]) -> None:
            raise RuntimeError("Erro ao salvar")

        manager = ColumnManager(["ID"])
        # Não deve lançar exceção
        manager.save_to_prefs(failing_saver, "user@example.com")


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnManager.get_visible_columns / get_hidden_columns
# ────────────────────────────────────────────────────────────────────────────────


class TestVisibleHiddenColumns:
    """Testes dos métodos get_visible_columns e get_hidden_columns."""

    def test_get_visible_columns(self):
        """Testa obtenção de colunas visíveis."""
        manager = ColumnManager(
            ["ID", "Nome", "CNPJ"],
            {"ID": True, "Nome": False, "CNPJ": True},
        )
        visible = manager.get_visible_columns()
        assert visible == ["ID", "CNPJ"]

    def test_get_hidden_columns(self):
        """Testa obtenção de colunas ocultas."""
        manager = ColumnManager(
            ["ID", "Nome", "CNPJ"],
            {"ID": True, "Nome": False, "CNPJ": True},
        )
        hidden = manager.get_hidden_columns()
        assert hidden == ["Nome"]

    def test_get_visible_all_visible(self):
        """Testa get_visible_columns quando todas estão visíveis."""
        manager = ColumnManager(["ID", "Nome"])
        visible = manager.get_visible_columns()
        assert visible == ["ID", "Nome"]

    def test_get_hidden_all_hidden_except_first(self):
        """Testa get_hidden_columns quando quase todas estão ocultas."""
        manager = ColumnManager(
            ["ID", "Nome", "CNPJ"],
            {"ID": True, "Nome": False, "CNPJ": False},  # Regra força ID visível
        )
        hidden = manager.get_hidden_columns()
        assert hidden == ["Nome", "CNPJ"]


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnManager.build_visibility_map_for_rendering
# ────────────────────────────────────────────────────────────────────────────────


class TestBuildVisibilityMapForRendering:
    """Testes do método build_visibility_map_for_rendering."""

    def test_build_visibility_map(self):
        """Testa construção do mapa de visibilidade."""
        manager = ColumnManager(["ID", "Nome"], {"ID": True, "Nome": False})
        vis_map = manager.build_visibility_map_for_rendering()
        assert vis_map == {"ID": True, "Nome": False}

    def test_build_visibility_map_is_copy(self):
        """Testa que mapa retornado é uma cópia (não altera internal state)."""
        manager = ColumnManager(["ID"])
        vis_map = manager.build_visibility_map_for_rendering()
        vis_map["ID"] = False  # Modificar cópia

        # Estado interno não deve mudar
        assert manager.get_state().visibility["ID"] is True


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ColumnManager.sync_to_ui_vars
# ────────────────────────────────────────────────────────────────────────────────


class TestSyncToUiVars:
    """Testes do método sync_to_ui_vars."""

    def test_sync_to_ui_vars_basic(self):
        """Testa sincronização com variáveis de UI."""
        var_id = Mock()
        var_nome = Mock()
        ui_vars = {"ID": var_id, "Nome": var_nome}

        manager = ColumnManager(["ID", "Nome"], {"ID": True, "Nome": False})
        manager.sync_to_ui_vars(ui_vars)

        var_id.set.assert_called_once_with(True)
        var_nome.set.assert_called_once_with(False)

    def test_sync_to_ui_vars_partial(self):
        """Testa sincronização com apenas algumas variáveis presentes."""
        var_id = Mock()
        ui_vars = {"ID": var_id}  # Nome não tem variável

        manager = ColumnManager(["ID", "Nome"], {"ID": True, "Nome": False})
        manager.sync_to_ui_vars(ui_vars)

        var_id.set.assert_called_once_with(True)
        # Nome não deve causar erro

    def test_sync_to_ui_vars_empty(self):
        """Testa sincronização com dicionário vazio."""
        manager = ColumnManager(["ID", "Nome"])
        # Não deve lançar exceção
        manager.sync_to_ui_vars({})


# ────────────────────────────────────────────────────────────────────────────────
# Tests: Integration Scenarios
# ────────────────────────────────────────────────────────────────────────────────


class TestColumnManagerIntegration:
    """Testes de cenários completos de uso do ColumnManager."""

    def test_full_workflow_toggle_and_persist(self):
        """Testa fluxo completo: criar, alternar, salvar, recriar, carregar."""
        saved_prefs = {}

        def saver(key: str, data: dict[str, bool]) -> None:
            saved_prefs[key] = data

        def loader(key: str) -> dict[str, bool]:
            return saved_prefs.get(key, {})

        # Criar manager inicial
        manager1 = ColumnManager(["ID", "Nome", "CNPJ"])
        manager1.toggle("Nome")  # Ocultar Nome
        manager1.save_to_prefs(saver, "user@test.com")

        # Criar novo manager e carregar preferências
        manager2 = ColumnManager(["ID", "Nome", "CNPJ"])
        state = manager2.load_from_prefs(loader, "user@test.com")

        # Verificar que preferência foi carregada
        assert state.visibility["Nome"] is False
        assert state.visibility["ID"] is True

    def test_mandatory_column_enforcement_throughout(self):
        """Testa que colunas obrigatórias são sempre respeitadas."""
        manager = ColumnManager(
            ["ID", "Nome"],
            initial_visibility={"ID": False, "Nome": True},
            mandatory_columns={"ID"},
        )

        # ID deve ter sido forçada a visível na inicialização
        assert manager.get_state().visibility["ID"] is True

        # Tentar ocultar via set_visibility
        state = manager.set_visibility("ID", False)
        assert state.visibility["ID"] is True  # Deve permanecer visível

        # Tentar ocultar via toggle
        state = manager.toggle("ID")
        assert state.visibility["ID"] is True  # Deve permanecer visível

    def test_at_least_one_visible_enforcement(self):
        """Testa que pelo menos uma coluna está sempre visível."""
        manager = ColumnManager(["ID", "Nome"])

        # Ocultar primeira coluna
        manager.set_visibility("ID", False)
        assert manager.get_state().visibility["Nome"] is True

        # Tentar ocultar a última visível
        state = manager.set_visibility("Nome", False)
        assert state.visibility["Nome"] is True  # Deve permanecer visível


# ────────────────────────────────────────────────────────────────────────────────
# Tests: Edge Cases
# ────────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Testes de casos extremos e edge cases."""

    def test_single_column_always_visible(self):
        """Testa que uma única coluna nunca pode ser ocultada."""
        manager = ColumnManager(["ID"])
        state = manager.set_visibility("ID", False)
        assert state.visibility["ID"] is True

    def test_all_columns_mandatory(self):
        """Testa gerenciamento quando todas as colunas são obrigatórias."""
        manager = ColumnManager(
            ["ID", "Nome"],
            mandatory_columns={"ID", "Nome"},
        )
        state = manager.get_state()
        assert state.visibility["ID"] is True
        assert state.visibility["Nome"] is True

        # Nenhuma pode ser ocultada
        manager.toggle("ID")
        manager.toggle("Nome")
        state = manager.get_state()
        assert state.visibility["ID"] is True
        assert state.visibility["Nome"] is True

    def test_defensive_copy_in_get_state(self):
        """Testa que get_state retorna cópia defensiva."""
        manager = ColumnManager(["ID", "Nome"])
        state = manager.get_state()
        state.visibility["ID"] = False  # Modificar estado retornado

        # Estado interno não deve mudar
        new_state = manager.get_state()
        assert new_state.visibility["ID"] is True

    def test_column_order_immutability(self):
        """Testa que ordem de colunas não pode ser alterada após init."""
        manager = ColumnManager(["ID", "Nome", "CNPJ"])
        state1 = manager.get_state()
        manager.toggle("Nome")
        state2 = manager.get_state()
        # Ordem deve permanecer a mesma
        assert state1.order == state2.order
