# TEST007_NOTAS_UPLOADS_REPOSITORY.md

**RC Gestor v1.4.72 — Notas TEST-007**  
**Módulo:** src/modules/uploads/repository.py  
**Propósito:** Integração com backend (Supabase) para operações de upload e persistência

---

## 1. API Pública (10 funções)

### 1.1 current_user_id() → str | None

**Entrada:** Nenhuma

**Saída:**
- `str`: ID do usuário autenticado (Supabase)
- `None`: Se não autenticado ou erro

**Exceções:** Nenhuma (captura internamente)

**Comportamento:**
```python
response = supabase.auth.get_user()
user = getattr(response, "user", None)
if user and getattr(user, "id", None):
    return user.id
if isinstance(response, dict):
    return (response.get("user") or {}).get("id")
return None
```

**Uso:** Obter user_id para insert de documents.

---

### 1.2 resolve_org_id() → str

**Entrada:** Nenhuma

**Saída:**
- `str`: org_id do usuário (via memberships table) ou fallback env

**Exceções:** Nenhuma (captura internamente)

**Comportamento:**
1. Obtém user_id via `current_user_id()`
2. Se não autenticado: retorna `SUPABASE_DEFAULT_ORG` env ou "unknown-org"
3. Consulta `memberships` table: `SELECT org_id WHERE user_id = ? LIMIT 1`
4. Se erro ou vazio: retorna fallback

**Fallback:** `os.getenv("SUPABASE_DEFAULT_ORG")` → `"unknown-org"`

**Uso:** Determinar org_id para storage paths e metadata.

---

### 1.3 ensure_storage_object_absent(path_key: str) → None

**Entrada:**
- `path_key: str`: chave completa no storage ("org/client/GERAL/file.pdf")

**Saída:** None (levanta exceção se arquivo existe)

**Exceções:**
- `RuntimeError`: Se arquivo já existe no storage

**Comportamento:**
1. Extrai folder_prefix e filename do path_key
2. Lista objetos em folder_prefix via `_storage_list_files()`
3. Para cada item (dict ou str):
   - Se `name == filename` ou `full_path == path_key`: **levanta RuntimeError**

**Uso:** Validação pré-upload para evitar sobrescrever arquivos existentes.

---

### 1.4 upload_local_file(local_path, storage_path, mime_type) → None

**Entrada:**
- `local_path: Path | str`: caminho local do arquivo
- `storage_path: str`: chave de destino no storage
- `mime_type: str`: Content-Type

**Saída:** None (sucesso silencioso)

**Exceções:** Propaga exceções de `_storage_upload_file()`

**Comportamento:**
```python
_storage_upload_file(str(local_path), storage_path, mime_type)
```

**Dependências:**
- `adapters.storage.api.upload_file` (alias `_storage_upload_file`)

**Uso:** Upload direto sem metadata persistence.

---

### 1.5 insert_document_record(*, client_id, title, mime_type, user_id) → dict

**Entrada (keyword-only):**
- `client_id: int`: ID do cliente
- `title: str`: título do documento
- `mime_type: str`: tipo MIME
- `user_id: str`: ID do usuário que fez upload

**Saída:**
- `dict[str, Any]`: representação do documento inserido

**Exceções:**
- `RuntimeError`: Se RLS bloqueia o INSERT (response.data vazio)

**Comportamento:**
```python
response = exec_postgrest(
    supabase.table("documents").insert({
        "client_id": int(client_id),
        "title": title,
        "kind": mime_type,
        "user_id": user_id,
    }, returning="representation")
)
if not response.data:
    raise RuntimeError(f"INSERT bloqueado por RLS em 'documents' para arquivo: {title}")
return response.data[0]
```

**Dependências:**
- `infra.supabase_client.exec_postgrest`
- `infra.supabase_client.supabase`

**Uso:** Criar entrada na tabela documents.

---

### 1.6 insert_document_version_record(*, document_id, storage_path, size_bytes, sha_value, uploaded_by) → dict

**Entrada (keyword-only):**
- `document_id: int`: ID do documento pai
- `storage_path: str`: chave no storage
- `size_bytes: int`: tamanho do arquivo
- `sha_value: str`: SHA256 hash
- `uploaded_by: str`: user_id do uploader

**Saída:**
- `dict[str, Any]`: representação da versão inserida

**Exceções:**
- `RuntimeError`: Se RLS bloqueia o INSERT

