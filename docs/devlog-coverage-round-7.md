# Devlog: Cobertura Round 7 - Clientes MainScreen (ordenação)

**MICROFASE 05 - Round 7 - Fase 1**: Extração de lógica de ordenação de `main_screen.py` para `main_screen_helpers.py`.

---

## 📋 Contexto

- `src/modules/clientes/views/main_screen.py` é um arquivo grande (~1647 linhas).
- Esta fase foca somente em:
  - rótulos de ordenação (`ORDER_LABEL_*`),
  - aliases de labels (`ORDER_LABEL_ALIASES`),
  - dicionário `ORDER_CHOICES`,
  - normalização de rótulos para a combobox/menu de ordenação.

---

## 🎯 Objetivos

Refatorar a lógica de ordenação para:

1. **Separar constantes de ordenação** do código GUI
2. **Criar helpers puros** para normalização
3. **Aumentar testabilidade** com testes unitários específicos
4. **Manter funcionalidade** exatamente igual na tela

---

## 🧩 Arquivos alterados

### Modificados

- `src/modules/clientes/views/main_screen.py` (redução: ~50 linhas)
- `src/modules/clientes/views/main_screen_helpers.py` (adição: ~115 linhas)

### Criados

- `tests/unit/modules/clientes/views/test_main_screen_order_helpers_round7.py` (18 testes)

---

## 🔧 Resumo técnico

### 1. Constantes movidas para `main_screen_helpers.py`

Extraídas do topo de `main_screen.py`:

```python
ORDER_LABEL_RAZAO = "Razão Social (A→Z)"
ORDER_LABEL_CNPJ = "CNPJ (A→Z)"
ORDER_LABEL_NOME = "Nome (A→Z)"
ORDER_LABEL_ID_ASC = "ID (1→9)"
ORDER_LABEL_ID_DESC = "ID (9→1)"
ORDER_LABEL_UPDATED_RECENT = "Última Alteração (mais recente)"
ORDER_LABEL_UPDATED_OLD = "Última Alteração (mais antiga)"

ORDER_LABEL_ALIASES = {
    "Razao Social (A->Z)": ORDER_LABEL_RAZAO,
    "CNPJ (A->Z)": ORDER_LABEL_CNPJ,
    "Nome (A->Z)": ORDER_LABEL_NOME,
    "Ultima Alteracao (mais recente)": ORDER_LABEL_UPDATED_RECENT,
    "Ultima Alteracao (mais antiga)": ORDER_LABEL_UPDATED_OLD,
    "ID (1→9)": ORDER_LABEL_ID_ASC,
    "ID (1->9)": ORDER_LABEL_ID_ASC,
    "ID (9→1)": ORDER_LABEL_ID_DESC,
    "ID (9->1)": ORDER_LABEL_ID_DESC,
}

DEFAULT_ORDER_LABEL = ORDER_LABEL_RAZAO

ORDER_CHOICES: Dict[str, Tuple[Optional[str], bool]] = {
    ORDER_LABEL_RAZAO: ("razao_social", False),
    ORDER_LABEL_CNPJ: ("cnpj", False),
    ORDER_LABEL_NOME: ("nome", False),
    ORDER_LABEL_ID_ASC: ("id", False),
    ORDER_LABEL_ID_DESC: ("id", True),
    ORDER_LABEL_UPDATED_RECENT: ("ultima_alteracao", False),
    ORDER_LABEL_UPDATED_OLD: ("ultima_alteracao", True),
}
```

### 2. Helpers puros criados

**`normalize_order_label(label: Optional[str]) -> str`**

- Normaliza rótulos usando `ORDER_LABEL_ALIASES`
- Trata `None` e strings vazias
- Retorna aliases conhecidos como labels canônicos
- Labels desconhecidos são retornados com `strip()`

**`normalize_order_choices(order_choices: Dict[str, Tuple[Optional[str], bool]]) -> Dict[str, Tuple[Optional[str], bool]]`**

- Normaliza chaves do dicionário de opções
- Mantém valores (campo, reverse) intocados
- Permite personalização de opções de ordenação

### 3. Refatoração de `MainScreenFrame`

**Removido:**
- Métodos `_normalize_order_label` (static)
- Métodos `_normalize_order_choices` (classmethod)
- Todas as constantes de ordenação

**Adicionado:**
- Imports dos helpers e constantes

**Atualizado no `__init__`:**

