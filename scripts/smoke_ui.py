#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test UI - valida funcionalidade básica de tema e janelas CTk.

OBJETIVO: Garantir que a interface CustomTkinter funciona corretamente:
- Instanciar janela CTk
- Alternar temas (light/dark/system)
- Criar/destruir CTkToplevel sem mainloop extra
- Destruir tudo e sair sem erros

Exit code:
- 0: Smoke test passou
- 1: Erro durante execução
"""

from __future__ import annotations

import sys
from pathlib import Path

# Adicionar src/ ao path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

try:
    import customtkinter as ctk
    from src.ui.theme_manager import theme_manager
except ImportError as e:
    print(f"❌ Erro ao importar dependências: {e}", file=sys.stderr)
    sys.exit(1)


def test_basic_window() -> None:
    """Testa criação/destruição de janela CTk."""
    print("   1️⃣ Testando criação de janela CTk...")
    
    root = ctk.CTk()
    root.title("Smoke Test UI")
    root.geometry("400x300")
    root.withdraw()  # Não mostrar janela
    
    # Criar alguns widgets
    label = ctk.CTkLabel(root, text="Smoke Test")
    label.pack(pady=20)
    
    button = ctk.CTkButton(root, text="Test Button")
    button.pack(pady=10)
    
    print("      ✓ Janela criada com widgets")
    
    # Destruir
    root.destroy()
    print("      ✓ Janela destruída")


def test_theme_switching() -> None:
    """Testa alternância de temas."""
    print("   2️⃣ Testando alternância de temas...")
    
    root = ctk.CTk()
    root.withdraw()
    
    # Inicializar singleton com master
    theme_manager.set_master(root)
    
    # Alternar para light
    theme_manager.set_mode("light")
    current = theme_manager.get_current_mode()
    assert current == "light", f"Esperado 'light', obteve '{current}'"
    print("      ✓ Tema light aplicado")
    
    # Alternar para dark
    theme_manager.set_mode("dark")
    current = theme_manager.get_current_mode()
    assert current == "dark", f"Esperado 'dark', obteve '{current}'"
    print("      ✓ Tema dark aplicado")
    
    # Alternar para system
    theme_manager.set_mode("system")
    current = theme_manager.get_current_mode()
    assert current == "system", f"Esperado 'system', obteve '{current}'"
    print("      ✓ Tema system aplicado")
    
    # Verificar resolve
    resolved = theme_manager.get_effective_mode()
    assert resolved in ("light", "dark"), f"Resolved inválido: {resolved}"
    print(f"      ✓ System resolvido para: {resolved}")
    
    root.destroy()


def test_toplevel() -> None:
    """Testa criação/destruição de CTkToplevel."""
    print("   3️⃣ Testando CTkToplevel...")
    
    root = ctk.CTk()
    root.withdraw()
    
    # Criar Toplevel
    toplevel = ctk.CTkToplevel(root)
    toplevel.title("Test Toplevel")
    toplevel.withdraw()
    
    # Adicionar widgets
    label = ctk.CTkLabel(toplevel, text="Toplevel Test")
    label.pack(pady=20)
    
    print("      ✓ CTkToplevel criada")
    
    # Destruir Toplevel (não deve causar erro)
    toplevel.destroy()
    print("      ✓ CTkToplevel destruída")
    
    # Destruir root
    root.destroy()
    print("      ✓ Root destruída")


def test_theme_manager_api() -> None:
    """Testa API completa do theme_manager."""
    print("   4️⃣ Testando API theme_manager...")
    
    # Importar resolve_effective_mode (função standalone)
    from src.ui.theme_manager import resolve_effective_mode
    
    # resolve_effective_mode
    resolved_light = resolve_effective_mode("light")
    assert resolved_light == "light"
    
    resolved_dark = resolve_effective_mode("dark")
    assert resolved_dark == "dark"
    
    resolved_system = resolve_effective_mode("system")
    assert resolved_system in ("light", "dark")
    print(f"      ✓ resolve_effective_mode: OK")
    
    # Métodos da instância
    current = theme_manager.get_current_mode()
    assert current in ("light", "dark", "system"), f"Modo inválido: {current}"
    print(f"      ✓ get_current_mode: {current}")
    
    effective = theme_manager.get_effective_mode()
    assert effective in ("light", "dark"), f"Modo efetivo inválido: {effective}"
    print(f"      ✓ get_effective_mode: {effective}")


def main() -> int:
    """Executa todos os testes."""
    print("🔬 Smoke Test UI - CustomTkinter\n")
    
    try:
        test_basic_window()
        test_theme_switching()
        test_toplevel()
        test_theme_manager_api()
        
        print("\n✅ Smoke test passou!")
        print("   - Janela CTk: OK")
        print("   - Alternância de temas: OK")
        print("   - CTkToplevel: OK")
        print("   - theme_manager API: OK")
        return 0
        
    except Exception as e:
        print(f"\n❌ Smoke test falhou: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
