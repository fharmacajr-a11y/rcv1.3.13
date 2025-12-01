"""Testes para o PasswordsController.

Cobertura de:
- load_all_passwords (cache e retorno)
- filter_passwords (sem filtros, por texto, por serviço)
- decrypt_password (delegação para crypto)
- list_clients (delegação para repo)
- create_password, update_password, delete_password (delegação para service)
"""

from unittest.mock import patch

import pytest

from src.modules.passwords.controller import ClientPasswordsSummary, PasswordsController


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def controller():
    """Instância do controlador para testes."""
    return PasswordsController()


@pytest.fixture
def sample_passwords():
    """Senhas de exemplo para testes."""
    return [
        {
            "id": "pwd-1",
            "org_id": "org-123",
            "client_id": "cli-1",
            "client_name": "Cliente A",
            "service": "Farmácia Popular",
            "username": "admin@clientea.com",
            "password_encrypted": "encrypted-data-1",
            "notes": "Senha principal",
            "created_by": "user-1",
        },
        {
            "id": "pwd-2",
            "org_id": "org-123",
            "client_id": "cli-1",
            "client_name": "Cliente A",
            "service": "SIFAP",
            "username": "ftp_user",
            "password_encrypted": "encrypted-data-2",
            "notes": "",
            "created_by": "user-1",
        },
        {
            "id": "pwd-3",
            "org_id": "org-123",
            "client_id": "cli-2",
            "client_name": "Cliente B",
            "service": "Farmácia Popular",
            "username": "db_admin",
            "password_encrypted": "encrypted-data-3",
            "notes": "Prod DB",
            "created_by": "user-2",
        },
    ]


@pytest.fixture
def sample_clients():
    """Clientes de exemplo para testes."""
    return [
        {
            "id": "cli-1",
            "name": "Cliente A",
            "org_id": "org-123",
        },
        {
            "id": "cli-2",
            "name": "Cliente B",
            "org_id": "org-123",
        },
    ]


# ============================================================================
# TESTES - load_all_passwords()
# ============================================================================


def test_load_all_passwords_populates_cache_and_returns_list(controller, sample_passwords):
    """Testa que load_all_passwords preenche o cache e retorna a lista."""
    with patch("src.modules.passwords.service.get_passwords", return_value=sample_passwords) as mock_get:
        result = controller.load_all_passwords("ORG123")

    # Verifica chamada ao service
    mock_get.assert_called_once_with("ORG123", None, "Todos")

    # Verifica retorno
    assert result == sample_passwords
    assert len(result) == 3

    # Verifica que o cache foi atualizado
    assert controller.all_passwords == sample_passwords
    assert controller.all_passwords is controller._all_passwords


def test_load_all_passwords_replaces_previous_cache(controller, sample_passwords):
    """Testa que load_all_passwords substitui o cache anterior."""
    # Preenche cache inicial
    controller._all_passwords = [{"id": "old-1"}]

    with patch("src.modules.passwords.service.get_passwords", return_value=sample_passwords):
        controller.load_all_passwords("ORG123")

    # Cache deve ser substituído, não concatenado
    assert len(controller.all_passwords) == 3
    assert controller.all_passwords[0]["id"] == "pwd-1"


def test_load_all_passwords_empty_result(controller):
    """Testa load_all_passwords quando não há senhas."""
    with patch("src.modules.passwords.service.get_passwords", return_value=[]):
        result = controller.load_all_passwords("ORG999")

    assert result == []
    assert controller.all_passwords == []


# ============================================================================
# TESTES - filter_passwords()
# ============================================================================


def test_filter_passwords_without_filters_returns_full_cache(controller, sample_passwords):
    """Testa que filter_passwords sem filtros retorna todo o cache."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text=None, service_filter=None)

    assert len(result) == 3
    assert result == sample_passwords


def test_filter_passwords_with_empty_string_filters_returns_full_cache(controller, sample_passwords):
    """Testa que filter_passwords com strings vazias retorna todo o cache."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text="", service_filter="")

    assert len(result) == 3
    assert result == sample_passwords


def test_filter_passwords_filters_by_search_text_case_insensitive(controller, sample_passwords):
    """Testa filtro por texto de busca (case-insensitive)."""
    controller._all_passwords = sample_passwords

    # Busca por "Cliente A" (case-sensitive no dado, mas busca insensitive)
    result = controller.filter_passwords(search_text="cliente a", service_filter=None)

    assert len(result) == 2
    assert all(p["client_name"] == "Cliente A" for p in result)


