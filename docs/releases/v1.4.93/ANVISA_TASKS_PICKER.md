# ANVISA Tasks Picker - Smart Navigation

## Contexto

No modo Hub ANVISA-only, o card **"Tarefas Hoje"** precisa navegar inteligentemente para o histórico de demandas ANVISA baseado no número de clientes com tarefas pendentes.

## Comportamento Implementado

### Regras de Navegação

1. **1 cliente único**: Abre `open_anvisa_history(client_id)` diretamente
2. **2+ clientes**: Abre modal `pick_anvisa_history_target(items)` para seleção
3. **Nenhum cliente identificado**: Fallback para `open_anvisa()` (tela principal)

### Detecção de Clientes

A lógica usa **`unique_client_ids`** extraídos de:
- `snapshot.clients_of_the_day` (prioridade)
- `snapshot.pending_tasks` (fallback)

**Importante**: Detecta clientes únicos, não total de tarefas. Múltiplas tarefas do mesmo cliente → navegação direta.

## Componentes Modificados

### Controllers
- `src/modules/hub/controllers/dashboard_actions.py`
  - `handle_tasks_today_card_click()`: Nova lógica de detecção + decisão de navegação

### Views
- `src/modules/hub/views/hub_screen.py`
  - `open_anvisa_history_picker()`: Orquestra modal e processa escolha do usuário

### Dialogs
- `src/modules/hub/views/hub_dialogs.py`
  - `pick_anvisa_history_target()`: Modal Treeview com lista de clientes + demandas
  - Botões: "Abrir histórico", "Abrir ANVISA", "Cancelar"
  - Atalhos: `Enter` (confirmar), `Escape` (cancelar), `Double-Click` (confirmar)

### Service
- `src/modules/hub/dashboard_service.py`
  - `get_dashboard_snapshot()`: Agora ANVISA-only, popula listas de demandas via `list_requests()`
  - Helpers: `_count_anvisa_open_and_due()`, `_build_anvisa_radar_from_requests()`, `_format_due_br()`

## Cobertura de Testes

### Unit Tests - Controllers
**Arquivo**: `tests/unit/modules/hub/controllers/test_dashboard_actions.py`
- ✅ 21 testes passando
- Casos cobertos:
  - `test_tasks_today_card_anvisa_only_with_multiple_tasks_opens_anvisa` (agora abre picker)
  - `test_tasks_today_card_anvisa_only_multiple_clients_opens_picker` (novo)
  - `test_tasks_today_card_anvisa_only_same_client_multiple_tasks_opens_history` (novo)

### Unit Tests - Service
**Arquivo**: `tests/unit/modules/hub/test_dashboard_service_mf43.py`
- ✅ 97 testes passando
- Migração completa para mocks de `infra.repositories.anvisa_requests_repository.list_requests`
- Helper de teste: `_fake_anvisa_requests()` gera demandas fake com status/due_date/check_daily

## Validações

```bash
# Linting
python -m ruff check CHANGELOG.md docs/ tests/

# Type Checking
python -m pyright --warnings tests/unit/modules/hub/test_dashboard_service_mf43.py tests/unit/modules/hub/controllers/test_dashboard_actions.py

# Tests
python -m pytest -q tests/unit/modules/hub/controllers/test_dashboard_actions.py -k "anvisa"
python -m pytest -q tests/unit/modules/hub/test_dashboard_service_mf43.py
```

## Referências

- ADR: `docs/adr/` (pendente, se houver)
- Testes: `tests/unit/modules/hub/controllers/test_dashboard_actions.py`, `test_dashboard_service_mf43.py`
- Changelog: `CHANGELOG.md` [Unreleased] → Fixed
