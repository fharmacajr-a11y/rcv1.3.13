# -*- coding: utf-8 -*-
"""Testes para src/modules/auditoria/application/controller.py - Fase 01.

Foco em cobertura do AuditoriaApplication (application layer/facade).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.modules.auditoria.application.controller import AuditoriaApplication, AuditoriaApplicationConfig
from src.modules.auditoria.archives import AuditoriaArchivePlan
from src.modules.auditoria.service import (
    AuditoriaServiceError,
    AuditoriaUploadContext,
    AuditoriaUploadResult,
)
from src.modules.auditoria.viewmodel import AuditoriaViewModel


@pytest.fixture
def mock_service(monkeypatch):
    """Mock do módulo auditoria_service."""
    from src.modules.auditoria import service as auditoria_service

    mock = MagicMock()
    # Copiar o módulo real para o mock
    for attr in dir(auditoria_service):
        if not attr.startswith("_"):
            setattr(mock, attr, MagicMock())

    # Configurar retornos padrão
    mock.is_online.return_value = True
    mock.get_supabase_client.return_value = MagicMock()
    mock.get_clients_bucket.return_value = "clients-bucket"
    mock.get_current_org_id.return_value = "org-123"
    mock.fetch_clients.return_value = []
    mock.fetch_auditorias.return_value = []

    return mock


@pytest.fixture
def app(mock_service, monkeypatch):
    """Instância de AuditoriaApplication com service mockado."""
    # Substituir o service no módulo controller
    import src.modules.auditoria.application.controller as controller_module

    monkeypatch.setattr(controller_module, "auditoria_service", mock_service)

    return AuditoriaApplication()


# ==================== Testes de Inicialização ====================


def test_auditoria_application_init_default_config(mock_service, monkeypatch):
    """Testa inicialização com config padrão."""
    import src.modules.auditoria.application.controller as controller_module

    monkeypatch.setattr(controller_module, "auditoria_service", mock_service)

    app = AuditoriaApplication()

    assert app.viewmodel is not None
    assert isinstance(app.viewmodel, AuditoriaViewModel)


def test_auditoria_application_init_custom_viewmodel(mock_service, monkeypatch):
    """Testa inicialização com viewmodel customizado."""
    import src.modules.auditoria.application.controller as controller_module

    monkeypatch.setattr(controller_module, "auditoria_service", mock_service)

    custom_vm = AuditoriaViewModel()
    config = AuditoriaApplicationConfig(viewmodel=custom_vm)
    app = AuditoriaApplication(config)

    assert app.viewmodel is custom_vm


def test_auditoria_application_init_none_config(mock_service, monkeypatch):
    """Testa inicialização com config=None."""
    import src.modules.auditoria.application.controller as controller_module

    monkeypatch.setattr(controller_module, "auditoria_service", mock_service)

    app = AuditoriaApplication(config=None)

    assert app.viewmodel is not None


# ==================== Testes de ViewModel Helpers ====================


def test_viewmodel_property(app):
    """Testa acesso à propriedade viewmodel."""
    vm = app.viewmodel
    assert isinstance(vm, AuditoriaViewModel)


def test_refresh_clientes(app, mock_service):
    """Testa refresh_clientes delega para viewmodel."""
    mock_service.fetch_clients.return_value = [{"id": 1, "name": "Client A"}]

    app.refresh_clientes()

    # Verificar que fetch_clients foi usado como fetcher
    mock_service.fetch_clients.assert_called()


def test_refresh_auditorias(app, mock_service):
    """Testa refresh_auditorias retorna lista de AuditoriaRow."""
    # Não precisamos mockar o retorno completo, apenas verificar que chama o service
    app.refresh_auditorias()

    # Deve chamar o service fetch_auditorias
    mock_service.fetch_auditorias.assert_called()


# ==================== Testes de Connectivity Helpers ====================


def test_is_online_returns_true(app, mock_service):
    """Testa is_online quando serviço está online."""
    mock_service.is_online.return_value = True

    assert app.is_online() is True
    mock_service.is_online.assert_called_once()


def test_is_online_returns_false(app, mock_service):
    """Testa is_online quando serviço está offline."""
    mock_service.is_online.return_value = False

    assert app.is_online() is False


def test_ensure_storage_ready(app, mock_service):
    """Testa ensure_storage_ready delega para service."""
    app.ensure_storage_ready()

    mock_service.ensure_storage_ready.assert_called_once()


def test_get_supabase_client_returns_client(app, mock_service):
    """Testa get_supabase_client retorna cliente."""
    mock_client = MagicMock()
    mock_service.get_supabase_client.return_value = mock_client

    result = app.get_supabase_client()

    assert result is mock_client
    mock_service.get_supabase_client.assert_called_once()


def test_get_supabase_client_returns_none(app, mock_service):
    """Testa get_supabase_client quando não há cliente."""
    mock_service.get_supabase_client.return_value = None

    result = app.get_supabase_client()

    assert result is None


# ==================== Testes de Data Operations ====================


def test_start_auditoria(app, mock_service):
    """Testa start_auditoria delega para service."""
    mock_service.start_auditoria.return_value = {"id": "123", "status": "pendente"}

    result = app.start_auditoria(42, status="pendente")

    assert result == {"id": "123", "status": "pendente"}
    mock_service.start_auditoria.assert_called_once_with(42, status="pendente")


def test_update_auditoria_status(app, mock_service):
    """Testa update_auditoria_status delega para service."""
    mock_service.update_auditoria_status.return_value = {"id": "123", "status": "completo"}

    result = app.update_auditoria_status("123", "completo")

    assert result == {"id": "123", "status": "completo"}
    mock_service.update_auditoria_status.assert_called_once_with("123", "completo")


def test_delete_auditorias(app, mock_service):
    """Testa delete_auditorias delega para service."""
    app.delete_auditorias(["1", "2", "3"])

    mock_service.delete_auditorias.assert_called_once_with(["1", "2", "3"])


# ==================== Testes de Storage Helpers ====================


def test_get_current_org_id_default(app, mock_service):
    """Testa get_current_org_id sem force_refresh."""
    mock_service.get_current_org_id.return_value = "org-456"

    result = app.get_current_org_id()

    assert result == "org-456"
    mock_service.get_current_org_id.assert_called_once_with(force_refresh=False)


def test_get_current_org_id_force_refresh(app, mock_service):
    """Testa get_current_org_id com force_refresh=True."""
    mock_service.get_current_org_id.return_value = "org-789"

    result = app.get_current_org_id(force_refresh=True)

    assert result == "org-789"
    mock_service.get_current_org_id.assert_called_once_with(force_refresh=True)


def test_get_storage_context(app, mock_service):
    """Testa get_storage_context delega para service."""
    mock_context = MagicMock()
    mock_service.get_storage_context.return_value = mock_context

    result = app.get_storage_context(42, org_id="org-123")

    assert result is mock_context
    mock_service.get_storage_context.assert_called_once_with(42, org_id="org-123")


def test_get_storage_context_no_org_id(app, mock_service):
    """Testa get_storage_context sem org_id."""
    mock_context = MagicMock()
    mock_service.get_storage_context.return_value = mock_context

    app.get_storage_context(42)

    mock_service.get_storage_context.assert_called_once_with(42, org_id=None)


def test_ensure_auditoria_folder(app, mock_service):
    """Testa ensure_auditoria_folder delega para service."""
    app.ensure_auditoria_folder(42, org_id="org-123")

    mock_service.ensure_auditoria_folder.assert_called_once_with(42, org_id="org-123")


def test_ensure_auditoria_folder_no_org_id(app, mock_service):
    """Testa ensure_auditoria_folder sem org_id."""
    app.ensure_auditoria_folder(42)

    mock_service.ensure_auditoria_folder.assert_called_once_with(42, org_id=None)


def test_remove_storage_objects(app, mock_service):
    """Testa remove_storage_objects delega para service."""
    app.remove_storage_objects("bucket", ["path1", "path2"])

    mock_service.remove_storage_objects.assert_called_once_with("bucket", ["path1", "path2"])


def test_get_clients_bucket(app, mock_service):
    """Testa get_clients_bucket retorna bucket."""
    mock_service.get_clients_bucket.return_value = "my-bucket"

    result = app.get_clients_bucket()

    assert result == "my-bucket"
    mock_service.get_clients_bucket.assert_called_once()


# ==================== Testes de delete_auditoria_folder ====================


def test_delete_auditoria_folder_offline_raises_error(app, mock_service):
    """Testa delete_auditoria_folder lança erro quando offline."""
    mock_service.is_online.return_value = False

    with pytest.raises(AuditoriaServiceError, match="Supabase client is not available"):
        app.delete_auditoria_folder("bucket", "prefix")


def test_delete_auditoria_folder_empty_keys_returns_zero(app, mock_service, monkeypatch):
    """Testa delete_auditoria_folder retorna 0 quando não há chaves."""
    mock_service.is_online.return_value = True
    monkeypatch.setattr(app, "_collect_storage_keys", lambda b, p: [])

    result = app.delete_auditoria_folder("bucket", "prefix")

    assert result == 0
    mock_service.remove_storage_objects.assert_not_called()


def test_delete_auditoria_folder_deletes_keys_in_batches(app, mock_service, monkeypatch):
    """Testa delete_auditoria_folder deleta chaves em batches."""
    mock_service.is_online.return_value = True

    # Simular 2500 chaves (vai precisar de 3 batches de 1000)
    keys = [f"key-{i}" for i in range(2500)]
    monkeypatch.setattr(app, "_collect_storage_keys", lambda b, p: keys)

    result = app.delete_auditoria_folder("bucket", "prefix")

    assert result == 2500
    # Verificar que remove_storage_objects foi chamado 3 vezes
    assert mock_service.remove_storage_objects.call_count == 3
    # Verificar os tamanhos dos batches
    calls = mock_service.remove_storage_objects.call_args_list
    assert len(calls[0][0][1]) == 1000  # Primeiro batch
    assert len(calls[1][0][1]) == 1000  # Segundo batch
    assert len(calls[2][0][1]) == 500  # Terceiro batch


def test_delete_auditoria_folder_single_batch(app, mock_service, monkeypatch):
    """Testa delete_auditoria_folder com menos de 1000 chaves."""
    mock_service.is_online.return_value = True

    keys = [f"key-{i}" for i in range(500)]
    monkeypatch.setattr(app, "_collect_storage_keys", lambda b, p: keys)

    result = app.delete_auditoria_folder("bucket", "prefix")

    assert result == 500
    mock_service.remove_storage_objects.assert_called_once()


# ==================== Testes de make_delete_folder_handler ====================


def test_make_delete_folder_handler_creates_handler(app):
    """Testa make_delete_folder_handler cria função handler."""
    handler = app.make_delete_folder_handler("allowed/prefix")

    assert callable(handler)


def test_make_delete_folder_handler_allows_prefix(app, mock_service, monkeypatch):
    """Testa handler permite delete dentro do prefixo permitido."""
    mock_service.is_online.return_value = True
    monkeypatch.setattr(app, "_collect_storage_keys", lambda b, p: ["key1"])

    handler = app.make_delete_folder_handler("allowed/prefix")
    handler("bucket", "allowed/prefix/subfolder")

    # Não deve lançar exceção
    mock_service.remove_storage_objects.assert_called()


def test_make_delete_folder_handler_blocks_wrong_prefix(app):
    """Testa handler bloqueia delete fora do prefixo permitido."""
    handler = app.make_delete_folder_handler("allowed/prefix")

    with pytest.raises(AuditoriaServiceError, match="Operação fora do escopo"):
        handler("bucket", "wrong/prefix")


def test_make_delete_folder_handler_normalizes_slashes(app, mock_service, monkeypatch):
    """Testa handler normaliza barras no prefixo."""
    mock_service.is_online.return_value = True
    monkeypatch.setattr(app, "_collect_storage_keys", lambda b, p: ["key1"])

    handler = app.make_delete_folder_handler("/allowed/prefix/")
    handler("bucket", "/allowed/prefix/subfolder/")

    # Não deve lançar exceção
    mock_service.remove_storage_objects.assert_called()


def test_make_delete_folder_handler_empty_allowed_prefix(app, mock_service, monkeypatch):
    """Testa handler com allowed_prefix vazio permite qualquer path."""
    mock_service.is_online.return_value = True
    monkeypatch.setattr(app, "_collect_storage_keys", lambda b, p: ["key1"])

    handler = app.make_delete_folder_handler("")
    handler("bucket", "any/path")

    # Não deve lançar exceção
    mock_service.remove_storage_objects.assert_called()


# ==================== Testes de _collect_storage_keys ====================


def test_collect_storage_keys_empty_list(app, monkeypatch):
    """Testa _collect_storage_keys com lista vazia."""
    from src.modules.uploads import service as uploads_service

    monkeypatch.setattr(uploads_service, "list_storage_objects", lambda b, prefix: [])

    result = app._collect_storage_keys("bucket", "prefix")

    assert result == []


def test_collect_storage_keys_files_only(app, monkeypatch):
    """Testa _collect_storage_keys com apenas arquivos."""
    from src.modules.uploads import service as uploads_service

    entries = [
        {"full_path": "file1.txt", "is_folder": False},
        {"full_path": "file2.txt", "is_folder": False},
    ]
    monkeypatch.setattr(uploads_service, "list_storage_objects", lambda b, prefix: entries)

    result = app._collect_storage_keys("bucket", "prefix")

    assert result == ["file1.txt", "file2.txt"]


def test_collect_storage_keys_with_folders_recursive(app, monkeypatch):
    """Testa _collect_storage_keys com pastas (recursão)."""
    from src.modules.uploads import service as uploads_service

    # Primeira chamada retorna pasta + arquivo
    # Segunda chamada (recursiva) retorna arquivos dentro da pasta
    call_count = [0]

    def mock_list(b, prefix):
        call_count[0] += 1
        if call_count[0] == 1:
            return [
                {"full_path": "folder1", "is_folder": True},
                {"full_path": "file1.txt", "is_folder": False},
            ]
        else:
            return [{"full_path": "folder1/file2.txt", "is_folder": False}]

    monkeypatch.setattr(uploads_service, "list_storage_objects", mock_list)

    result = app._collect_storage_keys("bucket", "prefix")

    assert "file1.txt" in result
    assert "folder1/file2.txt" in result
    assert "folder1" not in result  # Pastas não são incluídas


def test_collect_storage_keys_skips_empty_paths(app, monkeypatch):
    """Testa _collect_storage_keys ignora paths vazios após strip."""
    from src.modules.uploads import service as uploads_service

    entries = [
        {"full_path": "", "is_folder": False},  # Vazio será ignorado
        {"full_path": "file1.txt", "is_folder": False},
    ]
    monkeypatch.setattr(uploads_service, "list_storage_objects", lambda b, prefix: entries)

    result = app._collect_storage_keys("bucket", "prefix")

    assert result == ["file1.txt"]


def test_collect_storage_keys_normalizes_slashes(app, monkeypatch):
    """Testa _collect_storage_keys normaliza barras."""
    from src.modules.uploads import service as uploads_service

    entries = [
        {"full_path": "/file1.txt/", "is_folder": False},
        {"full_path": "//file2.txt//", "is_folder": False},
    ]
    monkeypatch.setattr(uploads_service, "list_storage_objects", lambda b, prefix: entries)

    result = app._collect_storage_keys("bucket", "prefix")

    assert result == ["file1.txt", "file2.txt"]


def test_collect_storage_keys_handles_none_list(app, monkeypatch):
    """Testa _collect_storage_keys quando list_storage_objects retorna None."""
    from src.modules.uploads import service as uploads_service

    monkeypatch.setattr(uploads_service, "list_storage_objects", lambda b, prefix: None)

    result = app._collect_storage_keys("bucket", "prefix")

    assert result == []


# ==================== Testes de Archive/Upload Pipeline ====================


def test_is_supported_archive(app, mock_service):
    """Testa is_supported_archive delega para service."""
    mock_service.is_supported_archive.return_value = True

    result = app.is_supported_archive("file.zip")

    assert result is True
    mock_service.is_supported_archive.assert_called_once_with("file.zip")


def test_is_supported_archive_path_object(app, mock_service):
    """Testa is_supported_archive com Path object."""
    mock_service.is_supported_archive.return_value = False

    result = app.is_supported_archive(Path("file.txt"))

    assert result is False


def test_prepare_upload_context(app, mock_service):
    """Testa prepare_upload_context delega para service."""
    mock_context = MagicMock(spec=AuditoriaUploadContext)
    mock_service.prepare_upload_context.return_value = mock_context

    result = app.prepare_upload_context(42, org_id="org-123")

    assert result is mock_context
    mock_service.prepare_upload_context.assert_called_once_with(42, org_id="org-123")


def test_prepare_upload_context_no_org_id(app, mock_service):
    """Testa prepare_upload_context sem org_id."""
    mock_context = MagicMock(spec=AuditoriaUploadContext)
    mock_service.prepare_upload_context.return_value = mock_context

    app.prepare_upload_context(42)

    mock_service.prepare_upload_context.assert_called_once_with(42, org_id=None)


def test_prepare_archive_plan(app, mock_service):
    """Testa prepare_archive_plan delega para service."""
    mock_plan = MagicMock(spec=AuditoriaArchivePlan)
    mock_service.prepare_archive_plan.return_value = mock_plan

    result = app.prepare_archive_plan("archive.zip")

    assert result is mock_plan
    mock_service.prepare_archive_plan.assert_called_once_with("archive.zip")


def test_cleanup_archive_plan(app, mock_service):
    """Testa cleanup_archive_plan delega para service."""
    mock_plan = MagicMock(spec=AuditoriaArchivePlan)

    app.cleanup_archive_plan(mock_plan)

    mock_service.cleanup_archive_plan.assert_called_once_with(mock_plan)


def test_cleanup_archive_plan_none(app, mock_service):
    """Testa cleanup_archive_plan com None."""
    app.cleanup_archive_plan(None)

    mock_service.cleanup_archive_plan.assert_called_once_with(None)


def test_list_existing_names_for_context(app, mock_service):
    """Testa list_existing_names_for_context delega para service."""
    mock_context = MagicMock(spec=AuditoriaUploadContext)
    mock_service.list_existing_names_for_context.return_value = {"file1.txt", "file2.txt"}

    result = app.list_existing_names_for_context(mock_context)

    assert result == {"file1.txt", "file2.txt"}
    mock_service.list_existing_names_for_context.assert_called_once_with(mock_context)


def test_detect_duplicate_file_names(app, mock_service):
    """Testa detect_duplicate_file_names delega para service."""
    mock_plan = MagicMock(spec=AuditoriaArchivePlan)
    existing = {"file1.txt"}
    mock_service.detect_duplicate_file_names.return_value = {"file1.txt"}

    result = app.detect_duplicate_file_names(mock_plan, existing)

    assert result == {"file1.txt"}
    mock_service.detect_duplicate_file_names.assert_called_once_with(mock_plan, existing)


def test_execute_archive_upload(app, mock_service):
    """Testa execute_archive_upload delega para service com todos os parâmetros."""
    mock_plan = MagicMock(spec=AuditoriaArchivePlan)
    mock_context = MagicMock(spec=AuditoriaUploadContext)
    mock_result = MagicMock(spec=AuditoriaUploadResult)
    mock_service.execute_archive_upload.return_value = mock_result

    def cancel_check():
        return False

    def progress_cb(p):
        pass

    existing = {"file1.txt"}
    duplicates = set()

    result = app.execute_archive_upload(
        mock_plan,
        mock_context,
        strategy="skip",
        existing_names=existing,
        duplicates=duplicates,
        cancel_check=cancel_check,
        progress_callback=progress_cb,
    )

    assert result is mock_result
    mock_service.execute_archive_upload.assert_called_once_with(
        mock_plan,
        mock_context,
        strategy="skip",
        existing_names=existing,
        duplicates=duplicates,
        cancel_check=cancel_check,
        progress_callback=progress_cb,
    )


def test_execute_archive_upload_minimal_params(app, mock_service):
    """Testa execute_archive_upload com parâmetros mínimos."""
    mock_plan = MagicMock(spec=AuditoriaArchivePlan)
    mock_context = MagicMock(spec=AuditoriaUploadContext)
    mock_result = MagicMock(spec=AuditoriaUploadResult)
    mock_service.execute_archive_upload.return_value = mock_result

    result = app.execute_archive_upload(
        mock_plan, mock_context, strategy="overwrite", existing_names=set(), duplicates=set()
    )

    assert result is mock_result


def test_list_existing_file_names(app, mock_service):
    """Testa list_existing_file_names delega para service."""
    mock_service.list_existing_file_names.return_value = {"file1.txt", "file2.txt"}

    result = app.list_existing_file_names("bucket", "prefix")

    assert result == {"file1.txt", "file2.txt"}
    mock_service.list_existing_file_names.assert_called_once_with("bucket", "prefix")


# ==================== Testes de Rollback ====================


def test_rollback_uploaded_paths(app, mock_service):
    """Testa rollback_uploaded_paths delega para service."""
    mock_context = MagicMock(spec=AuditoriaUploadContext)
    paths = ["path1", "path2"]

    app.rollback_uploaded_paths(mock_context, paths)

    mock_service.rollback_uploaded_paths.assert_called_once_with(mock_context, paths)
