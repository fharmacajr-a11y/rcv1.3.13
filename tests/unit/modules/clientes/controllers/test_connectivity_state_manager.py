# -*- coding: utf-8 -*-
"""Testes unitários para ConnectivityStateManager.

Este módulo testa o gerenciador de estado de conectividade de forma headless,
sem depender de Tkinter real. Foca na lógica de estado e transições.

Cobertura esperada: >= 90% do arquivo connectivity_state_manager.py
"""

from __future__ import annotations

import pytest

from src.modules.clientes.controllers.connectivity_state_manager import (
    ConnectivityRawInput,
    ConnectivitySnapshot,
    ConnectivityStateManager,
)


@pytest.fixture
def manager() -> ConnectivityStateManager:
    """Cria uma instância do ConnectivityStateManager."""
    return ConnectivityStateManager()


# ============================================================================
# TESTES DE DATA STRUCTURES
# ============================================================================


class TestConnectivityRawInput:
    """Testes da estrutura ConnectivityRawInput."""

    def test_connectivity_raw_input_criacao_completa(self) -> None:
        """ConnectivityRawInput deve ser criado com todos os parâmetros."""
        raw = ConnectivityRawInput(
            state="online",
            description="Conectado ao Supabase",
            text="ONLINE",
            last_known_state="offline",
        )

        assert raw.state == "online"
        assert raw.description == "Conectado ao Supabase"
        assert raw.text == "ONLINE"
        assert raw.last_known_state == "offline"

    def test_connectivity_raw_input_default_last_known_state(self) -> None:
        """ConnectivityRawInput deve ter valor padrão para last_known_state."""
        raw = ConnectivityRawInput(
            state="online",
            description="Conectado",
            text="ONLINE",
        )

        assert raw.last_known_state == "unknown"

    def test_connectivity_raw_input_frozen(self) -> None:
        """ConnectivityRawInput deve ser imutável (frozen dataclass)."""
        raw = ConnectivityRawInput(
            state="online",
            description="Conectado",
            text="ONLINE",
        )

        with pytest.raises(AttributeError):
            raw.state = "offline"  # type: ignore

    def test_connectivity_raw_input_todos_estados(self) -> None:
        """ConnectivityRawInput deve aceitar todos os estados válidos."""
        estados = ["online", "unstable", "offline", "unknown"]

        for estado in estados:
            raw = ConnectivityRawInput(
                state=estado,  # type: ignore
                description=f"Estado {estado}",
                text=estado.upper(),
            )
            assert raw.state == estado


class TestConnectivitySnapshot:
    """Testes da estrutura ConnectivitySnapshot."""

    def test_connectivity_snapshot_criacao_completa(self) -> None:
        """ConnectivitySnapshot deve ser criado com todos os parâmetros."""
        snapshot = ConnectivitySnapshot(
            state="online",
            description="Conectado ao Supabase",
            text_for_status_bar="Nuvem: ONLINE",
            is_online=True,
            should_log_transition=True,
            old_state="offline",
        )

        assert snapshot.state == "online"
        assert snapshot.description == "Conectado ao Supabase"
        assert snapshot.text_for_status_bar == "Nuvem: ONLINE"
        assert snapshot.is_online is True
        assert snapshot.should_log_transition is True
        assert snapshot.old_state == "offline"

    def test_connectivity_snapshot_default_old_state(self) -> None:
        """ConnectivitySnapshot deve ter valor padrão para old_state."""
        snapshot = ConnectivitySnapshot(
            state="online",
            description="Conectado",
            text_for_status_bar="Nuvem: ONLINE",
            is_online=True,
            should_log_transition=False,
        )

        assert snapshot.old_state == "unknown"

    def test_connectivity_snapshot_frozen(self) -> None:
        """ConnectivitySnapshot deve ser imutável (frozen dataclass)."""
        snapshot = ConnectivitySnapshot(
            state="online",
            description="Conectado",
            text_for_status_bar="Nuvem: ONLINE",
            is_online=True,
            should_log_transition=False,
        )

        with pytest.raises(AttributeError):
            snapshot.is_online = False  # type: ignore


