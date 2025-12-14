# tests/core/services/test_path_resolver.py
"""
Testes unitários para src/core/services/path_resolver.py
Objetivo: aumentar cobertura de branches não exercitados (linhas 21-25, 40-41, 44, 56-70, 89-98, 114, 116, 119, 121).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from src.core.services.path_resolver import (
    ResolveResult,
    _candidate_by_slug,
    _find_by_marker,
    _limited_walk,
    resolve_cliente_path,
    resolve_unique_path,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Test _limited_walk
# ============================================================================


def test_limited_walk_respects_max_depth(tmp_path: Path) -> None:
    """_limited_walk deve respeitar max_depth e não descer além do limite."""
    # Criar estrutura: tmp_path / level1 / level2 / level3
    level1 = tmp_path / "level1"
    level2 = level1 / "level2"
    level3 = level2 / "level3"
    level3.mkdir(parents=True)

    # Criar arquivo em cada nível para verificar
    (tmp_path / "root.txt").touch()
    (level1 / "l1.txt").touch()
    (level2 / "l2.txt").touch()
    (level3 / "l3.txt").touch()

    # max_depth=1 deve retornar apenas root e level1
    results = list(_limited_walk(str(tmp_path), max_depth=1))
    paths = [r[0] for r in results]

    assert str(tmp_path) in paths
    assert str(level1) in paths
    # level2 e level3 não devem aparecer
    assert str(level2) not in paths
    assert str(level3) not in paths


def test_limited_walk_max_depth_zero(tmp_path: Path) -> None:
    """_limited_walk com max_depth=0 deve retornar apenas a raiz."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    results = list(_limited_walk(str(tmp_path), max_depth=0))
    paths = [r[0] for r in results]

    assert str(tmp_path) in paths
    assert str(subdir) not in paths


# ============================================================================
# Test _candidate_by_slug
# ============================================================================


def test_candidate_by_slug_cliente_existe(monkeypatch: pytest.MonkeyPatch) -> None:
    """_candidate_by_slug deve retornar slug quando cliente existe no banco."""
    from types import SimpleNamespace

    fake_cliente = SimpleNamespace(
        numero="001",
        cnpj="12345678000199",
        razao_social="Acme Corp",
    )

    def fake_get_cliente_by_id(pk: int):
        if pk == 123:
            return fake_cliente
        return None

    monkeypatch.setattr("src.core.services.path_resolver.get_cliente_by_id", fake_get_cliente_by_id)

    result = _candidate_by_slug(123)
    assert result is not None
    assert "12345678" in result or "Acme" in result or "001" in result


def test_candidate_by_slug_cliente_nao_existe(monkeypatch: pytest.MonkeyPatch) -> None:
    """_candidate_by_slug deve retornar None quando cliente não existe."""

    def fake_get_cliente_by_id(pk: int):
        return None

    monkeypatch.setattr("src.core.services.path_resolver.get_cliente_by_id", fake_get_cliente_by_id)

    result = _candidate_by_slug(999)
    assert result is None


def test_candidate_by_slug_exception_no_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """_candidate_by_slug deve retornar None quando get_cliente_by_id levanta exceção."""

    def fake_get_cliente_by_id(pk: int):
        raise RuntimeError("Database error")

    monkeypatch.setattr("src.core.services.path_resolver.get_cliente_by_id", fake_get_cliente_by_id)

    result = _candidate_by_slug(123)
    assert result is None


# ============================================================================
# Test _find_by_marker
# ============================================================================


def test_find_by_marker_encontra_pasta_com_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_find_by_marker deve encontrar pasta quando .rcid existe e coincide com pk."""
    cliente_dir = tmp_path / "cliente_001"
    cliente_dir.mkdir()

    def fake_read_marker_id(path: str) -> int | None:
        if path == str(cliente_dir):
            return 42
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)

    result = _find_by_marker(tmp_path, 42)
    assert result == str(cliente_dir)


def test_find_by_marker_nao_encontra_quando_marker_diferente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_find_by_marker deve retornar None quando marker existe mas ID não coincide."""
    cliente_dir = tmp_path / "cliente_001"
    cliente_dir.mkdir()

    def fake_read_marker_id(path: str) -> int | None:
        return 99  # ID diferente

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)

    result = _find_by_marker(tmp_path, 42)
    assert result is None


