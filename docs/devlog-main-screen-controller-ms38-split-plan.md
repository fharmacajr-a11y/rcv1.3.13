# MS-38 – Plano de fatiamento do `main_screen.py`

## Mapeamento do `main_screen.py` (estrutura atual)
- **Imports e constantes**: tkinter/ttk/ttkbootstrap, controllers/headless (FilterSortManager, UiStateManager, SelectionManager, PickModeManager, BatchOperationsCoordinator, EventRouter, connectivity), helpers (`main_screen_helpers`, `main_screen_controller`, `_build_status_menu`), serviços (Supabase), componentes (toolbar/footer/treeview), constantes de pick mode.
- **Classe `MainScreenFrame`** (única classe pública):
  - `__init__`: injeta callbacks, normaliza ordenação, instancia viewmodel/managers headless, controllers (pick/connectivity/actions), estados internos, chama builders do `main_screen_ui_builder.py`, inicia conectividade e `_update_main_buttons_state`.
  - **Ciclo de vida**: `destroy`, `set_uploading`, pick mode enter/leave wrappers (`_enter_pick_mode_ui`, `_leave_pick_mode_ui`, `enter_pick_mode`, `exit_pick_mode`, `is_pick_mode_active`, `start_pick`, `_on_pick_cancel/_confirm`).
  - **Carregamento e filtros**: `carregar`, `_sort_by`, `_buscar`, `_limpar_busca`, `apply_filters`, `_populate_status_filter_options`, `_refresh_with_controller`, `_update_ui_from_computed`, `_update_batch_buttons_from_computed`, `_update_batch_buttons_on_selection_change`.
  - **Rendering / treeview helpers**: `_row_values_masked`, `_refresh_rows`, `_render_clientes`, `_get_selected_values`, `_get_clients_for_controller`, `_resolve_order_preferences`.
  - **Eventos/binds**: `_rebind_double_click_handler`, `_on_double_click`, `_on_click`, `_on_tree_delete_key`, `_on_order_changed`, `_build_event_context`.
  - **Batch operations (UI + coord.)**: `_on_batch_delete_clicked`, `_on_batch_restore_clicked`, `_on_batch_export_clicked`.
  - **Status/menus**: `_apply_connectivity_state`, `_ensure_status_menu`, `_show_status_menu`, `_on_status_menu`, `_on_status_pick`, `_set_status`.
  - **Integração app/status bar**: `_set_count_text`, `_apply_status_for`, `setup_app_references` (builder), `_start_connectivity_monitor`.
  - **Selection helpers**: `_build_selection_snapshot`, `_get_selected_ids`.
  - **Botões / estados**: `_update_batch_buttons_state`, `_update_main_buttons_state` (consumindo `compute_button_states`), `_update_main_buttons_state` delega a `_update_batch_buttons_on_selection_change`.
  - **Ações/Callbacks gerais**: `on_delete_selected_clients`, `_invoke`, `_invoke_safe`, `_handle_action_result`.

## Proposta de divisão (3–4 arquivos)
- **`main_screen_frame.py`**  
  Responsabilidade: classe `MainScreenFrame` fina (construtor, wiring inicial, chamadas aos módulos de eventos/binds/batch/status). Mantém import público `MainScreenFrame` (reexportar em `main_screen.py` ou vice-versa).  
  Conteúdo migrado: `__init__`, ciclo de vida (`destroy`, pick wrappers, `set_uploading`), referências a app/status bar, entrada de pick mode/exit, `_start_connectivity_monitor`, `_handle_action_result`, `_invoke/_invoke_safe`.
- **`main_screen_events.py`**  
  Responsabilidade: handlers de eventos e binds da Treeview/toolbar/footer.  
  Conteúdo: `_rebind_double_click_handler`, `_on_double_click`, `_on_click`, `_on_tree_delete_key`, `_on_order_changed`, `_on_status_menu`, `_on_status_pick`, `_set_status`, `bind_main_events` (pode ser adaptado ou reexportado do builder), helpers de seleção (`_build_selection_snapshot`, `_get_selected_ids`, `_build_event_context`).
- **`main_screen_dataflow.py`**  
  Responsabilidade: carregamento, filtros, renderização e atualização de UI via controller/headless.  
  Conteúdo: `carregar`, `_sort_by`, `_buscar`, `_limpar_busca`, `apply_filters`, `_populate_status_filter_options`, `_refresh_with_controller`, `_update_ui_from_computed`, `_update_batch_buttons_from_computed`, `_update_batch_buttons_on_selection_change`, `_row_values_masked`, `_refresh_rows`, `_render_clientes`, `_get_clients_for_controller`, `_resolve_order_preferences`, `_set_count_text`, `_apply_status_for`, `_apply_connectivity_state`, `_update_main_buttons_state`, `_update_batch_buttons_state`.
- **`main_screen_batch.py`**  
  Responsabilidade: UI bridges para batch (decisões já estão no controller headless).  
  Conteúdo: `_on_batch_delete_clicked`, `_on_batch_restore_clicked`, `_on_batch_export_clicked`.
- (Opcional, se quiser manter 3 arquivos): fundir `main_screen_batch.py` em `main_screen_events.py` ou `main_screen_dataflow.py` conforme tamanho final.

**`main_screen.py`** permanece como ponto de entrada, importando e expondo `MainScreenFrame` (e constantes) a partir dos módulos novos; pode conter apenas reexports.

## Estratégia segura para MS-39 (execução da divisão)
- **Ordem**  
  1) Criar novos arquivos vazios com imports/reexports mínimos.  
  2) Mover blocos de métodos por grupo (eventos, dataflow, batch) mantendo a assinatura e o `self` intactos.  
  3) Deixar `main_screen.py` como façade que importa `MainScreenFrame` (ou herda) de `main_screen_frame.py` e reexporta `__all__` e constantes.
- **Como manter entrada pública**  
  - `main_screen.py` continuará com `__all__ = ["MainScreenFrame", ...]` e fará `from .main_screen_frame import MainScreenFrame`.  
  - Outros módulos não precisam mudar imports.
- **Cuidados**  
  - Binds/eventos: garantir que lambdas/`add="+"` e referências a `_event_router`, `_pick_mode_manager`, `_selection_manager` permaneçam acessíveis (mesmo módulo ou import com `self`).  
  - Integração app/status bar: métodos que acessam `self.app` ou variáveis do builder devem manter ordem de inicialização.  
  - Batch: preservar uso de `decide_batch_*`, `_invoke_safe`, mensagens e coordenação de diálogos.  
  - Evitar imports circulares; preferir funções auxiliares que recebem `frame` como parâmetro (sem criar novas classes).
- **Testes a rodar na MS-39**  
  - `pytest tests/unit/modules/clientes/views/test_main_screen_batch_logic_fase07.py -q`  
  - `pytest tests/unit/modules/clientes/views/test_main_screen_controller_ms1.py -q`  
  - `pytest tests/unit/modules/clientes/views/test_main_screen_controller_filters_ms4.py -q`  
  - `pytest tests/unit/modules/clientes/controllers/test_main_screen_actions_ms25.py -q`  
  - `pytest tests/unit/modules/clientes/ -k "batch or lixeira or delete or restore or export" -q`

## Confirmação
- Nenhum código de produção foi alterado nesta fase; apenas leitura e documentação para o plano de fatiamento.
