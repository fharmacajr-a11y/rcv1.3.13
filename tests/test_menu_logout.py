from __future__ import annotations

import pytest

# Este modulo existe apenas para impedir que o pytest carregue a versao legada
# de test_menu_logout localizada em outra pasta (ex.: v1.2.76), que inicializa
# Tkinter/ttkbootstrap e threads do Supabase e pode causar crash no Windows
# com Python 3.13. Na v1.2.88, os fluxos de menu/logout ja estao cobertos por
# outros testes; este arquivo e mantido como "skip global" apenas para sombrear
# o teste antigo.
pytest.skip(
    "Legacy UI test (menu/logout) from older version disabled in v1.2.88; "
    "this module exists to shadow the old test_menu_logout and avoid Tk/threads crash.",
    allow_module_level=True,
)
