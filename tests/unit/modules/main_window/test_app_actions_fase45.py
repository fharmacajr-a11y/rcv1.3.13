"""
TESTE_1 - app_actions

Alvo: aumentar a cobertura de src/modules/main_window/app_actions.py na fase 45,
validando fluxos felizes, erros esperados e bordas das acoes da janela principal.
"""

from __future__ import annotations

import logging
import sys
import types
from unittest.mock import MagicMock

import pytest

# Skip GUI tests if CustomTkinter is not available
pytestmark = pytest.mark.gui

import src.modules.main_window.app_actions as app_actions
from src.modules.main_window.app_actions import AppActions


def _stub_tk_modules(monkeypatch):
    """Instala stubs minimos de tkinter/messagebox/filedialog e retorna chamadas e respostas configuraveis."""
    calls = {"showwarning": [], "showerror": [], "showinfo": [], "askyesno": [], "askdirectory": []}
    responses = {"askyesno": False, "askdirectory": None}

    def record(name):
        def _inner(*args, **kwargs):
            calls[name].append((args, kwargs))
            return responses.get(name)

        return _inner

    class _FakeToplevel:
        """Fake Toplevel que implementa métodos no-op para evitar AttributeError."""

        def __init__(self, *args, **kwargs):
            pass

        def withdraw(self):
            pass

        def title(self, text=""):
            pass

        def resizable(self, width=True, height=True):
            pass

        def transient(self, parent=None):
            pass

        def protocol(self, name, func):
            pass

        def iconbitmap(self, path=""):
            pass

        def geometry(self, geometry=""):
            pass

        def configure(self, **kwargs):
            pass

        def destroy(self):
            pass

        def deiconify(self):
            pass

    class _FakeTclError(Exception):
        """Fake TclError para compatibilidade com imports de tkinter."""

        pass

    class _FakeWidget:
        """Classe base fake para widgets tkinter/ttk."""

        def __init__(self, *args, **kwargs):
            pass

        def configure(self, **kwargs):
            pass

        def pack(self, **kwargs):
            pass

        def grid(self, **kwargs):
            pass

        def place(self, **kwargs):
            pass

        def bind(self, *args, **kwargs):
            pass

    messagebox_stub = types.SimpleNamespace(
        showwarning=record("showwarning"),
        showerror=record("showerror"),
        showinfo=record("showinfo"),
        askyesno=record("askyesno"),
    )
    filedialog_stub = types.SimpleNamespace(askdirectory=record("askdirectory"))

    # TTK stub com componentes necessários
    ttk_stub = types.SimpleNamespace(
        Frame=_FakeWidget,
        Label=_FakeWidget,
        Button=_FakeWidget,
        Entry=_FakeWidget,
        Progressbar=_FakeWidget,
    )

    # ScrolledText stub
    scrolledtext_stub = types.SimpleNamespace(ScrolledText=_FakeWidget)

    # Usar ModuleType para se parecer mais com módulo real
    tk_module = types.ModuleType("tkinter")
    tk_module.messagebox = messagebox_stub
    tk_module.filedialog = filedialog_stub
    tk_module.Toplevel = _FakeToplevel
    tk_module.Misc = object  # Interface base do tkinter
    tk_module.TclError = _FakeTclError
    tk_module.Event = type("Event", (), {})  # Fake Event class para imports
    tk_module.Grid = type("Grid", (), {})
    tk_module.Pack = type("Pack", (), {})
    tk_module.Place = type("Place", (), {})
    tk_module.ttk = ttk_stub
    tk_module.scrolledtext = scrolledtext_stub

    monkeypatch.setitem(sys.modules, "tkinter", tk_module)
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", messagebox_stub)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", filedialog_stub)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", ttk_stub)
    monkeypatch.setitem(sys.modules, "tkinter.scrolledtext", scrolledtext_stub)

    # Pre-injetar stubs de uploads para evitar importação real (CTkTreeview)
    _stub_uploads_modules(monkeypatch)

    return calls, responses


class _ImmediateThread:
    """Thread stub que executa o target imediatamente ao chamar start(), evitando race conditions nos testes."""

    def __init__(self, target=None, daemon=None, **kwargs):
        self._target = target

    def start(self):
        if self._target:
            self._target()


