"""Testes unitários para src/modules/passwords/service.py (funções puras)."""

from __future__ import annotations

from src.modules.passwords import service


class TestGroupPasswordsByClient:
    """Testes para group_passwords_by_client()."""

    def test_ignora_rows_sem_client_id(self):
        """Deve ignorar senhas sem client_id."""
        passwords = [
            {"client_id": None, "service": "email", "username": "user@example.com"},
            {"client_id": "", "service": "ftp", "username": "admin"},
            {"client_id": "123", "service": "ssh", "username": "root", "razao_social": "Cliente A"},
        ]
        summaries = service.group_passwords_by_client(passwords)
        assert len(summaries) == 1
        assert summaries[0].client_id == "123"

    def test_agrupa_corretamente_por_client_id(self):
        """Deve agrupar senhas pelo client_id."""
        passwords = [
            {
                "client_id": "1",
                "service": "email",
                "username": "a@b.com",
                "razao_social": "Cliente A",
                "client_external_id": 100,
            },
            {
                "client_id": "1",
                "service": "ftp",
                "username": "admin",
                "razao_social": "Cliente A",
                "client_external_id": 100,
            },
            {
                "client_id": "2",
                "service": "ssh",
                "username": "root",
                "razao_social": "Cliente B",
                "client_external_id": 200,
            },
        ]
        summaries = service.group_passwords_by_client(passwords)
        assert len(summaries) == 2
        # Verifica contagem de senhas
        client_a = next(s for s in summaries if s.client_id == "1")
        client_b = next(s for s in summaries if s.client_id == "2")
        assert client_a.passwords_count == 2
        assert client_b.passwords_count == 1

    def test_services_vem_ordenado_e_sem_duplicatas(self):
        """Deve retornar services ordenados e únicos."""
        passwords = [
            {"client_id": "1", "service": "z-service", "username": "u1", "razao_social": "Cliente A"},
            {"client_id": "1", "service": "a-service", "username": "u2", "razao_social": "Cliente A"},
            {"client_id": "1", "service": "z-service", "username": "u3", "razao_social": "Cliente A"},
            {"client_id": "1", "service": "m-service", "username": "u4", "razao_social": "Cliente A"},
        ]
        summaries = service.group_passwords_by_client(passwords)
        assert len(summaries) == 1
        assert summaries[0].services == ["a-service", "m-service", "z-service"]

    def test_ordena_summaries_por_razao_social_case_insensitive(self):
        """Deve ordenar summaries por razao_social (case-insensitive)."""
        passwords = [
            {"client_id": "3", "service": "s1", "username": "u1", "razao_social": "Zebra Corp"},
            {"client_id": "1", "service": "s2", "username": "u2", "razao_social": "Alpha Inc"},
            {"client_id": "2", "service": "s3", "username": "u3", "razao_social": "beta LLC"},
        ]
        summaries = service.group_passwords_by_client(passwords)
        assert len(summaries) == 3
        assert summaries[0].razao_social == "Alpha Inc"
        assert summaries[1].razao_social == "beta LLC"
        assert summaries[2].razao_social == "Zebra Corp"

    def test_ignora_services_vazios_ou_none(self):
        """Não deve incluir services vazios na lista."""
        passwords = [
            {"client_id": "1", "service": "valid", "username": "u1", "razao_social": "Cliente A"},
            {"client_id": "1", "service": "", "username": "u2", "razao_social": "Cliente A"},
            {"client_id": "1", "service": None, "username": "u3", "razao_social": "Cliente A"},
        ]
        summaries = service.group_passwords_by_client(passwords)
        assert len(summaries) == 1
        assert summaries[0].services == ["valid"]

    def test_display_name_com_external_id_e_razao_social(self):
        """display_name deve montar 'ID <external> – <razao>' quando ambos disponíveis."""
        passwords = [
            {
                "client_id": "123",
                "service": "s",
                "username": "u",
                "client_external_id": 456,
                "razao_social": "Acme Corp",
            }
        ]
        summaries = service.group_passwords_by_client(passwords)
        assert len(summaries) == 1
        assert summaries[0].display_name == "ID 456 – Acme Corp"

    def test_display_name_somente_razao_social(self):
        """display_name com apenas razao_social (external_id=0 ou inválido)."""
        passwords = [
            {"client_id": "123", "service": "s", "username": "u", "client_external_id": 0, "razao_social": "Foo Bar"}
        ]
        summaries = service.group_passwords_by_client(passwords)
        assert summaries[0].display_name == "Foo Bar"

    def test_display_name_fallback_para_client_id(self):
        """display_name deve usar client_id quando não há external_id nem razao_social."""
        passwords = [
            {"client_id": "abc-uuid", "service": "s", "username": "u", "client_external_id": None, "razao_social": ""}
        ]
        summaries = service.group_passwords_by_client(passwords)
        assert summaries[0].display_name == "abc-uuid"


