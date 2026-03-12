# ANÁLISE TÉCNICA DE REMOÇÃO — Fluxo Externo Legado de Arquivos

> **Documento**: análise pura, read-only — nenhuma alteração de código.  
> **Versão**: v1.5.99  
> **Data**: 11/03/2026  
> **Decisão de produto**: o ÚNICO caminho para abrir arquivos será entrar no cliente → editar → "Arquivos" (V2). Ctrl+S, subpastas, browser externo e múltiplos browsers coexistindo serão eliminados.

---

## 1. RESUMO EXECUTIVO

### O fluxo externo ainda está vivo?
**SIM** — exatamente **1 caminho** ainda está ativo em produção: `Ctrl+S` → `open_client_storage_subfolders()` → `browser.py`. Tudo o mais conectado ao browser externo é **código morto**.

### Ctrl+S / subpastas / browser.py sustentam algo necessário?
**NÃO.** O fluxo `Ctrl+S` é um atalho de conveniência que abre o browser externo V1a. O mesmo conteúdo (arquivos do cliente no Supabase) já é acessível pelo fluxo oficial V2 dentro do editor. Nenhum dado, estado ou lógica de negócio depende exclusivamente desse caminho.

### A remoção é viável na próxima fase?
**SIM — sem pré-requisitos de adaptação no V2.** Como a decisão de produto elimina o fluxo externo inteiro (não migra para V2), não é necessário adicionar `start_prefix` nem `modal/wait_window` ao V2. Basta: (1) desligar o atalho Ctrl+S, (2) remover o handler e o código morto, (3) deletar `browser.py`.

### O fluxo do editor (V2) depende de algo do V1a?
**NÃO.** O V2 (`browser_v2.py`) tem imports completamente independentes do V1a (`browser.py`). Nenhum código, classe, função ou variável do V1a é importado ou usado pelo V2. Confirmado via grep — zero referências cruzadas.

---

## 2. MAPA DO FLUXO EXTERNO

### 2.1 — `Ctrl+S` → Subpastas → browser.py  [ATIVO EM PRODUÇÃO]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `src/core/keybindings.py` → `src/modules/main_window/views/main_window_bootstrap.py` → `src/modules/main_window/views/main_window.py` → `src/modules/main_window/app_actions.py` → `src/modules/uploads/view.py` → `src/modules/uploads/views/browser.py` |
| **Função/Classe principal** | `AppActions.open_client_storage_subfolders()` → `open_files_browser()` → `UploadsBrowserWindow` |
| **Ponto de entrada** | Tecla `Ctrl+S` (bind em `keybindings.py:34`) |
| **Quem chama** | `bind_global_shortcuts()` com handler `"subpastas"` → `App.open_client_storage_subfolders` |
| **Ainda está em uso?** | **SIM** — funcionalidade de produção |
| **Legado morto?** | Não é morto — mas a decisão de produto o torna dispensável |
| **Depende do browser externo?** | **SIM** — é o único propósito dessa cadeia |

Cadeia completa:
```
Ctrl+S
 └─ keybindings.py:34   b("<Control-s>", _wrap(handlers.get("subpastas")))
    └─ bootstrap.py:159  "subpastas": app.open_client_storage_subfolders
       └─ main_window.py:535  App.open_client_storage_subfolders()
          └─ app_actions.py:156  AppActions.open_client_storage_subfolders()
             ├── valida seleção, obtém user/org_id
             └── open_files_browser(self._app, ..., start_prefix=base_prefix, modal=True)
                 └─ view.py:19 → browser.py:682 → UploadsBrowserWindow(...)
                    └─ parent.wait_window(window)
```

---

### 2.2 — `ver_subpastas()` alias  [DEPRECATED]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `app_actions.py:198-200`, `main_window.py:539-541` |
| **Função** | `ver_subpastas()` — alias deprecated |
| **Quem chama** | Ninguém externamente (alias interno), mas referenciado em testes e `_log_call` |
| **Legado morto?** | **SIM** — apenas redireciona → `open_client_storage_subfolders()` |
| **Depende do browser externo?** | SIM, indiretamente (delega pro fluxo 2.1) |

---

### 2.3 — Re-export chain: `view.py` → `__init__.py` → callers  [ATIVO COMO PONTE]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `src/modules/uploads/view.py:17-19` e `src/modules/uploads/__init__.py:5,51` |
| **Função** | `open_files_browser()` re-export e `UploadsFrame` classe-fachada |
| **Quem importa `open_files_browser`** | `app_actions.py:159`, `storage_ui_bridge.py:22`, `files_browser/__init__.py:11` |
| **Legado morto?** | A re-export é a ponte usada por `app_actions.py`. Com a remoção do fluxo externo, fica morta. |