def _stub_pdf_dependencies(monkeypatch):
    """Garante que imports de pdf_batch_converter usem stubs sem tkinter real."""
    convert_mock = MagicMock(return_value=[])
    pdf_tools_module = types.ModuleType("src.modules.pdf_tools.pdf_batch_from_images")
    pdf_tools_module.convert_subfolders_images_to_pdf = convert_mock
    monkeypatch.setitem(sys.modules, "src.modules.pdf_tools.pdf_batch_from_images", pdf_tools_module)

    dialog_class = MagicMock()
    progress_module = types.ModuleType("src.ui.progress.pdf_batch_progress")
    progress_module.PDFBatchProgressDialog = dialog_class

    progress_pkg = types.ModuleType("src.ui.progress")
    progress_pkg.__path__ = []
    progress_pkg.PDFBatchProgressDialog = dialog_class
    progress_pkg.pdf_batch_progress = progress_module

    monkeypatch.setitem(sys.modules, "src.ui.progress.pdf_batch_progress", progress_module)
    monkeypatch.setitem(sys.modules, "src.ui.progress", progress_pkg)
    ui_pkg = sys.modules.get("src.ui")
    if ui_pkg is None:
        ui_pkg = types.ModuleType("src.ui")
        ui_pkg.__path__ = []
        monkeypatch.setitem(sys.modules, "src.ui", ui_pkg)
    monkeypatch.setattr(ui_pkg, "progress", progress_pkg, raising=False)

    # Aplica stub de threading.Thread para execução síncrona no módulo threading
    import threading

    monkeypatch.setattr(threading, "Thread", _ImmediateThread)

    return convert_mock, dialog_class


def _stub_uploads_modules(monkeypatch):
    """Pre-injeta stubs para src.modules.uploads e sub-módulos.

    Evita que monkeypatch.setattr("src.modules.uploads.X", ...) cause
    importação real do módulo, que falha sem tkinter funcional (CTkTreeview
    tenta `from tkinter import Event, Grid, Pack, Place, ttk`).
    """
    # src.modules.uploads
    uploads_pkg = sys.modules.get("src.modules.uploads")
    if uploads_pkg is None:
        uploads_pkg = types.ModuleType("src.modules.uploads")
        uploads_pkg.__path__ = []  # type: ignore[attr-defined]
        uploads_pkg.open_files_browser = MagicMock()
        monkeypatch.setitem(sys.modules, "src.modules.uploads", uploads_pkg)
        # Vincular ao pacote pai
        src_modules = sys.modules.get("src.modules")
        if src_modules is not None:
            monkeypatch.setattr(src_modules, "uploads", uploads_pkg, raising=False)

    # src.modules.uploads.components
    uploads_comp = sys.modules.get("src.modules.uploads.components")
    if uploads_comp is None:
        uploads_comp = types.ModuleType("src.modules.uploads.components")
        uploads_comp.__path__ = []  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "src.modules.uploads.components", uploads_comp)
        uploads_pkg.components = uploads_comp  # type: ignore[attr-defined]

    # src.modules.uploads.components.helpers
    uploads_helpers = sys.modules.get("src.modules.uploads.components.helpers")
    if uploads_helpers is None:
        uploads_helpers = types.ModuleType("src.modules.uploads.components.helpers")
        uploads_helpers.client_prefix_for_id = MagicMock()
        uploads_helpers.get_clients_bucket = MagicMock()
        monkeypatch.setitem(sys.modules, "src.modules.uploads.components.helpers", uploads_helpers)
        uploads_comp.helpers = uploads_helpers  # type: ignore[attr-defined]

    # src.modules.uploads.uploader_supabase
    uploads_supa = sys.modules.get("src.modules.uploads.uploader_supabase")
    if uploads_supa is None:
        uploads_supa = types.ModuleType("src.modules.uploads.uploader_supabase")
        uploads_supa.send_to_supabase_interactive = MagicMock()
        monkeypatch.setitem(sys.modules, "src.modules.uploads.uploader_supabase", uploads_supa)
        uploads_pkg.uploader_supabase = uploads_supa  # type: ignore[attr-defined]


def test_novo_cliente_chama_app_core(monkeypatch):
    recorded = {}

    def fake_novo_cliente(app):
        recorded["app"] = app

    monkeypatch.setattr("src.core.app_core.novo_cliente", fake_novo_cliente)

    app = object()
    actions = AppActions(app)

    actions.novo_cliente()

    assert recorded["app"] is app


def test_editar_cliente_sem_selecao_mostra_alerta(monkeypatch):
    calls, _ = _stub_tk_modules(monkeypatch)
    app = types.SimpleNamespace(_selected_main_values=lambda: [])
    actions = AppActions(app)

    actions.editar_cliente()

    assert calls["showwarning"]
    assert not calls["showerror"]


