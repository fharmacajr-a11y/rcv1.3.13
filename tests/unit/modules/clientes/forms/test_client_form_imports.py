# -*- coding: utf-8 -*-
"""
Round 14: Teste de importação do client_form.py
Este teste valida que o módulo pode ser importado sem erros,
exercitando todas as linhas de import e definições de tipo.
"""

import sys
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parents[5] / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Importar no nível do módulo para pytest-cov capturar
from src.modules.clientes.forms import client_form as client_form_mod  # noqa: E402
from src.modules.clientes.forms.client_form import form_cliente  # noqa: E402


def test_client_form_module_imports_successfully():
    """Valida que client_form.py pode ser importado sem erros."""
    # Módulo já importado no nível do módulo
    assert client_form_mod is not None
    assert hasattr(client_form_mod, "form_cliente")


def test_client_form_exports_expected_types():
    """Valida que client_form.py exporta os tipos ClientRow, FormPreset, EntryMap."""
    # Verificar tipos exportados
    assert hasattr(client_form_mod, "ClientRow")
    assert hasattr(client_form_mod, "FormPreset")
    assert hasattr(client_form_mod, "EntryMap")
    assert hasattr(client_form_mod, "UploadButtonRef")


def test_client_form_re_exports_helpers():
    """Valida que client_form.py re-exporta funções helper."""
    # Funções re-exportadas de _collect.py
    assert hasattr(client_form_mod, "_collect_values")

    # Funções re-exportadas de _dupes.py
    assert hasattr(client_form_mod, "has_cnpj_conflict")
    assert hasattr(client_form_mod, "has_razao_conflict")
    assert hasattr(client_form_mod, "ask_razao_confirm")
    assert hasattr(client_form_mod, "show_cnpj_warning_and_abort")

    # Funções re-exportadas de components/
    assert hasattr(client_form_mod, "apply_status_prefix")
    assert hasattr(client_form_mod, "STATUS_CHOICES")
    assert hasattr(client_form_mod, "STATUS_PREFIX_RE")

    # Funções re-exportadas de ui/
    assert hasattr(client_form_mod, "center_on_parent")


def test_client_form_logger_configured():
    """Valida que client_form.py configura logger corretamente."""
    assert hasattr(client_form_mod, "logger")
    assert hasattr(client_form_mod, "log")
    assert client_form_mod.logger is not None
    assert client_form_mod.log is not None
    assert client_form_mod.logger.name == "src.modules.clientes.forms.client_form"


def test_form_cliente_signature():
    """Valida assinatura da função form_cliente()."""
    import inspect

    sig = inspect.signature(form_cliente)
    params = list(sig.parameters.keys())

    assert "self" in params
    assert "row" in params
    assert "preset" in params

    # Verificar valores padrão
    assert sig.parameters["row"].default is None
    assert sig.parameters["preset"].default is None
