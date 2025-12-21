# -*- coding: utf-8 -*-
"""
Testes de cobertura para src/utils/validators.py
Objetivo: atingir ≥85% de cobertura com testes sólidos de edge cases.
"""

import pytest
import sqlite3
from src.utils.validators import (
    only_digits,
    normalize_text,
    normalize_whatsapp,
    is_valid_whatsapp_br,
    normalize_cnpj,
    is_valid_cnpj,
    validate_required_fields,
    check_duplicates,
    validate_cliente_payload,
)


# ==================== only_digits ====================


class TestOnlyDigits:
    """Testa extração de apenas dígitos de strings."""

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("123-456-789", "123456789"),
            ("(11) 98765-4321", "11987654321"),
            ("ABC123DEF456", "123456"),
            ("", ""),
            ("NoDigitsHere!", ""),
            ("  123  ", "123"),
            ("R$ 1.234,56", "123456"),
        ],
    )
    def test_only_digits_various_inputs(self, input_str, expected):
        """Testa only_digits com vários formatos de entrada."""
        assert only_digits(input_str) == expected

    def test_only_digits_none_input(self):
        """Testa only_digits com None."""
        assert only_digits(None) == ""


# ==================== normalize_text ====================


class TestNormalizeText:
    """Testa normalização de texto (strip)."""

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("  texto com espaços  ", "texto com espaços"),
            ("semEspacos", "semEspacos"),
            ("", ""),
            ("   ", ""),
            ("\t\ntabs e newlines\n\t", "tabs e newlines"),
        ],
    )
    def test_normalize_text_various(self, input_str, expected):
        """Testa normalize_text com vários inputs."""
        assert normalize_text(input_str) == expected

    def test_normalize_text_none(self):
        """Testa normalize_text com None."""
        assert normalize_text(None) == ""


# ==================== normalize_whatsapp ====================


class TestNormalizeWhatsapp:
    """Testa normalização de números WhatsApp."""

    @pytest.mark.parametrize(
        "input_num,expected",
        [
            ("11987654321", "5511987654321"),  # adiciona 55
            ("5511987654321", "5511987654321"),  # já tem 55
            ("(11) 98765-4321", "5511987654321"),  # formatado
            ("21987654321", "5521987654321"),  # outro DDD
            ("", ""),  # vazio
            ("ABC123", "55123"),  # remove letras e adiciona 55
        ],
    )
    def test_normalize_whatsapp_various(self, input_num, expected):
        """Testa normalize_whatsapp com vários formatos."""
        assert normalize_whatsapp(input_num) == expected

    def test_normalize_whatsapp_none(self):
        """Testa normalize_whatsapp com None."""
        assert normalize_whatsapp(None) == ""

    def test_normalize_whatsapp_custom_country_code(self):
        """Testa normalize_whatsapp com código de país customizado."""
        result = normalize_whatsapp("987654321", country_code="1")
        assert result == "1987654321"


# ==================== is_valid_whatsapp_br ====================


class TestIsValidWhatsappBr:
    """Testa validação de WhatsApp brasileiro."""

    @pytest.mark.parametrize(
        "input_num,expected",
        [
            ("11987654321", True),  # 13 dígitos após normalizar (55+11+9dígitos)
            ("1133334444", True),  # 12 dígitos (55+10)
            ("5511987654321", True),  # já normalizado, 13 dígitos
            ("551133334444", True),  # já normalizado, 12 dígitos
            ("119876543", False),  # muito curto
            ("119876543210", False),  # muito longo (14 após 55)
            ("", False),  # vazio
            ("ABC", False),  # sem dígitos
        ],
    )
    def test_is_valid_whatsapp_br_various(self, input_num, expected):
        """Testa is_valid_whatsapp_br com vários inputs."""
        assert is_valid_whatsapp_br(input_num) == expected

    def test_is_valid_whatsapp_br_none(self):
        """Testa is_valid_whatsapp_br com None."""
        assert is_valid_whatsapp_br(None) is False

    # TEST-002: Casos adicionais de WhatsApp
    @pytest.mark.parametrize(
        "input_num,expected",
        [
            # Com prefixo +55
            ("+5511987654321", True),  # com +55
            ("+55 11 98765-4321", True),  # com +55 e formatação
            ("+55 (11) 98765-4321", True),  # com +55 e parênteses
            # Com 55 mas sem +
            ("55 11 98765-4321", True),
            ("55 (11) 98765-4321", True),
            # Sem DDI (55)
            ("(11) 98765-4321", True),  # será normalizado com 55
            ("11 98765-4321", True),
            ("21 98765-4321", True),  # RJ
            ("47 98765-4321", True),  # SC
            # Com espaços e hífens variados
            ("11-98765-4321", True),
            ("11 9 8765 4321", True),
            ("  11987654321  ", True),  # com espaços nas pontas
            # Números de linha fixa (10 dígitos + 55)
            ("1133334444", True),  # fixo SP
            ("(21) 3333-4444", True),  # fixo RJ
            # Inválidos
            ("11 9876", False),  # muito curto
            ("11 98765 4321 9999", False),  # muito longo (após normalizar)
        ],
    )
    def test_is_valid_whatsapp_br_test002_additional_cases(self, input_num, expected):
        """TEST-002: Testes adicionais de WhatsApp com vários formatos."""
        assert is_valid_whatsapp_br(input_num) == expected


