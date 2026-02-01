"""Testes unitários para main_screen_helpers do módulo clientes.

REFACTOR-UI-002 - Fase 01
"""

from __future__ import annotations

from datetime import date


from src.modules.clientes.core.ui_helpers import (
    calculate_button_states,
    calculate_new_clients_stats,
    extract_created_at_from_client,
    format_clients_summary,
    parse_created_at_date,
)


class TestCalculateButtonStates:
    """Testes para cálculo de estados de botões."""

    def test_all_enabled_when_online_with_selection(self):
        """Deve habilitar botões dependentes quando online e com seleção."""
        states = calculate_button_states(
            has_selection=True,
            is_online=True,
            is_uploading=False,
        )
        assert states["editar"] is True
        assert states["subpastas"] is True
        assert states["enviar"] is True
        assert states["novo"] is True
        assert states["lixeira"] is True
        assert states["select"] is False  # não está em pick_mode

    def test_no_selection_disables_selection_dependent_buttons(self):
        """Deve desabilitar botões que dependem de seleção."""
        states = calculate_button_states(
            has_selection=False,
            is_online=True,
            is_uploading=False,
        )
        assert states["editar"] is False
        assert states["subpastas"] is False
        assert states["enviar"] is False
        assert states["novo"] is True  # não depende de seleção
        assert states["lixeira"] is True  # não depende de seleção

    def test_offline_disables_all_network_buttons(self):
        """Deve desabilitar todos os botões quando offline."""
        states = calculate_button_states(
            has_selection=True,
            is_online=False,
            is_uploading=False,
        )
        assert states["editar"] is False
        assert states["subpastas"] is False
        assert states["enviar"] is False
        assert states["novo"] is False
        assert states["lixeira"] is False

    def test_uploading_disables_enviar(self):
        """Deve desabilitar botão enviar durante upload."""
        states = calculate_button_states(
            has_selection=True,
            is_online=True,
            is_uploading=True,
        )
        assert states["enviar"] is False
        assert states["editar"] is True  # outros não afetados

    def test_pick_mode_enables_select_button(self):
        """Deve habilitar botão select em modo pick com seleção."""
        states = calculate_button_states(
            has_selection=True,
            is_online=True,
            is_uploading=False,
            is_pick_mode=True,
        )
        assert states["select"] is True

    def test_pick_mode_without_selection(self):
        """Deve desabilitar select sem seleção mesmo em pick_mode."""
        states = calculate_button_states(
            has_selection=False,
            is_online=True,
            is_uploading=False,
            is_pick_mode=True,
        )
        assert states["select"] is False

    def test_all_false_conditions(self):
        """Deve desabilitar tudo quando todas flags são False."""
        states = calculate_button_states(
            has_selection=False,
            is_online=False,
            is_uploading=True,
            is_pick_mode=False,
        )
        assert all(not v for v in states.values())


class TestParseCreatedAtDate:
    """Testes para parsing de datas ISO."""

    def test_valid_iso_datetime(self):
        """Deve parsear datetime ISO válido."""
        result = parse_created_at_date("2025-11-28T15:30:00")
        assert result == date(2025, 11, 28)

    def test_valid_iso_datetime_with_tz(self):
        """Deve parsear datetime com timezone."""
        result = parse_created_at_date("2025-11-28T15:30:00+00:00")
        assert result == date(2025, 11, 28)

    def test_none_input(self):
        """Deve retornar None para input None."""
        result = parse_created_at_date(None)
        assert result is None

    def test_empty_string(self):
        """Deve retornar None para string vazia."""
        result = parse_created_at_date("")
        assert result is None

    def test_invalid_format(self):
        """Deve retornar None para formato inválido."""
        result = parse_created_at_date("invalid-date")
        assert result is None

    def test_partial_date(self):
        """Deve parsear data sem hora."""
        result = parse_created_at_date("2025-11-28")
        assert result == date(2025, 11, 28)


class TestExtractCreatedAtFromClient:
    """Testes para extração de created_at de objetos cliente."""

    def test_dict_with_created_at(self):
        """Deve extrair de dict com chave created_at."""
        client = {"created_at": "2025-11-28T10:00:00", "nome": "Test"}
        result = extract_created_at_from_client(client)
        assert result == "2025-11-28T10:00:00"

    def test_dict_without_created_at(self):
        """Deve retornar None se dict não tem created_at."""
        client = {"nome": "Test"}
        result = extract_created_at_from_client(client)
        assert result is None

    def test_object_with_attribute(self):
        """Deve extrair de objeto com atributo created_at."""

        class Cliente:
            created_at = "2025-11-28T10:00:00"

        result = extract_created_at_from_client(Cliente())
        assert result == "2025-11-28T10:00:00"

    def test_object_without_attribute(self):
        """Deve retornar None se objeto não tem atributo."""

        class Cliente:
            nome = "Test"

        result = extract_created_at_from_client(Cliente())
        assert result is None

    def test_dict_like_object(self):
        """Deve tentar dict.get se objeto tem método get."""

        class DictLike:
            def get(self, key, default=None):
                return "2025-11-28T10:00:00" if key == "created_at" else default

        result = extract_created_at_from_client(DictLike())
        assert result == "2025-11-28T10:00:00"