def test_editar_cliente_com_id_invalido_mostra_erro(monkeypatch):
    calls, _ = _stub_tk_modules(monkeypatch)
    app = types.SimpleNamespace(_selected_main_values=lambda: [None])
    monkeypatch.setattr("src.core.app_core.editar_cliente", lambda *args, **kwargs: pytest.fail("nao deve chamar"))
    actions = AppActions(app)

    actions.editar_cliente()

    assert calls["showerror"]
    assert not calls["showwarning"]


def test_editar_cliente_valido_chama_app_core(monkeypatch):
    calls, _ = _stub_tk_modules(monkeypatch)
    recorded = {}

    def fake_editar(app, pk):
        recorded["args"] = (app, pk)

    monkeypatch.setattr("src.core.app_core.editar_cliente", fake_editar)
    app = types.SimpleNamespace(_selected_main_values=lambda: ["10"])
    actions = AppActions(app)

    actions.editar_cliente()

    assert recorded["args"] == (app, 10)
    assert not calls["showwarning"]
    assert not calls["showerror"]


def test_excluir_cliente_sem_selecao_apenas_log(monkeypatch):
    logger = MagicMock()
    actions = AppActions(types.SimpleNamespace(_selected_main_values=lambda: []), logger=logger)

    actions._excluir_cliente()

    logger.info.assert_called_once()
    logger.error.assert_not_called()


def test_excluir_cliente_com_id_invalido_mostra_erro(monkeypatch):
    calls, _ = _stub_tk_modules(monkeypatch)
    logger = MagicMock()
    actions = AppActions(types.SimpleNamespace(_selected_main_values=lambda: ["abc"]), logger=logger)

    monkeypatch.setattr(
        "src.modules.clientes.core.service.mover_cliente_para_lixeira",
        lambda *args, **kwargs: pytest.fail("nao deve mover"),
    )

    actions._excluir_cliente()

    assert calls["showerror"]
    logger.error.assert_called_once()


def test_excluir_cliente_cancelado_na_confirmacao(monkeypatch):
    calls, responses = _stub_tk_modules(monkeypatch)
    responses["askyesno"] = False
    logger = MagicMock()
    mover_mock = MagicMock()
    monkeypatch.setattr("src.modules.clientes.core.service.mover_cliente_para_lixeira", mover_mock)

    app = types.SimpleNamespace(_selected_main_values=lambda: ["7", "ACME"])
    actions = AppActions(app, logger=logger)

    actions._excluir_cliente()

    assert calls["askyesno"]
    mover_mock.assert_not_called()
    logger.info.assert_not_called()


def test_excluir_cliente_sucesso_atualiza_fluxos(monkeypatch):
    calls, responses = _stub_tk_modules(monkeypatch)
    responses["askyesno"] = True

    mover_mock = MagicMock()
    refresh_mock = MagicMock()
    monkeypatch.setattr("src.modules.clientes.core.service.mover_cliente_para_lixeira", mover_mock)
    monkeypatch.setattr("src.modules.lixeira.refresh_if_open", refresh_mock)

    load_called = {}

    def fake_carregar():
        load_called["ok"] = True

    app = types.SimpleNamespace(_selected_main_values=lambda: ["42", " ACME "], carregar=fake_carregar)
    logger = MagicMock()
    actions = AppActions(app, logger=logger)

    actions._excluir_cliente()

    mover_mock.assert_called_once_with(42)
    assert load_called.get("ok") is True
    refresh_mock.assert_called_once_with()
    assert calls["showinfo"]
    logger.info.assert_called()


def test_abrir_lixeira_usa_lixeira_views_moderno(monkeypatch):
    """Valida que abrir_lixeira sempre usa src.modules.lixeira.views.lixeira."""
    from unittest.mock import MagicMock

    app = object()
    actions = AppActions(app)

    mock_abrir = MagicMock()
    monkeypatch.setattr("src.modules.lixeira.views.lixeira.abrir_lixeira", mock_abrir)

    actions.abrir_lixeira()

    mock_abrir.assert_called_once_with(app)


def test_open_client_storage_subfolders_sem_selecao_exibe_alerta(monkeypatch):
    calls, _ = _stub_tk_modules(monkeypatch)
    monkeypatch.setattr("src.modules.uploads.open_files_browser", lambda *a, **k: pytest.fail("nao deve abrir"))

    app = types.SimpleNamespace(_selected_main_values=lambda: [])
    actions = AppActions(app)

    actions.open_client_storage_subfolders()

    assert calls["showwarning"]


