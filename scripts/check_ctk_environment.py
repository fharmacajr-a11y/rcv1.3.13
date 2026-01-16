#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script diagnóstico para verificar configuração do ambiente Python/CustomTkinter.

Execute para validar que VS Code/Pylance estão configurados corretamente:
    python scripts/check_ctk_environment.py

Microfase: 5.1 (Fix Pylance CustomTkinter)
"""

import sys
import subprocess
from pathlib import Path

# Adicionar raiz do projeto ao sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_header(title: str) -> None:
    """Imprime cabeçalho de seção."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def check_python_executable() -> bool:
    """Verifica qual Python está sendo usado."""
    print_header("1. Python Executable")

    executable = sys.executable
    print(f"Python em uso: {executable}")

    # Verificar se é da venv do projeto
    project_venv = Path.cwd() / ".venv" / "Scripts" / "python.exe"

    if Path(executable).resolve() == project_venv.resolve():
        print("✅ Usando Python da .venv do projeto")
        return True
    else:
        print("⚠️  NÃO está usando .venv do projeto!")
        print(f"   Esperado: {project_venv}")
        print(f"   Atual: {executable}")
        print("\nAções:")
        print("  1. Ativar venv: .venv\\Scripts\\Activate.ps1")
        print("  2. VS Code: Ctrl+Shift+P → Python: Select Interpreter → .venv")
        return False


def check_customtkinter_installed() -> bool:
    """Verifica se CustomTkinter está instalado."""
    print_header("2. CustomTkinter Package")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "customtkinter"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            print(result.stdout)
            print("✅ CustomTkinter instalado")
            return True
        else:
            print("❌ CustomTkinter NÃO instalado")
            print("\nAções:")
            print("  pip install customtkinter")
            return False
    except Exception as e:
        print(f"❌ Erro ao verificar: {e}")
        return False


def check_customtkinter_import() -> bool:
    """Verifica se import funciona."""
    print_header("3. CustomTkinter Import")

    try:
        from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

        if HAS_CUSTOMTKINTER and ctk:
            version = getattr(ctk, "__version__", "unknown")
            print(f"✅ Import bem-sucedido: customtkinter {version} (via ctk_config SSoT)")
            return True
        else:
            print("❌ CustomTkinter não disponível (HAS_CUSTOMTKINTER=False)")
            print("\nAções:")
            print("  pip install customtkinter")
            return False
    except ImportError as e:
        print(f"❌ Import falhou: {e}")
        print("\nAções:")
        print("  pip install customtkinter")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False


def check_project_imports() -> bool:
    """Verifica imports do projeto."""
    print_header("4. Project Imports (Clientes CTk)")

    errors = []

    # Teste 1: Modal CTk
    try:
        from src.modules.clientes.ui import HAS_CUSTOMTKINTER

        print(f"✅ ClientesModalCTK: HAS_CUSTOMTKINTER = {HAS_CUSTOMTKINTER}")
    except Exception as e:
        errors.append(f"❌ ClientesModalCTK: {e}")

    # Teste 2: UI Builders CTk
    try:
        print("✅ client_form_ui_builders_ctk: import OK")
    except Exception as e:
        errors.append(f"❌ client_form_ui_builders_ctk: {e}")

    # Teste 3: View CTk
    try:
        print("✅ ClientFormViewCTK: import OK")
    except Exception as e:
        errors.append(f"❌ ClientFormViewCTK: {e}")

    if errors:
        print("\nErros encontrados:")
        for error in errors:
            print(f"  {error}")
        return False

    return True


def check_vscode_config() -> bool:
    """Verifica configurações do VS Code."""
    print_header("5. VS Code Configuration")

    settings_file = Path.cwd() / ".vscode" / "settings.json"
    pyright_file = Path.cwd() / "pyrightconfig.json"

    checks = []

    # settings.json
    if settings_file.exists():
        print(f"✅ {settings_file} existe")
        content = settings_file.read_text(encoding="utf-8")
        if "defaultInterpreterPath" in content:
            print("   ✅ defaultInterpreterPath configurado")
        else:
            print("   ⚠️  defaultInterpreterPath NÃO configurado")
            checks.append(False)

        if "python.analysis.indexing" in content:
            print("   ✅ python.analysis.indexing configurado")
        else:
            print("   ⚠️  python.analysis.indexing NÃO configurado")
            checks.append(False)
    else:
        print(f"❌ {settings_file} não existe")
        checks.append(False)

    # pyrightconfig.json
    if pyright_file.exists():
        print(f"✅ {pyright_file} existe")
        content = pyright_file.read_text(encoding="utf-8")
        if '"venvPath"' in content and '"venv"' in content:
            print("   ✅ venvPath/venv configurados")
        else:
            print("   ⚠️  venvPath/venv NÃO configurados")
            checks.append(False)
    else:
        print(f"❌ {pyright_file} não existe")
        checks.append(False)

    if False in checks:
        print("\nAções:")
        print("  Ver: docs/CLIENTES_PYLANCE_CUSTOMTKINTER_FIX.md")
        return False

    return True


def main() -> None:
    """Executa todos os checks."""
    print("=" * 60)
    print("  DIAGNÓSTICO: Python/CustomTkinter Environment")
    print("=" * 60)

    results = {
        "Python Executable": check_python_executable(),
        "CustomTkinter Installed": check_customtkinter_installed(),
        "CustomTkinter Import": check_customtkinter_import(),
        "Project Imports": check_project_imports(),
        "VS Code Config": check_vscode_config(),
    }

    print_header("RESUMO")

    for check, passed in results.items():
        status = "✅ OK" if passed else "❌ FALHOU"
        print(f"{status:12} {check}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 AMBIENTE OK - CustomTkinter configurado corretamente!")
    else:
        print("\n⚠️  AMBIENTE COM PROBLEMAS - Ver ações acima")
        print("\nDocumentação:")
        print("  docs/CLIENTES_PYLANCE_CUSTOMTKINTER_FIX.md")

    print("\n" + "=" * 60)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
