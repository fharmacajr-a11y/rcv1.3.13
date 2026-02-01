# FASE 4A - Inventário de src/modules/clientes/

**Data:** 2026-02-01  
**Objetivo:** Classificar arquivos para migração incremental para `clientes/core/`

---

## 📊 Mapa de Arquivos

### 🟢 CATEGORIA A - CORE Compartilhado (Migrar para `core/`)

#### 1. `service.py` (CORE - Business Logic)
- **Usado por:**
  - ✅ `lixeira/views/lixeira.py` - fetch_all_clientes_lixeira, restaurar_cliente, excluir_cliente_permanente
  - ✅ `hub/dashboard/data_access.py` - fetch_cliente_by_id
  - ✅ `forms/actions_impl.py` - extrair_dados_cartao_cnpj_em_pasta
  - ✅ `clientes/ui/views/client_editor_dialog.py` - salvar_cliente
  - ✅ `core/app_core.py` - get_cliente_by_id, mover_cliente_para_lixeira
  - ✅ `forms/_archived/*.py` - vários (legado)
- **Categoria:** CORE - Lógica de negócio essencial
- **Ação:** Migrar para `core/service.py` + shim de reexport

#### 2. `viewmodel.py` (CORE - Data Layer)
- **Usado por:**
  - ✅ `clientes/ui/view.py` - ClientesViewModel, ClienteRow
  - ✅ `clientes/ui/views/client_editor_dialog.py` - ClientesViewModel (3x)
  - ✅ `clientes/views/main_screen_helpers.py` - ClienteRow
  - ✅ `clientes_v2/` (shim) - várias views
- **Categoria:** CORE - ViewModel padrão MVVM
- **Ação:** Migrar para `core/viewmodel.py` + shim de reexport

#### 3. `export.py` (CORE - Export Utilities)
- **Usado por:**
  - ✅ `clientes/ui/view.py` - export_to_excel
- **Categoria:** CORE - Utilitário compartilhado
- **Ação:** Migrar para `core/export.py` + shim de reexport

#### 4. `components/helpers.py` (CORE - Constantes e Helpers)
- **Conteúdo:** STATUS_CHOICES, STATUS_PREFIX_RE
- **Usado por:**
  - ✅ `clientes/components/status.py`
  - ✅ `clientes/service.py`
  - ✅ `clientes/ui/views/toolbar.py` (2x)
  - ✅ `clientes/ui/views/client_editor_dialog.py`
  - ✅ `clientes/ui/view.py`
  - ✅ `forms/_archived/*.py` (legado)
- **Categoria:** CORE - Constantes compartilhadas
- **Ação:** Migrar para `core/constants.py` + shim de reexport

#### 5. `components/status.py` (CORE - Status Helpers)
- **Conteúdo:** apply_status_prefix
- **Usado por:**
  - ✅ `forms/_archived/*.py` (legado apenas)
- **Categoria:** CORE - Utilitário de status
- **Ação:** Migrar para `core/status_utils.py` + shim de reexport

#### 6. `views/main_screen_helpers.py` (CORE - UI Helpers)
- **Conteúdo:** ORDER_CHOICES, DEFAULT_ORDER_LABEL, normalize_order_label
- **Usado por:**
  - ✅ `clientes/ui/view.py` (2x)
- **Categoria:** CORE - Helpers de UI compartilhados
- **Ação:** Migrar para `core/ui_helpers.py` + shim de reexport

#### 7. `forms/client_subfolder_prompt.py` (CORE - Dialog Reutilizável)
- **Conteúdo:** SubpastaDialog
- **Usado por:**
  - ✅ `ui/subpastas/dialog.py` - open_subpastas_dialog (reexport)
  - ✅ `modules/uploads/uploader_supabase.py`
  - ✅ `modules/forms/view.py`
  - ✅ `modules/forms/actions_impl.py`
  - ✅ `clientes/ui/views/client_files_dialog.py`
  - ✅ `clientes/forms/client_form_upload_helpers.py`
  - ✅ `clientes_v2/views/client_files_dialog.py`
- **Categoria:** CORE - Dialog compartilhado entre módulos
- **Ação:** Migrar para `core/dialogs.py` + shim de reexport

#### 8. `forms/client_form_upload_helpers.py` (CORE - Upload Helpers)
- **Conteúdo:** execute_upload_flow
- **Usado por:**
  - ✅ `clientes/ui/views/client_editor_dialog.py`
  - ✅ `clientes_v2/views/client_editor_dialog.py`
  - ✅ `forms/_archived/client_form_adapters.py`
- **Categoria:** CORE - Utilitário de upload
- **Ação:** Migrar para `core/upload_utils.py` + shim de reexport

---

### 🔴 CATEGORIA B - UI Legada (Remover após validação)

#### 1. `forms/_archived/` (UI LEGADA)
**Arquivos:**
- `client_form.py` - Formulário antigo (Tkinter legacy)
- `client_form_view.py` - View antiga
- `client_form_view_ctk.py` - View CTK antiga
- `client_form_state.py` - State manager antigo
- `client_form_new.py` - Form novo antigo (irônico)
- `client_form_actions.py` - Actions antigas
- `client_form_cnpj_actions.py` - CNPJ actions antigas
- `client_form_adapters.py` - Adapters antigos
- `_prepare.py` - Preparador antigo

**Importados por:**
- ⚠️ `core/app_core.py` - form_cliente (2x) - **PRECISA MIGRAR**
- ✅ Entre si (imports internos)

**Razão para remoção:**
- UI foi completamente reescrita em `clientes/ui/views/client_editor_dialog.py`
- Forms antigas não seguem padrão moderno
- Mantidas apenas por compatibilidade com `app_core.py`

