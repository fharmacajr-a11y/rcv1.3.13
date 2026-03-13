# AUDITORIA TÉCNICA — MÓDULO HUB
**Versão auditada:** v1.6.22  
**Escopo primário:** `src/modules/hub/**`  
**Escopo secundário:** `src/modules/main_window/**`, `src/core/app_core.py`, `src/core/services/**`  
**Metodologia:** 4 camadas — leitura estrutural, análise estática (ruff/pyright/vulture/deptry), leitura de código com prova de uso, testes  
**Classificação de severidade:** CONFIRMADO / PROVÁVEL / INCERTO  

---

## SEÇÃO 1 — SUMÁRIO EXECUTIVO

### Estado geral

O módulo Hub está **bem estruturado** para o padrão de uma aplicação Python/Tkinter de porte médio. Aplica corretamente o padrão de Facade (MF-10 a MF-28), thin orchestrator (`HubScreen`), viewmodels, builders e separação de serviços. O suite de testes passa integralmente (1035 testes, 0 falhas).

A auditoria **não encontrou nenhum bug de crash em runtime confirmado na arquitetura ativa**. O deferred build com `after(0, ...)` é corretamente guardado e cancelado em `destroy()`. O polling teardown percorre o caminho `stop_polling()` → `_lifecycle_facade.stop_polling()` sem vazamentos identificados.

**Três problemas confirmados requerem ação:**

| # | Classificação | Descrição | Impacto |
|---|---|---|---|
| C-01 | **CONFIRMADO** | `module hub/controller.py` é módulo legado — não importado por nenhum código ativo | Código morto, risco de confusão futura |
| C-02 | **CONFIRMADO** | Log em `screen_registry.py:96` diz "6 telas" mas só 5 são registradas | Bug de consistência no log |
| C-03 | **CONFIRMADO** | `_notes_after_handle` em `controller.py` — escrito em 5 lugares, lido em zero | Dead attribute no módulo já morto |

**Quatro problemas com alta probabilidade:**

| # | Classificação | Descrição |
|---|---|---|
| P-01 | **PROVÁVEL** | Subsistema de dashboard desativado deixou ~30 funções/atributos orfãos no código ativo |
| P-02 | **PROVÁVEL** | Import `HubDashboardView` em `hub_dashboard_renderer.py:27` nunca usado (90% vulture) |
| P-03 | **PROVÁVEL** | Três funções de `notes_rendering.py` (`get_author_color`, `format_note_body`, `build_note_tooltip_text`) sem chamadores externos |
| P-04 | **PROVÁVEL** | `format_timestamp` implementada em 3 módulos distintos: `notes_rendering.py`, `helpers/notes.py`, `format.py` |

**Nenhum problema de segurança** foi identificado no escopo auditado.

---

## SEÇÃO 2 — ESTRUTURA E ARQUITETURA

### 2.1 Mapa de arquivos do Hub

