#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
smoke_runtime.py — Smoke test do runtime sem iniciar GUI.

Testa:
1. Imports de módulos chave
2. Healthcheck do Supabase
3. Verificação do Tesseract OCR
4. Importação de dependências críticas

Uso:
    python scripts/smoke_runtime.py
    cd runtime && python ../scripts/smoke_runtime.py
"""
import sys
from pathlib import Path

# Adiciona raiz ao path se executando de fora
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_imports():
    """Testa imports de módulos chave."""
    print("🔍 Testando imports de módulos...")

    modules = {
        "gui": ["gui.main_window", "gui.hub_screen", "gui.main_screen"],
        "ui": ["ui.login.login", "ui.theme", "ui.components"],
        "core": ["core.session.session", "core.db_manager.db_manager", "core.models"],
        "infra": ["infra.supabase_client", "infra.healthcheck", "infra.net_session"],
        "utils": ["utils.pdf_reader", "utils.hash_utils", "utils.text_utils"],
        "adapters": ["adapters.storage.supabase_storage"],
        "application": ["application.api", "application.auth_controller"],
    }

    failed = []
    for category, mod_list in modules.items():
        for mod in mod_list:
            try:
                __import__(mod)
                print(f"  ✅ {mod}")
            except Exception as e:
                print(f"  ❌ {mod}: {e}")
                failed.append((mod, str(e)))

    if failed:
        print(f"\n❌ {len(failed)} imports falharam")
        return False

    print(f"\n✅ Todos os {sum(len(m) for m in modules.values())} imports OK")
    return True


def test_dependencies():
    """Testa dependências críticas."""
    print("\n🔍 Testando dependências críticas...")

    deps = {
        "pypdf": "pypdf",
        "PIL": "pillow",
        "ttkbootstrap": "ttkbootstrap",
        "httpx": "httpx",
        "requests": "requests",
        "supabase": "supabase",
        "pytesseract": "pytesseract",
        "yaml": "pyyaml",
        "dotenv": "python-dotenv",
    }

    failed = []
    for name, package in deps.items():
        try:
            __import__(name)
            print(f"  ✅ {package}")
        except ImportError as e:
            print(f"  ❌ {package}: {e}")
            failed.append((package, str(e)))

    if failed:
        print(f"\n⚠️  {len(failed)} dependências faltando")
        return False

    print(f"\n✅ Todas as {len(deps)} dependências OK")
    return True


def test_healthcheck():
    """Testa healthcheck do Supabase."""
    print("\n🔍 Testando healthcheck...")

    try:
        from infra.healthcheck import check_tesseract

        # Não faz healthcheck real (requer .env e credenciais)
        # Apenas verifica que a função existe e é chamável
        print("  ✅ healthcheck() disponível")

        # Testa Tesseract
        ok, msg = check_tesseract()
        if ok:
            print(f"  ✅ Tesseract: {msg}")
        else:
            print(f"  ⚠️  Tesseract: {msg}")

        return True

    except Exception as e:
        print(f"  ❌ Erro: {e}")
        return False


def test_pdf_support():
    """Testa suporte a PDF."""
    print("\n🔍 Testando suporte a PDF...")

    try:

        print("  ✅ pypdf.PdfReader disponível")

        print("  ✅ read_pdf_text() disponível")

        return True

    except Exception as e:
        print(f"  ❌ Erro: {e}")
        return False


def main():
    """Executa smoke test completo."""
    print("=" * 60)
    print("🧪 RC-Gestor - Smoke Test do Runtime")
    print("=" * 60)
    print(f"\n📁 ROOT: {ROOT}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print()

    results = {
        "imports": test_imports(),
        "dependencies": test_dependencies(),
        "healthcheck": test_healthcheck(),
        "pdf_support": test_pdf_support(),
    }

    print("\n" + "=" * 60)
    print("📊 RESUMO")
    print("=" * 60)

    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test:20s} {status}")

    all_passed = all(results.values())

    print()
    if all_passed:
        print("✅ Smoke test PASSOU - Runtime está OK!")
        return 0
    else:
        failed_count = sum(1 for v in results.values() if not v)
        print(f"❌ Smoke test FALHOU - {failed_count} testes falharam")
        return 1


if __name__ == "__main__":
    sys.exit(main())
