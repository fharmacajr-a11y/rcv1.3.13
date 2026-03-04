# -*- coding: utf-8 -*-
"""PR3 – Testes de I/O assíncrono para contatos no EditorDataMixin.

Valida que:
  - _run_in_thread executa work em daemon-thread e despacha callbacks via after()
  - _load_contatos_from_db busca dados em background e preenche textbox na UI thread
  - _save_contatos_to_db lê textbox na UI thread, persiste em background, e chama on_done
  - Erros de rede são tratados sem travar a UI
"""

from __future__ import annotations

import os
import sys
import threading
import time
import types
from unittest.mock import MagicMock, patch

os.environ.setdefault("RC_TESTING", "1")


# ---------------------------------------------------------------------------
# Garantir que o módulo supabase_client é importável (pode precisar de stubs)
# ---------------------------------------------------------------------------


def _ensure_fake_module(name: str, **attrs: object) -> types.ModuleType:
    """Cria módulo fake e injeta em sys.modules SE ainda não existir."""
    if name not in sys.modules:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod
    return sys.modules[name]


# Apenas injetar stubs se os módulos reais não existirem (caso rode isolado)
_ensure_fake_module("src.infra.supabase", db_client=MagicMock())
_ensure_fake_module("src.infra.supabase.db_client", get_supabase=MagicMock())
_ensure_fake_module("src.infra.supabase.auth_client", bind_postgrest_auth_if_any=MagicMock())
_ensure_fake_module("src.infra.supabase.http_client", HTTPX_CLIENT=MagicMock(), HTTPX_TIMEOUT=30)
_ensure_fake_module(
    "src.infra.supabase.storage_client",
    DownloadCancelledError=type("DownloadCancelledError", (Exception,), {}),
    baixar_pasta_zip=MagicMock(),
)
_ensure_fake_module(
    "src.infra.supabase_client",
    get_supabase=MagicMock(),
    supabase=MagicMock(),
    exec_postgrest=MagicMock(),
    is_supabase_online=MagicMock(return_value=False),
    get_supabase_state=MagicMock(),
    is_really_online=MagicMock(return_value=False),
    get_cloud_status_for_ui=MagicMock(),
    bind_postgrest_auth_if_any=MagicMock(),
    HTTPX_CLIENT=MagicMock(),
    HTTPX_TIMEOUT=30,
    DownloadCancelledError=type("DownloadCancelledError", (Exception,), {}),
    baixar_pasta_zip=MagicMock(),
)

# Caminhos para patch — sempre no módulo barrel
_PATCH_GET_SUPABASE = "src.infra.supabase_client.get_supabase"
_PATCH_EXEC_POSTGREST = "src.infra.supabase_client.exec_postgrest"


# ---------------------------------------------------------------------------
# Fake self (simula EditorDialogProto sem tkinter real)
# ---------------------------------------------------------------------------


def _make_fake_self(*, contatos_text_content: str = ""):
    """Cria um objeto que implementa o protocolo mínimo para os testes.

    ``after()`` executa o callback *imediatamente* (simplificação para testes
    sem Tk mainloop).
    """
    fake = MagicMock()
    fake.winfo_exists.return_value = True

    # after(0, fn, *args) → executa fn(*args) imediatamente
    def _fake_after(_ms: int, fn=None, *args):
        if fn is not None:
            fn(*args)
        return "after#1"

    fake.after.side_effect = _fake_after

    # contatos_text: simula CTkTextbox
    _text_store = [contatos_text_content]

    def _text_get(start, end):
        return _text_store[0]

    def _text_delete(start, end):
        _text_store[0] = ""

    def _text_insert(pos, text):
        _text_store[0] = text

    fake.contatos_text.get.side_effect = _text_get
    fake.contatos_text.delete.side_effect = _text_delete
    fake.contatos_text.insert.side_effect = _text_insert

    # save_btn
    fake.save_btn.configure = MagicMock()

    # on_save callback
    fake.on_save = MagicMock()

    # _parse_contatos_from_textbox – delegamos para o método real
    from src.modules.clientes.ui.views._editor_data_mixin import EditorDataMixin

    fake._parse_contatos_from_textbox = lambda: EditorDataMixin._parse_contatos_from_textbox(fake)

    # _run_in_thread – delegar para implementação real (MagicMock criaria um stub)
    fake._run_in_thread = lambda work, **kw: EditorDataMixin._run_in_thread(fake, work, **kw)

    return fake, _text_store


