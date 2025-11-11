"""
Script de teste manual para o diálogo de seleção de arquivo ZIP/RAR.

Este script abre o diálogo de seleção de arquivo e mostra os logs
para validar que:
1. Os arquivos .rar aparecem no seletor
2. O filetypes está correto (tupla de padrões)
3. Os logs mostram as informações de debug
"""
import logging
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

# Configurar logging em DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

import tkinter as tk
from src.ui.dialogs.file_select import select_archive_file, validate_archive_extension


def main():
    """Função principal de teste."""
    root = tk.Tk()
    root.withdraw()  # Esconder a janela principal
    
    print("=" * 70)
    print("TESTE MANUAL: Diálogo de Seleção de Arquivo ZIP/RAR")
    print("=" * 70)
    print()
    print("Instruções:")
    print("1. O diálogo será aberto automaticamente")
    print("2. Verifique que arquivos .rar APARECEM na lista")
    print("3. Verifique que o filtro mostra 'Arquivos compactados (*.zip; *.rar)'")
    print("4. Selecione um arquivo (ou cancele)")
    print("5. Veja os logs abaixo mostrando o filetypes usado")
    print()
    print("-" * 70)
    print()
    
    # Abrir diálogo
    path = select_archive_file()
    
    print()
    print("-" * 70)
    print()
    
    if path:
        print(f"✅ Arquivo selecionado: {path}")
        print(f"📦 Nome: {Path(path).name}")
        print(f"📁 Diretório: {Path(path).parent}")
        print(f"🔍 Extensão válida: {validate_archive_extension(path)}")
        
        if not validate_archive_extension(path):
            print()
            print("⚠️  AVISO: Arquivo selecionado não é ZIP nem RAR!")
            print("   (Usuário provavelmente escolheu 'Todos os arquivos')")
    else:
        print("❌ Nenhum arquivo selecionado (cancelado)")
    
    print()
    print("=" * 70)
    print("TESTE CONCLUÍDO")
    print("=" * 70)
    print()
    print("Verificações:")
    print("  [ ] Arquivos .rar apareceram no diálogo?")
    print("  [ ] O filtro mostrou 'Arquivos compactados (*.zip; *.rar)'?")
    print("  [ ] Os logs mostraram filetypes=[('Arquivos compactados', ('*.zip', '*.rar')), ...]?")
    print()
    
    root.destroy()


if __name__ == "__main__":
    main()
