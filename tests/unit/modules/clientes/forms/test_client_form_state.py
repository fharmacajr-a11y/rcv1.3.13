# -*- coding: utf-8 -*-
"""Testes unitários para client_form_state.

Testa o estado do formulário de clientes sem depender de UI.

Refatoração: MICROFASE-11
"""

from __future__ import annotations


from src.modules.clientes.forms.client_form_state import (
    ClientFormData,
    ClientFormState,
    ClientFormValidation,
    build_window_title,
    extract_address_fields,
)


# =============================================================================
# Testes de ClientFormData
# =============================================================================


def test_client_form_data_default() -> None:
    """Testa criação de ClientFormData vazio."""
    data = ClientFormData()

    assert data.razao_social == ""
    assert data.cnpj == ""
    assert data.nome == ""
    assert data.whatsapp == ""
    assert data.observacoes == ""
    assert data.status == ""
    assert data.endereco == ""
    assert data.bairro == ""
    assert data.cidade == ""
    assert data.cep == ""


def test_client_form_data_to_dict() -> None:
    """Testa conversão de ClientFormData para dicionário."""
    data = ClientFormData(
        razao_social="Empresa Teste LTDA",
        cnpj="12.345.678/0001-90",
        nome="João Silva",
        whatsapp="11 99999-9999",
        status="Ativo",
    )

    result = data.to_dict()

    assert result["Razão Social"] == "Empresa Teste LTDA"
    assert result["CNPJ"] == "12.345.678/0001-90"
    assert result["Nome"] == "João Silva"
    assert result["WhatsApp"] == "11 99999-9999"
    assert result["Status do Cliente"] == "Ativo"


def test_client_form_data_from_dict() -> None:
    """Testa criação de ClientFormData a partir de dicionário."""
    data_dict = {
        "Razão Social": "Empresa Teste LTDA",
        "CNPJ": "12.345.678/0001-90",
        "Nome": "João Silva",
        "Status do Cliente": "Ativo",
    }

    data = ClientFormData.from_dict(data_dict)

    assert data.razao_social == "Empresa Teste LTDA"
    assert data.cnpj == "12.345.678/0001-90"
    assert data.nome == "João Silva"
    assert data.status == "Ativo"


def test_client_form_data_from_row() -> None:
    """Testa criação de ClientFormData a partir de row do banco."""
    row = (
        123,  # pk
        "Empresa Teste LTDA",  # razao
        "12.345.678/0001-90",  # cnpj
        "João Silva",  # nome
        "11 99999-9999",  # numero
        "Observação de teste",  # obs
        "2024-01-01",  # ult
    )

    data = ClientFormData.from_row(row)

    assert data.razao_social == "Empresa Teste LTDA"
    assert data.cnpj == "12.345.678/0001-90"
    assert data.nome == "João Silva"
    assert data.whatsapp == "11 99999-9999"
    assert data.observacoes == "Observação de teste"


def test_client_form_data_from_row_with_status_prefix() -> None:
    """Testa extração de status de observações com prefixo."""
    row = (
        123,
        "Empresa Teste LTDA",
        "12.345.678/0001-90",
        "João Silva",
        "11 99999-9999",
        "[Ativo] Observação de teste",  # status embutido (sem ST:)
        "2024-01-01",
    )

    data = ClientFormData.from_row(row)

    assert data.status == "Ativo"
    assert data.observacoes == "Observação de teste"


def test_client_form_data_from_row_empty() -> None:
    """Testa criação de ClientFormData a partir de row vazio."""
    data = ClientFormData.from_row(None)

    assert data.razao_social == ""
    assert data.cnpj == ""


# =============================================================================
# Testes de ClientFormValidation
# =============================================================================


def test_client_form_validation_default() -> None:
    """Testa criação de ClientFormValidation vazio."""
    validation = ClientFormValidation()

    assert validation.is_valid()
    assert not validation.has_warnings()


def test_client_form_validation_add_error() -> None:
    """Testa adição de erros."""
    validation = ClientFormValidation()

    validation.add_error("Campo obrigatório")
    validation.add_error("Formato inválido")

    assert not validation.is_valid()
    assert len(validation.errors) == 2
    assert "Campo obrigatório" in validation.errors


def test_client_form_validation_add_warning() -> None:
    """Testa adição de avisos."""
    validation = ClientFormValidation()

    validation.add_warning("Aviso de teste")

    assert validation.is_valid()  # Avisos não invalidam
    assert validation.has_warnings()
    assert len(validation.warnings) == 1


def test_client_form_validation_clear() -> None:
    """Testa limpeza de erros e avisos."""
    validation = ClientFormValidation()

    validation.add_error("Erro")
    validation.add_warning("Aviso")
    validation.clear()

    assert validation.is_valid()
    assert not validation.has_warnings()


# =============================================================================
# Testes de ClientFormState
# =============================================================================


def test_client_form_state_default() -> None:
    """Testa criação de ClientFormState padrão."""
    state = ClientFormState()

    assert state.client_id is None
    assert state.is_new
    assert not state.is_dirty
    assert state.initializing


def test_client_form_state_mark_dirty() -> None:
    """Testa marcação de dirty state."""
    state = ClientFormState()
    state.initializing = False  # Desabilita inicialização

    state.mark_dirty()

    assert state.is_dirty


