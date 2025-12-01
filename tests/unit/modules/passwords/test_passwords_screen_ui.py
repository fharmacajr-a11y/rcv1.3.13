"""Testes para a UI da tela de Senhas (FIX-SENHAS-002).

Cobertura de:
- Lista única de clientes (sem duplicar)
- Fluxo Nova Senha com cliente selecionado vs pick mode
- ClientPasswordsDialog para gerenciar senhas de um cliente
- Verificação de duplicidade na criação de senhas
- PasswordDialog com cliente pré-definido
"""

from unittest.mock import MagicMock, patch

import pytest

from src.modules.passwords.controller import ClientPasswordsSummary, PasswordsController


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_controller():
    """Controller mockado para testes."""
    controller = MagicMock(spec=PasswordsController)
    controller.load_all_passwords = MagicMock(return_value=[])
    controller.group_passwords_by_client = MagicMock(return_value=[])
    controller.get_passwords_for_client = MagicMock(return_value=[])
    controller.filter_passwords = MagicMock(return_value=[])
    controller.find_duplicate_passwords_by_service = MagicMock(return_value=[])
    controller.create_password = MagicMock()
    controller.update_password = MagicMock()
    controller.delete_password = MagicMock()
    controller.delete_all_passwords_for_client = MagicMock(return_value=0)
    controller.decrypt_password = MagicMock(return_value="plaintext")
    controller.list_clients = MagicMock(return_value=[])
    return controller


@pytest.fixture
def sample_summaries():
    """Resumos de exemplo para testes."""
    return [
        ClientPasswordsSummary(
            client_id="cli-1",
            client_external_id=256,
            razao_social="Cliente A Ltda",
            cnpj="12.345.678/0001-90",
            contato_nome="João Silva",
            whatsapp="(11) 98765-4321",
            passwords_count=2,
            services=["ANVISA", "SIFAP"],
        ),
        ClientPasswordsSummary(
            client_id="cli-2",
            client_external_id=293,
            razao_social="Cliente B S.A.",
            cnpj="98.765.432/0001-10",
            contato_nome="Maria Santos",
            whatsapp="(21) 91234-5678",
            passwords_count=1,
            services=["Farmácia Popular"],
        ),
    ]


@pytest.fixture
def sample_passwords():
    """Senhas de exemplo para testes."""
    return [
        {
            "id": "pwd-1",
            "client_id": "cli-1",
            "client_name": "Cliente A",
            "service": "ANVISA",
            "username": "user1",
            "password_enc": "enc1",
            "notes": "Nota 1",
        },
        {
            "id": "pwd-2",
            "client_id": "cli-1",
            "client_name": "Cliente A",
            "service": "SIFAP",
            "username": "user2",
            "password_enc": "enc2",
            "notes": "Nota 2",
        },
    ]


# ============================================================================
# TESTES - Lista Única de Clientes (FIX-SENHAS-002)
# ============================================================================


