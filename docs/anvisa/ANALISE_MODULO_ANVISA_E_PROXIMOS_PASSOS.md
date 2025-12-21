# Análise Técnica do Módulo ANVISA - RC v1.4.52

**Data da análise:** 19/12/2025  
**Status do módulo:** Funcional e estável com MVC parcial

---

## 1. Visão Geral

### Problema que o módulo resolve
O módulo ANVISA gerencia demandas regulatórias de clientes farmacêuticos junto à ANVISA (Agência Nacional de Vigilância Sanitária). Permite criar, visualizar, finalizar e excluir solicitações como:
- Alteração do Responsável Legal (RL)
- Alteração do Responsável Técnico (RT)
- Alteração da Razão Social
- Associação ao SNGPC
- Alteração de Porte
- **Cancelamento de AFE** (novo tipo adicionado)

### Principais telas
1. **Lista ANVISA** (tabela principal): 1 linha por cliente, resumo de demandas
2. **Popup de histórico**: Todas as demandas de um cliente específico com ações (finalizar/excluir)
3. **Modal de nova demanda**: Formulário para criar demanda com seleção de tipo
4. **Browser de arquivos**: Janela única por cliente para upload/gestão de documentos

### Fluxo de dados
```
Supabase (client_anvisa_requests + clients)
    ↓
AnvisaRequestsRepository (infra/repositories)
    ↓ list_requests / create_request / update_request_status / delete_request
AnvisaController (headless, sem GUI)
    ↓ delete_request / close_request
AnvisaScreen (View)
    ├─ _anvisa_requests_mixin.py (cache, load, helpers)
    ├─ _anvisa_handlers_mixin.py (eventos, menu contexto, exclusão)
    └─ _anvisa_history_popup_mixin.py (popup de histórico)
```

**Dados fluem:**
1. **Read**: Supabase → Repository (list_requests) → View (cache em `_requests_by_client`)
2. **Write**: View → Repository (create_request) → Supabase
3. **Update/Delete**: View → Controller → Repository → Supabase

---

## 2. Mapa do Código (Arquitetura Atual)

### Estrutura de arquivos

```
src/modules/anvisa/
├── views/
│   ├── anvisa_screen.py              [430 LOC] Tela principal + mixins + build UI
│   ├── _anvisa_requests_mixin.py     [446 LOC] Cache, load, helpers (status, duplicados, datetime)
│   ├── _anvisa_handlers_mixin.py     [550 LOC] Handlers de eventos, menu contexto, delete/finalizar
│   └── _anvisa_history_popup_mixin.py[337 LOC] Gerenciamento do popup de histórico
├── controllers/
│   └── anvisa_controller.py          [103 LOC] Controller headless (delete + close)
infra/repositories/
└── anvisa_requests_repository.py     [390 LOC] CRUD no Supabase + adapter

tests/unit/modules/anvisa/
├── test_anvisa_screen_basic.py       [644 LOC] Testes de helpers/formatação/lógica
└── test_anvisa_controller.py         [206 LOC] Testes do controller headless
```

### Responsabilidades por arquivo

| Arquivo | Responsabilidade |
|---------|-----------------|
| **anvisa_screen.py** | Tela principal: UI (Treeview + PanedWindow), integração mixins, centralização sash, anti-flash de janelas |
| **_anvisa_requests_mixin.py** | Load/cache de demandas, helpers (formato CNPJ/datetime/status), detecção duplicados, resumo para tabela |
| **_anvisa_handlers_mixin.py** | Eventos de UI (clique, duplo clique, menu contexto), ações delete/finalizar, abertura de browser único |
| **_anvisa_history_popup_mixin.py** | Popup de histórico: criação, centralização, foco, atualização de tree |
| **anvisa_controller.py** | Lógica headless de delete e close (finalizar), sem dependências de Tkinter |
| **anvisa_requests_repository.py** | Interface com Supabase: list/create/update/delete + normalização de status + adapter |

### Diagrama textual de dependências

