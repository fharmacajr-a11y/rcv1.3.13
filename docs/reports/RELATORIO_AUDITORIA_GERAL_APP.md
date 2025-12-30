# 📋 RELATÓRIO DE AUDITORIA GERAL — RC Gestor de Clientes

**Data:** 29 de dezembro de 2025  
**Branch:** `main`  
**Tag base:** `v1.5.27`  
**Commits à frente do remote:** —  
**Analista:** Copilot AI (Claude Opus 4.5)

---

## 📊 RESUMO EXECUTIVO

| Métrica | Valor |
|---------|-------|
| **Arquivos Python (src/)** | 458 |
| **Arquivos de teste** | 499 |
| **Linhas totais (top 25 arquivos)** | ~16.500 LOC |
| **Tags de versão** | v1.5.27 (base), v1.4.93, v1.1.45-qa-final, v1.0.29 |
| **Estado Git** | Working tree clean |
| **TODOs/FIXMEs ativos** | ~1 (registrado em TECH_DEBT_REGISTER) |
| **Módulos deprecated** | ~25+ shims/wrappers em `src/ui/` |
| **Exceções genéricas** | 100+ instâncias `except Exception` |

### Saúde Geral: 🟡 MÉDIA

O aplicativo está funcional mas apresenta **dívida técnica acumulada** principalmente em:
1. Tratamento de exceções genéricas (sem tipagem específica)
2. Acoplamento UI↔Lógica (messagebox em services)
3. Arquivos longos que centralizam responsabilidades
4. Módulos deprecated ainda presentes como shims

---

## 📐 PASSO 1 — SNAPSHOT DO ESTADO

### 1.1 Git Status
```
Branch: main
Tag base: v1.5.27
Working tree: clean
```

### 1.2 Histórico Recente (últimos 15 commits)
```
2cdc4b9 test: fix mocks messagebox (MF52.3) e ajustes relacionados
514ac2b test: robustez stubs tkinter e ajustes smoke UI; vulture cleanups
00df9f5 docs: relatório QA pós MF52.3 - análise completa
b92b533 chore: limpeza onda 1 (arquivos históricos e artefatos)
d302ab2 (tag: v1.4.93) chore: release v1.4.93 - security & housekeeping
6d0cef2 chore: cleanup artefatos locais e reorganizar docs
8054dd5 chore: limpar artefatos locais e ignorar exports/*.zip
31fab69 style: format export.py (ruff)
2f25a99 docs: atualizar TECH_DEBT_REGISTER com hash do commit
e35a0ab feat(clientes): exportar clientes para CSV (e XLSX opcional)
66c26c5 feat(hub): adicionar tooltips nos botões do painel
7f2a60e feat(anvisa): preencher created_by ao criar demanda
7125dac docs: marcar P3 (dirty check) como concluído
43b52f0 feat(clientes): confirmação ao cancelar com alterações não salvas
6d04866 docs: P2-004 - Criar registro de dívida técnica
```

### 1.3 Tags de Versão
| Tag | Descrição |
|-----|-----------|
| `v1.5.27` | Versão base desta auditoria |
| `v1.4.93` | Release anterior - security & housekeeping |
| `v1.1.45-qa-final` | Marco de QA |
| `v1.0.29` | Versão inicial estável |

---

## 🗺️ PASSO 2 — MAPA DO PROJETO (ARQUITETURA REAL)

### 2.1 Estrutura de Pastas Top-Level

| Pasta | Papel | Classe |
|-------|-------|--------|
| `src/` | **Código principal do aplicativo** | A (Runtime) |
| `adapters/` | Adaptadores de storage (abstração) | A (Runtime) |
| `infra/` | Infraestrutura (Supabase, HTTP, net, 7zip binários) | A (Runtime) |
| `data/` | Domain types, repositórios Supabase | A (Runtime) |
| `security/` | Módulo de criptografia | A (Runtime) |
| `helpers/` | Utilitários auxiliares compartilhados | A (Runtime) |
| `config/` | Configurações (OpenAI key example) | A (Runtime) |
| `assets/` | Ícones/imagens UI (login, topbar, módulos) | A (Runtime) |
| `migrations/` | SQL migrations para banco | A/B |
| `third_party/` | Vendor libs (7zip binários) | A/B |
| `typings/` | Type stubs (tkinter, ttkbootstrap) | C (Dev) |
| `tests/` | Suite completa de testes (499 arquivos) | C (Dev) |
| `docs/` | Documentação técnica, ADRs, relatórios | C (Dev) |
| `scripts/` | Scripts de automação (coverage, audit) | C (Dev) |
| `reports/` | Relatórios bandit/ruff/pyright | C/D |
| `tools/` | Ferramentas auxiliares de desenvolvimento | C (Dev) |
| `installer/` | Recursos para instalador Inno Setup | B (Build) |

### 2.2 Entrypoints Identificados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| `main.py` | **Principal** | Entry point que chama `src.app_gui` via runpy |
| `src/app_gui.py` | **GUI Bootstrap** | Inicializa Tkinter, login, MainWindow |
| `src/cli.py` | **CLI Args** | Parser de argumentos (--no-splash, etc.) |
| `rcgestor.spec` | **Build** | Spec do PyInstaller |
| `start_app.bat` | **Launcher** | Script batch para Windows |

### 2.3 Localização da UI (Tkinter/ttkbootstrap)

