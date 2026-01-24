#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Teste visual da toolbar CustomTkinter do módulo Clientes.

Abre uma janela com a toolbar isolada para testar visual e funcionalidade.

AVISO: Este script abre uma GUI. NÃO execute via pytest.
       Use: python scripts/visual/toolbar_ctk_clientes_visual.py
"""

import sys
import tkinter as tk
from pathlib import Path

# Adiciona raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """Executa teste visual da toolbar CustomTkinter."""
    try:
        from src.modules.clientes.appearance import ClientesThemeManager
        from src.modules.clientes.views.toolbar_ctk import ClientesToolbarCtk, HAS_CUSTOMTKINTER

        if not HAS_CUSTOMTKINTER:
            print("⚠ CustomTkinter não disponível. Instale com:")
            print("  pip install customtkinter")
            sys.exit(1)

        print("✓ Imports bem-sucedidos")

        # Cria theme manager
        theme_manager = ClientesThemeManager()
        mode = theme_manager.load_mode()
        print(f"✓ Theme manager criado, modo: {mode}")

        # Cria janela
        root = tk.Tk()
        root.title("Teste Visual - Toolbar CustomTkinter")
        root.geometry("1200x150")

        # Callbacks de teste
        def on_search(text):
            print(f"🔍 Buscar: '{text}'")

        def on_clear():
            print("✖ Limpar busca")

        def on_order(order):
            print(f"📊 Ordenar por: {order}")

        def on_status(status):
            print(f"📌 Status: {status}")

        def on_trash():
            print("🗑️ Abrir lixeira")

        # Cria toolbar
        toolbar = ClientesToolbarCtk(
            root,
            order_choices=["Nome", "ID", "CNPJ", "Razão Social", "Última Alteração"],
            default_order="Nome",
            status_choices=["Todos", "Ativo", "Inativo", "Pendente"],
            on_search_changed=on_search,
            on_clear_search=on_clear,
            on_order_changed=on_order,
            on_status_changed=on_status,
            on_open_trash=on_trash,
            theme_manager=theme_manager,
        )
        toolbar.pack(fill="both", expand=True)

        print("\n" + "=" * 70)
        print("Janela de teste aberta. Teste a toolbar:")
        print("- Digite no campo de pesquisa e pressione Enter")
        print("- Clique nos botões Buscar/Limpar")
        print("- Mude as opções de Ordenar e Status")
        print("- Clique no botão Lixeira")
        print("- Observe o visual moderno (cantos arredondados, cores)")
        print("=" * 70 + "\n")

        root.mainloop()

        print("\n✓ Teste visual concluído!")

    except ImportError as e:
        print(f"✗ Erro de import: {e}")
        print("\nInstale as dependências:")
        print("  pip install customtkinter ttkbootstrap")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Erro: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
