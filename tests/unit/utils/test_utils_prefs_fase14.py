from __future__ import annotations

import json
import os
from pathlib import Path


import src.utils.prefs as prefs


def test_get_base_dir_uses_appdata(tmp_path, monkeypatch):
    # Importar a função original antes do monkeypatch da fixture
    import src.utils.prefs as prefs_module
    import importlib

    importlib.reload(prefs_module)

    appdata = tmp_path / "appdata"
    appdata.mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))
    # assegurar que branch Windows é usada
    base_dir = prefs_module._get_base_dir()
    expected = appdata / prefs_module.APP_FOLDER_NAME
    assert Path(base_dir) == expected
    assert expected.is_dir()


def test_get_base_dir_fallback_home(tmp_path, monkeypatch):
    # Importar a função original antes do monkeypatch da fixture
    import src.utils.prefs as prefs_module
    import importlib

    importlib.reload(prefs_module)

    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(os.path, "expanduser", lambda _: str(tmp_path / "home"))

    base_dir = prefs_module._get_base_dir()
    expected = tmp_path / "home" / f".{prefs_module.APP_FOLDER_NAME.lower()}"
    assert Path(base_dir) == expected
    assert expected.is_dir()


def test_load_columns_visibility_no_file(monkeypatch, tmp_path):
    monkeypatch.setattr(prefs, "_get_base_dir", lambda: str(tmp_path))
    monkeypatch.setattr(prefs, "HAS_FILELOCK", False)

    result = prefs.load_columns_visibility("user@example.com")
    assert result == {}


def test_load_columns_visibility_with_lock_and_corrupted_json(monkeypatch, tmp_path):
    monkeypatch.setattr(prefs, "_get_base_dir", lambda: str(tmp_path))
    monkeypatch.setattr(prefs, "HAS_FILELOCK", True)
    prefs_path = Path(prefs._prefs_path())
    prefs_path.write_text("{ invalid json }", encoding="utf-8")

    result = prefs.load_columns_visibility("user@example.com")
    assert result == {}


def test_save_columns_visibility_without_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(prefs, "_get_base_dir", lambda: str(tmp_path))
    monkeypatch.setattr(prefs, "HAS_FILELOCK", False)

    mapping = {"col1": True, "col2": False}
    prefs.save_columns_visibility("user@example.com", mapping)

    saved = json.loads(Path(prefs._prefs_path()).read_text(encoding="utf-8"))
    assert saved["user@example.com"] == mapping


def test_load_last_prefix_variants(monkeypatch, tmp_path):
    monkeypatch.setattr(prefs, "_get_base_dir", lambda: str(tmp_path))
    path = Path(prefs._browser_state_path())

    # sem arquivo
    assert prefs.load_last_prefix("k") == ""

    # com valor numérico vira string
    path.write_text(json.dumps({"k": 123}), encoding="utf-8")
    assert prefs.load_last_prefix("k") == "123"

    # json inválido devolve vazio
    path.write_text("bad json", encoding="utf-8")
    assert prefs.load_last_prefix("k") == ""


def test_save_last_prefix_persists(monkeypatch, tmp_path):
    monkeypatch.setattr(prefs, "_get_base_dir", lambda: str(tmp_path))

    prefs.save_last_prefix("folder", "abc/123")
    data = json.loads(Path(prefs._browser_state_path()).read_text(encoding="utf-8"))
    assert data["folder"] == "abc/123"


def test_load_browser_status_map_handles_cases(monkeypatch, tmp_path):
    monkeypatch.setattr(prefs, "_get_base_dir", lambda: str(tmp_path))
    status_path = Path(prefs._browser_status_path())

    # sem arquivo
    assert prefs.load_browser_status_map("k") == {}

    # json inválido
    status_path.write_text("{ bad", encoding="utf-8")
    assert prefs.load_browser_status_map("k") == {}

    # dict com tipos variados -> converte para str
    status_path.write_text(json.dumps({"k": {"a": 1, 2: 3}}), encoding="utf-8")
    assert prefs.load_browser_status_map("k") == {"a": "1", "2": "3"}


def test_save_browser_status_map(monkeypatch, tmp_path):
    monkeypatch.setattr(prefs, "_get_base_dir", lambda: str(tmp_path))

    mapping = {"root": "ok", "child": "open"}
    prefs.save_browser_status_map("k", mapping)

    saved = json.loads(Path(prefs._browser_status_path()).read_text(encoding="utf-8"))
    assert saved["k"] == mapping
