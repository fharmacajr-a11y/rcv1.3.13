# Relatório de Remoção — Infraestrutura Local de Subpastas/Pastas

**Versão:** 1.5.99  
**Data:** 2025-06-18  
**Escopo:** remoção parcial da infra legado de sistema de arquivos local,
preservando tudo que é cloud-facing (Supabase Storage).

---

## 1. RESUMO DO QUE FOI REMOVIDO

Toda a infraestrutura que criava, migrava e lia pastas de clientes **no disco
local** foi removida. Desde que `CLOUD_ONLY` (via `env_bool("RC_NO_LOCAL_FS",
True)`) passou a ser `True` por padrão, essas funções eram no-ops em produção.

### Funções removidas

| Módulo | Função/Constante | Motivo |
|---|---|---|
| `subpastas_config.py` | `load_subpastas_config()`, `_flatten()`, `_norm()` | Liam `subpastas.yml` para o disco local |
| `path_utils.py` | `ensure_dir()`, `safe_copy()`, `open_folder()`, `ensure_subtree()`, `ensure_subpastas()` + helpers `_split_pathlike`, `_spec_name`, `_spec_children` | Operações exclusivas do FS local |
| `bytes_utils.py` | `MARKER_NAME`, `write_marker()`, `read_marker_id()`, `migrate_legacy_marker()`, `get_marker_updated_at()` | Leitura/escrita de `.rc_client_id` no disco |
| `clientes_service.py` | `_pasta_do_cliente()`, `_migrar_pasta_se_preciso()` | Criação/migração de diretório do cliente no disco |
| `app_core.py` | `dir_base_cliente_from_pk()`, `_ensure_live_folder_ready()`, `MARKER_NAME` constante | Path resolution e bootstrap de pasta local |

### Imports mortos removidos

| Arquivo | Imports removidos |
|---|---|
| `subpastas_config.py` | `yaml`, `logging`, `pathlib.Path`, `typing.Any` |
| `bytes_utils.py` | `from src.config.paths import CLOUD_ONLY` |
| `clientes_service.py` | `shutil`, `os`, `safe_base_from_fields`, `DOCS_DIR`, `ensure_subpastas`, `write_marker` |
| `app_core.py` | `CLOUD_ONLY`, `DOCS_DIR` (try/except), `safe_base_from_fields` (try/except) |
| `file_utils/__init__.py` | Todos os re-exports de `path_utils` e funções de marker |

---

## 2. O QUE FOI PRESERVADO

Todos os componentes **cloud-facing** permanecem intactos:

| Componente | Localização | Uso |
|---|---|---|
| `MANDATORY_SUBPASTAS` | `subpastas_config.py` | Tupla de nomes obrigatórios para Supabase Storage |
| `get_mandatory_subpastas()` | `subpastas_config.py` | Retorna a tupla (usada por uploads/SubpastaDialog) |
| `join_prefix()` | `subpastas_config.py` | Monta prefixos de path no storage |
| `sanitize_subfolder_name()` | `subpastas_config.py` | Normaliza nomes de subpastas |
| `list_storage_subfolders()` | `subpastas_config.py` | Lista subpastas via Supabase |
| `SubpastaDialog` | `client_subfolder_prompt.py` | Dialog de escolha de subpasta (V2) |
| `read_pdf_text()` | `bytes_utils.py` | Leitura de PDF (cloud e local) |
| `find_cartao_cnpj_pdf()` | `bytes_utils.py` | Busca de cartão CNPJ em PDF |
| `list_and_classify_pdfs()` | `bytes_utils.py` | Classificação de PDFs |
| `format_datetime()` | `bytes_utils.py` | Formatação de datas |
| `NO_FS` | `app_core.py` | Flag importada por `main_window_services.py` |
| `salvar_cliente()` | `clientes_service.py` | Preservado; retorno simplificado para `(pk, "")` |
| `ensure_directories()` | `paths.py` | Bootstrap de diretórios do app (não é de clientes) |

