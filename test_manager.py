"""
Test script para TtkTreeviewManager - verifica funcionamento completo
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

from src.ui.ttk_treeview_manager import get_treeview_manager


def test_manager():
    """Testa o manager com múltiplas trees."""
    print("\n=== TESTE DO TREEVIEW MANAGER ===\n")
    
    # Criar janela principal
    root = ctk.CTk()
    root.title("Teste Manager")
    root.geometry("800x600")
    
    # Modo inicial
    ctk.set_appearance_mode("Light")
    print("✅ Modo inicial: Light")
    
    # Frame principal
    main_frame = ctk.CTkFrame(root)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # === Tree 1: ClientesV2 ===
    frame1 = ctk.CTkFrame(main_frame)
    frame1.pack(fill="both", expand=True, pady=5)
    
    tree1 = ttk.Treeview(frame1, columns=("Nome", "Cidade"), show="tree headings")  # type: ignore[attr-defined]
    tree1.heading("#0", text="ID")  # type: ignore[attr-defined]
    tree1.heading("Nome", text="Nome")  # type: ignore[attr-defined]
    tree1.heading("Cidade", text="Cidade")  # type: ignore[attr-defined]
    tree1.pack(fill="both", expand=True)  # type: ignore[attr-defined]
    
    # Registrar tree1
    manager = get_treeview_manager()
    style1, colors1 = manager.register(tree1, frame1, "RC", zebra=True)
    print(f"✅ Tree1 registrada: style={style1}")
    print(f"   Cores Light: even={colors1.even_bg}, odd={colors1.odd_bg}")
    
    # Popular tree1
    for i in range(10):
        iid = tree1.insert("", "end", text=f"{i:03d}", values=(f"Cliente {i}", f"Cidade {i}"))
    
    # === Tree 2: ClientFiles ===
    frame2 = ctk.CTkFrame(main_frame)
    frame2.pack(fill="both", expand=True, pady=5)
    
    tree2 = ttk.Treeview(frame2, columns=("Tamanho",), show="tree headings")  # type: ignore[attr-defined]
    tree2.heading("#0", text="Arquivo")  # type: ignore[attr-defined]
    tree2.heading("Tamanho", text="Tamanho")  # type: ignore[attr-defined]
    tree2.pack(fill="both", expand=True)  # type: ignore[attr-defined]
    
    # Registrar tree2
    style2, colors2 = manager.register(tree2, frame2, "RC.Files", zebra=True)
    print(f"✅ Tree2 registrada: style={style2}")
    
    # Popular tree2
    for i in range(5):
        tree2.insert("", "end", text=f"file_{i}.txt", values=(f"{i*100} KB",))
    
    # === Botão de troca de tema ===
    def toggle_theme():
        current = ctk.get_appearance_mode()
        new_mode = "Dark" if current == "Light" else "Light"
        print(f"\n🔄 Trocando tema: {current} → {new_mode}")
        ctk.set_appearance_mode(new_mode)
        print(f"   Manager possui {len(manager._trees)} trees registradas")
    
    btn = ctk.CTkButton(root, text="Trocar Tema", command=toggle_theme)
    btn.pack(pady=10)
    
    # === Label informativo ===
    info = ctk.CTkLabel(
        root,
        text="Clique no botão para trocar o tema.\nAs duas Treeviews devem atualizar automaticamente.",
        font=("Arial", 10)
    )
    info.pack(pady=5)
    
    print("\n✅ Interface criada. Abra a janela e teste a troca de tema.\n")
    print("🔍 Verificações:")
    print("   1. Tree1 e Tree2 devem ter zebra em Light (odd=#e6eaf0)")
    print("   2. Ao trocar para Dark, ambas devem atualizar (background=#242424)")
    print("   3. Headings devem ser escuros em Dark mode")
    print("   4. Ao trocar de volta para Light, tudo deve restaurar")
    
    root.mainloop()


if __name__ == "__main__":
    test_manager()
