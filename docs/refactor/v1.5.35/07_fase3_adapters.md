# 07 - Fase 3: Migração de `adapters/` para `src/adapters/`

> **Data de execução:** 2025-01-02  
> **Status:** ✅ Concluída  
> **Duração estimada:** ~10 minutos

---

## 🎯 Objetivo

Mover a pasta `adapters/` da raiz para dentro de `src/adapters/` e atualizar todos os imports do projeto de `adapters.*` para `src.adapters.*`, mantendo o projeto em estado funcional.

---

## 📊 Métricas Antes/Depois

| Métrica | Antes | Depois |
|---------|-------|--------|
| Imports `from adapters` / `import adapters` | **30** | **0** |
| Imports `from src.adapters` / `import src.adapters` | **0** | **30** |
| Arquivos .py atualizados | - | **17** |
| Arquivos movidos | - | **5** |

---

## 📋 Plano de Execução

### Etapa 1: Verificações Prévias
- [x] Verificar se `src/adapters/` já existe → **Não existia**
- [x] Listar arquivos em `adapters/` → 5 arquivos .py

### Etapa 2: Mover Pasta
- [x] Executar `git mv adapters src/adapters`
- [x] Preservar histórico Git

### Etapa 3: Atualizar Imports
- [x] Substituir `from adapters.` → `from src.adapters.`
- [x] Substituir `import adapters.` → `import src.adapters.`
- [x] Incluir arquivos dentro de `src/adapters/` (imports internos)
- [x] Incluir testes em `tests/`

### Etapa 4: Validações
- [x] `python -m py_compile main.py` → **OK**
- [x] `python -m compileall -q src security tests` → **OK**
- [x] `python -c "import src; import src.adapters"` → **OK**
- [x] Contagem de imports `adapters` remanescentes → **0**

---

## 📁 Arquivos Movidos (5 arquivos .py)

```
adapters/__init__.py              → src/adapters/__init__.py
adapters/storage/__init__.py      → src/adapters/storage/__init__.py
adapters/storage/api.py           → src/adapters/storage/api.py
adapters/storage/port.py          → src/adapters/storage/port.py
adapters/storage/supabase_storage.py → src/adapters/storage/supabase_storage.py
```

---

## 📝 Arquivos com Imports Atualizados (17 arquivos)

### Código Principal (11 arquivos)

| Diretório | Arquivos |
|-----------|----------|
| `src/adapters/storage/` | `supabase_storage.py` (import interno) |
| `src/core/api/` | `api_files.py`, `api_notes.py` |
| `src/core/services/` | `lixeira_service.py` |
| `src/modules/anvisa/views/` | `anvisa_footer.py` |
| `src/modules/clientes/` | `service.py` |
| `src/modules/clientes/forms/` | `_prepare.py` |
| `src/modules/uploads/` | `repository.py`, `service.py`, `storage_browser_service.py` |
| `src/ui/` | `subpastas_dialog.py` |

### Testes (6 arquivos)

```
tests/adapters/test_storage_api.py
tests/unit/adapters/test_adapters_supabase_storage_fase37.py
tests/unit/adapters/test_supabase_storage_fase02.py
tests/unit/adapters/test_supabase_storage_observability.py
tests/unit/core/test_text_normalization_canonical_fase4.py
tests/unit/modules/clientes/test_clientes_integration.py
```

---

## 🔄 Padrões de Import Alterados

### Padrão 1: Import de módulo com alias

```python
# ANTES
from adapters.storage import api as storage_api

# DEPOIS
from src.adapters.storage import api as storage_api
```

### Padrão 2: Import de funções específicas

```python
# ANTES
from adapters.storage.api import delete_file as storage_delete_file
from adapters.storage.api import list_files as storage_list_files

# DEPOIS
from src.adapters.storage.api import delete_file as storage_delete_file
from src.adapters.storage.api import list_files as storage_list_files
```

### Padrão 3: Import de classe Adapter

```python
# ANTES
from adapters.storage.supabase_storage import SupabaseStorageAdapter

# DEPOIS
from src.adapters.storage.supabase_storage import SupabaseStorageAdapter
```

### Padrão 4: Import de módulo completo (em testes)

```python
# ANTES
import adapters.storage.api as storage_api

# DEPOIS
import src.adapters.storage.api as storage_api
```

### Padrão 5: Import interno do pacote

```python
# ANTES (em src/adapters/storage/supabase_storage.py)
from adapters.storage.port import StoragePort

# DEPOIS
from src.adapters.storage.port import StoragePort
```

---

## ✅ Validações Executadas

### 1. Sintaxe

```bash
$ python -m py_compile main.py
# (sem erros)

$ python -m compileall -q src security tests
# (sem erros)
```

### 2. Imports Básicos

```bash
$ python -c "import src; import src.adapters; print('OK')"
OK: src + src.adapters importaram
```

### 3. Contagem de Imports (via AST)

```
Imports remanescentes de adapters (sem src.): 0
Total de imports src.adapters: 30
```

---

## ⚠️ Dependências Identificadas

### 1. Dependência de `src.infra`

O arquivo `src/adapters/storage/supabase_storage.py` importa de `src.infra`:

```python
from src.infra.supabase_client import supabase, baixar_pasta_zip, DownloadCancelledError
```

**Status:** ✅ Já migrado na Fase 1.

### 2. Referências em sitecustomize.py

O arquivo `sitecustomize.py` pode ter referências a `adapters`. Isso será tratado na **Fase 5**.

### 3. Build PyInstaller (rcgestor.spec)

O arquivo `rcgestor.spec` pode precisar de ajustes para o novo path. Será tratado na **Fase 5**.

---

## 📋 Commit Sugerido

```bash
git add -A
git commit -m "refactor(adapters): move adapters/ to src/adapters/ and update imports

- Move all adapters/ contents to src/adapters/ preserving git history
- Update 30 import statements from 'adapters.*' to 'src.adapters.*'
- Update 17 Python files (11 source + 6 tests)
- All syntax validations passing

Phase 3 of src-layout consolidation (v1.5.35 refactor)
"
```

---

## 📎 Arquivos Relacionados

- [README.md](README.md) - Roadmap atualizado
- [06_fase2_data.md](06_fase2_data.md) - Documentação da Fase 2
- [05_fase1_infra.md](05_fase1_infra.md) - Documentação da Fase 1
