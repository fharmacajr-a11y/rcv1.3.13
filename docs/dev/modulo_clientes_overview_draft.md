# Modulo Clientes - Visao Inicial (draft)

## 1. Responsabilidades desejadas do modulo
- Entregar a lista principal de clientes com busca incremental, filtros de status, ordenacoes predefinidas e contadores agregados prontos para o hub.
- Orquestrar as acoes de CRUD e infraestrutura disparadas a partir da tela (novo, editar, exclusao, abrir subpastas, enviar arquivos/pastas para a nuvem, abrir lixeira) sem que widgets conhecam detalhes do core.
- Sincronizar e expor o estado operacional (status no campo Observacoes, conectividade Supabase, progresso de upload) mantendo feedback unico na UI.
- Servir como ponto de integracao para outros modulos (ex.: Senhas) que precisam escolher um cliente, fornecendo modo pick e normalizacao de dados de contato.
- Persistir preferencias por usuario (colunas visiveis, ordem, status da lista) para garantir continuidade entre sessoes.

## 2. Situacao atual (antes da modularizacao)
- `src/modules/clientes/views/main_screen.py` (1276 linhas) ainda e a view legada portada de `app_gui`: mistura Tkinter, callbacks do `app`, consultas direto ao core (`search_clientes`, `get_cliente_by_id`, `update_status_only`), monitoramento de Supabase e leitura de variaveis de ambiente/prefs.
- O alias `ClientesFrame` em `src/modules/clientes/view.py` apenas reexporta `MainScreenFrame`, portanto o roteador continua importando o arquivo gigante.
- Existem helpers dispersos (`components/helpers.py` para menu de status, `service.py` para lixeira/CNPJ/duplicatas), mas a view continua chamando-os diretamente e mantendo caches internos (`_all_clientes`, `_search_norm_cache`, `_saved_toolbar_state`).
- A maior parte da logica de filtragem, ordenacao, sincronizacao dos controles de coluna e modo de selecao mora em metodos privados do frame, o que impede testes unitarios e reaproveitamento.

Caminhos relacionados (estado atual):
- `src/modules/clientes/views/main_screen.py`: view enorme com toda a UI, filtros, watchers de rede e logica de status.
- `src/modules/clientes/view.py`: shim que expõe `ClientesFrame` para o app/router.
- `src/modules/clientes/service.py`: funcoes de dominio (duplicatas, lixeira, salvar cliente) usadas pelos formularios e gancho para o core legado.
- `src/modules/clientes/components/helpers.py`: constroi menu de status, choices e regex que extraem o prefixo `[STATUS]` das observacoes.
- `src/ui/main_window/router.py`: cria a tela principal via `_show_main`, injeta callbacks (`app.novo_cliente`, `app.ver_subpastas`, `app.enviar_para_supabase`, etc.) e tambem usa `start_pick` quando o modulo de Senhas precisa escolher um cliente.

### Arquivos inspecionados (inventario)
- `src/modules/clientes/views/main_screen.py`: define `MainScreenFrame`, constroi toolbar, Treeview, botoes de rodape, sincroniza preferencias de colunas, filtra/ordena clientes via `search_clientes`, manipula status em `Observacoes` e monitora Supabase a cada 5s.
- `src/modules/clientes/view.py`: classe `ClientesFrame` que herda de `MainScreenFrame` para manter a API esperada pelo roteador.
- `src/modules/clientes/service.py`: camada de servicos/dominio usada pelos formularios (duplicatas, lixeira, salvar cliente, contadores) ainda desacoplada da view principal.
- `src/modules/clientes/components/helpers.py`: helpers para montar o menu/contexto de status com suporte a grupos configurados via env vars.
- `src/ui/main_window/router.py`: navega para a tela de Clientes (`navigate_to(..., "main")`), injeta callbacks e tambem reabre o frame em modo pick para o modulo de Senhas.

