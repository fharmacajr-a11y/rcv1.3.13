import pytest
from pathlib import Path
import json

from src.utils import prefs as prefs_module


@pytest.fixture
def temp_auth_prefs_dir(monkeypatch, tmp_path):
    prefs_dir = tmp_path / "auth_prefs"
    prefs_dir.mkdir()
    monkeypatch.setattr("src.utils.prefs._get_base_dir", lambda: str(prefs_dir))
    return prefs_dir


def test_save_and_load_auth_session_basic(temp_auth_prefs_dir):
    prefs_module.save_auth_session("at", "rt", keep_logged=True)
    data = prefs_module.load_auth_session()
    assert data["access_token"] == "at"
    assert data["refresh_token"] == "rt"
    assert data["keep_logged"] is True
    assert data["created_at"]


def test_save_auth_session_clears_when_not_keep_logged(temp_auth_prefs_dir):
    prefs_module.save_auth_session("at", "rt", keep_logged=True)
    assert prefs_module.load_auth_session().get("access_token") == "at"

    prefs_module.save_auth_session("ignored", "ignored", keep_logged=False)
    data = prefs_module.load_auth_session()
    assert not data or not data.get("access_token")


def test_load_auth_session_corrupted_returns_empty(temp_auth_prefs_dir):
    path = Path(prefs_module._auth_session_path())
    path.write_text("{ invalid json", encoding="utf-8")

    data = prefs_module.load_auth_session()
    assert data == {}


def test_keyring_migration_from_file(temp_auth_prefs_dir, monkeypatch):
    """
    P1-001: Testa migração automática de auth_session.json para keyring.

    Simula:
    1. Sessão existente em arquivo (legado)
    2. Keyring disponível
    3. Ao carregar, deve migrar para keyring e remover arquivo
    """
    # Mock do keyring com storage em memória
    fake_keyring_storage = {}

    def mock_keyring_available():
        return True

    def mock_keyring_get(service, username):
        return fake_keyring_storage.get(f"{service}:{username}")

    def mock_keyring_set(service, username, password):
        fake_keyring_storage[f"{service}:{username}"] = password
        return True

    def mock_keyring_delete(service, username):
        key = f"{service}:{username}"
        if key in fake_keyring_storage:
            del fake_keyring_storage[key]

    # Aplicar mocks
    monkeypatch.setattr("src.utils.prefs._keyring_is_available", mock_keyring_available)

    # Mock das funções de keyring helpers
    def wrapped_get():
        if not mock_keyring_available():
            return None
        return mock_keyring_get(prefs_module.KEYRING_SERVICE_NAME, prefs_module.KEYRING_USERNAME)

    def wrapped_set(payload):
        if not mock_keyring_available():
            return False
        mock_keyring_set(prefs_module.KEYRING_SERVICE_NAME, prefs_module.KEYRING_USERNAME, payload)
        return True

    def wrapped_clear():
        if mock_keyring_available():
            mock_keyring_delete(prefs_module.KEYRING_SERVICE_NAME, prefs_module.KEYRING_USERNAME)

    monkeypatch.setattr("src.utils.prefs._keyring_get_session_json", wrapped_get)
    monkeypatch.setattr("src.utils.prefs._keyring_set_session_json", wrapped_set)
    monkeypatch.setattr("src.utils.prefs._keyring_clear_session", wrapped_clear)

    # 1. Criar sessão em arquivo (simular legado)
    auth_file = Path(prefs_module._auth_session_path())
    legacy_session = {
        "access_token": "legacy_at",
        "refresh_token": "legacy_rt",
        "created_at": "2025-12-26T10:00:00+00:00",
        "keep_logged": True,
    }
    auth_file.write_text(json.dumps(legacy_session), encoding="utf-8")

    # Verificar que arquivo existe
    assert auth_file.exists()

    # 2. Carregar sessão (deve migrar automaticamente)
    data = prefs_module.load_auth_session()

    # 3. Validar que carregou corretamente
    assert data["access_token"] == "legacy_at"
    assert data["refresh_token"] == "legacy_rt"

    # 4. Validar que migrou para keyring
    keyring_key = f"{prefs_module.KEYRING_SERVICE_NAME}:{prefs_module.KEYRING_USERNAME}"
    assert keyring_key in fake_keyring_storage
    stored_json = fake_keyring_storage[keyring_key]
    stored_data = json.loads(stored_json)
    assert stored_data["access_token"] == "legacy_at"

    # 5. Validar que arquivo foi removido após migração
    assert not auth_file.exists()

    # 6. Próximo load deve vir do keyring, não do arquivo
    data2 = prefs_module.load_auth_session()
    assert data2["access_token"] == "legacy_at"
    assert not auth_file.exists()  # Arquivo continua ausente