def test_open_client_storage_subfolders_sem_org_exibe_erro(monkeypatch):
    calls, _ = _stub_tk_modules(monkeypatch)
    monkeypatch.setattr("src.modules.uploads.open_files_browser", lambda *a, **k: pytest.fail("nao deve abrir"))

    app = types.SimpleNamespace(
        _selected_main_values=lambda: ["1", "Razao", "CNPJ"],
        _get_user_cached=lambda: {"id": "user1"},
        _get_org_id_cached=lambda _uid: None,
    )
    actions = AppActions(app)

    actions.open_client_storage_subfolders()

    assert calls["showerror"]


def test_open_client_storage_subfolders_chama_browser_com_parametros(monkeypatch):
    calls, _ = _stub_tk_modules(monkeypatch)
    browser_called = {}

    def fake_browser(*args, **kwargs):
        browser_called["args"] = args
        browser_called["kwargs"] = kwargs

    monkeypatch.setattr("src.modules.uploads.open_files_browser", fake_browser)
    monkeypatch.setattr("src.modules.uploads.components.helpers.client_prefix_for_id", lambda cid, oid: f"{oid}/{cid}")
    monkeypatch.setattr("src.modules.uploads.components.helpers.get_clients_bucket", lambda: "bucket-x")

    app = types.SimpleNamespace(
        _selected_main_values=lambda: ["2", "Razao", "CNPJ"],
        _get_user_cached=lambda: {"id": "u1"},
        _get_org_id_cached=lambda _uid: "org-9",
    )
    actions = AppActions(app)

    actions.open_client_storage_subfolders()

    assert browser_called["kwargs"]["org_id"] == "org-9"
    assert browser_called["kwargs"]["client_id"] == 2
    assert browser_called["kwargs"]["razao"] == "Razao"
    assert browser_called["kwargs"]["cnpj"] == "CNPJ"
    assert browser_called["kwargs"]["bucket"] == "bucket-x"
    assert browser_called["kwargs"]["base_prefix"] == "org-9/2"
    assert browser_called["kwargs"]["start_prefix"] == "org-9/2"
    assert browser_called["kwargs"]["modal"] is True
    assert not calls["showerror"]


def test_enviar_para_supabase_sucesso_chama_uploader(monkeypatch):
    calls, _ = _stub_tk_modules(monkeypatch)
    recorded = {}

    def fake_uploader(app, default_bucket, base_prefix, default_subprefix):
        recorded["params"] = (app, default_bucket, base_prefix, default_subprefix)
        return 1, 0

    monkeypatch.setenv("SUPABASE_BUCKET", "custom-bucket")
    monkeypatch.setattr("src.modules.uploads.uploader_supabase.send_to_supabase_interactive", fake_uploader)

    app = types.SimpleNamespace(get_current_client_storage_prefix=lambda: "org/client")
    logger = MagicMock()
    actions = AppActions(app, logger=logger)

    actions.enviar_para_supabase()

    assert recorded["params"] == (app, "custom-bucket", "org/client", "GERAL")
    assert not calls["showerror"]
    logger.info.assert_called()


def test_enviar_para_supabase_erro_mostra_dialogo(monkeypatch):
    calls, _ = _stub_tk_modules(monkeypatch)

    def fake_uploader(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.modules.uploads.uploader_supabase.send_to_supabase_interactive", fake_uploader)

    app = types.SimpleNamespace(get_current_client_storage_prefix=lambda: "base")
    logger = MagicMock()
    actions = AppActions(app, logger=logger)

    actions.enviar_para_supabase()

    assert calls["showerror"]
    logger.error.assert_called()


def test_run_pdf_batch_converter_cancela_sem_pasta(monkeypatch):
    calls, responses = _stub_tk_modules(monkeypatch)
    _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = ""

    app = types.SimpleNamespace()
    actions = AppActions(app)

    actions.run_pdf_batch_converter()

    assert calls["askdirectory"]
    assert not calls["showerror"]


def test_run_pdf_batch_converter_caminho_invalido(monkeypatch, tmp_path):
    calls, responses = _stub_tk_modules(monkeypatch)
    _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path / "naoexiste")

    app = types.SimpleNamespace()
    actions = AppActions(app)

    actions.run_pdf_batch_converter()

    assert calls["showerror"]


def test_run_pdf_batch_converter_sem_imagens_mostra_resultado(monkeypatch, tmp_path):
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, _ = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")
    recorded_msg = {}

    def fake_show_result(parent, message):
        recorded_msg["message"] = message

    monkeypatch.setattr(app_actions, "show_conversion_result", fake_show_result)

    actions = AppActions(types.SimpleNamespace())

    actions.run_pdf_batch_converter()

    assert "Nenhum PDF foi gerado" in recorded_msg["message"]
    assert calls["showwarning"] == []
    assert calls["showerror"] == []
    convert_mock.assert_not_called()


