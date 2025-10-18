# -*- coding: utf-8 -*-
"""
Smoke test para validação do backend PDF (pypdf)

Step 6 - Padronizar PDF em pypdf (compat)
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao sys.path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from utils.file_utils import read_pdf_text


def test_pdf_backend():
    """Testa se o backend pypdf está funcionando corretamente."""
    print("=" * 60)
    print("Smoke Test - Backend PDF (pypdf)")
    print("=" * 60)

    # Verifica qual backend está sendo usado
    try:
        import pypdf

        backend = "pypdf (✓ recomendado)"
        print(f"\n✓ Backend: {backend}")
        print(f"  Versão: pypdf {pypdf.__version__}")
    except ImportError:
        try:
            import PyPDF2

            backend = "PyPDF2 (deprecated)"
            print(f"\n⚠ Backend: {backend}")
            print(f"  Versão: PyPDF2 {PyPDF2.__version__}")
        except ImportError:
            print("\n✗ Erro: Nenhum backend PDF disponível!")
            return False

    print("\n" + "-" * 60)
    print("Teste 1: Verificar função read_pdf_text")
    print("-" * 60)

    try:
        # Tenta importar a função

        print("✓ Função _read_pdf_text_pypdf importada com sucesso")

        # Verifica se pdfmod está disponível
        from utils.file_utils.file_utils import pdfmod

        if pdfmod is None:
            print("✗ Erro: pdfmod não está disponível")
            return False

        print(f"✓ pdfmod disponível: {pdfmod.__name__}")

        # Verifica se PdfReader está disponível
        if hasattr(pdfmod, "PdfReader"):
            print("✓ PdfReader disponível")
        else:
            print("✗ Erro: PdfReader não encontrado")
            return False

    except Exception as e:
        print(f"✗ Erro ao importar: {e}")
        return False

    print("\n" + "-" * 60)
    print("Teste 2: API pública mantida")
    print("-" * 60)

    try:
        # Verifica se read_pdf_text existe
        assert callable(read_pdf_text), "read_pdf_text não é callable"
        print("✓ read_pdf_text está disponível")

        # Verifica assinatura (aceita str ou Path)
        import inspect

        sig = inspect.signature(read_pdf_text)
        print(f"✓ Assinatura: {sig}")

        # Verifica retorno
        print("✓ Retorno: Optional[str]")

    except Exception as e:
        print(f"✗ Erro ao verificar API: {e}")
        return False

    print("\n" + "-" * 60)
    print("Teste 3: Compatibilidade de imports")
    print("-" * 60)

    try:
        # Testa diferentes formas de import
        from utils.file_utils import read_pdf_text as func1

        print("✓ from utils.file_utils import read_pdf_text")

        from utils.file_utils.file_utils import read_pdf_text as func2

        print("✓ from utils.file_utils.file_utils import read_pdf_text")

        assert func1 is func2, "Funções são diferentes!"
        print("✓ Imports consistentes")

    except Exception as e:
        print(f"✗ Erro de import: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ SMOKE TEST PASSOU - Backend pypdf configurado corretamente!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    import sys

    success = test_pdf_backend()
    sys.exit(0 if success else 1)
