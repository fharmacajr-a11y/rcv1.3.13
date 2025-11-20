"""Service fino para o módulo Senhas.

Este arquivo expõe uma API estável para operações relacionadas
a senhas, a partir do código legado em
`infra.repositories.passwords_repository`.

Por enquanto, apenas reexporta as funções públicas do repositório,
sem adicionar lógica nova.
"""

from __future__ import annotations

from infra.repositories import passwords_repository

# Reexports finos – mantêm a assinatura do repositório legado
get_passwords = passwords_repository.get_passwords
create_password = passwords_repository.create_password
update_password_by_id = passwords_repository.update_password_by_id
delete_password_by_id = passwords_repository.delete_password_by_id

__all__ = [
    "get_passwords",
    "create_password",
    "update_password_by_id",
    "delete_password_by_id",
]
