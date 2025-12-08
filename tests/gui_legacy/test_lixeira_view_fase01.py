"""LEGACY TEST - Lixeira GUI (Fase 01)"""

import os
import pytest

pytestmark = [pytest.mark.legacy_ui]

if os.environ.get("RC_RUN_GUI_TESTS") != "1":
    pytest.skip(
        "GUI tests pulados por padrão (defina RC_RUN_GUI_TESTS=1 para rodar).",
        allow_module_level=True,
    )


def test_placeholder_lixeira_view() -> None:
    """Placeholder para teste legado da Lixeira (GUI)."""
    assert True