```
src/modules/hub/
├── __init__.py                    # lazy import via __getattr__, re-exports HubScreen
├── async_runner.py                # HubAsyncRunner (ThreadPoolExecutor + tk callback)
├── colors.py                      # constantes de cor
├── constants.py                   # constantes do módulo
├── controller.py                  # ⚠ LEGADO — não importado por nenhum código ativo
├── dashboard_formatters.py        # formatadores de dashboard
├── dashboard_service.py           # shim de compatibilidade via __getattr__/__dir__
├── format.py                      # helpers de formatação (_LOCAL_TZ, _format_timestamp)
├── hub_lifecycle.py               # HubLifecycle dataclass gerencia timers
├── hub_screen_controller.py       # HubScreenController headless
├── hub_state_manager.py           # HubStateManager — mutações centralizadas de estado
├── hub_utils.py                   # utilitários internos
├── layout.py                      # helpers de layout
├── notes_rendering.py             # rendering de notas (get_author_color etc.)
├── panels.py                      # builders de painéis
├── recent_activity_store.py       # store de atividade recente
├── state.py                       # HubState dataclass
├── utils.py                       # utilitários expostos
├── controllers/
│   ├── __init__.py
│   ├── dashboard_actions.py       # DashboardActionController
│   ├── notes_controller.py        # NotesController
│   └── quick_actions_controller.py
├── dashboard/                     # subsistema dashboard (DESATIVADO)
│   ├── models.py
│   └── service.py
├── helpers/
│   ├── __init__.py
│   ├── notes.py                   # format_timestamp (duplicata #2)
│   └── ...
├── infrastructure/                # inicialização de infraestrutura
├── services/
│   ├── hub_component_factory.py   # HubComponentFactory (instancia todos os componentes)
│   ├── hub_lifecycle_impl.py      # HubLifecycleImpl
│   ├── hub_notes_helpers.py       # helpers de notas
│   ├── hub_polling_service.py     # HubPollingService
│   └── hub_screen_builder.py      # HubScreenBuilder (orquestra build da tela)
├── viewmodels/
│   ├── dashboard_vm.py
│   ├── notes_vm.py
│   └── quick_actions_vm.py
└── views/
    ├── hub_screen.py              # 🎯 Orchestrator principal (~900 linhas)
    ├── hub_screen_view.py         # HubScreenView (protocolo/view adapter)
    ├── hub_screen_view_pure.py    # funções puras (format_note_line, make_module_button)
    ├── hub_screen_view_constants.py
    ├── hub_authors_cache.py
    ├── hub_authors_cache_facade.py
    ├── hub_dashboard_facade.py
    ├── hub_dashboard_handlers.py
    ├── hub_dashboard_renderer.py  # ⚠ importa HubDashboardView sem usar
    ├── hub_lifecycle_facade.py
    ├── hub_lifecycle_manager.py
    ├── hub_navigation.py
    ├── hub_navigation_facade.py
    ├── hub_notes_facade.py
    ├── hub_quick_actions_view.py
    ├── hub_screen_handlers.py
    ├── hub_screen_helpers.py
    ├── hub_screen_layout.py
    └── ... (outros helpers de views)
```

### 2.2 Arquitetura de construção

```
HubScreen.__init__()
 ├── _init_state()           → HubScreenBuilder.build()
 │    └── HubComponentFactory → instancia todos os componentes (viewmodels, controllers,
 │                               facades, lifecycle, polling)
 ├── _build_skeleton_ui()    → placeholder "Carregando Hub..."
 └── after(0, _build_deferred_ui)
      └── _build_deferred_ui()
           ├── HubQuickActionsView.build()    → modules_panel
           ├── ctk.CTkFrame (transparente)   → center_spacer (dashboard DESATIVADO)
           ├── build_notes_panel()            → notes_panel
           ├── apply_hub_notes_right()        → layout grid 3 colunas
           ├── setup_bindings()
           └── start_timers()
```

### 2.3 Cadeia de lifecycle

```
on_show()  →  _lifecycle_facade.on_show()
           →  HubLifecycleImpl.start_home_timers_safely()
           →  HubPollingService.start()
           →  agenda polling de notas + refresh de autores

destroy()  →  after_cancel(_hub_build_after_id)     [FASE 5A — correto]
           →  _lifecycle.stop()
           →  stop_polling() → _lifecycle_facade.stop_polling()
           →  _async.shutdown()
           →  super().destroy()
```

---

## SEÇÃO 3 — ANÁLISE ESTÁTICA

### 3.1 Ruff

**Configuração:** `target = "py313"`, selects `E, F, N`; ignores globais `E501, F403, F821`.

**Resultado para escopo auditado (hub + main_window + core):**
```
All checks passed!
```

Nenhuma violação das regras ativas. O código hub está limpo segundo o perfil ruff configurado.

> **Observação:** `F403` (wildcard imports) e `F821` (símbolos não definidos) estão **desativados globalmente**. Isso permite que `from module import *` passe sem análise. Não foi identificado abuso no escopo hub, mas é uma exceção que reduz a capacidade do linter de detectar importações mortas.

### 3.2 Pyright

**Modo básico — resultado:**
```
src/modules/hub/views/hub_screen.py:308:34
  warning: Cannot assign to attribute "center_spacer" for class "HubScreen*"
           Expression of type "CTkFrame" is not assignable to "Frame | None"
           (reportAttributeAccessIssue)

0 errors, 1 warning
```

**Modo strict — resultado adicional:**
```
src/modules/hub/format.py:11
  warning: Assignment to constant "_LOCAL_TZ" shadows prior constant of same type
           (reportConstantRedefinition)

src/modules/hub/helpers/notes.py:41
  warning: Assignment to constant "_LOCAL_TZ" shadows prior constant of same type
           (reportConstantRedefinition)

src/core/services/profiles_service.py:52
  warning: Assignment to constant "_WARNED_MISSING_COL" shadows prior constant
           (reportConstantRedefinition)

0 errors, 4 warnings (total incluindo o básico)
```

