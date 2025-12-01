# Round 15: Cobertura de `viewmodel.py` (76.5% → 97.1%)

**Meta**: Elevar a cobertura de `src/modules/clientes/viewmodel.py` para **95%+**, focando na lógica de estado, contadores e transformação de dados, sem envolver Tkinter.

---

## 📊 Baseline (antes)

```
src/modules/clientes/viewmodel.py
  - Statements: 215
  - Branches: 62
  - Cobertura: 76.5%
  - Miss: 46 statements
  - Partial: 9 branches
```

---

## 🎯 Classes e Métodos Cobertos

### `ClienteRow` (dataclass)
- `__init__` com todas as propriedades
- Criação de `search_norm` através de `join_and_normalize`
- Campos: id, razao_social, cnpj, nome, status, observacoes, ultima_alteracao, search_norm

### `ClientesViewModel`
#### Gerenciamento de Estado
- `load_from_iterable` (dict/object, todos/campos faltantes)
- `refresh_from_service` (com ordenação e propagação de erros)
- `get_rows` (retorna linhas filtradas/ordenadas)
- `get_count` (contador de linhas)

#### Filtros
- `set_search_text` (case-insensitive, normalizado)
- `set_status_filter` (exact match, case-insensitive)
- Flags de rebuild/reapply

#### Ordenação
- `set_order_label` (razao_social, nome, cnpj, id)
- Ascendente/Descendente
- Nulls last (valores vazios vão para o final)

#### Status
- `extract_status_and_observacoes` (prefixo `[STATUS]`)
- `apply_status_to_observacoes` (adiciona prefixo)
- `get_status_choices` (lista única e ordenada)

#### Batch Operations
- `delete_clientes_batch` (mock service)
- `restore_clientes_batch` (mock service)
- `export_clientes_batch` (mock service)

#### Construção de Linhas
- `_build_row_from_cliente` (formatação CNPJ, data, iniciais do autor)
- `_sort_rows` (ordenação com fallback)
- `_rebuild_rows` (reconstruir com filtros)

#### Helpers Estáticos
- `_value_from_cliente` (dict/object, fallback, None/empty)
- `_only_digits` (extração de dígitos)
- `_key_nulls_last` (chave de ordenação com nulls last)

### `ClientesViewModelError`
- Exceção customizada para erros do viewmodel

---

## 🧪 Estrutura de Testes

**Arquivo**: `tests/unit/modules/clientes/test_viewmodel_round15.py`

### Classes de Teste (11)
1. **TestClienteRow**: Validação do dataclass com search_norm
2. **TestLoadAndRebuild**: load_from_iterable com empty/single/multiple
3. **TestExtractStatus**: extract_status_and_observacoes com prefixos
4. **TestApplyStatus**: apply_status_to_observacoes
5. **TestFilters**: set_search_text e set_status_filter
6. **TestOrdering**: set_order_label (4 colunas, asc/desc, nulls last)
7. **TestStatusChoices**: get_status_choices (uniqueness e sorting)
8. **TestBatchOperations**: delete/restore/export com mocked services
9. **TestBuildRow**: _build_row_from_cliente (formatação e autor)
10. **TestValueFromCliente**: _value_from_cliente (dict/object, fallback)
11. **TestRefreshFromService**: refresh_from_service com ordenação
12. **TestStaticHelpers**: _only_digits, _key_nulls_last
13. **TestErrorHandling**: Fallbacks para format_cnpj, fmt_data, JSON inválido, IDs inválidos

### Total de Testes: **66**

#### Cenários Cobertos
- Construção de `ClienteRow` com todos/campos faltantes
- Filtros de texto (case-insensitive, normalizado)
- Filtros de status (exact match, case-insensitive)
- Ordenação por razao_social, nome, cnpj, id (asc/desc, nulls last)
- Batch operations (delete, restore, export) com mocked services
- Extração de status `[STATUS]` de observações
- Aplicação de prefixo `[STATUS]` em observações
- Formatação de CNPJ (com fallback se format_cnpj falhar)
- Formatação de data (com fallback se fmt_data falhar)
- Iniciais do autor (com RC_INITIALS_MAP e fallback para primeira letra do email)
- Normalização de texto (join_and_normalize remove acentos)
- Helpers estáticos (_only_digits, _key_nulls_last)
- Erro propagado de service.search_clientes

