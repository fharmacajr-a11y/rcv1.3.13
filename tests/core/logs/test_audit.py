from __future__ import annotations

import logging

from src.core.logs import audit


def test_ensure_schema_is_placeholder():
    assert audit.ensure_schema() is None


def test_log_client_action_is_noop(caplog):
    with caplog.at_level(logging.INFO, logger="src.core.logs.audit"):
        result = audit.log_client_action("alice", 10, "UPDATE", _details="note")

    assert result is None
    assert caplog.records == []


def test_last_action_of_user_returns_none(caplog):
    with caplog.at_level(logging.INFO):
        result = audit.last_action_of_user(99)

    assert result is None
    assert caplog.records == []


def test_last_client_activity_many_returns_empty_mapping(caplog):
    with caplog.at_level(logging.INFO):
        result = audit.last_client_activity_many([1, 2, 3])

    assert result == {}
    assert caplog.records == []