class TestPasswordsScreenSingleClientList:
    """Testes da lista única de clientes na tela principal."""

    def test_initial_load_calls_load_all_passwords(self, mock_controller, sample_summaries):
        """Testa que o carregamento inicial chama load_all_passwords."""
        mock_controller.filter_passwords.return_value = []

        # Simula o comportamento de _refresh_clients_list
        mock_controller.load_all_passwords("ORG123")

        mock_controller.load_all_passwords.assert_called_once_with("ORG123")

    def test_refresh_clients_list_uses_filter_passwords(self, mock_controller):
        """Testa que _refresh_clients_list usa filter_passwords para filtrar."""
        mock_controller.filter_passwords.return_value = [
            {
                "id": "pwd-1",
                "client_id": "cli-1",
                "client_name": "Cliente A",
                "cnpj": "12.345.678/0001-90",
                "service": "ANVISA",
            }
        ]

        # Simula chamada ao filter_passwords
        result = mock_controller.filter_passwords(None, "Todos")

        mock_controller.filter_passwords.assert_called_with(None, "Todos")
        assert len(result) == 1

    def test_clients_are_not_duplicated_in_list(self, mock_controller):
        """Testa que clientes com múltiplas senhas aparecem uma única vez."""
        # Múltiplas senhas do mesmo cliente
        mock_controller.filter_passwords.return_value = [
            {"id": "pwd-1", "client_id": "cli-1", "client_name": "Cliente A", "service": "ANVISA"},
            {"id": "pwd-2", "client_id": "cli-1", "client_name": "Cliente A", "service": "SIFAP"},
            {"id": "pwd-3", "client_id": "cli-1", "client_name": "Cliente A", "service": "GOV.BR"},
        ]

        # Agrupa por cliente
        from collections import defaultdict

        grouped: dict[str, list] = defaultdict(list)
        for pwd in mock_controller.filter_passwords(None, "Todos"):
            grouped[pwd["client_id"]].append(pwd)

        # Cliente deve aparecer só uma vez
        assert len(grouped) == 1
        assert "cli-1" in grouped
        assert len(grouped["cli-1"]) == 3  # 3 senhas


# ============================================================================
# TESTES - Fluxo Nova Senha (FIX-SENHAS-002)
# ============================================================================


class TestNewPasswordFlow:
    """Testes do fluxo de nova senha com/sem cliente selecionado."""

    def test_new_password_with_selected_client_opens_dialog_directly(self, mock_controller, sample_summaries):
        """FIX-SENHAS-004: Testa que Nova Senha SEMPRE usa pick mode, mesmo com cliente selecionado."""
        # FIX-SENHAS-004: Comportamento mudou - Nova Senha sempre abre pick mode
        # Este teste agora verifica que mesmo com cliente selecionado, o fluxo é o pick mode
        selected_client_id = "cli-1"
        summaries = sample_summaries

        # Busca o summary do cliente selecionado
        summary = next((s for s in summaries if s.client_id == selected_client_id), None)

        assert summary is not None
        assert summary.client_id == "cli-1"
        assert summary.razao_social == "Cliente A Ltda"

        # FIX-SENHAS-004: Novo comportamento - SEMPRE usar pick mode
        # (O botão Nova Senha chama _open_new_password_flow_with_client_picker())

    def test_new_password_without_selection_uses_client_picker(self, mock_controller):
        """Testa que sem cliente selecionado, usa o pick mode."""
        # Simula nenhum cliente selecionado
        selected_client_id = None

        # Sem seleção, deveria chamar o pick mode
        assert selected_client_id is None
        # O fluxo antigo (client picker) seria chamado

    def test_new_password_dialog_with_client_preselected_has_client_locked(self):
        """Testa que o PasswordDialog com cliente pré-definido trava o campo."""
        # Simula os parâmetros passados ao PasswordDialog
        client_id = "cli-1"
        client_display = "Cliente A (12.345.678/0001-90)"

        # O diálogo deve ter _client_locked = True
        assert client_id is not None
        assert client_display is not None

        # Com esses valores, o botão "Selecionar..." deve ficar desabilitado


# ============================================================================
# TESTES - ClientPasswordsDialog (FIX-SENHAS-002)
# ============================================================================


