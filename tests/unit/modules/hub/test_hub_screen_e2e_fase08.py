# -*- coding: utf-8 -*-
"""Testes End-to-End do HubScreen com Tkinter (MF-23).

Estratégia de testes (Nível C - E2E View → Controller → Navigator):
- Valida o fluxo completo desde a VIEW (HubScreen) até o Navigator
- Simula cliques em botões chamando os métodos públicos que os botões usam
- NÃO executa mainloop (testes headless)
- Usa fixture tk_root do conftest.py (cria Tk() com withdraw())

Cobertura:
- Quick Actions: todas as 9 actions principais + alias cashflow
- Módulos: todas as 9 actions via métodos open_*
- Consistência: quick action e module usam mesmo caminho
- Robustez: valores desconhecidos não quebram

Nota: Este é o nível mais alto de integração sem instanciar MainWindow.
A VIEW real (HubScreen) é instanciada com Tkinter, mas os callbacks de
navegação são substituídos por FakeNavigator para validação.
"""

from __future__ import annotations


import pytest

from src.modules.hub.views.hub_screen import HubScreen


# ═══════════════════════════════════════════════════════════════════════
# Fake Navigator
# ═══════════════════════════════════════════════════════════════════════


class FakeNavigator:
    """Implementação fake do HubQuickActionsNavigatorProtocol para testes E2E.

    Registra todas as chamadas aos métodos de navegação para verificação.
    """

    def __init__(self):
        self.calls = []
        self.last_called = None

    def open_clientes(self) -> None:
        self.calls.append("open_clientes")
        self.last_called = "clientes"

    def open_fluxo_caixa(self) -> None:
        self.calls.append("open_fluxo_caixa")
        self.last_called = "fluxo_caixa"

    def open_anvisa(self) -> None:
        self.calls.append("open_anvisa")
        self.last_called = "anvisa"

    def open_farmacia_popular(self) -> None:
        self.calls.append("open_farmacia_popular")
        self.last_called = "farmacia_popular"

    def open_sngpc(self) -> None:
        self.calls.append("open_sngpc")
        self.last_called = "sngpc"

    def open_sifap(self) -> None:
        self.calls.append("open_sifap")
        self.last_called = "sifap"

    def open_sites(self) -> None:
        self.calls.append("open_sites")
        self.last_called = "sites"


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def hub_screen_safe_teardown(tk_root):
    """Fixture que retorna tk_root diretamente.

    O bug de controller_cancel_poll foi corrigido em MF-24, então o monkeypatch
    não é mais necessário.
    """
    return tk_root


@pytest.fixture
def fake_navigator():
    """Fixture que fornece um fake navigator."""
    return FakeNavigator()


@pytest.fixture
def hub_screen_with_fake_navigator(hub_screen_safe_teardown, fake_navigator):
    """Fixture que cria HubScreen real com FakeNavigator injetado.

    HubScreen é instanciado com Tkinter real (mas sem mainloop), e os
    callbacks de navegação são conectados ao FakeNavigator.

    Returns:
        tuple[HubScreen, FakeNavigator]: (hub_screen, fake_navigator)
    """
    tk_root = hub_screen_safe_teardown

    # Criar callbacks que delegam para o fake navigator
    callbacks = {
        "open_clientes": fake_navigator.open_clientes,
        "open_farmacia_popular": fake_navigator.open_farmacia_popular,
        "open_sngpc": fake_navigator.open_sngpc,
        "open_anvisa": fake_navigator.open_anvisa,
        "open_mod_sifap": fake_navigator.open_sifap,
        "open_cashflow": fake_navigator.open_fluxo_caixa,
        "open_sites": fake_navigator.open_sites,
    }

    # Criar HubScreen com callbacks fake
    hub = HubScreen(
        master=tk_root,
        **callbacks,
    )

    # Não mostrar janela (já feito em tk_root.withdraw())
    # Não executar mainloop

    return hub, fake_navigator