# ==================== normalize_cnpj ====================


class TestNormalizeCnpj:
    """Testa normalização de CNPJ."""

    @pytest.mark.parametrize(
        "input_cnpj,expected",
        [
            ("12.345.678/0001-95", "12345678000195"),
            ("12345678000195", "12345678000195"),
            ("12 345 678 0001 95", "12345678000195"),
            ("", ""),
            ("ABC12345678000195", "12345678000195"),
        ],
    )
    def test_normalize_cnpj_various(self, input_cnpj, expected):
        """Testa normalize_cnpj com vários formatos."""
        assert normalize_cnpj(input_cnpj) == expected

    def test_normalize_cnpj_none(self):
        """Testa normalize_cnpj com None."""
        assert normalize_cnpj(None) == ""


# ==================== is_valid_cnpj ====================


class TestIsValidCnpj:
    """Testa validação de CNPJ com dígitos verificadores."""

    @pytest.mark.parametrize(
        "input_cnpj,expected",
        [
            # CNPJs válidos (dígitos verificadores corretos)
            ("11.222.333/0001-65", True),  # calculado corretamente
            ("11222333000165", True),  # sem formatação
            ("12.345.678/0001-10", True),  # outro CNPJ válido
            # CNPJs inválidos
            ("11.222.333/0001-99", False),  # dígitos errados
            ("12345678000195", False),  # dígitos incorretos
            ("00000000000000", False),  # sequência repetida
            ("11111111111111", False),  # sequência repetida
            ("123", False),  # muito curto
            ("123456789012345", False),  # muito longo
            ("", False),  # vazio
            ("ABCD1234567890", False),  # com letras
        ],
    )
    def test_is_valid_cnpj_various(self, input_cnpj, expected):
        """Testa is_valid_cnpj com CNPJs válidos e inválidos."""
        assert is_valid_cnpj(input_cnpj) == expected

    def test_is_valid_cnpj_none(self):
        """Testa is_valid_cnpj com None."""
        assert is_valid_cnpj(None) is False

    # TEST-002: Casos adicionais de CNPJ
    @pytest.mark.parametrize(
        "input_cnpj,expected",
        [
            # CNPJs válidos conhecidos (dos testes existentes)
            ("11.222.333/0001-65", True),  # já testado, confirmado válido
            ("12.345.678/0001-10", True),  # já testado, confirmado válido
            # Testando formatação variada dos mesmos CNPJs válidos
            ("11 222 333 0001 65", True),  # espaços
            ("11-222-333-0001-65", True),  # hífens
            ("12 345 678 0001 10", True),  # espaços
            ("12-345-678-0001-10", True),  # hífens
            # Dígitos verificadores incorretos (mesmo base, DV errado)
            ("11.222.333/0001-99", False),  # DV errado
            ("12.345.678/0001-99", False),  # DV errado
            # Sequências que devem ser rejeitadas (mais casos)
            ("22222222222222", False),
            ("55555555555555", False),
            ("77777777777777", False),
            ("88888888888888", False),
            # Tamanhos incorretos
            ("1122233300016", False),  # 13 dígitos
            ("112223330001655", False),  # 15 dígitos
            ("123456789", False),  # muito curto
        ],
    )
    def test_is_valid_cnpj_test002_additional_cases(self, input_cnpj, expected):
        """TEST-002: Testes adicionais de CNPJ - formatação e edge cases."""
        assert is_valid_cnpj(input_cnpj) == expected


