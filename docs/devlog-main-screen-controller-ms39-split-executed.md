# MS-39 – Split executado do `main_screen.py`

## Resumo Executivo
Execução do split do `main_screen.py` em múltiplos módulos especializados (frame/events/dataflow/batch), mantendo `MainScreenFrame` como ponto de entrada único via façade pattern.

## Arquitetura do Split

### Estratégia Utilizada: Mixins (Opção A)
O split foi implementado usando **mixins** para organizar o código em responsabilidades claras, mantendo a API pública intacta.

### Estrutura Resultante

```
src/modules/clientes/views/
├── main_screen.py              (façade - 27 linhas)
├── main_screen_frame.py        (classe principal - 358 linhas)
├── main_screen_events.py       (mixin de eventos - 192 linhas)
├── main_screen_dataflow.py     (mixin de dataflow - 390 linhas)
└── main_screen_batch.py        (mixin de batch ops - 166 linhas)
```

## Tamanhos dos Arquivos (antes/depois)

### Antes do Split (MS-38)
- **main_screen.py**: ~1055 linhas (monolito)

### Depois do Split (MS-39)
- **main_screen.py**: 27 linhas (façade pura)
- **main_screen_frame.py**: 358 linhas (frame principal + ciclo de vida + wiring)
- **main_screen_events.py**: 192 linhas (handlers de eventos)
- **main_screen_dataflow.py**: 390 linhas (carregamento, filtros, renderização)
- **main_screen_batch.py**: 166 linhas (operações em lote)

**Total**: 1133 linhas distribuídas (vs. 1055 no monolito - pequeno aumento devido a imports adicionais)

## Distribuição de Responsabilidades

### main_screen.py (façade)
Responsabilidade: **Ponto de entrada público**
- Reexporta `MainScreenFrame` de `main_screen_frame.py`
- Reexporta constantes de helpers
- Define constantes de pick mode (`PICK_MODE_BANNER_TEXT`, etc.)
- Mantém `__all__` para compatibilidade

### main_screen_frame.py
Responsabilidade: **Classe principal, ciclo de vida, wiring, integração**
Métodos migrados:
- `__init__`: Construtor completo com wiring de managers/controllers
- `destroy`: Cleanup do frame
- `set_uploading`: Estado de upload
- `_enter_pick_mode_ui` / `_leave_pick_mode_ui`: Gerenciamento de UI do pick mode
- `enter_pick_mode` / `exit_pick_mode` / `is_pick_mode_active`: API pública de pick mode
- `_start_connectivity_monitor`: Início do monitor de conectividade
- `_get_selected_values`: Helper de seleção
- `_resolve_author_initial`: Resolução de iniciais de autores
- `on_delete_selected_clients`: Callback de exclusão
- `start_pick`, `_on_pick_cancel`, `_on_pick_confirm`: API de integração com Senhas
- `_invoke`, `_invoke_safe`: Invocação segura de callbacks
- `_handle_action_result`: Interpretação de ActionResult

Herança: `MainScreenEventsMixin` + `MainScreenDataflowMixin` + `MainScreenBatchMixin` + `tb.Frame`

