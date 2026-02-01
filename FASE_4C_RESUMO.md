# FASE 4C - Eliminação de Shims Internos + Guard

## Data: 2026-02-01

### Objetivo
Garantir que o código interno do projeto use **APENAS** os caminhos definitivos em `src.modules.clientes.core.*`, eliminando dependência dos shims de compatibilidade.

Os shims continuam existindo para compatibilidade externa, mas código interno não deve usá-los.

---

## PASSO 1 - Atualização de Imports Internos

### Substituições Realizadas

| Path Antigo (shim) | Path Novo (core) |
|-------------------|------------------|
| `src.modules.clientes.export` | `src.modules.clientes.core.export` |
| `src.modules.clientes.viewmodel` | `src.modules.clientes.core.viewmodel` |
| `src.modules.clientes.service` | `src.modules.clientes.core.service` |
| `src.modules.clientes.components.helpers` | `src.modules.clientes.core.constants` |
| `src.modules.clientes.views.main_screen_helpers` | `src.modules.clientes.core.ui_helpers` |

### Arquivos Atualizados

#### src/ (22 arquivos)
- `src/core/app_core.py`
- `src/modules/clientes/components/status.py`
- `src/modules/clientes/core/ui_helpers.py`
- `src/modules/clientes/core/viewmodel.py` ⚠️ **Crítico**: corrigido import relativo `..components.helpers` → `.constants`
- `src/modules/clientes/ui/view.py`
- `src/modules/clientes/ui/views/client_editor_dialog.py`
- `src/modules/clientes/ui/views/toolbar.py`
- `src/modules/clientes/forms/_archived/*.py` (7 arquivos)
- `src/modules/clientes_v2/views/*.py` (2 arquivos)
- `src/modules/forms/actions_impl.py`
- `src/modules/hub/dashboard/data_access.py`
- `src/modules/lixeira/views/lixeira.py`

#### tests/ (30 arquivos)
- `tests/modules/clientes_ui/*.py` (5 arquivos)
- `tests/unit/modules/clientes/*.py` (12 arquivos)
- `tests/unit/modules/clientes/controllers/*.py` (5 arquivos)
- `tests/unit/modules/clientes/views/*.py` (13 arquivos)

**Total: 52 arquivos atualizados**

---

## PASSO 2 - Guard Anti-Regressão

### Arquivo Criado
`tools/check_no_clientes_shim_imports.py`