```
src/ui/                    → UI LEGADA (shims deprecated)
  ├── components/          → Componentes reutilizáveis (buttons, inputs, lists)
  ├── widgets/             → Widgets customizados (autocomplete, busy)
  ├── dialogs/             → Diálogos (file_select, pdf_converter)
  ├── progress/            → Progress dialogs
  ├── hub/                 → DEPRECATED → remapeia para src/modules/hub
  ├── forms/               → DEPRECATED → remapeia para src/modules/clientes/forms
  ├── lixeira/             → DEPRECATED → remapeia para src/modules/lixeira
  ├── main_window/         → DEPRECATED → remapeia para src/modules/main_window
  ├── login/               → DEPRECATED → remapeia para src/modules/login
  ├── login_dialog.py      → LoginDialog (UI real)
  ├── splash.py            → Splash screen
  ├── topbar.py            → TopBar (real)
  ├── menu_bar.py          → DEPRECATED (UI antiga)
  └── status_footer.py     → StatusFooter (real)

src/modules/               → UI MODERNA (módulos organizados)
  ├── main_window/views/   → MainWindow, layout, actions
  ├── hub/views/           → HubScreen, dashboard, dialogs
  ├── clientes/views/      → MainScreen, forms
  ├── anvisa/views/        → AnvisaScreen
  ├── passwords/views/     → PasswordsScreen
  ├── uploads/views/       → UploadsBrowserWindow
  ├── pdf_preview/views/   → PdfViewerWin
  ├── lixeira/views/       → Lixeira window
  └── ...
```

### 2.4 Localização do Core/Regras (Controllers/Services)

```
src/core/                  → NÚCLEO DO APLICATIVO
  ├── auth/                → Autenticação (auth.py)
  ├── session/             → Gerenciamento de sessão
  ├── services/            → Services compartilhados (clientes, profiles)
  ├── db_manager/          → Acesso DB SQLite (legado local)
  ├── bootstrap.py         → Configuração inicial (logging, HiDPI, health)
  ├── auth_bootstrap.py    → Flow de login
  ├── navigation_controller.py → Navegação entre telas
  ├── notifications_service.py → Polling de notificações
  └── status_monitor.py    → Monitor de conectividade

src/modules/*/             → LÓGICA POR MÓDULO
  ├── hub/
  │   ├── controller.py    → HubController
  │   ├── dashboard_service.py → DashboardSnapshot
  │   ├── services/        → authors_service, lifecycle_service
  │   └── viewmodels/      → notes_vm
  ├── clientes/
  │   ├── service.py       → CRUD clientes
  │   ├── viewmodel.py     → ClientesViewModel
  │   └── forms/           → Controllers de formulários
  ├── anvisa/
  │   └── services/anvisa_service.py
  ├── uploads/
  │   ├── service.py       → Upload service
  │   └── repository.py    → Upload repository
  └── ...
```

### 2.5 Localização de Infra/Adapters/Data

```
infra/                     → INFRAESTRUTURA
  ├── supabase/            → Clientes Supabase
  │   ├── db_client.py     → get_supabase(), health checks
  │   ├── storage_client.py → baixar_pasta_zip()
  │   ├── auth_client.py   → bind_postgrest_auth_if_any()
  │   └── http_client.py   → HTTPX_CLIENT, timeouts
  ├── http/                → HTTP helpers (retry)
  ├── repositories/        → (vazio ou shim)
  ├── net_status.py        → Status de conectividade
  ├── net_session.py       → Sessão HTTP
  └── healthcheck.py       → Health check utilities

adapters/
  └── storage/             → Abstração de storage

data/
  ├── supabase_repo.py     → Repositório Supabase
  ├── domain_types.py      → Tipos de domínio
  └── auth_bootstrap.py    → Auth bootstrap (data layer)
```

### 2.6 Mapa Textual de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENTRY POINTS                                   │
│    main.py ──► src/app_gui.py ──► LoginDialog ──► MainWindow               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              UI LAYER                                       │
│                                                                             │
│  src/modules/*/views/          src/ui/components/        src/ui/*.py       │
│  ├── HubScreen                 ├── buttons.py            ├── topbar.py     │
│  ├── MainScreen (Clientes)     ├── inputs.py             ├── splash.py     │
│  ├── AnvisaScreen              ├── lists.py              ├── login_dialog  │
│  ├── PasswordsScreen           ├── notifications/        └── status_footer │
│  ├── PdfViewerWin              └── progress_dialog.py                      │
│  └── UploadsBrowser                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTROLLER / SERVICE LAYER                          │
│                                                                             │
│  src/modules/*/              src/core/                                      │
│  ├── controller.py           ├── bootstrap.py                              │
│  ├── service.py              ├── auth_bootstrap.py                         │
│  ├── viewmodel.py            ├── navigation_controller.py                  │
│  └── forms/                  ├── notifications_service.py                  │
│                              └── services/                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INFRA / ADAPTER LAYER                             │
│                                                                             │
│  infra/supabase/             infra/                    adapters/storage/   │
│  ├── db_client.py            ├── net_status.py                             │
│  ├── storage_client.py       ├── net_session.py                            │
│  ├── auth_client.py          ├── healthcheck.py                            │
│  └── http_client.py          └── http/retry.py                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                     │
│                                                                             │
│  data/                       src/core/db_manager/      Supabase Cloud      │
│  ├── supabase_repo.py        └── db_manager.py         (PostgreSQL)        │
│  └── domain_types.py            (SQLite local)                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 PASSO 3 — CHECAGENS DE RISCO (BUSCAS GUIADAS)

### 3.1 Exceções Genéricas (`except Exception`)

**Total encontrado em `src/`:** 100+ instâncias

| Severidade | Probabilidade | Impacto | Mitigação |
|------------|---------------|---------|-----------|
| **P2** | Alta | Mascara erros reais, dificulta debug | Tipar exceções específicas |

#### Arquivos mais afetados:

| Arquivo | Ocorrências | Contexto |
|---------|-------------|----------|
| `src/app_core.py` | 19 | CRUD clientes, pastas |
| `src/app_status.py` | 12 | Status/health checks |
| `src/modules/uploads/views/browser.py` | 13 | File browser |
| `src/modules/uploads/uploader_supabase.py` | 14 | Upload flow |
| `src/modules/uploads/service.py` | 9 | Upload service |
| `src/modules/pdf_preview/views/pdf_viewer_actions.py` | 9 | PDF actions |
| `src/modules/pdf_preview/views/main_window.py` | ~5 | PDF viewer |

