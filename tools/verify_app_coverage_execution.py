#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICADOR DE EXECUÇÃO — COBERTURA GLOBAL DO APP

Executa o comando de cobertura global do app e verifica se tests/modules/clientes
é realmente EXECUTADO (não apenas coletado).

Gera diagnósticos em diagnostics/app_clientes/:
7. stdout da execução da cobertura global
8. stderr da execução da cobertura global
9. resumo consolidado (customtkinter + coleta + execução + artefatos)

Uso:
    python tools/verify_app_coverage_execution.py
"""

import json
import pathlib
import platform
import re
import subprocess
import sys
import time
import traceback
from typing import Any, Dict, Optional, Tuple


def ensure_diagnostics_dir() -> pathlib.Path:
    """Cria diretório diagnostics/app_clientes/ se não existir."""
    diag_dir = pathlib.Path("diagnostics/app_clientes")
    diag_dir.mkdir(parents=True, exist_ok=True)
    return diag_dir


def write_diagnostic(filename: str, content: str, diag_dir: pathlib.Path) -> None:
    """Escreve conteúdo no arquivo de diagnóstico."""
    filepath = diag_dir / filename
    try:
        filepath.write_text(content, encoding="utf-8")
        print(f"✓ {filename}")
    except Exception as e:
        print(f"✗ {filename}: {e}")


def find_venv_python() -> Optional[pathlib.Path]:
    """
    Descobre caminho do Python da .venv.

    Prioridade:
    1. .vscode/settings.json -> python.defaultInterpreterPath
    2. .venv/Scripts/python.exe (Windows)
    3. .venv/bin/python (Unix)
    """
    # Tentar .vscode/settings.json
    settings_file = pathlib.Path(".vscode/settings.json")
    if settings_file.exists():
        try:
            with open(settings_file, encoding="utf-8") as f:
                settings = json.load(f)
                interpreter_path = settings.get("python.defaultInterpreterPath")
                if interpreter_path:
                    path = pathlib.Path(interpreter_path)
                    if path.exists():
                        return path
        except Exception:
            pass

    # Fallback: .venv/Scripts/python.exe ou .venv/bin/python
    if platform.system() == "Windows":
        venv_python = pathlib.Path(".venv/Scripts/python.exe")
    else:
        venv_python = pathlib.Path(".venv/bin/python")

    if venv_python.exists():
        return venv_python

    return None


def discover_coverage_command() -> Tuple[str, str]:
    """
    Descobre comando de cobertura global do app.

    Prioridade:
    1. pytest -c pytest_cov.ini (se pytest_cov.ini existe)
    2. pytest --cov=src -v (fallback do CI)

    Returns:
        (command_description, command_args)
    """
    # Verificar argumento de linha de comando para teste rápido
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        return (
            "pytest tests/modules/clientes/ --cov=src -v (modo rápido)",
            "-m pytest tests/modules/clientes/ --cov=src --cov-report=term-missing -v",
        )

    # Prioridade 1: pytest_cov.ini
    if pathlib.Path("pytest_cov.ini").exists():
        return ("pytest -c pytest_cov.ini", "-m pytest -c pytest_cov.ini -ra --continue-on-collection-errors")

    # Fallback: comando do CI
    return ("pytest --cov=src -v", "-m pytest --cov=src --cov-report=term-missing -v")


def check_customtkinter_in_venv(venv_python: pathlib.Path) -> Tuple[bool, str]:
    """
    Verifica se customtkinter está instalado na .venv.

    Returns:
        (installed, version_or_error)
    """
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "import customtkinter; print(customtkinter.__version__)"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        else:
            return False, "ImportError"

    except Exception as e:
        return False, f"Exception: {e}"


def run_coverage_command(
    venv_python: pathlib.Path, command_args: str, diag_dir: pathlib.Path
) -> Tuple[bool, int, str, str]:
    """
    Executa comando de cobertura via subprocess.

    Returns:
        (success, returncode, stdout, stderr)
    """
    print("Executando comando de cobertura (pode levar 5-10 minutos)...")
    print("Aguarde...")

    try:
        # Preparar comando
        args = command_args.split()
        full_command = [str(venv_python)] + args

        start_time = time.time()

        # Executar com timeout maior
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutos
            cwd=pathlib.Path.cwd(),
        )

        elapsed = time.time() - start_time

        print(f"✓ Comando concluído em {elapsed:.1f} segundos ({elapsed/60:.1f} minutos)")

        return True, result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return False, -1, "", "TIMEOUT após 10 minutos"
    except Exception as e:
        return False, -1, "", f"Erro ao executar: {e}\n{traceback.format_exc()}"


def analyze_execution(stdout: str, stderr: str) -> Dict[str, Any]:
    """
    Analisa stdout/stderr para verificar se tests/modules/clientes foi executado.

    Returns:
        Dicionário com análise
    """
    analysis = {
        "tests_modules_clientes_executed": False,
        "tests_count": 0,
        "tests_modules_clientes_count": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "coverage_files_generated": {
            "htmlcov": False,
            "coverage_json": False,
            "reports_coverage_json": False,
        },
        "execution_summary": "",
        "timeout": False,
    }

    # Verificar timeout
    if "TIMEOUT" in stderr:
        analysis["timeout"] = True

    # Verificar se tests/modules/clientes aparece no stdout (vários formatos possíveis)
    patterns = [
        r"tests[/\\]modules[/\\]clientes",  # Path no nodeids
        r"test_client",  # Nomes de arquivos
        r"test_clientes",  # Nomes de arquivos
    ]

    for pattern in patterns:
        if re.search(pattern, stdout, re.IGNORECASE):
            analysis["tests_modules_clientes_executed"] = True
            break

    # Contar ocorrências (aproximação)
    if analysis["tests_modules_clientes_executed"]:
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, stdout, re.IGNORECASE))
        analysis["tests_modules_clientes_count"] = count

    # Extrair resumo do pytest (ex: "123 passed, 4 skipped in 45.67s")
    summary_match = re.search(
        r"(\d+)\s+passed(?:,\s+(\d+)\s+failed)?(?:,\s+(\d+)\s+skipped)?(?:,\s+(\d+)\s+error)?.*in\s+([\d.]+)s", stdout
    )

    if summary_match:
        analysis["passed"] = int(summary_match.group(1))
        analysis["failed"] = int(summary_match.group(2) or 0)
        analysis["skipped"] = int(summary_match.group(3) or 0)
        analysis["errors"] = int(summary_match.group(4) or 0)
        analysis["tests_count"] = analysis["passed"] + analysis["failed"] + analysis["errors"]
        analysis["execution_summary"] = summary_match.group(0)

    # Verificar artefatos gerados
    analysis["coverage_files_generated"]["htmlcov"] = pathlib.Path("htmlcov/index.html").exists()
    analysis["coverage_files_generated"]["coverage_json"] = pathlib.Path("coverage.json").exists()
    analysis["coverage_files_generated"]["reports_coverage_json"] = pathlib.Path("reports/coverage.json").exists()

    return analysis


def generate_consolidated_report(
    diag_dir: pathlib.Path,
    venv_python: Optional[pathlib.Path],
    customtkinter_status: Tuple[bool, str],
    command_desc: str,
    success: bool,
    returncode: int,
    analysis: Dict[str, Any],
) -> None:
    """Gera relatório consolidado final."""
    lines = []
    lines.append("=" * 80)
    lines.append("DIAGNÓSTICO 09: RESUMO CONSOLIDADO - COBERTURA GLOBAL DO APP")
    lines.append("=" * 80)
    lines.append("")

    # 1) Ambiente
    lines.append("[1. AMBIENTE]")
    lines.append("")

    if venv_python:
        lines.append(f"✓ Python da .venv: {venv_python}")
    else:
        lines.append("✗ Python da .venv: NÃO ENCONTRADO")

    lines.append("")

    if customtkinter_status[0]:
        lines.append(f"✓ customtkinter na .venv: OK (versão {customtkinter_status[1]})")
    else:
        lines.append(f"✗ customtkinter na .venv: {customtkinter_status[1]}")

    lines.append("")
    lines.append("")

    # 2) Comando executado
    lines.append("[2. COMANDO DE COBERTURA GLOBAL]")
    lines.append("")
    lines.append(f"Comando: {command_desc}")
    lines.append("")

    if success:
        lines.append(f"✓ Execução: CONCLUÍDA (exit code {returncode})")
    else:
        lines.append("✗ Execução: FALHOU")

    lines.append("")
    lines.append("")

    # 3) Coleta de testes/modules/clientes (referência do diagnóstico 05)
    lines.append("[3. COLETA DE tests/modules/clientes]")
    lines.append("")

    collect_file = diag_dir / "05_pytest_collect_only_active_command.txt"
    if collect_file.exists():
        content = collect_file.read_text(encoding="utf-8")
        if "tests/modules/clientes DETECTADO na coleta" in content:
            lines.append("✓ Status: DETECTADO na coleta (--collect-only)")

            # Extrair contagem
            match = re.search(r"(\d+)\s+linhas de testes/modules/clientes", content)
            if match:
                lines.append(f"✓ Arquivos coletados: {match.group(1)}")
        else:
            lines.append("✗ Status: NÃO DETECTADO na coleta")
    else:
        lines.append("⚠️  Status: Diagnóstico 05 não encontrado (execute verify_app_clientes_coverage_env.py)")

    lines.append("")
    lines.append("")

    # 4) EXECUÇÃO de tests/modules/clientes (NOVO)
    lines.append("[4. EXECUÇÃO DE tests/modules/clientes]")
    lines.append("")

    if analysis.get("timeout", False):
        lines.append("⚠️  Status: TIMEOUT (execução interrompida após 10 minutos)")
        lines.append("  Possíveis causas:")
        lines.append("  - Muitos testes no projeto (> 1000)")
        lines.append("  - Testes lentos ou travados")
        lines.append("  - Recomendação: Executar manualmente com -x (stop on first failure)")
    elif analysis["tests_modules_clientes_executed"]:
        lines.append("✓ Status: EXECUTADO (encontrado no stdout)")
        lines.append(f"✓ Ocorrências no log: ~{analysis['tests_modules_clientes_count']}")
    else:
        lines.append("✗ Status: NÃO EXECUTADO (não encontrado no stdout)")
        lines.append("  Possíveis causas:")
        lines.append("  - Todos os testes skipados (ImportError customtkinter)")
        lines.append("  - Comando exclui tests/modules")
        lines.append("  - Falha na execução")

    lines.append("")

    if analysis["execution_summary"]:
        lines.append(f"Resumo pytest: {analysis['execution_summary']}")

    lines.append("")
    lines.append("")

    # 5) Artefatos de cobertura
    lines.append("[5. ARTEFATOS DE COBERTURA GERADOS]")
    lines.append("")

    if analysis["coverage_files_generated"]["htmlcov"]:
        lines.append("✓ htmlcov/index.html: GERADO")
    else:
        lines.append("✗ htmlcov/index.html: NÃO ENCONTRADO")

    if analysis["coverage_files_generated"]["coverage_json"]:
        lines.append("✓ coverage.json: GERADO")
    else:
        lines.append("✗ coverage.json: NÃO ENCONTRADO")

    if analysis["coverage_files_generated"]["reports_coverage_json"]:
        lines.append("✓ reports/coverage.json: GERADO")
    else:
        lines.append("✗ reports/coverage.json: NÃO ENCONTRADO")

    lines.append("")
    lines.append("")

    # 6) CONCLUSÃO FINAL
    lines.append("[6. CONCLUSÃO FINAL]")
    lines.append("")

    all_ok = (
        customtkinter_status[0]
        and analysis["tests_modules_clientes_executed"]
        and (
            analysis["coverage_files_generated"]["htmlcov"]
            or analysis["coverage_files_generated"]["reports_coverage_json"]
        )
    )

    if all_ok:
        lines.append("✅ TUDO OK:")
        lines.append("  ✓ customtkinter instalado na .venv")
        lines.append("  ✓ tests/modules/clientes coletado")
        lines.append("  ✓ tests/modules/clientes EXECUTADO")
        lines.append("  ✓ Artefatos de cobertura gerados")
        lines.append("")
        lines.append("🎯 A cobertura global DO APP inclui módulos Clientes!")
    else:
        lines.append("⚠️  PROBLEMAS DETECTADOS:")

        if not customtkinter_status[0]:
            lines.append("  ✗ customtkinter ausente na .venv")
            lines.append("    Ação: pip install customtkinter>=5.2.0")

        if not analysis["tests_modules_clientes_executed"]:
            lines.append("  ✗ tests/modules/clientes NÃO executado")
            lines.append("    Ação: Verificar diagnósticos 03 e 04")

        if not any(analysis["coverage_files_generated"].values()):
            lines.append("  ✗ Nenhum artefato de cobertura gerado")
            lines.append("    Ação: Verificar stderr (diagnóstico 08)")

    lines.append("")
    lines.append("=" * 80)

    write_diagnostic("09_consolidated_report.txt", "\n".join(lines), diag_dir)


def main() -> None:
    """Função principal."""
    print("=" * 80)
    print("VERIFICADOR DE EXECUÇÃO — COBERTURA GLOBAL DO APP")
    print("=" * 80)
    print()

    # Verificar modo rápido
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        print("⚡ MODO RÁPIDO: testando apenas tests/modules/clientes/")
        print()

    # Criar diretório de diagnósticos
    diag_dir = ensure_diagnostics_dir()
    print(f"Diretório: {diag_dir.absolute()}")
    print()

    # 1) Verificar Python da .venv
    print("[1/6] Verificando Python da .venv...")
    venv_python = find_venv_python()

    if not venv_python:
        print("✗ Python da .venv NÃO ENCONTRADO")
        print("  Execute: python -m venv .venv")
        return

    print(f"✓ Encontrado: {venv_python}")
    print()

    # 2) Verificar customtkinter na .venv
    print("[2/6] Verificando customtkinter na .venv...")
    customtkinter_status = check_customtkinter_in_venv(venv_python)

    if customtkinter_status[0]:
        print(f"✓ customtkinter: OK (versão {customtkinter_status[1]})")
    else:
        print(f"⚠️  customtkinter: {customtkinter_status[1]}")
        print("  Testes de módulos Clientes serão skipados")
    print()

    # 3) Descobrir comando de cobertura
    print("[3/6] Descobrindo comando de cobertura global...")
    command_desc, command_args = discover_coverage_command()
    print(f"✓ Comando: {command_desc}")
    print()

    # 4) Executar comando de cobertura
    print("[4/6] Executando cobertura global...")
    success, returncode, stdout, stderr = run_coverage_command(venv_python, command_args, diag_dir)
    print()

    # 5) Salvar logs
    print("[5/6] Salvando logs de execução...")
    write_diagnostic("07_run_global_coverage_stdout.txt", stdout, diag_dir)
    write_diagnostic("08_run_global_coverage_stderr.txt", stderr, diag_dir)
    print()

    # 6) Analisar e gerar relatório consolidado
    print("[6/6] Analisando resultados...")
    analysis = analyze_execution(stdout, stderr)

    generate_consolidated_report(
        diag_dir, venv_python, customtkinter_status, command_desc, success, returncode, analysis
    )
    print()

    # Resumo no console
    print("=" * 80)
    print("RESUMO RÁPIDO")
    print("=" * 80)
    print()
    print(f"✓ customtkinter na .venv: {'OK' if customtkinter_status[0] else 'AUSENTE'}")
    print(f"✓ tests/modules/clientes executado: {'SIM' if analysis['tests_modules_clientes_executed'] else 'NÃO'}")

    if analysis["execution_summary"]:
        print(f"✓ Resultado: {analysis['execution_summary']}")

    artifacts_ok = any(analysis["coverage_files_generated"].values())
    print(f"✓ Artefatos gerados: {'SIM' if artifacts_ok else 'NÃO'}")
    print()
    print("=" * 80)
    print()
    print(f"Logs completos em: {diag_dir.absolute()}")
    print("  - 07_run_global_coverage_stdout.txt")
    print("  - 08_run_global_coverage_stderr.txt")
    print("  - 09_consolidated_report.txt")


if __name__ == "__main__":
    main()