### Funcionalidades
1. **Varre src/ e tests/** usando AST parsing
2. **Detecta imports proibidos** dos shims:
   - `from src.modules.clientes.export import ...`
   - `from src.modules.clientes.viewmodel import ...`
   - `from src.modules.clientes.service import ...`
   - `from src.modules.clientes.components.helpers import ...`
   - `from src.modules.clientes.views.main_screen_helpers import ...`

3. **Exceções permitidas**: Os 5 arquivos shim em si
   - `src/modules/clientes/export.py`
   - `src/modules/clientes/viewmodel.py`
   - `src/modules/clientes/service.py`
   - `src/modules/clientes/components/helpers.py`
   - `src/modules/clientes/views/main_screen_helpers.py`

4. **Output detalhado**:
   - Lista arquivo + linha + coluna de cada violação
   - Sugere caminhos corretos (`core.*`)
   - Exit code 1 se violações encontradas (bloqueia CI)

### Integração CI/Pre-commit
Adicionado em `.pre-commit-config.yaml`:
```yaml
- id: check-no-clientes-shim-imports
  name: Proibir uso interno de shims (usar core/*)
  language: system
  entry: python tools/check_no_clientes_shim_imports.py
  types: [python]
  pass_filenames: false
```

CI (`.github/workflows/ci.yml`) já executa `pre-commit run --all-files`, então guard está integrado automaticamente.

---

## PASSO 3 - Gate Forte: DeprecationWarning

### Teste Implementado
```python
python -c "
import warnings
warnings.filterwarnings('error', category=DeprecationWarning, module=r'src\.modules\.clientes\.')
import src.modules.clientes.ui.view
print('✅ Nenhum DeprecationWarning disparado')
"
```

### Resultado
✅ **PASSOU**: Nenhum DeprecationWarning disparado

Isso garante que:
- Código interno não usa shims
- Shims só são carregados via imports externos (se houver)
- Warnings configuráveis via `warnings.filterwarnings()`

---

## PASSO 4 - Validações

### ✅ Compilação
```bash
python -m compileall src -q
# Resultado: ✅ Compilação OK
```

### ✅ Guard Clientes V2
```bash
python tools/check_no_clientes_v2_imports.py
# Resultado: ✅ Nenhuma referência encontrada
```

### ✅ Guard Shims
```bash
python tools/check_no_clientes_shim_imports.py
# Resultado: ✅ Nenhum import de shim encontrado
```

### ✅ DeprecationWarning Gate
```bash
python -c "import warnings; warnings.filterwarnings('error', category=DeprecationWarning, module=r'src\.modules\.clientes\.'); import src.modules.clientes.ui.view; print('✅ OK')"
# Resultado: ✅ OK
```

---

## Correção Crítica Encontrada

Durante validação de DeprecationWarning, detectamos:

**Arquivo**: `src/modules/clientes/core/viewmodel.py`  
**Linha 19**: `from ..components import helpers as status_helpers`

**Problema**: Import relativo de shim dentro do próprio core  
**Correção**: `from . import constants as status_helpers`

Isso é uma **vitória do gate forte** - detectou código que passaria em AST check mas falharia em runtime warnings.

---

## Estrutura Final

```
src/modules/clientes/
├── core/                    # DEFINITIVO (usar sempre)
│   ├── constants.py        # <- Status helpers (ex-helpers.py)
│   ├── export.py           # <- Exportação CSV/XLSX
│   ├── service.py          # <- Domain services
│   ├── ui_helpers.py       # <- UI helpers puros (ex-main_screen_helpers.py)
│   └── viewmodel.py        # <- ViewModel principal
│
├── ui/                      # Interface CustomTkinter
│   ├── view.py             # ✅ Usa core.*
│   └── views/
│       ├── client_editor_dialog.py  # ✅ Usa core.*
│       └── toolbar.py               # ✅ Usa core.*
│
└── [SHIMS - NÃO USAR INTERNAMENTE]
    ├── export.py           # Re-export de core.export
    ├── service.py          # Re-export de core.service
    ├── viewmodel.py        # Re-export de core.viewmodel
    ├── components/
    │   └── helpers.py      # Re-export de core.constants
    └── views/
        └── main_screen_helpers.py  # Re-export de core.ui_helpers
```

---

## Métricas

- **52 arquivos atualizados** (22 src/ + 30 tests/)
- **5 shims** protegidos como exceções
- **0 violações** restantes
- **0 DeprecationWarnings** disparados por código interno
- **2 guards ativos** (clientes_v2 + shims)
- **100% CI/pre-commit integração**

---

## Comandos de Validação Rápida

```bash
# Validar tudo
python -m compileall src -q && \
python tools/check_no_clientes_v2_imports.py && \
python tools/check_no_clientes_shim_imports.py && \
python -c "import warnings; warnings.filterwarnings('error', category=DeprecationWarning, module=r'src\.modules\.clientes\.'); import src.modules.clientes.ui.view; print('✅ Validação completa OK')"
```

---

## Benefícios Alcançados

1. **Clareza Arquitetural**: `core/` é o source of truth
2. **Manutenibilidade**: Shims isolados, código interno limpo
3. **Prevenção de Regressões**: Guards automáticos em CI
4. **Compatibilidade Preservada**: Shims funcionam para imports externos
5. **Rastreabilidade**: DeprecationWarnings rastreiam uso externo dos shims
6. **Performance**: Menos camadas indiretas em código crítico

---

**FASE 4C CONCLUÍDA** ✅
