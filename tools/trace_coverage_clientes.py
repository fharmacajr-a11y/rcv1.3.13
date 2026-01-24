# -*- coding: utf-8 -*-
"""Script de coverage usando stdlib trace para testes do módulo Clientes.

Este script usa o módulo `trace` da stdlib (Python standard library) para
gerar relatórios de cobertura sem instalar pytest-cov ou coverage.py.

Criado na Microfase 12 (2026-01-14).

Como usar:
1. Abrir este arquivo no VS Code
2. Clicar com botão direito → "Run Python File"
3. Aguardar execução dos testes
4. Verificar relatórios em coverage/trace/

Por que trace?
- Parte da stdlib (zero dependências)
- Gera arquivos .cover anotados com contadores de execução
- Útil para identificar gaps de cobertura rapidamente
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TextIO, cast

if TYPE_CHECKING:
    import trace as trace_module


# ============================================================================
# HELPER: RECONFIGURE UTF-8 (FIX PYLANCE)
# ============================================================================


def _reconfigure_utf8_if_possible(stream: TextIO) -> None:
    """Configura stream para UTF-8 se possível (evita UnicodeEncodeError no Windows).

    Pyright/Pylance: sys.stdout é TextIO em typing, mas em runtime normalmente
    é TextIOWrapper que tem método reconfigure(). Este helper faz cast seguro.

    Args:
        stream: Stream a ser reconfigurado (sys.stdout ou sys.stderr)
    """
    if hasattr(stream, "reconfigure"):
        # Cast para io.TextIOWrapper para satisfazer type checker
        cast(io.TextIOWrapper, stream).reconfigure(encoding="utf-8", errors="replace")


# Configura stdout/stderr para UTF-8 (evita UnicodeEncodeError no Windows)
# Deve ser feito ANTES de qualquer print com caracteres especiais
_reconfigure_utf8_if_possible(sys.stdout)
_reconfigure_utf8_if_possible(sys.stderr)


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

# Diretório raiz do projeto
PROJECT_ROOT = Path(__file__).parent.parent

# Diretório de saída dos relatórios (será criado se não existir)
COVERAGE_DIR = PROJECT_ROOT / "coverage" / "trace"

# Módulos a serem rastreados (foco: views do Clientes)
TRACE_MODULES = [
    "src.modules.clientes.views.actionbar_ctk",
    "src.modules.clientes.views.toolbar_ctk",
    "src.modules.clientes.views.main_screen_ui_builder",
    "src.modules.clientes.views.footer",
    "src.modules.clientes.appearance",
]

# Testes a serem executados
TEST_PATH = "tests/modules/clientes/"


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================


def setup_environment() -> None:
    """Configura ambiente para execução."""
    # Adiciona raiz do projeto ao sys.path (permite imports absolutos)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    # Cria diretório de coverage se não existir
    COVERAGE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"[DIR] Diretorio de coverage: {COVERAGE_DIR.relative_to(PROJECT_ROOT)}")
    print(f"[TEST] Executando testes de: {TEST_PATH}")
    print(f"[TRACE] Rastreando modulos: {len(TRACE_MODULES)}")
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
        print("[ERROR] pytest nao encontrado. Instale com: pip install pytest")
        return 1

    print("[START] Iniciando testes com trace ativo...")
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
    print(f"[OK] Testes finalizados (exit code: {exit_code})")
    print()

    return exit_code


def generate_coverage_report(tracer: trace_module.Trace) -> None:
    """Gera relatórios de cobertura anotados (.cover).

    Args:
        tracer: Instância do Trace com dados de execução.
    """
    print("[REPORT] Gerando relatorios de cobertura...")
    print()

    # Obtém results do tracer
    results = tracer.results()

    # Escreve relatórios anotados em coverage/trace/
    # show_missing=True adiciona marcador >>> para linhas não executadas
    # summary=True imprime resumo no stdout
    results.write_results(
        show_missing=True,
        summary=True,
        coverdir=str(COVERAGE_DIR),
    )

    print()
    print("=" * 60)
    print(f"[SAVE] Relatorios salvos em: {COVERAGE_DIR.relative_to(PROJECT_ROOT)}")
    print()
    print("[INFO] Como interpretar os arquivos .cover:")
    print("   - Linhas com contador (ex: '    5:') foram executadas 5 vezes")
    print("   - Linhas com '>>>>>>>' não foram executadas (gap de cobertura)")
    print("   - Linhas sem contador são comentários/docstrings/vazias")
    print()


def list_generated_reports() -> None:
    """Lista relatórios gerados com tamanhos."""
    print("[FILES] Relatorios gerados:")
    print()

    cover_files = sorted(COVERAGE_DIR.glob("**/*.cover"))

    if not cover_files:
        print("   [WARN] Nenhum arquivo .cover encontrado!")
        return

    for cover_file in cover_files:
        # Calcula path relativo ao PROJECT_ROOT
        try:
            rel_path = cover_file.relative_to(PROJECT_ROOT)
        except ValueError:
            rel_path = cover_file

        # Tamanho em KB
        size_kb = cover_file.stat().st_size / 1024

        print(f"   - {rel_path} ({size_kb:.1f} KB)")

    print()
    print(f"Total: {len(cover_files)} arquivo(s)")


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:
    """Execução principal do script.

    Returns:
        Exit code (0 = sucesso, >0 = erro).
    """
    print()
    print("=" * 60)
    print("[TRACE] TRACE COVERAGE - Modulo Clientes (Microfase 12)")
    print("=" * 60)
    print()

    # Setup
    setup_environment()

    # Cria tracer
    tracer = create_tracer()

    # Executa testes com trace
    exit_code = run_tests_with_trace(tracer)

    # Gera relatórios
    generate_coverage_report(tracer)

    # Lista arquivos gerados
    list_generated_reports()

    print("=" * 60)
    print("[DONE] Processo concluido!")
    print("=" * 60)
    print()

    # Retorna exit code do pytest (não levanta SystemExit)
    return exit_code


if __name__ == "__main__":
    # Executa e retorna exit code
    sys.exit(main())