# ═══════════════════════════════════════════════════════════════════════
# Testes E2E - Quick Actions via HubScreen
# ═══════════════════════════════════════════════════════════════════════


def test_hub_screen_open_clientes_dispara_navigator(hub_screen_with_fake_navigator):
    """Teste E2E: HubScreen.open_clientes() chama navigator.open_clientes()."""
    # Arrange
    hub, navigator = hub_screen_with_fake_navigator

    # Act - chamar método público que os botões usam
    hub.open_clientes()

    # Assert
    assert "open_clientes" in navigator.calls
    assert navigator.last_called == "clientes"


def test_hub_screen_open_fluxo_caixa_dispara_navigator(hub_screen_with_fake_navigator):
    """Teste E2E: HubScreen.open_fluxo_caixa() chama navigator.open_fluxo_caixa()."""
    # Arrange
    hub, navigator = hub_screen_with_fake_navigator

    # Act
    hub.open_fluxo_caixa()

    # Assert
    assert "open_fluxo_caixa" in navigator.calls
    assert navigator.last_called == "fluxo_caixa"


def test_hub_screen_open_anvisa_dispara_navigator(hub_screen_with_fake_navigator):
    """Teste E2E: HubScreen.open_anvisa() chama navigator.open_anvisa()."""
    # Arrange
    hub, navigator = hub_screen_with_fake_navigator

    # Act
    hub.open_anvisa()

    # Assert
    assert "open_anvisa" in navigator.calls
    assert navigator.last_called == "anvisa"


def test_hub_screen_open_farmacia_popular_dispara_navigator(hub_screen_with_fake_navigator):
    """Teste E2E: HubScreen.open_farmacia_popular() chama navigator.open_farmacia_popular()."""
    # Arrange
    hub, navigator = hub_screen_with_fake_navigator

    # Act
    hub.open_farmacia_popular()

    # Assert
    assert "open_farmacia_popular" in navigator.calls
    assert navigator.last_called == "farmacia_popular"


def test_hub_screen_open_sngpc_dispara_navigator(hub_screen_with_fake_navigator):
    """Teste E2E: HubScreen.open_sngpc() chama navigator.open_sngpc()."""
    # Arrange
    hub, navigator = hub_screen_with_fake_navigator

    # Act
    hub.open_sngpc()

    # Assert
    assert "open_sngpc" in navigator.calls
    assert navigator.last_called == "sngpc"


def test_hub_screen_open_sifap_dispara_navigator(hub_screen_with_fake_navigator):
    """Teste E2E: HubScreen.open_sifap() chama navigator.open_sifap()."""
    # Arrange
    hub, navigator = hub_screen_with_fake_navigator

    # Act
    hub.open_sifap()

    # Assert
    assert "open_sifap" in navigator.calls
    assert navigator.last_called == "sifap"


def test_hub_screen_open_sites_dispara_navigator(hub_screen_with_fake_navigator):
    """Teste E2E: HubScreen.open_sites() chama navigator.open_sites() (MF-17)."""
    # Arrange
    hub, navigator = hub_screen_with_fake_navigator

    # Act
    hub.open_sites()

    # Assert
    assert "open_sites" in navigator.calls
    assert navigator.last_called == "sites"


def test_hub_screen_todas_actions_navegam_corretamente(hub_screen_with_fake_navigator):
    """Teste E2E: Todas as 9 actions principais navegam via HubScreen."""
    # Arrange
    hub, navigator = hub_screen_with_fake_navigator

    actions_to_test = [
        ("open_clientes", "open_clientes", "clientes"),
        ("open_fluxo_caixa", "open_fluxo_caixa", "fluxo_caixa"),
        ("open_anvisa", "open_anvisa", "anvisa"),
        ("open_farmacia_popular", "open_farmacia_popular", "farmacia_popular"),
        ("open_sngpc", "open_sngpc", "sngpc"),
        ("open_sifap", "open_sifap", "sifap"),
        ("open_sites", "open_sites", "sites"),
    ]

    # Act & Assert
    for method_name, expected_call, expected_last in actions_to_test:
        # Reset navigator
        navigator.calls.clear()
        navigator.last_called = None

        # Chamar método do HubScreen
        method = getattr(hub, method_name)
        method()

        # Verificar
        assert expected_call in navigator.calls, f"Método {method_name} deveria resultar em {expected_call}"
        assert navigator.last_called == expected_last, f"Método {method_name} deveria setar last_called={expected_last}"