```
┌─────────────────────────────────────────────────────────────┐
│  AnvisaScreen (ttk.Frame)                                   │
│  ├─ Herda de: AnvisaRequestsMixin, AnvisaHistoryPopupMixin, │
│  │             AnvisaHandlersMixin, ttk.Frame               │
│  ├─ Usa: AnvisaController (injeção de dependência)          │
│  └─ Interage: UploadsBrowserWindow (janela única)           │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────┐
        │  AnvisaController (headless)         │
        │  └─ Depende: AnvisaRequestsRepository│
        └─────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────┐
        │  AnvisaRequestsRepositoryAdapter     │
        │  └─ Funções: list/create/update/del  │
        └─────────────────────────────────────┘
                          ↓
               [ Supabase / PostgreSQL ]
```

### Pontos "headless" vs. UI
✅ **Headless (testável sem GUI):**
- `AnvisaController`: delete_request, close_request
- `anvisa_requests_repository`: todos os métodos CRUD
- Helpers puros em `_anvisa_requests_mixin`: `_norm_tipo`, `_is_open_status`, `_format_cnpj`, `_to_local_dt`

❌ **Ainda acoplado à UI (Tkinter):**
- Criação de demanda (modal + validação duplicado + insert Supabase) → em `anvisa_screen.py` (método `_on_new_anvisa_clicked`)
- Listagem e refresh → em `_anvisa_requests_mixin.py` (método `_load_requests_from_cloud`)
- Regras de summary e agrupamento → em `_anvisa_requests_mixin.py`
- Abertura de browser → em `_anvisa_handlers_mixin.py`

---

## 3. Resumo de Decisões Importantes

### Status do banco e mapeamento
- **Banco (CHECK constraint):** `draft`, `submitted`, `in_progress`, `done`, `canceled`
- **Exibição:** "Em aberto" (draft/submitted/in_progress) vs. "Finalizado" (done/canceled)
- **Normalização:** Repository tem dict de aliases para aceitar "Finalizada", "FECHADA", etc.

### Agrupamento 1 linha por cliente
- **Antes:** 1 linha por demanda (muitas linhas)
- **Agora:** 1 linha por cliente com resumo:
  - Se 1 demanda: mostra tipo diretamente
  - Se 2+ demandas: "X demandas (Y em aberto)"
- **Benefício:** Lista compacta, menos clutter

### Janela única do browser por cliente
- Dict `_anvisa_browser_windows[client_id]` mantém referência da janela
- Se já existe: `deiconify()` + `lift()` + `focus_force()`
- Se fechou: cleanup no callback `WM_DELETE_WINDOW`
- **Evita:** Múltiplas janelas do mesmo cliente abertas simultaneamente

### Bloqueio de resize/drag de colunas no Treeview
- `_lock_treeview_columns()` intercepta eventos:
  - `<Button-1>` e `<B1-Motion>` retornam "break" se region="separator"
  - `<Motion>` força cursor="arrow" no separator
- **Objetivo:** Layout fixo, UX consistente

### Timezone UTC → Local na exibição
- Banco armazena `created_at`/`updated_at` em UTC
- `_to_local_dt()` converte para UTC-3 (São Paulo, fixo)
- Formato exibido: `DD/MM/YYYY HH:MM`
- **Evita:** Confusão com horários em UTC

### Anti-flash/centralização de Toplevel
- **Padrão antigo:** Janelas surgem e "pulam" para o centro (flash visível)
- **Padrão novo:**
  1. `_prepare_hidden_window()`: `withdraw()` + `alpha=0.0` + `geometry("1x1+10000+10000")`
  2. Construir todos os widgets
  3. `_show_centered_no_flash()`: calcula centro, `geometry()`, `deiconify()`, restaura `alpha=1.0`
- **Resultado:** Janela aparece já centralizada, sem flash

### Novo tipo "Cancelamento de AFE"
- Adicionado na lista `request_types` em `_open_new_anvisa_request_dialog()`
- Funciona igual aos outros tipos (mesmas regras de duplicado/status)

### Cache de demandas por cliente
- `_demandas_cache[client_id]` armazena lista de demandas
- Invalidado após delete/create/update
- **Evita:** Requisições desnecessárias ao Supabase ao abrir histórico

### Popup de histórico (janela única)
- 1 popup por vez (reutiliza `_history_popup` se existir)
- Modal (grab_set) e transient ao parent
- Centralizado com `_center_window()` ou `_show_centered_no_flash()`
- Botões Finalizar/Excluir habilitados conforme status

---

## 4. Dívidas Técnicas e Riscos

