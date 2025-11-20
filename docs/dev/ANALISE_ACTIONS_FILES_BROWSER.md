# 📊 Análise de Modularização: `actions.py` e `files_browser.py`

**Data da Análise**: 2025-01-XX  
**Objetivo**: Identificar oportunidades de refatoração e modularização focadas em separar responsabilidades (UI, Lógica de Negócio, Infraestrutura).

---

## 1. 📋 Visão Geral de Cada Arquivo

### `src/ui/forms/actions.py` (419 linhas)

**Propósito Principal**: Orquestração do pipeline de upload de documentos e operações de storage (listagem, download).

**Responsabilidades Atuais**:
- ✅ **UI (Tkinter)**: BusyDialog (progress dialog), messagebox, filedialog
- ✅ **Lógica de Negócio**: Validação de inputs, classificação de erros, montagem de payloads
- ✅ **Infraestrutura**: Chamadas diretas ao Supabase Storage, manipulação de arquivos locais
- ✅ **Coordenação**: Pipeline completo de upload (validar → preparar → executar → finalizar)

**Principais Dependências**:
```python
# UI
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk

# Infra
from adapters.storage import StorageAdapter, get_storage_adapter
from infra.supabase_client import get_supabase_client
from uploader_supabase import upload_items

# Lógica
from src.ui.forms.pipeline import (
    validate_inputs,
    prepare_payload,
    perform_uploads,
    finalize_state,
)
```

**Estado Global/Externo**:
- Acessa `CURRENT_USER`, `ACTIVE_ORG` via `get_supabase_client()`
- Usa `upload_items` de `uploader_supabase.py` (módulo raiz)
- Depende de `src.ui.forms.pipeline` (já modularizado)

---

### `src/ui/files_browser.py` (1492 linhas)

**Propósito Principal**: Interface de navegação de arquivos no Supabase Storage com operações CRUD e preview.

**Responsabilidades Atuais**:
- ✅ **UI (Tkinter)**: Janela completa com Treeview, botões, navegação, progress dialogs
- ✅ **Lógica de Negócio**: 
  - Navegação de pastas (prefix management)
  - Status de pastas (PRONTA/NÃO PRONTA/NEUTRAL)
  - Formatação de tamanhos, sanitização de nomes
  - Coleta recursiva de arquivos em pastas
- ✅ **Infraestrutura**: 
  - Listagem de objetos no storage
  - Download de arquivos individuais e ZIP
  - Exclusão de arquivos/pastas
  - Preview de PDF/imagens
- ✅ **Threading**: ThreadPoolExecutor para operações assíncronas, cancelamento de downloads
- ✅ **Persistência**: Salvar/restaurar último prefix navegado, cache de status de pastas

**Principais Dependências**:
```python
# UI
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk

# Preview
from src.modules.pdf_preview import open_pdf_viewer

# Storage
from src.modules.uploads.service import (
    list_storage_objects,
    download_file,
    download_bytes,
    download_folder_zip,
    delete_file,
    DownloadCancelledError,
)

# Persistência
from src.helpers.preference_helper import (
    get_last_prefix,
    save_last_prefix,
    get_browser_status_map,
    save_browser_status_map,
)
```

**Estado Global**:
```python
_OPEN_WINDOWS: dict[tuple[str, str], tk.Toplevel] = {}  # Singleton windows
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="files_browser_")
```

**Características Críticas**:
- 🔴 **Função gigante**: `open_files_browser()` contém ~1450 linhas (todo o módulo é 1 função!)
- 🔴 **Acoplamento UI+Lógica+Infra**: Mistura completa de três camadas
- 🔴 **Threading complexo**: `_run_bg`, `_executor`, `_populate_children_async`, cancelamento de ZIP
- 🔴 **Multi-contexto**: Suporta dois módulos ("auditoria" vs padrão) com comportamentos diferentes

---

## 2. 🗺️ Mapa de Funções e Classes

### `actions.py` - Estrutura