# ==================== validate_required_fields ====================


class TestValidateRequiredFields:
    """Testa validação de campos obrigatórios."""

    def test_validate_required_fields_all_present(self):
        """Testa quando todos os campos obrigatórios estão presentes."""
        data = {"nome": "João", "email": "joao@example.com", "telefone": "123456"}
        required = ["nome", "email"]
        errors = validate_required_fields(data, required)
        assert errors == {}

    def test_validate_required_fields_missing_fields(self):
        """Testa quando há campos obrigatórios faltando."""
        data = {"nome": "", "email": None, "telefone": "123456"}
        required = ["nome", "email", "cpf"]
        errors = validate_required_fields(data, required)
        assert "nome" in errors
        assert "email" in errors
        assert "cpf" in errors
        assert errors["nome"] == "Campo obrigatório."

    def test_validate_required_fields_whitespace_only(self):
        """Testa campos com apenas espaços em branco."""
        data = {"nome": "   ", "email": "\t\n"}
        required = ["nome", "email"]
        errors = validate_required_fields(data, required)
        assert "nome" in errors
        assert "email" in errors

    def test_validate_required_fields_empty_required_list(self):
        """Testa com lista de campos obrigatórios vazia."""
        data = {"nome": "João"}
        required = []
        errors = validate_required_fields(data, required)
        assert errors == {}


# ==================== check_duplicates ====================


