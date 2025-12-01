from types import SimpleNamespace

import pytest

from src.modules.chatgpt import service


class FakeClient:
    def __init__(self, expected_content: str) -> None:
        self._expected_content = expected_content
        self.responses = SimpleNamespace(create=self._fake_create)
        self.last_kwargs: dict | None = None

    def _fake_create(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(output_text=self._expected_content)


def test_send_chat_completion_returns_content(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient("resposta teste")
    monkeypatch.setattr(service, "_client", fake)

    messages = [{"role": "user", "content": "Ola"}]
    result = service.send_chat_completion(messages, model="meu-modelo")

    assert result == "resposta teste"
    assert fake.last_kwargs is not None
    assert fake.last_kwargs["model"] == "meu-modelo"
    assert fake.last_kwargs["input"] == messages