**Comportamento:**
```python
response = exec_postgrest(
    supabase.table("document_versions").insert({
        "document_id": document_id,
        "storage_path": storage_path,
        "size_bytes": size_bytes,
        "sha256": sha_value,
        "uploaded_by": uploaded_by,
    }, returning="representation")
)
if not response.data:
    raise RuntimeError(f"INSERT bloqueado por RLS em 'document_versions' para arquivo: {storage_path}")
return response.data[0]
```

**Uso:** Criar versão do documento.

---

### 1.7 update_document_current_version(document_id, version_id) → None

**Entrada:**
- `document_id: int`: ID do documento
- `version_id: int`: ID da versão atual

**Saída:** None

**Exceções:** Propaga exceções de `exec_postgrest()`

**Comportamento:**
```python
exec_postgrest(
    supabase.table("documents")
    .update({"current_version": version_id})
    .eq("id", document_id)
)
```

**Uso:** Atualizar referência current_version após criar nova versão.

---

### 1.8 normalize_bucket(value: str | None) → str

**Entrada:**
- `value: str | None`: nome do bucket ou None

**Saída:**
- `str`: nome do bucket (fallback: "rc-docs")

**Exceções:** Nenhuma

**Comportamento:**
```python
raw = (value or os.getenv("SUPABASE_BUCKET") or "rc-docs").strip()
return raw or "rc-docs"
```

**Fallbacks:**
1. `value` fornecido
2. `SUPABASE_BUCKET` env
3. `"rc-docs"` hardcoded

**Uso:** Normalizar nome do bucket antes de criar adapter.

---

### 1.9 build_storage_adapter(*, bucket, supabase_client=None) → SupabaseStorageAdapter

**Entrada (keyword-only):**
- `bucket: str`: nome do bucket
- `supabase_client: Any | None`: cliente Supabase (default: global `supabase`)

**Saída:**
- `SupabaseStorageAdapter`: instância configurada

**Exceções:** Nenhuma (construtor pode levantar)

**Comportamento:**
```python
return SupabaseStorageAdapter(
    client=supabase_client or supabase,
    bucket=bucket,
    overwrite=False,  # SEMPRE False (proteção)
)
```

**Uso:** Factory para criar adapter com overwrite=False.

---

### 1.10 upload_items_with_adapter(...) → Tuple[int, list[Tuple[_TUploadItem, Exception]]]

**Entrada:**
- `adapter: SupabaseStorageAdapter`: adapter configurado
- `items: Sequence[_TUploadItem]`: lista de items a fazer upload
- `cnpj_digits: str`: CNPJ do cliente (fallback)
- `subfolder: str | None`: subpasta no storage
- `progress_callback: Callable | None` (keyword-only): callback de progresso
- `remote_path_builder: Callable` (keyword-only): função para montar remote_key
- `client_id: int | None` (keyword-only): ID do cliente
- `org_id: str | None` (keyword-only): ID da organização

**Saída:**
- `Tuple[int, list[Tuple[item, Exception]]]`:
  - `int`: número de uploads bem-sucedidos
  - `list`: lista de (item, exceção) para falhas

**Exceções:** Nenhuma (captura internamente)

**Comportamento:**
1. Para cada item:
   - Chama `progress_callback(item)` se fornecido
   - Monta `remote_key` via `remote_path_builder(cnpj_digits, item.relative_path, subfolder, client_id=..., org_id=...)`
   - Log debug do upload
   - Chama `upload_with_retry(adapter.upload_file, local_path, remote_key, content_type="application/pdf", max_retries=DEFAULT_MAX_RETRIES)`
   - Se sucesso: `ok += 1`, log info
   - Se exceção:
     - Classifica com `classify_upload_exception(exc)`
     - Se é duplicate (409): incrementa `duplicates`, log info, **continua** (não adiciona em failures)
     - Caso contrário: log error, adiciona em `failures`
2. Retorna `(ok, failures)`

**Retry Mechanism:**
- Usa `upload_with_retry()` de `upload_retry` module
- `DEFAULT_MAX_RETRIES` configurável
- Classifica exceções com `classify_upload_exception()`

**Tratamento de Duplicatas:**
- Se erro contém "duplicate" (case-insensitive) no `detail`: **não é falha**
- Incrementa contador interno `duplicates` (não retornado)
- Log info: "Upload SKIPPED (duplicate)"

**Uso:** Pipeline principal de upload batch com retry e tratamento de erros.

---

## 2. Dependências Externas

### 2.1 Supabase Client
- `infra.supabase_client.supabase`: cliente global Supabase
- `infra.supabase_client.exec_postgrest`: wrapper para queries

**Métodos usados:**
- `supabase.auth.get_user()` → response com user.id
- `supabase.table("memberships").select(...).eq(...).limit(1)` → query
- `supabase.table("documents").insert(..., returning="representation")` → insert
- `supabase.table("document_versions").insert(...)` → insert
- `supabase.table("documents").update(...).eq(...)` → update

