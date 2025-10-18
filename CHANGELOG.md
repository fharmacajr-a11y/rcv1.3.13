# Changelog

## v1.0.15 - 2025-10-16

### Refatorações (Batches 13D-17)
- **Batch 13D:** Extração da barra de menu para `gui/menu_bar.py` com callbacks centralizados.
- **Batch 14:** Criação de relatório LOC (`scripts/dev/loc_report.py`) e documentação de build.
- **Batch 15:** Extração de `AuthController`, `Keybindings`, `NavigationController` para `application/`.
- **Batch 16:** Movimentação da classe `App` de `app_gui.py` para `gui/main_window.py` (redução de 88.5% no entry point).
- **Batch 17:** Limpeza de dead-code: remoção de 8 módulos órfãos (0 referências externas), criação de `scripts/dev/find_unused.py`.

### Arquitetura
- NavigationController coordena troca de frames e integra com a TopBar.
- Adapter de Storage (`adapters/storage/api`) unifica uploads, downloads, zip e delega backend.
- Módulo de Lixeira cria subpastas obrigatórias automaticamente durante restauração.
- TopBar "Início" atualiza habilitação após cada navegação.
- Configuração e logging consolidados em `shared/config` e `shared/logging`.
- Scripts de healthcheck migrados para `infrastructure/`.

## v1.0.7 - 2025-10-14

### Novidades
- Modularizacao dos componentes de UI em `ui/components.py` e integracao com `app_gui.py`.
- Scripts de banco realocados para `infra/db/` e documentados em `CLEANUP_REPORT.md`.
- Smoke test automatizado (`scripts/smoke_test.py`) garantindo abertura/fechamento da janela principal.
- Centralizacao de configuracoes em `config/settings.py` e logging via `config/logging_config.py`.
- Configuracao padrao de tooling (`pyproject.toml` com Ruff/Mypy).

## v16 - 2025-10-11

### Novidades
- Telinha de carregamento ("Aguarde") com barra de progresso indeterminada no fluxo "Salvar + Enviar para Supabase". Janela modal, centralizada e usando o icone do app.
- Dialogo de Subpasta ao enviar documentos (ex.: `Sifap`, `Farmacia_Popular`, `Auditoria`). Padrao: `GERAL/`.
- Navegador "Ver Subpastas" do Storage: listar pastas/arquivos em `org_id/<client_id>/`, com opcao de download.

### Melhorias
- Botao "Cartao CNPJ" agora trabalha com pasta:
  - Prioriza arquivos por nome (palavras "cnpj", "cartao", etc.).
  - Faz leitura de PDF (pypdf/PyPDF2/fallback) para extrair CNPJ e, quando possivel, a Razao Social.
- CNPJ formatado com seguranca no formulario e na lista.
- Linhas com observacoes destacadas (negrito + azul) no grid.
- Icone `rc.ico` aplicado nos dialogos (Subpasta, Progresso, Mensagens).

### Correcoes
- Upload executado em thread (UI nao trava durante envio).
- Retorno de `salvar_cliente` tratado de forma robusta (aceita `int`, `str`, `tuple/list`, `dict` com `id/pk/client_id`).
- Ajustes de centralizacao/posicionamento das janelas auxiliares.
- Restabelecidos e estabilizados os helpers `list_storage_objects` e `download_file`.

### Notas tecnicas
- `ui/forms/actions.py`: novas rotinas `_coerce_client_id`, `_read_pdf_text_portable`, alem de melhorias em `preencher_via_pasta` e `salvar_e_enviar_para_supabase`.
- Extracao de campos via `utils.text_utils.extract_company_fields` para Razao Social/CNPJ a partir de PDFs.
- Estrutura de upload mantida: `org_id/<client_id>/GERAL/<subpasta>`.
