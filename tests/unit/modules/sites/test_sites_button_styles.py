from __future__ import annotations

from src.modules.sites.views.sites_screen import SitesScreen


def test_sites_button_styles_by_group(tk_root_session):
    screen = SitesScreen(tk_root_session)

    blue = "info"
    gray = "secondary"

    def _has_style(buttons, expected_prefix: str) -> bool:
        return buttons and all((btn.cget("style") or "").lower().startswith(expected_prefix) for btn in buttons)

    assert _has_style(screen.empresa_buttons, blue)
    assert _has_style(screen.convenios_buttons, gray)
    assert _has_style(screen.anvisa_buttons, blue)
    assert _has_style(screen.farmacia_popular_buttons, gray)
    assert _has_style(screen.financas_buttons, blue)

    try:
        screen.destroy()
    except Exception:
        pass
