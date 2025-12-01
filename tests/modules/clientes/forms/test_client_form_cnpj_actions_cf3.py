# -*- coding: utf-8 -*-
"""
Testes para client_form_cnpj_actions (CF-3).

Valida extração de dados do Cartão CNPJ e preenchimento de formulário
de forma independente de UI.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from src.modules.clientes.forms.client_form_cnpj_actions import (
    CnpjActionDeps,
    CnpjExtractionResult,
    apply_cnpj_data_to_form,
    extract_cnpj_from_directory,
    handle_cartao_cnpj_action,
)


# -----------------------------------------------------------------------------
# Fake Adapters
# -----------------------------------------------------------------------------


class FakeMessageSink:
    """Fake para capturar mensagens exibidas."""

    def __init__(self) -> None:
        self.warnings: list[tuple[str, str]] = []
        self.infos: list[tuple[str, str]] = []

    def warn(self, title: str, message: str) -> None:
        self.warnings.append((title, message))

    def info(self, title: str, message: str) -> None:
        self.infos.append((title, message))


class FakeFormFieldSetter:
    """Fake para capturar valores setados no formulário."""

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def set_value(self, field_name: str, value: str) -> None:
        self.values[field_name] = value


class FakeDirectorySelector:
    """Fake para simular seleção de diretório."""

    def __init__(self, directory: str | None = None) -> None:
        self.selected_directory = directory
        self.call_count = 0
        self.last_title: str | None = None

    def select_directory(self, title: str) -> str | None:
        self.call_count += 1
        self.last_title = title
        return self.selected_directory


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def fake_messages() -> FakeMessageSink:
    """Cria FakeMessageSink."""
    return FakeMessageSink()


@pytest.fixture
def fake_field_setter() -> FakeFormFieldSetter:
    """Cria FakeFormFieldSetter."""
    return FakeFormFieldSetter()


@pytest.fixture
def fake_directory_selector() -> FakeDirectorySelector:
    """Cria FakeDirectorySelector com diretório padrão."""
    return FakeDirectorySelector(directory="/fake/dir")


@pytest.fixture
def mock_service_success() -> Mock:
    """Mock do serviço retornando dados válidos."""
    with patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock:
        mock.return_value = {
            "cnpj": "12.345.678/0001-90",
            "razao_social": "EMPRESA TESTE LTDA",
        }
        yield mock


@pytest.fixture
def mock_service_no_data() -> Mock:
    """Mock do serviço retornando dados vazios."""
    with patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock:
        mock.return_value = {"cnpj": None, "razao_social": None}
        yield mock


@pytest.fixture
def mock_service_partial_data() -> Mock:
    """Mock do serviço retornando apenas CNPJ."""
    with patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock:
        mock.return_value = {
            "cnpj": "98765432000100",
            "razao_social": None,
        }
        yield mock


@pytest.fixture
def mock_service_exception() -> Mock:
    """Mock do serviço lançando exceção."""
    with patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock:
        mock.side_effect = RuntimeError("Erro simulado no serviço")
        yield mock


# -----------------------------------------------------------------------------
# Testes: extract_cnpj_from_directory
# -----------------------------------------------------------------------------


def test_extract_cnpj_success(mock_service_success: Mock) -> None:
    """Testa extração bem-sucedida de dados do Cartão CNPJ."""
    result = extract_cnpj_from_directory("/test/dir")

    assert result.ok is True
    assert result.base_dir == "/test/dir"
    assert result.cnpj == "12.345.678/0001-90"
    assert result.razao_social == "EMPRESA TESTE LTDA"
    assert result.error_message is None
    mock_service_success.assert_called_once_with("/test/dir")


def test_extract_cnpj_no_data(mock_service_no_data: Mock) -> None:
    """Testa extração sem dados encontrados."""
    result = extract_cnpj_from_directory("/test/dir")

    assert result.ok is False
    assert result.base_dir == "/test/dir"
    assert result.cnpj is None
    assert result.razao_social is None
    assert "Nenhum Cartão CNPJ válido encontrado" in (result.error_message or "")
    mock_service_no_data.assert_called_once_with("/test/dir")


def test_extract_cnpj_partial_data_ok(mock_service_partial_data: Mock) -> None:
    """Testa extração com apenas CNPJ (sem razão social)."""
    result = extract_cnpj_from_directory("/test/dir")

    assert result.ok is True
    assert result.base_dir == "/test/dir"
    assert result.cnpj == "98765432000100"
    assert result.razao_social is None
    mock_service_partial_data.assert_called_once_with("/test/dir")


def test_extract_cnpj_exception(mock_service_exception: Mock) -> None:
    """Testa extração com exceção no serviço."""
    result = extract_cnpj_from_directory("/test/dir")

    assert result.ok is False
    assert result.base_dir == "/test/dir"
    assert result.cnpj is None
    assert result.razao_social is None
    assert "Erro ao processar Cartão CNPJ" in (result.error_message or "")
    mock_service_exception.assert_called_once_with("/test/dir")


# -----------------------------------------------------------------------------
# Testes: apply_cnpj_data_to_form
# -----------------------------------------------------------------------------


def test_apply_cnpj_data_full(fake_field_setter: FakeFormFieldSetter) -> None:
    """Testa aplicação de CNPJ e razão social ao formulário."""
    result = CnpjExtractionResult(
        ok=True,
        base_dir="/test",
        cnpj="12.345.678/0001-90",
        razao_social="EMPRESA TESTE LTDA",
    )

    apply_cnpj_data_to_form(result, fake_field_setter)

    assert fake_field_setter.values["CNPJ"] == "12345678000190"  # Apenas dígitos
    assert fake_field_setter.values["Razão Social"] == "EMPRESA TESTE LTDA"


def test_apply_cnpj_data_only_cnpj(fake_field_setter: FakeFormFieldSetter) -> None:
    """Testa aplicação apenas de CNPJ ao formulário."""
    result = CnpjExtractionResult(
        ok=True,
        base_dir="/test",
        cnpj="98765432000100",
        razao_social=None,
    )

    apply_cnpj_data_to_form(result, fake_field_setter)

    assert fake_field_setter.values["CNPJ"] == "98765432000100"
    assert "Razão Social" not in fake_field_setter.values


def test_apply_cnpj_data_only_razao(fake_field_setter: FakeFormFieldSetter) -> None:
    """Testa aplicação apenas de razão social ao formulário."""
    result = CnpjExtractionResult(
        ok=True,
        base_dir="/test",
        cnpj=None,
        razao_social="OUTRA EMPRESA S/A",
    )

    apply_cnpj_data_to_form(result, fake_field_setter)

    assert "CNPJ" not in fake_field_setter.values
    assert fake_field_setter.values["Razão Social"] == "OUTRA EMPRESA S/A"


def test_apply_cnpj_data_not_ok(fake_field_setter: FakeFormFieldSetter) -> None:
    """Testa que não aplica dados se result.ok=False."""
    result = CnpjExtractionResult(
        ok=False,
        base_dir="/test",
        error_message="Erro simulado",
    )

    apply_cnpj_data_to_form(result, fake_field_setter)

    assert len(fake_field_setter.values) == 0


# -----------------------------------------------------------------------------
# Testes: handle_cartao_cnpj_action
# -----------------------------------------------------------------------------


def test_handle_cartao_cnpj_user_cancel(
    fake_messages: FakeMessageSink,
    fake_field_setter: FakeFormFieldSetter,
) -> None:
    """Testa cancelamento da seleção de diretório pelo usuário."""
    selector = FakeDirectorySelector(directory=None)  # Usuário cancelou
    deps = CnpjActionDeps(
        messages=fake_messages,
        field_setter=fake_field_setter,
        directory_selector=selector,
    )

    result = handle_cartao_cnpj_action(deps)

    assert result.ok is False
    assert result.base_dir is None
    assert result.error_message == "Seleção cancelada"
    assert selector.call_count == 1
    assert len(fake_field_setter.values) == 0
    assert len(fake_messages.warnings) == 0


def test_handle_cartao_cnpj_success(
    fake_messages: FakeMessageSink,
    fake_field_setter: FakeFormFieldSetter,
    fake_directory_selector: FakeDirectorySelector,
    mock_service_success: Mock,
) -> None:
    """Testa fluxo completo com extração bem-sucedida."""
    deps = CnpjActionDeps(
        messages=fake_messages,
        field_setter=fake_field_setter,
        directory_selector=fake_directory_selector,
    )

    result = handle_cartao_cnpj_action(deps)

    assert result.ok is True
    assert result.base_dir == "/fake/dir"
    assert result.cnpj == "12.345.678/0001-90"
    assert result.razao_social == "EMPRESA TESTE LTDA"
    assert fake_field_setter.values["CNPJ"] == "12345678000190"
    assert fake_field_setter.values["Razão Social"] == "EMPRESA TESTE LTDA"
    assert len(fake_messages.warnings) == 0


def test_handle_cartao_cnpj_no_data_warning(
    fake_messages: FakeMessageSink,
    fake_field_setter: FakeFormFieldSetter,
    fake_directory_selector: FakeDirectorySelector,
    mock_service_no_data: Mock,
) -> None:
    """Testa exibição de aviso quando nenhum dado é encontrado."""
    deps = CnpjActionDeps(
        messages=fake_messages,
        field_setter=fake_field_setter,
        directory_selector=fake_directory_selector,
    )

    result = handle_cartao_cnpj_action(deps)

    assert result.ok is False
    assert result.base_dir == "/fake/dir"
    assert len(fake_field_setter.values) == 0
    assert len(fake_messages.warnings) == 1
    title, msg = fake_messages.warnings[0]
    assert title == "Atenção"
    assert "Nenhum Cartão CNPJ válido encontrado" in msg


def test_handle_cartao_cnpj_exception_warning(
    fake_messages: FakeMessageSink,
    fake_field_setter: FakeFormFieldSetter,
    fake_directory_selector: FakeDirectorySelector,
    mock_service_exception: Mock,
) -> None:
    """Testa exibição de aviso quando ocorre exceção."""
    deps = CnpjActionDeps(
        messages=fake_messages,
        field_setter=fake_field_setter,
        directory_selector=fake_directory_selector,
    )

    result = handle_cartao_cnpj_action(deps)

    assert result.ok is False
    assert len(fake_field_setter.values) == 0
    assert len(fake_messages.warnings) == 1
    title, msg = fake_messages.warnings[0]
    assert title == "Atenção"
    assert "Erro ao processar Cartão CNPJ" in msg


def test_handle_cartao_cnpj_partial_data_fills_form(
    fake_messages: FakeMessageSink,
    fake_field_setter: FakeFormFieldSetter,
    fake_directory_selector: FakeDirectorySelector,
    mock_service_partial_data: Mock,
) -> None:
    """Testa preenchimento com dados parciais (apenas CNPJ)."""
    deps = CnpjActionDeps(
        messages=fake_messages,
        field_setter=fake_field_setter,
        directory_selector=fake_directory_selector,
    )

    result = handle_cartao_cnpj_action(deps)

    assert result.ok is True
    assert result.cnpj == "98765432000100"
    assert result.razao_social is None
    assert fake_field_setter.values["CNPJ"] == "98765432000100"
    assert "Razão Social" not in fake_field_setter.values
    assert len(fake_messages.warnings) == 0


def test_handle_cartao_cnpj_directory_selector_title() -> None:
    """Valida que o título correto é passado ao seletor de diretório."""
    selector = FakeDirectorySelector(directory="/any/dir")
    deps = CnpjActionDeps(
        messages=FakeMessageSink(),
        field_setter=FakeFormFieldSetter(),
        directory_selector=selector,
    )

    with patch("src.modules.clientes.service.extrair_dados_cartao_cnpj_em_pasta") as mock:
        mock.return_value = {"cnpj": None, "razao_social": None}
        handle_cartao_cnpj_action(deps)

    assert selector.last_title == "Escolha a pasta do cliente (com o Cartão CNPJ)"
