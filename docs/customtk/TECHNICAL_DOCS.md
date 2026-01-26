# 🔧 Documentação Técnica - CustomTkinter

**Políticas, configurações e padrões técnicos consolidados**

---

## 📋 Índice

1. [Import Policy](#import-policy)
2. [Theme System](#theme-system)
3. [Security Model](#security-model)
4. [Testing Strategy](#testing-strategy)
5. [UI Audit](#ui-audit)

---

## Import Policy

### Regra Principal

**PROIBIDO** import direto de `customtkinter`:

```python
# ❌ ERRADO
import customtkinter as ctk
from customtkinter import CTkButton

# ✅ CORRETO
from src.ui.ctk_config import ctk
```

### Justificativa

- **Centralização:** Único ponto de configuração
- **Testabilidade:** Fácil mocking via `ctk_config`
- **Controle:** Evita root implícita e configurações dispersas

### Enforcement

Pre-commit hook valida todos os arquivos Python:

```yaml
- id: ctk-import-policy
  name: Proibir import direto de customtkinter
  entry: python tools/check_ctk_imports.py
  language: system
  types: [python]
```

**Exceções permitidas:**
- `src/ui/ctk_config.py` (SSoT)
- `tests/` com mocks explícitos

---

## Theme System

### Single Source of Truth (SSoT)

**Arquivo:** `src/ui/ctk_config.py`

```python
import customtkinter as _ctk

# Configuração global (executada uma vez)
_ctk.set_appearance_mode("dark")
_ctk.set_default_color_theme("blue")

# Export controlado
ctk = _ctk
```

### Uso Correto

```python
from src.ui.ctk_config import ctk

class MyWidget(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.button = ctk.CTkButton(self, text="Click")
```

### Garantias

- ✅ Sem root implícita (Tk() não chamado no import)
- ✅ Tema carregado centralmente
- ✅ Configurações consistentes em toda aplicação

---

## Security Model

### Bandit Configuration

**Arquivo:** `.bandit`

**Skips globais:**
- `B101` (assert_used) - Usado extensivamente em testes
- `B110` (try_except_pass) - Padrão de fallback aceitável

**Tratamento Pontual:**

```python
# nosec B112 - Fallback pattern: tenta múltiplos caminhos
try:
    from src.infra.supabase.client import supabase_client
except ImportError:
    # nosec B112 - Pattern documentado
    pass
```

### Políticas

1. **Nunca** skip global sem justificativa
2. **Sempre** documentar `# nosec` com motivo
3. **Preferir** correção sobre supressão
4. **Validar** com `bandit -c .bandit -r src/`

---

## Testing Strategy

### Estrutura

```
tests/
├── unit/ - Testes unitários isolados
├── integration/ - Testes de integração
└── modules/
    └── clientes_v2/ - 112+ testes do módulo principal
```

### Coverage Targets

- **Global:** >75%
- **Módulos críticos:** >85%
- **UI components:** >70%

### Mocking CustomTkinter

```python
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_ctk(monkeypatch):
    """Mock customtkinter para testes unitários."""
    mock = MagicMock()
    monkeypatch.setattr("src.ui.ctk_config.ctk", mock)
    return mock

def test_button_creation(mock_ctk):
    from src.ui.components import MyButton
    button = MyButton(parent=None, text="Test")
    mock_ctk.CTkButton.assert_called_once()
```

### Skip Policy

**Tipos permitidos:**

1. **@pytest.mark.skip** - Temporário, com issue linkado
2. **@pytest.mark.skipif** - Condicional (ex: Windows only)
3. **@pytest.mark.xfail** - Falha conhecida, fixing in progress

**Proibido:**
- Skip sem justificativa
- Skip permanente sem issue
- Skip para "ocultar" falhas

---

## UI Audit

### Componentes Padrão

**Base:** `src/ui/components/`

- `CTkFrame` - Containers
- `CTkButton` - Botões
- `CTkEntry` - Inputs de texto
- `CTkLabel` - Labels
- `CTkScrollableFrame` - Frames com scroll

**Custom:** `src/ui/widgets/`

- `EnhancedTreeview` - Treeview customizado
- `SearchBar` - Barra de busca reutilizável
- `ActionButton` - Botões com ícones

### Padrões de Layout

**Grid system preferido:**

```python
self.grid_columnconfigure(0, weight=1)
self.grid_rowconfigure(0, weight=1)

# Elementos
label.grid(row=0, column=0, sticky="w", padx=5)
entry.grid(row=0, column=1, sticky="ew", padx=5)
```

**Evitar:**
- Mix de grid + pack no mesmo container
- Magic numbers (usar constantes)
- Hardcoded sizes (usar weights)

### Theme Compliance

**Colors permitidos:**

- Uso de `fg_color`, `hover_color` via tema
- **Evitar:** RGB hardcoded

**Fonts:**

- Usar `CTkFont` para consistência
- Tamanhos: 12 (normal), 14 (header), 10 (small)

---

## 🔗 Referências

### Documentos Arquivados

Detalhes completos em [_archive/](/_archive/):

- `CTK_IMPORT_POLICY.md` - Política completa de imports
- `SECURITY_MODEL.md` - Modelo de segurança detalhado
- `UI_AUDIT.md` - Auditoria completa de UI
- `TESTS_SKIPS_REPORT.md` - Relatório de skips
- `VSCODE_TESTING_CONFIG.md` - Config de testes no VSCode

### Guidelines Externas

- [CustomTkinter Docs](https://github.com/TomSchimansky/CustomTkinter)
- [Bandit Security](https://bandit.readthedocs.io/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/)

---

**Última atualização:** 26 de janeiro de 2026
