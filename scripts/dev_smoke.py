#!/usr/bin/env python
"""
Script de smoke test para validação rápida do build.

Executa:
1. py_compile em todos os arquivos .py (exceto .venv, build, dist, __pycache__)
2. Testa imports de contratos de compatibilidade confirmados no STATUS_REPORT.md

Uso:
    python scripts/dev_smoke.py
"""

import pathlib
import py_compile
import sys
from typing import List, Tuple


# Adiciona o diretório raiz ao path para imports funcionarem
ROOT_DIR = pathlib.Path(__file__).parent.parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def find_python_files() -> List[pathlib.Path]:
    """Encontra todos os arquivos .py válidos no projeto."""
    excluded = {".venv", "venv", "build", "dist", "__pycache__"}
    
    files = []
    for path in ROOT_DIR.rglob("*.py"):
        # Ignora arquivos em diretórios excluídos
        if any(excluded_part in path.parts for excluded_part in excluded):
            continue
        files.append(path)
    
    return sorted(files)


def test_py_compile() -> Tuple[bool, str]:
    """Testa compilação de todos os arquivos Python."""
    print("\n" + "="*60)
    print("ETAPA 1: py_compile em todos os arquivos .py")
    print("="*60)
    
    files = find_python_files()
    print(f"Encontrados {len(files)} arquivos Python")
    print("Compilando...", end="", flush=True)
    
    failed = []
    compiled = 0
    for file in files:
        try:
            py_compile.compile(str(file), doraise=True)
            compiled += 1
            if compiled % 10 == 0:
                print(".", end="", flush=True)
        except Exception as exc:
            failed.append((str(file), str(exc)))
    
    print()  # Nova linha após os pontos
    
    if failed:
        print(f"\n[FAIL] {len(failed)} arquivo(s) com erro de compilacao:")
        for file, error in failed[:5]:  # Mostra no máximo 5 erros
            print(f"  - {file}: {error}")
        if len(failed) > 5:
            print(f"  ... e mais {len(failed) - 5} erro(s)")
        return False, f"{len(failed)} arquivo(s) com erro"
    
    print(f"[OK] {len(files)} arquivos compilados com sucesso")
    return True, "Compilacao OK"


def test_compat_imports() -> Tuple[bool, str]:
    """Testa imports de contratos de compatibilidade."""
    print("\n" + "="*60)
    print("ETAPA 2: Imports de compatibilidade (confirmados no STATUS)")
    print("="*60)
    
    imports_to_test = [
        ("infra.supabase_client", "exec_postgrest"),
        ("ui.components", "toolbar_button"),
        ("utils.file_utils.file_utils", "ensure_dir"),
        ("application.api", "register_endpoints"),
        ("gui.main_window", "App"),
    ]
    
    failed = []
    for module, symbol in imports_to_test:
        try:
            print(f"  Testando: from {module} import {symbol} ... ", end="")
            exec(f"from {module} import {symbol}")
            print("[OK]")
        except Exception as exc:
            print(f"[FAIL] {exc.__class__.__name__}: {exc}")
            failed.append((module, symbol, str(exc)))
    
    if failed:
        print(f"\n[FAIL] {len(failed)} import(s) com erro:")
        for module, symbol, error in failed:
            print(f"  - from {module} import {symbol}")
            print(f"    Erro: {error}")
        return False, f"{len(failed)} import(s) falharam"
    
    print(f"\n[OK] Todos os {len(imports_to_test)} imports funcionando")
    return True, "Imports OK"


def main():
    """Executa o smoke test completo."""
    print("\n" + "="*60)
    print("DEV SMOKE TEST - Validacao Rapida do Build")
    print("="*60)
    
    results = []
    
    # Etapa 1: py_compile
    success, msg = test_py_compile()
    results.append(("py_compile", success, msg))
    
    # Etapa 2: imports de compatibilidade
    success, msg = test_compat_imports()
    results.append(("compat_imports", success, msg))
    
    # Resumo final
    print("\n" + "="*60)
    print("RESUMO FINAL")
    print("="*60)
    
    all_ok = True
    for name, success, msg in results:
        status = "OK  " if success else "FAIL"
        print(f"[{status}] {name:20} {msg}")
        if not success:
            all_ok = False
    
    print("\n" + "="*60)
    if all_ok:
        print("SMOKE: OK")
    else:
        print("SMOKE: FAIL")
    print("="*60 + "\n")
    
    # Não usar sys.exit(1) conforme especificação
    # return 0 if all_ok else 1


if __name__ == "__main__":
    main()
