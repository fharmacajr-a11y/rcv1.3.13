# Modulo Auditoria â€“ Visao Inicial (draft)

## 1. Responsabilidades desejadas do modulo
- Entregar uma tela unica de Auditoria no Hub/App que lista auditorias recentes, permite iniciar/encerrar fluxos por cliente e atualizar status (aberto, finalizado etc.) sem que a UI toque em Supabase diretamente.
- Prover comandos de acao (ver subpastas, enviar pacote compactado, excluir auditorias, criar pasta GERAL/Auditoria) encapsulando validacoes de org_id, bucket, prefixos e excecoes de negocio.
- Orquestrar o recebimento de pacotes ZIP/RAR/7z: validar formatos, extrair com seguranca, resolver duplicatas, acompanhar progresso deterministico e delegar uploads para a camada de Uploads/Storage.
- Integrar com o navegador padrao de arquivos (modules.uploads.open_files_browser) para que consultores possam revisar pastas da auditoria apos cada acao.
- Fornecer uma API de servico clara (listagem, status, storage context) reutilizavel em testes, scripts e em futuros shims da view legada.

## 2. Situacao atual (antes da modularizacao)
- O codigo esta concentrado em `src/modules/auditoria/view.py` (~1.4k linhas) e `src/modules/auditoria/service.py`; a view mistura Tkinter, logica de upload e chamadas ao storage, enquanto o service conhece Supabase e wrappers de arquivos.
- Ferramentas de infra importantes vivem fora do modulo (ex.: `infra/archive_utils.py` e `src/shared/storage_ui_bridge.py`), e documentos anteriores (`docs/architecture/FEATURE-auditoria-v1.md`) descrevem o objetivo, mas nao ha boundary real como em Clientes/Uploads.

### Arquivos inspecionados (inventario)
- `src/modules/auditoria/view.py` (UI + storage mix): classe `AuditoriaFrame` monta toolbar com busca de clientes (_build_ui), carrega caches de clientes/auditorias via `_lazy_load`, atualiza status pelo menu `_open_status_menu/_set_auditoria_status` e expÃµe botoes `Iniciar auditoria`, `Ver subpastas`, `Enviar arquivos`, `Excluir`. Funcoes criticas como `_open_subpastas`, `_upload_archive_to_auditoria`, `_worker_upload`, `_list_existing_names`, `_ask_rollback` e `_busy_done` tratam Supabase Storage, open_files_browser e as regras de ZIP/7z diretamente na view. Inclui ainda `DuplicatesDialog` (UI) e helpers de MIME/prefixos/ETA, evidenciando mistura de UI, regra de negocio e infra.
- `src/modules/auditoria/service.py` (service + infra): concentra chamadas ao Supabase (fetch_clients, fetch_auditorias, start/update/delete) e ao storage (get_storage_context, ensure_auditoria_folder, list_existing_file_names, upload_storage_bytes, remove_storage_objects). Tambem expÃµe wrappers para `infra.archive_utils` (`extract_archive_to`, `is_supported_archive`) e cacheia org_id em `_ORG_ID_CACHE`. Critico para separar regras de negocio e evitar que a view precise lidar com `infra.supabase_client` e storage client bruto.
- `infra/archive_utils.py` (infra/arquivos): oferece `extract_archive` com suporte a ZIP (zipfile), RAR (7z CLI) e 7z/volumes (py7zr), checa formatos (`is_supported_archive`), encontra o executavel do 7-Zip (`find_7z`) e expÃµe `ArchiveError`. A view (via service) depende dessas funcoes para validar/abrir pacotes antes de subir e trata mensagens de erro diretamente na UI.
- `src/shared/storage_ui_bridge.py` (bridge UI + storage): le variaveis RC_STORAGE_BUCKET_CLIENTS/RC_STORAGE_CLIENTS_FOLDER_FMT, resolve org_id via Supabase (`_get_org_id_from_supabase`) e reutiliza `src.modules.uploads.open_files_browser` para abrir o navegador de arquivos apontando para o cliente correto. Hoje a view de Auditoria nao usa o bridge; ela importa `src.ui.files_browser` direto.
- `docs/architecture/FEATURE-auditoria-v1.md` (documentacao): descreve a visao da feature, define a regra de dependencia `view.py -> service.py -> infra` e lista as funcoes expondo servicos (fetch/start/update/delete, storage context, ensure_auditoria_folder, upload_storage_bytes, wrappers de arquivos). Serve como referencia conceitual, mas o estado atual ainda viola o boundary porque a view manipula storage e arquivos.

