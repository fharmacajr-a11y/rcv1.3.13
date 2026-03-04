# -*- coding: utf-8 -*-
"""Tests for src.core.services.path_manager — PR21: coverage step 2.

Covers FS helpers (no network, no DB):
- ensure_dir: creates nested dir, returns True; handles failure
- safe_move_dir: normal move, overwrite guard, missing src
- ensure_subfolders: creates batch, reports failures
- read_marker_id / write_marker_id: round-trip, missing marker
- slug_from_path: basename extraction
- PathResolution dataclass instantiation
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.core.services.path_manager import (
    PathResolution,
    ensure_dir,
    ensure_subfolders,
    read_marker_id,
    safe_move_dir,
    slug_from_path,
    write_marker_id,
)


# ---------------------------------------------------------------------------
# slug_from_path (pure)
# ---------------------------------------------------------------------------
class TestSlugFromPath:
    def test_normal_path(self) -> None:
        assert slug_from_path("/home/user/docs/ACME Corp") == "ACME Corp"

    def test_trailing_slash(self) -> None:
        assert slug_from_path("C:\\Users\\docs\\Foo\\") == "Foo"

    def test_none(self) -> None:
        assert slug_from_path(None) is None

    def test_empty_string(self) -> None:
        assert slug_from_path("") is None


# ---------------------------------------------------------------------------
# PathResolution dataclass
# ---------------------------------------------------------------------------
def test_path_resolution_frozen() -> None:
    r = PathResolution(pk=1, active_path="/a", trash_path=None, location="active", has_conflict=False)
    assert r.pk == 1
    assert r.location == "active"
    assert r.marker_id is None
    with pytest.raises(AttributeError):
        r.pk = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ensure_dir
# ---------------------------------------------------------------------------
class TestEnsureDir:
    def test_creates_nested(self, tmp_path: Path) -> None:
        target = str(tmp_path / "a" / "b" / "c")
        assert ensure_dir(target) is True
        assert os.path.isdir(target)

    def test_existing_dir_is_ok(self, tmp_path: Path) -> None:
        target = str(tmp_path / "existing")
        os.makedirs(target)
        assert ensure_dir(target) is True

    def test_failure_returns_false(self, tmp_path: Path) -> None:
        # Create a file where a dir is expected — makedirs will fail
        blocker = tmp_path / "blocker"
        blocker.write_text("x")
        assert ensure_dir(str(blocker / "sub")) is False


# ---------------------------------------------------------------------------
# safe_move_dir
# ---------------------------------------------------------------------------
class TestSafeMoveDir:
    def test_normal_move(self, tmp_path: Path) -> None:
        src = tmp_path / "src_dir"
        src.mkdir()
        (src / "file.txt").write_text("hello")
        dst = str(tmp_path / "dst_dir")

        ok, err = safe_move_dir(str(src), dst)
        assert ok is True
        assert err is None
        assert os.path.isfile(os.path.join(dst, "file.txt"))
        assert not os.path.exists(str(src))

    def test_src_not_a_dir(self, tmp_path: Path) -> None:
        ok, err = safe_move_dir(str(tmp_path / "nonexistent"), str(tmp_path / "dst"))
        assert ok is False
        assert "Origem" in (err or "")

    def test_dst_exists_no_overwrite(self, tmp_path: Path) -> None:
        src = tmp_path / "s"
        src.mkdir()
        dst = tmp_path / "d"
        dst.mkdir()

        ok, err = safe_move_dir(str(src), str(dst), overwrite=False)
        assert ok is False
        assert "Destino" in (err or "")

    def test_creates_parent_of_dst(self, tmp_path: Path) -> None:
        src = tmp_path / "from"
        src.mkdir()
        dst = str(tmp_path / "deep" / "nested" / "to")

        ok, err = safe_move_dir(str(src), dst)
        assert ok is True
        assert os.path.isdir(dst)


# ---------------------------------------------------------------------------
# ensure_subfolders
# ---------------------------------------------------------------------------
class TestEnsureSubfolders:
    def test_creates_all(self, tmp_path: Path) -> None:
        created, failures = ensure_subfolders(str(tmp_path), ["GERAL", "FINANCEIRO", "CONTRATOS"])
        assert set(created) == {"GERAL", "FINANCEIRO", "CONTRATOS"}
        assert failures == []
        for name in created:
            assert os.path.isdir(tmp_path / name)

    def test_empty_names(self, tmp_path: Path) -> None:
        created, failures = ensure_subfolders(str(tmp_path), [])
        assert created == []
        assert failures == []

    def test_none_names(self, tmp_path: Path) -> None:
        created, failures = ensure_subfolders(str(tmp_path), None)  # type: ignore[arg-type]
        assert created == []
        assert failures == []


# ---------------------------------------------------------------------------
# read_marker_id / write_marker_id
# ---------------------------------------------------------------------------
class TestMarkerRoundTrip:
    def test_write_and_read(self, tmp_path: Path) -> None:
        dir_path = str(tmp_path / "client_42")
        assert write_marker_id(dir_path, "42") is True
        assert read_marker_id(dir_path) == "42"

    def test_read_none_when_no_marker(self, tmp_path: Path) -> None:
        empty_dir = str(tmp_path / "empty")
        os.makedirs(empty_dir)
        assert read_marker_id(empty_dir) is None

    def test_read_none_from_none_path(self) -> None:
        assert read_marker_id(None) is None

    def test_write_creates_dir_if_missing(self, tmp_path: Path) -> None:
        dir_path = str(tmp_path / "new_dir")
        assert write_marker_id(dir_path, "99") is True
        assert os.path.isdir(dir_path)
        assert read_marker_id(dir_path) == "99"

    def test_write_strips_whitespace(self, tmp_path: Path) -> None:
        dir_path = str(tmp_path / "ws")
        write_marker_id(dir_path, "  77  ")
        assert read_marker_id(dir_path) == "77"

    def test_custom_filename(self, tmp_path: Path) -> None:
        dir_path = str(tmp_path / "custom")
        write_marker_id(dir_path, "123", filename=".marker_id")
        # read_marker_id checks _MARKER_CANDIDATES which includes .marker_id
        assert read_marker_id(dir_path) == "123"
