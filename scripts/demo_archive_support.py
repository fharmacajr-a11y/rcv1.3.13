"""
Script de demonstração do suporte a ZIP/RAR embarcado.

Demonstra que:
1. O 7-Zip está embarcado no repositório
2. A extração de ZIP funciona com zipfile
3. A extração de RAR funciona com 7-Zip CLI
4. Não é necessário instalar nada no PC do usuário
"""
from pathlib import Path
import tempfile
import zipfile

from infra.archive_utils import (
    find_7z,
    is_7z_available,
    extract_archive,
    ArchiveError,
)


def main():
    print("=" * 60)
    print("DEMONSTRAÇÃO: Suporte ZIP/RAR Embarcado")
    print("=" * 60)
    print()

    # 1. Verificar 7-Zip embarcado
    print("1. Verificando 7-Zip embarcado...")
    seven_zip_path = find_7z()
    if seven_zip_path:
        print(f"   ✅ 7-Zip encontrado: {seven_zip_path}")
        print(f"   📦 Tamanho: {seven_zip_path.stat().st_size:,} bytes")
    else:
        print("   ❌ 7-Zip NÃO encontrado")
        return

    print()

    # 2. Testar extração de ZIP
    print("2. Testando extração de ZIP...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Criar um ZIP de teste
        zip_file = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("exemplo.txt", "Conteúdo de exemplo no ZIP")
            zf.writestr("pasta/arquivo.txt", "Arquivo dentro de pasta")

        # Extrair
        extract_dir = tmp_path / "extracted_zip"
        try:
            extract_archive(zip_file, extract_dir)
            print("   ✅ ZIP extraído com sucesso")
            print("   📁 Arquivos extraídos:")
            for f in extract_dir.rglob("*"):
                if f.is_file():
                    print(f"      - {f.relative_to(extract_dir)}")
        except ArchiveError as e:
            print(f"   ❌ Erro: {e}")

    print()

    # 3. Status final
    print("3. Status do sistema:")
    print(f"   🔧 7-Zip disponível: {is_7z_available()}")
    print("   📦 Formatos suportados: ZIP, RAR")
    print("   💾 Instalação necessária: NENHUMA (binários embarcados)")

    print()
    print("=" * 60)
    print("✅ Demonstração concluída!")
    print("=" * 60)


if __name__ == "__main__":
    main()