| Função/Classe | Tipo | Propósito | Linhas |
|--------------|------|-----------|--------|
| `_now_iso_z()` | Helper/Infra | Gera timestamp ISO 8601 UTC | ~5 |
| `_get_bucket_name()` | Helper/Infra | Retorna nome do bucket Supabase | ~5 |
| `_current_user_id()` | Helper/Infra | Retorna ID do usuário logado | ~10 |
| `_resolve_org_id(client_id, supabase)` | Helper/Lógica | Resolve `org_id` a partir de `client_id` | ~15 |
| `preencher_via_pasta(entry_cnpj, ...)` | UI+Lógica | Auto-preenche CNPJ detectando pasta GERAL no storage | ~50 |
| `_classify_storage_error(exc)` | Lógica | Classifica erros de storage em categorias (auth, network, etc.) | ~25 |
| `_salvar_e_upload_docs_impl(payload, ...)` | Coordenação | Núcleo do pipeline: executa validação → upload → finalização | ~80 |
| `salvar_e_enviar_para_supabase(...)` | UI+Coordenação | Wrapper que prepara payload e chama `_salvar_e_upload_docs_impl` | ~40 |
| `list_storage_objects(...)` | Infra | Lista objetos no storage (delegação para `adapter`) | ~15 |
| `download_file(...)` | Infra | Baixa arquivo do storage (delegação para `adapter`) | ~15 |
| `salvar_e_upload_docs(...)` | UI+Coordenação | Entry point principal: cria BusyDialog e executa pipeline | ~60 |
| `BusyDialog` | UI (Class) | Dialog de progresso (indeterminado/determinado) | 85 |

**Categorização por Camada**:
- 🟦 **UI Pura**: `BusyDialog`, `salvar_e_upload_docs` (dialog creation)
- 🟨 **Lógica**: `_classify_storage_error`, `_resolve_org_id`
- 🟥 **Infra**: `_now_iso_z`, `_get_bucket_name`, `_current_user_id`, `list_storage_objects`, `download_file`
- 🟧 **Híbrido (UI+Lógica+Infra)**: `preencher_via_pasta`, `salvar_e_enviar_para_supabase`, `_salvar_e_upload_docs_impl`

---

### `files_browser.py` - Estrutura

⚠️ **ATENÇÃO**: Quase todo o código está dentro de `open_files_browser()` (função de ~1450 linhas).

