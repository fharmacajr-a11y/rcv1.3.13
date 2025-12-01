from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import src.utils.file_utils.path_utils as path_utils


def test_split_pathlike_handles_slashes_and_empty() -> None:
    assert path_utils._split_pathlike("ANVISA/ALTERACAO_DE_PORTE") == ["ANVISA", "ALTERACAO_DE_PORTE"]
    assert path_utils._split_pathlike(r"\\foo\\bar\\") == ["foo", "bar"]
    assert path_utils._split_pathlike("") == []


def test_spec_helpers_handle_strings_and_mappings() -> None:
    assert path_utils._spec_name("name") == "name"
    assert path_utils._spec_name({"folder": "X"}) == "X"
    assert path_utils._spec_name({"dir": "Y"}) == "Y"
    assert path_utils._spec_name({"name": ""}) == ""

    assert path_utils._spec_children("leaf") == []
    assert path_utils._spec_children({"children": ["a", "b"]}) == ["a", "b"]
    assert path_utils._spec_children({"sub": ("x", "y")}) == ["x", "y"]
    assert path_utils._spec_children({"dirs": "not-list"}) == []


def test_ensure_dir_respects_cloud_only(monkeypatch, tmp_path: Path) -> None:
    orig = path_utils.CLOUD_ONLY
    try:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", True)
        target = tmp_path / "no_create"
        result = path_utils.ensure_dir(target)
        assert result == target
        assert not target.exists()

        monkeypatch.setattr(path_utils, "CLOUD_ONLY", False)
        target2 = tmp_path / "created"
        result2 = path_utils.ensure_dir(target2)
        assert result2.exists()
    finally:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", orig)


def test_safe_copy_creates_parent_and_copies(monkeypatch, tmp_path: Path) -> None:
    orig = path_utils.CLOUD_ONLY
    try:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", False)
        src = tmp_path / "src.txt"
        src.write_text("hello", encoding="utf-8")
        dst = tmp_path / "nested" / "dst.txt"

        path_utils.safe_copy(src, dst)

        assert dst.read_text(encoding="utf-8") == "hello"
    finally:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", orig)


def test_open_folder_skips_when_blocked(monkeypatch, tmp_path: Path) -> None:
    helper_mod = types.SimpleNamespace(check_cloud_only_block=lambda _: True)
    monkeypatch.setitem(sys.modules, "src.utils.helpers", helper_mod)
    called: list[str] = []
    monkeypatch.setattr(os, "startfile", lambda p: called.append(p))  # type: ignore[attr-defined]

    path_utils.open_folder(tmp_path)

    assert called == []


def test_open_folder_calls_startfile_when_allowed(monkeypatch, tmp_path: Path) -> None:
    helper_mod = types.SimpleNamespace(check_cloud_only_block=lambda _: False)
    monkeypatch.setitem(sys.modules, "src.utils.helpers", helper_mod)
    called: list[str] = []
    monkeypatch.setattr(os, "startfile", lambda p: called.append(p))  # type: ignore[attr-defined]

    path_utils.open_folder(tmp_path)

    assert called == [str(tmp_path)]


def test_ensure_subtree_creates_nested_structure(monkeypatch, tmp_path: Path) -> None:
    orig = path_utils.CLOUD_ONLY
    try:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", False)
        spec = [
            "",
            "DOCS/ANEXOS",
            {"name": ""},
            {"name": "ANVISA", "children": ["ALTERACAO_DE_PORTE", {"name": "RESP_LEGAL", "children": ["PROTOCOLOS"]}]},
        ]
        path_utils.ensure_subtree(tmp_path, spec)
        assert (tmp_path / "DOCS" / "ANEXOS").is_dir()
        assert (tmp_path / "ANVISA" / "ALTERACAO_DE_PORTE").is_dir()
        assert (tmp_path / "ANVISA" / "RESP_LEGAL" / "PROTOCOLOS").is_dir()
    finally:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", orig)


def test_ensure_subpastas_with_names(monkeypatch, tmp_path: Path) -> None:
    orig = path_utils.CLOUD_ONLY
    try:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", False)
        base = tmp_path / "base"
        nomes = ["DOCS", r"EXTRA\\SUB"]

        result = path_utils.ensure_subpastas(str(base), nomes=nomes)

        assert result is True
        assert (base / "DOCS").is_dir()
        assert (base / "EXTRA" / "SUB").is_dir()
    finally:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", orig)


