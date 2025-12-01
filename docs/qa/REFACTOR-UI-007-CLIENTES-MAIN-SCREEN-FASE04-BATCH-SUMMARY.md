# Refactor UI-007: Clientes Main Screen - Fase 04 - Batch Operations

**Branch**: `qa/fixpack-04`  
**Data**: 28/11/2025  
**Fase**: 04 - Batch Operations (Multi-Selection)

---

## Visão Geral da Fase 04

Esta fase implementou **Option C: Ações em massa (Batch Operations)**, extraindo a lógica de validação para operações em massa (multi-seleção) em helpers puros, mantendo o padrão estabelecido nas Fases 01-03.

### Objetivos Alcançados

✅ Extração de lógica de batch operations para helpers puros  
✅ Criação de testes unitários abrangentes (46 testes novos)  
✅ Validação completa com Pyright, Ruff e Bandit  
✅ Regressão do módulo clientes (369 testes passando)  
✅ Zero modificações em `main_screen.py` (API-only approach mantido)

---

## Helpers de Batch Operations Extraídos

### 1. `can_batch_delete`

```python
def can_batch_delete(
    selected_ids: Collection[str],
    *,
    is_trash_screen: bool,
    is_online: bool = True,
    max_items: int | None = None,
) -> bool
```

**Responsabilidade**: Determina se a ação 'excluir em massa' deve ser habilitada.

**Regras implementadas**:
- Requer ao menos 1 item selecionado
- Requer conexão online
- Respeita limite máximo de itens (se configurado)
- Funciona tanto na lista principal quanto na lixeira

**Casos de uso**:
- Seleção vazia → `False`
- 1+ itens, online, dentro do limite → `True`
- Offline → `False`
- Acima de `max_items` → `False`

### 2. `can_batch_restore`

```python
def can_batch_restore(
    selected_ids: Collection[str],
    *,
    is_trash_screen: bool,
    is_online: bool = True,
) -> bool
```

**Responsabilidade**: Determina se a ação 'restaurar em massa' deve ser habilitada.

**Regras implementadas**:
- Requer ao menos 1 item selecionado
- Requer conexão online
- **Só disponível na tela de lixeira**

**Casos de uso**:
- Na lixeira, online, 1+ itens → `True`
- Fora da lixeira → `False` (independente de outros fatores)
- Offline → `False`

### 3. `can_batch_export`

```python
def can_batch_export(
    selected_ids: Collection[str],
    *,
    max_items: int | None = None,
) -> bool
```

**Responsabilidade**: Determina se a ação 'exportar em massa' deve ser habilitada.

**Regras implementadas**:
- Requer ao menos 1 item selecionado
- Respeita limite máximo de itens (se configurado)
- **Não depende de conexão online** (exportação local)

**Casos de uso**:
- 1+ itens, dentro do limite → `True`
- Seleção vazia → `False`
- Acima de `max_items` → `False`
- Funciona offline (diferencial vs outras operações)

---

## Características dos Helpers

### Funções Puras

Todos os helpers são **completamente puros**:

```python
# ✅ Aceita apenas dados primitivos
selected_ids: Collection[str]  # Set, List, Tuple, Frozenset

# ✅ Flags simples
is_trash_screen: bool
is_online: bool

# ✅ Limites opcionais
max_items: int | None

# ❌ NÃO acessa:
# - Widgets Tkinter
# - self.tree.selection()
# - ViewModel
# - Estado global
```

### Flexibilidade de Tipos

Todos aceitam `Collection[str]`, permitindo:
- `set()`, `frozenset()` (sem duplicatas)
- `list()`, `tuple()` (com possíveis duplicatas)
- Qualquer coleção iterável de strings

### Consistência com Fases Anteriores

Reutilizam conceitos da **Fase 02 (Selection)**:
- Mesmo padrão de validação (`has_selection`, `is_online`)
- Nomenclatura consistente (`can_*`)
- Estrutura similar de parâmetros