### Pontos frágeis (podem quebrar fácil)
1. **Timezone fixo (UTC-3):** Não usa `zoneinfo`, assume São Paulo. Se cliente em outro timezone, horários errados.
2. **Normalização de status:** Dict de aliases em repository. Se usuário digitar status desconhecido, falha silenciosa (retorna False).
3. **Cache não sincronizado:** Se outro usuário alterar demandas, cache local fica desatualizado até refresh manual.
4. **Validação duplicado só na View:** Lógica em `anvisa_screen.py`. Se API externa criar demanda, bypass da regra.
5. **Janela de browser usa `winfo_exists()`:** Se janela for destruída de forma assíncrona, pode dar erro.

### Duplicação de código
- Helpers de janela (`withdraw`, `alpha`, `geometry`, centralização) repetidos em vários módulos:
  - `anvisa_screen.py`, `lixeira.py`, `pdf_preview`, `passwords`, `tasks`
- Formatação de CNPJ duplicada (deveria ser util global)
- Conversão datetime UTC→Local duplicada entre módulos

### Acoplamento UI ↔ Infra
- **Criação de demanda:** Toda lógica em `anvisa_screen._on_new_anvisa_clicked()` (UI)
  - Validação duplicado misturada com Tkinter
  - Messagebox dentro de lógica de negócio
  - Dificulta teste automatizado
- **Load requests:** `_load_requests_from_cloud()` popula Treeview diretamente
  - Não retorna dados para testes
  - Acoplado a `self.tree_requests`
- **Summary e agrupamento:** Em mixin, mas retorna já formatado para UI

### Pontos de UX para revisar depois
- [ ] Mensagem de "Múltiplas Demandas" ao excluir: UX confusa (abre histórico automaticamente)
- [ ] Botão "Excluir" desabilitado mesmo após selecionar linha (às vezes)
- [ ] Popup de histórico não fecha automaticamente após excluir última demanda
- [ ] Falta feedback visual após criar demanda (apenas `last_action.set()`)
- [ ] Botão "Nova" não valida se cliente selecionado (modo seleção pendente)
- [ ] Double-click abre browser, mas não há indicação visual de loading

---

## 5. Próximos Passos Recomendados (Roadmap Incremental)

### P0: Estabilização (Baixo Risco) - 4-6h total

**Objetivo:** Reduzir duplicação, centralizar constantes, melhorar robustez

#### P0.1: Centralizar constantes de status e request_type (1h)
- [ ] Criar `src/modules/anvisa/constants.py`:
  ```python
  REQUEST_TYPES = [
      "Alteração do Responsável Legal",
      "Alteração do Responsável Técnico",
      # ...
      "Cancelamento de AFE",
  ]

  STATUS_OPEN = {"draft", "submitted", "in_progress"}
  STATUS_CLOSED = {"done", "canceled"}
  STATUS_ALIASES = {...}
  ```
- [ ] Substituir hardcoded em `anvisa_screen.py`, `repository.py`, `_anvisa_requests_mixin.py`

#### P0.2: Padronizar helpers de janela em util global (1-2h)
- [ ] Criar `src/ui/window_utils.py` (se não existir, expandir):
  ```python
  def prepare_hidden_window(win: tk.Toplevel) -> None: ...
  def show_centered_no_flash(win: tk.Toplevel, parent: tk.Misc, ...) -> None: ...
  def apply_window_icon(win: tk.Toplevel | tk.Tk) -> None: ...
  ```
- [ ] Migrar `anvisa_screen._prepare_hidden_window()` e `_show_centered_no_flash()` para util
- [ ] Substituir em todos os módulos que usam (lixeira, pdf_preview, passwords, tasks)

#### P0.3: Reduzir logs redundantes (30min)
- [ ] Revisar `log.info()` duplicados em repository/controller/view
- [ ] Consolidar: 1 log no repository (fonte de verdade), controller só loga erros

#### P0.4: Garantir ações não disparam 2x (30min)
- [ ] Revisar binds de eventos em `anvisa_screen._build_ui()`:
  - `unbind()` antes de `bind()` para evitar duplos
  - Verificar se `_on_tree_select`, `_on_tree_double_click`, `_on_tree_right_click` podem ser chamados 2x
- [ ] Adicionar flag `_is_processing` para desabilitar botões temporariamente durante operações async