| Função/Closure | Tipo | Propósito | Linha Aprox. |
|---------------|------|-----------|--------------|
| **`open_files_browser(...)`** | **Main** | **Entry point: cria janela e define TODAS as funções internas** | **49-1492** |
| `_center_on_parent(...)` | Helper/UI | Centraliza janela sobre parent | ~120 |
| `_sanitize_filename(...)` | Helper/Lógica | Remove caracteres inválidos de nomes de arquivo | ~130 |
| `_sync_path_label()` | UI | Atualiza label de navegação com prefix atual | ~145 |
| `_set_prefix(...)` | Coordenação | Muda prefix atual e recarrega árvore | ~160 |
| `_go_up_one()` | UI+Lógica | Navega para pasta pai | ~175 |
| `_go_forward(...)` | UI+Lógica | Navega para pasta filha | ~185 |
| `_refresh_listing()` | Coordenação | Recarrega árvore no prefix atual | ~195 |
| `_folder_status_for_display(...)` | Lógica | Retorna glyph de status (✓/✗/•) | ~410 |
| `_insert_row(...)` | UI | Insere linha na Treeview com status | ~420 |
| `_get_item_fullpath(...)` | Lógica | Reconstrói path completo de item da árvore | ~435 |
| `_is_folder_iid(...)` | Lógica | Verifica se item é pasta | ~450 |
| `_apply_folder_status(...)` | Lógica+Persistência | Aplica status a pasta e salva em repo | ~460 |
| `_cycle_folder_status(...)` | Lógica | Rotaciona status (NEUTRAL → READY → NOTREADY) | ~480 |
| `_on_tree_left_click(...)` | UI+Lógica | Handler de clique na coluna de status | ~490 |
| `_ensure_status_menu()` | UI | Cria menu contextual de status | ~505 |
| `_on_tree_right_click(...)` | UI | Handler de clique direito na coluna status | ~525 |
| `_sort_tree(...)` | UI+Lógica | Ordena Treeview por coluna (com parsing de tamanhos) | ~550 |
| `_persist_state_on_close()` | Persistência | Salva prefix e status map antes de fechar | ~605 |
| `_on_close()` | Coordenação | Cleanup ao fechar janela | ~615 |
| `_run_bg(...)` | Threading | Executa função em thread com callback no main thread | ~645 |
| `_set_actions_empty_state()` | UI | Desabilita botões (listagem vazia) | ~660 |
| `_set_actions_normal_state()` | UI | Habilita botões (listagem com itens) | ~675 |
| `_format_size(...)` | Helper/Lógica | Formata bytes para KB/MB/GB | ~690 |
| `_toast_error(...)` | UI | Exibe messagebox de erro | ~705 |
| `_zip_suggest_name(...)` | Lógica | Gera nome sugerido para ZIP | ~715 |
| `_destino_zip(...)` | UI | Abre filedialog para escolher destino do ZIP | ~725 |
| `_resolve_full_prefix(...)` | Lógica | Resolve prefix completo a partir de relativo | ~740 |
| `_fetch_children(...)` | Infra | Lista objetos em prefix (delegação para service) | ~750 |
| `_clear_children(...)` | UI | Remove filhos de item da Treeview | ~770 |
| `_insert_children(...)` | UI+Lógica | Popula Treeview com lista de entries | ~780 |
| `_is_placeholder(...)` | Lógica | Verifica se item é placeholder de loading | ~810 |
| `_needs_population(...)` | Lógica | Verifica se pasta precisa ser populada | ~820 |
| `_is_folder_item(...)` | Lógica | Verifica se item é pasta (via valores) | ~830 |
| **`populate_tree(...)`** | **Coordenação** | **Popula Treeview com objetos do storage** | **~840** |
| `_populate_children_async(...)` | Threading+UI | Popula filhos de pasta em thread com placeholder | ~870 |
| `_get_rel_path(...)` | Lógica | Reconstrói path relativo de item | ~920 |
| `on_tree_open(...)` | UI+Threading | Handler de expansão de pasta (trigger async population) | ~930 |
| `_current_item_info()` | Lógica | Retorna info do item selecionado | ~950 |
| `_selected_folder_target()` | Lógica | Retorna prefix completo de pasta selecionada | ~965 |
| `_full_path_from_rel(...)` | Lógica | Converte path relativo em absoluto com validação | ~985 |
| `_collect_files_under_prefix(...)` | Infra+Lógica | Coleta recursivamente todos arquivos em pasta | ~995 |
| `_update_preview_state()` | UI+Lógica | Atualiza estado de botões (visualizar, excluir) | ~1010 |
| **`do_download()`** | **Infra+UI** | **Download de arquivo individual** | **~1040** |
| **`on_zip_folder()`** | **Infra+UI+Threading** | **Download de pasta como ZIP (com cancelamento)** | **~1070** |
| `_on_delete_files()` | Infra+UI | Exclui arquivos selecionados | ~1280 |
| `_on_delete_folder()` | Infra+UI | Exclui pasta e conteúdo | ~1320 |
| **`on_preview()`** | **Infra+UI+Threading** | **Preview de PDF/imagens** | **~1370** |
| `on_delete_selected()` | Infra+UI | Exclui arquivo (módulo auditoria) | ~1420 |
| `_activate_selection()` | UI+Lógica | Expande pasta ou visualiza arquivo (Enter/DblClick) | ~1450 |
| `on_double_click(...)` | UI | Handler de duplo clique | ~1475 |
| `on_enter_key(...)` | UI | Handler de tecla Enter | ~1480 |

**Categorização por Camada**:
- 🟦 **UI Pura**: 20+ funções (botões, treeview, dialogs, bindings)
- 🟨 **Lógica Pura**: ~15 funções (formatação, validação, navegação)
- 🟥 **Infra Pura**: ~5 funções (delegação para `uploads_service`)
- 🟧 **Híbrido Complexo**: ~20 funções (mixing 2-3 camadas)

---

## 3. 🔗 Pontos de Acoplamento Forte

### `actions.py`

