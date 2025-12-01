# -*- coding: utf-8 -*-
"""Testes unitários para FEATURE-SENHAS-001, FIX-SENHAS-CLIENTES-004 e FEATURE-SENHAS-002.

Arquivos afetados pelas features:
- src/modules/passwords/views/passwords_screen.py (PasswordDialog e PasswordsScreen)
- src/modules/passwords/controller.py (PasswordsController)
- infra/repositories/passwords_repository.py
- data/supabase_repo.py

Cenários testados:
1. set_client_from_data preenche campos corretamente
2. PasswordsScreen._handle_client_picked abre/atualiza diálogo
3. FEATURE-SENHAS-002: Novo fluxo Nova Senha (pick mode primeiro)
4. Salvar senha usa client_id selecionado
5. Controller e repository aceitam client_id
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch


class TestPasswordDialogClientSelection:
    """Testes para o fluxo de seleção de cliente em PasswordDialog (FIX-004)."""

    def test_set_client_from_data_preenche_campos_com_cnpj(self) -> None:
        """Test: set_client_from_data preenche selected_client_id e display com CNPJ."""
        from src.modules.passwords.views.passwords_screen import PasswordDialog

        # Criar um mock dialog simples sem inicializar Toplevel
        dialog = object.__new__(PasswordDialog)
        dialog.selected_client_id = None
        dialog.selected_client_display = ""
        dialog.client_display_var = MagicMock()

        # Simular seleção de cliente
        client_data = {
            "id": 256,
            "razao_social": "ALFARFARMA - PRODUTOS FARMACEUTICOS LTDA",
            "cnpj": "12.345.678/0001-90",
        }

        dialog.set_client_from_data(client_data)

        # Verificar que fields foram preenchidos
        assert dialog.selected_client_id == "256"
        assert "ID 256" in dialog.selected_client_display
        assert "ALFARFARMA" in dialog.selected_client_display
        assert "12.345.678/0001-90" in dialog.selected_client_display
        dialog.client_display_var.set.assert_called_once_with(dialog.selected_client_display)

    def test_set_client_from_data_sem_cnpj(self) -> None:
        """Test: set_client_from_data funciona sem CNPJ."""
        from src.modules.passwords.views.passwords_screen import PasswordDialog

        # Criar mock dialog
        dialog = object.__new__(PasswordDialog)
        dialog.selected_client_id = None
        dialog.selected_client_display = ""
        dialog.client_display_var = MagicMock()

        client_data = {
            "id": 100,
            "razao_social": "EMPRESA SEM CNPJ",
            "cnpj": "",
        }

        dialog.set_client_from_data(client_data)

        assert dialog.selected_client_id == "100"
        assert "ID 100" in dialog.selected_client_display
        assert "EMPRESA SEM CNPJ" in dialog.selected_client_display
        # Não deve incluir parênteses vazios quando CNPJ vazio
        assert "()" not in dialog.selected_client_display

    def test_set_client_from_data_desabilita_botao_selecionar(self) -> None:
        """Test: set_client_from_data desabilita botão Selecionar (FEATURE-SENHAS-002)."""
        from src.modules.passwords.views.passwords_screen import PasswordDialog

        # Criar mock dialog
        dialog = object.__new__(PasswordDialog)
        dialog.selected_client_id = None
        dialog.selected_client_display = ""
        dialog.client_display_var = MagicMock()

        # Mock do botão Selecionar
        mock_button = MagicMock()
        dialog.select_client_button = mock_button

        client_data = {
            "id": 256,
            "razao_social": "ALFARFARMA",
            "cnpj": "12.345.678/0001-90",
        }

        dialog.set_client_from_data(client_data)

        # Verificar que botão foi desabilitado
        mock_button.configure.assert_called_once_with(state="disabled")


class TestFeatureSenhas002NewPasswordFlow:
    """Testes para FEATURE-SENHAS-002: Novo fluxo Nova Senha com pick mode primeiro."""

    def test_on_new_password_clicked_abre_pick_mode(self) -> None:
        """Test: Clicar em Nova Senha sem cliente selecionado abre pick mode."""
        from src.modules.passwords.views.passwords_screen import PasswordsScreen

        screen = object.__new__(PasswordsScreen)
        screen._get_main_app = MagicMock(return_value=MagicMock())
        screen._handle_client_picked_for_new_password = MagicMock()
        # FIX-SENHAS-002: Agora verifica se há cliente selecionado primeiro
        screen._get_selected_client_id = MagicMock(return_value=None)

        with patch("src.modules.main_window.controller.navigate_to") as mock_navigate:
            screen._on_new_password_clicked()

            # Verificar que navigate_to foi chamado com clients_picker
            mock_navigate.assert_called_once()
            call_args = mock_navigate.call_args
            assert call_args[0][1] == "clients_picker"
            assert "on_pick" in call_args[1]
            assert call_args[1]["on_pick"] == screen._handle_client_picked_for_new_password

    def test_on_new_password_clicked_sem_app_mostra_erro(self) -> None:
        """Test: _on_new_password_clicked sem app mostra erro."""
        from src.modules.passwords.views.passwords_screen import PasswordsScreen

        screen = object.__new__(PasswordsScreen)
        screen._get_main_app = MagicMock(return_value=None)
        # FIX-SENHAS-002: Agora verifica se há cliente selecionado primeiro
        screen._get_selected_client_id = MagicMock(return_value=None)

        with patch("tkinter.messagebox.showerror") as mock_msg:
            screen._on_new_password_clicked()
            mock_msg.assert_called_once()

    def test_handle_client_picked_for_new_password_abre_dialog(self) -> None:
        """Test: _handle_client_picked_for_new_password abre diálogo com cliente preenchido."""
        from src.modules.passwords.views.passwords_screen import PasswordsScreen

        screen = object.__new__(PasswordsScreen)
        screen._open_new_password_dialog = MagicMock()

        client_data = {"id": 256, "razao_social": "ALFARFARMA", "cnpj": "12.345.678/0001-90"}

        screen._handle_client_picked_for_new_password(client_data)

        # Verificar que _open_new_password_dialog foi chamado com client_data
        screen._open_new_password_dialog.assert_called_once_with(client_data=client_data)

    def test_fluxo_completo_nova_senha_feature002(self) -> None:
        """Test: Fluxo completo Nova Senha sem cliente selecionado (FEATURE-SENHAS-002)."""
        from src.modules.passwords.views.passwords_screen import PasswordsScreen

        screen = object.__new__(PasswordsScreen)
        screen.org_id = "org-123"
        screen.user_id = "user-456"
        screen.clients = []
        screen.controller = MagicMock()
        screen._refresh_data = MagicMock()
        screen._password_dialog = None
        # FIX-SENHAS-002: Agora verifica se há cliente selecionado primeiro
        screen._get_selected_client_id = MagicMock(return_value=None)

        # Mock app
        mock_app = MagicMock()
        screen._get_main_app = MagicMock(return_value=mock_app)

        client_data = {"id": 256, "razao_social": "ALFARFARMA", "cnpj": "12.345.678/0001-90"}

        # Simular fluxo:
        # 1. Usuário clica Nova Senha
        with patch("src.modules.main_window.controller.navigate_to") as mock_navigate:
            screen._on_new_password_clicked()

            # Verificar que pick mode foi iniciado
            assert mock_navigate.called
            on_pick_callback = mock_navigate.call_args[1]["on_pick"]

        # 2. Usuário seleciona cliente no pick mode
        with patch("src.modules.passwords.views.passwords_screen.PasswordDialog") as mock_dialog_class:
            mock_dialog_instance = MagicMock()
            mock_dialog_class.return_value = mock_dialog_instance

            # Callback é chamado
            on_pick_callback(client_data)

            # Verificar que diálogo foi criado com client_id e client_display
            assert mock_dialog_class.called
            call_kwargs = mock_dialog_class.call_args[1]
            assert call_kwargs.get("client_id") == "256"
            assert "ALFARFARMA" in call_kwargs.get("client_display", "")


class TestPasswordsScreenOrchestration:
    """Testes para orquestração de pick mode no PasswordsScreen (FIX-004)."""

    def test_handle_client_picked_abre_dialog_se_nao_existir(self) -> None:
        """Test: _handle_client_picked abre novo diálogo se não houver um ativo."""
        from src.modules.passwords.views.passwords_screen import PasswordsScreen

        screen = object.__new__(PasswordsScreen)
        screen._password_dialog = None
        screen._last_selected_client_data = None
        screen.org_id = "org-123"
        screen.user_id = "user-456"
        screen.clients = []
        screen.controller = MagicMock()

        # Mock _open_new_password_dialog
        screen._open_new_password_dialog = MagicMock()

        client_data = {"id": 256, "razao_social": "ALFARFARMA", "cnpj": "12.345.678/0001-90"}

        screen._handle_client_picked(client_data)

        # Deve ter salvo os dados
        assert screen._last_selected_client_data == client_data
        # Deve ter aberto novo diálogo com os dados
        screen._open_new_password_dialog.assert_called_once_with(client_data=client_data)

    def test_handle_client_picked_atualiza_dialog_existente(self) -> None:
        """Test: _handle_client_picked atualiza diálogo existente se visível."""
        from src.modules.passwords.views.passwords_screen import PasswordsScreen

        screen = object.__new__(PasswordsScreen)
        screen._last_selected_client_data = None
        screen._open_new_password_dialog = MagicMock()

        # Mock dialog existente e visível
        mock_dialog = MagicMock()
        mock_dialog.is_visible.return_value = True
        mock_dialog.set_client_from_data = MagicMock()
        screen._password_dialog = mock_dialog

        client_data = {"id": 256, "razao_social": "ALFARFARMA", "cnpj": "12.345.678/0001-90"}

        screen._handle_client_picked(client_data)

        # Deve ter salvo os dados
        assert screen._last_selected_client_data == client_data
        # Deve ter atualizado dialog existente
        mock_dialog.set_client_from_data.assert_called_once_with(client_data)
        # NÃO deve ter criado novo
        screen._open_new_password_dialog.assert_not_called()

    def test_handle_client_picked_recria_dialog_se_fechado(self) -> None:
        """Test: _handle_client_picked recria diálogo se foi fechado."""
        from src.modules.passwords.views.passwords_screen import PasswordsScreen

        screen = object.__new__(PasswordsScreen)
        screen._last_selected_client_data = None
        screen._open_new_password_dialog = MagicMock()

        # Mock dialog existente mas NÃO visível (foi fechado)
        mock_dialog = MagicMock()
        mock_dialog.is_visible.return_value = False
        screen._password_dialog = mock_dialog

        client_data = {"id": 256, "razao_social": "ALFARFARMA", "cnpj": "12.345.678/0001-90"}

        screen._handle_client_picked(client_data)

        # Deve ter salvo os dados
        assert screen._last_selected_client_data == client_data
        # Deve ter recriado dialog
        screen._open_new_password_dialog.assert_called_once_with(client_data=client_data)


class TestPasswordsControllerClientId:
    """Testes para verificar que PasswordsController aceita client_id."""

    def test_create_password_aceita_client_id(self) -> None:
        """Test: create_password aceita e passa client_id para o service."""
        from src.modules.passwords.controller import PasswordsController

        controller = PasswordsController()

        with patch("src.modules.passwords.controller.passwords_service") as mock_service:
            controller.create_password(
                org_id="org-123",
                client_id="256",
                client_name="ALFARFARMA",
                service="SIFAP",
                username="user",
                password="pass",
                notes="nota",
                user_id="user-456",
            )

            # Verificar que service foi chamado com client_id
            mock_service.create_password.assert_called_once_with(
                "org-123",
                "ALFARFARMA",
                "SIFAP",
                "user",
                "pass",
                "nota",
                "user-456",
                "256",
            )

    def test_update_password_aceita_client_id(self) -> None:
        """Test: update_password aceita e passa client_id para o service."""
        from src.modules.passwords.controller import PasswordsController

        controller = PasswordsController()

        with patch("src.modules.passwords.controller.passwords_service") as mock_service:
            controller.update_password(
                password_id="pwd-789",
                client_id="256",
                client_name="ALFARFARMA",
                service="SIFAP",
                username="user",
                password_plain="newpass",
                notes="nova nota",
            )

            # Verificar que service foi chamado com client_id
            mock_service.update_password_by_id.assert_called_once_with(
                "pwd-789",
                client_id="256",
                client_name="ALFARFARMA",
                service="SIFAP",
                username="user",
                password_plain="newpass",
                notes="nova nota",
            )


class TestPasswordsRepositoryClientId:
    """Testes para verificar que passwords_repository aceita client_id."""

    @patch("data.supabase_repo.add_password")
    def test_create_password_com_client_id(self, mock_add: Mock) -> None:
        """Test: create_password passa client_id para add_password."""
        from infra.repositories.passwords_repository import create_password

        create_password(
            org_id="org-123",
            client_name="ALFARFARMA",
            service="SIFAP",
            username="user",
            password_plain="pass",
            notes="nota",
            created_by="user-456",
            client_id="256",
        )

        mock_add.assert_called_once_with(
            "org-123",
            "ALFARFARMA",
            "SIFAP",
            "user",
            "pass",
            "nota",
            "user-456",
            "256",
        )

    @patch("data.supabase_repo.update_password")
    def test_update_password_com_client_id(self, mock_update: Mock) -> None:
        """Test: update_password_by_id passa client_id para update_password."""
        from infra.repositories.passwords_repository import update_password_by_id

        update_password_by_id(
            password_id="pwd-789",
            client_id="256",
            client_name="ALFARFARMA",
            service="SIFAP",
            username="user",
            password_plain="newpass",
            notes="nova nota",
        )

        mock_update.assert_called_once_with(
            "pwd-789",
            "ALFARFARMA",
            "SIFAP",
            "user",
            "newpass",
            "nova nota",
            "256",
        )


class TestSupabaseRepoClientId:
    """Testes para verificar assinatura de supabase_repo com client_id."""

    def test_add_password_aceita_client_id_param(self) -> None:
        """Test: add_password aceita client_id como parâmetro opcional."""
        import inspect
        from data.supabase_repo import add_password

        sig = inspect.signature(add_password)
        params = list(sig.parameters.keys())

        # Verificar que client_id está na assinatura
        assert "client_id" in params

        # Verificar que é opcional
        client_id_param = sig.parameters["client_id"]
        assert client_id_param.default is not inspect.Parameter.empty

    def test_update_password_aceita_client_id_param(self) -> None:
        """Test: update_password aceita client_id como parâmetro opcional."""
        import inspect
        from data.supabase_repo import update_password

        sig = inspect.signature(update_password)
        params = list(sig.parameters.keys())

        # Verificar que client_id está na assinatura
        assert "client_id" in params

        # Verificar que é opcional
        client_id_param = sig.parameters["client_id"]
        assert client_id_param.default is not inspect.Parameter.empty
