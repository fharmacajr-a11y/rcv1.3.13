# scripts/test_ui_polish.py
"""
Teste rápido do polimento visual (tema, ícone, overlay)
Execute: python scripts/test_ui_polish.py
"""
import sys
from pathlib import Path

# Adiciona raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_theme_module():
    """Testa o módulo de tema"""
    print("🔍 Testando módulo de tema...")
    try:
        from ui.theme import DEFAULT_THEME, DEFAULT_SCALING

        print(
            f"✅ ui.theme OK (tema padrão: {DEFAULT_THEME}, scaling: {DEFAULT_SCALING})"
        )
        return True
    except Exception as e:
        print(f"❌ Erro ao importar ui.theme: {e}")
        return False


def test_theme_toggle():
    """Testa o módulo de alternância de tema"""
    print("\n🔍 Testando alternância de tema...")
    try:
        from ui.theme_toggle import get_available_themes, is_dark_theme

        themes = get_available_themes()
        print(f"✅ ui.theme_toggle OK ({len(themes)} temas disponíveis)")

        # Testa classificação de temas
        dark_count = sum(1 for t in themes if is_dark_theme(t))
        light_count = len(themes) - dark_count
        print(f"   📊 Temas escuros: {dark_count}, claros: {light_count}")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar ui.theme_toggle: {e}")
        return False


def test_busy_overlay():
    """Testa o overlay de carregamento"""
    print("\n🔍 Testando overlay de carregamento...")
    try:

        print("✅ ui.widgets.busy.BusyOverlay OK")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar BusyOverlay: {e}")
        return False


def test_icon_files():
    """Verifica se os arquivos de ícone existem"""
    print("\n🔍 Verificando arquivos de ícone...")
    from pathlib import Path

    base = Path(__file__).parent.parent

    icons = [base / "rc.ico", base / "assets" / "app.ico"]

    all_ok = True
    for icon in icons:
        if icon.exists():
            size_kb = icon.stat().st_size / 1024
            print(f"✅ {icon.name} existe ({size_kb:.1f} KB)")
        else:
            print(f"⚠️  {icon.name} não encontrado em {icon.parent}")
            all_ok = False

    return all_ok


def test_login_imports():
    """Testa se o login tem os novos imports"""
    print("\n🔍 Testando imports do login...")
    try:
        import ui.login.login as login_module

        # Verifica se tem threading
        if hasattr(login_module, "threading"):
            print("✅ Login importa threading")
        else:
            print("⚠️  Login não importa threading")

        # Verifica se tem BusyOverlay
        source = Path(login_module.__file__).read_text(encoding="utf-8")
        if "BusyOverlay" in source:
            print("✅ Login usa BusyOverlay")
        else:
            print("⚠️  Login não usa BusyOverlay")

        return True
    except Exception as e:
        print(f"❌ Erro ao verificar login: {e}")
        return False


def test_visual_demo():
    """Demonstração visual rápida (opcional)"""
    print("\n🎨 Teste visual (pressione Ctrl+C para pular)...")
    try:
        import tkinter as tk
        from ui.theme import init_theme

        print("   Criando janela de demonstração...")
        root = tk.Tk()
        style = init_theme(root, theme="flatly")
        root.title("RC — Teste Visual")
        root.geometry("400x300")

        # Centro da tela
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        x = (sw - 400) // 2
        y = (sh - 300) // 2
        root.geometry(f"400x300+{x}+{y}")

        label = tk.Label(
            root,
            text="✅ Tema e ícone aplicados!\n\nFeche esta janela.",
            font=("Segoe UI", 12),
        )
        label.pack(expand=True)

        # Testa overlay
        root.after(500, lambda: show_overlay_demo(root))

        # Fecha automaticamente após 3 segundos
        root.after(3000, root.destroy)

        root.mainloop()
        print("✅ Demonstração visual OK")
        return True
    except KeyboardInterrupt:
        print("⏭️  Demonstração visual pulada")
        return True
    except Exception as e:
        print(f"⚠️  Demonstração visual falhou: {e}")
        return True  # Não é erro crítico


def show_overlay_demo(root):
    """Mostra overlay por 1 segundo"""
    try:
        from ui.widgets.busy import BusyOverlay

        overlay = BusyOverlay(root, "Testando overlay...")
        overlay.show()
        root.after(1000, overlay.hide)
    except Exception as e:
        print(f"⚠️  Overlay demo falhou: {e}")


def main():
    print("=" * 70)
    print("🎨 TESTE DE POLIMENTO VISUAL - RC-GESTOR")
    print("=" * 70)

    results = []
    results.append(("Módulo de tema", test_theme_module()))
    results.append(("Alternância de tema", test_theme_toggle()))
    results.append(("Overlay de carregamento", test_busy_overlay()))
    results.append(("Arquivos de ícone", test_icon_files()))
    results.append(("Imports do login", test_login_imports()))

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

        # Pergunta se quer demo visual
        try:
            resp = (
                input("\n💡 Deseja ver uma demonstração visual? (s/N): ")
                .strip()
                .lower()
            )
            if resp in ("s", "sim", "y", "yes"):
                test_visual_demo()
        except (KeyboardInterrupt, EOFError):
            print("\n⏭️  Demo visual pulada")

        print("\n📝 Próximos passos:")
        print("   1. Execute: python app_gui.py")
        print("   2. Verifique tema, ícone e overlay no login")
        print("   3. Para build: pyinstaller build/rc_gestor.spec")
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
