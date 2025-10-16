# Changelog

## v1.0.7 — 2025-10-14

### Novidades
- Modularização dos componentes de UI em `ui/components.py` e integração com `app_gui.py`.
- Scripts de banco realocados para `infra/db/` e documentados em `CLEANUP_REPORT.md`.
- Smoke test automatizado (`scripts/smoke_test.py`) garantindo abertura/fechamento da janela principal.
- Centralização de configurações em `config/settings.py` e logging via `config/logging_config.py`.
- Configuração padrão de tooling (`pyproject.toml` com Ruff/Mypy).

## v16 — 2025-10-11

### Novidades
- Telinha de **carregamento** (“Aguarde…”) com barra de progresso **indeterminada** no fluxo **Salvar + Enviar para Supabase**. Janela modal, centralizada e usando o ícone do app.
- Diálogo de **Subpasta** ao enviar documentos (ex.: `Sifap`, `Farmacia_Popular`, `Auditoria`). Padrão: `GERAL/`.
- Navegador **Ver Subpastas** do Storage: listar pastas/arquivos em `org_id/<client_id>/`, com opção de **download**.

### Melhorias
- Botão **Cartão CNPJ** agora trabalha com **PASTA**:
  - Prioriza arquivos por nome (palavras “cnpj”, “cartão”, etc.).
  - Faz leitura de **PDF** (pypdf/PyPDF2/fallback) para extrair **CNPJ** e, quando possível, a **Razão Social**.
- **CNPJ** formatado com segurança no formulário e na lista.
- Linhas com **Observações** destacadas (negrito + azul) no grid.
- Ícone `rc.ico` aplicado nos diálogos (Subpasta, Progresso, Mensagens).

### Correções
- Upload executado em **thread** (UI não trava durante envio).
- Retorno de `salvar_cliente` tratado de forma robusta (aceita `int`, `str`, `tuple/list`, `dict` com `id/pk/client_id`).
- Ajustes de centralização/posicionamento das janelas auxiliares.
- Restabelecidos e estabilizados os helpers `list_storage_objects` e `download_file`.

### Notas técnicas
- `ui/forms/actions.py`: novas rotinas `_coerce_client_id`, `_read_pdf_text_portable`, além de melhorias em `preencher_via_pasta` e `salvar_e_enviar_para_supabase`.
- Extração de campos via `utils.text_utils.extract_company_fields` para Razão Social/CNPJ a partir de PDFs.
- Estrutura de upload mantida: `org_id/<client_id>/GERAL/<subpasta>`.
