# Microfase 23: Fonte Única de Verdade para CustomTkinter (Single Source of Truth)

**Data**: 2025-01-23  
**Status**: ✅ **Concluído**

---

## 🎯 Objetivo

Consolidar a política de CustomTkinter em **uma fonte única** para todo o aplicativo, eliminando duplicações de lógica `try/except import customtkinter` e `HAS_CUSTOMTKINTER` espalhadas por múltiplos arquivos.

**Decisão Arquitetural**: `src.ui.ctk_config` é a **única fonte de verdade** (Single Source of Truth - SSoT) para detecção e importação de CustomTkinter em todo o app.

---

## 📝 Contexto

Antes da Microfase 23, o app tinha múltiplas fontes de detecção de CustomTkinter:

1. **Microfase 22**: Módulo Uploads/Storage já usava `src.ui.ctk_config` ✅
2. **Módulo Clientes**: Tinha sua própria lógica em `appearance.py`
3. **Outros arquivos**: Cada arquivo tinha `try: import customtkinter` próprio

Isso causava:
- **Duplicação**: ~10 arquivos com lógica idêntica de detecção
- **Inconsistência**: Difícil garantir mesmo comportamento em todos os módulos
- **Manutenção difícil**: Alterar política exigia editar múltiplos arquivos
- **Code smell**: Violação do princípio DRY (Don't Repeat Yourself)

---

## 🏗️ Alterações Realizadas

### 1. **Fonte Única Estabelecida**

**Arquivo**: [`src/ui/ctk_config.py`](../src/ui/ctk_config.py) (já existia desde Microfase 22)

```python
"""Configuração centralizada para CustomTkinter."""

from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    import customtkinter

# Política: CustomTkinter é dependência obrigatória
try:
    import customtkinter
    _has_ctk = True
    _ctk_module = customtkinter
except ImportError:
    _has_ctk = False
    _ctk_module = None  # type: ignore[assignment]

HAS_CUSTOMTKINTER: Final[bool] = _has_ctk
ctk: Any = _ctk_module
```

**Exports**:
- `HAS_CUSTOMTKINTER: Final[bool]` - Flag de disponibilidade (imutável)
- `ctk: Any` - Módulo customtkinter ou None

---

### 2. **Migração: appearance.py (Hub do Clientes)**

**Arquivo**: [`src/modules/clientes/appearance.py`](../src/modules/clientes/appearance.py)

**Antes** (linhas 16-26):
```python
# Fonte única de HAS_CUSTOMTKINTER para o módulo Clientes (Microfase 8)
_has_customtkinter = False
ctk = None  # type: ignore[assignment]

try:
    import customtkinter as ctk
    _has_customtkinter = True
except ImportError:
    pass

HAS_CUSTOMTKINTER: Final[bool] = _has_customtkinter
```

**Depois**:
```python
# CustomTkinter: fonte única centralizada (Microfase 23 - SSoT)
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
```

**Impacto**: `appearance.py` agora **reexporta** de `ctk_config` ao invés de ter lógica própria. Mantém retrocompatibilidade para arquivos que importam de `appearance`.

---

### 3. **Arquivos Migrados (11 arquivos)**

Todos os arquivos abaixo foram atualizados para importar de `src.ui.ctk_config`:

#### **Módulo Clientes - Views**
1. [`src/modules/clientes/views/actionbar_ctk.py`](../src/modules/clientes/views/actionbar_ctk.py)
   - **Antes**: `from ..appearance import HAS_CUSTOMTKINTER` + `if HAS_CUSTOMTKINTER: import customtkinter as ctk`
   - **Depois**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk`
   - **Linha removida**: Condicional de import (linhas 18-21)

2. [`src/modules/clientes/views/toolbar_ctk.py`](../src/modules/clientes/views/toolbar_ctk.py)
   - **Antes**: `from ..appearance import HAS_CUSTOMTKINTER` + `if HAS_CUSTOMTKINTER: import customtkinter as ctk`
   - **Depois**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk`
   - **Linha removida**: Condicional de import (linhas 17-20)

#### **Módulo Clientes - Forms**
3. [`src/modules/clientes/forms/client_form.py`](../src/modules/clientes/forms/client_form.py)
   - **Antes**: `try: import customtkinter as ctk; HAS_CUSTOMTKINTER = True`
   - **Depois**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk`
   - **Linhas removidas**: 6 linhas de try/except (linhas 42-49)

4. [`src/modules/clientes/forms/client_form_ui_builders_ctk.py`](../src/modules/clientes/forms/client_form_ui_builders_ctk.py)
   - **Antes**: `_has_customtkinter = False` + `try: import customtkinter as ctk`
   - **Depois**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk`
   - **Linhas removidas**: 11 linhas (linhas 17-27)

5. [`src/modules/clientes/forms/client_form_view_ctk.py`](../src/modules/clientes/forms/client_form_view_ctk.py)
   - **Antes**: `_has_customtkinter = False` + `try: import customtkinter as ctk`
   - **Depois**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk`
   - **Linhas removidas**: 11 linhas (linhas 17-27)

6. [`src/modules/clientes/forms/client_form_new.py`](../src/modules/clientes/forms/client_form_new.py)
   - **Antes**: `try: from src.modules.clientes.ui import ClientesModalCTK, HAS_CUSTOMTKINTER`
   - **Depois**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER` + import condicional de modal
   - **Linhas removidas**: 4 linhas de try/except (linhas 40-43)

7. [`src/modules/clientes/forms/client_form_controller.py`](../src/modules/clientes/forms/client_form_controller.py)
   - **Antes**: `try: from src.modules.clientes.ui import ClientesModalCTK, HAS_CUSTOMTKINTER`
   - **Depois**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER` + import condicional de modal
   - **Linhas removidas**: 4 linhas de try/except (linhas 30-33)

8. [`src/modules/clientes/forms/client_form_adapters.py`](../src/modules/clientes/forms/client_form_adapters.py)
   - **Antes**: `try: from src.modules.clientes.ui import ClientesModalCTK, HAS_CUSTOMTKINTER`
   - **Depois**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER` separado de import de modal
   - **Linhas removidas**: Referência duplicada de HAS_CUSTOMTKINTER (linha 21)

#### **Módulo Clientes - UI**
9. [`src/modules/clientes/ui/clientes_modal_ctk.py`](../src/modules/clientes/ui/clientes_modal_ctk.py)
   - **Antes**: `_has_customtkinter = False` + `try: import customtkinter as ctk`
   - **Depois**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk`
   - **Linhas removidas**: 11 linhas (linhas 17-27)

#### **Módulo Clientes - Main**
10. [`src/modules/clientes/view.py`](../src/modules/clientes/view.py)
    - **Antes**: `HAS_CUSTOMTKINTER = False` + `try: from src.modules.clientes.appearance import ... HAS_CUSTOMTKINTER`
    - **Depois**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk`
    - **Linhas removidas**: 8 linhas de lógica condicional (linhas 27-34)

#### **Módulo Uploads - Views** (já migrados na Microfase 22)
11. [`src/modules/uploads/views/browser.py`](../src/modules/uploads/views/browser.py) ✅
12. [`src/modules/uploads/views/action_bar.py`](../src/modules/uploads/views/action_bar.py) ✅
13. [`src/modules/uploads/views/file_list.py`](../src/modules/uploads/views/file_list.py) ✅

---

## 📊 Métricas de Impacto

| Métrica | Antes (Microfase 22) | Depois (Microfase 23) | Melhoria |
|---------|----------------------|------------------------|----------|
| **Arquivos com lógica CTk duplicada** | 11 (Clientes) + 1 (Uploads já ok) | 1 (ctk_config) | **-92%** |
| **Linhas de código de detecção CTk** | ~80 linhas | 10 linhas (ctk_config) | **-88%** |
| **Pontos de manutenção de política CTk** | 11 arquivos | 1 arquivo | **-91%** |
| **Imports de `try: import customtkinter`** | 11 locais | 1 local | **-91%** |
| **Fontes de verdade para HAS_CUSTOMTKINTER** | 11 fontes | **1 fonte (SSoT)** | ✅ **Consolidado** |

---

## ✅ Validação

### Testes Módulos Clientes + Uploads (111 testes)
```bash
python -m pytest -c pytest_cov.ini --no-cov -q tests/modules/clientes tests/modules/uploads -x
```

**Resultado**: ✅ **110 passed, 1 skipped in ~15s**

Testes cobertos:
- ✅ **Clientes**: Forms, views, controllers, repositories (69 testes)
- ✅ **Uploads**: Browser, action_bar, file_list, services (41 testes)
- ⏭️ **1 skip**: test_download_not_supported_os (platform-specific)

**Warnings**: Apenas deprecations do pyiceberg (biblioteca externa, não relacionado ao código do app)

---

## 🔍 Padrão Final Estabelecido

### ✅ **Como importar CustomTkinter no app**:
```python
# SEMPRE usar (fonte única):
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

# Se precisar type hints:
if TYPE_CHECKING:
    import customtkinter as ctk  # type: ignore[no-redef]
```

### ❌ **O que NÃO fazer mais**:
```python
# ❌ NÃO fazer detecção local:
try:
    import customtkinter as ctk
    HAS_CUSTOMTKINTER = True
except ImportError:
    HAS_CUSTOMTKINTER = False
    ctk = None

# ❌ NÃO importar de appearance.py (exceto ClientesThemeManager):
from src.modules.clientes.appearance import HAS_CUSTOMTKINTER  # ❌ EVITAR

# ❌ NÃO criar variáveis intermediárias:
_has_customtkinter = False  # ❌ Desnecessário agora
```

### ✅ **Exceção: ttk.Treeview/Scrollbar**
```python
# Continuar usando ttk para widgets sem equivalente CTk:
from tkinter import ttk

tree = ttk.Treeview(...)  # CTk não tem Treeview nativo
scrollbar = ttk.Scrollbar(...)  # Pode usar CTkScrollbar se preferir
```

---

## 🎓 Lições Aprendidas

1. **Single Source of Truth (SSoT)**: Um módulo central (`ctk_config.py`) simplifica manutenção e garante consistência
2. **Reexportar é OK**: `appearance.py` pode reexportar de `ctk_config` para manter retrocompatibilidade
3. **Final[bool] importa**: Usar `Final[bool]` previne reassignment acidental de `HAS_CUSTOMTKINTER`
4. **Type hints resilientes**: `ctk: Any` evita erros de tipo quando CTk não está instalado
5. **Migração incremental**: Microfases 22 → 23 permitiram migração segura sem "big bang"

---

## 📚 Arquivos Modificados

### ✅ Módulo Central (1 arquivo)
- `src/ui/ctk_config.py` (já existia desde Microfase 22)

### ✅ Módulo Clientes (11 arquivos)
1. `src/modules/clientes/appearance.py` - Reexporta de ctk_config
2. `src/modules/clientes/view.py` - Import de ctk_config
3. `src/modules/clientes/views/actionbar_ctk.py` - Import de ctk_config
4. `src/modules/clientes/views/toolbar_ctk.py` - Import de ctk_config
5. `src/modules/clientes/forms/client_form.py` - Import de ctk_config
6. `src/modules/clientes/forms/client_form_ui_builders_ctk.py` - Import de ctk_config
7. `src/modules/clientes/forms/client_form_view_ctk.py` - Import de ctk_config
8. `src/modules/clientes/forms/client_form_new.py` - Import de ctk_config
9. `src/modules/clientes/forms/client_form_controller.py` - Import de ctk_config
10. `src/modules/clientes/forms/client_form_adapters.py` - Import de ctk_config
11. `src/modules/clientes/ui/clientes_modal_ctk.py` - Import de ctk_config

### ✅ Módulo Uploads (3 arquivos - já ok desde Microfase 22)
- `src/modules/uploads/views/browser.py` ✅
- `src/modules/uploads/views/action_bar.py` ✅
- `src/modules/uploads/views/file_list.py` ✅

**Total**: **11 arquivos modificados** + **~70 linhas removidas** (código duplicado eliminado)

---

## 🚀 Próximos Passos (Futuro)

1. **Outros módulos**: Aplicar mesma lógica em módulos ainda não migrados (se existirem)
2. **Tipagem melhorada**: Considerar substituir `ctk: Any` por Union type ou Protocol
3. **CI/CD**: Adicionar verificação no CI para prevenir novos `try: import customtkinter` fora de `ctk_config.py`
4. **Linter rule**: Criar regra do ruff/flake8 para alertar sobre imports locais de customtkinter
5. **Documentação técnica**: Adicionar regra no `CONTRIBUTING.md` sobre uso obrigatório de `ctk_config`

---

## 🏁 Conclusão

A **Microfase 23** consolidou a detecção de CustomTkinter em uma fonte única (`src.ui.ctk_config`), eliminando 11 duplicações de código e estabelecendo um padrão consistente para todo o app. Todos os testes passaram (110/111), confirmando que a refatoração não introduziu regressões.

**Política Final**:
- ✅ **SSoT**: `from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk`
- ✅ **Consolidação**: 92% de redução em pontos de detecção CTk
- ✅ **Manutenibilidade**: Alterar política CTk agora requer editar apenas 1 arquivo

---

## 🔧 Correções de Type Hints do Pylance

Após a migração, alguns erros de tipo do Pylance surgiram devido à mudança de fonte de importação. Foram corrigidos:

### 1. **client_form_view_ctk.py** (6 erros)

**Problema**: Pylance não reconhecia métodos de `CTkToplevel` devido ao tipo `Any` de `ctk`.

**Correções aplicadas** (linhas 148, 151, 153, 155, 156, 157, 524, 525, 527, 528):
```python
# Antes (Pylance reportava erros):
self.window.withdraw()
self.window.minsize(940, 520)
self.window.deiconify()

# Depois (com type hints adequados):
self.window.withdraw()  # type: ignore[union-attr]
self.window.minsize(940, 520)  # type: ignore[union-attr]
self.window.deiconify()  # type: ignore[union-attr]
```

**Justificativa**: Como `ctk` é tipado como `Any` em `ctk_config.py` (para permitir que seja `None` quando CTk não está instalado), o Pylance não consegue inferir os métodos de `CTkToplevel`. Adicionamos `# type: ignore[union-attr]` para suprimir warnings sem perder type safety em runtime.

### 2. **test_storage_ctk_smoke.py** (2 erros)

**Problema**: Import de `Tk` causava erro de símbolo desconhecido no Pylance.

**Correção aplicada** (linhas 6, 10, 19, 30):
```python
# Antes (erro: 'Tk' é símbolo de importação desconhecido):
from tkinter import Tk
root = Tk()
def make_browser_window(..., tk_root_session: Tk):

# Depois (import com alias padrão):
import tkinter as tk
root = tk.Tk()
def make_browser_window(..., tk_root_session: tk.Tk):
```

**Justificativa**: O Pylance tem melhor suporte para `import tkinter as tk` (padrão da comunidade Python) do que para `from tkinter import Tk`. Usar o alias `tk` resolve completamente o problema de reconhecimento.

### Resumo de Correções

| Arquivo | Erros Corrigidos | Solução |
|---------|------------------|---------|
| `client_form_view_ctk.py` | 6 erros | Adicionado `# type: ignore[union-attr]` em métodos de CTkToplevel |
| `test_storage_ctk_smoke.py` | 2 erros | Movido import `tkinter` para fora de `TYPE_CHECKING` |

**Total**: **8 erros do Pylance resolvidos** sem impactar comportamento em runtime.

---

## 🛡️ Enforcement (Microfase 23.1)

**Data**: 2025-01-16  
**Status**: ✅ **Implementado**

Para garantir que a política SSoT seja respeitada de forma permanente, implementamos enforcement automático via pre-commit e CI/CD.

### Arquivos Criados/Atualizados

1. **`.pre-commit-config.yaml`** (atualizado)
   - Adicionado hook `no-direct-customtkinter-import`
   - Language: `pygrep` (busca por regex em Python)
   - Detecta: `import customtkinter` e `from customtkinter import ...`
   - Whitelist: Apenas `src/ui/ctk_config.py` permitido

2. **`.github/workflows/pre-commit.yml`** (novo)
   - Roda pre-commit hooks em todos os pushes e PRs
   - Falha CI se violar política CustomTkinter
   - Upload de logs em caso de falha

3. **`docs/CTK_IMPORT_POLICY.md`** (novo)
   - Documentação completa da política
   - Exemplos de uso correto e incorreto
   - Guia de troubleshooting

4. **`scripts/validate_ctk_policy.py`** (novo)
   - Script Python para validação manual
   - Detecta violações antes de commitar
   - Relatório detalhado com linha e tipo de import

5. **`CONTRIBUTING.md`** (atualizado)
   - Adicionada seção "Política CustomTkinter (SSoT)"
   - Instruções de uso do pre-commit
   - Exemplos de correção

6. **`README.md`** (atualizado)
   - Link para documentação da política
   - Referência a guia de contribuição

### Hook Pre-commit

```yaml
- repo: local
  hooks:
    - id: no-direct-customtkinter-import
      name: Proibir import direto de customtkinter (usar src/ui/ctk_config.py)
      language: pygrep
      entry: '^\s*(import\s+customtkinter|from\s+customtkinter\s+import)'
      types: [python]
      exclude: ^src/ui/ctk_config\.py$
      description: |
        CustomTkinter deve ser importado apenas via src/ui/ctk_config.py (Single Source of Truth).
        Use: from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
```

### GitHub Actions Workflow

```yaml
name: Pre-commit Checks

on:
  push:
    branches: ['**']
  pull_request:
    branches: ['**']

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install pre-commit
      - uses: pre-commit/action@v3.0.1
        with:
          extra_args: --all-files --show-diff-on-failure
```

### Validação Manual

Você pode validar antes de commitar:

```powershell
# Rodar todos os hooks
pre-commit run --all-files

# Rodar apenas o hook CustomTkinter
pre-commit run no-direct-customtkinter-import --all-files

# Script Python customizado
python scripts/validate_ctk_policy.py
```

### Status Atual de Violações

**✅ Microfase 23.2 concluída** (2026-01-16): **0 violações restantes**

Todas as violações legadas foram corrigidas:
- **14 arquivos alterados**
- **15 ocorrências corrigidas**
- **110 testes passando** (1 skipped)
- **Pre-commit hook**: ✅ Passed
- **validate_ctk_policy.py**: ✅ 0 violações

<details>
<summary><strong>📜 Histórico de Violações (resolvidas)</strong></summary>

**Primeira validação** (2025-01-16): **15 violações encontradas**

Arquivos corrigidos na Microfase 23.2:
- `scripts/check_ctk_environment.py` (1)
- `tools/diagnose_clientes_env_and_coverage.py` (1)
- `tools/verify_app_clientes_coverage_env.py` (2)
- `tests/modules/test_clientes_apply_theme_no_crash.py` (1)
- `tests/modules/clientes/test_client_form_ctk_create_no_crash.py` (1)
- `tests/modules/uploads/test_storage_ctk_smoke.py` (1)
- `src/modules/clientes/_type_sanity.py` (1)
- `src/modules/uploads/views/action_bar.py` (1)
- `src/modules/clientes/forms/client_form_ui_builders_ctk.py` (1)
- `src/modules/clientes/forms/client_form_view_ctk.py` (1)
- `src/modules/clientes/ui/clientes_modal_ctk.py` (1)
- `src/modules/clientes/views/main_screen_ui_builder.py` (1)
- `scripts/visual/modal_ctk_clientes_visual.py` (1)
- `scripts/visual/theme_clientes_visual.py` (1)

</details>

### Comandos de Validação

```powershell
# 1. Instalar pre-commit (primeira vez)
pip install pre-commit
pre-commit install

# 2. Validar todos os arquivos
pre-commit run --all-files

# 3. Validar apenas política CTk
pre-commit run no-direct-customtkinter-import --all-files

# 4. Script Python customizado (mais detalhes)
python scripts/validate_ctk_policy.py

# 5. Forçar commit sem verificação (NÃO RECOMENDADO)
git commit --no-verify -m "message"
```

---

**Documentação gerada por**: GitHub Copilot + Engenharia de Software  
**Revisão técnica**: Aprovado por testes automatizados (110 testes verdes)  
**Relacionado**: [Microfase 22 - Uploads CTk Policy](CLIENTES_MICROFASE_22_UPLOADS_STORAGE_CTK_POLICY.md)
