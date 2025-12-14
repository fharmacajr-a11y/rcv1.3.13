# -*- coding: utf-8 -*-
"""Repositório para operações com senhas.

Este módulo fornece uma camada de abstração para gerenciar senhas de clientes,
delegando operações de persistência para o Supabase através de data.supabase_repo.

Funcionalidades:
- Listar senhas com filtros (texto, cliente)
- Criar novas senhas
- Atualizar senhas existentes
- Excluir senhas

Note:
    As senhas são armazenadas de forma criptografada no Supabase.
    Este repositório cuida apenas da lógica de negócio, não da criptografia.
"""

from __future__ import annotations

from data.domain_types import PasswordRow


def get_passwords(
    org_id: str,
    search_text: str | None = None,
    client_filter: str | None = None,
) -> list[PasswordRow]:
    """Lista senhas com filtros opcionais.

    Args:
        org_id: ID da organização proprietária das senhas
        search_text: Texto para buscar em client_name, service ou username (case-insensitive)
        client_filter: Filtro por nome do cliente (None ou "Todos" = sem filtro)

    Returns:
        Lista de senhas que atendem aos critérios de filtro

    Example:
        >>> senhas = get_passwords("org-123", search_text="gmail")
        >>> senhas_cliente = get_passwords("org-123", client_filter="Empresa XYZ")
    """
    from data.supabase_repo import list_passwords

    passwords: list[PasswordRow] = list_passwords(org_id)

    if search_text:
        search_lower: str = search_text.lower()
        passwords = [
            password
            for password in passwords
            if search_lower in password["client_name"].lower()
            or search_lower in password["service"].lower()
            or search_lower in password["username"].lower()
        ]

    if client_filter and client_filter != "Todos":
        passwords = [password for password in passwords if password["client_name"] == client_filter]

    return passwords


def create_password(
    org_id: str,
    client_name: str,
    service: str,
    username: str,
    password_plain: str,
    notes: str,
    created_by: str,
    client_id: str | None = None,
) -> PasswordRow:
    """Cria uma nova senha no repositório.

    Args:
        org_id: ID da organização proprietária
        client_name: Nome do cliente
        service: Nome do serviço (ex: "Gmail", "AWS Console")
        username: Nome de usuário/email para login
        password_plain: Senha em texto plano (será criptografada pelo supabase_repo)
        notes: Observações adicionais
        created_by: ID do usuário que criou o registro
        client_id: ID do cliente (opcional, se selecionado via modo pick)

    Returns:
        Registro da senha criada com todos os campos (incluindo ID gerado)

    Example:
        >>> nova_senha = create_password(
        ...     org_id="org-123",
        ...     client_name="Empresa XYZ",
        ...     service="Gmail",
        ...     username="contato@empresa.com",
        ...     password_plain="senhaSegura123",
        ...     notes="Conta compartilhada do time",
        ...     created_by="user-456",
        ...     client_id="256"
        ... )
    """
    from data.supabase_repo import add_password

    return add_password(org_id, client_name, service, username, password_plain, notes, created_by, client_id)


def update_password_by_id(
    password_id: str,
    client_name: str | None = None,
    service: str | None = None,
    username: str | None = None,
    password_plain: str | None = None,
    notes: str | None = None,
    client_id: str | None = None,
) -> PasswordRow:
    """Atualiza uma senha existente (campos opcionais).

    Args:
        password_id: ID da senha a ser atualizada
        client_name: Novo nome do cliente (None = manter atual)
        service: Novo nome do serviço (None = manter atual)
        username: Novo username (None = manter atual)
        password_plain: Nova senha em texto plano (None = manter atual)
        notes: Novas observações (None = manter atual)
        client_id: Novo ID do cliente (None = manter atual)

    Returns:
        Registro da senha atualizada

    Example:
        >>> senha = update_password_by_id(
        ...     password_id="pwd-789",
        ...     password_plain="novaSenha456",
        ...     notes="Senha atualizada em 2025-11",
        ...     client_id="256"
        ... )
    """
    from data.supabase_repo import update_password

    return update_password(password_id, client_name, service, username, password_plain, notes, client_id)


def delete_password_by_id(password_id: str) -> None:
    """Exclui uma senha do repositório.

    Args:
        password_id: ID da senha a ser excluída

    Returns:
        None

    Example:
        >>> delete_password_by_id("pwd-789")

    Note:
        Esta operação é irreversível. Recomenda-se confirmar com o usuário antes de executar.
    """
    from data.supabase_repo import delete_password

    delete_password(password_id)


def delete_all_passwords_for_client(org_id: str, client_id: str) -> int:
    """Exclui todas as senhas de um cliente.

    Args:
        org_id: ID da organização proprietária
        client_id: ID do cliente cujas senhas serão excluídas

    Returns:
        Número de senhas excluídas

    Example:
        >>> count = delete_all_passwords_for_client("org-123", "256")
        >>> print(f"{count} senha(s) excluída(s)")

    Note:
        Esta operação é irreversível. Recomenda-se confirmar com o usuário antes de executar.
    """
    from data.supabase_repo import delete_passwords_by_client

    return delete_passwords_by_client(org_id, client_id)


def find_duplicate_password_by_service(
    org_id: str,
    client_id: str,
    service: str,
) -> list[PasswordRow]:
    """Retorna todas as senhas para o mesmo (cliente + serviço).

    Usado para detectar duplicidade antes de criar nova senha.
    A chave de duplicidade é (org_id, client_id, service).

    Args:
        org_id: ID da organização
        client_id: ID do cliente
        service: Nome do serviço

    Returns:
        Lista de senhas que correspondem a essa combinação (pode ser vazia)

    Example:
        >>> duplicates = find_duplicate_password_by_service(
        ...     org_id="org-123",
        ...     client_id="256",
        ...     service="ANVISA"
        ... )
        >>> if duplicates:
        ...     print("Já existe senha para este serviço")
    """
    from data.supabase_repo import list_passwords

    all_passwords: list[PasswordRow] = list_passwords(org_id)

    return [
        password
        for password in all_passwords
        if password.get("client_id") == client_id and password.get("service") == service
    ]