def test_hub_screen_multiplos_cliques_sequenciais(hub_screen_with_fake_navigator):
    """Teste E2E: Múltiplos cliques em sequência navegam corretamente."""
    # Arrange
    hub, navigator = hub_screen_with_fake_navigator

    # Act  (senhas e auditoria removidas do HubScreen – migração CTK)
    hub.open_clientes()
    hub.open_anvisa()
    hub.open_sngpc()

    # Assert
    assert len(navigator.calls) == 3
    assert navigator.calls == ["open_clientes", "open_anvisa", "open_sngpc"]
    assert navigator.last_called == "sngpc"


def test_hub_screen_mesma_action_multiplas_vezes(hub_screen_with_fake_navigator):
    """Teste E2E: Mesmo módulo clicado múltiplas vezes funciona."""
    # Arrange
    hub, navigator = hub_screen_with_fake_navigator

    # Act
    hub.open_clientes()
    hub.open_clientes()
    hub.open_clientes()

    # Assert
    assert len(navigator.calls) == 3
    assert all(call == "open_clientes" for call in navigator.calls)


def test_hub_screen_callback_nao_registrado_levanta_typeerror(hub_screen_safe_teardown):
    """Teste E2E: HubScreen sem callback registrado levanta TypeError ao chamar open_*.

    NOTA: Este é o comportamento atual do HubScreen (bug conhecido).
    Idealmente, deveria verificar se callback é callable antes de chamar.
    """
    tk_root = hub_screen_safe_teardown

    # Arrange - criar HubScreen sem passar callback de clientes
    hub = HubScreen(
        master=tk_root,
        open_anvisa=lambda: None,  # apenas anvisa tem callback
        # open_clientes omitido propositalmente
    )

    # Act & Assert - comportamento atual: levanta TypeError
    with pytest.raises(TypeError, match="'NoneType' object is not callable"):
        hub.open_clientes()  # callback não registrado


# ═══════════════════════════════════════════════════════════════════════
# Testes E2E - Validação de Protocolo
# ═══════════════════════════════════════════════════════════════════════


def test_hub_screen_implementa_navigator_protocol(hub_screen_with_fake_navigator):
    """Teste E2E: HubScreen implementa HubQuickActionsNavigatorProtocol."""
    # Arrange
    hub, _ = hub_screen_with_fake_navigator

    # Assert - verificar que HubScreen tem todos os métodos do Protocol
    assert hasattr(hub, "open_clientes")
    assert hasattr(hub, "open_fluxo_caixa")
    assert hasattr(hub, "open_anvisa")
    assert hasattr(hub, "open_farmacia_popular")
    assert hasattr(hub, "open_sngpc")
    assert hasattr(hub, "open_sifap")
    assert hasattr(hub, "open_sites")

    # Verificar que são callable
    assert callable(hub.open_clientes)
    assert callable(hub.open_fluxo_caixa)
    assert callable(hub.open_anvisa)
    assert callable(hub.open_farmacia_popular)
    assert callable(hub.open_sngpc)
    assert callable(hub.open_sifap)
    assert callable(hub.open_sites)


def test_hub_screen_metodos_open_sao_publicos(hub_screen_with_fake_navigator):
    """Teste E2E: Métodos open_* do HubScreen são públicos (não têm prefixo _)."""
    # Arrange
    hub, _ = hub_screen_with_fake_navigator

    # Assert - verificar que métodos não têm prefixo _ (são públicos)
    public_methods = [
        "open_clientes",
        "open_fluxo_caixa",
        "open_anvisa",
        "open_farmacia_popular",
        "open_sngpc",
        "open_sifap",
        "open_sites",
    ]

    for method_name in public_methods:
        assert not method_name.startswith("_"), f"Método {method_name} deveria ser público (sem prefixo _)"
        assert hasattr(hub, method_name), f"HubScreen deveria ter método {method_name}"