| Acoplamento | Descrição | Impacto na Modularização |
|------------|-----------|-------------------------|
| **1. UI + Storage direto** | `preencher_via_pasta` mistura `messagebox.show*` com chamadas ao `adapter.list_objects()` | 🔴 **Alto** - dificulta testes unitários |
| **2. Coordenação + UI** | `salvar_e_upload_docs` cria `BusyDialog` E executa pipeline | 🟡 **Médio** - dialog deveria ser criado fora |
| **3. Pipeline + Infra** | `_salvar_e_upload_docs_impl` chama `upload_items` (módulo raiz) e `adapter` diretamente | 🟡 **Médio** - deveria usar service layer |
| **4. Helpers + Estado Global** | `_current_user_id()`, `_get_bucket_name()` leem globals via `get_supabase_client()` | 🟡 **Médio** - dificulta injeção de dependências |

**Dependências Circulares/Complexas**:
- `uploader_supabase.py` (módulo raiz) → deveria estar em `src/modules/uploads/`
- `pipeline.py` → já modularizado, mas ainda em `src/ui/forms/` (deveria estar em `src/modules/uploads/`)

---

### `files_browser.py`

| Acoplamento | Descrição | Impacto na Modularização |
|------------|-----------|-------------------------|
| **1. Função gigante (1450 linhas)** | TODO o código está em `open_files_browser()` - closures impossibilitam extração simples | 🔴 **CRÍTICO** - maior risco de quebra |
| **2. Threading + UI mixing** | `_run_bg`, `_populate_children_async` misturam `threading.Thread`, `_safe_after`, e manipulação de Treeview | 🔴 **Alto** - dificulta testes e reuso |
| **3. Estado em atributos dinâmicos** | `docs_window._current_prefix`, `._folder_status`, `._zip_cancel_evt` (setattr/getattr) | 🔴 **Alto** - dificulta rastreamento |
| **4. Multi-contexto (auditoria vs padrão)** | `if module == "auditoria"` em 5+ lugares com lógicas diferentes | 🟡 **Médio** - deveria usar Strategy Pattern |
| **5. UI + Lógica de Negócio** | `_sort_tree` mistura parsing de tamanhos (KB/MB/GB) com manipulação de Treeview | 🟡 **Médio** - lógica de parsing deveria ser helper |
| **6. Infra + UI direta** | `on_zip_folder` cria dialog, chama `download_folder_zip`, gerencia cancelamento, tudo em 200+ linhas | 🔴 **Alto** - impossível testar isoladamente |

**Estado Global Crítico**:
```python
_OPEN_WINDOWS: dict[tuple[str, str], tk.Toplevel]  # Singleton pattern
_executor = ThreadPoolExecutor(...)  # Thread pool global
```

---

## 4. 💡 O Que Dá Pra Extrair em Serviços/Helpers

### Extrações Prioritárias para `actions.py`

#### **A. Service Layer: `UploadService`**
```python
# src/modules/uploads/service.py (expandir existente)

class UploadService:
    def __init__(self, adapter: StorageAdapter, supabase_client):
        self._adapter = adapter
        self._supabase = supabase_client
    
    def execute_upload_pipeline(
        self,
        files: list[Path],
        folder_name: str,
        client_id: str,
        org_id: str,
        ...
    ) -> dict[str, Any]:
        """
        Orquestra: validate_inputs → prepare_payload → perform_uploads → finalize_state.
        Retorna dict com resultado (success, errors, uploaded_files).
        """
        pass
    
    def detect_cnpj_from_storage(self, client_id: str) -> str | None:
        """Lógica extraída de preencher_via_pasta (sem UI)."""
        pass
```

**Benefícios**:
- ✅ Testável isoladamente (mock adapter)
- ✅ Reusável em CLI/API
- ✅ Separa coordenação de UI

---

#### **B. Helper: `StorageErrorClassifier`**
```python
# src/helpers/storage_errors.py

class StorageErrorClassifier:
    @staticmethod
    def classify(exc: Exception) -> str:
        """Retorna: 'auth', 'network', 'validation', 'unknown'."""
        pass
    
    @staticmethod
    def user_friendly_message(exc: Exception) -> str:
        """Retorna mensagem amigável para UI."""
        pass
```

---

#### **C. Helper: `TimestampHelper`**
```python
# src/helpers/datetime_utils.py

def now_iso_utc() -> str:
    """Gera timestamp ISO 8601 UTC."""
    return datetime.now(timezone.utc).isoformat()
```