### Fluxos intactos

- **V2 — Arquivos do Cliente**: upload, download, preview, lixeira — tudo via Supabase Storage
- **SubpastaDialog**: prompt de escolha de subpasta (cloud)
- **CNPJ/telefone/validações**: sem alterações
- **Treeview de clientes**: sem alterações
- **Notes (bloco de notas)**: sem alterações

---

## 3. ARQUIVOS ALTERADOS (7)

| # | Arquivo | Ação |
|---|---|---|
| 1 | `src/utils/subpastas_config.py` | Removeu `load_subpastas_config`, `_flatten`, `_norm`, imports de yaml/logging/Path/Any |
| 2 | `src/utils/file_utils/path_utils.py` | Esvaziou: removeu todas as 5 funções + helpers; mantém docstring + `__all__ = []` |
| 3 | `src/utils/file_utils/bytes_utils.py` | Removeu `MARKER_NAME`, 4 funções de marker, import de `CLOUD_ONLY`; atualizou `__all__` |
| 4 | `src/utils/file_utils/__init__.py` | Removeu re-exports mortos de path_utils e bytes_utils |
| 5 | `src/core/services/clientes_service.py` | Removeu 2 funções, 6 imports, 2 atribuições `old_path`; retorno `(pk, "")` |
| 6 | `src/core/app_core.py` | Removeu 2 funções, imports mortos, `MARKER_NAME`; atualizou `__all__` |
| 7 | `src/core/services/__init__.py` | Removeu `path_resolver` de `__all__` e TYPE_CHECKING |
| 8 | `tests/test_p1_regression.py` | Removeu mocks órfãos (`ensure_subpastas`, `write_marker`) dos stubs |

---

## 4. ARQUIVOS REMOVIDOS (5)

| # | Arquivo | Linhas | Conteúdo |
|---|---|---|---|
| 1 | `subpastas.yml` | ~30 | Config YAML de subpastas locais |
| 2 | `src/core/services/path_resolver.py` | ~200 | Resolução de paths via markers e DOCS_DIR |
| 3 | `src/core/services/path_manager.py` | ~210 | Camada sobre path_resolver com helpers de FS |
| 4 | `src/ui/subpastas_dialog.py` | ~180 | SubpastaDialog backup (zero callers; o ativo é `client_subfolder_prompt.py`) |
| 5 | `tests/test_path_manager.py` | ~176 (21 testes) | Testes do módulo path_manager |

**Total removido:** ~796 linhas de código + ~30 linhas de YAML

---

## 5. DIFFS RESUMIDOS

### 5.1 `subpastas_config.py` (de ~110 → ~18 linhas)

```diff
- import logging
- import yaml
- from pathlib import Path
- from typing import Any
-
- def _flatten(node, prefix="") -> list[str]: ...
- def _norm(raw: Any) -> list[dict]: ...
- def load_subpastas_config(path=None) -> list[dict]: ...
  # Preservado:
  MANDATORY_SUBPASTAS = (...)
  def get_mandatory_subpastas(): ...
  def join_prefix(): ...
```

### 5.2 `path_utils.py` (de ~170 → ~10 linhas)

```diff
- import os, shutil, subprocess, sys, logging
- from pathlib import Path
- def ensure_dir(p): ...
- def safe_copy(src, dst): ...
- def open_folder(path): ...
- def _split_pathlike(spec): ...
- def _spec_name(spec): ...
- def _spec_children(spec): ...
- def ensure_subtree(base, specs): ...
- def ensure_subpastas(base, subpastas): ...
+ """Módulo esvaziado — funções locais removidas na v1.5.99."""
+ __all__: list[str] = []
```

### 5.3 `bytes_utils.py`

```diff
- from src.config.paths import CLOUD_ONLY
- MARKER_NAME = ".rc_client_id"
- def write_marker(folder, pk): ...
- def read_marker_id(folder): ...
- def migrate_legacy_marker(folder): ...
- def get_marker_updated_at(folder): ...
  # Preservado: read_pdf_text, find_cartao_cnpj_pdf, list_and_classify_pdfs, format_datetime
```

