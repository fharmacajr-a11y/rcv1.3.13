"""View principal do modulo Senhas.

Exponibiliza `PasswordsFrame`, heranca da view `PasswordsScreen`
agora em `src.modules.passwords.views.passwords_screen`, mantendo
compatibilidade com o restante do app.
"""

from __future__ import annotations

from typing import Any

from src.modules.passwords.views.passwords_screen import PasswordsScreen


class PasswordsFrame(PasswordsScreen):
    """Alias tipado para a tela principal de senhas.

    Nesta etapa não adicionamos comportamento novo; herdamos
    diretamente de `PasswordsScreen` para evitar qualquer
    mudança funcional.
    """

    # Nenhuma customização extra por enquanto.
    # O __init__ da classe base já aceita os argumentos necessários.
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
