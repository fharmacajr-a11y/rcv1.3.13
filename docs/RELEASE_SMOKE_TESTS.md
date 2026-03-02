# Smoke Tests — Release v1.5.73

## Pré-requisito: Aplicar a migration de audit trail

### 1. Adicione ao `.env`

```env
SUPABASE_DB_PASSWORD=<senha-do-banco>
# Senha em: Supabase Dashboard → Project Settings → Database → Database password
```

### 2. Aplique a migration

```powershell
.\.venv\Scripts\python.exe scripts/apply_migration.py migrations/20260223_add_audit_trail_to_clients.sql
```

### 3. Verifique o schema

```powershell
.\.venv\Scripts\python.exe scripts/verify_audit_trail_schema.py
```

Saída esperada:
```
  ✅  coluna clients.updated_by  (uuid NULL)
  ✅  coluna clients.deleted_by  (uuid NULL)
  ✅  coluna clients.restored_by (uuid NULL)
  ✅  trigger trg_clients_audit_trail  (BEFORE INSERT OR UPDATE)
  ✅  function fn_clients_audit_trail()  (RETURNS TRIGGER)
  ✅  índice idx_clients_updated_by
  ✅  índice idx_clients_deleted_by
  ✅  índice idx_clients_restored_by
```

---

## Smoke 1 — Lixeira → Restaurar → Validar campos `*_by`

### Passos na UI

1. Abra o app e faça login.
2. Na tela de Clientes, selecione um cliente existente.
3. Clique em **Excluir / Lixeira** → confirme "Enviar para Lixeira".
4. Clique no botão **Lixeira** para abrir a listagem.
5. Selecione o mesmo cliente → clique **Restaurar**.

### Query de validação (Supabase SQL Editor)

```sql
SELECT
    id,
    razao_social,
    deleted_at,
    updated_by,
    deleted_by,
    restored_by
FROM public.clients
WHERE id = <ID_DO_CLIENTE>
ORDER BY updated_at DESC
LIMIT 1;
```

**Resultados esperados após lixeira:**

| Campo        | Valor esperado                  |
|-------------|--------------------------------|
| `deleted_at` | timestamp preenchido            |
| `updated_by` | UUID do usuário logado          |
| `deleted_by` | UUID do usuário logado          |
| `restored_by`| `NULL`                          |

**Resultados esperados após restaurar:**

| Campo        | Valor esperado                  |
|-------------|--------------------------------|
| `deleted_at` | `NULL`                          |
| `updated_by` | UUID do usuário logado          |
| `deleted_by` | `NULL` (limpo pelo trigger)     |
| `restored_by`| UUID do usuário logado          |

> **Nota:** Se o usuário não estiver autenticado via JWT (env dev sem Supabase Auth), todos os `*_by` retornam `NULL` — isso é esperado conforme a nota na migration.

---

## Smoke 2 — Delete definitivo com falha no Storage → não deleta no banco

### Cenário

Simula um erro de Storage durante o hard-delete para garantir que o registro
do banco **não é removido** se o Storage falhar.

### Teste via código (unit test manual)

```python
# Execute no Python REPL dentro do venv:
from unittest.mock import patch
from src.modules.lixeira.service import hard_delete_clients

# Substitua pelo ID de um cliente na lixeira
CLIENT_ID = 999

with patch(
    "src.core.services.lixeira_service._remove_storage_prefix",
    side_effect=ConnectionError("Storage indisponível — teste"),
):
    ok, errs = hard_delete_clients([CLIENT_ID])

print("ok:", ok)          # esperado: 0
print("errs:", errs)      # esperado: [(CLIENT_ID, "Storage: Storage indisponível — teste")]
```

### Query de validação (confirmar que o DB não foi alterado)

```sql
SELECT id, razao_social, deleted_at
FROM public.clients
WHERE id = <CLIENT_ID>;
-- O cliente deve ainda existir na tabela
```

**Resultado esperado:**
- `ok == 0` no retorno da função
- O cliente AINDA aparece na query SQL acima
- Log contém: `"Falha ao limpar Storage de ... — abortando delete do DB"`

---

## Smoke 3 — Upload duplicado: `overwrite=False` → DUPLICATE; `overwrite=True` → sobrescreve

### Opção A — Via UI

1. Abra o app → selecione um cliente → botão **Arquivos** → **Enviar documentos**.
2. Selecione e envie um arquivo (ex: `teste.pdf`).
3. Tente enviar o mesmo arquivo novamente com a opção padrão (`overwrite=False`):
   - **Resultado esperado:** mensagem de erro/aviso "Arquivo já existe" (DUPLICATE) — o arquivo não é sobrescrito.
4. Selecione o arquivo e use **Enviar (sobrescrever)** (opção que passa `overwrite=True`):
   - **Resultado esperado:** upload conclui com sucesso, arquivo substituído no Storage.

### Opção B — Via código (REPL)

```python
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.modules.uploads.exceptions import UploadDuplicateError
from src.modules.uploads.upload_retry import upload_with_retry

# Simula resposta 409 do Storage
def _mock_upload_409(local_path: str, storage_path: str, mime: str, **kw):
    raise RuntimeError("StorageApiError: duplicate key value (409 Conflict)")

# overwrite=False → deve lançar UploadDuplicateError
try:
    upload_with_retry(
        upload_fn=_mock_upload_409,
        local_path="/tmp/teste.pdf",
        storage_path="org/1/teste.pdf",
        mime_type="application/pdf",
        overwrite=False,
        max_retries=1,
    )
    print("ERRO: deveria ter lançado exceção!")
except UploadDuplicateError:
    print("✅ overwrite=False → UploadDuplicateError (correto)")
except Exception as e:
    print(f"❌ Exceção inesperada: {e}")
```

### Query de validação (tabela de documentos)

```sql
-- Verificar que não houve duplicata na tabela de documentos
SELECT id, title, created_at, updated_at
FROM public.documents   -- ajuste o nome conforme seu schema
WHERE client_id = <CLIENT_ID>
  AND title = 'teste.pdf'
ORDER BY created_at DESC
LIMIT 5;
```

**Comportamento esperado:**
- `overwrite=False`: apenas 1 registro na tabela, sem duplicata.
- `overwrite=True`: registro atualizado (mesmo `id`, `updated_at` mais recente).

---

## Checklist final de Release

- [ ] `pre-commit run --all-files` → EXIT 0
- [ ] `python -m unittest discover -s tests -p "test_*.py"` → 387 OK
- [ ] Migration `20260223_add_audit_trail_to_clients.sql` aplicada
- [ ] `verify_audit_trail_schema.py` → todos ✅
- [ ] Smoke 1: campos `deleted_by`/`restored_by` preenchidos corretamente
- [ ] Smoke 2: storage failure → DB íntegro (cliente permanece no banco)
- [ ] Smoke 3: `overwrite=False` → DUPLICATE; `overwrite=True` → sobrescreve
