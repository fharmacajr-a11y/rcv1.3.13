"""
Configuracao do pytest para testes.

Este arquivo garante que o pytest reconheca a pasta tests/ como um pacote
e configure corretamente os caminhos para importar modulos do projeto.
"""

from __future__ import annotations

import functools
import gc
import os
import sqlite3
import sys
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator
from unittest.mock import MagicMock

import pytest

# ============================================================================
# DETECÇÃO DE TKINTER - Import condicional para ambientes sem Tk/Tcl
# ============================================================================
try:
    import tkinter as tk

    TK_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    tk = None  # type: ignore
    TK_AVAILABLE = False


# ============================================================================
# FIX: Python 3.13 tkinter.Image.__del__ crash during interpreter shutdown
# ----------------------------------------------------------------------------
# Durante o shutdown do interpretador, as globals do módulo tkinter são
# destruídas antes que todos os objetos Image sejam coletados. O método
# Image.__del__ tenta fazer "except TclError", mas TclError já é None,
# causando: TypeError: catching classes that do not inherit from BaseException
#
# Este fix faz wrap do __del__ original para capturar qualquer exceção que
# ocorra durante o shutdown, evitando o traceback poluir o stderr do pytest.
# Compatível com Python 3.11–3.13.
# ============================================================================
def _patch_tkinter_image_del() -> None:
    """
    Aplica monkeypatch no tkinter.Image.__del__ para evitar crash no shutdown.

    O wrapper captura TypeError e Exception que podem ocorrer quando as globals
    do tkinter já foram destruídas (TclError=None durante interpreter shutdown).
    """
    if not TK_AVAILABLE or tk is None:
        return

    try:
        image_class = getattr(tk, "Image", None)
        if image_class is None:
            return

        _original_del = getattr(image_class, "__del__", None)
        if _original_del is None:
            return

        # Marca para não aplicar múltiplas vezes
        if getattr(_original_del, "_pytest_patched", False):
            return

        def _safe_del(self: Any) -> None:
            """Wrapper que engole exceções durante shutdown do interpretador."""
            try:
                _original_del(self)
            except (TypeError, Exception):
                # TypeError: catching classes that do not inherit from BaseException
                # Ocorre quando TclError já foi destruída (globals=None no shutdown)
                pass

        _safe_del._pytest_patched = True  # type: ignore[attr-defined]
        image_class.__del__ = _safe_del

    except Exception:
        # Se qualquer coisa falhar, não queremos quebrar o pytest
        pass


# Aplica o patch imediatamente ao carregar conftest.py
_patch_tkinter_image_del()


@functools.lru_cache(maxsize=1)
def _check_tk_usable() -> bool:
    """
    Verifica se Tk/Tcl é realmente utilizável (não apenas importável).

    Tenta criar e destruir um Tk root de forma segura para detectar se
    tk.tcl/auto.tcl estão presentes. Em alguns ambientes, tkinter importa
    mas falha com TclError ao criar janelas.

    Usa lru_cache para garantir que o teste seja feito apenas uma vez
    durante toda a execução do pytest.

    Returns:
        True se Tk pode criar janelas, False caso contrário.
    """
    if not TK_AVAILABLE:
        return False

    try:
        import tkinter as _tk

        root = _tk.Tk()
        root.withdraw()  # Nunca mostrar janela
        root.update_idletasks()
        root.destroy()
        return True
    except Exception:
        # TclError: "Can't find a usable tk.tcl" ou similar
        return False


# Aliases de tipos para type checkers (evita reportInvalidTypeForm do Pylance)
if TYPE_CHECKING:
    from tkinter import Misc as TkMisc
    from tkinter import Tcl as TkTcl
    from tkinter import Tk as TkTk
else:
    # Fallback runtime para evitar NameError quando tk=None
    TkMisc = object
    TkTcl = object
    TkTk = object


# ============================================================================
# DESABILITAR MESSAGEBOXES DO TKINTER - Evita janelas modais durante testes
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def _disable_tk_messageboxes():
    """
    Desabilita messageboxes do tkinter durante toda a sessão de testes.
    Isso evita que janelas modais travem a execução do pytest.

    Se Tkinter não estiver disponível, não faz nada (yielda com segurança).
    """
    if not TK_AVAILABLE:
        yield
        return

    mp = pytest.MonkeyPatch()
    try:
        import tkinter.messagebox as mb
    except Exception:
        yield
        return

    # show* não deve abrir janela
    mp.setattr(mb, "showinfo", lambda *a, **k: None, raising=False)
    mp.setattr(mb, "showwarning", lambda *a, **k: None, raising=False)
    mp.setattr(mb, "showerror", lambda *a, **k: None, raising=False)

    # ask* precisa retornar algo consistente
    mp.setattr(mb, "askyesno", lambda *a, **k: False, raising=False)
    mp.setattr(mb, "askokcancel", lambda *a, **k: False, raising=False)
    mp.setattr(mb, "askretrycancel", lambda *a, **k: False, raising=False)
    mp.setattr(mb, "askquestion", lambda *a, **k: "no", raising=False)

    yield
    mp.undo()