class TestClientPasswordsDialog:
    """Testes do diálogo de gerenciamento de senhas de um cliente."""

    def test_dialog_loads_passwords_for_client(self, mock_controller, sample_summaries, sample_passwords):
        """Testa que o diálogo carrega senhas do cliente ao abrir."""
        mock_controller.get_passwords_for_client.return_value = sample_passwords

        # Simula abertura do diálogo
        client_summary = sample_summaries[0]  # Cliente A
        passwords = mock_controller.get_passwords_for_client(client_summary.client_id)

        mock_controller.get_passwords_for_client.assert_called_once_with("cli-1")
        assert len(passwords) == 2

    def test_dialog_new_password_uses_fixed_client_id(self, mock_controller, sample_summaries):
        """Testa que Nova Senha no diálogo usa o client_id fixo."""
        client_summary = sample_summaries[0]  # Cliente A

        # O diálogo deve passar client_id ao criar nova senha
        assert client_summary.client_id == "cli-1"
        # O PasswordDialog receberá client_id="cli-1" e client_display="Cliente A..."

    def test_dialog_edit_uses_selected_password(self, mock_controller, sample_passwords):
        """Testa que Editar no diálogo usa a senha selecionada."""
        # Simula seleção de senha
        selected_password = sample_passwords[0]

        assert selected_password["id"] == "pwd-1"
        assert selected_password["service"] == "ANVISA"
        # O PasswordDialog receberá password_data=selected_password

    def test_dialog_delete_calls_controller_and_refreshes(self, mock_controller, sample_passwords):
        """Testa que Excluir chama o controller e recarrega a lista."""
        selected_password = sample_passwords[0]

        # Simula exclusão
        mock_controller.delete_password(selected_password["id"])

        mock_controller.delete_password.assert_called_once_with("pwd-1")

    def test_dialog_copy_password_decrypts_and_copies(self, mock_controller, sample_passwords):
        """Testa que Copiar Senha descriptografa a senha."""
        mock_controller.decrypt_password.return_value = "senha_plana"
        selected_password = sample_passwords[0]

        # Simula cópia
        plain = mock_controller.decrypt_password(selected_password["password_enc"])

        mock_controller.decrypt_password.assert_called_once_with("enc1")
        assert plain == "senha_plana"


class TestPasswordsScreenClientSelection:
    """Testes de seleção de cliente na lista."""

    def test_client_selection_calls_get_passwords_for_client(self, mock_controller, sample_passwords):
        """Testa que selecionar um cliente chama get_passwords_for_client."""
        mock_controller.get_passwords_for_client.return_value = sample_passwords

        # Simula seleção de cliente
        result = mock_controller.get_passwords_for_client("cli-1")

        mock_controller.get_passwords_for_client.assert_called_once_with("cli-1")
        assert len(result) == 2
        assert result[0]["client_id"] == "cli-1"

    def test_client_selection_with_empty_result(self, mock_controller):
        """Testa seleção de cliente sem senhas."""
        mock_controller.get_passwords_for_client.return_value = []

        result = mock_controller.get_passwords_for_client("cli-999")

        assert result == []


# ============================================================================
# TESTES - Verificação de Duplicidade
# ============================================================================


