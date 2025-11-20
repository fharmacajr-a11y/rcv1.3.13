# Módulo Uploads / Arquivos – Visão Geral

## 1. Responsabilidade do módulo

- Oferecer o navegador oficial de arquivos da aplicação (lista Treeview, preview básico, barra de status/ações), compartilhado por Clientes, Auditoria e scripts internos.
- Encapsular operações de Storage do Supabase: listar objetos por prefixo, baixar arquivos/pastas, excluir itens, gerar downloads zipados quando necessário.
- Disponibilizar pipelines de upload reutilizáveis (UploadItem, upload_folder_to_supabase, upload_items_for_client) consumidos por Clientes, Auditoria e pelo CLI uploader_supabase.py.
- Centralizar a resolução de bucket/prefix/env (get_clients_bucket, client_prefix_for_id, org_id atual) para que UI e outros módulos não lidem com variáveis de ambiente diretamente.
- Servir como boundary único para interações com documents / document_versions, mantendo compatibilidade com o legado via shims (src/core/services/upload_service.py, uploader_supabase.py).

## 2. Estrutura de pastas

- src/modules/uploads/__init__.py — ponto único de export da API pública (services + views).
- src/modules/uploads/view.py — integração com app/router (UploadsFrame, open_files_browser) para quem ainda espera o alias legado.
- src/modules/uploads/service.py — serviços de domínio: UploadItem, coleta de PDFs, upload_items_for_client, upload_folder_to_supabase, list_browser_items, delete_storage_object, download_storage_object, download zip, etc.
- src/modules/uploads/views/browser.py — classe UploadsBrowserWindow que compõe os subcomponentes e orquestra callbacks.
- src/modules/uploads/views/file_list.py — componente com o Treeview/lista de arquivos (seleção, binds, atalhos).
- src/modules/uploads/views/action_bar.py — barra de ações (botões Baixar/Excluir e futuros comandos).
- src/modules/uploads/components/helpers.py — utilitários compartilhados (formatar CNPJ, resolver bucket/prefix, etc.).
- src/ui/files_browser.py — shim legado que apenas reexporta src.modules.uploads.open_files_browser para manter compatibilidade com imports antigos.

## 3. API pública do módulo

### 3.1. Services (rom src.modules.uploads import service as uploads_service)

- UploadItem — dataclass usada para representar arquivos locais prontos para upload.
- collect_pdfs_from_folder(dirpath) / uild_items_from_files(paths) — helpers para preparar UploadItem a partir de pastas/seleções.
- upload_items_for_client(items, cnpj_digits, bucket=None, supabase_client=None, subfolder=None, progress_callback=None) — executa o upload programático reutilizado por Clientes, Auditoria e scripts.
- upload_folder_to_supabase(folder, client_id, subdir="SIFAP") — pipeline completo para salvar metadados em documents/document_versions (compatível com o serviço legado).
- list_browser_items(prefix, bucket=None) — lista objetos do Storage para o navegador, já aplicando prefixo/org_id corretos.
- delete_storage_object(remote_key) — remove um objeto do Storage (usado pela UI de arquivos).
- download_storage_object(remote_key, destination) — baixa um objeto para o caminho informado.
- download_folder_zip(...), delete_file(...), download_bytes(...) — wrappers expostos para fluxos específicos ou scripts.

### 3.2. Views & entrypoints

- open_files_browser(master, *, org_id, client_id, ...) — função pública usada pelo App, Auditoria e scripts para abrir o navegador.
- UploadsBrowserWindow — classe principal da janela (com prefixos, status, refresh, etc.).
- FileList — componente responsável pelo Treeview/binds, emitindo callbacks para o window.
- ActionBar — barra com botões padrão (Baixar, Excluir). Subcomponentes adicionais podem ser adicionados aqui no futuro.

### 3.3. Relação com outros módulos

- **Clientes**: o pipeline de uploads localizado em src/modules/clientes/forms/pipeline.py usa modules.uploads.service para enviar anexos e gerenciar metadados.
- **Auditoria**: src/modules/auditoria/view.py chama open_files_browser para permitir que consultores naveguem pelos arquivos do cliente diretamente.
- **Scripts/CLI**: uploader_supabase.py continua exposto para suporte/QA, mas agora delega para o módulo Uploads (mesmo fluxo de UploadItem e inserções).

## 4. Dependências externas encapsuladas

- Supabase Storage, via dapters.storage.api / dapters.storage.supabase_storage e infra.supabase_client, é acessado apenas dentro de modules.uploads.service.
- Operações em documents / document_versions (inserts, updates) também ficam dentro do service, que resolve org_id/user_id através do cliente Supabase.
- Variáveis de ambiente relevantes (SUPABASE_BUCKET, RC_STORAGE_BUCKET_CLIENTS, SUPABASE_DEFAULT_ORG) são lidas nos helpers/serviços, não nas views.

## 5. Estratégia de testes

- No momento, Uploads é exercitado indiretamente pelos testes de Clientes e pelos fluxos de integração existentes (	ests/test_clientes_*).
- Próximos passos incluem criar 	ests/test_uploads_service.py (unitário) e 	ests/test_uploads_integration.py (navegador + service simulando adapters), garantindo cobertura direta do módulo.
- Scripts/CLI usados pelo time de suporte continuarão servindo como smoke manual enquanto os testes automatizados são escritos.

## 6. Como outros módulos devem usar Uploads

- Para abrir o navegador de arquivos, importar open_files_browser de src.modules.uploads em vez de src.ui.files_browser.
- Para pipelines de upload ou operações de Storage (listar/deletar/baixar), consumir as funções expostas em src.modules.uploads.service; evitar chamar infra.supabase_client ou dapters.storage diretamente.
- Novos fluxos que precisem interagir com arquivos/buckets devem solicitar novos helpers no service, mantendo a UI desacoplada de Supabase/adapters.

## 7. Pendências e futuras melhorias

- Migrar scripts/QA antigos (ex.: scripts/test_upload_*, uploader_supabase.py em modo CLI) para usar a API pública do módulo, reduzindo shims legados.
- Adicionar testes unitários e de integração específicos do módulo, conforme descrito na seção 5.
- Avaliar encoding/mensagens ainda herdadas do legado (ícones/strings) para padronização futura.
- Monitorar uso das funções shim (src/core/services/upload_service.py, src/ui/files_browser.py) e removê-las quando não houver mais dependentes externos.
