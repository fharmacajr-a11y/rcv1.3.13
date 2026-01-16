#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICADOR COMPLETO — APP CLIENTES (ENV + COBERTURA + PYLANCE HOTSPOTS)

Gera diagnósticos em diagnostics/app_clientes/:
1. Python ativo (sys.executable + customtkinter)
2. Python da .venv (sys.executable + customtkinter)
3. Comandos de cobertura encontrados no projeto
4. Diagnóstico de inclusão/exclusão de tests/modules
5. Coleta real do pytest (--collect-only)
6. Hotspots Pylance (HAS_CUSTOMTKINTER redefinido + .reconfigure)

Uso:
    python tools/verify_app_clientes_coverage_env.py
"""

import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple


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


def get_env_vars() -> Dict[str, Optional[str]]:
    """Captura variáveis de ambiente relevantes."""
    return {
        "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV"),
        "CONDA_PREFIX": os.environ.get("CONDA_PREFIX"),
        "PYTHONPATH": os.environ.get("PYTHONPATH"),
        "PATH": os.environ.get("PATH", "")[:200] + "...",  # Truncar PATH
    }


def check_customtkinter_import() -> Tuple[bool, str, str]:
    """
    Tenta importar customtkinter no Python atual (via ctk_config SSoT).

    Returns:
        (success, version_or_error, file_or_traceback)
    """
    try:
        from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

        if not HAS_CUSTOMTKINTER:
            return (False, "not_available", "HAS_CUSTOMTKINTER=False")

        # Tentar pegar versão
        version = "unknown"
        try:
            version = getattr(ctk, "__version__", "unknown") if ctk else "unknown"
        except Exception:
            pass

        # Fallback: importlib.metadata
        if version == "unknown":
            try:
                from importlib.metadata import version as get_version

                version = get_version("customtkinter")
            except Exception:
                pass

        file_path = getattr(ctk, "__file__", "unknown") if ctk else "unknown"
        return True, version, file_path

    except ImportError as e:
        return False, "ImportError", str(e)
    except Exception:
        return False, "Exception", traceback.format_exc()


def diagnose_active_python(diag_dir: pathlib.Path) -> None:
    """Gera 01_env_active_python.txt."""
    lines = []
    lines.append("=" * 80)
    lines.append("DIAGNÓSTICO 01: PYTHON ATIVO (sys.executable)")
    lines.append("=" * 80)
    lines.append("")

    # Informações do Python
    lines.append("[Python Ativo]")
    lines.append(f"sys.executable: {sys.executable}")
    lines.append(f"sys.version: {sys.version}")
    lines.append(f"sys.prefix: {sys.prefix}")
    lines.append(f"sys.base_prefix: {sys.base_prefix}")
    lines.append(f"platform: {platform.platform()}")
    lines.append("")

    # Variáveis de ambiente
    lines.append("[Variáveis de Ambiente]")
    env_vars = get_env_vars()
    for key, value in env_vars.items():
        lines.append(f"{key}: {value or 'não definido'}")
    lines.append("")

    # Tentar importar customtkinter
    lines.append("[Import customtkinter]")
    success, version_or_error, file_or_traceback = check_customtkinter_import()

    if success:
        lines.append("✓ Status: OK")
        lines.append(f"✓ Versão: {version_or_error}")
        lines.append(f"✓ Localização: {file_or_traceback}")
    else:
        lines.append("✗ Status: FALHOU")
        lines.append(f"✗ Tipo: {version_or_error}")
        lines.append("✗ Detalhes:")
        lines.append(file_or_traceback)

    lines.append("")
    lines.append("=" * 80)

    write_diagnostic("01_env_active_python.txt", "\n".join(lines), diag_dir)


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


def run_subprocess_python(python_exe: pathlib.Path, code: str) -> Tuple[bool, str]:
    """
    Executa código Python via subprocess.

    Returns:
        (success, output_or_error)
    """
    try:
        result = subprocess.run(
            [str(python_exe), "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=pathlib.Path.cwd(),
        )

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, f"Exit code {result.returncode}\n{result.stderr}"

    except subprocess.TimeoutExpired:
        return False, "Timeout após 10 segundos"
    except Exception as e:
        return False, f"Erro ao executar subprocess: {e}\n{traceback.format_exc()}"


def diagnose_venv_python(diag_dir: pathlib.Path) -> None:
    """Gera 02_env_venv_python.txt."""
    lines = []
    lines.append("=" * 80)
    lines.append("DIAGNÓSTICO 02: PYTHON DA .venv")
    lines.append("=" * 80)
    lines.append("")

    venv_python = find_venv_python()

    if not venv_python:
        lines.append("✗ Python da .venv NÃO ENCONTRADO")
        lines.append("")
        lines.append("Locais verificados:")
        lines.append("  1. .vscode/settings.json -> python.defaultInterpreterPath")
        lines.append("  2. .venv/Scripts/python.exe (Windows)")
        lines.append("  3. .venv/bin/python (Unix)")
        lines.append("")
        lines.append("Recomendação: Criar .venv com:")
        lines.append("  python -m venv .venv")
        lines.append("=" * 80)
        write_diagnostic("02_env_venv_python.txt", "\n".join(lines), diag_dir)
        return

    lines.append(f"✓ Python da .venv ENCONTRADO: {venv_python}")
    lines.append("")

    # Executar código de verificação via subprocess
    code = """