---

## Testes Unitários

**Arquivo**: `tests/unit/modules/clientes/views/test_main_screen_helpers_fase04.py`

### Estatísticas

- **Total de testes**: 46 (100% passando)
- **Classes de teste**: 4
  - `TestCanBatchDelete`: 16 testes
  - `TestCanBatchRestore`: 9 testes
  - `TestCanBatchExport`: 15 testes
  - `TestBatchOperationsIntegration`: 6 testes

### Cobertura de Cenários

#### `can_batch_delete` (16 testes)

✅ Seleção vazia  
✅ Seleção única (online/offline)  
✅ Multi-seleção (online/offline)  
✅ Tela principal vs lixeira  
✅ Limites (`max_items=None/0/N`)  
✅ Tipos de coleção (list/tuple/set/frozenset)  
✅ IDs duplicados

#### `can_batch_restore` (9 testes)

✅ Seleção vazia  
✅ Lixeira vs tela principal  
✅ Online vs offline  
✅ Seleção única vs múltipla  
✅ Tipos de coleção (list/tuple/set/frozenset)

#### `can_batch_export` (15 testes)

✅ Seleção vazia  
✅ Seleção única vs múltipla  
✅ Limites (`max_items=None/0/N`)  
✅ Tipos de coleção (list/tuple/set/frozenset)  
✅ IDs duplicados  
✅ Seleções grandes (1000+ itens)

#### Integração (6 testes)

✅ Todas operações desabilitadas com seleção vazia  
✅ Combinações de disponibilidade (tela principal online)  
✅ Todas operações na lixeira (online)  
✅ Apenas export disponível offline  
✅ Efeito de `max_items` em cada operação  
✅ Consistência single vs batch

---

## Resultados de Validação

### Pytest

```bash
pytest tests/unit/modules/clientes/views/test_main_screen_helpers_fase04.py -vv --maxfail=1
```

**Resultado**: ✅ **46/46 testes passando** (7.49s)

### Regressão Módulo Clientes

```bash
pytest tests/unit/modules/clientes -vv --maxfail=1
```

**Resultado**: ✅ **369/369 testes passando** (49.49s)

Distribuição:
- Fase 01 (Buttons/Stats): 35 testes
- Fase 02 (Selection): 53 testes
- Fase 03 (Filters): 53 testes
- **Fase 04 (Batch Ops): 46 testes**
- Service/Forms/Outros: 182 testes

### Pyright (Tipagem)

```bash
pyright src/modules/clientes/views/main_screen_helpers.py \
  tests/unit/modules/clientes/views/test_main_screen_helpers_fase*.py
```

**Resultado**: ✅ **0 erros, 0 warnings, 0 informações**

Todas as type hints validadas:
- `Collection[str]` corretamente aplicado
- `int | None` para parâmetros opcionais
- `bool` para retornos e flags

### Ruff (Estilo)

```bash
ruff check src/modules/clientes/views/main_screen_helpers.py \
  tests/unit/modules/clientes/views/test_main_screen_helpers_fase*.py
```

**Resultado**: ✅ **All checks passed!**

Correções aplicadas:
- Import `Collection` movido para topo do arquivo
- Import `pytest` não utilizado removido

### Bandit (Segurança)

```bash
bandit -r src/modules/clientes/views/main_screen_helpers.py -x tests \
  -f json -o reports/bandit-refactor-ui-007-clientes-main-screen-fase04-batch.json
```

**Resultado**: ✅ **0 issues encontrados**

```json
{
  "metrics": {
    "_totals": {
      "SEVERITY.HIGH": 0,
      "SEVERITY.MEDIUM": 0,
      "SEVERITY.LOW": 0,
      "loc": 553
    }
  },
  "results": []
}
```

---

## Métricas Acumuladas (Fases 01-04)

### Arquivo `main_screen_helpers.py`