---

### 2.4 — `UploadsFrame`  [CÓDIGO MORTO]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `src/modules/uploads/view.py:10-14` |
| **Classe** | `UploadsFrame.__new__()` → chama `open_files_browser()` |
| **Quem instancia** | **NINGUÉM** — zero instanciações externas no repositório inteiro |
| **Legado morto?** | **SIM** — completamente morto |
| **Depende do browser externo?** | SIM (delegaria pra browser.py) |

---

### 2.5 — `storage_ui_bridge.py` funções mortas  [CÓDIGO MORTO]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `src/utils/storage_ui_bridge.py` |
| **Funções mortas** | `open_client_files_window()` (L109-155), `_get_open_files_browser()` (L15-29), `_get_org_id_from_supabase()` (L69-86), `_client_title()` (L89-106) |
| **Variáveis mortas** | `open_files_browser = None` (L11), `_OPEN_BROWSER_LOAD_FAILED = False` (L12) |
| **Quem chama** | **NINGUÉM** — `open_client_files_window` tem zero callers no repositório |
| **Legado morto?** | **SIM** — toda a cadeia de lazy-loading + bridge pra auditoria |
| **Depende do browser externo?** | SIM |

---

### 2.6 — `storage_ui_bridge.py` funções VIVAS  [MANTER]

| Campo | Detalhe |
|-------|---------|
| **Funções vivas** | `build_client_prefix()` (L52-67), `get_clients_bucket()` (L31-40), `client_prefix_for_id()` (L42-49) |
| **Quem usa** | `helpers.py:13` importa `build_client_prefix`; `app_actions.py` e `_editor_actions_mixin.py` usam os helpers indiretamente |
| **Depende do browser externo?** | **NÃO** — funções de string/env puras, independentes de qualquer janela |

---

### 2.7 — Botão "📁 Arquivos V2 [teste]" no ctx menu  [ARTEFATO DE TESTE]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `src/modules/clientes/ui/view.py:659-672` (botão) e `view.py:1639-1695` (handler `_on_open_browser_v2`) |
| **Quem chama** | Clique direito no cliente na lista → botão azul "[V2-TESTE]" |
| **Ainda está em uso?** | Visível ao usuário final, mas marcado como teste |
| **Legado morto?** | **SIM** como bypass de teste — o fluxo oficial já é via editor |
| **Depende do browser externo?** | NÃO (abre V2 diretamente) |
| **Problema extra** | Busca org_id fazendo `repo.get_all()` + iteração O(n) |

---

### 2.8 — `browser.py` suporte de auditoria  [CÓDIGO MORTO INTERNO]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `src/modules/uploads/views/browser.py:158, 170` |
| **Lógica** | `if module == "auditoria":` → título customizado + `load_browser_status_map()` |
| **Quem passa `module="auditoria"`** | **NINGUÉM** — zero callers em todo o repositório |
| **Legado morto?** | **SIM** — feature nunca ativada |

---

### 2.9 — `action_bar.py` (ActionBar widget)  [EXCLUSIVO DO V1a]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `src/modules/uploads/views/action_bar.py` |
| **Quem importa** | **Apenas** `browser.py:43` (`from .action_bar import ActionBar`) |
| **Depende do browser externo?** | **SIM** — componente exclusivo do V1a |
| **Note** | V2 tem seus botões inline no `_build_ui()` — não usa ActionBar |

---

### 2.10 — `get_current_client_storage_prefix()`  [ATIVO — INDEPENDENTE]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `src/modules/main_window/views/main_window_actions.py:316-345` |
| **Quem chama** | `app_actions.py:233` (fluxo de upload `enviar_para_supabase`) |
| **Depende do browser externo?** | **NÃO** — apenas constrói string `{org_id}/{client_id}`, sem imports de browser. Só tem um comentário mencionando `open_files_browser`. |

---

