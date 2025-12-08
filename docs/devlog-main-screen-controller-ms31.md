# MS-31 – Mapa Controller/Headless da Main Screen de Clientes

## Resumo executivo
Analisei a tela principal de clientes (MainScreenFrame e builders) para entender onde a lógica de negócio permanece acoplada à camada Tkinter. A view já delega parte do trabalho a managers headless (FilterSortManager, UiStateManager, SelectionManager, PickModeManager) e a um controller de ações (MainScreenActions), mas ainda contém decisões de negócio (validações, cálculo de estados e mensagens) misturadas a atualizações de widgets.
Há espaço para consolidar essa lógica em um controller headless único que receba snapshots de estado (seleção, conectividade, upload, filtros, pick mode) e devolva resultados puros (estados de botões, ações a executar, mensagens), reduzindo duplicação e risco ao evoluir a UI.

## Responsabilidades por arquivo
### src/modules/clientes/views/main_screen.py
| Responsabilidade | Tipo |
| --- | --- |
| Instancia view model, managers headless (FilterSortManager, UiStateManager, SelectionManager, PickModeManager, Connectivity) e Actions | MISTO |
| Orquestra builders de UI e mantém referências de widgets (toolbar, tree, footer, banner) | VIEW |
| Carrega dados (carregar), aplica filtros/ordenação via FilterSortManager e renderiza Treeview | MISTO |
| Atualiza estados de botões (_update_main_buttons_state) usando UiStateManager, mas aplicando diretamente em widgets | MISTO |
| Lida com pick mode (enter/leave), salvando/restaurando estados de botões/menus | MISTO |
| Handlers de batch (delete/restore/export) com validações, diálogos e chamadas ao BatchOperationsCoordinator | MISTO |
| Mudança de status (_apply_status_for) chamando serviço e mostrando messagebox | MISTO |
| Bindings de eventos (duplo clique, delete key) com EventRouter e callbacks | MISTO |
| Atualização de status footer (_set_count_text) com cálculo de estatísticas e escrita na UI global | MISTO |

### src/modules/clientes/views/main_screen_ui_builder.py
| Responsabilidade | Tipo |
| --- | --- |
| Monta toolbar, footer, banner e bind inicial de seleção para habilitar/desabilitar envio | VIEW |
| Constrói Treeview e controles de coluna; sincroniza com ColumnManager e persiste visibilidade | MISTO |
| Normaliza ordem inicial e expõe vars/refs da toolbar para a view | MISTO |
| Configura proxies/binds para scroll e alinhamento de controles de coluna | VIEW |

### src/modules/clientes/views/main_screen_helpers.py
| Responsabilidade | Tipo |
| --- | --- |
| Normalização de labels de ordenação/filtro e aliases | HEADLESS |
| Construção de choices para filtro de status | HEADLESS |
| Sort keys e aplicação de filtros/busca (apply_combined_filters, filter_clients) | HEADLESS |
| Cálculo de estados de botões (calculate_button_states) | HEADLESS |
| Cálculo de estatísticas de novos clientes e parsing de datas | HEADLESS |

### src/modules/clientes/controllers/main_screen_actions.py (MS-25/MS-26)
| Responsabilidade | Tipo |
| --- | --- |
| Define ActionResult estruturado | HEADLESS |
| Handlers de ações principais (novo, editar, subpastas, enviar Supabase/pasta, lixeira, obrigações) chamando callbacks fornecidos pela view | HEADLESS |
| Log de erros e tradução para mensagens sugeridas (sem Tkinter) | HEADLESS |

### src/modules/clientes/views/main_screen_controller.py
| Responsabilidade | Tipo |
| --- | --- |
| compute_main_screen_state: filtros, ordenação e flags de batch operations a partir de estado puro | HEADLESS |
| filter_clients / order_clients / aplicação de regras de batch (can_batch_*) | HEADLESS |
| Protocolo MainScreenComputedLike para consumo tipado pela view | HEADLESS |

## Pontos de acoplamento forte (View x Lógica)
- `_update_main_buttons_state`: calcula estados via UiStateManager mas aplica diretamente nos widgets e lê conectividade pelo get_supabase_state; mistura snapshot de negócio com manipulação Tk.
- `_on_batch_delete/_restore/_export`: validam seleção e conectividade, constroem mensagens/diálogos e executam coordenador; decisões de negócio + UI no mesmo método.
- `_apply_status_for`: lê/atualiza status via serviço e decide mensagens de erro dentro da view.
- `_set_count_text`: calcula estatísticas de novos clientes (regra) e escreve no status footer global.
- `_sort_by` e `_on_order_changed`: contêm regras de alternância de ordenação e side effects de UI.
- `_enter_pick_mode_ui` / `_leave_pick_mode_ui`: encapsulam snapshot do pick manager, mas também aplicam estados em footer/topbar/lixeira diretamente.
- `bind_main_events` / `_refresh_send_state`: calculam regra de habilitação de envio com base em seleção e atualizam widgets.