def test_filter_passwords_search_text_matches_client_name(controller, sample_passwords):
    """Testa busca por texto no client_name."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text="Cliente B", service_filter=None)

    assert len(result) == 1
    assert result[0]["id"] == "pwd-3"
    assert result[0]["client_name"] == "Cliente B"


def test_filter_passwords_search_text_matches_service(controller, sample_passwords):
    """Testa busca por texto no service."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text="SIFAP", service_filter=None)

    assert len(result) == 1
    assert result[0]["id"] == "pwd-2"
    assert result[0]["service"] == "SIFAP"


def test_filter_passwords_search_text_matches_username(controller, sample_passwords):
    """Testa busca por texto no username."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text="ftp_user", service_filter=None)

    assert len(result) == 1
    assert result[0]["id"] == "pwd-2"
    assert result[0]["username"] == "ftp_user"


def test_filter_passwords_search_text_partial_match(controller, sample_passwords):
    """Testa busca parcial (substring)."""
    controller._all_passwords = sample_passwords

    # "admin" está em "admin@clientea.com" e "db_admin"
    result = controller.filter_passwords(search_text="admin", service_filter=None)

    assert len(result) == 2
    assert result[0]["id"] == "pwd-1"
    assert result[1]["id"] == "pwd-3"


def test_filter_passwords_search_text_case_insensitive_uppercase(controller, sample_passwords):
    """Testa busca case-insensitive com texto em maiúsculas."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text="FARMÁCIA", service_filter=None)

    assert len(result) == 2  # pwd-1 e pwd-3 têm "Farmácia Popular"


def test_filter_passwords_search_text_with_whitespace_trimmed(controller, sample_passwords):
    """Testa que espaços em branco são removidos da busca."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text="  Cliente A  ", service_filter=None)

    assert len(result) == 2
    assert all(p["client_name"] == "Cliente A" for p in result)


def test_filter_passwords_filters_by_service_filter_excluding_todos(controller, sample_passwords):
    """Testa filtro por serviço (excluindo 'Todos')."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text=None, service_filter="Farmácia Popular")

    assert len(result) == 2
    assert all(p["service"] == "Farmácia Popular" for p in result)


def test_filter_passwords_service_filter_sifap(controller, sample_passwords):
    """Testa filtro por serviço SIFAP."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text=None, service_filter="SIFAP")

    assert len(result) == 1
    assert result[0]["id"] == "pwd-2"
    assert result[0]["service"] == "SIFAP"


def test_filter_passwords_service_filter_todos_returns_all(controller, sample_passwords):
    """Testa que service_filter='Todos' não aplica filtro."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text=None, service_filter="Todos")

    assert len(result) == 3
    assert result == sample_passwords


def test_filter_passwords_combined_search_and_service_filter(controller, sample_passwords):
    """Testa combinação de busca por texto e filtro de serviço."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(
        search_text="Cliente A",
        service_filter="Farmácia Popular",
    )

    # Apenas pwd-1 (Cliente A + Farmácia Popular)
    assert len(result) == 1
    assert result[0]["id"] == "pwd-1"


def test_filter_passwords_search_no_matches(controller, sample_passwords):
    """Testa busca sem resultados."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text="inexistente", service_filter=None)

    assert result == []