### 2.11 — `subpastas_config.py` / `ensure_subpastas`  [ATIVO — INDEPENDENTE]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `src/utils/subpastas_config.py`, `src/utils/file_utils/path_utils.py`, `src/core/app_core.py`, `src/core/services/clientes_service.py`, `src/core/services/lixeira_service.py` |
| **O que faz** | Gerencia **pastas locais do disco** (SIFAP, ANVISA, etc.) — não tem NADA a ver com o browser de storage no Supabase |
| **Depende do browser externo?** | **NÃO** — sistema de pastas locais, completamente ortogonal |
| **Nome confuso** | O handler `"subpastas"` em keybindings aponta para `open_client_storage_subfolders` (browser Supabase), enquanto `ensure_subpastas` gerencia pastas locais. São dois conceitos com o mesmo nome. |

---

### 2.12 — `ProgressDialog` usado pelo ZIP no V1a  [COMPARTILHADO — NÃO REMOVER]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `src/ui/components/progress_dialog.py` |
| **Quem usa** | `browser.py:35` (V1a ZIP), `upload_dialog.py:23`, `uploader_supabase.py:31`, `feedback.py:26,399` |
| **Depende do browser externo?** | **NÃO** — componente genérico de UI, usado por módulos independentes |
| **Risco de remover junto** | **ALTO** — usado por upload e feedback. NÃO pode ser deletado com browser.py |

---

### 2.13 — `files_browser/utils.py` utilitários  [COMPARTILHADO — NÃO REMOVER]

| Campo | Detalhe |
|-------|---------|
| **Arquivo** | `src/ui/files_browser/utils.py` |
| **Funções** | `sanitize_filename()` (só browser.py), `suggest_zip_filename()` (só browser.py), `format_file_size()` (uploader_supabase + client_form_upload_helpers) |
| **Risco** | `format_file_size()` é usado fora do V1a. O módulo `utils.py` sobrevive, mas `sanitize_filename` e `suggest_zip_filename` perdem todos os callers |

---

## 3. ITENS PARA REMOÇÃO FUTURA

### 3A — Pode sair (zero risco)

| # | Item | Arquivo | Linhas | Motivo |
|---|------|---------|--------|--------|
| 1 | `open_client_files_window()` | `storage_ui_bridge.py` | L109-155 | Zero callers |
| 2 | `_get_open_files_browser()` | `storage_ui_bridge.py` | L15-29 | Usado só por item 1 (morto) |
| 3 | `_get_org_id_from_supabase()` | `storage_ui_bridge.py` | L69-86 | Usado só por item 1 (morto) |
| 4 | `_client_title()` | `storage_ui_bridge.py` | L89-106 | Usado só por item 1 (morto) |
| 5 | Variável global `open_files_browser` | `storage_ui_bridge.py` | L11 | Suporte ao lazy-load morto |
| 6 | Flag `_OPEN_BROWSER_LOAD_FAILED` | `storage_ui_bridge.py` | L12 | Suporte ao lazy-load morto |
| 7 | `UploadsFrame` classe | `view.py` | L10-14 | Zero instanciações externas |
| 8 | `UploadsFrame` re-export | `__init__.py` | L5, L50 | Zero importações externas |

### 3B — Pode sair (baixo risco — decisão de produto torna desnecessário)

| # | Item | Arquivo | Linhas | Motivo |
|---|------|---------|--------|--------|
| 9 | `open_client_storage_subfolders()` | `app_actions.py` | L156-194 | Handler do Ctrl+S — decisão de produto mata |
| 10 | `ver_subpastas()` | `app_actions.py` | L198-200 | Alias deprecated do item 9 |
| 11 | `open_client_storage_subfolders()` delegador | `main_window.py` | L535-537 | Delegador do item 9 |
| 12 | `ver_subpastas()` delegador | `main_window.py` | L539-541 | Delegador do item 10 |
| 13 | `_log_call(App.open_client_storage_subfolders)` | `main_window.py` | L772 | Decorador do item 11 |
| 14 | `_log_call(App.ver_subpastas)` | `main_window.py` | L773 | Decorador do item 12 |
| 15 | Bind `Ctrl+S` → `subpastas` | `keybindings.py` | L34 | Atalho que ativa o fluxo externo |
| 16 | Wiring `"subpastas"` no bootstrap | `bootstrap.py` | L159 | Conecta atalho ao handler |
| 17 | `open_files_browser()` re-export | `view.py` | L17-19 | Ponte usada por app_actions; sem caller restante |
| 18 | `open_files_browser` em `__all__` | `__init__.py` | L51 | Re-export que ficará sem caller |
| 19 | Botão "📁 Arquivos V2 [teste]" | `clientes/ui/view.py` | L659-672 | Artefato de teste |
| 20 | `_on_open_browser_v2()` handler | `clientes/ui/view.py` | L1639-1695 | Handler do botão teste |

