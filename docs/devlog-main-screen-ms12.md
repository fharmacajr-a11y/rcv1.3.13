# DevLog - Main Screen MS-12: State Builder

**Projeto:** RC Gestor de Clientes v1.3.38  
**Branch:** `qa/fixpack-04`  
**Python:** 3.13  
**Autor:** Codex (GPT-5)  
**Data:** 2025-01-XX

---

## Objetivo

Centralizar a construção de `MainScreenState` em um builder reutilizável para reduzir duplicação entre UI/controller, melhorar legibilidade e permitir testes isolados.

---

## Arquivos Alterados/Novos

1. `src/modules/clientes/views/main_screen_state_builder.py` *(novo)*
2. `src/modules/clientes/views/main_screen.py`
3. `tests/unit/modules/clientes/views/test_main_screen_state_builder_ms12.py` *(novo)*

---

## Extração da Lógica de Builder

| Antes | Depois |
| --- | --- |
| `MainScreenFrame` montava `MainScreenState` manualmente em dois pontos ( `_build_main_screen_state` e `_update_batch_buttons_on_selection_change` ), repetindo normalizações de labels, `.strip()` em filtros/busca, conversão da seleção para `list` e leitura do Supabase. | Nova função `build_main_screen_state` concentra essa lógica, recebe valores "crus" da UI, aplica `normalize_order_label`, higieniza filtro/busca, converte `selected_ids` para `list` e resolve `is_online` com fallback seguro se `get_supabase_state` falhar. A UI apenas fornece parâmetros crus. |

### Implementação

- Adicionada `build_main_screen_state(...)` em `main_screen_state_builder.py` (Sequence/Collection + try/except no Supabase).
- `_build_main_screen_state` invoca o builder com a lista produzida em `_get_clients_for_controller`.
- `_update_batch_buttons_on_selection_change` passa o cache `_current_rows` e reaproveita o builder.
- Novo teste garante normalização/seleção, e outro valida fallback `is_online=False` quando o Supabase levanta exceção.

---

## Testes e Qualidade

| Tipo | Comando | Resultado |
| --- | --- | --- |
| Pytest | `pytest tests/unit/modules/clientes/views/test_main_screen_state_builder_ms12.py tests/unit/modules/clientes/views/test_main_screen_contract_ms11.py tests/unit/modules/clientes/views/test_main_screen_controller_ms1.py tests/unit/modules/clientes/views/test_main_screen_controller_filters_ms4.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase01.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase02.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase03.py tests/unit/modules/clientes/views/test_main_screen_helpers_fase04.py -v` | OK `237 passed, 1 skipped` (30.32s) |
| Ruff | `ruff check src/modules/clientes/views/main_screen_state.py src/modules/clientes/views/main_screen_controller.py src/modules/clientes/views/main_screen_helpers.py src/modules/clientes/views/main_screen.py src/modules/clientes/views/main_screen_state_builder.py tests/unit/modules/clientes/views/test_main_screen_state_builder_ms12.py` | OK Sem findings |
| Pyright | `pyright src/modules/clientes/views/main_screen_state.py src/modules/clientes/views/main_screen_controller.py src/modules/clientes/views/main_screen_helpers.py src/modules/clientes/views/main_screen.py src/modules/clientes/views/main_screen_state_builder.py` | WARN Apenas ruídos conhecidos do Tkinter (imports/membros desconhecidos). Builder e demais módulos relevantes permanecem sem erros novos (`pyright ...main_screen_state_builder.py` -> `0 errors`). |

---

## Conclusão

- Toda construção de `MainScreenState` agora passa por `build_main_screen_state`, garantindo consistência nos trims, normalização e status online/offline.
- A UI continua em modo `strict`, sem alterações na interface pública do controller.
- Novo teste isolado protege o builder contra regressões.
- CF2 da Main Screen segue pronta "pra vida real": mesmas 234 suítes passando e tooling limpo (exceto ruídos Tkinter já catalogados).