### Entrypoints e comandos de UI
- O usuario sai do Hub (`HubFrame`) clicando em "Clientes"; o router chama `_show_main`, instancia `ClientesFrame` e ja executa `frame.carregar()`. Outros modulos reutilizam o mesmo frame chamando `navigate_to(app, "main")`.
- Botoes/atalhos principais: buscar/limpar, combo de ordenacao, filtro de status, abrir lixeira, `Novo Cliente`, `Editar`, `Excluir`, `Ver Subpastas`, `Enviar para SupaBase`, `Enviar pasta`, menu de status (coluna 7), clique na coluna WhatsApp para abrir `wa.me`, e o modo de selecao para Senhas (`start_pick`, `btn_select`).
- A view tambem alimenta `app.status_footer` com contagem total/novos clientes, mostra banner de conectividade (via `get_supabase_state`) e bloqueia botoes conforme estado online/unstable/offline.

## 3. Acoplamentos fortes identificados
- A UI chama diretamente `search_clientes`, `get_cliente_by_id`, `update_status_only` e escreve no campo Observacoes substituindo o prefixo `[STATUS]`, sem intermediar pelo `service.py`.
- Controle de conectividade e texto dos botoes depende de `infra.supabase_client.get_supabase_state/get_cloud_status_for_ui`, alem de setar flags internas no objeto `app`.
- Preferencias de colunas (load/save) e variaveis de ambiente (`RC_INITIALS_MAP`, `RC_STATUS_CHOICES`, `RC_STATUS_GROUPS`) sao lidas pela view, misturando UI com storage/config.
- Formatar datas, CNPJ e nomes exige imports diretos de `src.app_utils`, `src.ui.hub.authors`, `src.utils.phone_utils`, espalhando helpers dentro da view.
- O modo pick conversa com o modulo de Senhas via `app.nav`, `navigate_to`, bindings globais e normalizacao manual do CNPJ, criando risco de regressao quando o frame for fatiado.

## 4. Estrutura proposta para src/modules/clientes
- `src/modules/clientes/service.py` continua sendo a fronteira com Supabase/core; precisamos expor funcoes especificas para listar clientes com filtros e para atualizar status/observacoes, deixando a view chamar apenas o service.
- Criar `src/modules/clientes/viewmodel.py` para encapsular `_all_clientes`, filtros de busca/status, cache normalizado (`_search_norm_cache`) e contadores exibidos no rodape. `MainScreenFrame` passaria a apenas disparar comandos do viewmodel.
- Reorganizar `views/` em componentes menores:
  - `views/main_frame.py`: shell que monta grid basico e injeta subcomponentes.
  - `views/toolbar.py` + `views/status_filter.py`: toolbar de busca, ordenacao, status e botoes de atalho (hoje em `create_search_controls` + logica extra).
  - `views/client_list.py`: Treeview e sincronizacao das colunas/Checkbuttons.
  - `views/footer.py`: botoes CRUD/upload/lixeira, isolando `set_uploading`.
  - `views/dialogs.py` ou `views/status_menu.py`: menu/contexto de status com helpers atuais.
  - `views/pick_mode.py`: comportamento especifico para `start_pick`, binds e banner.
- Extrair um `connectivity_monitor.py` (ou `controllers/cloud_status.py`) que observe `get_supabase_state` e exponha eventos para a view, evitando `after`/UI logic manual dentro do frame.
- Mapping legado -> destino:
  - `MainScreenFrame.carregar/_sort_clientes/_row_dict_from_cliente` -> `viewmodel.load_clientes` + formatters puros testaveis.
  - `_start_connectivity_monitor` + `set_uploading` -> controlador dedicado em `controllers/connectivity.py`.
  - `_ensure_status_menu/_apply_status_for` -> `status_menu.py` + service (`update_status`).
  - `_ensure_pick_ui/start_pick/_confirm_pick` -> `pick_mode.py`, mantendo API publica inalterada.

