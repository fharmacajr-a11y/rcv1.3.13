import os
import pytest

if os.environ.get("RC_RUN_GUI_TESTS") != "1":
    pytest.skip(
        "GUI tests de ui/components (Treeview) pulados por padrão (defina RC_RUN_GUI_TESTS=1 para rodar).",
        allow_module_level=True,
    )

# Placeholder: trazer casos reais de create_clients_treeview se/quando necessário.


def test_placeholder_ui_components_treeview() -> None:
    assert True