def test_excluir_cliente_log_falha_capturada(monkeypatch):
    """Testa que exceção no log não quebra o fluxo quando não há seleção."""
    logger = MagicMock()
    logger.info.side_effect = RuntimeError("log boom")
    logger.debug = MagicMock()

    actions = AppActions(types.SimpleNamespace(_selected_main_values=lambda: []), logger=logger)

    actions._excluir_cliente()

    logger.info.assert_called_once()
    logger.debug.assert_called_once()


def test_excluir_cliente_falha_ao_mover(monkeypatch):
    """Testa que exceção ao mover cliente para lixeira mostra erro."""
    calls, responses = _stub_tk_modules(monkeypatch)
    responses["askyesno"] = True
    logger = MagicMock()

    def fake_mover(_client_id):
        raise RuntimeError("DB error")

    monkeypatch.setattr("src.modules.clientes.core.service.mover_cliente_para_lixeira", fake_mover)

    app = types.SimpleNamespace(_selected_main_values=lambda: ["5", "Test"])
    actions = AppActions(app, logger=logger)

    actions._excluir_cliente()

    assert calls["showerror"]
    logger.exception.assert_called()


def test_excluir_cliente_falha_ao_carregar(monkeypatch):
    """Testa que exceção ao atualizar lista é logada mas não quebra fluxo."""
    calls, responses = _stub_tk_modules(monkeypatch)
    responses["askyesno"] = True
    logger = MagicMock()

    mover_mock = MagicMock()
    refresh_mock = MagicMock()
    monkeypatch.setattr("src.modules.clientes.core.service.mover_cliente_para_lixeira", mover_mock)
    monkeypatch.setattr("src.modules.lixeira.refresh_if_open", refresh_mock)

    def fake_carregar():
        raise RuntimeError("Refresh error")

    app = types.SimpleNamespace(_selected_main_values=lambda: ["10", "Company"], carregar=fake_carregar)
    actions = AppActions(app, logger=logger)

    actions._excluir_cliente()

    mover_mock.assert_called_once_with(10)
    logger.exception.assert_called()
    assert calls["showinfo"]


def test_excluir_cliente_falha_refresh_lixeira(monkeypatch):
    """Testa que exceção ao atualizar lixeira é logada (debug)."""
    calls, responses = _stub_tk_modules(monkeypatch)
    responses["askyesno"] = True
    logger = MagicMock()

    mover_mock = MagicMock()
    monkeypatch.setattr("src.modules.clientes.core.service.mover_cliente_para_lixeira", mover_mock)

    def fake_refresh():
        raise RuntimeError("Lixeira UI error")

    monkeypatch.setattr("src.modules.lixeira.refresh_if_open", fake_refresh)

    app = types.SimpleNamespace(_selected_main_values=lambda: ["3"], carregar=lambda: None)
    actions = AppActions(app, logger=logger)

    actions._excluir_cliente()

    logger.debug.assert_called()
    assert calls["showinfo"]


def test_open_client_storage_subfolders_sem_usuario_exibe_erro(monkeypatch):
    """Testa que falta de usuário autenticado mostra erro."""
    calls, _ = _stub_tk_modules(monkeypatch)

    app = types.SimpleNamespace(
        _selected_main_values=lambda: ["1", "Razao", "CNPJ"],
        _get_user_cached=lambda: None,
    )
    actions = AppActions(app)

    actions.open_client_storage_subfolders()

    assert calls["showerror"]


def test_open_client_storage_subfolders_id_invalido_exibe_erro(monkeypatch):
    """Testa que ID inválido mostra erro."""
    calls, _ = _stub_tk_modules(monkeypatch)

    app = types.SimpleNamespace(_selected_main_values=lambda: ["abc", "Razao"])
    actions = AppActions(app)

    actions.open_client_storage_subfolders()

    assert calls["showerror"]


def test_ver_subpastas_alias_delega_para_novo_metodo(monkeypatch):
    """Garante que o wrapper legacy ainda funciona."""
    app = types.SimpleNamespace(_selected_main_values=lambda: [])
    actions = AppActions(app)
    actions.open_client_storage_subfolders = MagicMock()

    actions.ver_subpastas()

    actions.open_client_storage_subfolders.assert_called_once()


