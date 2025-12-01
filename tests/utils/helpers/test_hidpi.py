import sys
import types


def _inject_fake_ttk(monkeypatch, func):
    """Install fake ttkbootstrap.utility.enable_high_dpi_awareness for the test."""
    mod_util = types.ModuleType("ttkbootstrap.utility")
    mod_util.enable_high_dpi_awareness = func

    mod_ttk = types.ModuleType("ttkbootstrap")
    mod_ttk.utility = mod_util

    monkeypatch.setitem(sys.modules, "ttkbootstrap.utility", mod_util)
    monkeypatch.setitem(sys.modules, "ttkbootstrap", mod_ttk)


def test_configure_hidpi_support_noop_on_non_windows(monkeypatch):
    calls = []

    def fake_enable(*args, **kwargs):
        calls.append((args, kwargs))

    _inject_fake_ttk(monkeypatch, fake_enable)
    monkeypatch.setattr("platform.system", lambda: "Darwin")

    import src.utils.helpers.hidpi as hidpi

    hidpi.configure_hidpi_support()

    assert calls == []


def test_configure_hidpi_support_windows_calls_api(monkeypatch):
    calls = []

    def fake_enable(*args, **kwargs):
        calls.append((args, kwargs))

    _inject_fake_ttk(monkeypatch, fake_enable)
    monkeypatch.setattr("platform.system", lambda: "Windows")

    import src.utils.helpers.hidpi as hidpi

    hidpi.configure_hidpi_support(root=None)

    assert calls == [((), {})]


def test_configure_hidpi_support_windows_swallows_errors(monkeypatch):
    def failing_enable(*_args, **_kwargs):
        raise RuntimeError("boom")

    _inject_fake_ttk(monkeypatch, failing_enable)
    monkeypatch.setattr("platform.system", lambda: "Windows")

    import src.utils.helpers.hidpi as hidpi

    hidpi.configure_hidpi_support(root=None)  # should not raise


def test_configure_hidpi_support_linux_uses_detected_scaling(monkeypatch):
    calls = []

    def fake_enable(*args, **kwargs):
        calls.append((args, kwargs))

    _inject_fake_ttk(monkeypatch, fake_enable)
    monkeypatch.setattr("platform.system", lambda: "Linux")

    import src.utils.helpers.hidpi as hidpi

    fake_root = object()
    monkeypatch.setattr(hidpi, "_detect_linux_scaling", lambda root: 1.7)

    hidpi.configure_hidpi_support(root=fake_root)

    assert calls == [((fake_root, 1.7), {})]


def test_configure_hidpi_support_linux_uses_explicit_scaling(monkeypatch):
    calls = []

    def fake_enable(*args, **kwargs):
        calls.append((args, kwargs))

    _inject_fake_ttk(monkeypatch, fake_enable)
    monkeypatch.setattr("platform.system", lambda: "Linux")

    import src.utils.helpers.hidpi as hidpi

    fake_root = object()

    hidpi.configure_hidpi_support(root=fake_root, scaling=2.0)

    assert calls == [((fake_root, 2.0), {})]


def test_configure_hidpi_support_linux_without_root_no_call(monkeypatch):
    calls = []

    def fake_enable(*args, **kwargs):
        calls.append((args, kwargs))

    _inject_fake_ttk(monkeypatch, fake_enable)
    monkeypatch.setattr("platform.system", lambda: "Linux")

    import src.utils.helpers.hidpi as hidpi

    hidpi.configure_hidpi_support(root=None)

    assert calls == []


def test_configure_hidpi_support_import_failure(monkeypatch):
    # Force ImportError for ttkbootstrap.utility
    def fake_import(name, *args, **kwargs):
        if name == "ttkbootstrap.utility":
            raise ImportError("missing ttkbootstrap")
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr("platform.system", lambda: "Windows")

    import src.utils.helpers.hidpi as hidpi

    hidpi.configure_hidpi_support()  # should simply return without raising


def test_detect_linux_scaling_computes_expected_factor():
    class Root:
        def __init__(self, dpi):
            self._dpi = dpi

        def winfo_fpixels(self, _):
            return self._dpi

    import src.utils.helpers.hidpi as hidpi

    assert hidpi._detect_linux_scaling(Root(96)) == 1.0
    assert hidpi._detect_linux_scaling(Root(192)) == 2.0
    assert hidpi._detect_linux_scaling(Root(400)) == 3.0  # clamped and rounded


def test_detect_linux_scaling_fallback_on_error():
    class BadRoot:
        def winfo_fpixels(self, _):
            raise ValueError("oops")

    import src.utils.helpers.hidpi as hidpi

    assert hidpi._detect_linux_scaling(BadRoot()) == 1.0