# ============================================================================
# BLINDAGEM SYS.PATH - Garante que imports venham do repo atual
# ============================================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # tests/conftest.py -> project root

# ============================================================================
# SMOKE SUITE - Arquivo com nodeids de testes críticos
# ============================================================================
SMOKE_NODEIDS_FILE = PROJECT_ROOT / "scripts" / "suites" / "smoke_nodeids.txt"


@functools.lru_cache(maxsize=1)
def _load_smoke_prefixes() -> tuple[str, ...]:
    """Carrega prefixos de nodeids da smoke suite."""
    if not SMOKE_NODEIDS_FILE.exists():
        raise FileNotFoundError(str(SMOKE_NODEIDS_FILE))

    prefixes: list[str] = []
    for raw in SMOKE_NODEIDS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        prefixes.append(line.replace("\\", "/"))

    # Dedup preservando ordem
    unique: list[str] = []
    seen: set[str] = set()
    for p in prefixes:
        if p not in seen:
            unique.append(p)
            seen.add(p)

    return tuple(unique)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Adiciona opções --smoke e --smoke-strict ao pytest."""
    parser.addoption(
        "--smoke",
        action="store_true",
        default=False,
        help="Executa apenas a smoke suite definida em scripts/suites/smoke_nodeids.txt",
    )
    parser.addoption(
        "--smoke-strict",
        action="store_true",
        default=False,
        help="Falha se algum item do smoke_nodeids.txt não casar com nenhum teste.",
    )


# Remove o PROJECT_ROOT se já estiver em sys.path (pode estar em posição errada)
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))

# Insere no início para ter prioridade máxima
sys.path.insert(0, str(PROJECT_ROOT))

# Opcional: Remover outros clones v1.x.xx do Desktop que podem causar imports errados
# (Somente se detectarmos que estão no sys.path)
_desktop_pattern = str(Path.home() / "Desktop")
_current_version = PROJECT_ROOT.name  # Ex: "v1.4.26"

for path_entry in list(sys.path):
    path_obj = Path(path_entry).resolve()
    # Se for outro clone v1.x no Desktop e não for o atual, remove
    if str(path_obj).startswith(_desktop_pattern) and path_obj.name.startswith("v1.") and path_obj != PROJECT_ROOT:
        sys.path.remove(path_entry)

# ============================================================================
# MODO TESTE - Define ambiente antes de qualquer importação
# ============================================================================
os.environ.setdefault("RC_TESTING", "1")
os.environ.setdefault("RC_HEALTHCHECK_DISABLE", "1")

# Silenciar logs de health check durante testes para evitar spam
import logging  # noqa: E402 - Import após configuração de ambiente é intencional

logging.getLogger("src.infra.supabase.db_client").setLevel(logging.ERROR)


# ============================================================================
# MARKERS PERSONALIZADOS - Categorização de testes
# ============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Registra markers customizados e reaplica filtros de warnings."""
    # Registrar markers
    config.addinivalue_line(
        "markers", "legacy_ui: marca testes que cobrem UI antiga (src.ui.*) - mantidos apenas como referência histórica"
    )

    # Reaplicar filtros de warnings após pytest inicializar
    _apply_global_warning_filters()


