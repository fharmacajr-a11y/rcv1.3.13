# -*- coding: utf-8 -*-
"""Testes unitários para hub_auth_helpers.py (MF-35).

Cobertura:
- get_app_from_widget: sucesso, fallback, não encontrado
- get_org_id_safe_from_widget: sucesso, fallback cached, sem app/auth
- get_email_safe_from_widget: sucesso, sem app/auth, erro silencioso
- get_user_id_safe_from_widget: sucesso, sem app/auth, erro silencioso
- is_online_from_widget: online, offline, sem app (default True), erro silencioso
"""

from __future__ import annotations

from typing import Any, Optional
from unittest.mock import MagicMock


from src.modules.hub.services.hub_auth_helpers import (
    get_app_from_widget,
    get_email_safe_from_widget,
    get_org_id_safe_from_widget,
    get_user_id_safe_from_widget,
    is_online_from_widget,
)


# ============================================================================
# Fixtures e helpers
# ============================================================================


class DummyAuth:
    """Mock de objeto auth para testes."""

    def __init__(
        self,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> None:
        self._org_id = org_id
        self._user_id = user_id
        self._email = email

    def get_org_id(self) -> Optional[str]:
        return self._org_id

    def get_user_id(self) -> Optional[str]:
        return self._user_id

    def get_email(self) -> Optional[str]:
        return self._email


class DummyWidget:
    """Mock de widget Tkinter com hierarquia."""

    def __init__(self, master: Any = None) -> None:
        self.master = master


class DummyApp:
    """Mock de App principal."""

    def __init__(
        self,
        auth: Optional[DummyAuth] = None,
        has_cache: bool = False,
        cached_org_id: Optional[str] = None,
        is_online: Optional[bool] = None,
    ) -> None:
        self.auth = auth
        if has_cache:
            self._org_id_cache = {}
            self._cached_org_id = cached_org_id

    def _get_org_id_cached(self, user_id: str) -> Optional[str]:
        """Simula método legado de cache de org_id."""
        return getattr(self, "_cached_org_id", None)


# ============================================================================
# Testes: get_app_from_widget
# ============================================================================


def test_get_app_from_widget_encontra_app_direta():
    """Deve encontrar app quando widget já é a app."""
    app = DummyApp(auth=DummyAuth())
    result = get_app_from_widget(app)
    assert result is app


def test_get_app_from_widget_sobe_hierarquia_ate_app():
    """Deve subir na hierarquia master.master até encontrar app."""
    app = DummyApp(auth=DummyAuth())
    widget_level1 = DummyWidget(master=app)
    widget_level2 = DummyWidget(master=widget_level1)
    widget_level3 = DummyWidget(master=widget_level2)

    result = get_app_from_widget(widget_level3)
    assert result is app


def test_get_app_from_widget_encontra_por_org_id_cache():
    """Deve aceitar app sem auth mas com _org_id_cache."""
    app = DummyApp(has_cache=True)
    widget = DummyWidget(master=app)

    result = get_app_from_widget(widget)
    assert result is app


def test_get_app_from_widget_retorna_none_quando_nao_encontra():
    """Deve retornar None se não encontrar app na hierarquia."""
    widget1 = DummyWidget()
    widget2 = DummyWidget(master=widget1)
    widget3 = DummyWidget(master=widget2)

    result = get_app_from_widget(widget3)
    assert result is None


def test_get_app_from_widget_retorna_none_se_widget_none():
    """Deve retornar None se widget inicial for None."""
    result = get_app_from_widget(None)
    assert result is None


def test_get_app_from_widget_nao_levanta_excecao_em_erro():
    """Deve capturar exceção e retornar None."""

    # Widget que levanta exceção ao acessar master
    class BrokenWidget:
        @property
        def master(self):
            raise RuntimeError("boom")

    broken_widget = BrokenWidget()
    result = get_app_from_widget(broken_widget)
    assert result is None


# ============================================================================
# Testes: get_org_id_safe_from_widget
# ============================================================================


def test_get_org_id_safe_retorna_org_id_direto_do_auth():
    """Deve retornar org_id via auth.get_org_id() quando disponível."""
    org_id = "12345678-1234-1234-1234-123456789abc"
    auth = DummyAuth(org_id=org_id)
    app = DummyApp(auth=auth)
    widget = DummyWidget(master=app)

    result = get_org_id_safe_from_widget(widget)
    assert result == org_id


def test_get_org_id_safe_fallback_para_cached_quando_auth_org_id_none():
    """Deve usar _get_org_id_cached quando auth.get_org_id() retorna None."""
    cached_org_id = "cached-org-id-uuid"
    user_id = "user-123"
    auth = DummyAuth(org_id=None, user_id=user_id)
    app = DummyApp(auth=auth, has_cache=True, cached_org_id=cached_org_id)
    widget = DummyWidget(master=app)

    result = get_org_id_safe_from_widget(widget)
    assert result == cached_org_id


def test_get_org_id_safe_retorna_none_quando_nao_tem_app():
    """Deve retornar None se não encontrar app."""
    widget = DummyWidget()
    result = get_org_id_safe_from_widget(widget)
    assert result is None


def test_get_org_id_safe_retorna_none_quando_app_sem_auth():
    """Deve retornar None se app não tem auth."""
    app = DummyApp(auth=None)
    widget = DummyWidget(master=app)

    result = get_org_id_safe_from_widget(widget)
    assert result is None


def test_get_org_id_safe_retorna_none_quando_auth_vazio():
    """Deve retornar None quando auth existe mas não tem org_id."""
    auth = DummyAuth(org_id=None, user_id=None)
    app = DummyApp(auth=auth)
    widget = DummyWidget(master=app)

    result = get_org_id_safe_from_widget(widget)
    assert result is None


def test_get_org_id_safe_nao_levanta_excecao_em_erro():
    """Deve capturar exceção e retornar None."""
    # Auth que levanta exceção
    broken_auth = MagicMock()
    broken_auth.get_org_id = MagicMock(side_effect=RuntimeError("auth error"))
    app = DummyApp()
    app.auth = broken_auth
    widget = DummyWidget(master=app)

    result = get_org_id_safe_from_widget(widget)
    assert result is None


# ============================================================================
# Testes: get_email_safe_from_widget
# ============================================================================


def test_get_email_safe_retorna_email_quando_disponivel():
    """Deve retornar email via auth.get_email()."""
    email = "user@example.com"
    auth = DummyAuth(email=email)
    app = DummyApp(auth=auth)
    widget = DummyWidget(master=app)

    result = get_email_safe_from_widget(widget)
    assert result == email


def test_get_email_safe_retorna_none_quando_nao_tem_app():
    """Deve retornar None se não encontrar app."""
    widget = DummyWidget()
    result = get_email_safe_from_widget(widget)
    assert result is None


def test_get_email_safe_retorna_none_quando_app_sem_auth():
    """Deve retornar None se app não tem auth."""
    app = DummyApp(auth=None)
    widget = DummyWidget(master=app)

    result = get_email_safe_from_widget(widget)
    assert result is None


def test_get_email_safe_retorna_none_quando_email_none():
    """Deve retornar None quando auth.get_email() retorna None."""
    auth = DummyAuth(email=None)
    app = DummyApp(auth=auth)
    widget = DummyWidget(master=app)

    result = get_email_safe_from_widget(widget)
    assert result is None


def test_get_email_safe_nao_levanta_excecao_em_erro():
    """Deve capturar exceção e retornar None."""
    broken_auth = MagicMock()
    broken_auth.get_email = MagicMock(side_effect=RuntimeError("email error"))
    app = DummyApp()
    app.auth = broken_auth
    widget = DummyWidget(master=app)

    result = get_email_safe_from_widget(widget)
    assert result is None


# ============================================================================
# Testes: get_user_id_safe_from_widget
# ============================================================================


def test_get_user_id_safe_retorna_user_id_quando_disponivel():
    """Deve retornar user_id via auth.get_user_id()."""
    user_id = "user-uuid-123"
    auth = DummyAuth(user_id=user_id)
    app = DummyApp(auth=auth)
    widget = DummyWidget(master=app)

    result = get_user_id_safe_from_widget(widget)
    assert result == user_id


def test_get_user_id_safe_retorna_none_quando_nao_tem_app():
    """Deve retornar None se não encontrar app."""
    widget = DummyWidget()
    result = get_user_id_safe_from_widget(widget)
    assert result is None


def test_get_user_id_safe_retorna_none_quando_app_sem_auth():
    """Deve retornar None se app não tem auth."""
    app = DummyApp(auth=None)
    widget = DummyWidget(master=app)

    result = get_user_id_safe_from_widget(widget)
    assert result is None


def test_get_user_id_safe_retorna_none_quando_user_id_none():
    """Deve retornar None quando auth.get_user_id() retorna None."""
    auth = DummyAuth(user_id=None)
    app = DummyApp(auth=auth)
    widget = DummyWidget(master=app)

    result = get_user_id_safe_from_widget(widget)
    assert result is None


def test_get_user_id_safe_nao_levanta_excecao_em_erro():
    """Deve capturar exceção e retornar None."""
    broken_auth = MagicMock()
    broken_auth.get_user_id = MagicMock(side_effect=RuntimeError("user_id error"))
    app = DummyApp()
    app.auth = broken_auth
    widget = DummyWidget(master=app)

    result = get_user_id_safe_from_widget(widget)
    assert result is None


# ============================================================================
# Testes: is_online_from_widget
# ============================================================================


def test_is_online_retorna_true_quando_app_online():
    """Deve retornar True quando app._net_is_online == True."""
    app = DummyApp()
    app._net_is_online = True
    widget = DummyWidget(master=app)

    result = is_online_from_widget(widget)
    assert result is True


def test_is_online_retorna_false_quando_app_offline():
    """Deve retornar False quando app._net_is_online == False."""
    app = DummyApp()
    app._net_is_online = False
    widget = DummyWidget(master=app)

    result = is_online_from_widget(widget)
    assert result is False


def test_is_online_retorna_true_quando_nao_tem_app():
    """Deve retornar True (assume online) se não encontrar app."""
    widget = DummyWidget()

    result = is_online_from_widget(widget)
    assert result is True


def test_is_online_retorna_true_quando_app_sem_atributo_net():
    """Deve retornar True (assume online) se app não tem _net_is_online."""
    app = DummyApp()
    # Não definir _net_is_online
    widget = DummyWidget(master=app)

    result = is_online_from_widget(widget)
    assert result is True


def test_is_online_nao_levanta_excecao_em_erro():
    """Deve capturar exceção e retornar True (assume online)."""
    broken_app = MagicMock()
    # Simular erro ao acessar _net_is_online
    type(broken_app)._net_is_online = property(lambda self: (_ for _ in ()).throw(RuntimeError("net error")))
    widget = DummyWidget(master=broken_app)

    result = is_online_from_widget(widget)
    assert result is True


# ============================================================================
# Testes: Casos de edge com None explícito
# ============================================================================


def test_get_org_id_safe_widget_none():
    """Deve retornar None se widget for None."""
    result = get_org_id_safe_from_widget(None)
    assert result is None


def test_get_email_safe_widget_none():
    """Deve retornar None se widget for None."""
    result = get_email_safe_from_widget(None)
    assert result is None


def test_get_user_id_safe_widget_none():
    """Deve retornar None se widget for None."""
    result = get_user_id_safe_from_widget(None)
    assert result is None


def test_is_online_widget_none():
    """Deve retornar True (assume online) se widget for None."""
    result = is_online_from_widget(None)
    assert result is True
