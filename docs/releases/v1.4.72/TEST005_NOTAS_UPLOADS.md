# TEST005_NOTAS_UPLOADS.md

**RC Gestor v1.4.72 — Mapeamento de src/modules/uploads/service.py**  
**Data:** 2025-12-20  
**Objetivo:** Documentar API pública do módulo uploads antes de criar TEST-005

---

## 1. Funções Públicas

### 1.1 `upload_folder_to_supabase(folder, client_id, subdir="SIFAP")`

**Assinatura:**
```python
def upload_folder_to_supabase(
    folder: str | Path,
    client_id: int,
    *,
    subdir: str = "SIFAP",
) -> list[dict[str, Any]]
```

**Comportamento:**
- Valida pasta com `validation.ensure_existing_folder()`
- Exige usuário autenticado (`repository.current_user_id()`)
- Resolve org_id automaticamente
- Prepara entries com validação + hash SHA256
- Faz upload para Storage
- Insere registros em `documents` e `document_versions` (DB)
- Atualiza `current_version_id`

**Retorno:** Lista de dicts com `relative_path`, `storage_path`, `document_id`, `version_id`, `size_bytes`, `sha256`, `mime`

**Exceções:**
- `RuntimeError("Usuario nao autenticado...")` se sem user_id

---

### 1.2 `upload_items_for_client(items, cnpj_digits, bucket, ...)`

**Assinatura:**
```python
def upload_items_for_client(
    items: Sequence[UploadItem],
    *,
    cnpj_digits: str,
    bucket: Optional[str] = None,
    supabase_client: Any | None = None,
    subfolder: Optional[str] = None,
    progress_callback: Optional[Callable[[UploadItem], None]] = None,
    client_id: int | None = None,
    org_id: str | None = None,
) -> Tuple[int, list[Tuple[UploadItem, Exception]]]
```

**Comportamento:**
- Cria `SupabaseStorageAdapter` com bucket normalizado
- Delega para `repository.upload_items_with_adapter()`
- Suporta callback de progresso

**Retorno:** `(success_count: int, errors: list[Tuple[UploadItem, Exception]])`

---

### 1.3 `download_and_open_file(remote_key, bucket, mode="external")`

**Assinatura:**
```python
def download_and_open_file(
    remote_key: str,
    *,
    bucket: str | None = None,
    mode: str = "external"
) -> dict[str, Any]
```

**Comportamento:**
- Cria arquivo temporário gerenciado
- Baixa arquivo do Storage
- **Mode "external":** Abre no viewer do SO (os.startfile/open/xdg-open)
- **Mode "internal":** Retorna path para caller abrir (PDF preview)
- Usa `shutil.which()` para resolver comandos (segurança contra injeção)

**Retorno:** Dict com `ok: bool`, `message: str`, `temp_path: str | None`, `error: str | None`

**Exceções:**
- `ValueError` se mode não for "external" ou "internal"

---

### 1.4 `delete_storage_object(remote_key, bucket)`

**Assinatura:**
```python
def delete_storage_object(
    remote_key: str,
    *,
    bucket: str | None = None
) -> bool
```

**Comportamento:**
- Usa `SupabaseStorageAdapter` + context manager
- Delega para `_delete_file()` (adapters.storage.api)
- Log de sucesso/falha

**Retorno:** `True` se deletado, `False` caso contrário (não propaga exceção)

---

### 1.5 `delete_storage_folder(prefix, bucket)`

**Assinatura:**
```python
def delete_storage_folder(
    prefix: str,
    *,
    bucket: str | None = None
) -> dict[str, Any]
```

**Comportamento:**
- Coleta recursivamente todos os arquivos sob o prefixo
- Deleta um por um com `_delete_file()`
- Acumula erros sem interromper (parcial ok)

**Retorno:** Dict com `ok: bool`, `deleted: int`, `errors: list[str]`, `message: str`

---

### 1.6 `download_storage_object(remote_key, destination, bucket)`

**Assinatura:**
```python
def download_storage_object(
    remote_key: str,
    destination: str,
    *,
    bucket: str | None = None
) -> dict[str, Any]
```

**Comportamento:**
- Wrapper para `download_file()` (lazy import de src.modules.forms.view)
- Usa bucket de clientes (padrão: rc-docs)

**Retorno:** Dict com `ok: bool`, `errors: list`, `message: str`, `local_path: str | None`

---

### 1.7 `list_browser_items(prefix, bucket)`

**Assinatura:**
```python
def list_browser_items(
    prefix: str,
    *,
    bucket: str | None = None
) -> Iterable[Any]
```

**Comportamento:**
- Corrige bug de versões >=1.1.86 (prefix caindo como bucket_name)
- Normaliza prefix (strip "/")
- Delega para `list_storage_objects()`

**Retorno:** Iterable de objetos (dicts com `full_path`, `is_folder`, etc.)

---

