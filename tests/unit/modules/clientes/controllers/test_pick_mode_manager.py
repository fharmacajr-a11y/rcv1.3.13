"""
Testes unitários para pick_mode_manager.py (MS-20 Pick Mode Management).

Este módulo testa PickModeSnapshot e PickModeManager de forma headless,
sem dependências do Tkinter. Segue o padrão estabelecido nas microfases anteriores.

Objetivo: Elevar a cobertura de ~55.2% para ≥85%.
Linhas não cobertas alvo: 85-86, 97-103, 111-112, 120, 128, 136.
"""

import pytest

from src.modules.clientes.controllers.pick_mode_manager import (
    PickModeManager,
    PickModeSnapshot,
)


# ────────────────────────────────────────────────────────────────────────────────
# Tests: PickModeSnapshot
# ────────────────────────────────────────────────────────────────────────────────


class TestPickModeSnapshot:
    """Testes do dataclass PickModeSnapshot."""

    def test_snapshot_creation_all_true(self):
        """Testa criação de snapshot com todas as flags True."""
        snapshot = PickModeSnapshot(
            is_pick_mode_active=True,
            should_disable_trash_button=True,
            should_disable_topbar_menus=True,
            should_show_pick_banner=True,
            should_disable_crud_buttons=True,
        )
        assert snapshot.is_pick_mode_active is True
        assert snapshot.should_disable_trash_button is True
        assert snapshot.should_disable_topbar_menus is True
        assert snapshot.should_show_pick_banner is True
        assert snapshot.should_disable_crud_buttons is True

    def test_snapshot_creation_all_false(self):
        """Testa criação de snapshot com todas as flags False."""
        snapshot = PickModeSnapshot(
            is_pick_mode_active=False,
            should_disable_trash_button=False,
            should_disable_topbar_menus=False,
            should_show_pick_banner=False,
            should_disable_crud_buttons=False,
        )
        assert snapshot.is_pick_mode_active is False
        assert snapshot.should_disable_trash_button is False
        assert snapshot.should_disable_topbar_menus is False
        assert snapshot.should_show_pick_banner is False
        assert snapshot.should_disable_crud_buttons is False

    def test_snapshot_immutability(self):
        """Testa imutabilidade do dataclass frozen."""
        snapshot = PickModeSnapshot(
            is_pick_mode_active=True,
            should_disable_trash_button=True,
            should_disable_topbar_menus=True,
            should_show_pick_banner=True,
            should_disable_crud_buttons=True,
        )
        with pytest.raises(AttributeError):
            snapshot.is_pick_mode_active = False  # type: ignore

    def test_snapshot_repr(self):
        """Testa __repr__ gerado automaticamente."""
        snapshot = PickModeSnapshot(
            is_pick_mode_active=True,
            should_disable_trash_button=True,
            should_disable_topbar_menus=True,
            should_show_pick_banner=True,
            should_disable_crud_buttons=True,
        )
        repr_str = repr(snapshot)
        assert "PickModeSnapshot" in repr_str
        assert "is_pick_mode_active" in repr_str


# ────────────────────────────────────────────────────────────────────────────────
# Tests: PickModeManager Initialization
# ────────────────────────────────────────────────────────────────────────────────


class TestPickModeManagerInit:
    """Testes de inicialização do PickModeManager."""

    def test_init_default_state(self):
        """Testa que PickModeManager inicia desativado (linhas 85-86)."""
        manager = PickModeManager()
        snapshot = manager.get_snapshot()
        assert snapshot.is_pick_mode_active is False
        assert snapshot.should_disable_trash_button is False
        assert snapshot.should_disable_topbar_menus is False
        assert snapshot.should_show_pick_banner is False
        assert snapshot.should_disable_crud_buttons is False

    def test_init_trash_button_state_is_none(self):
        """Testa que estado salvo da lixeira inicia como None (linha 86)."""
        manager = PickModeManager()
        # get_saved_trash_button_state() deve retornar "normal" quando None
        assert manager.get_saved_trash_button_state() == "normal"


# ────────────────────────────────────────────────────────────────────────────────
# Tests: PickModeManager.enter_pick_mode
# ────────────────────────────────────────────────────────────────────────────────