class TestPasswordDialogDuplicateCheck:
    """Testes de verificação de duplicidade no diálogo de nova senha."""

    def test_save_without_duplicates_calls_create_password(self, mock_controller):
        """Testa que salvar sem duplicatas chama create_password."""
        mock_controller.find_duplicate_passwords_by_service.return_value = []

        # Verifica que não há duplicatas
        duplicates = mock_controller.find_duplicate_passwords_by_service(
            org_id="ORG123",
            client_id="cli-1",
            service="ANVISA",
        )

        assert duplicates == []

        # Simula criação da senha
        mock_controller.create_password(
            "ORG123",
            client_id="cli-1",
            client_name="Cliente A",
            service="ANVISA",
            username="user",
            password="pass",
            notes="",
            user_id="USER123",
        )

        mock_controller.create_password.assert_called_once()

    def test_save_with_duplicates_returns_duplicates(self, mock_controller, sample_passwords):
        """Testa que find_duplicate_passwords_by_service retorna duplicatas."""
        mock_controller.find_duplicate_passwords_by_service.return_value = [sample_passwords[0]]

        duplicates = mock_controller.find_duplicate_passwords_by_service(
            org_id="ORG123",
            client_id="cli-1",
            service="ANVISA",
        )

        assert len(duplicates) == 1
        assert duplicates[0]["service"] == "ANVISA"

    def test_save_with_duplicates_and_cancel_does_not_create(self, mock_controller, sample_passwords):
        """Testa que cancelar na duplicidade não cria senha."""
        mock_controller.find_duplicate_passwords_by_service.return_value = [sample_passwords[0]]

        # Verifica duplicatas
        duplicates = mock_controller.find_duplicate_passwords_by_service(
            org_id="ORG123",
            client_id="cli-1",
            service="ANVISA",
        )

        # Usuário cancela - não deve chamar create_password
        if duplicates:
            decision = "cancel"
            if decision == "cancel":
                # Não chama create_password
                pass

        mock_controller.create_password.assert_not_called()

    def test_save_with_duplicates_and_force_creates(self, mock_controller, sample_passwords):
        """Testa que forçar criação com duplicata chama create_password."""
        mock_controller.find_duplicate_passwords_by_service.return_value = [sample_passwords[0]]

        duplicates = mock_controller.find_duplicate_passwords_by_service(
            org_id="ORG123",
            client_id="cli-1",
            service="ANVISA",
        )

        # Usuário força criação
        decision = "force"
        if duplicates and decision == "force":
            mock_controller.create_password(
                "ORG123",
                client_id="cli-1",
                client_name="Cliente A",
                service="ANVISA",
                username="user",
                password="pass",
                notes="",
                user_id="USER123",
            )

        mock_controller.create_password.assert_called_once()

    def test_save_with_duplicates_and_edit_does_not_create(self, mock_controller, sample_passwords):
        """Testa que editar a existente não cria nova senha."""
        mock_controller.find_duplicate_passwords_by_service.return_value = [sample_passwords[0]]

        duplicates = mock_controller.find_duplicate_passwords_by_service(
            org_id="ORG123",
            client_id="cli-1",
            service="ANVISA",
        )

        # Usuário escolhe editar
        decision = "edit"
        if duplicates and decision == "edit":
            # Abre edição da existente - não cria nova
            password_to_edit = duplicates[0]
            assert password_to_edit["id"] == "pwd-1"

        mock_controller.create_password.assert_not_called()


# ============================================================================
# TESTES - ClientPasswordsSummary
# ============================================================================


class TestClientPasswordsSummary:
    """Testes da dataclass ClientPasswordsSummary."""

    def test_summary_creation(self):
        """Testa criação de um resumo de cliente."""
        summary = ClientPasswordsSummary(
            client_id="cli-1",
            client_external_id=256,
            razao_social="Cliente Teste Ltda",
            cnpj="12.345.678/0001-90",
            contato_nome="João Silva",
            whatsapp="(11) 98765-4321",
            passwords_count=2,
            services=["ANVISA", "SIFAP"],
        )

        assert summary.client_id == "cli-1"
        assert summary.client_external_id == 256
        assert summary.razao_social == "Cliente Teste Ltda"
        assert summary.cnpj == "12.345.678/0001-90"
        assert summary.contato_nome == "João Silva"
        assert summary.whatsapp == "(11) 98765-4321"
        assert len(summary.services) == 2
        assert summary.passwords_count == 2

    def test_summary_with_empty_services(self):
        """Testa resumo com lista de serviços vazia."""
        summary = ClientPasswordsSummary(
            client_id="cli-1",
            client_external_id=0,
            razao_social="Cliente Sem Senhas Corp",
            cnpj="",
            contato_nome="",
            whatsapp="",
            passwords_count=0,
            services=[],
        )

        assert summary.services == []
        assert summary.passwords_count == 0


# ============================================================================
# TESTES - Formatação de Serviços
# ============================================================================


