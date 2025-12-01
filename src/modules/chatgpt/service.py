from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI  # pragma: no cover

log = logging.getLogger(__name__)

# Caminho para o arquivo de chave da API OpenAI
BASE_DIR = Path(__file__).resolve().parents[3]  # raiz do projeto (acima de src/)
OPENAI_KEY_FILE = BASE_DIR / "config" / "openai_key.txt"

_client: Optional["OpenAI"] = None  # type: ignore[name-defined]


def _load_openai_api_key() -> str:
    """
    Obtém a chave da API da OpenAI.

    Ordem de prioridade:
    1. Variável de ambiente OPENAI_API_KEY
    2. Arquivo config/openai_key.txt (uma linha com a chave)

    Lança RuntimeError com mensagem amigável se nada for encontrado.

    Para configurar a chave via arquivo:
    1. Crie uma cópia de config/openai_key.example.txt com o nome openai_key.txt
    2. Abra config/openai_key.txt e cole a chave da OpenAI (uma linha, sem aspas)
    3. O arquivo está no .gitignore e não será versionado

    Returns:
        str: A chave da API OpenAI.

    Raises:
        RuntimeError: Se a chave não for encontrada em nenhum local.
    """
    # Prioridade 1: variável de ambiente
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key.strip()

    # Prioridade 2: arquivo de configuração
    if OPENAI_KEY_FILE.is_file():
        try:
            content = OPENAI_KEY_FILE.read_text(encoding="utf-8").strip()
        except OSError as exc:  # noqa: PERF203
            raise RuntimeError(f"ChatGPT indisponível: erro ao ler o arquivo {OPENAI_KEY_FILE}: {exc}") from exc

        # Ignorar linhas de comentário e linhas vazias
        lines = [line.strip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
        if lines:
            return lines[0]  # Primeira linha não-comentário

    raise RuntimeError(
        "ChatGPT indisponível: variável de ambiente OPENAI_API_KEY não está definida "
        "e o arquivo config/openai_key.txt não foi encontrado ou está vazio."
    )


def _get_openai_client():
    """
    Lazy-import do OpenAI para evitar quebrar o app se a lib não estiver instalada.
    Lança RuntimeError com mensagem amigável em caso de problema.
    """
    global _client
    if _client is not None:
        return _client

    api_key = _load_openai_api_key()

    try:
        from openai import OpenAI  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment packages
        raise RuntimeError(
            "ChatGPT indisponível: biblioteca 'openai' não está instalada. "
            "Instale 'openai>=1.40.0' no mesmo ambiente virtual."
        ) from exc
    except ImportError as exc:  # pragma: no cover - depends on environment packages
        raise RuntimeError(
            "ChatGPT indisponível: versão incompatível do pacote 'openai'. "
            "Atualize para 'openai>=1.40.0' no mesmo ambiente virtual."
        ) from exc

    _client = OpenAI(api_key=api_key)
    return _client


def send_chat_completion(
    messages: Sequence[dict[str, str]],
    model: str | None = None,
) -> str:
    """
    Envia uma conversa para o ChatGPT e retorna o conteúdo da mensagem de resposta.
    Lança RuntimeError com mensagem amigável se não for possível usar a API.
    """
    if not messages:
        return ""

    client = _get_openai_client()
    model_name = model or os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    try:
        response = client.responses.create(
            model=model_name,
            input=[{"role": m["role"], "content": m["content"]} for m in messages],
            max_output_tokens=1024,
        )
        text = getattr(response, "output_text", None)
        if isinstance(text, str):
            return text.strip()

        # compat: se API retornar em outra estrutura
        if getattr(response, "choices", None):
            choice = response.choices[0]
            content = getattr(choice, "message", None)
            if content is not None:
                msg_content = getattr(content, "content", None)
                if isinstance(msg_content, str):
                    return msg_content
                if isinstance(msg_content, list) and msg_content:
                    return "".join(str(part) for part in msg_content)
        return str(response)
    except Exception as exc:  # noqa: BLE001
        log.exception("Erro ao chamar ChatGPT.")
        raise RuntimeError(f"Erro ao chamar ChatGPT: {exc}") from exc
