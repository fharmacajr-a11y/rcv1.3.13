"""Testes para src/utils/storage_utils.py."""

from __future__ import annotations


from src.utils.storage_utils import get_bucket_name


class TestGetBucketName:
    """Testes para a função get_bucket_name."""

    def test_explicit_parameter_has_highest_priority(self, monkeypatch):
        """Quando explicit é fornecido, deve retorná-lo ignorando env vars."""
        monkeypatch.setenv("RC_STORAGE_BUCKET_CLIENTS", "env-clients")
        monkeypatch.setenv("SUPABASE_BUCKET", "env-legacy")

        result = get_bucket_name(explicit="custom-bucket")

        assert result == "custom-bucket"

    def test_explicit_parameter_with_whitespace_is_stripped(self, monkeypatch):
        """Explicit com espaços em branco deve ser normalizado."""
        monkeypatch.delenv("RC_STORAGE_BUCKET_CLIENTS", raising=False)
        monkeypatch.delenv("SUPABASE_BUCKET", raising=False)

        result = get_bucket_name(explicit="  custom-bucket  ")

        assert result == "custom-bucket"

    def test_rc_storage_bucket_clients_has_second_priority(self, monkeypatch):
        """RC_STORAGE_BUCKET_CLIENTS deve ser usado quando explicit não é fornecido."""
        monkeypatch.setenv("RC_STORAGE_BUCKET_CLIENTS", "clients-bucket")
        monkeypatch.setenv("SUPABASE_BUCKET", "legacy-bucket")

        result = get_bucket_name()

        assert result == "clients-bucket"

    def test_rc_storage_bucket_clients_with_whitespace_is_stripped(self, monkeypatch):
        """RC_STORAGE_BUCKET_CLIENTS com espaços deve ser normalizado."""
        monkeypatch.setenv("RC_STORAGE_BUCKET_CLIENTS", "  clients-bucket  ")
        monkeypatch.delenv("SUPABASE_BUCKET", raising=False)

        result = get_bucket_name()

        assert result == "clients-bucket"

    def test_supabase_bucket_has_third_priority(self, monkeypatch):
        """SUPABASE_BUCKET deve ser usado quando explicit e RC_STORAGE_BUCKET_CLIENTS não existem."""
        monkeypatch.delenv("RC_STORAGE_BUCKET_CLIENTS", raising=False)
        monkeypatch.setenv("SUPABASE_BUCKET", "legacy-bucket")

        result = get_bucket_name()

        assert result == "legacy-bucket"

    def test_supabase_bucket_with_whitespace_is_stripped(self, monkeypatch):
        """SUPABASE_BUCKET com espaços deve ser normalizado."""
        monkeypatch.delenv("RC_STORAGE_BUCKET_CLIENTS", raising=False)
        monkeypatch.setenv("SUPABASE_BUCKET", "  legacy-bucket  ")

        result = get_bucket_name()

        assert result == "legacy-bucket"

    def test_fallback_to_rc_docs_when_no_source_available(self, monkeypatch):
        """Deve retornar 'rc-docs' quando nenhuma fonte está disponível."""
        monkeypatch.delenv("RC_STORAGE_BUCKET_CLIENTS", raising=False)
        monkeypatch.delenv("SUPABASE_BUCKET", raising=False)

        result = get_bucket_name()

        assert result == "rc-docs"

    def test_fallback_when_explicit_is_none(self, monkeypatch):
        """Deve usar env vars quando explicit é None."""
        monkeypatch.setenv("RC_STORAGE_BUCKET_CLIENTS", "clients-bucket")

        result = get_bucket_name(explicit=None)

        assert result == "clients-bucket"

    def test_fallback_when_explicit_is_empty_string(self, monkeypatch):
        """Deve usar env vars quando explicit é string vazia."""
        monkeypatch.setenv("RC_STORAGE_BUCKET_CLIENTS", "clients-bucket")

        result = get_bucket_name(explicit="")

        assert result == "clients-bucket"

    def test_fallback_when_explicit_is_whitespace_only(self, monkeypatch):
        """Deve usar env vars quando explicit contém apenas espaços."""
        monkeypatch.setenv("RC_STORAGE_BUCKET_CLIENTS", "clients-bucket")

        result = get_bucket_name(explicit="   ")

        assert result == "clients-bucket"

    def test_fallback_when_rc_storage_is_empty_string(self, monkeypatch):
        """Deve pular RC_STORAGE_BUCKET_CLIENTS se for string vazia."""
        monkeypatch.setenv("RC_STORAGE_BUCKET_CLIENTS", "")
        monkeypatch.setenv("SUPABASE_BUCKET", "legacy-bucket")

        result = get_bucket_name()

        assert result == "legacy-bucket"

    def test_fallback_when_rc_storage_is_whitespace_only(self, monkeypatch):
        """Deve pular RC_STORAGE_BUCKET_CLIENTS se contiver apenas espaços."""
        monkeypatch.setenv("RC_STORAGE_BUCKET_CLIENTS", "   ")
        monkeypatch.setenv("SUPABASE_BUCKET", "legacy-bucket")

        result = get_bucket_name()

        assert result == "legacy-bucket"

    def test_fallback_when_supabase_bucket_is_empty_string(self, monkeypatch):
        """Deve usar fallback se SUPABASE_BUCKET for string vazia."""
        monkeypatch.delenv("RC_STORAGE_BUCKET_CLIENTS", raising=False)
        monkeypatch.setenv("SUPABASE_BUCKET", "")

        result = get_bucket_name()

        assert result == "rc-docs"

    def test_fallback_when_supabase_bucket_is_whitespace_only(self, monkeypatch):
        """Deve usar fallback se SUPABASE_BUCKET contiver apenas espaços."""
        monkeypatch.delenv("RC_STORAGE_BUCKET_CLIENTS", raising=False)
        monkeypatch.setenv("SUPABASE_BUCKET", "   ")

        result = get_bucket_name()

        assert result == "rc-docs"

    def test_all_sources_empty_returns_fallback(self, monkeypatch):
        """Quando todas as fontes são vazias/whitespace, retorna fallback."""
        monkeypatch.setenv("RC_STORAGE_BUCKET_CLIENTS", "  ")
        monkeypatch.setenv("SUPABASE_BUCKET", "")

        result = get_bucket_name(explicit="   ")

        assert result == "rc-docs"

    def test_explicit_with_special_characters(self, monkeypatch):
        """Deve aceitar nomes com caracteres especiais."""
        monkeypatch.delenv("RC_STORAGE_BUCKET_CLIENTS", raising=False)
        monkeypatch.delenv("SUPABASE_BUCKET", raising=False)

        result = get_bucket_name(explicit="my-bucket_2024.v1")

        assert result == "my-bucket_2024.v1"

    def test_env_var_with_special_characters(self, monkeypatch):
        """Deve aceitar env var com caracteres especiais."""
        monkeypatch.setenv("RC_STORAGE_BUCKET_CLIENTS", "client-bucket_prod.2024")
        monkeypatch.delenv("SUPABASE_BUCKET", raising=False)

        result = get_bucket_name()

        assert result == "client-bucket_prod.2024"