class TestEnterPickMode:
    """Testes do método enter_pick_mode (linhas 97-103)."""

    def test_enter_pick_mode_without_trash_state(self):
        """Testa entrada em pick mode sem passar estado da lixeira (linha 100)."""
        manager = PickModeManager()
        snapshot = manager.enter_pick_mode()

        assert snapshot.is_pick_mode_active is True
        assert snapshot.should_disable_trash_button is True
        assert snapshot.should_disable_topbar_menus is True
        assert snapshot.should_show_pick_banner is True
        assert snapshot.should_disable_crud_buttons is True

    def test_enter_pick_mode_with_trash_state_normal(self):
        """Testa entrada em pick mode passando estado 'normal' (linhas 97-103)."""
        manager = PickModeManager()
        snapshot = manager.enter_pick_mode(trash_button_current_state="normal")

        assert snapshot.is_pick_mode_active is True
        assert manager.get_saved_trash_button_state() == "normal"

    def test_enter_pick_mode_with_trash_state_disabled(self):
        """Testa entrada em pick mode passando estado 'disabled' (linhas 97-103)."""
        manager = PickModeManager()
        snapshot = manager.enter_pick_mode(trash_button_current_state="disabled")

        assert snapshot.is_pick_mode_active is True
        assert manager.get_saved_trash_button_state() == "disabled"

    def test_enter_pick_mode_twice(self):
        """Testa entrar em pick mode quando já está ativo."""
        manager = PickModeManager()
        snapshot1 = manager.enter_pick_mode(trash_button_current_state="normal")
        assert snapshot1.is_pick_mode_active is True

        # Entrar novamente (sobrescreve estado salvo)
        snapshot2 = manager.enter_pick_mode(trash_button_current_state="disabled")
        assert snapshot2.is_pick_mode_active is True
        assert manager.get_saved_trash_button_state() == "disabled"

    def test_enter_pick_mode_preserves_trash_state_if_none(self):
        """Testa que estado da lixeira não é sobrescrito se passar None."""
        manager = PickModeManager()
        manager.enter_pick_mode(trash_button_current_state="disabled")
        assert manager.get_saved_trash_button_state() == "disabled"

        # Entrar novamente sem passar estado (não deve sobrescrever)
        manager.enter_pick_mode(trash_button_current_state=None)
        # Estado anterior deve ser preservado
        assert manager.get_saved_trash_button_state() == "disabled"


# ────────────────────────────────────────────────────────────────────────────────
# Tests: PickModeManager.exit_pick_mode
# ────────────────────────────────────────────────────────────────────────────────


class TestExitPickMode:
    """Testes do método exit_pick_mode (linhas 111-112)."""

    def test_exit_pick_mode_when_active(self):
        """Testa saída de pick mode quando está ativo (linhas 111-112)."""
        manager = PickModeManager()
        manager.enter_pick_mode()
        assert manager.get_snapshot().is_pick_mode_active is True

        snapshot = manager.exit_pick_mode()
        assert snapshot.is_pick_mode_active is False
        assert snapshot.should_disable_trash_button is False
        assert snapshot.should_disable_topbar_menus is False
        assert snapshot.should_show_pick_banner is False
        assert snapshot.should_disable_crud_buttons is False

    def test_exit_pick_mode_when_already_inactive(self):
        """Testa saída de pick mode quando já está desativado."""
        manager = PickModeManager()
        # Já inicia desativado
        snapshot = manager.exit_pick_mode()
        assert snapshot.is_pick_mode_active is False

    def test_exit_pick_mode_preserves_saved_trash_state(self):
        """Testa que estado salvo da lixeira é preservado após sair."""
        manager = PickModeManager()
        manager.enter_pick_mode(trash_button_current_state="disabled")
        manager.exit_pick_mode()

        # Estado salvo deve permanecer
        assert manager.get_saved_trash_button_state() == "disabled"


# ────────────────────────────────────────────────────────────────────────────────
# Tests: PickModeManager.get_snapshot
# ────────────────────────────────────────────────────────────────────────────────


class TestGetSnapshot:
    """Testes do método get_snapshot (linha 120)."""

    def test_get_snapshot_when_inactive(self):
        """Testa get_snapshot quando pick mode está desativado (linha 120)."""
        manager = PickModeManager()
        snapshot = manager.get_snapshot()
        assert snapshot.is_pick_mode_active is False
        assert snapshot.should_disable_trash_button is False

    def test_get_snapshot_when_active(self):
        """Testa get_snapshot quando pick mode está ativo (linha 120)."""
        manager = PickModeManager()
        manager.enter_pick_mode()
        snapshot = manager.get_snapshot()
        assert snapshot.is_pick_mode_active is True
        assert snapshot.should_disable_trash_button is True

    def test_get_snapshot_is_idempotent(self):
        """Testa que get_snapshot não altera o estado."""
        manager = PickModeManager()
        manager.enter_pick_mode()

        snapshot1 = manager.get_snapshot()
        snapshot2 = manager.get_snapshot()

        assert snapshot1.is_pick_mode_active == snapshot2.is_pick_mode_active
        assert snapshot1.should_disable_trash_button == snapshot2.should_disable_trash_button