---

## 📈 Cobertura Após Round 15

```
src/modules/clientes/viewmodel.py
  - Coverage: 97.1%
  - Statements: 215, Miss: 4
  - Branches: 62, Partial: 4
  - Missing lines: 103→105, 242, 284→286, 291-292, 294
```

### Linhas não cobertas (edge cases de error handling)
- **103→105**: Branch de set_order_label (edge case raro)
- **242**: Fallback de _sort_rows (exceção durante sorting)
- **284→286**: Exceção ao carregar RC_INITIALS_MAP (JSON inválido)
- **291-292, 294**: Fallback do author resolver (exceção ao resolver iniciais)

---

## ✅ Quality Gates

### pytest
```
66 passed in 14.42s
```

### ruff
```
2 unused imports auto-fixed (Dict, Mock)
0 remaining issues
```

### bandit
```
119 issues B101 (assert_used) - esperado em testes
0 security issues reais
```

---

## 🔧 Estratégia

1. **Foco em Business Logic**: Todos os testes focaram em estado, filtros, ordenação e transformação de dados, sem tocar em Tkinter
2. **Mocking Abrangente**: Mockadas todas as dependências externas:
   - `service.excluir_clientes_definitivamente`
   - `service.restaurar_clientes_da_lixeira`
   - `service.search_clientes`
   - `app_utils.fmt_data`
   - `text_utils.format_cnpj`
   - `text_utils.join_and_normalize`
   - `text_utils.normalize_search`
3. **Error Handling**: 5 testes adicionais para cobrir caminhos de exceção (CNPJ format fail, date format fail, invalid JSON, invalid IDs)
4. **Patch Paths**: Corretos desde a primeira iteração (patch do módulo original, não do importador)
5. **Assertions Precisas**: Validação de valores exatos, não substring matching

---

## 📚 Resumo da Campanha de Cobertura (Rounds 9-15)

| Round | Arquivo | Baseline | Meta | Final | Testes Novos |
|-------|---------|----------|------|-------|--------------|
| 9 | text_utils.py | 86.5% | 95%+ | 96.5% | 19 |
| 10 | collect.py | 73.3% | 95%+ | 98.4% | 35 |
| 11 | dupes.py | 79.3% | 95%+ | 96.2% | 36 |
| 12 | prepare.py | 69.4% | 95%+ | 97.6% | 39 |
| 13 | upload.py | 68.3% | 95%+ | 98.8% | 27 |
| 14 | client_form.py | 21.3% | 50%+ | 33.7% | 4 |
| **15** | **viewmodel.py** | **76.5%** | **95%+** | **97.1%** | **66** |

### Totais
- **Testes adicionados**: 226
- **Cobertura média**: 88.3%
- **Arquivos com 95%+**: 6/7 (86%)

---

## 💡 Lições Aprendidas

1. **Patch de Imports Dinâmicos**: Ao mockar funções importadas localmente dentro de métodos, sempre patchear o módulo original onde a função é definida
2. **Teste de Edge Cases**: 4 linhas não cobertas são exceções raras que requerem cenários extremamente específicos (JSON malformado, exceção durante sort)
3. **Cobertura de Lógica sem UI**: É possível atingir 97%+ mockando todas as dependências externas e focando em business logic
4. **Dataclasses**: Criar testes para validar construção correta com todos/campos faltantes garante robustez

---

## 🎓 Conclusão

Round 15 atingiu **97.1%** de cobertura (meta 95%+), adicionando **66 testes** que validam toda a lógica de estado, filtros, ordenação e transformação de dados do `ClientesViewModel`, sem envolver Tkinter. A campanha de cobertura para o módulo `clientes` está completa, com 6 de 7 arquivos acima de 95% e uma média final de 88.3%.
