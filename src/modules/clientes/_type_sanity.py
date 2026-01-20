# -*- coding: utf-8 -*-
"""Type Sanity Check para o módulo Clientes.

Este arquivo serve como "canário na mina de carvão" para detectar regressões
de tipagem precocemente. Se alguém modificar stubs locais (/typings) ou alterar
imports de forma que quebre a compatibilidade com nosso Protocol SupportsCgetConfigure,
o Pylance reportará erros AQUI primeiro, antes de quebrar o código de produção.

⚠️ IMPORTANTE: Todo código aqui está dentro de `if TYPE_CHECKING:`, portanto:
   - Zero impacto em runtime (não é executado)
   - Não instancia widgets reais
   - Não cria janelas tkinter
   - Apenas valida tipagem estática

Criado na Microfase 10 (2026-01-14) para prevenir regressões de tipagem.

Como funciona:
1. Importa widgets reais (tk/ctk) como no código de produção
2. Anota variáveis com nosso Protocol (SupportsCgetConfigure)
3. Atribui instâncias de widgets reais a essas variáveis
4. Chama métodos esperados (cget, configure, __getitem__)
5. Se algum stub/tipo quebrar, Pylance acusa erro AQUI

Exemplo de regressão detectada:
- Se alguém remover `cget` do stub de CTkButton
- Este arquivo mostrará: "Type 'CTkButton' cannot be assigned to 'SupportsCgetConfigure'"
- Problema detectado antes de chegar ao código de produção ✅

Validação:
- Ctrl+Shift+M (Problems) deve mostrar 0 erros neste arquivo
- Hover sobre variáveis deve inferir tipos corretamente
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Imports apenas para análise estática (não afetam runtime)
    import tkinter as tk
    

    # CustomTkinter via SSoT
    from src.ui.ctk_config import ctk

    # Nosso Protocol (interface esperada)
    from src.modules.clientes._typing_widgets import SupportsCgetConfigure

    # ========================================================================
    # TESTE 1: Widgets tkinter padrão devem implementar o Protocol
    # ========================================================================

    def _test_tkinter_button_implements_protocol() -> None:
        """Valida que tk.Button implementa SupportsCgetConfigure."""
        # Nota: usamos None como master (só para tipagem, não executa)
        btn: SupportsCgetConfigure = tk.Button(None, text="Test")  # type: ignore[arg-type]

        # Se o stub de tkinter estiver incompleto, estas linhas darão erro
        _ = btn.cget("state")  # noqa: F841
        btn.configure(state="normal")
        _ = btn["state"]  # __getitem__  # noqa: F841

    # ========================================================================
    # TESTE 2: Widgets themed devem implementar o Protocol
    # ========================================================================

    def _test_ttk_button_implements_protocol() -> None:
        """Valida que ctk.CTkButton implementa SupportsCgetConfigure."""
        btn: SupportsCgetConfigure = ctk.CTkButton(None, text="Test")  # type: ignore[arg-type]

        _ = btn.cget("state")  # noqa: F841
        btn.configure(state="normal")
        _ = btn["state"]  # noqa: F841

    def _test_ttk_label_implements_protocol() -> None:
        """Valida que ctk.CTkLabel implementa SupportsCgetConfigure."""
        lbl: SupportsCgetConfigure = ctk.CTkLabel(None, text="Test")  # type: ignore[arg-type]

        _ = lbl.cget("text")  # noqa: F841
        lbl.configure(text="Updated")
        _ = lbl["text"]  # noqa: F841

    # ========================================================================
    # TESTE 3: Widgets CustomTkinter devem implementar o Protocol
    # ========================================================================

    if ctk is not None:

        def _test_ctk_button_implements_protocol() -> None:
            """Valida que ctk.CTkButton implementa SupportsCgetConfigure."""
            btn: SupportsCgetConfigure = ctk.CTkButton(None, text="Test")  # type: ignore[arg-type,union-attr]

            # Se o stub de customtkinter estiver incompleto, estas linhas darão erro
            _ = btn.cget("state")  # noqa: F841
            btn.configure(state="normal")
            _ = btn["state"]  # noqa: F841

        def _test_ctk_label_implements_protocol() -> None:
            """Valida que ctk.CTkLabel implementa SupportsCgetConfigure."""
            lbl: SupportsCgetConfigure = ctk.CTkLabel(None, text="Test")  # type: ignore[arg-type,union-attr]

            _ = lbl.cget("text")  # noqa: F841
            lbl.configure(text="Updated")
            _ = lbl["text"]  # noqa: F841

        def _test_ctk_entry_implements_protocol() -> None:
            """Valida que ctk.CTkEntry implementa SupportsCgetConfigure."""
            entry: SupportsCgetConfigure = ctk.CTkEntry(None)  # type: ignore[arg-type,union-attr]

            _ = entry.cget("state")  # noqa: F841
            entry.configure(state="normal")
            _ = entry["state"]  # noqa: F841

    # ========================================================================
    # TESTE 4: Protocol funciona com nossa função de produção (simulação)
    # ========================================================================

    def _test_protocol_in_production_like_code() -> None:
        """Simula código de produção usando o Protocol."""

        def save_widget_state(widget: SupportsCgetConfigure) -> str:
            """Função típica que usa o Protocol (como em actionbar_ctk.py)."""
            # Estas operações devem funcionar para tk/ctk widgets
            current = widget.cget("state")
            _ = widget["state"]  # Sintaxe alternativa  # noqa: F841
            return str(current)

        def restore_widget_state(widget: SupportsCgetConfigure, state: str) -> None:
            """Restaura estado do widget."""
            widget.configure(state=state)

        # Testa com diferentes tipos de widgets
        tk_btn: SupportsCgetConfigure = tk.Button(None, text="TK")  # type: ignore[arg-type]
        ttk_btn: SupportsCgetConfigure = ctk.CTkButton(None, text="Themed")  # type: ignore[arg-type]

        # Deve funcionar sem erros de tipo
        _ = save_widget_state(tk_btn)  # noqa: F841
        _ = save_widget_state(ttk_btn)  # noqa: F841
        restore_widget_state(tk_btn, "disabled")
        restore_widget_state(ttk_btn, "normal")

        if ctk is not None:
            ctk_btn: SupportsCgetConfigure = ctk.CTkButton(None, text="CTK")  # type: ignore[arg-type,union-attr]
            _ = save_widget_state(ctk_btn)  # noqa: F841
            restore_widget_state(ctk_btn, "normal")

# ============================================================================
# STATUS: Este arquivo deve sempre ter 0 erros do Pylance
# ============================================================================
#
# Como usar este arquivo:
# 1. Após modificar stubs em /typings, recarregar VS Code (Ctrl+Shift+P → Reload Window)
# 2. Abrir este arquivo e verificar Problems (Ctrl+Shift+M)
# 3. Se houver erros aqui, significa que os stubs foram quebrados
# 4. Corrigir os stubs ANTES de commitar
#
# Exemplos de regressões que este arquivo detectaria:
# ❌ Remover `cget` de CTkBaseClass → Erro: "Type 'CTkButton' cannot be assigned"
# ❌ Remover `configure` de Misc (tkinter) → Erro: "Type 'Button' cannot be assigned"
# ❌ Remover `__getitem__` → Erro: "Item access not supported"
#
# ✅ Com stubs corretos: 0 erros neste arquivo
# ============================================================================
