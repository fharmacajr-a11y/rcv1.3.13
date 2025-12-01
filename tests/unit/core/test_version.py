import os

import src.version as version


def test_app_version_constant_matches_dunder() -> None:
    assert version.APP_VERSION == version.__version__


def test_get_version_returns_default_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("RC_APP_VERSION", raising=False)

    assert version.get_version() == version.__version__


def test_get_version_respects_env_override(monkeypatch) -> None:
    monkeypatch.setenv("RC_APP_VERSION", "v9.9.9")

    assert version.get_version() == "v9.9.9"


def test_get_version_falls_back_on_getenv_failure(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(os, "getenv", _boom)

    assert version.get_version() == version.__version__
