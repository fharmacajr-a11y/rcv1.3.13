#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Teste manual do toggle de tema no módulo Clientes.

Este script simula a criação do ClientesFrame para verificar que o toggle
aparece corretamente e não quebra com TclError.

AVISO: Este script abre uma GUI. NÃO execute via pytest.
       Use: python scripts/visual/toggle_theme_clientes.py
"""

import sys
from pathlib import Path

# Adiciona raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """Executa teste do toggle de tema."""
    try:
        import ttkbootstrap as tb
        from src.modules.clientes.view import ClientesFrame

        print("✓ Imports bem-sucedidos")

        # Cria janela de teste
        root = tb.Window(themename="litera")
        root.title("Teste Toggle Tema - Módulo Clientes")
        root.geometry("1000x600")

        print("✓ Janela criada")

        # Callbacks mock (para não precisar de todo o app)
        def mock_callback():
            print("  Mock callback chamado")

        # Cria ClientesFrame
        print("✓ Criando ClientesFrame...")
        try:
            frame = ClientesFrame(
                root,
                on_new=mock_callback,
                on_edit=mock_callback,
                on_delete=mock_callback,
                on_upload=mock_callback,
                on_open_subpastas=mock_callback,
                on_open_lixeira=mock_callback,
                on_obrigacoes=mock_callback,
            )
            frame.pack(fill="both", expand=True)
            print("✓ ClientesFrame criado com sucesso")

            # Verifica se o toggle foi inserido
            if hasattr(frame, "_theme_switch") and frame._theme_switch is not None:
                print("✓ Toggle de tema inserido com sucesso!")
                if frame._theme_manager is not None:
                    print(f"  Modo atual: {frame._theme_manager.current_mode}")
                print(f"  Switch text: {frame._theme_switch.cget('text')}")
            else:
                print("⚠ Toggle não foi inserido (CustomTkinter pode não estar disponível)")

        except Exception as e:
            print(f"✗ Erro ao criar ClientesFrame: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

        print("\n" + "=" * 60)
        print("Janela de teste aberta. Verifique:")
        print("1. O toggle aparece à direita da toolbar")
        print("2. O texto indica o modo oposto (🌙 Escuro ou ☀️ Claro)")
        print("3. Clique no toggle para alternar")
        print("4. Feche a janela quando terminar")
        print("=" * 60 + "\n")

        root.mainloop()

        print("\n✓ Teste concluído!")

    except ImportError as e:
        print(f"✗ Erro de import: {e}")
        print("\nVerifique se as dependências estão instaladas:")
        print("  pip install ttkbootstrap customtkinter")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Erro: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
