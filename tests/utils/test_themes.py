import importlib
import json
import os
import sys
import types


def reload_themes(monkeypatch, tmp_path, *, no_fs=True, default_theme="flatly", safe_mode=False):
    """Reload the themes module with controlled env/modules to isolate tests."""
    monkeypatch.setenv("RC_NO_LOCAL_FS", "1" if no_fs else "0")
    if default_theme is None:
        monkeypatch.delenv("RC_DEFAULT_THEME", raising=False)
    else:
        monkeypatch.setenv("RC_DEFAULT_THEME", default_theme)

    fake_cli = types.ModuleType("src.cli")

    def get_args():
        return types.SimpleNamespace(safe_mode=safe_mode)

    fake_cli.get_args = get_args
    monkeypatch.setitem(sys.modules, "src.cli", fake_cli)

    if not no_fs:
        config_module = types.ModuleType("config")
        config_paths = types.ModuleType("config.paths")
        config_paths.BASE_DIR = tmp_path
        config_module.paths = config_paths
        monkeypatch.setitem(sys.modules, "config", config_module)
        monkeypatch.setitem(sys.modules, "config.paths", config_paths)

    sys.modules.pop("src.utils.themes", None)
    import src.utils.themes as themes

    return importlib.reload(themes)


def test_load_theme_returns_default_in_safe_mode(monkeypatch, tmp_path):
    themes = reload_themes(monkeypatch, tmp_path, no_fs=True, safe_mode=True)
    themes._CACHED_THEME = "cached"

    assert themes.load_theme() == "default"
    assert themes._CACHED_THEME == "cached"  # safe-mode não mexe no cache


def test_load_theme_no_fs_uses_env_default_and_cache(monkeypatch, tmp_path):
    themes = reload_themes(monkeypatch, tmp_path, no_fs=True, default_theme="azure")

    assert themes.load_theme() == "azure"
    assert themes._CACHED_THEME == "azure"
    assert themes._CACHED_MTIME is None

    themes._CACHED_THEME = "cached-theme"
    assert themes.load_theme() == "cached-theme"


def test_load_theme_reads_from_disk_and_respects_force_reload(monkeypatch, tmp_path):
    themes = reload_themes(monkeypatch, tmp_path, no_fs=False, default_theme="flatly")
    config_path = themes.CONFIG_FILE
    assert config_path

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"theme": "dark"}, f)

    first = themes.load_theme(force_reload=True)
    first_mtime = themes._CACHED_MTIME
    assert first == "dark"
    assert first_mtime is not None

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"theme": "light"}, f)
    os.utime(config_path, (first_mtime + 1, first_mtime + 1))

    second = themes.load_theme(force_reload=True)
    assert second == "light"
    assert themes._CACHED_MTIME != first_mtime


def test_save_theme_no_fs_updates_cache_only(monkeypatch, tmp_path):
    themes = reload_themes(monkeypatch, tmp_path, no_fs=True, default_theme="flatly")

    themes.save_theme("custom")

    assert themes._CACHED_THEME == "custom"
    assert themes._CACHED_MTIME is None
    assert themes.CONFIG_FILE is None or not os.path.exists(themes.CONFIG_FILE)


def test_save_theme_persists_to_disk(monkeypatch, tmp_path):
    themes = reload_themes(monkeypatch, tmp_path, no_fs=False, default_theme="flatly")
    config_path = themes.CONFIG_FILE
    assert config_path

    themes.save_theme("midnight")

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["theme"] == "midnight"
    assert themes._CACHED_THEME == "midnight"
    assert themes._CACHED_MTIME == os.path.getmtime(config_path)

    themes._CACHED_THEME = None
    assert themes.load_theme(force_reload=True) == "midnight"


def test_toggle_theme_switches_and_updates_buttons(monkeypatch, tmp_path):
    themes = reload_themes(monkeypatch, tmp_path, no_fs=True, default_theme="flatly")
    style_calls = []

    class FakeStyle:
        def theme_use(self, name):
            style_calls.append(name)

    class FakeTb:
        def Style(self):
            return FakeStyle()

    themes.tb = FakeTb()

    class FakeButton:
        def __init__(self):
            self.bootstyles = []

        def configure(self, *, bootstyle):
            self.bootstyles.append(bootstyle)

    class FakeApp:
        def __init__(self):
            self.btn_limpar = FakeButton()
            self.btn_abrir = FakeButton()
            self.btn_subpastas = FakeButton()

    app = FakeApp()
    themes.save_theme(themes.DEFAULT_THEME)

    first = themes.toggle_theme(app)
    assert first == themes.ALT_THEME
    assert app.tema_atual == themes.ALT_THEME
    assert style_calls[-1] == themes.ALT_THEME
    assert app.btn_limpar.bootstyles[-1] == "secondary"
    assert app.btn_abrir.bootstyles[-1] == "secondary"
    assert app.btn_subpastas.bootstyles[-1] == "secondary"

    second = themes.toggle_theme(app)
    assert second == themes.DEFAULT_THEME
    assert style_calls[-1] == themes.DEFAULT_THEME
    assert app.btn_limpar.bootstyles[-1] == "danger"
    assert app.btn_abrir.bootstyles[-1] == "primary"
    assert app.btn_subpastas.bootstyles[-1] == "secondary"


def test_apply_theme_handles_missing_ttkbootstrap(monkeypatch, tmp_path):
    themes = reload_themes(monkeypatch, tmp_path, no_fs=True, default_theme="flatly")
    themes.tb = None

    themes.apply_theme(win=object(), theme="custom")  # deve ser no-op sem erro


def test_apply_theme_uses_style_when_available(monkeypatch, tmp_path):
    themes = reload_themes(monkeypatch, tmp_path, no_fs=True, default_theme="flatly")
    calls = []

    class FakeStyle:
        def theme_use(self, name):
            calls.append(name)

    class FakeTb:
        def Style(self):
            return FakeStyle()

    themes.tb = FakeTb()

    themes.apply_theme(win=object(), theme="custom")

    assert calls == ["custom"]
