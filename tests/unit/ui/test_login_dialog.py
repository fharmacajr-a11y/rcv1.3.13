"""Testes unitários para src/ui/login_dialog.py - Microfase UI-TEST-001 + QA-003."""

from __future__ import annotations

import tkinter as tk
from typing import Generator
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.ui.login_dialog import LoginDialog


# ==================== Fixtures ====================


@pytest.fixture
def root(tk_root_session: tk.Tk) -> Generator[tk.Toplevel, None, None]:
    """
    Para cada teste de LoginDialog, cria um Toplevel ligado ao tk_root_session
    e destrói apenas esse Toplevel ao final.

    O tk_root_session (interpreter global) jamais é destruído aqui.
    """
    toplevel = tk.Toplevel(master=tk_root_session)
    toplevel.withdraw()
    yield toplevel
    try:
        for child in toplevel.winfo_children():
            try:
                child.destroy()
            except tk.TclError:
                pass
        toplevel.destroy()
    except tk.TclError:
        # Se o Toplevel já tiver sido destruído pelo próprio dialog, ignora
        pass


@pytest.fixture
def mock_get_supabase():
    """Mock do cliente Supabase."""
    with patch("src.ui.login_dialog.get_supabase") as mock:
        client = MagicMock()
        client.auth.get_session.return_value = MagicMock(
            user=MagicMock(id="user123"),
            session=MagicMock(access_token="at123", refresh_token="rt123"),
        )
        mock.return_value = client
        yield mock


@pytest.fixture
def mock_authenticate_user():
    """Mock da função authenticate_user."""
    with patch("src.ui.login_dialog.authenticate_user") as mock:
        mock.return_value = (True, "Login successful")
        yield mock


@pytest.fixture
def mock_get_access_token():
    """Mock do _get_access_token."""
    with patch("src.ui.login_dialog._get_access_token") as mock:
        mock.return_value = "token123"
        yield mock


@pytest.fixture
def mock_bind_postgrest():
    """Mock do bind_postgrest_auth_if_any."""
    with patch("src.ui.login_dialog.bind_postgrest_auth_if_any") as mock:
        yield mock


@pytest.fixture
def mock_refresh_user():
    """Mock do refresh_current_user_from_supabase."""
    with patch("src.ui.login_dialog.refresh_current_user_from_supabase") as mock:
        yield mock


@pytest.fixture
def mock_healthcheck():
    """Mock do healthcheck."""
    with patch("src.ui.login_dialog.healthcheck") as mock:
        mock.return_value = {"ok": True, "items": []}
        yield mock


@pytest.fixture
def mock_prefs_utils():
    """Mock do módulo prefs_utils."""
    with patch("src.ui.login_dialog.prefs_utils") as mock:
        mock.load_login_prefs.return_value = {}
        yield mock


@pytest.fixture
def mock_resource_path():
    """Mock do resource_path para evitar erros de assets."""
    with patch("src.ui.login_dialog.resource_path") as mock:
        mock.side_effect = lambda x: f"/fake/path/{x}"
        yield mock


@pytest.fixture
def mock_messagebox():
    """Mock do messagebox."""
    with patch("src.ui.login_dialog.messagebox") as mock:
        yield mock


# ==================== Testes de Inicialização ====================


def test_login_dialog_inicializa_sem_excecao(root, mock_prefs_utils, mock_resource_path):
    """Testa que LoginDialog é criado sem exceção."""
    dialog = LoginDialog(root)
    assert dialog is not None
    assert isinstance(dialog, tk.Toplevel)
    dialog.destroy()


def test_login_dialog_cria_variaveis_controle(root, mock_prefs_utils, mock_resource_path):
    """Testa que LoginDialog cria StringVar e BooleanVar corretamente."""
    dialog = LoginDialog(root)

    assert isinstance(dialog.email_var, tk.StringVar)
    assert isinstance(dialog.pass_var, tk.StringVar)
    assert isinstance(dialog.remember_email_var, tk.BooleanVar)
    assert isinstance(dialog.keep_logged_var, tk.BooleanVar)
    assert dialog.login_success is False

    dialog.destroy()


