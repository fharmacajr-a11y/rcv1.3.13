# Política CustomTkinter - Single Source of Truth (SSoT)

## 📖 Visão Geral

Este documento descreve a política obrigatória de importação de CustomTkinter no projeto RC Gestor de Clientes.

## 🎯 Regra Principal

**NUNCA importe `customtkinter` diretamente em nenhum arquivo do projeto, exceto `src/ui/ctk_config.py`.**

## ✅ Padrão Correto

```python
# Em qualquer módulo do projeto
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

# Uso condicional
if HAS_CUSTOMTKINTER:
    button = ctk.CTkButton(parent, text="Clique")
else:
    # Fallback (se necessário)
    button = ttk.Button(parent, text="Clique")

# Uso direto (quando CTk é obrigatório)
window = ctk.CTkToplevel()  # type: ignore[union-attr]
```

## ❌ Padrões Proibidos

```python
# ❌ Import direto - VAI FALHAR no pre-commit
import customtkinter

# ❌ Import from - VAI FALHAR no pre-commit
from customtkinter import CTkButton

# ❌ Import com alias - VAI FALHAR no pre-commit
import customtkinter as ctk

# ❌ Import condicional local - VAI FALHAR no pre-commit
try:
    import customtkinter
    HAS_CTK = True
except ImportError:
    HAS_CTK = False
```

## 🛡️ Enforcement (Como é garantido?)

### 1. Pre-commit Hook Local

Ao fazer commit, o hook `no-direct-customtkinter-import` verifica:

```yaml
- id: no-direct-customtkinter-import
  language: pygrep
  entry: '^\s*(import\s+customtkinter|from\s+customtkinter\s+import)'
  types: [python]
  exclude: ^src/ui/ctk_config\.py$
```

**Detecta:**
- `import customtkinter`
- `from customtkinter import ...`
- Variações com indentação (dentro de try/except, if, etc.)

**Permite:**
- Apenas `src/ui/ctk_config.py`

### 2. GitHub Actions CI/CD

Workflow `.github/workflows/pre-commit.yml` roda todos os hooks em:
- Pushes para qualquer branch
- Pull Requests

Se algum arquivo violar a política:
- ❌ CI falha
- ❌ PR não pode ser merged
- 📝 Diff completo é mostrado

### 3. Validação Manual

Você pode verificar antes de commitar:

```powershell
# Rodar todos os hooks
pre-commit run --all-files

# Rodar apenas o hook CustomTkinter
pre-commit run no-direct-customtkinter-import --all-files

# Verificar arquivos específicos
pre-commit run no-direct-customtkinter-import --files src/modules/clientes/view.py
```

## 🔧 Como Corrigir Violações

Se o hook falhar ao commitar:

### Passo 1: Identificar o arquivo
```
no-direct-customtkinter-import...............................Failed
- hook id: no-direct-customtkinter-import
- exit code: 1

src/modules/exemplo/view.py:15:import customtkinter
```

### Passo 2: Refatorar o import

**Antes:**
```python
import customtkinter

class MinhaView:
    def __init__(self):
        self.button = customtkinter.CTkButton(...)
```

**Depois:**
```python
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

class MinhaView:
    def __init__(self):
        if not HAS_CUSTOMTKINTER:
            raise RuntimeError("CustomTkinter não disponível")
        self.button = ctk.CTkButton(...)  # type: ignore[union-attr]
```

### Passo 3: Adicionar e commitar
```powershell
git add src/modules/exemplo/view.py
git commit -m "refactor: migrar para src.ui.ctk_config (SSoT)"
```

## 📂 Arquivo Whitelist

Único arquivo permitido para importar `customtkinter`:

- ✅ `src/ui/ctk_config.py`

**Conteúdo do arquivo:**
```python
"""Configuração central de CustomTkinter (Single Source of Truth)."""

from typing import Final

_has_ctk = False
_ctk_module = None

try:
    import customtkinter
    _has_ctk = True
    _ctk_module = customtkinter
except ImportError:
    pass

# Exports
HAS_CUSTOMTKINTER: Final[bool] = _has_ctk
ctk = _ctk_module  # type: Any
```

## 🤔 Por Que Esta Política?

### Problemas Sem SSoT
1. **Duplicação:** 20+ arquivos tinham `try: import customtkinter` idêntico
2. **Inconsistência:** Diferentes módulos com lógicas ligeiramente diferentes
3. **Manutenção:** Mudanças precisavam ser replicadas em múltiplos lugares
4. **Type Checking:** Pylance/Pyright reportavam erros inconsistentes

### Benefícios do SSoT
1. ✅ **Um lugar:** Toda lógica de detecção em `src/ui/ctk_config.py`
2. ✅ **Consistência:** Todos os módulos usam o mesmo HAS_CUSTOMTKINTER
3. ✅ **Manutenção:** Mudanças em um único arquivo
4. ✅ **Type Hints:** Centralizado, fácil de adicionar type ignores
5. ✅ **Testing:** Fácil mock de `HAS_CUSTOMTKINTER` em testes

## 📚 Referências

- [Microfase 23 - Consolidação SSoT](../docs/MICROFASE_23_CTK_SINGLE_SOURCE_OF_TRUTH.md)
- [CONTRIBUTING.md - Política CustomTkinter](../CONTRIBUTING.md#-política-customtkinter-single-source-of-truth)
- [Pre-commit Config](../.pre-commit-config.yaml)

## 🆘 Suporte

Se encontrar problemas ou casos edge:

1. Verifique se está usando `from src.ui.ctk_config import ...`
2. Rode `pre-commit run --all-files` para validar
3. Consulte documentação da Microfase 23
4. Abra issue explicando o caso específico

---

**Última atualização:** 16 de janeiro de 2026  
**Implementado em:** Microfase 23 (v1.5.42)