def pytest_report_header(config: pytest.Config) -> list[str]:
    """Adiciona informações de ambiente no header do pytest."""
    headers = []

    # Informar status do Tk quando RC_RUN_GUI_TESTS=1
    if os.getenv("RC_RUN_GUI_TESTS") == "1":
        if not TK_AVAILABLE:
            headers.append("⚠️  Tkinter: não disponível (ImportError) - testes GUI serão ignorados")
        elif not has_working_tk():
            headers.append(
                "⚠️  Tkinter: importável mas não funcional (tk.tcl não encontrado) - testes GUI serão ignorados"
            )
        else:
            headers.append("✓ Tkinter: funcional - testes GUI habilitados")

    return headers


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool | None:
    """
    Evita coleta de testes GUI/Tk que causam crashes durante a importação.

    Retorna True para ignorar a coleta, None para permitir (não retornar False).
    Isso previne access violations no Python 3.13+ Windows durante `pytest -m "skip or skipif"`.

    Verifica tanto TK_AVAILABLE (import funciona) quanto has_working_tk()
    (Tk realmente utilizável) para detectar casos onde tkinter importa mas
    tk.tcl está faltando ou quebrado.
    """
    # Normalizar path para comparação
    path_str = str(collection_path).replace("\\", "/")

    # Padrões de testes GUI que dependem de Tk
    gui_patterns = [
        "/tests/gui_legacy/",
        "/tests/integration/modules/",
        "/tests/unit/modules/pdf_preview/views/",
        "/tests/modules/anvisa/",
        "/tests/test_login_dialog",
    ]

    # Detectar se o arquivo atual é GUI
    is_gui_test = any(pattern in path_str for pattern in gui_patterns)

    # Se é teste GUI, verificar se Tk está utilizável
    if is_gui_test:
        # Primeiro verificar ImportError (TK_AVAILABLE)
        if not TK_AVAILABLE:
            return True
        # Depois verificar se Tk realmente funciona (has_working_tk com cache)
        if not has_working_tk():
            return True

    # Ignorar testes GUI legacy quando RC_RUN_GUI_TESTS != "1"
    if os.getenv("RC_RUN_GUI_TESTS") != "1":
        if "/tests/gui_legacy/" in path_str:
            return True
        # Ignorar testes modules/anvisa (contém Tk e pode crashar na coleta de markers)
        if "/tests/modules/anvisa/" in path_str:
            return True

    # Ignorar testes PDF UI quando RC_RUN_PDF_UI_TESTS != "1"
    if os.getenv("RC_RUN_PDF_UI_TESTS") != "1":
        if "/tests/unit/modules/pdf_preview/views/" in path_str:
            return True

    # Windows + Python 3.13+: ignorar testes conhecidos de Tk crash
    # mesmo durante a coleta (crash ocorre na importação)
    if sys.platform.startswith("win") and sys.version_info >= (3, 13):
        crash_patterns = [
            "/tests/unit/modules/clientes/forms/test_client_form_adapters.py",
            "/tests/unit/modules/tasks/views/test_task_dialog.py",
            "/tests/integration/modules/clientes/forms/test_client_form_integration_fase01.py",
            "/tests/test_login_dialog_focus.py",
            "/tests/test_login_dialog_style.py",
            "/tests/test_login_dialog_window_state.py",
        ]
        if any(pattern in path_str for pattern in crash_patterns):
            return True

    # Permitir coleta (retornar None, não False)
    return None


# ============================================================================
# FILTROS DE WARNINGS GLOBAIS
# ============================================================================


def _apply_global_warning_filters() -> None:
    """Silencia avisos conhecidos que só aparecem na suíte completa."""

    # DeprecationWarning da lib nativa "swigvarlink" (código de terceiros).
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=r"builtin type swigvarlink has no __module__ attribute",
    )

    # Fallback absoluto: se o warn escapar dos filtros (por exemplo, no shutdown do Python),
    # interceptamos a escrita para não poluir o stdout.
    _patch_showwarning()


_ORIGINAL_SHOWWARNING = warnings.showwarning
_SHOWWARNING_PATCHED = False


def _patch_showwarning() -> None:
    global _SHOWWARNING_PATCHED
    if _SHOWWARNING_PATCHED:
        return

    def _filtered_showwarning(
        message: Warning | str,
        category: type[Warning],
        filename: str,
        lineno: int,
        file=None,
        line: str | None = None,
    ):
        text = str(message)
        if category is DeprecationWarning and "swigvarlink has no __module__ attribute" in text:
            return
        return _ORIGINAL_SHOWWARNING(message, category, filename, lineno, file=file, line=line)

    warnings.showwarning = _filtered_showwarning
    _SHOWWARNING_PATCHED = True


_apply_global_warning_filters()


# ============================================================================
# HELPER PARA DETECÇÃO DE Tk/Tcl FUNCIONAL
# ============================================================================


def has_working_tk() -> bool:
    """Verifica se Tk/Tcl está funcional no ambiente.

    Retorna False se Tcl/Tk não estiver instalado ou tiver arquivos faltando
    (ex.: auto.tcl, init.tcl). Útil para skip de testes GUI em ambientes
    sem instalação completa do Python/Tcl.

    Usa lru_cache via _check_tk_usable() para evitar criar Tk root múltiplas vezes.
    """
    return _check_tk_usable()