| Métrica | Valor |
|---------|-------|
| **Total de helpers** | 22 funções |
| Fase 01 (Buttons/Stats) | 5 helpers |
| Fase 02 (Selection) | 8 helpers |
| Fase 03 (Filters) | 6 helpers |
| **Fase 04 (Batch Ops)** | **3 helpers** |
| Linhas de código | 553 LOC |
| Complexidade | Baixa (funções puras) |

### Testes Unitários de Helpers

| Métrica | Valor |
|---------|-------|
| **Total de testes** | 187 testes |
| `test_main_screen_helpers_fase01.py` | 35 testes |
| `test_main_screen_helpers_fase02.py` | 53 testes |
| `test_main_screen_helpers_fase03.py` | 53 testes |
| **`test_main_screen_helpers_fase04.py`** | **46 testes** |
| Taxa de aprovação | 100% |

### Módulo Clientes Completo

| Métrica | Valor |
|---------|-------|
| **Total de testes** | 369 testes |
| Helpers (Fases 01-04) | 187 testes |
| Service | ~140 testes |
| Forms (Prepare/Upload/Finalize) | ~40 testes |
| Integração | 2 testes |
| Taxa de aprovação | 100% |
| Tempo de execução | 49.49s |

---

## Impacto em Testabilidade

### Antes da Fase 04

Lógica de batch operations:
- ❌ Acoplada a `main_screen.py`
- ❌ Dependente de Tkinter (`.selection()`)
- ❌ Difícil de testar isoladamente
- ❌ Validações dispersas em callbacks

### Depois da Fase 04

✅ Lógica extraída em helpers puros  
✅ Zero dependência de Tkinter  
✅ Testável com dados primitivos  
✅ 46 testes cobrindo edge cases  
✅ Reutilizável em outros contextos  
✅ Mantém consistência com Fases 01-03

---

## Arquitetura e Padrões

### Separação de Responsabilidades

```
┌─────────────────────────────────────┐
│ main_screen.py (View/UI)            │
│ - Gerencia widgets Tkinter          │
│ - Lê self.tree.selection()          │
│ - Chama helpers puros               │
│ - Atualiza estado de botões         │
└────────────┬────────────────────────┘
             │ chama
             ▼
┌─────────────────────────────────────┐
│ main_screen_helpers.py (Logic)      │
│ ✓ can_batch_delete(ids, ...)        │
│ ✓ can_batch_restore(ids, ...)       │
│ ✓ can_batch_export(ids, ...)        │
│ - Funções puras                     │
│ - Apenas lógica de negócio          │
└─────────────────────────────────────┘
```

### API Consistency

Todos os helpers de batch seguem mesmo padrão:

```python
def can_batch_<operation>(
    selected_ids: Collection[str],  # Sempre primeiro
    *,                               # Keyword-only args
    is_trash_screen: bool,          # Contexto de tela (quando relevante)
    is_online: bool = True,         # Estado de conexão (quando relevante)
    max_items: int | None = None,  # Limites opcionais
) -> bool:                          # Sempre retorna bool
```

---

## Estado do Código-Fonte

### Arquivos Modificados

1. **`src/modules/clientes/views/main_screen_helpers.py`**
   - ➕ Seção "Fase 04: Batch Operations"
   - ➕ Import `Collection` no topo
   - ➕ 3 helpers novos
   - ➕ ~150 linhas (incluindo docstrings)
   - Status: ✅ Pyright/Ruff/Bandit limpos

2. **`tests/unit/modules/clientes/views/test_main_screen_helpers_fase04.py`**
   - ➕ Arquivo novo
   - ➕ 4 classes de teste
   - ➕ 46 testes unitários
   - Status: ✅ 100% passando

### Arquivos NÃO Modificados

❌ `src/modules/clientes/views/main_screen.py`  
❌ `src/modules/clientes/viewmodel.py`  
❌ Qualquer outro módulo do app

**Rationale**: Mantendo **API-only approach**. A integração dos helpers na UI será feita em fase posterior de refactor da `main_screen.py`.

