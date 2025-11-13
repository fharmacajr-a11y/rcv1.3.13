# QA-DELTA-15: CompatPack-09 - Type-Safe analyze_supabase_errors DevTool

**Data**: 2025-11-13
**Branch**: `qa/fixpack-04`
**Autor**: QA Session 15
**Status**: ✅ Concluído

---

## 📋 Resumo Executivo

CompatPack-09 adicionou type hints completos ao script de análise `analyze_supabase_errors.py`, eliminando **100% dos avisos Pyright/Pylance** (18 → 0). Introduziu TypedDicts para estrutura Pyright JSON e anotações explícitas em todas variáveis/funções.

### Métricas

| Métrica                                   | Antes | Depois | Δ        |
|-------------------------------------------|-------|--------|----------|
| Pyright warnings em analyze_supabase_errors.py | 18    | 0      | **-18** ✅ |
| reportUnknownVariableType                 | 6     | 0      | **-6**   |
| reportUnknownMemberType                   | 5     | 0      | **-5**   |
| reportUnknownArgumentType                 | 7     | 0      | **-7**   |
| Script functionality                      | ✅ OK | ✅ OK  | 0        |

---

## 🎯 Objetivo

Eliminar **todos** os avisos Pyright em `devtools/qa/analyze_supabase_errors.py`:
- **TypedDict para Pyright JSON**: PyrightDiagnostic, PyrightRange, PyrightRangePos
- **Type annotations explícitas**: todas variáveis (`by_file`, `errors`, `line`, `msg`)
- **Funções helper tipadas**: load_pyright_report, filter_supabase_errors, etc.
- **Sem mudança de comportamento**: mesmo output de antes

### Restrições

- ✅ **TypedDict completo**: Modelar estrutura JSON Pyright
- ✅ **Type annotations**: Todas variáveis/parâmetros/retornos
- ✅ **Funções helper**: Extrair lógica complexa para funções tipadas
- ✅ **Comportamento preservado**: Script produz saída idêntica
- ✅ **DevTool apenas**: Não tocar em código de produção

---

## 🔧 Implementação

### 1. TypedDict definitions para Pyright JSON

**Antes**:
```python
import json
from pathlib import Path


def main() -> None:
    """Filter and display Supabase-related Pyright errors."""
    qa_dir = Path(__file__).parent
    pyright_json = qa_dir / "pyright.json"

    if not pyright_json.exists():
        print(f"❌ {pyright_json} not found. Run pyright first.")
        return

    with open(pyright_json, encoding="utf-8-sig") as f:
        data = json.load(f)

    diagnostics = data.get("generalDiagnostics", [])
```

**Depois**:
```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict


# -----------------------------------------------------------------------------
# Pyright JSON structure types
# -----------------------------------------------------------------------------
class PyrightRangePos(TypedDict, total=False):
    """Position in a text file (line, character)."""

    line: int
    character: int


class PyrightRange(TypedDict, total=False):
    """Range in a text file (start, end positions)."""

    start: PyrightRangePos
    end: PyrightRangePos


class PyrightDiagnostic(TypedDict, total=False):
    """Pyright diagnostic entry from generalDiagnostics array."""

    file: str
    message: str
    severity: str
    rule: str
    range: PyrightRange


class PyrightReport(TypedDict, total=False):
    """Top-level Pyright JSON report structure."""

    generalDiagnostics: list[PyrightDiagnostic]
    summary: dict[str, Any]


def load_pyright_report(path: Path) -> PyrightReport | None:
    """Load Pyright JSON report from file."""
    if not path.exists():
        print(f"❌ {path} not found. Run pyright first.")
        return None

    with open(path, encoding="utf-8-sig") as f:
        data: PyrightReport = json.load(f)
    return data


def main() -> None:
    """Filter and display Supabase-related Pyright errors."""
    qa_dir: Path = Path(__file__).parent
    pyright_json: Path = qa_dir / "pyright.json"

    report: PyrightReport | None = load_pyright_report(pyright_json)
    if report is None:
        return

    diagnostics: list[PyrightDiagnostic] = report.get("generalDiagnostics", [])
```

