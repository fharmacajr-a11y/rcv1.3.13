# 00b - Correção do Baseline

> **Data:** 2025-01-02  
> **Fase:** 0.1 - Correção de Baseline  
> **Status:** ✅ Concluído

---

## 🎯 Objetivo

Corrigir as contagens subestimadas do baseline original, que usava métodos imprecisos (regex PowerShell) que não capturavam todos os imports reais do projeto.

---

## ❌ Problemas do Baseline Anterior

### 1. Método de Contagem de Imports

| Problema | Impacto |
|----------|---------|
| Regex `^import` / `^from` não pega imports indentados | Perdeu ~90% dos imports (lazy imports dentro de funções) |
| PowerShell `Select-String` com escopo limitado | Não recursou corretamente em todos os subdiretórios |
| Não parseava AST | Contava comentários e docstrings como imports |
| Falta de normalização de paths | Duplicatas e caminhos inconsistentes |

### 2. Método de Contagem de Linhas

| Problema | Impacto |
|----------|---------|
| `(Get-Content).Lines` com encoding default | Arquivos UTF-8 com BOM causavam erro de contagem |
| Não ignorava corretamente `__pycache__` | Incluía arquivos .pyc compilados |
| Top 20 insuficiente | Vários arquivos >500 linhas ficaram de fora |

---

## ✅ Nova Metodologia

### Para Contagem de Imports

```python
# Script determinístico usando Python AST
import ast
from pathlib import Path

def count_imports(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        tree = ast.parse(f.read())

    count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            count += 1  # Conta APENAS statements reais de import
    return count
```

**Vantagens:**
- Captura imports em qualquer nível de indentação (lazy imports)
- Ignora comentários e docstrings
- Preciso e reprodutível
- Fornece número da linha para cada import

### Para Contagem de Linhas

```python
# Contagem simples e precisa
with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    lines = len(f.read().splitlines())
```

**Escopo de diretórios:**
- `src/`, `infra/`, `data/`, `adapters/`, `security/`, `tests/`

**Ignorados:**
- `.venv/`, `__pycache__/`, `dist/`, `build/`, `.git/`, `htmlcov/`, `third_party/`

---

## 📊 Resultados: Antes vs Depois

### Contagem de Imports por Prefixo

| Padrão | Antes (PowerShell) | Depois (AST) | Delta |
|--------|-------------------|--------------|-------|
| `infra` | 36 | **312** | +276 (+767%) |
| `data` | 12 | **47** | +35 (+292%) |
| `adapters` | 4 | **30** | +26 (+650%) |
| `security` | 0 | **6** | +6 (novo) |
| `src.helpers` | 4 | **36** | +32 (+800%) |
| `src.shared` | 3 | **7** | +4 (+133%) |
| `src.utils` | 29 | **211** | +182 (+628%) |
| `src.modules` | 13 | **1325** | +1312 (+10092%) |
| `src.features` | 0 | **59** | +59 (novo) |
| **TOTAL estimado** | ~100 | **~2033** | **+1933 (+1933%)** |

### Contagem de Arquivos Grandes

| Métrica | Antes | Depois |
|---------|-------|--------|
| Top 20 máximo | 891 linhas | **1056 linhas** |
| Arquivos > 500 linhas | 14 | **30** |
| Arquivos analisados | ~200 | **497** |

---

## 🔍 Evidência de Execução

### Script de Coleta (executado em 2025-01-02)

```
================================================================================
RESUMO DE IMPORTS POR PREFIXO (via AST)
================================================================================
Total de arquivos .py analisados: 1001
Total de statements de import: 6260

### infra: 312 imports
------------------------------------------------------------
  1. src\app_status.py:13 -> from infra.net_status import Status, probe
  2. src\core\auth_bootstrap.py:14 -> from infra.supabase_client import ...
  3. src\core\status_monitor.py:11 -> from infra.net_status import Status, probe
  ... (mais 309 imports)

### data: 47 imports
### adapters: 30 imports
### security: 6 imports
### src.helpers: 36 imports
### src.shared: 7 imports
### src.utils: 211 imports
### src.modules: 1325 imports
### src.features: 59 imports
```

---

## 📋 Impacto na Refatoração

### Antes (estimativa errada)
- ~100 imports para atualizar
- Parecia uma tarefa simples

### Depois (realidade)
- **~2033 imports** para atualizar
- Requer automação cuidadosa
- Cada fase deve ser atômica e validada

### Arquivos com Mais Imports a Atualizar

| Prefixo | Arquivos principais afetados |
|---------|------------------------------|
| `infra` | `src/core/`, `src/modules/hub/`, `src/modules/anvisa/` |
| `src.modules` | Quase todo o `src/` (imports entre módulos) |
| `src.utils` | Espalhado por todo o projeto |

---

## ✅ Ações Tomadas

1. ✅ Reexecutada coleta com Python AST
2. ✅ Atualizado `02_mapa_imports_baseline.md` com dados reais
3. ✅ Atualizado `04_lista_arquivos_grandes.md` com top 30
4. ✅ Atualizado `README.md` com fases atômicas e seguras

---

## 📎 Arquivos Relacionados

- [02_mapa_imports_baseline.md](02_mapa_imports_baseline.md) - Mapa atualizado
- [04_lista_arquivos_grandes.md](04_lista_arquivos_grandes.md) - Lista atualizada
- [README.md](README.md) - Roadmap com fases seguras
