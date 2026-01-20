"""DEPRECATED: Testes do ThemeManager legado (sistema de 14 temas).

MICROFASE 24: Estes testes cobrem o módulo src.utils.theme_manager (legado).
Mantidos para garantir compatibilidade com código que ainda não foi migrado.

Novos testes devem cobrir src.ui.theme_manager (CustomTkinter).
"""

from __future__ import annotations

import src.utils.theme_manager as tm


class DummyWindow:
    def __init__(self, exists: bool = True) -> None:
        self._exists = exists

    def winfo_exists(self) -> bool:
        return self._exists


def test_theme_property_uses_load_once(monkeypatch) -> None:
    calls: list[str] = []

    def fake_load() -> str:
        calls.append("load")
        return "darkly"

    manager = tm.ThemeManager()
    monkeypatch.setattr(tm.themes, "load_theme", fake_load)

    assert manager.theme == "darkly"
    assert manager.theme == "darkly"
    assert calls == ["load"]  # cache evita nova leitura


def test_register_window_applies_theme_and_handles_errors(monkeypatch) -> None:
    applied: list[tuple[object, str]] = []
    manager = tm.ThemeManager()
    monkeypatch.setattr(tm.themes, "load_theme", lambda: "flatly")
    monkeypatch.setattr(tm.themes, "apply_theme", lambda win, theme: applied.append((win, theme)))
    win_ok = object()

    manager.register_window(win_ok)

    assert win_ok in manager._windows  # noqa: SLF001 (verificando cache interno)
    assert applied == [(win_ok, "flatly")]

    # agora forca uma excecao e garante que nao propaga
    def boom_apply(win, theme):
        raise RuntimeError("boom")

    monkeypatch.setattr(tm.themes, "apply_theme", boom_apply)
    win_fail = object()
    manager.register_window(win_fail)  # deve atualizar set sem levantar
    assert win_fail in manager._windows


def test_unregister_window_removes_reference(monkeypatch) -> None:
    manager = tm.ThemeManager()
    win = object()
    manager._windows = {win}  # noqa: SLF001

    manager.unregister_window(win)

    assert win not in manager._windows


def test_apply_all_applies_only_existing_and_notifies(monkeypatch) -> None:
    applied: list[tuple[object, str]] = []
    notified: list[str] = []
    manager = tm.ThemeManager()
    manager._theme = "custom-theme"  # noqa: SLF001
    win_alive = DummyWindow(True)
    win_dead = DummyWindow(False)
    manager._windows = {win_alive, win_dead}  # noqa: SLF001

    monkeypatch.setattr(tm.themes, "apply_theme", lambda win, theme: applied.append((win, theme)))
    manager.add_listener(lambda t: notified.append(t))

    def bad_listener(theme: str) -> None:
        notified.append(f"bad:{theme}")
        raise RuntimeError("listener boom")

    manager.add_listener(bad_listener)

    manager.apply_all()

    assert win_dead not in manager._windows  # janela inexistente removida
    assert applied == [(win_alive, "custom-theme")]
    assert "custom-theme" in notified
    assert "bad:custom-theme" in notified  # listener com erro tratado


def test_apply_all_handles_apply_theme_errors(monkeypatch) -> None:
    manager = tm.ThemeManager()
    manager._theme = "custom"  # noqa: SLF001
    win = DummyWindow(True)
    manager._windows = {win}  # noqa: SLF001

    def fail_apply(win, theme):
        raise RuntimeError("boom")

    monkeypatch.setattr(tm.themes, "apply_theme", fail_apply)

    # deve engolir excecao e seguir sem remover janela
    manager.apply_all()
    assert win in manager._windows


def test_set_theme_saves_and_applies(monkeypatch) -> None:
    saved: list[str] = []
    applied: list[str] = []
    manager = tm.ThemeManager()

    monkeypatch.setattr(tm.themes, "save_theme", lambda theme: saved.append(theme))
    monkeypatch.setattr(manager, "apply_all", lambda: applied.append("called"))

    manager.set_theme("darkly")

    assert saved == ["darkly"]
    assert manager.theme == "darkly"
    assert applied == ["called"]


def test_set_theme_updates_cache_even_when_save_fails(monkeypatch) -> None:
    applied: list[str] = []
    manager = tm.ThemeManager()

    def fail_save(theme: str) -> None:
        raise RuntimeError("disk error")

    monkeypatch.setattr(tm.themes, "save_theme", fail_save)
    monkeypatch.setattr(manager, "apply_all", lambda: applied.append("called"))

    manager.set_theme("alt-theme")

    assert manager.theme == "alt-theme"
    assert applied == ["called"]


def test_toggle_updates_theme_and_applies(monkeypatch) -> None:
    applied: list[str] = []
    manager = tm.ThemeManager()

    monkeypatch.setattr(tm.themes, "toggle_theme", lambda: "swapped")
    monkeypatch.setattr(manager, "apply_all", lambda: applied.append("called"))

    result = manager.toggle()

    assert result == "swapped"
    assert manager.theme == "swapped"
    assert applied == ["called"]


def test_remove_listener_swallows_missing() -> None:
    manager = tm.ThemeManager()

    def listener(theme: str) -> None:
        raise RuntimeError(theme)

    manager.add_listener(listener)
    manager.remove_listener(listener)

    # remover novamente deve ser silencioso
    manager.remove_listener(listener)
    assert listener not in manager._listeners  # noqa: SLF001
