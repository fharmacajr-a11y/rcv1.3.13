#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demo visual do guardrail Cloud-Only

Abre uma janela simples com um botão que tenta abrir uma pasta.
Em modo Cloud-Only, mostra messagebox de bloqueio.
"""
import sys
import os
from pathlib import Path

# Garantir que está em Cloud-Only para demonstração
os.environ["RC_NO_LOCAL_FS"] = "1"

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import tkinter as tk
from tkinter import ttk


def demo_guardrail():
    """Demonstra o guardrail em ação."""
    from utils.file_utils import open_folder
    from pathlib import Path

    # Tenta abrir a pasta do usuário (será bloqueado)
    open_folder(Path.home())


def main():
    """Cria janela de demonstração."""
    root = tk.Tk()
    root.title("Demo - Guardrail Cloud-Only (Step 7)")
    root.geometry("400x200")

    # Frame principal
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill=tk.BOTH, expand=True)

    # Título
    title = ttk.Label(
        frame,
        text="Demonstração do Guardrail Cloud-Only",
        font=("Arial", 12, "bold"),
    )
    title.pack(pady=(0, 20))

    # Explicação
    info = ttk.Label(
        frame,
        text="Clique no botão abaixo para tentar abrir uma pasta.\n"
        "Como RC_NO_LOCAL_FS=1, o guardrail deve bloquear\n"
        "a operação e exibir um messagebox informativo.",
        justify=tk.CENTER,
    )
    info.pack(pady=(0, 20))

    # Botão de teste
    btn = ttk.Button(
        frame, text="Tentar Abrir Pasta (será bloqueado)", command=demo_guardrail
    )
    btn.pack(pady=(0, 10))

    # Status
    from config.paths import CLOUD_ONLY

    status = ttk.Label(
        frame,
        text=f"Status: CLOUD_ONLY = {CLOUD_ONLY}",
        foreground="green" if CLOUD_ONLY else "red",
    )
    status.pack()

    # Botão fechar
    close_btn = ttk.Button(frame, text="Fechar", command=root.destroy)
    close_btn.pack(pady=(10, 0))

    root.mainloop()


if __name__ == "__main__":
    print("=" * 60)
    print("Demo Visual - Guardrail Cloud-Only")
    print("=" * 60)
    print()
    print("INSTRUÇÕES:")
    print("1. Uma janela será aberta")
    print("2. Clique no botão 'Tentar Abrir Pasta'")
    print("3. Você deve ver um messagebox informando que a função")
    print("   está indisponível no modo Cloud-Only")
    print()
    print("Iniciando demo...")
    print()

    main()
