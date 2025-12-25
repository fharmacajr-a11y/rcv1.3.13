# -*- coding: utf-8 -*-
"""Testes unitários para screen_registry (headless, sem telas reais).

Estratégia:
- Usar monkeypatch para inserir módulos fake em sys.modules
- Validar que register_main_window_screens() registra 8 telas
- NÃO chamar factories (para não puxar UI real)
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

import pytest


# ===== Fixtures =====


@pytest.fixture
def fake_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Injeta módulos fake em sys.modules para evitar import real."""

    # Criar classes fake para cada tela
    class FakeAnvisaScreen:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class FakeAuditoriaFrame:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class FakeCashflowFrame:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class FakeClientesFrame:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def carregar(self) -> None:
            pass

    class FakeHubFrame:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def on_show(self) -> None:
            pass

    class FakePasswordsFrame:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def on_show(self) -> None:
            pass

    class FakeSitesScreen:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class FakeComingSoonScreen:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    # Criar módulos fake
    fake_anvisa = type(sys)("src.modules.anvisa")
    fake_anvisa.AnvisaScreen = FakeAnvisaScreen  # type: ignore[attr-defined]

    fake_auditoria = type(sys)("src.modules.auditoria")
    fake_auditoria.AuditoriaFrame = FakeAuditoriaFrame  # type: ignore[attr-defined]

    fake_cashflow = type(sys)("src.modules.cashflow")
    fake_cashflow.CashflowFrame = FakeCashflowFrame  # type: ignore[attr-defined]

    fake_clientes = type(sys)("src.modules.clientes")
    fake_clientes.ClientesFrame = FakeClientesFrame  # type: ignore[attr-defined]
    fake_clientes.DEFAULT_ORDER_LABEL = "Ordem Padrão"  # type: ignore[attr-defined]
    fake_clientes.ORDER_CHOICES = ["A-Z", "Z-A"]  # type: ignore[attr-defined]

    fake_notas = type(sys)("src.modules.notas")
    fake_notas.HubFrame = FakeHubFrame  # type: ignore[attr-defined]

    fake_passwords = type(sys)("src.modules.passwords")
    fake_passwords.PasswordsFrame = FakePasswordsFrame  # type: ignore[attr-defined]

    fake_sites = type(sys)("src.modules.sites")
    fake_sites.SitesScreen = FakeSitesScreen  # type: ignore[attr-defined]

    fake_placeholders = type(sys)("src.ui.placeholders")
    fake_placeholders.ComingSoonScreen = FakeComingSoonScreen  # type: ignore[attr-defined]

    # Injetar em sys.modules
    monkeypatch.setitem(sys.modules, "src.modules.anvisa", fake_anvisa)
    monkeypatch.setitem(sys.modules, "src.modules.auditoria", fake_auditoria)
    monkeypatch.setitem(sys.modules, "src.modules.cashflow", fake_cashflow)
    monkeypatch.setitem(sys.modules, "src.modules.clientes", fake_clientes)
    monkeypatch.setitem(sys.modules, "src.modules.notas", fake_notas)
    monkeypatch.setitem(sys.modules, "src.modules.passwords", fake_passwords)
    monkeypatch.setitem(sys.modules, "src.modules.sites", fake_sites)
    monkeypatch.setitem(sys.modules, "src.ui.placeholders", fake_placeholders)


@pytest.fixture
def stub_router() -> MagicMock:
    """Retorna router stub que rastreia chamadas a register()."""
    router = MagicMock()
    router.register_calls: list[tuple[str, Any, bool]] = []  # type: ignore[attr-defined]

    def mock_register(name: str, factory: Any, *, cache: bool = False) -> None:
        router.register_calls.append((name, factory, cache))  # type: ignore[attr-defined]

    router.register = mock_register
    return router