### Entrypoints e comandos de UI
- O Hub (`src/ui/hub_screen.py`, botao "Auditoria") chama `navigate_to(app, "auditoria")` no router; `src/ui/main_window/router.py::_show_auditoria` instancia `AuditoriaFrame` com `go_back` para o Hub, o que faz dessa view o unico entrypoint da feature.
- Dentro da tela, a toolbar expÃµe busca incremental por cliente, combobox para escolher o cliente alvo, botao Limpar e atalho F5 via `_do_refresh`. A lista central (`ttk.Treeview`) mostra cliente/status/datas, abre menu de status no clique direito (`_open_status_menu`) e habilita as acoes do rodape.
- Comandos principais: `Iniciar auditoria` (_on_iniciar + service.start_auditoria), `Ver subpastas` (_open_subpastas -> `src.ui.files_browser.open_files_browser`), `Enviar arquivos para Auditoria` (_upload_archive_to_auditoria/_worker_upload) e `Excluir auditoria(s)` (_delete_auditorias). O menu de status usa `_set_auditoria_status` para chamar o service, e a view tambem oferece `_create_auditoria_folder` (manual) e `_add_refresh_menu_entry` (menu Exibir).
- Ao final de um upload, `_busy_done` reabre o navegador de arquivos posicionando `start_prefix` em `.../GERAL/Auditoria`, reforÃ§ando que a view controla integraÃ§Ãµes com Uploads diretamente.

## 3. Acoplamentos fortes identificados
- `src/modules/auditoria/view.py::_lazy_load/_load_clientes/_load_auditorias`: a view chama `auditoria_service.fetch_clients/fetch_auditorias` e manipula respostas Supabase diretamente, mantendo caches e indices de busca dentro da UI.
- `view._open_subpastas` importa `src.ui.files_browser.open_files_browser`, resolve `org_id` pelo service e monta `start_prefix` manualmente antes de abrir a janela. Em vez de delegar a bridge/modules.uploads, a UI sabe como navegar no bucket e segura o supabase client exposto.
- `view._upload_archive_to_auditoria` + `_worker_upload` usam `select_archive_file`, `zipfile`, `tempfile`, `auditoria_service.extract_archive_to`, `_guess_mime` e `auditoria_service.upload_storage_bytes` numa thread propria. Compactacao, checagem de duplicatas, estrategia (skip/replace/rename) e progresso (ETA, bytes) acontecem na view junto com dialogs Tk.
- `view._list_existing_names` chama `auditoria_service.list_existing_file_names`, mas o loop e cache vivem na UI para comparar com nomes do zip. `_ask_rollback` tambem chama `auditoria_service.remove_storage_objects`, mostrando que rollback e orchestrado via Tk threads.
- `_require_storage_ready` le `auditoria_service.is_online` e `get_clients_bucket` para exibir messageboxes sobre env vars; a UI conhece detalhes do bucket e do modo offline.
- `_busy_done` e `_busy_fail` cuidam de mensagens e tambem reimportam `open_files_browser` para atualizar a pasta; qualquer mudanca no navegador exige tocar essa view gigante.
- No service, funcoes como `get_storage_context`, `ensure_auditoria_folder`, `list_existing_file_names`, `upload_storage_bytes` e `remove_storage_objects` acessam `infra.supabase_client`/`sb.storage.from_(...)` diretamente, o que reforca que toda interacao com storage deve permanecer no service, mas hoje a view continua chamando essas APIs baixo nivel.
- `auditoria_service.extract_archive_to/is_supported_archive` sao apenas wrappers para `infra.archive_utils`, entao a view ainda fica dependente de `ArchiveError` e das limitacoes de ZIP/RAR/7z (dependencia do 7z.exe e py7zr) sem isolacao adequada.

Esses pontos serao os alvos para mover regras de upload/storage para `modules.auditoria.service`, delegando ao modulo Uploads (para browser) e deixando a view focada em eventos de UI.