def test_enviar_para_supabase_sem_base_prefix(monkeypatch):
    """Testa envio sem cliente selecionado (base_prefix vazio)."""
    calls, _ = _stub_tk_modules(monkeypatch)
    logger = MagicMock()
    recorded = {}

    def fake_uploader(app, default_bucket, base_prefix, default_subprefix):
        recorded["base_prefix"] = base_prefix
        return 0, 0

    monkeypatch.setattr("src.modules.uploads.uploader_supabase.send_to_supabase_interactive", fake_uploader)

    app = types.SimpleNamespace(get_current_client_storage_prefix=lambda: "")
    actions = AppActions(app, logger=logger)

    actions.enviar_para_supabase()

    assert recorded["base_prefix"] == ""
    logger.warning.assert_called()


def test_enviar_para_supabase_sem_uploads(monkeypatch):
    """Testa que 0 uploads (cancelado) é logado corretamente."""
    logger = MagicMock()

    def fake_uploader(*args, **kwargs):
        return 0, 0

    monkeypatch.setattr("src.modules.uploads.uploader_supabase.send_to_supabase_interactive", fake_uploader)

    app = types.SimpleNamespace(get_current_client_storage_prefix=lambda: "base")
    actions = AppActions(app, logger=logger)

    actions.enviar_para_supabase()

    logger.info.assert_called()


def test_run_pdf_batch_converter_usuario_cancela_delecao(monkeypatch, tmp_path):
    """Testa que cancelamento no diálogo de deleção de imagens interrompe fluxo."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, _ = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "cancel")

    actions = AppActions(types.SimpleNamespace())

    actions.run_pdf_batch_converter()

    convert_mock.assert_not_called()
    assert not calls["showerror"]


def test_run_pdf_batch_converter_erro_ao_analisar_subpastas(monkeypatch, tmp_path):
    """Testa que erro ao iterar subpastas mostra erro."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, _ = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")
    logger = MagicMock()

    from pathlib import Path

    original_iterdir = Path.iterdir

    def fake_iterdir(self):
        if self == tmp_path:
            raise RuntimeError("Permission denied")
        return original_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", fake_iterdir)

    actions = AppActions(types.SimpleNamespace(), logger=logger)

    actions.run_pdf_batch_converter()

    assert calls["showerror"]
    logger.exception.assert_called()
    convert_mock.assert_not_called()


def test_run_pdf_batch_converter_com_imagens_executa_conversao(monkeypatch, tmp_path):
    """Testa conversão bem-sucedida com imagens."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "yes")

    subdir = tmp_path / "subdir1"
    subdir.mkdir()
    img = subdir / "test.jpg"
    img.write_bytes(b"fake image")

    convert_mock.return_value = [subdir / "test.pdf"]
    recorded_msg = {}

    def fake_show_result(parent, message):
        recorded_msg["message"] = message

    monkeypatch.setattr(app_actions, "show_conversion_result", fake_show_result)

    app_mock = MagicMock()
    app_mock.after = lambda delay, fn: fn()

    actions = AppActions(app_mock)

    actions.run_pdf_batch_converter()

    convert_mock.assert_called_once()
    assert "PDFs gerados: 1" in recorded_msg["message"]
    assert "EXCLUÍDAS" in recorded_msg["message"]


def test_run_pdf_batch_converter_erro_durante_conversao(monkeypatch, tmp_path):
    """Testa que erro durante conversão é tratado."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "subdir1"
    subdir.mkdir()
    img = subdir / "test.png"
    img.write_bytes(b"fake")

    convert_mock.side_effect = RuntimeError("Conversion failed")
    logger = MagicMock()

    app_mock = MagicMock()
    app_mock.after = lambda delay, fn: fn()

    actions = AppActions(app_mock, logger=logger)

    actions.run_pdf_batch_converter()

    logger.exception.assert_called()
    assert calls["showerror"]


def test_run_pdf_batch_converter_conversao_retorna_vazio(monkeypatch, tmp_path):
    """Testa que conversão retornando lista vazia mostra mensagem."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "subdir1"
    subdir.mkdir()
    img = subdir / "test.jpeg"
    img.write_bytes(b"data")

    convert_mock.return_value = []
    recorded_msg = {}

    def fake_show_result(parent, message):
        recorded_msg["message"] = message

    monkeypatch.setattr(app_actions, "show_conversion_result", fake_show_result)

    app_mock = MagicMock()
    app_mock.after = lambda delay, fn: fn()

    actions = AppActions(app_mock)

    actions.run_pdf_batch_converter()

    assert "Nenhum PDF foi gerado" in recorded_msg["message"]


def test_run_pdf_batch_converter_log_sucesso_falha(monkeypatch, tmp_path):
    """Testa que falha ao logar sucesso não quebra fluxo."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "img.jfif").write_bytes(b"x")

    convert_mock.return_value = [subdir / "pdf.pdf"]
    logger = MagicMock()
    logger.info.side_effect = RuntimeError("log failed")

    recorded_msg = {}

    def fake_show_result(parent, message):
        recorded_msg["message"] = message

    monkeypatch.setattr(app_actions, "show_conversion_result", fake_show_result)

    app_mock = MagicMock()
    app_mock.after = lambda delay, fn: fn()

    actions = AppActions(app_mock, logger=logger)

    actions.run_pdf_batch_converter()

    logger.debug.assert_called()
    assert "PDFs gerados: 1" in recorded_msg["message"]


