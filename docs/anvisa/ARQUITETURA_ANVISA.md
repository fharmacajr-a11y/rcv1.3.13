# Arquitetura do Módulo ANVISA

## Visão Geral

O módulo ANVISA gerencia demandas regulatórias submetidas à ANVISA para farmácias. Segue padrão **MVC incremental** com **Service Layer headless** extraído gradualmente das Views (padrão **Strangler Fig**).

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                    View Layer (Tkinter/ttkbootstrap)            │
│                                                                   │
│  AnvisaScreen                                                     │
│  ├── _anvisa_requests_mixin.py     (carregamento/cache)          │
│  ├── _anvisa_handlers_mixin.py     (handlers de botões)          │
│  └── _anvisa_history_popup_mixin.py (popup histórico)            │
│                                                                   │
│  Responsabilidade: APENAS renderizar UI                          │
│  - Recebe view models do Service                                 │
│  - Chama Controller para writes                                  │
│  - NÃO contém lógica de negócio                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ├─ consome view models
                     ├─ delega writes
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Service Layer (Headless)                      │
│                                                                   │
│  AnvisaService (src/modules/anvisa/services/anvisa_service.py)   │
│                                                                   │
│  Responsabilidade: Lógica de negócio SEM UI                      │
│  ├── build_main_rows()        → view model tabela principal      │
│  ├── build_history_rows()     → view model popup histórico       │
│  ├── allowed_actions()        → regras de botões                 │
│  ├── human_status()           → conversão status legível         │
│  ├── normalize_status()       → status legado → canônico         │
│  ├── can_close() / can_cancel() → regras de workflow             │
│  ├── format_dt_local()        → formatação timezone              │
│  ├── group_by_client()        → agrupamento por cliente          │
│  ├── summarize_demands()      → resumo de demandas               │
│  ├── check_duplicate_open_request() → validação duplicado        │
│  └── validate_new_request_in_memory() → validação pré-save       │
│                                                                   │
│  ✅ Testável sem Tkinter                                         │
│  ✅ Fonte única da verdade para regras                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ uses (read-only)
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Controller Layer                              │
│                                                                   │
│  AnvisaController (src/modules/anvisa/controllers/)              │
│                                                                   │
│  Responsabilidade: Orquestrar WRITES                             │
│  ├── set_status()        → atualização genérica de status        │
│  ├── close_request()     → finalizar demanda (done)              │
│  ├── cancel_request()    → cancelar demanda (canceled)           │
│  ├── delete_request()    → excluir demanda                       │
│  └── create_request()    → criar nova demanda                    │
│                                                                   │
│  ✅ Ponto único para writes                                      │
│  ✅ Logging centralizado                                         │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ delegates to
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Repository Layer                              │
│                                                                   │
│  AnvisaRequestsRepository (infra/repositories/)                  │
│                                                                   │
│  Responsabilidade: Acesso ao Supabase                            │
│  ├── list_requests()        → SELECT                             │
│  ├── create_request()       → INSERT                             │
│  ├── update_request_status() → UPDATE status                     │
│  └── delete_request()       → DELETE                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ SQL/RPC
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Database (Supabase/PostgreSQL)                │
│                                                                   │
│  Tabela: anvisa_requests                                         │
│  ├── id (UUID PK)                                                │
│  ├── org_id (TEXT FK)                                            │
│  ├── client_id (BIGINT FK → clients)                             │
│  ├── request_type (TEXT) - tipo de demanda                       │
│  ├── status (TEXT) - status da demanda                           │
│  ├── created_at (TIMESTAMPTZ)                                    │
│  ├── updated_at (TIMESTAMPTZ)                                    │
│  ├── created_by (TEXT)                                           │
│  └── payload (JSONB)                                             │
│                                                                   │
│  CHECK constraints:                                              │
│  - status IN (draft, submitted, in_progress, done, canceled)     │
└──────────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados

### Leitura (Listagem de Demandas)

