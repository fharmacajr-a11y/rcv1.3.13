"""Testes adicionais para src/core/auth_bootstrap.py - Microfase TEST-001 + QA-003."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, cast
from unittest.mock import MagicMock, patch

import pytest

from src.core import auth_bootstrap


# ==================== Testes de _supabase_client ====================


def test_supabase_client_retorna_none_quando_get_supabase_nao_callable(monkeypatch):
    """Testa que _supabase_client() retorna None quando get_supabase não é callable."""
    monkeypatch.setattr("src.core.auth_bootstrap.get_supabase", None)
    assert auth_bootstrap._supabase_client() is None


def test_supabase_client_retorna_none_quando_get_supabase_lanca_excecao(monkeypatch):
    """Testa que _supabase_client() retorna None quando get_supabase lança exceção."""

    def fake_get_supabase():
        raise RuntimeError("Supabase connection error")

    monkeypatch.setattr("src.core.auth_bootstrap.get_supabase", fake_get_supabase)
    assert auth_bootstrap._supabase_client() is None


def test_supabase_client_retorna_cliente_quando_sucesso(monkeypatch):
    """Testa que _supabase_client() retorna cliente quando get_supabase funciona."""
    fake_client = MagicMock()
    monkeypatch.setattr("src.core.auth_bootstrap.get_supabase", lambda: fake_client)

    result = auth_bootstrap._supabase_client()
    assert result is fake_client


# ==================== Testes de _bind_postgrest ====================


def test_bind_postgrest_ignora_quando_nao_disponivel(monkeypatch):
    """Testa que _bind_postgrest() ignora quando bind_postgrest_auth_if_any não está disponível."""
    monkeypatch.setattr("src.core.auth_bootstrap.bind_postgrest_auth_if_any", None)

    # Não deve lançar exceção
    auth_bootstrap._bind_postgrest(MagicMock())


def test_bind_postgrest_chama_funcao_quando_disponivel(monkeypatch):
    """Testa que _bind_postgrest() chama bind_postgrest_auth_if_any quando disponível."""
    calls = []

    def fake_bind(client):
        calls.append(client)

    monkeypatch.setattr("src.core.auth_bootstrap.bind_postgrest_auth_if_any", fake_bind)

    fake_client = MagicMock()
    auth_bootstrap._bind_postgrest(fake_client)

    assert len(calls) == 1
    assert calls[0] is fake_client


def test_bind_postgrest_ignora_excecao_ao_chamar_bind(monkeypatch):
    """Testa que _bind_postgrest() ignora exceção ao chamar bind_postgrest_auth_if_any."""

    def fake_bind(client):
        raise RuntimeError("Bind failed")

    monkeypatch.setattr("src.core.auth_bootstrap.bind_postgrest_auth_if_any", fake_bind)

    # Não deve lançar exceção
    auth_bootstrap._bind_postgrest(MagicMock())


# ==================== Testes de _destroy_splash ====================


def test_destroy_splash_com_splash_none_e_callback(monkeypatch):
    """Testa que _destroy_splash() chama callback quando splash é None."""
    callback_called = []

    def on_closed():
        callback_called.append(True)

    auth_bootstrap._destroy_splash(None, on_closed=on_closed)

    assert len(callback_called) == 1


def test_destroy_splash_com_splash_none_e_callback_lanca_excecao(monkeypatch):
    """Testa que _destroy_splash() ignora exceção no callback quando splash é None."""

    def on_closed():
        raise RuntimeError("Callback error")

    # Não deve lançar exceção
    auth_bootstrap._destroy_splash(None, on_closed=on_closed)


def test_destroy_splash_usa_metodo_close_quando_disponivel():
    """Testa que _destroy_splash() usa método close() quando disponível."""
    close_called = []

    class FakeSplash:
        def close(self, on_closed: Optional[Callable[[], None]] = None) -> None:
            close_called.append(True)
            if on_closed:
                on_closed()

        def winfo_exists(self) -> bool:
            return True

        def destroy(self) -> None:
            pass

    callback_called = []
    splash = FakeSplash()
    auth_bootstrap._destroy_splash(splash, on_closed=lambda: callback_called.append(True))

    assert len(close_called) == 1
    assert len(callback_called) == 1


def test_destroy_splash_chama_close_sem_callback():
    """Testa que _destroy_splash() chama close() mesmo quando on_closed é None."""
    close_called = []

    class FakeSplash:
        def close(self, on_closed: Optional[Callable[[], None]] = None) -> None:
            close_called.append(on_closed)

        def winfo_exists(self) -> bool:
            return True

        def destroy(self) -> None:
            pass

    splash = FakeSplash()
    auth_bootstrap._destroy_splash(splash, on_closed=None)

    assert len(close_called) == 1
    assert close_called[0] is None


def test_destroy_splash_usa_destroy_quando_close_nao_disponivel():
    """Testa que _destroy_splash() usa destroy() quando close() não está disponível."""
    destroy_called = []

    class FakeSplashWithoutClose:
        def winfo_exists(self) -> bool:
            return True

        def destroy(self) -> None:
            destroy_called.append(True)

    callback_called = []
    # NOTA: FakeSplashWithoutClose não implementa close() propositalmente
    # para testar o fallback para destroy(). O cast é necessário pois o
    # protocolo SplashLike requer close(), mas _destroy_splash aceita via getattr.
    splash = cast(auth_bootstrap.SplashLike, FakeSplashWithoutClose())
    auth_bootstrap._destroy_splash(splash, on_closed=lambda: callback_called.append(True))

    assert len(destroy_called) == 1
    assert len(callback_called) == 1


def test_destroy_splash_nao_quebra_quando_winfo_exists_false():
    """Testa que _destroy_splash() não quebra quando winfo_exists() retorna False."""

    class FakeSplash:
        def winfo_exists(self) -> bool:
            return False

        def destroy(self) -> None:
            raise RuntimeError("Should not be called")

        def close(self, on_closed: Optional[Callable[[], None]] = None) -> None:
            pass

    # Não deve lançar exceção nem chamar destroy()
    auth_bootstrap._destroy_splash(FakeSplash(), on_closed=None)


def test_destroy_splash_ignora_excecao_ao_destruir():
    """Testa que _destroy_splash() ignora exceção ao destruir splash."""

    class FakeSplashQuebrada:
        def winfo_exists(self) -> bool:
            raise RuntimeError("winfo error")

        def destroy(self) -> None:
            pass

        # Não implementa close() para forçar uso de winfo_exists/destroy

    # Não deve lançar exceção mesmo com winfo_exists() quebrando
    # Usa cast porque FakeSplashQuebrada não implementa close() (teste de fallback)
    auth_bootstrap._destroy_splash(cast(auth_bootstrap.SplashLike, FakeSplashQuebrada()), on_closed=None)


def test_destroy_splash_ignora_excecao_no_callback_pos_destroy():
    """Testa que _destroy_splash() ignora exceção no callback após destroy."""

    class FakeSplashSemClose:
        def winfo_exists(self) -> bool:
            return True

        def destroy(self) -> None:
            pass

    def bad_callback():
        raise RuntimeError("Callback error")

    # Não deve lançar exceção mesmo com callback quebrando após destroy()
    # Usa cast porque FakeSplashSemClose não implementa close() (teste de fallback)
    auth_bootstrap._destroy_splash(cast(auth_bootstrap.SplashLike, FakeSplashSemClose()), on_closed=bad_callback)


# ==================== Testes de _refresh_session_state ====================


def test_refresh_session_state_chama_refresh_current_user(monkeypatch):
    """Testa que _refresh_session_state() chama refresh_current_user_from_supabase()."""
    calls = []

    def fake_refresh():
        calls.append(True)

    monkeypatch.setattr("src.core.auth_bootstrap.refresh_current_user_from_supabase", fake_refresh)

    fake_client = MagicMock()
    auth_bootstrap._refresh_session_state(fake_client, None)

    assert len(calls) == 1


def test_refresh_session_state_loga_warning_quando_falha(monkeypatch):
    """Testa que _refresh_session_state() loga warning quando refresh_current_user falha."""

    def fake_refresh():
        raise RuntimeError("Refresh failed")

    monkeypatch.setattr("src.core.auth_bootstrap.refresh_current_user_from_supabase", fake_refresh)

    logger = MagicMock()
    fake_client = MagicMock()
    auth_bootstrap._refresh_session_state(fake_client, logger)

    assert logger.warning.called


def test_refresh_session_state_usa_log_default_quando_logger_none(monkeypatch):
    """Testa que _refresh_session_state() usa log padrão quando logger é None."""

    def fake_refresh():
        raise RuntimeError("Refresh failed")

    monkeypatch.setattr("src.core.auth_bootstrap.refresh_current_user_from_supabase", fake_refresh)

    # Não deve lançar exceção
    fake_client = MagicMock()
    auth_bootstrap._refresh_session_state(fake_client, None)


# ==================== Testes de is_persisted_auth_session_valid ====================


def test_is_persisted_auth_session_valid_retorna_false_quando_data_none():
    """Testa que is_persisted_auth_session_valid retorna False quando data é None."""
    # NOTA: A função aceita AuthSessionData mas trata None em runtime (linha 128: if not data)
    # O cast é necessário para passar None sem erro de tipo.
    assert auth_bootstrap.is_persisted_auth_session_valid(cast(Any, None)) is False


def test_is_persisted_auth_session_valid_retorna_false_quando_data_vazio():
    """Testa que is_persisted_auth_session_valid retorna False quando data é vazio."""
    assert auth_bootstrap.is_persisted_auth_session_valid({}) is False


def test_is_persisted_auth_session_valid_retorna_false_quando_keep_logged_false():
    """Testa que is_persisted_auth_session_valid retorna False quando keep_logged é False."""
    now = datetime.now(timezone.utc)
    created_at = (now - timedelta(days=1)).isoformat()
    data = {
        "access_token": "at",
        "refresh_token": "rt",
        "created_at": created_at,
        "keep_logged": False,  # False
    }
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=now) is False


def test_is_persisted_auth_session_valid_retorna_false_quando_access_token_vazio():
    """Testa que is_persisted_auth_session_valid retorna False quando access_token é vazio."""
    now = datetime.now(timezone.utc)
    created_at = (now - timedelta(days=1)).isoformat()
    data = {
        "access_token": "",  # Vazio
        "refresh_token": "rt",
        "created_at": created_at,
        "keep_logged": True,
    }
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=now) is False


def test_is_persisted_auth_session_valid_retorna_false_quando_refresh_token_vazio():
    """Testa que is_persisted_auth_session_valid retorna False quando refresh_token é vazio."""
    now = datetime.now(timezone.utc)
    created_at = (now - timedelta(days=1)).isoformat()
    data = {
        "access_token": "at",
        "refresh_token": "",  # Vazio
        "created_at": created_at,
        "keep_logged": True,
    }
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=now) is False


def test_is_persisted_auth_session_valid_retorna_false_quando_created_at_vazio():
    """Testa que is_persisted_auth_session_valid retorna False quando created_at é vazio."""
    now = datetime.now(timezone.utc)
    data = {
        "access_token": "at",
        "refresh_token": "rt",
        "created_at": "",  # Vazio
        "keep_logged": True,
    }
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=now) is False


def test_is_persisted_auth_session_valid_retorna_false_quando_created_at_invalido():
    """Testa que is_persisted_auth_session_valid retorna False quando created_at não é parseable."""
    now = datetime.now(timezone.utc)
    data = {
        "access_token": "at",
        "refresh_token": "rt",
        "created_at": "invalid-datetime",  # Inválido
        "keep_logged": True,
    }
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=now) is False


def test_is_persisted_auth_session_valid_adiciona_timezone_quando_naive():
    """Testa que is_persisted_auth_session_valid adiciona timezone UTC quando datetime é naive."""
    now = datetime(2025, 1, 8, tzinfo=timezone.utc)
    created_at_naive = "2025-01-07T10:00:00"  # Sem timezone
    data = {
        "access_token": "at",
        "refresh_token": "rt",
        "created_at": created_at_naive,
        "keep_logged": True,
    }
    # Deve ser válido (assumindo timezone UTC)
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=now, max_age_days=7) is True


def test_is_persisted_auth_session_valid_usa_now_padrao_quando_none():
    """Testa que is_persisted_auth_session_valid usa datetime.now(utc) quando now é None."""
    # Sessão criada há 1 dia
    created_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    data = {
        "access_token": "at",
        "refresh_token": "rt",
        "created_at": created_at,
        "keep_logged": True,
    }
    # Deve ser válido (now será datetime.now())
    assert auth_bootstrap.is_persisted_auth_session_valid(data, now=None, max_age_days=7) is True


# ==================== Testes de restore_persisted_auth_session_if_any ====================


def test_restore_persisted_auth_session_retorna_false_quando_load_falha(monkeypatch):
    """Testa que restore_persisted_auth_session_if_any retorna False quando load_auth_session falha."""

    def fake_load():
        raise RuntimeError("Load failed")

    monkeypatch.setattr("src.utils.prefs.load_auth_session", fake_load)

    fake_client = MagicMock()
    result = auth_bootstrap.restore_persisted_auth_session_if_any(fake_client)

    assert result is False


def test_restore_persisted_auth_session_limpa_sessao_quando_invalida(monkeypatch):
    """Testa que restore_persisted_auth_session_if_any limpa sessão quando data é inválida."""

    def fake_load():
        return {"keep_logged": False}  # Inválida

    clear_called = []

    def fake_clear():
        clear_called.append(True)

    monkeypatch.setattr("src.utils.prefs.load_auth_session", fake_load)
    monkeypatch.setattr("src.utils.prefs.clear_auth_session", fake_clear)

    fake_client = MagicMock()
    result = auth_bootstrap.restore_persisted_auth_session_if_any(fake_client)

    assert result is False
    assert len(clear_called) == 1


def test_restore_persisted_auth_session_ignora_excecao_ao_limpar_invalida(monkeypatch):
    """Testa que restore_persisted_auth_session_if_any ignora exceção ao limpar sessão inválida."""

    def fake_load():
        return {"keep_logged": False}

    def fake_clear():
        raise RuntimeError("Clear failed")

    monkeypatch.setattr("src.utils.prefs.load_auth_session", fake_load)
    monkeypatch.setattr("src.utils.prefs.clear_auth_session", fake_clear)

    fake_client = MagicMock()
    result = auth_bootstrap.restore_persisted_auth_session_if_any(fake_client)

    assert result is False


def test_restore_persisted_auth_session_limpa_quando_tokens_vazios(monkeypatch):
    """Testa que restore_persisted_auth_session_if_any limpa quando tokens estão vazios após validação."""
    now = datetime.now(timezone.utc)
    created_at = (now - timedelta(days=1)).isoformat()

    # Data válida MAS com tokens vazios (cenário edge)
    def fake_load():
        return {
            "access_token": "   ",  # Apenas espaços
            "refresh_token": "",
            "created_at": created_at,
            "keep_logged": True,
        }

    clear_called = []

    def fake_clear():
        clear_called.append(True)

    monkeypatch.setattr("src.utils.prefs.load_auth_session", fake_load)
    monkeypatch.setattr("src.utils.prefs.clear_auth_session", fake_clear)

    fake_client = MagicMock()
    result = auth_bootstrap.restore_persisted_auth_session_if_any(fake_client)

    assert result is False
    assert len(clear_called) == 1


def test_restore_persisted_auth_session_limpa_quando_set_session_falha(monkeypatch):
    """Testa que restore_persisted_auth_session_if_any limpa quando set_session lança exceção."""
    now = datetime.now(timezone.utc)
    created_at = (now - timedelta(days=1)).isoformat()

    def fake_load():
        return {
            "access_token": "at",
            "refresh_token": "rt",
            "created_at": created_at,
            "keep_logged": True,
        }

    clear_called = []

    def fake_clear():
        clear_called.append(True)

    monkeypatch.setattr("src.utils.prefs.load_auth_session", fake_load)
    monkeypatch.setattr("src.utils.prefs.clear_auth_session", fake_clear)

    fake_client = MagicMock()
    fake_client.auth.set_session.side_effect = RuntimeError("Set session failed")

    result = auth_bootstrap.restore_persisted_auth_session_if_any(fake_client)

    assert result is False
    assert len(clear_called) == 1


def test_restore_persisted_auth_session_ignora_excecao_ao_limpar_apos_set_session_falha(monkeypatch):
    """Testa que restore_persisted_auth_session_if_any ignora exceção ao limpar após set_session falhar."""
    now = datetime.now(timezone.utc)
    created_at = (now - timedelta(days=1)).isoformat()

    def fake_load():
        return {
            "access_token": "at",
            "refresh_token": "rt",
            "created_at": created_at,
            "keep_logged": True,
        }

    def fake_clear():
        raise RuntimeError("Clear failed")

    monkeypatch.setattr("src.utils.prefs.load_auth_session", fake_load)
    monkeypatch.setattr("src.utils.prefs.clear_auth_session", fake_clear)

    fake_client = MagicMock()
    fake_client.auth.set_session.side_effect = RuntimeError("Set session failed")

    result = auth_bootstrap.restore_persisted_auth_session_if_any(fake_client)

    assert result is False


def test_restore_persisted_auth_session_retorna_true_quando_sucesso(monkeypatch):
    """Testa que restore_persisted_auth_session_if_any retorna True quando set_session funciona."""
    now = datetime.now(timezone.utc)
    created_at = (now - timedelta(days=1)).isoformat()

    def fake_load():
        return {
            "access_token": "at",
            "refresh_token": "rt",
            "created_at": created_at,
            "keep_logged": True,
        }

    monkeypatch.setattr("src.utils.prefs.load_auth_session", fake_load)

    fake_client = MagicMock()
    result = auth_bootstrap.restore_persisted_auth_session_if_any(fake_client)

    assert result is True
    fake_client.auth.set_session.assert_called_once_with("at", "rt")


# ==================== Testes de _ensure_session ====================


def test_ensure_session_retorna_false_quando_client_none(monkeypatch, tk_root_session):
    """Testa que _ensure_session retorna False quando cliente Supabase não está disponível."""
    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: None)

    fake_app = MagicMock()
    result = auth_bootstrap._ensure_session(fake_app, None)

    assert result is False


def test_ensure_session_retorna_true_quando_ja_existe_sessao_valida(monkeypatch):
    """Testa que _ensure_session retorna True quando já existe sessão válida."""

    def fake_get_access_token(client):
        return "existing-token"

    monkeypatch.setattr("src.core.auth_bootstrap._get_access_token", fake_get_access_token)

    fake_client = MagicMock()
    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    fake_app = MagicMock()
    result = auth_bootstrap._ensure_session(fake_app, None)

    assert result is True


def test_ensure_session_abre_login_dialog_quando_sem_sessao(monkeypatch):
    """Testa que _ensure_session abre LoginDialog quando não há sessão."""

    def fake_get_access_token(client):
        return None

    monkeypatch.setattr("src.core.auth_bootstrap._get_access_token", fake_get_access_token)

    fake_client = MagicMock()
    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    # Mock restore e bind
    monkeypatch.setattr("src.core.auth_bootstrap.restore_persisted_auth_session_if_any", lambda c: None)
    monkeypatch.setattr("src.core.auth_bootstrap._bind_postgrest", lambda c: None)

    dialog_created = []

    class FakeLoginDialog:
        def __init__(self, master):
            dialog_created.append(master)
            self.login_success = False  # Login falhou

    monkeypatch.setattr("src.core.auth_bootstrap.LoginDialog", FakeLoginDialog)

    fake_app = MagicMock()
    auth_bootstrap._ensure_session(fake_app, None)

    assert len(dialog_created) == 1
    assert dialog_created[0] is fake_app


def test_ensure_session_retorna_true_apos_login_com_sucesso(monkeypatch):
    """Testa que _ensure_session retorna True após login bem-sucedido."""

    def fake_get_access_token(client):
        return None  # Sem sessão existente

    monkeypatch.setattr("src.core.auth_bootstrap._get_access_token", fake_get_access_token)

    fake_client = MagicMock()
    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    # Mock restore, bind e refresh
    monkeypatch.setattr("src.core.auth_bootstrap.restore_persisted_auth_session_if_any", lambda c: None)
    monkeypatch.setattr("src.core.auth_bootstrap._bind_postgrest", lambda c: None)
    monkeypatch.setattr("src.core.auth_bootstrap._refresh_session_state", lambda c, l: None)

    class FakeLoginDialog:
        def __init__(self, master):
            pass

        login_success = True  # Login bem-sucedido

    monkeypatch.setattr("src.core.auth_bootstrap.LoginDialog", FakeLoginDialog)

    fake_app = MagicMock()
    result = auth_bootstrap._ensure_session(fake_app, None)

    assert result is True


def test_ensure_session_retorna_false_quando_login_falha(monkeypatch):
    """Testa que _ensure_session retorna False quando login falha."""

    def fake_get_access_token(client):
        return None  # Sempre None (login falhou)

    monkeypatch.setattr("src.core.auth_bootstrap._get_access_token", fake_get_access_token)

    fake_client = MagicMock()
    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    # Mock restore e bind
    monkeypatch.setattr("src.core.auth_bootstrap.restore_persisted_auth_session_if_any", lambda c: None)
    monkeypatch.setattr("src.core.auth_bootstrap._bind_postgrest", lambda c: None)

    class FakeLoginDialog:
        def __init__(self, master):
            pass

        login_success = False  # Login falhou

    monkeypatch.setattr("src.core.auth_bootstrap.LoginDialog", FakeLoginDialog)

    fake_app = MagicMock()
    result = auth_bootstrap._ensure_session(fake_app, None)

    assert result is False


def test_ensure_session_ignora_excecao_ao_restaurar_sessao_persistida(monkeypatch):
    """Testa que _ensure_session ignora exceção ao restaurar sessão persistida."""

    def fake_restore(client):
        raise RuntimeError("Restore failed")

    def fake_get_access_token(client):
        return None

    monkeypatch.setattr("src.core.auth_bootstrap.restore_persisted_auth_session_if_any", fake_restore)
    monkeypatch.setattr("src.core.auth_bootstrap._get_access_token", fake_get_access_token)
    monkeypatch.setattr("src.core.auth_bootstrap._bind_postgrest", lambda c: None)

    fake_client = MagicMock()
    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    class FakeLoginDialog:
        def __init__(self, master):
            pass

        login_success = False

    monkeypatch.setattr("src.core.auth_bootstrap.LoginDialog", FakeLoginDialog)

    fake_app = MagicMock()
    # Não deve lançar exceção
    result = auth_bootstrap._ensure_session(fake_app, None)

    assert result is False


# ==================== Testes de _log_session_state ====================


def test_log_session_state_loga_info_quando_tem_usuario(monkeypatch):
    """Testa que _log_session_state loga info quando há usuário autenticado."""
    fake_client = MagicMock()
    fake_user = MagicMock()
    fake_user.id = "user123"
    fake_session = MagicMock()
    fake_session.user = fake_user
    fake_client.auth.get_session.return_value = fake_session

    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)
    monkeypatch.setattr("src.core.auth_bootstrap._get_access_token", lambda c: "token123")

    logger = MagicMock()
    auth_bootstrap._log_session_state(logger)

    assert logger.info.called


def test_log_session_state_loga_warning_quando_sem_usuario(monkeypatch):
    """Testa que _log_session_state loga warning quando get_session lança exceção."""
    fake_client = MagicMock()
    fake_client.auth.get_session.side_effect = RuntimeError("No session")

    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    logger = MagicMock()
    auth_bootstrap._log_session_state(logger)

    assert logger.warning.called


def test_log_session_state_usa_log_default_quando_logger_none(monkeypatch):
    """Testa que _log_session_state não quebra quando logger é None e cliente é None."""
    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: None)

    # Não deve lançar exceção
    auth_bootstrap._log_session_state(None)


# ==================== Testes de _update_footer_email ====================


def test_update_footer_email_atualiza_quando_tem_usuario(monkeypatch):
    """Testa que _update_footer_email atualiza footer quando há usuário."""
    fake_client = MagicMock()
    fake_user = MagicMock()
    fake_user.email = "test@example.com"
    fake_session = MagicMock()
    fake_session.user = fake_user
    fake_client.auth.get_session.return_value = fake_session

    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    fake_app = MagicMock()
    fake_app.layout_refs = None  # Força fallback para app.footer
    fake_app.footer = MagicMock()
    auth_bootstrap._update_footer_email(fake_app)

    fake_app.footer.set_user.assert_called_once_with("test@example.com")


def test_update_footer_email_nao_atualiza_quando_sem_usuario(monkeypatch):
    """Testa que _update_footer_email não atualiza footer quando session.user é None."""
    fake_client = MagicMock()
    fake_session = MagicMock()
    fake_session.user = None
    fake_client.auth.get_session.return_value = fake_session

    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    fake_app = MagicMock()
    fake_app.layout_refs = None  # Força fallback para app.footer
    fake_app.footer = MagicMock()
    auth_bootstrap._update_footer_email(fake_app)

    fake_app.footer.set_user.assert_not_called()


def test_update_footer_email_nao_quebra_quando_app_sem_metodo(monkeypatch):
    """Testa que _update_footer_email não quebra quando app não tem atributo footer."""
    fake_client = MagicMock()
    fake_user = MagicMock()
    fake_user.email = "test@example.com"
    fake_session = MagicMock()
    fake_session.user = fake_user
    fake_client.auth.get_session.return_value = fake_session

    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    fake_app = MagicMock(spec=["deiconify"])  # Sem footer

    # Não deve lançar exceção
    auth_bootstrap._update_footer_email(fake_app)


def test_update_footer_email_nao_quebra_quando_get_session_falha(monkeypatch):
    """Testa que _update_footer_email não quebra quando get_session lança exceção."""
    fake_client = MagicMock()
    fake_client.auth.get_session.side_effect = RuntimeError("Session error")

    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    fake_app = MagicMock()

    # Não deve lançar exceção
    auth_bootstrap._update_footer_email(fake_app)


# ==================== Testes de _mark_app_online ====================


def test_mark_app_online_restaura_janela_e_atualiza_status(monkeypatch):
    """Testa que _mark_app_online atualiza cloud status e user status sem tocar na janela."""
    fake_client = MagicMock()
    fake_user = MagicMock()
    fake_user.email = "test@example.com"
    fake_session = MagicMock()
    fake_session.user = fake_user
    fake_client.auth.get_session.return_value = fake_session

    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    fake_app = MagicMock()
    fake_status_monitor = MagicMock()
    fake_app._status_monitor = fake_status_monitor
    fake_app.footer = MagicMock()

    auth_bootstrap._mark_app_online(fake_app, None)

    # _mark_app_online não chama mais deiconify
    fake_app.deiconify.assert_not_called()
    fake_status_monitor.set_cloud_status.assert_called_once_with(True)
    fake_app._update_user_status.assert_called_once()


def test_mark_app_online_funciona_sem_status_monitor(monkeypatch):
    """Testa que _mark_app_online funciona quando app não tem _status_monitor."""
    fake_client = MagicMock()
    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    fake_app = MagicMock(spec=["_update_user_status"])  # Sem _status_monitor

    # Não deve lançar exceção
    auth_bootstrap._mark_app_online(fake_app, None)

    # Não exige deiconify mais
    fake_app._update_user_status.assert_called_once()


def test_mark_app_online_loga_warning_quando_falha_set_cloud_status(monkeypatch):
    """Testa que _mark_app_online loga debug quando set_cloud_status falha."""
    fake_client = MagicMock()
    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    fake_app = MagicMock()
    fake_status_monitor = MagicMock()
    fake_status_monitor.set_cloud_status.side_effect = RuntimeError("Monitor failed")
    fake_app._status_monitor = fake_status_monitor

    logger = MagicMock()
    auth_bootstrap._mark_app_online(fake_app, logger)

    assert logger.debug.called


def test_mark_app_online_loga_warning_quando_falha_update_user_status(monkeypatch):
    """Testa que _mark_app_online loga warning quando _update_user_status falha."""
    fake_client = MagicMock()
    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    fake_app = MagicMock()
    fake_app._update_user_status.side_effect = RuntimeError("Update failed")

    logger = MagicMock()
    auth_bootstrap._mark_app_online(fake_app, logger)

    assert logger.warning.called


def test_mark_app_online_loga_debug_quando_falha_deiconify(monkeypatch):
    """Testa que _mark_app_online loga debug quando set_cloud_status falha (teste renomeado)."""
    # Teste renomeado: agora verifica log debug quando set_cloud_status falha
    # (não mais deiconify, que não é responsabilidade de _mark_app_online)
    fake_client = MagicMock()
    monkeypatch.setattr("src.core.auth_bootstrap._supabase_client", lambda: fake_client)

    fake_app = MagicMock()
    fake_status_monitor = MagicMock()
    fake_status_monitor.set_cloud_status.side_effect = RuntimeError("Monitor failed")
    fake_app._status_monitor = fake_status_monitor

    logger = MagicMock()
    auth_bootstrap._mark_app_online(fake_app, logger)

    assert logger.debug.called


# ==================== Testes de ensure_logged ====================


def test_ensure_logged_destroi_splash_e_aguarda(monkeypatch):
    """Testa que ensure_logged destrói splash e aguarda antes de prosseguir."""
    # Ensure_session retorna True (login bem-sucedido)
    monkeypatch.setattr("src.core.auth_bootstrap._ensure_session", lambda a, l: True)

    # Log e mark online
    monkeypatch.setattr("src.core.auth_bootstrap._log_session_state", lambda l: None)
    monkeypatch.setattr("src.core.auth_bootstrap._mark_app_online", lambda a, l: None)

    # Destroy splash
    destroy_called = []
    monkeypatch.setattr("src.core.auth_bootstrap._destroy_splash", lambda s: destroy_called.append(s))

    fake_app = MagicMock()
    fake_splash = MagicMock()

    result = auth_bootstrap.ensure_logged(fake_app, splash=fake_splash)

    assert result is True
    assert len(destroy_called) == 1
    fake_app.wait_window.assert_called_once_with(fake_splash)


def test_ensure_logged_marca_app_online_quando_login_sucesso(monkeypatch):
    """Testa que ensure_logged marca app online quando login tem sucesso."""
    # Ensure_session retorna True
    monkeypatch.setattr("src.core.auth_bootstrap._ensure_session", lambda a, l: True)

    # Log
    monkeypatch.setattr("src.core.auth_bootstrap._log_session_state", lambda l: None)

    # Mark online
    mark_called = []
    monkeypatch.setattr("src.core.auth_bootstrap._mark_app_online", lambda a, l: mark_called.append(a))

    # Destroy splash
    monkeypatch.setattr("src.core.auth_bootstrap._destroy_splash", lambda s: None)

    fake_app = MagicMock()

    result = auth_bootstrap.ensure_logged(fake_app, splash=None)

    assert result is True
    assert len(mark_called) == 1
    assert mark_called[0] is fake_app


def test_ensure_logged_retorna_false_quando_login_falha(monkeypatch):
    """Testa que ensure_logged retorna False quando login falha."""
    # Ensure_session retorna False (login falhou)
    monkeypatch.setattr("src.core.auth_bootstrap._ensure_session", lambda a, l: False)

    # Log (sempre chamado)
    monkeypatch.setattr("src.core.auth_bootstrap._log_session_state", lambda l: None)

    # Mark online NÃO deve ser chamado
    mark_called = []
    monkeypatch.setattr("src.core.auth_bootstrap._mark_app_online", lambda a, l: mark_called.append(a))

    # Destroy splash
    monkeypatch.setattr("src.core.auth_bootstrap._destroy_splash", lambda s: None)

    fake_app = MagicMock()

    result = auth_bootstrap.ensure_logged(fake_app, splash=None)

    assert result is False
    assert len(mark_called) == 0


def test_ensure_logged_ignora_excecao_ao_destruir_splash(monkeypatch):
    """Testa que ensure_logged ignora exceção ao destruir splash."""

    def fake_destroy(splash):
        raise RuntimeError("Destroy failed")

    monkeypatch.setattr("src.core.auth_bootstrap._destroy_splash", fake_destroy)
    monkeypatch.setattr("src.core.auth_bootstrap._ensure_session", lambda a, l: True)
    monkeypatch.setattr("src.core.auth_bootstrap._log_session_state", lambda l: None)
    monkeypatch.setattr("src.core.auth_bootstrap._mark_app_online", lambda a, l: None)

    fake_app = MagicMock()
    fake_splash = MagicMock()

    # Não deve lançar exceção
    result = auth_bootstrap.ensure_logged(fake_app, splash=fake_splash)

    assert result is True


def test_ensure_logged_ignora_excecao_ao_aguardar_splash(monkeypatch):
    """Testa que ensure_logged ignora exceção ao aguardar splash encerrar."""
    monkeypatch.setattr("src.core.auth_bootstrap._destroy_splash", lambda s: None)
    monkeypatch.setattr("src.core.auth_bootstrap._ensure_session", lambda a, l: True)
    monkeypatch.setattr("src.core.auth_bootstrap._log_session_state", lambda l: None)
    monkeypatch.setattr("src.core.auth_bootstrap._mark_app_online", lambda a, l: None)

    fake_app = MagicMock()
    fake_app.wait_window.side_effect = RuntimeError("Wait failed")
    fake_splash = MagicMock()

    # Não deve lançar exceção
    result = auth_bootstrap.ensure_logged(fake_app, splash=fake_splash)

    assert result is True


def test_ensure_logged_retorna_false_quando_ensure_session_lanca_excecao(monkeypatch, tk_root_session):
    """Testa que ensure_logged retorna False quando _ensure_session lança exceção."""

    def fake_ensure_session(app, logger):
        raise RuntimeError("Session failed")

    monkeypatch.setattr("src.core.auth_bootstrap._ensure_session", fake_ensure_session)
    monkeypatch.setattr("src.core.auth_bootstrap._destroy_splash", lambda s: None)
    monkeypatch.setattr("src.core.auth_bootstrap._log_session_state", lambda l: None)

    # Mark online NÃO deve ser chamado
    mark_called = []
    monkeypatch.setattr("src.core.auth_bootstrap._mark_app_online", lambda a, l: mark_called.append(a))

    fake_app = MagicMock()

    result = auth_bootstrap.ensure_logged(fake_app, splash=None)

    assert result is False
    assert len(mark_called) == 0


def test_ensure_logged_funciona_sem_splash(monkeypatch):
    """Testa que ensure_logged funciona quando splash não é fornecido."""
    monkeypatch.setattr("src.core.auth_bootstrap._ensure_session", lambda a, l: True)
    monkeypatch.setattr("src.core.auth_bootstrap._log_session_state", lambda l: None)
    monkeypatch.setattr("src.core.auth_bootstrap._mark_app_online", lambda a, l: None)

    destroy_called = []
    monkeypatch.setattr("src.core.auth_bootstrap._destroy_splash", lambda s: destroy_called.append(s))

    fake_app = MagicMock()

    # Sem especificar splash (padrão None)
    result = auth_bootstrap.ensure_logged(fake_app)

    assert result is True
    # _destroy_splash não é chamado quando splash is None
    assert len(destroy_called) == 0
    fake_app.wait_window.assert_not_called()