from src.modules.clientes.ui.views._editor_data_mixin import EditorDataMixin  # noqa: E402


# ===========================================================================
# _run_in_thread
# ===========================================================================


class TestRunInThread:
    """Testa o helper genérico _run_in_thread."""

    def test_success_callback_dispatched_via_after(self):
        """on_success é chamado via self.after() na thread principal."""
        fake, _ = _make_fake_self()
        result_box: list = []

        def work():
            return 42

        def on_success(val):
            result_box.append(val)

        EditorDataMixin._run_in_thread(fake, work, on_success=on_success)

        # Esperar a thread completar
        time.sleep(0.3)

        assert result_box == [42]
        # after() foi chamado pelo menos uma vez (para despachar on_success)
        assert fake.after.called

    def test_error_callback_dispatched_via_after(self):
        """on_error é chamado via self.after() quando work lança exceção."""
        fake, _ = _make_fake_self()
        error_box: list = []

        def work():
            raise ConnectionError("timeout")

        def on_error(exc):
            error_box.append(exc)

        EditorDataMixin._run_in_thread(fake, work, on_error=on_error)

        time.sleep(0.3)

        assert len(error_box) == 1
        assert isinstance(error_box[0], ConnectionError)

    def test_callback_skipped_if_widget_destroyed(self):
        """Se winfo_exists() retorna False, callbacks não são chamados."""
        fake, _ = _make_fake_self()
        fake.winfo_exists.return_value = False
        result_box: list = []

        def work():
            return "ok"

        def on_success(val):
            result_box.append(val)

        EditorDataMixin._run_in_thread(fake, work, on_success=on_success)

        time.sleep(0.3)

        # Callback NÃO deve ter sido chamado
        assert result_box == []

    def test_thread_is_daemon(self):
        """Thread criada deve ser daemon (não impede saída do processo)."""
        fake, _ = _make_fake_self()
        thread_ref: list[threading.Thread] = []

        original_start = threading.Thread.start

        def _capture_start(self_thread):
            thread_ref.append(self_thread)
            original_start(self_thread)

        with patch.object(threading.Thread, "start", _capture_start):
            EditorDataMixin._run_in_thread(fake, lambda: None)

        time.sleep(0.2)
        assert len(thread_ref) == 1
        assert thread_ref[0].daemon is True


# ===========================================================================
# _load_contatos_from_db
# ===========================================================================


class TestLoadContatosFromDb:
    """Testa carregamento assíncrono de contatos."""

    def test_fills_textbox_on_success(self):
        """Textbox é preenchido com contatos retornados pelo Supabase."""
        fake, text_store = _make_fake_self()

        mock_response = MagicMock()
        mock_response.data = [
            {"nome": "João", "whatsapp": "11999999999"},
            {"nome": "Maria", "whatsapp": ""},
        ]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch(_PATCH_GET_SUPABASE, return_value=mock_supabase):
            EditorDataMixin._load_contatos_from_db(fake, cliente_id=1)
            time.sleep(0.5)

        assert "João - 11999999999" in text_store[0]
        assert "Maria" in text_store[0]

    def test_empty_response_does_not_touch_textbox(self):
        """Se Supabase retorna lista vazia, textbox não é alterado."""
        fake, text_store = _make_fake_self(contatos_text_content="existente")

        mock_response = MagicMock()
        mock_response.data = []

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch(_PATCH_GET_SUPABASE, return_value=mock_supabase):
            EditorDataMixin._load_contatos_from_db(fake, cliente_id=1)
            time.sleep(0.5)

        # Textbox não foi alterado (mantém conteúdo original)
        assert text_store[0] == "existente"

    def test_network_error_is_logged_not_raised(self):
        """Erro de rede é logado, não propaga exceção nem trava UI."""
        fake, _ = _make_fake_self()

        with patch(_PATCH_GET_SUPABASE, side_effect=ConnectionError("refused")):
            # Não deve lançar exceção
            EditorDataMixin._load_contatos_from_db(fake, cliente_id=1)
            time.sleep(0.5)

    def test_null_fields_handled_gracefully(self):
        """Contatos com nome/whatsapp None são tratados sem erro."""
        fake, text_store = _make_fake_self()

        mock_response = MagicMock()
        mock_response.data = [
            {"nome": None, "whatsapp": None},  # Deve ser ignorado (sem nome)
            {"nome": "Ana", "whatsapp": None},
        ]

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch(_PATCH_GET_SUPABASE, return_value=mock_supabase):
            EditorDataMixin._load_contatos_from_db(fake, cliente_id=1)
            time.sleep(0.5)

        assert text_store[0] == "Ana"