#### Exemplos críticos:

```python
# src/app_core.py:17 - Import silencioso
try:
    from src.modules.lixeira import abrir_lixeira
except Exception:
    _module_abrir_lixeira = None  # Pode mascarar ImportError real

# src/app_core.py:52 - Resolução de cliente silenciada
try:
    cliente = get_cliente_by_id(pk)
except Exception:
    log.exception("Failed to resolve client...")
    return None  # Pode esconder problemas de conexão

# src/app_status.py:39 - Health check catch-all
try:
    # health check code
except Exception as exc:
    log.debug("...")  # Debug level mascara falhas reais
```

#### Mitigação recomendada:
1. Substituir `except Exception` por tipos específicos: `ConnectionError`, `TimeoutError`, `ValueError`
2. Usar `except Exception` apenas em top-level handlers com logging adequado
3. Adicionar `# noqa: BLE001` apenas quando documentado

---

### 3.2 TODO/FIXME/HACK/XXX Ativos

**Total encontrado em `src/`:** ~1 ativo (registrado)

| Arquivo | Linha | Tag | Conteúdo |
|---------|-------|-----|----------|
| `src/modules/hub/views/hub_screen_view.py` | 383 | TODO | `TODO ANVISA-only: no futuro, pode-se implementar...` |

**Status:** O projeto passou por limpeza extensiva de TODOs. O `TECH_DEBT_REGISTER.md` documenta 4 itens concluídos recentemente.

---

### 3.3 Padrões de Risco: eval/exec/subprocess

#### `eval()`:
| Arquivo | Linha | Contexto | Severidade | Mitigação |
|---------|-------|----------|------------|-----------|
| `src/modules/hub/services/authors_service.py` | 93 | `ast.literal_eval(rc_initials_map)` | **P3** (Baixo) | ✅ Usa `ast.literal_eval` (seguro) |

**Análise:** `ast.literal_eval` é seguro - só aceita literais Python (strings, números, dicts, lists). Não há uso de `eval()` inseguro.

#### `exec()`:
**Nenhum uso encontrado.** ✅

#### `subprocess`:
| Arquivo | Linha | Contexto | Severidade | Mitigação |
|---------|-------|----------|------------|-----------|
| `src/modules/uploads/service.py` | 14 | Import com `# nosec B404` | P4 | Documentado |
| `src/modules/uploads/service.py` | 413 | `subprocess.Popen([open_cmd, local_path])` | P3 | `# nosec B603` |
| `src/modules/uploads/service.py` | 420 | `subprocess.Popen([xdg_cmd, local_path])` | P3 | `# nosec B603` |

**Análise:** Uso controlado para abrir arquivos locais. **Não usa `shell=True`**. Anotado com `nosec` para Bandit.

---

### 3.4 `messagebox` fora de UI (Acoplamento)

**Total encontrado:** 80+ instâncias

| Severidade | Probabilidade | Impacto |
|------------|---------------|---------|
| **P2** | Alta | Acoplamento UI↔Lógica, dificulta testes |

#### Arquivos fora de `views/`:

| Arquivo | Ocorrências | Contexto | Risco |
|---------|-------------|----------|-------|
| `src/utils/network.py` | 2 | `messagebox.askokcancel` para confirm offline | **Médio** |
| `src/utils/helpers/cloud_guardrails.py` | 1 | `messagebox.showinfo` | **Médio** |
| `src/utils/errors.py` | 2 | `messagebox.showerror` em exception handler | **Baixo** (top-level) |
| `src/shared/storage_ui_bridge.py` | 6 | `messagebox.*` em bridge | **Alto** |
| `src/modules/uploads/uploader_supabase.py` | 15 | messagebox em upload flow | **Alto** |

#### Exemplos problemáticos:

```python
# src/utils/network.py:111-117 - Cria Tk root no import
def check_internet_connectivity():
    ...
    if os.getenv("RC_NO_GUI_ERRORS") != "1":
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()  # ⚠️ Cria janela Tk temporária
        root.withdraw()
        result = messagebox.askokcancel(...)
```

```python
# src/shared/storage_ui_bridge.py:117-119 - Bridge com UI direta
from tkinter import messagebox
messagebox.showwarning("Arquivos", "Modo offline.")
```

#### Mitigação recomendada:
1. Criar protocolo/interface para feedback de UI
2. Injetar callbacks de UI nos services
3. Usar padrão Result/Either para retornar erros sem UI

---

### 3.5 Side-effects em Import

#### Criação de Tk no import:
| Arquivo | Evidência | Severidade | Impacto |
|---------|-----------|------------|---------|
| `src/utils/network.py:114` | `root = tk.Tk()` dentro de função | **P2** | Pode travar em ambientes sem display |

**Nota:** O Tk é criado dentro de função `check_internet_connectivity()`, não no import direto. Porém, pode ser chamado cedo no startup.

#### Leitura de arquivo no import:
| Arquivo | Evidência | Severidade |
|---------|-----------|------------|
| `src/utils/themes.py` | `load_theme()` lê `config_theme.json` | P3 (Baixo) |
| `src/config/environment.py` | `load_env()` lê `.env` | P3 (Baixo) |

**Análise:** A maioria dos side-effects está em funções chamadas explicitamente, não no import direto. ✅

---

### 3.6 Uso de Variáveis Globais

**Total encontrado:** 33 instâncias de `global`

| Arquivo | Variável | Propósito | Risco |
|---------|----------|-----------|-------|
| `src/core/session/session.py` | `_CURRENT_USER` | Singleton de sessão | Médio |
| `src/core/auth/auth.py` | `login_attempts` | Rate limiting | Baixo |
| `src/core/services/clientes_service.py` | `_clients_cache` | Cache de clientes | Médio |
| `src/modules/lixeira/views/lixeira.py` | `_OPEN_WINDOW` | Singleton de janela | Médio |
| `src/modules/hub/recent_activity_store.py` | `_store_instance` | Singleton | Médio |
| `src/modules/chatgpt/service.py` | `_client` | Cliente OpenAI | Baixo |