### 3C — Arquivos inteiros que podem ser DELETADOS

| # | Arquivo | Linhas | Motivo |
|---|---------|--------|--------|
| 21 | `src/modules/uploads/views/browser.py` | 955 | Browser V1a inteiro |
| 22 | `src/modules/uploads/views/action_bar.py` | ~60 | Usado EXCLUSIVAMENTE por browser.py |

### 3D — Precisa de atualização, NÃO remoção

| # | Item | Arquivo | O que fazer |
|---|------|---------|-------------|
| 23 | Docstring referenciando browser.py | `files_browser/__init__.py` | Atualizar referência → browser_v2.py |
| 24 | Comentário mencionando `open_files_browser` | `main_window_actions.py:322,340` | Atualizar 2 comentários |

---

## 4. RISCOS

### 4.1 — Dependências compartilhadas que NÃO devem ser apagadas junto

| Componente | Arquivo | Quem mais usa |
|-----------|---------|---------------|
| `ProgressDialog` | `src/ui/components/progress_dialog.py` | `upload_dialog.py`, `uploader_supabase.py`, `feedback.py` |
| `FileList` | `src/modules/uploads/views/file_list.py` | `browser_v2.py` (V2) — o V2 importa e usa diretamente |
| `build_client_prefix()` | `storage_ui_bridge.py` | `helpers.py:13` — usado pelo editor e V2 |
| `get_clients_bucket()` | `storage_ui_bridge.py` | `helpers.py` (indiretamente) |
| `client_prefix_for_id()` | `storage_ui_bridge.py` | `helpers.py`, `_editor_actions_mixin.py`, `_on_open_browser_v2` |
| `format_file_size()` | `files_browser/utils.py` | `uploader_supabase.py`, `client_form_upload_helpers.py` |
| `prepare_hidden_window` / `show_centered_no_flash` | `src/ui/window_utils.py` | `client_editor_dialog.py`, `download_result_dialog.py` |
| `set_win_dark_titlebar` | `src/ui/dark_window_helper.py` | Outros dialogs |
| `load_browser_status_map()` | `src/utils/prefs.py:494` | **Apenas** browser.py — mas `prefs.py` tem dezenas de outras funções, não pode ser deletado |

### 4.2 — O que pode quebrar se remover errado

| Cenário errado | O que quebra |
|----------------|-------------|
| Deletar `storage_ui_bridge.py` inteiro | `helpers.py:13` tem `from src.utils.storage_ui_bridge import build_client_prefix` → ImportError → **editor e V2 quebram** |
| Deletar `file_list.py` | `browser_v2.py:71` importa FileList → V2 quebra |
| Deletar `files_browser/utils.py` | `uploader_supabase.py:33` e `client_form_upload_helpers.py:24` → import error |
| Remover `open_files_browser` de `__init__.py` sem remover caller em `app_actions.py` primeiro | ImportError em produção se Ctrl+S for pressionado |
| Remover handler sem remover bind Ctrl+S | `_wrap(None)` em keybindings → silenciosamente engole (fn callable check retorna False), mas `"subpastas"` vira chave morta no dict |

### 4.3 — O que NÃO tem risco oculto

| Ação | Por que é segura |
|------|-----------------|
| Deletar `browser.py` | V2 não faz nenhum import de `browser.py`. Zero referências cruzadas confirmadas |
| Deletar `action_bar.py` | Usado exclusivamente por `browser.py`. Se `browser.py` sai, `action_bar.py` pode sair junto |
| Remover `open_client_storage_subfolders` de `app_actions.py` | Editor usa `_on_arquivos()` → `open_files_browser_v2` diretamente. Caminhos completamente separados |
| Remover bind Ctrl+S | Nenhum outro handler depende da tecla `<Control-s>` |
| Remover botão V2-TESTE | Fluxo oficial é via editor; botão de teste não é usado em produção |

---

## 5. ORDEM RECOMENDADA DA PRÓXIMA EXECUÇÃO

### Passo 1 — Limpar código morto (zero risco)
Remover do `storage_ui_bridge.py`:
- Variável `open_files_browser = None` (L11)
- Flag `_OPEN_BROWSER_LOAD_FAILED` (L12)
- `_get_open_files_browser()` (L15-29)
- `_get_org_id_from_supabase()` (L69-86)
- `_client_title()` (L89-106)
- `open_client_files_window()` (L109-155)
- Import de `Mapping` e `Optional` se ficarem órfãos
- Atualizar docstring do módulo

