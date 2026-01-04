# 05 - Fase 1: Migração de `infra/` para `src/infra/`

> **Data de execução:** 2025-01-02  
> **Status:** ✅ Concluída  
> **Duração estimada:** ~30 minutos

---

## 🎯 Objetivo

Mover a pasta `infra/` da raiz para dentro de `src/infra/` e atualizar todos os imports do projeto de `infra.*` para `src.infra.*`, mantendo o projeto em estado funcional.

---

## 📊 Métricas Antes/Depois

| Métrica | Antes | Depois |
|---------|-------|--------|
| Imports `from infra` / `import infra` | **312** | **0** |
| Imports `from src.infra` / `import src.infra` | **0** | **312** |
| Arquivos .py atualizados | - | **82** |
| Arquivos movidos | - | **23** |

---

## 📋 Plano de Execução

### Etapa 1: Verificações Prévias
- [x] Verificar se `src/infra/` já existe → **Não existia**
- [x] Verificar se `src/infrastructure/` existe → **Existia (vazio)**
- [x] Verificar imports de `src.infrastructure` → **Nenhum**
- [x] Remover `src/infrastructure/` (pasta vazia)

### Etapa 2: Mover Pasta
- [x] Executar `git mv infra src/infra`
- [x] Preservar histórico Git

### Etapa 3: Atualizar Imports
- [x] Substituir `from infra.` → `from src.infra.`
- [x] Substituir `import infra.` → `import src.infra.`
- [x] Incluir arquivos dentro de `src/infra/` (imports internos)
- [x] Incluir testes em `tests/`

### Etapa 4: Validações
- [x] `python -m py_compile main.py` → **OK**
- [x] `python -m compileall -q src data adapters security` → **OK**
- [x] `python -c "import src; import src.infra"` → **OK**
- [x] Contagem de imports `infra` remanescentes → **0**

---

## 📁 Arquivos Movidos (23 arquivos)

```
infra/__init__.py                    → src/infra/__init__.py
infra/archive_utils.py               → src/infra/archive_utils.py
infra/db_schemas.py                  → src/infra/db_schemas.py
infra/healthcheck.py                 → src/infra/healthcheck.py
infra/net_session.py                 → src/infra/net_session.py
infra/net_status.py                  → src/infra/net_status.py
infra/settings.py                    → src/infra/settings.py
infra/supabase_auth.py               → src/infra/supabase_auth.py
infra/supabase_client.py             → src/infra/supabase_client.py
infra/http/__init__.py               → src/infra/http/__init__.py
infra/http/retry.py                  → src/infra/http/retry.py
infra/repositories/__init__.py       → src/infra/repositories/__init__.py
infra/repositories/activity_events_repository.py    → src/infra/repositories/activity_events_repository.py
infra/repositories/anvisa_requests_repository.py    → src/infra/repositories/anvisa_requests_repository.py
infra/repositories/notifications_repository.py      → src/infra/repositories/notifications_repository.py
infra/repositories/passwords_repository.py          → src/infra/repositories/passwords_repository.py
infra/supabase/__init__.py           → src/infra/supabase/__init__.py
infra/supabase/auth_client.py        → src/infra/supabase/auth_client.py
infra/supabase/db_client.py          → src/infra/supabase/db_client.py
infra/supabase/http_client.py        → src/infra/supabase/http_client.py
infra/supabase/storage_client.py     → src/infra/supabase/storage_client.py
infra/supabase/storage_helpers.py    → src/infra/supabase/storage_helpers.py
infra/supabase/types.py              → src/infra/supabase/types.py
```

**Também movido (não-Python):**
```
infra/bin/7zip/7z.dll                → src/infra/bin/7zip/7z.dll
infra/bin/7zip/7z.exe                → src/infra/bin/7zip/7z.exe
infra/bin/7zip/README.md             → src/infra/bin/7zip/README.md
```

---

## 📝 Arquivos com Imports Atualizados (82 arquivos)

### Código Principal (56 arquivos)

| Diretório | Arquivos |
|-----------|----------|
| `src/` (raiz) | `app_status.py` |
| `src/core/` | `auth_bootstrap.py`, `status_monitor.py` |
| `src/core/auth/` | `auth.py` |
| `src/core/db_manager/` | `db_manager.py` |
| `src/core/search/` | `search.py` |
| `src/core/services/` | `clientes_service.py`, `lixeira_service.py`, `notes_service.py`, `notes_service_adapter.py`, `profiles_service.py` |
| `src/core/session/` | `session.py`, `session_guard.py` |
| `src/features/regulations/` | `service.py` |
| `src/helpers/` | `auth_utils.py` |
| `src/infra/` | `healthcheck.py`, `net_status.py`, `supabase_auth.py`, `supabase_client.py` |
| `src/infra/repositories/` | `activity_events_repository.py`, `anvisa_requests_repository.py`, `notifications_repository.py` |
| `src/infra/supabase/` | `db_client.py`, `storage_client.py`, `storage_helpers.py` |
| `src/modules/anvisa/` | `controllers/anvisa_client_lookup_controller.py`, `controllers/anvisa_requests_controller.py`, `views/_anvisa_handlers_mixin.py`, `views/anvisa_screen.py` |
| `src/modules/auditoria/` | `archives.py`, `service.py` |
| `src/modules/clientes/` | `service.py`, `controllers/connectivity.py`, `forms/_prepare.py`, `views/main_screen_batch.py`, `views/main_screen_dataflow.py` |
| `src/modules/hub/` | `hub_screen_controller.py`, `recent_activity_store.py`, `dashboard/service.py`, `views/hub_dialogs.py`, `views/hub_gateway_impl.py` |
| `src/modules/main_window/` | `session_service.py`, `views/main_window.py`, `views/main_window_actions.py`, `views/main_window_handlers.py`, `views/main_window_services.py` |
| `src/modules/passwords/` | `helpers.py`, `service.py` |
| `src/modules/uploads/` | `external_upload_service.py`, `repository.py`, `service.py`, `components/helpers.py` |
| `src/ui/` | `login_dialog.py`, `dialogs/file_select.py` |
| `data/` | `supabase_repo.py` |
| `adapters/storage/` | `supabase_storage.py` |