class TestCheckDuplicates:
    """Testa verificação de duplicatas."""

    def test_check_duplicates_no_duplicates_in_memory(self):
        """Testa check_duplicates sem duplicatas usando existing."""
        existing = [
            {"ID": 1, "CNPJ": "11222333000181", "RAZAO_SOCIAL": "Empresa A"},
            {"ID": 2, "CNPJ": "22333444000182", "RAZAO_SOCIAL": "Empresa B"},
        ]
        result = check_duplicates(
            cnpj="33444555000183",
            razao_social="Empresa C",
            existing=existing,
        )
        assert result["has_any"] is False
        assert result["duplicates"]["CNPJ"] == []
        assert result["duplicates"]["RAZAO_SOCIAL"] == []

    def test_check_duplicates_cnpj_duplicate_in_memory(self):
        """Testa check_duplicates com CNPJ duplicado usando existing."""
        existing = [
            {"ID": 1, "CNPJ": "11222333000181", "RAZAO_SOCIAL": "Empresa A"},
            {"ID": 2, "CNPJ": "22333444000182", "RAZAO_SOCIAL": "Empresa B"},
        ]
        result = check_duplicates(
            cnpj="11.222.333/0001-81",  # formatado, mas mesmo CNPJ
            razao_social="Empresa C",
            existing=existing,
        )
        assert result["has_any"] is True
        assert 1 in result["duplicates"]["CNPJ"]

    def test_check_duplicates_razao_social_duplicate_in_memory(self):
        """Testa check_duplicates com Razão Social duplicada (case insensitive)."""
        existing = [
            {"ID": 1, "CNPJ": "11222333000181", "RAZAO_SOCIAL": "Empresa A"},
            {"ID": 2, "CNPJ": "22333444000182", "RAZAO_SOCIAL": "Empresa B"},
        ]
        result = check_duplicates(
            cnpj="33444555000183",
            razao_social="empresa a",  # minúsculas
            existing=existing,
        )
        assert result["has_any"] is True
        assert 1 in result["duplicates"]["RAZAO_SOCIAL"]

    def test_check_duplicates_exclude_id_in_memory(self):
        """Testa check_duplicates excluindo um ID específico."""
        existing = [
            {"ID": 1, "CNPJ": "11222333000181", "RAZAO_SOCIAL": "Empresa A"},
            {"ID": 2, "CNPJ": "22333444000182", "RAZAO_SOCIAL": "Empresa B"},
        ]
        result = check_duplicates(
            cnpj="11222333000181",
            razao_social="Empresa A",
            exclude_id=1,  # exclui o próprio registro
            existing=existing,
        )
        assert result["has_any"] is False

    # TEST-002: Casos adicionais de check_duplicates
    def test_check_duplicates_multiple_criteria_test002(self):
        """TEST-002: Testa múltiplos critérios de duplicação simultaneamente."""
        existing = [
            {"ID": 1, "CNPJ": "11222333000181", "RAZAO_SOCIAL": "Empresa A"},
            {"ID": 2, "CNPJ": "22333444000182", "RAZAO_SOCIAL": "Empresa B"},
            {"ID": 3, "CNPJ": "33444555000183", "RAZAO_SOCIAL": "Empresa C"},
        ]
        # Busca com CNPJ de ID=1 e Razão de ID=2
        result = check_duplicates(
            cnpj="11222333000181",  # match ID=1
            razao_social="Empresa B",  # match ID=2
            existing=existing,
        )
        assert result["has_any"] is True
        assert 1 in result["duplicates"]["CNPJ"]
        assert 2 in result["duplicates"]["RAZAO_SOCIAL"]

    def test_check_duplicates_razao_social_normalization_test002(self):
        """TEST-002: Testa normalização de Razão Social (espaços, case)."""
        existing = [
            {"ID": 1, "CNPJ": "11222333000181", "RAZAO_SOCIAL": "  EMPRESA ABC LTDA  "},
            {"ID": 2, "CNPJ": "22333444000182", "RAZAO_SOCIAL": "Empresa XYZ"},
        ]
        # Case insensitive e trim
        result = check_duplicates(
            cnpj="99999999999999",
            razao_social="empresa abc ltda",  # minúsculas, sem espaços extras
            existing=existing,
        )
        assert result["has_any"] is True
        assert 1 in result["duplicates"]["RAZAO_SOCIAL"]

    def test_check_duplicates_skip_id_multiple_test002(self):
        """TEST-002: Testa exclude_id quando há múltiplos registros similares."""
        existing = [
            {"ID": 1, "CNPJ": "11222333000181", "RAZAO_SOCIAL": "Empresa A"},
            {"ID": 2, "CNPJ": "11222333000181", "RAZAO_SOCIAL": "Empresa A Filial"},  # mesmo CNPJ
            {"ID": 3, "CNPJ": "22333444000182", "RAZAO_SOCIAL": "Empresa A"},  # mesma razão
        ]
        # Edição do registro ID=1, deve ignorá-lo mas encontrar ID=2 (CNPJ) e ID=3 (Razão)
        result = check_duplicates(
            cnpj="11222333000181",
            razao_social="Empresa A",
            exclude_id=1,
            existing=existing,
        )
        assert result["has_any"] is True
        assert 1 not in result["duplicates"]["CNPJ"]  # ID=1 excluído
        assert 2 in result["duplicates"]["CNPJ"]  # ID=2 encontrado
        assert 3 in result["duplicates"]["RAZAO_SOCIAL"]  # ID=3 encontrado

    def test_check_duplicates_with_db_connection(self, tmp_path):
        """Testa check_duplicates usando conexão SQLite."""
        db_path = tmp_path / "test_clientes.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE clientes (
                ID INTEGER PRIMARY KEY,
                CNPJ TEXT,
                RAZAO_SOCIAL TEXT,
                DELETED_AT TEXT
            )
        """
        )
        conn.execute(
            "INSERT INTO clientes (ID, CNPJ, RAZAO_SOCIAL, DELETED_AT) VALUES (?, ?, ?, ?)",
            (1, "11222333000181", "Empresa A", None),
        )
        conn.execute(
            "INSERT INTO clientes (ID, CNPJ, RAZAO_SOCIAL, DELETED_AT) VALUES (?, ?, ?, ?)",
            (2, "22333444000182", "Empresa B", None),
        )
        conn.commit()

        # Busca duplicata por CNPJ
        result = check_duplicates(
            cnpj="11222333000181",
            razao_social="Empresa C",
            conn=conn,
        )
        assert result["has_any"] is True
        assert 1 in result["duplicates"]["CNPJ"]

        conn.close()

    def test_check_duplicates_with_db_exclude_id(self, tmp_path):
        """Testa check_duplicates com DB excluindo ID."""
        db_path = tmp_path / "test_clientes.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE clientes (
                ID INTEGER PRIMARY KEY,
                CNPJ TEXT,
                RAZAO_SOCIAL TEXT,
                DELETED_AT TEXT
            )
        """
        )
        conn.execute(
            "INSERT INTO clientes (ID, CNPJ, RAZAO_SOCIAL, DELETED_AT) VALUES (?, ?, ?, ?)",
            (1, "11222333000181", "Empresa A", None),
        )
        conn.commit()

        result = check_duplicates(
            cnpj="11222333000181",
            razao_social="Empresa A",
            exclude_id=1,
            conn=conn,
        )
        assert result["has_any"] is False

        conn.close()

    def test_check_duplicates_empty_inputs(self):
        """Testa check_duplicates com inputs vazios."""
        result = check_duplicates(
            cnpj="",
            razao_social="",
            existing=[],
        )
        assert result["has_any"] is False

    def test_check_duplicates_no_data_source(self):
        """Testa check_duplicates sem conn nem existing."""
        result = check_duplicates(
            cnpj="11222333000181",
            razao_social="Empresa A",
        )
        assert result["has_any"] is False

    def test_check_duplicates_db_error_handling(self, tmp_path):
        """Testa tratamento de erro no SQL (tabela inexistente)."""
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        # não cria tabela clientes, vai dar erro

        result = check_duplicates(
            cnpj="11222333000181",
            razao_social="Empresa A",
            conn=conn,
        )
        # deve retornar vazio sem quebrar
        assert result["has_any"] is False
        conn.close()

    def test_check_duplicates_existing_error_handling(self):
        """Testa tratamento de erro ao processar existing com dados malformados."""
        existing = [
            {"ID": "invalid", "CNPJ": "11222333000181"},  # ID não é int
        ]
        result = check_duplicates(
            cnpj="11222333000181",
            razao_social="Test",
            existing=existing,
        )
        # deve retornar vazio sem quebrar
        assert result["has_any"] is False


