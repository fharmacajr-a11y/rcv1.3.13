# -*- coding: utf-8 -*-
"""
Script de validação: verifica ausência de ttkbootstrap no código.

Uso:
    python scripts/validate_no_ttkbootstrap.py
    python scripts/validate_no_ttkbootstrap.py --path src/modules/clientes
    python scripts/validate_no_ttkbootstrap.py --path src/modules/clientes --enforce
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def find_ttkbootstrap_usage(root_path: Path, enforce: bool = False) -> int:
    """Encontra usos de ttkbootstrap no código.
    
    Args:
        root_path: Diretório raiz para busca.
        enforce: Se True, considera comentários como violação.
        
    Returns:
        Número de violações encontradas.
    """
    violations = 0
    
    # Padrões a procurar
    import_pattern = re.compile(r"^\s*import\s+ttkbootstrap", re.MULTILINE)
    from_pattern = re.compile(r"^\s*from\s+ttkbootstrap", re.MULTILINE)
    bootstyle_pattern = re.compile(r"\bbootstyle\s*=", re.MULTILINE)
    tb_widget_pattern = re.compile(r"\btb\.(Frame|Button|Label|Entry|Combobox|Toplevel|Checkbutton|Text|Scrollbar)\b")
    
    for py_file in root_path.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
            
            # Remove comentários se não estiver no modo enforce
            if not enforce:
                lines = content.split("\n")
                filtered_lines = []
                for line in lines:
                    # Remove comentários inline
                    if "#" in line:
                        code_part = line.split("#")[0]
                        filtered_lines.append(code_part)
                    else:
                        filtered_lines.append(line)
                content = "\n".join(filtered_lines)
            
            file_violations = []
            
            # Verifica import ttkbootstrap
            for match in import_pattern.finditer(content):
                line_num = content[:match.start()].count("\n") + 1
                file_violations.append((line_num, f"import ttkbootstrap encontrado"))
            
            # Verifica from ttkbootstrap
            for match in from_pattern.finditer(content):
                line_num = content[:match.start()].count("\n") + 1
                file_violations.append((line_num, f"from ttkbootstrap encontrado"))
            
            # Verifica bootstyle=
            for match in bootstyle_pattern.finditer(content):
                line_num = content[:match.start()].count("\n") + 1
                file_violations.append((line_num, f"parâmetro bootstyle= encontrado"))
            
            # Verifica tb.Widget
            for match in tb_widget_pattern.finditer(content):
                line_num = content[:match.start()].count("\n") + 1
                widget = match.group(1)
                file_violations.append((line_num, f"tb.{widget} encontrado (widget ttkbootstrap)"))
            
            if file_violations:
                violations += len(file_violations)
                rel_path = py_file.relative_to(root_path)
                print(f"\n❌ {rel_path}:")
                for line_num, msg in file_violations:
                    print(f"  Linha {line_num}: {msg}")
        
        except Exception as e:
            print(f"⚠️  Erro ao processar {py_file}: {e}", file=sys.stderr)
    
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida ausência de ttkbootstrap no código")
    parser.add_argument(
        "--path",
        type=str,
        default="src",
        help="Caminho para validar (padrão: src)",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Modo estrito: considera comentários como violação",
    )
    args = parser.parse_args()
    
    root = Path(args.path)
    if not root.exists():
        print(f"❌ Caminho não encontrado: {root}", file=sys.stderr)
        return 1
    
    print(f"🔍 Validando ausência de ttkbootstrap em: {root}")
    if args.enforce:
        print("⚠️  Modo estrito ativado (comentários serão validados)")
    print()
    
    violations = find_ttkbootstrap_usage(root, args.enforce)
    
    if violations == 0:
        print("✅ Nenhum uso de ttkbootstrap encontrado!")
        print("✅ Migração para CustomTkinter completa!")
        return 0
    else:
        print(f"\n❌ {violations} violação(ões) encontrada(s).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