**Mudanças**:
1. ✅ `PyrightRangePos` TypedDict para `{line: int, character: int}`
2. ✅ `PyrightRange` TypedDict para `{start: ..., end: ...}`
3. ✅ `PyrightDiagnostic` TypedDict para entradas de diagnóstico
4. ✅ `PyrightReport` TypedDict para estrutura raiz do JSON
5. ✅ `total=False` permite campos opcionais
6. ✅ Função `load_pyright_report()` com retorno tipado
7. ✅ Todas variáveis locais anotadas: `qa_dir: Path`, `diagnostics: list[PyrightDiagnostic]`

**Impacto**: Elimina "Type is unknown/partially unknown" em `data`, `diagnostics`

---

### 2. Helper functions com type annotations

**Antes**:
```python
def main() -> None:
    # Filter for Supabase-related files
    supabase_keywords = ["supabase_repo", "supabase_client", "supabase_auth"]
    supabase_errors = [
        d for d in diagnostics
        if any(kw in d.get("file", "").lower() for kw in supabase_keywords)
    ]

    # Also filter return type errors across all files
    return_type_errors = [
        d for d in diagnostics
        if any(pattern in d.get("message", "").lower() for pattern in [
            "return type",
            "declared return type",
            "inferred return type",
        ])
    ]
```

**Depois**:
```python
def filter_supabase_errors(diagnostics: list[PyrightDiagnostic]) -> list[PyrightDiagnostic]:
    """Filter diagnostics for Supabase-related files."""
    supabase_keywords: list[str] = ["supabase_repo", "supabase_client", "supabase_auth"]
    return [
        d for d in diagnostics
        if any(kw in d.get("file", "").lower() for kw in supabase_keywords)
    ]


def filter_return_type_errors(diagnostics: list[PyrightDiagnostic]) -> list[PyrightDiagnostic]:
    """Filter diagnostics for return type related errors."""
    return_patterns: list[str] = [
        "return type",
        "declared return type",
        "inferred return type",
    ]
    return [
        d for d in diagnostics
        if any(pattern in d.get("message", "").lower() for pattern in return_patterns)
    ]


def main() -> None:
    ...
    diagnostics: list[PyrightDiagnostic] = report.get("generalDiagnostics", [])
    supabase_errors: list[PyrightDiagnostic] = filter_supabase_errors(diagnostics)
    return_type_errors: list[PyrightDiagnostic] = filter_return_type_errors(diagnostics)
```

**Mudanças**:
1. ✅ Extrair lógica de filtro para funções helper
2. ✅ Type hints explícitos: `list[PyrightDiagnostic]` em parâmetros e retornos
3. ✅ Anotações locais: `supabase_keywords: list[str]`, `return_patterns: list[str]`
4. ✅ Docstrings para todas funções helper

**Impacto**: Elimina "Argument type is partially unknown" em comprehensions

---

### 3. Loop variables com type annotations

**Antes**:
```python
# Group by file
by_file: dict[str, list[dict]] = {}  # ❌ dict[Unknown, Unknown]
for err in supabase_errors:
    file_path = err.get("file", "unknown")
    by_file.setdefault(file_path, []).append(err)

for idx, (file_path, errors) in enumerate(sorted(by_file.items()), 1):
    print(f"\n{idx}. {file_path} ({len(errors)} errors)")
    print("-" * 80)

    # Show first 15 errors per file
    for err in errors[:15]:
        line = err.get("range", {}).get("start", {}).get("line", 0) + 1  # ❌ line: Unknown
        msg = err.get("message", "")  # ❌ msg: Unknown
        if len(msg) > 100:
            msg = msg[:97] + "..."
        print(f"   Line {line:4d}: {msg}")
```