## 5. Riscos e pontos de atencao
- Integracao estreita com o modulo de Senhas via `start_pick`/`_return_to` e bindings globais (`bind_all("<Escape>")`) pode quebrar se o frame for reestruturado.
- Atualizacao das observacoes/STATUS depende de regex compartilhada com outros fluxos (service/forms). Precisamos garantir que mover essa logica nao mude o formato em disco.
- O monitoramento de conectividade e os textos do footer afetam `app.status_footer` e status bar global; qualquer split precisa preservar esses atributos ( `app._main_frame_ref`, `_net_state` ).
- Preferencias por usuario sao persistidas via `load_columns_visibility/save_columns_visibility`; mover a UI exige manter mesma chave `_user_key`.
- A view assume que `search_clientes` retorna objetos com atributos variados (Obj, dict, namedtuple). Separar em camadas exige normalizacao cuidadosa.

## 6. Proximas etapas sugeridas
- **Etapa 1**: criar viewmodel/formatters puros com testes cobrindo filtragem, ordenacao e extracao de status/observacoes. `MainScreenFrame` passa a delegar carregamento para a nova camada.
- **Etapa 2**: extrair toolbar/status filter e botoes do footer para `views/toolbar.py` e `views/footer.py`, preservando callbacks injetados pelo router.
- **Etapa 3**: mover `start_pick`/`_ensure_pick_ui` para `views/pick_mode.py`, isolando integracao com Senhas e facilitando testes.
- **Etapa 4**: encapsular `_start_connectivity_monitor` em um controlador observavel (timer unico + signals) reaproveitavel entre Clientes e outros modulos.
- **Etapa 5**: substituir chamadas diretas a `get_cliente_by_id/update_status_only` por funcoes explicitas no service, destravando faturos testes de status menu e preparando futura API publica do modulo.


## Etapa 2 – Toolbar e footer em views/

**Objetivo**
- Reduzir o tamanho de `src/modules/clientes/views/main_screen.py`
  extraindo a toolbar e o footer para componentes dedicados
  (`views/toolbar.py` e `views/footer.py`), mantendo o mesmo layout e
  callbacks.

**Implementado nesta etapa**
- Criação de `src/modules/clientes/views/toolbar.py` com a classe
  `ClientesToolbar`, responsável por busca, ordenação, filtro de
  status e atalhos, encaminhando eventos para o `MainScreenFrame`.
- Criação de `src/modules/clientes/views/footer.py` com a classe
  `ClientesFooter`, concentrando os botões CRUD/upload/lixeira e a
  lógica de `set_uploading`.
- `MainScreenFrame` passou a instanciar `ClientesToolbar` e
  `ClientesFooter` em `_build_ui`, mantendo aliases para atributos
  usados em código legado (entry de busca, combos, botões) e
  delegando as ações para os callbacks já existentes.
- Nenhuma alteração proposital na UX: textos, atalhos e layout da
  tela de Clientes permanecem iguais.

**Próximos passos**
- Etapa 3: extrair o comportamento de `start_pick`/`_ensure_pick_ui`
  para um componente/módulo dedicado (`views/pick_mode.py`), isolando
  a integração com o módulo de Senhas.


## Etapa 3 – Pick mode em views/pick_mode.py

**Objetivo**
- Isolar a lógica do modo seleção (“pick”) da tela de Clientes em
  um controlador dedicado (`PickModeController` em
  `views/pick_mode.py`), mantendo a API pública `start_pick` usada
  pelo router/módulo de Senhas.

**Implementado nesta etapa**
- Criação de `src/modules/clientes/views/pick_mode.py` com a classe
  `PickModeController`, responsável por:
  - entrar/sair do modo pick;
  - configurar e restaurar botões/labels específicos do modo;
  - lidar com binds de teclado/clique;
  - invocar o callback com o cliente selecionado.
- `MainScreenFrame.start_pick` passou a delegar ao controller,
  preservando a assinatura esperada pelo router.