def test_login_dialog_carrega_preferencias_salvas(root, mock_prefs_utils, mock_resource_path):
    """Testa que LoginDialog carrega email salvo nas preferências."""
    mock_prefs_utils.load_login_prefs.return_value = {
        "email": "saved@test.com",
        "remember_email": True,
    }

    dialog = LoginDialog(root)

    assert dialog.email_var.get() == "saved@test.com"
    assert dialog.remember_email_var.get() is True

    dialog.destroy()


def test_login_dialog_inicializa_sem_preferencias(root, mock_prefs_utils, mock_resource_path):
    """Testa que LoginDialog funciona sem preferências salvas."""
    mock_prefs_utils.load_login_prefs.return_value = {}

    dialog = LoginDialog(root)

    assert dialog.email_var.get() == ""
    assert dialog.remember_email_var.get() is True  # Default

    dialog.destroy()


def test_login_dialog_ignora_excecao_ao_carregar_prefs(root, mock_prefs_utils, mock_resource_path):
    """Testa que LoginDialog não quebra quando load_login_prefs falha."""
    mock_prefs_utils.load_login_prefs.side_effect = RuntimeError("Prefs error")

    dialog = LoginDialog(root)
    assert dialog is not None
    dialog.destroy()


# ==================== Testes de Validação ====================


def test_login_dialog_valida_email_vazio(root, mock_prefs_utils, mock_resource_path, mock_messagebox):
    """Testa que _do_login valida email vazio."""
    dialog = LoginDialog(root)
    dialog.email_var.set("")
    dialog.pass_var.set("senha123")

    dialog._do_login()

    mock_messagebox.showerror.assert_called_once()
    assert "Preencha e-mail e senha" in str(mock_messagebox.showerror.call_args)

    dialog.destroy()


def test_login_dialog_valida_senha_vazia(root, mock_prefs_utils, mock_resource_path, mock_messagebox):
    """Testa que _do_login valida senha vazia."""
    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("")

    dialog._do_login()

    mock_messagebox.showerror.assert_called_once()
    assert "Preencha e-mail e senha" in str(mock_messagebox.showerror.call_args)

    dialog.destroy()


def test_login_dialog_valida_ambos_vazios(root, mock_prefs_utils, mock_resource_path, mock_messagebox):
    """Testa que _do_login valida email e senha vazios."""
    dialog = LoginDialog(root)
    dialog.email_var.set("")
    dialog.pass_var.set("")

    dialog._do_login()

    mock_messagebox.showerror.assert_called_once()

    dialog.destroy()


# ==================== Testes de Login Bem-Sucedido ====================


