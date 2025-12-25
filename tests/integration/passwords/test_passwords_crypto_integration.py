"""Testes de integração com crypto real + repo fake.

FASE 6 - Validar fluxo completo de criptografia end-to-end.
"""

from __future__ import annotations

from typing import Any

import pytest
from cryptography.fernet import Fernet

from security import crypto


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def test_fernet_key() -> str:
    """Chave Fernet válida para testes (NÃO usar em produção)."""
    return Fernet.generate_key().decode("utf-8")


@pytest.fixture(autouse=True)
def reset_crypto_cache():
    """Limpa o cache singleton antes de cada teste."""
    crypto._reset_fernet_cache()
    yield
    crypto._reset_fernet_cache()


@pytest.fixture
def mock_env_with_test_key(test_fernet_key: str, monkeypatch):
    """Configura ambiente com chave de teste."""
    monkeypatch.setenv("RC_CLIENT_SECRET_KEY", test_fernet_key)
    return test_fernet_key


# ========================================
# InMemoryPasswordsRepo com criptografia
# ========================================


class InMemoryCryptoRepo:
    """Repositório em memória que simula criptografia como o Supabase real.

    Senhas são armazenadas criptografadas, como no banco de dados real.
    """

    def __init__(self) -> None:
        self._passwords: list[dict[str, Any]] = []
        self._next_id = 1

    def add_password(
        self,
        org_id: str,
        client_name: str,
        service: str,
        username: str,
        password_plain: str,
        notes: str,
        created_by: str,
        client_id: str | None = None,
    ) -> dict[str, Any]:
        """Adiciona senha criptografando o valor."""
        # Simula comportamento do supabase_repo.add_password
        password_enc = crypto.encrypt_text(password_plain) if password_plain else ""

        pwd_id = f"pwd-{self._next_id}"
        self._next_id += 1

        record = {
            "id": pwd_id,
            "org_id": org_id,
            "client_id": client_id or "",
            "client_name": client_name,
            "service": service,
            "username": username,
            "password_enc": password_enc,  # CRIPTOGRAFADO
            "notes": notes,
            "created_by": created_by,
            "created_at": "2025-12-02T00:00:00Z",
            "updated_at": "2025-12-02T00:00:00Z",
        }
        self._passwords.append(record)
        return record

    def get_password_by_id(self, password_id: str) -> dict[str, Any] | None:
        """Busca senha por ID (retorna criptografada)."""
        for pwd in self._passwords:
            if pwd["id"] == password_id:
                return pwd
        return None

    def update_password(
        self,
        password_id: str,
        password_plain: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Atualiza senha, criptografando se fornecida."""
        for pwd in self._passwords:
            if pwd["id"] == password_id:
                if password_plain is not None:
                    pwd["password_enc"] = crypto.encrypt_text(password_plain) if password_plain else ""
                for key, value in kwargs.items():
                    if value is not None and key in pwd:
                        pwd[key] = value
                return pwd
        raise ValueError(f"Password {password_id} not found")

    def delete_password(self, password_id: str) -> None:
        """Remove senha."""
        self._passwords = [p for p in self._passwords if p["id"] != password_id]

    def list_passwords(self, org_id: str) -> list[dict[str, Any]]:
        """Lista senhas (criptografadas)."""
        return [p for p in self._passwords if p.get("org_id") == org_id]

    def decrypt_password(self, password_enc: str) -> str:
        """Descriptografa uma senha."""
        return crypto.decrypt_text(password_enc)


# ========================================
# Testes de integração com crypto real
# ========================================


class TestCryptoIntegrationRoundtrip:
    """Testes de roundtrip: criar → buscar → decrypt."""

    def test_create_and_decrypt_password(
        self,
        mock_env_with_test_key: str,
    ) -> None:
        """Criar senha e descriptografar deve retornar valor original."""
        repo = InMemoryCryptoRepo()

        # Criar senha
        original_password = "minha_senha_segura_123!@#"
        created = repo.add_password(
            org_id="org-1",
            client_name="Cliente Teste",
            service="SIFAP",
            username="usuario@test.com",
            password_plain=original_password,
            notes="Nota de teste",
            created_by="user-1",
            client_id="client-1",
        )

        # Verificar que está criptografada
        assert created["password_enc"] != original_password
        assert created["password_enc"] != ""

        # Descriptografar
        decrypted = repo.decrypt_password(created["password_enc"])
        assert decrypted == original_password

    def test_create_multiple_passwords_different_encrypted(
        self,
        mock_env_with_test_key: str,
    ) -> None:
        """Mesma senha deve gerar tokens diferentes (IV único)."""
        repo = InMemoryCryptoRepo()

        same_password = "senha_igual"

        pwd1 = repo.add_password(
            org_id="org-1",
            client_name="Cliente 1",
            service="Serviço A",
            username="user1",
            password_plain=same_password,
            notes="",
            created_by="user-1",
        )

        pwd2 = repo.add_password(
            org_id="org-1",
            client_name="Cliente 2",
            service="Serviço B",
            username="user2",
            password_plain=same_password,
            notes="",
            created_by="user-1",
        )

        # Tokens devem ser diferentes (Fernet usa IV aleatório)
        assert pwd1["password_enc"] != pwd2["password_enc"]

        # Mas ambos descriptografam para o mesmo valor
        assert repo.decrypt_password(pwd1["password_enc"]) == same_password
        assert repo.decrypt_password(pwd2["password_enc"]) == same_password

    def test_update_password_re_encrypts(
        self,
        mock_env_with_test_key: str,
    ) -> None:
        """Atualizar senha deve re-criptografar."""
        repo = InMemoryCryptoRepo()

        # Criar senha inicial
        created = repo.add_password(
            org_id="org-1",
            client_name="Cliente",
            service="Serviço",
            username="user",
            password_plain="senha_antiga",
            notes="",
            created_by="user-1",
        )
        old_enc = created["password_enc"]

        # Atualizar senha
        updated = repo.update_password(
            password_id=created["id"],
            password_plain="senha_nova_segura",
        )

        # Token deve ser diferente
        assert updated["password_enc"] != old_enc

        # Novo token descriptografa para nova senha
        assert repo.decrypt_password(updated["password_enc"]) == "senha_nova_segura"

    def test_empty_password_stored_as_empty(
        self,
        mock_env_with_test_key: str,
    ) -> None:
        """Senha vazia deve ser armazenada como string vazia."""
        repo = InMemoryCryptoRepo()

        created = repo.add_password(
            org_id="org-1",
            client_name="Cliente",
            service="Serviço",
            username="user",
            password_plain="",  # Vazia
            notes="",
            created_by="user-1",
        )

        assert created["password_enc"] == ""
        assert repo.decrypt_password(created["password_enc"]) == ""


class TestCryptoIntegrationErrors:
    """Testes de erros de criptografia no fluxo."""

    def test_decrypt_with_wrong_key_fails(
        self,
        test_fernet_key: str,
        monkeypatch,
    ) -> None:
        """Descriptografar com chave diferente deve falhar."""
        # Criar com uma chave
        monkeypatch.setenv("RC_CLIENT_SECRET_KEY", test_fernet_key)
        repo = InMemoryCryptoRepo()

        created = repo.add_password(
            org_id="org-1",
            client_name="Cliente",
            service="Serviço",
            username="user",
            password_plain="senha_secreta",
            notes="",
            created_by="user-1",
        )

        # Trocar para outra chave
        new_key = Fernet.generate_key().decode("utf-8")
        crypto._reset_fernet_cache()  # IMPORTANTE: limpar cache antes de trocar chave
        monkeypatch.setenv("RC_CLIENT_SECRET_KEY", new_key)

        # TEST-001: Descriptografar deve retornar string vazia (não lança exceção)
        result = repo.decrypt_password(created["password_enc"])
        assert result == ""

    def test_decrypt_corrupted_token_fails(
        self,
        mock_env_with_test_key: str,
    ) -> None:
        """Descriptografar token corrompido deve falhar."""
        repo = InMemoryCryptoRepo()

        created = repo.add_password(
            org_id="org-1",
            client_name="Cliente",
            service="Serviço",
            username="user",
            password_plain="senha",
            notes="",
            created_by="user-1",
        )

        # Corromper o token
        corrupted = created["password_enc"][:10] + "CORRUPTED" + created["password_enc"][20:]

        # TEST-001: Descriptografar token corrompido retorna string vazia (não lança exceção)
        result = repo.decrypt_password(corrupted)
        assert result == ""

    def test_create_without_key_fails(self, monkeypatch) -> None:
        """Criar senha sem chave no ambiente deve falhar."""
        monkeypatch.delenv("RC_CLIENT_SECRET_KEY", raising=False)
        repo = InMemoryCryptoRepo()

        with pytest.raises(RuntimeError, match="RC_CLIENT_SECRET_KEY"):
            repo.add_password(
                org_id="org-1",
                client_name="Cliente",
                service="Serviço",
                username="user",
                password_plain="senha",
                notes="",
                created_by="user-1",
            )


class TestCryptoIntegrationFlow:
    """Testes de fluxo completo CRUD."""

    def test_full_crud_flow(
        self,
        mock_env_with_test_key: str,
    ) -> None:
        """Fluxo completo: Create → Read → Update → Delete."""
        repo = InMemoryCryptoRepo()
        org_id = "test-org"

        # 1. CREATE
        created = repo.add_password(
            org_id=org_id,
            client_name="Empresa XYZ",
            service="Portal Gov",
            username="xyz@gov.br",
            password_plain="senha_inicial_123",
            notes="Acesso ao portal",
            created_by="admin",
            client_id="client-xyz",
        )
        assert created["id"] == "pwd-1"

        # 2. READ - listar e descriptografar
        all_passwords = repo.list_passwords(org_id)
        assert len(all_passwords) == 1
        assert repo.decrypt_password(all_passwords[0]["password_enc"]) == "senha_inicial_123"

        # 3. UPDATE
        updated = repo.update_password(
            password_id=created["id"],
            password_plain="nova_senha_456",
            service="Portal Gov v2",
        )
        assert updated["service"] == "Portal Gov v2"
        assert repo.decrypt_password(updated["password_enc"]) == "nova_senha_456"

        # 4. DELETE
        repo.delete_password(created["id"])
        assert len(repo.list_passwords(org_id)) == 0

    def test_multiple_clients_isolation(
        self,
        mock_env_with_test_key: str,
    ) -> None:
        """Senhas de diferentes orgs/clientes devem estar isoladas."""
        repo = InMemoryCryptoRepo()

        # Criar senhas para org diferentes
        repo.add_password(
            org_id="org-1",
            client_name="Cliente A",
            service="Serviço",
            username="a@test.com",
            password_plain="senha_org1",
            notes="",
            created_by="user-1",
        )

        repo.add_password(
            org_id="org-2",
            client_name="Cliente B",
            service="Serviço",
            username="b@test.com",
            password_plain="senha_org2",
            notes="",
            created_by="user-2",
        )

        # Listar por org
        org1_passwords = repo.list_passwords("org-1")
        org2_passwords = repo.list_passwords("org-2")

        assert len(org1_passwords) == 1
        assert len(org2_passwords) == 1

        assert repo.decrypt_password(org1_passwords[0]["password_enc"]) == "senha_org1"
        assert repo.decrypt_password(org2_passwords[0]["password_enc"]) == "senha_org2"

    def test_unicode_passwords(
        self,
        mock_env_with_test_key: str,
    ) -> None:
        """Senhas com caracteres especiais/unicode devem funcionar."""
        repo = InMemoryCryptoRepo()

        special_passwords = [
            "senha_com_áçêntös",
            "密码测试",  # Chinês
            "パスワード",  # Japonês
            "🔐🔑💻",  # Emojis
            "senha\twith\ttabs\nand\nnewlines",
            "  spaces  around  ",
        ]

        for i, pwd in enumerate(special_passwords):
            created = repo.add_password(
                org_id="org-1",
                client_name=f"Cliente {i}",
                service="Serviço",
                username=f"user{i}",
                password_plain=pwd,
                notes="",
                created_by="user-1",
            )
            decrypted = repo.decrypt_password(created["password_enc"])
            assert decrypted == pwd, f"Falha para: {repr(pwd)}"