**Análise das warnings de `_LOCAL_TZ`:**  
O padrão é `try: _LOCAL_TZ = get_local_timezone() / except: _LOCAL_TZ = timezone.utc`. Isso é idiomático para fallback de timezone e o re-assignment é **intencional**. A warning do pyright strict é um **falso positivo** para este pattern. Não requer correção mas pode ser silenciado com `# pyright: ignore[reportConstantRedefinition]`.

### 3.3 Vulture

#### Confiança 100% — CONFIRMADO

| Arquivo | Linha | Símbolo | Tipo |
|---|---|---|---|
| `hub/views/hub_screen_view_pure.py` | 20 | `width` | variável atribuída, nunca lida |
| `main_window/views/main_window_actions.py` | 220 | `theme` | variável atribuída, nunca lida |
| `main_window/services/main_window_services.py` | 47 | `username` | variável atribuída, nunca lida |
| `core/services/clientes_service.py` | 49 | `base_delay` | variável atribuída, nunca lida |
| `core/services/clientes_service.py` | 49 | `max_retries` | variável atribuída, nunca lida |

Estes são **achados confirmados** — variáveis computadas e descartadas imediatamente. Risco de confusão (parece intencional, mas é morto).

#### Confiança 90% — PROVÁVEL

| Arquivo | Linha | Símbolo | Evidência adicional |
|---|---|---|---|
| `hub/views/hub_dashboard_renderer.py` | 27 | `from ... import HubDashboardView` | Dashboard desativado; import não referenciado no corpo do arquivo |

#### Confiança 60% — INCERTO (requer cross-validação individual)

Ver Seção 4 para análise detalhada dos itens 60%.

### 3.4 Deptry

**Hub-relevantes:**

| Código | Pacote | Arquivo | Avaliação |
|---|---|---|---|
| DEP003 | `customtkinter` | `screen_router.py`, `main_window_bootstrap.py`, `main_window_layout.py` | Dependência transitiva usada diretamente — adicionar a `requirements.in` se uso direto for intencional |
| DEP003 | `tzlocal` | `hub_screen_pure.py` | Idem — transitive dep usada como direta |
| DEP001 | `core`, `ui`, `utils` | vários arquivos legados | Pacotes internos não declarados — sem risco de runtime, apenas ruído no deptry |

---

## SEÇÃO 4 — CÓDIGO MORTO: CLASSIFICAÇÃO COMPLETA

### 4.1 CONFIRMADO — evidência direta

#### C-01: `src/modules/hub/controller.py` — módulo inteiro morto
**Evidência:**
- `grep -r "from src.modules.hub.controller import"` → **zero resultados** em `src/`
- `grep -r "from src.modules.hub import controller"` → **zero resultados**
- O `hub/__init__.py` lista `__all__` **sem** incluir nenhum símbolo de `controller.py`
- O arquivo contém funções de polling legado (`schedule_poll`, `cancel_poll`, `poll_notes_if_needed`, `on_realtime_note`, `append_note_incremental`, `refresh_notes_async`) que operam diretamente no objeto `screen` — padrão anterior ao MF-14/15

**Conteúdo do módulo:** 13 funções, ~420 linhas  
**Risco de remoção:** Baixo — nenhum importador ativo, funcionalidade substituída por HubPollingService + HubLifecycleImpl + facades

#### C-02: `screen_registry.py:96` — log com contagem incorreta
**Evidência:**
```python
router.register("hub", _create_hub, cache=True)       # 1
router.register("main", _create_main, cache=True)     # 2
router.register("cashflow", _create_cashflow, cache=False) # 3
router.register("sites", _create_sites, cache=False)  # 4
router.register("placeholder", _create_placeholder, cache=False) # 5

_log.debug("Registradas 6 telas no ScreenRouter")  # ← diz 6, registra 5
```
**Impacto:** Apenas no log, nenhum impacto funcional. Mas corrompe diagnósticos baseados em log.

#### C-03: `controller.py` — `_notes_after_handle` escrito, nunca lido
**Evidência (dentro do módulo já morto C-01):**
- Linha 251: `screen._notes_after_handle = screen.after(...)`
- Linha 263: `screen._notes_after_handle = screen.after(...)`
- Linha 272: `screen._notes_after_handle = None`
- Linha 292: `screen._notes_after_handle = screen.after(...)`
- Linha 394: `screen._notes_after_handle = None`
- Zero leituras. O handle nunca foi usado para `after_cancel()`, constituindo um memory leak no módulo legado.