**Resultado**: `storage_ui_bridge.py` fica com ~40 linhas (3 funções vivas + imports)

### Passo 2 — Remover `UploadsFrame` e re-export chain
- Deletar `class UploadsFrame` de `view.py`
- Remover `UploadsFrame` de `__init__.py` (import L5 + `__all__` L50)

### Passo 3 — Desligar o atalho Ctrl+S e remover handler
- Em `keybindings.py:34`: remover a linha `b("<Control-s>", _wrap(handlers.get("subpastas")))`
- Em `main_window_bootstrap.py:159`: remover `"subpastas": app.open_client_storage_subfolders`
- Em `app_actions.py`: remover `open_client_storage_subfolders()` (L156-194) e `ver_subpastas()` (L198-200)
- Em `main_window.py`: remover delegadores `open_client_storage_subfolders()` (L535-537), `ver_subpastas()` (L539-541), ambos `_log_call` (L772-773)

### Passo 4 — Remover re-export de `open_files_browser`
- Em `view.py`: remover `def open_files_browser(...)` (L17-19) e import de `browser as browser_view` (L7)
- Em `__init__.py`: remover `open_files_browser` de import (L5) e `__all__` (L51)
- Em `files_browser/__init__.py`: remover referência na docstring (L11)

### Passo 5 — Deletar browser V1a e ActionBar exclusiva
- Deletar `src/modules/uploads/views/browser.py` (955 linhas)
- Deletar `src/modules/uploads/views/action_bar.py` (~60 linhas)

### Passo 6 — Remover botão V2-TESTE do ctx menu
- Em `clientes/ui/view.py`: remover bloco do botão "📁 Arquivos V2 [teste]" (L659-672)
- Em `clientes/ui/view.py`: remover handler `_on_open_browser_v2()` inteiro (L1639-1695)

### Passo 7 — Limpar comentários residuais
- `main_window_actions.py:322` e L340: atualizar comentários que mencionam `open_files_browser`

### Passo 8 — Atualizar testes
- `test_ui_subpastas_affordance.py`: remover/adaptar testes que verificam Ctrl+S → subpastas, `ver_subpastas` aliases, bootstrap wiring
- `test_p3_final_subpastas.py`: remover/adaptar testes que verificam bootstrap → `open_client_storage_subfolders`
- Verificar se algum outro test faz referência ao bind `<Control-s>` ou ao handler subpastas

### Passo 9 — Rodar todos os testes
```
python -m pytest --timeout=30 -q
```
**Expectativa**: 949 testes ou menos (testes removidos), todos passando.

---

## 6. ARQUIVOS PRINCIPAIS ENVOLVIDOS

### Arquivos a DELETAR
| Arquivo | Motivo |
|---------|--------|
| `src/modules/uploads/views/browser.py` | Browser V1a inteiro — 955 linhas |
| `src/modules/uploads/views/action_bar.py` | Widget exclusivo do V1a — ~60 linhas |

### Arquivos a EDITAR
| Arquivo | O que muda |
|---------|-----------|
| `src/utils/storage_ui_bridge.py` | Remover 6 funções/variáveis mortas (fica ~40 linhas) |
| `src/modules/uploads/view.py` | Remover `UploadsFrame` + `open_files_browser` re-export |
| `src/modules/uploads/__init__.py` | Remover `UploadsFrame` + `open_files_browser` de imports e `__all__` |
| `src/core/keybindings.py` | Remover bind `<Control-s>` |
| `src/modules/main_window/views/main_window_bootstrap.py` | Remover wiring `"subpastas"` |
| `src/modules/main_window/app_actions.py` | Remover `open_client_storage_subfolders` + `ver_subpastas` |
| `src/modules/main_window/views/main_window.py` | Remover delegadores + `_log_call` wrappers |
| `src/modules/clientes/ui/view.py` | Remover botão V2-TESTE + handler |
| `src/ui/files_browser/__init__.py` | Atualizar docstring |
| `src/modules/main_window/views/main_window_actions.py` | Atualizar 2 comentários |
| `tests/test_ui_subpastas_affordance.py` | Adaptar/remover testes do fluxo externo |
| `tests/test_p3_final_subpastas.py` | Adaptar/remover testes do fluxo externo |

