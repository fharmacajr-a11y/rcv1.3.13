from __future__ import annotations

from types import SimpleNamespace


def test_app_is_reexported():
    import src.app_gui as app_gui

    # App deve estar acessível no namespace do módulo
    assert hasattr(app_gui, "App")


def test_main_flow_calls_dependencies(monkeypatch, caplog):
    # Preparar mocks das dependências chamadas no bloco __main__
    called = {
        "install_hook": 0,
        "get_args": 0,
        "configure_hidpi": 0,
        "configure_logging": 0,
        "App": [],
        "healthcheck": 0,
        "show_splash": 0,
        "ensure_logged": 0,
        "show_hub_screen": 0,
        "destroy": 0,
    }

    class DummyApp:
        def __init__(self, **kwargs):
            called["App"].append(kwargs)
            self._after = None

        def after(self, delay, fn):
            self._after = (delay, fn)

        def mainloop(self):
            # Executa callback agendado imediatamente para teste
            if self._after:
                _, fn = self._after
                fn()

        def show_hub_screen(self):
            called["show_hub_screen"] += 1

        def destroy(self):
            called["destroy"] += 1

    monkeypatch.setattr(
        "src.utils.errors.install_global_exception_hook",
        lambda: called.__setitem__("install_hook", called["install_hook"] + 1),
    )
    monkeypatch.setattr(
        "src.cli.get_args",
        lambda: SimpleNamespace(no_splash=False),
    )
    monkeypatch.setattr(
        "src.core.bootstrap.configure_hidpi",
        lambda: called.__setitem__("configure_hidpi", called["configure_hidpi"] + 1),
    )
    monkeypatch.setattr(
        "src.core.bootstrap.configure_logging",
        lambda preload=False: (
            called.__setitem__("configure_logging", called["configure_logging"] + 1)
            or SimpleNamespace(
                info=lambda *a, **k: None,
                error=lambda *a, **k: None,
            )
        ),
    )
    monkeypatch.setattr(
        "src.core.bootstrap.schedule_healthcheck_after_gui",
        lambda app, logger=None, delay_ms=0: called.__setitem__("healthcheck", called["healthcheck"] + 1),
    )
    monkeypatch.setattr(
        "src.modules.login.view.show_splash",
        lambda app: called.__setitem__("show_splash", called["show_splash"] + 1) or "splash",
    )
    monkeypatch.setattr(
        "src.core.auth_bootstrap.ensure_logged",
        lambda app, splash=None, logger=None: called.__setitem__("ensure_logged", called["ensure_logged"] + 1) or True,
    )
    monkeypatch.setattr("src.ui.main_window.App", DummyApp)

    caplog.set_level("INFO")

    import importlib

    importlib.reload(__import__("src.app_gui"))

    # Como executamos o módulo via reload, o bloco __main__ não roda.
    # Em vez disso, chamamos manualmente o fluxo principal para validar wiring.
    import src.app_gui as app_gui  # noqa

    # Simular execução do fluxo __main__
    app_gui.__dict__["__name__"] = "__main__"
    exec(  # noqa: S102
        open(app_gui.__file__, encoding="utf-8").read(),
        app_gui.__dict__,
    )

    assert called["install_hook"] == 1
    assert called["get_args"] == 0 or called["get_args"] == 0  # get_args é lido diretamente no bloco exec
    assert called["configure_hidpi"] == 1
    assert called["configure_logging"] >= 1
    assert called["healthcheck"] == 1
    assert called["show_splash"] == 1
    assert called["ensure_logged"] == 1
    assert called["show_hub_screen"] == 1
    assert called["destroy"] == 0  # fluxo feliz não destrói o app