def test_ensure_subpastas_with_alias_and_blank(monkeypatch, tmp_path: Path) -> None:
    orig = path_utils.CLOUD_ONLY
    try:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", False)
        base = tmp_path / "alias"
        names = ["", "/", "mantem"]

        result = path_utils.ensure_subpastas(str(base), subpastas=names)

        assert result is True
        assert (base / "mantem").is_dir()
    finally:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", orig)


def test_ensure_subpastas_uses_subpastas_config(monkeypatch, tmp_path: Path) -> None:
    orig = path_utils.CLOUD_ONLY
    try:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", False)
        fake_mod = types.SimpleNamespace(load_subpastas_config=lambda: (["A"], ["B"]))
        monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", fake_mod)

        base = tmp_path / "cfg"
        result = path_utils.ensure_subpastas(str(base))

        assert result is True
        assert (base / "A").is_dir()
        assert (base / "B").is_dir()
    finally:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", orig)
        sys.modules.pop("src.utils.subpastas_config", None)


def test_ensure_subpastas_len_three_tuple(monkeypatch, tmp_path: Path) -> None:
    orig = path_utils.CLOUD_ONLY
    try:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", False)
        fake_mod = types.SimpleNamespace(load_subpastas_config=lambda: ("TOP", ["ONE"], ["EXTRA"]))
        monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", fake_mod)

        base = tmp_path / "len3"
        result = path_utils.ensure_subpastas(str(base))

        assert result is True
        assert (base / "ONE").is_dir()
        assert (base / "EXTRA").is_dir()
    finally:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", orig)
        sys.modules.pop("src.utils.subpastas_config", None)


def test_ensure_subpastas_defaults_when_config_fails(monkeypatch, tmp_path: Path) -> None:
    orig = path_utils.CLOUD_ONLY
    try:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", False)
        fake_module = types.SimpleNamespace(load_subpastas_config=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", fake_module)

        base = tmp_path / "fallback"
        result = path_utils.ensure_subpastas(str(base))

        assert result is True
        assert (base / "DOCS").is_dir()
        assert (base / "ANEXOS").is_dir()
    finally:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", orig)
        sys.modules.pop("src.utils.subpastas_config", None)


def test_ensure_subpastas_default_creation_handles_os_error(monkeypatch, tmp_path: Path) -> None:
    orig = path_utils.CLOUD_ONLY
    try:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", False)
        fake_module = types.SimpleNamespace(load_subpastas_config=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        monkeypatch.setitem(sys.modules, "src.utils.subpastas_config", fake_module)
        called: list[str] = []
        real_makedirs = os.makedirs

        def fail_makedirs(path, exist_ok=False):
            called.append(path)
            # allow base creation, fail on defaults
            if path.endswith("DOCS") or path.endswith("ANEXOS"):
                raise OSError("nope")
            return real_makedirs(path, exist_ok=exist_ok)

        monkeypatch.setattr(os, "makedirs", fail_makedirs)  # type: ignore[assignment]

        base = tmp_path / "osfail"
        result = path_utils.ensure_subpastas(str(base))

        assert result is True
        assert called  # both attempts hit exception branches
    finally:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", orig)
        sys.modules.pop("src.utils.subpastas_config", None)


def test_ensure_subpastas_handles_os_error_in_final_loop(monkeypatch, tmp_path: Path) -> None:
    orig = path_utils.CLOUD_ONLY
    try:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", False)
        base = tmp_path / "final"
        calls: list[str] = []
        real_makedirs = os.makedirs

        def fail_makedirs(path, exist_ok=False):
            calls.append(path)
            if path.endswith("X"):
                raise OSError("fail")
            return real_makedirs(path, exist_ok=exist_ok)

        monkeypatch.setattr(os, "makedirs", fail_makedirs)  # type: ignore[assignment]

        result = path_utils.ensure_subpastas(str(base), nomes=["X"])

        assert result is True
        assert any(call.endswith("X") for call in calls)
    finally:
        monkeypatch.setattr(path_utils, "CLOUD_ONLY", orig)