---

### 4.2 PROVÁVEL — evidência forte, sem certeza absoluta

#### P-01: Subsistema dashboard desativado — resíduos no código ativo

**Contexto:** O dashboard foi explicitamente desativado (`# DASHBOARD DESATIVADO` nos comentários). Porém o código que o suportava **não foi removido**, apenas silenciado.

Símbolos identificados como prováveis órfãos **no código ativo** (não em `controller.py`):

| Arquivo | Símbolo | Razão |
|---|---|---|
| `hub/views/hub_screen.py` | `_update_dashboard_ui()`, `update_dashboard()`, `reload_dashboard()`, `_load_dashboard()` | No-ops explícitos, mantidos apenas para protocolo |
| `hub/views/hub_screen.py` | `_on_view_all_activity()`, `_on_card_clients_click()`, `_on_card_pendencias_click()`, `_on_card_tarefas_click()` | Delegam para `_dashboard_facade` — mas o dashboard está desativado |
| `hub/hub_lifecycle.py` | `schedule_dashboard_load()`, `schedule_notes_load()` | Ligados ao dashboard que não existe mais |
| `hub/hub_screen_controller.py` | `load_dashboard_data_async()`, `load_dashboard_data()` | Dashboard desativado |
| `hub/state.py` | `is_dashboard_loaded`, `last_dashboard_refresh_time`, `enable_dashboard_refresh` | Campos de estado do dashboard morto |
| `hub/dashboard/models.py` | `cash_in_month`, `upcoming_deadlines`, `risk_radar`, `recent_activity` | Modelos do dashboard não renderizado |

**Ressalva:** Alguns destes métodos (ex: `reload_dashboard`) existem para compatibilidade de **protocolo** (interface pública esperada por `MainWindow`). Remoção requer verificação de que nenhum chamador externo os usa.

#### P-02: Import morto em `hub_dashboard_renderer.py:27`

```python
from src.modules.hub.views.hub_dashboard_view import HubDashboardView  # linha 27
```

**Evidência:**
- Confiança vulture: 90%
- Dashboard está desativado (`_dashboard_view = None` em `hub_screen.py`)
- `HubDashboardView` não aparece no corpo do arquivo após a linha de import

**Ação sugerida:** Remover o import ou adicionar ao `vulture_whitelist.py` com justificativa se planejado reativar.

#### P-03: Três funções em `notes_rendering.py` sem chamadores externos

```python
def get_author_color(author_key: str) -> str: ...      # linha 39
def format_note_body(note, max_len: int = 200) -> str: # linha 78
def build_note_tooltip_text(note) -> str: ...          # linha 133
```

**Evidência:**
- `grep "get_author_color|format_note_body|build_note_tooltip_text"` em `src/**` → apenas as próprias definições
- A única referência a `get_author_color` em todo o codebase é um comentário em `panels.py:242`: `# Sem ensure_author_tag (fallback usa get_author_color)` — **não é uma chamada**
- `format_note_full_line` (linha 97) **está ativa** (importada por `notes_vm.py:15`) e usa `format_note_header` e `format_timestamp` internamente — essas são vivas
- `build_note_tooltip_text` pode ter sido usada em um tooltip widget que foi removido

**Ressalva:** Funções públicas podem ser chamadas via duck typing ou testes. Verificar antes de remover.

#### P-04: `format_timestamp` implementada em 3 módulos distintos

| Arquivo | Nome da função | Observação |
|---|---|---|
| `hub/notes_rendering.py:111` | `format_timestamp(iso_timestamp: str) -> str` | Versão original |
| `hub/helpers/notes.py:261` | `format_timestamp(ts_iso: str \| None) -> str` | Aceita `None`, mais defensiva |
| `hub/format.py:14` | `_format_timestamp(ts_iso: str \| None) -> str` | Privada, usada em `controller.py` (morto) |

**Risco:** Triplicação silenciosa de lógica de formatação de timestamps. Se o comportamento divergir entre versões (ex: fuso horário, fallback para None), pode produzir outputs inconsistentes dependendo de qual função é chamada. `helpers/notes.py` está exportada em `helpers/__init__.py` e é a versão canônica atual.