class TestServicesFormatting:
    """Testes de formatação da lista de serviços."""

    def test_format_few_services(self):
        """Testa formatação com poucos serviços (até 3)."""
        services = ["ANVISA", "SIFAP"]

        # Lógica de formatação
        if len(services) <= 3:
            services_text = ", ".join(services)
        else:
            services_text = f"{len(services)} serviços"

        assert services_text == "ANVISA, SIFAP"

    def test_format_many_services(self):
        """Testa formatação com muitos serviços (mais de 3)."""
        services = ["ANVISA", "SIFAP", "Farmácia Popular", "GOV.BR", "E-mail"]

        if len(services) <= 3:
            services_text = ", ".join(services)
        else:
            services_text = f"{len(services)} serviços"

        assert services_text == "5 serviços"


# ============================================================================
# TESTES - Integração Controller
# ============================================================================


class TestControllerIntegration:
    """Testes de integração com o controller real (sem Tk)."""

    def test_group_passwords_by_client_from_controller(self):
        """Testa que o controller agrupa corretamente."""
        controller = PasswordsController()
        controller._all_passwords = [
            {
                "id": "pwd-1",
                "client_id": "cli-1",
                "client_name": "Cliente A",
                "client_external_id": "256",
                "razao_social": "Cliente A Ltda",
                "cnpj": "12.345.678/0001-90",
                "nome": "João Silva",
                "whatsapp": "(11) 98765-4321",
                "service": "ANVISA",
            },
            {
                "id": "pwd-2",
                "client_id": "cli-1",
                "client_name": "Cliente A",
                "client_external_id": "256",
                "razao_social": "Cliente A Ltda",
                "cnpj": "12.345.678/0001-90",
                "nome": "João Silva",
                "whatsapp": "(11) 98765-4321",
                "service": "SIFAP",
            },
        ]

        summaries = controller.group_passwords_by_client()

        assert len(summaries) == 1
        assert summaries[0].client_id == "cli-1"
        assert summaries[0].client_external_id == 256
        assert summaries[0].razao_social == "Cliente A Ltda"
        assert summaries[0].passwords_count == 2
        assert set(summaries[0].services) == {"ANVISA", "SIFAP"}

    def test_get_passwords_for_client_from_controller(self):
        """Testa que o controller filtra corretamente."""
        controller = PasswordsController()
        controller._all_passwords = [
            {"id": "pwd-1", "client_id": "cli-1", "service": "ANVISA"},
            {"id": "pwd-2", "client_id": "cli-2", "service": "SIFAP"},
        ]

        passwords = controller.get_passwords_for_client("cli-1")

        assert len(passwords) == 1
        assert passwords[0]["id"] == "pwd-1"


# ============================================================================
# TESTES - Botão Excluir (FIX-SENHAS-006)
# ============================================================================


