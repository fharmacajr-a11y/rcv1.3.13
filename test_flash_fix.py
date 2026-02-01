"""
Script de teste para verificar eliminação do flash ao abrir ClientEditorDialog
Abre o diálogo 20x seguidas e mede o tempo de abertura
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import time
import customtkinter as ctk
from src.modules.clientes.ui.views.client_editor_dialog import ClientEditorDialog

print("\n" + "="*60)
print("TESTE DE FLASH - ClientEditorDialog")
print("="*60)
print("\nInstruções:")
print("1. Observe se há flash branco ao abrir cada janela")
print("2. Cada janela será aberta e fechada automaticamente")
print("3. Teste será repetido 20x")
print("\n" + "="*60 + "\n")

root = ctk.CTk()
root.withdraw()  # Ocultar janela principal

times = []
flash_count = 0

for i in range(20):
    print(f"\n[{i+1}/20] Abrindo diálogo...")
    
    start = time.time()
    
    # Criar diálogo (NOVO cliente)
    dialog = ClientEditorDialog(
        parent=root,
        client_id=None,  # Novo cliente
        session_id=f"test-{i+1}"
    )
    
    elapsed = time.time() - start
    times.append(elapsed)
    
    print(f"        Tempo de abertura: {elapsed:.3f}s")
    
    # Aguardar 500ms para observar
    root.after(500)
    root.update()  # type: ignore[attr-defined]
    
    # Fechar
    dialog.destroy()
    root.update()  # type: ignore[attr-defined]
    
    # Pequena pausa entre testes
    time.sleep(0.1)

print("\n" + "="*60)
print("RESULTADOS")
print("="*60)
print(f"Total de aberturas: 20")
print(f"Tempo médio: {sum(times)/len(times):.3f}s")
print(f"Tempo mínimo: {min(times):.3f}s")
print(f"Tempo máximo: {max(times):.3f}s")
print("\n✅ Se NÃO houve flash branco: CORREÇÃO FUNCIONOU")
print("❌ Se AINDA há flash branco: verificar logs detalhados")
print("="*60 + "\n")

root.destroy()