**Depois**:
```python
# Group by file
by_file: dict[str, list[PyrightDiagnostic]] = {}  # ✅ Tipado explicitamente
for err in supabase_errors:
    file_path: str = err.get("file", "unknown")
    file_errors: list[PyrightDiagnostic] = by_file.setdefault(file_path, [])
    file_errors.append(err)

# Extracted to helper function for better type safety
def print_grouped_errors(errors_by_file: dict[str, list[PyrightDiagnostic]]) -> None:
    """Print errors grouped by file."""
    for idx, (file_path, file_errors) in enumerate(sorted(errors_by_file.items()), 1):
        error_count: int = len(file_errors)
        print(f"\n{idx}. {file_path} ({error_count} errors)")
        print("-" * 80)

        max_display: int = 15
        for err in file_errors[:max_display]:
            line_num: int = get_line_number(err)  # ✅ Helper function
            msg: str = err.get("message", "")
            if len(msg) > 100:
                msg = msg[:97] + "..."
            print(f"   Line {line_num:4d}: {msg}")

        remaining: int = error_count - max_display
        if remaining > 0:
            print(f"   ... and {remaining} more errors")


def get_line_number(diagnostic: PyrightDiagnostic) -> int:
    """Extract line number from diagnostic (1-indexed for display)."""
    range_data: PyrightRange | None = diagnostic.get("range")
    if range_data:
        start_pos: PyrightRangePos | None = range_data.get("start")
        if start_pos:
            line_zero_indexed: int | None = start_pos.get("line")
            if line_zero_indexed is not None:
                return line_zero_indexed + 1
    return 0
```

**Mudanças**:
1. ✅ `by_file: dict[str, list[PyrightDiagnostic]]` com tipo completo
2. ✅ Todas variáveis loop anotadas: `file_path: str`, `error_count: int`, `msg: str`
3. ✅ Extrair navegação nested dict para `get_line_number()` helper
4. ✅ Helper `print_grouped_errors()` com signature tipada
5. ✅ Uso de `setdefault` com variável intermediária para evitar chaining
6. ✅ Anotações de None: `range_data: PyrightRange | None`

**Impacto**: Elimina todos "Type of X is unknown/partially unknown" em loops

---

### 4. Priority errors printing

**Antes**:
```python
print(f"\n🎯 High-priority type errors: {len(priority_errors)}")
for idx, err in enumerate(priority_errors[:20], 1):
    file_path = Path(err.get("file", "")).name  # ❌ err: dict[Unknown, Unknown]
    line = err.get("range", {}).get("start", {}).get("line", 0) + 1  # ❌ line: Unknown
    msg = err.get("message", "")  # ❌ msg: Unknown
    if len(msg) > 80:
        msg = msg[:77] + "..."
    print(f"{idx:2d}. {file_path}:{line:4d} | {msg}")
```

**Depois**:
```python
def print_priority_errors(priority_errors: list[PyrightDiagnostic]) -> None:
    """Print high-priority errors in compact format."""
    max_display: int = 20
    for idx, err in enumerate(priority_errors[:max_display], 1):
        file_name: str = Path(err.get("file", "")).name
        line_num: int = get_line_number(err)  # ✅ Reusa helper
        msg: str = err.get("message", "")
        if len(msg) > 80:
            msg = msg[:77] + "..."
        print(f"{idx:2d}. {file_name}:{line_num:4d} | {msg}")

    remaining: int = len(priority_errors) - max_display
    if remaining > 0:
        print(f"    ... and {remaining} more priority errors")


def main() -> None:
    ...
    print(f"\n🎯 High-priority type errors: {len(priority_errors)}")
    print_priority_errors(priority_errors)
```

**Mudanças**:
1. ✅ Extrair loop para `print_priority_errors()` helper
2. ✅ Parâmetro tipado: `priority_errors: list[PyrightDiagnostic]`
3. ✅ Todas variáveis anotadas: `file_name: str`, `line_num: int`, `msg: str`
4. ✅ Reuso de `get_line_number()` helper
5. ✅ Cálculo `remaining` explicitamente tipado

**Impacto**: Elimina warnings finais em priority error loop

---

## 📊 Tabela de Correções

