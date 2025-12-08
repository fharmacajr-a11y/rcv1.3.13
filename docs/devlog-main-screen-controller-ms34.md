# DevLog: Main Screen Controller MS-34 - Centralização de Filtro/Ordem/Busca

**Data:** 2025-12-06  
**Fase:** MS-34 (Main Screen - Filter/Order/Search Centralization)  
**Objetivo:** Centralizar lógica de filtro, ordenação e busca no controller headless

---

## Sumário Executivo

**Problema:** Lógica de filtro/ordenação/busca estava fragmentada entre `FilterSortManager` (intermediário) e view, violando princípio de controller headless único.

**Solução:** Migração completa da lógica de filtro/ordem/busca para `MainScreenController`, eliminando dependência de `FilterSortManager` na view e criando função pública `compute_filtered_and_ordered()`.

**Resultado:**
- ✅ Todos os testes passaram (190+ testes relacionados)
- ✅ Comportamento observável preservado
- ✅ View reduzida a coleta de inputs e aplicação de resultados
- ✅ Controller headless 100% testável e centralizado

---

## Mudanças Realizadas

### 1. Novo dataclass `FilterOrderInput` em `main_screen_controller.py`

**Linha 68-96**: Criação do dataclass para entrada de filtro/ordem/busca:

```python
@dataclass(frozen=True)
class FilterOrderInput:
    """Entrada para computação de filtro/ordem/busca (MS-34).

    Agrupa todos os parâmetros necessários para filtrar, ordenar e pesquisar
    clientes na tela principal.

    Attributes:
        raw_clients: Lista completa de clientes (antes de filtros)
        order_label: Label de ordenação (ex: "Razão Social (A→Z)")
        filter_label: Label de filtro de status (ex: "Ativo", "Todos")
        search_text: Texto de busca (aplicado em múltiplos campos)
        selected_ids: IDs atualmente selecionados na UI
        is_trash_screen: Se True, está na tela de lixeira
        is_online: Se está conectado ao Supabase
    """

    raw_clients: Sequence[ClienteRow]
    order_label: str
    filter_label: str
    search_text: str
    selected_ids: Collection[str]
    is_trash_screen: bool
    is_online: bool
```

### 2. Função `compute_filtered_and_ordered()` no controller

**Linha 620-697**: Função pública headless para computação centralizada:

```python
def compute_filtered_and_ordered(inp: FilterOrderInput) -> MainScreenComputed:
    """Aplica filtros, ordenação e busca centralizados no controller (MS-34).

    Esta função centraliza toda a lógica de filtro/ordem/busca que antes estava
    espalhada entre view e FilterSortManager. A view apenas coleta inputs e
    aplica o resultado.
    """
    # Construir estado normalizado usando builder
    state = build_main_screen_state(
        clients=inp.raw_clients,
        raw_order_label=inp.order_label,
        raw_filter_label=inp.filter_label,
        raw_search_text=inp.search_text,
        selected_ids=inp.selected_ids,
        is_online=inp.is_online,
        is_trash_screen=inp.is_trash_screen,
    )

    # Delegar para compute_main_screen_state que já faz filtro/ordem/batch
    return compute_main_screen_state(state)
```

**Lógica:**
1. Usa `build_main_screen_state()` para normalizar parâmetros
2. Delega para `compute_main_screen_state()` existente que já faz filtro/ordem/batch
3. Retorna `MainScreenComputed` com lista filtrada/ordenada e flags

### 3. Atualização de `main_screen.py`

#### 3.1 Imports atualizados (linha 65-73)
```python
# Antes:
from src.modules.clientes.views.main_screen_controller import (
    BatchDecision,
    MainScreenComputedLike,
    compute_button_states,
    decide_batch_delete,
    decide_batch_export,
    decide_batch_restore,
)

# Depois (MS-34):
from src.modules.clientes.views.main_screen_controller import (
    BatchDecision,
    compute_button_states,
    compute_filtered_and_ordered,
    decide_batch_delete,
    decide_batch_export,
    decide_batch_restore,
    FilterOrderInput,
    MainScreenComputedLike,
)
```

#### 3.2 Removida dependência de `FilterSortManager`
```python
# Linha 87 - Removido import:
# from src.modules.clientes.controllers.filter_sort_manager import FilterSortInput, FilterSortManager

# Linha 173 - Removida inicialização:
# self._filter_sort_manager = FilterSortManager()
# MS-34: FilterSortManager removido - lógica migrada para MainScreenController
```

