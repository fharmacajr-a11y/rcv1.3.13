# -*- coding: utf-8 -*-
"""Testes da extração de CNPJ da pasta (FASE 3.7).

Valida o fluxo completo do botão "Cartão CNPJ":
- Seleção de pasta
- Extração de dados (CNPJ e Razão Social)
- Preenchimento automático dos campos
- Tratamento de erros (pasta sem PDF, PDF inválido)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from unittest.mock import patch


from src.modules.clientes_v2.views.client_editor_dialog import ClientEditorDialog

log = logging.getLogger(__name__)


class TestCNPJExtraction:
    """Testes da extração de CNPJ da pasta."""

    def test_extract_cnpj_success_fills_fields(self, root: Any, tmp_path: Path) -> None:
        """Testa extração bem-sucedida que preenche campos automaticamente.

        FASE 3.7: Validar que quando a extração retorna CNPJ e razão social,
        os campos do formulário são preenchidos corretamente.
        """
        # Arrange
        test_folder = tmp_path / "cliente_teste"
        test_folder.mkdir()

        dialog = ClientEditorDialog(root)

        # Mock para askdirectory retornar pasta temporária
        with (
            patch("tkinter.filedialog.askdirectory", return_value=str(test_folder)),
            patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock_extrair,
            patch("tkinter.messagebox.showinfo") as mock_info,
        ):
            # Configurar retorno do service (sucesso)
            mock_extrair.return_value = {"cnpj": "12.345.678/0001-90", "razao_social": "EMPRESA TESTE LTDA"}

            # Act
            dialog._on_cartao_cnpj()

            # Assert
            mock_extrair.assert_called_once_with(str(test_folder))

            # Verificar que campos foram preenchidos
            assert dialog.cnpj_entry.get() == "12.345.678/0001-90"
            assert dialog.razao_entry.get() == "EMPRESA TESTE LTDA"

            # Verificar mensagem de sucesso
            mock_info.assert_called_once()
            args = mock_info.call_args[0]
            assert args[0] == "Sucesso"
            assert "sucesso" in args[1].lower()

    def test_extract_cnpj_partial_data_fills_available_fields(self, root: Any, tmp_path: Path) -> None:
        """Testa extração parcial (apenas CNPJ OU apenas razão social).

        FASE 3.7: Validar que campos disponíveis são preenchidos mesmo
        quando a extração retorna apenas um dos dados.
        """
        # Arrange
        test_folder = tmp_path / "cliente_parcial"
        test_folder.mkdir()

        dialog = ClientEditorDialog(root)
        dialog.razao_entry.insert(0, "RAZÃO ANTIGA")

        # Mock para askdirectory
        with (
            patch("tkinter.filedialog.askdirectory", return_value=str(test_folder)),
            patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock_extrair,
            patch("tkinter.messagebox.showinfo") as mock_info,
        ):
            # Configurar retorno parcial (apenas CNPJ)
            mock_extrair.return_value = {"cnpj": "99.888.777/0001-66", "razao_social": None}

            # Act
            dialog._on_cartao_cnpj()

            # Assert
            assert dialog.cnpj_entry.get() == "99.888.777/0001-66"
            assert dialog.razao_entry.get() == "RAZÃO ANTIGA"  # Não sobrescreve

            mock_info.assert_called_once()

    def test_extract_cnpj_no_pdf_shows_warning(self, root: Any, tmp_path: Path) -> None:
        """Testa aviso quando pasta não contém PDF de cartão CNPJ.

        FASE 3.7: Validar que quando o service não encontra PDF válido,
        uma mensagem de aviso é exibida ao usuário.
        """
        # Arrange
        empty_folder = tmp_path / "pasta_vazia"
        empty_folder.mkdir()

        dialog = ClientEditorDialog(root)

        # Mock para askdirectory
        with (
            patch("tkinter.filedialog.askdirectory", return_value=str(empty_folder)),
            patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock_extrair,
            patch("tkinter.messagebox.showwarning") as mock_warning,
            patch("tkinter.messagebox.showinfo") as mock_info,
        ):
            # Configurar retorno vazio (nenhum dado extraído)
            mock_extrair.return_value = {"cnpj": None, "razao_social": None}

            # Act
            dialog._on_cartao_cnpj()

            # Assert
            mock_extrair.assert_called_once_with(str(empty_folder))

            # Verificar mensagem de aviso (não sucesso)
            mock_warning.assert_called_once()
            args = mock_warning.call_args[0]
            assert args[0] == "Atenção"
            assert "não encontrado" in args[1].lower() or "nenhum" in args[1].lower()

            # NÃO deve mostrar sucesso
            mock_info.assert_not_called()

    def test_extract_cnpj_cancel_does_nothing(self, root: Any) -> None:
        """Testa cancelamento da seleção de pasta.

        FASE 3.7: Validar que quando o usuário cancela o diálogo de
        seleção de pasta, nenhuma ação é executada.
        """
        # Arrange
        dialog = ClientEditorDialog(root)
        dialog.cnpj_entry.insert(0, "CNPJ ORIGINAL")

        # Mock para askdirectory retornar None (cancelado)
        with (
            patch("tkinter.filedialog.askdirectory", return_value=""),
            patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock_extrair,
            patch("tkinter.messagebox.showwarning") as mock_warning,
        ):
            # Act
            dialog._on_cartao_cnpj()

            # Assert
            # Service NÃO deve ser chamado
            mock_extrair.assert_not_called()
            mock_warning.assert_not_called()

            # Campo não deve ter sido alterado
            assert dialog.cnpj_entry.get() == "CNPJ ORIGINAL"

    def test_extract_cnpj_service_error_shows_error(self, root: Any, tmp_path: Path) -> None:
        """Testa tratamento de erro quando service lança exceção.

        FASE 3.7: Validar que erros inesperados (IO, parsing, etc)
        são capturados e exibidos ao usuário.
        """
        # Arrange
        error_folder = tmp_path / "pasta_com_erro"
        error_folder.mkdir()

        dialog = ClientEditorDialog(root)

        # Mock para askdirectory
        with (
            patch("tkinter.filedialog.askdirectory", return_value=str(error_folder)),
            patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock_extrair,
            patch("tkinter.messagebox.showerror") as mock_error,
        ):
            # Configurar service para lançar exceção
            mock_extrair.side_effect = IOError("Erro ao ler PDF")

            # Act
            dialog._on_cartao_cnpj()

            # Assert
            mock_error.assert_called_once()
            args = mock_error.call_args[0]
            assert args[0] == "Erro"
            assert "erro" in args[1].lower()

    def test_extract_cnpj_preserves_other_fields(self, root: Any, tmp_path: Path) -> None:
        """Testa que outros campos do formulário não são alterados.

        FASE 3.7: Validar que a extração de CNPJ afeta apenas os campos
        CNPJ e Razão Social, preservando WhatsApp, Nome, etc.
        """
        # Arrange
        test_folder = tmp_path / "cliente_preserva"
        test_folder.mkdir()

        dialog = ClientEditorDialog(root)

        # Preencher campos que NÃO devem ser alterados
        dialog.nome_entry.insert(0, "Nome Teste")
        dialog.whatsapp_entry.insert(0, "(11) 98765-4321")
        dialog.obs_text.insert("1.0", "Observações importantes")

        # Mock para askdirectory
        with (
            patch("tkinter.filedialog.askdirectory", return_value=str(test_folder)),
            patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock_extrair,
            patch("tkinter.messagebox.showinfo"),
        ):
            # Configurar retorno do service
            mock_extrair.return_value = {"cnpj": "11.222.333/0001-44", "razao_social": "NOVA EMPRESA LTDA"}

            # Act
            dialog._on_cartao_cnpj()

            # Assert
            # Campos extraídos devem ter mudado
            assert dialog.cnpj_entry.get() == "11.222.333/0001-44"
            assert dialog.razao_entry.get() == "NOVA EMPRESA LTDA"

            # Outros campos devem ter sido preservados
            assert dialog.nome_entry.get() == "Nome Teste"
            assert dialog.whatsapp_entry.get() == "(11) 98765-4321"
            assert "Observações importantes" in dialog.obs_text.get("1.0", "end")

    def test_extract_cnpj_overwrites_existing_data(self, root: Any, tmp_path: Path) -> None:
        """Testa que extração sobrescreve dados existentes nos campos.

        FASE 3.7: Validar que quando há dados preexistentes nos campos
        CNPJ e Razão Social, eles são substituídos pelos novos valores.
        """
        # Arrange
        test_folder = tmp_path / "cliente_sobrescreve"
        test_folder.mkdir()

        dialog = ClientEditorDialog(root)

        # Preencher campos com dados antigos
        dialog.cnpj_entry.insert(0, "99.999.999/0001-99")
        dialog.razao_entry.insert(0, "EMPRESA ANTIGA LTDA")

        # Mock para askdirectory
        with (
            patch("tkinter.filedialog.askdirectory", return_value=str(test_folder)),
            patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock_extrair,
            patch("tkinter.messagebox.showinfo"),
        ):
            # Configurar retorno com novos dados
            mock_extrair.return_value = {"cnpj": "11.111.111/0001-11", "razao_social": "EMPRESA NOVA LTDA"}

            # Act
            dialog._on_cartao_cnpj()

            # Assert
            # Dados antigos devem ter sido substituídos
            assert dialog.cnpj_entry.get() == "11.111.111/0001-11"
            assert dialog.razao_entry.get() == "EMPRESA NOVA LTDA"

            # Garantir que não há resíduos dos dados antigos
            assert "99.999.999" not in dialog.cnpj_entry.get()
            assert "ANTIGA" not in dialog.razao_entry.get()

    def test_extract_cnpj_button_exists_in_dialog(self, root: Any) -> None:
        """Testa que o botão 'Cartão CNPJ' existe no diálogo.

        FASE 3.7: Validar que o botão foi adicionado corretamente
        à interface e está acessível.
        """
        # Arrange & Act
        dialog = ClientEditorDialog(root)

        # Assert
        assert hasattr(dialog, "cartao_btn"), "Botão 'Cartão CNPJ' não encontrado"
        assert dialog.cartao_btn is not None
        assert dialog.cartao_btn.cget("text") == "Cartão CNPJ"

    def test_extract_cnpj_handles_empty_strings(self, root: Any, tmp_path: Path) -> None:
        """Testa tratamento de strings vazias retornadas pelo service.

        FASE 3.7: Validar que strings vazias são tratadas como dados
        não disponíveis (similar a None).
        """
        # Arrange
        test_folder = tmp_path / "cliente_strings_vazias"
        test_folder.mkdir()

        dialog = ClientEditorDialog(root)
        dialog.cnpj_entry.insert(0, "CNPJ EXISTENTE")
        dialog.razao_entry.insert(0, "RAZÃO EXISTENTE")

        # Mock para askdirectory
        with (
            patch("tkinter.filedialog.askdirectory", return_value=str(test_folder)),
            patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock_extrair,
            patch("tkinter.messagebox.showwarning") as mock_warning,
        ):
            # Configurar retorno com strings vazias
            mock_extrair.return_value = {"cnpj": "", "razao_social": ""}

            # Act
            dialog._on_cartao_cnpj()

            # Assert
            # Deve mostrar aviso (tratado como sem dados)
            mock_warning.assert_called_once()

            # Campos não devem ter sido alterados
            assert dialog.cnpj_entry.get() == "CNPJ EXISTENTE"
            assert dialog.razao_entry.get() == "RAZÃO EXISTENTE"