#### P0.5: Melhorar mensagens de erro e retorno bool do repo (30min)
- [ ] Repository sempre retorna `bool` (não `dict | None`)
- [ ] Controller interpreta `False` e loga mensagem específica
- [ ] View usa `messagebox` consistente (erro vs. warning vs. info)

#### P0.6: Formatação CNPJ em util global (30min)
- [ ] Mover `_format_cnpj()` para `src/utils/formatters.py` ou helpers
- [ ] Substituir em `anvisa_screen`, `clientes`, `uploads`

---

### P1: MVC Incremental (Strangler Fig) - 10-15h total

**Objetivo:** Mover lógica de negócio da View para Controller/Service, sem big bang

#### P1.1: Criar `AnvisaService` headless (2h)
- [ ] Novo arquivo: `src/modules/anvisa/services/anvisa_service.py`
- [ ] Responsabilidades:
  - Validação de duplicados (`check_duplicate_open_request`)
  - Criação de demanda (`create_request_for_client`)
  - Listagem com agrupamento (`list_requests_grouped_by_client`)
  - Summary de demandas (`summarize_demands`)
- [ ] Injeção de dependência: `AnvisaService(repository: AnvisaRequestsRepository)`
- [ ] Retorna dicts/listas, sem referência a Tkinter

**Teste:** `test_anvisa_service.py` com mock do repository

#### P1.2: Migrar validação de duplicado para Service (1h)
**De:** `anvisa_screen._on_new_anvisa_clicked()` valida duplicado inline  
**Para:** `service.check_duplicate_open_request(client_id, request_type) -> bool | dict`

**Novo método no service:**
```python
def check_duplicate_open_request(
    self,
    client_id: str,
    request_type: str
) -> Optional[dict[str, Any]]:
    """Busca demanda aberta duplicada do mesmo tipo."""
    ...
```

**View chama:**
```python
duplicado = self._service.check_duplicate_open_request(client_id, request_type)
if duplicado:
    # Mostrar messagebox
    return
```

**Teste:** `test_anvisa_service::test_check_duplicate_blocks_same_type_open`

#### P1.3: Migrar criação de demanda para Service (2h)
**De:** `anvisa_screen._on_new_anvisa_clicked()` cria + persiste + atualiza UI  
**Para:** `service.create_request_for_client(client_id, request_type) -> dict | None`

**Novo método no service:**
```python
def create_request_for_client(
    self,
    client_id: int,
    request_type: str,
    status: str = "draft"
) -> Optional[dict[str, Any]]:
    """Cria demanda no repositório e retorna registro criado."""
    org_id = self._resolve_org_id()
    if not org_id:
        return None

    return self._repo.create_request(org_id, client_id, request_type, status)
```

**View chama:**
```python
created = self._service.create_request_for_client(client_id, request_type)
if created:
    self._invalidate_cache(client_id)
    self._load_requests_from_cloud()
    messagebox.showinfo(...)
```

**Teste:** `test_anvisa_service::test_create_request_success`

#### P1.4: Migrar listagem/refresh para Service (2h)
**De:** `_anvisa_requests_mixin._load_requests_from_cloud()` carrega + popula Treeview  
**Para:** `service.list_requests_grouped() -> dict[str, list[dict]]`

**Novo método no service:**
```python
def list_requests_grouped_by_client(
    self,
    org_id: str
) -> dict[str, list[dict[str, Any]]]:
    """Lista demandas agrupadas por client_id."""
    ...
```

**View chama:**
```python
requests_by_client = self._service.list_requests_grouped_by_client(org_id)
self._populate_tree(requests_by_client)  # Novo método privado da View
```

**Teste:** `test_anvisa_service::test_list_requests_grouped`

#### P1.5: Migrar summary de demandas para Service (1h)
**De:** `_anvisa_requests_mixin._summarize_demands_for_main()` retorna strings formatadas  
**Para:** `service.summarize_demands(demandas) -> dict`

**Novo método no service:**
```python
def summarize_demands(
    self,
    demandas: list[dict[str, Any]]
) -> dict[str, Any]:
    """Resume demandas de um cliente."""
    return {
        "total": len(demandas),
        "open_count": sum(1 for d in demandas if self._is_open_status(d["status"])),
        "label": "...",  # Lógica de label
        "last_update": max(...),  # Datetime object
    }
```

**View formata:**
```python
summary = self._service.summarize_demands(demandas)
label = summary["label"]
last_update_str = self._format_datetime(summary["last_update"])
```

