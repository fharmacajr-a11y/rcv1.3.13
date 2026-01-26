# Guia Rápido: Validar Política CustomTkinter

## ✅ Instalação (Primeira Vez)

```powershell
# 1. Instalar pre-commit
pip install pre-commit

# 2. Instalar hooks no repositório
pre-commit install

# 3. Rodar pela primeira vez (vai instalar hooks)
pre-commit run --all-files
```

## 🔍 Comandos de Validação

### Validar Todos os Hooks

```powershell
pre-commit run --all-files
```

Roda todos os hooks configurados (ruff, yaml, trailing whitespace, CTk policy, etc.).

### Validar Apenas Política CustomTkinter

```powershell
pre-commit run no-direct-customtkinter-import --all-files
```

Verifica apenas imports diretos de `customtkinter`.

### Validar Arquivo Específico

```powershell
pre-commit run no-direct-customtkinter-import --files src/modules/exemplo/view.py
```

### Script Python Customizado (Mais Detalhado)

```powershell
python scripts/validate_ctk_policy.py
```

**Vantagens**:
- Mostra linha exata da violação
- Tipo de import (import vs from)
- Relatório formatado e colorido
- Guia de correção

## 🔧 Corrigindo Violações

### Exemplo 1: Import Direto

**Antes (❌ VIOLA POLÍTICA):**
```python
import customtkinter

class MyView:
    def __init__(self):
        self.button = customtkinter.CTkButton(...)
```

**Depois (✅ CORRETO):**
```python
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

class MyView:
    def __init__(self):
        if not HAS_CUSTOMTKINTER:
            raise RuntimeError("CustomTkinter não disponível")
        self.button = ctk.CTkButton(...)  # type: ignore[union-attr]
```

### Exemplo 2: Import From

**Antes (❌ VIOLA POLÍTICA):**
```python
from customtkinter import CTkButton, CTkFrame

class ActionBar(CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.btn = CTkButton(self, text="OK")
```

**Depois (✅ CORRETO):**
```python
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

class ActionBar(ctk.CTkFrame):  # type: ignore[misc]
    def __init__(self, parent):
        super().__init__(parent)
        self.btn = ctk.CTkButton(self, text="OK")  # type: ignore[union-attr]
```

### Exemplo 3: Import Condicional (Try/Except)

**Antes (❌ VIOLA POLÍTICA):**
```python
_has_ctk = False
try:
    import customtkinter
    _has_ctk = True
except ImportError:
    pass

HAS_CUSTOMTKINTER = _has_ctk
```

**Depois (✅ CORRETO):**
```python
from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk

# Usar diretamente HAS_CUSTOMTKINTER e ctk
# Não precisa de lógica local!
```

## 🚨 O Que Fazer Quando Hook Falha no Commit

```
no-direct-customtkinter-import...............................Failed
- hook id: no-direct-customtkinter-import
- exit code: 1

src/modules/exemplo/view.py:15:import customtkinter
```

**Passo a passo:**

1. **Identifique o arquivo**: `src/modules/exemplo/view.py` linha 15
2. **Abra o arquivo** e localize o import
3. **Substitua** conforme exemplos acima
4. **Adicione novamente**: `git add src/modules/exemplo/view.py`
5. **Commite**: `git commit -m "refactor: migrar para src.ui.ctk_config"`

## 🔄 Atualizar Hooks

Se o `.pre-commit-config.yaml` mudar:

```powershell
pre-commit autoupdate
pre-commit run --all-files
```

## 🚫 Bypass (NÃO RECOMENDADO)

```powershell
# Pular pre-commit (use apenas se tiver certeza absoluta)
git commit --no-verify -m "docs: atualizar README"
```

**⚠️ Aviso**: Mesmo pulando localmente, a CI no GitHub vai falhar!

## 📊 Status Atual do Repositório

Para ver quantas violações existem:

```powershell
python scripts/validate_ctk_policy.py
```

Exemplo de saída:

```
🔍 Validando política CustomTkinter (SSoT)...

❌ 15 violação(ões) encontrada(s):

  📄 src/modules/uploads/views/action_bar.py:11
     from customtkinter import CTkButton, CTkFrame
     Tipo: from

🔧 Como corrigir:
   1. Substitua imports diretos por:
      from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk
   2. Use 'ctk.CTkButton' ao invés de 'customtkinter.CTkButton'
   3. Rode: pre-commit run no-direct-customtkinter-import --all-files
```

## 📚 Documentação Completa

- [Política CustomTkinter (SSoT)](CTK_IMPORT_POLICY.md)
- [Microfase 23 - Single Source of Truth](MICROFASE_23_CTK_SINGLE_SOURCE_OF_TRUTH.md)
- [CONTRIBUTING.md - Política CustomTkinter](../CONTRIBUTING.md#-política-customtkinter-single-source-of-truth)

---

**TL;DR**: Use sempre `from src.ui.ctk_config import HAS_CUSTOMTKINTER, ctk`. Nunca `import customtkinter`.