**Risco:** Globals dificultam testes e podem causar state leaks entre tests.

---

## 🔥 PASSO 4 — HOTSPOTS DE MANUTENÇÃO

### 4.1 Top 25 Arquivos Mais Longos (LOC)

| # | Arquivo | Linhas | Por que é hotspot |
|---|---------|--------|-------------------|
| 1 | `tests/unit/modules/hub/test_dashboard_service.py` | 2106 | Arquivo de teste grande |
| 2 | `tests/unit/modules/hub/test_dashboard_service_mf43.py` | 1728 | Arquivo de teste |
| 3 | `tests/unit/modules/anvisa/test_anvisa_service.py` | 1291 | Arquivo de teste |
| 4 | `tests/unit/modules/hub/views/test_dashboard_center.py` | 938 | Arquivo de teste |
| 5 | `tests/unit/modules/uploads/test_uploads_service_fase32.py` | 906 | Arquivo de teste |
| 6 | **`src/modules/pdf_preview/views/main_window.py`** | **895** | ⚠️ UI + lógica de PDF |
| 7 | `tests/unit/modules/hub/test_hub_screen_controller_mf42.py` | 883 | Arquivo de teste |
| 8 | **`src/modules/hub/dashboard_service.py`** | **862** | ⚠️ Service complexo |
| 9 | `tests/unit/modules/clientes/forms/test_prepare_round12.py` | 852 | Arquivo de teste |
| 10 | **`src/modules/hub/views/dashboard_center.py`** | **805** | ⚠️ UI do dashboard |
| 11 | **`src/modules/clientes/views/main_screen_helpers.py`** | **797** | ⚠️ Helpers misturados |
| 12 | `tests/unit/modules/hub/views/test_hub_screen_helpers_fase01.py` | 792 | Arquivo de teste |
| 13 | `tests/unit/data/test_supabase_repo.py` | 780 | Arquivo de teste |
| 14 | **`src/modules/anvisa/views/_anvisa_handlers_mixin.py`** | **767** | ⚠️ Mixin complexo |
| 15 | `tests/unit/modules/main_window/test_app_actions_fase45.py` | 751 | Arquivo de teste |
| 16 | **`src/modules/anvisa/services/anvisa_service.py`** | **725** | ⚠️ Service complexo |
| 17 | `tests/unit/modules/hub/viewmodels/test_notes_vm.py` | 720 | Arquivo de teste |
| 18 | **`src/modules/clientes/views/main_screen_controller.py`** | **690** | ⚠️ Controller grande |
| 19 | **`src/modules/hub/views/hub_screen.py`** | **681** | ⚠️ Tela principal |
| 20 | `tests/conftest.py` | 671 | Config de testes |
| 21 | **`src/modules/main_window/views/main_window_actions.py`** | **659** | ⚠️ Ações extraídas |
| 22 | **`src/modules/anvisa/views/anvisa_screen.py`** | **655** | ⚠️ Tela ANVISA |
| 23 | **`src/modules/hub/views/hub_dialogs.py`** | **640** | ⚠️ Muitos dialogs |
| 24 | **`src/modules/uploads/views/browser.py`** | **560** | ⚠️ Browser complexo |
| 25 | **`src/modules/main_window/views/main_window.py`** | **544** | ⚠️ Janela principal |

### 4.2 Análise dos Hotspots de Código

#### 4.2.1 `src/modules/pdf_preview/views/main_window.py` (895 linhas)

| Sintoma | Evidência |
|---------|-----------|
| Múltiplas responsabilidades | UI + renderização PDF + cache + zoom + scroll |
| Lógica de negócio em view | `_render_page_image()`, `pixmap_to_photoimage()` |
| PhotoImage references | `self._img_refs: Dict[int, tk.PhotoImage]` |

**Estratégia de redução:**
1. Extrair `PdfRenderService` headless
2. Separar cache management em classe própria
3. Manter apenas bindings e layout na view

#### 4.2.2 `src/modules/hub/dashboard_service.py` (862 linhas)

| Sintoma | Evidência |
|---------|-----------|
| Dataclass muito grande | `DashboardSnapshot` com 12 campos |
| Muitas queries agregadas | Obrigações, tarefas, clientes, atividades |
| Formatação de dados | `_format_due_br()`, `_parse_due_date_iso()` |

**Estratégia de redução:**
1. Dividir em sub-services: `ObligationsService`, `TasksService`
2. Extrair formatters para módulo `hub/formatters.py`
3. Criar DTOs menores para cada seção do dashboard

#### 4.2.3 `src/modules/clientes/views/main_screen_helpers.py` (797 linhas)

| Sintoma | Evidência |
|---------|-----------|
| Nome genérico "helpers" | Catch-all de funções |
| Mistura de responsabilidades | UI helpers + data formatting + validation |

**Estratégia de redução:**
1. Separar em `formatters.py`, `validators.py`, `ui_helpers.py`
2. Mover lógica de negócio para `viewmodel.py`

#### 4.2.4 `src/modules/anvisa/views/_anvisa_handlers_mixin.py` (767 linhas)

| Sintoma | Evidência |
|---------|-----------|
| Mixin muito grande | Deveria ser composição, não herança |
| Handlers misturados | Eventos de UI + lógica de negócio |
| `# type: ignore[attr-defined]` | Indica acoplamento com classe host |

**Estratégia de redução:**
1. Converter mixin em Controller injetado
2. Extrair handlers para funções puras
3. Usar composition over inheritance

---

## 🖥️ PASSO 5 — UI/UX E ESTABILIDADE (Tkinter/ttkbootstrap)

### 5.1 Componentes UI Críticos