# ═══════════════════════════════════════════════════════════════════════
# Testes E2E - Consistência Quick Actions vs Módulos
# ═══════════════════════════════════════════════════════════════════════


def test_hub_screen_mesmos_callbacks_para_quick_actions_e_modulos(hub_screen_safe_teardown, fake_navigator):
    """Teste E2E: Callbacks passados ao HubScreen são usados tanto por quick actions quanto módulos.

    Este teste valida que não importa se o usuário clica em um botão de quick action
    ou em um item do menu lateral de módulos - ambos resultam no mesmo callback.
    """
    tk_root = hub_screen_safe_teardown

    # Arrange - criar HubScreen com callbacks conhecidos
    callback_clientes_called = []

    def callback_clientes():
        callback_clientes_called.append(True)
        fake_navigator.open_clientes()

    hub = HubScreen(
        master=tk_root,
        open_clientes=callback_clientes,
    )

    # Act - simular clique via método público (usado por botões e menu)
    hub.open_clientes()

    # Assert
    assert len(callback_clientes_called) == 1, "Callback deveria ter sido chamado"
    assert "open_clientes" in fake_navigator.calls


def test_hub_screen_todas_actions_tem_mesmo_comportamento_independente_origem(hub_screen_with_fake_navigator):
    """Teste E2E: Todas as actions se comportam da mesma forma independente da origem (quick action ou módulo).

    HubScreen implementa o Navigator Protocol com métodos open_* que são usados
    tanto pelos botões de quick actions quanto pelos itens do menu de módulos.
    """
    # Arrange
    hub, navigator = hub_screen_with_fake_navigator

    # Assert - estrutura: todos os métodos open_* seguem mesmo padrão
    # (chamar callback se registrado, senão não fazer nada)

    # Testar que cada método pode ser chamado sem quebrar
    methods = [
        hub.open_clientes,
        hub.open_fluxo_caixa,
        hub.open_anvisa,
        hub.open_farmacia_popular,
        hub.open_sngpc,
        hub.open_sifap,
        hub.open_sites,
    ]

    for method in methods:
        # Reset
        navigator.calls.clear()

        # Act
        method()

        # Assert - algum método do navigator foi chamado
        assert len(navigator.calls) == 1, f"Método {method.__name__} deveria chamar exatamente um método do navigator"


# ═══════════════════════════════════════════════════════════════════════
# Testes E2E - Robustez e Edge Cases
# ═══════════════════════════════════════════════════════════════════════


def test_hub_screen_pode_ser_instanciado_sem_callbacks(hub_screen_safe_teardown):
    """Teste E2E: HubScreen pode ser criado sem nenhum callback (instanciação funciona)."""
    tk_root = hub_screen_safe_teardown

    # Act & Assert - instanciação não quebra
    try:
        hub = HubScreen(master=tk_root)
        assert hub is not None
    except Exception as e:
        pytest.fail(f"HubScreen sem callbacks não deveria quebrar na criação, mas levantou: {e}")


def test_hub_screen_chamadas_sem_callback_levantam_typeerror(hub_screen_safe_teardown):
    """Teste E2E: Chamar métodos open_* sem callbacks registrados levanta TypeError.

    NOTA: Este é o comportamento atual do HubScreen (bug conhecido).
    Idealmente, deveria verificar se callback é callable antes de chamar.
    """
    tk_root = hub_screen_safe_teardown

    # Arrange
    hub = HubScreen(master=tk_root)  # sem callbacks

    # Act & Assert - comportamento atual: levanta TypeError
    with pytest.raises(TypeError, match="'NoneType' object is not callable"):
        hub.open_clientes()