class TestFilterPasswords:
    """Testes para filter_passwords()."""

    def test_search_text_filtra_por_client_name(self):
        """Deve filtrar por client_name (case-insensitive)."""
        passwords = [
            {"client_id": "1", "client_name": "Alpha Corp", "service": "email", "username": "user1"},
            {"client_id": "2", "client_name": "Beta Inc", "service": "ftp", "username": "user2"},
        ]
        filtered = service.filter_passwords(passwords, search_text="alpha", service_filter=None)
        assert len(filtered) == 1
        assert filtered[0]["client_name"] == "Alpha Corp"

    def test_search_text_filtra_por_service(self):
        """Deve filtrar por service (case-insensitive)."""
        passwords = [
            {"client_id": "1", "client_name": "Client A", "service": "SSH", "username": "root"},
            {"client_id": "2", "client_name": "Client B", "service": "FTP", "username": "admin"},
        ]
        filtered = service.filter_passwords(passwords, search_text="ssh", service_filter=None)
        assert len(filtered) == 1
        assert filtered[0]["service"] == "SSH"

    def test_search_text_filtra_por_username(self):
        """Deve filtrar por username (case-insensitive)."""
        passwords = [
            {"client_id": "1", "client_name": "Client A", "service": "email", "username": "alice@example.com"},
            {"client_id": "2", "client_name": "Client B", "service": "email", "username": "bob@example.com"},
        ]
        filtered = service.filter_passwords(passwords, search_text="alice", service_filter=None)
        assert len(filtered) == 1
        assert filtered[0]["username"] == "alice@example.com"

    def test_service_filter_aplica_corretamente(self):
        """Deve aplicar service_filter quando diferente de 'Todos'."""
        passwords = [
            {"client_id": "1", "client_name": "A", "service": "email", "username": "u1"},
            {"client_id": "2", "client_name": "B", "service": "ftp", "username": "u2"},
            {"client_id": "3", "client_name": "C", "service": "email", "username": "u3"},
        ]
        filtered = service.filter_passwords(passwords, search_text=None, service_filter="email")
        assert len(filtered) == 2
        assert all(p["service"] == "email" for p in filtered)

    def test_service_filter_todos_nao_filtra(self):
        """service_filter='Todos' não deve filtrar nada."""
        passwords = [
            {"client_id": "1", "client_name": "A", "service": "email", "username": "u1"},
            {"client_id": "2", "client_name": "B", "service": "ftp", "username": "u2"},
        ]
        filtered = service.filter_passwords(passwords, search_text=None, service_filter="Todos")
        assert len(filtered) == 2

    def test_combina_search_text_e_service_filter(self):
        """Deve combinar search_text + service_filter (AND)."""
        passwords = [
            {"client_id": "1", "client_name": "Alpha Corp", "service": "email", "username": "user1"},
            {"client_id": "2", "client_name": "Alpha LLC", "service": "ftp", "username": "user2"},
            {"client_id": "3", "client_name": "Beta Inc", "service": "email", "username": "user3"},
        ]
        filtered = service.filter_passwords(passwords, search_text="alpha", service_filter="email")
        assert len(filtered) == 1
        assert filtered[0]["client_name"] == "Alpha Corp"

    def test_search_text_vazio_ou_whitespace_nao_filtra(self):
        """search_text vazio ou só espaços não deve filtrar."""
        passwords = [
            {"client_id": "1", "client_name": "A", "service": "s", "username": "u"},
            {"client_id": "2", "client_name": "B", "service": "s", "username": "v"},
        ]
        filtered = service.filter_passwords(passwords, search_text="   ", service_filter=None)
        assert len(filtered) == 2

    def test_none_values_nao_causam_erro(self):
        """Campos None não devem causar exceção."""
        passwords = [
            {"client_id": "1", "client_name": None, "service": None, "username": None},
            {"client_id": "2", "client_name": "Valid", "service": "ssh", "username": "admin"},
        ]
        filtered = service.filter_passwords(passwords, search_text="valid", service_filter=None)
        assert len(filtered) == 1


class TestCoerceClientExternalId:
    """Testes para _coerce_client_external_id()."""

    def test_converte_int_valido(self):
        """Deve converter inteiro válido."""
        assert service._coerce_client_external_id(123, "fallback") == 123

    def test_converte_string_numerica(self):
        """Deve converter string numérica."""
        assert service._coerce_client_external_id("456", "fallback") == 456

    def test_usa_fallback_quando_raw_id_invalido(self):
        """Deve usar fallback quando raw_id não pode ser convertido."""
        assert service._coerce_client_external_id("abc", "789") == 789

    def test_retorna_zero_quando_ambos_invalidos(self):
        """Deve retornar 0 quando ambos raw_id e fallback são inválidos."""
        assert service._coerce_client_external_id("abc", "xyz") == 0

    def test_trata_none(self):
        """Deve tratar None adequadamente."""
        assert service._coerce_client_external_id(None, "100") == 100
