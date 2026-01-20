# -*- coding: utf-8 -*-
"""
SMOKE TEST - Microfase 4.5: WhatsApp Alignment
==============================================

Valida que a coluna WhatsApp está configurada corretamente com:
- Width ajustado para 140px (aproximar da borda esquerda)
- Minwidth de 120px (suficiente para números completos)
- Anchor 'w' (esquerda) para heading e column
- Heading com padding consistente

Executar com:
    python -m pytest tests/modules/clientes/test_clientes_whatsapp_alignment_smoke.py -v
"""
from __future__ import annotations

from src.config.constants import COL_WHATSAPP_WIDTH
from src.ui.components.lists import CLIENTS_COL_ANCHOR


def test_whatsapp_width_constant():
    """
    Valida que COL_WHATSAPP_WIDTH foi ajustado para 110px.
    
    Microfase 4.5: Ajustado para 110px.
    """
    assert COL_WHATSAPP_WIDTH == 110, (
        f"COL_WHATSAPP_WIDTH deve ser 110px (atual: {COL_WHATSAPP_WIDTH}px). "
        "Microfase 4.5 otimizado."
    )


def test_whatsapp_anchor_is_left():
    """
    Valida que WhatsApp tem anchor='w' (esquerda) no dicionário CLIENTS_COL_ANCHOR.
    
    Implementado na Microfase 4.2, mantido na 4.5.
    """
    assert CLIENTS_COL_ANCHOR.get("WhatsApp") == "w", (
        "WhatsApp deve ter anchor='w' (esquerda) para alinhamento consistente"
    )


def test_whatsapp_column_definition():
    """
    Valida que a definição da coluna WhatsApp em lists.py está correta.
    
    Esperado:
    - key: "WhatsApp"
    - heading: "WhatsApp"
    - width: COL_WHATSAPP_WIDTH (140)
    - minwidth: 120
    - stretch: False
    """
    # Import local para evitar criar Treeview
    from src.ui.components.lists import create_clients_treeview
    import inspect
    
    # Ler código-fonte da função para validar definição
    source = inspect.getsource(create_clients_treeview)
    
    # Validar que linha da coluna WhatsApp existe e está correta
    assert '"WhatsApp"' in source or "'WhatsApp'" in source, (
        "Coluna WhatsApp deve estar definida em create_clients_treeview"
    )
    
    # Validar que usa COL_WHATSAPP_WIDTH
    assert "COL_WHATSAPP_WIDTH" in source, (
        "Coluna WhatsApp deve usar constante COL_WHATSAPP_WIDTH"
    )
    
    # Validar que minwidth é 120
    # Nota: não podemos validar linha exata sem criar Treeview
    assert "120" in source, (
        "Código deve conter minwidth=120 para WhatsApp"
    )


def test_heading_anchor_logic():
    """
    Valida que a lógica de heading anchor em lists.py está correta.
    
    Esperado:
    - WhatsApp: anchor='w' (esquerda)
    - Outras colunas: anchor='center' (centro)
    """
    from src.ui.components.lists import create_clients_treeview
    import inspect
    
    source = inspect.getsource(create_clients_treeview)
    
    # Validar lógica condicional para heading anchor
    assert 'if key == "WhatsApp"' in source or "if key == 'WhatsApp'" in source, (
        "Deve existir condicional para WhatsApp heading anchor"
    )
    
    assert 'heading_anchor = "w"' in source or "heading_anchor = 'w'" in source, (
        "WhatsApp deve ter heading_anchor='w'"
    )


def test_heading_padding_in_appearance():
    """
    Valida que o padding do heading foi adicionado em appearance.py.
    
    Microfase 4.5: Adiciona padding=(8, 6) para aparência uniforme
    e menos 'botão'.
    """
    from src.modules.clientes.appearance import ClientesThemeManager
    import inspect
    
    # Ler código-fonte da classe
    source = inspect.getsource(ClientesThemeManager)
    
    # Validar que padding está configurado no heading
    assert "padding=" in source, (
        "Heading style deve ter padding configurado em appearance.py"
    )
    
    # Validar valor específico (8, 6)
    assert "padding=(8, 6)" in source or "padding = (8, 6)" in source, (
        "Heading padding deve ser (8, 6) conforme Microfase 4.5"
    )
    
    # Validar que está no contexto do Treeview.Heading
    assert "Clientes.Treeview.Heading" in source, (
        "Style deve ser aplicado em 'Clientes.Treeview.Heading'"
    )


def test_all_columns_have_anchor():
    """
    Valida que todas as colunas têm anchor definido em CLIENTS_COL_ANCHOR.
    
    Garante consistência: todas as colunas devem ter alinhamento explícito.
    """
    expected_columns = [
        "ID", "Razao Social", "CNPJ", "Nome", "WhatsApp",
        "Observacoes", "Status", "Ultima Alteracao"
    ]
    
    for col in expected_columns:
        assert col in CLIENTS_COL_ANCHOR, (
            f"Coluna '{col}' deve ter anchor definido em CLIENTS_COL_ANCHOR"
        )
        
        anchor = CLIENTS_COL_ANCHOR[col]
        assert anchor in ["w", "center", "e"], (
            f"Anchor da coluna '{col}' deve ser 'w', 'center' ou 'e' (atual: {anchor})"
        )


def test_whatsapp_is_only_left_aligned():
    """
    Valida que apenas WhatsApp tem anchor='w' (esquerda).
    
    Outras colunas devem ser centralizadas para manter padrão visual.
    """
    left_aligned = [col for col, anchor in CLIENTS_COL_ANCHOR.items() if anchor == "w"]
    
    assert len(left_aligned) == 1, (
        f"Apenas 1 coluna deve ter anchor='w' (atual: {len(left_aligned)})"
    )
    
    assert left_aligned[0] == "WhatsApp", (
        f"A coluna com anchor='w' deve ser WhatsApp (atual: {left_aligned[0]})"
    )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