### 5.4 `file_utils/__init__.py`

```diff
- from .path_utils import ensure_dir, ensure_subpastas, ensure_subtree, open_folder, safe_copy
- from .bytes_utils import write_marker, read_marker_id, migrate_legacy_marker, get_marker_updated_at
  from .bytes_utils import find_cartao_cnpj_pdf, format_datetime, list_and_classify_pdfs, read_pdf_text
```

### 5.5 `clientes_service.py`

```diff
- import os, shutil
- from src.core.app_utils import safe_base_from_fields
- from src.config.paths import DOCS_DIR
- from src.utils.file_utils import ensure_subpastas, write_marker
-
- def _pasta_do_cliente(pk, cnpj, numero, razao): ...  # ~25 linhas
- def _migrar_pasta_se_preciso(old_base, new_base): ...  # ~15 linhas
-
  # Em salvar_cliente():
-   old_path = None  (2 ocorrências)
-   return real_pk, pasta
+   return real_pk, ""
```

### 5.6 `app_core.py`

```diff
- from src.config.paths import CLOUD_ONLY
- try: from src.config.paths import DOCS_DIR ...
- try: from src.core.app_utils import safe_base_from_fields ...
- MARKER_NAME = ".rc_client_id"
-
- def dir_base_cliente_from_pk(pk): ...  # ~20 linhas
- def _ensure_live_folder_ready(pk, cnpj, numero, razao): ...  # ~30 linhas
  # __all__ atualizado
```

### 5.7 `services/__init__.py`

```diff
- from . import path_resolver  (TYPE_CHECKING)
- __all__ = [..., "path_resolver"]
+ __all__ = ["clientes_service", "lixeira_service", "notes_service", "profiles_service"]
```

### 5.8 `test_p1_regression.py`

```diff
- "src.utils.file_utils": _mk(
-     "src.utils.file_utils",
-     ensure_subpastas=MagicMock(),
-     write_marker=MagicMock(),
- ),
+ "src.utils.file_utils": _mk("src.utils.file_utils"),
```

---

## 6. RISCOS REMANESCENTES

| Risco | Severidade | Mitigação |
|---|---|---|
| `path_utils.py` mantido como arquivo vazio — pode confundir devs | Baixa | Docstring explica a remoção; pode ser deletado no futuro |
| `rc_hotfix_no_local_fs.py` ainda existe em `diagnostics/` | Baixa | Script standalone sem callers; remover quando conveniente |
| `ensure_directories()` em `paths.py` permanece | Nenhuma | É bootstrap do app (cria `AppData/RCGestor`), não é de clientes |
| `safe_base_from_fields()` em `app_utils.py` não tem mais callers | Baixa | Pode ser removida num futuro cleanup; é helper puro sem side-effects |
| `NO_FS` em `app_core.py` permanece | Nenhuma | Ainda importada por `main_window_services.py` |
| `salvar_cliente()` retorna `(pk, "")` em vez de `(pk, pasta)` | Nenhuma | Nenhum caller usa `result[1]`; assinatura mantida para backward compat |

---

## 7. RESULTADO DOS TESTES

```
========== 928 passed in 28.77s ==========
```

- **928/928** testes passaram (era 949 antes; 21 removidos com `test_path_manager.py`)
- **test_p1_regression.py**: 13/13 passando (mocks limpos)
- **Zero** referências órfãs a símbolos removidos em `src/` e `tests/`
- **Zero** erros de import

### Verificação manual recomendada

1. Abrir o app → Clientes → Novo Cliente → salvar → confirmar que PK retorna
2. Editar cliente → aba Arquivos (V2) → upload/download/preview funcionando
3. Confirmar que lixeira (excluir cliente) funciona normalmente
4. Confirmar que SubpastaDialog aparece ao fazer upload com múltiplas subpastas

---

*Relatório gerado automaticamente — v1.5.99*
