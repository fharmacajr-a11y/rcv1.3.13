# TEST006_NOTAS_UPLOADS_VALIDATION.md

**RC Gestor v1.4.72 — Notas TEST-006**  
**Módulo:** src/modules/uploads/validation.py  
**Propósito:** Validação, normalização e preparação de arquivos para upload

---

## 1. API Pública (9 funções/classes)

### 1.1 Classe: PreparedUploadEntry

**Dataclass (slots=True):**
```python
@dataclass(slots=True)
class PreparedUploadEntry:
    path: Path
    relative_path: str
    storage_path: str
    safe_relative_path: str
    size_bytes: int
    sha256: str
    mime_type: str
```

**Propósito:** Container de metadados para um arquivo a ser persistido no Supabase Storage.

---

### 1.2 ensure_existing_folder(folder: str | Path) → Path

**Entrada:**
- `folder`: string ou Path do diretório

**Saída:**
- Path resolvido (absolute)

**Exceções:**
- `FileNotFoundError`: Se pasta não existe

**Comportamento:**
```python
base = Path(folder).resolve()
if not base.exists():
    raise FileNotFoundError(f"Pasta nao encontrada: {base}")
return base
```

**Uso:** Validar diretório antes de processar uploads.

---

### 1.3 iter_local_files(base: Path) → Iterator[Path]

**Entrada:**
- `base`: Path do diretório

**Saída:**
- Iterator com todos os arquivos recursivamente

**Exceções:** Nenhuma (itera vazio se pasta vazia)

**Comportamento:**
```python
for item in base.rglob("*"):
    if item.is_file():
        yield item
```

**Uso:** Iterar sobre todos os arquivos de uma pasta recursivamente.

---

### 1.4 guess_mime(path: Path | str) → str

**Entrada:**
- `path`: arquivo local

**Saída:**
- MIME type (fallback: "application/octet-stream")

**Exceções:** Nenhuma

**Comportamento:**
```python
mime_type, _ = mimetypes.guess_type(str(path))
return mime_type or "application/octet-stream"
```

**Uso:** Determinar Content-Type para upload.

---

### 1.5 normalize_relative_path(relative: str) → str

