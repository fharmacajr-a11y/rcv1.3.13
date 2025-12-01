import os
import pytest

if os.environ.get("RC_RUN_GUI_TESTS") != "1":
    pytest.skip(
        "GUI tests pulados por padrão (defina RC_RUN_GUI_TESTS=1 para rodar).",
        allow_module_level=True,
    )


def test_placeholder_clientes_client_form() -> None:
    """Placeholder para teste legado de formulário de clientes (GUI)."""
    assert True
