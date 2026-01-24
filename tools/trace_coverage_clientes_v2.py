# -*- coding: utf-8 -*-
"""
Trace Coverage - Módulo Clientes (Microfase 12) - V2
Script para executar testes com trace.py (stdlib) e gerar relatórios .cover anotados.
Versão 2: Com filtros para evitar erros de arquivos inexistentes.
"""

from __future__ import annotations

import sys
import trace as trace_module
from pathlib import Path

# ===== CONFIGURAÇÃO =====

# Root do projeto (ajuste conforme necessário)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
TEST_PATH = "tests/modules/clientes/"
COVERAGE_DIR = PROJECT_ROOT / "coverage" / "trace"

# Módulos a serem rastreados (apenas os 5 principais do Clientes)
TRACE_MODULES = [
    "src.modules.clientes.views.toolbar_ctk",
    "src.modules.clientes.views.main_screen_ui_builder",
    "src.modules.clientes.views.footer",
    "src.modules.clientes.views.actionbar_ctk",
    "src.modules.clientes.controllers.pick_mode_manager",
]


def print_header() -> None:
    """Imprime cabeçalho do script."""
    print()
    print("=" * 60)
    print("🔬 TRACE COVERAGE - Módulo Clientes (Microfase 12) V2")
    print("=" * 60)
    print()

    # Garante que PROJECT_ROOT está no sys.path
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    # Cria diretório de coverage se não existir
    COVERAGE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📁 Diretório de coverage: {COVERAGE_DIR.relative_to(PROJECT_ROOT)}")
    print(f"🧪 Executando testes de: {TEST_PATH}")
    print(f"🔍 Rastreando módulos: {len(TRACE_MODULES)}")
    print()


def create_tracer() -> trace_module.Trace:
    """Cria instância do Trace configurada.

    Returns:
        Tracer configurado para contar execuções sem logging verboso.
    """
    import trace

    # Diretórios a serem ignorados (stdlib, venv, site-packages)
    ignore_dirs = [
        sys.base_prefix,  # Python installation dir
        sys.base_exec_prefix,  # Exec prefix (pode ser diferente em venv)
    ]

    # Adiciona .venv se existir
    venv_dir = PROJECT_ROOT / ".venv"
    if venv_dir.exists():
        ignore_dirs.append(str(venv_dir))

    tracer = trace.Trace(
        count=True,  # Conta execuções de linha
        trace=False,  # Não imprime cada linha executada (silencioso)
        ignoredirs=ignore_dirs,  # Ignora stdlib e venv
    )

    return tracer


def run_tests_with_trace(tracer: trace_module.Trace) -> int:
    """Executa pytest com trace ativo.

    Args:
        tracer: Instância do Trace configurada.

    Returns:
        Exit code do pytest (0 = sucesso, >0 = falhas).
    """
    try:
        import pytest
    except ImportError:
        print("❌ pytest não encontrado. Instale com: pip install pytest")
        return 1

    print("🚀 Iniciando testes com trace ativo...")
    print("=" * 60)
    print()

    # Executa pytest programaticamente
    # Nota: pytest.main() retorna exit code (não levanta SystemExit)
    exit_code = tracer.runfunc(
        pytest.main,
        [
            TEST_PATH,
            "-q",  # Quiet mode (menos verbose)
            "--tb=short",  # Traceback curto em caso de erro
            "-v",  # Verbose para mostrar progresso
        ],
    )

    print()
    print("=" * 60)
    print(f"✅ Testes finalizados (exit code: {exit_code})")
    print()

    return exit_code


def generate_coverage_report_safe(tracer: trace_module.Trace) -> None:
    """Gera relatórios de cobertura anotados (.cover) de forma segura.

    Args:
        tracer: Instância do Trace com dados de execução.
    """
    print("📊 Gerando relatórios de cobertura...")
    print()

    # Obtém results do tracer
    results = tracer.results()

    # Filtrar apenas arquivos que existem
    counts = results.counts
    filtered_counts = {}

    for key in counts:
        filepath, _ = key
        if Path(filepath).exists():
            filtered_counts[key] = counts[key]

    # Substituir counts por versão filtrada
    results.counts = filtered_counts

    # Escreve relatórios anotados em coverage/trace/
    # show_missing=True adiciona marcador >>> para linhas não executadas
    # summary=True imprime resumo no stdout
    try:
        results.write_results(
            show_missing=True,
            summary=True,
            coverdir=str(COVERAGE_DIR),
        )
    except FileNotFoundError as exc:
        print(f"⚠️  Arquivo não encontrado (ignorado): {exc}")
    except Exception as exc:
        print(f"⚠️  Erro ao gerar relatórios: {exc}")

    print()
    print("=" * 60)
    print(f"📁 Relatórios salvos em: {COVERAGE_DIR.relative_to(PROJECT_ROOT)}")
    print()
    print("📖 Como interpretar os arquivos .cover:")
    print("   - Linhas com contador (ex: '    5:') foram executadas 5 vezes")
    print("   - Linhas com '>>>>>>>' não foram executadas (gap de cobertura)")
    print("   - Linhas sem contador são comentários/docstrings/vazias")
    print()


def list_generated_reports() -> None:
    """Lista relatórios gerados com tamanhos."""
    print("📄 Relatórios gerados:")
    print()

    cover_files = sorted(COVERAGE_DIR.glob("**/*.cover"))

    if not cover_files:
        print("   ⚠️  Nenhum arquivo .cover encontrado!")
        return

    for file in cover_files:
        # Mostra apenas caminho relativo ao COVERAGE_DIR
        rel = file.relative_to(COVERAGE_DIR)
        size_kb = file.stat().st_size / 1024
        print(f"   📄 {rel} ({size_kb:.1f} KB)")

    print()
    print(f"Total: {len(cover_files)} arquivo(s)")
    print()


def print_footer() -> None:
    """Imprime rodapé com instruções."""
    print("=" * 60)
    print("✨ Coverage trace concluído!")
    print()
    print("📌 Próximos passos:")
    print("   1. Examine arquivos .cover em coverage/trace/")
    print("   2. Busque por linhas com >>>>>>> (gaps)")
    print("   3. Crie testes para cobrir essas linhas")
    print("=" * 60)
    print()


def main() -> int:
    """Entry point principal."""
    print_header()

    tracer = create_tracer()

    exit_code = run_tests_with_trace(tracer)

    generate_coverage_report_safe(tracer)

    list_generated_reports()

    print_footer()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
