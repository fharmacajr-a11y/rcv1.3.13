# -*- coding: utf-8 -*-
"""Testes de proteção para touch_ultima_alteracao e o fluxo de refresh do browser.

Garante os invariantes descobertos na rodada de debug funcional dirigido:
  1. touch_ultima_alteracao detecta 0 linhas afetadas e emite WARNING.
  2. touch_ultima_alteracao detecta e loga a exceção da tentativa primária (INFO).
  3. touch_ultima_alteracao loga INFO na tentativa bem-sucedida com row count.
  4. _count_updated trata corretamente resp.count, resp.data e resposta vazia.
  5. _editor_actions_mixin: _on_mutation_cb loga INFO (log rastreável em runtime).
  6. _editor_actions_mixin: _on_browser_close loga estado de _files_mutated.
  7. _editor_actions_mixin: _notify_main loga quando editor já foi destruído.
  8. _editor_actions_mixin: _bg loga início e conclusão do touch.
"""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


_SRC = Path(__file__).resolve().parent.parent / "src"
_EDITOR_ACTIONS = _SRC / "modules" / "clientes" / "ui" / "views" / "_editor_actions_mixin.py"
_SERVICE = _SRC / "modules" / "clientes" / "core" / "service.py"


def _src(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ===========================================================================
# Helpers
# ===========================================================================


def _make_resp(count=None, data=None):
    """Cria resposta mock do PostgREST."""
    return SimpleNamespace(count=count, data=data)


# ===========================================================================
# 1. _count_updated
# ===========================================================================


class TestCountUpdated:
    """_count_updated extrai corretamente a contagem de linhas."""

    def _fn(self):
        from src.modules.clientes.core.service import _count_updated

        return _count_updated

    def test_uses_count_when_not_none(self):
        fn = self._fn()
        assert fn(_make_resp(count=3)) == 3

    def test_count_zero_explicit(self):
        fn = self._fn()
        assert fn(_make_resp(count=0)) == 0

    def test_falls_back_to_data_len_when_count_is_none(self):
        fn = self._fn()
        assert fn(_make_resp(count=None, data=[{"id": 1}, {"id": 2}])) == 2

    def test_empty_data_returns_zero(self):
        fn = self._fn()
        assert fn(_make_resp(count=None, data=[])) == 0

    def test_none_data_returns_zero(self):
        fn = self._fn()
        assert fn(_make_resp(count=None, data=None)) == 0

    def test_no_attributes_returns_zero(self):
        fn = self._fn()
        assert fn(object()) == 0


# ===========================================================================
# 2. touch_ultima_alteracao — 0 linhas afetadas gera WARNING
# ===========================================================================


class TestTouchUltimaAlteracaoZeroRows:
    """touch_ultima_alteracao DEVE emitir WARNING quando 0 linhas forem afetadas."""

    def _patch_exec(self, data=None, count=None):
        resp = _make_resp(count=count, data=data or [])
        return patch("src.modules.clientes.core.service.exec_postgrest", return_value=resp)

    def test_zero_rows_primary_logs_warning(self, caplog):
        with self._patch_exec(data=[]):
            with caplog.at_level(logging.WARNING, logger="src.modules.clientes.core.service"):
                from src.modules.clientes.core.service import touch_ultima_alteracao

                touch_ultima_alteracao(99)
        assert any(
            "0 linhas" in r.message for r in caplog.records
        ), "touch_ultima_alteracao deve emitir WARNING quando 0 linhas forem afetadas."

    def test_one_row_primary_no_warning(self, caplog):
        with self._patch_exec(data=[{"id": 99}]):
            with caplog.at_level(logging.WARNING, logger="src.modules.clientes.core.service"):
                from src.modules.clientes.core.service import touch_ultima_alteracao

                touch_ultima_alteracao(99)
        warnings = [
            r for r in caplog.records if r.levelno == logging.WARNING and "touch_ultima_alteracao" in r.name + r.message
        ]
        assert not warnings, f"Não deve haver WARNING quando 1 linha for afetada, mas houve: {warnings}"


# ===========================================================================
# 3. touch_ultima_alteracao — exceção primária cai para fallback com log DEBUG
# ===========================================================================


class TestTouchUltimaAlteracaoFallback:
    """Exceção na tentativa primária deve aparecer em DEBUG e acionar fallback."""

    def test_primary_exception_triggers_fallback(self, caplog):
        fallback_resp = _make_resp(data=[{"id": 1}])
        call_count = [0]

        def mock_exec(request):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("coluna ultima_por inexistente")
            return fallback_resp

        with patch("src.modules.clientes.core.service.exec_postgrest", side_effect=mock_exec):
            with caplog.at_level(logging.INFO, logger="src.modules.clientes.core.service"):
                import src.modules.clientes.core.service as svc

                svc.touch_ultima_alteracao(7)

        assert call_count[0] == 2, "exec_postgrest deve ser chamado 2x (primária + fallback)"
        info_msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any(
            "tentando fallback" in m or "falhou" in m for m in info_msgs
        ), "Deve haver log INFO indicando que o fallback foi acionado por exceção."

    def test_both_fail_logs_warning(self, caplog):
        with patch(
            "src.modules.clientes.core.service.exec_postgrest",
            side_effect=RuntimeError("rede instável"),
        ):
            with caplog.at_level(logging.WARNING, logger="src.modules.clientes.core.service"):
                from src.modules.clientes.core.service import touch_ultima_alteracao

                touch_ultima_alteracao(5)

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings, "Deve emitir WARNING quando tanto primária quanto fallback falharem."


# ===========================================================================
# 4. Inspeção de source: _count_updated existe e é usada em touch_ultima_alteracao
# ===========================================================================


class TestServiceSourceInvariants:
    """Invariantes verificados por inspeção de fonte em service.py."""

    def test_count_updated_helper_defined(self):
        source = _src(_SERVICE)
        assert "def _count_updated(" in source, (
            "service.py: _count_updated não está definida. " "A verificação de 0 linhas afetadas não está presente."
        )

    def test_touch_uses_count_updated(self):
        source = _src(_SERVICE)
        touch_start = source.find("def touch_ultima_alteracao(")
        assert touch_start >= 0
        # Pegar até o final da função (próxima def de mesmo nível)
        next_def = source.find("\ndef ", touch_start + 1)
        snippet = source[touch_start:next_def] if next_def > 0 else source[touch_start:]
        assert "_count_updated(" in snippet, (
            "touch_ultima_alteracao não usa _count_updated. "
            "Falhas silenciosas de UPDATE (0 linhas) não serão detectadas."
        )

    def test_outer_except_has_debug_log(self):
        source = _src(_SERVICE)
        touch_start = source.find("def touch_ultima_alteracao(")
        assert touch_start >= 0
        next_def = source.find("\ndef ", touch_start + 1)
        snippet = source[touch_start:next_def] if next_def > 0 else source[touch_start:]
        # O primeiro except (antes do fallback) deve ter log.info (visível em INFO level)
        first_except = snippet.find("except Exception")
        assert first_except >= 0
        # Verificar que existe log.info ANTES do próximo try: após o except
        between = snippet[first_except : first_except + 300]
        assert "log.info" in between, (
            "service.py: o except primário de touch_ultima_alteracao não tem log.info. "
            "Exceções na tentativa primária são silenciosas em runtime (INFO level)."
        )


# ===========================================================================
# 5. Inspeção de source: logs rastreáveis no mixin
# ===========================================================================


class TestEditorActionsMixinTraceLogs:
    """Invariantes de logs rastreáveis em _editor_actions_mixin.py."""

    def test_on_mutation_cb_has_debug_log(self):
        source = _src(_EDITOR_ACTIONS)
        # _on_mutation_cb deve ter log.info (visível em runtime INFO level)
        start = source.find("def _on_mutation_cb(")
        assert start >= 0, "_editor_actions_mixin.py: _on_mutation_cb não encontrada"
        snippet = source[start : start + 200]
        assert "log.info" in snippet, (
            "_editor_actions_mixin.py: _on_mutation_cb não tem log.info. "
            "Não é possível rastrear se o callback foi acionado no smoke manual."
        )

    def test_on_browser_close_logs_files_mutated(self):
        source = _src(_EDITOR_ACTIONS)
        start = source.find("def _on_browser_close(")
        assert start >= 0
        snippet = source[start : start + 400]
        assert "log.info" in snippet, (
            "_editor_actions_mixin.py: _on_browser_close não tem log.info. "
            "Não é possível rastrear o estado de _files_mutated ao fechar o browser."
        )
        assert (
            "_files_mutated" in snippet
        ), "_editor_actions_mixin.py: _on_browser_close não referencia _files_mutated no log."

    def test_bg_logs_touch_start_and_end(self):
        source = _src(_EDITOR_ACTIONS)
        start = source.find("def _bg() -> None:")
        assert start >= 0
        notify_start = source.find("def _notify_main() -> None:", start)
        assert notify_start >= 0
        bg_body = source[start:notify_start]
        assert bg_body.count("log.info") >= 2, (
            "_editor_actions_mixin.py: _bg deve ter ao menos 2 log.info "
            "(início e conclusão do touch) visíveis em runtime."
        )

    def test_notify_main_logs_when_editor_destroyed(self):
        source = _src(_EDITOR_ACTIONS)
        start = source.find("def _notify_main() -> None:")
        assert start >= 0
        snippet = source[start : start + 400]
        assert "log.info" in snippet, (
            "_editor_actions_mixin.py: _notify_main não tem log.info. "
            "Não é possível rastrear se o editor foi destruído antes do refresh."
        )
