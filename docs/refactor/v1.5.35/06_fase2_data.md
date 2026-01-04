# 06 - Fase 2: Migração de `data/` para `src/data/`

> **Data de execução:** 2025-01-02  
> **Status:** ✅ Concluída  
> **Duração estimada:** ~15 minutos

---

## 🎯 Objetivo

Mover a pasta `data/` da raiz para dentro de `src/data/` e atualizar todos os imports do projeto de `data.*` para `src.data.*`, mantendo o projeto em estado funcional.

---

## 📊 Métricas Antes/Depois

| Métrica | Antes | Depois |
|---------|-------|--------|
| Imports `from data` / `import data` | **47** | **0** |
| Imports `from src.data` / `import src.data` | **0** | **47** |
| Arquivos .py atualizados | - | **34** |
| Arquivos movidos | - | **4** |

---

## 📋 Plano de Execução

### Etapa 1: Verificações Prévias
- [x] Verificar se `src/data/` já existe → **Não existia**
- [x] Listar arquivos em `data/` → 4 arquivos .py

### Etapa 2: Mover Pasta
- [x] Executar `git mv data src/data`
- [x] Preservar histórico Git

### Etapa 3: Atualizar Imports
- [x] Substituir `from data.` → `from src.data.`
- [x] Substituir `import data.` → `import src.data.`
- [x] Incluir arquivos dentro de `src/data/` (imports internos)
- [x] Incluir `src/infra/` (que importa de data)
- [x] Incluir testes em `tests/`

### Etapa 4: Validações
- [x] `python -m py_compile main.py` → **OK**
- [x] `python -m compileall -q src adapters security` → **OK**
- [x] `python -c "import src; import src.data"` → **OK**
- [x] Contagem de imports `data` remanescentes → **0**

---

## 📁 Arquivos Movidos (4 arquivos)

```
data/__init__.py        → src/data/__init__.py
data/auth_bootstrap.py  → src/data/auth_bootstrap.py
data/domain_types.py    → src/data/domain_types.py
data/supabase_repo.py   → src/data/supabase_repo.py
```

---

## 📝 Arquivos com Imports Atualizados (34 arquivos)

### Código Principal (22 arquivos)

| Diretório | Arquivos |
|-----------|----------|
| `src/core/` | `auth_bootstrap.py` |
| `src/core/services/` | `lixeira_service.py` |
| `src/data/` | `supabase_repo.py` (import interno) |
| `src/features/cashflow/` | `repository.py` |
| `src/features/regulations/` | `repository.py`, `service.py` |
| `src/features/tasks/` | `repository.py`, `service.py` |
| `src/infra/repositories/` | `passwords_repository.py` |
| `src/infra/supabase/` | `auth_client.py` |
| `src/modules/clientes/forms/` | `client_picker.py` |
| `src/modules/clientes/views/` | `client_obligations_frame.py`, `obligation_dialog.py` |
| `src/modules/hub/views/` | `hub_dashboard_callbacks.py` |
| `src/modules/passwords/` | `controller.py`, `passwords_actions.py`, `service.py` |
| `src/modules/passwords/views/` | `client_passwords_dialog.py`, `passwords_screen.py`, `password_dialog.py` |
| `src/modules/tasks/views/` | `task_dialog.py` |
| `src/ui/` | `login_dialog.py` |

### Testes (12 arquivos)

```
tests/data/test_auth_bootstrap_data.py
tests/data/test_supabase_repo.py
tests/infra/repositories/test_passwords_repository.py
tests/integration/passwords/test_passwords_flows.py
tests/unit/data/test_supabase_repo.py
tests/unit/features/regulations/test_service_obligations.py
tests/unit/features/tasks/test_service_create_task.py
tests/unit/modules/cashflow/test_cashflow_service.py
tests/unit/modules/passwords/conftest.py
tests/unit/modules/passwords/test_passwords_controller.py
tests/unit/modules/passwords/test_passwords_service_errors.py
tests/unit/modules/tasks/views/test_task_dialog.py
```

---

## 🔄 Padrões de Import Alterados

### Padrão Principal (maioria dos casos)

```python
# ANTES
from data.domain_types import ClientRow, PasswordRow
from data.supabase_repo import list_clients_for_picker

# DEPOIS
from src.data.domain_types import ClientRow, PasswordRow
from src.data.supabase_repo import list_clients_for_picker
```

### Import de Módulo Completo (em testes)

```python
# ANTES
import data.supabase_repo as repo

# DEPOIS
import src.data.supabase_repo as repo
```

### Import Interno (dentro de src/data/)

```python
# ANTES (em src/data/supabase_repo.py)
from data.domain_types import ClientRow, PasswordRow

# DEPOIS
from src.data.domain_types import ClientRow, PasswordRow
```

---

## ✅ Validações Executadas

### 1. Sintaxe

```bash
$ python -m py_compile main.py
# (sem erros)

$ python -m compileall -q src adapters security
# (sem erros)
```

### 2. Imports Básicos

```bash
$ python -c "import src; import src.data; print('OK')"
OK: src + src.data importaram
```

### 3. Contagem de Imports (via AST)

```
Imports remanescentes de data (sem src.): 0
Total de imports src.data: 47
```

---

## ⚠️ Dependências Identificadas

### 1. Dependência de `security.crypto`

O arquivo `src/data/supabase_repo.py` importa de `security.crypto`:

```python
from security.crypto import decrypt_text, encrypt_text
```

**Status:** Será atualizado na Fase 4 quando `security/` for movido para `src/security/`.

### 2. Paths de Filesystem

Não foram encontrados paths hardcoded para a pasta `data/` como diretório de arquivos. Apenas strings de texto/labels contendo "data/" (não relacionadas ao pacote).

---

## 📋 Commit Sugerido

```bash
git add -A
git commit -m "refactor(data): move data/ to src/data/ and update imports

- Move all data/ contents to src/data/ preserving git history
- Update 47 import statements from 'data.*' to 'src.data.*'
- Update 34 Python files (22 source + 12 tests)
- All syntax validations passing

Phase 2 of src-layout consolidation (v1.5.35 refactor)
"
```

---

## 📎 Arquivos Relacionados

- [README.md](README.md) - Roadmap atualizado
- [05_fase1_infra.md](05_fase1_infra.md) - Documentação da Fase 1
