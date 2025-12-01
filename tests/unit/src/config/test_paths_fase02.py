"""
Testes para src.config.paths - Coverage Pack 05 - Fase 02.

Objetivo: cobrir branches de cloud-only vs modo local (linhas 47-54).
Estratégia: usar monkeypatch para simular diferentes valores de RC_NO_LOCAL_FS.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _cleanup_imports():
    """Remove src.config.paths do cache de módulos para reimportar."""
    import sys

    if "src.config.paths" in sys.modules:
        del sys.modules["src.config.paths"]
    if "src.config.environment" in sys.modules:
        del sys.modules["src.config.environment"]

    yield

    if "src.config.paths" in sys.modules:
        del sys.modules["src.config.paths"]
    if "src.config.environment" in sys.modules:
        del sys.modules["src.config.environment"]


def test_paths_modo_cloud_only(monkeypatch):
    """
    Testa branch cloud-only (linhas 33-43).

    Quando RC_NO_LOCAL_FS=1, paths devem apontar para diretório temporário
    e NÃO criar diretórios na pasta do app.
    """
    # Define RC_NO_LOCAL_FS=1 para ativar cloud-only
    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")

    # Importa paths após configurar a variável de ambiente
    import src.config.paths as paths

    # Verifica flag cloud-only
    assert paths.CLOUD_ONLY is True

    # Verifica que os paths estão no diretório temporário
    tmp_base = Path(tempfile.gettempdir()) / "rc_void"
    assert paths.DB_DIR == tmp_base / "db"
    assert paths.DB_PATH == tmp_base / "db" / "disabled.db"
    assert paths.USERS_DB_PATH == tmp_base / "users" / "disabled_users.db"
    assert paths.DOCS_DIR == tmp_base / "docs"

    # Verifica que os diretórios NÃO foram criados automaticamente
    # (característica do modo cloud: lazy creation)
    assert not paths.DB_DIR.exists()
    assert not paths.DOCS_DIR.exists()


def test_paths_modo_local_cria_diretorios(monkeypatch, tmp_path):
    """
    Testa branch local (linhas 47-54).

    Quando RC_NO_LOCAL_FS != 1, paths devem criar diretórios db/ e clientes_docs/
    dentro do APP_DATA.
    """
    # Define RC_NO_LOCAL_FS=0 (ou qualquer valor != "1")
    monkeypatch.setenv("RC_NO_LOCAL_FS", "0")

    # Usa tmp_path como RC_APP_DATA para isolar o teste
    monkeypatch.setenv("RC_APP_DATA", str(tmp_path))

    # Importa paths após configurar as variáveis
    import src.config.paths as paths

    # Verifica flag cloud-only
    assert paths.CLOUD_ONLY is False

    # Verifica que APP_DATA aponta para tmp_path
    assert paths.APP_DATA == tmp_path

    # Verifica que os paths estão dentro do APP_DATA
    assert paths.DB_DIR == tmp_path / "db"
    assert paths.DB_PATH == tmp_path / "db" / "clientes.db"
    assert paths.USERS_DB_PATH == tmp_path / "db" / "users.db"
    assert paths.DOCS_DIR == tmp_path / "clientes_docs"

    # Verifica que os diretórios foram criados automaticamente
    assert paths.DB_DIR.exists()
    assert paths.DOCS_DIR.exists()


def test_paths_modo_local_sem_rc_app_data(monkeypatch):
    """
    Testa branch local quando RC_APP_DATA não está definida.

    Deve usar BASE_DIR (diretório do projeto) como APP_DATA.
    """
    # RC_NO_LOCAL_FS deve ser explicitamente False (modo local)
    monkeypatch.setenv("RC_NO_LOCAL_FS", "false")

    # RC_APP_DATA não definida
    monkeypatch.delenv("RC_APP_DATA", raising=False)

    # Importa paths
    import src.config.paths as paths

    # Verifica que CLOUD_ONLY é False
    assert paths.CLOUD_ONLY is False

    # Verifica que APP_DATA é BASE_DIR (default)
    assert paths.APP_DATA == paths.BASE_DIR

    # Verifica que os paths usam BASE_DIR
    assert paths.DB_DIR == paths.BASE_DIR / "db"
    assert paths.DOCS_DIR == paths.BASE_DIR / "clientes_docs"


def test_paths_base_dir_esta_correto():
    """
    Testa que BASE_DIR aponta para a raiz do projeto.

    paths.py está em src/config/paths.py → BASE_DIR é src/ (parent de config).
    """
    import src.config.paths as paths

    # BASE_DIR deve ser o diretório src/
    assert paths.BASE_DIR.name == "src"
    assert (paths.BASE_DIR / "config" / "paths.py").exists()


def test_paths_all_exporta_simbolos_corretos():
    """
    Testa que __all__ exporta os símbolos principais.
    """
    import src.config.paths as paths

    expected_exports = [
        "BASE_DIR",
        "APP_DATA",
        "CLOUD_ONLY",
        "DB_DIR",
        "DB_PATH",
        "USERS_DB_PATH",
        "DOCS_DIR",
    ]

    assert paths.__all__ == expected_exports

    # Verifica que todos os símbolos existem
    for symbol in expected_exports:
        assert hasattr(paths, symbol)


def test_paths_cloud_only_usa_tempdir():
    """
    Testa que modo cloud-only usa tempfile.gettempdir() corretamente.
    """
    import src.config.paths as paths

    if paths.CLOUD_ONLY:
        tmp_base = Path(tempfile.gettempdir()) / "rc_void"

        # Verifica que todos os paths estão sob tmp_base
        assert str(paths.DB_DIR).startswith(str(tmp_base))
        assert str(paths.DB_PATH).startswith(str(tmp_base))
        assert str(paths.USERS_DB_PATH).startswith(str(tmp_base))
        assert str(paths.DOCS_DIR).startswith(str(tmp_base))


def test_paths_local_db_path_correto(monkeypatch, tmp_path):
    """
    Testa que em modo local, DB_PATH aponta para clientes.db.
    """
    monkeypatch.setenv("RC_NO_LOCAL_FS", "0")
    monkeypatch.setenv("RC_APP_DATA", str(tmp_path))

    import src.config.paths as paths

    # Verifica nome do arquivo
    assert paths.DB_PATH.name == "clientes.db"
    assert paths.USERS_DB_PATH.name == "users.db"

    # Verifica que estão dentro de db/
    assert paths.DB_PATH.parent == paths.DB_DIR
    assert paths.USERS_DB_PATH.parent == paths.DB_DIR


def test_paths_cloud_db_path_disabled(monkeypatch):
    """
    Testa que em modo cloud, DB_PATH aponta para disabled.db.
    """
    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")

    import src.config.paths as paths

    # Verifica nome do arquivo
    assert paths.DB_PATH.name == "disabled.db"
    assert paths.USERS_DB_PATH.name == "disabled_users.db"
