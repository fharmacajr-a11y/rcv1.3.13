# -*- coding: utf-8 -*-
"""Testes para ordenação por última alteração com timestamp.

Verifica que a ordenação por "Última Alteração (mais recente)"
usa o timestamp real ao invés da string formatada.
"""

from __future__ import annotations

from datetime import datetime, timedelta


from src.modules.clientes.viewmodel import ClienteRow
from src.modules.clientes.views.main_screen_controller import (
    FilterOrderInput,
    compute_filtered_and_ordered,
)
from src.modules.clientes.views.main_screen_helpers import (
    ORDER_LABEL_UPDATED_OLD,
    ORDER_LABEL_UPDATED_RECENT,
)


class TestOrderByUltimaAlteracao:
    """Testes para ordenação por última alteração usando timestamp."""

    def test_order_by_updated_recent_uses_timestamp(self) -> None:
        """Testa que "mais recente" ordena corretamente usando timestamp."""
        # Criar datas de teste
        hoje = datetime.now()
        ontem = hoje - timedelta(days=1)
        mes_passado = hoje - timedelta(days=30)

        # Criar clientes com timestamps diferentes
        clientes = [
            ClienteRow(
                id="1",
                razao_social="Cliente A",
                cnpj="11111111000111",
                nome="A",
                whatsapp="",
                observacoes="",
                status="",
                ultima_alteracao="01/11/2024 - 10:00:00 (J)",  # String formatada (mês passado)
                search_norm="cliente a",
                ultima_alteracao_ts=mes_passado,  # Timestamp real
            ),
            ClienteRow(
                id="2",
                razao_social="Cliente B",
                cnpj="22222222000122",
                nome="B",
                whatsapp="",
                observacoes="",
                status="",
                ultima_alteracao="06/12/2024 - 15:30:00 (J)",  # String formatada (ontem)
                search_norm="cliente b",
                ultima_alteracao_ts=ontem,  # Timestamp real
            ),
            ClienteRow(
                id="3",
                razao_social="Cliente C",
                cnpj="33333333000133",
                nome="C",
                whatsapp="",
                observacoes="",
                status="",
                ultima_alteracao="07/12/2024 - 11:37:10 (J)",  # String formatada (hoje)
                search_norm="cliente c",
                ultima_alteracao_ts=hoje,  # Timestamp real
            ),
        ]

        # Ordenar por "mais recente"
        inp = FilterOrderInput(
            raw_clients=clientes,
            order_label=ORDER_LABEL_UPDATED_RECENT,
            filter_label="Todos",
            search_text="",
            selected_ids=[],
            is_trash_screen=False,
            is_online=True,
        )
        resultado = compute_filtered_and_ordered(inp)

        # Deve vir na ordem: hoje, ontem, mês passado
        assert resultado.visible_clients[0].id == "3", "Cliente mais recente deve vir primeiro"
        assert resultado.visible_clients[1].id == "2", "Cliente de ontem deve vir no meio"
        assert resultado.visible_clients[2].id == "1", "Cliente de mês passado deve vir por último"

    def test_order_by_updated_old_uses_timestamp(self) -> None:
        """Testa que "mais antiga" ordena corretamente usando timestamp."""
        hoje = datetime.now()
        ontem = hoje - timedelta(days=1)
        mes_passado = hoje - timedelta(days=30)

        clientes = [
            ClienteRow(
                id="1",
                razao_social="Cliente A",
                cnpj="11111111000111",
                nome="A",
                whatsapp="",
                observacoes="",
                status="",
                ultima_alteracao="07/12/2024 - 11:37:10 (J)",
                search_norm="cliente a",
                ultima_alteracao_ts=hoje,
            ),
            ClienteRow(
                id="2",
                razao_social="Cliente B",
                cnpj="22222222000122",
                nome="B",
                whatsapp="",
                observacoes="",
                status="",
                ultima_alteracao="01/11/2024 - 10:00:00 (J)",
                search_norm="cliente b",
                ultima_alteracao_ts=mes_passado,
            ),
            ClienteRow(
                id="3",
                razao_social="Cliente C",
                cnpj="33333333000133",
                nome="C",
                whatsapp="",
                observacoes="",
                status="",
                ultima_alteracao="06/12/2024 - 15:30:00 (J)",
                search_norm="cliente c",
                ultima_alteracao_ts=ontem,
            ),
        ]

        # Ordenar por "mais antiga"
        inp = FilterOrderInput(
            raw_clients=clientes,
            order_label=ORDER_LABEL_UPDATED_OLD,
            filter_label="Todos",
            search_text="",
            selected_ids=[],
            is_trash_screen=False,
            is_online=True,
        )
        resultado = compute_filtered_and_ordered(inp)

        # Deve vir na ordem: mês passado, ontem, hoje
        assert resultado.visible_clients[0].id == "2", "Cliente mais antigo deve vir primeiro"
        assert resultado.visible_clients[1].id == "3", "Cliente de ontem deve vir no meio"
        assert resultado.visible_clients[2].id == "1", "Cliente mais recente deve vir por último"

    def test_order_by_updated_handles_none_timestamps(self) -> None:
        """Testa que clientes sem timestamp vão para o final."""
        hoje = datetime.now()

        clientes = [
            ClienteRow(
                id="1",
                razao_social="Cliente A",
                cnpj="11111111000111",
                nome="A",
                whatsapp="",
                observacoes="",
                status="",
                ultima_alteracao="",
                search_norm="cliente a",
                ultima_alteracao_ts=None,  # Sem data
            ),
            ClienteRow(
                id="2",
                razao_social="Cliente B",
                cnpj="22222222000122",
                nome="B",
                whatsapp="",
                observacoes="",
                status="",
                ultima_alteracao="07/12/2024 - 11:37:10 (J)",
                search_norm="cliente b",
                ultima_alteracao_ts=hoje,
            ),
            ClienteRow(
                id="3",
                razao_social="Cliente C",
                cnpj="33333333000133",
                nome="C",
                whatsapp="",
                observacoes="",
                status="",
                ultima_alteracao="",
                search_norm="cliente c",
                ultima_alteracao_ts=None,  # Sem data
            ),
        ]

        # Ordenar por "mais recente"
        inp = FilterOrderInput(
            raw_clients=clientes,
            order_label=ORDER_LABEL_UPDATED_RECENT,
            filter_label="Todos",
            search_text="",
            selected_ids=[],
            is_trash_screen=False,
            is_online=True,
        )
        resultado = compute_filtered_and_ordered(inp)

        # Cliente com data deve vir primeiro
        assert resultado.visible_clients[0].id == "2", "Cliente com data deve vir primeiro"
        # Clientes sem data ficam no final (ordem original preservada)
        assert resultado.visible_clients[1].id in ["1", "3"], "Clientes sem data devem vir no final"
        assert resultado.visible_clients[2].id in ["1", "3"], "Clientes sem data devem vir no final"

    def test_order_by_updated_handles_string_timestamps(self) -> None:
        """Testa que timestamps em formato string ISO são parseados corretamente."""
        clientes = [
            ClienteRow(
                id="1",
                razao_social="Cliente A",
                cnpj="11111111000111",
                nome="A",
                whatsapp="",
                observacoes="",
                status="",
                ultima_alteracao="01/11/2024 - 10:00:00 (J)",
                search_norm="cliente a",
                ultima_alteracao_ts="2024-11-01T10:00:00",  # String ISO
            ),
            ClienteRow(
                id="2",
                razao_social="Cliente B",
                cnpj="22222222000122",
                nome="B",
                whatsapp="",
                observacoes="",
                status="",
                ultima_alteracao="07/12/2024 - 11:37:10 (J)",
                search_norm="cliente b",
                ultima_alteracao_ts="2024-12-07T11:37:10",  # String ISO
            ),
        ]

        # Ordenar por "mais recente"
        inp = FilterOrderInput(
            raw_clients=clientes,
            order_label=ORDER_LABEL_UPDATED_RECENT,
            filter_label="Todos",
            search_text="",
            selected_ids=[],
            is_trash_screen=False,
            is_online=True,
        )
        resultado = compute_filtered_and_ordered(inp)

        # Deve ordenar corretamente mesmo com strings ISO
        assert resultado.visible_clients[0].id == "2", "Cliente de dezembro deve vir primeiro"
        assert resultado.visible_clients[1].id == "1", "Cliente de novembro deve vir depois"