# ────────────────────────────────────────────────────────────────────────────────
# Tests: PickModeManager.get_saved_trash_button_state
# ────────────────────────────────────────────────────────────────────────────────


class TestGetSavedTrashButtonState:
    """Testes do método get_saved_trash_button_state (linha 128)."""

    def test_get_saved_trash_button_state_default(self):
        """Testa retorno padrão quando não há estado salvo (linha 128)."""
        manager = PickModeManager()
        assert manager.get_saved_trash_button_state() == "normal"

    def test_get_saved_trash_button_state_after_enter_with_normal(self):
        """Testa retorno após entrar em pick mode com 'normal' (linha 128)."""
        manager = PickModeManager()
        manager.enter_pick_mode(trash_button_current_state="normal")
        assert manager.get_saved_trash_button_state() == "normal"

    def test_get_saved_trash_button_state_after_enter_with_disabled(self):
        """Testa retorno após entrar em pick mode com 'disabled' (linha 128)."""
        manager = PickModeManager()
        manager.enter_pick_mode(trash_button_current_state="disabled")
        assert manager.get_saved_trash_button_state() == "disabled"

    def test_get_saved_trash_button_state_persists_after_exit(self):
        """Testa que estado salvo persiste após sair de pick mode."""
        manager = PickModeManager()
        manager.enter_pick_mode(trash_button_current_state="disabled")
        manager.exit_pick_mode()
        assert manager.get_saved_trash_button_state() == "disabled"


# ────────────────────────────────────────────────────────────────────────────────
# Tests: PickModeManager._build_snapshot (private method coverage)
# ────────────────────────────────────────────────────────────────────────────────


class TestBuildSnapshot:
    """Testes indiretos do método _build_snapshot (linha 136)."""

    def test_build_snapshot_inactive_state(self):
        """Testa snapshot construído quando inativo (linha 136)."""
        manager = PickModeManager()
        snapshot = manager._build_snapshot()  # type: ignore
        assert snapshot.is_pick_mode_active is False
        assert snapshot.should_disable_trash_button is False
        assert snapshot.should_disable_topbar_menus is False
        assert snapshot.should_show_pick_banner is False
        assert snapshot.should_disable_crud_buttons is False

    def test_build_snapshot_active_state(self):
        """Testa snapshot construído quando ativo (linha 136)."""
        manager = PickModeManager()
        manager.enter_pick_mode()
        snapshot = manager._build_snapshot()  # type: ignore
        assert snapshot.is_pick_mode_active is True
        assert snapshot.should_disable_trash_button is True
        assert snapshot.should_disable_topbar_menus is True
        assert snapshot.should_show_pick_banner is True
        assert snapshot.should_disable_crud_buttons is True

    def test_build_snapshot_flags_consistency(self):
        """Testa que todas as flags seguem o estado ativo/inativo consistentemente."""
        manager = PickModeManager()

        # Desativado: todas as flags devem ser False
        manager._active = False  # type: ignore
        snapshot_inactive = manager._build_snapshot()  # type: ignore
        assert snapshot_inactive.is_pick_mode_active is False
        assert snapshot_inactive.should_disable_trash_button is False
        assert snapshot_inactive.should_disable_topbar_menus is False
        assert snapshot_inactive.should_show_pick_banner is False
        assert snapshot_inactive.should_disable_crud_buttons is False

        # Ativado: todas as flags devem ser True
        manager._active = True  # type: ignore
        snapshot_active = manager._build_snapshot()  # type: ignore
        assert snapshot_active.is_pick_mode_active is True
        assert snapshot_active.should_disable_trash_button is True
        assert snapshot_active.should_disable_topbar_menus is True
        assert snapshot_active.should_show_pick_banner is True
        assert snapshot_active.should_disable_crud_buttons is True


# ────────────────────────────────────────────────────────────────────────────────
# Tests: Integration Scenarios
# ────────────────────────────────────────────────────────────────────────────────


