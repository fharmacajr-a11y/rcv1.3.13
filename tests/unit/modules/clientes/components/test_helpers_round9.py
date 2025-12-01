"""
Round 9 - Comprehensive test coverage for clientes/components/helpers.py

Objetivo: Aumentar cobertura de ~51% para 90%+ testando todas as funções e branches.

Funções testadas:
- _load_status_choices()
- _load_status_groups()
- _build_status_menu()
- STATUS_PREFIX_RE (regex)
- STATUS_CHOICES e STATUS_GROUPS (constantes)
"""

from __future__ import annotations

import importlib
import json
import tkinter as tk
from unittest.mock import Mock

import pytest

from src.modules.clientes.components import helpers


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def clean_env(monkeypatch):
    """Remove environment variables to test default behavior."""
    monkeypatch.delenv("RC_STATUS_CHOICES", raising=False)
    monkeypatch.delenv("RC_STATUS_GROUPS", raising=False)
    importlib.reload(helpers)
    yield
    importlib.reload(helpers)


@pytest.fixture
def mock_menu():
    """Create a mock tk.Menu for testing _build_status_menu."""
    menu = Mock(spec=tk.Menu)
    menu.delete = Mock()
    menu.add_separator = Mock()
    menu.add_command = Mock()
    return menu


# ============================================================================
# Test _load_status_choices()
# ============================================================================


class TestLoadStatusChoices:
    """Test _load_status_choices function with various environment configurations."""

    def test_returns_defaults_when_env_not_set(self, monkeypatch):
        """Should return DEFAULT_STATUS_CHOICES when RC_STATUS_CHOICES is not set."""
        monkeypatch.delenv("RC_STATUS_CHOICES", raising=False)

        result = helpers._load_status_choices()

        assert isinstance(result, list)
        assert len(result) > 0
        assert "Novo cliente" in result
        assert "Finalizado" in result

    def test_returns_defaults_when_env_is_empty_string(self, monkeypatch):
        """Should return defaults when RC_STATUS_CHOICES is empty string."""
        monkeypatch.setenv("RC_STATUS_CHOICES", "")

        result = helpers._load_status_choices()

        assert result == list(helpers.DEFAULT_STATUS_CHOICES)

    def test_returns_defaults_when_env_is_whitespace(self, monkeypatch):
        """Should return defaults when RC_STATUS_CHOICES is only whitespace."""
        monkeypatch.setenv("RC_STATUS_CHOICES", "   ")

        result = helpers._load_status_choices()

        assert result == list(helpers.DEFAULT_STATUS_CHOICES)

    def test_parses_json_array(self, monkeypatch):
        """Should parse JSON array from RC_STATUS_CHOICES."""
        monkeypatch.setenv("RC_STATUS_CHOICES", '["Status A", "Status B", "Status C"]')

        result = helpers._load_status_choices()

        assert result == ["Status A", "Status B", "Status C"]

    def test_parses_comma_separated_values(self, monkeypatch):
        """Should parse comma-separated values from RC_STATUS_CHOICES."""
        monkeypatch.setenv("RC_STATUS_CHOICES", "Status A, Status B, Status C")

        result = helpers._load_status_choices()

        assert result == ["Status A", "Status B", "Status C"]

    def test_strips_whitespace_from_csv(self, monkeypatch):
        """Should strip whitespace from comma-separated values."""
        monkeypatch.setenv("RC_STATUS_CHOICES", "  Status A  ,  Status B  ,  Status C  ")

        result = helpers._load_status_choices()

        assert result == ["Status A", "Status B", "Status C"]

    def test_filters_empty_strings_from_csv(self, monkeypatch):
        """Should filter out empty strings from comma-separated values."""
        monkeypatch.setenv("RC_STATUS_CHOICES", "Status A,,Status B,  ,Status C")

        result = helpers._load_status_choices()

        assert result == ["Status A", "Status B", "Status C"]

    def test_converts_values_to_strings(self, monkeypatch):
        """Should convert all values to strings."""
        monkeypatch.setenv("RC_STATUS_CHOICES", '[123, 456, "text"]')

        result = helpers._load_status_choices()

        assert result == ["123", "456", "text"]
        assert all(isinstance(s, str) for s in result)

    def test_returns_defaults_on_invalid_json(self, monkeypatch):
        """Should return defaults when JSON is malformed."""
        monkeypatch.setenv("RC_STATUS_CHOICES", '["Status A", invalid json')

        result = helpers._load_status_choices()

        assert result == list(helpers.DEFAULT_STATUS_CHOICES)

    def test_filters_empty_values_from_json(self, monkeypatch):
        """Should filter out empty/falsy values from JSON array."""
        monkeypatch.setenv("RC_STATUS_CHOICES", '["Status A", "", null, "Status B", 0, "Status C"]')

        result = helpers._load_status_choices()

        # Only non-empty string values should be kept
        # null becomes "null" string, 0 becomes "0" string, but empty "" is filtered
        assert "Status A" in result
        assert "Status B" in result
        assert "Status C" in result
        assert "" not in result