---

### 4.3 INCERTO — 60% de confiança, requer análise caso a caso

Os itens abaixo foram detectados pelo vulture com confiança de 60% (limiar onde falsos positivos são comuns). **Nenhum deve ser tratado como morto sem cross-validação individual.**

#### HubStateManager — API pública (hub_state_manager.py)

Vulture listou ~18 métodos como "unused": `set_loading`, `set_dashboard_loaded`, `set_notes_loaded`, `set_names_refreshing`, `set_names_cache_loading`, `update_email_prefix_map`, `set_cached_notes`, `set_notes_poll_interval`, `set_live_sync_on`, `set_live_org_id`, `set_live_channel`, `set_active`, `set_last_dashboard_refresh_time`, `set_last_notes_refresh_time`, `set_last_author_cache_refresh`, `set_last_org_for_names`, `set_last_refresh_ts`, `merge_author_cache`, `bulk_update`.

**Avaliação:** O `HubStateManager` define uma API pública de mutações. Métodos públicos podem ser:
- Usados por facades via duck typing ou Protocol
- Usados por `bulk_update` internamente  
- Planejados para uso futuro quando o dashboard for reativado

Vulture não consegue rastrear chamadas através de `Protocol` ou `getattr()`. Tratar como INCERTO até inspeção individual de cada método.

#### HubScreen — métodos privados de lifecycle

Vulture lista `_start_notes_polling`, `_start_live_sync_impl`, `_stop_live_sync_impl`, `_schedule_poll`, `_poll_notes_if_needed`, `_poll_notes_impl`, `_on_realtime_note`.

**Avaliação:** Estes métodos são **callbacks registrados** passados para facades e serviços — não são chamados diretamente pelo nome de dentro de `hub_screen.py`. Vulture não rastreia referências por string ou lambda. **Provavelmente vivos.**

#### `recent_activity_store.py` — `get_lines`, `get_recent_activity_store`

**Avaliação:** Componente do subsistema de atividade recente. Se o dashboard foi desativado, este store pode estar órfão. Mas `get_recent_activity_store` pode ser usado como factory em testes. **INCERTO.**

#### `viewmodels/notes_vm.py` — `show_only_pinned`, `total_count`, `update_author_names_cache`, `start_loading`

**Avaliação:** ViewModels têm APIs que são acessadas por componentes de UI diferentes. Propriedades como `show_only_pinned` podem ser lidas por filtros de renderização. **INCERTO — verificar callers antes de remover.**

---

## SEÇÃO 5 — LIFECYCLE, TIMERS E AFTER()

### 5.1 Deferred build (`_hub_build_after_id`)

**Código em `__init__`:**
```python
self._hub_build_after_id: Optional[str] = None
# ...
self._hub_build_after_id = self.after(0, self._build_deferred_ui)
```

**Código em `destroy()`:**
```python
if hasattr(self, "_hub_build_after_id") and self._hub_build_after_id is not None:
    try:
        self.after_cancel(self._hub_build_after_id)
        logger.debug("HubScreen.destroy: deferred build cancelado")
    except (tk.TclError, Exception) as e:
        logger.debug(f"HubScreen.destroy: erro ao cancelar deferred build: {e}")
    self._hub_build_after_id = None
```

**Avaliação: ✅ CORRETO.** O ID é cancelado antes de destruir o widget. A flag `_destroy_called` previne duplo destroy. O `_build_deferred_ui()` tem guard adicional: `if not self.winfo_exists(): return`.

### 5.2 Guardia de duplo destroy

```python
self._destroy_called = False  # em __init__
# ...
if self._destroy_called:
    return
# ...
self._destroy_called = True  # antes de qualquer teardown
```

**Avaliação: ✅ CORRETO.** Proteção idiomática contra chamadas duplicadas ao `destroy()`.

### 5.3 Cadeia de teardown de polling

```
HubScreen.destroy()
  └─ stop_polling()
       └─ _lifecycle_facade.stop_polling()
            └─ HubLifecycleImpl.stop_polling()
                 ├─ HubPollingService.stop()
                 └─ HubLifecycle.stop()
```

**Avaliação:** O caminho existe e está documentado. A verificação `if hasattr(self, "_lifecycle_facade") and self._lifecycle_facade is not None` previne falha caso `_init_state()` não tenha completado antes de um `destroy()` prematuro.

