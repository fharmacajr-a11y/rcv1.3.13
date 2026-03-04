from __future__ import annotations

import logging
import os
from typing import Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI  # pragma: no cover

log = logging.getLogger(__name__)

_client: Optional["OpenAI"] = None  # type: ignore[name-defined]


def get_openai_api_key() -> str:
    """Obtém a chave da API da OpenAI **exclusivamente** via variável de ambiente.

    Returns:
        str: A chave da API OpenAI.

    Raises:
        RuntimeError: Se ``OPENAI_API_KEY`` não estiver definida ou estiver vazia.
    """
    env_key = os.getenv("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key

    raise RuntimeError(
        "ChatGPT indisponível: a variável de ambiente OPENAI_API_KEY não está definida. "
        "Configure-a antes de iniciar o aplicativo.\n\n"
        "  PowerShell:  $env:OPENAI_API_KEY = 'sk-...'\n"
        "  Linux/Mac:   export OPENAI_API_KEY='sk-...'"
    )


def _get_openai_client():
    """
    Lazy-import do OpenAI para evitar quebrar o app se a lib não estiver instalada.
    Lança RuntimeError com mensagem amigável em caso de problema.
    """
    global _client
    if _client is not None:
        return _client

    api_key = get_openai_api_key()

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
            input=[{"role": m["role"], "content": m["content"]} for m in messages],  # type: ignore[arg-type]
            max_output_tokens=1024,
        )
        text = getattr(response, "output_text", None)
        if isinstance(text, str):
            return text.strip()

        # compat: se API retornar em outra estrutura
        if getattr(response, "choices", None):
            choice = response.choices[0]  # pyright: ignore[reportAttributeAccessIssue]
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
