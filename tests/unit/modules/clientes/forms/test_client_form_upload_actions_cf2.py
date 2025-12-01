# -*- coding: utf-8 -*-
"""
Testes para o módulo client_form_upload_actions.py - lógica headless de upload.

Este módulo testa a lógica de upload extraída do client_form.py,
sem depender de Tkinter ou outras bibliotecas de UI.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

from src.modules.clientes.forms import client_form_upload_actions as upload_actions


# -----------------------------------------------------------------------------
# Fixtures e Helpers
# -----------------------------------------------------------------------------


class FakeUploadExecutor:
    """Implementação fake de UploadExecutor para testes."""

    def __init__(self) -> None:
        self.executions: list[dict[str, Any]] = []
        self.should_fail: bool = False
        self.error_to_raise: Exception | None = None

    def execute_upload(
        self,
        host: Any,
        row: tuple[Any, ...] | None,
        ents: dict[str, Any],
        arquivos_selecionados: list | None,
        win: Any,
        **kwargs: Any,
    ) -> Any:
        """Registra a execução do upload."""
        if self.should_fail and self.error_to_raise:
            raise self.error_to_raise

        self.executions.append(
            {
                "host": host,
                "row": row,
                "ents": ents,
                "arquivos_selecionados": arquivos_selecionados,
                "win": win,
                "kwargs": kwargs,
            }
        )
        return "upload_result"


class FakeClientPersistence:
    """Implementação fake de ClientPersistence para testes."""

    def __init__(self, success: bool = True, saved_id: int | None = None) -> None:
        self.persist_calls: list[int | None] = []
        self.success = success
        self.saved_id = saved_id

    def persist_if_new(self, client_id: int | None) -> tuple[bool, int | None]:
        """Registra a chamada e retorna resultado configurado."""
        self.persist_calls.append(client_id)

        # Se já tem ID, não precisa salvar
        if client_id is not None:
            return (True, client_id)

        # Cliente novo
        return (self.success, self.saved_id)


def make_upload_ctx(**overrides: Any) -> upload_actions.UploadContext:
    """Helper para criar contexto de upload com valores padrão."""
    base = upload_actions.UploadContext(
        client_id=None,
        is_new=True,
        row=None,
        ents={},
    )
    for key, val in overrides.items():
        setattr(base, key, val)
    return base


def make_upload_deps(
    executor: upload_actions.UploadExecutor | None = None,
    persistence: upload_actions.ClientPersistence | None = None,
    host: Any = None,
) -> upload_actions.UploadDeps:
    """Helper para criar dependências de upload."""
    return upload_actions.UploadDeps(
        executor=executor or FakeUploadExecutor(),
        persistence=persistence or FakeClientPersistence(),
        host=host or Mock(),
    )


# -----------------------------------------------------------------------------
# Testes: prepare_upload_context
# -----------------------------------------------------------------------------


def test_prepare_upload_context_new_client() -> None:
    """Testa preparação de contexto para cliente novo."""
    ctx = upload_actions.prepare_upload_context(
        client_id=None,
        row=None,
        ents={"Razão Social": "Empresa X"},
        win=Mock(),
    )

    assert ctx.client_id is None
    assert ctx.is_new is True
    assert ctx.row is None
    assert ctx.ents == {"Razão Social": "Empresa X"}
    assert ctx.skip_duplicate_prompt is True
    assert ctx.abort is False


def test_prepare_upload_context_existing_client() -> None:
    """Testa preparação de contexto para cliente existente."""
    ctx = upload_actions.prepare_upload_context(
        client_id=42,
        row=(42, "Empresa Y", "12345678901234"),
        ents={"Razão Social": "Empresa Y"},
        win=Mock(),
    )

    assert ctx.client_id == 42
    assert ctx.is_new is False
    assert ctx.row == (42, "Empresa Y", "12345678901234")


def test_prepare_upload_context_with_files() -> None:
    """Testa preparação de contexto com arquivos pré-selecionados."""
    files = [("path1", "doc1.pdf"), ("path2", "doc2.pdf")]

    ctx = upload_actions.prepare_upload_context(
        client_id=100,
        row=(100,),
        ents={},
        win=Mock(),
        arquivos_selecionados=files,
    )

    assert ctx.arquivos_selecionados == files


# -----------------------------------------------------------------------------
# Testes: execute_salvar_e_enviar - Cliente Existente
# -----------------------------------------------------------------------------


def test_execute_salvar_e_enviar_existing_client() -> None:
    """Testa upload para cliente existente (não precisa salvar)."""
    ctx = make_upload_ctx(client_id=200, is_new=False, row=(200,))
    executor = FakeUploadExecutor()
    persistence = FakeClientPersistence()
    deps = make_upload_deps(executor=executor, persistence=persistence)

    result_ctx = upload_actions.execute_salvar_e_enviar(ctx, deps)

    # Não deve ter tentado persistir (cliente já existe)
    assert len(persistence.persist_calls) == 0

    # Deve ter executado upload
    assert len(executor.executions) == 1
    assert executor.executions[0]["row"] == (200,)

    # Contexto não deve ter abortado
    assert result_ctx.abort is False
    assert result_ctx.client_id == 200


# -----------------------------------------------------------------------------
# Testes: execute_salvar_e_enviar - Cliente Novo
# -----------------------------------------------------------------------------


def test_execute_salvar_e_enviar_new_client_success() -> None:
    """Testa upload para cliente novo (salva antes)."""
    ctx = make_upload_ctx(client_id=None, is_new=True, row=None)
    executor = FakeUploadExecutor()
    persistence = FakeClientPersistence(success=True, saved_id=999)
    deps = make_upload_deps(executor=executor, persistence=persistence)

    result_ctx = upload_actions.execute_salvar_e_enviar(ctx, deps)

    # Deve ter tentado persistir
    assert len(persistence.persist_calls) == 1
    assert persistence.persist_calls[0] is None

    # Contexto deve ter sido atualizado com ID salvo
    assert result_ctx.client_id == 999
    assert result_ctx.is_new is False
    assert result_ctx.newly_created is True

    # Row deve ter sido atualizada
    assert result_ctx.row == (999,)

    # Upload deve ter sido executado
    assert len(executor.executions) == 1
    assert executor.executions[0]["row"] == (999,)

    # Não deve ter abortado
    assert result_ctx.abort is False


def test_execute_salvar_e_enviar_new_client_persist_fails() -> None:
    """Testa que falha ao salvar cliente novo aborta o upload."""
    ctx = make_upload_ctx(client_id=None, is_new=True)
    executor = FakeUploadExecutor()
    persistence = FakeClientPersistence(success=False, saved_id=None)
    deps = make_upload_deps(executor=executor, persistence=persistence)

    result_ctx = upload_actions.execute_salvar_e_enviar(ctx, deps)

    # Deve ter tentado persistir
    assert len(persistence.persist_calls) == 1

    # Deve ter abortado
    assert result_ctx.abort is True
    assert result_ctx.error_message is not None
    assert "salvar o cliente" in result_ctx.error_message.lower()

    # Upload NÃO deve ter sido executado
    assert len(executor.executions) == 0


# -----------------------------------------------------------------------------
# Testes: execute_salvar_e_enviar - Flags no Host
# -----------------------------------------------------------------------------


def test_execute_salvar_e_enviar_sets_host_flags_for_new_client() -> None:
    """Testa que flags são configuradas no host para cliente novo."""
    ctx = make_upload_ctx(client_id=None, is_new=True)
    executor = FakeUploadExecutor()
    persistence = FakeClientPersistence(success=True, saved_id=777)

    # Mock host com atributos que devem ser setados
    mock_host = Mock()
    mock_host._force_client_id_for_upload = None
    mock_host._upload_force_is_new = False

    deps = make_upload_deps(executor=executor, persistence=persistence, host=mock_host)

    result_ctx = upload_actions.execute_salvar_e_enviar(ctx, deps)

    # Verifica que flags foram setadas
    assert mock_host._force_client_id_for_upload == 777
    assert mock_host._upload_force_is_new is True
    assert result_ctx.abort is False


def test_execute_salvar_e_enviar_sets_host_flags_for_existing_client() -> None:
    """Testa que flags são configuradas no host para cliente existente."""
    ctx = make_upload_ctx(client_id=888, is_new=False)
    executor = FakeUploadExecutor()
    persistence = FakeClientPersistence()

    mock_host = Mock()
    mock_host._force_client_id_for_upload = None

    deps = make_upload_deps(executor=executor, persistence=persistence, host=mock_host)

    result_ctx = upload_actions.execute_salvar_e_enviar(ctx, deps)

    # Verifica que flag foi setada
    assert mock_host._force_client_id_for_upload == 888
    # Para cliente existente, _upload_force_is_new não deve ser True
    # (Mock cria atributo automaticamente, mas não deve ser setado como True)
    if hasattr(mock_host, "_upload_force_is_new"):
        # Se foi setado, deve ser False (mas no código atual só seta para newly_created)
        # Como não é newly_created, esperamos que não seja True
        assert mock_host._upload_force_is_new is not True
    assert result_ctx.abort is False


def test_execute_salvar_e_enviar_handles_missing_host_attributes() -> None:
    """Testa que não falha se host não tiver os atributos esperados."""
    ctx = make_upload_ctx(client_id=555, is_new=False)
    executor = FakeUploadExecutor()
    persistence = FakeClientPersistence()

    # Host sem atributos especiais
    mock_host = Mock(spec=[])  # Sem atributos

    deps = make_upload_deps(executor=executor, persistence=persistence, host=mock_host)

    # Não deve falhar mesmo sem os atributos
    result_ctx = upload_actions.execute_salvar_e_enviar(ctx, deps)

    assert result_ctx.abort is False
    assert len(executor.executions) == 1


# -----------------------------------------------------------------------------
# Testes: execute_salvar_e_enviar - Tratamento de Erros
# -----------------------------------------------------------------------------


def test_execute_salvar_e_enviar_handles_upload_error() -> None:
    """Testa que erros durante upload são capturados."""
    ctx = make_upload_ctx(client_id=123, is_new=False)

    executor = FakeUploadExecutor()
    executor.should_fail = True
    executor.error_to_raise = RuntimeError("Falha no upload")

    persistence = FakeClientPersistence()
    deps = make_upload_deps(executor=executor, persistence=persistence)

    result_ctx = upload_actions.execute_salvar_e_enviar(ctx, deps)

    # Deve ter abortado com erro
    assert result_ctx.abort is True
    assert result_ctx.error_message is not None
    assert "Falha no upload" in result_ctx.error_message


# -----------------------------------------------------------------------------
# Testes: Integração - Fluxo Completo
# -----------------------------------------------------------------------------


def test_full_workflow_new_client_with_upload() -> None:
    """Testa fluxo completo: prepare → execute para cliente novo."""
    # 1. Preparar contexto
    ctx = upload_actions.prepare_upload_context(
        client_id=None,
        row=None,
        ents={"Razão Social": "Nova Empresa", "CNPJ": "12345678901234"},
        win=Mock(),
    )

    assert ctx.is_new is True

    # 2. Executar salvar e enviar
    executor = FakeUploadExecutor()
    persistence = FakeClientPersistence(success=True, saved_id=1001)
    deps = make_upload_deps(executor=executor, persistence=persistence)

    result_ctx = upload_actions.execute_salvar_e_enviar(ctx, deps)

    # 3. Verificar resultado
    assert result_ctx.abort is False
    assert result_ctx.client_id == 1001
    assert result_ctx.newly_created is True
    assert len(executor.executions) == 1
    assert executor.executions[0]["row"] == (1001,)


def test_full_workflow_existing_client_with_upload() -> None:
    """Testa fluxo completo: prepare → execute para cliente existente."""
    # 1. Preparar contexto
    ctx = upload_actions.prepare_upload_context(
        client_id=2002,
        row=(2002, "Empresa Existente"),
        ents={"Razão Social": "Empresa Existente"},
        win=Mock(),
    )

    assert ctx.is_new is False

    # 2. Executar upload (sem salvar)
    executor = FakeUploadExecutor()
    persistence = FakeClientPersistence()
    deps = make_upload_deps(executor=executor, persistence=persistence)

    result_ctx = upload_actions.execute_salvar_e_enviar(ctx, deps)

    # 3. Verificar resultado
    assert result_ctx.abort is False
    assert result_ctx.client_id == 2002
    assert result_ctx.newly_created is False
    assert len(persistence.persist_calls) == 0  # Não chamou persist
    assert len(executor.executions) == 1
