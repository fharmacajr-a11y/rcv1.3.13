import os
import pytest

if os.environ.get("RC_RUN_GUI_TESTS") != "1":
    pytest.skip(
        "GUI tests pulados por padrão (defina RC_RUN_GUI_TESTS=1 para rodar).",
        allow_module_level=True,
    )


def test_placeholder_hub_screen() -> None:
    """Placeholder para teste legado da HubScreen (GUI)."""
    assert True