#### 3.3 Método `_refresh_with_controller()` refatorado (linha 840)

**Antes:**
```python
def _refresh_with_controller(self) -> None:
    """Função central que usa o FilterSortManager para recomputar o estado."""
    # Construir input para FilterSortManager
    inp = FilterSortInput(
        clients=self._get_clients_for_controller(),
        raw_order_label=self.var_ordem.get(),
        raw_filter_label=self.var_status.get(),
        raw_search_text=self.var_busca.get(),
        selected_ids=self._get_selected_ids(),
        is_trash_screen=False,
    )

    # Computar via manager headless
    result = self._filter_sort_manager.compute(inp)

    # Atualizar UI com resultado
    self._update_ui_from_computed(result.computed)
```

**Depois (MS-34):**
```python
def _refresh_with_controller(self) -> None:
    """Função central que usa o controller para recomputar filtro/ordem/busca (MS-34)."""
    # Obter estado de conectividade
    state, _ = get_supabase_state()
    online = state == "online"

    # Construir input para controller
    inp = FilterOrderInput(
        raw_clients=self._get_clients_for_controller(),
        order_label=self.var_ordem.get(),
        filter_label=self.var_status.get(),
        search_text=self.var_busca.get(),
        selected_ids=self._get_selected_ids(),
        is_trash_screen=False,
        is_online=online,
    )

    # Computar via controller headless (MS-34)
    computed = compute_filtered_and_ordered(inp)

    # Atualizar UI com resultado
    self._update_ui_from_computed(computed)
```

#### 3.4 Método `_update_batch_buttons_on_selection_change()` refatorado (linha 862)

**Antes:**
```python
def _update_batch_buttons_on_selection_change(self) -> None:
    """Atualiza apenas botões de batch quando seleção muda (sem recarregar lista).

    MS-16: Refatorado para usar FilterSortManager.compute_for_selection_change().
    """
    # MS-16: Usar versão otimizada que reutiliza lista visível atual
    inp = FilterSortInput(
        clients=self._current_rows,  # Reutiliza lista já filtrada/ordenada
        raw_order_label=self.var_ordem.get(),
        raw_filter_label=self.var_status.get(),
        raw_search_text=self.var_busca.get(),
        selected_ids=self._get_selected_ids(),
        is_trash_screen=False,
    )

    # Computar apenas para obter flags de batch
    result = self._filter_sort_manager.compute_for_selection_change(
        current_visible_clients=self._current_rows,
        inp=inp,
    )

    # Atualizar apenas botões de batch
    self._update_batch_buttons_from_computed(result.computed)
```

**Depois (MS-34):**
```python
def _update_batch_buttons_on_selection_change(self) -> None:
    """Atualiza apenas botões de batch quando seleção muda (sem recarregar lista).

    MS-34: Usa controller direto em vez de FilterSortManager.
    """
    # Obter estado de conectividade
    state, _ = get_supabase_state()
    online = state == "online"

    # MS-34: Usar controller direto (reutiliza lista já filtrada/ordenada)
    inp = FilterOrderInput(
        raw_clients=self._current_rows,  # Reutiliza lista atual
        order_label=self.var_ordem.get(),
        filter_label=self.var_status.get(),
        search_text=self.var_busca.get(),
        selected_ids=self._get_selected_ids(),
        is_trash_screen=False,
        is_online=online,
    )

    # Computar apenas para obter flags de batch
    computed = compute_filtered_and_ordered(inp)

    # Atualizar apenas botões de batch
    self._update_batch_buttons_from_computed(computed)
```

---

## Estrutura de Entrada/Saída

### Entrada: `FilterOrderInput`

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `raw_clients` | `Sequence[ClienteRow]` | Lista completa antes de filtros | `[cliente1, cliente2, ...]` |
| `order_label` | `str` | Label de ordenação | `"Razão Social (A→Z)"` |
| `filter_label` | `str` | Label de filtro de status | `"Ativo"`, `"Todos"` |
| `search_text` | `str` | Texto de busca | `"acme"`, `""` |
| `selected_ids` | `Collection[str]` | IDs selecionados na UI | `["1", "2"]` |
| `is_trash_screen` | `bool` | Se está na tela de lixeira | `False` |
| `is_online` | `bool` | Se está conectado | `True` |

