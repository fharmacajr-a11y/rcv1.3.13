from types import SimpleNamespace

import pytest

from src.modules.passwords import helpers
from src.modules.passwords.controller import ClientPasswordsSummary


class _MessageBoxStub:
    def __init__(self) -> None:
        self.infos: list[tuple[str, str, object | None]] = []
        self.errors: list[tuple[str, str, object | None]] = []

    def showinfo(self, title: str, message: str, parent=None) -> None:  # noqa: ANN001
        self.infos.append((title, message, parent))

    def showerror(self, title: str, message: str, parent=None) -> None:  # noqa: ANN001
        self.errors.append((title, message, parent))


class _DummyParent:
    def winfo_toplevel(self):
        return self

    def winfo_exists(self) -> bool:
        return True

    def _get_org_id_cached(self, _uid: str) -> str:  # noqa: ANN001
        return "org-1"

    def refresh_current_view(self) -> None:
        return None


def _stub_supabase_user(monkeypatch: pytest.MonkeyPatch, user_id: str = "user-1") -> None:
    fake_supabase = SimpleNamespace(
        auth=SimpleNamespace(get_user=lambda: SimpleNamespace(user=SimpleNamespace(id=user_id)))
    )
    monkeypatch.setattr(helpers, "supabase", fake_supabase)


def test_open_senhas_for_cliente_opens_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    parent = _DummyParent()
    _stub_supabase_user(monkeypatch)

    mb = _MessageBoxStub()
    monkeypatch.setattr(helpers, "messagebox", mb)

    summary = ClientPasswordsSummary(
        client_id="123",
        client_external_id=123,
        razao_social="ACME",
        cnpj="00.000.000/0000-00",
        contato_nome="Contato",
        whatsapp="",
        passwords_count=1,
        services=["srv"],
    )

    class FakeController:
        def __init__(self) -> None:
            self.loaded = False

        def load_all_passwords(self, org_id: str):  # noqa: ANN001
            self.loaded = True
            return []

        def group_passwords_by_client(self):
            return [summary]

        def list_clients(self, org_id: str):  # noqa: ANN001
            return ["client-row"]

    called: dict[str, tuple] = {}

    class FakeDialog:
        def __init__(self, *args, **kwargs):  # noqa: ANN001
            called["args"] = args
            called["kwargs"] = kwargs

    helpers.open_senhas_for_cliente(
        parent,
        "123",
        razao_social="ACME",
        controller_factory=FakeController,
        dialog_cls=FakeDialog,
    )

    assert "args" in called
    assert called["args"][3] == "org-1"
    assert not mb.infos
    assert not mb.errors


def test_open_senhas_for_cliente_show_info_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    parent = _DummyParent()
    _stub_supabase_user(monkeypatch)

    mb = _MessageBoxStub()
    monkeypatch.setattr(helpers, "messagebox", mb)

    class EmptyController:
        def load_all_passwords(self, org_id: str):  # noqa: ANN001
            return []

        def group_passwords_by_client(self):
            return []

        def list_clients(self, org_id: str):  # noqa: ANN001
            return []

    helpers.open_senhas_for_cliente(
        parent,
        "999",
        controller_factory=EmptyController,
        dialog_cls=lambda *a, **k: None,
    )

    assert mb.infos
    assert any("não possui senhas" in msg for _title, msg, _parent in mb.infos)
    assert all(entry[2] is parent for entry in mb.infos)