def test_find_by_marker_skip_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_find_by_marker deve pular pastas em skip_names."""
    # Criar apenas _LIXEIRA para garantir que é a única opção
    lixeira = tmp_path / "_LIXEIRA"
    lixeira.mkdir()

    call_count = 0

    def fake_read_marker_id(path: str) -> int | None:
        nonlocal call_count
        call_count += 1
        if path == str(lixeira):
            return 42
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)

    # Sem skip_names, deveria encontrar
    call_count = 0
    result_sem_skip = _find_by_marker(tmp_path, 42)
    assert result_sem_skip == str(lixeira)
    assert call_count > 0

    # Com skip_names, não deve encontrar
    call_count = 0
    result_com_skip = _find_by_marker(tmp_path, 42, skip_names={"_LIXEIRA"})
    assert result_com_skip is None
    # Não deve ter chamado read_marker_id para _LIXEIRA
    # (mas pode ter chamado para outras pastas criadas pelo pytest)


def test_find_by_marker_root_nao_existe(tmp_path: Path) -> None:
    """_find_by_marker deve retornar None quando root não é diretório."""
    nao_existe = tmp_path / "nao_existe"
    result = _find_by_marker(nao_existe, 42)
    assert result is None


def test_find_by_marker_ignora_arquivos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_find_by_marker deve ignorar arquivos (não-diretórios)."""
    arquivo = tmp_path / "arquivo.txt"
    arquivo.touch()

    cliente_dir = tmp_path / "cliente_001"
    cliente_dir.mkdir()

    def fake_read_marker_id(path: str) -> int | None:
        if path == str(cliente_dir):
            return 42
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)

    result = _find_by_marker(tmp_path, 42)
    assert result == str(cliente_dir)


def test_find_by_marker_exception_reading_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """_find_by_marker deve ignorar exceções ao ler marker e continuar procurando."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    def fake_read_marker_id(path: str) -> int | None:
        if path == str(dir1):
            raise OSError("Cannot read marker")
        if path == str(dir2):
            return 42
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)

    result = _find_by_marker(tmp_path, 42)
    assert result == str(dir2)


# ============================================================================
# Test resolve_cliente_path
# ============================================================================


def test_resolve_cliente_path_encontra_por_marker_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_cliente_path deve encontrar pasta ativa via marker."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    cliente_dir = docs_dir / "cliente_001"
    cliente_dir.mkdir()

    monkeypatch.setattr("src.core.services.path_resolver.DOCS_DIR", str(docs_dir))
    monkeypatch.setattr("src.core.services.path_resolver.TRASH_DIR", str(docs_dir / "_LIXEIRA"))

    def fake_read_marker_id(path: str) -> int | None:
        if path == str(cliente_dir):
            return 42
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)

    result = resolve_cliente_path(42)
    assert result.pk == 42
    assert result.active == str(cliente_dir)
    assert result.trash is None


def test_resolve_cliente_path_encontra_por_marker_trash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_cliente_path deve encontrar pasta na lixeira via marker."""
    docs_dir = tmp_path / "docs"
    trash_dir = docs_dir / "_LIXEIRA"
    trash_dir.mkdir(parents=True)
    cliente_trash = trash_dir / "cliente_001"
    cliente_trash.mkdir()

    monkeypatch.setattr("src.core.services.path_resolver.DOCS_DIR", str(docs_dir))
    monkeypatch.setattr("src.core.services.path_resolver.TRASH_DIR", str(trash_dir))

    def fake_read_marker_id(path: str) -> int | None:
        if path == str(cliente_trash):
            return 42
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)

    result = resolve_cliente_path(42)
    assert result.pk == 42
    assert result.active is None
    assert result.trash == str(cliente_trash)


