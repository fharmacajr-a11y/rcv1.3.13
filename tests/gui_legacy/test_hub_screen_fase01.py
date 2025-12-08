"""LEGACY TEST - Hub Screen GUI (Fase 01)

Este arquivo cobre a UI antiga do Hub.
Não faz parte da bateria de regressão atual; mantido apenas por referência.
"""

import os
import pytest

pytestmark = [
    pytest.mark.legacy_ui,
]

if os.environ.get("RC_RUN_GUI_TESTS") != "1":
    pytest.skip(
        "GUI tests pulados por padrão (defina RC_RUN_GUI_TESTS=1 para rodar).",
        allow_module_level=True,
    )


def test_placeholder_hub_screen() -> None:
    """Placeholder para teste legado da HubScreen (GUI)."""
    assert True