---

## Próximos Passos (Planejamento)

### Fase 05 (Sugestão): Integration Layer

Quando integrar os helpers na `main_screen.py`:

1. Adicionar método `_get_selected_ids()` que retorna `set[str]`
2. Criar método `_update_batch_buttons_state()` que:
   ```python
   selected_ids = self._get_selected_ids()
   is_trash = self._is_trash_screen()
   is_online = self._get_online_state()

   # Batch delete button
   can_delete = can_batch_delete(
       selected_ids,
       is_trash_screen=is_trash,
       is_online=is_online,
       max_items=100,  # Configurável
   )
   self.btn_batch_delete.configure(state="normal" if can_delete else "disabled")

   # ... similar para restore e export
   ```
3. Conectar ao evento `<<TreeviewSelect>>`
4. Adicionar testes de integração UI

### Fase 06 (Sugestão): Batch Actions Implementation

Implementar os handlers reais:

1. `_on_batch_delete_clicked()`
2. `_on_batch_restore_clicked()`
3. `_on_batch_export_clicked()`

Com:
- Confirmação ("Tem certeza de excluir X itens?")
- Progress dialog para operações longas
- Tratamento de erros parciais
- Auditoria de ações em massa

---

## Observações Técnicas

### Design Decisions

1. **`Collection[str]` vs `Sequence[str]`**
   - Escolhido `Collection` para aceitar `set`/`frozenset` (mais comum em seleções)
   - Ainda aceita `list`/`tuple` (covariance)

2. **`max_items` opcional**
   - `None` = sem limite (comportamento padrão)
   - Permite configuração futura sem quebrar API

3. **`is_trash_screen` explícito**
   - Melhor que inferir do contexto
   - Torna testes mais claros
   - Previne bugs de estado

4. **Export não requer `is_online`**
   - Operação local (exportar para arquivo)
   - Diferencial importante vs delete/restore

### Edge Cases Cobertos

✅ IDs duplicados em listas  
✅ Seleções muito grandes (1000+ itens)  
✅ Strings vazias como IDs  
✅ Unicode em IDs  
✅ Coleções imutáveis (frozenset)  
✅ `max_items=0` (edge case)

### Bugs Potenciais Prevenidos

🐛 Permitir restore fora da lixeira  
🐛 Permitir operações offline sem validação  
🐛 Ultrapassar limites de batch sem warning  
🐛 Confusão entre seleção única e múltipla

---

## Conclusão da Fase 04

### Status: ✅ COMPLETO

A Fase 04 implementou com sucesso a extração de helpers de batch operations, mantendo 100% de consistência com as fases anteriores:

- ✅ **3 helpers puros** criados
- ✅ **46 testes unitários** (100% passando)
- ✅ **369 testes de regressão** (módulo clientes completo)
- ✅ **Pyright/Ruff/Bandit** limpos
- ✅ **Zero alterações** em `main_screen.py`
- ✅ **Comportamento** da tela inalterado

### Qualidade Mantida

| Aspecto | Status |
|---------|--------|
| Testes | ✅ 100% passando |
| Tipagem | ✅ 0 erros Pyright |
| Estilo | ✅ Ruff clean |
| Segurança | ✅ 0 issues Bandit |
| Cobertura | ✅ 46 testes, edge cases incluídos |
| Documentação | ✅ Docstrings completas + summary |

### Próximo Milestone

Com as **4 fases de helpers** concluídas (Buttons/Stats, Selection, Filters, Batch), o módulo clientes agora possui uma camada de lógica completamente testável e isolada, pronta para:

1. Integração gradual na `main_screen.py`
2. Remoção de código acoplado
3. Melhoria de manutenibilidade
4. Expansão para outras telas (lixeira, subpastas, etc.)

---

**Documento gerado**: 28/11/2025  
**Branch**: `qa/fixpack-04`  
**Responsável**: GitHub Copilot  
**Revisão**: Pendente