---

#### **D. Mover `BusyDialog` para módulo UI genérico**
```python
# src/ui/components/progress_dialog.py

class ProgressDialog(tk.Toplevel):
    """Dialog reutilizável de progresso (indeterminado/determinado)."""
    pass
```

---

### Extrações Prioritárias para `files_browser.py`

#### **A. Service Layer: `FileBrowserService`**
```python
# src/modules/files_browser/service.py

class FileBrowserService:
    def __init__(self, storage_service):
        self._storage = storage_service
    
    def list_children(self, prefix: str) -> list[FileEntry]:
        """Lista filhos de um prefix (abstrai objetos raw)."""
        pass
    
    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download de arquivo individual."""
        pass
    
    def download_folder_as_zip(
        self,
        prefix: str,
        zip_name: str,
        out_dir: str,
        progress_callback=None,
        cancel_event=None
    ) -> str:
        """Download de pasta como ZIP com suporte a cancelamento."""
        pass
    
    def delete_files(self, keys: list[str]) -> None:
        """Exclusão de múltiplos arquivos."""
        pass
    
    def delete_folder(self, prefix: str) -> None:
        """Exclusão recursiva de pasta."""
        pass
    
    def collect_files_recursive(self, prefix: str) -> list[str]:
        """Coleta todos arquivos em pasta (recursivo)."""
        pass
```

---

#### **B. Helper: `FormatHelper`**
```python
# src/helpers/format_utils.py

def format_file_size(bytes_val: int | None) -> str:
    """Formata bytes para KB/MB/GB."""
    pass

def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos de nomes de arquivo."""
    pass
```

---

#### **C. Helper: `NavigationHelper`**
```python
# src/modules/files_browser/navigation.py

class NavigationHelper:
    def __init__(self, base_prefix: str):
        self._base = base_prefix
        self._current = base_prefix
        self._history: list[str] = [base_prefix]
    
    def go_forward(self, child_name: str) -> str:
        """Navega para pasta filha."""
        pass
    
    def go_up(self) -> str:
        """Navega para pasta pai."""
        pass
    
    def resolve_full_prefix(self, rel_prefix: str) -> str:
        """Resolve prefix completo a partir de relativo."""
        pass
```

---

#### **D. Model: `FolderStatusManager`**
```python
# src/modules/files_browser/status_manager.py

class FolderStatusManager:
    NEUTRAL = "neutral"
    READY = "ready"
    NOTREADY = "notready"
    
    GLYPHS = {NEUTRAL: "•", READY: "✓", NOTREADY: "✗"}
    
    def __init__(self):
        self._status_map: dict[str, str] = {}
    
    def get_status(self, folder_path: str) -> str:
        """Retorna status atual."""
        pass
    
    def set_status(self, folder_path: str, status: str) -> None:
        """Define status."""
        pass
    
    def cycle_status(self, folder_path: str) -> str:
        """Rotaciona status (NEUTRAL → READY → NOTREADY)."""
        pass
    
    def get_glyph(self, folder_path: str) -> str:
        """Retorna glyph de status."""
        pass
    
    def load_from_repo(self, browser_key: str) -> None:
        """Carrega status de persistência."""
        pass
    
    def save_to_repo(self, browser_key: str) -> None:
        """Salva status em persistência."""
        pass
```

---

#### **E. UI Component: `FileBrowserWindow`**
```python
# src/ui/components/file_browser_window.py

class FileBrowserWindow(tk.Toplevel):
    """
    Janela de navegação de arquivos (UI pura).
    Recebe FileBrowserService e FolderStatusManager como dependências.
    """
    
    def __init__(
        self,
        parent,
        service: FileBrowserService,
        status_manager: FolderStatusManager,
        config: BrowserConfig,
    ):
        pass
    
    def refresh_listing(self) -> None:
        """Recarrega árvore no prefix atual."""
        pass
    
    def navigate_to(self, prefix: str) -> None:
        """Navega para prefix especificado."""
        pass
```

---