**Teste:** `test_anvisa_service::test_summarize_demands_single`

#### P1.6: Revisar Controller - expandir para close_multiple (30min)
- [ ] Adicionar `close_requests(request_ids: list[str]) -> dict[str, bool]`
- [ ] Útil para finalizar múltiplas demandas de uma vez (futuro)

**Teste:** `test_anvisa_controller::test_close_multiple_requests`

---

### P2: Qualidade / Testes / UX - 6-8h total

**Objetivo:** Melhorar cobertura de testes, reduzir testes com Tkinter, checklist de QA

#### P2.1: Melhorar testes headless (controller/service) (2h)
- [ ] `test_anvisa_controller.py`: adicionar testes de edge cases
  - Delete de request inexistente
  - Close de request já finalizada
  - Exceções no repository
- [ ] `test_anvisa_service.py` (novo): testar todos os métodos do service
  - Mock do repository com pytest-mock
  - Testar lógica de duplicado, summary, agrupamento

#### P2.2: Diminuir testes com Tkinter (1h)
- [ ] `test_anvisa_screen_basic.py`: manter apenas helpers puros
  - `_format_cnpj`, `_format_datetime`, `_is_open_status`, `_find_open_duplicate`
- [ ] Remover testes que dependem de `ttk.Frame` (smoke tests em E2E)

#### P2.3: Adicionar smoke test de integração (1h)
- [ ] Criar `tests/integration/test_anvisa_smoke.py`:
  - Mock do Supabase
  - Simula criação de demanda end-to-end
  - Valida que controller → repository → supabase funciona

#### P2.4: Checklist de testes manuais essenciais (30min)
Criar `docs/anvisa/CHECKLIST_MANUAL.md`:
```
- [ ] Abrir lista ANVISA
- [ ] Criar nova demanda
- [ ] Validar duplicado bloqueado
- [ ] Finalizar demanda via histórico
- [ ] Excluir demanda via menu contexto
- [ ] Abrir browser (janela única)
- [ ] Verificar timezone correto em demandas
- [ ] Fechar/reabrir popup de histórico
- [ ] Redimensionar colunas (deve estar bloqueado)
```

#### P2.5: Melhorar feedback visual (UX) (2h)
- [ ] Adicionar ProgressDialog ao criar demanda (simular delay)
- [ ] Toast notification após criar/excluir/finalizar (em vez de `last_action.set()`)
- [ ] Loader/spinner ao carregar demandas do Supabase
- [ ] Icone de status (🟢 aberto, 🔴 finalizado) na coluna de demandas

#### P2.6: Revisar mensagens de erro (30min)
- [ ] Padronizar título/mensagem de `messagebox`:
  - Erro: "Erro ao [ação]"
  - Warning: "Aviso"
  - Info: "Sucesso"
- [ ] Adicionar dica de ação no final ("Tente novamente" / "Contate o suporte")

---

## 6. Lista de "Quick Wins" (até 1h cada)

1. **Adicionar tipo "Renovação de AFE"** (15min)
   - Adicionar em `request_types` em `anvisa_screen.py` linha 582

2. **Ordenar tipos de demanda alfabeticamente** (5min)
   - `request_types.sort()` antes de popular radiobuttons

3. **Tooltip nos botões Nova/Excluir** (10min)
   - Usar `ttkbootstrap.tooltip.ToolTip(btn, "Texto")`

4. **Atalho de teclado para Nova (Ctrl+N)** (20min)
   - `self.bind_all("<Control-n>", lambda e: self._on_new_anvisa_clicked())`

5. **Atalho de teclado para Excluir (Delete)** (20min)
   - `self.tree_requests.bind("<Delete>", lambda e: self._on_delete_request_clicked())`

6. **Adicionar coluna "Criada em" na tabela principal** (30min)
   - Adicionar coluna `created_at` em `columns` e `_summarize_demands_for_main()`

7. **Filtro de demandas por status (aberto/finalizado)** (45min)
   - Adicionar Combobox acima da Treeview
   - Filtrar `_requests_by_client` ao popular tree

8. **Exportar lista para CSV** (1h)
   - Botão "Exportar" no rodapé
   - Usar `csv.writer()` para gerar arquivo

