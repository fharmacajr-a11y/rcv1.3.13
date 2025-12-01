from __future__ import annotations

from pathlib import Path

import pytest

from src.utils import subpastas_config as sc


def test_flatten_handles_nested_dicts_and_lists() -> None:
    data = [
        "ROOT",
        {"A": ["B", {"C": ["D"]}]},
        {"EMPTY": []},
        {"NONE": None},
    ]
    result = sc._flatten(data)  # pyright: ignore[reportPrivateUsage]
    assert result == ["ROOT", "A/B", "A/C/D", "EMPTY", "NONE"]


def test_norm_removes_duplicates_and_backslashes() -> None:
    assert sc._norm(r"//a\\b//c/") == "a/b/c"
    assert sc._norm("") == ""


def test_flatten_accepts_dict_root() -> None:
    assert sc._flatten({"root": {"child": None}}) == ["root/child"]


def test_load_subpastas_config_with_explicit_file(tmp_path: Path) -> None:
    cfg_path = tmp_path / "subpastas.yml"
    cfg_path.write_text(
        """
SUBPASTAS:
  - SIFAP
  - {ANVISA: [child, child]}
  - {EXTRA: ''}
EXTRAS_VISIBLE:
  - [extra1, extra1]
  - {extra2: null}
""",
        encoding="utf-8",
    )

    sub, extras = sc.load_subpastas_config(cfg_path)

    assert sub == ["SIFAP", "ANVISA/child", "EXTRA"]
    assert extras == ["extra2"]


def test_load_subpastas_config_missing_file_returns_empty(tmp_path: Path) -> None:
    cfg_path = tmp_path / "does_not_exist.yml"
    sub, extras = sc.load_subpastas_config(cfg_path)
    assert sub == []
    assert extras == []


def test_load_subpastas_config_default_paths_without_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "exists", lambda self: False, raising=False)
    sub, extras = sc.load_subpastas_config()
    assert sub == []
    assert extras == []


def test_load_subpastas_config_io_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    cfg_path = tmp_path / "broken.yml"

    def fake_exists(path: Path) -> bool:
        return path == cfg_path

    def fake_open(self: Path, *args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(Path, "exists", fake_exists, raising=False)
    monkeypatch.setattr(Path, "open", fake_open, raising=False)

    sub, extras = sc.load_subpastas_config(cfg_path)

    assert sub == []
    assert extras == []
    assert any("subpastas.yml" in rec.message for rec in caplog.records)


def test_get_mandatory_subpastas_is_tuple_copy() -> None:
    mandatory = sc.get_mandatory_subpastas()
    assert mandatory == sc.MANDATORY_SUBPASTAS
    assert isinstance(mandatory, tuple)


def test_join_prefix_various_cases() -> None:
    assert sc.join_prefix("base/", "child", "/leaf/") == "base/child/leaf/"
    assert sc.join_prefix("base", "") == "base/"
    assert sc.join_prefix("", "only") == "only/"