# ==================== validate_cliente_payload ====================


class TestValidateClientePayload:
    """Testa validação completa de payload de cliente."""

    def test_validate_cliente_payload_valid_all_fields(self):
        """Testa payload válido com todos os campos preenchidos."""
        result = validate_cliente_payload(
            nome="João Silva",
            razao_social="Empresa ABC Ltda",
            cnpj="11.222.333/0001-65",
            numero="11987654321",
        )
        assert result["ok"] is True
        assert result["errors"] == {}
        assert result["clean"]["nome"] == "João Silva"
        assert result["clean"]["razao_social"] == "Empresa ABC Ltda"
        assert result["clean"]["cnpj"] == "11222333000165"
        assert result["clean"]["numero"] == "5511987654321"

    def test_validate_cliente_payload_missing_required_fields(self):
        """Testa payload com campos obrigatórios faltando."""
        result = validate_cliente_payload(
            nome="João",
            razao_social="",
            cnpj="",
            numero="11987654321",
        )
        assert result["ok"] is False
        assert "razao_social" in result["errors"]
        assert "cnpj" in result["errors"]

    def test_validate_cliente_payload_invalid_cnpj(self):
        """Testa payload com CNPJ inválido."""
        result = validate_cliente_payload(
            nome="João",
            razao_social="Empresa XYZ",
            cnpj="12345678000195",  # dígitos verificadores errados
            numero="11987654321",
        )
        assert result["ok"] is False
        assert "cnpj" in result["errors"]
        assert result["errors"]["cnpj"] == "CNPJ inválido."

    def test_validate_cliente_payload_invalid_whatsapp(self):
        """Testa payload com WhatsApp inválido."""
        result = validate_cliente_payload(
            nome="João",
            razao_social="Empresa ABC",
            cnpj="11.222.333/0001-65",
            numero="123",  # muito curto
        )
        assert result["ok"] is False
        assert "numero" in result["errors"]
        assert result["errors"]["numero"] == "WhatsApp inválido."

    def test_validate_cliente_payload_none_values(self):
        """Testa payload com valores None."""
        result = validate_cliente_payload(
            nome=None,
            razao_social=None,
            cnpj=None,
            numero=None,
        )
        assert result["ok"] is False
        assert "razao_social" in result["errors"]
        assert "cnpj" in result["errors"]

    def test_validate_cliente_payload_whitespace_values(self):
        """Testa payload com valores apenas com espaços."""
        result = validate_cliente_payload(
            nome="  ",
            razao_social="   ",
            cnpj="  ",
            numero="",
        )
        assert result["ok"] is False
        assert "razao_social" in result["errors"]
        assert "cnpj" in result["errors"]

    def test_validate_cliente_payload_valid_without_numero(self):
        """Testa payload válido sem número de WhatsApp."""
        result = validate_cliente_payload(
            nome="João",
            razao_social="Empresa ABC",
            cnpj="11.222.333/0001-65",
            numero="",
        )
        assert result["ok"] is True
        assert result["clean"]["numero"] == ""