class TestPickModeIntegration:
    """Testes de cenários completos de uso do PickModeManager."""

    def test_full_lifecycle_enter_exit(self):
        """Testa ciclo completo: criar → entrar → sair."""
        manager = PickModeManager()

        # Estado inicial
        assert manager.get_snapshot().is_pick_mode_active is False

        # Entrar em pick mode
        enter_snapshot = manager.enter_pick_mode(trash_button_current_state="normal")
        assert enter_snapshot.is_pick_mode_active is True
        assert enter_snapshot.should_show_pick_banner is True

        # Verificar estado intermediário
        assert manager.get_snapshot().is_pick_mode_active is True

        # Sair de pick mode
        exit_snapshot = manager.exit_pick_mode()
        assert exit_snapshot.is_pick_mode_active is False
        assert exit_snapshot.should_show_pick_banner is False

        # Verificar estado final
        assert manager.get_snapshot().is_pick_mode_active is False

    def test_multiple_enter_exit_cycles(self):
        """Testa múltiplos ciclos de entrar/sair."""
        manager = PickModeManager()

        for i in range(3):
            # Entrar
            manager.enter_pick_mode(trash_button_current_state="normal")
            assert manager.get_snapshot().is_pick_mode_active is True

            # Sair
            manager.exit_pick_mode()
            assert manager.get_snapshot().is_pick_mode_active is False

    def test_trash_button_state_preservation_scenario(self):
        """Testa cenário real de preservação do estado da lixeira."""
        manager = PickModeManager()

        # Usuário tem lixeira desabilitada (sem seleção)
        manager.enter_pick_mode(trash_button_current_state="disabled")
        assert manager.get_saved_trash_button_state() == "disabled"

        # Durante pick mode, usuário seleciona itens (mas lixeira continua desabilitada)
        assert manager.get_snapshot().should_disable_trash_button is True

        # Sair de pick mode: deve restaurar "disabled"
        manager.exit_pick_mode()
        assert manager.get_saved_trash_button_state() == "disabled"

    def test_trash_button_state_overwrite_scenario(self):
        """Testa cenário onde estado da lixeira é sobrescrito."""
        manager = PickModeManager()

        # Primeira entrada: lixeira normal
        manager.enter_pick_mode(trash_button_current_state="normal")
        assert manager.get_saved_trash_button_state() == "normal"

        # Segunda entrada (sem sair): lixeira disabled
        manager.enter_pick_mode(trash_button_current_state="disabled")
        assert manager.get_saved_trash_button_state() == "disabled"


# ────────────────────────────────────────────────────────────────────────────────
# Tests: Edge Cases
# ────────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Testes de casos extremos e edge cases."""

    def test_exit_without_enter(self):
        """Testa sair de pick mode sem nunca ter entrado."""
        manager = PickModeManager()
        snapshot = manager.exit_pick_mode()
        assert snapshot.is_pick_mode_active is False

    def test_multiple_consecutive_enters(self):
        """Testa múltiplas entradas consecutivas sem sair."""
        manager = PickModeManager()

        manager.enter_pick_mode(trash_button_current_state="normal")
        manager.enter_pick_mode(trash_button_current_state="disabled")
        manager.enter_pick_mode(trash_button_current_state="normal")

        assert manager.get_snapshot().is_pick_mode_active is True
        assert manager.get_saved_trash_button_state() == "normal"

    def test_multiple_consecutive_exits(self):
        """Testa múltiplas saídas consecutivas."""
        manager = PickModeManager()
        manager.enter_pick_mode()

        manager.exit_pick_mode()
        manager.exit_pick_mode()
        manager.exit_pick_mode()

        assert manager.get_snapshot().is_pick_mode_active is False

    def test_get_snapshot_immutability_across_state_changes(self):
        """Testa que snapshots antigos permanecem imutáveis após mudança de estado."""
        manager = PickModeManager()

        # Snapshot inativo
        snapshot_inactive = manager.get_snapshot()
        assert snapshot_inactive.is_pick_mode_active is False

        # Entrar em pick mode
        manager.enter_pick_mode()

        # Snapshot antigo deve permanecer inalterado (imutável)
        assert snapshot_inactive.is_pick_mode_active is False

        # Novo snapshot deve refletir estado ativo
        snapshot_active = manager.get_snapshot()
        assert snapshot_active.is_pick_mode_active is True

    def test_trash_button_state_with_empty_string(self):
        """Testa entrada com string vazia como estado da lixeira (tratado como None)."""
        manager = PickModeManager()
        manager.enter_pick_mode(trash_button_current_state="")
        # String vazia é falsy, então não é salvo (retorna default "normal")
        assert manager.get_saved_trash_button_state() == "normal"

    def test_trash_button_state_with_custom_value(self):
        """Testa entrada com valor customizado de estado."""
        manager = PickModeManager()
        manager.enter_pick_mode(trash_button_current_state="active")
        assert manager.get_saved_trash_button_state() == "active"