def test_run_pdf_batch_converter_progress_dialog_falha(monkeypatch, tmp_path):
    """Testa que falha ao criar progress dialog continua conversão."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "img.png").write_bytes(b"data")

    dialog_class.side_effect = RuntimeError("Dialog failed")
    convert_mock.return_value = [subdir / "out.pdf"]

    recorded_msg = {}

    def fake_show_result(parent, message):
        recorded_msg["message"] = message

    monkeypatch.setattr(app_actions, "show_conversion_result", fake_show_result)

    app_mock = MagicMock()
    app_mock.after = lambda delay, fn: fn()

    actions = AppActions(app_mock)

    actions.run_pdf_batch_converter()

    convert_mock.assert_called_once()
    assert "PDFs gerados: 1" in recorded_msg["message"]


def test_run_pdf_batch_converter_progress_update_com_dialog_closed(monkeypatch, tmp_path):
    """Testa que progress_cb retorna early se dialog foi fechado."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "img.jpg").write_bytes(b"x")

    dialog_instance = MagicMock()
    dialog_instance.is_closed = True
    dialog_class.return_value = dialog_instance

    captured_progress_cb = {}

    def fake_convert(root_folder, delete_images, progress_cb):
        captured_progress_cb["cb"] = progress_cb
        progress_cb(100, 100, 1, 1, subdir, "img.jpg")
        return [subdir / "out.pdf"]

    convert_mock.side_effect = fake_convert

    recorded_msg = {}

    def fake_show_result(parent, message):
        recorded_msg["message"] = message

    monkeypatch.setattr(app_actions, "show_conversion_result", fake_show_result)

    app_mock = MagicMock()
    app_mock.after = lambda delay, fn: fn()

    actions = AppActions(app_mock)

    actions.run_pdf_batch_converter()

    dialog_instance.update_progress.assert_not_called()
    assert "PDFs gerados: 1" in recorded_msg["message"]


def test_run_pdf_batch_converter_progress_update_app_after_falha(monkeypatch, tmp_path):
    """Testa que falha em app.after não quebra progress_cb."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "img.jpg").write_bytes(b"x")

    dialog_instance = MagicMock()
    dialog_instance.is_closed = False
    dialog_class.return_value = dialog_instance

    captured_progress_cb = {}

    def fake_convert(root_folder, delete_images, progress_cb):
        captured_progress_cb["cb"] = progress_cb
        progress_cb(50, 100, 1, 1, subdir, "img.jpg")
        return [subdir / "out.pdf"]

    convert_mock.side_effect = fake_convert
    logger = MagicMock()

    recorded_msg = {}

    def fake_show_result(parent, message):
        recorded_msg["message"] = message

    monkeypatch.setattr(app_actions, "show_conversion_result", fake_show_result)

    app_mock = MagicMock()
    app_mock.after.side_effect = RuntimeError("after failed")

    actions = AppActions(app_mock, logger=logger)

    actions.run_pdf_batch_converter()

    logger.debug.assert_called()
    assert "PDFs gerados: 1" in recorded_msg["message"]


def test_run_pdf_batch_converter_on_error_dialog_close_falha(monkeypatch, tmp_path):
    """Testa que erro ao fechar dialog em on_error não quebra."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "img.jpg").write_bytes(b"x")

    dialog_instance = MagicMock()
    dialog_instance.close.side_effect = RuntimeError("Close failed")
    dialog_class.return_value = dialog_instance

    convert_mock.side_effect = RuntimeError("Convert boom")
    logger = MagicMock()

    app_mock = MagicMock()
    app_mock.after = lambda delay, fn: fn()

    actions = AppActions(app_mock, logger=logger)

    actions.run_pdf_batch_converter()

    logger.debug.assert_called()
    assert calls["showerror"]