| Componente | Arquivo | Criticidade |
|------------|---------|-------------|
| MainWindow (App) | `src/modules/main_window/views/main_window.py` | **Alta** |
| LoginDialog | `src/ui/login_dialog.py` | **Alta** |
| HubScreen | `src/modules/hub/views/hub_screen.py` | **Alta** |
| ClientesFrame | `src/modules/clientes/views/main_screen.py` | **Alta** |
| AnvisaScreen | `src/modules/anvisa/views/anvisa_screen.py` | **Média** |
| UploadsBrowserWindow | `src/modules/uploads/views/browser.py` | **Média** |
| PdfViewerWin | `src/modules/pdf_preview/views/main_window.py` | **Média** |
| PasswordsScreen | `src/modules/passwords/views/passwords_screen.py` | **Baixa** |

### 5.2 Padrões de PhotoImage e Ciclo de Vida

#### Arquivos com PhotoImage:

| Arquivo | Uso | Risco |
|---------|-----|-------|
| `src/ui/splash.py` | `logo_image = tk.PhotoImage(file=...)` | Mantém ref em `self._logo` ✅ |
| `src/ui/login_dialog.py` | `self._icon_email = tk.PhotoImage(...)` | Referência como atributo ✅ |
| `src/modules/pdf_preview/views/main_window.py` | `self._img_refs: Dict[int, PhotoImage]` | Cache com referências ✅ |
| `src/ui/components/misc.py` | `_ICON_CACHE: dict[tuple, PhotoImage]` | Cache global ✅ |
| `src/ui/components/inputs.py` | `search_icon: tk.PhotoImage | None` | ⚠️ Pode ser GC'd |

#### Potencial problema em inputs.py:

```python
# src/ui/components/inputs.py:142-154
search_icon: tk.PhotoImage | None = None
try:
    search_icon = tk.PhotoImage(file=icon_path)
except Exception:
    logger.debug("...")
# FIX-TESTS-002: Manter referência forte à PhotoImage
if search_icon:
    entry._search_icon_ref = search_icon  # ✅ Corrigido
```

### 5.3 Dependência de root/default root

| Arquivo | Padrão | Risco |
|---------|--------|-------|
| `src/utils/network.py:114` | `root = tk.Tk()` temporário | **Médio** - Cria root extra |
| `src/modules/main_window/views/main_window.py` | Herda de `tb.Window` | ✅ OK |

### 5.4 Uso de Toplevel/Dialogs

**Total de classes Toplevel:** 15+

| Classe | Arquivo | Tipo |
|--------|---------|------|
| `UploadsBrowserWindow` | `src/modules/uploads/views/browser.py` | `tk.Toplevel` |
| `PdfViewerWin` | `src/modules/pdf_preview/views/main_window.py` | `tk.Toplevel` |
| `NovaTarefaDialog` | `src/modules/tasks/views/task_dialog.py` | `tb.Toplevel` |
| `ClientPasswordsDialog` | `src/modules/passwords/views/client_passwords_dialog.py` | `tb.Toplevel` |
| `PasswordDialog` | `src/modules/passwords/views/password_dialog.py` | `tb.Toplevel` |
| `ClientObligationsWindow` | `src/modules/clientes/views/client_obligations_window.py` | `tb.Toplevel` |
| `ObligationDialog` | `src/modules/clientes/views/obligation_dialog.py` | `tb.Toplevel` |
| `SubpastaDialog` | `src/modules/clientes/forms/client_subfolder_prompt.py` | `tk.Toplevel` |
| `ClientPicker` | `src/modules/clientes/forms/client_picker.py` | `tk.Toplevel` |
| `ChatGPTWindow` | `src/modules/chatgpt/views/chatgpt_window.py` | `tk.Toplevel` |
| `DuplicatesDialog` | `src/modules/auditoria/views/dialogs.py` | `tk.Toplevel` |

### 5.5 Guard Rails Faltantes

| Arquivo | Problema | Mitigação Sugerida |
|---------|----------|-------------------|
| `src/ui/splash.py` | Asset ausente causa crash | ✅ Já tem `_safe_resource_path()` |
| `src/ui/login_dialog.py` | ícone ausente | ✅ Tem try/except |
| `src/ui/components/topbar_nav.py` | ícone ausente | ✅ Tem try/except |
| `src/modules/uploads/views/browser.py` | Sem check de root | ⚠️ Adicionar verificação |

---

## 🧪 PASSO 6 — TESTES: COBERTURA QUALITATIVA

### 6.1 Estrutura dos Testes

```
tests/                     (499 arquivos .py)
├── unit/                  (363 arquivos)
│   ├── modules/           ← Testes por módulo
│   │   ├── hub/           (forte cobertura)
│   │   ├── clientes/      (forte cobertura)
│   │   ├── anvisa/        (boa cobertura)
│   │   ├── uploads/       (boa cobertura)
│   │   ├── passwords/     (moderada)
│   │   └── ...
│   ├── core/              (boa cobertura)
│   ├── data/              (boa cobertura)
│   ├── infra/             (moderada)
│   └── ui/                (smoke tests)
├── integration/           (5 arquivos)
│   └── passwords/         test_passwords_flows.py
├── conftest.py            (877 linhas - robusto)
└── manual/                (testes manuais documentados)
```

### 6.2 Módulos com Testes Fortes

| Módulo | Arquivos de teste | Cobertura estimada |
|--------|-------------------|-------------------|
| `hub` | 20+ arquivos | **Alta** (dashboard, notes, lifecycle) |
| `clientes` | 15+ arquivos | **Alta** (forms, viewmodel, export) |
| `anvisa` | 10+ arquivos | **Boa** (service, handlers) |
| `uploads` | 8+ arquivos | **Boa** (service, browser) |
| `core/auth` | 5+ arquivos | **Boa** |
| `data` | 3+ arquivos | **Boa** (supabase_repo) |

### 6.3 Módulos com Proteção Fraca

