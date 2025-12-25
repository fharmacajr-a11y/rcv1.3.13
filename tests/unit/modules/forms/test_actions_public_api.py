# -*- coding: utf-8 -*-
"""Testes unitários para API pública de actions (lazy imports e re-exports).

Cobertura:
- Funções re-exportadas apontam para implementação correta
- __getattr__("SubpastaDialog") retorna classe (lazy import)
- __getattr__ inválido levanta AttributeError
"""

from __future__ import annotations

import pytest


class TestPublicAPI:
    """Testes para API pública de src.modules.forms.actions."""

    def test_functions_exported_correctly(self):
        """Funções públicas devem apontar para implementação em actions_impl."""
        from src.modules.forms import actions
        from src.modules.forms import actions_impl

        # Verificar que funções são as mesmas (identidade)
        assert actions.preencher_via_pasta is actions_impl.preencher_via_pasta
        assert actions.salvar_e_enviar_para_supabase is actions_impl.salvar_e_enviar_para_supabase
        assert actions.list_storage_objects is actions_impl.list_storage_objects
        assert actions.download_file is actions_impl.download_file
        assert actions.salvar_e_upload_docs is actions_impl.salvar_e_upload_docs

    def test_lazy_import_subpasta_dialog_returns_class(self):
        """__getattr__("SubpastaDialog") deve retornar a classe via lazy import."""
        from src.modules.forms import actions

        # ACT - lazy import dispara ao acessar atributo
        subpasta_dialog = actions.SubpastaDialog

        # ASSERT - deve ser uma classe
        assert subpasta_dialog is not None
        assert callable(subpasta_dialog)  # Classe é callable
        # Não vamos instanciar (precisa de parent Tk), só verificar que foi importado

    def test_getattr_invalid_attribute_raises_error(self):
        """__getattr__ com nome inválido deve levantar AttributeError."""
        from src.modules.forms import actions

        with pytest.raises(AttributeError, match="has no attribute 'InvalidAttribute'"):
            _ = actions.InvalidAttribute  # type: ignore[attr-defined]


class TestActionsImplLazyImport:
    """Testes para __getattr__ em actions_impl.py."""

    def test_actions_impl_lazy_import_subpasta_dialog(self):
        """actions_impl.__getattr__("SubpastaDialog") deve retornar classe."""
        from src.modules.forms import actions_impl

        # ACT
        subpasta_dialog = actions_impl.SubpastaDialog

        # ASSERT
        assert subpasta_dialog is not None
        assert callable(subpasta_dialog)

    def test_actions_impl_getattr_invalid_raises_error(self):
        """actions_impl.__getattr__ com nome inválido deve levantar AttributeError."""
        from src.modules.forms import actions_impl

        with pytest.raises(AttributeError, match="has no attribute 'NonExistent'"):
            _ = actions_impl.NonExistent  # type: ignore[attr-defined]