### 1.8 Helpers de Coleta

**`collect_pdfs_from_folder(dirpath)`**
- Delega para `validation.collect_pdf_items_from_folder()`
- Retorna `list[UploadItem]` (apenas PDFs)

**`build_items_from_files(paths)`**
- Delega para `validation.build_items_from_files()`
- Retorna `list[UploadItem]` (qualquer extensão)

---

## 2. Dataclasses/Tipos

### 2.1 `UploadItem`

```python
@dataclass(slots=True)
class UploadItem:
    path: Path
    relative_path: str
```

---

## 3. Dependências Externas

### 3.1 Storage/Supabase
- `adapters.storage.api` (using_storage_backend, delete_file, download_folder_zip)
- `adapters.storage.supabase_storage.SupabaseStorageAdapter`
- `infra.supabase.storage_helpers.download_bytes`

### 3.2 Repository (src/modules/uploads/repository.py)
- `current_user_id()` → str | None
- `resolve_org_id()` → str
- `build_storage_adapter()` → SupabaseStorageAdapter
- `normalize_bucket()` → str
- `upload_items_with_adapter()` → (int, list[Tuple])
- `ensure_storage_object_absent()` → void
- `upload_local_file()` → void
- `insert_document_record()` → dict
- `insert_document_version_record()` → dict
- `update_document_current_version()` → void

### 3.3 Validation (src/modules/uploads/validation.py)
- `ensure_existing_folder()` → Path
- `prepare_folder_entries()` → list[Entry]
- `collect_pdf_items_from_folder()` → list[UploadItem]
- `build_items_from_files()` → list[UploadItem]
- `build_remote_path()` → str

### 3.4 Helpers (src/modules/uploads/components/helpers.py)
- `_cnpj_only_digits()` → str
- `client_prefix_for_id()` → str
- `format_cnpj_for_display()` → str
- `get_clients_bucket()` → str
- `get_current_org_id()` → str
- `strip_cnpj_from_razao()` → str

### 3.5 Temp Files (src/modules/uploads/temp_files.py)
- `create_temp_file()` → TempFileInfo (com .path)

### 3.6 Hash Utils
- `src.utils.hash_utils.sha256_file()` → str
- Fallback local se importação falhar

### 3.7 Sistema Operacional
- `os.startfile()` (Windows)
- `shutil.which()` → resolver comandos seguros
- `subprocess.Popen()` (macOS/Linux: open/xdg-open)

---

## 4. Contratos/Retornos

### 4.1 Success Paths
- `upload_folder_to_supabase()` → lista de dicts (metadados)
- `upload_items_for_client()` → (success_count, errors_list)
- `delete_storage_object()` → bool (True/False, sem exceção)
- `delete_storage_folder()` → dict com ok/deleted/errors/message
- `download_and_open_file()` → dict com ok/message/temp_path/error
- `download_storage_object()` → dict com ok/errors/message/local_path

### 4.2 Exceções
- `RuntimeError` se usuário não autenticado (upload_folder_to_supabase)
- `ValueError` se mode inválido (download_and_open_file)
- Demais funções: retornam dicts com `ok: False` + erro, SEM propagar exceção

### 4.3 Padrão de Erro
- Funções de delete/download retornam `ok: bool` + `message/error`
- Log detalhado em todos os casos (info, warning, error)
- Erros parciais OK (ex.: delete_storage_folder deleta o que conseguir)

---

## 5. Cenários de Teste (TEST-005)

### A) Upload

**upload_folder_to_supabase:**
1. ✅ Upload com sucesso → retorna lista de metadados
2. ❌ Usuário não autenticado → RuntimeError
3. ❌ Pasta inexistente → ValidationError (de validation.ensure_existing_folder)
4. ✅ Múltiplos arquivos → processa todos

**upload_items_for_client:**
1. ✅ Upload com sucesso → (success_count, [])
2. ⚠️ Alguns arquivos falham → (partial_count, errors_list)
3. ✅ Progress callback chamado por item

### B) Download

**download_and_open_file:**
1. ✅ Mode "external" + Windows → os.startfile chamado
2. ✅ Mode "external" + macOS → shutil.which("open") + subprocess
3. ✅ Mode "external" + Linux → shutil.which("xdg-open") + subprocess
4. ✅ Mode "internal" → retorna temp_path sem abrir
5. ❌ Mode inválido → ValueError
6. ❌ Falha no download → ok=False, error populado
7. ❌ Falha ao abrir viewer → ok=False, temp_path presente
8. ⚠️ Arquivo criado mas download falha → ok=False

**download_storage_object:**
1. ✅ Download com sucesso → ok=True, local_path populado
2. ❌ Falha no download → ok=False, errors populados

### C) Delete

**delete_storage_object:**
1. ✅ Delete com sucesso → True
2. ❌ Falha no delete → False (sem exceção)
3. ⚠️ Exceção do adapter → False (log + sem propagar)