```
1. View: _load_requests_from_cloud()
   ↓
2. Service: build_main_rows(requests)
   - Agrupa por client_id
   - Calcula resumos ("2 demandas (1 em aberto)")
   - Formata datas (timezone local)
   - Ordena por razão social
   ↓
3. View: Renderiza rows no Treeview
   - 1 linha por cliente
   - Mostra: ID | Razão Social | CNPJ | Demanda | Última Alteração
```

### Visualização de Histórico (Popup)

```
1. View: Double-click no cliente → _open_history_popup()
   ↓
2. Service: build_history_rows(demandas_do_cliente)
   - Extrai campos (tipo, status, datas)
   - normalize_status() → status canônico
   - human_status() → "Em aberto"/"Finalizado"
   - allowed_actions() → {close: true, cancel: true, delete: true}
   - Ordena por updated_at desc
   ↓
3. View: Renderiza popup
   - Tabela: Tipo | Status | Criada Em | Atualizada Em
   - Botões habilitados via row["actions"]
```

### Criação de Demanda

```
1. View: Botão "Nova" → Seleciona cliente
   ↓
2. View: Modal de seleção de tipo
   ↓
3. Service: validate_new_request_in_memory()
   - Verifica tipo válido (normalize_request_type)
   - Verifica duplicado (check_duplicate_open_request)
   ↓
4. Controller: create_request(org_id, client_id, request_type)
   - Converte client_id para int
   - Define status = "draft" (DEFAULT_CREATE_STATUS)
   ↓
5. Repository: create_request() → INSERT no Supabase
   ↓
6. View: Invalida cache + recarrega lista
```

### Workflow de Status (Finalizar/Cancelar)

```
1. View: Popup histórico → Botão "Finalizar" ou "Cancelar"
   - Botões habilitados via row["actions"] pré-calculadas
   ↓
2. View: Confirmação (messagebox)
   ↓
3. Controller: close_request(id) ou cancel_request(id)
   - Ambos delegam para set_status(id, novo_status)
   ↓
4. Repository: update_request_status() → UPDATE no Supabase
   ↓
5. View: Invalida cache + recarrega lista + atualiza popup
```

## Status Permitidos

### Status Canônicos (Banco)

```python
STATUS_OPEN = {"draft", "submitted", "in_progress"}
STATUS_CLOSED = {"done", "canceled"}

# Aliases legado → canônico
STATUS_ALIASES = {
    "aberta": "draft",
    "em andamento": "in_progress",
    "submetida": "submitted",
    "finalizada": "done",
    "concluida": "done",
    "cancelada": "canceled",
    # ... mais aliases
}
```

### Constantes de Workflow

```python
DEFAULT_CREATE_STATUS = "draft"        # Ao criar demanda
DEFAULT_CLOSE_STATUS = "done"          # Ao finalizar
```

### Transições de Status

```
draft ──┬─→ submitted ──→ in_progress ──→ done
        │
        └─→ canceled

Regras:
- close_request: status aberto → "done"
- cancel_request: status aberto → "canceled"
- delete_request: qualquer status
```

## Tipos de Demanda (REQUEST_TYPES)

```python
REQUEST_TYPES = [
    "Alteração do Responsável Legal",
    "Alteração do Responsável Técnico",
    "Alteração de Porte",
    "Cancelamento de AFE",
    "Baixa de Empresa",
    "Outras Solicitações ANVISA"
]
```

## Localização de Código

### Service (Lógica de Negócio)

```
src/modules/anvisa/services/anvisa_service.py (~700 linhas)
├── build_main_rows()        # View model tabela principal
├── build_history_rows()     # View model popup (com actions)
├── allowed_actions()        # Regras de botões {close, cancel, delete}
├── normalize_status()       # Legado → canônico
├── human_status()           # Canônico → "Em aberto"/"Finalizado"
├── can_close()              # True se status aberto
├── can_cancel()             # True se status aberto
├── format_dt_local()        # UTC → America/Sao_Paulo
├── group_by_client()        # Agrupa demandas por client_id
├── summarize_demands()      # Resumo: "X demandas (Y em aberto)"
├── check_duplicate_open_request()  # Valida duplicado mesmo tipo
├── validate_new_request_in_memory() # Validação completa pré-save
└── normalize_request_type() # Valida tipo oficial
```