**Entrada:**
- `relative`: path relativo (pode ter `\`, `..`, `./`)

**Saída:**
- Path normalizado (sem `..`, sem leading `/`, só `/` como separador)

**Exceções:** Nenhuma

**Comportamento:**
```python
rel = relative.replace("\\", "/")
rel = os.path.normpath(rel).replace("\\", "/")
rel = rel.replace("..", "").lstrip("./")
return rel.strip("/")
```

**Segurança:** Remove path traversal (`..`), normaliza separadores.

**Exemplos:**
- `"pasta\\arquivo.pdf"` → `"pasta/arquivo.pdf"`
- `"../etc/passwd"` → `"etc/passwd"`
- `"./pasta/./arquivo.pdf"` → `"pasta/arquivo.pdf"`

---

### 1.6 prepare_folder_entries(base, client_id, subdir, org_id, hash_func) → list[PreparedUploadEntry]

**Entrada:**
- `base: Path`: diretório local
- `client_id: int`: ID do cliente
- `subdir: str`: subdiretório no storage ("GERAL", "ANVISA", etc.)
- `org_id: str`: ID da organização
- `hash_func: Callable[[Path | str], str]`: função para calcular SHA256

**Saída:**
- Lista de `PreparedUploadEntry` com metadados completos

**Exceções:** Nenhuma (lista vazia se pasta vazia)

**Comportamento:**
1. Itera recursivamente em `base` com `iter_local_files()`
2. Para cada arquivo:
   - Calcula `relative_path` (path.relative_to(base))
   - Extrai dir_segments e filename com `_split_relative_path()`
   - Monta `storage_path` com `make_storage_key(org_id, client_id, subdir, ...)`
   - Sanitiza dir_segments com `_sanitize_directory_segments()`
   - Sanitiza filename com `storage_slug_filename()`
   - Calcula `size_bytes`, `sha256` (via hash_func), `mime_type`
   - Cria `PreparedUploadEntry`

**Dependências:**
- `make_storage_key()` (src.core.storage_key)
- `storage_slug_part()` (sanitização de dir)
- `storage_slug_filename()` (sanitização de filename)
- `hash_func` (normalmente sha256_file)

**Uso:** Pipeline de validação antes de upload real.

---

### 1.7 collect_pdf_items_from_folder(dirpath, factory) → list[_TItem]

**Entrada:**
- `dirpath: str`: caminho do diretório
- `factory: Callable[[Path, str], _TItem]`: função factory para criar items

**Saída:**
- Lista de items (tipo genérico `_TItem`, geralmente `UploadItem`)

**Exceções:** Nenhuma

**Comportamento:**
1. Verifica se `dirpath` é diretório válido (senão retorna [])
2. Itera recursivamente em busca de arquivos `.pdf`
3. Para cada PDF:
   - Calcula `relative_path` (as_posix)
   - Adiciona tupla `(relative.lower(), relative, path)` para ordenação
4. Ordena por lowercase
5. Chama `factory(path, relative)` para cada arquivo

**Filtros:**
- Ignora não-arquivos (pastas)
- Ignora extensões != `.pdf`

**Uso:** Coletar PDFs de uma pasta para upload batch.

---

### 1.8 build_items_from_files(paths, factory) → list[_TItem]

**Entrada:**
- `paths: Sequence[str]`: lista de caminhos absolutos
- `factory: Callable[[Path, str], _TItem]`: função factory

**Saída:**
- Lista de items (ordenada por filename lowercase)

**Exceções:** Nenhuma

**Comportamento:**
1. Para cada path em `paths`:
   - Se extensão != `.pdf`: ignora
   - Adiciona tupla `(path.name.lower(), path.name, path)` para ordenação
2. Ordena por filename lowercase
3. Chama `factory(path, relative)` com `relative = path.name`

**Diferença de collect_pdf_items_from_folder:**
- Não busca recursivamente
- Usa `path.name` como relative_path (sem diretórios)

**Uso:** Upload de lista explícita de arquivos (drag-and-drop, seleção múltipla).

---

### 1.9 build_remote_path(cnpj_digits, relative_path, subfolder, *, client_id, org_id) → str

**Entrada:**
- `cnpj_digits: str`: CNPJ do cliente (fallback)
- `relative_path: str`: caminho relativo do arquivo
- `subfolder: str | None`: subdiretório ("GERAL", etc.)
- `client_id: int | None` (keyword-only): ID do cliente
- `org_id: str | None` (keyword-only): ID da organização

**Saída:**
- Storage key completo (string)

**Exceções:** Nenhuma

**Comportamento:**

**Modo 1 (client_id e org_id fornecidos):**
```python
# Estrutura: {org_id}/{client_id}/GERAL/{subfolder?}/{relative_path}
prefix = client_prefix_for_id(client_id, org_id)
parts = [prefix, "GERAL"]
if subfolder:
    parts.append(subfolder.strip("/"))
parts.append(normalize_relative_path(relative_path))
```

**Modo 2 (fallback - apenas cnpj_digits):**
```python
# Estrutura: {cnpj_digits}/{subfolder?}/{relative_path}
parts = [cnpj_digits]
if subfolder:
    parts.append(subfolder.strip("/"))
parts.append(normalize_relative_path(relative_path))
```

**Normalização:** Junta com `/`, remove leading/trailing `/` de cada segment.

**Dependências:**
- `client_prefix_for_id()` (src.modules.uploads.components.helpers)
- `normalize_relative_path()` (próprio módulo)

**Uso:** Montar chave de storage para download/delete.

---

## 2. Funções Privadas (helpers)

### 2.1 _split_relative_path(relative_path, fallback_name) → (list[str], str)

**Propósito:** Separar diretórios e filename, com fallback se path vazio.

**Exemplo:**
- `("pasta/sub/arquivo.pdf", "default.pdf")` → `(["pasta", "sub"], "arquivo.pdf")`
- `("", "default.pdf")` → `([], "default.pdf")`

---

### 2.2 _sanitize_directory_segments(dir_segments) → list[str]

**Propósito:** Sanitizar cada segment de diretório usando `storage_slug_part()`.

**Comportamento:**
- Remove caracteres inválidos
- Remove segments vazios após sanitização

---

## 3. Dependências Externas

### 3.1 Módulos stdlib
- `mimetypes.guess_type()` (MIME detection)
- `os.path.normpath()` (normalização de paths)
- `pathlib.Path` (operações de FS)

### 3.2 Módulos internos
- `src.core.storage_key`:
  - `make_storage_key()`: monta chave de storage
  - `storage_slug_part()`: sanitiza segment de diretório
  - `storage_slug_filename()`: sanitiza filename
- `src.modules.uploads.components.helpers`:
  - `client_prefix_for_id()`: monta prefix org/client

### 3.3 Hash Function
- `hash_func: Callable[[Path | str], str]`: Normalmente `sha256_file()` de `src.helpers.hash_utils`

---

## 4. Cenários de Teste (TEST-006)

### 4.1 ensure_existing_folder
- ✅ Path válido (tmp_path) → retorna Path resolvido
- ❌ Path inexistente → FileNotFoundError
- ❌ Path apontando para arquivo → FileNotFoundError (não é diretório)

### 4.2 iter_local_files
- ✅ Pasta com 2 arquivos → itera ambos
- ✅ Pasta com subdiretório → itera recursivamente
- ✅ Pasta vazia → iterator vazio

### 4.3 guess_mime
- ✅ arquivo.pdf → "application/pdf"
- ✅ arquivo.jpg → "image/jpeg"
- ✅ arquivo.txt → "text/plain"
- ✅ arquivo.xyz (desconhecido) → "application/octet-stream"

### 4.4 normalize_relative_path
- ✅ `"pasta\\arquivo.pdf"` → `"pasta/arquivo.pdf"` (normaliza backslash)
- ✅ `"../etc/passwd"` → `"etc/passwd"` (remove path traversal)
- ✅ `"./pasta/./arquivo.pdf"` → `"pasta/arquivo.pdf"` (remove ./)
- ✅ `"/pasta/arquivo.pdf"` → `"pasta/arquivo.pdf"` (remove leading /)
- ✅ `"pasta/arquivo.pdf/"` → `"pasta/arquivo.pdf"` (remove trailing /)

### 4.5 prepare_folder_entries
- ✅ Pasta com 2 PDFs → 2 entries com storage_path, sha256, size, mime
- ✅ Pasta com subdiretório → relative_path preserva estrutura
- ✅ Monta storage_path correto: `{org_id}/{client_id}/{subdir}/{relative}`
- ✅ Sanitiza filename e dir_segments
- ✅ Chama hash_func para cada arquivo
- ✅ Pasta vazia → []

### 4.6 collect_pdf_items_from_folder
- ✅ Pasta com pdf + txt → retorna só pdf
- ✅ Pasta vazia → []
- ✅ Diretório não existe → []
- ✅ Path aponta para arquivo (não dir) → []
- ✅ Múltiplos PDFs → ordena por lowercase

### 4.7 build_items_from_files
- ✅ Lista vazia → []
- ✅ Lista com PDFs → items com relative_path = filename
- ✅ Lista com PDF + TXT → filtra só PDF
- ✅ Múltiplos PDFs → ordena por filename lowercase

### 4.8 build_remote_path
- ✅ Modo 1 (client_id + org_id): `{org_id}/{client_id}/GERAL/{subfolder}/{relative}`
- ✅ Modo 2 (fallback): `{cnpj_digits}/{subfolder}/{relative}`
- ✅ subfolder=None → omite subfolder
- ✅ relative_path com `\` → normaliza para `/`
- ✅ relative_path com `..` → remove path traversal

---

## 5. Isolamento (Mocks Necessários)

### 5.1 Sem FS Real
- ✅ **tmp_path fixture:** criar arquivos pequenos para teste
- ✅ **monkeypatch:** não necessário (usa tmp_path real)

### 5.2 Mock de Hash Function
- ✅ `hash_func = lambda p: "fake-sha256-hash"` (para prepare_folder_entries)
- ✅ Evita calcular SHA256 real (performance)

### 5.3 Mock de Funções Externas
- ✅ `make_storage_key()`: pode mockar para testar storage_path
- ✅ `client_prefix_for_id()`: mockar para retornar "org123/client456"
- ✅ `storage_slug_part()`, `storage_slug_filename()`: usar real ou mockar

### 5.4 Mock de Factory
- ✅ `factory = lambda path, rel: (path, rel)` (collect_pdf, build_items)
- ✅ Simplifica teste sem criar UploadItem real

---

## 6. Edge Cases

### 6.1 Paths Maliciosos
- ✅ Path traversal (`../../../etc/passwd`) → sanitizado
- ✅ Leading `/` → removido
- ✅ Backslashes mistos → normalizados para `/`

### 6.2 Arquivos Especiais
- ✅ Arquivo sem extensão → mime: "application/octet-stream"
- ✅ Arquivo oculto (`.gitignore`) → se PDF, deve processar

### 6.3 Estruturas Vazias
- ✅ Pasta vazia → prepare_folder_entries retorna []
- ✅ Lista vazia de paths → build_items_from_files retorna []

### 6.4 Ordenação
- ✅ PDFs com nomes unicode → ordena por lowercase corretamente
- ✅ PDFs com números → ordena lexicograficamente (não numérico)

---

## 7. Dependências para Mock

```python
# Funções a mockar em testes:
from src.core.storage_key import (
    make_storage_key,          # → "org/client/GERAL/subdir/file.pdf"
    storage_slug_part,         # → sanitiza dir segment
    storage_slug_filename,     # → sanitiza filename
)
from src.modules.uploads.components.helpers import (
    client_prefix_for_id,      # → "org123/client456"
)
```

**Hash function:**
```python
# Normalmente vem de src.helpers.hash_utils.sha256_file
# Para testes: lambda p: "fake-sha256"
```

---

## 8. Observações de Implementação

### 8.1 Segurança
- ✅ `normalize_relative_path()` remove `..` para evitar path traversal
- ✅ `storage_slug_part()` e `storage_slug_filename()` sanitizam caracteres perigosos

### 8.2 Performance
- ✅ `iter_local_files()` usa generator (não carrega tudo na memória)
- ✅ `prepare_folder_entries()` processa arquivos sequencialmente

### 8.3 Compatibilidade
- ✅ Suporta Windows (`\`) e Unix (`/`) paths
- ✅ Fallback de MIME type para "application/octet-stream"

---

## 9. Estrutura de Testes Sugerida

```python
# tests/unit/modules/uploads/test_uploads_validation_fase63.py

import pytest
from pathlib import Path
from src.modules.uploads.validation import (
    ensure_existing_folder,
    iter_local_files,
    guess_mime,
    normalize_relative_path,
    prepare_folder_entries,
    collect_pdf_items_from_folder,
    build_items_from_files,
    build_remote_path,
    PreparedUploadEntry,
)

class TestEnsureExistingFolder:
    # 3 testes

class TestIterLocalFiles:
    # 3 testes

class TestGuessMime:
    # 4 testes

class TestNormalizeRelativePath:
    # 5 testes

class TestPrepareFolderEntries:
    # 6 testes

class TestCollectPdfItemsFromFolder:
    # 5 testes

class TestBuildItemsFromFiles:
    # 4 testes

class TestBuildRemotePath:
    # 5 testes
```

**Total estimado:** ~35 testes

---

**Próximo passo:** Criar test_uploads_validation_fase63.py
