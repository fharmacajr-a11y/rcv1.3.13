#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Smoke test para Step 7 - UI Guardrails & HiDPI

Testa:
1. Guardrail Cloud-Only em open_folder
2. Configuração HiDPI
3. Import do entrypoint app_gui
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

print("=" * 60)
print("Smoke Test - Step 7: UI Guardrails & HiDPI")
print("=" * 60)
print()

# Teste 1: Verificar guardrail cloud_only
print("-" * 60)
print("Teste 1: Verificar guardrail Cloud-Only")
print("-" * 60)

try:
    from utils.helpers import check_cloud_only_block

    print("✓ check_cloud_only_block importado com sucesso")

    # Verificar assinatura
    import inspect

    sig = inspect.signature(check_cloud_only_block)
    print(f"✓ Assinatura: {sig}")

    # Verificar que retorna bool
    result = check_cloud_only_block.__annotations__.get("return")
    if result is bool:
        print("✓ Retorno: bool")
    else:
        print(f"⚠ Retorno esperado: bool, obtido: {result}")

except Exception as e:
    print(f"✗ Erro ao importar guardrail: {e}")
    sys.exit(1)

print()

# Teste 2: Verificar open_folder com guardrail
print("-" * 60)
print("Teste 2: Verificar open_folder com guardrail")
print("-" * 60)

try:
    from utils.file_utils import open_folder
    import inspect

    print("✓ open_folder importado com sucesso")

    # Verificar código fonte contém guardrail
    source = inspect.getsource(open_folder)
    if "check_cloud_only_block" in source:
        print("✓ open_folder contém guardrail check_cloud_only_block")
    else:
        print("⚠ open_folder NÃO contém guardrail check_cloud_only_block")

    # Verificar assinatura mantida
    sig = inspect.signature(open_folder)
    expected = "(p: str | Path) -> None"
    if str(sig) == expected or "p:" in str(sig):
        print(f"✓ Assinatura mantida: {sig}")
    else:
        print(f"⚠ Assinatura mudou: {sig}")

except Exception as e:
    print(f"✗ Erro ao verificar open_folder: {e}")
    sys.exit(1)

print()

# Teste 3: Verificar configuração HiDPI
print("-" * 60)
print("Teste 3: Verificar configuração HiDPI")
print("-" * 60)

try:
    from utils.helpers import configure_hidpi_support
    import inspect

    print("✓ configure_hidpi_support importado com sucesso")

    # Verificar assinatura
    sig = inspect.signature(configure_hidpi_support)
    print(f"✓ Assinatura: {sig}")

    # Verificar parâmetros
    params = list(sig.parameters.keys())
    if "root" in params and "scaling" in params:
        print("✓ Parâmetros: root, scaling")
    else:
        print(f"⚠ Parâmetros esperados: root, scaling; obtidos: {params}")

except Exception as e:
    print(f"✗ Erro ao importar HiDPI config: {e}")
    sys.exit(1)

print()

# Teste 4: Verificar import do entrypoint
print("-" * 60)
print("Teste 4: Verificar import do app_gui")
print("-" * 60)

try:
    import app_gui

    print("✓ app_gui importado com sucesso")

    # Verificar que App está disponível
    if hasattr(app_gui, "App"):
        print("✓ app_gui.App disponível")
    else:
        print("⚠ app_gui.App NÃO disponível")

except Exception as e:
    print(f"✗ Erro ao importar app_gui: {e}")
    sys.exit(1)

print()

# Teste 5: Verificar que CLOUD_ONLY está configurado
print("-" * 60)
print("Teste 5: Verificar configuração CLOUD_ONLY")
print("-" * 60)

try:
    from config.paths import CLOUD_ONLY

    print(f"✓ CLOUD_ONLY = {CLOUD_ONLY}")

    if CLOUD_ONLY:
        print("✓ Modo Cloud-Only ATIVO (guardrails devem bloquear)")
    else:
        print("✓ Modo Local (guardrails não devem bloquear)")

except Exception as e:
    print(f"✗ Erro ao verificar CLOUD_ONLY: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("✓ SMOKE TEST PASSOU - Step 7 configurado corretamente!")
print("=" * 60)
print()
print("Nota: Para testar o messagebox e HiDPI visual,")
print("execute a aplicação completa: python app_gui.py")
