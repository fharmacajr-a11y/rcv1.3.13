"""
Configuracao do pytest para testes.

Este arquivo garante que o pytest reconheca a pasta tests/ como um pacote
e configure corretamente os caminhos para importar modulos do projeto.
"""

from __future__ import annotations

import gc
import sqlite3
import sys
import warnings
from typing import Any, Generator
from unittest.mock import MagicMock

import pytest
import tkinter as tk

try:
    import ttkbootstrap as tb
    from ttkbootstrap import style as tb_style
except Exception:  # ttkbootstrap pode nao estar disponivel em alguns ambientes
    tb = None
    tb_style = None


class DummyStyle:
    """Estilo fake para testes, evita chamadas nativas do Tk."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # master pode ser None; nao vamos chamar nada nele
        self.master = None

    def theme_use(self, *args: Any, **kwargs: Any) -> str:
        # retorna um nome de tema qualquer
        return "default"

    def configure(self, *args: Any, **kwargs: Any) -> None:
        # nao faz nada, apenas para compatibilidade
        return None

    def map(self, *args: Any, **kwargs: Any) -> list[tuple[str, str]]:
        # Retorna lista vazia de estados; compatível com ttk Style.map()
        # Formato: [("estado", "valor"), ...]
        return []

    def lookup(self, style: str, option: str, state: tuple[str, ...] | None = None) -> str:
        # Retorna valor de placeholder para qualquer consulta
        # Para fieldbackground/background, retorna cor clara padrão
        if option in ("fieldbackground", "background"):
            return "#ffffff"
        return ""

    def layout(self, *args: Any, **kwargs: Any) -> tuple[Any, ...]:
        # usado em alguns widgets; devolve algo neutro
        return ()

    def element_create(self, *args: Any, **kwargs: Any) -> None:
        # no-op
        return None


@pytest.fixture(autouse=True)
def patch_ttkbootstrap_style(monkeypatch: pytest.MonkeyPatch):
    """
    Fixture autouse que roda em TODOS os testes.

    - Substitui ttkbootstrap.Style por DummyStyle.
    - Substitui Style usado diretamente nos modulos que fazem `from ttkbootstrap import Style`.
    - Desativa StyleBuilderTTK.scale_size para nao chamar tk.windowingsystem.
    """
    if tb is None or tb_style is None:
        # ttkbootstrap nao disponivel, nada a fazer
        yield
        return

    # 1) Patch no modulo ttkbootstrap principal
    monkeypatch.setattr(tb, "Style", DummyStyle, raising=False)

    # 2) Patch nos modulos que importam Style diretamente
    try:
        import src.modules.main_window.views.main_window as mw_main

        if hasattr(mw_main, "Style"):
            monkeypatch.setattr(mw_main, "Style", DummyStyle, raising=False)
    except Exception:
        # Se o modulo ainda nao foi importado, ignorar silenciosamente
        pass

    # 3) Patch em StyleBuilderTTK.scale_size para nao chamar tk.windowingsystem
    if hasattr(tb_style, "StyleBuilderTTK"):

        def safe_scale_size(self, size):
            # simplesmente devolve o tamanho original, sem consultar tk
            return size

        monkeypatch.setattr(tb_style.StyleBuilderTTK, "scale_size", safe_scale_size, raising=False)

    # A fixture e autouse, entao esse patch vale para a duracao de cada teste
    yield


# ============================================================================
# HOOKS DO PYTEST - Limpeza de estado global
# ============================================================================


def pytest_runtest_setup(item):
    """
    Hook executado ANTES de cada teste para limpar estado global.

    Este hook garante que testes comecam com estado limpo.
    Se um teste usa monkeypatch para substituir completamente um objeto,
    o monkeypatch tera precedencia (roda depois deste hook).
    """
    # Limpar rate limit state do modulo auth
    try:
        import src.core.auth.auth as auth_module

        if hasattr(auth_module, "_reset_auth_for_tests"):
            auth_module._reset_auth_for_tests()
    except (ImportError, AttributeError):
        pass

    _clear_magicmock_modules()


def _clear_magicmock_modules() -> None:
    """
    Remove entradas de sys.modules que foram substituidas por MagicMock.
    Isso evita contaminacao de estado entre testes quando algum teste deixa mocks no cache.
    """
    prefixes = ("src.", "infra.", "adapters.", "data.")
    for name, mod in list(sys.modules.items()):
        if isinstance(mod, MagicMock) and name.startswith(prefixes):
            sys.modules.pop(name, None)


# ============================================================================
# FIXTURES DE SEGURANCA - Valores FAKE para testes
# ============================================================================
# IMPORTANTE: Estes valores sao FICTICIOS e nao devem ser usados em producao
# Proposito: Evitar hardcoding de URLs/keys reais nos testes
# ============================================================================


@pytest.fixture
def fake_supabase_url() -> str:
    """URL fake do Supabase para testes."""
    return "https://test-fake-project.supabase.co"


@pytest.fixture
def fake_supabase_key() -> str:
    """Chave fake do Supabase para testes."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.FAKE_TEST_KEY_DO_NOT_USE"


