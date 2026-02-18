#!/usr/bin/env python3
"""
MICROFASE 36 - Validador de kwargs inválidos CustomTkinter
==========================================

Este script detecta automaticamente kwargs inválidos que causam crashes em CTk widgets.
Verifica os problemas mais comuns:
- padding= em CTkFrame, CTkButton, CTkLabel
- text= em CTkFrame
- labelwidget= em CTkFrame
- bootstyle= em CTk widgets (é para ttkbootstrap apenas)

Uso:
    python scripts/validate_ctk_kwargs.py
    python scripts/validate_ctk_kwargs.py --fix  # modo automático (futuro)
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict


# Widgets CTk e seus kwargs inválidos mais comuns
INVALID_KWARGS = {
    "CTkFrame": ["padding", "text", "labelwidget", "bootstyle"],
    "CTkButton": ["padding", "bootstyle"],
    "CTkLabel": ["padding", "bootstyle"],
    "CTkEntry": ["padding", "bootstyle"],
    "CTkCheckBox": ["padding", "bootstyle"],
    "CTkRadioButton": ["padding", "bootstyle", "style"],
    "CTkComboBox": ["padding", "bootstyle", "textvariable"],  # CTkComboBox não suporta textvariable
    "CTkSwitch": ["padding", "bootstyle"],
    "CTkSlider": ["padding", "bootstyle"],
    "CTkProgressBar": ["padding", "bootstyle"],
    "CTkTextbox": ["padding", "bootstyle"],
    "CTkScrollableFrame": ["padding", "bootstyle"],
}

# Padrões regex para detectar cada tipo de problema
PATTERNS = {
    "widget_constructor": re.compile(r"(\w+\.(CTk\w+))\s*\(\s*([^)]+)\s*\)", re.MULTILINE | re.DOTALL),
    "kwargs_parser": re.compile(r"(\w+)\s*=\s*([^,)]+)", re.MULTILINE),
}


class CTkKwargsValidator:
    """Valida kwargs inválidos em CustomTkinter widgets"""

    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.issues: List[Dict] = []

    def scan_workspace(self) -> int:
        """
        Escaneia todo o workspace buscando problemas de kwargs inválidos.
        Retorna número total de issues encontradas.
        """
        print("🔍 Escaneando workspace para kwargs inválidos...")
        print(f"📁 Workspace: {self.workspace_path}")
        print()

        # Buscar todos arquivos .py no src/
        src_path = self.workspace_path / "src"
        if not src_path.exists():
            print("❌ Pasta src/ não encontrada!")
            return 0

        py_files = list(src_path.rglob("*.py"))
        print(f"📄 Analisando {len(py_files)} arquivos Python...")
        print()

        for py_file in py_files:
            try:
                self._scan_file(py_file)
            except Exception as e:
                print(f"⚠️  Erro ao analisar {py_file}: {e}")

        return len(self.issues)

    def _scan_file(self, file_path: Path) -> None:
        """Escaneia um arquivo específico"""
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Tentar com latin-1 se UTF-8 falhar
            content = file_path.read_text(encoding="latin-1")

        # Buscar todas as construções de widgets CTk
        for match in PATTERNS["widget_constructor"].finditer(content):
            match.group(0)
            widget_class = match.group(2)
            args_section = match.group(3)

            if widget_class not in INVALID_KWARGS:
                continue

            # Extrair kwargs do construtor
            kwargs = self._extract_kwargs(args_section)

            # Verificar se há kwargs inválidos para este widget
            invalid_found = []
            for kwarg in kwargs:
                if kwarg in INVALID_KWARGS[widget_class]:
                    invalid_found.append(kwarg)

            if invalid_found:
                line_num = content[: match.start()].count("\n") + 1

                self.issues.append(
                    {
                        "file": str(file_path),
                        "line": line_num,
                        "widget": widget_class,
                        "invalid_kwargs": invalid_found,
                        "code_snippet": self._get_code_context(content, match.start(), match.end()),
                        "severity": self._classify_severity(invalid_found),
                    }
                )

    def _extract_kwargs(self, args_text: str) -> List[str]:
        """Extrai nomes de kwargs de uma string de argumentos"""
        kwargs = []

        for match in PATTERNS["kwargs_parser"].finditer(args_text):
            kwarg_name = match.group(1).strip()
            # Filtrar argumentos posicionais e métodos
            if not kwarg_name.startswith("_") and kwarg_name.isidentifier():
                kwargs.append(kwarg_name)

        return kwargs

    def _get_code_context(self, content: str, start: int, end: int) -> str:
        """Obtém contexto do código ao redor do problema"""
        lines = content.split("\n")
        start_line = content[:start].count("\n")

        # Pegar 2 linhas antes e depois para contexto
        context_start = max(0, start_line - 2)
        context_end = min(len(lines), start_line + 3)

        context_lines = []
        for i in range(context_start, context_end):
            prefix = ">>>" if i == start_line else "   "
            context_lines.append(f"{prefix} {i + 1:3}: {lines[i]}")

        return "\n".join(context_lines)

    def _classify_severity(self, invalid_kwargs: List[str]) -> str:
        """Classifica severidade do problema"""
        if any(k in ["padding", "textvariable"] for k in invalid_kwargs):
            return "CRITICAL"  # Causa ValueError imediatamente
        elif any(k in ["text", "labelwidget"] for k in invalid_kwargs):
            return "HIGH"  # Pode causar crashes dependendo do contexto
        else:
            return "MEDIUM"  # bootstyle e outros: ignorados silenciosamente

    def print_report(self) -> None:
        """Imprime relatório detalhado dos problemas encontrados"""
        if not self.issues:
            print("✅ Nenhum problema de kwargs inválidos encontrado!")
            return

        print(f"❌ {len(self.issues)} problema(s) encontrado(s):")
        print()

        # Agrupar por severidade
        by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": []}
        for issue in self.issues:
            by_severity[issue["severity"]].append(issue)

        # Mostrar críticos primeiro
        for severity in ["CRITICAL", "HIGH", "MEDIUM"]:
            issues_in_level = by_severity[severity]
            if not issues_in_level:
                continue

            print(f"🔴 {severity} ({len(issues_in_level)} issue(s)):")
            print("-" * 50)

            for issue in issues_in_level:
                rel_path = os.path.relpath(issue["file"], self.workspace_path)
                print(f"📄 {rel_path}:{issue['line']}")
                print(f"🔧 Widget: {issue['widget']}")
                print(f"⚠️  Kwargs inválidos: {', '.join(issue['invalid_kwargs'])}")
                print("📝 Código:")
                print(issue["code_snippet"])
                print()

        # Estatísticas finais
        print("📊 ESTATÍSTICAS:")
        print(f"   • Total de issues: {len(self.issues)}")
        print(f"   • Críticas: {len(by_severity['CRITICAL'])}")
        print(f"   • Altas: {len(by_severity['HIGH'])}")
        print(f"   • Médias: {len(by_severity['MEDIUM'])}")
        print()

        if by_severity["CRITICAL"]:
            print("⚡ AÇÃO NECESSÁRIA: Issues críticas causam crashes imediatos!")
            print("   Recomendação: Corrigir 'padding=' primeiro, depois 'text='/'labelwidget='")


def main():
    """Função principal"""
    workspace = Path(__file__).parent.parent  # v1.5.54

    print("=" * 60)
    print("🔍 MICROFASE 36 - Validador CTk kwargs")
    print("=" * 60)
    print()

    validator = CTkKwargsValidator(str(workspace))
    total_issues = validator.scan_workspace()

    print()
    validator.print_report()

    if total_issues > 0:
        print()
        print("💡 SOLUÇÕES RECOMENDADAS:")
        print("   • padding= → usar pack(padx=, pady=) ou grid(padx=, pady=)")
        print("   • textvariable= → CTkComboBox usa .set()/.get() ao invés de StringVar")
        print("   • text= em CTkFrame → usar CTkSection ou CTkLabel separado")
        print("   • bootstyle= → remover (é específico do ttkbootstrap)")
        print("   • labelwidget= → usar layout manual com CTkLabel")

        return 1  # Exit code para CI/CD
    else:
        print("🎉 Projeto está 100% compatível com CustomTkinter!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
