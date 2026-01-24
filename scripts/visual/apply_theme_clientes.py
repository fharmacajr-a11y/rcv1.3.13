#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Teste manual para verificar que apply_theme não causa ValueError.

Simula a inicialização do módulo Clientes e alternância de tema,
verificando que não há erros relacionados a 'bg' em widgets CustomTkinter.

AVISO: Este script abre uma GUI. NÃO execute via pytest.
       Use: python scripts/visual/apply_theme_clientes.py
"""

import sys
from pathlib import Path

# Adiciona raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """Executa teste visual de aplicação de tema."""
    try:
        import tkinter as tk
        from src.modules.clientes.view import ClientesFrame
        from src.modules.clientes.views.toolbar_ctk import HAS_CUSTOMTKINTER

        print("=" * 70)
        print("TESTE: Aplicação de Tema Sem Crash (Microfase 2.1)")
        print("=" * 70)

        if not HAS_CUSTOMTKINTER:
            print("⚠ CustomTkinter não disponível")
            print("Este teste só é relevante com CustomTkinter instalado")
            sys.exit(0)

        print("✓ CustomTkinter disponível")

        # Cria janela
        root = tk.Tk()
        root.title("Teste Manual - Apply Theme Fix")
        root.geometry("1200x600")

        print("✓ Janela criada")

        # Callbacks mock
        def mock_cb(*args, **kwargs):
            return None

        print("✓ Criando ClientesFrame...")
        try:
            frame = ClientesFrame(
                root,
                on_new=mock_cb,
                on_edit=mock_cb,
                on_delete=mock_cb,
                on_upload=mock_cb,
                on_open_subpastas=mock_cb,
                on_open_lixeira=mock_cb,
                on_obrigacoes=mock_cb,
            )
            frame.pack(fill="both", expand=True)
            print("✓ ClientesFrame criado SEM ERROS")
        except ValueError as e:
            if "are not supported arguments" in str(e):
                print(f"✗ FALHA: ValueError relacionado a 'bg': {e}")
                root.destroy()
                sys.exit(1)
            raise

        print("✓ Testando _apply_theme_to_widgets()...")
        try:
            frame._apply_theme_to_widgets()
            print("✓ _apply_theme_to_widgets() executado SEM ERROS")
        except ValueError as e:
            if "are not supported arguments" in str(e):
                print(f"✗ FALHA: ValueError ao aplicar tema: {e}")
                root.destroy()
                sys.exit(1)
            raise

        print("\n" + "=" * 70)
        print("TESTE INTERATIVO:")
        print("1. Observe a toolbar CustomTkinter (visual moderno)")
        print("2. Clique no switch à direita para alternar tema")
        print("3. Verifique que NÃO aparece erro no terminal")
        print("4. Cores da toolbar devem mudar")
        print("5. Feche a janela quando terminar")
        print("=" * 70 + "\n")

        # Contador de toggles
        toggle_count = [0]

        def on_window_close():
            print(f"\n✓ Janela fechada após {toggle_count[0]} toggles")
            if toggle_count[0] > 0:
                print("✓ Tema foi alternado com sucesso!")
            print("\n" + "=" * 70)
            print("RESULTADO: ✅ TESTE PASSOU - Nenhum ValueError de 'bg'")
            print("=" * 70)
            root.destroy()

        # Hook para contar toggles
        original_toggle = frame._on_theme_toggle

        def counting_toggle():
            toggle_count[0] += 1
            print(f"  → Toggle #{toggle_count[0]}: alterando tema...")
            try:
                original_toggle()
                print(f"  ✓ Toggle #{toggle_count[0]}: SEM ERROS")
            except ValueError as e:
                if "are not supported arguments" in str(e):
                    print(f"  ✗ Toggle #{toggle_count[0]}: ValueError de 'bg'!")
                    print(f"     Erro: {e}")
                    root.destroy()
                    sys.exit(1)
                raise

        frame._on_theme_toggle = counting_toggle

        root.protocol("WM_DELETE_WINDOW", on_window_close)
        root.mainloop()

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