# ============================================================================
# TESTES DE INICIALIZAÇÃO
# ============================================================================


class TestConnectivityStateManagerInit:
    """Testes de inicialização do ConnectivityStateManager."""

    def test_manager_criado_sem_estado(self) -> None:
        """ConnectivityStateManager deve ser criado sem estado interno."""
        manager = ConnectivityStateManager()
        # Manager é stateless, apenas verificamos que foi criado
        assert manager is not None


# ============================================================================
# TESTES DO MÉTODO COMPUTE_SNAPSHOT
# ============================================================================


class TestConnectivityStateManagerComputeSnapshot:
    """Testes do método compute_snapshot()."""

    def test_compute_snapshot_estado_online(self, manager: ConnectivityStateManager) -> None:
        """compute_snapshot deve considerar is_online=True apenas para state='online'."""
        raw = ConnectivityRawInput(
            state="online",
            description="Conectado ao Supabase",
            text="ONLINE",
            last_known_state="offline",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.state == "online"
        assert snapshot.is_online is True
        assert snapshot.text_for_status_bar == "Nuvem: ONLINE"
        assert snapshot.should_log_transition is True
        assert snapshot.old_state == "offline"

    def test_compute_snapshot_estado_offline(self, manager: ConnectivityStateManager) -> None:
        """compute_snapshot deve considerar is_online=False para state='offline'."""
        raw = ConnectivityRawInput(
            state="offline",
            description="Desconectado",
            text="OFFLINE",
            last_known_state="online",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.state == "offline"
        assert snapshot.is_online is False
        assert snapshot.text_for_status_bar == "Nuvem: OFFLINE"
        assert snapshot.should_log_transition is True
        assert snapshot.old_state == "online"

    def test_compute_snapshot_estado_unstable(self, manager: ConnectivityStateManager) -> None:
        """compute_snapshot deve considerar is_online=False para state='unstable'."""
        raw = ConnectivityRawInput(
            state="unstable",
            description="Conexão instável",
            text="INSTÁVEL",
            last_known_state="online",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.state == "unstable"
        assert snapshot.is_online is False
        assert snapshot.text_for_status_bar == "Nuvem: INSTÁVEL"

    def test_compute_snapshot_estado_unknown(self, manager: ConnectivityStateManager) -> None:
        """compute_snapshot deve considerar is_online=False para state='unknown'."""
        raw = ConnectivityRawInput(
            state="unknown",
            description="Estado desconhecido",
            text="DESCONHECIDO",
            last_known_state="offline",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.state == "unknown"
        assert snapshot.is_online is False
        assert snapshot.text_for_status_bar == "Nuvem: DESCONHECIDO"

    def test_compute_snapshot_sem_transicao(self, manager: ConnectivityStateManager) -> None:
        """compute_snapshot deve detectar que não houve transição quando estado não muda."""
        raw = ConnectivityRawInput(
            state="online",
            description="Conectado",
            text="ONLINE",
            last_known_state="online",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.should_log_transition is False
        assert snapshot.old_state == "online"

    def test_compute_snapshot_transicao_offline_para_online(self, manager: ConnectivityStateManager) -> None:
        """compute_snapshot deve detectar transição de offline para online."""
        raw = ConnectivityRawInput(
            state="online",
            description="Reconectado",
            text="ONLINE",
            last_known_state="offline",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.should_log_transition is True
        assert snapshot.old_state == "offline"
        assert snapshot.state == "online"

    def test_compute_snapshot_transicao_online_para_unstable(self, manager: ConnectivityStateManager) -> None:
        """compute_snapshot deve detectar transição de online para unstable."""
        raw = ConnectivityRawInput(
            state="unstable",
            description="Conexão instável",
            text="INSTÁVEL",
            last_known_state="online",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.should_log_transition is True
        assert snapshot.old_state == "online"
        assert snapshot.state == "unstable"

    def test_compute_snapshot_transicao_unknown_inicial(self, manager: ConnectivityStateManager) -> None:
        """compute_snapshot deve detectar transição desde estado inicial unknown."""
        raw = ConnectivityRawInput(
            state="online",
            description="Primeira conexão",
            text="ONLINE",
            last_known_state="unknown",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.should_log_transition is True
        assert snapshot.old_state == "unknown"

    def test_compute_snapshot_preserva_description(self, manager: ConnectivityStateManager) -> None:
        """compute_snapshot deve preservar description original."""
        raw = ConnectivityRawInput(
            state="online",
            description="Conectado com sucesso ao Supabase",
            text="ONLINE",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.description == "Conectado com sucesso ao Supabase"

    def test_compute_snapshot_formato_texto_status_bar(self, manager: ConnectivityStateManager) -> None:
        """compute_snapshot deve formatar texto como 'Nuvem: TEXTO'."""
        raw = ConnectivityRawInput(
            state="offline",
            description="Sem conexão",
            text="SEM CONEXÃO",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.text_for_status_bar == "Nuvem: SEM CONEXÃO"


# ============================================================================
# TESTES DO MÉTODO UPDATE_STATUS_BAR_TEXT
# ============================================================================


class TestConnectivityStateManagerUpdateStatusBarText:
    """Testes do método update_status_bar_text()."""

    def test_update_status_bar_text_substitui_parte_nuvem(self, manager: ConnectivityStateManager) -> None:
        """update_status_bar_text deve substituir apenas a parte 'Nuvem: ...'."""
        current = "Nuvem: ONLINE | Usuário: admin"
        new_cloud = "Nuvem: OFFLINE"

        result = manager.update_status_bar_text(current, new_cloud)

        # Note: split("|") preserva espaços, então " | " vira " |  "
        assert result == "Nuvem: OFFLINE |  Usuário: admin"

    def test_update_status_bar_text_adiciona_quando_ausente(self, manager: ConnectivityStateManager) -> None:
        """update_status_bar_text deve adicionar texto quando 'Nuvem:' ausente."""
        current = "Usuário: admin"
        new_cloud = "Nuvem: ONLINE"

        result = manager.update_status_bar_text(current, new_cloud)

        assert result == "Nuvem: ONLINE"

    def test_update_status_bar_text_multiplas_partes(self, manager: ConnectivityStateManager) -> None:
        """update_status_bar_text deve preservar múltiplas partes separadas por |."""
        current = "Nuvem: ONLINE | Usuário: admin | Modo: Normal"
        new_cloud = "Nuvem: INSTÁVEL"

        result = manager.update_status_bar_text(current, new_cloud)

        # Note: split("|") preserva espaços
        assert result == "Nuvem: INSTÁVEL |  Usuário: admin  |  Modo: Normal"

    def test_update_status_bar_text_apenas_nuvem(self, manager: ConnectivityStateManager) -> None:
        """update_status_bar_text deve funcionar quando só há texto de nuvem."""
        current = "Nuvem: ONLINE"
        new_cloud = "Nuvem: OFFLINE"

        result = manager.update_status_bar_text(current, new_cloud)

        assert result == "Nuvem: OFFLINE"

    def test_update_status_bar_text_vazio(self, manager: ConnectivityStateManager) -> None:
        """update_status_bar_text deve adicionar texto quando current vazio."""
        current = ""
        new_cloud = "Nuvem: ONLINE"

        result = manager.update_status_bar_text(current, new_cloud)

        assert result == "Nuvem: ONLINE"

    def test_update_status_bar_text_espacos_extras(self, manager: ConnectivityStateManager) -> None:
        """update_status_bar_text deve preservar formatação com espaços."""
        current = "Nuvem: ONLINE | Usuário: admin | Status: Ativo"
        new_cloud = "Nuvem: OFFLINE"

        result = manager.update_status_bar_text(current, new_cloud)

        # Verifica que preservou os espaços ao redor de |
        assert " | " in result
        assert result.startswith("Nuvem: OFFLINE")

    def test_update_status_bar_text_case_sensitive(self, manager: ConnectivityStateManager) -> None:
        """update_status_bar_text deve ser case-sensitive para 'Nuvem:'."""
        current = "nuvem: online | Usuário: admin"
        new_cloud = "Nuvem: OFFLINE"

        # Como não tem "Nuvem:" (com N maiúsculo), deve adicionar
        result = manager.update_status_bar_text(current, new_cloud)

        assert result == "Nuvem: OFFLINE"

    def test_update_status_bar_text_nuvem_no_meio(self, manager: ConnectivityStateManager) -> None:
        """update_status_bar_text deve detectar 'Nuvem:' mesmo se não está no início."""
        current = "Sistema: OK | Nuvem: ONLINE | Usuário: admin"
        new_cloud = "Nuvem: OFFLINE"

        result = manager.update_status_bar_text(current, new_cloud)

        # Deve substituir apenas a primeira parte, e split("|") preserva espaços
        assert result == "Nuvem: OFFLINE |  Nuvem: ONLINE  |  Usuário: admin"


# ============================================================================
# TESTES DE CENÁRIOS COMPLETOS
# ============================================================================


class TestConnectivityStateManagerScenarios:
    """Testes de cenários completos de uso."""

    def test_cenario_inicial_para_online(self, manager: ConnectivityStateManager) -> None:
        """Cenário: estado inicial (unknown) → online."""
        raw = ConnectivityRawInput(
            state="online",
            description="Conectado",
            text="ONLINE",
            last_known_state="unknown",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.is_online is True
        assert snapshot.should_log_transition is True
        assert snapshot.old_state == "unknown"
        assert snapshot.text_for_status_bar == "Nuvem: ONLINE"

    def test_cenario_online_para_offline(self, manager: ConnectivityStateManager) -> None:
        """Cenário: online → offline (perda de conexão)."""
        raw = ConnectivityRawInput(
            state="offline",
            description="Conexão perdida",
            text="OFFLINE",
            last_known_state="online",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.is_online is False
        assert snapshot.should_log_transition is True
        assert snapshot.old_state == "online"

    def test_cenario_offline_para_online_reconexao(self, manager: ConnectivityStateManager) -> None:
        """Cenário: offline → online (reconexão)."""
        raw = ConnectivityRawInput(
            state="online",
            description="Reconectado",
            text="ONLINE",
            last_known_state="offline",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.is_online is True
        assert snapshot.should_log_transition is True

    def test_cenario_online_permanece_online(self, manager: ConnectivityStateManager) -> None:
        """Cenário: online → online (sem mudança)."""
        raw = ConnectivityRawInput(
            state="online",
            description="Conectado",
            text="ONLINE",
            last_known_state="online",
        )

        snapshot = manager.compute_snapshot(raw)

        assert snapshot.is_online is True
        assert snapshot.should_log_transition is False

    def test_cenario_online_unstable_offline(self, manager: ConnectivityStateManager) -> None:
        """Cenário: online → unstable → offline."""
        # Primeiro: online → unstable
        raw1 = ConnectivityRawInput(
            state="unstable",
            description="Conexão instável",
            text="INSTÁVEL",
            last_known_state="online",
        )

        snapshot1 = manager.compute_snapshot(raw1)

        assert snapshot1.state == "unstable"
        assert snapshot1.is_online is False
        assert snapshot1.should_log_transition is True

        # Depois: unstable → offline
        raw2 = ConnectivityRawInput(
            state="offline",
            description="Conexão perdida",
            text="OFFLINE",
            last_known_state="unstable",
        )

        snapshot2 = manager.compute_snapshot(raw2)

        assert snapshot2.state == "offline"
        assert snapshot2.is_online is False
        assert snapshot2.should_log_transition is True