### 5.4 Risco residual: polling iniciado parcialmente

**Cenário hipotético:** Se `start_timers()` (chamado no final de `_build_deferred_ui`) registrar callbacks em `HubLifecycle`, mas o widget for destruído antes que o `stop_polling()` percorra a mesma cadeia — o lifecycle poderia manter timers ativos.

**Avaliação: INCERTO/BAIXO.** O `HubLifecycle.stop()` cancela todos os timers registrados via `after_cancel`. Não há evidência de timer órfão, mas **não há teste de integração cobrindo o cenário de destroy() chamado entre `after(0,...)` e `start_timers()`.**

### 5.5 `_auth_ready_callback` em facades

Vulture lista `_auth_ready_callback` como atributo não lido em `hub_lifecycle_facade.py` e `hub_authors_cache_facade.py`.

**Avaliação: INCERTO.** Callbacks armazenados em atributos são frequentemente chamados via mecanismo de despacho indireto. Sem inspeção linha-a-linha de cada facade, não é possível confirmar se é morto ou não.

---

## SEÇÃO 6 — RISCOS DE TIPO E INTERFACE

### 6.1 `center_spacer`: anotação incorreta [CONFIRMADO]

**Arquivo:** `src/modules/hub/views/hub_screen.py:308` (declaração em `_build_skeleton_ui`) e atribuição em `_build_deferred_ui`:

```python
# _build_skeleton_ui():
self.center_spacer: Optional[tk.Frame] = None   # anotado como tk.Frame | None

# _build_deferred_ui():
self.center_spacer = ctk.CTkFrame(               # atribuído como ctk.CTkFrame
    self, fg_color="transparent", ...
)
```

`ctk.CTkFrame` não é subclasse de `tk.Frame` na hierarquia de tipos (é subclasse de `tk.Canvas`). O pyright levanta `reportAttributeAccessIssue` nesta linha.

**Impacto:** Não causa erro em runtime no Python convencional (duck typing). Mas pode enganar type checkers e IDEs, mascarando future type errors.

**Correção sugerida:**
```python
self.center_spacer: Optional[ctk.CTkFrame] = None
```
Ou, se precisar aceitar ambos:
```python
self.center_spacer: Optional[Union[tk.Frame, ctk.CTkFrame]] = None
```

### 6.2 `_LOCAL_TZ` constant redefinition [INCERTO/Falso positivo]

**Arquivos:** `hub/format.py:11`, `hub/helpers/notes.py:41`

```python
try:
    _LOCAL_TZ = get_local_timezone()
except Exception:
    _LOCAL_TZ = timezone.utc      # ← pyright strict: "shadows prior constant"
```

**Avaliação:** Este é um **padrão de fallback idiomático**. A warning do pyright strict é tecnicamente correta (dois assignments para o mesmo nome com prefixo `_` maiúsculo), mas o comportamento é intencional. Pode ser silenciado com:
```python
_LOCAL_TZ: tzinfo  # tipagem explícita antes do try
try:
    _LOCAL_TZ = get_local_timezone()
except Exception:
    _LOCAL_TZ = timezone.utc
```
Isso elimina a warning sem alterar semântica.

### 6.3 `HubScreenView` passado onde `HubScreen` é esperado

Em `hub_component_factory.py:260`:
```python
hub_controller = HubScreenController(
    view=screen,  # type: ignore[arg-type]  # HubScreen implementa HubScreenView funcionalmente
    ...
)
```

O `# type: ignore[arg-type]` já suprime a warning, mas indica um acoplamento estrutural: `HubScreen` não herda de `HubScreenView` nem implementa um Protocol formal. A supressão manual é frágil — uma mudança de assinatura em `HubScreenController.__init__` pode quebrar silenciosamente.

---

## SEÇÃO 7 — DUPLICAÇÕES E DIVERGÊNCIAS DE LÓGICA

### 7.1 `format_timestamp`: três implementações paralelas

| Arquivo | Função | Assinatura | Aceita None? |
|---|---|---|---|
| `hub/notes_rendering.py:111` | `format_timestamp` | `(iso_timestamp: str) -> str` | Não |
| `hub/helpers/notes.py:261` | `format_timestamp` | `(ts_iso: str \| None) -> str` | Sim (retorna `""`) |
| `hub/format.py:14` | `_format_timestamp` | `(ts_iso: str \| None) -> str` | Sim |

