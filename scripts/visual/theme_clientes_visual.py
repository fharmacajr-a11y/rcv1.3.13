#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script de teste visual para verificar o tema Light/Dark do módulo Clientes.

AVISO: Este script abre uma GUI. NÃO execute via pytest.
       Use: python scripts/visual/theme_clientes_visual.py
"""

import tkinter as tk
import sys
from pathlib import Path

# Adiciona raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """Executa teste visual do tema."""
    try:
        from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
        from src.modules.clientes.appearance import ClientesThemeManager
        import ttkbootstrap as tb

        if not HAS_CUSTOMTKINTER:
            print("❌ CustomTkinter não disponível")
            print("Instale com: pip install customtkinter")
            return

        print("✓ Imports bem-sucedidos")
        version = getattr(ctk, "__version__", "unknown") if ctk else "unknown"
        print(f"✓ CustomTkinter versão: {version}")

        # Cria theme manager
        manager = ClientesThemeManager()
        print(f"✓ Theme manager criado, modo atual: {manager.current_mode}")

        # Testa paletas
        light_palette = manager.get_palette("light")
        dark_palette = manager.get_palette("dark")
        print(f"✓ Paleta Light tem {len(light_palette)} cores")
        print(f"✓ Paleta Dark tem {len(dark_palette)} cores")

        # Cria janela de teste
        root = tk.Tk()
        root.title("Teste Visual - Theme Clientes")
        root.geometry("600x400")

        # Frame principal
        main_frame = tk.Frame(root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Label de status
        status_label = tk.Label(
            main_frame,
            text=f"Modo atual: {manager.current_mode.upper()}",
            font=("Segoe UI", 14, "bold"),
        )
        status_label.pack(pady=10)

        # Preview de cores
        colors_frame = tk.Frame(main_frame)
        colors_frame.pack(pady=10, fill="x")

        palette = manager.get_palette()
        for i, (key, color) in enumerate(list(palette.items())[:6]):
            color_box = tk.Frame(
                colors_frame,
                bg=color,
                width=80,
                height=60,
                relief="solid",
                borderwidth=1,
            )
            color_box.pack(side="left", padx=5)
            color_label = tk.Label(colors_frame, text=f"{key}\n{color}", font=("Consolas", 8))
            color_label.pack(side="left", padx=5)

        # Switch para alternar
        def toggle_theme():
            style = tb.Style()
            new_mode = manager.toggle(style)
            status_label.config(text=f"Modo atual: {new_mode.upper()}")
            print(f"✓ Tema alternado para: {new_mode}")

            # Atualiza preview de cores
            palette = manager.get_palette()
            for i, widget_pair in enumerate(zip(colors_frame.winfo_children()[::2], list(palette.items())[:6])):
                color_box, (_, color) = widget_pair, list(palette.items())[i]
                color_box.config(bg=color)

        if ctk is not None:
            switch = ctk.CTkSwitch(
                main_frame,
                text="Modo Escuro",
                command=toggle_theme,
            )
            if manager.current_mode == "dark":
                switch.select()
            switch.pack(pady=20)

        # Instruções
        instructions = tk.Label(
            main_frame,
            text="Alterne o switch acima para ver as cores mudarem.\n" "As preferências são salvas automaticamente.",
            font=("Segoe UI", 10),
            justify="center",
        )
        instructions.pack(pady=10)

        # Botão fechar
        close_btn = tk.Button(main_frame, text="Fechar", command=root.destroy)
        close_btn.pack(pady=10)

        print("\n✓ Janela de teste aberta. Teste o switch e feche quando terminar.")
        print("=" * 60)

        root.mainloop()

        print("\n✓ Teste visual concluído!")
        print(f"✓ Modo final salvo: {manager.current_mode}")

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
