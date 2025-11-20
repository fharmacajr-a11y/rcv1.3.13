# Módulo Uploads / Arquivos – Visão Inicial (draft)

## 1. Responsabilidades desejadas do módulo
- Oferecer uma API única para navegar, visualizar e operar arquivos do Storage (listar, baixar, pre-visualizar PDFs) independente de quem chama (Clientes, Auditoria, scripts).
- Encapsular pipelines de upload (seleção de arquivos/pastas, validação, hashes, inserção em documents/document_versions) sem que UI precise conversar com Supabase ou adapters diretamente.
- Centralizar operações administrativas (apagar/mover objetos, zipar downloads, verificar status) e repassar apenas eventos/estado para a UI.
- Padronizar a integração com Supabase Storage (resolução de bucket/prefixo, org_id, autenticação, RLS) e com os adapters dapters.storage.*.
- Expor utilitários reutilizáveis para domínios que dependem de Uploads (Clientes, Auditoria, scripts de suporte), garantindo consistência de logs, toasts e progress bars.

## 2. Situação atual (antes da modularização)

### Arquivos/funções principais
- **src/ui/files_browser.py** (UI + services embarcados): janela Tk muito grande com treeview, atalhos e dezenas de closures responsáveis por listar objetos, montar downloads (download_folder_zip), excluir arquivos via Supabase e acionar previews. Mistura UI, cache local e chamadas diretas aos helpers/storage.
- **src/core/services/upload_service.py** (service + infra): implementa upload_folder_to_supabase, cuidando de percorrer pastas, gerar chaves (make_storage_key), checar duplicidade pedindo dapters.storage.api.list_files, subir bytes e inserir registros em documents/document_versions via infra.supabase_client. Não tem boundary de módulo.
- **uploader_supabase.py** (mistureba UI + service): define diálogos Tk (UploadProgressDialog), seleção de PDFs, confirmação para volumes grandes, interação com supabase.storage e com SupabaseStorageAdapter. É chamado pelo App para uploads “avançados”.
- **src/ui/forms/actions.py** (UI + infra): tela/hub legado de uploads dentro de “Forms” que importa diretamente infra.supabase_client, dapters.storage.*, executa download/preview, executa pipeline (validate/prepare/perform) e manipula buckets/RLS manualmente.
- **src/modules/uploads/*** (façade): iew.py apenas reexporta open_files_browser, service.py só dá alias para src.core.services.upload_service, e components/helpers.py contém utilitários de prefixo/org. Ainda não há módulo real.
- **src/ui/main_window/app.py** (App shell): botões/menu chamam open_files_browser (para “Ver subpastas do cliente”) e os helpers send_to_supabase_interactive/send_folder_to_supabase do uploader_supabase.py. Também expõe get_current_client_storage_prefix para ser chamado pelo uploader.
- **Outros consumidores**: src/modules/auditoria/view.py e src/shared/storage_ui_bridge.py importam open_files_browser para abrir a janela a partir da tela de Auditoria; scripts em scripts/test_upload_* usam diretamente uploader_supabase/upload_service.

### Entrypoints de UI identificados
- open_files_browser(...) em src/ui/files_browser.py: usado pelo menu principal do App, pela Auditoria (AuditoriaFrame._open_subpastas / _busy_done), e pelo bridge storage_ui_bridge.
- App.enviar_para_supabase() e App.enviar_pasta_supabase() (src/ui/main_window/app.py): chamam send_to_supabase_interactive / send_folder_to_supabase para uploads livres.
- APIs auxiliares do uploader (send_to_supabase_interactive, send_folder_to_supabase, upload_files_to_supabase) são acionadas por botões na toolbar/menu e pelos scripts de QA.
- src/ui/forms/actions.py expõe comandos como “Enviar PDFs do formulário” e “Baixar arquivos para conferência” usados na tela legada de cadastros.

## 3. Acoplamentos fortes identificados
- src/ui/files_browser.py::open_files_browser e closures como _on_delete_files chamam supabase.storage.from_(bucket) diretamente para remover objetos quando o usuário confirma exclusão ? responsabilidade deveria migrar para modules.uploads.service (subdomínio: **navegador**).
- uploader_supabase.upload_files_to_supabase utiliza supabase.table("documents") e SupabaseStorageAdapter diretamente para cada arquivo; também depende do método App.get_current_client_storage_prefix para saber o destino ? deveria depender de um serviço de Uploads (subdomínio: **pipeline genérico/Clientes**).
- src/ui/forms/actions.py importa infra.supabase_client.exec_postgrest, supabase e SupabaseStorageAdapter, realiza _resolve_org_id e chama storage_download_file/delete_file dentro de handlers de UI ? acoplamento a **pipeline legado**.
- src/core/services/upload_service.py aciona dapters.storage.api (list/upload) e manipula documents/document_versions diretamente; qualquer UI que precise subir algo precisa importar esse service bruto ? deveria ser encapsulado pela camada modules.uploads.service (subdomínio: **serviço de metadados**).
- src/ui/main_window.app conhece detalhes de buckets/env (SUPABASE_BUCKET, RC_STORAGE_BUCKET_CLIENTS) e passa ase_prefix manualmente aos helpers, além de lidar com mensagens de erro do uploader ? deveria delegar a um façade modules.uploads.open_manager().

## 4. Estrutura proposta para src/modules/uploads
- src/modules/uploads/__init__.py: expor open_files_browser, UploadsFrame e o namespace service. Hoje já existe, mas passaria a importar apenas do pacote interno.
- src/modules/uploads/views/browser.py: mover o conteúdo de src/ui/files_browser.py (fracionado em componentes menores). iew.py atual viraria simples adaptador.
- src/modules/uploads/forms/: centralizar diálogos auxiliares hoje espalhados em uploader_supabase.py e closures da UI (ex.: prompt de subpasta, confirm dialogs, progresso determinístico).
- src/modules/uploads/service.py: camada oficial falando com Supabase/storage. Absorve src/core/services/upload_service.py, grande parte do uploader_supabase.py (cálculo de chaves, checagem de duplicidade, inserts em documents) e operações de delete/list do iles_browser.
- src/modules/uploads/pipeline.py (ou service/pipeline.py): abstrair pipelines reutilizáveis (ex.: enviar múltiplos PDFs, upload de pastas, pipelines específicos de Auditoria). Poderia envolver código reaproveitado do pipeline de Clientes + uploader_supabase.
- 	ests/test_uploads_service.py: unitários simulando adapters/storage (monkeypatch) para garantir que service gere chaves corretas, valide duplicidade e trate erros.
- 	ests/test_uploads_integration.py: fluxo end-to-end mockado (listar ? upload ? delete), cobrindo API pública.

**Mapeamento aproximado atual ? futuro**
- src/ui/files_browser.py ? src/modules/uploads/views/browser.py + orms/ auxiliares.
- uploader_supabase.py ? utilidades de UI (dialogs/progressos) vão para orms/, lógica de supabase/storage vai para service.py/pipeline.py.
- src/core/services/upload_service.py ? funções migradas para modules/uploads/service.py (com adapters via injeção) e testes dedicados.
- src/ui/forms/actions.py ? chamadas a storage serão substituídas por helpers de módulo; arquivo vira shim semelhante ao que foi feito em Clientes.
- src/modules/uploads/components/helpers.py ? permanece dentro do módulo, servindo tanto views quanto service (talvez movido para src/modules/uploads/helpers.py).

## 5. Riscos e pontos de atenção
- **Integração com Clientes**: pipeline atual de src/modules.clientes.forms.pipeline chama diretamente src.core.services.upload_service; migrar deve manter compatibilidade durante um bom tempo.
- **Auditoria**: tela depende da janela do browser e dispara uploads próprios (ZIP/7z) que hoje vivem dentro de AuditoriaFrame; precisará consumir o novo serviço sem duplicar lógica.
- **Scripts/QA**: scripts/test_upload_*.py e uploader_supabase.py são usados por suporte; precisam continuar funcionando (talvez mantendo CLI/shim).
- **Progress/Status no App**: uploader_supabase atual manipula diretamente status bar e dialogs; ao modularizar, precisamos expor callbacks/observables para a UI, evitando acoplamento com Tk.
- **Configuração de buckets/org_id**: hoje espalhada em vários arquivos (env vars diferentes). O módulo deve centralizar leitura dessas variáveis para não quebrar ambientes customizados.

## 6. Próximas etapas sugeridas
- **Etapa 2:** criar skeleton real em src/modules/uploads/{__init__,service.py} reexportando as funções existentes (wrappers vazios), além de mover components/helpers.py para dentro do pacote como dependência única.
- **Etapa 3:** extrair pequenos helpers do uploader_supabase.py e src/core/services/upload_service.py para o novo service, mantendo shims (por exemplo, mover cálculo de prefix/bucket e inserção em documents).
- **Etapa 4:** iniciar a migração da UI (iles_browser.py) para src/modules/uploads.views, quebrando closures em classes menores e consumindo a nova API de service; src/ui/files_browser.py vira shim temporário.
## Etapa 2 - Skeleton do modulo src.modules.uploads

**Objetivo**
- Introduzir src/modules/uploads/service.py e src/modules/uploads/__init__.py como fachada inicial para o codigo legado de uploads.

**Implementado nesta etapa**
- Criacao do arquivo src/modules/uploads/service.py com docstring e wrappers que delegam para uploader_supabase.py e src.core.services.upload_service sem alterar comportamento.
- Ajuste de src/modules/uploads/__init__.py para expor a API publica minima (wrappers de upload, utilitarios e excecoes) alem do modulo service original.

**Proximos passos**
- Etapa 3: mover helpers especificos de upload de uploader_supabase.py e src/core/services/upload_service.py para modules.uploads.service, mantendo shims nos arquivos antigos.
- Etapa 4: iniciar a migracao da UI de uploads (src/ui/files_browser.py) para views/forms dentro de src/modules/uploads consumindo a nova API.
## Etapa 3 - Movimento de helpers para modules.uploads.service

**Objetivo**
- Migrar a logica de Supabase/Storage e metadados de uploader_supabase.py e src/core/services/upload_service.py para src/modules/uploads/service.py, mantendo os arquivos antigos como shims de UI/compatibilidade.

**Implementado nesta etapa**
- src/modules/uploads/service.py agora concentra o upload completo de pastas (upload_folder_to_supabase), o modelo UploadItem, helpers para coletar/normalizar PDFs e o fluxo upload_items_for_client (usado pelo uploader).
- src/core/services/upload_service.py tornou-se um shim que reexporta upload_folder_to_supabase do modulo Uploads.
- uploader_supabase.py passou a importar/usar os helpers do modulo (UploadItem, collect_pdfs_from_folder, upload_items_for_client), mantendo apenas a orquestracao de UI (dialogs, summary, progress bar).

**Proximos passos**
- Etapa 4: iniciar a extracao da UI do navegador (src/ui/files_browser.py) para src/modules/uploads/views/ e orms/, consumindo diretamente modules.uploads.service.
- Revisar scripts/QA (scripts/test_upload_*) para adotar o modulo Uploads quando fizer sentido e manter compatibilidade com as CLIs existentes.
## Etapa 4 - UI do navegador em modules.uploads.views

**Objetivo**
- Migrar a janela principal de arquivos (src/ui/files_browser.py) para src/modules/uploads/views, mantendo o arquivo antigo como shim.

**Implementado nesta etapa**
- Criado src/modules/uploads/views/browser.py com UploadsBrowserWindow e toda a construcao da UI (treeview, botoes, refresh) reutilizando os helpers do modulo.
- Atualizado src/modules/uploads/view.py e src/modules/uploads/__init__.py para reexportar UploadsBrowserWindow/open_files_browser do novo caminho.
- src/ui/files_browser.py tornou-se um shim que apenas delega para modules.uploads.open_files_browser, preservando compatibilidade com importacoes antigas.

**Proximos passos**
- Etapa 5: quebrar a view em componentes menores (tree/lista, painel de preview, status) e reduzir callbacks gigantes.
- Etapa 6: mover a logica residual de storage/estado da view para modules.uploads.service, mantendo a interface apenas com preocupacoes de UI.
## Etapa 6 - Logica de storage movida para o service

**Objetivo**
- Remover chamadas diretas a Supabase/Storage das views, centralizando-as em src/modules/uploads/service.py.

**Implementado nesta etapa**
- Criadas funcoes de dominio (list_browser_items, delete_storage_object, download_storage_object) em modules.uploads.service para listar, excluir e baixar objetos.
- UploadsBrowserWindow/FileList passaram a chamar apenas essas funcoes, mantendo a mesma UX.
- Views nao importam mais helpers de storage externos; toda a logica de acesso fica encapsulada no service.

**Proximos passos**
- Revisar scripts/CLI de upload para usar o modulo Uploads.
- Adicionar testes unitarios/integracao dedicados ao modulo (service + views).
## Foto final do modulo Uploads

O overview consolidado do modulo Uploads / Arquivos esta em docs/dev/modulo_uploads_overview.md. Este arquivo permanece como historico das etapas e migracoes, similar ao docs/dev/modularizacao_clientes.md.
