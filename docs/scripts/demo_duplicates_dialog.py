#!/usr/bin/env python3
"""
Script de demonstração do diálogo de duplicatas.

Uso:
    python scripts/demo_duplicates_dialog.py
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.modules.auditoria.view import DuplicatesDialog

    print("=" * 70)
    print("DEMO: Diálogo de Duplicatas")
    print("=" * 70)
    print("\n📋 Funcionalidades:")
    print("  ✓ Lista até 20 nomes duplicados")
    print("  ✓ 3 opções: Pular / Substituir / Renomear")
    print("  ✓ Padrão: Pular (recomendado)")
    print("  ✓ Botões: OK / Cancelar")
    print("  ✓ Atalhos: Enter (OK) / Escape (Cancelar)")
    print("\n" + "=" * 70)

    # Criar janela raiz
    root = tk.Tk()
    root.title("Demo: Duplicates Dialog")
    root.geometry("400x300")

    # Frame de instruções
    frame_info = tk.Frame(root, padx=20, pady=20)
    frame_info.pack(fill="both", expand=True)

    lbl_info = tk.Label(
        frame_info,
        text="Clique no botão abaixo para ver o diálogo de duplicatas.\n\nSimula 15 arquivos duplicados encontrados.",
        font=("-size", 10),
        justify="left",
        wraplength=360,
    )
    lbl_info.pack(pady=(0, 20))

    result_var = tk.StringVar(value="Nenhum resultado ainda")
    lbl_result = tk.Label(frame_info, textvariable=result_var, font=("-size", 9), foreground="#666")
    lbl_result.pack(pady=(0, 20))

    def show_dialog():
        # Simular 15 duplicatas
        sample_names = [
            "documento.pdf",
            "planilha.xlsx",
            "foto.jpg",
            "relatorio_2024.docx",
            "contrato.pdf",
            "nota_fiscal_123.pdf",
            "balanco_mensal.xlsx",
            "apresentacao.pptx",
            "logo.png",
            "backup_dados.zip",
            "email_importante.msg",
            "anexo_1.pdf",
            "anexo_2.pdf",
            "tabela_precos.csv",
            "comprovante.pdf",
        ]

        dlg = DuplicatesDialog(root, len(sample_names), sample_names)
        root.wait_window(dlg)

        if dlg.strategy is None:
            result_var.set("❌ Usuário cancelou o upload")
        elif dlg.strategy == "skip":
            result_var.set("⊘ Escolhido: Pular duplicatas (não enviar)")
        elif dlg.strategy == "replace":
            result_var.set("♻ Escolhido: Substituir duplicatas (sobrescrever)")
        elif dlg.strategy == "rename":
            result_var.set("✏ Escolhido: Renomear duplicatas (sufixo)")

        print(f"\n📊 Resultado: {dlg.strategy}")

    btn_show = tk.Button(
        frame_info, text="Mostrar Diálogo de Duplicatas", command=show_dialog, font=("-size", 10), padx=20, pady=10
    )
    btn_show.pack()

    print("\n🎬 Janela de demo aberta. Clique no botão para ver o diálogo.")
    print("   Pressione Ctrl+C ou feche a janela para sair.\n")

    root.mainloop()

    print("\n✅ Demo concluída.")
