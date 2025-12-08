import pytest

from src.modules.passwords import service as passwords_service
from src.modules.passwords.passwords_actions import (
    PasswordDialogActions,
    PasswordFormData,
    PasswordsActions,
)


class FakeController:
    def __init__(self, *, clients=None, passwords=None, delete_result=0):
        self._clients = clients or []
        self._passwords = passwords or []
        self.list_clients_calls: list[str] = []
        self.load_passwords_calls: list[str] = []
        self.deleted_calls: list[tuple[str, str]] = []
        self.create_calls: list[dict] = []
        self.update_calls: list[dict] = []
        self.duplicate_calls: list[tuple[str, str, str]] = []
        self.delete_result = delete_result
        self.duplicates_response: list[dict] = []

    def list_clients(self, org_id: str):
        self.list_clients_calls.append(org_id)
        return list(self._clients)

    def load_all_passwords(self, org_id: str):
        self.load_passwords_calls.append(org_id)
        return list(self._passwords)

    def delete_all_passwords_for_client(self, org_id: str, client_id: str) -> int:
        self.deleted_calls.append((org_id, client_id))
        return self.delete_result

    def create_password(self, org_id, client_name, service, username, password, notes, user_id, client_id):
        self.create_calls.append(
            {
                "org_id": org_id,
                "client_name": client_name,
                "service": service,
                "username": username,
                "password": password,
                "notes": notes,
                "user_id": user_id,
                "client_id": client_id,
            }
        )

    def update_password(self, password_id, **kwargs):
        entry = {"password_id": password_id}
        entry.update(kwargs)
        self.update_calls.append(entry)

    def find_duplicate_passwords_by_service(self, org_id, client_id, service):
        self.duplicate_calls.append((org_id, client_id, service))
        return list(self.duplicates_response)


def test_passwords_actions_bootstrap_screen(monkeypatch):
    controller = FakeController(
        clients=[{"id": 1, "name": "Client"}],
        passwords=[{"client_id": "1", "service": "SIFAP"}],
    )
    actions = PasswordsActions(controller=controller)
    ctx = passwords_service.PasswordsUserContext(org_id="ORG-1", user_id="USER-9")
    monkeypatch.setattr(passwords_service, "resolve_user_context", lambda _: ctx)

    state = actions.bootstrap_screen(main_window=object())

    assert state.org_id == "ORG-1"
    assert state.user_id == "USER-9"
    assert controller.list_clients_calls == ["ORG-1"]
    assert controller.load_passwords_calls == ["ORG-1"]
    assert state.all_passwords == [{"client_id": "1", "service": "SIFAP"}]


def test_passwords_actions_build_summaries_filters_data():
    sample = [
        {"client_id": "1", "client_name": "Alpha", "service": "SIFAP", "username": "alpha"},
        {"client_id": "2", "client_name": "Beta", "service": "GOV.BR", "username": "beta"},
    ]
    actions = PasswordsActions(controller=FakeController())

    summaries = actions.build_summaries(sample, search_text="beta", service_filter="GOV.BR")

    assert len(summaries.all_summaries) == 2
    assert len(summaries.filtered_summaries) == 1
    assert summaries.filtered_summaries[0].client_id == "2"
    assert summaries.summaries_by_id["1"].razao_social


def test_passwords_actions_delete_client_passwords_calls_controller():
    controller = FakeController(delete_result=3)
    actions = PasswordsActions(controller=controller)

    deleted = actions.delete_client_passwords("ORG-X", "client-9")

    assert deleted == 3
    assert controller.deleted_calls == [("ORG-X", "client-9")]


def test_password_dialog_actions_validate_form_errors():
    form = PasswordFormData(
        client_id="",
        client_name=" ",
        service="",
        username="",
        password="",
        notes="",
        is_editing=False,
    )

    errors = PasswordDialogActions.validate_form(form)

    assert "Selecione um cliente" in errors[0]
    assert any("Cliente está vazio" in err for err in errors)
    assert any("Informe o serviço" in err for err in errors)
    assert any("Informe o usuário" in err for err in errors)
    assert any("Informe a senha" in err for err in errors)


def test_password_dialog_actions_create_password_calls_controller():
    controller = FakeController()
    actions = PasswordDialogActions(controller=controller)
    form = PasswordFormData(
        client_id="1",
        client_name="Alpha",
        service="SIFAP",
        username="alpha",
        password="secret",
        notes="",
        is_editing=False,
    )

    actions.create_password("ORG", "USER", form)

    assert controller.create_calls[0]["client_name"] == "Alpha"
    assert controller.create_calls[0]["user_id"] == "USER"


def test_password_dialog_actions_update_requires_id():
    actions = PasswordDialogActions(controller=FakeController())
    form = PasswordFormData(
        client_id="1",
        client_name="Alpha",
        service="SIFAP",
        username="alpha",
        password="secret",
        notes="",
        is_editing=True,
        password_id=None,
    )

    with pytest.raises(ValueError):
        actions.update_password(form)


def test_password_dialog_actions_update_calls_controller():
    controller = FakeController()
    actions = PasswordDialogActions(controller=controller)
    form = PasswordFormData(
        client_id="1",
        client_name="Alpha",
        service="SIFAP",
        username="alpha",
        password="secret",
        notes="",
        is_editing=True,
        password_id="pwd-1",
    )

    actions.update_password(form)

    assert controller.update_calls[0]["password_id"] == "pwd-1"
    assert controller.update_calls[0]["service"] == "SIFAP"


def test_password_dialog_actions_find_duplicates_delegates_to_controller():
    controller = FakeController()
    controller.duplicates_response = [{"service": "SIFAP"}]
    actions = PasswordDialogActions(controller=controller)

    duplicates = actions.find_duplicates("ORG", "1", "SIFAP")

    assert controller.duplicate_calls == [("ORG", "1", "SIFAP")]
    assert duplicates == [{"service": "SIFAP"}]
