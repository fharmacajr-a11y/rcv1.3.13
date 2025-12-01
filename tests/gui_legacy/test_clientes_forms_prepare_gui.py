import os
import pytest

if os.environ.get("RC_RUN_GUI_TESTS") != "1":
    pytest.skip(
        "GUI tests de clientes/forms pulados por padrão (defina RC_RUN_GUI_TESTS=1 para rodar).",
        allow_module_level=True,
    )

# Placeholder: trazer casos reais de prepare_payload gui se/quando necessário.


def test_placeholder_clientes_forms_prepare_gui() -> None:
    assert True