| Módulo | Arquivos de teste | Gap |
|--------|-------------------|-----|
| `pdf_preview` | ~3 arquivos | Falta testar render, zoom |
| `chatgpt` | ~2 arquivos | Falta testar flow completo |
| `lixeira` | ~2 arquivos | Básico |
| `auditoria` | ~2 arquivos | Básico |
| `sites` | ~2 arquivos | Apenas UI smoke |

### 6.4 Cenários de Regressão Críticos (Smokes)

| # | Cenário | Por que é crítico | Teste existente? |
|---|---------|-------------------|------------------|
| 1 | App abre sem crash | Entry point funcional | ⚠️ Parcial |
| 2 | Login com credenciais válidas | Autenticação | ✅ Sim |
| 3 | Login com credenciais inválidas | Tratamento de erro | ✅ Sim |
| 4 | Hub carrega dashboard | Tela principal | ✅ Sim |
| 5 | Hub carrega notas | Feature core | ✅ Sim |
| 6 | Navegar para Clientes | Navegação | ⚠️ Parcial |
| 7 | Criar novo cliente | CRUD básico | ✅ Sim |
| 8 | Editar cliente existente | CRUD básico | ✅ Sim |
| 9 | Mover cliente para lixeira | CRUD básico | ✅ Sim |
| 10 | Upload de arquivo | Feature core | ✅ Sim |
| 11 | Download de arquivo | Feature core | ✅ Sim |
| 12 | Abrir PDF viewer | Feature auxiliar | ⚠️ Parcial |
| 13 | Buscar cliente | UX crítica | ✅ Sim |
| 14 | Filtrar por status | UX crítica | ✅ Sim |
| 15 | Health check online/offline | Resiliência | ✅ Sim |

### 6.5 Suíte Mínima de Regressão Proposta

```bash
# Smoke tests críticos (executar em todo PR)
pytest tests/unit/core/test_auth_bootstrap_microfase.py -v
pytest tests/unit/modules/hub/test_dashboard_service.py::TestDashboardSnapshot -v
pytest tests/unit/modules/hub/test_hub_screen_controller_mf42.py::TestHubInit -v
pytest tests/unit/modules/clientes/test_viewmodel_round15.py::TestClientesCRUD -v
pytest tests/unit/modules/clientes/forms/test_prepare_round12.py::TestFormValidation -v
pytest tests/unit/modules/uploads/test_uploads_service_fase32.py::TestUploadBasic -v
pytest tests/unit/modules/anvisa/test_anvisa_service.py::TestAnvisaBasic -v
pytest tests/unit/data/test_supabase_repo.py::TestSupabaseRepoConnection -v
pytest tests/unit/infra/test_health_check.py -v
pytest tests/unit/ui/test_topbar_home_button.py -v

# Total estimado: ~200 testes, ~2-3 minutos
```

---

## ⚙️ PASSO 7 — CONFIG/EMPACOTAMENTO/ENV

### 7.1 Carregamento de Ambiente

| Arquivo | Mecanismo | Risco |
|---------|-----------|-------|
| `src/config/environment.py` | `load_dotenv()` com fallback | ✅ Robusto |
| `src/app_gui.py` | `bootstrap.configure_environment()` | ✅ OK |

#### Variáveis de ambiente críticas:

| Variável | Propósito | Default | Onde usada |
|----------|-----------|---------|------------|
| `RC_NO_LOCAL_FS` | Modo cloud-only | `True` | paths.py, themes.py, etc. |
| `RC_TESTING` | Modo teste | - | conftest.py |
| `RC_HEALTHCHECK_DISABLE` | Desabilitar health | - | testes |
| `SUPABASE_URL` | URL do Supabase | - | db_client.py |
| `SUPABASE_KEY` | Chave anon | - | db_client.py |
| `SUPABASE_BUCKET` | Bucket default | `rc-docs` | repository.py |
| `OPENAI_API_KEY` | Chave OpenAI | - | chatgpt/service.py |

### 7.2 resource_path / PyInstaller

| Arquivo | Implementação | Status |
|---------|---------------|--------|
| `src/utils/paths.py` | `resource_path()` central | ✅ Robusto |
| `src/utils/resource_path.py` | Re-export para compat | ✅ OK |
| `rcgestor.spec` | Config PyInstaller | ✅ Documentado |

#### Locais que usam resource_path:

- `src/ui/splash.py` - logo, ícones
- `src/ui/login_dialog.py` - ícones
- `src/ui/components/topbar_nav.py` - ícones
- `src/ui/components/notifications/` - ícones
- `src/modules/main_window/views/` - ícones

### 7.3 Paths Relativos/Absolutos

| Local | Tipo | Risco |
|-------|------|-------|
| `src/config/paths.py` | `Path(__file__).resolve().parent.parent` | ✅ Absoluto |
| `src/utils/themes.py` | `CONFIG_FILE` relativo ao BASE_DIR | ✅ OK |
| Assets em `assets/` | Via `resource_path()` | ✅ OK |

### 7.4 Checklist de Release

```markdown
## Checklist de Release v1.x.xx

### Pré-build
- [ ] Verificar `.env` NÃO está no .gitignore (mas NÃO empacotar)
- [ ] Atualizar `src/version.py` com nova versão
- [ ] Atualizar `CHANGELOG.md`
- [ ] Rodar `ruff check .` - sem erros
- [ ] Rodar `bandit -c .bandit -r src infra adapters data security` - sem P0/P1
- [ ] Rodar `pytest tests/unit -x --tb=short` - todos passam

### Build
- [ ] `pyinstaller rcgestor.spec --clean`
- [ ] Verificar `dist/RC-Gestor-Clientes-{version}.exe` existe
- [ ] Verificar tamanho (~50-100MB esperado)

### Pós-build (smoke manual)
- [ ] Executar .exe em máquina limpa
- [ ] Login funciona
- [ ] Hub carrega
- [ ] Criar/editar cliente funciona
- [ ] Upload de arquivo funciona

### Release
- [ ] Criar tag `v1.x.xx`
- [ ] Push tag para origin
- [ ] Criar release no GitHub com .exe anexado
```