**delete_storage_folder:**
1. ✅ Pasta vazia → ok=True, deleted=0
2. ✅ Pasta com arquivos → ok=True, deleted=N
3. ⚠️ Alguns arquivos falham → ok=False, deleted=partial, errors preenchido
4. ❌ Prefix vazio → ok=False, erro "prefix vazio"
5. ⚠️ Exceção ao coletar keys → ok=False, erro de listagem

### D) Listagem

**list_browser_items:**
1. ✅ Prefix válido → retorna iterable
2. ✅ Prefix com "/" → normaliza antes de listar
3. ✅ Bucket padrão → usa get_clients_bucket()
4. ✅ Bucket explícito → usa o fornecido

### E) Helpers

**collect_pdfs_from_folder:**
1. ✅ Pasta com PDFs → retorna list[UploadItem]
2. ✅ Pasta vazia → retorna []
3. ✅ Pasta com não-PDFs → ignora

**build_items_from_files:**
1. ✅ Paths válidos → retorna list[UploadItem]
2. ✅ Lista vazia → retorna []

---

## 6. Pontos de Mock para Testes

### 6.1 Repository
- `repository.current_user_id()` → "user-123" | None
- `repository.resolve_org_id()` → "org-456"
- `repository.build_storage_adapter()` → Mock adapter
- `repository.normalize_bucket()` → "rc-docs"
- `repository.upload_items_with_adapter()` → (count, errors)
- `repository.ensure_storage_object_absent()` → void
- `repository.upload_local_file()` → void
- `repository.insert_document_record()` → {"id": 1}
- `repository.insert_document_version_record()` → {"id": 1}
- `repository.update_document_current_version()` → void

### 6.2 Validation
- `validation.ensure_existing_folder()` → Path("/tmp/folder")
- `validation.prepare_folder_entries()` → list[Mock entries]
- `validation.collect_pdf_items_from_folder()` → list[UploadItem]
- `validation.build_items_from_files()` → list[UploadItem]
- `validation.build_remote_path()` → "org/client/file.pdf"

### 6.3 Storage API
- `adapters.storage.api.delete_file()` → True | False
- `adapters.storage.api.using_storage_backend()` → context manager
- `adapters.storage.api.download_folder_zip()` → Mock result

### 6.4 Download/List (lazy imports)
- `src.modules.forms.view.download_file()` → {"ok": True, ...}
- `src.modules.forms.view.list_storage_objects()` → [{"full_path": ...}]

### 6.5 Temp Files
- `create_temp_file()` → Mock com .path = "/tmp/file.pdf"

### 6.6 Sistema Operacional
- `sys.platform` → "win32" | "darwin" | "linux"
- `os.startfile()` → void (Windows)
- `shutil.which()` → "/usr/bin/open" | "/usr/bin/xdg-open" | None
- `subprocess.Popen()` → Mock process

### 6.7 Helpers
- `get_clients_bucket()` → "rc-docs"
- `get_current_org_id()` → "org-456"

---

## 7. Observações Importantes

### 7.1 Segurança
- **shutil.which():** Resolve comandos para evitar injeção de PATH
- **subprocess.Popen():** Usa array de args, NUNCA shell=True
- **os.startfile():** Windows-only, caminho controlado pelo app
- **nosec markers:** B404 (import subprocess OK), B606 (os.startfile OK), B603 (subprocess sem shell OK)

### 7.2 Fallback/Parcial OK
- `delete_storage_folder()` deleta o que conseguir, retorna ok=False se houver erros
- `upload_items_for_client()` retorna (success_count, errors_list) - parcial ok
- `delete_storage_object()` retorna False sem propagar exceção

### 7.3 Lazy Imports
- `src.modules.forms.view` importado dentro das funções para evitar ciclos
- `download_file()` e `list_storage_objects()` são wrappers

### 7.4 Bug Fix (v1.1.86)
- `list_browser_items()` corrige bug de prefix caindo como bucket_name
- Agora passa bucket explicitamente para list_storage_objects()

### 7.5 Hash SHA256
- Tenta importar de `src.utils.hash_utils`
- Fallback para implementação local se falhar

---

## 8. Prioridade de Testes

**ALTA:**
- `download_and_open_file()` (3 platforms + 2 modes + error paths)
- `delete_storage_folder()` (recursão + parcial ok + edge cases)
- `upload_folder_to_supabase()` (auth check + validação)

**MÉDIA:**
- `upload_items_for_client()` (callback + partial errors)
- `delete_storage_object()` (error handling sem exceção)
- `download_storage_object()` (wrapper)

**BAIXA:**
- `list_browser_items()` (wrapper com normalização)
- `collect_pdfs_from_folder()` (delegate)
- `build_items_from_files()` (delegate)

---

**Status:** Mapeamento completo. Pronto para criar test_uploads_service_fase62.py.