| Local/Variável             | Problema Pyright Original                                   | Correção Aplicada                                     |
|----------------------------|-------------------------------------------------------------|-------------------------------------------------------|
| `data` (JSON load)         | Type of "data" is unknown                                   | `data: PyrightReport = json.load(f)`                  |
| `diagnostics`              | Type is "list[Unknown]"                                     | `diagnostics: list[PyrightDiagnostic]`                |
| `by_file`                  | `dict[str, list[dict[Unknown, Unknown]]]`                   | `dict[str, list[PyrightDiagnostic]]`                  |
| `by_file.setdefault`       | Type of "setdefault" is partially unknown                   | Variável intermediária + anotação                     |
| `by_file.append`           | Type of "append" is partially unknown                       | `file_errors: list[PyrightDiagnostic]` explícito      |
| `errors` (loop var)        | Type is `list[dict[Unknown, Unknown]]`                      | Função `print_grouped_errors()` tipada                |
| `for err in errors`        | Type of "err" is `dict[Unknown, Unknown]`                   | Loop em `file_errors: list[PyrightDiagnostic]`        |
| `line` (nested .get)       | Type is unknown                                             | Helper `get_line_number()` com return `int`           |
| `msg` (from err)           | Type is unknown                                             | `msg: str = err.get("message", "")`                   |
| `sorted(by_file.items())`  | Argument type is partially unknown                          | `dict[str, list[PyrightDiagnostic]]` upstream         |
| `len(errors)`              | Argument type is partially unknown                          | Type annotations propagam até len()                   |
| `priority_errors` loop     | All vars unknown                                            | Função `print_priority_errors()` + anotações          |

**Total**: **18 warnings eliminados** (6 UnknownVariableType + 5 UnknownMemberType + 7 UnknownArgumentType)

---

## 🏗️ Arquitetura do Script

### Funções Helper Criadas

| Função                     | Signature                                                                     | Propósito                                    |
|----------------------------|-------------------------------------------------------------------------------|----------------------------------------------|
| `load_pyright_report`      | `(path: Path) -> PyrightReport \| None`                                      | Carregar JSON com tipo seguro                |
| `filter_supabase_errors`   | `(diagnostics: list[PyrightDiagnostic]) -> list[PyrightDiagnostic]`          | Filtrar erros Supabase                       |
| `filter_return_type_errors`| `(diagnostics: list[PyrightDiagnostic]) -> list[PyrightDiagnostic]`          | Filtrar erros de return type                 |
| `get_line_number`          | `(diagnostic: PyrightDiagnostic) -> int`                                      | Extrair linha de diagnóstico (safe)          |
| `print_grouped_errors`     | `(errors_by_file: dict[str, list[PyrightDiagnostic]]) -> None`               | Imprimir erros agrupados por arquivo         |
| `print_priority_errors`    | `(priority_errors: list[PyrightDiagnostic]) -> None`                          | Imprimir erros prioritários compacto         |

### TypedDict Hierarchy

```
PyrightReport
├── generalDiagnostics: list[PyrightDiagnostic]
│   ├── file: str
│   ├── message: str
│   ├── severity: str
│   ├── rule: str
│   └── range: PyrightRange
│       ├── start: PyrightRangePos
│       │   ├── line: int
│       │   └── character: int
│       └── end: PyrightRangePos
│           ├── line: int
│           └── character: int
└── summary: dict[str, Any]
```

---

## ✅ Validação

### Testes Executados

1. **Script execution**: `python devtools/qa/analyze_supabase_errors.py` → ✅ Saída idêntica

2. **Pyright analysis**: `pyright devtools/qa/analyze_supabase_errors.py` → **18 warnings → 0 warnings** ✅

3. **Output comparison**:
   ```
   📊 Total Pyright errors: 2827
   🔍 Supabase-related errors: 9
   📤 Return type errors (all files): 127
   ```
   Idêntico ao output anterior

### Resultado

- ✅ **18 warnings Pyright eliminados** (100%)
- ✅ **0 regressões** (script funciona identicamente)
- ✅ **Type safety completo** em devtool
- ✅ **Código mais legível** (funções helper extraídas)
- ✅ **Documentação inline** (docstrings em todas funções)

---

## 🔄 Arquivos Modificados

| Arquivo                                      | Linhas Δ | Tipo       | Descrição                                          |
|----------------------------------------------|----------|------------|----------------------------------------------------|
| `devtools/qa/analyze_supabase_errors.py`     | +86      | Modificado | TypedDicts + helper functions + type annotations   |

**Total**: 1 arquivo modificado (+86 linhas, de 114 para 200 linhas com helpers/docs)

---

## 📝 Lições Aprendidas

### ✅ Acertos