- Botão “Selecionar” e atalhos (`Escape`, `Enter`, duplo clique)
  passaram a chamar o controller, mantendo o mesmo comportamento.
- Nenhuma mudança intencional na experiência do módulo de Senhas:
  o payload do cliente selecionado e o fluxo de navegação permanecem
  iguais.

**Próximos passos**
- Etapa 4: avaliar extração do monitor de conectividade Supabase
  para um controlador compartilhado, a partir do padrão usado em
  Auditoria.

## Etapa 5 – Boundary de service para get_cliente_by_id/update_status_only

**Objetivo**
- Substituir chamadas diretas a `get_cliente_by_id` e
  `update_status_only` por funções explícitas no `service.py`,
  preparando o módulo para testes mais isolados e uma API pública
  mais clara.

**Implementado nesta etapa**
- Criação de `fetch_cliente_by_id` e
  `update_cliente_status_and_observacoes` em
  `src/modules/clientes/service.py` como wrappers de alto nível
  para as operações de leitura e atualização de STATUS/Observações.
- `MainScreenFrame` e demais pontos do módulo Clientes passaram a
  usar essas funções em vez de chamar o core diretamente.
- Mantido o mesmo formato de STATUS (`[STATUS] texto`) e o mesmo
  comportamento de atualização na UI.

**Próximos passos**
- Etapa 6 (possível): revisar o módulo como um todo, marcar um
  checkpoint de modularização de Clientes e iniciar a
  refatoração de outro arquivo grande (ex.: `src/ui/pdf_preview_native.py`),
  reaproveitando o padrão aplicado em Auditoria/Clientes.

## Etapa 4 – Monitor de conectividade em controller dedicado

**Objetivo**
- Remover do `MainScreenFrame` a responsabilidade de monitorar
  Supabase/Cloud, centralizando essa lógica em um controlador
  reutilizável baseado em `after`, sem alterar a experiência do
  usuário.

**Implementado nesta etapa**
- Criação de `src/modules/clientes/controllers/connectivity.py`
  com a classe `ClientesConnectivityController`, responsável por
  agendar checagens periódicas, consultar o estado Supabase/Cloud
  e chamar o frame para atualizar UI e botões.
- `MainScreenFrame` passou a instanciar o controller e delegar
  `start/stop` do monitor para ele.
- A lógica de atualização de banner, `status_footer` e habilitação
  de ações foi concentrada em `_apply_connectivity_state`, chamada
  pelo controller.
- Mantida a mesma frequência de checagens e o mesmo comportamento
  visual (cores, textos, bloqueio de ações).

**Próximos passos**
- Etapa 5: encapsular chamadas a `get_cliente_by_id` e
  `update_status_only` em funções explícitas no `service.py`,
  preparando testes de menu de status e API pública do módulo.

## Etapa 6 – Checkpoint de modularização de Clientes

**Objetivo**
- Registrar o estado atual do módulo Clientes após as etapas
  de modularização (viewmodel, toolbar/footer, pick mode,
  controller de conectividade e boundaries de service), marcando
  uma baseline estável para futuras features.

**Estado atual**
- Viewmodel em src/modules/clientes/viewmodel.py centralizando
  cache de clientes, filtros/ordenação e STATUS em Observações.
- UI dividida em componentes:
  - iews/toolbar.py (ClientesToolbar)
  - iews/footer.py (ClientesFooter)
  - iews/pick_mode.py (PickModeController)
- Controlador de conectividade em
  src/modules/clientes/controllers/connectivity.py.
- Boundaries de service em src/modules/clientes/service.py
  (etch_cliente_by_id, update_cliente_status_and_observacoes)
  encapsulando acesso ao core.
- Testes cobrindo viewmodel e service (STATUS/Observações) e
  demais partes conforme implementado.

**Próximos passos possíveis**
- Apenas ajustes pontuais/bugs ou evolução de UX, seguindo o
  padrão de camadas estabelecido.