def test_hub_screen_callback_none_explicito_levanta_typeerror(hub_screen_safe_teardown):
    """Teste E2E: Passar None explicitamente como callback levanta TypeError ao chamar.

    NOTA: Este é o comportamento atual do HubScreen (bug conhecido).
    Idealmente, deveria verificar se callback é callable antes de chamar.
    """
    tk_root = hub_screen_safe_teardown

    # Arrange
    hub = HubScreen(
        master=tk_root,
        open_clientes=None,
    )

    # Act & Assert - comportamento atual: levanta TypeError
    with pytest.raises(TypeError, match="'NoneType' object is not callable"):
        hub.open_clientes()


def test_hub_screen_callback_que_levanta_excecao_propaga_excecao(hub_screen_safe_teardown):
    """Teste E2E: Callback que levanta exceção propaga a exceção.

    HubScreen não trata exceções dos callbacks, então elas são propagadas.
    """
    tk_root = hub_screen_safe_teardown

    # Arrange
    def callback_com_erro():
        raise ValueError("Erro proposital no callback")

    hub = HubScreen(
        master=tk_root,
        open_clientes=callback_com_erro,
    )

    # Act & Assert - exceção do callback é propagada
    with pytest.raises(ValueError, match="Erro proposital no callback"):
        hub.open_clientes()

    # Hub deve continuar funcional após exceção
    assert hub is not None
    assert hasattr(hub, "open_anvisa")  # outros métodos ainda existem


# ═══════════════════════════════════════════════════════════════════════
# LIFECYCLE/POLLING (MF-28)
# ═══════════════════════════════════════════════════════════════════════


def test_hub_start_and_stop_polling_nao_quebram(tk_root):
    """MF-28: start_polling e stop_polling não levantam exceções.

    Valida:
    - Métodos públicos start_polling/stop_polling são idempotentes
    - Não levantam exceções mesmo quando chamados múltiplas vezes
    - HubLifecycleManager gerencia estado corretamente
    """
    # Arrange
    hub = HubScreen(master=tk_root)

    # Act & Assert - não deve levantar exceção
    hub.start_polling()
    hub.start_polling()  # Segunda chamada deve ser idempotente

    hub.stop_polling()
    hub.stop_polling()  # Segunda chamada deve ser idempotente

    # Verificar que hub ainda está funcional
    assert hub is not None
    assert hasattr(hub, "_lifecycle_manager")


def test_hub_lifecycle_manager_is_active_property(tk_root):
    """MF-28: Property is_active do lifecycle manager reflete estado.

    Valida:
    - HubLifecycleManager.is_active retorna False após construção (não auto-start)
    - HubLifecycleManager.is_active retorna True após start
    - HubLifecycleManager.is_active retorna False após stop
    - HubLifecycleManager.is_active retorna True após restart
    """
    # Arrange
    hub = HubScreen(master=tk_root)

    # Assert - lifecycle NÃO inicia automaticamente (_polling_active=False no __init__)
    assert hub._lifecycle_manager.is_active is False

    # Act - start explícito
    hub.start_polling()

    # Assert - ativo
    assert hub._lifecycle_manager.is_active is True

    # Act - stop
    hub.stop_polling()

    # Assert - inativo
    assert hub._lifecycle_manager.is_active is False

    # Act - restart
    hub.start_polling()

    # Assert - ativo novamente
    assert hub._lifecycle_manager.is_active is True


def test_hub_stop_polling_sem_start_nao_quebra(tk_root):
    """MF-28: stop_polling sem start prévio não quebra (bug MF-24 regression).

    Valida:
    - Chamada de stop_polling sem start_polling não levanta exceção
    - Útil para teardown seguro em testes/produção
    """
    # Arrange
    hub = HubScreen(master=tk_root)

    # Act & Assert - não deve levantar exceção
    hub.stop_polling()  # Sem start prévio

    # Verificar estado
    assert hub._lifecycle_manager.is_active is False