def test_login_dialog_login_sucesso_marca_flag(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que login bem-sucedido marca login_success = True."""
    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")

    # Mock para evitar destruir antes de assert
    original_destroy = dialog.destroy
    dialog.destroy = Mock()

    dialog._do_login()

    assert dialog.login_success is True
    assert dialog.destroy.called

    original_destroy()


def test_login_dialog_chama_authenticate_user(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que _do_login chama authenticate_user com email e senha."""
    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.destroy = Mock()

    dialog._do_login()

    mock_authenticate_user.assert_called_once_with("user@test.com", "senha123")

    dialog.destroy()


def test_login_dialog_chama_bind_postgrest_apos_sucesso(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que bind_postgrest_auth_if_any é chamado após login sucesso."""
    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.destroy = Mock()

    dialog._do_login()

    mock_bind_postgrest.assert_called_once()

    dialog.destroy()


def test_login_dialog_chama_refresh_user_apos_sucesso(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que refresh_current_user_from_supabase é chamado após login."""
    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.destroy = Mock()

    dialog._do_login()

    mock_refresh_user.assert_called_once()

    dialog.destroy()


def test_login_dialog_chama_healthcheck_apos_sucesso(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que healthcheck é chamado após login bem-sucedido."""
    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.destroy = Mock()

    dialog._do_login()

    mock_healthcheck.assert_called_once()

    dialog.destroy()


def test_login_dialog_salva_login_prefs_quando_remember_true(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que save_login_prefs é chamado quando remember_email=True."""
    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.remember_email_var.set(True)
    dialog.destroy = Mock()

    dialog._do_login()

    mock_prefs_utils.save_login_prefs.assert_called_once_with("user@test.com", True)

    dialog.destroy()


def test_login_dialog_salva_login_prefs_quando_remember_false(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que save_login_prefs é chamado com False quando desmarcado."""
    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.remember_email_var.set(False)
    dialog.destroy = Mock()

    dialog._do_login()

    mock_prefs_utils.save_login_prefs.assert_called_once_with("user@test.com", False)

    dialog.destroy()


def test_login_dialog_salva_auth_session_quando_keep_logged(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que save_auth_session é chamado quando keep_logged=True."""
    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.keep_logged_var.set(True)
    dialog.destroy = Mock()

    dialog._do_login()

    mock_prefs_utils.save_auth_session.assert_called_once_with("at123", "rt123", keep_logged=True)

    dialog.destroy()


def test_login_dialog_limpa_auth_session_quando_keep_logged_false(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que clear_auth_session é chamado quando keep_logged=False."""
    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.keep_logged_var.set(False)
    dialog.destroy = Mock()

    dialog._do_login()

    mock_prefs_utils.clear_auth_session.assert_called_once()

    dialog.destroy()


# ==================== Testes de Falha de Login ====================


def test_login_dialog_login_falha_mostra_erro(
    root, mock_prefs_utils, mock_resource_path, mock_get_supabase, mock_authenticate_user, mock_messagebox
):
    """Testa que login falhado mostra messagebox de erro."""
    mock_authenticate_user.return_value = (False, "Credenciais inválidas")

    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha_errada")

    dialog._do_login()

    mock_messagebox.showerror.assert_called_once()
    assert "Credenciais inválidas" in str(mock_messagebox.showerror.call_args)
    assert dialog.login_success is False

    dialog.destroy()


def test_login_dialog_nao_marca_sucesso_quando_falha(
    root, mock_prefs_utils, mock_resource_path, mock_get_supabase, mock_authenticate_user, mock_messagebox
):
    """Testa que login_success permanece False quando login falha."""
    mock_authenticate_user.return_value = (False, "Erro")

    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")

    dialog._do_login()

    assert dialog.login_success is False

    dialog.destroy()


def test_login_dialog_desabilita_botao_quando_bloqueado(
    root, mock_prefs_utils, mock_resource_path, mock_get_supabase, mock_authenticate_user, mock_messagebox
):
    """Testa que botão é desabilitado quando mensagem contém 'Aguarde Xs'."""
    mock_authenticate_user.return_value = (False, "Muitas tentativas. Aguarde 5s")

    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")

    dialog._do_login()

    # Verifica que botão foi desabilitado
    assert str(dialog.login_btn.cget("state")) == "disabled"

    dialog.destroy()


# ==================== Testes de Token Ausente ====================


def test_login_dialog_mostra_erro_quando_sem_token(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_messagebox,
):
    """Testa que erro é mostrado quando token não é gerado após login."""
    mock_get_access_token.return_value = None  # Sem token

    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")

    dialog._do_login()

    mock_messagebox.showerror.assert_called()
    assert "Login não gerou token" in str(mock_messagebox.showerror.call_args)
    assert dialog.login_success is False

    dialog.destroy()


# ==================== Testes de Exceções ====================


def test_login_dialog_ignora_excecao_refresh_user(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que exceção em refresh_current_user não quebra login."""
    mock_refresh_user.side_effect = RuntimeError("Refresh failed")

    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.destroy = Mock()

    # Não deve lançar exceção
    dialog._do_login()

    assert dialog.login_success is True

    dialog.destroy()


def test_login_dialog_ignora_excecao_healthcheck(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que exceção em healthcheck não quebra login."""
    mock_healthcheck.side_effect = RuntimeError("Health failed")

    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.destroy = Mock()

    dialog._do_login()

    assert dialog.login_success is True

    dialog.destroy()


def test_login_dialog_ignora_excecao_save_login_prefs(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que exceção em save_login_prefs não quebra login."""
    mock_prefs_utils.save_login_prefs.side_effect = RuntimeError("Save failed")

    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.destroy = Mock()

    dialog._do_login()

    assert dialog.login_success is True

    dialog.destroy()


def test_login_dialog_ignora_excecao_save_auth_session(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que exceção em save_auth_session não quebra login."""
    mock_prefs_utils.save_auth_session.side_effect = RuntimeError("Save failed")

    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.keep_logged_var.set(True)
    dialog.destroy = Mock()

    dialog._do_login()

    assert dialog.login_success is True

    dialog.destroy()


# ==================== Testes de Cancelamento ====================


def test_login_dialog_on_exit_destroi_dialogo(root, mock_prefs_utils, mock_resource_path):
    """Testa que _on_exit destrói o diálogo."""
    dialog = LoginDialog(root)
    original_destroy = dialog.destroy
    dialog.destroy = Mock()

    dialog._on_exit()

    assert dialog.destroy.called

    original_destroy()


def test_login_dialog_on_exit_nao_marca_sucesso(root, mock_prefs_utils, mock_resource_path):
    """Testa que _on_exit não marca login_success."""
    dialog = LoginDialog(root)
    dialog.destroy = Mock()

    dialog._on_exit()

    assert dialog.login_success is False

    dialog.destroy()


# ==================== Testes de Bindings ====================


def test_login_dialog_unbind_enter_remove_binding(root, mock_prefs_utils, mock_resource_path):
    """Testa que _unbind_enter remove binding de <Return>."""
    dialog = LoginDialog(root)

    dialog._unbind_enter()

    # Tentar trigger <Return> não deve chamar _do_login
    dialog._do_login = Mock()
    dialog.event_generate("<Return>")
    dialog.update()

    dialog._do_login.assert_not_called()

    dialog.destroy()


def test_login_dialog_enable_btn_reativa_botao(root, mock_prefs_utils, mock_resource_path):
    """Testa que _enable_btn reativa botão após desabilitação."""
    dialog = LoginDialog(root)
    dialog.login_btn.config(state="disabled")

    dialog._enable_btn()

    assert str(dialog.login_btn.cget("state")) == "normal"

    dialog.destroy()


# ==================== Testes de Integração com Componentes Visuais ====================


def test_login_dialog_tem_todos_widgets_principais(root, mock_prefs_utils, mock_resource_path):
    """Testa que LoginDialog tem todos os widgets principais."""
    dialog = LoginDialog(root)

    assert hasattr(dialog, "email_label")
    assert hasattr(dialog, "email_entry")
    assert hasattr(dialog, "pass_label")
    assert hasattr(dialog, "pass_entry")
    assert hasattr(dialog, "remember_email_check")
    assert hasattr(dialog, "keep_logged_check")
    assert hasattr(dialog, "separator_bottom")
    assert hasattr(dialog, "buttons_frame")
    assert hasattr(dialog, "exit_btn")
    assert hasattr(dialog, "login_btn")

    dialog.destroy()


def test_login_dialog_senha_entry_oculta_caracteres(root, mock_prefs_utils, mock_resource_path):
    """Testa que campo de senha oculta caracteres."""
    dialog = LoginDialog(root)

    assert dialog.pass_entry.cget("show") == "•"

    dialog.destroy()


# ==================== Testes de Exceções de Inicialização ====================


def test_login_dialog_ignora_excecao_resource_path_icone(root, mock_prefs_utils):
    """Testa que LoginDialog não quebra quando resource_path falha ao buscar ícone."""
    with patch("src.ui.login_dialog.resource_path") as mock:
        mock.side_effect = RuntimeError("Resource error")

        dialog = LoginDialog(root)
        assert dialog is not None
        dialog.destroy()


def test_login_dialog_ignora_excecao_photoimage_email(root, mock_prefs_utils):
    """Testa que LoginDialog não quebra quando tk.PhotoImage falha ao carregar ícone email."""
    with patch("src.ui.login_dialog.resource_path") as mock_res:
        mock_res.side_effect = lambda x: f"/fake/{x}"
        with patch("src.ui.login_dialog.tk.PhotoImage") as mock_photo:
            mock_photo.side_effect = RuntimeError("Image error")

            dialog = LoginDialog(root)
            assert dialog._icon_email is None
            assert dialog._icon_senha is None
            dialog.destroy()


def test_login_dialog_trata_os_exists_false_para_icone(root, mock_prefs_utils):
    """Testa que LoginDialog lida com ícone não existente."""
    with patch("src.ui.login_dialog.resource_path") as mock_res:
        mock_res.return_value = "/fake/rc.ico"
        with patch("src.ui.login_dialog.os.path.exists") as mock_exists:
            mock_exists.return_value = False

            dialog = LoginDialog(root)
            assert dialog is not None
            dialog.destroy()


def test_login_dialog_trata_iconbitmap_exception(root, mock_prefs_utils):
    """Testa que LoginDialog tenta iconphoto quando iconbitmap falha."""
    with patch("src.ui.login_dialog.resource_path") as mock_res:
        mock_res.return_value = "/fake/rc.ico"
        with patch("src.ui.login_dialog.os.path.exists") as mock_exists:
            mock_exists.return_value = True

            dialog = LoginDialog(root)
            # iconbitmap vai falhar em ambiente de teste, mas não deve quebrar
            assert dialog is not None
            dialog.destroy()


def test_login_dialog_trata_iconphoto_exception(root, mock_prefs_utils):
    """Testa que LoginDialog ignora exceção em iconphoto."""
    with patch("src.ui.login_dialog.resource_path") as mock_res:
        mock_res.return_value = "/fake/rc.ico"
        with patch("src.ui.login_dialog.os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch.object(tk.Toplevel, "iconbitmap") as mock_iconbitmap:
                mock_iconbitmap.side_effect = RuntimeError("Iconbitmap failed")
                with patch("src.ui.login_dialog.tk.PhotoImage") as mock_photo:
                    mock_photo.side_effect = RuntimeError("PhotoImage failed")

                    dialog = LoginDialog(root)
                    assert dialog is not None
                    dialog.destroy()


def test_login_dialog_ignora_excecao_log_info_tempo(root, mock_prefs_utils, mock_resource_path):
    """Testa que LoginDialog ignora exceção ao logar tempo de inicialização."""
    with patch("src.ui.login_dialog.log.info") as mock_log:
        mock_log.side_effect = RuntimeError("Log failed")

        dialog = LoginDialog(root)
        assert dialog is not None
        dialog.destroy()


# ==================== Testes de Branches Complexos ====================


def test_login_dialog_trata_sessao_sem_atributo_session(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que _do_login lida com sess_response sem atributo 'session'."""
    # Simular sessão que não tem atributo 'session' (linha 250)
    mock_client = mock_get_supabase.return_value
    sess_response = MagicMock(spec=[])  # Sem atributo 'session'
    sess_response.access_token = "direct_at"
    sess_response.refresh_token = "direct_rt"
    mock_client.auth.get_session.return_value = sess_response

    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.keep_logged_var.set(True)
    dialog.destroy = Mock()

    dialog._do_login()

    # Deve usar sess_response diretamente
    mock_prefs_utils.save_auth_session.assert_called_once_with("direct_at", "direct_rt", keep_logged=True)

    dialog.destroy()


def test_login_dialog_nao_salva_sessao_sem_tokens(
    root,
    mock_prefs_utils,
    mock_resource_path,
    mock_get_supabase,
    mock_authenticate_user,
    mock_get_access_token,
    mock_bind_postgrest,
    mock_refresh_user,
    mock_healthcheck,
):
    """Testa que _do_login não salva sessão quando tokens estão vazios."""
    mock_client = mock_get_supabase.return_value
    sess_response = MagicMock(session=MagicMock(access_token="", refresh_token=""))
    mock_client.auth.get_session.return_value = sess_response

    dialog = LoginDialog(root)
    dialog.email_var.set("user@test.com")
    dialog.pass_var.set("senha123")
    dialog.keep_logged_var.set(True)
    dialog.destroy = Mock()

    dialog._do_login()

    # Deve chamar clear_auth_session ao invés de save
    mock_prefs_utils.clear_auth_session.assert_called_once()
    mock_prefs_utils.save_auth_session.assert_not_called()

    dialog.destroy()
