from __future__ import annotations

import sys
from types import SimpleNamespace


def test_reexports_public_members(monkeypatch):
    # Mock submodules to expose known symbols
    monkeypatch.setitem(
        sys.modules,
        "src.utils.file_utils.bytes_utils",
        SimpleNamespace(BYTES_FN="bytes_fn"),
    )
    monkeypatch.setitem(
        sys.modules,
        "src.utils.file_utils.path_utils",
        SimpleNamespace(PATH_FN="path_fn"),
    )
    monkeypatch.setitem(
        sys.modules,
        "src.utils.file_utils.zip_utils",
        SimpleNamespace(ZIP_FN="zip_fn"),
    )

    import importlib

    module = importlib.reload(importlib.import_module("src.utils.file_utils.file_utils"))

    # __all__ should include the mocked names and exclude dunders
    assert "BYTES_FN" in module.__all__
    assert "PATH_FN" in module.__all__
    assert "ZIP_FN" in module.__all__
    assert not any(name.startswith("__") for name in module.__all__)
