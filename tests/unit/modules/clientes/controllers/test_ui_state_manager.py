"""
Testes unitários para ui_state_manager.py (MS-18 UI State Management).

Este módulo testa UiStateManager de forma headless, sem dependências do Tkinter.
Segue o padrão estabelecido nas microfases anteriores.

Objetivo: Elevar a cobertura de ~61.0% para ≥85%.
Linhas não cobertas alvo: 113-126, 151-159.
"""

import pytest

from src.modules.clientes.controllers.ui_state_manager import (
    ButtonStatesSnapshot,
    UiStateInput,
    UiStateManager,
)


# ────────────────────────────────────────────────────────────────────────────────
# Tests: ButtonStatesSnapshot
# ────────────────────────────────────────────────────────────────────────────────


class TestButtonStatesSnapshot:
    """Testes do dataclass ButtonStatesSnapshot."""

    def test_snapshot_creation_all_enabled(self):
        """Testa criação de snapshot com todos os botões habilitados."""
        snapshot = ButtonStatesSnapshot(
            editar=True,
            subpastas=True,
            enviar=True,
            novo=True,
            lixeira=True,
            select=True,
            enviar_text="Enviar Para SupaBase",
        )
        assert snapshot.editar is True
        assert snapshot.subpastas is True
        assert snapshot.enviar is True
        assert snapshot.novo is True
        assert snapshot.lixeira is True
        assert snapshot.select is True
        assert snapshot.enviar_text == "Enviar Para SupaBase"

    def test_snapshot_creation_all_disabled(self):
        """Testa criação de snapshot com todos os botões desabilitados."""
        snapshot = ButtonStatesSnapshot(
            editar=False,
            subpastas=False,
            enviar=False,
            novo=False,
            lixeira=False,
            select=False,
            enviar_text="Envio suspenso - Offline",
        )
        assert snapshot.editar is False
        assert snapshot.subpastas is False
        assert snapshot.enviar is False
        assert snapshot.novo is False
        assert snapshot.lixeira is False
        assert snapshot.select is False
        assert snapshot.enviar_text == "Envio suspenso - Offline"

    def test_snapshot_default_enviar_text(self):
        """Testa valor padrão do enviar_text."""
        snapshot = ButtonStatesSnapshot(
            editar=True,
            subpastas=True,
            enviar=True,
            novo=True,
            lixeira=True,
            select=True,
        )
        assert snapshot.enviar_text == "Enviar Para SupaBase"

    def test_snapshot_immutability(self):
        """Testa imutabilidade do dataclass frozen."""
        snapshot = ButtonStatesSnapshot(
            editar=True,
            subpastas=True,
            enviar=True,
            novo=True,
            lixeira=True,
            select=True,
        )
        with pytest.raises(AttributeError):
            snapshot.editar = False  # type: ignore

    def test_snapshot_repr(self):
        """Testa __repr__ gerado automaticamente."""
        snapshot = ButtonStatesSnapshot(
            editar=True,
            subpastas=False,
            enviar=True,
            novo=False,
            lixeira=True,
            select=False,
        )
        repr_str = repr(snapshot)
        assert "ButtonStatesSnapshot" in repr_str
        assert "editar" in repr_str


# ────────────────────────────────────────────────────────────────────────────────
# Tests: UiStateInput
# ────────────────────────────────────────────────────────────────────────────────


class TestUiStateInput:
    """Testes do dataclass UiStateInput."""

    def test_input_creation_basic(self):
        """Testa criação de UiStateInput com campos obrigatórios."""
        inp = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
        )
        assert inp.has_selection is True
        assert inp.is_online is True
        assert inp.is_uploading is False
        assert inp.is_pick_mode is False  # default
        assert inp.connectivity_state == "online"  # default

    def test_input_creation_with_all_fields(self):
        """Testa criação de UiStateInput com todos os campos."""
        inp = UiStateInput(
            has_selection=True,
            is_online=False,
            is_uploading=True,
            is_pick_mode=True,
            connectivity_state="unstable",
        )
        assert inp.has_selection is True
        assert inp.is_online is False
        assert inp.is_uploading is True
        assert inp.is_pick_mode is True
        assert inp.connectivity_state == "unstable"

    def test_input_connectivity_states(self):
        """Testa todos os valores válidos de connectivity_state."""
        for state in ["online", "unstable", "offline"]:
            inp = UiStateInput(
                has_selection=False,
                is_online=False,
                is_uploading=False,
                connectivity_state=state,  # type: ignore
            )
            assert inp.connectivity_state == state

    def test_input_immutability(self):
        """Testa imutabilidade do dataclass frozen."""
        inp = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
        )
        with pytest.raises(AttributeError):
            inp.has_selection = False  # type: ignore