# ===========================================================================
# _save_contatos_to_db
# ===========================================================================


class TestSaveContatosToDb:
    """Testa persistência assíncrona de contatos via RPC atômica."""

    def test_calls_rpc_with_correct_payload(self):
        """RPC rc_save_cliente_contatos é chamada com payload correto."""
        fake, _ = _make_fake_self(contatos_text_content="Carlos - 21888888888\n")

        mock_supabase = MagicMock()
        mock_exec = MagicMock()
        done_event = threading.Event()

        with (
            patch(_PATCH_GET_SUPABASE, return_value=mock_supabase),
            patch(_PATCH_EXEC_POSTGREST, mock_exec),
        ):
            EditorDataMixin._save_contatos_to_db(fake, cliente_id=5, on_done=done_event.set)
            done_event.wait(timeout=2.0)

        # exec_postgrest foi chamado com o request builder do rpc()
        assert mock_exec.called
        # Verificar que rpc() foi chamado com o nome e payload corretos
        mock_supabase.rpc.assert_called_once()
        rpc_args = mock_supabase.rpc.call_args
        assert rpc_args[0][0] == "rc_save_cliente_contatos"
        params = rpc_args[0][1]
        assert params["p_cliente_id"] == 5
        assert len(params["p_contatos"]) == 1
        assert params["p_contatos"][0]["nome"] == "Carlos"
        assert params["p_contatos"][0]["whatsapp"] == "21888888888"

    def test_no_direct_delete_or_insert(self):
        """Python NÃO deve chamar delete() ou insert() diretamente."""
        fake, _ = _make_fake_self(contatos_text_content="Teste - 123")
        mock_supabase = MagicMock()
        mock_exec = MagicMock()
        done_event = threading.Event()

        with (
            patch(_PATCH_GET_SUPABASE, return_value=mock_supabase),
            patch(_PATCH_EXEC_POSTGREST, mock_exec),
        ):
            EditorDataMixin._save_contatos_to_db(fake, 1, on_done=done_event.set)
            done_event.wait(timeout=2.0)

        # table() NÃO deve ter sido chamado (nem delete nem insert)
        mock_supabase.table.assert_not_called()

    def test_on_done_called_on_success(self):
        """Callback on_done é chamado após sucesso."""
        fake, _ = _make_fake_self(contatos_text_content="A - 1")
        mock_supabase = MagicMock()
        mock_exec = MagicMock()
        done_event = threading.Event()

        with (
            patch(_PATCH_GET_SUPABASE, return_value=mock_supabase),
            patch(_PATCH_EXEC_POSTGREST, mock_exec),
        ):
            EditorDataMixin._save_contatos_to_db(fake, 1, on_done=done_event.set)
            assert done_event.wait(timeout=2.0), "on_done não foi chamado"

    def test_on_done_called_on_rpc_error(self):
        """Callback on_done é chamado mesmo se RPC lançar exceção."""
        fake, _ = _make_fake_self(contatos_text_content="X - 0")
        mock_supabase = MagicMock()
        mock_exec = MagicMock(side_effect=ConnectionError("rpc fail"))
        done_event = threading.Event()

        with (
            patch(_PATCH_GET_SUPABASE, return_value=mock_supabase),
            patch(_PATCH_EXEC_POSTGREST, mock_exec),
        ):
            EditorDataMixin._save_contatos_to_db(fake, 1, on_done=done_event.set)
            assert done_event.wait(timeout=2.0), "on_done não foi chamado após erro RPC"

    def test_rpc_error_preserves_atomicity(self):
        """Se RPC falha, nenhum delete/insert parcial ocorre no Python.

        A atomicidade real é garantida pelo PostgreSQL (a função PL/pgSQL roda
        numa transação). No lado Python, verificamos que NÃO há chamadas
        separadas a table().delete() / table().insert() — tudo passa pelo rpc().
        """
        fake, _ = _make_fake_self(contatos_text_content="Dado - 999")
        mock_supabase = MagicMock()
        mock_exec = MagicMock(side_effect=RuntimeError("simulated RPC failure"))
        done_event = threading.Event()

        with (
            patch(_PATCH_GET_SUPABASE, return_value=mock_supabase),
            patch(_PATCH_EXEC_POSTGREST, mock_exec),
        ):
            EditorDataMixin._save_contatos_to_db(fake, 1, on_done=done_event.set)
            done_event.wait(timeout=2.0)

        # Nenhuma operação table() direta (delete/insert) ocorreu
        mock_supabase.table.assert_not_called()
        # RPC foi chamada (e falhou)
        mock_supabase.rpc.assert_called_once()

    def test_save_btn_disabled_during_save(self):
        """Botão salvar é desabilitado enquanto a persistência roda."""
        fake, _ = _make_fake_self(contatos_text_content="B - 2")
        mock_supabase = MagicMock()
        mock_exec = MagicMock()
        done_event = threading.Event()

        with (
            patch(_PATCH_GET_SUPABASE, return_value=mock_supabase),
            patch(_PATCH_EXEC_POSTGREST, mock_exec),
        ):
            EditorDataMixin._save_contatos_to_db(fake, 1, on_done=done_event.set)

            # Botão deve ser desabilitado IMEDIATAMENTE (antes da thread terminar)
            fake.save_btn.configure.assert_called_with(state="disabled")

            done_event.wait(timeout=2.0)

    def test_empty_textbox_sends_empty_payload(self):
        """Se textbox está vazio, RPC é chamada com payload vazio (só deleta)."""
        fake, _ = _make_fake_self(contatos_text_content="")
        mock_supabase = MagicMock()
        mock_exec = MagicMock()
        done_event = threading.Event()

        with (
            patch(_PATCH_GET_SUPABASE, return_value=mock_supabase),
            patch(_PATCH_EXEC_POSTGREST, mock_exec),
        ):
            EditorDataMixin._save_contatos_to_db(fake, 1, on_done=done_event.set)
            done_event.wait(timeout=2.0)

        # RPC chamada com lista vazia
        mock_supabase.rpc.assert_called_once()
        params = mock_supabase.rpc.call_args[0][1]
        assert params["p_contatos"] == []
        # Sem table() direto
        mock_supabase.table.assert_not_called()

    def test_whatsapp_none_for_empty_string(self):
        """WhatsApp vazio é enviado como None no payload."""
        fake, _ = _make_fake_self(contatos_text_content="Ana")
        mock_supabase = MagicMock()
        mock_exec = MagicMock()
        done_event = threading.Event()

        with (
            patch(_PATCH_GET_SUPABASE, return_value=mock_supabase),
            patch(_PATCH_EXEC_POSTGREST, mock_exec),
        ):
            EditorDataMixin._save_contatos_to_db(fake, 1, on_done=done_event.set)
            done_event.wait(timeout=2.0)

        params = mock_supabase.rpc.call_args[0][1]
        assert params["p_contatos"][0]["whatsapp"] is None
