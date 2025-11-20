# Scan global de modularização – RC Gestor

## 1. Visão geral

- Objetivo desta rodada foi levantar diagnóstico de arquitetura/modularização em todo o repositório (src, infra, adapters, data, helpers, security, scripts, migrations) sem tocar em código de produção.
- O módulo Clientes permanece como referência já modularizada: lógica encapsulada em src/modules/clientes/*, API pública consumida por src/ui/src/app_core.py, testes (	ests/test_clientes_*.py) e documentação própria (docs/dev/modulo_clientes_overview.md, docs/dev/modularizacao_clientes.md).
- As observações abaixo servem para priorizar próximos módulos/domínios a modularizar seguindo o padrão de Clientes.

## 2. Inventário de domínios

### Clientes (MODULARIZADO – referência)
- **Pastas/arquivos principais:** src/modules/clientes/view.py, src/modules/clientes/views/main_screen.py, src/modules/clientes/forms/*, src/modules/clientes/service.py, 	ests/test_clientes_*.
- **Interação com UI/app:** App carrega ClientesFrame e chama serviços/pipeline apenas via src.modules.clientes (UI e src/app_core.py não conversam direto com src.core).
- **Notas:** boundary bem definido, documentação atualizada e testes cobrindo regras + integração.

### Auditoria
- **Pastas/arquivos principais:** src/modules/auditoria/view.py (UI gigante), src/modules/auditoria/service.py, infra/archive_utils.py, src/ui/files_browser.py (dep de navegação), docs/architecture/FEATURE-auditoria-v1.md.
- **Interação com UI/app:** HubScreen e App abrem AuditoriaFrame diretamente; view ainda manipula storage, Supabase e diálogos.

### Uploads / Arquivos (browser + pipeline)
- **Pastas/arquivos principais:** src/ui/files_browser.py, src/core/services/upload_service.py, uploader_supabase.py, src/ui/forms/actions.py, src/modules/uploads/*, src/modules/forms/view.py.
- **Interação com UI/app:** menu principal chama helpers do iles_browser e uploader_supabase; forms/pipeline ainda ficam em src/ui, importando infra.supabase_client e dapters.storage direto.

### Senhas / Passwords
- **Pastas/arquivos principais:** src/ui/passwords_screen.py, data/supabase_repo.py, infra/repositories/passwords_repository.py, security/crypto.py, src/modules/passwords/*.
- **Interação com UI/app:** Hub/App acionam PasswordsScreen diretamente, que consulta o repositório Supabase e decripta dados; src.modules.passwords só reexporta APIs.

### Hub / Notas compartilhadas
- **Pastas/arquivos principais:** src/ui/hub_screen.py + subpastas src/ui/hub/*, src/modules/notas/*, src/core/services/notes_service.py.
- **Interação com UI/app:** Hub é frame carregado pelo App; view orquestra polling/realtime, status de Supabase e abre módulos satélite sem boundary claro.

### Fluxo de Caixa / Financeiro
- **Pastas/arquivos principais:** src/features/cashflow/ui.py, src/features/cashflow/repository.py, src/features/cashflow/dialogs.py, src/modules/cashflow/*.
- **Interação com UI/app:** Hub e menu chamam src.modules.cashflow.open_cashflow_window, que ainda depende das telas antigas e repositório acessando Supabase diretamente.

### Login & Sessão
- **Pastas/arquivos principais:** src/modules/login/service.py, src/modules/login/view.py, src/ui/login_dialog.py, src/ui/login/*, src/core/auth/*, src/core/session/*, data/auth_bootstrap.py.
- **Interação com UI/app:** src/app_gui.py e src/ui/main_window/app.py instanciam LoginDialog diretamente e manipulam Supabase client/sessão.

### Lixeira
- **Pastas/arquivos principais:** src/ui/lixeira/lixeira.py, src/modules/lixeira/*, src/core/services/lixeira_service.py.
- **Interação com UI/app:** src/app_core.py e src.ui.menu_bar abrem janela de lixeira (ainda da pasta src/ui), enquanto serviços seguem em src/core.

### PDF Preview & Documentos
- **Pastas/arquivos principais:** src/ui/pdf_preview_native.py, src/modules/pdf_preview/*, src/ui/files_browser.py (usa preview), src/utils/pdf_reader.py.
- **Interação com UI/app:** Browser, auditoria e uploads instanciam PdfViewerWin diretamente via src.modules.pdf_preview.

### App Shell & Navegação
- **Pastas/arquivos principais:** src/ui/main_window/app.py, src/ui/main_window/router.py, src/ui/main_window/frame_factory.py, src/app_core.py, src/ui/menu_bar.py, src/ui/topbar.py.
- **Interação com UI/app:** Camada responsável por menus, navegação entre módulos, status de rede e comandos rápidos; ainda contém lógicas de Supabase, uploads, lixeira e forms.

### Core & Serviços Compartilhados
- **Pastas/arquivos principais:** src/core/db_manager/*, src/core/services/*.py, src/core/search/search.py, src/core/navigation_controller.py, src/core/status_monitor.py, src/core/session/*, src/core/auth/*.
- **Interação com UI/app:** Vários módulos de UI importam diretamente src.core.db_manager, src.core.services.* e ferramentas de sessão/log.

### Infra / Adapters / Data / Security / Helpers
- **Pastas/arquivos principais:** infra/supabase_*, infra/archive_utils.py, infra/net_status.py, infra/repositories/passwords_repository.py, dapters/storage/*, data/supabase_repo.py, security/crypto.py, src/helpers/*.
- **Interação com UI/app:** UI usa diretamente Supabase client (infra.supabase_client), storage adapters e repositórios; scripts e serviços compartilham esses componentes.

### Scripts utilitários e migrações
- **Pastas/arquivos principais:** scripts/*.py (smoke tests, upload demos, validações), uploader_supabase.py, migrations/*.sql.
- **Interação com UI/app:** usados manualmente por equipe para validar suporte (7z, uploads, busca) e preparar bases Supabase (RPC ping, rc_notes, etc.).

## 3. Hotspots por domínio

### Auditoria
- **Arquivos grandes:** src/modules/auditoria/view.py (~1?464 linhas) e src/modules/auditoria/service.py (~10?kB) misturam UI, estado e acesso direto ao storage.
- **Funções complexas:** _upload_archive_to_auditoria / _worker_upload tratam zip/7z, progress bar e rollback em blocos >150 linhas.
- **Acoplamentos fortes:** view importa infra.supabase_client e src.ui.files_browser diretamente.

### Uploads / Arquivos
- **Arquivos grandes:** src/ui/files_browser.py (~1?256 linhas), src/ui/pdf_preview_native.py (~874) e src/core/services/upload_service.py (~400+) concentram UI + storage.
- **Funções complexas:** open_files_browser define dezenas de closures; App.enviar_para_supabase mistura seleção e envio em blocos grandes.
- **Acoplamentos fortes:** UI e forms ainda chamam infra.supabase_client, dapters.storage.* e uploader_supabase diretamente.

### App Shell & Core
- **Arquivos grandes:** src/ui/main_window/app.py (~726) e src/app_core.py (~360 relevantes) ainda misturam UI, services e filesystem.
- **Funções complexas:** App.__init__ e _wire_session_and_health configuram temas, monitoramento e login no mesmo bloco.
- **Acoplamentos fortes:** fallback de dir_base_cliente_from_pk continua acessando src.core.db_manager direto.

### Senhas / Password Vault
- **Arquivos grandes:** src/ui/passwords_screen.py (~423) e data/supabase_repo.py (~400+) concentram UI e RLS.
- **Funções complexas:** _build_ui, _open_new_password_dialog e PasswordDialog._save_password fazem validação + Supabase na mesma rotina.
- **Acoplamentos fortes:** UI importa data.supabase_repo e infra.repositories.passwords_repository diretamente.

### Hub / Notas & Fluxo de Caixa
- **Arquivos grandes:** src/ui/hub_screen.py (~671) e src/features/cashflow/ui.py (~11?kB) ainda são monolíticos.
- **Funções complexas:** HubScreen.__init__ e hub.controller.refresh_notes_async misturam Supabase, threads e UI.
- **Acoplamentos fortes:** Hub chama infra.supabase_client.get_supabase dentro da view; cashflow repository executa queries em Supabase sem boundary.

### Clientes (referência)
- **Arquivos grandes:** src/modules/clientes/views/main_screen.py (~1?097) e src/modules/clientes/forms/pipeline.py (~525).
- **Funções complexas:** _build_toolbar, _populate_tree e pipeline.perform_uploads ainda misturam responsabilidades, mas dentro do módulo.
- **Acoplamentos fortes:** ainda existem chamadas a src.core.db_manager por compatibilidade em alguns helpers.

## 4. Candidatos a modularização

### Uploads / Arquivos
- Responsabilidade: navegador, download/exclusão e pipeline de upload (clientes + auditoria).
- Código atual espalhado entre src/ui/files_browser.py, src/ui/forms/actions.py, uploader_supabase.py, src/core/services/upload_service.py e shims.
- Sintomas: funções monolíticas, UI conversando direto com Supabase/Storage, duplicação de lógica entre browser e uploader.
- **Estrutura sugerida:** src/modules/uploads/__init__.py, iews/browser.py, orms/, service.py, 	ests/test_uploads_service.py, 	ests/test_uploads_integration.py.
- **Esforço estimado:** alto.

### Auditoria
- Responsabilidade: listar auditorias, abrir pastas, iniciar uploads de pacotes.
- Sintomas: view gigante, storage prefix resolvido na UI, difícil de testar.
- **Estrutura sugerida:** quebrar view em múltiplos arquivos, dividir service (auditorias/storage/status), criar forms específicos.
- **Esforço estimado:** alto.

### Senhas / Password Vault
- Responsabilidade: CRUD de credenciais criptografadas.
- Sintomas: UI faz Supabase + crypto direto, sem testes, repositório fora do módulo.
- **Estrutura sugerida:** iews/, orms/, service.py encapsulando data.supabase_repo/security.crypto.
- **Esforço estimado:** médio.

### Hub / Notas
- Responsabilidade: tela inicial, mural em tempo real e atalhos para módulos.
- Sintomas: Hub view controla Supabase/polling, cashflow repository acessa Supabase direto.
- **Estrutura sugerida:** iews/hub.py, serviços dedicados, testes de controller.
- **Esforço estimado:** médio/alto.

## 5. Pendências globais e riscos

- Chamadas diretas a src.core.db_manager persistem em src/app_core.py, src/core/services/path_resolver.py, src/core/search/search.py e alguns scripts.
- UI usando Supabase/Storage cru: src/ui/forms/actions.py, src/ui/main_window/app.py, src/ui/passwords_screen.py, src/ui/hub_screen.py, uploader_supabase.py.
- Scripts/migrations críticos (scripts/dev_smoke.py, scripts/test_upload_advanced.py, scripts/validate_7z_support.py, docs/files_browser-plan.md) assumem acesso direto ao storage.
- Módulos com UI herdada: Uploads, Senhas, Notas, Cashflow, Lixeira, PDF Preview (alguns já em transição).
- Migrations/infra: arquivos migrations/*.sql executados manualmente; qualquer mudança de schema precisa de owner.
- Segurança: security/crypto.py depende de RC_CLIENT_SECRET_KEY; falhas quebram Senhas inteira.

## 6. Próximos módulos recomendados

- **Status**: Uploads / Arquivos concluído (overview em docs/dev/modulo_uploads_overview.md).
1. **Auditoria** - view mais complexa do sistema; separar camadas (UI, serviço, storage) permitirá evoluir upload de pacotes e integrações com storage sem tocar na tela principal.
2. **Senhas / Password Vault** - domínio com regras específicas (criptografia, RLS) mas isolado; mover UI + repositório para um módulo permitirá testes e evitará tocar Supabase direto da tela.
3. **Hub / Notas + Cashflow** - ponto de entrada do app e orquestrador de outros módulos; modularizar permitirá desacoplar polling/realtime e padronizar chamadas para cashflow/notes.

_Atualizacao 2025-11-15:_ Uploads/Arquivos finalizado como módulo estável (docs/dev/modulo_uploads_overview.md). Prioridade agora segue para Auditoria, Senhas e Hub/Notas.

_Nota 2025-11-15:_ Auditoria entrou oficialmente em **Etapa 1 - inventario + plano**; o draft esta em `docs/dev/modulo_auditoria_overview_draft.md` e Uploads/Clientes seguem como modulos de referencia.
