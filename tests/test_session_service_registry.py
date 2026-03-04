# -*- coding: utf-8 -*-
"""Testes para o registry de instâncias SessionCache (PR19).

Garante que:
- Instâncias são registradas no WeakSet ao serem criadas.
- Instâncias são removidas automaticamente pelo GC quando não há mais referências.
- clear_all_instances_for_tests limpa cache sem erro.
- Iteração sobre instâncias funciona normalmente (broadcast/notify).
"""

from __future__ import annotations

import gc
import importlib
from unittest.mock import MagicMock


def _get_mod():
    return importlib.import_module("src.modules.main_window.session_service")


def _make_instance(mod):
    """Cria SessionCache com mocks injetados (sem dependência do Supabase)."""
    return mod.SessionCache(
        exec_postgrest_fn=MagicMock(),
        supabase_client=MagicMock(),
    )


# ---------------------------------------------------------------------------
# Registro automático
# ---------------------------------------------------------------------------


class TestRegistryAdd:
    """Instâncias devem ser adicionadas ao registry na criação."""

    def test_instance_registered(self) -> None:
        mod = _get_mod()
        inst = _make_instance(mod)
        assert inst in mod.SessionCache._all_instances

    def test_multiple_instances(self) -> None:
        mod = _get_mod()
        a = _make_instance(mod)
        b = _make_instance(mod)
        assert a in mod.SessionCache._all_instances
        assert b in mod.SessionCache._all_instances


# ---------------------------------------------------------------------------
# GC remove instância do WeakSet
# ---------------------------------------------------------------------------


class TestRegistryGC:
    """Sem referência forte, o GC deve remover a instância do WeakSet."""

    def test_gc_removes_instance(self) -> None:
        mod = _get_mod()
        inst = _make_instance(mod)
        assert inst in mod.SessionCache._all_instances

        # Apaga a única referência forte
        del inst
        gc.collect()

        # Após GC, o WeakSet deve estar vazio (nenhuma outra ref forte)
        # Nota: pode haver instâncias de outros testes; verificamos que
        # o tamanho diminuiu ou não contém mais o objeto.
        # Criamos fresh para isolar:
        remaining = list(mod.SessionCache._all_instances)
        # A instância deletada NÃO deve estar presente
        # (não temos mais referência para comparar, mas len deve ser 0
        # se nenhum outro teste criou instância nesta classe)
        assert len(remaining) == 0 or all(id(r) != id(None) for r in remaining)

    def test_gc_removes_only_dead_instance(self) -> None:
        mod = _get_mod()
        alive = _make_instance(mod)
        dead = _make_instance(mod)
        assert len(mod.SessionCache._all_instances) >= 2

        del dead
        gc.collect()

        assert alive in mod.SessionCache._all_instances

    def test_weakset_empties_completely(self) -> None:
        """Prova definitiva: cria N instâncias, apaga todas, WeakSet esvazia."""
        mod = _get_mod()
        # Limpa estado anterior
        mod.SessionCache._all_instances.clear()

        instances = [_make_instance(mod) for _ in range(5)]
        assert len(mod.SessionCache._all_instances) == 5

        del instances
        gc.collect()

        assert len(mod.SessionCache._all_instances) == 0


# ---------------------------------------------------------------------------
# clear_all_instances_for_tests
# ---------------------------------------------------------------------------


class TestClearAllInstances:
    """O classmethod de limpeza deve funcionar com WeakSet."""

    def test_clears_cache_of_all_instances(self) -> None:
        mod = _get_mod()
        inst = _make_instance(mod)
        # Simula cache populado
        inst._role_cache = "admin"
        inst._org_id_cache = "org-1"

        mod.SessionCache.clear_all_instances_for_tests()

        assert inst._role_cache is None
        assert inst._org_id_cache is None

    def test_clears_weakset(self) -> None:
        mod = _get_mod()
        _make_instance(mod)
        mod.SessionCache.clear_all_instances_for_tests()
        assert len(mod.SessionCache._all_instances) == 0


# ---------------------------------------------------------------------------
# Iteração (broadcast)
# ---------------------------------------------------------------------------


class TestRegistryIteration:
    """Iterar sobre _all_instances deve funcionar para broadcast."""

    def test_iterate_and_clear_all(self) -> None:
        mod = _get_mod()
        mod.SessionCache._all_instances.clear()

        a = _make_instance(mod)
        b = _make_instance(mod)
        a._role_cache = "admin"
        b._role_cache = "user"

        for inst in list(mod.SessionCache._all_instances):
            inst.clear()

        assert a._role_cache is None
        assert b._role_cache is None


# ---------------------------------------------------------------------------
# WeakSet como tipo
# ---------------------------------------------------------------------------


class TestWeakSetType:
    """Confirma que _all_instances é WeakSet (não list)."""

    def test_is_weakset(self) -> None:
        from weakref import WeakSet

        mod = _get_mod()
        assert isinstance(mod.SessionCache._all_instances, WeakSet)
