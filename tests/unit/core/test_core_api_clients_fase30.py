"""
TEST-001 Fase 30 - Testes para src/core/api/api_clients.py

Objetivo:
- Aumentar cobertura de src/core/api/api_clients.py de 0% para 70-85%+
- Cobrir todas as funções públicas (switch_theme, get_current_theme, upload_folder,
  create_client, update_client, delete_client, search_clients)
- Testar cenários de sucesso e falha
- Mockar todas as dependências externas (temas, serviços, search)

Meta: 70-85%+ de cobertura
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, Mock, patch


from src.core.api import api_clients
from src.core.models import Cliente


# ============================================================================
# TestSwitchTheme
# ============================================================================


class TestSwitchTheme:
    """Testes para switch_theme()"""

    def test_switch_theme_success(self) -> None:
        """switch_theme() deve aplicar tema com sucesso"""
        mock_root = Mock()
        mock_apply = Mock()

        with patch("src.utils.themes.apply_theme", mock_apply):
            api_clients.switch_theme(mock_root, "darkly")

        mock_apply.assert_called_once_with(mock_root, theme="darkly")

    def test_switch_theme_import_error(self, caplog: Any) -> None:
        """switch_theme() deve logar warning se import falhar"""
        mock_root = Mock()

        # Simula falha no import fazendo apply_theme levantar exceção
        with patch("src.utils.themes.apply_theme", side_effect=ImportError("no module")):
            api_clients.switch_theme(mock_root, "flatly")

        # Deve logar warning mas não crashar
        assert any("Failed to apply theme" in rec.message for rec in caplog.records)

    def test_switch_theme_apply_error(self, caplog: Any) -> None:
        """switch_theme() deve logar warning se apply_theme falhar"""
        mock_root = Mock()

        with patch(
            "src.utils.themes.apply_theme",
            side_effect=Exception("theme error"),
        ):
            api_clients.switch_theme(mock_root, "invalid")

        assert any("Failed to apply theme" in rec.message for rec in caplog.records)


# ============================================================================
# TestGetCurrentTheme
# ============================================================================


class TestGetCurrentTheme:
    """Testes para get_current_theme()"""

    def test_get_current_theme_success(self) -> None:
        """get_current_theme() deve retornar tema atual"""
        with patch("src.utils.themes.load_theme", return_value="darkly"):
            result = api_clients.get_current_theme()

        assert result == "darkly"

    def test_get_current_theme_error_fallback(self) -> None:
        """get_current_theme() deve retornar 'flatly' em caso de erro"""
        with patch(
            "src.utils.themes.load_theme",
            side_effect=Exception("load error"),
        ):
            result = api_clients.get_current_theme()

        assert result == "flatly"

    def test_get_current_theme_import_error(self) -> None:
        """get_current_theme() deve retornar fallback se import falhar"""
        with patch("src.utils.themes.load_theme", side_effect=ImportError("no module")):
            result = api_clients.get_current_theme()

        assert result == "flatly"


# ============================================================================
# TestUploadFolder
# ============================================================================


class TestUploadFolder:
    """Testes para upload_folder()"""

    def test_upload_folder_success(self) -> None:
        """upload_folder() deve delegar para upload_service e retornar resultado"""
        mock_result = {"success": True, "uploaded_count": 5, "errors": []}

        with patch.object(
            __import__("src.core.services.upload_service", fromlist=["upload_folder"]),
            "upload_folder",
            Mock(return_value=mock_result),
            create=True,
        ) as mock_upload:
            result = api_clients.upload_folder(
                local_dir="/tmp/docs",
                org_id="org123",
                client_id="client456",
                subdir="SIFAP",
            )

        assert result == mock_result
        mock_upload.assert_called_once_with(
            "/tmp/docs",
            org_id="org123",
            client_id="client456",
            subdir="SIFAP",
        )

    def test_upload_folder_default_subdir(self) -> None:
        """upload_folder() deve usar subdir padrão 'GERAL' se não especificado"""
        mock_result = {"success": True, "uploaded_count": 2, "errors": []}

        with patch.object(
            __import__("src.core.services.upload_service", fromlist=["upload_folder"]),
            "upload_folder",
            Mock(return_value=mock_result),
            create=True,
        ) as mock_upload:
            result = api_clients.upload_folder(
                local_dir="/tmp/docs",
                org_id="org1",
                client_id="client2",
            )

        assert result == mock_result
        # Verifica que subdir="GERAL" foi passado
        assert mock_upload.call_args[1]["subdir"] == "GERAL"

    def test_upload_folder_error(self, caplog: Any) -> None:
        """upload_folder() deve retornar dict de erro se upload_service falhar"""
        with patch.object(
            __import__("src.core.services.upload_service", fromlist=["upload_folder"]),
            "upload_folder",
            Mock(side_effect=Exception("network error")),
            create=True,
        ):
            result = api_clients.upload_folder(
                local_dir="/tmp/x",
                org_id="org1",
                client_id="client2",
            )

        assert result["success"] is False
        assert result["uploaded_count"] == 0
        assert len(result["errors"]) == 1
        assert "network error" in result["errors"][0]
        assert any("Folder upload failed" in rec.message for rec in caplog.records)


# ============================================================================
# TestCreateClient
# ============================================================================


class TestCreateClient:
    """Testes para create_client()"""

    def test_create_client_success(self) -> None:
        """create_client() deve retornar ID do cliente criado"""
        data = {"razao_social": "Empresa ABC", "cnpj": "12345678000190"}

        with patch.object(
            __import__("src.core.services.clientes_service", fromlist=["create_cliente"]),
            "create_cliente",
            Mock(return_value="new_client_id_123"),
            create=True,
        ):
            result = api_clients.create_client(data)

        assert result == "new_client_id_123"

    def test_create_client_error(self, caplog: Any) -> None:
        """create_client() deve retornar None em caso de erro"""
        data = {"razao_social": "Teste"}

        with patch.object(
            __import__("src.core.services.clientes_service", fromlist=["create_cliente"]),
            "create_cliente",
            Mock(side_effect=Exception("DB error")),
            create=True,
        ):
            result = api_clients.create_client(data)

        assert result is None
        assert any("Create client failed" in rec.message for rec in caplog.records)


# ============================================================================
# TestUpdateClient
# ============================================================================


class TestUpdateClient:
    """Testes para update_client()"""

    def test_update_client_success(self) -> None:
        """update_client() deve retornar True em caso de sucesso"""
        data = {"razao_social": "Empresa XYZ Atualizada"}
        mock_update = Mock()

        with patch("src.core.services.clientes_service.update_cliente", mock_update):
            result = api_clients.update_client("client_id_456", data)

        assert result is True
        mock_update.assert_called_once_with("client_id_456", data)

    def test_update_client_error(self, caplog: Any) -> None:
        """update_client() deve retornar False em caso de erro"""
        data = {"cnpj": "00000000000000"}

        with patch(
            "src.core.services.clientes_service.update_cliente",
            side_effect=Exception("validation error"),
        ):
            result = api_clients.update_client("client999", data)

        assert result is False
        assert any("Update client failed" in rec.message for rec in caplog.records)


# ============================================================================
# TestDeleteClient
# ============================================================================


class TestDeleteClient:
    """Testes para delete_client()"""

    def test_delete_client_soft_default(self) -> None:
        """delete_client() deve fazer soft delete por padrão"""
        with patch.object(
            __import__("src.core.services.clientes_service", fromlist=["delete_cliente"]),
            "delete_cliente",
            Mock(),
            create=True,
        ) as mock_delete:
            result = api_clients.delete_client("client_abc")

        assert result is True
        mock_delete.assert_called_once_with("client_abc", soft=True)

    def test_delete_client_soft_explicit(self) -> None:
        """delete_client() deve fazer soft delete quando soft=True"""
        with patch.object(
            __import__("src.core.services.clientes_service", fromlist=["delete_cliente"]),
            "delete_cliente",
            Mock(),
            create=True,
        ) as mock_delete:
            result = api_clients.delete_client("client_abc", soft=True)

        assert result is True
        mock_delete.assert_called_once_with("client_abc", soft=True)

    def test_delete_client_hard(self) -> None:
        """delete_client() deve fazer hard delete quando soft=False"""
        with patch.object(
            __import__("src.core.services.clientes_service", fromlist=["delete_cliente"]),
            "delete_cliente",
            Mock(),
            create=True,
        ) as mock_delete:
            result = api_clients.delete_client("client_xyz", soft=False)

        assert result is True
        mock_delete.assert_called_once_with("client_xyz", soft=False)

    def test_delete_client_error(self, caplog: Any) -> None:
        """delete_client() deve retornar False em caso de erro"""
        with patch.object(
            __import__("src.core.services.clientes_service", fromlist=["delete_cliente"]),
            "delete_cliente",
            Mock(side_effect=Exception("not found")),
            create=True,
        ):
            result = api_clients.delete_client("nonexistent")

        assert result is False
        assert any("Delete client failed" in rec.message for rec in caplog.records)


# ============================================================================
# TestSearchClients
# ============================================================================


class TestSearchClients:
    """Testes para search_clients()"""

    def test_search_clients_success(self) -> None:
        """search_clients() deve retornar lista de clientes"""
        mock_cliente1 = MagicMock(spec=Cliente)
        mock_cliente1.id = "c1"
        mock_cliente1.razao_social = "Empresa A"

        mock_cliente2 = MagicMock(spec=Cliente)
        mock_cliente2.id = "c2"
        mock_cliente2.razao_social = "Empresa B"

        mock_search = Mock(return_value=[mock_cliente1, mock_cliente2])

        with patch("src.core.search.search_clientes", mock_search):
            result = api_clients.search_clients("Empresa")

        assert len(result) == 2
        assert result[0].id == "c1"
        assert result[1].id == "c2"
        mock_search.assert_called_once_with("Empresa", org_id=None)

    def test_search_clients_with_org_id(self) -> None:
        """search_clients() deve passar org_id para search_clientes"""
        mock_cliente = MagicMock(spec=Cliente)
        mock_search = Mock(return_value=[mock_cliente])

        with patch("src.core.search.search_clientes", mock_search):
            result = api_clients.search_clients("ABC", org_id="org789")

        assert len(result) == 1
        mock_search.assert_called_once_with("ABC", org_id="org789")

    def test_search_clients_empty_result(self) -> None:
        """search_clients() deve retornar lista vazia se nada for encontrado"""
        mock_search = Mock(return_value=[])

        with patch("src.core.search.search_clientes", mock_search):
            result = api_clients.search_clients("naoexiste")

        assert result == []

    def test_search_clients_error(self, caplog: Any) -> None:
        """search_clients() deve retornar lista vazia em caso de erro"""
        with patch(
            "src.core.search.search_clientes",
            side_effect=Exception("search failed"),
        ):
            result = api_clients.search_clients("teste")

        assert result == []
        assert any("Client search failed" in rec.message for rec in caplog.records)


# ============================================================================
# TestEdgeCases
# ============================================================================


class TestEdgeCases:
    """Testes de edge cases e cobertura adicional"""

    def test_all_functions_in_all(self) -> None:
        """Verificar que __all__ contém todas as funções públicas"""
        expected = {
            "switch_theme",
            "get_current_theme",
            "upload_folder",
            "create_client",
            "update_client",
            "delete_client",
            "search_clients",
        }
        assert set(api_clients.__all__) == expected

    def test_upload_folder_partial_success(self) -> None:
        """upload_folder() pode retornar sucesso parcial com alguns erros"""
        mock_result = {
            "success": True,
            "uploaded_count": 3,
            "errors": ["file1.pdf: access denied", "file2.docx: too large"],
        }

        with patch.object(
            __import__("src.core.services.upload_service", fromlist=["upload_folder"]),
            "upload_folder",
            Mock(return_value=mock_result),
            create=True,
        ):
            result = api_clients.upload_folder("/tmp/docs", "org1", "client1")

        assert result["success"] is True
        assert result["uploaded_count"] == 3
        assert len(result["errors"]) == 2

    def test_switch_theme_with_none_root(self, caplog: Any) -> None:
        """switch_theme() deve lidar com root=None gracefully"""
        with patch(
            "src.utils.themes.apply_theme",
            side_effect=AttributeError("root is None"),
        ):
            api_clients.switch_theme(None, "flatly")  # type: ignore

        assert any("Failed to apply theme" in rec.message for rec in caplog.records)

    def test_search_clients_query_empty_string(self) -> None:
        """search_clients() deve funcionar com query vazia"""
        mock_search = Mock(return_value=[])

        with patch("src.core.search.search_clientes", mock_search):
            result = api_clients.search_clients("")

        assert result == []
        mock_search.assert_called_once_with("", org_id=None)