### Testes (26 arquivos)

```
tests/infra/repositories/test_passwords_repository.py
tests/modules/passwords/test_passwords_service.py
tests/unit/core/test_notifications_minimal.py
tests/unit/core/test_notifications_repository.py
tests/unit/core/test_notifications_repository_coverage.py
tests/unit/infra/http/test_retry_fase02.py
tests/unit/infra/repositories/test_anvisa_repository_coverage.py
tests/unit/infra/repositories/test_anvisa_requests_repository.py
tests/unit/infra/repositories/test_notifications_repository.py
tests/unit/infra/test_archive_utils_fase52.py
tests/unit/infra/test_archives.py
tests/unit/infra/test_db_client_cobertura_qa.py
tests/unit/infra/test_db_client_fase54.py
tests/unit/infra/test_db_client_offline_ux.py
tests/unit/infra/test_db_schemas_contracts.py
tests/unit/infra/test_health_fallback.py
tests/unit/infra/test_httpx_timeout_alias.py
tests/unit/infra/test_infra_healthcheck_fase37.py
tests/unit/infra/test_infra_net_session_fase44.py
tests/unit/infra/test_infra_net_status_fase38.py
tests/unit/infra/test_infra_settings_fase35.py
tests/unit/infra/test_infra_storage_client_fase36.py
tests/unit/infra/test_supabase_key_compat.py
tests/unit/modules/main_window/test_main_window_view.py
tests/unit/modules/passwords/test_passwords_service_errors.py
tests/unit/ui/test_file_select.py
```

---

## 🔄 Padrões de Import Alterados

### Padrão Principal (maioria dos casos)

```python
# ANTES
from infra.supabase_client import get_supabase, exec_postgrest

# DEPOIS
from src.infra.supabase_client import get_supabase, exec_postgrest
```

### Imports de Submódulos

```python
# ANTES
from infra.db_schemas import MEMBERSHIPS_SELECT_ORG_ID
from infra.repositories.notifications_repository import NotificationsRepository

# DEPOIS
from src.infra.db_schemas import MEMBERSHIPS_SELECT_ORG_ID
from src.infra.repositories.notifications_repository import NotificationsRepository
```

### Imports Internos do Pacote

```python
# ANTES (dentro de src/infra/supabase_client.py)
from infra.supabase.auth_client import bind_postgrest_auth_if_any
from infra.supabase.db_client import get_client

# DEPOIS
from src.infra.supabase.auth_client import bind_postgrest_auth_if_any
from src.infra.supabase.db_client import get_client
```

---

## ✅ Validações Executadas

### 1. Sintaxe

```bash
$ python -m py_compile main.py
# (sem erros)

$ python -m compileall -q src data adapters security
# (sem erros)
```

### 2. Imports Básicos

```bash
$ python -c "import src; import src.infra; print('OK')"
OK: src + src.infra importaram
```

### 3. Contagem de Imports Remanescentes

```bash
# Imports "infra" (sem "src.") = 0
# Imports "src.infra" = 312
```

### 4. Build PyInstaller

> ⚠️ **Não executado nesta fase** - será validado na Fase 5 (`sitecustomize.py` e ajustes de build).

---

## ⚠️ Riscos e Follow-ups

### 1. Binários em `src/infra/bin/7zip/`

Os arquivos `7z.exe` e `7z.dll` foram movidos para `src/infra/bin/7zip/`.

**Ação necessária (Fase 5):**
- Verificar se `rcgestor.spec` referencia `infra/bin/7zip` como path
- Atualizar para `src/infra/bin/7zip` se necessário
- Testar build do PyInstaller

### 2. Comentários/Docstrings com Paths Antigos

Alguns arquivos de teste contêm comentários mencionando `infra/` como path (ex.: `# Testes para infra/supabase/db_client.py`). Estes são apenas documentação e **não precisam** ser alterados, mas podem ser atualizados para clareza em uma fase futura.

### 3. `sitecustomize.py`

Verificar se há referências a `infra` em `sitecustomize.py` (Fase 5).

---

## 📋 Commit Sugerido

```bash
git add -A
git commit -m "refactor(infra): move infra/ to src/infra/ and update imports

- Move all infra/ contents to src/infra/ preserving git history
- Update 312 import statements from 'infra.*' to 'src.infra.*'
- Update 82 Python files (56 source + 26 tests)
- Remove empty src/infrastructure/ directory
- All syntax validations passing

Phase 1 of src-layout consolidation (v1.5.35 refactor)
"
```

---

## 📎 Arquivos Relacionados

- [README.md](README.md) - Roadmap atualizado
- [00b_correcao_baseline.md](00b_correcao_baseline.md) - Baseline corrigido
- [02_mapa_imports_baseline.md](02_mapa_imports_baseline.md) - Mapa de imports original