import sys
print(f"sys.executable: {sys.executable}")
print(f"sys.version: {sys.version}")
print(f"sys.prefix: {sys.prefix}")
print()

try:
    from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
    if HAS_CUSTOMTKINTER and ctk:
        version = getattr(ctk, "__version__", "unknown")
        if version == "unknown":
            try:
                from importlib.metadata import version as get_version
                version = get_version("customtkinter")
            except Exception:
                pass
        print("OK customtkinter: OK")
        print(f"OK Versao: {version}")
        if hasattr(ctk, '__file__'):
            print(f"OK Localizacao: {ctk.__file__}")
    else:
        print("ERRO customtkinter: Não disponível (HAS_CUSTOMTKINTER=False)")
except ImportError as e:
    print("ERRO customtkinter: ImportError")
    print(f"ERRO Detalhes: {e}")
except Exception as e:
    print("ERRO customtkinter: Exception")
    print(f"ERRO Detalhes: {e}")
"""

    lines.append("[Executando verificação via subprocess...]")
    success, output = run_subprocess_python(venv_python, code)

    if success:
        lines.append("")
        lines.append(output.strip())
    else:
        lines.append("")
        lines.append("✗ FALHA ao executar subprocess:")
        lines.append(output)

    lines.append("")
    lines.append("=" * 80)

    write_diagnostic("02_env_venv_python.txt", "\n".join(lines), diag_dir)


def scan_coverage_commands() -> List[Tuple[str, int, str]]:
    """
    Varre arquivos conhecidos procurando comandos pytest/coverage.

    Returns:
        Lista de (filepath, line_number, line_content)
    """
    results = []

    # Arquivos a varrer
    patterns = [
        ".vscode/tasks.json",
        "pyproject.toml",
        "tox.ini",
        "noxfile.py",
        "Makefile",
        "package.json",
        "pytest.ini",
        "pytest_cov.ini",
        ".coveragerc",
        "scripts/*.py",
        "scripts/*.ps1",
        "scripts/*.cmd",
        "tools/*.py",
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
    ]

    # Palavras-chave para buscar
    keywords = [
        "pytest",
        "--cov",
        "pytest-cov",
        "coverage",
        "tests/unit",
        "tests/modules",
    ]

    for pattern in patterns:
        for filepath in pathlib.Path(".").glob(pattern):
            if not filepath.is_file():
                continue

            try:
                with open(filepath, encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, start=1):
                        # Verificar se linha contém alguma palavra-chave
                        if any(keyword in line.lower() for keyword in keywords):
                            results.append((str(filepath), line_num, line.rstrip()))
            except Exception:
                continue

    return results


def diagnose_coverage_commands(diag_dir: pathlib.Path) -> None:
    """Gera 03_app_coverage_commands_found.txt."""
    lines = []
    lines.append("=" * 80)
    lines.append("DIAGNÓSTICO 03: COMANDOS DE COBERTURA ENCONTRADOS")
    lines.append("=" * 80)
    lines.append("")

    results = scan_coverage_commands()

    if not results:
        lines.append("✗ Nenhum comando de cobertura encontrado")
    else:
        lines.append(f"✓ {len(results)} linhas encontradas com keywords:")
        lines.append("")

        # Agrupar por arquivo
        by_file: Dict[str, List[Tuple[int, str]]] = {}
        for filepath, line_num, line_content in results:
            if filepath not in by_file:
                by_file[filepath] = []
            by_file[filepath].append((line_num, line_content))

        for filepath in sorted(by_file.keys()):
            lines.append(f"[{filepath}]")
            for line_num, line_content in by_file[filepath]:
                lines.append(f"  Linha {line_num}: {line_content}")
            lines.append("")

    lines.append("=" * 80)

    write_diagnostic("03_app_coverage_commands_found.txt", "\n".join(lines), diag_dir)


def analyze_test_selection() -> Dict[str, Any]:
    """
    Analisa se comandos/configs incluem ou excluem tests/modules.

    Returns:
        Dicionário com análise
    """
    analysis = {
        "explicit_unit_only": [],
        "explicit_modules_exclude": [],
        "pytest_ini_testpaths": None,
        "pytest_ini_norecursedirs": None,
        "conclusion": "unknown",
    }

    # Verificar comandos encontrados
    results = scan_coverage_commands()
    for filepath, line_num, line_content in results:
        # Pular o próprio script verificador
        if "verify_app_clientes_coverage_env.py" in filepath:
            continue

        # Comandos que EXCLUEM modules explicitamente
        if "tests/unit" in line_content and "tests/modules" not in line_content:
            # Verificar se é um comando que especifica caminho de testes
            if "pytest" in line_content.lower():
                analysis["explicit_unit_only"].append(f"{filepath}:{line_num}")

        # Markers que podem excluir
        if re.search(r"-m\s+unit", line_content) or re.search(r"-k\s+unit", line_content):
            analysis["explicit_modules_exclude"].append(f"{filepath}:{line_num}")

    # Analisar pytest.ini
    for ini_file in ["pytest.ini", "pytest_cov.ini"]:
        if pathlib.Path(ini_file).exists():
            try:
                with open(ini_file, encoding="utf-8") as f:
                    content = f.read()

                    # Extrair testpaths
                    match = re.search(r"testpaths\s*=\s*(.+)", content)
                    if match:
                        analysis["pytest_ini_testpaths"] = match.group(1).strip()

                    # Extrair norecursedirs
                    match = re.search(r"norecursedirs\s*=\s*(.+?)(?:\n\n|\Z)", content, re.DOTALL)
                    if match:
                        analysis["pytest_ini_norecursedirs"] = match.group(1).strip()
            except Exception:
                pass

    # Conclusão
    if analysis["explicit_unit_only"] or analysis["explicit_modules_exclude"]:
        analysis["conclusion"] = "EXCLUI tests/modules"
    elif analysis["pytest_ini_testpaths"] and "tests" in analysis["pytest_ini_testpaths"]:
        analysis["conclusion"] = "INCLUI tests/modules (testpaths=tests)"
    else:
        analysis["conclusion"] = "INCERTO (verificar coleta real)"

    return analysis


def diagnose_test_selection(diag_dir: pathlib.Path) -> None:
    """Gera 04_test_selection_diagnosis.txt."""
    lines = []
    lines.append("=" * 80)
    lines.append("DIAGNÓSTICO 04: SELEÇÃO DE TESTES (INCLUI/EXCLUI modules)")
    lines.append("=" * 80)
    lines.append("")

    analysis = analyze_test_selection()

    lines.append("[Comandos que especificam APENAS tests/unit]")
    if analysis["explicit_unit_only"]:
        for item in analysis["explicit_unit_only"]:
            lines.append(f"  ⚠️  {item}")
    else:
        lines.append("  ✓ Nenhum encontrado")
    lines.append("")

    lines.append("[Comandos com markers que excluem modules (-m/-k)]")
    if analysis["explicit_modules_exclude"]:
        for item in analysis["explicit_modules_exclude"]:
            lines.append(f"  ⚠️  {item}")
    else:
        lines.append("  ✓ Nenhum encontrado")
    lines.append("")

    lines.append("[Configuração pytest.ini / pytest_cov.ini]")
    if analysis["pytest_ini_testpaths"]:
        lines.append(f"  testpaths: {analysis['pytest_ini_testpaths']}")
        if "tests" in analysis["pytest_ini_testpaths"] and "tests/unit" not in analysis["pytest_ini_testpaths"]:
            lines.append("  ✓ Inclui todo o diretório tests/ (modules incluído)")
    else:
        lines.append("  ⚠️  testpaths não encontrado")

    if analysis["pytest_ini_norecursedirs"]:
        lines.append(f"  norecursedirs: {analysis['pytest_ini_norecursedirs']}")
    lines.append("")

    lines.append("[CONCLUSÃO]")
    lines.append(f"  {analysis['conclusion']}")
    lines.append("")

    if analysis["conclusion"] == "EXCLUI tests/modules":
        lines.append("⚠️  AÇÃO NECESSÁRIA:")
        lines.append("  - Comandos encontrados excluem tests/modules/clientes")
        lines.append("  - Cobertura de módulos Clientes NÃO entra na PP")
    elif analysis["conclusion"] == "INCLUI tests/modules (testpaths=tests)":
        lines.append("✓ TUDO CERTO:")
        lines.append("  - Configuração inclui tests/modules/clientes")
        lines.append("  - Cobertura de módulos Clientes ENTRA na PP")

    lines.append("")
    lines.append("=" * 80)

    write_diagnostic("04_test_selection_diagnosis.txt", "\n".join(lines), diag_dir)


def run_pytest_collect_only(diag_dir: pathlib.Path) -> None:
    """Gera 05_pytest_collect_only_active_command.txt."""
    lines = []
    lines.append("=" * 80)
    lines.append("DIAGNÓSTICO 05: PYTEST COLLECT-ONLY (COLETA REAL)")
    lines.append("=" * 80)
    lines.append("")

    # Tentar usar Python da .venv
    venv_python = find_venv_python()
    python_exe = venv_python if venv_python else pathlib.Path(sys.executable)

    lines.append(f"[Python usado]: {python_exe}")
    lines.append("")

    # Executar pytest --collect-only -q
    try:
        result = subprocess.run(
            [str(python_exe), "-m", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=pathlib.Path.cwd(),
        )

        lines.append("[Saída do comando: pytest --collect-only -q]")
        lines.append("")
        lines.append(result.stdout[:5000])  # Limitar a 5000 chars

        if len(result.stdout) > 5000:
            lines.append("")
            lines.append("... (truncado, muito longo)")

        if result.stderr:
            lines.append("")
            lines.append("[Erros/Warnings]")
            lines.append(result.stderr[:2000])

        lines.append("")
        lines.append("[Análise]")
        if "tests/modules/clientes" in result.stdout:
            lines.append("✓ tests/modules/clientes DETECTADO na coleta")

            # Contar quantos testes
            count = result.stdout.count("tests/modules/clientes")
            lines.append(f"✓ {count} linhas de testes/modules/clientes encontradas")
        else:
            lines.append("✗ tests/modules/clientes NÃO DETECTADO na coleta")
            lines.append("  Possíveis causas:")
            lines.append("  - Comando exclui tests/modules")
            lines.append("  - Todos os testes são skipados (ImportError customtkinter)")
            lines.append("  - Configuração pytest.ini exclui o diretório")

    except subprocess.TimeoutExpired:
        lines.append("✗ TIMEOUT após 30 segundos")
        lines.append("  Possível causa: muitos testes para coletar")
    except Exception as e:
        lines.append(f"✗ ERRO ao executar pytest: {e}")
        lines.append("")
        lines.append(traceback.format_exc())

    lines.append("")
    lines.append("=" * 80)

    write_diagnostic("05_pytest_collect_only_active_command.txt", "\n".join(lines), diag_dir)


def scan_pylance_hotspots() -> Dict[str, List[Tuple[int, str]]]:
    """
    Scan estático de hotspots Pylance.

    Returns:
        Dicionário {filepath: [(line_num, line_content)]}
    """
    hotspots: Dict[str, List[Tuple[int, str]]] = {}

    # 1) HAS_CUSTOMTKINTER redefinido em tests/modules/clientes
    # Buscar por redefinição no MESMO arquivo (try/except com HAS_CUSTOMTKINTER = True/False)
    for pattern in ["tests/modules/clientes/**/*.py", "tests/unit/modules/clientes/**/*.py"]:
        for filepath in pathlib.Path(".").glob(pattern):
            if not filepath.is_file():
                continue

            try:
                with open(filepath, encoding="utf-8") as f:
                    lines = f.readlines()

                    # Procurar por padrão try/except com HAS_CUSTOMTKINTER
                    in_try_block = False
                    has_ctk_lines = []

                    for line_num, line in enumerate(lines, start=1):
                        # Detectar bloco try que importa customtkinter
                        if "try:" in line and line_num < len(lines) - 3:
                            next_lines = "".join(lines[line_num : line_num + 5])
                            if "customtkinter" in next_lines and "HAS_CUSTOMTKINTER" in next_lines:
                                in_try_block = True

                        # Detectar múltiplas atribuições de HAS_CUSTOMTKINTER
                        if re.match(r"^\s*HAS_CUSTOMTKINTER\s*=\s*(True|False)", line):
                            has_ctk_lines.append((line_num, line.strip()))

                        # Sair do bloco try
                        if in_try_block and line.strip() and not line.startswith((" ", "\t")):
                            in_try_block = False

                    # Se encontrou 2+ atribuições (redefinição)
                    if len(has_ctk_lines) >= 2:
                        if str(filepath) not in hotspots:
                            hotspots[str(filepath)] = []
                        hotspots[str(filepath)].extend(has_ctk_lines)

            except Exception:
                continue

    # 2) .reconfigure( em tools/ (SEM cast para io.TextIOWrapper)
    for filepath in pathlib.Path("tools").glob("**/*.py"):
        if not filepath.is_file():
            continue

        # Pular o próprio script verificador
        if filepath.name == "verify_app_clientes_coverage_env.py":
            continue

        try:
            with open(filepath, encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    # Procurar .reconfigure( sem cast
                    if ".reconfigure(" in line and "cast(" not in line and "cast(io.TextIOWrapper" not in line:
                        if str(filepath) not in hotspots:
                            hotspots[str(filepath)] = []
                        hotspots[str(filepath)].append((line_num, line.strip()))
        except Exception:
            continue

    return hotspots


def diagnose_pylance_hotspots(diag_dir: pathlib.Path) -> None:
    """Gera 06_pylance_hotspots_scan.txt."""
    lines = []
    lines.append("=" * 80)
    lines.append("DIAGNÓSTICO 06: PYLANCE HOTSPOTS (SCAN ESTÁTICO)")
    lines.append("=" * 80)
    lines.append("")

    hotspots = scan_pylance_hotspots()

    if not hotspots:
        lines.append("✓ Nenhum hotspot Pylance encontrado")
        lines.append("")
        lines.append("Verificações realizadas:")
        lines.append("  1. HAS_CUSTOMTKINTER redefinido em tests/modules/clientes/**/*.py")
        lines.append("  2. .reconfigure( em tools/**/*.py")
    else:
        lines.append(f"⚠️  {len(hotspots)} arquivo(s) com hotspots Pylance:")
        lines.append("")

        for filepath in sorted(hotspots.keys()):
            lines.append(f"[{filepath}]")

            for line_num, line_content in hotspots[filepath]:
                lines.append(f"  Linha {line_num}: {line_content}")

            lines.append("")

            # Sugestões de correção
            if "HAS_CUSTOMTKINTER" in filepath:
                lines.append("  → Correção: Importar de appearance.py em vez de redefinir")
                lines.append("    from src.modules.clientes.appearance import HAS_CUSTOMTKINTER")
                lines.append("")

            if ".reconfigure(" in str(hotspots[filepath]):
                lines.append("  → Correção: Usar cast para io.TextIOWrapper")
                lines.append("    from typing import cast")
                lines.append("    import io")
                lines.append("    cast(io.TextIOWrapper, sys.stdout).reconfigure(...)")
                lines.append("")

    lines.append("=" * 80)

    write_diagnostic("06_pylance_hotspots_scan.txt", "\n".join(lines), diag_dir)


def main() -> None:
    """Função principal."""
    print("=" * 80)
    print("VERIFICADOR APP CLIENTES — ENV + COBERTURA + PYLANCE")
    print("=" * 80)
    print()

    # Criar diretório de diagnósticos
    diag_dir = ensure_diagnostics_dir()
    print(f"Diretório: {diag_dir.absolute()}")
    print()

    # Executar diagnósticos
    print("Gerando diagnósticos:")

    diagnose_active_python(diag_dir)
    diagnose_venv_python(diag_dir)
    diagnose_coverage_commands(diag_dir)
    diagnose_test_selection(diag_dir)
    run_pytest_collect_only(diag_dir)
    diagnose_pylance_hotspots(diag_dir)

    print()
    print("=" * 80)
    print("CONCLUÍDO")
    print("=" * 80)
    print()
    print(f"Arquivos gerados em: {diag_dir.absolute()}")
    print()
    print("Para interpretar os resultados, consulte:")
    print("  docs/CLIENTES_MICROFASE_18_VERIFY_APP_ENV_AND_COVERAGE.md")


if __name__ == "__main__":
    main()