#### **F. Strategy Pattern: `ModuleBehavior`**
```python
# src/modules/files_browser/module_behaviors.py

class ModuleBehavior(ABC):
    @abstractmethod
    def get_delete_file_button_text(self) -> str:
        pass
    
    @abstractmethod
    def handle_folder_deletion(self, bucket: str, prefix: str) -> None:
        pass

class AuditoriaBehavior(ModuleBehavior):
    def __init__(self, delete_folder_handler):
        self._handler = delete_folder_handler
    
    def get_delete_file_button_text(self) -> str:
        return "Excluir selecionado"
    
    def handle_folder_deletion(self, bucket: str, prefix: str) -> None:
        if self._handler:
            self._handler(bucket, prefix)

class DefaultBehavior(ModuleBehavior):
    def get_delete_file_button_text(self) -> str:
        return "Excluir arquivo(s)"
    
    def handle_folder_deletion(self, bucket: str, prefix: str) -> None:
        # Lógica de coleta recursiva + deleção
        pass
```

---

## 5. 🛣️ Ordem Sugerida de Modularização

### **Fase A: Preparação (baixo risco, alta utilidade)**

**A1. Extrair Helpers Genéricos** (1-2 dias)
- ✅ `src/helpers/format_utils.py`: `format_file_size`, `sanitize_filename`
- ✅ `src/helpers/datetime_utils.py`: `now_iso_utc`
- ✅ `src/helpers/storage_errors.py`: `StorageErrorClassifier`

**A2. Mover `BusyDialog`** (1 dia)
- ✅ `src/ui/components/progress_dialog.py`: Extrair `BusyDialog` de `actions.py`
- ✅ Atualizar imports em `actions.py`

**A3. Criar `FolderStatusManager`** (2 dias)
- ✅ `src/modules/files_browser/status_manager.py`
- ✅ Testes unitários isolados
- ⚠️ **NÃO modificar `files_browser.py` ainda** - apenas criar módulo

---

### **Fase B: Service Layer (médio risco, permite testes)**

**B1. Expandir `UploadService`** (3 dias)
- ✅ `src/modules/uploads/service.py`: Adicionar `execute_upload_pipeline`, `detect_cnpj_from_storage`
- ✅ Refatorar `_salvar_e_upload_docs_impl` para usar service
- ✅ Testes unitários com mock do adapter

**B2. Criar `FileBrowserService`** (4 dias)
- ✅ `src/modules/files_browser/service.py`: Métodos de listagem, download, exclusão
- ✅ Consolidar chamadas de `uploads_service` (já existe)
- ✅ Testes unitários

**B3. Criar `NavigationHelper`** (2 dias)
- ✅ `src/modules/files_browser/navigation.py`
- ✅ Testes unitários de navegação (go_up, go_forward, resolve_prefix)

---

### **Fase C: Refatoração de `files_browser.py` (alto risco, incremental)**

⚠️ **ATENÇÃO**: Este é o trabalho mais complexo. Requer micro-steps rigorosos.

**C1. Extrair Closures para Métodos de Classe** (5 dias)
- ✅ Criar `src/ui/components/file_browser_window.py` (classe vazia)
- ✅ Mover closures para métodos (mantendo lógica idêntica)
- ✅ Testes manuais extensivos após cada 10-15 closures migradas

**C2. Injetar Services via Construtor** (3 dias)
- ✅ `FileBrowserWindow.__init__` recebe `FileBrowserService`, `FolderStatusManager`, `NavigationHelper`
- ✅ Substituir lógica inline por chamadas aos services
- ✅ Validação E2E

**C3. Implementar Strategy Pattern** (2 dias)
- ✅ `src/modules/files_browser/module_behaviors.py`: `AuditoriaBehavior`, `DefaultBehavior`
- ✅ Remover `if module == "auditoria"` do código UI

**C4. Limpar Estado Global** (2 dias)
- ✅ `_OPEN_WINDOWS` → mover para `WindowManager` singleton
- ✅ `_executor` → injetar via DI ou manter como atributo de classe

---

### **Fase D: Consolidação (baixo risco, polish)**

**D1. Mover `pipeline.py`** (1 dia)
- ✅ `src/ui/forms/pipeline.py` → `src/modules/uploads/pipeline.py`
- ✅ Atualizar imports

**D2. Mover `uploader_supabase.py`** (1 dia)
- ✅ Raiz → `src/modules/uploads/supabase_uploader.py`
- ✅ Atualizar imports