# ────────────────────────────────────────────────────────────────────────────────
# Tests: UiStateManager.compute_button_states (linhas 113-126)
# ────────────────────────────────────────────────────────────────────────────────


class TestComputeButtonStates:
    """Testes do método compute_button_states (linhas 113-126)."""

    def test_compute_online_with_selection(self):
        """Testa cálculo de estados quando online com seleção (linhas 113-126)."""
        manager = UiStateManager()
        inp = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
        )
        snapshot = manager.compute_button_states(inp)

        # Botões que dependem de seleção + online devem estar habilitados
        assert snapshot.editar is True
        assert snapshot.subpastas is True
        assert snapshot.enviar is True

        # Botões que dependem apenas de online
        assert snapshot.novo is True
        assert snapshot.lixeira is True

        # Select depende de pick_mode (False aqui)
        assert snapshot.select is False

        # Texto padrão quando online e não uploading
        assert snapshot.enviar_text == "Enviar Para SupaBase"

    def test_compute_online_without_selection(self):
        """Testa cálculo de estados quando online sem seleção (linhas 113-126)."""
        manager = UiStateManager()
        inp = UiStateInput(
            has_selection=False,
            is_online=True,
            is_uploading=False,
        )
        snapshot = manager.compute_button_states(inp)

        # Botões que dependem de seleção devem estar desabilitados
        assert snapshot.editar is False
        assert snapshot.subpastas is False
        assert snapshot.enviar is False

        # Botões que dependem apenas de online
        assert snapshot.novo is True
        assert snapshot.lixeira is True

    def test_compute_offline_with_selection(self):
        """Testa cálculo de estados quando offline com seleção (linhas 113-126)."""
        manager = UiStateManager()
        inp = UiStateInput(
            has_selection=True,
            is_online=False,
            is_uploading=False,
            connectivity_state="offline",
        )
        snapshot = manager.compute_button_states(inp)

        # Todos os botões devem estar desabilitados quando offline
        assert snapshot.editar is False
        assert snapshot.subpastas is False
        assert snapshot.enviar is False
        assert snapshot.novo is False
        assert snapshot.lixeira is False

        # Texto reflete estado offline
        assert snapshot.enviar_text == "Envio suspenso - Offline"

    def test_compute_unstable_with_selection(self):
        """Testa cálculo de estados quando conexão instável (linhas 113-126)."""
        manager = UiStateManager()
        inp = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
            connectivity_state="unstable",
        )
        snapshot = manager.compute_button_states(inp)

        # Botões devem seguir lógica normal (is_online=True)
        assert snapshot.editar is True
        assert snapshot.subpastas is True
        assert snapshot.enviar is True

        # Texto reflete conexão instável
        assert snapshot.enviar_text == "Envio suspenso - Conexao instavel"

    def test_compute_uploading_state(self):
        """Testa cálculo de estados durante upload (linhas 113-126)."""
        manager = UiStateManager()
        inp = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=True,
        )
        snapshot = manager.compute_button_states(inp)

        # Botão Enviar deve estar desabilitado durante upload
        assert snapshot.enviar is False

        # Outros botões dependem de outros fatores
        assert snapshot.editar is True
        assert snapshot.subpastas is True

        # Texto reflete estado de upload
        assert snapshot.enviar_text == "Enviando..."

    def test_compute_pick_mode_with_selection(self):
        """Testa cálculo de estados em pick mode com seleção (linhas 113-126)."""
        manager = UiStateManager()
        inp = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
            is_pick_mode=True,
        )
        snapshot = manager.compute_button_states(inp)

        # Botão Select deve estar habilitado em pick mode com seleção
        assert snapshot.select is True

    def test_compute_pick_mode_without_selection(self):
        """Testa cálculo de estados em pick mode sem seleção (linhas 113-126)."""
        manager = UiStateManager()
        inp = UiStateInput(
            has_selection=False,
            is_online=True,
            is_uploading=False,
            is_pick_mode=True,
        )
        snapshot = manager.compute_button_states(inp)

        # Botão Select deve estar desabilitado sem seleção
        assert snapshot.select is False

    def test_compute_all_disabled_scenario(self):
        """Testa cenário onde todos os botões estão desabilitados."""
        manager = UiStateManager()
        inp = UiStateInput(
            has_selection=False,
            is_online=False,
            is_uploading=False,
            is_pick_mode=False,
            connectivity_state="offline",
        )
        snapshot = manager.compute_button_states(inp)

        assert snapshot.editar is False
        assert snapshot.subpastas is False
        assert snapshot.enviar is False
        assert snapshot.novo is False
        assert snapshot.lixeira is False
        assert snapshot.select is False


# ────────────────────────────────────────────────────────────────────────────────
# Tests: UiStateManager._compute_enviar_text (linhas 151-159)
# ────────────────────────────────────────────────────────────────────────────────


