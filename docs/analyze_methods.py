"""Analisa tamanho dos métodos em main_window.py"""

import re

file_path = "src/modules/main_window/views/main_window.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

methods = []
current_method = None
start_line = 0
indent_level = 0

for i, line in enumerate(lines, 1):
    # Detectar definição de método (indentado 4 espaços = método de classe)
    match = re.match(r"^    def (\w+)\(", line)
    if match:
        # Salvar método anterior
        if current_method:
            methods.append((current_method, start_line, i - 1, i - start_line))

        current_method = match.group(1)
        start_line = i
        indent_level = len(line) - len(line.lstrip())

# Adicionar último método
if current_method:
    methods.append((current_method, start_line, len(lines), len(lines) - start_line + 1))

# Ordenar por tamanho (descendente)
methods.sort(key=lambda x: x[3], reverse=True)

print(f"\n{'=' * 80}")
print("TOP 15 MÉTODOS MAIS LONGOS em main_window.py")
print(f"{'=' * 80}\n")
print(f"{'#':<4} {'Método':<40} {'Linhas':<8} {'Range':<15}")
print(f"{'-' * 80}")

for idx, (name, start, end, size) in enumerate(methods[:15], 1):
    print(f"{idx:<4} {name:<40} {size:<8} L{start}-{end}")

print(f"\n{'=' * 80}")
print(f"Total de métodos analisados: {len(methods)}")
print(f"Soma Top 15: {sum(m[3] for m in methods[:15])} linhas")
print(f"{'=' * 80}\n")