def test_resolve_cliente_path_encontra_por_slug_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_cliente_path deve encontrar pasta ativa via slug quando marker não existe."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    slug = "001_12345678_Acme"
    cliente_dir = docs_dir / slug
    cliente_dir.mkdir()

    monkeypatch.setattr("src.core.services.path_resolver.DOCS_DIR", str(docs_dir))
    monkeypatch.setattr("src.core.services.path_resolver.TRASH_DIR", str(docs_dir / "_LIXEIRA"))

    def fake_read_marker_id(path: str) -> int | None:
        return None  # Sem marker

    def fake_candidate_by_slug(pk: int) -> str | None:
        return slug

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)
    monkeypatch.setattr("src.core.services.path_resolver._candidate_by_slug", fake_candidate_by_slug)

    result = resolve_cliente_path(42)
    assert result.pk == 42
    assert result.active == str(cliente_dir)
    assert result.slug == slug


def test_resolve_cliente_path_encontra_por_slug_trash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_cliente_path deve encontrar pasta na lixeira via slug."""
    docs_dir = tmp_path / "docs"
    trash_dir = docs_dir / "_LIXEIRA"
    trash_dir.mkdir(parents=True)
    slug = "001_12345678_Acme"
    cliente_trash = trash_dir / slug
    cliente_trash.mkdir()

    monkeypatch.setattr("src.core.services.path_resolver.DOCS_DIR", str(docs_dir))
    monkeypatch.setattr("src.core.services.path_resolver.TRASH_DIR", str(trash_dir))

    def fake_read_marker_id(path: str) -> int | None:
        return None

    def fake_candidate_by_slug(pk: int) -> str | None:
        return slug

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)
    monkeypatch.setattr("src.core.services.path_resolver._candidate_by_slug", fake_candidate_by_slug)

    result = resolve_cliente_path(42)
    assert result.pk == 42
    assert result.active is None
    assert result.trash == str(cliente_trash)


def test_resolve_cliente_path_nao_encontra_nada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_cliente_path deve retornar result vazio quando pasta não existe."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    monkeypatch.setattr("src.core.services.path_resolver.DOCS_DIR", str(docs_dir))
    monkeypatch.setattr("src.core.services.path_resolver.TRASH_DIR", str(docs_dir / "_LIXEIRA"))

    def fake_read_marker_id(path: str) -> int | None:
        return None

    def fake_candidate_by_slug(pk: int) -> str | None:
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)
    monkeypatch.setattr("src.core.services.path_resolver._candidate_by_slug", fake_candidate_by_slug)

    result = resolve_cliente_path(999)
    assert result.pk == 999
    assert result.active is None
    assert result.trash is None
    assert result.slug is None


# ============================================================================
# Test resolve_unique_path
# ============================================================================


def test_resolve_unique_path_prefer_active_quando_existe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_unique_path com prefer='active' deve retornar active quando existe."""
    docs_dir = tmp_path / "docs"
    trash_dir = docs_dir / "_LIXEIRA"
    docs_dir.mkdir()
    trash_dir.mkdir()

    active_dir = docs_dir / "cliente_001"
    trash_cliente = trash_dir / "cliente_001"
    active_dir.mkdir()
    trash_cliente.mkdir()

    monkeypatch.setattr("src.core.services.path_resolver.DOCS_DIR", str(docs_dir))
    monkeypatch.setattr("src.core.services.path_resolver.TRASH_DIR", str(trash_dir))

    def fake_read_marker_id(path: str) -> int | None:
        if path == str(active_dir):
            return 42
        if path == str(trash_cliente):
            return 42
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)

    path, location = resolve_unique_path(42, prefer="active")
    assert path == str(active_dir)
    assert location == "active"