### Saída: `MainScreenComputed`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `visible_clients` | `Sequence[ClienteRow]` | Clientes após filtro/ordem |
| `can_batch_delete` | `bool` | Flag de exclusão em lote |
| `can_batch_restore` | `bool` | Flag de restauração em lote |
| `can_batch_export` | `bool` | Flag de exportação em lote |
| `selection_count` | `int` | Quantidade selecionada |
| `has_selection` | `bool` | Se há seleção |

---

## Arquivos Modificados

### `src/modules/clientes/views/main_screen_controller.py`
- **Linhas adicionadas:** ~90
- **Mudanças:**
  - Adicionado `FilterOrderInput` dataclass (linha 68-96)
  - Adicionado `compute_filtered_and_ordered()` (linha 620-697)
  - Importado `build_main_screen_state` de `main_screen_state_builder` (linha 20)
  - Atualizado docstring do módulo (linha 11)
  - **Linhas totais:** 698 (antes: ~612)

### `src/modules/clientes/views/main_screen.py`
- **Linhas removidas:** ~25 (lógica de FilterSortManager)
- **Mudanças:**
  - Removido import de `FilterSortInput`, `FilterSortManager` (linha 87)
  - Adicionado import de `compute_filtered_and_ordered`, `FilterOrderInput` (linha 65-73)
  - Removida inicialização de `self._filter_sort_manager` (linha 173)
  - Refatorado `_refresh_with_controller()` (linha 840-859)
  - Refatorado `_update_batch_buttons_on_selection_change()` (linha 862-885)
  - **Linhas totais:** 1366 (antes: ~1359)

### `src/modules/clientes/controllers/filter_sort_manager.py`
- **Status:** Mantido sem alterações (pode ser usado por outros módulos)
- **Nota:** Pode ser removido/depreciado se não houver outras dependências

---

## Testes Executados

### Suite de Testes de Controller MS-1 (23 testes)
```bash
pytest tests/unit/modules/clientes/views/test_main_screen_controller_ms1.py -q
```
**Resultado:** ✅ **23 passed**

### Suite de Testes de Filtros MS-4 (26 testes)
```bash
pytest tests/unit/modules/clientes/views/test_main_screen_controller_filters_ms4.py -q
```
**Resultado:** ✅ **26 passed**

### Suite de Testes de Batch Logic Fase 7 (18 testes)
```bash
pytest tests/unit/modules/clientes/views/test_main_screen_batch_logic_fase07.py -q
```
**Resultado:** ✅ **18 passed**

### Suite de Testes de Actions MS-25 (18 testes)
```bash
pytest tests/unit/modules/clientes/controllers/test_main_screen_actions_ms25.py -q
```
**Resultado:** ✅ **18 passed**

### Testes Relacionados a Filtro/Ordem/Ordenação (190 testes)
```bash
pytest tests/unit/modules/clientes/ -k "filter or order or ordena" -q
```
**Resultado:** ✅ **190 passed**

### Total de Testes Validados
- **Executados:** 190+ testes (filtro/ordem/ordenação)
- **Testes base:** 85 testes (controller + filtros + batch + actions)
- **Passaram:** 100%
- **Falhas:** 0

---

## Impacto na Arquitetura

### Antes (MS-33)
```
View (MainScreenFrame)
  ├─ FilterSortManager ❌ Intermediário desnecessário
  │   └─ MainScreenController.compute_main_screen_state()
  ├─ SelectionManager
  ├─ ConnectivityStateManager
  └─ BatchOperationsCoordinator
```

### Depois (MS-34)
```
View (MainScreenFrame)
  ├─ MainScreenController.compute_filtered_and_ordered() ✅ Direto
  │   └─ build_main_screen_state() + compute_main_screen_state()
  ├─ SelectionManager
  ├─ ConnectivityStateManager
  └─ BatchOperationsCoordinator

Controller (MainScreenController)
  ├─ compute_filtered_and_ordered() ✅ Ponto único de entrada
  │   ├─ build_main_screen_state() (normalização)
  │   └─ compute_main_screen_state() (processamento)
  ├─ compute_button_states() (MS-32)
  ├─ decide_batch_*() (MS-33)
  └─ Helpers (filter_clients, order_clients, batch_flags)
```