def test_client_form_state_mark_dirty_during_initialization() -> None:
    """Testa que dirty é ignorado durante inicialização."""
    state = ClientFormState()
    state.initializing = True

    state.mark_dirty()

    assert not state.is_dirty


def test_client_form_state_mark_clean() -> None:
    """Testa marcação de clean state."""
    state = ClientFormState()
    state.is_dirty = True

    state.mark_clean()

    assert not state.is_dirty


def test_client_form_state_update_client_id() -> None:
    """Testa atualização de client_id."""
    state = ClientFormState()

    state.update_client_id(123)

    assert state.client_id == 123
    assert not state.is_new


def test_client_form_state_load_from_row() -> None:
    """Testa carregamento de dados de row."""
    state = ClientFormState()
    row = (
        123,
        "Empresa Teste LTDA",
        "12.345.678/0001-90",
        "João Silva",
        "11 99999-9999",
        "Observação de teste",
        "2024-01-01",
    )

    state.load_from_row(row)

    assert state.client_id == 123
    assert not state.is_new
    assert state.data.razao_social == "Empresa Teste LTDA"
    assert state.data.cnpj == "12.345.678/0001-90"


def test_client_form_state_load_from_preset() -> None:
    """Testa carregamento de dados de preset."""
    state = ClientFormState()
    preset = {
        "razao": "Empresa Teste LTDA",
        "cnpj": "12.345.678/0001-90",
    }

    state.load_from_preset(preset)

    assert state.data.razao_social == "Empresa Teste LTDA"
    assert state.data.cnpj == "12.345.678/0001-90"


def test_client_form_state_validate_ok() -> None:
    """Testa validação com dados válidos."""
    state = ClientFormState()
    state.data.razao_social = "Empresa Teste LTDA"
    state.data.cnpj = "12.345.678/0001-90"

    result = state.validate()

    assert result.is_valid()


def test_client_form_state_validate_missing_razao() -> None:
    """Testa validação com razão social faltando."""
    state = ClientFormState()
    state.data.cnpj = "12.345.678/0001-90"
    # razao_social vazio

    result = state.validate()

    assert not result.is_valid()
    assert any("Razão Social" in err for err in result.errors)


def test_client_form_state_validate_missing_cnpj() -> None:
    """Testa validação com CNPJ faltando."""
    state = ClientFormState()
    state.data.razao_social = "Empresa Teste LTDA"
    # cnpj vazio

    result = state.validate()

    assert not result.is_valid()
    assert any("CNPJ" in err for err in result.errors)


def test_client_form_state_validate_invalid_cnpj() -> None:
    """Testa validação com CNPJ inválido."""
    state = ClientFormState()
    state.data.razao_social = "Empresa Teste LTDA"
    state.data.cnpj = "123"  # CNPJ muito curto

    result = state.validate()

    assert result.is_valid()  # Não é erro, apenas aviso
    assert result.has_warnings()
    assert any("formato inválido" in w for w in result.warnings)


def test_client_form_state_finish_initialization() -> None:
    """Testa finalização de inicialização."""
    state = ClientFormState()
    assert state.initializing

    state.finish_initialization()

    assert not state.initializing


# =============================================================================
# Testes de Funções Auxiliares
# =============================================================================


def test_build_window_title_new_client() -> None:
    """Testa construção de título para novo cliente."""
    state = ClientFormState()

    title = build_window_title(state)

    assert title == "Editar Cliente"


def test_build_window_title_with_id() -> None:
    """Testa construção de título com ID."""
    state = ClientFormState(client_id=123)

    title = build_window_title(state)

    assert "123" in title


def test_build_window_title_with_data() -> None:
    """Testa construção de título com dados."""
    state = ClientFormState(client_id=123)

    title = build_window_title(
        state,
        razao_social="Empresa Teste LTDA",
        cnpj="12.345.678/0001-90",
    )

    assert "123" in title
    assert "Empresa Teste LTDA" in title
    assert "12.345.678/0001-90" in title


def test_extract_address_fields_from_dict() -> None:
    """Testa extração de campos de endereço de dict."""
    cliente = {
        "endereco": "Rua Teste, 123",
        "bairro": "Centro",
        "cidade": "São Paulo",
        "cep": "01234-567",
    }

    result = extract_address_fields(cliente)

    assert result["endereco"] == "Rua Teste, 123"
    assert result["bairro"] == "Centro"
    assert result["cidade"] == "São Paulo"
    assert result["cep"] == "01234-567"


def test_extract_address_fields_from_object() -> None:
    """Testa extração de campos de endereço de objeto."""

    class Cliente:
        endereco = "Rua Teste, 123"
        bairro = "Centro"
        cidade = "São Paulo"
        cep = "01234-567"

    result = extract_address_fields(Cliente())

    assert result["endereco"] == "Rua Teste, 123"
    assert result["bairro"] == "Centro"


def test_extract_address_fields_empty() -> None:
    """Testa extração de campos de endereço de objeto vazio."""
    result = extract_address_fields(None)

    assert result["endereco"] == ""
    assert result["bairro"] == ""
    assert result["cidade"] == ""
    assert result["cep"] == ""