**Ação:**
1. Migrar `app_core.py` para usar `clientes/ui/views/client_editor_dialog.py`
2. Remover pasta `forms/_archived/` completa

#### 2. `forms/_dupes.py` (CÓDIGO MORTO?)
- **Conteúdo:** Possível duplicação/teste
- **Usado por:** ❓ Verificar com grep
- **Ação:** Verificar e remover se não usado

---

### ⚪ CATEGORIA C - Código Morto (Verificar e Remover)

#### 1. `components/__init__.py`
- **Conteúdo:** Provavelmente vazio ou reexports
- **Ação:** Verificar se reexporta algo útil

#### 2. `views/__init__.py`
- **Conteúdo:** Provavelmente vazio ou reexports
- **Ação:** Verificar se reexporta algo útil

#### 3. `forms/__init__.py`
- **Conteúdo:** Reexports ClientPicker, open_subpastas_dialog
- **Usado por:**
  - ✅ `ui/widgets/client_picker.py`
  - ✅ `ui/subpastas/dialog.py`
  - ✅ `core/app_core.py`
- **Ação:** Manter por enquanto, migrar para `core/` depois

---

## 📋 Estrutura Proposta para `clientes/core/`

```
src/modules/clientes/
├── core/                           # 🆕 CORE compartilhado
│   ├── __init__.py                 # Exporta tudo
│   ├── service.py                  # ← de clientes/service.py
│   ├── viewmodel.py                # ← de clientes/viewmodel.py
│   ├── export.py                   # ← de clientes/export.py
│   ├── constants.py                # ← de components/helpers.py
│   ├── status_utils.py             # ← de components/status.py
│   ├── ui_helpers.py               # ← de views/main_screen_helpers.py
│   ├── dialogs.py                  # ← de forms/client_subfolder_prompt.py
│   └── upload_utils.py             # ← de forms/client_form_upload_helpers.py
├── ui/                             # UI moderna (já migrado)
│   ├── view.py
│   └── views/
├── forms/                          # ⚠️ Manter temporariamente
│   ├── __init__.py                 # Reexports para compatibilidade
│   ├── client_subfolder_prompt.py  # → shim: from ..core.dialogs import *
│   ├── client_form_upload_helpers.py # → shim: from ..core.upload_utils import *
│   └── _archived/                  # 🗑️ REMOVER após migrar app_core.py
├── components/                     # ⚠️ Manter temporariamente
│   ├── helpers.py                  # → shim: from ..core.constants import *
│   └── status.py                   # → shim: from ..core.status_utils import *
├── views/                          # ⚠️ Manter temporariamente
│   └── main_screen_helpers.py      # → shim: from ..core.ui_helpers import *
├── service.py                      # → shim: from .core.service import *
├── viewmodel.py                    # → shim: from .core.viewmodel import *
├── export.py                       # → shim: from .core.export import *
└── __init__.py                     # Mantém exports públicos
```

---

## 🎯 Ordem de Migração (Incremental, 1 arquivo por vez)

### FASE 4B - Mover para core/ (com shims)

1. ✅ Criar `clientes/core/` + `__init__.py`
2. 🔄 Migrar `viewmodel.py` (mais usado, começar por ele)
3. 🔄 Migrar `service.py`
4. 🔄 Migrar `components/helpers.py` → `core/constants.py`
5. 🔄 Migrar `views/main_screen_helpers.py` → `core/ui_helpers.py`
6. 🔄 Migrar `export.py`
7. 🔄 Migrar `components/status.py` → `core/status_utils.py`
8. 🔄 Migrar `forms/client_subfolder_prompt.py` → `core/dialogs.py`
9. 🔄 Migrar `forms/client_form_upload_helpers.py` → `core/upload_utils.py`

### FASE 4C - Atualizar imports em clientes/ui

10. 🔄 Atualizar `clientes/ui/view.py` para usar `core.*`
11. 🔄 Atualizar `clientes/ui/views/*.py` para usar `core.*`

### FASE 4D - Remover UI Legada

12. 🔄 Migrar `core/app_core.py` para usar `clientes/ui/views/client_editor_dialog.py`
13. 🗑️ Remover `forms/_archived/` completo
14. 🗑️ Remover `forms/_dupes.py` se não usado

---

## 📊 Estatísticas

| Categoria | Arquivos | Status |
|-----------|----------|--------|
| **A - CORE** | 8 arquivos | Migrar para `core/` |
| **B - UI Legada** | ~10 arquivos (_archived/) | Remover após migração |
| **C - Código Morto** | 2-3 arquivos | Verificar e remover |
| **Total** | ~20 arquivos | Consolidar para ~8 em `core/` |

---

## ⚠️ Riscos e Mitigações

### Risco 1: Quebrar imports existentes
**Mitigação:** Criar shims de reexport em todos caminhos antigos

### Risco 2: Quebrar app_core.py
**Mitigação:** Migrar app_core.py ANTES de remover forms/_archived/

### Risco 3: Circular imports
**Mitigação:** Mover um arquivo por vez, testar a cada step

---

## ✅ Gates de Validação (Cada Step)

Após cada migração, executar:
```bash
# 1. Guard anti-regressão
python tools/check_no_clientes_v2_imports.py

# 2. Sintaxe Python
python -m py_compile src/modules/clientes/core/*.py

# 3. Aplicação
python main.py
# Testar: Novo, Editar, Arquivos, Upload, Lixeira, Status, Tema

# 4. Testes (se houver)
pytest tests/modules/clientes_ui/ -q
```

---

**Próximo Passo:** FASE 4B - Criar `core/` e migrar `viewmodel.py` primeiro.
