from __future__ import annotations

import sys
from unittest.mock import MagicMock


def test_magicmock_module_added_forgets_without_cleanup() -> None:
    sys.modules["src.utils.errors"] = MagicMock()
    assert isinstance(sys.modules["src.utils.errors"], MagicMock)


def test_magicmock_module_is_cleared_before_next_test() -> None:
    assert not isinstance(sys.modules.get("src.utils.errors"), MagicMock)