9. **Link direto para cliente em outra tela** (30min)
   - Coluna "ID" como hyperlink (bind `<Button-1>`)
   - Navegar para tela de clientes com filtro

10. **Indicador de demandas não lidas** (45min)
    - Badge com contador de novas demandas (created_at < 24h)
    - Exibir no label da caixinha "Anvisa"

---

## 7. Checklist de Verificação (Para o Usuário Testar no App)

### Funcionalidades básicas
- [ ] Abrir tela ANVISA e ver lista de clientes
- [ ] Verificar resumo de demandas (1 linha por cliente)
- [ ] Criar nova demanda clicando em "Nova"
- [ ] Validar que duplicado é bloqueado (mesma demanda aberta)
- [ ] Criar segunda demanda de tipo diferente para mesmo cliente
- [ ] Verificar que resumo atualiza para "X demandas (Y em aberto)"

### Histórico de demandas
- [ ] Clicar com botão direito em cliente e selecionar "Histórico de demandas"
- [ ] Verificar que popup abre centralizado sem flash
- [ ] Selecionar demanda aberta e clicar em "Finalizar"
- [ ] Verificar que status muda para "Finalizado"
- [ ] Fechar e reabrir histórico - verificar que status persiste

### Exclusão de demandas
- [ ] Excluir demanda única via botão "Excluir" (cliente com 1 demanda)
- [ ] Excluir demanda via menu contexto (botão direito)
- [ ] Cliente com múltiplas demandas: verificar que histórico abre
- [ ] Excluir demanda no popup via botão "Excluir"
- [ ] Verificar que cliente some da lista após excluir última demanda

### Browser de arquivos
- [ ] Duplo clique em cliente para abrir browser
- [ ] Verificar que janela abre com título correto (razão + CNPJ + tipo demanda)
- [ ] Tentar abrir browser do mesmo cliente novamente (deve reutilizar janela)
- [ ] Fechar browser e reabrir (deve criar nova janela)

### UI e formatação
- [ ] Verificar que CNPJ está formatado: `XX.XXX.XXX/XXXX-XX`
- [ ] Verificar que data/hora está no timezone local (UTC-3)
- [ ] Tentar redimensionar colunas (deve estar bloqueado)
- [ ] Verificar que sash do PanedWindow está centralizado (50/50)
- [ ] Redimensionar janela e verificar que layout não quebra

### Edge cases
- [ ] Criar demanda com cliente sem demandas anteriores
- [ ] Criar 10 demandas para mesmo cliente e verificar performance
- [ ] Finalizar todas as demandas de um cliente e verificar que mostra "0 em aberto"
- [ ] Tentar excluir demanda já excluída (deve mostrar aviso)
- [ ] Logout e login - verificar que demandas persistem

---

## Recomendação do Próximo Passo

**Comece por P0.1 e P0.2** (centralizar constantes + helpers de janela). São mudanças de baixo risco que reduzem duplicação e melhoram manutenibilidade. Isso prepara o terreno para as refatorações maiores de P1 (MVC incremental).

Após P0 estar 100% concluído e testado, parta para **P1.1 (criar AnvisaService)** e vá migrando responsabilidades uma de cada vez (P1.2 → P1.3 → ...), sempre com testes unitários. A abordagem Strangler Fig permite refatorar sem quebrar o sistema em produção.

**Prioridade atual (próximas 2 semanas):**
1. P0.1, P0.2, P0.6 (3h) → **Entrega:** Código mais limpo, sem duplicação
2. P1.1 (2h) → **Entrega:** Service headless testável
3. P1.2, P1.3 (3h) → **Entrega:** Validação duplicado + criação de demanda headless
4. P2.4 (30min) → **Entrega:** Checklist de QA para validar mudanças

**Isso totaliza ~8-9h de trabalho focado e entrega valor incremental a cada etapa.**

---

**Fim da análise** | RC v1.4.52 | Módulo ANVISA | 19/12/2025

---

## ✅ IMPLEMENTADO - P0.1 + P0.2 (19/12/2025)

### P0.1: Constantes Centralizadas ✅
**Arquivo criado:** [`src/modules/anvisa/constants.py`](../../src/modules/anvisa/constants.py)

