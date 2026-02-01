"""
Script de teste para verificar se ttk.Style está aplicando corretamente
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk

print("\n=== TESTE TTK.STYLE ===\n")

# Criar janela
root = ctk.CTk()
root.title("Teste ttk.Style")
root.geometry("600x400")

# Frame CTk
frame = ctk.CTkFrame(root)
frame.pack(fill="both", expand=True, padx=10, pady=10)

# Criar Treeview
tree = ttk.Treeview(frame, columns=("col1",), show="tree headings")  # type: ignore[attr-defined]
tree.heading("#0", text="ID")  # type: ignore[attr-defined]
tree.heading("col1", text="Nome")  # type: ignore[attr-defined]
tree.pack(fill="both", expand=True)  # type: ignore[attr-defined]

# Popular
for i in range(10):
    tree.insert("", "end", text=f"Item {i}", values=(f"Valor {i}",))  # type: ignore[attr-defined]

# Criar Style com frame como master
style = ttk.Style(frame)  # type: ignore[call-arg]
print(f"Tema atual: {style.theme_use()}")
print(f"Temas disponíveis: {style.theme_names()}")

# Forçar clam
style.theme_use("clam")
print(f"Tema após forçar clam: {style.theme_use()}")

# Configurar Dark
print("\n--- Configurando Dark Mode ---")
style.configure(
    "RC.Treeview",
    background="#2b2b2b",
    fieldbackground="#2b2b2b",
    foreground="#f5f5f5",
    borderwidth=0,
    relief="flat",
)
style.configure(
    "RC.Treeview.Heading",
    background="#1a1a1a",
    foreground="#f5f5f5",
    relief="flat",
)

# Aplicar no tree
tree.configure(style="RC.Treeview")  # type: ignore[attr-defined]

# Verificar configurações
print(f"RC.Treeview background: {style.lookup('RC.Treeview', 'background')}")
print(f"RC.Treeview fieldbackground: {style.lookup('RC.Treeview', 'fieldbackground')}")
print(f"RC.Treeview foreground: {style.lookup('RC.Treeview', 'foreground')}")
print(f"RC.Treeview.Heading background: {style.lookup('RC.Treeview.Heading', 'background')}")

print("\n✅ Se a Treeview estiver ESCURA, ttk.Style funciona.")
print("❌ Se a Treeview estiver CLARA, há problema com ttk.Style.\n")

root.mainloop()