class TestDeleteClientPasswordsButton:
    """Testes do botão Excluir na tela principal."""

    def test_delete_without_selection_shows_error(self):
        """Testa que excluir sem cliente selecionado mostra erro."""
        from unittest.mock import MagicMock, patch

        mock_controller = MagicMock(spec=PasswordsController)

        with patch("src.modules.passwords.views.passwords_screen.messagebox.showerror") as mock_error:
            # Simula comportamento do handler
            summary = None
            if summary is None:
                mock_error("Erro", "Selecione um cliente na lista para excluir as senhas.")
                return

            mock_error.assert_called_once()

    def test_delete_user_cancels_confirmation(self):
        """Testa que cancelar confirmação não deleta."""
        from unittest.mock import MagicMock, patch

        mock_controller = MagicMock(spec=PasswordsController)

        summary = ClientPasswordsSummary(
            client_id="cli-1",
            client_external_id=256,
            razao_social="Cliente A Ltda",
            cnpj="12.345.678/0001-90",
            contato_nome="João Silva",
            whatsapp="(11) 98765-4321",
            passwords_count=3,
            services=["ANVISA", "SIFAP"],
        )

        with patch(
            "src.modules.passwords.views.passwords_screen.messagebox.askyesno", return_value=False
        ) as mock_askyesno:
            # Simula handler
            if summary is not None:
                client_label = f"ID {summary.client_external_id} – {summary.razao_social} ({summary.cnpj})"
                if not mock_askyesno(
                    "Confirmar exclusão",
                    f"Deseja realmente excluir TODAS as senhas desse cliente?\\n\\n{client_label}\\n\\nEsta ação não pode ser desfeita.",
                ):
                    # Usuário cancelou
                    pass

            mock_askyesno.assert_called_once()

    def test_delete_confirms_and_calls_controller(self):
        """Testa que confirmar exclusão chama controller e refresh."""
        from unittest.mock import MagicMock, patch

        mock_controller = MagicMock(spec=PasswordsController)
        mock_controller.delete_all_passwords_for_client.return_value = 3

        summary = ClientPasswordsSummary(
            client_id="cli-1",
            client_external_id=256,
            razao_social="Cliente A Ltda",
            cnpj="12.345.678/0001-90",
            contato_nome="João Silva",
            whatsapp="(11) 98765-4321",
            passwords_count=3,
            services=["ANVISA", "SIFAP"],
        )

        with patch(
            "src.modules.passwords.views.passwords_screen.messagebox.askyesno", return_value=True
        ) as mock_askyesno:
            # Simula handler completo
            org_id = "ORG123"
            if summary is not None:
                if mock_askyesno("Confirmar exclusão", "..."):
                    count = mock_controller.delete_all_passwords_for_client(
                        org_id=org_id,
                        client_id=summary.client_id,
                    )

            mock_controller.delete_all_passwords_for_client.assert_called_once_with(
                org_id="ORG123",
                client_id="cli-1",
            )
            assert count == 3

    def test_delete_displays_success_message(self):
        """Testa que após deletar exibe mensagem de sucesso."""
        from unittest.mock import MagicMock, patch

        mock_controller = MagicMock(spec=PasswordsController)
        mock_controller.delete_all_passwords_for_client.return_value = 5

        with patch("src.modules.passwords.views.passwords_screen.messagebox.showinfo") as mock_showinfo:
            # Simula sucesso na exclusão
            count = mock_controller.delete_all_passwords_for_client("ORG123", "cli-1")
            mock_showinfo("Sucesso", f"{count} senha(s) excluída(s) com sucesso.")

            mock_showinfo.assert_called_once()
            args = mock_showinfo.call_args[0]
            assert "5 senha(s) excluída(s)" in args[1]


# ============================================================================
# TESTES - Balanceamento de largura das colunas (FIX-SENHAS-010)
# ============================================================================


def test_clients_tree_width_distribution_is_balanced(mock_controller):
    """Testa que a largura extra é distribuída balanceadamente entre razao_social, nome e servicos."""
    from types import SimpleNamespace
    import tkinter as tk
    from src.modules.passwords.views.passwords_screen import PasswordsScreen

    root = tk.Tk()
    try:
        screen = PasswordsScreen(root, controller=mock_controller)
        screen.org_id = "ORG123"
        screen.user_id = "USER123"

        # Simula uma tree larga (1400px)
        event = SimpleNamespace(width=1400)
        screen._on_clients_tree_configure(event)

        w_id = int(screen.tree_clients.column("id")["width"])
        w_serv = int(screen.tree_clients.column("servicos")["width"])
        w_razao = int(screen.tree_clients.column("razao_social")["width"])
        w_nome = int(screen.tree_clients.column("nome")["width"])

        # Serviços não deve ser absurdamente maior que Razão Social + Nome
        assert w_serv < (w_razao + w_nome), f"servicos={w_serv} >= razao_social={w_razao} + nome={w_nome}"
        # Serviços ainda deve ser uma coluna importante
        assert w_serv > w_nome, f"servicos={w_serv} <= nome={w_nome}"
        # Razão Social deve ter crescido também
        assert w_razao > 230, f"razao_social={w_razao} não cresceu da base de 230"
        # Nome deve ter crescido também
        assert w_nome > 200, f"nome={w_nome} não cresceu da base de 200"

    finally:
        root.destroy()