def test_run_pdf_batch_converter_on_empty_dialog_close_falha(monkeypatch, tmp_path):
    """Testa que erro ao fechar dialog em on_empty não quebra."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "img.jpg").write_bytes(b"x")

    dialog_instance = MagicMock()
    dialog_instance.close.side_effect = RuntimeError("Close failed")
    dialog_class.return_value = dialog_instance

    convert_mock.return_value = []
    logger = MagicMock()

    recorded_msg = {}

    def fake_show_result(parent, message):
        recorded_msg["message"] = message

    monkeypatch.setattr(app_actions, "show_conversion_result", fake_show_result)

    app_mock = MagicMock()
    app_mock.after = lambda delay, fn: fn()

    actions = AppActions(app_mock, logger=logger)

    actions.run_pdf_batch_converter()

    logger.debug.assert_called()
    assert "Nenhum PDF foi gerado" in recorded_msg["message"]


def test_run_pdf_batch_converter_on_done_dialog_close_falha(monkeypatch, tmp_path):
    """Testa que erro ao fechar dialog em on_done não quebra."""
    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "img.jpg").write_bytes(b"x")

    dialog_instance = MagicMock()
    dialog_instance.close.side_effect = RuntimeError("Close failed")
    dialog_class.return_value = dialog_instance

    convert_mock.return_value = [subdir / "out.pdf"]
    logger = MagicMock()

    recorded_msg = {}

    def fake_show_result(parent, message):
        recorded_msg["message"] = message

    monkeypatch.setattr(app_actions, "show_conversion_result", fake_show_result)

    app_mock = MagicMock()
    app_mock.after = lambda delay, fn: fn()

    actions = AppActions(app_mock, logger=logger)

    actions.run_pdf_batch_converter()

    logger.debug.assert_called()
    assert "PDFs gerados: 1" in recorded_msg["message"]


def test_run_pdf_batch_converter_app_after_falha_on_error(monkeypatch, tmp_path):
    """Testa que falha em app.after em on_error executa callback diretamente."""
    import time

    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "img.jpg").write_bytes(b"x")

    convert_mock.side_effect = RuntimeError("Convert error")

    app_mock = MagicMock()
    app_mock.after.side_effect = RuntimeError("after failed")

    actions = AppActions(app_mock)

    actions.run_pdf_batch_converter()

    time.sleep(0.1)

    assert calls["showerror"]


def test_run_pdf_batch_converter_app_after_falha_on_empty(monkeypatch, tmp_path):
    """Testa que falha em app.after em on_empty executa callback diretamente."""
    import time

    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "img.jpg").write_bytes(b"x")

    convert_mock.return_value = []
    recorded_msg = {}

    def fake_show_result(parent, message):
        recorded_msg["message"] = message

    monkeypatch.setattr(app_actions, "show_conversion_result", fake_show_result)

    app_mock = MagicMock()
    app_mock.after.side_effect = RuntimeError("after failed")

    actions = AppActions(app_mock)

    actions.run_pdf_batch_converter()

    time.sleep(0.1)

    assert "Nenhum PDF foi gerado" in recorded_msg["message"]


def test_run_pdf_batch_converter_app_after_falha_on_done(monkeypatch, tmp_path):
    """Testa que falha em app.after em on_done executa callback diretamente."""
    import time

    calls, responses = _stub_tk_modules(monkeypatch)
    convert_mock, dialog_class = _stub_pdf_dependencies(monkeypatch)
    responses["askdirectory"] = str(tmp_path)
    monkeypatch.setattr(app_actions, "ask_delete_images", lambda parent: "no")

    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "img.jpg").write_bytes(b"x")

    convert_mock.return_value = [subdir / "out.pdf"]
    recorded_msg = {}

    def fake_show_result(parent, message):
        recorded_msg["message"] = message

    monkeypatch.setattr(app_actions, "show_conversion_result", fake_show_result)

    app_mock = MagicMock()
    app_mock.after.side_effect = RuntimeError("after failed")

    actions = AppActions(app_mock)

    actions.run_pdf_batch_converter()

    time.sleep(0.1)

    assert "PDFs gerados: 1" in recorded_msg["message"]


def test_abrir_lixeira_loga_erro_quando_modulo_falha(monkeypatch, caplog):
    """Valida que erros ao abrir lixeira são logados corretamente."""
    from unittest.mock import MagicMock

    app = object()
    actions = AppActions(app)

    mock_abrir = MagicMock(side_effect=Exception("Erro simulado"))
    monkeypatch.setattr("src.modules.lixeira.views.lixeira.abrir_lixeira", mock_abrir)

    with caplog.at_level(logging.ERROR):
        actions.abrir_lixeira()

    # Valida que o erro foi logado
    assert any("Erro ao abrir a tela da Lixeira" in rec.message for rec in caplog.records)
    mock_abrir.assert_called_once_with(app)