### main_screen_events.py (MainScreenEventsMixin)
Responsabilidade: **Handlers de eventos (treeview, toolbar, status)**
Métodos migrados:
- `_rebind_double_click_handler`: Rebind de duplo clique
- `_on_double_click`: Roteamento de duplo clique (editar vs. pick)
- `_on_click`: WhatsApp (col #5) + menu de status (col #7)
- `_on_tree_delete_key`: Handler da tecla Delete
- `_on_order_changed`: Mudança de ordenação
- `_on_status_menu`: Menu contextual de status
- `_on_status_pick`: Seleção de status no menu
- `_set_status`: Aplicação de status escolhido
- `_build_selection_snapshot`: Construção de snapshot de seleção
- `_get_selected_ids`: Obtenção de IDs selecionados
- `_build_event_context`: Montagem de contexto para EventRouter
- `_ensure_status_menu`: Criação/configuração do menu de status
- `_show_status_menu`: Exibição do menu de status

### main_screen_dataflow.py (MainScreenDataflowMixin)
Responsabilidade: **Carregamento, filtros, dataflow, integração com controller**
Métodos migrados:
- `carregar`: Carregamento principal da lista
- `_sort_by`: Ordenação por coluna
- `_buscar`: Debounce de busca
- `_limpar_busca`: Limpar filtros de busca
- `apply_filters`: Aplicação de filtros via controller
- `_populate_status_filter_options`: Atualização dinâmica de filtros de status
- `_row_values_masked`: Conversão de ClienteRow para tupla de exibição
- `_refresh_rows`: Atualização de rows na treeview
- `_render_clientes`: Renderização da lista de clientes
- `_get_clients_for_controller`: Obtenção de lista completa para controller
- `_update_ui_from_computed`: Atualização de UI com dados computados
- `_update_batch_buttons_from_computed`: Atualização de botões de batch
- `_refresh_with_controller`: Função central de filtro/ordem/busca (MS-34)
- `_update_batch_buttons_on_selection_change`: Atualização de batch ao mudar seleção
- `_apply_status_for`: Mudança de status (MS-35)
- `_apply_connectivity_state`: Aplicação de estado de conectividade
- `_update_main_buttons_state`: Atualização de estados de botões (MS-32)
- `_set_count_text`: Atualização de estatísticas de clientes (MS-35)

### main_screen_batch.py (MainScreenBatchMixin)
Responsabilidade: **Operações em lote (batch delete/restore/export)**
Métodos migrados:
- `_on_batch_delete_clicked`: Handler de exclusão em lote
- `_on_batch_restore_clicked`: Handler de restauração em lote
- `_on_batch_export_clicked`: Handler de exportação em lote

## Testes Executados

### Comandos Rodados
```bash
pytest tests/unit/modules/clientes/views/test_main_screen_controller_core.py -q
pytest tests/unit/modules/clientes/views/test_main_screen_controller_filters.py -q
pytest tests/unit/modules/clientes/views/test_main_screen_batch_logic.py -q
pytest tests/unit/modules/clientes/controllers/test_main_screen_actions.py -q
pytest tests/unit/modules/clientes/ -k "main_screen" -q
```

### Resultado
✅ **Todos os testes passaram**

- `test_main_screen_controller_core.py`: 23 testes OK
- `test_main_screen_controller_filters.py`: 26 testes OK
- `test_main_screen_batch_logic.py`: 18 testes OK (após atualização de patches)
- `test_main_screen_actions.py`: 18 testes OK
- Busca geral por "main_screen": Todos OK (alguns skipped por serem opcionais)

### Ajustes nos Testes
Os testes de `test_main_screen_batch_logic.py` precisaram ser atualizados para fazer patch nos módulos corretos:
- `src.modules.clientes.views.main_screen.messagebox` → `src.modules.clientes.views.main_screen_batch.messagebox`
- `src.modules.clientes.views.main_screen.get_supabase_state` → `src.modules.clientes.views.main_screen_batch.get_supabase_state`

Isso ocorreu porque o split moveu os imports de `messagebox` e `get_supabase_state` para os mixins específicos.

## Compatibilidade e API Pública

### Importação Mantida
Todos os imports externos permanecem funcionando:
```python
from src.modules.clientes.views.main_screen import MainScreenFrame
```

A façade `main_screen.py` garante que nenhum outro arquivo do projeto precise mudar.

### Constantes Públicas Mantidas
```python
__all__ = [
    "MainScreenFrame",
    "DEFAULT_ORDER_LABEL",
    "ORDER_CHOICES",
    "PICK_MODE_BANNER_TEXT",
    "PICK_MODE_CANCEL_TEXT",
    "PICK_MODE_SELECT_TEXT",
]
```

## Benefícios do Split

1. **Organização Clara**: Cada módulo tem uma responsabilidade bem definida
2. **Facilita Manutenção**: Mudanças em eventos não afetam dataflow e vice-versa
3. **Reduz Complexidade Cognitiva**: Arquivos menores (~200-400 linhas vs. 1000+)
4. **Mantém Compatibilidade**: API pública intacta via façade pattern
5. **Testabilidade**: Testes podem focar em aspectos específicos
6. **Escalabilidade**: Facilita futuras refatorações

## Conclusão

**MS-39 concluída**: `main_screen.py` dividido em múltiplos módulos (frame/events/dataflow/batch), mantendo interface pública e comportamento preservados.

O módulo main screen agora está organizado de forma sustentável, com cada arquivo tendo uma responsabilidade clara e tamanho gerenciável. A abordagem de mixins permitiu manter a herança simples e a API pública intacta, garantindo que nenhum código externo precise ser alterado.

## Próximos Passos Sugeridos

1. **Revisar organização**: Verificar se a distribuição de métodos entre mixins está ideal
2. **Documentar padrão**: Usar este split como referência para outros módulos grandes
3. **Considerar extrações adicionais**: Se algum mixin ficar muito grande (>500 linhas), considerar subdivisão
4. **Migração de GodBless**: Aplicar padrão similar ao próximo módulo monolítico

---

**Data**: 6 de dezembro de 2025
**Branch**: qa/fixpack-04
**Autor**: GitHub Copilot (MS-39)
