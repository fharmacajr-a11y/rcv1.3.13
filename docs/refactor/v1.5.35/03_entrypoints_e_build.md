# 03 - Entrypoints e Build

> **Versão de referência:** v1.5.35  
> **Data:** 2025-01-02

Este documento identifica os pontos de entrada do aplicativo e a configuração de build.

---

## 🚀 Entrypoints Identificados

### 1. `main.py` (Raiz)

**Caminho:** `main.py`  
**Tipo:** Script de entrada principal

```python
# -*- coding: utf-8 -*-
"""Entry point script for the application."""

if __name__ == "__main__":
    import runpy

    runpy.run_module("src.app_gui", run_name="__main__")
```

**Análise:**
- Usa `runpy.run_module` para executar `src.app_gui`
- Simples e delega para o módulo real
- Não será afetado diretamente pela refatoração

---

### 2. `src/app_gui.py` (Entrypoint Real)

**Caminho:** `src/app_gui.py`  
**Tipo:** Módulo GUI principal

Este é o **verdadeiro ponto de entrada** do aplicativo. O `main.py` apenas o invoca.

**Dependências típicas:**
- Importa de `src.core`
- Importa de `src.modules`
- Importa de `infra` (via `sitecustomize.py`)

---

### 3. `src/app_core.py`

**Caminho:** `src/app_core.py`  
**Tipo:** Core do aplicativo (lógica central)

Contém a lógica central de inicialização e configuração.

---

### 4. Outros arquivos app_*

| Arquivo | Descrição |
|---------|-----------|
| `src/app_status.py` | Gerenciamento de status |
| `src/app_utils.py` | Utilitários do app |
| `src/modules/main_window/app_actions.py` | Ações da janela principal |

---

## 📦 Configuração PyInstaller

### Arquivo: `rcgestor.spec`

**Localização:** Raiz do projeto

#### Trecho Principal (linhas 1-60):

```python
# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# RC Gestor de Clientes - PyInstaller Spec File
# =============================================================================
# Arquivo de configuração para geração do executável Windows.
#
# Uso:
#   pyinstaller rcgestor.spec
#
# Saída:
#   dist/RC-Gestor-Clientes-{versão}.exe
#
# Revisado na FASE 4 (2025-12-02) - Documentação e organização do build.
# =============================================================================

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

# =============================================================================
# CAMINHOS BASE
# =============================================================================
BASE = Path(SPECPATH).resolve()  # usar pasta do .spec (estavel)
SRC = BASE / "src"
sys.path.insert(0, str(SRC))

# Importa versão do app para nomear o executável
from src.version import get_version  # noqa: E402

APP_VERSION = get_version()

# =============================================================================
# ARQUIVOS DE DADOS (datas)
# =============================================================================
datas = []

def add_file(src: Path, dest: str = ".") -> None:
    """Adiciona arquivo aos datas se existir."""
    if src.exists():
        datas.append((str(src), dest))

# Arquivos opcionais da raiz do projeto
add_file(BASE / "rc.ico", ".")
# SEGURANÇA: .env NÃO deve ser empacotado
add_file(BASE / "CHANGELOG.md", ".")
add_file(BASE / "CHANGELOG_CONSOLIDADO.md", ".")

# Dados de pacotes Python (site-packages)
datas += collect_data_files("ttkbootstrap")
datas += collect_data_files("tzdata")
```

#### Pontos Importantes:

1. **Path manipulation:** O spec adiciona `src/` ao `sys.path`
2. **Importa `src.version`** para nomear o executável
3. **Coleta dados** de ttkbootstrap e tzdata
4. **Usa `BASE`** como referência para caminhos

---

## ⚠️ sitecustomize.py (CRÍTICO)

### Conteúdo Completo:

```python
"""Project-level sitecustomize to expose src-style packages on sys.path."""

import os
import sys
import warnings

_ROOT = os.path.dirname(os.path.abspath(__file__))
for rel_path in ("src", "infra", "adapters"):
    abs_path = os.path.join(_ROOT, rel_path)
    if os.path.isdir(abs_path) and abs_path not in sys.path:
        sys.path.insert(0, abs_path)

# PyMuPDF (fitz) dispara um DeprecationWarning envolvendo swigvarlink
# Silenciamos no processo inteiro para evitar ruído
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r"builtin type swigvarlink has no __module__ attribute",
)
```

### Análise:

**O que faz:**
1. Adiciona `src/`, `infra/`, `adapters/` ao `sys.path`
2. Silencia warning do PyMuPDF

**Impacto na refatoração:**
- **Após mover `infra/` → `src/infra/`:** Remover `"infra"` da lista
- **Após mover `adapters/` → `src/adapters/`:** Remover `"adapters"` da lista
- **Objetivo final:** Manter apenas `"src"` na lista (ou remover o arquivo)

**Nota:** `data/` e `security/` NÃO estão na lista do `sitecustomize.py`.  
Isso significa que imports de `data` e `security` podem estar sendo resolvidos de outra forma (talvez pelo PYTHONPATH ou pelo próprio layout).

---

## 📋 Resumo dos Impactos no Build

| Componente | Impacto | Ação Necessária |
|------------|---------|-----------------|
| `main.py` | Nenhum | Nenhuma |
| `src/app_gui.py` | Imports mudarão | Atualizar imports |
| `rcgestor.spec` | Paths podem mudar | Revisar coleta de dados |
| `sitecustomize.py` | Lista de paths | Remover `infra`, `adapters` |

---

## 🔗 Arquivos Relacionados

- `pyproject.toml` - Configuração do projeto Python
- `pyrightconfig.json` - Configuração do Pyright (type checker)
- `ruff.toml` - Configuração do Ruff (linter)