class TestComputeEnviarText:
    """Testes do método _compute_enviar_text (linhas 151-159)."""

    def test_enviar_text_uploading(self):
        """Testa texto quando está fazendo upload (linha 152)."""
        manager = UiStateManager()
        text = manager._compute_enviar_text(  # type: ignore
            connectivity_state="online",
            is_uploading=True,
        )
        assert text == "Enviando..."

    def test_enviar_text_uploading_offline(self):
        """Testa texto quando está fazendo upload mesmo offline."""
        manager = UiStateManager()
        text = manager._compute_enviar_text(  # type: ignore
            connectivity_state="offline",
            is_uploading=True,
        )
        # is_uploading tem prioridade
        assert text == "Enviando..."

    def test_enviar_text_online(self):
        """Testa texto quando online e não uploading (linha 155)."""
        manager = UiStateManager()
        text = manager._compute_enviar_text(  # type: ignore
            connectivity_state="online",
            is_uploading=False,
        )
        assert text == "Enviar Para SupaBase"

    def test_enviar_text_unstable(self):
        """Testa texto quando conexão instável (linha 157)."""
        manager = UiStateManager()
        text = manager._compute_enviar_text(  # type: ignore
            connectivity_state="unstable",
            is_uploading=False,
        )
        assert text == "Envio suspenso - Conexao instavel"

    def test_enviar_text_offline(self):
        """Testa texto quando offline (linha 159)."""
        manager = UiStateManager()
        text = manager._compute_enviar_text(  # type: ignore
            connectivity_state="offline",
            is_uploading=False,
        )
        assert text == "Envio suspenso - Offline"


# ────────────────────────────────────────────────────────────────────────────────
# Tests: Integration Scenarios
# ────────────────────────────────────────────────────────────────────────────────


class TestUiStateManagerIntegration:
    """Testes de cenários completos de uso do UiStateManager."""

    def test_full_workflow_online_to_offline(self):
        """Testa transição de online para offline."""
        manager = UiStateManager()

        # Estado online com seleção
        inp_online = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
            connectivity_state="online",
        )
        snapshot_online = manager.compute_button_states(inp_online)
        assert snapshot_online.editar is True
        assert snapshot_online.novo is True
        assert snapshot_online.enviar_text == "Enviar Para SupaBase"

        # Transição para offline
        inp_offline = UiStateInput(
            has_selection=True,
            is_online=False,
            is_uploading=False,
            connectivity_state="offline",
        )
        snapshot_offline = manager.compute_button_states(inp_offline)
        assert snapshot_offline.editar is False
        assert snapshot_offline.novo is False
        assert snapshot_offline.enviar_text == "Envio suspenso - Offline"

    def test_upload_lifecycle(self):
        """Testa ciclo de vida de upload."""
        manager = UiStateManager()

        # Antes do upload
        inp_before = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
        )
        snapshot_before = manager.compute_button_states(inp_before)
        assert snapshot_before.enviar is True
        assert snapshot_before.enviar_text == "Enviar Para SupaBase"

        # Durante upload
        inp_during = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=True,
        )
        snapshot_during = manager.compute_button_states(inp_during)
        assert snapshot_during.enviar is False
        assert snapshot_during.enviar_text == "Enviando..."

        # Depois do upload
        inp_after = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
        )
        snapshot_after = manager.compute_button_states(inp_after)
        assert snapshot_after.enviar is True
        assert snapshot_after.enviar_text == "Enviar Para SupaBase"

    def test_pick_mode_workflow(self):
        """Testa fluxo de pick mode."""
        manager = UiStateManager()

        # Modo normal sem seleção
        inp_normal = UiStateInput(
            has_selection=False,
            is_online=True,
            is_uploading=False,
            is_pick_mode=False,
        )
        snapshot_normal = manager.compute_button_states(inp_normal)
        assert snapshot_normal.select is False

        # Entrar em pick mode sem seleção
        inp_pick_no_sel = UiStateInput(
            has_selection=False,
            is_online=True,
            is_uploading=False,
            is_pick_mode=True,
        )
        snapshot_pick_no_sel = manager.compute_button_states(inp_pick_no_sel)
        assert snapshot_pick_no_sel.select is False

        # Selecionar item em pick mode
        inp_pick_with_sel = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
            is_pick_mode=True,
        )
        snapshot_pick_with_sel = manager.compute_button_states(inp_pick_with_sel)
        assert snapshot_pick_with_sel.select is True

    def test_unstable_connection_recovery(self):
        """Testa recuperação de conexão instável."""
        manager = UiStateManager()

        # Conexão instável
        inp_unstable = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
            connectivity_state="unstable",
        )
        snapshot_unstable = manager.compute_button_states(inp_unstable)
        assert snapshot_unstable.enviar_text == "Envio suspenso - Conexao instavel"
        # Botões ainda funcionam (is_online=True)
        assert snapshot_unstable.editar is True

        # Recuperação para online
        inp_recovered = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
            connectivity_state="online",
        )
        snapshot_recovered = manager.compute_button_states(inp_recovered)
        assert snapshot_recovered.enviar_text == "Enviar Para SupaBase"
        assert snapshot_recovered.editar is True

    def test_manager_is_stateless(self):
        """Testa que UiStateManager é stateless (sem estado interno)."""
        manager = UiStateManager()

        # Primeira chamada
        inp1 = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
        )
        snapshot1 = manager.compute_button_states(inp1)
        assert snapshot1.editar is True

        # Segunda chamada com input diferente (não deve ser influenciada pela primeira)
        inp2 = UiStateInput(
            has_selection=False,
            is_online=False,
            is_uploading=False,
        )
        snapshot2 = manager.compute_button_states(inp2)
        assert snapshot2.editar is False

        # Terceira chamada igual à primeira (resultado deve ser idêntico)
        snapshot3 = manager.compute_button_states(inp1)
        assert snapshot3.editar == snapshot1.editar
        assert snapshot3.enviar_text == snapshot1.enviar_text