# Garantir que tb sempre existe, mesmo se ttkbootstrap não estiver instalado
tb = None
tb_style = None

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
    prefixes = ("src.", "src.infra.", "src.adapters.", "src.db.")
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
# FIXTURES DE TK/TKINTER - Ambiente gráfico seguro para testes
# ============================================================================


@pytest.fixture
def tk_root(tk_root_session) -> Generator[TkMisc, None, None]:
    """
    Cria uma janela Toplevel segura e invisível para testes de UI.

    Usa Toplevel em vez de Tk() para evitar conflitos com o root principal
    da sessão. Tkinter recomenda apenas um Tk() por processo; janelas extras
    devem ser Toplevel.

    Em ambientes sem Tk válido (CI/headless), o teste é automaticamente
    marcado como skip com mensagem clara, evitando TclError no output.

    Garante cleanup automático via teardown.

    TEST-003: Cleanup aprimorado para evitar vazamento entre testes.

    Examples:
        >>> def test_frame_creation(tk_root):
        ...     frame = Frame(tk_root)
        ...     assert frame.master is tk_root
    """
    if not TK_AVAILABLE:
        pytest.skip("Tkinter não está disponível neste ambiente")

    # TEST-003: Forçar garbage collection antes de criar novo Toplevel
    gc.collect()

    try:
        import tkinter as tk

        win = tk.Toplevel(tk_root_session)
        win.withdraw()

        # TEST-003: Limpar cache do ttkbootstrap Style para evitar referências a Tk destruídos
        try:
            import ttkbootstrap.style

            # Forçar recriação do StyleBuilderTTK com o novo Toplevel
            if hasattr(ttkbootstrap.style, "_builder_cache"):
                ttkbootstrap.style._builder_cache.clear()
        except (ImportError, AttributeError):
            pass

    except tk.TclError as exc:
        pytest.skip(f"Toplevel não disponível (TclError: {exc}) – pulando teste dependente de Tk")

    # Forçar update_idletasks para garantir que o Toplevel está pronto
    try:
        win.update_idletasks()
    except tk.TclError:
        pass

    yield win

    # TEST-003: Cleanup robusto com tratamento de exceções
    try:
        if win.winfo_exists():
            # Destruir todos os filhos primeiro (de trás para frente para evitar problemas de ordem)
            children = list(win.winfo_children())
            for child in reversed(children):
                try:
                    child.destroy()
                except tk.TclError:
                    pass

            # TEST-003: Limpar variáveis Tkinter associadas
            try:
                for var_name in win.tk.call("info", "vars"):
                    try:
                        win.tk.unsetvar(str(var_name))
                    except tk.TclError:
                        pass
            except tk.TclError:
                pass

            win.destroy()
    except tk.TclError:
        pass

    # TEST-003: Forçar garbage collection duplo após destruir
    gc.collect()
    gc.collect()


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

    with sqlite3.connect(str(db_path)) as conn:
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


@pytest.fixture(scope="session", autouse=True)
def tcl_session() -> Generator[TkTcl, None, None]:
    """
    Cria um único interpreter Tcl leve para a sessão de testes (AUTOUSE).

    Esta fixture é executada automaticamente no início da sessão de testes,
    criando um interpreter Tcl que provê funcionalidades básicas de Tk sem
    inicializar o subsistema completo de GUI. Isso evita RuntimeError do tipo
    "No master specified and tkinter.NoDefaultRoot() was called" em testes
    que não criam widgets mas importam módulos que dependem de Tkinter.

    Para testes que realmente criam widgets Tk, use a fixture tk_root_session
    explicitamente no teste.

    Benefício de performance: ~0.5-1.0s mais rápido que tk_root_session.
    """
    if not TK_AVAILABLE:
        # Em ambientes sem Tkinter, não criar Tcl e yieldar com segurança
        yield None  # type: ignore
        return

    try:
        import tkinter as tk

        interp = tk.Tcl()
    except tk.TclError as exc:
        pytest.skip(f"Tcl nao esta disponivel neste ambiente de testes (TclError: {exc})")

    # Garante que o Tcl msgcat esteja disponível (ttkbootstrap pode precisar)
    try:
        interp.eval("package require msgcat")
    except tk.TclError:
        pass

    yield interp