# ============================================================================
# Test _load_status_groups()
# ============================================================================


class TestLoadStatusGroups:
    """Test _load_status_groups function with various environment configurations."""

    def test_returns_defaults_when_env_not_set(self, monkeypatch):
        """Should return DEFAULT_STATUS_GROUPS when RC_STATUS_GROUPS is not set."""
        monkeypatch.delenv("RC_STATUS_GROUPS", raising=False)

        result = helpers._load_status_groups()

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(g, tuple) and len(g) == 2 for g in result)

        # Check structure
        group_names = [name for name, _ in result]
        assert "Status gerais" in group_names
        assert "SIFAP" in group_names

    def test_returns_defaults_when_env_is_empty_string(self, monkeypatch):
        """Should return defaults when RC_STATUS_GROUPS is empty string."""
        monkeypatch.setenv("RC_STATUS_GROUPS", "")

        result = helpers._load_status_groups()

        assert result == list(helpers.DEFAULT_STATUS_GROUPS)

    def test_returns_defaults_when_env_is_whitespace(self, monkeypatch):
        """Should return defaults when RC_STATUS_GROUPS is only whitespace."""
        monkeypatch.setenv("RC_STATUS_GROUPS", "   ")

        result = helpers._load_status_groups()

        assert result == list(helpers.DEFAULT_STATUS_GROUPS)

    def test_parses_valid_json_dict(self, monkeypatch):
        """Should parse valid JSON dictionary from RC_STATUS_GROUPS."""
        groups_json = json.dumps({"Grupo A": ["Status 1", "Status 2"], "Grupo B": ["Status 3", "Status 4"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)

        result = helpers._load_status_groups()

        assert len(result) == 2
        assert ("Grupo A", ["Status 1", "Status 2"]) in result
        assert ("Grupo B", ["Status 3", "Status 4"]) in result

    def test_filters_empty_value_lists(self, monkeypatch):
        """Should filter out groups with empty value lists."""
        groups_json = json.dumps({"Grupo A": ["Status 1"], "Grupo B": [], "Grupo C": ["Status 2"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)

        result = helpers._load_status_groups()

        assert len(result) == 2
        group_names = [name for name, _ in result]
        assert "Grupo A" in group_names
        assert "Grupo C" in group_names
        assert "Grupo B" not in group_names

    def test_filters_non_list_values(self, monkeypatch):
        """Should filter out groups where values are not list/tuple."""
        groups_json = json.dumps({"Grupo A": ["Status 1"], "Grupo B": "not a list", "Grupo C": ["Status 2"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)

        result = helpers._load_status_groups()

        assert len(result) == 2
        group_names = [name for name, _ in result]
        assert "Grupo A" in group_names
        assert "Grupo C" in group_names
        assert "Grupo B" not in group_names

    def test_strips_whitespace_from_items(self, monkeypatch):
        """Should strip whitespace from status items."""
        groups_json = json.dumps({"Grupo A": ["  Status 1  ", "  Status 2  "]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)

        result = helpers._load_status_groups()

        assert result[0] == ("Grupo A", ["Status 1", "Status 2"])

    def test_filters_empty_strings_from_items(self, monkeypatch):
        """Should filter out empty strings from status items."""
        groups_json = json.dumps({"Grupo A": ["Status 1", "", "  ", "Status 2"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)

        result = helpers._load_status_groups()

        assert result[0] == ("Grupo A", ["Status 1", "Status 2"])

    def test_converts_all_values_to_strings(self, monkeypatch):
        """Should convert all values to strings."""
        groups_json = json.dumps({"Grupo A": [123, 456, "text"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)

        result = helpers._load_status_groups()

        assert result[0] == ("Grupo A", ["123", "456", "text"])

    def test_returns_defaults_on_invalid_json(self, monkeypatch):
        """Should return defaults when JSON is malformed."""
        monkeypatch.setenv("RC_STATUS_GROUPS", '{"Grupo A": invalid json')

        result = helpers._load_status_groups()

        assert result == list(helpers.DEFAULT_STATUS_GROUPS)

    def test_returns_defaults_when_json_is_not_dict(self, monkeypatch):
        """Should return defaults when JSON is not a dictionary."""
        monkeypatch.setenv("RC_STATUS_GROUPS", '["not", "a", "dict"]')

        result = helpers._load_status_groups()

        assert result == list(helpers.DEFAULT_STATUS_GROUPS)

    def test_returns_defaults_when_json_is_empty_dict(self, monkeypatch):
        """Should return defaults when JSON is an empty dictionary."""
        monkeypatch.setenv("RC_STATUS_GROUPS", "{}")

        result = helpers._load_status_groups()

        assert result == list(helpers.DEFAULT_STATUS_GROUPS)

    def test_converts_group_name_to_string(self, monkeypatch):
        """Should convert group names to strings."""
        groups_json = json.dumps({123: ["Status 1", "Status 2"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)

        result = helpers._load_status_groups()

        assert result[0][0] == "123"


# ============================================================================
# Test _build_status_menu()
# ============================================================================


class TestBuildStatusMenu:
    """Test _build_status_menu function that builds Tkinter menu."""

    def test_clears_existing_menu(self, mock_menu, monkeypatch):
        """Should clear existing menu items before rebuilding."""
        monkeypatch.delenv("RC_STATUS_GROUPS", raising=False)
        callback = Mock()

        helpers._build_status_menu(mock_menu, callback)

        mock_menu.delete.assert_called_once_with(0, "end")

    def test_adds_group_headers_as_disabled(self, mock_menu, monkeypatch):
        """Should add group headers as disabled menu items."""
        groups_json = json.dumps({"Grupo A": ["Status 1"], "Grupo B": ["Status 2"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)
        callback = Mock()

        helpers._build_status_menu(mock_menu, callback)

        # Find calls with disabled headers
        header_calls = [c for c in mock_menu.add_command.call_args_list if c[1].get("state") == "disabled"]

        assert len(header_calls) == 2
        assert any("Grupo A" in str(c[1]["label"]) for c in header_calls)
        assert any("Grupo B" in str(c[1]["label"]) for c in header_calls)

    def test_adds_separators_between_groups(self, mock_menu, monkeypatch):
        """Should add separators between groups (not before first group)."""
        groups_json = json.dumps({"Grupo A": ["Status 1"], "Grupo B": ["Status 2"], "Grupo C": ["Status 3"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)
        callback = Mock()

        helpers._build_status_menu(mock_menu, callback)

        # Should have separators between groups + 1 final separator before "Limpar"
        # With 3 groups: 2 separators between + 1 before Limpar = 3 total
        assert mock_menu.add_separator.call_count == 3

    def test_adds_status_items_with_callback(self, mock_menu, monkeypatch):
        """Should add status items with callback that passes the label."""
        groups_json = json.dumps({"Grupo A": ["Status 1", "Status 2"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)
        callback = Mock()

        helpers._build_status_menu(mock_menu, callback)

        # Find calls that are status items (have command, not disabled)
        status_calls = [
            c for c in mock_menu.add_command.call_args_list if "command" in c[1] and c[1].get("state") != "disabled"
        ]

        # Should have 2 status items + 1 "Limpar" = 3 total
        assert len(status_calls) >= 2

        # Verify status items
        labels = [c[1]["label"] for c in status_calls if c[1]["label"] != "Limpar"]
        assert "Status 1" in labels
        assert "Status 2" in labels

    def test_adds_clear_option_at_end(self, mock_menu, monkeypatch):
        """Should add 'Limpar' option at the end with empty string callback."""
        monkeypatch.delenv("RC_STATUS_GROUPS", raising=False)
        callback = Mock()

        helpers._build_status_menu(mock_menu, callback)

        # Find "Limpar" call
        clear_calls = [c for c in mock_menu.add_command.call_args_list if c[1].get("label") == "Limpar"]

        assert len(clear_calls) == 1

        # Execute the command and verify it calls callback with empty string
        clear_calls[0][1]["command"]()
        callback.assert_called_with("")

    def test_callback_receives_correct_label(self, mock_menu, monkeypatch):
        """Should pass correct label to callback when status item is clicked."""
        groups_json = json.dumps({"Grupo A": ["Status Test"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)
        callback = Mock()

        helpers._build_status_menu(mock_menu, callback)

        # Find "Status Test" command
        status_calls = [c for c in mock_menu.add_command.call_args_list if c[1].get("label") == "Status Test"]

        assert len(status_calls) == 1

        # Execute the command
        status_calls[0][1]["command"]()
        callback.assert_called_once_with("Status Test")

    def test_handles_default_groups(self, mock_menu, monkeypatch):
        """Should handle DEFAULT_STATUS_GROUPS correctly."""
        monkeypatch.delenv("RC_STATUS_GROUPS", raising=False)
        callback = Mock()

        helpers._build_status_menu(mock_menu, callback)

        # Should add commands for default groups
        mock_menu.add_command.assert_called()

        # Find header calls
        header_calls = [c for c in mock_menu.add_command.call_args_list if c[1].get("state") == "disabled"]

        # Should have headers for "Status gerais" and "SIFAP"
        header_labels = [c[1]["label"] for c in header_calls]
        assert any("Status gerais" in label for label in header_labels)
        assert any("SIFAP" in label for label in header_labels)


# ============================================================================
# Test STATUS_PREFIX_RE
# ============================================================================


class TestStatusPrefixRegex:
    """Test STATUS_PREFIX_RE regex pattern for parsing status prefixes."""

    def test_matches_simple_prefix(self):
        """Should match simple status prefix like [Status]."""
        text = "[Aguardando documento] restante do texto"

        match = helpers.STATUS_PREFIX_RE.match(text)

        assert match is not None
        assert match.group("st") == "Aguardando documento"

    def test_matches_prefix_with_leading_whitespace(self):
        """Should match prefix with leading whitespace."""
        text = "  [Aguardando documento] restante"

        match = helpers.STATUS_PREFIX_RE.match(text)

        assert match is not None
        assert match.group("st") == "Aguardando documento"

    def test_matches_prefix_with_trailing_whitespace(self):
        """Should match prefix with trailing whitespace after bracket."""
        text = "[Aguardando documento]  restante"

        match = helpers.STATUS_PREFIX_RE.match(text)

        assert match is not None
        assert match.group("st") == "Aguardando documento"

    def test_does_not_match_without_prefix(self):
        """Should not match text without status prefix."""
        text = "texto sem prefixo"

        match = helpers.STATUS_PREFIX_RE.match(text)

        assert match is None

    def test_does_not_match_unclosed_bracket(self):
        """Should not match unclosed bracket."""
        text = "[Aguardando documento restante"

        match = helpers.STATUS_PREFIX_RE.match(text)

        assert match is None

    def test_sub_removes_prefix(self):
        """Should remove prefix when using sub()."""
        text = "[Aguardando documento] restante do texto"

        result = helpers.STATUS_PREFIX_RE.sub("", text, count=1).strip()

        assert result == "restante do texto"

    def test_sub_with_count_only_removes_first(self):
        """Should only remove first occurrence when count=1."""
        text = "[Status A] texto [Status B] mais texto"

        result = helpers.STATUS_PREFIX_RE.sub("", text, count=1).strip()

        assert result == "texto [Status B] mais texto"

    def test_sub_empty_text_after_prefix(self):
        """Should handle empty text after prefix."""
        text = "[Status A]"

        result = helpers.STATUS_PREFIX_RE.sub("", text, count=1).strip()

        assert result == ""

    def test_sub_with_whitespace_only_after_prefix(self):
        """Should handle whitespace-only text after prefix."""
        text = "[Status A]    "

        result = helpers.STATUS_PREFIX_RE.sub("", text, count=1).strip()

        assert result == ""

    def test_matches_complex_status_with_special_chars(self):
        """Should match status with spaces and special characters."""
        text = "[Follow-up amanhã] restante"

        match = helpers.STATUS_PREFIX_RE.match(text)

        assert match is not None
        assert match.group("st") == "Follow-up amanhã"

    def test_does_not_match_nested_brackets(self):
        """Should not match nested brackets (matches until first ])."""
        text = "[Status [nested]] restante"

        match = helpers.STATUS_PREFIX_RE.match(text)

        assert match is not None
        # Regex stops at first ], so captures "Status [nested"
        assert match.group("st") == "Status [nested"


# ============================================================================
# Test Module Constants
# ============================================================================


class TestModuleConstants:
    """Test module-level constants STATUS_CHOICES and STATUS_GROUPS."""

    def test_status_choices_is_list(self):
        """STATUS_CHOICES should be a list."""
        assert isinstance(helpers.STATUS_CHOICES, list)

    def test_status_choices_not_empty(self):
        """STATUS_CHOICES should not be empty."""
        assert len(helpers.STATUS_CHOICES) > 0

    def test_status_choices_contains_defaults(self):
        """STATUS_CHOICES should contain expected default values."""
        # Note: Use case-insensitive check as env vars may override
        choices_lower = [c.lower() for c in helpers.STATUS_CHOICES]
        assert "novo cliente" in choices_lower
        assert "aguardando documento" in choices_lower
        assert "análise da caixa" in choices_lower or "análise do ministério" in choices_lower

    def test_status_groups_is_list(self):
        """STATUS_GROUPS should be a list."""
        assert isinstance(helpers.STATUS_GROUPS, list)

    def test_status_groups_not_empty(self):
        """STATUS_GROUPS should not be empty."""
        assert len(helpers.STATUS_GROUPS) > 0

    def test_status_groups_structure(self):
        """Each item in STATUS_GROUPS should be (str, list[str]) tuple."""
        for item in helpers.STATUS_GROUPS:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], str)  # Group name
            assert isinstance(item[1], list)  # Status items
            assert all(isinstance(s, str) for s in item[1])

    def test_status_groups_contains_defaults(self):
        """STATUS_GROUPS should contain expected default groups."""
        group_names = [name for name, _ in helpers.STATUS_GROUPS]
        assert "Status gerais" in group_names
        assert "SIFAP" in group_names

    def test_status_choices_matches_flattened_groups(self):
        """STATUS_CHOICES should match flattened STATUS_GROUPS."""
        flattened = [label for _, values in helpers.STATUS_GROUPS for label in values]
        assert helpers.STATUS_CHOICES == flattened

    def test_default_status_groups_structure(self):
        """DEFAULT_STATUS_GROUPS should have correct structure."""
        assert isinstance(helpers.DEFAULT_STATUS_GROUPS, list)
        assert len(helpers.DEFAULT_STATUS_GROUPS) > 0

        for item in helpers.DEFAULT_STATUS_GROUPS:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_default_status_choices_not_empty(self):
        """DEFAULT_STATUS_CHOICES should not be empty."""
        assert isinstance(helpers.DEFAULT_STATUS_CHOICES, list)
        assert len(helpers.DEFAULT_STATUS_CHOICES) > 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestEnvironmentIntegration:
    """Integration tests for environment variable behavior."""

    def test_reload_with_custom_choices_affects_constants(self, monkeypatch):
        """Setting RC_STATUS_GROUPS and reloading should affect STATUS_CHOICES."""
        # Note: STATUS_CHOICES is derived from STATUS_GROUPS, not RC_STATUS_CHOICES
        groups_json = json.dumps({"Custom Group": ["Custom A", "Custom B"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)
        monkeypatch.delenv("RC_STATUS_CHOICES", raising=False)

        reloaded = importlib.reload(helpers)

        try:
            assert reloaded.STATUS_CHOICES == ["Custom A", "Custom B"]
        finally:
            importlib.reload(helpers)

    def test_reload_with_custom_groups_affects_constants(self, monkeypatch):
        """Setting RC_STATUS_GROUPS and reloading should affect STATUS_GROUPS."""
        groups_json = json.dumps({"Custom Group": ["Custom Status"]})
        monkeypatch.setenv("RC_STATUS_GROUPS", groups_json)

        reloaded = importlib.reload(helpers)

        try:
            assert reloaded.STATUS_GROUPS == [("Custom Group", ["Custom Status"])]
        finally:
            importlib.reload(helpers)

    def test_fallback_to_defaults_preserves_consistency(self, monkeypatch):
        """When falling back to defaults, STATUS_CHOICES should match flattened STATUS_GROUPS."""
        monkeypatch.delenv("RC_STATUS_CHOICES", raising=False)
        monkeypatch.delenv("RC_STATUS_GROUPS", raising=False)

        reloaded = importlib.reload(helpers)

        try:
            flattened = [label for _, values in reloaded.STATUS_GROUPS for label in values]
            assert reloaded.STATUS_CHOICES == flattened
        finally:
            importlib.reload(helpers)


__all__ = [
    "TestLoadStatusChoices",
    "TestLoadStatusGroups",
    "TestBuildStatusMenu",
    "TestStatusPrefixRegex",
    "TestModuleConstants",
    "TestEnvironmentIntegration",
]
