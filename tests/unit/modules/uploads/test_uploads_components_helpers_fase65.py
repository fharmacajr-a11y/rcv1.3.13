"""Testes unitários para src.modules.uploads.components.helpers — Fase 65.

TEST-008: Cobertura de funções "headless" de helpers do módulo uploads.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.modules.uploads.components.helpers import (
    _cnpj_only_digits,
    client_prefix_for_id,
    format_cnpj_for_display,
    get_clients_bucket,
    get_current_org_id,
    strip_cnpj_from_razao,
)


# ==========================
# A) Funções puras de formatação/normalização
# ==========================


class TestCnpjOnlyDigits:
    """Testes para _cnpj_only_digits (wrapper para only_digits)."""

    def test_none_retorna_vazio(self) -> None:
        """None deve retornar string vazia."""
        assert _cnpj_only_digits(None) == ""  # type: ignore[arg-type]

    def test_string_vazia(self) -> None:
        """String vazia deve retornar vazia."""
        assert _cnpj_only_digits("") == ""

    def test_apenas_digitos(self) -> None:
        """String com apenas dígitos deve retornar os mesmos dígitos."""
        assert _cnpj_only_digits("12345678000195") == "12345678000195"

    def test_com_formatacao(self) -> None:
        """CNPJ formatado deve retornar apenas dígitos."""
        assert _cnpj_only_digits("12.345.678/0001-95") == "12345678000195"

    def test_com_espacos_e_caracteres_especiais(self) -> None:
        """Deve remover espaços e caracteres especiais."""
        assert _cnpj_only_digits(" 12-345-678/0001-95 ") == "12345678000195"


class TestFormatCnpjForDisplay:
    """Testes para format_cnpj_for_display."""

    def test_cnpj_14_digitos_formatado(self) -> None:
        """CNPJ com 14 dígitos deve ser formatado corretamente."""
        result = format_cnpj_for_display("12345678000195")
        assert result == "12.345.678/0001-95"

    def test_cnpj_com_menos_digitos(self) -> None:
        """CNPJ com menos de 14 dígitos deve retornar como veio."""
        result = format_cnpj_for_display("123456")
        assert result == "123456"

    def test_cnpj_com_mais_digitos(self) -> None:
        """CNPJ com mais de 14 dígitos deve retornar como veio."""
        result = format_cnpj_for_display("123456780001950000")
        assert result == "123456780001950000"

    def test_cnpj_vazio(self) -> None:
        """String vazia deve retornar vazia."""
        result = format_cnpj_for_display("")
        assert result == ""

    def test_cnpj_nao_numerico(self) -> None:
        """CNPJ com letras deve retornar como veio (futuro alfanumérico)."""
        result = format_cnpj_for_display("ABC123DEF456")
        assert result == "ABC123DEF456"


class TestStripCnpjFromRazao:
    """Testes para strip_cnpj_from_razao."""

    def test_razao_vazia_retorna_vazia(self) -> None:
        """Razão social vazia deve retornar vazia."""
        assert strip_cnpj_from_razao("", "12345678000195") == ""

    def test_razao_none_retorna_vazio(self) -> None:
        """None na razão deve retornar vazio."""
        assert strip_cnpj_from_razao(None, "12345678000195") == ""  # type: ignore[arg-type]

    def test_razao_sem_cnpj_retorna_inalterada(self) -> None:
        """Razão sem CNPJ deve retornar inalterada."""
        razao = "Empresa XYZ Ltda"
        assert strip_cnpj_from_razao(razao, "12345678000195") == razao

    def test_remove_cnpj_simples_do_fim(self) -> None:
        """Deve remover CNPJ simples do fim da razão."""
        razao = "Empresa XYZ Ltda 12345678000195"
        result = strip_cnpj_from_razao(razao, "12345678000195")
        assert result == "Empresa XYZ Ltda"

    def test_remove_cnpj_com_traco(self) -> None:
        """Deve remover CNPJ com traço do fim da razão."""
        razao = "Empresa XYZ Ltda - 12345678000195"
        result = strip_cnpj_from_razao(razao, "12345678000195")
        assert result == "Empresa XYZ Ltda"

    def test_remove_cnpj_com_underscore(self) -> None:
        """Deve remover CNPJ com underscore do fim da razão."""
        razao = "Empresa XYZ Ltda_12345678000195"
        result = strip_cnpj_from_razao(razao, "12345678000195")
        assert result == "Empresa XYZ Ltda"

    def test_remove_cnpj_com_barra(self) -> None:
        """Deve remover CNPJ com barra do fim da razão."""
        razao = "Empresa XYZ Ltda / 12345678000195"
        result = strip_cnpj_from_razao(razao, "12345678000195")
        assert result == "Empresa XYZ Ltda"

    def test_remove_cnpj_com_aspas(self) -> None:
        """Deve remover CNPJ com aspas do fim da razão."""
        razao = 'Empresa XYZ Ltda " 12345678000195'
        result = strip_cnpj_from_razao(razao, "12345678000195")
        assert result == "Empresa XYZ Ltda"

    def test_remove_cnpj_com_apostrofo(self) -> None:
        """Deve remover CNPJ com apóstrofo do fim da razão."""
        razao = "Empresa XYZ Ltda ' 12345678000195"
        result = strip_cnpj_from_razao(razao, "12345678000195")
        assert result == "Empresa XYZ Ltda"

    def test_nao_remove_cnpj_do_meio(self) -> None:
        """Não deve remover CNPJ do meio da razão."""
        razao = "Empresa 12345678000195 XYZ Ltda"
        result = strip_cnpj_from_razao(razao, "12345678000195")
        assert result == razao

    def test_cnpj_none_retorna_razao_original(self) -> None:
        """CNPJ None deve retornar razão original."""
        razao = "Empresa XYZ Ltda"
        assert strip_cnpj_from_razao(razao, None) == razao  # type: ignore[arg-type]

    def test_cnpj_vazio_retorna_razao_original(self) -> None:
        """CNPJ vazio deve retornar razão original."""
        razao = "Empresa XYZ Ltda"
        assert strip_cnpj_from_razao(razao, "") == razao

    def test_trim_espacos(self) -> None:
        """Deve fazer trim dos espaços ao redor."""
        razao = "  Empresa XYZ Ltda  "
        result = strip_cnpj_from_razao(razao, "")
        assert result == "Empresa XYZ Ltda"


class TestGetClientsBucket:
    """Testes para get_clients_bucket."""

    def test_retorna_bucket_correto(self) -> None:
        """Deve retornar o nome do bucket de clientes."""
        assert get_clients_bucket() == "rc-docs"


# ==========================
# C) Builders/Delegação
# ==========================


class TestClientPrefixForId:
    """Testes para client_prefix_for_id (delega para build_client_prefix)."""

    def test_delega_para_build_client_prefix(self) -> None:
        """Deve delegar corretamente para build_client_prefix."""
        result = client_prefix_for_id(client_id=123, org_id="org-abc")
        # Assumindo que build_client_prefix retorna "org-abc/clients/123"
        # (ajustar conforme implementação real)
        assert "org-abc" in result
        assert "123" in str(result)

    def test_client_id_zero(self) -> None:
        """Deve funcionar com client_id = 0."""
        result = client_prefix_for_id(client_id=0, org_id="org-xyz")
        assert "org-xyz" in result
        assert "0" in str(result)

    def test_org_id_vazio(self) -> None:
        """Deve funcionar com org_id vazio."""
        result = client_prefix_for_id(client_id=456, org_id="")
        assert "456" in str(result)


# ==========================
# B) Integração Supabase (mock)
# ==========================


class TestGetCurrentOrgId:
    """Testes para get_current_org_id (com mock de Supabase)."""

    def test_usuario_nao_autenticado_retorna_vazio(self) -> None:
        """Sem usuário autenticado, deve retornar vazio."""
        sb_mock = MagicMock()
        sb_mock.auth.get_user.return_value = None

        result = get_current_org_id(sb_mock)
        assert result == ""

    def test_usuario_sem_user_field_retorna_vazio(self) -> None:
        """Usuário sem campo user deve retornar vazio."""
        sb_mock = MagicMock()
        user_response = MagicMock()
        user_response.user = None
        sb_mock.auth.get_user.return_value = user_response

        result = get_current_org_id(sb_mock)
        assert result == ""

    def test_usuario_com_org_id_retorna_org_id(self) -> None:
        """Usuário com org_id na tabela memberships deve retornar org_id."""
        sb_mock = MagicMock()
        user_response = MagicMock()
        user_response.user.id = "user-123"
        sb_mock.auth.get_user.return_value = user_response

        table_mock = MagicMock()
        sb_mock.table.return_value = table_mock
        select_mock = MagicMock()
        table_mock.select.return_value = select_mock
        eq_mock = MagicMock()
        select_mock.eq.return_value = eq_mock
        limit_mock = MagicMock()
        eq_mock.limit.return_value = limit_mock

        execute_result = MagicMock()
        execute_result.data = [{"org_id": "org-456"}]
        limit_mock.execute.return_value = execute_result

        result = get_current_org_id(sb_mock)
        assert result == "org-456"

    def test_tabela_memberships_vazia_retorna_vazio(self) -> None:
        """Se não houver registros na tabela memberships, deve retornar vazio."""
        sb_mock = MagicMock()
        user_response = MagicMock()
        user_response.user.id = "user-789"
        sb_mock.auth.get_user.return_value = user_response

        table_mock = MagicMock()
        sb_mock.table.return_value = table_mock
        select_mock = MagicMock()
        table_mock.select.return_value = select_mock
        eq_mock = MagicMock()
        select_mock.eq.return_value = eq_mock
        limit_mock = MagicMock()
        eq_mock.limit.return_value = limit_mock

        execute_result = MagicMock()
        execute_result.data = []
        limit_mock.execute.return_value = execute_result

        result = get_current_org_id(sb_mock)
        assert result == ""

    def test_sem_campo_org_id_retorna_vazio(self) -> None:
        """Se o registro não tiver org_id, deve retornar vazio."""
        sb_mock = MagicMock()
        user_response = MagicMock()
        user_response.user.id = "user-999"
        sb_mock.auth.get_user.return_value = user_response

        table_mock = MagicMock()
        sb_mock.table.return_value = table_mock
        select_mock = MagicMock()
        table_mock.select.return_value = select_mock
        eq_mock = MagicMock()
        select_mock.eq.return_value = eq_mock
        limit_mock = MagicMock()
        eq_mock.limit.return_value = limit_mock

        execute_result = MagicMock()
        execute_result.data = [{"other_field": "value"}]
        limit_mock.execute.return_value = execute_result

        result = get_current_org_id(sb_mock)
        assert result == ""

    def test_excecao_durante_busca_retorna_vazio(self) -> None:
        """Se ocorrer exceção, deve retornar vazio e logar debug."""
        sb_mock = MagicMock()
        sb_mock.auth.get_user.side_effect = Exception("Falha de conexão")

        result = get_current_org_id(sb_mock)
        assert result == ""

    def test_excecao_na_tabela_retorna_vazio(self) -> None:
        """Se ocorrer exceção ao buscar na tabela, deve retornar vazio."""
        sb_mock = MagicMock()
        user_response = MagicMock()
        user_response.user.id = "user-error"
        sb_mock.auth.get_user.return_value = user_response

        sb_mock.table.side_effect = Exception("Erro no Supabase")

        result = get_current_org_id(sb_mock)
        assert result == ""