## 4. Estrutura proposta para src/modules/auditoria
- `src/modules/auditoria/__init__.py`: exportar `AuditoriaFrame` e funcoes publicas (service facade) para o router/hub.
- `src/modules/auditoria/views/main_frame.py`: conter `AuditoriaFrame` focado em UI (toolbar, tree, binds, callbacks) chamando apenas metodos do service/bridge.
- `src/modules/auditoria/views/dialogs.py`: mover `DuplicatesDialog`, modal de progresso (_show_busy/_progress_update_ui) e futuros dialogs (confirmacoes, criacao de pasta).
- `src/modules/auditoria/service.py`: separar subdominios (`AuditoriaService` para CRUD/status/listagem, `AuditoriaUploadsService` para pipeline ZIP/7z usando modules.uploads.service ou helpers dedicados). Deve encapsular supabase, storage context, duplicatas, rollback, compressao e o relacionamento com Uploads.
- `src/modules/auditoria/forms/` (opcional): localizar formularios/inputs especificos se surgirem (ex.: filtros avancados, anotacoes).
- `src/modules/auditoria/tests/test_auditoria_service.py` e `tests/test_auditoria_integration.py`: garantir cobertura de status list/create/delete e do pipeline de upload (com stubs para storage e archive_utils).

### Mapeamento legado -> destino
- Trechos de construcao de UI (_build_ui, binds, toolbar, treeview) migrarao de `view.py` para `views/main_frame.py`; `DuplicatesDialog`, modais de progresso e helpers TK vao para `views/dialogs.py`.
- LÃ³gica de upload/copia de arquivos (`_upload_archive_to_auditoria`, `_worker_upload`, `_list_existing_names`, `_ask_rollback`, `_busy_done`, `_busy_fail`, `_require_storage_ready`) vira metodos no novo `AuditoriaUploadsService`, expondo callbacks para UI e reutilizando `modules.uploads.service` para subir bytes.
- Helpers de status/clientes (`canonical_status`, `_build_search_index`, `_filtra_clientes`) podem virar utils dentro do modulo ou funcoes privadas do service para facilitar testes.
- Pontos de integracao com `src.ui.files_browser` devem passar para um adapter (ex.: `storage_ui_bridge` ou `modules.uploads.open_files_browser`) chamado via service, mantendo a view agnostica do browser.

### Subdominios identificados
- **Listagem e filtros**: carregar clientes/auditorias, aplicar busca, atualizar status.
- **Upload/importacao de pacotes**: validar/abrir ZIP-RAR-7z, detectar duplicatas, acompanhar progresso, rollback.
- **Integracao com storage/browser**: resolver bucket/prefix, abrir janela de arquivos, garantir pasta GERAL/Auditoria, consultar nomes existentes.
- **Integracao com Clientes**: reaproveitar dados (razao, CNPJ, display_id) e manter cache sincronizado com o modulo Clientes sem duplicar logica.

## 5. Riscos e pontos de atencao
- Dependencia forte do modulo Uploads: precisamos garantir que `open_files_browser` e futuros helpers de upload estejam acessiveis via API publica (sem importar `src.ui.files_browser` direto) e que Auditoria nao duplique pipelines de Uploads.
- Compressao ZIP/RAR/7z depende de zipfile, 7z.exe (para RAR), py7zr e volumes `.7z.001`; erros de IO/senha e a falta do binario precisam ser tratados no service para nao travar a UI.
- Supabase/Storage offline: view e service exibem mensagens quando `auditoria_service.is_online()` falha; modularizacao deve manter feedback claro e suportar modo offline (ex.: permitir leitura local vs bloquear uploads).
- Scripts/QA: ha scripts (`scripts/test_upload_advanced.py`) e rotinas de suporte que importam `AuditoriaFrame`; qualquer mudanca no path publico precisa fornecer shims para nao quebrar QA na fase de migracao.

## 6. Proximas etapas sugeridas
- **Etapa 2**: criar skeleton real para `src/modules/auditoria/service.py` (separando subservicos) e `__init__.py` com wrappers/shims que mantem a API legado, sem alterar comportamento.
- **Etapa 3**: mover helpers de upload/zip/storage da view para o service (ou um novo adapter) e ajustar a view para chamar apenas operacoes de alto nivel, mantendo a UI responsavel por dialogs.
- **Etapa 4**: quebrar a view gigante em `views/main_frame.py` + `views/dialogs.py`, conectando com modules.uploads para abrir browser e com Clientes para reusar caches, em linha com o padrao ja aplicado no modulo Uploads.

## Etapa 2 - Skeleton do modulo src.modules.auditoria

**Objetivo**
- Organizar `src/modules/auditoria/service.py` em secoes de responsabilidade e criar a API publica (`src/modules/auditoria/__init__.py`) sem alterar comportamento.

**Implementado nesta etapa**
- Documentacao e comentarios em blocos no `service.py` (dados, storage, arquivos/ZIP) para evidenciar responsabilidades.
- Criacao das fachadas `AuditoriaDataService` e `AuditoriaStorageService`, mantendo as funcoes top-level intactas.
- Definicao de `__init__.py` reexportando os servicos, tipos auxiliares e `AuditoriaFrame` como interface publica.