```python
# Antes:
self._order_choices = self._normalize_order_choices(order_choices or ORDER_CHOICES)
self._default_order_label = self._normalize_order_label(default_order_label) or DEFAULT_ORDER_LABEL

# Depois:
self._order_choices = normalize_order_choices(order_choices or ORDER_CHOICES)
self._default_order_label = normalize_order_label(default_order_label) or DEFAULT_ORDER_LABEL
```

### 4. Nenhuma alteração visual

- Layout permanece idêntico
- Combobox de ordenação funciona igual
- Comportamento da UI inalterado
- **Somente refatoração interna**

---

## ✅ Testes criados

### `test_main_screen_order_helpers_round7.py`

**Total: 18 testes** organizados em 4 classes:

#### `TestNormalizeOrderLabel` (5 testes)
- ✅ Normalização de aliases conhecidos
- ✅ Variantes de formato de seta (`->` vs `→`)
- ✅ Casos genéricos e de borda (empty, None)
- ✅ Preservação de labels desconhecidos
- ✅ Tratamento de whitespace

#### `TestNormalizeOrderChoices` (4 testes)
- ✅ Normalização de chaves do dicionário
- ✅ Preservação de valores (campo, reverse)
- ✅ Dicionário vazio
- ✅ Mix de aliases e labels canônicos

#### `TestOrderChoicesConstants` (8 testes)
- ✅ Chaves esperadas presentes
- ✅ Valores são tuplas válidas
- ✅ DEFAULT_ORDER_LABEL está em ORDER_CHOICES
- ✅ Padrão é Razão Social
- ✅ Mapeamentos específicos (razao, id, updated)

#### `TestOrderLabelConstants` (1 teste)
- ✅ Formato correto dos labels
- ✅ Unicidade dos labels

---

## 🧪 Testes rodados pelo agente

### Imports

```powershell
✅ python -c "from src.modules.clientes.views import main_screen_helpers as msh; print('CLIENTES_MAIN_SCREEN_HELPERS_IMPORT_OK')"
   → CLIENTES_MAIN_SCREEN_HELPERS_IMPORT_OK

✅ python -c "from src.modules.clientes.views.main_screen import MainScreenFrame; print('CLIENTES_MAIN_SCREEN_IMPORT_OK')"
   → CLIENTES_MAIN_SCREEN_IMPORT_OK
```

### Testes unitários

```powershell
✅ python -m pytest tests/unit/modules/clientes/views/test_main_screen_order_helpers_round7.py -v
   → 18 passed in 3.20s

✅ python -m pytest tests/unit/modules/clientes/views/test_main_screen_batch_integration_fase05.py -v
   → 11 passed in 2.62s
```

---

## 📊 Métricas

| Métrica | Antes | Depois | Diferença |
|---------|-------|--------|-----------|
| Linhas em `main_screen.py` | ~1647 | ~1597 | **-50** |
| Linhas em `main_screen_helpers.py` | ~764 | ~879 | **+115** |
| Testes de ordenação | 0 | 18 | **+18** |
| Métodos internos em `MainScreenFrame` | 2 | 0 | **-2** |
| Constantes no nível do módulo | 9 | 0 | **-9** |

---

## 🎓 Lições aprendidas

### ✅ Boas práticas aplicadas

1. **Separação de responsabilidades**
   - Constantes e lógica pura → `helpers`
   - Orquestração GUI → `MainScreenFrame`

2. **Testabilidade**
   - Helpers puros são triviais de testar
   - Não dependem de Tkinter ou GUI
   - Cobertura completa de casos de borda

3. **Documentação**
   - Docstrings com Examples
   - Type hints completos
   - Comentários organizacionais

4. **Incremental**
   - Mudanças pequenas e focadas
   - Validação constante (imports + testes)
   - Sem quebrar funcionalidade existente

### 🔍 Oportunidades futuras

- Round 7 - Fase 2: Extrair lógica de filtros
- Round 7 - Fase 3: Extrair handlers de eventos
- Round 7 - Fase 4: Extrair lógica de seleção/pick mode

---

## 🏁 Status final

✅ **COMPLETO** - Round 7, Fase 1

- Todos os testes passando
- Imports validados
- Funcionalidade preservada
- Código mais testável e modular
- Documentação criada

---

## 📝 Notas técnicas

### Compatibilidade

- Python 3.13.7
- pytest 8.4.2
- Sem dependências adicionais

### Padrão de aliases

O sistema suporta dois formatos de seta:
- `->` (ASCII, usado em aliases)
- `→` (Unicode, usado em labels canônicos)

