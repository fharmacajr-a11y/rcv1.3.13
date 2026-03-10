# Diagnóstico Técnico — Módulo de Clientes v1.5.99

**Data:** 2025-07-10  
**Escopo:** Varredura completa de TODOS os arquivos, fluxos, serviços, validações, integrações e pontos de persistência do módulo de clientes.  
**Método:** Leitura integral de código + execução de testes existentes (212 passed, 0 failed).

---

## Índice

1. [Inventário de Arquivos](#1-inventário-de-arquivos)
2. [Mapa de Dependências](#2-mapa-de-dependências)
3. [Fluxos Críticos de Dados](#3-fluxos-críticos-de-dados)
4. [Bugs e Defeitos Confirmados](#4-bugs-e-defeitos-confirmados)
5. [Inconsistências de Tipos e Modelos](#5-inconsistências-de-tipos-e-modelos)
6. [Código Morto e Deprecações Pendentes](#6-código-morto-e-deprecações-pendentes)
7. [Thread Safety e Concorrência](#7-thread-safety-e-concorrência)
8. [Cobertura de Testes](#8-cobertura-de-testes)
9. [Tratamento de Erros e Resiliência](#9-tratamento-de-erros-e-resiliência)
10. [Duplicação de Código](#10-duplicação-de-código)
11. [UX / Performance / UI](#11-ux--performance--ui)
12. [Plano de Ação Priorizado](#12-plano-de-ação-priorizado)

---

## 1. Inventário de Arquivos

### 1.1 Core (Lógica de Negócio)

| Arquivo | Linhas | Responsabilidade |
|---------|--------|-----------------|
| `src/modules/clientes/core/service.py` | 724 | Orquestração: salvar, duplicatas, lixeira, exclusão, batch, storage |
| `src/modules/clientes/core/viewmodel.py` | 747 | ViewModel: carga, filtragem, ordenação, paginação, build de rows |
| `src/modules/clientes/core/constants.py` | 107 | STATUS_CHOICES, STATUS_PREFIX_RE, grupos de status |
| `src/modules/clientes/core/ui_helpers.py` | ~500 | Funções puras: ordering, filtering, seleção, button states, stats |
| `src/modules/clientes/core/export.py` | ~200 | CSV/XLSX export |

### 1.2 Camada de Persistência

| Arquivo | Linhas | Responsabilidade |
|---------|--------|-----------------|
| `src/core/db_manager/db_manager.py` | 643 | CRUD Supabase: list, get, insert, update, soft/hard delete, batch |
| `src/core/services/clientes_service.py` | 237 | Serviço legado: count, duplicatas, salvar (validação + pasta) |
| `src/core/search/search.py` | 248 | Busca server-side ilike + fallback local |
| `src/core/models.py` | 19 | Dataclass `Cliente` |
| `src/db/domain_types.py` | 148 | TypedDicts: `ClientRow`, `PasswordRow`, FKs |

### 1.3 UI — View Principal

| Arquivo | Linhas | Responsabilidade |
|---------|--------|-----------------|
| `src/modules/clientes/ui/view.py` | ~2000 | ClientesV2Frame: treeview, async load, search, filter, sort, pick mode |
| `src/modules/clientes/ui/views/toolbar.py` | ~230 | Barra de busca + combos + lixeira/export |
| `src/modules/clientes/ui/views/actionbar.py` | ~149 | Botões Novo/Editar/Excluir/Restaurar |
| `src/modules/clientes/ui/tree_theme.py` | ~65 | DEPRECATED: shims de tema para treeview |

### 1.4 UI — Editor de Cliente

| Arquivo | Linhas | Responsabilidade |
|---------|--------|-----------------|
| `src/modules/clientes/ui/views/client_editor_dialog.py` | 245 | Modal CTkToplevel com MRO (3 mixins) |
| `src/modules/clientes/ui/views/_editor_ui_mixin.py` | 289 | Construção da UI (campos, bloco notas, status, botões) |
| `src/modules/clientes/ui/views/_editor_data_mixin.py` | 576 | Carga, validação, save, contatos, bloco_notas |
| `src/modules/clientes/ui/views/_editor_actions_mixin.py` | 259 | Callbacks: Enter, Cancel, Arquivos, Cartão CNPJ, Upload |
| `src/modules/clientes/ui/views/_dialogs_typing.py` | 218 | Protocol types para mixins |

### 1.5 UI — Arquivos do Cliente

| Arquivo | Linhas | Responsabilidade |
|---------|--------|-----------------|
| `src/modules/clientes/ui/views/client_files_dialog.py` | ~260 | Modal de arquivos Supabase Storage (4 mixins) |
| `src/modules/clientes/ui/views/_files_ui_mixin.py` | ~500 | UI do browser de arquivos |
| `src/modules/clientes/ui/views/_files_navigation_mixin.py` | ~270 | Navegação, listagem, breadcrumb |
| `src/modules/clientes/ui/views/_files_download_mixin.py` | ~640 | Download, visualização, ZIP |
| `src/modules/clientes/ui/views/_files_upload_mixin.py` | ~260 | Upload, exclusão de arquivos/pastas |

### 1.6 Forms e Componentes

| Arquivo | Linhas | Status |
|---------|--------|--------|
| `src/modules/clientes/forms/__init__.py` | 98 | Stubs deprecated (form_cliente, ClientPicker, open_subpastas_dialog) |
| `src/modules/clientes/forms/_dupes.py` | 137 | Detecção de duplicatas (CNPJ e Razão Social) |
| `src/modules/clientes/forms/client_form_upload_helpers.py` | 271 | Fluxo headless de upload |
| `src/modules/clientes/forms/client_subfolder_prompt.py` | 149 | SubpastaDialog (CTk) |
| `src/modules/clientes/forms/client_picker.py` | ~10 | Stub de compatibilidade |
| `src/modules/clientes/components/helpers.py` | ~28 | DEPRECATED: re-exports de constants |
| `src/modules/clientes/components/status.py` | ~18 | `apply_status_prefix()` |
| `src/modules/clientes/views/client_obligations_window.py` | ~35 | STUB: funcionalidade não implementada |

### 1.7 Facade / Integração

| Arquivo | Linhas relevantes | Responsabilidade |
|---------|-------------------|-----------------|
| `src/core/app_core.py` | 82–284 | Facade: novo_cliente, editar_cliente, excluir, pasta, subpastas |
| `src/modules/main_window/app_actions.py` | 25–200 | Delegadores que chamam app_core |
| `src/modules/main_window/views/main_window_bootstrap.py` | 154–159 | Bind de botões UI → app_actions |

### 1.8 Testes

| Arquivo | Linhas | Foco |
|---------|--------|------|
| `tests/test_clientes_audit_trail.py` | ~290 | Soft/hard delete + audit trail |
| `tests/test_clientes_bulk_load.py` | ~800 | Ordenação bulk, phone utils, batch, cap_hit |
| `tests/test_clientes_pagination.py` | ~710 | Paginação server-side + ViewModel |
| `tests/test_clientes_delete_storage_consistency.py` | ~230 | Hard delete + storage consistency |
| `tests/test_clientes_service_bounds.py` | ~260 | _resolve_current_org_id |
| `tests/test_clientes_trash_pagination.py` | ~500 | Lixeira: filtros, ordem, paginação |
| `tests/test_clientes_trash_filter_persist.py` | ~165 | Persistência de filtros em modo lixeira |
| `tests/test_clientes_ui_helpers.py` | ~105 | _first_line_preview, _one_line |
| `tests/test_client_editor_helpers.py` | ~95 | _safe_get, _conflict_desc |
| `tests/test_client_files_dialog_cleanup.py` | ~265 | Shutdown executor / safe close |
| `tests/test_editor_contatos_async.py` | ~450 | Thread helper, load/save contatos RPC |
| `tests/test_main_window_selected_values_compat.py` | ~240 | _get_selected_values compat |

**Total:** ~10.500 linhas de produção + ~4.200 linhas de teste

---

## 2. Mapa de Dependências

```
main_window_bootstrap.py
    ├── "new" button → App.novo_cliente() → app_actions.novo_cliente()
    │       → app_core.novo_cliente() → form_cliente() → ❌ NotImplementedError
    ├── "edit" → App.editar_cliente() → app_core.editar_cliente() → form_cliente() → ❌ NotImplementedError
    └── "subpastas" → App.open_client_storage_subfolders()
            → app_actions → Supabase file browser (OK)

ClientesV2Frame (view.py)
    ├── _on_new_client() → ClientEditorDialog(client_id=None) ✅
    ├── _on_edit_client() → _open_client_editor() → ClientEditorDialog(client_id=X) ✅
    ├── _on_delete_client() → service.mover_cliente_para_lixeira / excluir_definitivamente ✅
    ├── _on_restore_client() → service.restaurar_clientes_da_lixeira ✅
    ├── load_async() → ViewModel.refresh_from_service() → search_clientes() ✅
    └── _on_enviar_documentos() → ClientEditorDialog → trigger_upload after(200) ✅

ClientEditorDialog (MRO: Actions → Data → UI → CTkToplevel)
    ├── _load_client_data() → db_manager.get_cliente_by_id() ✅
    ├── _on_save_clicked() → _validate_fields() → checar_duplicatas_para_form() → salvar_cliente_a_partir_do_form()
    │       → _save_contatos_to_db() (RPC) → _save_bloco_notas_to_db() (RPC) ✅
    ├── _on_arquivos() → ClientFilesDialog ✅
    └── _on_enviar_documentos() → execute_upload_flow() ✅

ClientFilesDialog (MRO: Download → Upload → Navigation → UI → CTkToplevel)
    ├── ThreadPoolExecutor(max_workers=4)
    ├── Navigation: list() → render tree → breadcrumb
    ├── Upload: filedialogs → SubpastaDialog → adapter.upload_file()
    └── Download: adapter.download() → temp → os.startfile / ZIP
```

---

## 3. Fluxos Críticos de Dados

### 3.1 Criação de Cliente (via V2Frame)
```
Botão Novo / Ctrl+N
  → ClientesV2Frame._on_new_client()
  → ClientEditorDialog(client_id=None)
  → Usuário preenche campos
  → Enter ou botão Salvar
  → EditorDataMixin._on_save_clicked()
  → _validate_fields() [requer Razão Social E CNPJ]
  → service.checar_duplicatas_para_form(valores)
       └─ "Raz?o Social" key fallback (encoding bug)
  → service.salvar_cliente_a_partir_do_form(None, valores)
       └─ clientes_service.salvar_cliente() [requer QUALQUER UM]
  → _save_contatos_to_db() via RPC rc_save_cliente_contatos
  → _save_bloco_notas_to_db() via RPC rc_save_cliente_bloco_notas
  → callback on_save → load_async() → refresh treeview
```

### 3.2 Criação de Cliente (via MainWindow — QUEBRADO)
```
Botão "Novo" no main_window_bootstrap
  → App.novo_cliente()
  → app_actions.novo_cliente()
  → app_core.novo_cliente()
  → from src.modules.clientes.forms import form_cliente
  → form_cliente(app)
  → ❌ raises NotImplementedError (stub deprecated)
```

### 3.3 Exclusão (Soft Delete → Hard Delete)
```
Soft delete: mover_cliente_para_lixeira(id)
  → exec_postgrest UPDATE deleted_at, ultima_alteracao, ultima_por

Hard delete: excluir_clientes_definitivamente([ids])
  → _remove_cliente_storage(id)  [Supabase Storage: list + remove]
  → exec_postgrest DELETE FROM clients WHERE id = …
  → Se storage falha: DB NÃO é chamado (correto)
```

### 3.4 Busca e Paginação
```
search_clientes(term, offset, limit=200, order_by)
  → Supabase .ilike("razao_social", f"%{term}%")
  → .or_("cnpj.ilike.%{term}%, nome.ilike.%{term}%, …")
  → .range(offset, offset + limit - 1)
  → Fallback local se termo < 3 caracteres

ViewModel.refresh_from_service()
  → search_clientes(offset=0, limit=200)
  → _build_rows() → ClienteRow dataclass
  → cap_hit se total >= 1000

ViewModel.load_next_page()
  → search_clientes(offset=current, limit=200)
  → append to _rows
```

---

## 4. Bugs e Defeitos Confirmados

### P0 — Crash / Funcionalidade Quebrada

| # | Local | Descrição | Evidência |
|---|-------|-----------|-----------|
| **P0-1** | `app_core.py` L82-88, L91-98 | **`novo_cliente()` e `editar_cliente()` chamam `form_cliente()` que lança `NotImplementedError`**. São mapeados ao botão "new" no `main_window_bootstrap.py` L154. O fluxo via `ClientesV2Frame` funciona, mas o caminho legado pela main window está ativamente wired e crasha. | `form_cliente()` em `forms/__init__.py` L31-42 é stub que faz `raise NotImplementedError` |
| **P0-2** | `service.py` L245 | **Encoding artefact: `"Raz?o Social"` com `?` em vez de `ã`**. A chave `valores.get("Raz?o Social")` nunca matchará porque o caller (`_editor_data_mixin.py`) passa `"Razão Social"` (com ã). O fallback `or valores.get("Razao Social")` também não matcha. **Resultado: `razao_val` é sempre `""` na checagem de duplicatas**, desabilitando a detecção de duplicatas por razão social. | `checar_duplicatas_para_form()` L245 vs `_editor_data_mixin.py` L493 que usa `"Razão Social"` |

### P1 — Lógica Incorreta / Dados Inconsistentes

| # | Local | Descrição |
|---|-------|-----------|
| **P1-1** | `clientes_service.py` L205 | **`numero_conflicts` sempre retorna `[]` (lista vazia)**. A detecção de duplicatas por número/telefone está estruturalmente presente no código (`_editor_data_mixin.py` L503-518 consome `numero_conflicts`) mas a fonte de dados nunca popula. Feature inoperante. |
| **P1-2** | `_editor_data_mixin.py` L458-468 vs `clientes_service.py` L242 | **Validação assimétrica**: o editor exige AMBOS "Razão Social" E "CNPJ" preenchidos (`_validate_fields()`). Mas `salvar_cliente()` no serviço aceita QUALQUER UM de (razao, cnpj, nome, numero). Cenários como "cliente só com nome" são impossíveis via editor mas possíveis via batch/API. |
| **P1-3** | `_editor_data_mixin.py` L537-560 | **Erros de contatos e bloco_notas são engolidos**: se `_save_contatos_to_db` ou `_save_bloco_notas_to_db` falhar (RPC error), o erro é logado mas `on_done` ainda é chamado e o diálogo fecha. O usuário vê "salvo com sucesso" enquanto dados secundários ficaram perdidos. |
| **P1-4** | `app_core.py` L13 vs L178 | **Import duplicado/conflitante de `get_cliente_by_id`**: linha 13 importa de `src.modules.clientes.core.service`, linha 178 (dentro de `dir_base_cliente_from_pk`) importa de `src.core.db_manager`. São implementações potencialmente diferentes do mesmo nome. |

### P2 — Corretude Baixa Prioridade

| # | Local | Descrição |
|---|-------|-----------|
| **P2-1** | `_editor_data_mixin.py` L483, `_editor_actions_mixin.py` L229 | **Criação desnecessária de `ClientesViewModel()` temporário** apenas para chamar `apply_status_to_observacoes()` / `extract_status_and_observacoes()`. Deveria usar a função estática em `components/status.py` ou `constants.py`. |
| **P2-2** | `_files_download_mixin.py` | **Nome de arquivo ZIP usa PID**: `rc_zip_{os.getpid()}.zip` — se dois downloads ZIP ocorrem simultaneamente (possível com `ThreadPoolExecutor(4)`), ambos escrevem no mesmo arquivo temp, causando corrupção. Deveria usar `tempfile.mkstemp` ou UUID. |
| **P2-3** | `components/status.py` L12 | **`apply_status_prefix` não sanitiza colchetes no status**: se `status = "[Ativo]"`, o resultado é `[[Ativo]] corpo` — colchetes duplicados. |

---

## 5. Inconsistências de Tipos e Modelos

| # | Prioridade | Descrição |
|---|-----------|-----------|
| **T-1** | **P1** | `models.py` `Cliente.id = Optional[int]` vs `domain_types.py` `ClientRow.id = str` (UUID). O dataclass trata ID como inteiro; o TypedDict trata como string UUID. As FKs em `RCTaskRow.client_id` usam `int | None` e `RegObligationRow.client_id` usa `int`. Se a tabela usa UUID mas o app cast para int, há conversões implícitas que podem falhar. |
| **T-2** | **P2** | `ClientRow` (TypedDict) não tem `ultima_alteracao`, `ultima_por`, `created_at` — presentes no dataclass `Cliente`. `ClientRow` tem `nome_fantasia` — ausente no dataclass. Os dois tipos representam a mesma tabela mas estão dessincronizados. |
| **T-3** | **P2** | `PasswordRow.client_id = NotRequired[str | None]` vs `RegObligationRow.client_id = int` — mesma FK com tipos incompatíveis. |
| **T-4** | **P3** | `_resolve_cliente_row` em `app_core.py` L67-74 retorna tupla posicional sem nomes. Qualquer mudança na ordem dos campos do `Cliente` quebra callers silenciosamente. |

---

## 6. Código Morto e Deprecações Pendentes

| # | Arquivo | Status | Risco |
|---|---------|--------|-------|
| **D-1** | `forms/__init__.py` — `form_cliente`, `ClientPicker`, `open_subpastas_dialog` | Stubs que lançam `NotImplementedError`. **`form_cliente` ainda é chamado ativamente** (ver P0-1). `open_subpastas_dialog` é importada em `app_core.py` L271 mas o path que a chama (`open_client_local_subfolders`) não é invocado externamente. | **P0** (form_cliente) / P3 (os outros) |
| **D-2** | `components/helpers.py` | DEPRECATED: re-export de `core.constants` via `import *`. Emite `DeprecationWarning` no import. | P3 — remover quando nenhum caller existir |
| **D-3** | `ui/tree_theme.py` | DEPRECATED: wrappers que delegam para `src.ui.ttk_treeview_theme`. Emite `log.warning` a cada chamada (spam de logs em loops de re-render). | P3 |
| **D-4** | `views/client_obligations_window.py` | STUB: `show_client_obligations_window()` apenas loga e retorna None. Feature não implementada. | P3 — informacional |
| **D-5** | `app_core.py` L274 `ver_subpastas` | DEPRECATED mas exportada em `__all__`. Sem `warnings.warn`. | P3 |

---

## 7. Thread Safety e Concorrência

| # | Prioridade | Local | Descrição |
|---|-----------|-------|-----------|
| **C-1** | **P1** | `client_files_dialog.py` | **Race condition em `_shutdown_executor`**: `self._executor = None` executado antes de `executor.shutdown(wait=False)`. Se outra thread verifica `self._executor is not None` entre o null e o shutdown, pode submeter trabalho para um executor em processo de shutdown. |
| **C-2** | **P2** | `_files_navigation_mixin.py` | **`_loading` flag sem lock**: se `_refresh_files` lança exceção antes de resetar `_loading`, o diálogo fica permanentemente travado (nenhum refresh possível). Não há `try/finally` protegendo o flag. |
| **C-3** | **P2** | `view.py` `_on_new_client()` | **Sem guard de reentrância**: diferente de `_open_client_editor()` que tem `_opening_editor` flag + `_editor_dialog` check, o `_on_new_client()` cria um novo `ClientEditorDialog` a cada chamada sem verificar se um já está aberto. Ctrl+N repetido pode abrir múltiplos diálogos. |
| **C-4** | **P3** | `client_files_dialog.py` | **`_safe_after` acumula IDs no set sem limpeza**: `_after_ids` cresce indefinidamente durante a vida do diálogo. Impacto mínimo (strings curtas), mas é um leak lógico. |
| **C-5** | **P3** | `view.py` L767 (generation counter) | **Pattern correto**: `_load_gen` counter previne renders de dados stale. Bem implementado. |

---

## 8. Cobertura de Testes

### 8.1 Resultado da Suíte Existente

```
212 passed in 24.72s (12 arquivos de teste)
```

### 8.2 Mapa de Cobertura

| Módulo | Cobertura | Avaliação |
|--------|-----------|-----------|
| `service.py` — lixeira/restore/delete | ✅ Boa | Audit trail, storage consistency, bounds |
| `viewmodel.py` — paginação/ordenação | ✅ Boa | Bulk, pagination, trash, cap_hit |
| `search.py` — busca server-side | ✅ Boa | Range, offset, tiebreaker, normalize |
| `_editor_data_mixin.py` — contatos | ✅ Boa | Thread helper, RPC save, load, null fields |
| `service.py` — salvar, duplicatas, form | ❌ **Zero** | `salvar_cliente_a_partir_do_form`, `checar_duplicatas_para_form`, `extrair_dados_cartao_cnpj_em_pasta` |
| `core/export.py` | ❌ **Zero** | CSV, XLSX — nenhum teste |
| `core/ui_helpers.py` | ❌ **Zero** | ~20 funções: classify_selection, calculate_button_states, stats, normalize_filter, etc. |
| `forms/_dupes.py` | ❌ **Zero** | has_cnpj_conflict, has_razao_conflict, build warnings |
| `forms/client_form_upload_helpers.py` | ❌ **Zero** | execute_upload_flow |
| `_editor_actions_mixin.py` | ❌ **Zero** | _on_return_key, _on_cancel, _on_arquivos, _on_cartao_cnpj, _on_enviar_documentos |
| `_editor_ui_mixin.py` | ❌ **Zero** | _build_ui, _build_left_panel, _build_right_panel |
| `_files_*_mixin.py` (4 mixins) | ❌ **Zero** | Navegação, download, upload, UI — nenhum teste funcional |
| `components/status.py` | ❌ **Zero** | apply_status_prefix |

### 8.3 Gaps Críticos

1. **`salvar_cliente_a_partir_do_form()`** — fluxo principal de save sem qualquer teste
2. **`checar_duplicatas_para_form()`** — lógica de dedup com o bug P0-2 não é testada
3. **`core/export.py`** — export CSV/XLSX inteiramente descoberto
4. **`core/ui_helpers.py`** — ~20 funções de lógica de UI pura, facilmente testáveis, zero cobertura
5. **Upload e download de arquivos** — nenhum teste funcional para os mixins do ClientFilesDialog

### 8.4 Observações sobre Qualidade dos Testes

- **Mocks corretos**: target paths de `@patch` consistentemente no local de uso
- **AST extraction**: técnica inteligente para testar lógica sem carregar Tk/CTk
- **Duplicação de setup**: cada arquivo reimplementa seus mocks Supabase; não há fixtures compartilhadas
- **Arquivo enganoso**: `test_clientes_ui_helpers.py` testa `view._first_line_preview` e `_one_line`, **não** as funções de `core/ui_helpers.py`

---

## 9. Tratamento de Erros e Resiliência

| # | Prioridade | Local | Descrição |
|---|-----------|-------|-----------|
| **E-1** | **P1** | `_editor_data_mixin.py` L537-560 | Contatos/bloco_notas RPC errors logados mas callback `on_done` prossegue — dá falsa impressão de sucesso ao usuário |
| **E-2** | **P2** | `_files_download_mixin.py` | `subprocess.Popen` para `xdg-open` sem `wait()` nem fechar handle — resource leak em Linux |
| **E-3** | **P2** | `_files_download_mixin.py`, `_files_upload_mixin.py` | **Sem timeout nas operações de rede** — se Supabase Storage travar, a thread fica bloqueada indefinidamente (o executor tem 4 workers) |
| **E-4** | **P2** | `_files_upload_mixin.py` | **Upload não valida tamanho/tipo de arquivo** — qualquer arquivo passa, potencialmente excedendo limites do bucket |
| **E-5** | **P2** | `_files_upload_mixin.py` | **Exclusão parcial de pasta sem rollback**: `adapter.remove_files(chunk)` em loop — se um chunk falha, os anteriores já foram deletados |
| **E-6** | **P3** | `client_files_dialog.py` `_resolve_supabase_client()` | `except Exception` genérico em múltiplos pontos — `ImportError` de dependência real é mascarado como "módulo inexistente" |
| **E-7** | **P3** | `_files_ui_mixin.py` `_on_header_configure` | Outer `except Exception: pass` engole completamente erros de layout |
| **E-8** | **P3** | `toolbar.py` `_on_search_text_changed` | `try/except Exception` para `after_cancel` — engole qualquer erro |

---

## 10. Duplicação de Código

| # | Prioridade | Descrição |
|---|-----------|-----------|
| **DUP-1** | **P2** | **`_enumerate_files()` definida 3× dentro de closures** em `_files_download_mixin.py` — mesma função reescrita em 3 threads diferentes. Extrair para método do mixin. |
| **DUP-2** | **P2** | **Lógica de download ZIP duplicada (~80 linhas)** entre `_download_folder_as_zip` e `_on_download_zip` no mesmo mixin. Diferença: apenas cálculo de `full_prefix`. |
| **DUP-3** | **P2** | **`_log_slow()` / `log_slow()`** definida em `client_files_dialog.py` E `_files_navigation_mixin.py` — mesma exata função em dois módulos. |
| **DUP-4** | **P3** | **`_safe_get()` duplicada** em `_editor_actions_mixin.py` L22-26 com comentário explícito "duplicado do data mixin para evitar dependência cruzada". |
| **DUP-5** | **P3** | **Stubs Supabase nos testes** — cada arquivo de teste reimplementa os mesmos `sys.modules` stubs para Tk/CTk/Supabase sem fixture compartilhada. |

---

## 11. UX / Performance / UI

| # | Prioridade | Local | Descrição |
|---|-----------|-------|-----------|
| **UX-1** | **P2** | `_files_ui_mixin.py` | **`_on_header_configure` cria `tkfont.Font` a cada resize** — durante drag de janela, cria dezenas de fontes por segundo. Deveria cachear. |
| **UX-2** | **P2** | `_files_ui_mixin.py` | **`_poll_progress_queue` roda a cada 100ms indefinidamente** — mesmo quando não há operação em andamento. Deveria iniciar/parar sob demanda. |
| **UX-3** | **P2** | `toolbar.py` `refresh_theme` | **Incompleto**: só reconfigura `entry_search`, ignora `CTkOptionMenu` e botões — mudança de tema deixa combos desatualizados. |
| **UX-4** | **P2** | `actionbar.py` `set_trash_mode` | **Fragilidade de pack ordering**: chamadas repetidas de `restore_btn.pack()` podem alterar a ordem dos botões. Deveria checar `winfo_ismapped()` antes. |
| **UX-5** | **P3** | `tree_theme.py` | **`log.warning` de deprecação a cada chamada** — pode inundar logs em loops de re-render. Deveria usar `warnings.warn` com filtro ou log uma vez. |
| **UX-6** | **P3** | `_files_navigation_mixin.py` | **Detecção de `is_folder` frágil**: `metadata is None or not metadata` — `metadata = {}` (dict vazio) para um arquivo real seria interpretado como pasta. |
| **UX-7** | **P3** | `_files_ui_mixin.py` | **`_disable_buttons`/`_enable_buttons` usam lista de strings**: se um botão for renomeado, não há erro de compilação — falha silenciosa. |

---

## 12. Plano de Ação Priorizado

### P0 — Correção Imediata (Crash / Funcionalidade Quebrada)

| # | Ação | Esforço | Arquivo(s) |
|---|------|---------|------------|
| **P0-1** | Rewire `app_core.novo_cliente()` e `editar_cliente()` para usar `ClientEditorDialog` em vez de `form_cliente()`. Ou remover os caminhos legados se a UI V2 já os substituiu completamente. | Baixo | `app_core.py` L82-98 |
| **P0-2** | Corrigir encoding em `service.py` L245: trocar `"Raz?o Social"` por `"Razão Social"`. Adicionar teste unitário para `checar_duplicatas_para_form()`. | Baixo | `service.py` L245 |

### P1 — Bugs de Lógica / Dados Silenciosamente Incorretos

| # | Ação | Esforço | Arquivo(s) |
|---|------|---------|------------|
| **P1-1** | Implementar detecção de `numero_conflicts` em `checar_duplicatas_info()` ou remover o consumo morto no editor. Documentar decisão. | Médio | `clientes_service.py` L205, `_editor_data_mixin.py` L503-518 |
| **P1-2** | Alinhar validação do editor com o serviço: decidir se Razão Social + CNPJ são ambos obrigatórios ou se o editor deveria aceitar apenas um. | Baixo | `_editor_data_mixin.py` L458-468 |
| **P1-3** | Exibir warning ao usuário quando save de contatos/bloco_notas falhar (em vez de prosseguir silenciosamente). | Baixo | `_editor_data_mixin.py` L537-560 |
| **P1-4** | Unificar import de `get_cliente_by_id` em `app_core.py` — usar um só módulo. | Baixo | `app_core.py` L13, L178 |
| **P1-5** | Resolver inconsistência `Cliente.id: int` vs `ClientRow.id: str`. Verificar o tipo real da coluna `id` na tabela Supabase e alinhar ambos. | Médio | `models.py`, `domain_types.py` |

### P2 — Robustez, Qualidade e Performance

| # | Ação | Esforço |
|---|------|---------|
| **P2-1** | Extrair `_enumerate_files` para método do mixin; eliminar as 3 duplicações no download mixin | Baixo |
| **P2-2** | Unificar lógica de download ZIP duplicada | Médio |
| **P2-3** | Usar `tempfile.mkstemp` em vez de PID para nome de ZIP temporário | Baixo |
| **P2-4** | Adicionar timeout nas operações de storage (download/upload) | Médio |
| **P2-5** | Proteger `_loading` flag com `try/finally` no navigation mixin | Baixo |
| **P2-6** | Guard de reentrância em `_on_new_client()` (similar ao `_open_client_editor`) | Baixo |
| **P2-7** | Cachear fontes em `_on_header_configure` | Baixo |
| **P2-8** | Completar `refresh_theme` em toolbar (combos + botões) | Médio |
| **P2-9** | Sanitizar colchetes em `apply_status_prefix` | Baixo |

### P3 — Limpeza e Dívida Técnica

| # | Ação | Esforço |
|---|------|---------|
| **P3-1** | Remover `components/helpers.py` (shim deprecated) quando nenhum caller existir | Baixo |
| **P3-2** | Remover `ui/tree_theme.py` ou migrar callers para `src.ui.ttk_treeview_theme` | Baixo |
| **P3-3** | Substituir `log.warning` repetido em tree_theme por `warnings.warn` com filtro | Baixo |
| **P3-4** | Converter `_resolve_cliente_row` para retornar NamedTuple/dataclass | Baixo |
| **P3-5** | Adicionar `warnings.warn` em `app_core.ver_subpastas` DEPRECATED | Trivial |
| **P3-6** | Criar fixtures compartilhadas nos testes (mock Supabase, mock Tk stubs) | Médio |
| **P3-7** | Adicionar testes para `core/export.py`, `core/ui_helpers.py`, `forms/_dupes.py`, `components/status.py` | Alto |
| **P3-8** | Documentar que `client_obligations_window` é stub intencional ou implementar feature | Trivial |

---

## Resumo Executivo

O módulo de clientes está **funcionalmente maduro** pela rota `ClientesV2Frame → ClientEditorDialog`, com boa arquitetura em camadas (View → ViewModel → Service → db_manager). Os 212 testes passam sem falhas e cobrem bem paginação, lixeira, audit trail e consistência de storage.

No entanto, existem **2 bugs P0** que precisam de correção imediata:

1. A rota legada `main_window → app_core.novo_cliente/editar_cliente → form_cliente` está **wired a botões ativos na UI** mas crasha com `NotImplementedError` porque `form_cliente` foi deprecated sem rewiring dos callers.

2. Um artefato de encoding (`"Raz?o Social"` com `?`) em `service.py` L245 **desabilita silenciosamente** a detecção de duplicatas por razão social — a chave nunca matcha o dict passado pelo editor.

A cobertura de testes é **boa para ~40% do código** (paginação, lixeira, audit trail) mas **zero para ~60%** (export, ui_helpers, duplicatas, upload/download, actions mixin). Os problemas de thread safety são gerenciáveis mas merecem atenção no `_files_download_mixin` e no `_loading` flag do navigation mixin.