**Proximos passos**
- Etapa 3: mover helpers de upload/zip/storage da `view.py` para o `service.py`, usando a API exposta agora e mantendo a view focada em UI.
- Etapa 4: quebrar a view em `views/main_frame.py` + `views/dialogs.py`, consumindo os servicos reorganizados.

## Etapa 3 - Movendo helpers de upload/ZIP/storage da view para o service

**Objetivo**
- Tirar da `AuditoriaFrame` a lógica pesada de ZIP/7z, Supabase Storage e rollback,
  centralizando essas responsabilidades em `src/modules/auditoria/service.py`
  (com possibilidade de delegar para `modules.uploads.service`), mantendo a view focada em UI.

**Implementado nesta etapa**
- Funções de serviço para preparar contexto de upload, listar nomes existentes,
  executar o envio completo (com estratégia de duplicatas e callback de progresso)
  e realizar rollback em caso de falha/cancelamento.
- Métodos da view `_upload_archive_to_auditoria`, `_worker_upload`, `_require_storage_ready`
  e auxiliares agora chamam essas funções do service, mantendo a mesma UX e removendo
  acesso direto ao storage/archive_utils na view.

**Próximos passos**
- Etapa 4: quebrar `view.py` em `views/main_frame.py` + `views/dialogs.py`, extraindo
  `DuplicatesDialog`, modais de busy/progresso e deixando o frame principal mais enxuto.
- Etapa 5: criar testes específicos para o pipeline de upload (service) simulando
  storage/archive_utils para garantir regressão zero.




## Etapa 4 – Split da view em views/main_frame.py + views/dialogs.py

**Objetivo**
- Reduzir o tamanho de src/modules/auditoria/view.py extraindo:
  - AuditoriaFrame para iews/main_frame.py;
  - diálogos auxiliares (ex.: DuplicatesDialog, modal de progresso) para iews/dialogs.py;
  mantendo iew.py como shim de compatibilidade.

**Implementado nesta etapa**
- Criado pacote src/modules/auditoria/views/ com:
  - main_frame.py concentrando AuditoriaFrame e lógica direta da tela principal;
  - dialogs.py com DuplicatesDialog e o modal reutilizado no progresso dos uploads.
- src/modules/auditoria/view.py passou a reexportar AuditoriaFrame, preservando o caminho legado usado pelo router/hub.
- src/modules/auditoria/__init__.py atualizou os imports para apontar para o novo pacote sem quebrar a API pública.

**Próximos passos**
- Etapa 5: continuar quebrando componentes internos da tela (listas, toolbars) ou iniciar os primeiros testes de serviço/integração do módulo.


## Etapa 5 – Testes de serviço/integração

**Objetivo**
- Criar a primeira bateria de testes de unidade e integração leve para o módulo Auditoria,
  cobrindo a API de dados (CRUD) e o pipeline de upload de arquivos, sem alterar comportamento.

**Implementado nesta etapa**
- Arquivo 	ests/modules/auditoria/test_auditoria_service_data.py cobrindo fetch/start/update/delete.
- Arquivo 	ests/modules/auditoria/test_auditoria_service_uploads.py cobrindo formatos suportados,
  duplicatas, rollback e cancelamento com dublês para Supabase/storage/archive_utils.
- Pequenas adaptações internas em service.py (se necessárias) para facilitar monkeypatch e injeção de dependências.

**Próximos passos**
- Etapa 6: com os testes protegendo o comportamento, fatiar componentes internos da UI
  (listas, toolbars) em helpers/classe separada dentro de iews/main_frame.py ou novos módulos
  em iews/, mantendo iew.py apenas como shim de compatibilidade.


## Etapa 6 ? Layout helpers para o AuditoriaFrame

**Objetivo**
- Diminuir o tamanho de `src/modules/auditoria/views/main_frame.py` movendo a constru??o do layout
  (toolbar, tree/lista, barra de a??es e menus) para um m?dulo dedicado em `views/`, sem alterar UX.

**Implementado nesta etapa**
- Criado `src/modules/auditoria/views/layout.py` com `build_auditoria_ui(frame)` e helpers privativos
  respons?veis por montar toolbar, treeview e rodap? em cima do frame recebido.
- O m?todo `_build_ui` agora delega inteiramente para `layout.build_auditoria_ui(self)` e apenas
  posiciona o label de status offline.
