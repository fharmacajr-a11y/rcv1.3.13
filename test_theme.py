# -*- coding: utf-8 -*-
"""Teste rápido do tema da Treeview do ClientesV2."""

import tkinter as tk
from tkinter import ttk  # type: ignore[attr-defined]
from src.modules.clientes.ui.tree_theme import apply_clients_v2_treeview_theme, apply_treeview_zebra_tags


def test_theme():
    """Testa aplicação do tema Light e Dark."""
    root = tk.Tk()  # type: ignore[attr-defined]
    root.title("Teste Treeview Theme")
    root.geometry("800x600")

    # Frame para controles
    controls = tk.Frame(root)  # type: ignore[attr-defined]
    controls.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)  # type: ignore[attr-defined]

    # Variável de modo
    mode_var = tk.StringVar(value="Light")  # type: ignore[attr-defined]

    def apply_theme():
        """Aplica tema selecionado."""
        mode = mode_var.get()
        print(f"\n=== Aplicando tema: {mode} ===")
        even_bg, odd_bg, fg, heading_bg, heading_fg = apply_clients_v2_treeview_theme(mode, master=root)
        print(f"Cores: even={even_bg}, odd={odd_bg}, fg={fg}, heading={heading_bg}")
        apply_treeview_zebra_tags(tree, even_bg, odd_bg, fg)
        print("Zebra aplicada!")

    # Botões
    tk.Radiobutton(controls, text="Light", variable=mode_var, value="Light", command=apply_theme).pack(side=tk.LEFT)  # type: ignore[attr-defined]
    tk.Radiobutton(controls, text="Dark", variable=mode_var, value="Dark", command=apply_theme).pack(side=tk.LEFT)  # type: ignore[attr-defined]

    # Frame para Treeview
    tree_frame = tk.Frame(root)  # type: ignore[attr-defined]
    tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)  # type: ignore[attr-defined]
    tree_frame.grid_rowconfigure(0, weight=1)
    tree_frame.grid_columnconfigure(0, weight=1)

    # Criar Treeview
    tree = ttk.Treeview(
        tree_frame, columns=("id", "nome", "status"), show="tree headings", style="RC.ClientesV2.Treeview"
    )

    tree.heading("#0", text="")
    tree.heading("id", text="ID")
    tree.heading("nome", text="Nome")
    tree.heading("status", text="Status")

    tree.column("#0", width=0, stretch=False)
    tree.column("id", width=50)
    tree.column("nome", width=300)
    tree.column("status", width=150)

    # Scrollbar
    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)  # type: ignore[attr-defined]
    tree.configure(yscrollcommand=scrollbar.set)

    tree.grid(row=0, column=0, sticky="nsew")  # type: ignore[attr-defined]
    scrollbar.grid(row=0, column=1, sticky="ns")

    # Inserir dados de teste
    for i in range(20):
        tree.insert("", "end", values=(i + 1, f"Cliente {i + 1}", "Ativo" if i % 2 == 0 else "Inativo"))

    # Aplicar tema inicial
    apply_theme()

    print("\n✅ Teste iniciado - Clique nos botões Light/Dark para trocar tema")
    print("💡 Verifique se:")
    print("   1. As linhas estão zebradas (cores alternadas)")
    print("   2. No Dark: fundo escuro, heading escuro, sem branco residual")
    print("   3. No Light: fundo claro, heading claro, zebra visível")

    root.mainloop()


if __name__ == "__main__":
    test_theme()