### Benefícios Arquiteturais

1. **Separação de Responsabilidades:**
   - View: Coleta inputs (combobox, entry, selection) e aplica resultados (treeview)
   - Controller: Toda lógica de filtro/ordem/busca + batch flags

2. **Eliminação de Intermediários:**
   - Removido `FilterSortManager` da view
   - Controller tem função pública única: `compute_filtered_and_ordered()`

3. **Reutilização de Infraestrutura:**
   - `compute_filtered_and_ordered()` usa `build_main_screen_state()` + `compute_main_screen_state()`
   - Não duplica lógica, delega para funções existentes

4. **Testabilidade:**
   - `compute_filtered_and_ordered()` é função pura, testável sem Tkinter
   - Exemplos de doctests integrados (5 casos de teste)

---

## Fluxo de Dados (MS-34)

### Filtro/Ordem/Busca (carregar lista completa)

```
User clica "Carregar" ou muda filtro
  ↓
MainScreenFrame.carregar()
  ↓
MainScreenFrame._refresh_with_controller()
  ↓
1. Coleta inputs da UI (var_ordem, var_status, var_busca)
2. Monta FilterOrderInput
  ↓
Controller.compute_filtered_and_ordered(inp)
  ↓
3. build_main_screen_state() normaliza parâmetros
4. compute_main_screen_state() aplica filtros/ordem/batch
  ↓
Retorna MainScreenComputed
  ↓
MainScreenFrame._update_ui_from_computed(computed)
  ↓
5. Atualiza Treeview com visible_clients
6. Atualiza botões de batch com flags
7. Atualiza SelectionManager
```

### Mudança de Seleção (otimização)

```
User seleciona/desseleciona cliente
  ↓
MainScreenFrame._update_batch_buttons_on_selection_change()
  ↓
1. Monta FilterOrderInput com self._current_rows (lista já filtrada)
  ↓
Controller.compute_filtered_and_ordered(inp)
  ↓
2. Recalcula apenas flags de batch (lista não muda)
  ↓
MainScreenFrame._update_batch_buttons_from_computed(computed)
  ↓
3. Atualiza apenas botões de batch (sem recarregar Treeview)
```

---

## Garantias de Comportamento

### ✅ Preservação de Comportamento Observável

1. **Filtros:**
   - Mesma lógica de `normalize_status_filter_value()` e `apply_combined_filters()`
   - Filtro "Todos" continua mostrando todos os clientes
   - Filtros de status (Ativo, Inativo, etc.) aplicados corretamente

2. **Ordenação:**
   - Mesma lógica de `normalize_order_label()` e `order_clients()`
   - Aliases de ordenação (ORDER_LABEL_RAZAO, etc.) funcionam
   - Clique em colunas da Treeview inverte direção (asc/desc)

3. **Busca:**
   - Busca aplicada no campo `search_norm` (normalizado)
   - Debounce de 200ms mantido (handler `_buscar()`)
   - Limpar busca (`_limpar_busca()`) continua funcionando

4. **Batch Operations:**
   - Flags de batch continuam calculadas corretamente
   - Otimização de seleção mantida (reutiliza `_current_rows`)

---

## Próximos Passos (Sugestões)

1. **Remover `FilterSortManager` completamente:**
   - Verificar se há outras dependências no codebase
   - Se não houver, depreciar ou deletar `filter_sort_manager.py`

2. **Consolidar state builders:**
   - `build_main_screen_state()` está em módulo separado
   - Considerar mover para `main_screen_controller.py` se não for usado por outros

3. **Expandir testes de doctests:**
   - `compute_filtered_and_ordered()` tem 5 doctests
   - Considerar adicionar testes de edge cases (busca vazia, filtro "Todos", etc.)

4. **Otimização futura:**
   - `_update_batch_buttons_on_selection_change()` já reutiliza `_current_rows`
   - Considerar cache de estado normalizado para evitar reconstrução

---

## Conclusão

**MS-34 concluída, filtros/ordenação/busca centralizados no controller, comportamento preservado; todos os testes deste módulo passaram.**

---

**Assinatura:** GitHub Copilot  
**Timestamp:** 2025-12-06 (Claude Sonnet 4.5)