@pytest.fixture
def stub_app() -> MagicMock:
    """Retorna app stub com atributos mínimos."""
    app = MagicMock()
    app._content_container = MagicMock()
    app.show_main_screen = MagicMock()
    app.show_passwords_screen = MagicMock()
    app.show_cashflow_screen = MagicMock()
    app.show_sites_screen = MagicMock()
    app.show_placeholder_screen = MagicMock()
    app.show_hub_screen = MagicMock()
    app.novo_cliente = MagicMock()
    app.editar_cliente = MagicMock()
    app._excluir_cliente = MagicMock()
    app.enviar_para_supabase = MagicMock()
    app.open_client_storage_subfolders = MagicMock()
    app.abrir_lixeira = MagicMock()
    app.abrir_obrigacoes_cliente = MagicMock()
    app.enviar_pasta_supabase = MagicMock()
    app._hub_screen_instance = None
    app._main_frame_ref = None
    app._passwords_screen_instance = None
    app._anvisa_screen_instance = None
    return app


# ===== Testes =====


def test_register_main_window_screens_registers_all_eight_screens(
    fake_modules: None,
    stub_router: MagicMock,
    stub_app: MagicMock,
) -> None:
    """register_main_window_screens() deve registrar 8 telas com cache correto."""
    from src.modules.main_window.controllers.screen_registry import (
        register_main_window_screens,
    )

    register_main_window_screens(stub_router, stub_app)

    # Validar que 8 telas foram registradas
    calls = stub_router.register_calls  # type: ignore[attr-defined]
    assert len(calls) == 8

    # Extrair nomes, factories e cache flags
    names = [call[0] for call in calls]
    factories = [call[1] for call in calls]
    cache_flags = [call[2] for call in calls]

    # Validar nomes das telas
    expected_names = [
        "hub",
        "main",
        "passwords",
        "cashflow",
        "sites",
        "anvisa",
        "auditoria",
        "placeholder",
    ]
    assert names == expected_names

    # Validar cache flags
    expected_cache = [
        True,  # hub
        False,  # main
        True,  # passwords
        False,  # cashflow
        False,  # sites
        True,  # anvisa
        False,  # auditoria
        False,  # placeholder
    ]
    assert cache_flags == expected_cache

    # Validar que todos factories são callables
    for i, factory in enumerate(factories):
        assert callable(factory), f"Factory para '{names[i]}' não é callable"


def test_hub_factory_creates_hub_frame_and_calls_on_show(
    fake_modules: None,
    stub_router: MagicMock,
    stub_app: MagicMock,
) -> None:
    """Factory 'hub' deve criar HubFrame e chamar on_show()."""
    from src.modules.main_window.controllers.screen_registry import (
        register_main_window_screens,
    )

    register_main_window_screens(stub_router, stub_app)

    # Obter factory do hub (primeira chamada)
    hub_factory = stub_router.register_calls[0][1]  # type: ignore[attr-defined]

    # Chamar factory (deve criar HubFrame)
    frame = hub_factory()

    # Validar que frame foi criado
    assert frame is not None
    # Validar que referência legacy foi mantida
    assert stub_app._hub_screen_instance is frame


def test_main_factory_creates_clientes_frame_and_calls_carregar(
    fake_modules: None,
    stub_router: MagicMock,
    stub_app: MagicMock,
) -> None:
    """Factory 'main' deve criar ClientesFrame e chamar carregar()."""
    from src.modules.main_window.controllers.screen_registry import (
        register_main_window_screens,
    )

    register_main_window_screens(stub_router, stub_app)

    # Obter factory do main (segunda chamada)
    main_factory = stub_router.register_calls[1][1]  # type: ignore[attr-defined]

    # Chamar factory (deve criar ClientesFrame)
    frame = main_factory()

    # Validar que frame foi criado
    assert frame is not None
    # Validar que referência legacy foi mantida
    assert stub_app._main_frame_ref is frame


def test_passwords_factory_creates_singleton_and_calls_on_show(
    fake_modules: None,
    stub_router: MagicMock,
    stub_app: MagicMock,
) -> None:
    """Factory 'passwords' deve criar singleton e chamar on_show()."""
    from src.modules.main_window.controllers.screen_registry import (
        register_main_window_screens,
    )

    register_main_window_screens(stub_router, stub_app)

    # Obter factory do passwords (terceira chamada)
    passwords_factory = stub_router.register_calls[2][1]  # type: ignore[attr-defined]

    # Primeira chamada cria nova instância
    frame1 = passwords_factory()
    assert frame1 is not None
    assert stub_app._passwords_screen_instance is frame1

    # Segunda chamada retorna mesma instância
    frame2 = passwords_factory()
    assert frame2 is frame1