Exemplo:
```python
"ID (1->9)" → normaliza para → "ID (1→9)"
```

Isso permite flexibilidade em configurações legadas mantendo consistência visual.

---

**Próximo passo sugerido:** Round 7 - Fase 3 (Handlers de eventos)

---

## FASE 2: Extração da lógica de filtros

**Data:** 1 de dezembro de 2025

### 📋 Contexto

Após a conclusão da Fase 1 (ordenação), esta fase foca na extração da **lógica de filtros** da tela principal de clientes, especificamente:

- Normalização de valores de filtro de status
- Construção de opções para combobox de filtros
- Resolução de seleção atual com fallback inteligente

### 🎯 Objetivos

Refatorar a lógica de filtros para:

1. **Separar lógica de normalização** de filtros do código GUI
2. **Criar helpers puros** para manipulação de filtros
3. **Aumentar testabilidade** com testes unitários específicos
4. **Manter funcionalidade** exatamente igual na tela

### 🧩 Arquivos alterados

**Modificados:**
- `src/modules/clientes/views/main_screen.py` (redução: ~15 linhas de lógica complexa)
- `src/modules/clientes/views/main_screen_helpers.py` (adição: ~145 linhas)

**Criados:**
- `tests/unit/modules/clientes/views/test_main_screen_filter_helpers_round7.py` (27 testes)

### 🔧 Resumo técnico

#### 1. Constantes adicionadas a `main_screen_helpers.py`

```python
# Label especial para "sem filtro"
FILTER_LABEL_TODOS = "Todos"
DEFAULT_FILTER_LABEL = FILTER_LABEL_TODOS

# Aliases para normalização (case-insensitive)
FILTER_LABEL_ALIASES: Dict[str, str] = {
    "todos": FILTER_LABEL_TODOS,
    "TODOS": FILTER_LABEL_TODOS,
    "all": FILTER_LABEL_TODOS,
    "All": FILTER_LABEL_TODOS,
    "ALL": FILTER_LABEL_TODOS,
}
```

#### 2. Helpers puros criados

**`normalize_filter_label(label: Optional[str]) -> str`**
- Normaliza rótulos de filtro usando aliases
- Trata `None` e strings vazias
- Retorna aliases conhecidos como labels canônicos

**`normalize_status_filter_value(status_value: Optional[str]) -> Optional[str]`**
- Converte "Todos" (case-insensitive) para `None`
- Normaliza outros valores com `strip()`
- Usado para converter valor da UI para formato interno

**`build_filter_choices_with_all_option(status_options: Sequence[str]) -> list[str]`**
- Adiciona "Todos" no início das opções
- Usado para popular combobox de filtros

**`resolve_filter_choice_from_options(current_value: Optional[str], available_choices: Sequence[str]) -> str`**
- Faz matching case-insensitive
- Retorna opção com case correto
- Fallback para "Todos" se valor inválido

#### 3. Refatoração de `MainScreenFrame`

**Método `apply_filters`:**

```python
# Antes:
status_filter = None if not status_value or status_value.lower() == "todos" else status_value

# Depois:
status_filter = normalize_status_filter_value(status_value)
```

**Método `_populate_status_filter_options`:**

```python
# Antes (10 linhas de lógica):
choices = ["Todos"] + statuses if statuses else ["Todos"]
# ... lógica de normalização case-insensitive ...
normalized_current = current.lower()
available_map = {choice.lower(): choice for choice in choices}
if normalized_current in available_map:
    resolved = available_map[normalized_current]
    if resolved != current:
        self.var_status.set(resolved)
else:
    self.var_status.set("Todos")

# Depois (3 linhas):
choices = build_filter_choices_with_all_option(statuses)
resolved = resolve_filter_choice_from_options(current, choices)
if resolved != current:
    self.var_status.set(resolved)
```

### ✅ Testes criados

#### `test_main_screen_filter_helpers_round7.py`

**Total: 27 testes** organizados em 6 classes:

**`TestNormalizeFilterLabel` (5 testes)**
- ✅ Normalização de variantes "Todos"
- ✅ Preservação de status específicos
- ✅ Strip de whitespace
- ✅ Casos de borda (None, empty)
- ✅ Case sensitivity para não-aliases

**`TestNormalizeStatusFilterValue` (4 testes)**
- ✅ "Todos" → None (case-insensitive)
- ✅ Valores vazios → None
- ✅ Preservação de status válidos
- ✅ Case sensitivity (exceto "Todos")

