# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO AUTOMÁTICO — Módulo Clientes
Gera 5 arquivos de diagnóstico para análise de ambiente, coverage e testes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

# ===== CONFIGURAÇÃO =====

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DIAGNOSTICS_DIR = PROJECT_ROOT / "diagnostics" / "clientes"

# ===== UTILITÁRIOS =====


def ensure_diagnostics_dir() -> None:
    """Cria diretório diagnostics/clientes/ se não existir."""
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Diretório de diagnóstico: {DIAGNOSTICS_DIR.relative_to(PROJECT_ROOT)}")
    print()


def write_section(file_path: Path, title: str, content: str) -> None:
    """Escreve seção em arquivo de diagnóstico."""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"{title}\n")
        f.write("=" * 80 + "\n")
        f.write(content)
        f.write("\n\n")


def write_file(file_path: Path, content: str) -> None:
    """Escreve conteúdo completo em arquivo."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


# ===== DIAGNÓSTICO 1: AMBIENTE PYTHON =====


def diagnose_python_env() -> None:
    """Gera 01_python_env.txt com informações do ambiente Python."""
    print("🔍 [1/5] Diagnosticando ambiente Python...")

    output_file = DIAGNOSTICS_DIR / "01_python_env.txt"

    try:
        # Limpa arquivo
        write_file(output_file, "")

        # Seção 1: Executável Python
        content = f"Executável: {sys.executable}\n"
        content += f"Versão: {sys.version}\n"
        content += f"Plataforma: {sys.platform}\n"
        write_section(output_file, "EXECUTÁVEL PYTHON", content)

        # Seção 2: Prefixos
        content = f"sys.prefix: {sys.prefix}\n"
        content += f"sys.base_prefix: {sys.base_prefix}\n"
        content += f"sys.exec_prefix: {sys.exec_prefix}\n"
        content += f"sys.base_exec_prefix: {sys.base_exec_prefix}\n"
        write_section(output_file, "PREFIXOS", content)

        # Seção 3: sys.path
        content = "sys.path:\n"
        for i, path in enumerate(sys.path, 1):
            content += f"  [{i}] {path}\n"
        write_section(output_file, "SYS.PATH", content)

        # Seção 4: Variáveis de ambiente
        content = ""
        env_vars = ["VIRTUAL_ENV", "CONDA_PREFIX", "PYTHONPATH", "PYTHONHOME"]
        for var in env_vars:
            value = os.environ.get(var, "<não definida>")
            content += f"{var}: {value}\n"
        write_section(output_file, "VARIÁVEIS DE AMBIENTE", content)

        # Seção 5: CustomTkinter
        content = ""
        try:
            from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

            if HAS_CUSTOMTKINTER:
                content += "✅ customtkinter importado com sucesso (via ctk_config SSoT)\n"
                if ctk and hasattr(ctk, "__file__"):
                    content += f"Arquivo: {ctk.__file__}\n\n"

                # Tenta obter versão
                version = getattr(ctk, "__version__", None) if ctk else None
                if version:
                    content += f"Versão (__version__): {version}\n"
                else:
                    content += "Versão (__version__): <não encontrada>\n"

                # Tenta via importlib.metadata
                try:
                    import importlib.metadata

                    version_metadata = importlib.metadata.version("customtkinter")
                    content += f"Versão (metadata): {version_metadata}\n"
                except Exception as e:
                    content += f"Versão (metadata): <falha ao obter: {e}>\n"
            else:
                content += "❌ customtkinter NÃO disponível (HAS_CUSTOMTKINTER=False)\n"

        except ImportError:
            content += "❌ customtkinter NÃO importado\n"

        # Seção 6: Verificação de Interpreter (VS Code vs sys.executable)
        content = ""
        content += "=== VALIDAÇÃO DE AMBIENTE ===\n\n"

        # Caminho atual do sys.executable
        current_exec = Path(sys.executable).resolve()
        content += f"Interpreter ATUAL (sys.executable):\n  {current_exec}\n\n"

        # Tenta carregar settings.json do VS Code
        settings_file = PROJECT_ROOT / ".vscode" / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)

                vscode_python = settings.get("python.defaultInterpreterPath", "<não configurado>")
                content += f"VS Code settings.json (python.defaultInterpreterPath):\n  {vscode_python}\n\n"

                # Verifica se é .venv
                if ".venv" in str(vscode_python).lower() or "${workspaceFolder}/.venv" in str(vscode_python):
                    # Verifica se sys.executable também é .venv
                    if ".venv" not in str(current_exec).lower():
                        content += "⚠️  ALERTA: VS Code aponta para .venv, mas sys.executable NÃO é .venv!\n"
                        content += "   Possível causa: Script rodou com Python global em vez do .venv\n"
                        content += "   Solução: Ativar .venv antes de rodar o script\n"
                        content += f"     Windows: {PROJECT_ROOT}\\.venv\\Scripts\\activate\n"
                        content += f"     Unix/Mac: source {PROJECT_ROOT}/.venv/bin/activate\n\n"
                    else:
                        content += "✅ OK: sys.executable está usando .venv conforme configurado no VS Code\n\n"
                else:
                    content += "ℹ️  VS Code não aponta para .venv (ou variável não resolvida)\n\n"

            except Exception as e:
                content += f"⚠️  Erro ao ler settings.json: {e}\n\n"
        else:
            content += "ℹ️  Arquivo .vscode/settings.json não encontrado\n\n"

        write_section(output_file, "VALIDAÇÃO DE INTERPRETER", content)

        print(f"   ✅ Salvo em: {output_file.relative_to(PROJECT_ROOT)}")

    except Exception:
        error_content = f"❌ ERRO ao gerar diagnóstico de ambiente Python:\n\n{traceback.format_exc()}"
        write_file(output_file, error_content)
        print("   ⚠️  Erro capturado (salvo em arquivo)")


# ===== DIAGNÓSTICO 2: CONFIGS VS CODE/PYRIGHT =====


def diagnose_vscode_settings() -> None:
    """Gera 02_vscode_and_pyright_settings.txt com configurações."""
    print("🔍 [2/5] Diagnosticando configurações VS Code/Pyright...")

    output_file = DIAGNOSTICS_DIR / "02_vscode_and_pyright_settings.txt"

    try:
        # Limpa arquivo
        write_file(output_file, "")

        # Seção 1: .vscode/settings.json
        settings_file = PROJECT_ROOT / ".vscode" / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings_raw = f.read()
                content = f"Arquivo encontrado: {settings_file.relative_to(PROJECT_ROOT)}\n\n"
                content += "Conteúdo RAW:\n"
                content += settings_raw

                # Tenta parsear JSON
                try:
                    settings_parsed = json.loads(settings_raw)
                    content += "\n\n" + "=" * 40 + "\n"
                    content += "Configurações relevantes (parsed):\n"
                    content += "=" * 40 + "\n\n"

                    relevant_keys = [
                        "python.defaultInterpreterPath",
                        "python.analysis.stubPath",
                        "python.analysis.extraPaths",
                        "python.testing.pytestEnabled",
                        "python.testing.pytestArgs",
                    ]

                    for key in relevant_keys:
                        if key in settings_parsed:
                            content += f"{key}: {settings_parsed[key]}\n"
                        else:
                            content += f"{key}: <não encontrado>\n"

                except json.JSONDecodeError as e:
                    content += f"\n\n⚠️  Falha ao parsear JSON: {e}\n"

            except Exception as e:
                content = f"⚠️  Erro ao ler arquivo: {e}\n"
        else:
            content = f"❌ Arquivo não encontrado: {settings_file.relative_to(PROJECT_ROOT)}\n"

        write_section(output_file, ".VSCODE/SETTINGS.JSON", content)

        # Seção 2: pyrightconfig.json
        pyright_file = PROJECT_ROOT / "pyrightconfig.json"
        if pyright_file.exists():
            try:
                with open(pyright_file, "r", encoding="utf-8") as f:
                    pyright_raw = f.read()
                content = f"Arquivo encontrado: {pyright_file.relative_to(PROJECT_ROOT)}\n\n"
                content += "Conteúdo RAW:\n"
                content += pyright_raw

                # Tenta parsear JSON
                try:
                    pyright_parsed = json.loads(pyright_raw)
                    content += "\n\n" + "=" * 40 + "\n"
                    content += "Configurações relevantes (parsed):\n"
                    content += "=" * 40 + "\n\n"

                    relevant_keys = [
                        "stubPath",
                        "extraPaths",
                        "venvPath",
                        "venv",
                        "pythonVersion",
                        "typeCheckingMode",
                    ]

                    for key in relevant_keys:
                        if key in pyright_parsed:
                            content += f"{key}: {pyright_parsed[key]}\n"
                        else:
                            content += f"{key}: <não encontrado>\n"

                except json.JSONDecodeError as e:
                    content += f"\n\n⚠️  Falha ao parsear JSON: {e}\n"

            except Exception as e:
                content = f"⚠️  Erro ao ler arquivo: {e}\n"
        else:
            content = f"❌ Arquivo não encontrado: {pyright_file.relative_to(PROJECT_ROOT)}\n"

        write_section(output_file, "PYRIGHTCONFIG.JSON", content)

        print(f"   ✅ Salvo em: {output_file.relative_to(PROJECT_ROOT)}")

    except Exception:
        error_content = f"❌ ERRO ao gerar diagnóstico de configurações:\n\n{traceback.format_exc()}"
        write_file(output_file, error_content)
        print("   ⚠️  Erro capturado (salvo em arquivo)")


# ===== DIAGNÓSTICO 3: TRACE COVERAGE =====


def diagnose_trace_coverage() -> None:
    """Executa tools/trace_coverage_clientes.py e captura output."""
    print("🔍 [3/5] Executando trace coverage...")

    stdout_file = DIAGNOSTICS_DIR / "03_trace_stdout.txt"
    stderr_file = DIAGNOSTICS_DIR / "03_trace_stderr.txt"

    trace_script = PROJECT_ROOT / "tools" / "trace_coverage_clientes.py"

    if not trace_script.exists():
        warning = f"⚠️  Script não encontrado: {trace_script.relative_to(PROJECT_ROOT)}\n"
        warning += "Não é possível executar trace coverage.\n"
        write_file(stdout_file, warning)
        write_file(stderr_file, "")
        print("   ⚠️  Script de trace não encontrado")
        return

    try:
        # Executa script usando o mesmo Python
        result = subprocess.run(
            [sys.executable, str(trace_script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutos max
        )

        # Salva stdout
        stdout_content = f"Return Code: {result.returncode}\n\n"
        stdout_content += "=" * 80 + "\n"
        stdout_content += "STDOUT\n"
        stdout_content += "=" * 80 + "\n\n"
        stdout_content += result.stdout
        write_file(stdout_file, stdout_content)

        # Salva stderr
        stderr_content = "=" * 80 + "\n"
        stderr_content += "STDERR\n"
        stderr_content += "=" * 80 + "\n\n"
        stderr_content += result.stderr if result.stderr else "<vazio>\n"
        write_file(stderr_file, stderr_content)

        status = "✅" if result.returncode == 0 else "⚠️"
        print(f"   {status} Trace executado (returncode={result.returncode})")
        print(f"   📄 Stdout: {stdout_file.relative_to(PROJECT_ROOT)}")
        print(f"   📄 Stderr: {stderr_file.relative_to(PROJECT_ROOT)}")

    except subprocess.TimeoutExpired:
        error_content = "❌ TIMEOUT: Trace coverage excedeu 5 minutos\n"
        write_file(stdout_file, error_content)
        write_file(stderr_file, "")
        print("   ⚠️  Timeout (>5min)")

    except Exception:
        error_content = f"❌ ERRO ao executar trace coverage:\n\n{traceback.format_exc()}"
        write_file(stdout_file, error_content)
        write_file(stderr_file, "")
        print("   ⚠️  Erro capturado (salvo em arquivo)")


# ===== DIAGNÓSTICO 4: PYTEST COLLECT =====


def diagnose_pytest_collect() -> None:
    """Executa pytest --collect-only e captura output."""
    print("🔍 [4/5] Executando pytest --collect-only...")

    output_file = DIAGNOSTICS_DIR / "04_pytest_collect_only.txt"

    try:
        # Executa pytest --collect-only
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-q", "--collect-only"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60,  # 1 minuto max
        )

        # Salva output
        content = f"Return Code: {result.returncode}\n\n"
        content += "=" * 80 + "\n"
        content += "STDOUT\n"
        content += "=" * 80 + "\n\n"
        content += result.stdout

        if result.stderr:
            content += "\n\n" + "=" * 80 + "\n"
            content += "STDERR\n"
            content += "=" * 80 + "\n\n"
            content += result.stderr

        write_file(output_file, content)

        status = "✅" if result.returncode == 0 else "⚠️"
        print(f"   {status} Pytest collect executado (returncode={result.returncode})")
        print(f"   📄 Salvo em: {output_file.relative_to(PROJECT_ROOT)}")

    except subprocess.TimeoutExpired:
        error_content = "❌ TIMEOUT: pytest --collect-only excedeu 1 minuto\n"
        write_file(output_file, error_content)
        print("   ⚠️  Timeout (>1min)")

    except Exception:
        error_content = f"❌ ERRO ao executar pytest --collect-only:\n\n{traceback.format_exc()}"
        write_file(output_file, error_content)
        print("   ⚠️  Erro capturado (salvo em arquivo)")


# ===== DIAGNÓSTICO 5: PYTEST COM SKIP REASONS =====


def diagnose_pytest_run_with_skips() -> None:
    """Executa pytest -rs e captura output com motivos de skip."""
    print("🔍 [5/5] Executando pytest com skip reasons (-rs)...")

    output_file = DIAGNOSTICS_DIR / "05_pytest_run_with_skips.txt"

    try:
        # Executa pytest -rs
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/modules/clientes", "-q", "-rs"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=180,  # 3 minutos max
        )

        # Salva output
        content = f"Return Code: {result.returncode}\n\n"
        content += "=" * 80 + "\n"
        content += "STDOUT\n"
        content += "=" * 80 + "\n\n"
        content += result.stdout

        if result.stderr:
            content += "\n\n" + "=" * 80 + "\n"
            content += "STDERR\n"
            content += "=" * 80 + "\n\n"
            content += result.stderr

        write_file(output_file, content)

        status = "✅" if result.returncode == 0 else "⚠️"
        print(f"   {status} Pytest executado (returncode={result.returncode})")
        print(f"   📄 Salvo em: {output_file.relative_to(PROJECT_ROOT)}")

    except subprocess.TimeoutExpired:
        error_content = "❌ TIMEOUT: pytest excedeu 3 minutos\n"
        write_file(output_file, error_content)
        print("   ⚠️  Timeout (>3min)")

    except Exception:
        error_content = f"❌ ERRO ao executar pytest:\n\n{traceback.format_exc()}"
        write_file(output_file, error_content)
        print("   ⚠️  Erro capturado (salvo em arquivo)")


# ===== MAIN =====


def main() -> int:
    """Entry point principal."""
    print()
    print("=" * 80)
    print("🔬 DIAGNÓSTICO AUTOMÁTICO — Módulo Clientes")
    print("=" * 80)
    print()

    # Cria diretório de diagnóstico
    ensure_diagnostics_dir()

    # Executa diagnósticos
    diagnose_python_env()
    diagnose_vscode_settings()
    diagnose_trace_coverage()
    diagnose_pytest_collect()
    diagnose_pytest_run_with_skips()

    # Lista arquivos gerados
    print()
    print("=" * 80)
    print("✅ DIAGNÓSTICO CONCLUÍDO")
    print("=" * 80)
    print()
    print("📄 Arquivos gerados:")
    print()

    diagnostics_files = [
        "01_python_env.txt",
        "02_vscode_and_pyright_settings.txt",
        "03_trace_stdout.txt",
        "03_trace_stderr.txt",
        "04_pytest_collect_only.txt",
        "05_pytest_run_with_skips.txt",
    ]

    for filename in diagnostics_files:
        file_path = DIAGNOSTICS_DIR / filename
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            relative = file_path.relative_to(PROJECT_ROOT)
            print(f"   ✅ {relative} ({size_kb:.1f} KB)")
        else:
            relative = (DIAGNOSTICS_DIR / filename).relative_to(PROJECT_ROOT)
            print(f"   ❌ {relative} (não gerado)")

    print()
    print("📌 Próximos passos:")
    print("   1. Examine os arquivos em diagnostics/clientes/")
    print("   2. Envie-os para o ChatGPT para análise")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
