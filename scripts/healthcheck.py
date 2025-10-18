#!/usr/bin/env python3
from __future__ import annotations
from config.paths import CLOUD_ONLY

import argparse
import ast
import contextlib
import dataclasses
import json
import os
import re
import subprocess
import sys
import traceback
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = "VARREDURA-RELATORIO.md"
IGNORED_DIRS = {".venv", "__pycache__", ".git", ".mypy_cache", ".pytest_cache"}
MAX_DIFFS = 200
TRACE_RE = re.compile(r'File "(.+?)", line (\d+), in (.+)')

# ---------- helpers ----------


def _json_default(obj: Any) -> Any:
    """Fallback para JSON: converte Path em str."""
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


@dataclass
class CommandResult:
    command: str
    returncode: Optional[int]
    stdout: str
    stderr: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


def join_command(parts: Sequence[str]) -> str:
    return " ".join(str(p) for p in parts)


def run_command(parts: Sequence[str]) -> CommandResult:
    cmd_str = join_command(parts)
    try:
        proc = subprocess.run(
            parts,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return CommandResult(
            command=cmd_str,
            returncode=proc.returncode,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
        )
    except FileNotFoundError as exc:
        return CommandResult(cmd_str, None, "", "", str(exc))
    except Exception as exc:  # pragma: no cover
        return CommandResult(cmd_str, None, "", "", f"{type(exc).__name__}: {exc}")


def should_ignore(path: Path) -> bool:
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return True
    return any(part in IGNORED_DIRS for part in parts)


def collect_python_files() -> List[Path]:
    files: List[Path] = []
    for path in ROOT.rglob("*.py"):
        if should_ignore(path):
            continue
        files.append(path)
    return sorted(files)


# ---------- AST scan ----------


class EnvAssetVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.env_calls: List[Dict[str, Any]] = []
        self.asset_calls: List[Dict[str, Any]] = []
        self.os_aliases = {"os"}
        self.getenv_aliases: set[str] = set()
        self.resource_names: set[str] = {"resource_path"}
        self.path_names: set[str] = set()
        self.open_names: set[str] = {"open"}

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            if alias.name == "os":
                self.os_aliases.add(alias.asname or alias.name)
        return self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        module = node.module or ""
        for alias in node.names:
            if module == "os" and alias.name == "getenv":
                self.getenv_aliases.add(alias.asname or alias.name)
            if module == "pathlib" and alias.name == "Path":
                self.path_names.add(alias.asname or alias.name)
            if alias.name == "resource_path":
                self.resource_names.add(alias.asname or alias.name)
        return self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        func = node.func

        if isinstance(func, ast.Attribute):
            if (
                func.attr == "getenv"
                and isinstance(func.value, ast.Name)
                and func.value.id in self.os_aliases
            ):
                name = self._extract_str_arg(node)
                if name:
                    self.env_calls.append(
                        {"var": name, "file": self.path, "line": node.lineno}
                    )
        elif isinstance(func, ast.Name) and func.id in self.getenv_aliases:
            name = self._extract_str_arg(node)
            if name:
                self.env_calls.append(
                    {"var": name, "file": self.path, "line": node.lineno}
                )

        func_name = None
        if isinstance(func, ast.Name):
            func_name = func.id
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            func_name = f"{func.value.id}.{func.attr}"

        if func_name in self.resource_names:
            path_arg = self._extract_str_arg(node)
            if path_arg:
                self.asset_calls.append(
                    {
                        "api": "resource_path",
                        "target": path_arg,
                        "file": self.path,
                        "line": node.lineno,
                    }
                )
        elif func_name in self.open_names:
            path_arg = self._extract_str_arg(node)
            if path_arg:
                self.asset_calls.append(
                    {
                        "api": "open",
                        "target": path_arg,
                        "file": self.path,
                        "line": node.lineno,
                    }
                )
        elif isinstance(func, ast.Name) and func.id in self.path_names:
            path_arg = self._extract_str_arg(node)
            if path_arg:
                self.asset_calls.append(
                    {
                        "api": "Path",
                        "target": path_arg,
                        "file": self.path,
                        "line": node.lineno,
                    }
                )

        return self.generic_visit(node)

    @staticmethod
    def _extract_str_arg(node: ast.Call, index: int = 0) -> Optional[str]:
        if not node.args or len(node.args) <= index:
            return None
        arg = node.args[index]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        return None


def scan_env_and_assets(
    py_files: Sequence[Path],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    env_calls: List[Dict[str, Any]] = []
    asset_calls: List[Dict[str, Any]] = []
    syntax_errors: List[Dict[str, Any]] = []
    for path in py_files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            syntax_errors.append(
                {
                    "file": str(path),
                    "line": exc.lineno,
                    "offset": exc.offset,
                    "msg": exc.msg,
                }
            )
            continue
        visitor = EnvAssetVisitor(path)
        visitor.visit(tree)
        env_calls.extend(visitor.env_calls)
        asset_calls.extend(visitor.asset_calls)
    return env_calls, asset_calls, syntax_errors


def parse_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    data: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        data[key] = value
    return data


def aggregate_env_usage(
    env_calls: Sequence[Dict[str, Any]],
    env_file_vars: Dict[str, str],
) -> List[Dict[str, Any]]:
    aggregated: Dict[str, Dict[str, Any]] = {}
    for call in env_calls:
        var = call["var"]
        entry = aggregated.setdefault(var, {"name": var, "locations": []})
        entry["locations"].append(
            {"file": safe_relpath(call["file"]), "line": call["line"]}
        )
    for var, entry in aggregated.items():
        entry["defined_in_env_file"] = var in env_file_vars
        entry["defined_in_os_env"] = var in os.environ
    return sorted(aggregated.values(), key=lambda x: x["name"])


def resolve_asset_candidates(
    target: str, src: Path
) -> Tuple[bool, Optional[Path], List[Path]]:
    candidates: List[Path] = []
    existing: Optional[Path] = None
    if not target:
        return False, None, candidates

    raw = Path(target)
    possible: List[Path] = []
    if raw.is_absolute():
        possible.append(raw)
    else:
        possible.append((ROOT / target).resolve())
        possible.append((src.parent / target).resolve())

    seen: set[Path] = set()
    for cand in possible:
        if cand in seen:
            continue
        seen.add(cand)
        candidates.append(cand)
        if cand.exists() and existing is None:
            existing = cand
    return existing is not None, existing, candidates


def evaluate_asset_references(
    asset_calls: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    evaluated: List[Dict[str, Any]] = []
    for ref in asset_calls:
        exists, found_path, candidates = resolve_asset_candidates(
            ref["target"], ref["file"]
        )
        evaluated.append(
            {
                "api": ref["api"],
                "target": ref["target"],
                "file": safe_relpath(ref["file"]),
                "line": ref["line"],
                "exists": exists,
                "found_path": str(found_path) if found_path else None,
                "candidates": [str(c) for c in candidates],
            }
        )
    return evaluated


def module_name_from_path(path: Path) -> Optional[str]:
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        return None
    parts = list(rel.parts)
    if not parts:
        return None
    if parts[-1].endswith(".py"):
        last = parts[-1][:-3]
        if last == "__init__":
            parts = parts[:-1]
        else:
            parts[-1] = last
    else:
        return None
    if not parts:
        return None
    return ".".join(parts)


def discover_modules(py_files: Sequence[Path]) -> List[Tuple[str, Path]]:
    modules: Dict[str, Path] = {}
    for path in py_files:
        name = module_name_from_path(path)
        if not name or name == "scripts.healthcheck":
            continue
        modules[name] = path
    return sorted(modules.items())


def extract_trace_location(
    tb: str,
) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    for line in reversed(tb.splitlines()):
        match = TRACE_RE.search(line)
        if match:
            file_path = match.group(1)
            try:
                line_no = int(match.group(2))
            except ValueError:
                line_no = None
            func = match.group(3)
            return file_path, line_no, func
    return None, None, None


def attempt_import(module: str) -> Dict[str, Any]:
    try:
        with contextlib.redirect_stdout(sys.stdout), contextlib.redirect_stderr(
            sys.stderr
        ):
            import importlib

            importlib.invalidate_caches()
            importlib.import_module(module)
        return {"module": module, "ok": True, "stdout": "", "stderr": ""}
    except Exception as exc:  # pragma: no cover
        tb = traceback.format_exc()
        file_path, line, func = extract_trace_location(tb)
        return {
            "module": module,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": tb,
            "file": file_path,
            "line": line,
            "function": func,
            "stdout": "",
            "stderr": "",
        }


def compare_latest_zip() -> Dict[str, Any]:
    zip_files = [p for p in ROOT.rglob("*.zip") if p.is_file()]
    if not zip_files:
        return {
            "zip_path": None,
            "missing_in_workspace": [],
            "missing_in_zip": [],
            "zip_entries_sample": [],
            "zip_mtime": None,
            "notes": ["Nenhum arquivo .zip encontrado."],
        }
    latest = max(zip_files, key=lambda p: p.stat().st_mtime)
    with zipfile.ZipFile(latest) as zf:
        names = [n for n in zf.namelist() if n and not n.endswith("/")]
    prefix = None
    if names:
        first_parts = {Path(n).parts[0] for n in names if Path(n).parts}
        if len(first_parts) == 1:
            (prefix,) = first_parts

    normalized_zip: set[str] = set()
    for name in names:
        parts = list(Path(name).parts)
        if prefix and parts and parts[0] == prefix:
            parts = parts[1:]
        normalized_zip.add("/".join(parts))

    workspace_files: set[str] = set()
    for path in ROOT.rglob("*"):
        if path.is_file() and not should_ignore(path):
            workspace_files.add(path.relative_to(ROOT).as_posix())

    missing_in_workspace = sorted(
        [e for e in normalized_zip if e and e not in workspace_files]
    )
    missing_in_zip = sorted(
        [e for e in workspace_files if e and e not in normalized_zip]
    )

    return {
        "zip_path": str(latest),
        "zip_mtime": datetime.fromtimestamp(latest.stat().st_mtime).isoformat(),
        "missing_in_workspace": missing_in_workspace[:MAX_DIFFS],
        "missing_in_workspace_truncated": len(missing_in_workspace) > MAX_DIFFS,
        "missing_in_zip": missing_in_zip[:MAX_DIFFS],
        "missing_in_zip_truncated": len(missing_in_zip) > MAX_DIFFS,
        "zip_entries_sample": sorted(list(normalized_zip))[:50],
        "notes": [],
    }


def find_symbol_line(file: Path, symbol: str) -> int | None:
    try:
        text = file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    # casa "def NOME" OU "class NOME"
    pattern = rf"^\s*(?:def|class)\s+{re.escape(symbol)}\b"
    m = re.search(pattern, text, flags=re.M)
    if m:
        return text[: m.start()].count("\n") + 1
    return None


def find_line_with_text(path: Path, text: str) -> Optional[int]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return None
    for idx, line in enumerate(lines, start=1):
        if text in line:
            return idx
    return None


def find_pyinstaller_artifacts(
    py_files: Sequence[Path], zip_info: Dict[str, Any]
) -> Dict[str, Any]:
    spec_files = [
        p for p in ROOT.rglob("*.spec") if p.is_file() and not should_ignore(p)
    ]
    refs: List[str] = []
    for path in py_files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "pyinstaller" in text.lower():
            refs.append(safe_relpath(path))

    normalized_zip = set(zip_info.get("zip_entries_sample", []))
    includes = {
        ".env": ".env" in normalized_zip,
        "CHANGELOG.md": "CHANGELOG.md" in normalized_zip,
        "rc.ico": "rc.ico" in normalized_zip,
        "rc.png": "rc.png" in normalized_zip,
    }

    notes: List[str] = []
    if not spec_files:
        notes.append(
            "Nenhum arquivo .spec encontrado; revisar configuracao do PyInstaller manualmente."
        )
    if not refs:
        notes.append("Nenhuma referencia a PyInstaller encontrada no codigo.")

    return {
        "spec_files": [safe_relpath(p) for p in spec_files],
        "pyinstaller_references": refs,
        "includes_detected_in_zip": includes,
        "notes": notes,
    }


def build_log_suggestions() -> List[Dict[str, Any]]:
    items = [
        # infra/supabase_client.py
        {
            "file": ROOT / "infra" / "supabase_client.py",
            "locator": ("symbol", "baixar_pasta_zip", 0),
            "level": "INFO",
            "message": "Iniciar download via Edge Function zipper (bucket, prefix, zip_name, timeout).",
            "context": "Registrar parametros e marcar inicio para medir duracao.",
            "verbose": False,
        },
        {
            "file": ROOT / "infra" / "supabase_client.py",
            "locator": ("text", "if resp.status_code != 200", 0),
            "level": "WARNING",
            "message": "HTTP {status_code} ao baixar ZIP; anexar detalhe retornado pelo servidor.",
            "context": "Investigar erros de autorizacao ou limites do Supabase.",
            "verbose": False,
        },
        {
            "file": ROOT / "infra" / "supabase_client.py",
            "locator": ("text", "except req_exc.RequestException as e", 0),
            "level": "EXCEPTION",
            "message": "Falha de rede ao baixar pasta; incluir tipo de excecao e tentativas.",
            "context": "Capturar stack trace para diagnosticar intermitencias.",
            "verbose": False,
        },
        # ui/files_browser.py
        {
            "file": ROOT / "ui" / "files_browser.py",
            "locator": ("symbol", "open_files_browser", 0),
            "level": "INFO",
            "message": "Usuario abriu navegador de arquivos; logar org_id/client_id e raiz atual.",
            "context": "Auditar navegacao e identificar gargalos de listagem.",
            "verbose": False,
        },
        {
            "file": ROOT / "ui" / "files_browser.py",
            "locator": ("text", "def do_download()", 0),
            "level": "INFO",
            "message": "Download individual solicitado; registrar caminho remoto e destino local.",
            "context": "Cobrir fluxo do botao Baixar selecionado.",
            "verbose": False,
        },
        # infra/upload_queue.py
        {
            "file": ROOT / "infra" / "upload_queue.py",
            "locator": ("symbol", "enqueue", 0),
            "level": "WARNING",
            "message": "Arquivo enfileirado para reenvio; incluir bucket, storage_path e hash.",
            "context": "Sinalizar operacoes offline e backlog de sincronizacao.",
            "verbose": False,
        },
        {
            "file": ROOT / "infra" / "upload_queue.py",
            "locator": ("symbol", "flush_once", 0),
            "level": "VERBOSE",
            "message": "RC_VERBOSE=1: logar CALL/DONE com tempo de execucao do reenvio.",
            "context": "Monitorar desempenho da drenagem sem poluir logs padrao.",
            "verbose": True,
        },
        # core/db_manager
        {
            "file": ROOT / "core" / "db_manager" / "db_manager.py",
            "locator": ("symbol", "insert_cliente", 0),
            "level": "INFO",
            "message": "Novo cliente inserido; registrar numero/cnpj e retorno do Supabase.",
            "context": "Rastrear inclusoes e fallback ao buscar ID.",
            "verbose": False,
        },
        {
            "file": ROOT / "core" / "db_manager" / "db_manager.py",
            "locator": ("symbol", "soft_delete_clientes", 0),
            "level": "WARNING",
            "message": "Solicitacao de soft-delete; listar quantidade de IDs e timestamp aplicado.",
            "context": "Auditar exclusoes em massa.",
            "verbose": False,
        },
        # app_gui.py
        {
            "file": ROOT / "app_gui.py",
            "locator": ("text", "def main()", 0),
            "level": "VERBOSE",
            "message": "RC_VERBOSE=1: logar CALL/DONE do bootstrap principal e tempo total.",
            "context": "Medir inicializacao da interface grafica.",
            "verbose": True,
        },
    ]

    suggestions: List[Dict[str, Any]] = []
    for item in items:
        path = item["file"]
        if not path.exists():
            continue
        locator_type, locator_value, offset = item["locator"]
        line: Optional[int] = None
        if locator_type == "symbol":
            line = find_symbol_line(path, locator_value)
        elif locator_type == "text":
            line = find_line_with_text(path, locator_value)
        if line is not None and offset:
            line += offset
        suggestions.append(
            {
                "file": safe_relpath(path),
                "line": line,
                "level": item["level"],
                "message": item["message"],
                "context": item["context"],
                "verbose": item["verbose"],
            }
        )
    return suggestions


def safe_relpath(path: Path | str | None) -> str:
    if path is None:
        return ""
    path_obj = Path(path)
    try:
        return path_obj.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path_obj)


def sanitize_markdown(text: str) -> str:
    return text.replace("|", "\\|").replace("`", "\\`")


def indent_block(text: str, prefix: str) -> str:
    return "\n".join(
        f"{prefix}{line}" if line else prefix for line in text.splitlines()
    )


# ---------- rendering ----------


def render_markdown(data: Dict[str, Any]) -> str:
    errors = data["summary"]["errors"]
    warnings = data["summary"]["warnings"]

    def format_command_block(cmd: Dict[str, Any]) -> str:
        body: List[str] = []
        body.append(f"- Comando: `{cmd['command']}`")
        rc = cmd.get("returncode")
        body.append(
            "  - Retorno: nao executado" if rc is None else f"  - Retorno: {rc}"
        )
        if cmd.get("error"):
            body.append(f"  - Erro: {cmd['error']}")
        if cmd.get("stdout"):
            body.append("  - stdout:")
            body.append("    ```")
            body.append(indent_block(cmd["stdout"], "    "))
            body.append("    ```")
        if cmd.get("stderr"):
            body.append("  - stderr:")
            body.append("    ```")
            body.append(indent_block(cmd["stderr"], "    "))
            body.append("    ```")
        return "\n".join(body)

    lines: List[str] = []
    lines.append(f"# VARREDURA DO PROJETO ({data['generated_at']})\n")
    lines.append("## Resumo")
    lines.append(f"- Erros: {len(errors)}")
    for msg in errors[:10]:
        lines.append(f"  - {msg}")
    if len(errors) > 10:
        lines.append(f"  - ... (+{len(errors) - 10} itens)")
    lines.append(f"- Avisos: {len(warnings)}")
    for msg in warnings[:10]:
        lines.append(f"  - {msg}")
    if len(warnings) > 10:
        lines.append(f"  - ... (+{len(warnings) - 10} itens)")
    lines.append(f"- OK: {data['summary']['ok_message']}\n")

    lines.append("## Ambiente Python")
    for cmd in data["commands"][:2]:
        lines.append(format_command_block(cmd))
        lines.append("")

    lines.append("## Dependencias (pip check)")
    lines.append(format_command_block(data["pip_check"]))
    lines.append("")

    lines.append("## Imports quebrados")
    broken = data["broken_imports"]
    if not broken:
        lines.append("- Nenhum problema de import identificado.")
    else:
        lines.append("| Modulo | Arquivo | Linha | Erro |")
        lines.append("| --- | --- | --- | --- |")
        for item in broken:
            file_ref = item.get("file")
            if file_ref:
                file_ref = safe_relpath(file_ref)
            lines.append(
                f"| `{item['module']}` | `{file_ref or ''}` | {item.get('line') or ''} | {sanitize_markdown(item['error'])} |"
            )
    lines.append("")

    lines.append("## Arquivos/recursos faltando")
    missing_assets = [a for a in data["assets"] if not a["exists"]]
    if not missing_assets:
        lines.append("- Nenhum asset faltando detectado para chamadas diretas.")
    else:
        lines.append("| API | Alvo | Localizacao | Candidatos verificados |")
        lines.append("| --- | --- | --- | --- |")
        for asset in missing_assets:
            candidates = "<br>".join(asset["candidates"])
            lines.append(
                f"| {asset['api']} | `{sanitize_markdown(asset['target'])}` | {asset['file']}:{asset['line']} | {sanitize_markdown(candidates)} |"
            )
    lines.append("")

    lines.append("## Variaveis de ambiente")
    if not data["env_usage"]:
        lines.append("- Nenhuma chamada direta a os.getenv encontrada.")
    else:
        lines.append(
            "| Variavel | Definida em `.env` | Definida no ambiente | Onde e usada |"
        )
        lines.append("| --- | --- | --- | --- |")
        for var in data["env_usage"]:
            where = "<br>".join(
                f"{loc['file']}:{loc['line']}" for loc in var["locations"]
            )
            lines.append(
                f"| `{var['name']}` | {'Sim' if var['defined_in_env_file'] else 'Nao'} | {'Sim' if var['defined_in_os_env'] else 'Nao'} | {where} |"
            )
    lines.append("")

    lines.append("## Erros de compile/import")
    lines.append(format_command_block(data["compile_command"]))
    lines.append("")
    if data["syntax_errors"]:
        lines.append("### Erros de sintaxe detectados via AST")
        for err in data["syntax_errors"]:
            lines.append(
                f"- {safe_relpath(err['file'])}:{err['line']} (offset {err.get('offset')}) -> {err['msg']}"
            )
        lines.append("")

    lines.append("## Smoke tests")
    tk = data["tkinter_smoke"]
    if tk["ok"]:
        lines.append("- Tkinter: OK (janela criada e destruida).")
    else:
        lines.append(f"- Tkinter: FALHA -> {tk['error']}")
        if tk.get("traceback"):
            lines.append("```")
            lines.append(tk["traceback"])
            lines.append("```")
    for script in data["diagnostic_scripts"]:
        lines.append(format_command_block(script))
        lines.append("")
    if not data["diagnostic_scripts"]:
        lines.append(
            "- Nenhum script de smoke executado (use --skip-smoke para manter skip explicito)."
        )
        lines.append("")

    lines.append("## Comparacao com o ultimo .zip")
    zip_info = data["zip_comparison"]
    if not zip_info["zip_path"]:
        lines.append("- Nenhum arquivo .zip encontrado.")
    else:
        lines.append(f"- ZIP analisado: `{safe_relpath(zip_info['zip_path'])}`")
        lines.append(f"- Modificacao: {zip_info['zip_mtime']}")
        if zip_info["missing_in_workspace"]:
            lines.append("### Presentes no ZIP e ausentes no workspace")
            for entry in zip_info["missing_in_workspace"]:
                lines.append(f"- {entry}")
            if zip_info.get("missing_in_workspace_truncated"):
                lines.append("- ... lista truncada.")
        else:
            lines.append("- Nenhuma falta no workspace em relacao ao ZIP.")
        if zip_info["missing_in_zip"]:
            lines.append("### Presentes no workspace e ausentes no ZIP")
            for entry in zip_info["missing_in_zip"]:
                lines.append(f"- {entry}")
            if zip_info.get("missing_in_zip_truncated"):
                lines.append("- ... lista truncada.")
        else:
            lines.append("- Nenhum arquivo extra encontrado fora do ZIP.")
    lines.append("")

    lines.append("## Checklist PyInstaller")
    pyinst = data["pyinstaller"]
    if pyinst["spec_files"]:
        lines.append("- Arquivos .spec:")
        for spec in pyinst["spec_files"]:
            lines.append(f"  - `{spec}`")
    else:
        lines.append("- Nenhum .spec identificado.")
    if pyinst["pyinstaller_references"]:
        lines.append("- Referencias a PyInstaller no codigo:")
        for ref in pyinst["pyinstaller_references"]:
            lines.append(f"  - `{ref}`")
    includes = pyinst["includes_detected_in_zip"]
    if includes:
        lines.append("- Arquivos relevantes encontrados no ZIP:")
        for key, present in includes.items():
            lines.append(f"  - {key}: {'OK' if present else 'Nao encontrado'}")
    if pyinst["notes"]:
        lines.append("- Observacoes:")
        for note in pyinst["notes"]:
            lines.append(f"  - {note}")
    lines.append("")

    lines.append("## Pontos recomendados de LOG")
    suggestions = data["log_suggestions"]
    if not suggestions:
        lines.append("- Nenhuma sugestao automatica gerada.")
    else:
        for item in suggestions:
            location = (
                f"{item['file']}:{item['line']}" if item["line"] else item["file"]
            )
            lines.append(f"- **{item['level']}** @ `{location}` — {item['message']}")
            lines.append(f"  - Contexto: {item['context']}")
            if item["verbose"]:
                lines.append("  - Ativar apenas com `RC_VERBOSE=1`.")
    lines.append("")

    lines.append("## Checagens especificas")
    for check in data["special_checks"]:
        status = "OK" if check["ok"] else "FALHA"
        detail = f" {check['detail']}" if check.get("detail") else ""
        lines.append(f"- {status}: {check['label']}{detail}")
    lines.append("")

    lines.append("## Comandos executados (detalhe)")
    for cmd in data["commands"]:
        lines.append(format_command_block(cmd))
        lines.append("")
    lines.append(format_command_block(data["pip_check"]))
    lines.append("")
    lines.append(format_command_block(data["compile_command"]))
    lines.append("")
    for script in data["diagnostic_scripts"]:
        lines.append(format_command_block(script))
        lines.append("")

    return "\n".join(lines).strip() + "\n"


# ---------- CLI ----------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Varredura estatica + smoke do projeto."
    )
    parser.add_argument(
        "--write-md", default=DEFAULT_REPORT, help="Caminho do markdown de saida."
    )
    parser.add_argument(
        "--json", help="Opcional: caminho para salvar relatorio em JSON."
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Nao executar scripts/smoke_test.py nem smoke Tkinter.",
    )
    return parser.parse_args()


# ---------- main ----------


def main() -> int:
    args = parse_args()

    summary = {"errors": [], "warnings": []}
    commands: List[Dict[str, Any]] = []

    # python/pip
    cmd_python_v = run_command(["python", "-V"])
    commands.append(cmd_python_v.to_dict())
    if cmd_python_v.returncode not in (0,):
        summary["errors"].append("python -V falhou.")

    cmd_pip_version = run_command(["pip", "--version"])
    if cmd_pip_version.returncode is None and cmd_pip_version.error:
        summary["warnings"].append(
            "pip --version nao encontrado; usando python -m pip --version."
        )
        cmd_pip_version = run_command([sys.executable, "-m", "pip", "--version"])
        cmd_pip_version.command = f"{sys.executable} -m pip --version"
    commands.append(cmd_pip_version.to_dict())
    if cmd_pip_version.returncode not in (0,):
        summary["errors"].append("pip --version retornou codigo diferente de zero.")

    # pip check
    if any(ROOT.glob("requirements*.txt")) or (ROOT / "pyproject.toml").exists():
        pip_check = run_command(["python", "-m", "pip", "check"])
        if pip_check.returncode not in (0,):
            summary["errors"].append("python -m pip check apontou conflitos ou faltas.")
    else:
        pip_check = CommandResult(
            "python -m pip check",
            None,
            "Requisitos nao detectados (requirements*.txt ou pyproject.toml ausente).",
            "",
            None,
        )
        summary["warnings"].append(
            "Nenhum arquivo de requisitos encontrado; pip check nao executado."
        )

    # compileall
    compile_cmd = run_command(["python", "-m", "compileall", "."])
    if compile_cmd.returncode not in (0,):
        summary["errors"].append("python -m compileall . retornou erros.")

    # scans
    py_files = collect_python_files()
    env_calls, asset_calls, syntax_errors = scan_env_and_assets(py_files)
    env_vars_file = parse_env_file(ROOT / ".env")
    env_usage = aggregate_env_usage(env_calls, env_vars_file)
    assets = evaluate_asset_references(asset_calls)

    for var in env_usage:
        if not var["defined_in_env_file"] and not var["defined_in_os_env"]:
            summary["warnings"].append(
                f"Variavel {var['name']} nao definida em .env nem no ambiente."
            )

    for asset in assets:
        if not asset["exists"]:
            summary["errors"].append(
                f"Asset ausente: {asset['target']} referenciado em {asset['file']}:{asset['line']}."
            )

    # imports
    sys_path_added = False
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
        sys_path_added = True

    import_results: List[Dict[str, Any]] = []
    broken_imports: List[Dict[str, Any]] = []
    for module, _ in discover_modules(py_files):
        result = attempt_import(module)
        import_results.append(result)
        if not result["ok"]:
            broken_imports.append(result)
            summary["errors"].append(f"Import falhou: {module} -> {result['error']}")

    if sys_path_added:
        with contextlib.suppress(ValueError):
            sys.path.remove(str(ROOT))

    # smokes
    diagnostic_scripts: List[Dict[str, Any]] = []
    tk_result: Dict[str, Any] = {"ok": True}
    if not args.skip_smoke:
        scripts_dir = ROOT / "scripts"
        smoke_path = scripts_dir / "smoke_test.py"
        if smoke_path.exists():
            res = run_command([sys.executable, str(smoke_path)])
            res_dict = res.to_dict()
            res_dict["command"] = f"{sys.executable} {safe_relpath(smoke_path)}"
            diagnostic_scripts.append(res_dict)
            if res.returncode not in (0,):
                summary["errors"].append(
                    "scripts/smoke_test.py retornou codigo nao-zero."
                )

        try:
            import tkinter as tk  # noqa: F401

            root = tk.Tk()
            root.update()
            root.destroy()
        except Exception as exc:  # pragma: no cover
            tk_result = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
            summary["errors"].append("Falha no smoke Tkinter.")
    else:
        tk_result = {"ok": False, "error": "Smoke desativado via --skip-smoke."}

    # zip
    zip_info = compare_latest_zip()
    if not zip_info["zip_path"]:
        summary["warnings"].append("Nenhum arquivo .zip encontrado para comparacao.")

    # pyinstaller
    pyinstaller_info = find_pyinstaller_artifacts(py_files, zip_info)
    for note in pyinstaller_info["notes"]:
        summary["warnings"].append(note)

    # checagens especificas
    special_checks: List[Dict[str, Any]] = []

    files_browser = ROOT / "ui" / "files_browser.py"
    if files_browser.exists():
        line_fb = find_symbol_line(files_browser, "open_files_browser")
        ok = line_fb is not None
        if not ok:
            summary["errors"].append(
                "ui/files_browser.py nao expoe open_files_browser."
            )
        special_checks.append(
            {
                "label": "ui/files_browser.open_files_browser",
                "ok": ok,
                "detail": f"(linha {line_fb})" if line_fb else "",
            }
        )
    else:
        summary["warnings"].append("ui/files_browser.py nao encontrado.")

    supabase_client = ROOT / "infra" / "supabase_client.py"
    if supabase_client.exists():
        line_zip = find_symbol_line(supabase_client, "baixar_pasta_zip")
        line_exc = find_symbol_line(supabase_client, "DownloadCancelledError")
        ok_zip = line_zip is not None
        ok_exc = line_exc is not None
        if not ok_zip:
            summary["errors"].append(
                "infra/supabase_client.py sem funcao baixar_pasta_zip."
            )
        if not ok_exc:
            summary["errors"].append(
                "infra/supabase_client.py sem classe DownloadCancelledError."
            )
        special_checks.append(
            {
                "label": "infra/supabase_client.baixar_pasta_zip",
                "ok": ok_zip,
                "detail": f"(linha {line_zip})" if line_zip else "",
            }
        )
        special_checks.append(
            {
                "label": "infra/supabase_client.DownloadCancelledError",
                "ok": ok_exc,
                "detail": f"(linha {line_exc})" if line_exc else "",
            }
        )
    else:
        summary["errors"].append("infra/supabase_client.py nao encontrado.")

    log_suggestions = build_log_suggestions()
    summary.setdefault("ok_message", "Checagens executadas; veja secoes abaixo.")

    # report
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "commands": commands,
        "pip_check": (
            pip_check.to_dict() if isinstance(pip_check, CommandResult) else pip_check
        ),
        "compile_command": compile_cmd.to_dict(),
        "env_usage": env_usage,
        "assets": assets,
        "syntax_errors": syntax_errors,
        "import_results": import_results,
        "broken_imports": broken_imports,
        "diagnostic_scripts": diagnostic_scripts,
        "tkinter_smoke": tk_result,
        "zip_comparison": zip_info,
        "pyinstaller": pyinstaller_info,
        "special_checks": special_checks,
        "log_suggestions": log_suggestions,
    }

    markdown = render_markdown(report)

    out_path = Path(args.write_md)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    if not CLOUD_ONLY:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    if args.json:
        json_path = Path(args.json)
        if not json_path.is_absolute():
            json_path = ROOT / json_path
        if not CLOUD_ONLY:
            json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=_json_default),
            encoding="utf-8",
        )

    print(f"Relatorio gerado em {out_path}")
    if args.json:
        print(f"JSON salvo em {json_path}")

    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