---

## 🗑️ PASSO 8 — DÍVIDA TÉCNICA E REMOÇÃO SEGURA

### 8.1 Módulos Deprecated (Candidatos a Remoção)

| Módulo | Risco | Validação |
|--------|-------|-----------|
| `src/ui/hub/` (10 arquivos) | Baixo | Shims que redirecionam para `src/modules/hub` |
| `src/ui/forms/` (5 arquivos) | Baixo | Shims para `src/modules/clientes/forms` |
| `src/ui/lixeira/` (2 arquivos) | Baixo | Shims para `src/modules/lixeira` |
| `src/ui/main_window/` (5 arquivos) | Baixo | Shims para `src/modules/main_window` |
| `src/ui/login/login.py` | Baixo | Wrapper deprecated |
| `src/ui/passwords_screen.py` | Baixo | Shim para `src/modules/passwords` |
| `src/ui/main_screen.py` | Baixo | Shim para `src/modules/clientes` |
| `src/ui/hub_screen.py` | Baixo | Shim para `src/modules/hub` |
| `src/ui/files_browser.py` | Baixo | Shim para `src/modules/uploads` |
| `src/ui/menu_bar.py` | Médio | UI antiga, ainda pode ter uso |

### 8.2 Processo de Remoção Segura

```bash
# 1. Verificar imports com vulture (confiança alta)
vulture src/ --min-confidence 90 > vulture_report.txt

# 2. Grep por imports do módulo candidato
grep -r "from src.ui.hub" src/ tests/

# 3. Se nenhum import encontrado, mover para tests/archived/
# 4. Rodar pytest completo
# 5. Se passar, remover do archived em próxima release
```

### 8.3 Arquivos .bak Encontrados

| Arquivo | Tamanho | Ação |
|---------|---------|------|
| `src/modules/hub/services/authors_service.py.bak` | ~220 linhas | **Remover** |
| `tests/pytest.ini.bak` | pequeno | **Remover** |

---

## 🎯 PASSO 9 — PRÓXIMO PASSO (O MAIS IMPORTANTE)

### 9.1 Avaliação: O App Está Pronto?

**Resposta: 🟡 DEPENDE**

| Critério | Status | Justificativa |
|----------|--------|---------------|
| **Funcionalidade** | ✅ Sim | App funciona, features principais OK |
| **Estabilidade** | ⚠️ Parcial | Exceções genéricas podem mascarar bugs |
| **Testabilidade** | ✅ Sim | 499 arquivos de teste, boa cobertura |
| **Manutenibilidade** | ⚠️ Parcial | Alguns hotspots grandes, acoplamento UI |
| **Segurança** | ✅ Sim | Sem eval/exec inseguros, Bandit limpo |

**Conclusão:** O app está pronto para **uso em produção** com monitoramento.  
Para **desenvolvimento contínuo seguro**, recomenda-se reduzir hotspots antes de adicionar features grandes.

### 9.2 Top 10 Ações Recomendadas

#### LOW RISK (Quick Wins) — Executar imediatamente

| # | Ação | Esforço | Impacto |
|---|------|---------|---------|
| 1 | **Remover arquivos .bak** (`authors_service.py.bak`, `pytest.ini.bak`) | 5 min | Limpeza |
| 2 | **Tipar exceções em `app_core.py`** (substituir `except Exception` por tipos específicos) | 2h | Debugging |
| 3 | **Extrair formatters de `dashboard_service.py`** para `hub/formatters.py` | 2h | Manutenção |
| 4 | **Adicionar guard em `uploads/views/browser.py`** para verificar root | 30 min | Estabilidade |
| 5 | **Criar aliases de nodeids** para suíte de regressão em `pyproject.toml` | 1h | CI/CD |

#### MEDIUM RISK — Próximo sprint

| # | Ação | Esforço | Impacto |
|---|------|---------|---------|
| 6 | **Extrair `PdfRenderService`** de `pdf_preview/main_window.py` | 4h | Testabilidade |
| 7 | **Converter `_anvisa_handlers_mixin.py`** em Controller injetado | 6h | Manutenção |
| 8 | **Criar protocolo de UI feedback** para substituir messageboxes em services | 4h | Desacoplamento |

#### HIGH RISK — Planejar com cuidado

| # | Ação | Esforço | Impacto |
|---|------|---------|---------|
| 9 | **Remover shims deprecated** em `src/ui/` (após validação vulture) | 8h | Limpeza estrutural |
| 10 | **Dividir `dashboard_service.py`** em sub-services | 8h | Arquitetura |

### 9.3 Próxima Microfase Recomendada

**Recomendação: QA-003 (Types/Pyright) no módulo `hub`**

#### Justificativa:

1. **Hub é o módulo mais testado** (20+ arquivos de teste)
2. **Já passou por MF52.3** (mocks robustos)
3. **Tem estrutura clara** (service → viewmodel → view)
4. **Impacto alto em UX** (tela principal)

#### Escopo QA-003-HUB:

```markdown
## QA-003-HUB: Type Safety no Módulo Hub

### Objetivo
Adicionar anotações de tipo completas e habilitar strict mode do Pyright
para `src/modules/hub/`.

### Arquivos alvo (por ordem de prioridade)
1. src/modules/hub/dashboard_service.py
2. src/modules/hub/controller.py
3. src/modules/hub/viewmodels/notes_vm.py
4. src/modules/hub/services/authors_service.py
5. src/modules/hub/services/lifecycle_service.py
6. src/modules/hub/views/hub_screen.py (parcial - apenas interfaces públicas)

### Critério de aceite
- [ ] 0 erros Pyright em arquivos alvo
- [ ] Todos os testes existentes passam
- [ ] Sem regressão de funcionalidade
```

#### Alternativa: TEST-001 se preferir cobertura primeiro

