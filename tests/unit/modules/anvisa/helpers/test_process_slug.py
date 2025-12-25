# -*- coding: utf-8 -*-
"""Testes unitários para helpers/process_slug.py (funções puras).

Testa slugificação de nomes de processos ANVISA:
- Remoção de acentos
- Conversão para minúsculas
- Substituição de espaços/caracteres especiais por underscore
- Normalização de underscores múltiplos
- Casos de borda (strings vazias, None-like, Unicode)
"""

from __future__ import annotations

from typing import cast

from src.modules.anvisa.helpers.process_slug import (
    get_process_slug,
    slugify_process,
    PROCESS_SLUGS,
)
from src.modules.anvisa.constants import REQUEST_TYPES, RequestTypeStr


class TestSlugifyProcess:
    """Testes para slugify_process() - função pura de slugificação."""

    def test_basic_slug_no_accents(self):
        """Testa slugificação básica sem acentos."""
        assert slugify_process("Alteracao de RT") == "alteracao_de_rt"
        assert slugify_process("Associacao ao SNGPC") == "associacao_ao_sngpc"

    def test_slug_with_accents(self):
        """Testa remoção de acentos (NFD + decomposição)."""
        assert slugify_process("Alteração do Responsável Legal") == "alteracao_do_responsavel_legal"
        assert slugify_process("Associação ao SNGPC") == "associacao_ao_sngpc"
        assert slugify_process("Razão Social") == "razao_social"

    def test_slug_uppercase_to_lowercase(self):
        """Testa conversão para minúsculas."""
        assert slugify_process("ALTERAÇÃO DE RT") == "alteracao_de_rt"
        assert slugify_process("MiXeD CaSe NaMe") == "mixed_case_name"

    def test_slug_special_characters(self):
        """Testa substituição de caracteres especiais por underscore."""
        assert slugify_process("Nome-com-hífens") == "nome_com_hifens"
        assert slugify_process("Nome.com.pontos") == "nome_com_pontos"
        assert slugify_process("Nome com (parênteses)") == "nome_com_parenteses"
        assert slugify_process("Nome@especial#teste") == "nome_especial_teste"

    def test_slug_multiple_spaces(self):
        """Testa normalização de espaços múltiplos."""
        assert slugify_process("Alteração    do   Responsável") == "alteracao_do_responsavel"
        assert slugify_process("Nome  com     espaços") == "nome_com_espacos"

    def test_slug_leading_trailing_spaces(self):
        """Testa remoção de espaços nas extremidades."""
        assert slugify_process("  Alteração de RT  ") == "alteracao_de_rt"
        assert slugify_process("\t\nNome com tabs\n\t") == "nome_com_tabs"

    def test_slug_multiple_underscores(self):
        """Testa remoção de underscores duplicados."""
        # Múltiplos espaços/caracteres especiais geram underscores múltiplos internamente
        assert slugify_process("Nome --- com --- separadores") == "nome_com_separadores"

    def test_slug_empty_string(self):
        """Testa string vazia."""
        assert slugify_process("") == ""

    def test_slug_only_special_characters(self):
        """Testa string com apenas caracteres especiais."""
        assert slugify_process("@#$%^&*()") == ""
        assert slugify_process("---") == ""

    def test_slug_numeric_characters(self):
        """Testa que números são preservados."""
        assert slugify_process("Processo 123") == "processo_123"
        assert slugify_process("Versão 2.0") == "versao_2_0"

    def test_slug_unicode_special_cases(self):
        """Testa casos especiais de Unicode."""
        assert slugify_process("Café com açúcar") == "cafe_com_acucar"
        assert slugify_process("Ñoño") == "nono"
        # ß não se decompõe com NFD, permanece e é removido por não ser a-z
        assert slugify_process("Strauß") == "strau"

    def test_slug_all_official_request_types(self):
        """Testa que todos os tipos oficiais de REQUEST_TYPES geram slugs válidos."""
        for request_type in REQUEST_TYPES:
            slug = slugify_process(request_type)
            # Deve gerar slug não vazio
            assert slug
            # Deve conter apenas lowercase, números e underscores
            assert all(c.islower() or c.isdigit() or c == "_" for c in slug)
            # Não deve ter underscores nas extremidades
            assert not slug.startswith("_")
            assert not slug.endswith("_")
            # Não deve ter underscores duplicados
            assert "__" not in slug


class TestGetProcessSlug:
    """Testes para get_process_slug() - versão com cache."""

    def test_get_slug_uses_cache_for_official_types(self):
        """Testa que tipos oficiais usam cache PROCESS_SLUGS."""
        for request_type in REQUEST_TYPES:
            slug = get_process_slug(request_type)
            # Deve estar no cache
            assert slug == PROCESS_SLUGS[request_type]
            # Deve ser idêntico ao resultado de slugify_process
            assert slug == slugify_process(request_type)

    def test_get_slug_fallback_for_unknown_types(self):
        """Testa fallback para tipos não oficiais."""
        slug = get_process_slug("Tipo Customizado Não Oficial")
        assert slug == "tipo_customizado_nao_oficial"
        # Não deve estar no cache
        assert "Tipo Customizado Não Oficial" not in PROCESS_SLUGS

    def test_get_slug_empty_string(self):
        """Testa get_process_slug com string vazia."""
        assert get_process_slug("") == ""


class TestProcessSlugsCache:
    """Testes para PROCESS_SLUGS - cache pré-gerado."""

    def test_cache_contains_all_official_types(self):
        """Testa que cache contém todos os 6 tipos oficiais."""
        assert len(PROCESS_SLUGS) == len(REQUEST_TYPES)
        for request_type in REQUEST_TYPES:
            assert request_type in PROCESS_SLUGS

    def test_cache_values_are_valid_slugs(self):
        """Testa que valores do cache são slugs válidos."""
        for slug in PROCESS_SLUGS.values():
            # Não vazio
            assert slug
            # Apenas lowercase, números, underscores
            assert all(c.islower() or c.isdigit() or c == "_" for c in slug)
            # Sem underscores nas extremidades
            assert not slug.startswith("_")
            assert not slug.endswith("_")
            # Sem underscores duplicados
            assert "__" not in slug

    def test_cache_specific_values(self):
        """Testa alguns mapeamentos específicos esperados."""
        expected_mappings = {
            "Alteração do Responsável Legal": "alteracao_do_responsavel_legal",
            "Alteração do Responsável Técnico": "alteracao_do_responsavel_tecnico",
            "Alteração da Razão Social": "alteracao_da_razao_social",
            "Associação ao SNGPC": "associacao_ao_sngpc",
            "Alteração de Porte": "alteracao_de_porte",
            "Cancelamento de AFE": "cancelamento_de_afe",
        }

        for request_type, expected_slug in expected_mappings.items():
            # cast: request_type é uma string do dict, mas sabemos que é um RequestTypeStr válido
            assert PROCESS_SLUGS[cast(RequestTypeStr, request_type)] == expected_slug
