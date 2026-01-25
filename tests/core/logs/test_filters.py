from __future__ import annotations

import logging

import pytest

from src.core.logs.filters import Redact, RedactSensitiveData


def make_record(msg, args=None):
    return logging.LogRecord(
        name="app.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg=msg,
        args=args,
        exc_info=None,
    )


def test_filter_redacts_sensitive_text_in_message():
    flt = RedactSensitiveData()
    record = make_record("apikey=123 token=abc user=ok")

    allowed = flt.filter(record)

    assert allowed is True
    assert record.msg == "apikey=*** token=*** user=ok"


def test_filter_keeps_non_string_message():
    flt = RedactSensitiveData()
    record = make_record({"message": "apikey=123"})

    allowed = flt.filter(record)

    assert allowed is True
    assert record.msg == {"message": "apikey=123"}


def test_filter_redacts_dict_args_and_nested_values():
    flt = RedactSensitiveData()
    record = make_record(
        "message",
        args={
            "password": "super-secret",
            "nested": {"token": "abc", "safe": "value"},
            "note": "token=abc should hide",
        },
    )

    flt.filter(record)

    assert record.args["password"] == "***"
    assert record.args["nested"] == {"token": "***", "safe": "value"}
    assert record.args["note"] == "token=*** should hide"


@pytest.mark.parametrize("args_input", [("apikey=abc", {"key": "secret"}, 5), ["apikey=abc", {"key": "secret"}, 5]])
def test_filter_redacts_sequence_args(args_input):
    flt = Redact()
    record = make_record("message", args=args_input)

    flt.filter(record)

    assert record.args[0] == "apikey=***"
    assert record.args[1] == {"key": "***"}
    assert record.args[2] == 5
    assert isinstance(record.args, tuple)


def test_filter_ignores_empty_args():
    flt = RedactSensitiveData()
    record = make_record("no secrets here", args=())

    flt.filter(record)

    assert record.args == ()


def test_filter_keeps_non_iterable_args_as_is():
    flt = RedactSensitiveData()
    record = make_record("message", args="raw-args")

    flt.filter(record)

    assert record.args == "raw-args"
