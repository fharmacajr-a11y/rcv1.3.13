# REFACTOR-UI-007 – Clientes `main_screen.py` – Fase 02

**Data**: 28/11/2025  
**Branch**: `qa/fixpack-04`  
**Contexto**: Segunda fase de extração de lógica pura do módulo clientes  

---

## 📋 Objetivo

Extrair lógica de **seleção (selection)** do `main_screen.py` para helpers testáveis, seguindo o padrão estabelecido no REFACTOR-UI-006 (pdf_preview Fase 03).

**Estratégia**: Criar API de helpers sem integração imediata (zero breaking changes).

---

## 🎯 Recorte Escolhido

**Option A: Selection Logic** (seleção de itens no Treeview)

Padrão encontrado no `main_screen.py`:
```python
# Linhas 575, 726, 1002, 1136
has_sel = bool(self.tree.selection())
selection = self.client_list.selection()
```

**Motivo da escolha**:
- Lógica simples, testável sem Tkinter
- Uso frequente (4+ ocorrências)
- Base para futuras refatorações (like pdf_preview Fase 03 pattern)

---

## ✅ Fase 01 (Existente)

**Arquivo**: `src/modules/clientes/views/main_screen_helpers.py`  
**Funções** (5):
- `calculate_button_states` – Estados de botões (editar/subpastas/enviar/novo/lixeira/select)
- `parse_created_at_date` – Parser de datas ISO
- `extract_created_at_from_client` – Extração de campo `created_at`
- `calculate_new_clients_stats` – Contadores (hoje/mês)
- `format_clients_summary` – String de resumo

**Testes**: `tests/unit/modules/clientes/views/test_main_screen_helpers_fase01.py` (35 tests)

---

## 🆕 Fase 02 (Nova)

### Funções Adicionadas (8)

#### 1. `has_selection(selection_tuple: Sequence[str]) -> bool`
Verifica se há seleção.

**Uso futuro**: `bool(self.tree.selection())` → `has_selection(self.tree.selection())`

#### 2. `get_selection_count(selection_tuple: Sequence[str]) -> int`
Retorna quantidade de itens selecionados.

#### 3. `is_single_selection(selection_tuple: Sequence[str]) -> bool`
Verifica se exatamente 1 item selecionado.

#### 4. `is_multiple_selection(selection_tuple: Sequence[str]) -> bool`
Verifica se 2+ itens selecionados.

#### 5. `get_first_selected_id(selection_tuple: Sequence[str]) -> str | None`
Retorna ID do primeiro item ou `None`.

#### 6. `can_edit_selection(selection_tuple, *, is_online=True) -> bool`
Valida se pode editar: `single_selection AND online`.

#### 7. `can_delete_selection(selection_tuple, *, is_online=True) -> bool`
Valida se pode deletar: `has_selection AND online`.

#### 8. `can_open_folder_for_selection(selection_tuple: Sequence[str]) -> bool`
Valida se pode abrir pasta: `single_selection`.

---

### Testes Criados

**Arquivo**: `tests/unit/modules/clientes/views/test_main_screen_helpers_fase02.py`  
**Total**: **53 testes**

#### Breakdown:
- `TestHasSelection` (4 tests) – empty/single/multiple/lista
- `TestGetSelectionCount` (4 tests) – 0/1/3/100 items
- `TestIsSingleSelection` (4 tests) – exactly 1 vs others
- `TestIsMultipleSelection` (5 tests) – 2+/single/empty/large
- `TestGetFirstSelectedId` (5 tests) – single/multiple/empty/numeric/special chars
- `TestCanEditSelection` (6 tests) – online/offline × single/multiple/empty
- `TestCanDeleteSelection` (6 tests) – online/offline × single/multiple/empty
- `TestCanOpenFolderForSelection` (4 tests) – single/multiple/empty/3+
- `TestSelectionWorkflows` (9 tests) – edit/delete/folder workflows, offline, transitions
- `TestSelectionEdgeCases` (6 tests) – empty tuple, single item, long IDs, unicode, online flags

---

## 📊 Resultados

### Pytest

```bash
# Fase 02 focado
$ python -m pytest tests/unit/modules/clientes/views/test_main_screen_helpers_fase02.py -vv --maxfail=1
========== 53 passed in 6.95s ==========
```

```bash
# Regressão módulo clientes
$ python -m pytest tests/unit/modules/clientes -vv --maxfail=1
========== 270 passed in 38.28s ==========
```

**Totais clientes**:
- Fase 01 helpers: 35 tests
- **Fase 02 helpers: 53 tests**
- Outros módulos: 182 tests
- **Total**: 270 tests

### Pyright

```bash
$ python -m pyright src/modules/clientes/views/main_screen_helpers.py \
                     tests/unit/modules/clientes/views/test_main_screen_helpers_fase02.py
0 errors, 0 warnings, 0 informations
```

✅ **Type safety OK**

### Ruff

```bash
$ python -m ruff check src/modules/clientes/views/main_screen_helpers.py \
                        tests/unit/modules/clientes/views/test_main_screen_helpers_fase02.py
All checks passed!
```

✅ **Linting OK**

### Bandit