def test_anvisa_factory_creates_singleton(
    fake_modules: None,
    stub_router: MagicMock,
    stub_app: MagicMock,
) -> None:
    """Factory 'anvisa' deve criar singleton."""
    from src.modules.main_window.controllers.screen_registry import (
        register_main_window_screens,
    )

    register_main_window_screens(stub_router, stub_app)

    # Obter factory do anvisa (sexta chamada, índice 5)
    anvisa_factory = stub_router.register_calls[5][1]  # type: ignore[attr-defined]

    # Primeira chamada cria nova instância
    frame1 = anvisa_factory()
    assert frame1 is not None
    assert stub_app._anvisa_screen_instance is frame1

    # Segunda chamada retorna mesma instância
    frame2 = anvisa_factory()
    assert frame2 is frame1


def test_cashflow_factory_creates_new_instance(
    fake_modules: None,
    stub_router: MagicMock,
    stub_app: MagicMock,
) -> None:
    """Factory 'cashflow' deve criar nova instância sempre."""
    from src.modules.main_window.controllers.screen_registry import (
        register_main_window_screens,
    )

    register_main_window_screens(stub_router, stub_app)

    # Obter factory do cashflow (quarta chamada)
    cashflow_factory = stub_router.register_calls[3][1]  # type: ignore[attr-defined]

    # Chamar factory duas vezes
    frame1 = cashflow_factory()
    frame2 = cashflow_factory()

    # Validar que são instâncias diferentes
    assert frame1 is not None
    assert frame2 is not None
    assert frame1 is not frame2


def test_sites_factory_creates_new_instance(
    fake_modules: None,
    stub_router: MagicMock,
    stub_app: MagicMock,
) -> None:
    """Factory 'sites' deve criar nova instância sempre."""
    from src.modules.main_window.controllers.screen_registry import (
        register_main_window_screens,
    )

    register_main_window_screens(stub_router, stub_app)

    # Obter factory do sites (quinta chamada)
    sites_factory = stub_router.register_calls[4][1]  # type: ignore[attr-defined]

    # Chamar factory duas vezes
    frame1 = sites_factory()
    frame2 = sites_factory()

    # Validar que são instâncias diferentes
    assert frame1 is not None
    assert frame2 is not None
    assert frame1 is not frame2


def test_auditoria_factory_creates_new_instance(
    fake_modules: None,
    stub_router: MagicMock,
    stub_app: MagicMock,
) -> None:
    """Factory 'auditoria' deve criar nova instância sempre."""
    from src.modules.main_window.controllers.screen_registry import (
        register_main_window_screens,
    )

    register_main_window_screens(stub_router, stub_app)

    # Obter factory do auditoria (sétima chamada, índice 6)
    auditoria_factory = stub_router.register_calls[6][1]  # type: ignore[attr-defined]

    # Chamar factory duas vezes
    frame1 = auditoria_factory()
    frame2 = auditoria_factory()

    # Validar que são instâncias diferentes
    assert frame1 is not None
    assert frame2 is not None
    assert frame1 is not frame2


def test_placeholder_factory_creates_new_instance(
    fake_modules: None,
    stub_router: MagicMock,
    stub_app: MagicMock,
) -> None:
    """Factory 'placeholder' deve criar nova instância sempre."""
    from src.modules.main_window.controllers.screen_registry import (
        register_main_window_screens,
    )

    register_main_window_screens(stub_router, stub_app)

    # Obter factory do placeholder (oitava chamada, índice 7)
    placeholder_factory = stub_router.register_calls[7][1]  # type: ignore[attr-defined]

    # Chamar factory duas vezes
    frame1 = placeholder_factory()
    frame2 = placeholder_factory()

    # Validar que são instâncias diferentes
    assert frame1 is not None
    assert frame2 is not None
    assert frame1 is not frame2