### Arquivos que NÃO mudam
| Arquivo | Motivo |
|---------|--------|
| `src/modules/uploads/views/browser_v2.py` | V2 oficial — não precisa de adaptação |
| `src/modules/uploads/views/file_list.py` | Compartilhado V1a + V2 — V2 continua usando |
| `src/modules/uploads/components/helpers.py` | Usa `build_client_prefix` (sobrevive em bridge) |
| `src/ui/files_browser/utils.py` | `format_file_size()` usado por upload — sobrevive |
| `src/ui/files_browser/constants.py` | Constantes compartilhadas |
| `src/ui/components/progress_dialog.py` | Usado por upload/feedback — independente |
| `src/modules/clientes/ui/views/_editor_actions_mixin.py` | Fluxo oficial V2 via editor — intocado |
| `src/modules/clientes/ui/views/_editor_ui_mixin.py` | Botão "Arquivos" do editor — intocado |
| `src/utils/subpastas_config.py` | Gerencia pastas locais do disco — nada a ver com browser |
| `src/core/app_core.py` | `ensure_subpastas` é disco local, não storage |
| `src/modules/main_window/views/main_window_actions.py` | `get_current_client_storage_prefix` — independente (só atualizar comentários) |

---

## 7. VALIDAÇÃO: DECISÃO DE PRODUTO vs CÓDIGO

| Pergunta | Resposta | Evidência |
|----------|---------|-----------|
| Dá pra eliminar Ctrl+S sem quebrar o editor? | **SIM** | Editor usa `_on_arquivos()` → `open_files_browser_v2()` via `_editor_actions_mixin.py:190`. Caminho completamente independente do `Ctrl+S` → `open_client_storage_subfolders()`. Zero referências cruzadas. |
| Alguma parte do app depende obrigatoriamente do browser externo? | **NÃO** | O único caller real (`app_actions.py:186`) é o handler do Ctrl+S. Removido o handler, nenhum outro código tenta abrir `browser.py`. |
| "Subpastas" sustenta alguma função necessária? | **NÃO** | O conceito "subpastas" tem dois significados separados: (1) `ensure_subpastas` = pastas locais no disco (SIFAP, ANVISA, etc.) — **independente, sobrevive**; (2) handler `"subpastas"` no keybindings = atalho Ctrl+S → browser externo — **esse é o alvo da remoção**. |
| O V2 do editor usa algo do fluxo externo indiretamente? | **NÃO** | V2 importa: `FileList`, `SupabaseStorageAdapter`, `DownloadResultDialog`, service functions, UI tokens. Nenhum desses vem de `browser.py`, `app_actions`, ou `storage_ui_bridge` (exceto `build_client_prefix` via helpers, que sobrevive). |

---

## 8. O QUE VEM DEPOIS

### Polimento visual do V2
Após a remoção do fluxo externo, o V2 será o **único browser**. Candidatos a polimento:

1. ~`_status_cache`~ — inicializado como `{}` mas nunca populado. Se auditoria não foi ativada, pode ser removido ou mantido como no-op.
2. Download ZIP — V2 usa implementação inline com `tempfile + zipfile`. Funcional, mas poderia ser unificado com `download_folder_zip()` do service.
3. `_on_open_browser_v2` em `clientes/ui/view.py` — será deletado nesta fase, mas se fosse mantido, o `repo.get_all()` + O(n) iteração precisaria fix.

### Janelas/dialogs suspeitos para futura auditoria de flash/lifecycle/foco

| Dialog | Arquivo | Por que auditar |
|--------|---------|----------------|
| `UploadDialog` | `views/upload_dialog.py` | CTkToplevel — verificar anti-flash, grab, foco |
| `DownloadResultDialog` | `ui/dialogs/download_result_dialog.py` | Usa `prepare_hidden_window` — verificar consistência |
| `ProgressDialog` | `ui/components/progress_dialog.py` | CTkToplevel — grab_set, lifecycle |
| `PDFBatchProgressDialog` | `ui/progress/pdf_batch_progress.py` | CTkToplevel — centralização, _windows_set_titlebar_color |
| `ClientEditorDialog` | `clientes/ui/views/client_editor_dialog.py` | Principal — já usa anti-flash, mas grab_set/release flow com V2 é complexo |
| Upload interativo | `uploader_supabase.py` | CTkToplevel — padrão anti-flash diferente (sem `prepare_hidden_window`) |
| Client form upload | `client_form_upload_helpers.py` | CTkToplevel — sem anti-flash explícito |