**`TestBuildFilterChoicesWithAllOption` (5 testes)**
- ✅ Adiciona "Todos" no início
- ✅ Lista vazia
- ✅ Preservação de ordem
- ✅ Lista com único item
- ✅ Não modifica input

**`TestResolveFilterChoiceFromOptions` (7 testes)**
- ✅ Matching case-insensitive
- ✅ Match exato
- ✅ Fallback para padrão se não encontrar
- ✅ None/empty → padrão
- ✅ Tratamento de whitespace
- ✅ Lista vazia de opções
- ✅ Duplicatas com case variants

**`TestFilterConstants` (3 testes)**
- ✅ FILTER_LABEL_TODOS definido
- ✅ DEFAULT_FILTER_LABEL = "Todos"
- ✅ Tipos corretos

**`TestFilterIntegration` (3 testes)**
- ✅ Workflow: build + resolve + normalize
- ✅ Workflow: seleção "Todos"
- ✅ Workflow: seleção inválida → fallback

### 🧪 Testes executados

```powershell
✅ python -m pytest tests/unit/modules/clientes/views/test_main_screen_order_helpers_round7.py -v
   → 18 passed in 3.34s

✅ python -m pytest tests/unit/modules/clientes/views/test_main_screen_filter_helpers_round7.py -v
   → 27 passed in 4.11s

✅ python -m pytest tests/unit/modules/clientes/views/test_main_screen_batch_integration_fase05.py -v
   → 11 passed in 2.69s
```

### 📊 Métricas da Fase 2

| Métrica | Antes | Depois | Diferença |
|---------|-------|--------|-----------|
| Linhas de lógica em `apply_filters` | 3 | 1 | **-2** |
| Linhas de lógica em `_populate_status_filter_options` | 15 | 7 | **-8** |
| Linhas em `main_screen_helpers.py` | ~879 | ~1024 | **+145** |
| Testes de filtros | 0 | 27 | **+27** |
| Helpers de filtros | 0 | 4 | **+4** |

### 🎓 Lições aprendadas na Fase 2

**✅ Boas práticas aplicadas:**

1. **Reutilização de padrões da Fase 1**
   - Mesma estrutura de constantes e helpers
   - Organização similar de testes
   - Documentação consistente

2. **Helpers compostos**
   - `normalize_status_filter_value` encapsula lógica "Todos" → None
   - `resolve_filter_choice_from_options` abstrai matching complexo
   - Cada helper tem responsabilidade única

3. **Evitando conflitos de nomes**
   - Renomeado `build_status_filter_choices` → `build_filter_choices_with_all_option`
   - Evita sobrecarga com função legada de assinatura diferente

4. **Testes de integração**
   - Classe `TestFilterIntegration` valida workflows completos
   - Garante que helpers funcionam bem juntos

**🔍 Observações técnicas:**

- Função legada `build_status_filter_choices(clients, ...)` ainda existe no código
- Nova função `build_filter_choices_with_all_option(statuses)` tem propósito mais específico
- Ambas coexistem sem conflito após renomeação

### 🏁 Status da Fase 2

✅ **COMPLETO** - Round 7, Fase 2

- Todos os testes passando (56 testes no total: 18 + 27 + 11)
- Imports validados
- Funcionalidade preservada
- Lógica de filtros modularizada
- Código mais testável

### 📊 Métricas acumuladas (Fases 1 + 2)

| Métrica | Round 7 Total |
|---------|---------------|
| **Testes criados** | **45** (18 + 27) |
| **Helpers extraídos** | **6** (2 ordenação + 4 filtros) |
| **Linhas de lógica removidas de GUI** | **~60** |
| **Linhas adicionadas em helpers** | **~260** |
| **Cobertura de casos de borda** | **Alta** |

---

**Próximo passo sugerido:** Round 7 - Fase 3 (Handlers de eventos)

---

## FASE 3: Extração da lógica de handlers de eventos

**Data:** 1 de dezembro de 2025

###  Contexto

Após as Fases 1 (ordenação) e 2 (filtros), esta fase foca na extração da **lógica de decisão dos handlers de eventos** da tela principal de clientes, especificamente:

- Classificação de seleção (nenhum, um ou múltiplos itens)
- Validação de seleção para ações específicas
- Decisões sobre permissão de ações baseadas em seleção

###  Objetivos

Refatorar a lógica de eventos para:

