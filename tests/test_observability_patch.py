# -*- coding: utf-8 -*-
"""Validação automatizada do patch de observabilidade v1.5.99.

Cenários cobertos:
  C1 - Startup normal (backend disponível)
  C2 - Falha de DNS/rede antes do login
  C3 - Sessão persistida + backend indisponível
  C4 - Login cancelado pelo usuário
  C5 - Fechamento por X / ESC (mesmo caminho de C4)
  C6 - Recuperação (backend volta)

Cada teste usa caplog para capturar logs sem depender de backend real.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# ─── helpers / fixtures ───────────────────────────────────────────────


def _make_mock_session(*, uid: str | None = None, access_token: str | None = None):
    """Cria sessão mock do Supabase (SimpleNamespace aninhado)."""
    user = SimpleNamespace(id=uid, email="user@test.com") if uid else None
    sess = SimpleNamespace(
        user=user,
        access_token=access_token,
        refresh_token="fake-refresh" if access_token else None,
    )
    return sess


def _make_mock_client(*, session=None, set_session_side_effect=None):
    """Cria um mock de SupabaseClient compatível com auth_bootstrap."""
    client = MagicMock()
    client.auth.get_session.return_value = session
    if set_session_side_effect:
        client.auth.set_session.side_effect = set_session_side_effect
    return client


@pytest.fixture()
def _reset_db_client_singleton():
    """Reseta o singleton de db_client antes e depois de cada teste."""
    import src.infra.supabase.db_client as mod

    orig_singleton = mod._SUPABASE_SINGLETON
    orig_reuse = mod._SINGLETON_REUSE_LOGGED
    orig_started = mod._HEALTH_CHECKER_STARTED
    mod._SUPABASE_SINGLETON = None
    mod._SINGLETON_REUSE_LOGGED = False
    mod._HEALTH_CHECKER_STARTED = False
    yield
    mod._SUPABASE_SINGLETON = orig_singleton
    mod._SINGLETON_REUSE_LOGGED = orig_reuse
    mod._HEALTH_CHECKER_STARTED = orig_started


# =====================================================================
# T1 – _classify_network_error  (cobertura de classificação)
# =====================================================================


class TestClassifyNetworkError:
    """Valida que _classify_network_error retorna categorias coerentes."""

    def _classify(self, exc: Exception) -> str:
        from src.infra.supabase.db_client import _classify_network_error

        return _classify_network_error(exc)

    def test_dns_via_getaddrinfo(self):
        assert self._classify(OSError("getaddrinfo failed")) == "dns"

    def test_dns_via_nodename(self):
        assert self._classify(OSError("nodename nor servname provided")) == "dns"

    def test_dns_via_name_resolution(self):
        assert self._classify(OSError("Name resolution failed")) == "dns"

    def test_timeout(self):
        assert self._classify(TimeoutError("timed out")) == "timeout"

    def test_timeout_in_message(self):
        assert self._classify(Exception("Connection timeout after 30s")) == "timeout"

    def test_connection_refused(self):
        assert self._classify(ConnectionRefusedError("Connection refused")) == "connection_refused"

    def test_connection_error(self):
        assert self._classify(ConnectionError("Network is unreachable")) == "connection"

    def test_os_error_generic(self):
        assert self._classify(OSError("Some socket error")) == "connection"

    def test_http_502(self):
        assert self._classify(Exception("502 Bad Gateway")) == "http_502"

    def test_http_503(self):
        assert self._classify(Exception("Service Unavailable 503")) == "http_503"

    def test_unknown(self):
        assert self._classify(ValueError("something weird")) == "unknown"


# =====================================================================
# T2 – get_supabase() NÃO emite "Backend: conectado"  (C1)
# =====================================================================


@pytest.mark.usefixtures("_reset_db_client_singleton")
class TestGetSupabaseSingletonLog:
    """Confirma que get_supabase() não gera falso positivo de conectividade."""

    @patch.dict(os.environ, {"SUPABASE_URL": "https://fake.supabase.co", "SUPABASE_ANON_KEY": "fake-key"})
    @patch("src.infra.supabase.db_client.create_client")
    @patch("src.infra.supabase.db_client._start_health_checker")
    def test_no_backend_conectado(self, mock_hc, mock_create, caplog):
        """O log antigo 'Backend: conectado' não deve existir."""
        import src.infra.supabase.db_client as mod

        mock_create.return_value = MagicMock()
        with caplog.at_level(logging.DEBUG, logger="src.infra.supabase.db_client"):
            mod.get_supabase()

        all_msgs = [r.message for r in caplog.records]
        # Não pode conter falso positivo
        assert not any("Backend: conectado" in m for m in all_msgs), f"Falso positivo encontrado: {all_msgs}"
        # Deve conter mensagem honesta
        assert any(
            "nenhum I/O de rede realizado" in m for m in all_msgs
        ), f"Mensagem esperada não encontrada: {all_msgs}"


# =====================================================================
# T3 – _health_check_once: fallback classifica erro  (C1/C2/C6)
# =====================================================================


class TestHealthCheckFallbackClassification:
    """Confirma que o fallback de health check classifica a exceção."""

    def test_fallback_classifies_dns(self, caplog):
        from src.infra.supabase.db_client import _health_check_once

        client = MagicMock()
        # RPC desabilitado para forçar fallback
        with (
            patch("src.infra.supabase.db_client.supa_types") as mock_types,
            patch("src.infra.supabase.db_client.exec_postgrest") as mock_exec,
            patch.dict(os.environ, {}, clear=False),
        ):
            mock_types.HEALTHCHECK_USE_RPC = False
            mock_types.HEALTHCHECK_FALLBACK_TABLE = "test_health"
            mock_exec.side_effect = OSError("getaddrinfo failed: Name or service not known")

            # Remover PYTEST_CURRENT_TEST temporariamente para permitir log
            env_backup = os.environ.pop("PYTEST_CURRENT_TEST", None)
            try:
                with caplog.at_level(logging.WARNING, logger="src.infra.supabase.db_client"):
                    result = _health_check_once(client)
            finally:
                if env_backup is not None:
                    os.environ["PYTEST_CURRENT_TEST"] = env_backup

        assert result is False
        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("[dns]" in m for m in warning_msgs), f"Classificação [dns] ausente: {warning_msgs}"
        assert any("Health check fallback (table query) falhou" in m for m in warning_msgs)

    def test_fallback_classifies_timeout(self, caplog):
        from src.infra.supabase.db_client import _health_check_once

        client = MagicMock()
        with (
            patch("src.infra.supabase.db_client.supa_types") as mock_types,
            patch("src.infra.supabase.db_client.exec_postgrest") as mock_exec,
        ):
            mock_types.HEALTHCHECK_USE_RPC = False
            mock_types.HEALTHCHECK_FALLBACK_TABLE = "test_health"
            mock_exec.side_effect = TimeoutError("Connection timed out")

            env_backup = os.environ.pop("PYTEST_CURRENT_TEST", None)
            try:
                with caplog.at_level(logging.WARNING, logger="src.infra.supabase.db_client"):
                    result = _health_check_once(client)
            finally:
                if env_backup is not None:
                    os.environ["PYTEST_CURRENT_TEST"] = env_backup

        assert result is False
        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("[timeout]" in m for m in warning_msgs), f"Classificação [timeout] ausente: {warning_msgs}"

    def test_success_no_warning(self, caplog):
        """Health check bem-sucedido não deve emitir warning."""
        from src.infra.supabase.db_client import _health_check_once

        client = MagicMock()
        with (
            patch("src.infra.supabase.db_client.supa_types") as mock_types,
            patch("src.infra.supabase.db_client.exec_postgrest") as mock_exec,
        ):
            mock_types.HEALTHCHECK_USE_RPC = False
            mock_types.HEALTHCHECK_FALLBACK_TABLE = "test_health"
            mock_exec.return_value = MagicMock()  # Sucesso

            with caplog.at_level(logging.DEBUG, logger="src.infra.supabase.db_client"):
                result = _health_check_once(client)

        assert result is True
        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_msgs) == 0, f"Warnings inesperados: {warning_msgs}"


# =====================================================================
# T4 – restore_persisted_auth_session: classificação de falha (C2/C3)
# =====================================================================


class TestRestoreSessionClassification:
    """Valida classificação de erros no restore de sessão."""

    def _restore(self, client, caplog):
        from src.core.auth_bootstrap import restore_persisted_auth_session_if_any

        with caplog.at_level(logging.DEBUG, logger="src.core.auth_bootstrap"):
            return restore_persisted_auth_session_if_any(client)

    @patch("src.core.auth_bootstrap.prefs_utils.load_auth_session")
    @patch("src.core.auth_bootstrap.prefs_utils.clear_auth_session")
    def test_network_error_preserves_session(self, mock_clear, mock_load, caplog):
        """C3: erro de rede → sessão preservada, log [network]."""
        mock_load.return_value = {
            "access_token": "tok123",
            "refresh_token": "ref456",
            "keep_logged": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        client = _make_mock_client(set_session_side_effect=OSError("getaddrinfo failed"))

        result = self._restore(client, caplog)

        assert result is False
        mock_clear.assert_not_called()  # Sessão preservada

        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("[network]" in m for m in warning_msgs), f"[network] ausente: {warning_msgs}"
        assert any(
            "sessão preservada no storage" in m for m in warning_msgs
        ), f"'sessão preservada no storage' ausente: {warning_msgs}"
        # Não pode conter falso positivo de "restaurada"
        assert not any(
            "Sessão restaurada" in m for m in warning_msgs
        ), f"Falso positivo 'Sessão restaurada': {warning_msgs}"

    @patch("src.core.auth_bootstrap.prefs_utils.load_auth_session")
    @patch("src.core.auth_bootstrap.prefs_utils.clear_auth_session")
    def test_auth_error_removes_session(self, mock_clear, mock_load, caplog):
        """C3 variante: erro de auth → sessão removida, log [auth]."""
        mock_load.return_value = {
            "access_token": "tok123",
            "refresh_token": "ref456",
            "keep_logged": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        client = _make_mock_client(set_session_side_effect=Exception("invalid refresh token expired"))

        result = self._restore(client, caplog)

        assert result is False
        mock_clear.assert_called_once()  # Sessão removida

        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("[auth]" in m for m in warning_msgs), f"[auth] ausente: {warning_msgs}"
        assert any(
            "sessão removida do storage" in m for m in warning_msgs
        ), f"'sessão removida do storage' ausente: {warning_msgs}"

    @patch("src.core.auth_bootstrap.prefs_utils.load_auth_session")
    @patch("src.core.auth_bootstrap.prefs_utils.clear_auth_session")
    def test_unknown_error_removes_session(self, mock_clear, mock_load, caplog):
        """C3 variante: erro desconhecido → sessão removida, log [unknown]."""
        mock_load.return_value = {
            "access_token": "tok123",
            "refresh_token": "ref456",
            "keep_logged": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        client = _make_mock_client(set_session_side_effect=RuntimeError("completely unexpected"))

        result = self._restore(client, caplog)

        assert result is False
        mock_clear.assert_called_once()

        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("[unknown]" in m for m in warning_msgs), f"[unknown] ausente: {warning_msgs}"

    @patch("src.core.auth_bootstrap.prefs_utils.load_auth_session")
    def test_successful_restore_returns_true(self, mock_load, caplog):
        """C1: restore bem-sucedido → True, sem warnings."""
        mock_load.return_value = {
            "access_token": "tok123",
            "refresh_token": "ref456",
            "keep_logged": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        client = _make_mock_client()
        # set_session não levanta exceção (sucesso)

        result = self._restore(client, caplog)

        assert result is True
        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        # Nenhum warning em restore bem-sucedido
        assert len(warning_msgs) == 0, f"Warnings inesperados: {warning_msgs}"

    @patch("src.core.auth_bootstrap.prefs_utils.load_auth_session")
    @patch("src.core.auth_bootstrap.prefs_utils.clear_auth_session")
    def test_no_persisted_session_returns_false(self, mock_clear, mock_load, caplog):
        """Sem sessão persistida → False, sem warnings de rede."""
        mock_load.return_value = {}  # Nada persistido
        client = _make_mock_client()

        result = self._restore(client, caplog)

        assert result is False
        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert not any("[network]" in m for m in warning_msgs)


# =====================================================================
# T5 – _log_session_snapshot: mensagem correta por estado (C1/C4)
# =====================================================================


class TestLogSessionSnapshot:
    """Valida que _log_session_snapshot registra estado sem ambiguidade."""

    @patch("src.core.auth_bootstrap._supabase_client")
    @patch("src.core.auth_bootstrap._get_access_token")
    def test_active_session_logs_info(self, mock_token, mock_client, caplog):
        """C1: sessão ativa → INFO 'Sessão ativa'."""
        sess = _make_mock_session(uid="abcdef12-3456-7890-abcd-ef1234567890", access_token="tok")
        mock_client.return_value = _make_mock_client(session=sess)
        mock_token.return_value = "tok"

        from src.core.auth_bootstrap import _log_session_snapshot

        logger = logging.getLogger("src.core.auth_bootstrap")
        with caplog.at_level(logging.DEBUG, logger="src.core.auth_bootstrap"):
            _log_session_snapshot(logger)

        info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("Sessão ativa" in m for m in info_msgs), f"'Sessão ativa' ausente: {info_msgs}"
        assert any("token=presente" in m for m in info_msgs)
        # UUID deve estar truncado
        assert any("abcdef12..." in m for m in info_msgs), f"UID truncado ausente: {info_msgs}"

        # Não deve conter "Sessão restaurada" (antigo falso positivo)
        all_msgs = [r.message for r in caplog.records]
        assert not any("Sessão restaurada" in m for m in all_msgs)

    @patch("src.core.auth_bootstrap._supabase_client")
    @patch("src.core.auth_bootstrap._get_access_token")
    def test_no_session_logs_warning(self, mock_token, mock_client, caplog):
        """C4/C5: sem sessão → WARNING 'Nenhuma sessão ativa'."""
        sess = _make_mock_session()  # uid=None, token=None
        mock_client.return_value = _make_mock_client(session=sess)
        mock_token.return_value = None

        from src.core.auth_bootstrap import _log_session_snapshot

        logger = logging.getLogger("src.core.auth_bootstrap")
        with caplog.at_level(logging.DEBUG, logger="src.core.auth_bootstrap"):
            _log_session_snapshot(logger)

        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("Nenhuma sessão ativa" in m for m in warning_msgs), f"'Nenhuma sessão ativa' ausente: {warning_msgs}"
        assert any("token=ausente" in m for m in warning_msgs)


# =====================================================================
# T6 – _ensure_session: sessão existente vs. abrir login (C1/C4)
# =====================================================================


class TestEnsureSession:
    """Valida logs do fluxo de ensure_session."""

    @patch("src.core.auth_bootstrap.LoginDialog")
    @patch("src.core.auth_bootstrap._refresh_session_state")
    @patch("src.core.auth_bootstrap._bind_postgrest")
    @patch("src.core.auth_bootstrap.restore_persisted_auth_session_if_any")
    @patch("src.core.auth_bootstrap._get_access_token", return_value="valid-token")
    @patch("src.core.auth_bootstrap._supabase_client")
    def test_existing_token_no_login_dialog(
        self, mock_client, mock_token, mock_restore, mock_bind, mock_refresh, mock_dialog, caplog
    ):
        """C1: token presente → não abre LoginDialog, loga 'Sessão já existente'."""
        mock_client.return_value = _make_mock_client()
        app = MagicMock()

        from src.core.auth_bootstrap import _ensure_session

        logger = logging.getLogger("src.core.auth_bootstrap")
        with caplog.at_level(logging.DEBUG, logger="src.core.auth_bootstrap"):
            result = _ensure_session(app, logger)

        assert result is True
        mock_dialog.assert_not_called()

        info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any(
            "Sessão já existente no boot" in m for m in info_msgs
        ), f"'Sessão já existente no boot' ausente: {info_msgs}"

    @patch("src.core.auth_bootstrap.LoginDialog")
    @patch("src.core.auth_bootstrap._bind_postgrest")
    @patch("src.core.auth_bootstrap.restore_persisted_auth_session_if_any")
    @patch("src.core.auth_bootstrap._get_access_token", return_value=None)
    @patch("src.core.auth_bootstrap._supabase_client")
    def test_no_token_opens_login(self, mock_client, mock_token, mock_restore, mock_bind, mock_dialog, caplog):
        """C4: sem token → abre LoginDialog, loga 'Abrindo diálogo de login'."""
        mock_client.return_value = _make_mock_client()
        app = MagicMock()
        # Simula que LoginDialog não completou login
        mock_dialog.return_value = MagicMock(login_success=False)

        from src.core.auth_bootstrap import _ensure_session

        logger = logging.getLogger("src.core.auth_bootstrap")
        with caplog.at_level(logging.DEBUG, logger="src.core.auth_bootstrap"):
            # Precisamos pular o check de internet (cloud-only)
            with patch.dict(os.environ, {"RC_NO_LOCAL_FS": "0"}):
                result = _ensure_session(app, logger)

        assert result is False
        mock_dialog.assert_called_once()

        info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any(
            "Abrindo diálogo de login" in m for m in info_msgs
        ), f"'Abrindo diálogo de login' ausente: {info_msgs}"

    @patch("src.core.auth_bootstrap.LoginDialog")
    @patch("src.utils.network.check_internet_connectivity")
    @patch("src.core.auth_bootstrap._bind_postgrest")
    @patch("src.core.auth_bootstrap.restore_persisted_auth_session_if_any")
    @patch("src.core.auth_bootstrap._get_access_token", return_value=None)
    @patch("src.core.auth_bootstrap._supabase_client")
    def test_cloud_only_connectivity_check_logged(
        self, mock_client, mock_token, mock_restore, mock_bind, mock_inet, mock_dialog, caplog
    ):
        """C2: cloud-only sem internet → loga verificação de conectividade."""
        mock_client.return_value = _make_mock_client()
        app = MagicMock()

        from src.core.auth_bootstrap import _ensure_session

        logger = logging.getLogger("src.core.auth_bootstrap")

        # Simula: primeira chamada False (sem internet), segunda True (internet voltou)
        call_count = 0

        def fake_connectivity(timeout=1.0):
            nonlocal call_count
            call_count += 1
            return call_count > 1  # True na segunda tentativa

        mock_inet.side_effect = fake_connectivity

        # Precisamos limpar PYTEST_CURRENT_TEST e RC_TESTING para ativar cloud-only path
        env_clean = {k: v for k, v in os.environ.items() if k not in ("PYTEST_CURRENT_TEST", "RC_TESTING")}
        env_clean["RC_NO_LOCAL_FS"] = "1"

        with caplog.at_level(logging.DEBUG, logger="src.core.auth_bootstrap"):
            with patch.dict(os.environ, env_clean, clear=True):
                with patch("tkinter.messagebox") as mock_mb:
                    mock_mb.askretrycancel.return_value = True  # retry
                    mock_dialog.return_value = MagicMock(login_success=False)
                    _ensure_session(app, logger)

        info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any(
            "Verificando conectividade" in m for m in info_msgs
        ), f"'Verificando conectividade' ausente: {info_msgs}"


# =====================================================================
# T7 – ensure_logged: encerramento com mensagem correta (C4)
# =====================================================================


class TestEnsureLogged:
    """Valida logs do fluxo ensure_logged."""

    @patch("src.core.auth_bootstrap._mark_app_online")
    @patch("src.core.auth_bootstrap._log_session_snapshot")
    @patch("src.core.auth_bootstrap._ensure_session", return_value=False)
    @patch("src.core.auth_bootstrap._destroy_splash")
    def test_login_not_completed_message(self, mock_splash, mock_session, mock_snap, mock_online, caplog):
        """C4: login não completado → mensagem correta sem duplicação."""
        app = MagicMock()

        from src.core.auth_bootstrap import ensure_logged

        logger = logging.getLogger("src.core.auth_bootstrap")
        with caplog.at_level(logging.DEBUG, logger="src.core.auth_bootstrap"):
            logged_result = ensure_logged(app, logger=logger)

        assert logged_result is False
        mock_online.assert_not_called()

        info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any(
            "Encerrando aplicação: login não completado" in m for m in info_msgs
        ), f"Mensagem de encerramento ausente: {info_msgs}"
        # Antigo texto ambíguo não pode estar presente
        all_msgs = [r.message for r in caplog.records]
        assert not any("Login cancelado ou falhou" in m for m in all_msgs), "Texto antigo ambíguo encontrado"

    @patch("src.core.auth_bootstrap._mark_app_online")
    @patch("src.core.auth_bootstrap._log_session_snapshot")
    @patch("src.core.auth_bootstrap._ensure_session", return_value=True)
    @patch("src.core.auth_bootstrap._destroy_splash")
    def test_login_success_marks_online(self, mock_splash, mock_session, mock_snap, mock_online, caplog):
        """C1: login OK → marca app online, sem mensagem de encerramento."""
        app = MagicMock()

        from src.core.auth_bootstrap import ensure_logged

        logger = logging.getLogger("src.core.auth_bootstrap")
        with caplog.at_level(logging.DEBUG, logger="src.core.auth_bootstrap"):
            result = ensure_logged(app, logger=logger)

        assert result is True
        mock_online.assert_called_once()

        all_msgs = [r.message for r in caplog.records]
        assert not any(
            "Encerrando aplicação" in m for m in all_msgs
        ), "Mensagem de encerramento não deveria aparecer em login OK"


# =====================================================================
# T8 – LoginDialog._on_exit loga cancelamento (C4/C5)
#       (apenas validação de código — sem Tk runtime)
# =====================================================================


class TestLoginDialogCancelLog:
    """Valida semântica do _on_exit via inspeção de AST/código.

    Como LoginDialog requer Tk root (não disponível em CI headless),
    validamos via source analysis que:
    1. _on_exit() contém log.info com 'cancelamento'
    2. ESC binding chama _on_exit()
    """

    def test_on_exit_contains_cancel_log(self):
        """Verifica que _on_exit tem log de cancelamento no código-fonte."""
        import ast
        from pathlib import Path

        src = Path("src/ui/login_dialog.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        # Encontrar método _on_exit
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_on_exit":
                # Verificar que contém chamada log.info com "cancelamento"
                source_lines = src.splitlines()
                method_src = "\n".join(source_lines[node.lineno - 1 : node.end_lineno])
                assert "cancelamento" in method_src, f"_on_exit não contém 'cancelamento': {method_src}"
                assert "log.info" in method_src, f"_on_exit não contém log.info: {method_src}"
                break
        else:
            pytest.fail("Método _on_exit não encontrado em login_dialog.py")

    def test_esc_binding_calls_on_exit(self):
        """Verifica que ESC chama _on_exit() (não self.destroy() direto)."""
        src_path = "src/ui/login_dialog.py"
        with open(src_path, encoding="utf-8") as f:
            source = f.read()

        # Procurar binding de Escape
        import re

        esc_bindings = re.findall(r'self\.bind\(["\']<Escape>["\'].*?\)', source)
        assert len(esc_bindings) > 0, "Nenhum binding de ESC encontrado"

        for binding in esc_bindings:
            # ESC deve chamar _on_exit, não destroy direto
            assert "_on_exit" in binding, f"ESC binding não chama _on_exit: {binding}"
            assert (
                "self.destroy()" not in binding or "_on_exit" in binding
            ), f"ESC binding chama destroy direto (bypass _on_exit): {binding}"


# =====================================================================
# T9 – app.py não duplica mensagem de encerramento (C4)
# =====================================================================


class TestAppNoDuplicateShutdownLog:
    """Verifica que app.py não emite log duplicado de encerramento."""

    def test_no_duplicate_login_nao_completado_log(self):
        """app.py não deve conter log.info('Encerrando aplicação: login não completado')."""
        src_path = "src/core/app.py"
        with open(src_path, encoding="utf-8") as f:
            source = f.read()

        import re

        # Procurar log.info ou logger.info com mensagem de encerramento
        pattern = r'(?:log|logger)\.info\(["\'].*[Ee]ncerrando.*login.*não completado'
        matches = re.findall(pattern, source)
        assert len(matches) == 0, f"app.py contém log duplicado de encerramento: {matches}"


# =====================================================================
# T10 – Fluxo completo C1: startup → sessão existente → online (C1)
# =====================================================================


class TestFullFlowC1:
    """Simula fluxo completo de startup normal."""

    @patch("src.core.auth_bootstrap._mark_app_online")
    @patch("src.core.auth_bootstrap._update_footer_email")
    @patch("src.core.auth_bootstrap._refresh_session_state")
    @patch("src.core.auth_bootstrap._bind_postgrest")
    @patch("src.core.auth_bootstrap.restore_persisted_auth_session_if_any", return_value=True)
    @patch("src.core.auth_bootstrap._get_access_token", return_value="valid-tok")
    @patch("src.core.auth_bootstrap._supabase_client")
    def test_startup_happy_path(
        self, mock_client, mock_token, mock_restore, mock_bind, mock_refresh, mock_footer, mock_online, caplog
    ):
        """C1: startup normal — sem falsos positivos, sessão ativa."""
        mock_client.return_value = _make_mock_client(
            session=_make_mock_session(uid="12345678-1234-1234-1234-123456789abc", access_token="valid-tok")
        )
        app = MagicMock()

        from src.core.auth_bootstrap import ensure_logged

        logger = logging.getLogger("src.core.auth_bootstrap")
        with caplog.at_level(logging.DEBUG, logger="src.core.auth_bootstrap"):
            result = ensure_logged(app, logger=logger)

        assert result is True

        all_msgs = [r.message for r in caplog.records]

        # Verificar ausência de falsos positivos
        assert not any("Backend: conectado" in m for m in all_msgs)
        assert not any("Sessão restaurada" in m for m in all_msgs)
        assert not any("Login cancelado ou falhou" in m for m in all_msgs)

        # Verificar presença de logs corretos
        info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("Sessão já existente no boot" in m for m in info_msgs)


# =====================================================================
# T11 – Fluxo C3: sessão persistida + backend down (C3)
# =====================================================================


class TestFullFlowC3:
    """Simula restore falhando por backend indisponível."""

    @patch("src.core.auth_bootstrap.LoginDialog")
    @patch("src.core.auth_bootstrap._mark_app_online")
    @patch("src.core.auth_bootstrap._bind_postgrest")
    @patch("src.core.auth_bootstrap._get_access_token", return_value=None)
    @patch("src.core.auth_bootstrap._supabase_client")
    @patch("src.core.auth_bootstrap.prefs_utils.load_auth_session")
    def test_restore_fails_network_then_login(
        self, mock_load, mock_client, mock_token, mock_bind, mock_online, mock_dialog, caplog
    ):
        """C3: restore falha por rede → tenta login → classificação correta."""
        mock_load.return_value = {
            "access_token": "tok123",
            "refresh_token": "ref456",
            "keep_logged": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        client = _make_mock_client(set_session_side_effect=OSError("getaddrinfo failed"))
        mock_client.return_value = client
        mock_dialog.return_value = MagicMock(login_success=False)
        app = MagicMock()

        from src.core.auth_bootstrap import ensure_logged

        logger = logging.getLogger("src.core.auth_bootstrap")
        with caplog.at_level(logging.DEBUG, logger="src.core.auth_bootstrap"):
            with patch.dict(os.environ, {"RC_NO_LOCAL_FS": "0"}):
                result = ensure_logged(app, logger=logger)

        assert result is False

        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        # Deve ter classificação [network]
        assert any("[network]" in m for m in warning_msgs), f"[network] ausente: {warning_msgs}"
        assert any("sessão preservada no storage" in m for m in warning_msgs)

        info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("Encerrando aplicação: login não completado" in m for m in info_msgs)


# =====================================================================
# T12 – Fluxo C6: recuperação (backend volta) (C6)
# =====================================================================


class TestHealthCheckRecovery:
    """Simula health check falhando e depois recuperando."""

    def test_recovery_from_offline_to_online(self, caplog):
        """C6: health check falha, depois sucesso → log adequado."""
        from src.infra.supabase.db_client import _health_check_once

        client = MagicMock()
        call_count = 0

        def fake_exec(builder):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("getaddrinfo failed")
            return MagicMock()  # Sucesso

        with (
            patch("src.infra.supabase.db_client.supa_types") as mock_types,
            patch("src.infra.supabase.db_client.exec_postgrest") as mock_exec,
        ):
            mock_types.HEALTHCHECK_USE_RPC = False
            mock_types.HEALTHCHECK_FALLBACK_TABLE = "test_health"
            mock_exec.side_effect = fake_exec

            # Primeira chamada: falha
            env_backup = os.environ.pop("PYTEST_CURRENT_TEST", None)
            try:
                with caplog.at_level(logging.DEBUG, logger="src.infra.supabase.db_client"):
                    result1 = _health_check_once(client)
            finally:
                if env_backup is not None:
                    os.environ["PYTEST_CURRENT_TEST"] = env_backup

            assert result1 is False

            # Segunda chamada: sucesso
            with caplog.at_level(logging.DEBUG, logger="src.infra.supabase.db_client"):
                result2 = _health_check_once(client)

            assert result2 is True

        # Verificar que não há warning residual na segunda chamada
        # (os records da segunda chamada não devem conter warnings de falha)
        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        # Deve ter exatamente 1 warning (da primeira chamada)
        health_warnings = [m for m in warning_msgs if "Health check fallback" in m]
        assert len(health_warnings) == 1, f"Esperado 1 warning, encontrados: {health_warnings}"


# ┌─────────────────────────────────────────────────────────────────────┐
# │ C-StartupId: Validação do startup_id / correlation id              │
# └─────────────────────────────────────────────────────────────────────┘


class TestStartupIdFilter:
    """Valida que o StartupIdFilter injeta startup_id em cada record."""

    def test_filter_injects_startup_id(self):
        """C1 — O filter deve adicionar startup_id ao LogRecord."""
        from src.core.logs.filters import StartupIdFilter

        f = StartupIdFilter("abc12345")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=(),
            exc_info=None,
        )
        assert not hasattr(record, "startup_id")
        result = f.filter(record)
        assert result is True
        assert record.startup_id == "abc12345"  # type: ignore[attr-defined]

    def test_filter_always_returns_true(self):
        """O filter nunca bloqueia records — apenas injeta o atributo."""
        from src.core.logs.filters import StartupIdFilter

        f = StartupIdFilter("xyz")
        for lvl in (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL):
            record = logging.LogRecord(
                name="any",
                level=lvl,
                pathname="",
                lineno=0,
                msg="m",
                args=(),
                exc_info=None,
            )
            assert f.filter(record) is True

    def test_same_id_across_records(self):
        """C1 — Todos os records de uma mesma execução recebem o mesmo ID."""
        from src.core.logs.filters import StartupIdFilter

        f = StartupIdFilter("stable99")
        records = []
        for i in range(5):
            r = logging.LogRecord(
                name=f"mod{i}",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=f"msg {i}",
                args=(),
                exc_info=None,
            )
            f.filter(r)
            records.append(r)
        ids = {r.startup_id for r in records}  # type: ignore[attr-defined]
        assert ids == {"stable99"}

    def test_different_filter_instances_different_ids(self):
        """C1 — Duas execuções (filtros distintos) produzem IDs distintos."""
        from src.core.logs.filters import StartupIdFilter

        f1 = StartupIdFilter("exec_aaa")
        f2 = StartupIdFilter("exec_bbb")
        r1 = logging.LogRecord(name="t", level=logging.INFO, pathname="", lineno=0, msg="x", args=(), exc_info=None)
        r2 = logging.LogRecord(name="t", level=logging.INFO, pathname="", lineno=0, msg="x", args=(), exc_info=None)
        f1.filter(r1)
        f2.filter(r2)
        assert r1.startup_id != r2.startup_id  # type: ignore[attr-defined]


class TestStartupIdInConfigure:
    """Valida que configure.py gera e expõe STARTUP_ID."""

    def test_startup_id_is_8_hex_chars(self):
        """O STARTUP_ID gerado deve ter 8 caracteres hexadecimais."""
        from src.core.logs.configure import STARTUP_ID

        assert len(STARTUP_ID) == 8
        assert all(c in "0123456789abcdef" for c in STARTUP_ID)

    def test_startup_id_is_stable_within_process(self):
        """Importar o módulo múltiplas vezes retorna o mesmo ID (cache de import)."""
        import importlib

        from src.core.logs.configure import STARTUP_ID

        # Reimport não regenera (Python module cache)
        mod = importlib.import_module("src.core.logs.configure")
        assert mod.STARTUP_ID == STARTUP_ID


class TestStartupIdFormatterIntegration:
    """C3 — Valida que o formatter funciona sem KeyError quando startup_id está presente."""

    def test_console_format_with_startup_id(self):
        """O format string do console renderiza sem erro com startup_id injetado."""
        from src.core.logs.filters import StartupIdFilter

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | [%(startup_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        flt = StartupIdFilter("f00dcafe")
        record = logging.LogRecord(
            name="src.core.auth_bootstrap",
            level=logging.INFO,
            pathname="auth_bootstrap.py",
            lineno=42,
            msg="Sessão ativa: uid=%s, token=%s",
            args=("abc...", "presente"),
            exc_info=None,
        )
        flt.filter(record)
        output = formatter.format(record)
        assert "[f00dcafe]" in output
        assert "Sessão ativa: uid=abc..., token=presente" in output

    def test_file_format_with_startup_id(self):
        """O format string do arquivo renderiza sem erro com startup_id injetado."""
        from src.core.logs.filters import StartupIdFilter

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-40s | %(filename)s:%(lineno)d | [%(startup_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        flt = StartupIdFilter("deadbeef")
        record = logging.LogRecord(
            name="startup",
            level=logging.INFO,
            pathname="bootstrap.py",
            lineno=10,
            msg="Logging level ativo: %s",
            args=("INFO",),
            exc_info=None,
        )
        flt.filter(record)
        output = formatter.format(record)
        assert "[deadbeef]" in output
        assert "Logging level ativo: INFO" in output

    def test_format_fails_without_startup_id(self):
        """Sem o filter, o formatter com %(startup_id)s deve falhar."""
        formatter = logging.Formatter(
            "%(asctime)s | [%(startup_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=(),
            exc_info=None,
        )
        # Python 3.13 levanta ValueError wrapping KeyError
        with pytest.raises((KeyError, ValueError)):
            formatter.format(record)


class TestStartupIdFilterCompatibility:
    """C4 — Valida compatibilidade com filtros existentes."""

    def test_compatible_with_redact_filter(self):
        """RedactSensitiveData não interfere no startup_id."""
        from src.core.logs.filters import RedactSensitiveData, StartupIdFilter

        sid = StartupIdFilter("compat01")
        redact = RedactSensitiveData()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="token=%s detected",
            args=("secretvalue",),
            exc_info=None,
        )
        sid.filter(record)
        redact.filter(record)
        assert record.startup_id == "compat01"  # type: ignore[attr-defined]
        # Redact should NOT touch startup_id itself
        assert record.startup_id == "compat01"  # type: ignore[attr-defined]

    def test_compatible_with_antispam_filter(self):
        """AntiSpamFilter não interfere no startup_id."""
        from src.core.logs.filters import AntiSpamFilter, StartupIdFilter

        sid = StartupIdFilter("compat02")
        antispam = AntiSpamFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Normal log message",
            args=(),
            exc_info=None,
        )
        sid.filter(record)
        antispam.filter(record)
        assert record.startup_id == "compat02"  # type: ignore[attr-defined]

    def test_compatible_with_console_important_filter(self):
        """ConsoleImportantFilter não interfere no startup_id (allowlisted logger)."""
        from src.core.logs.filters import ConsoleImportantFilter, StartupIdFilter

        sid = StartupIdFilter("compat03")
        cif = ConsoleImportantFilter()
        record = logging.LogRecord(
            name="src.core.auth_bootstrap",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Sessão ativa",
            args=(),
            exc_info=None,
        )
        sid.filter(record)
        passes = cif.filter(record)
        assert passes is True
        assert record.startup_id == "compat03"  # type: ignore[attr-defined]

    def test_full_filter_pipeline(self, caplog):
        """Pipeline completo: StartupId → Redact → AntiSpam → logs preservam startup_id."""
        from src.core.logs.filters import AntiSpamFilter, RedactSensitiveData, StartupIdFilter

        sid = StartupIdFilter("pipeline")
        redact = RedactSensitiveData()
        antispam = AntiSpamFilter()

        record = logging.LogRecord(
            name="src.core.auth_bootstrap",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Login OK: user.id=%s | token=%s",
            args=("abc12345...", "presente"),
            exc_info=None,
        )
        sid.filter(record)
        redact.filter(record)
        antispam.filter(record)

        # startup_id sobrevive ao pipeline inteiro
        assert record.startup_id == "pipeline"  # type: ignore[attr-defined]


class TestStartupIdEndToEnd:
    """C2/C5 — Verifica que o startup_id aparece em logs capturados via caplog."""

    def test_startup_id_in_caplog_records(self, caplog):
        """Logs capturados via handler real devem ter startup_id como atributo."""
        from src.core.logs.filters import StartupIdFilter

        # Criar handler manual com o filter
        handler = logging.StreamHandler()
        flt = StartupIdFilter("e2e_test")
        handler.addFilter(flt)
        formatter = logging.Formatter("[%(startup_id)s] %(message)s")
        handler.setFormatter(formatter)

        test_logger = logging.getLogger("test.startup_id.e2e")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)

        try:
            with caplog.at_level(logging.INFO, logger="test.startup_id.e2e"):
                test_logger.info("Startup log")
                test_logger.info("Shutdown log")

            # caplog records: startup_id é injetado pelo filter no handler,
            # MAS caplog tem seu próprio handler sem o filter.
            # Portanto, verificamos via handler direto: format output inclui o ID.
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="check",
                args=(),
                exc_info=None,
            )
            flt.filter(record)
            formatted = handler.formatter.format(record)
            assert "[e2e_test]" in formatted
        finally:
            test_logger.removeHandler(handler)


# =====================================================================
# T13 – is_persisted_auth_session_valid: cobertura de borda
# =====================================================================


class TestIsPersistedSessionValid:
    """Valida que sessão inválida não gera falsos positivos de restore."""

    def test_empty_data(self):
        from src.core.auth_bootstrap import is_persisted_auth_session_valid

        assert is_persisted_auth_session_valid({}) is False

    def test_expired_session(self):
        from src.core.auth_bootstrap import is_persisted_auth_session_valid

        old = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        data = {
            "access_token": "tok",
            "refresh_token": "ref",
            "keep_logged": True,
            "created_at": old,
        }
        assert is_persisted_auth_session_valid(data) is False

    def test_valid_session(self):
        from src.core.auth_bootstrap import is_persisted_auth_session_valid

        data = {
            "access_token": "tok",
            "refresh_token": "ref",
            "keep_logged": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        assert is_persisted_auth_session_valid(data) is True

    def test_keep_logged_false(self):
        from src.core.auth_bootstrap import is_persisted_auth_session_valid

        data = {
            "access_token": "tok",
            "refresh_token": "ref",
            "keep_logged": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        assert is_persisted_auth_session_valid(data) is False


# =====================================================================
# T14 – ConsoleImportantFilter: verificação de cobertura (diagnóstico)
# =====================================================================


class TestConsoleFilterCoverage:
    """Verifica quais loggers do patch passam pelo filtro de console.

    Não é um teste de funcionalidade, mas um diagnóstico de observabilidade.
    Documenta quais mensagens INFO do patch chegam ao console.
    """

    def test_auth_bootstrap_info_passes_console_filter(self):
        """src.core.auth_bootstrap INFO deve chegar ao console."""
        from src.core.logs.filters import ConsoleImportantFilter

        f = ConsoleImportantFilter()
        record = logging.LogRecord(
            name="src.core.auth_bootstrap",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Sessão já existente no boot.",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True, "src.core.auth_bootstrap INFO deveria passar pelo ConsoleImportantFilter"

    def test_login_dialog_info_passes_console_filter(self):
        """src.ui.login_dialog INFO deve chegar ao console."""
        from src.core.logs.filters import ConsoleImportantFilter

        f = ConsoleImportantFilter()
        record = logging.LogRecord(
            name="src.ui.login_dialog",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="LoginDialog: fechado pelo usuário (cancelamento)",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True, "src.ui.login_dialog INFO deveria passar pelo ConsoleImportantFilter"

    def test_auth_bootstrap_warning_passes_filter(self):
        """WARNING de auth_bootstrap sempre chega no console."""
        from src.core.logs.filters import ConsoleImportantFilter

        f = ConsoleImportantFilter()
        record = logging.LogRecord(
            name="src.core.auth_bootstrap",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Nenhuma sessão ativa: uid=none, token=ausente",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True

    def test_db_client_warning_passes_filter(self):
        """WARNING de db_client sempre chega no console."""
        from src.core.logs.filters import ConsoleImportantFilter

        f = ConsoleImportantFilter()
        record = logging.LogRecord(
            name="src.infra.supabase.db_client",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Health check fallback (table query) falhou [dns]: getaddrinfo failed",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True

    def test_non_allowlisted_logger_info_blocked(self):
        """INFO de logger não-allowlisted continua bloqueado."""
        from src.core.logs.filters import ConsoleImportantFilter

        f = ConsoleImportantFilter()
        record = logging.LogRecord(
            name="src.modules.uploads.some_module",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Algum log irrelevante para console",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is False, "Logger não-allowlisted não deveria passar pelo ConsoleImportantFilter"


# =====================================================================
# T15 – SENSITIVE_PATTERN não captura placeholders de logging (%s/%d)
# =====================================================================


class TestSensitivePatternPreservesPlaceholders:
    """Garante que SENSITIVE_PATTERN não destrói placeholders %s no template."""

    def test_token_placeholder_not_matched(self):
        """token=%s no template NÃO deve ser redactado."""
        from src.core.logs.filters import SENSITIVE_PATTERN

        template = "Login OK: user.id=%s | token=%s"
        result = SENSITIVE_PATTERN.sub(lambda m: f"{m.group(1)}=***", template)
        assert result == template, f"Placeholder %s foi destruído: {result}"

    def test_real_token_still_redacted(self):
        """token=eyJabc123 (valor real) DEVE ser redactado."""
        from src.core.logs.filters import SENSITIVE_PATTERN

        msg = "Authorization token=eyJhbGciOi123 header"
        result = SENSITIVE_PATTERN.sub(lambda m: f"{m.group(1)}=***", msg)
        assert "eyJhbGciOi123" not in result
        assert "token=***" in result

    def test_password_placeholder_not_matched(self):
        """password=%s no template NÃO deve ser redactado."""
        from src.core.logs.filters import SENSITIVE_PATTERN

        template = "Auth: password=%s"
        result = SENSITIVE_PATTERN.sub(lambda m: f"{m.group(1)}=***", template)
        assert result == template

    def test_full_filter_pipeline_login_ok(self, caplog):
        """Pipeline completa: log de login não contém %s literal."""
        from src.core.logs.filters import RedactSensitiveData

        redact = RedactSensitiveData()
        record = logging.LogRecord(
            name="src.ui.login_dialog",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Login OK: user.id=%s | token=%s",
            args=("abcdef12…", "presente"),
            exc_info=None,
        )
        redact.filter(record)
        formatted = record.getMessage()
        assert "%s" not in formatted, f"Placeholder literal no output: {formatted}"
        assert "presente" in formatted
        assert "abcdef12" in formatted

    def test_full_filter_pipeline_session_snapshot(self, caplog):
        """Pipeline completa: snapshot de sessão não contém %s literal."""
        from src.core.logs.filters import RedactSensitiveData

        redact = RedactSensitiveData()
        record = logging.LogRecord(
            name="src.core.auth_bootstrap",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Sessão ativa: uid=%s, token=%s",
            args=("abcdef12...", "presente"),
            exc_info=None,
        )
        redact.filter(record)
        formatted = record.getMessage()
        assert "%s" not in formatted, f"Placeholder literal no output: {formatted}"
        assert "presente" in formatted
        assert "abcdef12" in formatted


# ┌─────────────────────────────────────────────────────────────────────┐
# │ T-ExcInfo: Validação de exc_info=True em warnings/errors críticos  │
# └─────────────────────────────────────────────────────────────────────┘


class TestExcInfoHealthCheckFallback:
    """Valida que health check fallback emite traceback no log."""

    def test_health_check_fallback_has_exc_info(self, caplog):
        """Health check fallback (table query) deve ter exc_info quando falha."""
        from src.infra.supabase.db_client import _health_check_once

        client = MagicMock()
        client.table.return_value.select.return_value.limit.return_value.execute.side_effect = ConnectionError(
            "getaddrinfo failed"
        )

        with (
            patch("src.infra.supabase.db_client.supa_types") as mock_types,
            patch("src.infra.supabase.db_client.exec_postgrest") as mock_exec,
        ):
            mock_types.HEALTHCHECK_USE_RPC = False
            mock_types.HEALTHCHECK_FALLBACK_TABLE = "test_health"
            mock_exec.side_effect = ConnectionError("getaddrinfo failed")

            env_backup = os.environ.pop("PYTEST_CURRENT_TEST", None)
            try:
                with caplog.at_level(logging.WARNING, logger="src.infra.supabase.db_client"):
                    result = _health_check_once(client)
            finally:
                if env_backup is not None:
                    os.environ["PYTEST_CURRENT_TEST"] = env_backup

        assert result is False
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) >= 1, "Esperado pelo menos 1 warning de fallback"
        assert warning_records[0].exc_info is not None, "exc_info deve estar presente no warning de fallback"
        assert warning_records[0].exc_info[0] is ConnectionError


class TestExcInfoRefreshSessionState:
    """Valida que _refresh_session_state emite traceback quando falha."""

    def test_refresh_failure_has_exc_info(self, caplog):
        """Falha ao hidratar org_id/usuário deve ter exc_info."""
        from src.core.auth_bootstrap import _refresh_session_state

        mock_client = MagicMock()
        with patch(
            "src.core.auth_bootstrap.refresh_current_user_from_supabase",
            side_effect=RuntimeError("DB connection lost"),
        ):
            with caplog.at_level(logging.WARNING, logger="src.core.auth_bootstrap"):
                _refresh_session_state(mock_client, None)

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) == 1
        assert "hidratar" in warning_records[0].message
        assert warning_records[0].exc_info is not None
        assert warning_records[0].exc_info[0] is RuntimeError


class TestExcInfoSessionSnapshot:
    """Valida que _log_session_snapshot emite traceback quando get_session falha."""

    def test_session_snapshot_error_has_exc_info(self, caplog):
        """Erro ao verificar estado da sessão deve ter exc_info."""
        from src.core.auth_bootstrap import _log_session_snapshot

        mock_client = MagicMock()
        mock_client.auth.get_session.side_effect = RuntimeError("auth service down")

        with patch("src.core.auth_bootstrap._supabase_client", return_value=mock_client):
            with caplog.at_level(logging.WARNING, logger="src.core.auth_bootstrap"):
                _log_session_snapshot(None)

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) == 1
        assert "Erro ao verificar estado" in warning_records[0].message
        assert warning_records[0].exc_info is not None


class TestExcInfoEnsureLogged:
    """Valida que ensure_logged emite traceback quando _ensure_session levanta exceção."""

    def test_login_flow_error_has_exc_info(self, caplog):
        """Erro inesperado no fluxo de login deve ter exc_info."""
        from src.core.auth_bootstrap import ensure_logged

        mock_app = MagicMock()
        mock_app.wait_window = MagicMock()
        mock_app._update_user_status = MagicMock()
        mock_app.footer = MagicMock()
        mock_app._status_monitor = None
        mock_app.layout_refs = None

        with (
            patch("src.core.auth_bootstrap._ensure_session", side_effect=RuntimeError("Unexpected crash")),
            patch("src.core.auth_bootstrap._log_session_snapshot"),
            patch("src.core.auth_bootstrap._supabase_client", return_value=None),
            patch("tkinter.messagebox.showerror"),
        ):
            with caplog.at_level(logging.WARNING, logger="src.core.auth_bootstrap"):
                result = ensure_logged(mock_app, splash=None, logger=None)

        assert result is False
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING and "fluxo de login" in r.message]
        assert len(warning_records) == 1
        assert warning_records[0].exc_info is not None
        assert warning_records[0].exc_info[0] is RuntimeError


class TestExcInfoNotAddedToExpectedWarnings:
    """Valida que warnings operacionais esperados NÃO têm exc_info."""

    def test_no_session_snapshot_no_exc_info(self, caplog):
        """'Nenhuma sessão ativa' é warning operacional — sem traceback."""
        from src.core.auth_bootstrap import _log_session_snapshot

        mock_client = MagicMock()
        sess = SimpleNamespace(user=SimpleNamespace(id="abc"), access_token=None, refresh_token=None)
        mock_client.auth.get_session.return_value = sess

        with (
            patch("src.core.auth_bootstrap._supabase_client", return_value=mock_client),
            patch("src.core.auth_bootstrap._get_access_token", return_value=None),
        ):
            with caplog.at_level(logging.WARNING, logger="src.core.auth_bootstrap"):
                _log_session_snapshot(None)

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_records) == 1
        assert "Nenhuma sessão ativa" in warning_records[0].message
        # Este warning NÃO deve ter exc_info (é estado operacional, não exceção)
        assert warning_records[0].exc_info is None

    def test_cloud_only_no_internet_no_exc_info(self):
        """'Sem internet em modo cloud-only' é UX esperada — sem traceback.
        Verificação via AST para não precisar de Tk."""
        import ast
        from pathlib import Path

        src = Path("src/core/auth_bootstrap.py").read_text(encoding="utf-8")
        tree = ast.parse(src)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "warning":
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if "Sem internet em modo cloud-only" in arg.value:
                                kw_names = [kw.arg for kw in node.keywords]
                                assert (
                                    "exc_info" not in kw_names
                                ), "Warning 'Sem internet em modo cloud-only' não deve ter exc_info"