1. **TypedDict com total=False**: Permite campos opcionais do JSON sem over-engineering
2. **Helper functions**: Extrair nested dict navigation para funções tipadas elimina warnings
3. **Intermediate variables**: `file_errors = by_file.setdefault(...)` em vez de chain direto
4. **Explicit annotations**: Todas variáveis loop anotadas previne type inference issues
5. **Docstrings**: Documentar helpers melhora legibilidade

### ⚠️ Desafios

1. **Nested dict access**: `err.get("range", {}).get("start", {}).get("line")` requer helper
2. **TypedDict total=False**: Requer `| None` em todos gets
3. **List comprehensions**: Pyright pode inferir mal, requer tipo explícito no resultado

### 🎯 Estratégias de Type Hints em DevTools

| Pattern                          | Solution                                         | Benefit                                  |
|----------------------------------|--------------------------------------------------|------------------------------------------|
| JSON load sem tipo               | `data: PyrightReport = json.load(f)`             | Type checker conhece estrutura           |
| Nested dict navigation           | Helper function `get_line_number()`              | Evita chaining não tipado                |
| Loop over dict items             | Type annotation upstream: `dict[str, list[T]]`   | Inference propaga para loop vars         |
| List comprehension               | Anotar resultado: `x: list[T] = [... for ...]`  | Previne inference parcial                |
| setdefault + append              | Variável intermediária tipada                    | Evita "partially unknown member type"    |
| Helper functions                 | Sempre com signature completa                    | Self-documenting + type safe             |

---

## 🚫 Não Aplicável

Este CompatPack afetou **apenas devtools**, não há código de produção modificado.

---

## 🔗 Contexto

- **CompatPack-01**: Mapeamento dos 112 erros Pyright (análise sem code changes)
- **CompatPack-02**: ttkbootstrap stubs (-16 erros, 113 → 97)
- **CompatPack-03**: PathLikeStr type alias (-2 erros, 97 → 95)
- **CompatPack-04**: TypeGuard para Unknown/Any (-10 erros Unknown, 19 → 9)
- **CompatPack-05**: Clean typing_helpers.py warnings (-3 warnings)
- **CompatPack-06**: Unknown em UI/forms/actions/hub (-7 erros, 95 → 88)
- **CompatPack-07**: Config/settings & simple returns (-43 erros, 2893 → 2850)
- **CompatPack-08**: Supabase repo return types (-23 erros, 2850 → 2827)
- **CompatPack-09**: Type-safe analyze_supabase_errors devtool (-18 warnings em devtools) ← **YOU ARE HERE**

---

## 🚀 Próximos Passos

Possíveis alvos para CompatPack-10:

1. **Limpar outros scripts devtools**:
   - `devtools/qa/analyze_pyright_errors.py`
   - `devtools/qa/analyze_config_errors.py`
   - `devtools/qa/analyze_path_errors.py`
   - Aplicar mesma estratégia TypedDict

2. **Criar stubs para postgrest** (`typings/postgrest/`):
   - APIResponse TypedDict
   - QueryBuilder type hints
   - Reduzir "Type of exec_postgrest is partially unknown"

3. **Atacar infra/supabase/db_client.py**:
   - Type hints em `_health_check_once()`
   - Type hints em `get_supabase()` → `Client`

4. **Type hints em services layer**:
   - src/core/services/*.py
   - Funções que usam supabase_repo

5. **Expandir TypedDicts de domínio**:
   - `ClientRow` detalhado (id, org_id, razao_social, ...)
   - `PasswordRow` detalhado (id, org_id, client_name, ...)

---

**Commit Message**:
```
CompatPack-09: type-safe analyze_supabase_errors devtool

- Introduce PyrightDiagnostic/PyrightRange/PyrightRangePos TypedDicts
- Annotate all collections: dict[str, list[PyrightDiagnostic]] instead of dict[str, list[dict]]
- Extract helper functions: load_pyright_report, filter_supabase_errors, get_line_number, print_grouped_errors
- Ensure all loop variables have explicit type annotations
- Add comprehensive docstrings to all helper functions
- Remove 100% of Pyright/Pylance warnings: 18 -> 0 (-18, -100%)
- Keep devtool behavior identical (same printed summary)
- Improve code readability with extracted helper functions
```
