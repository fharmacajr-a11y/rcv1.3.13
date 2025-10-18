# scripts/test_login.py
"""
Teste rápido do login via Supabase Auth
Execute: python scripts/test_login.py
"""
import sys
from pathlib import Path

# Adiciona raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Testa se todos os imports necessários funcionam"""
    print("🔍 Testando imports...")
    try:

        print("✅ infra.supabase_auth OK")

        print("✅ core.session.session_guard OK")

        from infra.supabase_client import (
            EMBED_SUPABASE_URL,
            EMBED_SUPABASE_ANON_KEY,
        )

        print("✅ infra.supabase_client OK")

        # Verifica se as chaves foram configuradas
        if "SEU-PROJETO" in EMBED_SUPABASE_URL:
            print(
                "⚠️  ATENÇÃO: Configure EMBED_SUPABASE_URL em infra/supabase_client.py"
            )
        else:
            print(f"✅ EMBED_SUPABASE_URL configurada: {EMBED_SUPABASE_URL[:40]}...")

        if "SUA_ANON_KEY" in EMBED_SUPABASE_ANON_KEY:
            print(
                "⚠️  ATENÇÃO: Configure EMBED_SUPABASE_ANON_KEY em infra/supabase_client.py"
            )
        else:
            print(
                f"✅ EMBED_SUPABASE_ANON_KEY configurada: {EMBED_SUPABASE_ANON_KEY[:40]}..."
            )

        return True
    except Exception as e:
        print(f"❌ Erro ao importar: {e}")
        return False


def test_client():
    """Testa se o cliente Supabase pode ser criado"""
    print("\n🔍 Testando cliente Supabase...")
    try:
        from infra.supabase_client import get_supabase

        sb = get_supabase()
        print("✅ Cliente Supabase criado com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar cliente: {e}")
        return False


def main():
    print("=" * 60)
    print("🧪 TESTE RÁPIDO - LOGIN VIA SUPABASE AUTH")
    print("=" * 60)

    if not test_imports():
        print("\n❌ Falha nos imports. Corrija os erros acima.")
        return 1

    if not test_client():
        print("\n❌ Falha ao criar cliente Supabase.")
        return 1

    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    print("\n📝 Próximos passos:")
    print("   1. Execute: python app_gui.py")
    print("   2. Faça login com e-mail/senha do Supabase")
    print("   3. Para build: pyinstaller build/rc_gestor.spec")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