### Controller (Writes)

```
src/modules/anvisa/controllers/anvisa_controller.py (~150 linhas)
├── set_status(id, status)   # Genérico update status
├── close_request(id)        # Delega set_status(id, "done")
├── cancel_request(id)       # Delega set_status(id, "canceled")
├── delete_request(id)       # Exclui demanda
└── create_request(...)      # Cria nova demanda
```

### View (Renderização)

```
src/modules/anvisa/views/
├── anvisa_screen.py                    # Tela principal
├── _anvisa_requests_mixin.py           # Carregamento/cache
├── _anvisa_handlers_mixin.py           # Handlers de botões
│   ├── _finalizar_demanda()
│   ├── _cancelar_demanda()
│   └── _excluir_demanda_popup()
└── _anvisa_history_popup_mixin.py      # Popup histórico
    ├── _open_history_popup()
    ├── _update_history_popup()
    └── _on_history_select()            # Habilita botões via actions
```

### Repository

```
infra/repositories/anvisa_requests_repository.py
├── list_requests(org_id)
├── create_request(org_id, client_id, request_type, status, ...)
├── update_request_status(request_id, new_status)
└── delete_request(request_id)
```

### Tests

```
tests/unit/modules/anvisa/
├── test_anvisa_service.py          # ~132 testes (lógica de negócio)
│   ├── build_main_rows
│   ├── build_history_rows (com actions)
│   ├── allowed_actions (open/closed)
│   ├── normalize_status (legado→canônico)
│   ├── human_status
│   ├── group_by_client
│   ├── summarize_demands
│   └── validate_new_request_in_memory
│
├── test_anvisa_controller.py       # ~24 testes (writes)
│   ├── set_status
│   ├── close_request
│   ├── cancel_request
│   ├── delete_request
│   └── create_request
│
└── test_anvisa_screen_basic.py     # ~11 testes (smoke/render)
    ├── Renderização sem erros
    ├── Botões presentes
    ├── Treeview com colunas
    └── Consumo de view models (sem revalidar lógica)
```

## Checklist de Teste Manual

### 1. Criar Nova Demanda

- [ ] Clicar em "Nova" → selecionar cliente
- [ ] Modal abre com 6 tipos de demanda
- [ ] Selecionar tipo → confirmar
- [ ] Demanda aparece na lista principal
- [ ] Status inicial: "Em aberto"
- [ ] Demanda aparece no histórico do cliente

### 2. Duplicado

- [ ] Tentar criar mesma demanda (mesmo tipo + cliente + status aberto)
- [ ] Sistema bloqueia e mostra mensagem de erro
- [ ] Pode criar demanda diferente para mesmo cliente
- [ ] Pode criar mesmo tipo se demanda anterior estiver finalizada/cancelada

### 3. Finalizar Demanda

- [ ] Double-click no cliente → popup histórico
- [ ] Selecionar demanda "Em aberto"
- [ ] Botão "Finalizar Demanda" habilitado
- [ ] Confirmar → status muda para "Finalizado"
- [ ] Botão "Finalizar" fica desabilitado (demanda fechada)

### 4. Cancelar Demanda

- [ ] Popup histórico → selecionar demanda "Em aberto"
- [ ] Botão "Cancelar" habilitado
- [ ] Confirmar → status muda para "Finalizado" (canceled)
- [ ] Botões "Finalizar" e "Cancelar" ficam desabilitados

### 5. Excluir Demanda

- [ ] Popup histórico → selecionar qualquer demanda
- [ ] Botão "Excluir" sempre habilitado
- [ ] Confirmar → demanda removida
- [ ] Lista principal atualizada
- [ ] Se era única demanda do cliente, cliente desaparece da lista

### 6. Histórico

- [ ] Double-click em cliente → popup abre
- [ ] Tabela mostra: Tipo | Status | Criada Em | Atualizada Em
- [ ] Demandas ordenadas por data de atualização (mais recente primeiro)
- [ ] Status legível: "Em aberto" ou "Finalizado"
- [ ] Datas formatadas: DD/MM/YYYY HH:MM