## O que já está headless / duplicações
- FilterSortManager + main_screen_controller.py já centralizam filtros/ordenação e flags de batch, mas a view ainda recalcula botões principais via UiStateManager e lógica adicional (_refresh_send_state, pick mode), gerando decisões duplicadas.
- main_screen_helpers.py oferece calculate_button_states e funções de filtro/ordem, enquanto main_screen.py mantém lógica própria para alternar ordenação (_sort_by) e para estados de botões (UiStateManager + lógica adicional de pick mode/menus).
- MainScreenActions encapsula callbacks com ActionResult, mas mensagens finais e recargas são decididas na view (_handle_action_result).

## Proposta de arquitetura de controller headless
- Criar/estender `MainScreenController` (controllers/main_screen_controller.py) para orquestrar: filtros/ordem (já existente), estados de botões (migrar da view/UiStateManager), decisões de batch e de envio de status.
- Interface sugerida:
  - `ViewStateInput`: snapshot puro (clientes visíveis/atuais, selected_ids, order_label, filter_label, search_text, is_online, is_uploading, is_pick_mode, connectivity_state, is_trash_screen, user_prefs?).
  - `compute(view_state) -> ViewStateResult`: devolve `visible_clients`, `button_states` (principal + batch), `status_filter_choices`, `order_label_normalized`, `messages` opcionais, `next_selection` opcional.
  - `handle_action(action: Literal["new","edit","trash","subfolders","send_supabase","send_folder","obrigacoes","status_change","batch_delete","batch_restore","batch_export"], ctx: ActionContext) -> ActionDecision`: usa SelectionManager/BatchCoordinator headless para validar e retorna enum + mensagem/parameters (ex.: `{"kind": "confirm", "message": "...", "on_confirm": Callable or token}`) que a view traduz em UI.
  - `apply_pick_mode_snapshot(snapshot_input) -> PickUiState`: decide estados/flags para footer/lixeira/menus, deixando a view só aplicar.
- A view passa a ser apenas: binding de eventos, renderização Tk, e aplicação de resultados (habilitar/desabilitar, abrir diálogos conforme decisão do controller).

## Plano incremental (MS-32+)
- **MS-32**: Extrair cálculo de estados de botões principais/batch para o controller (composição de UiStateManager + regras de pick mode).  
  Arquivos: main_screen_controller.py (novas estruturas), main_screen.py (consome resultado), possivelmente main_screen_helpers.py (reaproveitar calculate_button_states).  
  Riscos: mudança de interface de `_update_main_buttons_state`; mitigar criando função de adaptação sem alterar assinatura pública do frame e cobrindo com testes unitários do controller.
- **MS-33**: Mover validações de batch (delete/restore/export) e construção de mensagens para o controller, retornando decisões estruturadas (ok/confirm/warn/error).  
  Arquivos: main_screen_controller.py, main_screen.py (handlers passam a pedir decisão e só exibem diálogos).  
  Riscos: divergência com mensagens atuais; mitigar replicando textos em testes e garantindo ActionDecision com mensagens existentes.
- **MS-34**: Unificar ordenação/filtro/busca no controller (inclusive alternância de ordem e normalização), removendo lógica duplicada em `_sort_by` e `_on_order_changed`.  
  Arquivos: main_screen_controller.py, main_screen.py (handlers chamam controller), main_screen_helpers.py (reuso das funções).  
  Riscos: quebra de aliases; mitigar com testes cobrindo ORDER_LABEL_ALIASES.
- **MS-35**: Migrar mudança de status (_apply_status_for) e contagem (_set_count_text) para o controller, retornando payload para a view aplicar (mensagens e updates no status footer).  
  Arquivos: main_screen_controller.py, main_screen.py.  
  Riscos: efeitos colaterais no status footer; mitigar mantendo métodos da view como adaptadores.
- **MS-36**: Consolidar MainScreenActions em uma interface única com o controller (sem sufixo de fase), ajustando testes para bater direto no headless.  
  Arquivos: main_screen_controller.py, main_screen_actions.py, main_screen.py, testes unitários existentes (redirecionar para controller).  
  Riscos: compatibilidade com callbacks fornecidos pelo app; mitigar mantendo ActionResult/ActionDecision compatíveis e adaptadores na view.

## Confirmações
- Nenhum arquivo .py de lógica foi alterado nesta fase; apenas foi adicionado este devlog.
- Testes não executados nesta fase (sem alterações de código).