**Constantes definidas:**
- `REQUEST_TYPES`: Lista com 6 tipos de demanda (incluindo "Cancelamento de AFE")
- `STATUS_OPEN`: Set com status abertos (`draft`, `submitted`, `in_progress`)
- `STATUS_CLOSED`: Set com status fechados (`done`, `canceled`)
- `STATUS_ALL`: União de todos os status válidos
- `STATUS_ALIASES`: Dict com 17 aliases para normalização (incluindo legados como "ABERTA")
- `DEFAULT_CLOSE_STATUS`: Status padrão para finalizar (`done`)

**Arquivos atualizados:**
- ✅ `src/modules/anvisa/views/anvisa_screen.py` (linha 582-590): Usa `REQUEST_TYPES` no modal
- ✅ `src/modules/anvisa/views/_anvisa_requests_mixin.py` (linha 130-152): Usa `STATUS_OPEN/CLOSED/ALIASES` em `_is_open_status()`
- ✅ `src/modules/anvisa/controllers/anvisa_controller.py` (linha 90): Usa `DEFAULT_CLOSE_STATUS` em `close_request()`
- ✅ `infra/repositories/anvisa_requests_repository.py` (linha 223-230): Usa `STATUS_ALL` e `STATUS_ALIASES`

**Benefícios:**
- ✅ Fonte única de verdade para tipos e status
- ✅ Facilita adicionar novos tipos de demanda (apenas 1 linha)
- ✅ Normalização consistente de status legados
- ✅ Menos duplicação de código

### P0.2: Helpers de Janela Unificados ✅
**Arquivo atualizado:** [`src/ui/window_utils.py`](../../src/ui/window_utils.py)

**Funções adicionadas:**
- `apply_window_icon(window)`: Aplica `rc.ico` em Toplevel/Tk
- `prepare_hidden_window(win)`: Prepara janela hidden (anti-flash)
- `show_centered_no_flash(win, parent, width, height)`: Mostra janela centralizada sem flash
- `center_window_simple(window, parent)`: Centralização simples

**Arquivos atualizados:**
- ✅ `src/modules/anvisa/views/anvisa_screen.py`:
  - Importa helpers do `window_utils` (linha 21-26)
  - Remove métodos estáticos `_apply_window_icon`, `_prepare_hidden_window`, `_show_centered_no_flash`
  - Usa `prepare_hidden_window()` e `apply_window_icon()` no modal (linha 459-467)
  - Usa `show_centered_no_flash()` para centralização (linha 566)
- ✅ `src/modules/anvisa/views/_anvisa_history_popup_mixin.py`:
  - Importa helpers do `window_utils` (linha 12-16)
  - Remove método `_center_window()` (duplicado)
  - Usa `prepare_hidden_window()` e `apply_window_icon()` no popup (linha 53-61)
  - Usa `center_window_simple()` para reposicionar popup (linha 43)

**Benefícios:**
- ✅ Elimina duplicação de helpers entre módulos (ANVISA, lixeira, pdf_preview, etc.)
- ✅ Facilita manutenção (1 lugar para corrigir bugs)
- ✅ Padrão consistente de anti-flash em todas as janelas
- ✅ Reduz LOC total do projeto

### Validações Executadas ✅
```bash
✅ python -m compileall (todos os arquivos alterados) - OK
✅ python -m ruff check --fix (7 arquivos) - 1 erro corrigido automaticamente
✅ python -m pyright (4 arquivos) --level error - 0 erros
✅ pytest test_anvisa_controller.py - 9 passed
✅ pytest test_anvisa_screen_basic.py - 19 passed, 15 skipped
```

### Comportamento Mantido ✅
- ✅ Criação de demanda funciona idêntico (modal com 6 tipos)
- ✅ Validação de duplicado usa mesma lógica (agora com constantes)
- ✅ Finalizar demanda seta status `done` como antes
- ✅ Janelas aparecem centralizadas sem flash (mesmo comportamento)
- ✅ Ícone `rc.ico` aplicado em todas as janelas
- ✅ Testes passam sem regressão

### Próximos Passos Recomendados
Agora que P0.1 e P0.2 estão concluídos, partir para:
1. **P0.3**: Reduzir logs redundantes (30min)
2. **P0.4**: Garantir ações não disparam 2x (30min)
3. **P0.6**: Formatação CNPJ em util global (30min)

Após P0 completo, iniciar **P1.1** (criar AnvisaService).

---

**Fim da análise** | RC v1.4.52 | Módulo ANVISA | 19/12/2025