@pytest.fixture(scope="session")
def tk_root_session() -> Generator[TkTk, None, None]:
    """
    Cria um único interpreter Tk completo para a sessão de testes de UI.

    ⚠️  IMPORTANTE: Esta fixture NÃO é autouse. Solicite explicitamente em
        testes que REALMENTE criam widgets Tk (Toplevel, Frame, Button, etc).

    Esta fixture cria um root Tkinter global oculto que evita RuntimeError do
    tipo "No master specified and tkinter.NoDefaultRoot() was called".

    Marca o root como 'de teste' e protege o método destroy, para que
    nenhum código de produção/teste mate o interpreter durante os testes.

    Isso evita o erro "_tkinter.TclError: can't invoke 'tk' command:
    application has been destroyed" quando múltiplos testes precisam de Tk.
    """
    if not TK_AVAILABLE:
        pytest.skip("Tkinter não está disponível neste ambiente")

    try:
        import tkinter as tk

        root = tk.Tk()
    except tk.TclError as exc:
        # Em ambientes sem Tk (CI/headless), skip com mensagem detalhada
        pytest.skip(f"Tkinter nao esta disponivel neste ambiente de testes (TclError: {exc})")

    root.withdraw()

    # Garante que o Tcl msgcat esteja disponível (ttkbootstrap usa ::msgcat::mcmset)
    try:
        root.tk.call("package", "require", "msgcat")
    except tk.TclError:
        # Se o pacote msgcat não existir no ambiente, não falhar aqui;
        # porém isso evita crash em ambientes onde ele existe mas não está carregado.
        pass

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


# ============================================================================
# SKIP AUTOMÁTICO DE TESTES COM CRASH CONHECIDO NO WINDOWS + SMOKE SUITE
# ============================================================================


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """
    Modifica a coleção de testes:
    1. Filtra para smoke suite se --smoke estiver ativo
    2. Pula testes de PDF Preview que causam crash no Windows

    Para forçar execução dos testes de PDF: RC_RUN_PDF_UI_TESTS=1
    """
    # --- SMOKE SUITE ---
    if config.getoption("smoke", default=False):
        try:
            prefixes = _load_smoke_prefixes()
        except FileNotFoundError as exc:
            raise pytest.UsageError(f"--smoke ativo, mas arquivo não encontrado: {exc}") from exc

        if not prefixes:
            raise pytest.UsageError("--smoke ativo, mas smoke_nodeids.txt está vazio")

        # Detectar quais prefixes têm match
        matched: dict[str, bool] = {p: False for p in prefixes}
        for item in items:
            nid = item.nodeid.replace("\\", "/")
            for p in prefixes:
                if nid.startswith(p):
                    matched[p] = True
                    break

        unmatched = [p for p, ok in matched.items() if not ok]
        if unmatched:
            if config.getoption("smoke_strict", default=False):
                raise pytest.UsageError("Entradas sem match no smoke_nodeids.txt:\n- " + "\n- ".join(unmatched))
            setattr(config, "_smoke_unmatched_prefixes", unmatched)

        # Filtrar itens
        selected: list[pytest.Item] = []
        deselected: list[pytest.Item] = []
        for item in items:
            nodeid = item.nodeid.replace("\\", "/")
            if nodeid.startswith(prefixes):
                selected.append(item)
            else:
                deselected.append(item)

        if deselected:
            config.hook.pytest_deselected(items=deselected)

        items[:] = selected

    # --- SKIP PDF PREVIEW CRASH (Windows) ---
    if os.getenv("RC_RUN_PDF_UI_TESTS") == "1":
        return

    if sys.platform.startswith("win"):
        crash_files = {
            "tests/unit/modules/pdf_preview/views/test_view_main_window_contract_fasePDF_final.py",
            "tests/unit/modules/pdf_preview/views/test_view_widgets_contract_fasePDF_final.py",
        }
        for item in items:
            p = str(item.fspath).replace("\\", "/")
            if any(p.endswith(f) for f in crash_files):
                item.add_marker(
                    pytest.mark.skip(
                        reason="Windows: ttkbootstrap/tkinter element_create causa access violation (crash). Rodar com RC_RUN_PDF_UI_TESTS=1 se precisar."
                    )
                )


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:
    """Mostra aviso sobre entradas sem match no smoke_nodeids.txt."""
    unmatched = getattr(config, "_smoke_unmatched_prefixes", None)
    if unmatched:
        terminalreporter.write_line("")
        terminalreporter.write_line("[smoke] ATENÇÃO: entradas sem match no smoke_nodeids.txt:")
        for p in unmatched:
            terminalreporter.write_line(f"  - {p}")