class TestCalculateNewClientsStats:
    """Testes para cálculo de estatísticas de novos clientes."""

    def test_empty_list(self):
        """Deve retornar zeros para lista vazia."""
        today = date(2025, 11, 28)
        new_today, new_month = calculate_new_clients_stats([], today)
        assert new_today == 0
        assert new_month == 0

    def test_clients_created_today(self):
        """Deve contar clientes criados hoje."""
        clients = [
            {"created_at": "2025-11-28T10:00:00"},
            {"created_at": "2025-11-28T15:00:00"},
            {"created_at": "2025-11-27T10:00:00"},
        ]
        today = date(2025, 11, 28)
        new_today, new_month = calculate_new_clients_stats(clients, today)
        assert new_today == 2
        assert new_month == 3  # todos de novembro

    def test_clients_created_this_month(self):
        """Deve contar clientes criados no mês atual."""
        clients = [
            {"created_at": "2025-11-28T10:00:00"},
            {"created_at": "2025-11-15T10:00:00"},
            {"created_at": "2025-11-01T10:00:00"},
            {"created_at": "2025-10-28T10:00:00"},
        ]
        today = date(2025, 11, 28)
        new_today, new_month = calculate_new_clients_stats(clients, today)
        assert new_today == 1
        assert new_month == 3

    def test_clients_with_no_created_at(self):
        """Deve ignorar clientes sem created_at."""
        clients = [
            {"created_at": "2025-11-28T10:00:00"},
            {"nome": "Cliente sem data"},
            {"created_at": None},
        ]
        today = date(2025, 11, 28)
        new_today, new_month = calculate_new_clients_stats(clients, today)
        assert new_today == 1
        assert new_month == 1

    def test_clients_with_invalid_dates(self):
        """Deve ignorar datas inválidas."""
        clients = [
            {"created_at": "2025-11-28T10:00:00"},
            {"created_at": "invalid-date"},
            {"created_at": ""},
        ]
        today = date(2025, 11, 28)
        new_today, new_month = calculate_new_clients_stats(clients, today)
        assert new_today == 1
        assert new_month == 1

    def test_first_day_of_month(self):
        """Deve funcionar corretamente no primeiro dia do mês."""
        clients = [
            {"created_at": "2025-12-01T10:00:00"},
            {"created_at": "2025-11-30T10:00:00"},
        ]
        today = date(2025, 12, 1)
        new_today, new_month = calculate_new_clients_stats(clients, today)
        assert new_today == 1
        assert new_month == 1  # só o de dezembro

    def test_mixed_object_and_dict_clients(self):
        """Deve funcionar com mix de objetos e dicts."""

        class Cliente:
            def __init__(self, created_at):
                self.created_at = created_at

        clients = [
            Cliente("2025-11-28T10:00:00"),
            {"created_at": "2025-11-28T15:00:00"},
        ]
        today = date(2025, 11, 28)
        new_today, new_month = calculate_new_clients_stats(clients, today)
        assert new_today == 2
        assert new_month == 2


class TestFormatClientsSummary:
    """Testes para formatação de resumo de clientes."""

    def test_zero_clients(self):
        """Deve formatar zero clientes."""
        result = format_clients_summary(0, 0, 0)
        assert result == "0 clientes"

    def test_one_client(self):
        """Deve usar singular para 1 cliente."""
        result = format_clients_summary(1, 0, 0)
        assert result == "1 cliente"

    def test_multiple_clients_no_new(self):
        """Deve formatar múltiplos clientes sem novos."""
        result = format_clients_summary(100, 0, 0)
        assert result == "100 clientes"

    def test_with_new_today(self):
        """Deve incluir novos hoje."""
        result = format_clients_summary(100, 5, 20)
        assert result == "100 clientes (5 hoje, 20 este mês)"

    def test_only_new_today(self):
        """Deve mostrar parênteses mesmo se só houver novos hoje."""
        result = format_clients_summary(100, 5, 5)
        assert result == "100 clientes (5 hoje, 5 este mês)"

    def test_only_new_month(self):
        """Deve mostrar parênteses se houver novos no mês."""
        result = format_clients_summary(100, 0, 10)
        assert result == "100 clientes (0 hoje, 10 este mês)"


class TestIntegrationScenarios:
    """Testes de integração simulando fluxos reais."""

    def test_button_workflow_normal_usage(self):
        """Simula uso normal com cliente selecionado e online."""
        states = calculate_button_states(
            has_selection=True,
            is_online=True,
            is_uploading=False,
        )
        # Todos botões principais devem estar habilitados
        assert states["editar"]
        assert states["enviar"]
        assert states["novo"]

    def test_button_workflow_offline(self):
        """Simula perda de conexão."""
        states = calculate_button_states(
            has_selection=True,
            is_online=False,
            is_uploading=False,
        )
        # Nenhum botão deve estar habilitado
        assert not states["editar"]
        assert not states["enviar"]
        assert not states["novo"]

    def test_stats_calculation_workflow(self):
        """Simula cálculo completo de estatísticas."""
        clients = [
            {"created_at": "2025-11-28T10:00:00", "nome": "Cliente 1"},
            {"created_at": "2025-11-28T15:00:00", "nome": "Cliente 2"},
            {"created_at": "2025-11-15T10:00:00", "nome": "Cliente 3"},
            {"created_at": "2025-10-28T10:00:00", "nome": "Cliente 4"},
        ]
        today = date(2025, 11, 28)

        # Calcula stats
        new_today, new_month = calculate_new_clients_stats(clients, today)
        assert new_today == 2
        assert new_month == 3

        # Formata resumo
        summary = format_clients_summary(len(clients), new_today, new_month)
        assert "4 clientes" in summary
        assert "2 hoje" in summary
        assert "3 este mês" in summary

    def test_pick_mode_workflow(self):
        """Simula modo de seleção (pick) para integração com Senhas."""
        # Usuário entra em modo pick e seleciona cliente
        states = calculate_button_states(
            has_selection=True,
            is_online=True,
            is_uploading=False,
            is_pick_mode=True,
        )
        assert states["select"] is True

        # Usuário remove seleção
        states = calculate_button_states(
            has_selection=False,
            is_online=True,
            is_uploading=False,
            is_pick_mode=True,
        )
        assert states["select"] is False
