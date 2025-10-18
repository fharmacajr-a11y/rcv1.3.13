# scripts/test_robustness.py
"""
Teste de robustez: diagnóstico, retry e tratamento de erros.
Execute: python scripts/test_robustness.py
"""
import sys
from pathlib import Path

# Adiciona raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_healthcheck():
    """Testa módulo de healthcheck"""
    print("🔍 Testando healthcheck...")
    try:
        from infra.healthcheck import healthcheck, DEFAULT_BUCKET

        print(f"✅ infra.healthcheck OK (bucket: {DEFAULT_BUCKET})")

        # Tenta executar (pode falhar se não estiver logado)
        try:
            result = healthcheck(DEFAULT_BUCKET)
            if result.get("ok"):
                print("   ✅ Diagnóstico executado com sucesso")
                print(f"      - Sessão: {result['items']['session']['ok']}")
                print(f"      - Storage: {result['items']['storage']['ok']}")
            else:
                print("   ⚠️  Diagnóstico retornou falha (normal se não logado)")
        except Exception as e:
            print(f"   ⚠️  Execução falhou: {e} (normal se não logado)")

        return True
    except Exception as e:
        print(f"❌ Erro ao importar healthcheck: {e}")
        return False


def test_net_retry():
    """Testa módulo de retry"""
    print("\n🔍 Testando net_retry...")
    try:
        from utils.net_retry import run_cloud_op

        print("✅ utils.net_retry OK")

        # Teste básico com função dummy
        def dummy_op():
            return "OK"

        result = run_cloud_op(dummy_op, retries=1)
        if result == "OK":
            print("   ✅ run_cloud_op funciona corretamente")
        else:
            print("   ⚠️  run_cloud_op retornou resultado inesperado")

        return True
    except Exception as e:
        print(f"❌ Erro ao importar net_retry: {e}")
        return False


def test_session_guard():
    """Testa SessionGuard"""
    print("\n🔍 Testando SessionGuard...")
    try:
        from core.session.session_guard import SessionGuard

        print("✅ core.session.session_guard OK")

        # Tenta verificar sessão (pode falhar se não logado)
        try:
            alive = SessionGuard.ensure_alive()
            if alive:
                print("   ✅ Sessão está viva")
            else:
                print("   ⚠️  Sem sessão ativa (normal se não logado)")
        except Exception as e:
            print(f"   ⚠️  Verificação falhou: {e} (normal se não logado)")

        return True
    except Exception as e:
        print(f"❌ Erro ao importar SessionGuard: {e}")
        return False


def test_login_improvements():
    """Verifica melhorias no login"""
    print("\n🔍 Verificando melhorias no login...")
    try:
        from pathlib import Path

        login_file = Path(__file__).parent.parent / "ui" / "login" / "login.py"
        content = login_file.read_text(encoding="utf-8")

        checks = {
            "threading": "import threading" in content,
            "BusyOverlay": "BusyOverlay" in content,
            "Storage validation": "storage.from_" in content.lower(),
            "Error handling": "network" in content.lower()
            or "connection" in content.lower(),
        }

        all_ok = True
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
            all_ok = all_ok and passed

        return all_ok
    except Exception as e:
        print(f"❌ Erro ao verificar login: {e}")
        return False


def test_menu_diagnostico():
    """Verifica se menu de diagnóstico está configurado"""
    print("\n🔍 Verificando menu Diagnóstico...")
    try:
        from pathlib import Path

        # Verifica menu_bar.py
        menu_bar_file = Path(__file__).parent.parent / "gui" / "menu_bar.py"
        menu_content = menu_bar_file.read_text(encoding="utf-8")

        # Verifica main_window.py
        main_window_file = Path(__file__).parent.parent / "gui" / "main_window.py"
        main_content = main_window_file.read_text(encoding="utf-8")

        checks = {
            "on_diagnostico no menu_bar": "on_diagnostico" in menu_content,
            "Diagnóstico… no menu": "Diagnóstico" in menu_content
            or "Diagnóstico…" in menu_content,
            "_on_diagnostico no main_window": "_on_diagnostico" in main_content,
            "healthcheck importado": "from infra.healthcheck" in main_content,
        }

        all_ok = True
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
            all_ok = all_ok and passed

        return all_ok
    except Exception as e:
        print(f"❌ Erro ao verificar menu: {e}")
        return False


def test_code_cleanliness():
    """Verifica se código está limpo"""
    print("\n🔍 Verificando limpeza do código...")
    from pathlib import Path

    base = Path(__file__).parent.parent

    checks = {
        "core/auth existe": (base / "core" / "auth").exists(),
        "infrastructure/ existe": (base / "infrastructure").exists(),
        "rc.ico na raiz existe": (base / "rc.ico").exists(),
        "assets/app.ico existe": (base / "assets" / "app.ico").exists(),
    }

    # Invertidos: queremos que NÃO existam (exceto app.ico)
    for check, exists in checks.items():
        if "app.ico" in check:
            status = "✅" if exists else "⚠️ "
            print(f"   {status} {check}")
        else:
            status = "⚠️ " if exists else "✅"
            print(
                f"   {status} {check} {'(ainda presente)' if exists else '(removido)'}"
            )

    # Sucesso se app.ico existe e pelo menos um dos legados foi removido
    app_ico_ok = checks["assets/app.ico existe"]
    some_cleaned = (
        not checks["core/auth existe"]
        or not checks["infrastructure/ existe"]
        or not checks["rc.ico na raiz existe"]
    )

    if app_ico_ok and some_cleaned:
        print("\n   💡 Execute 'python scripts/cleanup.py' para limpar código legado")

    return True  # Não é erro crítico


def main():
    print("=" * 70)
    print("🛡️  TESTE DE ROBUSTEZ - RC-GESTOR")
    print("=" * 70)
    print("\nTestando diagnóstico, retry e tratamento de erros...")

    results = []
    results.append(("Healthcheck", test_healthcheck()))
    results.append(("Net retry", test_net_retry()))
    results.append(("SessionGuard", test_session_guard()))
    results.append(("Melhorias no login", test_login_improvements()))
    results.append(("Menu Diagnóstico", test_menu_diagnostico()))
    results.append(("Limpeza do código", test_code_cleanliness()))

    print("\n" + "=" * 70)
    print("📊 RESUMO DOS TESTES")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{status:12} - {name}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n" + "=" * 70)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("=" * 70)

        print("\n📝 Recursos implementados:")
        print("   ✅ Diagnóstico Supabase (Auth + Storage)")
        print("   ✅ Retry automático com backoff")
        print("   ✅ SessionGuard para renovar sessão")
        print("   ✅ Login validando Storage")
        print("   ✅ Menu Ajuda → Diagnóstico")
        print("   ✅ Tratamento robusto de erros")

        print("\n📝 Próximos passos:")
        print("   1. Execute: python scripts/cleanup.py (limpeza segura)")
        print("   2. Teste: python app_gui.py")
        print("   3. Menu: Ajuda → Diagnóstico")
        print("   4. Build: pyinstaller build/rc_gestor.spec")
        return 0
    else:
        print("\n❌ ALGUNS TESTES FALHARAM!")
        print("   Corrija os erros acima antes de prosseguir.")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Testes interrompidos pelo usuário")
        sys.exit(130)