### 7. Browser (Janela Única)

- [ ] Tela ANVISA abre normalmente
- [ ] Clicar em "Nova" → browser abre
- [ ] Fechar browser sem selecionar → voltar para ANVISA
- [ ] Clicar em "Nova" novamente → browser NÃO abre segunda janela
- [ ] Selecionar cliente no browser → modal de tipo aparece

### 8. Listagem Principal

- [ ] Clientes ordenados por razão social (A→Z)
- [ ] CNPJ formatado: XX.XXX.XXX/XXXX-XX
- [ ] Coluna "Demanda": mostra tipo único ou "X demandas (Y em aberto)"
- [ ] Coluna "Última Alteração": formatada DD/MM/YYYY HH:MM
- [ ] Recarregar → lista atualiza

## Padrões e Convenções

### Princípios Arquiteturais

1. **View Layer**: APENAS renderização
   - Consome view models do Service
   - Delega writes ao Controller
   - NÃO valida lógica de negócio
   - NÃO formata datas/status diretamente

2. **Service Layer**: Lógica headless
   - Retorna view models prontos ({close: bool, cancel: bool})
   - Testável sem Tkinter
   - Fonte única da verdade

3. **Controller Layer**: Ponto único writes
   - Todos os updates passam por set_status()
   - Logging centralizado
   - Tratamento de exceções

4. **Repository Layer**: Acesso ao banco
   - Protocolo duck-typed (AnvisaRequestsRepository)
   - Dependency Injection via Protocol

### Padrões de Código

```python
# ✅ BOM: View consome view model
rows = self._service.build_history_rows(demandas)
for row in rows:
    actions = row["actions"]
    self._btn_finalizar.configure(state="normal" if actions["close"] else "disabled")

# ❌ RUIM: View valida regra
for demanda in demandas:
    status = demanda["status"]
    if status == "draft" or status == "in_progress":
        self._btn_finalizar.configure(state="normal")
```

### Testes

```python
# ✅ BOM: Testar Service (headless)
def test_allowed_actions_open_status():
    service = AnvisaService(repo)
    actions = service.allowed_actions("draft")
    assert actions["close"] is True
    assert actions["cancel"] is True

# ❌ RUIM: Testar View com lógica de negócio
def test_button_enabled_for_draft():
    screen = AnvisaScreen(root)
    # ... setup ...
    assert screen._btn_finalizar.cget("state") == "normal"
```

## Troubleshooting

### Botões desabilitados incorretamente

**Problema**: Botão "Finalizar" desabilitado para demanda aberta

**Causa**: View não está usando `allowed_actions` ou `build_history_rows` não retorna actions

**Solução**:
1. Verificar que `build_history_rows` inclui campo `actions`
2. Verificar que View usa `row["actions"]` (não calcula manualmente)
3. Verificar logs do Service

### Status legado não reconhecido

**Problema**: Status "ABERTA" não é tratado como aberto

**Causa**: Falta no `STATUS_ALIASES`

**Solução**:
1. Adicionar alias em `src/modules/anvisa/constants.py`
2. Adicionar teste em `test_anvisa_service.py`

### Demanda duplicada não bloqueada

**Problema**: Sistema permite criar demanda duplicada

**Causa**: Validação `check_duplicate_open_request` não executada

**Solução**:
1. Verificar que View chama `service.validate_new_request_in_memory()` antes de `controller.create_request()`
2. Verificar logs do Service

## Próximas Melhorias (Roadmap)

### P3.1: Anexos de Documentos
- Upload de PDFs/imagens
- Armazenamento no Supabase Storage
- Visualização inline

### P3.2: Notificações
- Alertas de status change
- Integração com sistema de notificações

### P3.3: Relatórios
- Exportação para Excel
- Dashboard de métricas

### P3.4: Histórico de Mudanças
- Auditoria completa (quem/quando/o quê)
- Tabela `anvisa_requests_history`

---

**Última atualização**: 19/12/2025  
**Versão**: v1.4.52
