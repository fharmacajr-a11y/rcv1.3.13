"""Testes de regressao para os modulos src.modules.*.

Garante que os services/views expostos pelos modulos apontam
para as mesmas funcoes/classes do codigo legado. Isso ajuda a
detectar regressoes quando refatorarmos a camada de modulos.
"""

from __future__ import annotations


def test_clientes_service_aliases() -> None:
    from src.modules.clientes import service as mod
    from src.core.services import clientes_service as legacy

    assert mod.count_clients is legacy.count_clients
    assert mod.checar_duplicatas_info is legacy.checar_duplicatas_info
    assert mod.salvar_cliente is legacy.salvar_cliente


def test_lixeira_service_aliases() -> None:
    from src.modules.lixeira import service as mod
    from src.core.services import lixeira_service as legacy

    assert mod.restore_clients is legacy.restore_clients
    assert mod.hard_delete_clients is legacy.hard_delete_clients


def test_notas_service_aliases() -> None:
    from src.modules.notas import service as mod
    from src.core.services import notes_service as legacy

    assert mod.list_notes is legacy.list_notes
    assert mod.add_note is legacy.add_note
    assert mod.list_notes_since is legacy.list_notes_since
    assert mod.NotesTransientError is legacy.NotesTransientError
    assert mod.NotesAuthError is legacy.NotesAuthError
    assert mod.NotesTableMissingError is legacy.NotesTableMissingError


def test_uploads_service_aliases() -> None:
    from src.modules.uploads import service as mod
    from src.core.services import upload_service as legacy

    assert mod.upload_folder_to_supabase is legacy.upload_folder_to_supabase


def test_forms_service_aliases() -> None:
    from src.modules.forms import service as mod
    from src.core.services import clientes_service as legacy_clientes

    assert mod.salvar_cliente is legacy_clientes.salvar_cliente
    assert mod.checar_duplicatas_info is legacy_clientes.checar_duplicatas_info


def test_login_service_aliases() -> None:
    from src.modules.login import service as mod
    from src.core import auth as legacy_auth
    from src.core import auth_controller as legacy_controller

    assert mod.authenticate_user is legacy_auth.authenticate_user
    assert mod.create_user is legacy_auth.create_user
    assert mod.ensure_users_db is legacy_auth.ensure_users_db
    assert mod.validate_credentials is legacy_auth.validate_credentials
    assert mod.AuthController is legacy_controller.AuthController


def test_pdf_preview_service_aliases() -> None:
    from src.modules.pdf_preview import service as mod
    from src.utils import pdf_reader as legacy

    assert mod.read_pdf_text is legacy.read_pdf_text