```markdown
## TEST-001: Testes para pdf_preview

### Objetivo
Aumentar cobertura de testes para módulo `pdf_preview` que está com
proteção fraca.

### Cenários a cobrir
1. Abrir PDF válido
2. Tentar abrir arquivo inválido (não-PDF)
3. Zoom in/out
4. Navegação de páginas
5. Busca de texto
```

---

## 📊 TABELAS CONSOLIDADAS

### Tabela de Riscos Identificados

| ID | Severidade | Descrição | Arquivo(s) | Mitigação |
|----|------------|-----------|------------|-----------|
| R01 | P2 | 100+ `except Exception` em src/ | Múltiplos | Tipar exceções |
| R02 | P2 | messagebox em services | network.py, storage_ui_bridge.py | Protocolo UI |
| R03 | P2 | Hotspots >700 LOC | 8 arquivos | Extrair classes |
| R04 | P3 | Globals para singletons | session.py, lixeira.py | DI/Factory |
| R05 | P3 | Shims deprecated ativos | src/ui/* | Remover após vulture |
| R06 | P3 | PhotoImage sem ref forte | inputs.py | Manter referência |
| R07 | P4 | Tk root temporário | network.py | Refatorar |
| R08 | P4 | Arquivos .bak no repo | 2 arquivos | Remover |

### Tabela de Backlog Técnico

| ID | Prioridade | Descrição | Esforço | Sprint | Status | Evidência (commit) |
|----|------------|-----------|---------|--------|--------|--------------------||
| T01 | Alta | Tipar exceções em app_core.py | 2h | Atual | ✅ Concluído | 1727261 |
| T02 | Alta | Remover arquivos .bak | 5min | Atual | ✅ Concluído | 0f3bbc0 |
| T03 | Alta | Criar suíte de regressão mínima (smoke + --smoke/--smoke-strict) | 1h | Atual | ✅ Concluído | 1ae2a76, dcdad37, 1ce3bab |
| T04 | Média | Extrair formatters de dashboard_service | 2h | +1 | ⏳ Pendente | — |
| T05 | Média | Guard em uploads/browser.py | 30min | Atual | ⏳ Pendente | — |
| T06 | Média | Extrair PdfRenderService | 4h | +1 | ⏳ Pendente | — |
| T07 | Média | Converter mixin ANVISA em Controller | 6h | +2 | ⏳ Pendente | — |
| T08 | Média | Protocolo UI feedback | 4h | +2 | ⏳ Pendente | — |
| T09 | Baixa | Remover shims deprecated | 8h | +3 | ⏳ Pendente | — |
| T10 | Baixa | Dividir dashboard_service | 8h | +3 | ⏳ Pendente | — |
| T11 | Alta | Corrigir Pyright + robustez notifications (timezone/mocks) | 30min | Atual | ✅ Concluído | 7d42348 |
| T12 | Média | Aplicar ruff format (arquivos de teste) | 15min | Atual | ✅ Concluído | 4dacd0e |
| T13 | Média | Vulture 100% + whitelist + config no pyproject | 30min | Atual | ✅ Concluído | 4037546, a605855 |
| T14 | Média | Alinhar pre-commit (Ruff + EOL) + documentar fluxo padrão | 30min | Atual | ✅ Concluído | 939c236, fc5a10b, b03a184 |

---

## � Fluxo padrão de qualidade (recomendado)

Esta seção documenta os comandos padrão para manter a qualidade do código.

### 1) Rodar hooks localmente (equivalente ao commit)

```bash
pre-commit run --all-files
```

> **⚠️ Observação (Windows):** O pre-commit pode modificar arquivos (EOL/whitespace/format).  
> Se isso acontecer: rode `git add -A` e execute novamente `pre-commit run --all-files` até passar.

### 2) Smoke suite (rápida e crítica)

```bash
pytest --smoke --smoke-strict -q -x --tb=short
```

Este comando executa apenas os testes críticos definidos em `scripts/suites/smoke_nodeids.txt`.  
Sem `--smoke-strict`, o pytest imprime um **AVISO** no resumo se algum prefixo não casar.  
Com `--smoke-strict`, o pytest **FALHA** (UsageError) se algum prefixo não casar.

### 3) Checks rápidos (sem rodar suite inteira)

```bash
ruff check .
pyright
```

### 4) (Opcional) Smoke via script alternativo

```bash
python scripts/run_smoke.py
python scripts/run_smoke.py --dry-run  # apenas lista os testes
```

> **Nota:** O smoke oficial é via `pytest --smoke`. O script é uma alternativa para uso ad-hoc.

### 5) Quality Gate completo (antes de PR)

```bash
pre-commit run --all-files
pytest --smoke --smoke-strict -q -x --tb=short
ruff check .
pyright
```

---

## �📝 CONCLUSÃO

O **RC - Gestor de Clientes** é um aplicativo desktop funcional e bem testado, com arquitetura modular em transição de uma estrutura legada (`src/ui/`) para uma organização por domínio (`src/modules/`).

### Pontos Fortes:
- ✅ 499 arquivos de teste com boa cobertura
- ✅ Sem vulnerabilidades de segurança críticas (eval/exec)
- ✅ Arquitetura clara com separação de camadas
- ✅ Documentação técnica extensa
- ✅ Processo de release documentado

### Pontos de Atenção:
- ⚠️ Exceções genéricas em excesso
- ⚠️ Acoplamento UI em services (messagebox)
- ⚠️ Arquivos hotspot grandes (>700 LOC)
- ⚠️ Shims deprecated ainda presentes

### Recomendação Final:

**Iniciar QA-003-HUB** (type safety) como próxima microfase, pois:
1. Hub é módulo mais crítico (tela principal)
2. Já tem testes robustos (pré-requisito para refactoring seguro)
3. Type hints facilitarão futuras extrações de classes
4. Impacto positivo em todo o codebase (hub é importado por muitos)

---

*Relatório gerado automaticamente por auditoria Copilot AI*  
*Data: 29/12/2025 | Versão base: v1.5.27 | Branch: main*
