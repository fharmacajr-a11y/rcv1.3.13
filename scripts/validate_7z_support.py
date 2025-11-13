"""
Script de validação para suporte .7z no módulo Auditoria.
Execute este script para verificar se tudo está configurado corretamente.
"""

import sys
from pathlib import Path


def check_python_version():
    """Verifica se a versão do Python é compatível."""
    version = sys.version_info
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("  ⚠️ AVISO: Python 3.9+ recomendado (você tem {}.{})".format(
            version.major, version.minor
        ))
        return False
    return True


def check_py7zr():
    """Verifica se py7zr está instalado."""
    try:
        import py7zr
        print(f"✓ py7zr {py7zr.__version__} instalado")
        return True
    except ImportError:
        print("✗ py7zr NÃO instalado")
        print("  Execute: pip install py7zr")
        return False


def check_dependencies():
    """Verifica dependências essenciais."""
    deps = {
        "ttkbootstrap": ("Interface gráfica", True),
        "supabase": ("Cliente Supabase", True),
        "PyMuPDF": ("Visualização de PDFs", False),  # Opcional
        "pathlib": ("Manipulação de paths (built-in)", True),
        "tempfile": ("Arquivos temporários (built-in)", True),
        "zipfile": ("Suporte a ZIP (built-in)", True),
    }

    all_ok = True
    for module, (desc, required) in deps.items():
        try:
            __import__(module)
            print(f"✓ {module} — {desc}")
        except ImportError:
            if required:
                print(f"✗ {module} — {desc} NÃO instalado")
                all_ok = False
            else:
                print(f"⚠️ {module} — {desc} NÃO instalado (opcional)")

    return all_ok


def check_files():
    """Verifica arquivos essenciais do projeto."""
    files = [
        "src/modules/auditoria/view.py",
        "pyrightconfig.json",
        "requirements.txt",
        "INSTALACAO.md",
    ]

    all_ok = True
    for file in files:
        path = Path(file)
        if path.exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} NÃO encontrado")
            all_ok = False

    return all_ok


def check_py7zr_in_requirements():
    """Verifica se py7zr está em requirements.txt."""
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("✗ requirements.txt não encontrado")
        return False

    content = req_file.read_text(encoding="utf-8")
    if "py7zr" in content:
        print("✓ py7zr listado em requirements.txt")
        return True
    else:
        print("✗ py7zr NÃO está em requirements.txt")
        print("  Adicione: py7zr>=0.21.0")
        return False


def check_import_in_view():
    """Verifica se o import do py7zr está correto em view.py."""
    view_file = Path("src/modules/auditoria/view.py")
    if not view_file.exists():
        print("✗ src/modules/auditoria/view.py não encontrado")
        return False

    content = view_file.read_text(encoding="utf-8")

    # Verifica import com type: ignore
    if "import py7zr  # type: ignore[import]" in content:
        print("✓ Import py7zr com type: ignore[import]")
    elif "import py7zr" in content:
        print("⚠️ Import py7zr SEM type: ignore (pode gerar warning)")
    else:
        print("✗ Import py7zr NÃO encontrado em view.py")
        return False

    # Verifica uso da API correta
    if "SevenZipFile" in content and "extractall" in content:
        print("✓ API py7zr.SevenZipFile.extractall() detectada")
    else:
        print("⚠️ Uso da API py7zr não detectado")

    return True


def test_py7zr_extraction():
    """Testa extração de um arquivo .7z simples (se py7zr estiver instalado)."""
    try:
        import py7zr
        import tempfile

        # Cria um .7z em memória para teste
        with tempfile.TemporaryDirectory() as tmpd:
            test_file = Path(tmpd) / "test.txt"
            test_file.write_text("Teste de extração py7zr")

            # Comprime
            archive_path = Path(tmpd) / "test.7z"
            with py7zr.SevenZipFile(archive_path, mode="w") as z:
                z.write(test_file, arcname="test.txt")

            # Extrai
            extract_dir = Path(tmpd) / "extracted"
            extract_dir.mkdir()
            with py7zr.SevenZipFile(archive_path, mode="r") as z:
                z.extractall(extract_dir)

            # Valida
            extracted_file = extract_dir / "test.txt"
            if extracted_file.exists():
                content = extracted_file.read_text()
                if content == "Teste de extração py7zr":
                    print("✓ Teste de extração .7z PASSOU")
                    return True

        print("✗ Teste de extração .7z FALHOU")
        return False

    except Exception as e:
        print(f"✗ Teste de extração .7z FALHOU: {e}")
        return False


def main():
    """Executa todos os checks."""
    print("=" * 60)
    print("VALIDAÇÃO DO SUPORTE .7z — MÓDULO AUDITORIA")
    print("=" * 60)
    print()

    results = []

    print("1️⃣ Verificando Python...")
    results.append(check_python_version())
    print()

    print("2️⃣ Verificando py7zr...")
    results.append(check_py7zr())
    print()

    print("3️⃣ Verificando dependências...")
    results.append(check_dependencies())
    print()

    print("4️⃣ Verificando arquivos do projeto...")
    results.append(check_files())
    print()

    print("5️⃣ Verificando requirements.txt...")
    results.append(check_py7zr_in_requirements())
    print()

    print("6️⃣ Verificando view.py...")
    results.append(check_import_in_view())
    print()

    print("7️⃣ Testando extração .7z...")
    results.append(test_py7zr_extraction())
    print()

    print("=" * 60)
    passed = sum(results)
    total = len(results)

    if all(results):
        print(f"✅ TODOS OS TESTES PASSARAM ({passed}/{total})")
        print()
        print("🎉 O suporte a .7z está corretamente configurado!")
        print("   Você pode usar arquivos .zip e .7z no módulo Auditoria.")
        return 0
    else:
        print(f"⚠️ ALGUNS TESTES FALHARAM ({passed}/{total})")
        print()
        print("📝 Resolva os problemas acima e execute novamente:")
        print("   python scripts/validate_7z_support.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