- `_add_refresh_menu_entry` virou um wrapper fino que chama `layout.add_refresh_menu_entry(self)`,
  mantendo o nome original usado em outras partes da view.
- Nenhuma assinatura p?blica de `AuditoriaFrame` mudou e todos os widgets/atributos continuam
  dispon?veis com os mesmos nomes.

**Pr?ximos passos**
- Etapa 7 (sugerida): aprofundar a separa??o extraindo componentes menores (por exemplo,
  pain?is/toolbar como classes pr?prias) e continuar reduzindo o acoplamento entre UI e l?gica.


## Etapa 7 ? Componentiza??o da UI (toolbar e lista)

**Objetivo**
- Reduzir acoplamento e tamanho do `AuditoriaFrame` extraindo a toolbar
  e a lista principal de auditorias para componentes reutiliz?veis,
  mantendo a mesma UX e API p?blica.

**Implementado nesta etapa**
- Cria??o de `src/modules/auditoria/views/components.py` com:
  - `AuditoriaToolbar`: encapsula a barra superior (busca, sele??o de cliente,
    bot?es de a??o), recebendo callbacks para m?todos do `AuditoriaFrame`.
  - `AuditoriaListPanel`: encapsula o `Treeview` principal, scrollbars e binds.
- `views/layout.py::build_auditoria_ui` passou a instanciar esses componentes,
  conectando-os ao `AuditoriaFrame` via callbacks.
- Aliases em `AuditoriaFrame` foram mantidos (`self.tree`, vari?veis de busca,
  combobox etc.), evitando altera??es na API p?blica e em c?digo legado.

**Pr?ximos passos**
- Etapa 8 (poss?vel): avaliar extra??o de um ?controller/viewmodel? leve
  para isolar ainda mais caches de clientes/auditorias e l?gicas de filtro,
  mantendo a UI como cliente do servi?o e do controller.



## Etapa 8 – ViewModel/Controller de Auditoria

**Objetivo**
- Isolar o estado da tela (clientes/auditorias, filtros e busca) em um
  AuditoriaViewModel, reduzindo a responsabilidade do AuditoriaFrame e
  deixando a UI consumir uma API de dados já filtrados.

**Implementado nesta etapa**
- Criação de `src/modules/auditoria/viewmodel.py` com:
  - `AuditoriaRow`: tipo de linha normalizada para a Treeview.
  - `AuditoriaViewModel`: responsável por carregar dados via
    `auditoria_service`, manter caches, aplicar filtros/busca e expor
    `get_rows()` para a view.
- `AuditoriaFrame` passou a delegar o carregamento e os filtros para o
  viewmodel (`self._vm`), atualizando a Treeview por meio de um método
  `_load_auditorias` baseado na lista do viewmodel.
- Remoção/migração de caches e helpers de filtro da view para o
  viewmodel, sem alterar a API pública da tela.

**Próximos passos**
- Etapa 9 (possível): avaliar novas melhorias na UX (ex.: filtros extras,
  colunas adicionais, ordenação) agora apoiadas na camada de viewmodel,
  e/ou aumentar cobertura de testes unitários para o viewmodel.

## Etapa 9 – Checkpoint de modularização

**Objetivo**
- Registrar o estado atual do módulo Auditoria após as etapas de
  modularização (service, views, viewmodel, componentes e testes),
  marcando-o como baseline estável para futuros ajustes e features.

**Estado atual**
- Service reorganizado em `src/modules/auditoria/service.py` com
  separação clara entre dados, storage e pipeline de upload.
- UI dividida em:
  - `views/main_frame.py` (AuditoriaFrame)
  - `views/dialogs.py` (diálogos)
  - `views/layout.py` (construção de layout)
  - `views/components.py` (toolbar e painel da lista)
- Camada de viewmodel em `src/modules/auditoria/viewmodel.py`
  concentrando caches de clientes/auditorias, filtros e busca.
- Testes de serviço e upload em `tests/modules/auditoria/`.
- Pylance sem avisos relevantes no módulo Auditoria após ajustes de
  tipos e guards opcionais.
- Nenhuma mudança intencional de comportamento da tela foi
  introduzida nesta etapa; apenas reorganização estrutural e ajustes
  de tipos.

**Próximos passos possíveis**
- (Opcional) Ampliar testes unitários para o `AuditoriaViewModel`.
- (Opcional) Evoluir UX sobre a camada atual (filtros extras,
  ordenação avançada), sempre em novas etapas específicas.