A versão em `helpers/notes.py` é a exportada canonicamente via `helpers/__init__.py` e usada por `hub_screen_helpers.py` e `hub_helpers_notes.py`. A versão em `notes_rendering.py` é usada apenas internamente por `format_note_header` → `format_note_full_line`. A versão em `format.py` é usada apenas em `controller.py` (módulo morto).

**Risco:** Se a lógica de parsing de timestamp precisar ser ajustada (ex: suporte a novo formato de `created_at`), a correção em um lugar **não se propaga** para os outros. O comportamento já diverge: aceitar `None` vs não aceitar.

### 7.2 Comentário `# Sem ensure_author_tag (fallback usa get_author_color)`

`panels.py:242` menciona `get_author_color` como fallback em comentário, mas a função não é importada no arquivo. Isso sugere que a funcionalidade foi removida mas o comentário não foi atualizado — **divergência documentação/código**.

---

## SEÇÃO 8 — COBERTURA DE TESTES

### 8.1 Estado dos testes

```
pytest tests/ -q --no-header --tb=no
1035 passed in 31.95s
```

Zero falhas. Todos os 1035 testes passam.

### 8.2 Testes hub-específicos

```
pytest tests/ -q -k "hub or main_window or screen or routing or callback or dashboard or polling or navigation"
50 passed in 3.45s
```

Arquivos hub key: `test_hub_async_runner.py` (13 testes), `test_hub_controller.py` (10 testes)

### 8.3 Lacunas de cobertura identificadas

As lacunas abaixo **não são obrigatórias** — são áreas onde falhas silenciosas seriam possíveis sem testes:

| Cenário | Risco se falhar |
|---|---|
| `destroy()` chamado antes de `_build_deferred_ui` executar | Timer ID seria cancelado corretamente? — **atualmente coberto pelo guard em destroy(), mas sem teste específico** |
| `destroy()` chamado de thread não-main | TclError silenciosa |
| `on_show()` chamado repetidamente sem `destroy()` | Double-start de timers/polling |
| `after()` callbacks executados após `_destroy_called = True` | `winfo_exists()` guard presente, mas sem test de integração |
| Realtime note chegando durante `_build_deferred_ui` | `_on_realtime_note` chamaria antes da UI estar pronta |

### 8.4 Testes de regressão recomendados

1. **Teste de lifecycle deferred:** Criar `HubScreen`, chamar `destroy()` imediatamente (antes do `after(0,...)` disparar), verificar que não há TclError.
2. **Teste de double show:** Chamar `on_show()` duas vezes sem destroy entre elas, verificar que polling não é duplicado.
3. **Teste de teardown completo:** Criar `HubScreen`, aguardar `_build_deferred_ui`, chamar `destroy()`, verificar que threads do `HubAsyncRunner` terminaram.

---

## SEÇÃO 9 — RECOMENDAÇÕES PRIORIZADAS

### P0 — Ação imediata (sem risco de regressão)

#### R-01: Corrigir log em `screen_registry.py:96`
```python
# Antes:
_log.debug("Registradas 6 telas no ScreenRouter")
# Depois:
_log.debug("Registradas 5 telas no ScreenRouter")
```
**Risco de regressão:** Zero. Apenas corrige uma string de log.

---

### P1 — Alta prioridade (evidência confirmada)

#### R-02: Remover `src/modules/hub/controller.py`
**Evidência:** Nenhum importador ativo encontrado em `src/`. Módulo com ~420 linhas, completamente substituído pelas MF-14/15 facades e services.  
**Procedimento sugerido:**
1. Adicionar ao `.gitignore` temporariamente OU renomear para `controller.py.bak` e rodar o suite completo de testes
2. Se 1035 testes passarem → remover definitivamente
3. Atualizar `vulture_whitelist.py` se necessário

#### R-03: Remover import morto em `hub_dashboard_renderer.py:27`
```python
# Remover esta linha:
from src.modules.hub.views.hub_dashboard_view import HubDashboardView
```
**Evidência:** 90% vulture + dashboard desativado + símbolo não usado no corpo do arquivo.  
**Risco de regressão:** Mínimo. Se o import fosse usado, o pyright já teria flagado erro de nome não usado.

---

### P2 — Média prioridade (melhora qualidade/manutenibilidade)