1. **Separar decisão de apresentação** (lógica pura vs GUI)
2. **Criar helpers reutilizáveis** para validação de seleção
3. **Aumentar testabilidade** com testes unitários sem Tkinter
4. **Padronizar** padrões de validação entre handlers

###  Arquivos alterados

**Modificados:**
- `src/modules/clientes/views/main_screen.py` (imports atualizados)
- `src/modules/clientes/views/main_screen_helpers.py` (adição: ~136 linhas)

**Criados:**
- `tests/unit/modules/clientes/views/test_main_screen_event_helpers_round7.py` (32 testes)

###  Resumo técnico

#### 1. Helpers de seleção criados

**`classify_selection(selected_ids: Collection[str]) -> SelectionResult`**
- Classifica seleção como "none", "single" ou "multiple"
- Retorna tupla (status, client_id)
- Trabalha com qualquer coleção (set, list, tuple)

**`validate_single_selection(selected_ids: Collection[str]) -> Tuple[bool, Optional[str], Optional[str]]`**
- Helper conveniente para validação completa
- Retorna (is_valid, client_id, error_key)
- error_key pode ser usado para buscar mensagens apropriadas

**`can_perform_single_item_action(selection_status: SelectionStatus) -> bool`**
- Decide se pode executar ação que requer exatamente 1 item
- Retorna True apenas para status "single"

**`can_perform_multi_item_action(selection_status: SelectionStatus) -> bool`**
- Decide se pode executar ação que aceita múltiplos itens
- Retorna True para "single" ou "multiple"

**`get_selection_count(selected_ids: Collection[str]) -> int`**
- Retorna quantidade de itens selecionados
- Helper simples mas padroniza acesso

**`has_selection(selected_ids: Collection[str]) -> bool`**
- Verifica se há pelo menos um item selecionado
- Padrão comum em vários handlers

#### 2. Type aliases definidos

```python
SelectionStatus = Literal["none", "single", "multiple"]
SelectionResult = Tuple[SelectionStatus, Optional[str]]
```

###  Testes criados

#### `test_main_screen_event_helpers_round7.py`

**Total: 32 testes** organizados em 7 classes:

- **TestClassifySelection** (9 testes)
- **TestCanPerformSingleItemAction** (3 testes)
- **TestCanPerformMultiItemAction** (3 testes)
- **TestValidateSingleSelection** (5 testes)
- **TestGetSelectionCount** (4 testes)
- **TestHasSelection** (4 testes)
- **TestEventHelpersIntegration** (4 testes)

###  Testes executados

```powershell
 python -m pytest tests/unit/modules/clientes/views/test_main_screen_order_helpers_round7.py -v
    18 passed in 3.08s

 python -m pytest tests/unit/modules/clientes/views/test_main_screen_filter_helpers_round7.py -v
    27 passed in 4.16s

 python -m pytest tests/unit/modules/clientes/views/test_main_screen_event_helpers_round7.py -v
    32 passed in 4.51s

 python -m pytest tests/unit/modules/clientes/views/test_main_screen_batch_integration_fase05.py -v
    11 passed in 2.57s
```

###  Métricas da Fase 3

| Métrica | Antes | Depois | Diferença |
|---------|-------|--------|-----------|
| Linhas em `main_screen_helpers.py` | ~1024 | ~1160 | **+136** |
| Testes de eventos | 0 | 32 | **+32** |
| Helpers de eventos | 0 | 6 | **+6** |
| Funções legadas removidas | 0 | 2 | **-2** (duplicatas) |

###  Status da Fase 3

 **COMPLETO** - Round 7, Fase 3

- Todos os testes passando (88 testes no total: 18 + 27 + 32 + 11)
- Imports validados
- Helpers de eventos criados e testados
- Nenhuma quebra de funcionalidade
- Base sólida para refatoração incremental de handlers

###  Métricas acumuladas (Fases 1 + 2 + 3)

| Métrica | Round 7 Total |
|---------|---------------|
| **Testes criados** | **77** (18 + 27 + 32) |
| **Helpers extraídos** | **12** (2 ordenação + 4 filtros + 6 eventos) |
| **Linhas adicionadas em helpers** | **~396** |
| **Cobertura de casos de borda** | **Alta** |
| **Testes de integração** | **11** (batch) |
| **Total de testes passando** | **88** |

---

**Próximo passo sugerido:** Aplicação incremental dos helpers nos handlers existentes ou Round 8 focando em outra área.
