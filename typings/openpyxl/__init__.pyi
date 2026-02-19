"""Type stubs para openpyxl (subset usado no projeto)."""

from typing import Any

class Workbook:
    """Workbook class stub."""

    active: Any

    def __init__(self) -> None: ...
    def save(self, filename: Any) -> None: ...

def load_workbook(filename: Any, *args: Any, **kwargs: Any) -> Any:
    """Load workbook stub."""
    ...