```bash
$ python -m bandit -c .bandit -r src/modules/clientes/views/main_screen_helpers.py
Test results:
    No issues identified.

Code scanned:
    Total lines of code: 266
    Total lines skipped (#nosec): 0
```

✅ **Security scan OK**

---

## 🔄 Integração

**Status**: **NÃO integrado nesta fase** (API-only approach)

**Padrão seguido**: pdf_preview Fase 03 (create tested infrastructure without breaking changes)

### Uso Futuro (exemplo):

**Antes** (main_screen.py linha 575):
```python
has_sel = bool(self.tree.selection())
```

**Depois** (refatoração futura):
```python
from .main_screen_helpers import has_selection
...
has_sel = has_selection(self.tree.selection())
```

**Benefícios**:
- ✅ Zero mudanças de comportamento (risk-free)
- ✅ Helpers prontos para uso (tested API)
- ✅ Refatoração gradual possível

---

## 📈 Cobertura Acumulada

### Módulo clientes

| Componente | Fase | Testes | Status |
|------------|------|--------|--------|
| main_screen_helpers | Fase 01 | 35 | ✅ |
| **main_screen_helpers** | **Fase 02** | **53** | ✅ |
| clientes_forms (prepare/upload/finalize) | - | 40 | ✅ |
| clientes_service | - | 138 | ✅ |
| clientes_integration | - | 2 | ✅ |
| clientes_status_helpers | - | 2 | ✅ |
| **TOTAL** | - | **270** | ✅ |

### Projeto completo (referência)

| Módulo | Total Tests | Status |
|--------|-------------|--------|
| pdf_preview | 164 | ✅ |
| **clientes** | **270** | ✅ |
| lixeira | 93 | ✅ |
| hub | 42 | ✅ |
| ... | ... | ... |

---

## 🏗️ Arquitetura

```
src/modules/clientes/views/
├── main_screen.py (1600+ linhas, sem mudanças nesta fase)
└── main_screen_helpers.py (266 linhas)
    ├── [Fase 01] Button states, stats, formatting (5 funcs)
    └── [Fase 02] Selection logic (8 funcs) ← NOVA

tests/unit/modules/clientes/views/
├── test_main_screen_helpers_fase01.py (35 tests)
└── test_main_screen_helpers_fase02.py (53 tests) ← NOVA
```

---

## 📝 Lessons Learned

### ✅ Padrões Consolidados

1. **API-first approach**: Criar helpers testados sem integração imediata (pdf_preview Fase 03 pattern)
2. **Pure functions**: `Sequence[str]` input → primitives output (bool/int/str/None)
3. **Comprehensive testing**: 53 tests para 8 funções (~6.6 tests/func)
4. **Edge cases coverage**: empty, single, multiple, large, unicode, special chars

### 🎯 Decisões de Design

- **Não usar `tuple` direto**: `Sequence[str]` aceita tuplas E listas (flexibilidade)
- **Keyword-only `is_online`**: `can_edit_selection(sel, is_online=True)` (explícito)
- **Return `None` vs `""` **: `get_first_selected_id` retorna `None` quando vazio (idiomatic Python)

### 🔄 Workflow Otimizado

1. Mapear existente (Fase 01)
2. Escolher recorte específico (Selection logic)
3. Adicionar helpers puros
4. Criar testes abrangentes (unit + workflows + edge cases)
5. Validar QA stack (pytest/pyright/ruff/bandit)
6. Documentar

**Tempo total**: ~1.5h (design + implementação + testes + validação + docs)

---

## 🚀 Próximos Passos

### Fase 03 (Futuro)

**Opções de recorte**:
- **Option B**: Filtros (apply_filters, _get_selected_values, _populate_status_filter_options)
- **Option C**: Ações em massa (batch operations)
- **Option D**: Estado de UI (loading, busy states)

**OU**

### Integração Gradual

Aplicar helpers de Fase 01 + Fase 02 no `main_screen.py`:
- Substituir `bool(self.tree.selection())` por `has_selection(...)`
- Usar `can_edit_selection()` / `can_delete_selection()` nas validações
- Aplicar testes de integração

---

## 📌 Checklist Final

- [x] Mapear Fase 01 existente
- [x] Escolher recorte (Selection logic)
- [x] Adicionar 8 funções de seleção
- [x] Criar 53 testes (test_main_screen_helpers_fase02.py)
- [x] Pytest focado (53 passed)
- [x] Regressão clientes (270 passed)
- [x] Pyright (0 errors)
- [x] Ruff (all checks passed)
- [x] Bandit (0 issues)
- [x] Documentação (este arquivo)

---

## 🎉 Conclusão

**REFACTOR-UI-007 Fase 02 concluída com sucesso!**

- ✅ **8 novos helpers** de seleção
- ✅ **53 novos testes** (100% passing)
- ✅ **270 testes totais** no módulo clientes
- ✅ **Zero breaking changes** (API-only approach)
- ✅ **QA completa** (Pyright, Ruff, Bandit)

**Padrão consolidado**: Helpers puros + testes abrangentes + validação rigorosa = código confiável e manutenível.

---

**Autor**: GitHub Copilot (Claude Sonnet 4.5)  
**Revisão**: QA Automation  
**Versão RC Gestor**: v1.2.97