def test_filter_passwords_service_filter_no_matches(controller, sample_passwords):
    """Testa filtro de serviço sem resultados."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text=None, service_filter="Serviço Inexistente")

    assert result == []


def test_filter_passwords_does_not_modify_original_cache(controller, sample_passwords):
    """Testa que filter_passwords não modifica o cache original."""
    controller._all_passwords = sample_passwords.copy()
    original_length = len(controller._all_passwords)

    result = controller.filter_passwords(search_text="Cliente A", service_filter=None)

    # Cache original não deve ser modificado
    assert len(controller._all_passwords) == original_length
    assert len(result) == 2  # Resultado filtrado é menor


# ============================================================================
# TESTES - decrypt_password()
# ============================================================================


def test_decrypt_password_delegates_to_crypto(controller):
    """Testa que decrypt_password delega para security.crypto.decrypt_text."""
    with patch("src.modules.passwords.controller.decrypt_text", return_value="decrypted-value") as mock_decrypt:
        result = controller.decrypt_password("ENCRYPTED")

    mock_decrypt.assert_called_once_with("ENCRYPTED")
    assert result == "decrypted-value"


def test_decrypt_password_multiple_calls(controller):
    """Testa múltiplas chamadas de decrypt_password."""
    with patch("src.modules.passwords.controller.decrypt_text", side_effect=["pass1", "pass2"]) as mock_decrypt:
        result1 = controller.decrypt_password("ENC1")
        result2 = controller.decrypt_password("ENC2")

    assert mock_decrypt.call_count == 2
    assert result1 == "pass1"
    assert result2 == "pass2"


# ============================================================================
# TESTES - list_clients()
# ============================================================================


def test_list_clients_delegates_to_repo(controller, sample_clients):
    """Testa que list_clients delega para data.supabase_repo.list_clients_for_picker."""
    with patch("src.modules.passwords.controller.list_clients_for_picker", return_value=sample_clients) as mock_list:
        result = controller.list_clients("ORG123")

    mock_list.assert_called_once_with("ORG123")
    assert result == sample_clients
    assert len(result) == 2


def test_list_clients_empty_result(controller):
    """Testa list_clients quando não há clientes."""
    with patch("src.modules.passwords.controller.list_clients_for_picker", return_value=[]):
        result = controller.list_clients("ORG999")

    assert result == []


# ============================================================================
# TESTES - create_password()
# ============================================================================


def test_create_password_delegates_to_service(controller):
    """Testa que create_password delega para passwords_service.create_password."""
    with patch("src.modules.passwords.service.create_password") as mock_create:
        controller.create_password(
            org_id="ORG123",
            client_id="CLI456",
            client_name="Cliente X",
            service="Email",
            username="user@example.com",
            password="secret123",
            notes="Notas importantes",
            user_id="USER789",
        )

    mock_create.assert_called_once_with(
        "ORG123",
        "Cliente X",
        "Email",
        "user@example.com",
        "secret123",
        "Notas importantes",
        "USER789",
        "CLI456",
    )


def test_create_password_with_empty_notes(controller):
    """Testa create_password com notas vazias."""
    with patch("src.modules.passwords.service.create_password") as mock_create:
        controller.create_password(
            org_id="ORG123",
            client_id="CLI456",
            client_name="Cliente Y",
            service="FTP",
            username="ftpuser",
            password="pass456",
            notes="",
            user_id="USER789",
        )

    # Verifica que notes vazias são passadas corretamente
    assert mock_create.call_args[0][5] == ""


# ============================================================================
# TESTES - update_password()
# ============================================================================


def test_update_password_delegates_to_service(controller):
    """Testa que update_password delega para passwords_service.update_password_by_id."""
    with patch("src.modules.passwords.service.update_password_by_id") as mock_update:
        controller.update_password(
            password_id="PWD123",
            client_id="CLI456",
            client_name="Cliente Z",
            service="SSH",
            username="root",
            password_plain="newpass789",
            notes="Atualizado",
        )

    mock_update.assert_called_once_with(
        "PWD123",
        client_id="CLI456",
        client_name="Cliente Z",
        service="SSH",
        username="root",
        password_plain="newpass789",
        notes="Atualizado",
    )


def test_update_password_with_none_client_id(controller):
    """Testa update_password com client_id=None."""
    with patch("src.modules.passwords.service.update_password_by_id") as mock_update:
        controller.update_password(
            password_id="PWD123",
            client_id=None,
            client_name="Cliente W",
            service="API",
            username="api_user",
            password_plain="apikey",
            notes="",
        )

    # Verifica que client_id=None é passado corretamente
    assert mock_update.call_args[1]["client_id"] is None


# ============================================================================
# TESTES - delete_password()
# ============================================================================


def test_delete_password_delegates_to_service(controller):
    """Testa que delete_password delega para passwords_service.delete_password_by_id."""
    with patch("src.modules.passwords.service.delete_password_by_id") as mock_delete:
        controller.delete_password("PWD999")

    mock_delete.assert_called_once_with("PWD999")


def test_delete_password_multiple_calls(controller):
    """Testa múltiplas exclusões de senhas."""
    with patch("src.modules.passwords.service.delete_password_by_id") as mock_delete:
        controller.delete_password("PWD1")
        controller.delete_password("PWD2")
        controller.delete_password("PWD3")

    assert mock_delete.call_count == 3
    mock_delete.assert_any_call("PWD1")
    mock_delete.assert_any_call("PWD2")
    mock_delete.assert_any_call("PWD3")


# ============================================================================
# TESTES - delete_all_passwords_for_client() (FIX-SENHAS-006)
# ============================================================================


def test_delete_all_passwords_for_client_delegates_to_service(controller):
    """Testa que delete_all_passwords_for_client delega para o service."""
    with patch("src.modules.passwords.service.delete_all_passwords_for_client", return_value=3) as mock_delete:
        result = controller.delete_all_passwords_for_client("ORG123", "CLI456")

    mock_delete.assert_called_once_with("ORG123", "CLI456")
    assert result == 3


def test_delete_all_passwords_for_client_returns_count(controller):
    """Testa que delete_all_passwords_for_client retorna o número de senhas excluídas."""
    with patch("src.modules.passwords.service.delete_all_passwords_for_client", return_value=5):
        result = controller.delete_all_passwords_for_client("ORG999", "CLI789")

    assert result == 5


def test_delete_all_passwords_for_client_zero_deleted(controller):
    """Testa delete_all_passwords_for_client quando cliente não tem senhas."""
    with patch("src.modules.passwords.service.delete_all_passwords_for_client", return_value=0):
        result = controller.delete_all_passwords_for_client("ORG123", "CLI-INEXISTENTE")

    assert result == 0


# ============================================================================
# TESTES - EDGE CASES
# ============================================================================


def test_all_passwords_property_returns_cache(controller, sample_passwords):
    """Testa que a property all_passwords retorna o cache interno."""
    controller._all_passwords = sample_passwords

    result = controller.all_passwords

    assert result is controller._all_passwords
    assert result == sample_passwords


def test_controller_initialization_empty_cache(controller):
    """Testa que o controller é inicializado com cache vazio."""
    assert controller.all_passwords == []
    assert isinstance(controller.all_passwords, list)


def test_filter_passwords_empty_cache(controller):
    """Testa filter_passwords com cache vazio."""
    result = controller.filter_passwords(search_text="qualquer", service_filter=None)

    assert result == []


def test_filter_passwords_preserves_order(controller, sample_passwords):
    """Testa que filter_passwords preserva a ordem original."""
    controller._all_passwords = sample_passwords

    result = controller.filter_passwords(search_text="Cliente", service_filter=None)

    # Ordem deve ser preservada: pwd-1, pwd-2, pwd-3
    assert result[0]["id"] == "pwd-1"
    assert result[1]["id"] == "pwd-2"
    assert result[2]["id"] == "pwd-3"


# ============================================================================
# TESTES - group_passwords_by_client()
# ============================================================================


def test_group_passwords_by_client_groups_and_counts_correctly(controller):
    """Testa agrupamento de senhas por cliente com contagem correta."""
    controller._all_passwords = [
        {
            "id": "pwd-1",
            "client_id": "cli-1",
            "client_name": "Cliente A",
            "client_external_id": "256",
            "razao_social": "Cliente A Ltda",
            "cnpj": "12.345.678/0001-90",
            "nome": "João Silva",
            "whatsapp": "(11) 98765-4321",
            "service": "ANVISA",
            "username": "user1",
        },
        {
            "id": "pwd-2",
            "client_id": "cli-1",
            "client_name": "Cliente A",
            "client_external_id": "256",
            "razao_social": "Cliente A Ltda",
            "cnpj": "12.345.678/0001-90",
            "nome": "João Silva",
            "whatsapp": "(11) 98765-4321",
            "service": "SIFAP",
            "username": "user2",
        },
        {
            "id": "pwd-3",
            "client_id": "cli-2",
            "client_name": "Cliente B",
            "client_external_id": "293",
            "razao_social": "Cliente B S.A.",
            "cnpj": "98.765.432/0001-10",
            "nome": "Maria Santos",
            "whatsapp": "(21) 91234-5678",
            "service": "Farmácia Popular",
            "username": "user3",
        },
    ]

    result = controller.group_passwords_by_client()

    # Deve ter 2 clientes distintos
    assert len(result) == 2

    # Busca resumo do Cliente A
    cli_a = next((s for s in result if s.client_id == "cli-1"), None)
    assert cli_a is not None
    assert cli_a.client_external_id == 256
    assert cli_a.razao_social == "Cliente A Ltda"
    assert cli_a.cnpj == "12.345.678/0001-90"
    assert cli_a.contato_nome == "João Silva"
    assert cli_a.whatsapp == "(11) 98765-4321"
    assert cli_a.passwords_count == 2
    assert set(cli_a.services) == {"ANVISA", "SIFAP"}

    # Busca resumo do Cliente B
    cli_b = next((s for s in result if s.client_id == "cli-2"), None)
    assert cli_b is not None
    assert cli_b.client_external_id == 293
    assert cli_b.razao_social == "Cliente B S.A."
    assert cli_b.passwords_count == 1
    assert cli_b.services == ["Farmácia Popular"]


def test_group_passwords_by_client_empty_cache(controller):
    """Testa agrupamento com cache vazio."""
    controller._all_passwords = []

    result = controller.group_passwords_by_client()

    assert result == []


def test_group_passwords_by_client_sorts_alphabetically(controller):
    """Testa que group_passwords_by_client ordena alfabeticamente."""
    controller._all_passwords = [
        {
            "id": "pwd-1",
            "client_id": "cli-1",
            "client_name": "Zebra Corp",
            "razao_social": "Zebra Corp Ltda",
            "cnpj": "",
            "nome": "",
            "whatsapp": "",
            "client_external_id": "100",
            "service": "Email",
        },
        {
            "id": "pwd-2",
            "client_id": "cli-2",
            "client_name": "Alpha Inc",
            "razao_social": "Alpha Inc S.A.",
            "cnpj": "",
            "nome": "",
            "whatsapp": "",
            "client_external_id": "200",
            "service": "FTP",
        },
    ]

    result = controller.group_passwords_by_client()

    # Alpha deve vir antes de Zebra
    assert result[0].razao_social == "Alpha Inc S.A."
    assert result[1].razao_social == "Zebra Corp Ltda"


def test_group_passwords_by_client_sorts_services(controller):
    """Testa que os serviços são ordenados alfabeticamente."""
    controller._all_passwords = [
        {
            "id": "pwd-1",
            "client_id": "cli-1",
            "client_name": "Cliente X",
            "razao_social": "Cliente X Corp",
            "cnpj": "",
            "nome": "",
            "whatsapp": "",
            "client_external_id": "300",
            "service": "SIFAP",
        },
        {
            "id": "pwd-2",
            "client_id": "cli-1",
            "client_name": "Cliente X",
            "razao_social": "Cliente X Corp",
            "cnpj": "",
            "nome": "",
            "whatsapp": "",
            "client_external_id": "300",
            "service": "ANVISA",
        },
        {
            "id": "pwd-3",
            "client_id": "cli-1",
            "client_name": "Cliente X",
            "razao_social": "Cliente X Corp",
            "cnpj": "",
            "nome": "",
            "whatsapp": "",
            "client_external_id": "300",
            "service": "Farmácia Popular",
        },
    ]

    result = controller.group_passwords_by_client()

    assert len(result) == 1
    # Serviços devem estar ordenados
    assert result[0].services == ["ANVISA", "Farmácia Popular", "SIFAP"]


def test_group_passwords_by_client_ignores_empty_client_id(controller):
    """Testa que senhas sem client_id são ignoradas."""
    controller._all_passwords = [
        {
            "id": "pwd-1",
            "client_id": "cli-1",
            "client_name": "Cliente A",
            "razao_social": "Cliente A Corp",
            "cnpj": "",
            "nome": "",
            "whatsapp": "",
            "client_external_id": "400",
            "service": "Email",
        },
        {
            "id": "pwd-2",
            "client_id": "",
            "client_name": "Sem ID",
            "razao_social": "Sem ID Corp",
            "cnpj": "",
            "nome": "",
            "whatsapp": "",
            "client_external_id": "",
            "service": "FTP",
        },
    ]

    result = controller.group_passwords_by_client()

    # Apenas cliente com ID válido
    assert len(result) == 1
    assert result[0].client_id == "cli-1"


# ============================================================================
# TESTES - get_passwords_for_client()
# ============================================================================


def test_get_passwords_for_client_filters_correctly(controller):
    """Testa que get_passwords_for_client filtra por client_id."""
    controller._all_passwords = [
        {"id": "pwd-1", "client_id": "cli-1", "service": "ANVISA"},
        {"id": "pwd-2", "client_id": "cli-1", "service": "SIFAP"},
        {"id": "pwd-3", "client_id": "cli-2", "service": "Email"},
    ]

    result = controller.get_passwords_for_client("cli-1")

    assert len(result) == 2
    assert all(p["client_id"] == "cli-1" for p in result)
    assert result[0]["id"] == "pwd-1"
    assert result[1]["id"] == "pwd-2"


def test_get_passwords_for_client_empty_result(controller):
    """Testa get_passwords_for_client quando cliente não tem senhas."""
    controller._all_passwords = [
        {"id": "pwd-1", "client_id": "cli-1", "service": "Email"},
    ]

    result = controller.get_passwords_for_client("cli-999")

    assert result == []


def test_get_passwords_for_client_empty_cache(controller):
    """Testa get_passwords_for_client com cache vazio."""
    controller._all_passwords = []

    result = controller.get_passwords_for_client("cli-1")

    assert result == []


# ============================================================================
# TESTES - find_duplicate_passwords_by_service()
# ============================================================================


def test_find_duplicate_passwords_by_service_delegates_to_service(controller):
    """Testa que find_duplicate_passwords_by_service delega para o service."""
    fake_duplicates = [
        {"id": "pwd-1", "client_id": "cli-1", "service": "ANVISA"},
    ]

    with patch(
        "src.modules.passwords.service.find_duplicate_password_by_service",
        return_value=fake_duplicates,
    ) as mock_find:
        result = controller.find_duplicate_passwords_by_service(
            org_id="ORG123",
            client_id="cli-1",
            service="ANVISA",
        )

    mock_find.assert_called_once_with(
        org_id="ORG123",
        client_id="cli-1",
        service="ANVISA",
    )
    assert result == fake_duplicates


def test_find_duplicate_passwords_by_service_no_duplicates(controller):
    """Testa find_duplicate_passwords_by_service quando não há duplicatas."""
    with patch(
        "src.modules.passwords.service.find_duplicate_password_by_service",
        return_value=[],
    ):
        result = controller.find_duplicate_passwords_by_service(
            org_id="ORG123",
            client_id="cli-1",
            service="SIFAP",
        )

    assert result == []


# ============================================================================
# TESTES - ClientPasswordsSummary.display_name
# ============================================================================


def test_client_passwords_summary_display_name_uses_external_id_razao_social_and_cnpj():
    """Testa que display_name formata corretamente ID e razão social (sem CNPJ)."""
    summary = ClientPasswordsSummary(
        client_id="uuid-123",
        client_external_id=336,
        razao_social="A DE LIMA FARMACIA",
        cnpj="05788603000113",
        contato_nome="Alexandre de Lima",
        whatsapp="5514999999999",
        passwords_count=2,
        services=["CRF"],
    )

    assert "ID 336" in summary.display_name
    assert "A DE LIMA FARMACIA" in summary.display_name
    assert "05788603000113" not in summary.display_name  # FIX-SENHAS-011: CNPJ não deve estar no display_name


def test_client_passwords_summary_display_name_without_cnpj():
    """Testa display_name quando CNPJ está vazio."""
    summary = ClientPasswordsSummary(
        client_id="uuid-456",
        client_external_id=100,
        razao_social="Farmácia Exemplo",
        cnpj="",
        contato_nome="João Silva",
        whatsapp="11999999999",
        passwords_count=1,
        services=["SIFAP"],
    )

    assert "ID 100" in summary.display_name
    assert "Farmácia Exemplo" in summary.display_name
    assert "(" not in summary.display_name  # Sem CNPJ, não deve ter parênteses


def test_client_passwords_summary_display_name_minimal_data():
    """Testa display_name com dados mínimos."""
    summary = ClientPasswordsSummary(
        client_id="uuid-789",
        client_external_id=789,
        razao_social="",
        cnpj="",
        contato_nome="",
        whatsapp="",
        passwords_count=0,
        services=[],
    )

    # Com external_id mas sem razão social, deve mostrar o ID
    assert "ID 789" in summary.display_name


def test_client_passwords_summary_display_name_never_includes_cnpj():
    """FIX-SENHAS-011: Testa que display_name NUNCA inclui CNPJ."""
    summary_with_cnpj = ClientPasswordsSummary(
        client_id="uuid-999",
        client_external_id=999,
        razao_social="FARMACIA TESTE LTDA",
        cnpj="12345678000199",
        contato_nome="Teste",
        whatsapp="11999999999",
        passwords_count=5,
        services=["CRF", "SIFAP"],
    )

    assert "ID 999" in summary_with_cnpj.display_name
    assert "FARMACIA TESTE LTDA" in summary_with_cnpj.display_name
    assert "12345678000199" not in summary_with_cnpj.display_name
    assert "(" not in summary_with_cnpj.display_name
    assert ")" not in summary_with_cnpj.display_name
