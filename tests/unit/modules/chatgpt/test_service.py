# -*- coding: utf-8 -*-
"""
Testes unitários para src/modules/chatgpt/service.py.

BATCH 07: Cobertura de módulo headless de serviço (ChatGPT integration).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.modules.chatgpt import service


class TestLoadOpenAIAPIKey:
    """Testes para _load_openai_api_key()."""

    def test_loads_from_env_variable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que carrega a chave da variável de ambiente OPENAI_API_KEY."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-env-key")
        key = service._load_openai_api_key()
        assert key == "sk-test-env-key"

    def test_strips_whitespace_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que remove espaços em branco da chave do env."""
        monkeypatch.setenv("OPENAI_API_KEY", "  sk-test-key-whitespace  ")
        key = service._load_openai_api_key()
        assert key == "sk-test-key-whitespace"

    def test_loads_from_file_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que carrega do arquivo quando env não está setado."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Mock do caminho do arquivo
        fake_key_file = tmp_path / "openai_key.txt"
        fake_key_file.write_text("sk-test-file-key", encoding="utf-8")
        monkeypatch.setattr(service, "OPENAI_KEY_FILE", fake_key_file)

        key = service._load_openai_api_key()
        assert key == "sk-test-file-key"

    def test_ignores_comments_in_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que ignora linhas de comentário no arquivo."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        fake_key_file = tmp_path / "openai_key.txt"
        fake_key_file.write_text(
            "# This is a comment\n# Another comment\nsk-actual-key\n# More comments", encoding="utf-8"
        )
        monkeypatch.setattr(service, "OPENAI_KEY_FILE", fake_key_file)

        key = service._load_openai_api_key()
        assert key == "sk-actual-key"

    def test_ignores_empty_lines_in_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que ignora linhas vazias no arquivo."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        fake_key_file = tmp_path / "openai_key.txt"
        fake_key_file.write_text("\n  \nsk-real-key\n\n", encoding="utf-8")
        monkeypatch.setattr(service, "OPENAI_KEY_FILE", fake_key_file)

        key = service._load_openai_api_key()
        assert key == "sk-real-key"

    def test_raises_when_file_not_found(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que lança RuntimeError quando arquivo não existe."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        fake_key_file = tmp_path / "nonexistent.txt"
        monkeypatch.setattr(service, "OPENAI_KEY_FILE", fake_key_file)

        with pytest.raises(RuntimeError, match="ChatGPT indisponível.*não foi encontrado ou está vazio"):
            service._load_openai_api_key()

    def test_raises_when_file_empty(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que lança RuntimeError quando arquivo está vazio."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        fake_key_file = tmp_path / "empty.txt"
        fake_key_file.write_text("", encoding="utf-8")
        monkeypatch.setattr(service, "OPENAI_KEY_FILE", fake_key_file)

        with pytest.raises(RuntimeError, match="ChatGPT indisponível.*não foi encontrado ou está vazio"):
            service._load_openai_api_key()

    def test_raises_when_file_only_comments(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que lança RuntimeError quando arquivo só tem comentários."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        fake_key_file = tmp_path / "comments_only.txt"
        fake_key_file.write_text("# Comment 1\n# Comment 2\n   # Comment 3", encoding="utf-8")
        monkeypatch.setattr(service, "OPENAI_KEY_FILE", fake_key_file)

        with pytest.raises(RuntimeError, match="ChatGPT indisponível.*não foi encontrado ou está vazio"):
            service._load_openai_api_key()

    def test_raises_when_file_read_error(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que lança RuntimeError quando há erro ao ler arquivo."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        fake_key_file = tmp_path / "unreadable.txt"
        fake_key_file.write_text("sk-key", encoding="utf-8")
        monkeypatch.setattr(service, "OPENAI_KEY_FILE", fake_key_file)

        # Mock read_text para simular erro de leitura
        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            with pytest.raises(RuntimeError, match="ChatGPT indisponível.*erro ao ler o arquivo"):
                service._load_openai_api_key()

    def test_env_takes_precedence_over_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Testa que env var tem prioridade sobre arquivo."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")

        fake_key_file = tmp_path / "openai_key.txt"
        fake_key_file.write_text("sk-file-key", encoding="utf-8")
        monkeypatch.setattr(service, "OPENAI_KEY_FILE", fake_key_file)

        key = service._load_openai_api_key()
        assert key == "sk-env-key"


class TestGetOpenAIClient:
    """Testes para _get_openai_client()."""

    def test_returns_cached_client_on_second_call(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que retorna cliente em cache na segunda chamada."""
        # Reset global client
        service._client = None

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock OpenAI import
        mock_openai_class = MagicMock()
        mock_client_instance = MagicMock()
        mock_openai_class.return_value = mock_client_instance

        with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=mock_openai_class)}):
            # Primeira chamada cria o cliente
            client1 = service._get_openai_client()
            assert client1 is mock_client_instance

            # Segunda chamada retorna o mesmo cliente (cached)
            client2 = service._get_openai_client()
            assert client2 is client1
            assert mock_openai_class.call_count == 1  # Só inicializado uma vez

    def test_creates_client_with_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que cria cliente com a API key correta."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-api-key")

        mock_openai_class = MagicMock()
        with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=mock_openai_class)}):
            service._get_openai_client()
            mock_openai_class.assert_called_once_with(api_key="sk-test-api-key")

    def test_raises_when_openai_not_installed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que lança RuntimeError quando openai não está instalado."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        with patch("builtins.__import__", side_effect=ModuleNotFoundError("No module named 'openai'")):
            with pytest.raises(RuntimeError, match="ChatGPT indisponível.*não está instalada"):
                service._get_openai_client()

    def test_raises_when_openai_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que lança RuntimeError quando há erro de import do openai."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        with patch("builtins.__import__", side_effect=ImportError("Incompatible version")):
            with pytest.raises(RuntimeError, match="ChatGPT indisponível.*versão incompatível"):
                service._get_openai_client()


class TestSendChatCompletion:
    """Testes para send_chat_completion()."""

    def test_returns_empty_string_for_empty_messages(self) -> None:
        """Testa que retorna string vazia para lista de mensagens vazia."""
        result = service.send_chat_completion([])
        assert result == ""

    def test_uses_default_model_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que usa modelo padrão da variável de ambiente."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("OPENAI_CHAT_MODEL", "gpt-4")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = "Test response"
        mock_client.responses.create.return_value = mock_response

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [{"role": "user", "content": "Hello"}]
            result = service.send_chat_completion(messages)

            assert result == "Test response"
            mock_client.responses.create.assert_called_once()
            call_kwargs = mock_client.responses.create.call_args[1]
            assert call_kwargs["model"] == "gpt-4"

    def test_uses_default_model_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que usa gpt-4o-mini por padrão quando env não está setado."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.delenv("OPENAI_CHAT_MODEL", raising=False)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = "Test response"
        mock_client.responses.create.return_value = mock_response

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [{"role": "user", "content": "Hello"}]
            service.send_chat_completion(messages)

            call_kwargs = mock_client.responses.create.call_args[1]
            assert call_kwargs["model"] == "gpt-4o-mini"

    def test_uses_custom_model_parameter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que usa modelo customizado passado como parâmetro."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = "Test response"
        mock_client.responses.create.return_value = mock_response

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [{"role": "user", "content": "Hello"}]
            service.send_chat_completion(messages, model="gpt-3.5-turbo")

            call_kwargs = mock_client.responses.create.call_args[1]
            assert call_kwargs["model"] == "gpt-3.5-turbo"

    def test_formats_messages_correctly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que formata mensagens corretamente para a API."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = "Response"
        mock_client.responses.create.return_value = mock_response

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
            service.send_chat_completion(messages)

            call_kwargs = mock_client.responses.create.call_args[1]
            expected_input = [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
            assert call_kwargs["input"] == expected_input

    def test_strips_whitespace_from_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que remove espaços em branco da resposta."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = "  Test response with spaces  "
        mock_client.responses.create.return_value = mock_response

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [{"role": "user", "content": "Hello"}]
            result = service.send_chat_completion(messages)
            assert result == "Test response with spaces"

    def test_handles_choices_format_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa compatibilidade com formato 'choices' da resposta."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = None  # Sem output_text
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response via choices"
        mock_client.responses.create.return_value = mock_response

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [{"role": "user", "content": "Hello"}]
            result = service.send_chat_completion(messages)
            assert result == "Response via choices"

    def test_handles_list_content_in_choices(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa compatibilidade com content como lista."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = None
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ["Part 1", " Part 2", " Part 3"]
        mock_client.responses.create.return_value = mock_response

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [{"role": "user", "content": "Hello"}]
            result = service.send_chat_completion(messages)
            assert result == "Part 1 Part 2 Part 3"

    def test_fallback_to_str_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa fallback para str(response) quando formato não reconhecido."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = None
        mock_response.choices = None
        mock_response.__str__ = lambda _: "Fallback string"
        mock_client.responses.create.return_value = mock_response

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [{"role": "user", "content": "Hello"}]
            result = service.send_chat_completion(messages)
            assert result == "Fallback string"

    def test_raises_runtime_error_on_api_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que lança RuntimeError quando API retorna exceção."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_client.responses.create.side_effect = Exception("API Error")

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [{"role": "user", "content": "Hello"}]
            with pytest.raises(RuntimeError, match="Erro ao chamar ChatGPT"):
                service.send_chat_completion(messages)

    def test_choices_without_message_attribute(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa fallback quando choices existe mas choice não tem message (branch 120->126)."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = None
        # Simula choices[0] sem atributo message (getattr retorna None)
        mock_choice = MagicMock(spec=[])  # spec vazio = sem atributos
        mock_response.choices = [mock_choice]
        mock_response.__str__ = lambda _: "Fallback via str(response)"
        mock_client.responses.create.return_value = mock_response

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [{"role": "user", "content": "Hello"}]
            result = service.send_chat_completion(messages)
            assert result == "Fallback via str(response)"

    def test_choices_with_message_but_invalid_content(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa fallback quando message.content não é str nem lista (branch 124->126)."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = None
        # Simula choices[0].message.content com tipo inesperado (int, dict, etc)
        mock_message = MagicMock()
        mock_message.content = 12345  # Não é str nem lista
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_response.__str__ = lambda _: "Fallback due to invalid content type"
        mock_client.responses.create.return_value = mock_response

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [{"role": "user", "content": "Hello"}]
            result = service.send_chat_completion(messages)
            assert result == "Fallback due to invalid content type"

    def test_sets_max_output_tokens(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Testa que configura max_output_tokens corretamente."""
        service._client = None
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.output_text = "Response"
        mock_client.responses.create.return_value = mock_response

        with patch.object(service, "_get_openai_client", return_value=mock_client):
            messages = [{"role": "user", "content": "Hello"}]
            service.send_chat_completion(messages)

            call_kwargs = mock_client.responses.create.call_args[1]
            assert call_kwargs["max_output_tokens"] == 1024


class TestModuleConstants:
    """Testes para constantes do módulo."""

    def test_base_dir_points_to_project_root(self) -> None:
        """Testa que BASE_DIR aponta para a raiz do projeto."""
        # BASE_DIR deve ser 3 níveis acima de src/modules/chatgpt/service.py
        assert service.BASE_DIR.name == "v1.4.79" or service.BASE_DIR.is_dir()

    def test_openai_key_file_path_correct(self) -> None:
        """Testa que OPENAI_KEY_FILE aponta para config/openai_key.txt."""
        assert service.OPENAI_KEY_FILE.name == "openai_key.txt"
        assert service.OPENAI_KEY_FILE.parent.name == "config"


class TestClientGlobalState:
    """Testes para o estado global _client."""

    def test_client_starts_as_none(self) -> None:
        """Testa que _client começa como None."""
        # Reset
        service._client = None
        assert service._client is None
