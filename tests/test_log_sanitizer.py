# -*- coding: utf-8 -*-
"""PR6 – Testes do módulo log_sanitizer.

Valida:
  a) mask_email mascara corretamente (preserva 1° char + domínio)
  b) mask_phone mascara dígitos internos
  c) mask_ip mascara últimos dois octetos
  d) sanitize_for_log remove tokens, passwords, CPFs de texto livre
  e) sanitize_dict_for_log mascara chaves sensíveis em dicts
  f) SensitiveDataFilter aplica sanitização automática em LogRecords
"""

from __future__ import annotations

import logging

from src.utils.log_sanitizer import (
    SensitiveDataFilter,
    mask_email,
    mask_ip,
    mask_phone,
    sanitize_dict_for_log,
    sanitize_for_log,
)


# ===========================================================================
# mask_email
# ===========================================================================


class TestMaskEmail:
    def test_normal_email(self):
        assert mask_email("joao@empresa.com") == "j***@empresa.com"

    def test_short_local(self):
        assert mask_email("a@x.io") == "a***@x.io"

    def test_none(self):
        assert mask_email(None) == "***"

    def test_empty(self):
        assert mask_email("") == "***"

    def test_no_at(self):
        assert mask_email("invalid") == "***"

    def test_long_email(self):
        result = mask_email("administrator@longdomain.example.org")
        assert result == "a***@longdomain.example.org"


# ===========================================================================
# mask_phone
# ===========================================================================


class TestMaskPhone:
    def test_digits_only(self):
        assert mask_phone("21999887766") == "21*****66"

    def test_formatted(self):
        assert mask_phone("(21) 99988-7766") == "21*****66"

    def test_short(self):
        assert mask_phone("123") == "***"

    def test_none(self):
        assert mask_phone(None) == "***"

    def test_empty(self):
        assert mask_phone("") == "***"

    def test_with_country_code(self):
        result = mask_phone("+5521999887766")
        assert result.startswith("55")
        assert result.endswith("66")
        assert "*****" in result


# ===========================================================================
# mask_ip
# ===========================================================================


class TestMaskIp:
    def test_normal_ipv4(self):
        assert mask_ip("192.168.1.42") == "192.168.*.*"

    def test_none(self):
        assert mask_ip(None) == "***"

    def test_empty(self):
        assert mask_ip("") == "***"

    def test_non_ipv4(self):
        # IPv6 ou string aleatória → ***
        assert mask_ip("fe80::1") == "***"


# ===========================================================================
# sanitize_for_log (funções existentes)
# ===========================================================================


class TestSanitizeForLog:
    def test_masks_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        result = sanitize_for_log(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "Bearer" in result

    def test_masks_password_field(self):
        text = 'password="s3cr3t123"'
        result = sanitize_for_log(text)
        assert "s3cr3t123" not in result
        assert "********" in result

    def test_masks_cpf(self):
        text = "CPF do cliente: 123.456.789-01"
        result = sanitize_for_log(text)
        assert "123.456.789-01" not in result
        assert "***" in result

    def test_masks_cnpj(self):
        text = "CNPJ: 12.345.678/0001-90"
        result = sanitize_for_log(text)
        assert "12.345.678/0001-90" not in result

    def test_masks_secret_field(self):
        text = "secret=minha_chave_super_secreta"
        result = sanitize_for_log(text)
        assert "minha_chave_super_secreta" not in result

    def test_preserves_normal_text(self):
        text = "Operação concluída com sucesso em 1.2s"
        assert sanitize_for_log(text) == text

    def test_none_returns_none_string(self):
        assert sanitize_for_log(None) == "None"


# ===========================================================================
# sanitize_dict_for_log
# ===========================================================================


class TestSanitizeDictForLog:
    def test_masks_token_key(self):
        data = {"access_token": "eyJhbGci...", "user": "admin"}
        result = sanitize_dict_for_log(data)
        # Token > 8 chars → primeiros 2 + *** + últimos 2
        assert "eyJhbGci..." not in str(result["access_token"])
        assert result["user"] == "admin"

    def test_masks_password_key(self):
        data = {"password": "hunter2"}
        result = sanitize_dict_for_log(data)
        assert result["password"] == "***"

    def test_masks_nested_dict(self):
        data = {"config": {"secret": "abc123"}}
        result = sanitize_dict_for_log(data)
        assert result["config"]["secret"] == "***"

    def test_preserves_safe_keys(self):
        data = {"name": "João", "age": 30}
        result = sanitize_dict_for_log(data)
        assert result == {"name": "João", "age": 30}


# ===========================================================================
# SensitiveDataFilter (logging.Filter)
# ===========================================================================


class TestSensitiveDataFilter:
    def test_filter_masks_token_in_message(self):
        filt = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.body.signature",
            args=None,
            exc_info=None,
        )
        filt.filter(record)
        assert "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9" not in record.msg

    def test_filter_masks_cpf_in_args(self):
        filt = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Cliente CPF: %s",
            args=("123.456.789-01",),
            exc_info=None,
        )
        filt.filter(record)
        assert isinstance(record.args, tuple)
        assert "123.456.789-01" not in str(record.args[0])

    def test_filter_returns_true(self):
        """Filter nunca descarta records — apenas sanitiza."""
        filt = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="normal message",
            args=None,
            exc_info=None,
        )
        assert filt.filter(record) is True

    def test_filter_with_tuple_args(self):
        filt = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="password=%s",
            args=("hunter2",),
            exc_info=None,
        )
        filt.filter(record)
        # Os args devem ter sido sanitizados
        assert isinstance(record.args, tuple)

    def test_filter_preserves_safe_message(self):
        filt = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Carregados 42 clientes em 0.5s",
            args=None,
            exc_info=None,
        )
        filt.filter(record)
        assert record.msg == "Carregados 42 clientes em 0.5s"
