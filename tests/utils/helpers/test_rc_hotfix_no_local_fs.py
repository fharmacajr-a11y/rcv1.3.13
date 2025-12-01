from __future__ import annotations

import importlib
import os
from types import SimpleNamespace


def reload_module(monkeypatch):
    """Reload the module under test with a clean environment."""
    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)
    module = importlib.reload(importlib.import_module("src.utils.helpers.rc_hotfix_no_local_fs"))
    return module


def test_sets_env_and_creates_tmp_base(monkeypatch, tmp_path):
    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    module = reload_module(monkeypatch)

    assert os.environ["RC_NO_LOCAL_FS"] == "1"
    assert module.TMP_BASE.exists()
    assert module.TMP_BASE.is_dir()


def test_idempotent_when_flag_already_set(monkeypatch, tmp_path):
    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    reload_module(monkeypatch)

    assert os.environ["RC_NO_LOCAL_FS"] == "1"
    # Reimport again should not raise and keep same flag
    module_again = reload_module(monkeypatch)
    assert os.environ["RC_NO_LOCAL_FS"] == "1"
    assert module_again.TMP_BASE.exists()


def test_monkeypatch_config_paths_if_loaded(monkeypatch, tmp_path):
    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))

    # Fake config.paths module already imported
    fake_paths = SimpleNamespace()
    monkeypatch.setitem(
        importlib.sys.modules,
        "config.paths",
        fake_paths,
    )

    module = reload_module(monkeypatch)

    assert getattr(fake_paths, "CLOUD_ONLY", False) is True
    assert getattr(fake_paths, "DB_DIR").exists()
    assert getattr(fake_paths, "DOCS_DIR").exists()
    # TMP_BASE should match our tmp_path base
    assert module.TMP_BASE.parent == tmp_path


def test_handles_missing_config_paths(monkeypatch, tmp_path):
    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    # Ensure config.paths is not preloaded
    monkeypatch.delitem(importlib.sys.modules, "config.paths", raising=False)

    module = reload_module(monkeypatch)

    assert os.environ["RC_NO_LOCAL_FS"] == "1"
    assert module.TMP_BASE.exists()
