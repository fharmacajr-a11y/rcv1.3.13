# -*- coding: utf-8 -*-
"""
Testes unitários para src/utils/log_sanitizer.py (SEC-006).

BATCH 05: Cobertura headless sem GUI/Tk.
"""

from __future__ import annotations


from src.utils.log_sanitizer import sanitize_dict_for_log, sanitize_for_log


class TestSanitizeForLog:
    """Testes para sanitize_for_log()."""

    def test_none_value(self) -> None:
        """Testa sanitização de None."""
        result = sanitize_for_log(None)
        assert result == "None"

    def test_simple_string(self) -> None:
        """Testa string simples sem dados sensíveis."""
        result = sanitize_for_log("Hello, World!")
        assert result == "Hello, World!"

    def test_integer_value(self) -> None:
        """Testa sanitização de inteiro."""
        result = sanitize_for_log(42)
        assert result == "42"

    def test_mask_password_with_equals(self) -> None:
        """Testa mascaramento de senha com =."""
        result = sanitize_for_log("password=secret123")
        assert "secret123" not in result
        assert "password=********" in result

    def test_mask_password_with_colon(self) -> None:
        """Testa mascaramento de senha com :."""
        result = sanitize_for_log('"password": "mypass"')
        assert "mypass" not in result
        assert "password=********" in result

    def test_mask_senha_portuguese(self) -> None:
        """Testa mascaramento de 'senha' em português."""
        result = sanitize_for_log("senha=minhasenha")
        assert "minhasenha" not in result
        assert "senha=********" in result

    def test_mask_pwd(self) -> None:
        """Testa mascaramento de pwd."""
        result = sanitize_for_log("pwd=short")
        assert "short" not in result
        assert "pwd=********" in result

    def test_mask_secret(self) -> None:
        """Testa mascaramento de secret."""
        result = sanitize_for_log("secret=topsecret")
        assert "topsecret" not in result
        assert "secret=********" in result

    def test_mask_bearer_token(self) -> None:
        """Testa mascaramento de Bearer token."""
        result = sanitize_for_log("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "Bearer=" in result
        assert "eyJh" in result  # primeiros 4
        assert "VCJ9" in result  # últimos 4

    def test_mask_token_field(self) -> None:
        """Testa mascaramento de campo token."""
        result = sanitize_for_log("token=abc123xyz789")
        assert "abc123xyz789" not in result
        assert "token=" in result
        assert "********" in result

    def test_mask_api_key(self) -> None:
        """Testa mascaramento de api_key."""
        result = sanitize_for_log("api_key=sk_test_1234567890abcdef")
        assert "sk_test_1234567890abcdef" not in result
        assert "api_key=" in result

    def test_mask_rc_client_secret(self) -> None:
        """Testa mascaramento de RC_CLIENT_SECRET_KEY."""
        result = sanitize_for_log("RC_CLIENT_SECRET_KEY=base64encodedkey123==")
        assert "base64encodedkey123==" not in result
        assert "RC_CLIENT_SECRET_KEY=" in result

    def test_mask_cpf_with_dots(self) -> None:
        """Testa mascaramento de CPF com pontuação."""
        result = sanitize_for_log("CPF: 123.456.789-01")
        assert "123.456.789-01" not in result
        assert "***.***" in result
        assert "***-**" in result

    def test_mask_cpf_without_dots(self) -> None:
        """Testa mascaramento de CPF sem pontuação."""
        result = sanitize_for_log("CPF: 12345678901")
        assert "12345678901" not in result
        assert "***" in result

    def test_mask_cnpj_with_dots(self) -> None:
        """Testa mascaramento de CNPJ com pontuação."""
        result = sanitize_for_log("CNPJ: 12.345.678/0001-90")
        assert "12.345.678/0001-90" not in result
        assert "**.***" in result

    def test_mask_cnpj_without_dots(self) -> None:
        """Testa mascaramento de CNPJ sem pontuação."""
        result = sanitize_for_log("CNPJ: 12345678000190")
        assert "12345678000190" not in result

    def test_mask_credit_card(self) -> None:
        """Testa mascaramento de cartão de crédito."""
        result = sanitize_for_log("Card: 1234 5678 9012 3456")
        assert "1234 5678 9012 3456" not in result
        assert "****-****-****-****" in result

    def test_mask_credit_card_no_spaces(self) -> None:
        """Testa mascaramento de cartão sem espaços."""
        result = sanitize_for_log("Card: 1234567890123456")
        assert "1234567890123456" not in result

    def test_multiple_sensitive_fields(self) -> None:
        """Testa string com múltiplos campos sensíveis."""
        text = "user=john password=secret123 token=abc123xyz api_key=sk_live_test"
        result = sanitize_for_log(text)

        assert "secret123" not in result
        assert "abc123xyz" not in result
        assert "sk_live_test" not in result
        assert "user=john" in result  # campo não sensível mantido

    def test_custom_mask_char(self) -> None:
        """Testa uso de caractere de máscara customizado."""
        result = sanitize_for_log("password=secret", mask_char="#")
        assert "secret" not in result
        assert "########" in result

    def test_case_insensitive_patterns(self) -> None:
        """Testa que padrões são case-insensitive."""
        result = sanitize_for_log("PASSWORD=Secret123")
        assert "Secret123" not in result
        assert "password=********" in result.lower()

    def test_email_password_context(self) -> None:
        """Testa mascaramento em contexto de email."""
        result = sanitize_for_log("email=user@test.com&password=pass123")
        assert "pass123" not in result
        assert "email=user@test.com" in result  # email preservado

    def test_json_like_password(self) -> None:
        """Testa mascaramento em formato JSON."""
        result = sanitize_for_log('{"password": "mypassword", "username": "john"}')
        assert "mypassword" not in result
        assert "username" in result
        assert "john" in result


class TestSanitizeDictForLog:
    """Testes para sanitize_dict_for_log()."""

    def test_empty_dict(self) -> None:
        """Testa dicionário vazio."""
        result = sanitize_dict_for_log({})
        assert result == {}

    def test_non_sensitive_dict(self) -> None:
        """Testa dicionário sem campos sensíveis."""
        data = {"name": "John", "age": 30, "city": "NYC"}
        result = sanitize_dict_for_log(data)
        assert result == data

    def test_mask_password_field(self) -> None:
        """Testa mascaramento de campo password."""
        data = {"username": "john", "password": "secret123"}
        result = sanitize_dict_for_log(data)

        assert result["username"] == "john"
        assert result["password"] == "se***23"  # 9 chars: primeiros 2 + *** + últimos 2
        assert "secret123" not in str(result)

    def test_mask_long_password(self) -> None:
        """Testa mascaramento de senha longa (>8 chars)."""
        data = {"password": "verylongsecret123"}
        result = sanitize_dict_for_log(data)

        assert result["password"] == "ve***23"
        assert "verylongsecret123" not in str(result)

    def test_mask_senha_portuguese(self) -> None:
        """Testa mascaramento de campo 'senha'."""
        data = {"email": "user@test.com", "senha": "minhasenha"}
        result = sanitize_dict_for_log(data)

        assert result["email"] == "user@test.com"
        assert result["senha"] == "mi***ha"

    def test_mask_token(self) -> None:
        """Testa mascaramento de token."""
        data = {"user_id": 123, "token": "abc123xyz789"}
        result = sanitize_dict_for_log(data)

        assert result["user_id"] == 123
        assert result["token"] == "ab***89"

    def test_mask_api_key(self) -> None:
        """Testa mascaramento de api_key."""
        data = {"api_key": "sk_test_123456"}
        result = sanitize_dict_for_log(data)

        assert result["api_key"] == "sk***56"

    def test_mask_cpf(self) -> None:
        """Testa mascaramento de CPF."""
        data = {"nome": "João", "cpf": "123.456.789-01"}
        result = sanitize_dict_for_log(data)

        assert result["nome"] == "João"
        assert result["cpf"] == "12***01"

    def test_mask_cnpj(self) -> None:
        """Testa mascaramento de CNPJ."""
        data = {"empresa": "Acme", "cnpj": "12.345.678/0001-90"}
        result = sanitize_dict_for_log(data)

        assert result["empresa"] == "Acme"
        assert result["cnpj"] == "12***90"

    def test_mask_credit_card(self) -> None:
        """Testa mascaramento de cartão."""
        data = {"credit_card": "1234567890123456"}
        result = sanitize_dict_for_log(data)

        assert result["credit_card"] == "12***56"

    def test_nested_dict(self) -> None:
        """Testa dicionário aninhado."""
        data = {
            "user": {
                "name": "John",
                "password": "secret123",
            },
            "status": "active",
        }
        result = sanitize_dict_for_log(data)

        assert result["user"]["name"] == "John"
        assert result["user"]["password"] == "se***23"
        assert result["status"] == "active"

    def test_deeply_nested_dict(self) -> None:
        """Testa dicionário profundamente aninhado."""
        data = {
            "level1": {
                "level2": {
                    "api_key": "secret_key_123",
                    "public_data": "visible",
                },
            },
        }
        result = sanitize_dict_for_log(data)

        assert result["level1"]["level2"]["public_data"] == "visible"
        assert result["level1"]["level2"]["api_key"] == "se***23"

    def test_custom_sensitive_keys(self) -> None:
        """Testa chaves sensíveis customizadas."""
        data = {
            "username": "john",
            "custom_secret": "mysecret",
        }
        result = sanitize_dict_for_log(data, sensitive_keys={"custom_secret"})

        assert result["username"] == "john"
        assert result["custom_secret"] == "***"

    def test_case_insensitive_key_matching(self) -> None:
        """Testa que matching de chaves é case-insensitive."""
        data = {
            "PASSWORD": "secret",
            "Api_Key": "key123",
        }
        result = sanitize_dict_for_log(data)

        assert result["PASSWORD"] == "***"
        assert result["Api_Key"] == "***"

    def test_partial_key_matching(self) -> None:
        """Testa matching parcial de chaves (ex: 'user_password')."""
        data = {
            "user_password": "secret123",
            "password_reset": "token456",
        }
        result = sanitize_dict_for_log(data)

        assert result["user_password"] == "se***23"
        assert result["password_reset"] == "***"  # 8 chars exato = formato curto

    def test_non_string_sensitive_value(self) -> None:
        """Testa valor sensível não-string."""
        data = {
            "password": 123456,  # int
            "token": None,
        }
        result = sanitize_dict_for_log(data)

        assert result["password"] == "***"
        assert result["token"] == "***"

    def test_empty_string_sensitive_value(self) -> None:
        """Testa valor sensível vazio."""
        data = {"password": ""}
        result = sanitize_dict_for_log(data)

        assert result["password"] == "***"

    def test_short_sensitive_value(self) -> None:
        """Testa valor sensível curto (<=8 chars)."""
        data = {"password": "short"}
        result = sanitize_dict_for_log(data)

        assert result["password"] == "***"

    def test_authorization_field(self) -> None:
        """Testa mascaramento de authorization."""
        data = {"authorization": "Bearer token123"}
        result = sanitize_dict_for_log(data)

        assert result["authorization"] == "Be***23"

    def test_access_token_field(self) -> None:
        """Testa mascaramento de access_token."""
        data = {"access_token": "eyJhbGciOiJIUzI1NiJ9"}
        result = sanitize_dict_for_log(data)

        assert result["access_token"] == "ey***J9"

    def test_refresh_token_field(self) -> None:
        """Testa mascaramento de refresh_token."""
        data = {"refresh_token": "refresh_abc123xyz"}
        result = sanitize_dict_for_log(data)

        assert result["refresh_token"] == "re***yz"

    def test_mixed_sensitive_and_nested(self) -> None:
        """Testa mix de campos sensíveis e aninhamento."""
        data = {
            "user_id": 42,
            "credentials": {
                "username": "admin",
                "password": "supersecret",
                "api_key": "sk_live_test123",
            },
            "metadata": {
                "created_at": "2024-01-01",
                "secret": "hidden",
            },
        }
        result = sanitize_dict_for_log(data)

        assert result["user_id"] == 42
        assert result["credentials"]["username"] == "admin"
        assert result["credentials"]["password"] == "su***et"
        assert result["credentials"]["api_key"] == "sk***23"
        assert result["metadata"]["created_at"] == "2024-01-01"
        assert result["metadata"]["secret"] == "***"


class TestEdgeCases:
    """Testes de edge cases e comportamentos extremos."""

    def test_sanitize_for_log_with_list(self) -> None:
        """Testa que lista é convertida para string."""
        result = sanitize_for_log(["item1", "password=secret"])
        assert "password=********" in result
        assert "item1" in result

    def test_sanitize_for_log_with_dict(self) -> None:
        """Testa que dict é convertido para string."""
        result = sanitize_for_log({"password": "secret"})
        assert "password" in result
        # Dict será convertido para str() primeiro

    def test_sanitize_dict_with_list_value(self) -> None:
        """Testa que valores lista são preservados."""
        data = {"items": [1, 2, 3], "password": "secret"}
        result = sanitize_dict_for_log(data)

        assert result["items"] == [1, 2, 3]
        assert result["password"] == "***"

    def test_very_long_token(self) -> None:
        """Testa token muito longo."""
        long_token = "a" * 100
        result = sanitize_for_log(f"token={long_token}")

        assert long_token not in result
        assert "token=aaaa********" in result

    def test_multiple_passwords_same_string(self) -> None:
        """Testa múltiplas senhas na mesma string."""
        text = "password=secret1 senha=secret2 pwd=secret3"
        result = sanitize_for_log(text)

        assert "secret1" not in result
        assert "secret2" not in result
        assert "secret3" not in result
        assert result.count("********") >= 3

    def test_unicode_in_sensitive_field(self) -> None:
        """Testa unicode em campo sensível."""
        data = {"password": "señá123ção"}
        result = sanitize_dict_for_log(data)

        assert "señá123ção" not in str(result)
        assert result["password"] == "se***ão"

    def test_special_chars_in_token(self) -> None:
        """Testa caracteres especiais em token."""
        result = sanitize_for_log("token=abc-123_xyz.test")
        assert "abc-123_xyz.test" not in result
        assert "token=" in result