### 2.2 Storage Adapters
- `adapters.storage.api.list_files` (alias `_storage_list_files`)
- `adapters.storage.api.upload_file` (alias `_storage_upload_file`)
- `adapters.storage.supabase_storage.SupabaseStorageAdapter`

**Métodos do adapter:**
- `adapter.upload_file(local_path, remote_key, content_type="application/pdf")`

### 2.3 Retry Mechanism
- `src.modules.uploads.upload_retry.upload_with_retry`
- `src.modules.uploads.upload_retry.classify_upload_exception`
- `src.modules.uploads.upload_retry.DEFAULT_MAX_RETRIES`

### 2.4 Environment Variables
- `SUPABASE_DEFAULT_ORG`: fallback org_id
- `SUPABASE_BUCKET`: fallback bucket name

---

## 3. Cenários de Teste (TEST-007)

### 3.1 current_user_id
- ✅ Usuário autenticado → retorna user.id
- ✅ Usuário não autenticado → retorna None
- ✅ Exceção no auth.get_user() → retorna None (sem propagar)
- ✅ Response é dict (formato alternativo) → extrai user.id

### 3.2 resolve_org_id
- ✅ Usuário autenticado + memberships com org_id → retorna org_id
- ✅ Usuário não autenticado → retorna env fallback ou "unknown-org"
- ✅ Memberships vazio → retorna fallback
- ✅ Exceção na query → retorna fallback
- ✅ Env SUPABASE_DEFAULT_ORG definido → usa env como fallback

### 3.3 ensure_storage_object_absent
- ✅ Arquivo não existe → não levanta exceção
- ❌ Arquivo existe (name match) → RuntimeError
- ❌ Arquivo existe (full_path match) → RuntimeError
- ✅ Item é dict com name/full_path
- ✅ Item é string

### 3.4 upload_local_file
- ✅ Upload bem-sucedido → não levanta exceção
- ❌ Upload falha → propaga exceção de _storage_upload_file

### 3.5 insert_document_record
- ✅ Insert bem-sucedido → retorna dict
- ❌ RLS bloqueia (response.data vazio) → RuntimeError
- ✅ Converte client_id para int

### 3.6 insert_document_version_record
- ✅ Insert bem-sucedido → retorna dict
- ❌ RLS bloqueia → RuntimeError

### 3.7 update_document_current_version
- ✅ Update bem-sucedido → não levanta exceção
- ❌ Update falha → propaga exceção

### 3.8 normalize_bucket
- ✅ value fornecido → retorna value
- ✅ value=None + env definido → retorna env
- ✅ value=None + env vazio → retorna "rc-docs"
- ✅ Strip whitespace

### 3.9 build_storage_adapter
- ✅ Cria adapter com bucket fornecido
- ✅ overwrite=False sempre
- ✅ supabase_client default → usa global supabase
- ✅ supabase_client fornecido → usa fornecido

### 3.10 upload_items_with_adapter
- ✅ Todos os items bem-sucedidos → (count, [])
- ✅ 1 item falha → (count-1, [(item, exc)])
- ✅ Duplicate error (409) → não adiciona em failures, continua
- ✅ Chama progress_callback para cada item
- ✅ Usa remote_path_builder com client_id/org_id keywords
- ✅ Log debug/info/error apropriados
- ✅ Usa upload_with_retry (max_retries)
- ✅ Classifica exceções com classify_upload_exception

---

## 4. Isolamento (Mocks Necessários)

### 4.1 Mock de Supabase Client
**current_user_id:**
```python
mock_get_user = Mock(return_value=Mock(user=Mock(id="user-123")))
monkeypatch.setattr("infra.supabase_client.supabase.auth.get_user", mock_get_user)
```

**resolve_org_id:**
```python
mock_exec_postgrest = Mock(return_value=Mock(data=[{"org_id": "org-456"}]))
monkeypatch.setattr("src.modules.uploads.repository.exec_postgrest", mock_exec_postgrest)
```

**insert/update:**
```python
mock_exec_postgrest = Mock(return_value=Mock(data=[{"id": 1, "title": "doc.pdf"}]))
```

### 4.2 Mock de Storage API
**ensure_storage_object_absent:**
```python
mock_list_files = Mock(return_value=[{"name": "file.pdf", "full_path": "org/client/file.pdf"}])
monkeypatch.setattr("src.modules.uploads.repository._storage_list_files", mock_list_files)
```