#### R-04: Corrigir anotação de tipo `center_spacer`
```python
# hub_screen.py _build_skeleton_ui():
# Antes:
self.center_spacer: Optional[tk.Frame] = None
# Depois:
self.center_spacer: Optional[ctk.CTkFrame] = None
```
Elimina a única warning do pyright básico. Sem impacto em runtime.

#### R-05: Silenciar warnings de `_LOCAL_TZ` em modo strict (opcional)
Adicionar tipagem explícita antes do bloco `try/except` em `format.py` e `helpers/notes.py`:
```python
_LOCAL_TZ: tzinfo
try:
    _LOCAL_TZ = get_local_timezone()
except Exception:
    _LOCAL_TZ = timezone.utc
```

#### R-06: Consolidar `format_timestamp` em uma única implementação canônica
Substituir usos em `notes_rendering.py` pela importação de `helpers/notes.py`:
```python
from src.modules.hub.helpers import format_timestamp
```
E remover a implementação duplicada em `notes_rendering.py:111-130`.

---

### P3 — Baixa prioridade (quando dashboard for reativado ou definitivamente removido)

#### R-07: Decidir se o subsistema dashboard será reativado ou removido

Atualmente o código está num estado híbrido: métodos presentes mas no-op, models existentes mas não renderizados, state fields existentes mas não escritos. Isso é aceitável para manutenção ativa de feature desativada, mas acumula dívida técnica.

**Opção A: Reativar dashboard** → Remover os comentários "DESATIVADO", conectar `_dashboard_view` ao `HubDashboardRenderer`, reativar polling de dashboard  
**Opção B: Remover definitivamente** → Remover `dashboard/`, remover campos de estado dashboard, remover métodos no-op, remover `hub_dashboard_*.py` views

Enquanto a decisão não for tomada, documentar o status no `hub/__init__.py` ou em um comentário em `hub_screen.py:__init__` com data e justificativa.

#### R-08: Avaliar remoção de `get_author_color`, `format_note_body`, `build_note_tooltip_text`

Cross-validar via:
```powershell
grep -r "get_author_color\|format_note_body\|build_note_tooltip_text" tests/
```
Se zero resultados em testes também, estas funções podem ser removidas com segurança.

#### R-09: Adicionar `customtkinter` e `tzlocal` a `requirements.in`

Atualmente usados como dependências transitivas mas não declaradas diretamente. Se uma versão futura do `pyproject.toml` remover a dep transitiva, o import falhará em runtime.

---

## APÊNDICE A — Evidências Detalhadas de Ferramentas

### Ruff (normal + F401 + F841)
```
All checks passed.
```

### Pyright básico
```
src/modules/hub/views/hub_screen.py:308:34 - warning: Cannot assign to attribute
"center_spacer" for class "HubScreen*"
  Expression of type "CTkFrame" is not assignable to declared type "Frame | None"
  "CTkFrame" is not assignable to "Frame | None" (reportAttributeAccessIssue)
0 errors, 1 warning
```

### Pyright strict (adicionais)
```
src/modules/hub/format.py:11:1 - warning: Assignment to constant "_LOCAL_TZ" shadows
prior constant of same type (reportConstantRedefinition)
src/modules/hub/helpers/notes.py:41:1 - warning: Assignment to constant "_LOCAL_TZ"
shadows prior constant of same type (reportConstantRedefinition)
0 errors, 4 warnings (total)
```

### Vulture 100% (confirmados)
```
hub/views/hub_screen_view_pure.py:20: unused variable 'width'
main_window/views/main_window_actions.py:220: unused variable 'theme'
main_window/services/main_window_services.py:47: unused variable 'username'
core/services/clientes_service.py:49: unused variable 'base_delay'
core/services/clientes_service.py:49: unused variable 'max_retries'
```

### Pytest
```
1035 passed in 31.95s
```

---

## APÊNDICE B — Arquivos FORA DO ESCOPO desta auditoria

Os arquivos abaixo existem no workspace e podem conter issues não investigadas:
- `src/modules/clientes/**`
- `src/modules/cashflow/**`
- `src/modules/sites/**`
- `src/modules/notas/**` (diferente de `hub/notes_rendering.py`)
- `src/ui/**`
- `scripts/**`
- `diagnostics/**`

---

*Auditoria executada com: Python 3.13, ruff 0.x, pyright latest, vulture 2.x, deptry 0.x, pytest 8.x.*  
*Todas as ferramentas foram executadas no ambiente virtual do projeto com o suite completo passando.*