@pytest.fixture
def fake_env_vars(fake_supabase_url: str, fake_supabase_key: str) -> dict[str, str]:
    """
    Dicionario completo de variaveis de ambiente fake para testes.

    Use com `patch.dict("os.environ", fake_env_vars)` nos testes.
    """
    return {
        "SUPABASE_URL": fake_supabase_url,
        "SUPABASE_KEY": fake_supabase_key,
        "RC_LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "test",
    }


# ============================================================================
# FIXTURES DE AUTH - Isolamento de SQLite e rate limit
# ============================================================================


@pytest.fixture
def isolated_users_db(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Cria um banco SQLite isolado para testes de CRUD de usuarios."""
    db_path = tmp_path / "test_users.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    import src.core.auth.auth as auth_module

    monkeypatch.setattr(auth_module, "USERS_DB_PATH", db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    return db_path


@pytest.fixture(autouse=True)
def reset_auth_rate_limit():
    """
    Reseta o rate limit de autenticacao entre testes.

    Garante que cada teste comeca com estado limpo de tentativas de login,
    evitando interferencias entre testes que manipulam rate limiting.
    """
    from src.core.auth.auth import _reset_auth_for_tests

    _reset_auth_for_tests()
    yield
    _reset_auth_for_tests()

    for obj in gc.get_objects():
        try:
            if isinstance(obj, sqlite3.Connection):
                obj.close()
        except Exception:
            pass

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed database.*")
        gc.collect()
        gc.collect()


@pytest.fixture(autouse=True)
def reset_session_state():
    """
    Reseta o estado global de sessao entre testes.

    Garante que cada teste comeca com sessao limpa, evitando vazamento
    de estado de autenticacao entre testes.
    """
    try:
        from src.core.session import session as session_module

        original_user = getattr(session_module, "_CURRENT_USER", None)
        if hasattr(session_module, "_CURRENT_USER"):
            session_module._CURRENT_USER = None  # type: ignore[attr-defined]
        yield
        if hasattr(session_module, "_CURRENT_USER"):
            session_module._CURRENT_USER = original_user  # type: ignore[attr-defined]
    except ImportError:
        yield


@pytest.fixture(autouse=True)
def reset_session_cache():
    """
    Reseta o cache de SessionCache entre testes.

    Garante que cada teste comece com cache limpo, evitando que dados
    cacheados de testes anteriores (role, org_id, user) contaminem
    testes subsequentes no run global.

    Limpa TODAS as instâncias de SessionCache criadas até o momento,
    resolvendo o problema de AssertionError em test_get_role_uses_memberships_and_caches.
    """
    try:
        from src.modules.main_window.session_service import SessionCache

        # Limpa antes do teste
        SessionCache.clear_all_instances_for_tests()
        yield
        # Limpa depois do teste
        SessionCache.clear_all_instances_for_tests()
    except ImportError:
        yield


@pytest.fixture(autouse=True)
def protect_tkinter_module():
    """
    Protege o módulo tkinter contra modificações em sys.modules.

    Alguns testes (como test_utils_errors_fase17.py e test_app_actions_fase45.py)
    substituem temporariamente sys.modules["tkinter"] por mocks, o que pode quebrar
    tk_root_session criado anteriormente. Esta fixture garante que o módulo real
    seja restaurado após cada teste.
    """
    import sys

    # Salva referências aos módulos tkinter reais (se existirem)
    original_tk = sys.modules.get("tkinter")
    original_tk_messagebox = sys.modules.get("tkinter.messagebox")
    original_tk_filedialog = sys.modules.get("tkinter.filedialog")

    yield

    # Restaura módulos tkinter reais se foram substituídos
    if original_tk is not None:
        current_tk = sys.modules.get("tkinter")
        # Se o módulo foi substituído por um mock/fake, restaurar o original
        if current_tk is not original_tk:
            sys.modules["tkinter"] = original_tk

    if original_tk_messagebox is not None:
        current_messagebox = sys.modules.get("tkinter.messagebox")
        if current_messagebox is not original_tk_messagebox:
            sys.modules["tkinter.messagebox"] = original_tk_messagebox

    if original_tk_filedialog is not None:
        current_filedialog = sys.modules.get("tkinter.filedialog")
        if current_filedialog is not original_tk_filedialog:
            sys.modules["tkinter.filedialog"] = original_tk_filedialog


# ============================================================================
# FIXTURES DE PREFS - Isolamento de preferencias entre testes
# ============================================================================


@pytest.fixture(autouse=True)
def isolated_prefs_dir(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """
    Isola diretorio de preferencias para cada teste.

    Garante que:
    - Cada teste usa seu proprio diretorio temporario
    - Nao ha contaminacao de preferencias entre testes
    - Arquivos de prefs sao limpos automaticamente apos cada teste
    """
    prefs_dir = tmp_path / "test_prefs"
    prefs_dir.mkdir(exist_ok=True)

    try:
        import src.utils.prefs as prefs_module

        monkeypatch.setattr(prefs_module, "_get_base_dir", lambda: str(prefs_dir))
    except (ImportError, AttributeError):
        pass

    return prefs_dir


# ============================================================================
# FIXTURE DE TK/TCL - Root unico para testes de UI
# ============================================================================


@pytest.fixture(scope="session")
def tk_root_session() -> Generator[tk.Tk, None, None]:
    """
    Cria um único interpreter Tk para a sessão de testes de UI.

    Marca o root como 'de teste' e protege o método destroy, para que
    nenhum código de produção/teste mate o interpreter durante os testes.

    Isso evita o erro "_tkinter.TclError: can't invoke 'tk' command:
    application has been destroyed" quando múltiplos testes precisam de Tk.
    """
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tkinter nao esta disponivel neste ambiente de testes.")

    root.withdraw()

    # Marca esse root como "root de teste"
    setattr(root, "_is_test_root", True)

    # Guarda o destroy original
    original_destroy = root.destroy

    def safe_destroy() -> None:
        """
        Versão segura de destroy para o root de teste.

        Em vez de destruir o interpreter, apenas esconde o root.
        Isso evita o erro `_tkinter.TclError: can't invoke "tk" command:
        application has been destroyed` quando outros testes ainda querem
        usar Tk.
        """
        # Em ambiente de teste, nunca destruímos realmente o root global
        try:
            root.withdraw()
        except tk.TclError:
            # Se o interpreter já estiver destruído por algum motivo,
            # apenas ignore para não quebrar os próximos testes.
            pass

    # Monkeypatch no destroy do root de teste
    root.destroy = safe_destroy  # type: ignore[assignment]

    try:
        yield root
    finally:
        # No teardown da sessão, tenta destruir de verdade (best effort).
        try:
            original_destroy()
        except tk.TclError:
            pass