**upload_local_file:**
```python
mock_upload_file = Mock(return_value=None)
monkeypatch.setattr("src.modules.uploads.repository._storage_upload_file", mock_upload_file)
```

### 4.3 Mock de Adapter
**upload_items_with_adapter:**
```python
mock_adapter = Mock(spec=SupabaseStorageAdapter)
mock_adapter.upload_file = Mock(return_value=None)  # ou side_effect para falhas
```

### 4.4 Mock de Retry/Classify
**upload_items_with_adapter:**
```python
mock_upload_retry = Mock(return_value=None)
monkeypatch.setattr("src.modules.uploads.repository.upload_with_retry", mock_upload_retry)

mock_classify = Mock(side_effect=lambda exc: exc)
monkeypatch.setattr("src.modules.uploads.repository.classify_upload_exception", mock_classify)
```

### 4.5 Mock de Environment Variables
```python
monkeypatch.setenv("SUPABASE_DEFAULT_ORG", "test-org")
monkeypatch.setenv("SUPABASE_BUCKET", "test-bucket")
```

---

## 5. Edge Cases

### 5.1 Autenticação
- ✅ current_user_id() sem crash em exceção
- ✅ resolve_org_id() fallback em múltiplos cenários

### 5.2 RLS (Row Level Security)
- ❌ INSERT bloqueado → RuntimeError com mensagem clara
- ✅ Testa ambos: documents e document_versions

### 5.3 Duplicatas
- ✅ upload_items_with_adapter trata 409 Duplicate como "já existe", não falha
- ✅ Verifica `error_detail` com "duplicate" (case-insensitive)
- ✅ Não adiciona em failures, continua processamento

### 5.4 Retry Mechanism
- ✅ upload_with_retry chamado com DEFAULT_MAX_RETRIES
- ✅ classify_upload_exception usado para tratar erros

### 5.5 Paths e Remote Keys
- ✅ remote_path_builder chamado com keywords client_id/org_id
- ✅ Cast para Any para contornar type checking

### 5.6 Logging
- ✅ Debug: upload iniciado com detalhes
- ✅ Info: sucesso ou duplicate skipped
- ✅ Error: falha com repr da exceção

---

## 6. Estrutura de Testes Sugerida

```python
# tests/unit/modules/uploads/test_uploads_repository_fase64.py

import pytest
from unittest.mock import Mock
from src.modules.uploads.repository import (
    current_user_id,
    resolve_org_id,
    ensure_storage_object_absent,
    upload_local_file,
    insert_document_record,
    insert_document_version_record,
    update_document_current_version,
    normalize_bucket,
    build_storage_adapter,
    upload_items_with_adapter,
)

class TestCurrentUserId:
    # 4 testes

class TestResolveOrgId:
    # 5 testes

class TestEnsureStorageObjectAbsent:
    # 4 testes

class TestUploadLocalFile:
    # 2 testes

class TestInsertDocumentRecord:
    # 3 testes

class TestInsertDocumentVersionRecord:
    # 2 testes

class TestUpdateDocumentCurrentVersion:
    # 2 testes

class TestNormalizeBucket:
    # 4 testes

class TestBuildStorageAdapter:
    # 3 testes

class TestUploadItemsWithAdapter:
    # 8 testes
```

**Total estimado:** ~37 testes

---

## 7. Observações de Segurança

### 7.1 Proteção contra Overwrite
- ✅ `build_storage_adapter()` sempre usa `overwrite=False`
- ✅ `ensure_storage_object_absent()` valida pré-upload

### 7.2 RLS Enforcement
- ✅ INSERT/UPDATE podem falhar por RLS (RuntimeError com mensagem clara)
- ✅ Não bypassa segurança do backend

### 7.3 Error Handling
- ✅ `current_user_id()` não propaga exceções (graceful degradation)
- ✅ `resolve_org_id()` fallback em múltiplos cenários
- ✅ `upload_items_with_adapter()` coleta falhas sem parar processamento

---

## 8. Performance e Reliability

### 8.1 Retry Mechanism
- ✅ `upload_with_retry()` lida com erros transientes
- ✅ `DEFAULT_MAX_RETRIES` configurável
- ✅ `classify_upload_exception()` trata diferentes tipos de erro

### 8.2 Batch Processing
- ✅ `upload_items_with_adapter()` processa múltiplos items
- ✅ Coleta falhas sem parar processamento
- ✅ Retorna count de sucessos + lista de falhas

### 8.3 Progress Tracking
- ✅ `progress_callback` opcional para UI updates
- ✅ Chamado antes de cada upload

---

**Próximo passo:** Criar test_uploads_repository_fase64.py
