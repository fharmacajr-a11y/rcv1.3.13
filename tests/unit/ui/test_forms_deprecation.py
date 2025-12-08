"""Testes para verificar que src.ui.forms emite DeprecationWarning quando usado."""

from __future__ import annotations

import warnings


def test_src_ui_forms_form_cliente_emits_deprecation_warning() -> None:
    """Acessar form_cliente via src.ui.forms deve emitir DeprecationWarning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Importar o módulo não deve emitir warning
        import src.ui.forms

        # Mas acessar form_cliente deve emitir
        _ = src.ui.forms.form_cliente

        # Verificar que warning foi emitido
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "src.ui.forms.form_cliente está deprecated" in str(w[0].message)
        assert "src.modules.clientes.forms.form_cliente" in str(w[0].message)


def test_src_ui_forms_module_import_does_not_emit_warning() -> None:
    """Apenas importar src.ui.forms (sem acessar atributos) não deve emitir warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        import src.ui.forms  # noqa: F401

        # Nenhum warning deve ser emitido apenas pela importação
        deprecation_warnings = [
            warning
            for warning in w
            if issubclass(warning.category, DeprecationWarning) and "src.ui.forms" in str(warning.message)
        ]
        assert len(deprecation_warnings) == 0