**D3. Documentação e Diagramas** (1 dia)
- ✅ Atualizar ADRs
- ✅ Diagrama de arquitetura pós-refatoração

---

## 6. ⚠️ Riscos e Pontos Sensíveis

### **Riscos de `actions.py`**

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| **Pipeline quebrar** | 🔴 Alta | Testes E2E antes/depois de cada mudança; manter `salvar_e_upload_docs` como facade por 1-2 releases |
| **BusyDialog incompatível** | 🟡 Média | Extrair com cuidado mantendo mesma API; adicionar testes de UI manual |
| **Dependência de `uploader_supabase`** | 🟡 Média | Mover para `src/modules/uploads/` antes de refatorar `actions.py` |

---

### **Riscos de `files_browser.py`**

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| **Função de 1450 linhas** | 🔴 **CRÍTICA** | **Micro-steps obrigatórios**: migrar 10-15 closures por vez; testar manualmente após cada batch; manter versão original comentada por 2 releases |
| **Threading race conditions** | 🔴 Alta | Manter lógica de threading EXATAMENTE igual; adicionar logs extensivos; testes de carga |
| **Estado em atributos dinâmicos** | 🔴 Alta | Migrar para atributos tipados gradualmente; usar TypedDict para mapear `docs_window._*` |
| **Multi-contexto (auditoria)** | 🟡 Média | Implementar Strategy Pattern DEPOIS de extrair classe; validar ambos os módulos em produção |
| **Singleton `_OPEN_WINDOWS`** | 🟡 Média | Mover para `WindowManager` singleton após extrair classe principal |
| **ThreadPoolExecutor global** | 🟡 Média | Aceitar como singleton ou injetar via DI (decisão arquitetural) |

---

### **Pontos Sensíveis (NÃO tocar sem planejamento)**

#### `actions.py`
- ❌ **Ordem do pipeline**: `validate_inputs → prepare_payload → perform_uploads → finalize_state` (definido em `pipeline.py`)
- ❌ **Callback de progresso**: `BusyDialog.set_progress()` chamado de dentro do `upload_items`
- ❌ **Tratamento de 409 Duplicate**: Lógica em `src/modules/uploads/repository.py` (já modularizada)

#### `files_browser.py`
- ❌ **`_safe_after`**: Wrapper crítico para thread safety (chamadas de thread → main thread)
- ❌ **Placeholder system**: Tags `PLACEHOLDER_TAG`, `EMPTY_TAG` para loading assíncrono
- ❌ **Cancelamento de ZIP**: `_zip_cancel_evt` + `download_folder_zip(cancel_event=...)`
- ❌ **Preview de PDF/Imagens**: Integração com `open_pdf_viewer` (módulo externo)
- ❌ **Persistência de estado**: `save_last_prefix`, `save_browser_status_map` (fechar janela)

---

## 7. 📊 Resumo Executivo

| Arquivo | Tamanho | Complexidade | Prioridade de Refatoração | Tempo Estimado |
|---------|---------|--------------|--------------------------|---------------|
| `actions.py` | 419 linhas | 🟡 Média | 🟢 **Fase B** (service layer) | 5-7 dias |
| `files_browser.py` | 1492 linhas | 🔴 **MUITO ALTA** | 🔴 **Fase C** (alto risco) | 15-20 dias |

---

### **Recomendações Finais**

1. **Comece por `actions.py`** (menor risco, aprende padrões para aplicar em `files_browser.py`)
2. **Micro-steps rigorosos** para `files_browser.py` (10-15 closures por commit, testes manuais obrigatórios)
3. **Mantenha versões paralelas** por 1-2 releases (facade pattern)
4. **Testes E2E críticos**:
   - Upload completo (arquivos + pasta)
   - Navegação de pastas
   - Download de ZIP com cancelamento
   - Preview de PDF/Imagens
   - Exclusão de arquivos/pastas
   - Status de pastas (PRONTA/NÃO PRONTA)

---

**Próximos Passos**: 
1. Validar este relatório com stakeholders
2. Criar ADR para estratégia de refatoração
3. Configurar feature flags para migration paralela (se necessário)
4. Executar Fase A (preparação) como warmup