def test_resolve_unique_path_prefer_trash_quando_existe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_unique_path com prefer='trash' deve retornar trash quando existe."""
    docs_dir = tmp_path / "docs"
    trash_dir = docs_dir / "_LIXEIRA"
    docs_dir.mkdir()
    trash_dir.mkdir()

    active_dir = docs_dir / "cliente_001"
    trash_cliente = trash_dir / "cliente_001"
    active_dir.mkdir()
    trash_cliente.mkdir()

    monkeypatch.setattr("src.core.services.path_resolver.DOCS_DIR", str(docs_dir))
    monkeypatch.setattr("src.core.services.path_resolver.TRASH_DIR", str(trash_dir))

    def fake_read_marker_id(path: str) -> int | None:
        if path == str(active_dir):
            return 42
        if path == str(trash_cliente):
            return 42
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)

    path, location = resolve_unique_path(42, prefer="trash")
    assert path == str(trash_cliente)
    assert location == "trash"


def test_resolve_unique_path_fallback_to_active_quando_both(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_unique_path com prefer='both' deve priorizar active quando ambos existem."""
    docs_dir = tmp_path / "docs"
    trash_dir = docs_dir / "_LIXEIRA"
    docs_dir.mkdir()
    trash_dir.mkdir()

    active_dir = docs_dir / "cliente_001"
    trash_cliente = trash_dir / "cliente_001"
    active_dir.mkdir()
    trash_cliente.mkdir()

    monkeypatch.setattr("src.core.services.path_resolver.DOCS_DIR", str(docs_dir))
    monkeypatch.setattr("src.core.services.path_resolver.TRASH_DIR", str(trash_dir))

    def fake_read_marker_id(path: str) -> int | None:
        if path == str(active_dir):
            return 42
        if path == str(trash_cliente):
            return 42
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)

    path, location = resolve_unique_path(42, prefer="both")
    assert path == str(active_dir)
    assert location == "active"


def test_resolve_unique_path_retorna_trash_quando_active_nao_existe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """resolve_unique_path deve retornar trash quando active não existe."""
    docs_dir = tmp_path / "docs"
    trash_dir = docs_dir / "_LIXEIRA"
    docs_dir.mkdir()
    trash_dir.mkdir()

    trash_cliente = trash_dir / "cliente_001"
    trash_cliente.mkdir()

    monkeypatch.setattr("src.core.services.path_resolver.DOCS_DIR", str(docs_dir))
    monkeypatch.setattr("src.core.services.path_resolver.TRASH_DIR", str(trash_dir))

    def fake_read_marker_id(path: str) -> int | None:
        if path == str(trash_cliente):
            return 42
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)

    path, location = resolve_unique_path(42, prefer="both")
    assert path == str(trash_cliente)
    assert location == "trash"


def test_resolve_unique_path_retorna_none_quando_nada_existe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve_unique_path deve retornar (None, None) quando nenhuma pasta existe."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    monkeypatch.setattr("src.core.services.path_resolver.DOCS_DIR", str(docs_dir))
    monkeypatch.setattr("src.core.services.path_resolver.TRASH_DIR", str(docs_dir / "_LIXEIRA"))

    def fake_read_marker_id(path: str) -> int | None:
        return None

    def fake_candidate_by_slug(pk: int) -> str | None:
        return None

    monkeypatch.setattr("src.core.services.path_resolver.read_marker_id", fake_read_marker_id)
    monkeypatch.setattr("src.core.services.path_resolver._candidate_by_slug", fake_candidate_by_slug)

    path, location = resolve_unique_path(999, prefer="both")
    assert path is None
    assert location is None


# ============================================================================
# Test ResolveResult dataclass
# ============================================================================


def test_resolve_result_default_values() -> None:
    """ResolveResult deve ter valores padrão None para campos opcionais."""
    result = ResolveResult(pk=123)
    assert result.pk == 123
    assert result.active is None
    assert result.trash is None
    assert result.slug is None


def test_resolve_result_com_valores() -> None:
    """ResolveResult deve armazenar valores fornecidos."""
    result = ResolveResult(pk=42, active="/path/to/active", trash="/path/to/trash", slug="001_cnpj_razao")
    assert result.pk == 42
    assert result.active == "/path/to/active"
    assert result.trash == "/path/to/trash"
    assert result.slug == "001_cnpj_razao"