# ────────────────────────────────────────────────────────────────────────────────
# Tests: Edge Cases
# ────────────────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Testes de casos extremos e edge cases."""

    def test_multiple_manager_instances(self):
        """Testa que múltiplas instâncias se comportam identicamente."""
        manager1 = UiStateManager()
        manager2 = UiStateManager()

        inp = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
        )

        snapshot1 = manager1.compute_button_states(inp)
        snapshot2 = manager2.compute_button_states(inp)

        assert snapshot1.editar == snapshot2.editar
        assert snapshot1.enviar_text == snapshot2.enviar_text

    def test_snapshot_immutability_across_compute_calls(self):
        """Testa que snapshots antigos não mudam após novas computações."""
        manager = UiStateManager()

        inp1 = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
        )
        snapshot1 = manager.compute_button_states(inp1)
        assert snapshot1.editar is True

        # Nova computação com input diferente
        inp2 = UiStateInput(
            has_selection=False,
            is_online=False,
            is_uploading=False,
        )
        snapshot2 = manager.compute_button_states(inp2)

        # snapshot1 deve permanecer inalterado (imutável)
        assert snapshot1.editar is True
        assert snapshot2.editar is False

    def test_all_connectivity_states_covered(self):
        """Testa que todos os estados de conectividade geram textos distintos."""
        manager = UiStateManager()

        texts_collected: set[str] = set()

        for state in ["online", "unstable", "offline"]:
            inp = UiStateInput(
                has_selection=True,
                is_online=(state == "online"),
                is_uploading=False,
                connectivity_state=state,  # type: ignore
            )
            snapshot = manager.compute_button_states(inp)
            texts_collected.add(snapshot.enviar_text)

        # Deve ter 3 textos distintos
        assert len(texts_collected) == 3
        assert "Enviar Para SupaBase" in texts_collected
        assert "Envio suspenso - Conexao instavel" in texts_collected
        assert "Envio suspenso - Offline" in texts_collected

    def test_uploading_overrides_connectivity_text(self):
        """Testa que is_uploading tem prioridade sobre connectivity_state no texto."""
        manager = UiStateManager()

        for state in ["online", "unstable", "offline"]:
            inp = UiStateInput(
                has_selection=True,
                is_online=True,
                is_uploading=True,
                connectivity_state=state,  # type: ignore
            )
            snapshot = manager.compute_button_states(inp)
            # Sempre "Enviando..." quando is_uploading=True
            assert snapshot.enviar_text == "Enviando..."

    def test_contradictory_input_is_online_false_connectivity_online(self):
        """Testa input contraditório: is_online=False mas connectivity_state=online."""
        manager = UiStateManager()
        inp = UiStateInput(
            has_selection=True,
            is_online=False,  # Diz que está offline
            is_uploading=False,
            connectivity_state="online",  # Mas connectivity_state diz online
        )
        snapshot = manager.compute_button_states(inp)

        # Botões seguem is_online (desabilitados)
        assert snapshot.editar is False
        assert snapshot.novo is False

        # Texto segue connectivity_state (online)
        assert snapshot.enviar_text == "Enviar Para SupaBase"

    def test_init_creates_usable_manager(self):
        """Testa que __init__ cria um manager utilizável."""
        manager = UiStateManager()
        inp = UiStateInput(
            has_selection=True,
            is_online=True,
            is_uploading=False,
        )
        # Não deve lançar exceção
        snapshot = manager.compute_button_states(inp)
        assert isinstance(snapshot, ButtonStatesSnapshot)
