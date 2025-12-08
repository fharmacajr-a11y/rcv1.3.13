# QA-GLOBAL-001 – Panorama de Qualidade (v1.3.47)

## Contexto
- Versão: v1.3.47
- Objetivo: consolidar estado de testes, lint, tipagem e segurança em todo o projeto, e propor próximo(s) módulo(s) para refactor/testes.
- Referências lidas: `devlog-refactor-main-screen-ms4.md`, `devlog-refactor-client-form-cf-final.md`, `devlog-ui-global-03.md`, `devlog-tests-passwords-ms1.md`, `devlog-int-passwords-ms1.md`, `devlog-tests-passwords-legacy-ms1.md`, `devlog-fix-tests-clientes-mainwindow-ms1.md`, `devlog-fix-tests-uploads-clientes-ms2.md`.

## Inventário de testes
### Estrutura de pastas
| Pasta | ~Arquivos | Observações |
| --- | --- | --- |
| `tests/unit/adapters` | 2 | Adapters de storage e API, cobrem comportamentos síncronos em rede. |
| `tests/unit/core` | 27 | Env precedence, services, auth/bootstrap – 400+ testes headless. |
| `tests/unit/helpers` | 3 | Helpers de Tk skip e factories usados nos GUI tests. |
| `tests/unit/infra` | 16 | Supabase clients, retry, healthcheck; bastante I/O fake. |
| `tests/unit/modules` | 93 | Maior bloco (clientes tem 47 arquivos); inclui auditoria, hub, main_window, pdf_preview, uploads etc. |
| `tests/unit/security` | 1 | Verificações de hashing/permissions. |
| `tests/unit/src` | 3 | Smoke tests de entry points. |
| `tests/unit/ui` | 10 | Treeviews, diálogos Tk e window_utils (dependem de `tk_skip`). |
| `tests/unit/utils` | 17 | Helpers gerais (paths, textnorm, zip). |
| `tests/modules/auditoria` | 4 | Serviços/repo headless; sem UI. |
| `tests/modules/clientes` | 3 | Actions headless (form/clientes). |
| `tests/modules/passwords` | 2 | TEST-001 (service/actions). |
| `tests/modules/uploads` | 2 | Uploader headless e dialogs de progresso. |
| `tests/integration/passwords` | 2 | INT-001: Fake repo + controller cobrindo bootstrap/filtros/CRUD. |
| `tests/gui_legacy` | 9 | Suites antigas de UI (Clientes, Lixeira, Hub etc.) preservadas mas sempre `pytest.skip`. |

### Skips e testes legacy
- `tests/gui_legacy/*.py`, `tests/test_login_dialog_*.py`, `tests/test_menu_logout.py`: `pytest.skip` no topo porque dependem de Tk real ou fluxos CTX antigos.
- `tests/unit/modules/passwords/LEGACY_*.py` + `tests/unit/modules/passwords/__init__.py`: módulo inteiro dá `pytest.skip` para preservar histórico (LEGACY-TESTS-MS1). Testes válidos migraram para `tests/modules/passwords` e `tests/integration/passwords`.
- `tests/unit/modules/chatgpt/test_chatgpt_*` e `tests/unit/modules/sites/test_sites_screen_ui.py`: marcam skip automático quando Tkinter não está disponível.
- `tests/unit/modules/clientes/test_editor_cliente.py`: possui `pytest.importorskip("tkinter")` e cria janelas reais. Rodando sozinho passa, mas executar o bloco completo `tests/unit` ainda provoca crash do Tcl/TtkBootstrap (detalhes abaixo).
- Helpers `tests/helpers/tk_skip.py` são amplamente referenciados para detectar ausência de Tk e pular cenários de UI.

## Resultados de pytest (por bloco)
- Comando 1: `python -m pytest tests/unit --no-cov -q`
  - Resultado: abortou após ~40% com `Windows fatal exception: access violation` dentro de `ttkbootstrap.Style` quando `tests/unit/modules/clientes/test_form_cliente_cria_campos_internos` tentou inicializar vários `Toplevel`. Esse crash impede rodar `tests/unit` de ponta a ponta no ambiente atual.
  - Ação: executei todos os diretórios/arquivos em blocos menores com `--no-cov` para mapear o estado real.
- Blocos unitários executados (100% PASS, exceto skips esperados):
  - `python -m pytest tests/unit/core --no-cov`: 421 passed (69s).
  - `python -m pytest tests/unit/helpers --no-cov`: 77 passed.
  - `python -m pytest tests/unit/infra --no-cov`: 270 passed.
  - `python -m pytest tests/unit/adapters --no-cov`: 91 passed.
  - `python -m pytest tests/unit/ui --no-cov`: 110 passed.
  - `python -m pytest tests/unit/utils --no-cov`: 231 passed.
  - `python -m pytest tests/unit/security --no-cov`: 22 passed.
  - `python -m pytest tests/unit/src --no-cov`: 48 passed.
  - `python -m pytest tests/unit/modules/auditoria --no-cov`: 35 passed.
  - `python -m pytest tests/unit/modules/cashflow --no-cov`: 78 passed.
  - `python -m pytest tests/unit/modules/chatgpt --no-cov`: 9 passed, 1 skipped (`Tkinter indisponível` guard).
  - `python -m pytest tests/unit/modules/clientes/components|forms|views --no-cov`: 54 + 197 + 415 passed (3 skips em `views` por Tk).
  - 15 arquivos avulsos de Clientes (service, forms legacy, status helpers, order combobox, document timestamps, viewmodels etc.) rodados individualmente: 955 testes no total, todos `passed`. `test_clientes_forms_prepare.py` é o mais lento (5m49s).
  - `python -m pytest tests/unit/modules/clientes/test_editor_cliente.py --no-cov`: 5 passed (quando isolado, não crasha).
  - `python -m pytest tests/unit/modules/hub --no-cov`: 180 passed.
  - `python -m pytest tests/unit/modules/lixeira --no-cov`: 93 passed.
  - `python -m pytest tests/unit/modules/main_window --no-cov`: 215 passed.
  - `python -m pytest tests/unit/modules/notas --no-cov`: 54 passed.
  - `python -m pytest tests/unit/modules/passwords --no-cov`: 0 tests (pasta inteira é legacy + skipped).
  - `python -m pytest tests/unit/modules/pdf_preview --no-cov`: 164 passed.
  - `python -m pytest tests/unit/modules/profiles --no-cov`: 21 passed.
  - `python -m pytest tests/unit/modules/sites --no-cov`: 2 passed, 1 skipped (Tk).
  - `python -m pytest tests/unit/modules/uploads --no-cov`: 120 passed.
- Tests por módulo de alto nível:
  - `python -m pytest tests/modules --no-cov`: 120 passed (Clientes actions, Auditoria repo, Uploads, Senhas headless).
- Integração:
  - `python -m pytest tests/integration --no-cov`: 14 passed (INT-001 Senhas, com FakeRepo e controller custom).
- Observações gerais:
  - **Módulos estáveis**: Clientes (apesar de volumoso, todos os ~1k testes passaram isoladamente), Senhas (unit + integration), Uploads (unit + módulos), MainWindow e Hub.
  - **Pontos de atenção**: rodar `tests/unit` completo segue impossível por crash do Tcl quando `ttkbootstrap.Style` é instanciado em sequência; seria ideal encapsular `client_form` nos helpers de skip/harness para que a suíte global não se auto interrompa. `test_clientes_forms_prepare.py` levou 5m49s sozinho – pode virar alvo de otimização/marcação `slow`.
  - **Skips visíveis**: 1 em `chatgpt` (Tk), 3 em `clientes/views` (Tk treeview), 1 em `sites` (Tk). Diretório `tests/unit/modules/passwords` é totalmente ignorado por desenho (LEGACY).

## Resultados de Ruff (lint)
- Comando: `ruff check src tests infra adapters`
- Total de findings: 11 (todos em arquivos específicos).
- Principais regras:
  - `F401` (imports não usados) – `src/ui/pdf_preview_native.py` e vários `LEGACY_test_passwords_*`.
  - `E402` (imports fora do topo) – `tests/unit/modules/clientes/forms/test_client_form_imports.py` mantém imports tardios para cobrir `client_form`.
  - `F811`/`F841` (redefinição de `patch` e variáveis não usadas) – concentradas em `tests/unit/modules/passwords/LEGACY_test_passwords_screen_ui.py`.
- Top arquivos com findings:
  1. `src/ui/pdf_preview_native.py` – 1 F401 (`tkinter` nunca usado após migração do preview para `PdfViewerWin` headless).
  2. `tests/unit/modules/clientes/forms/test_client_form_imports.py` – 2 E402 (aparentemente intencionais porém o lint acusa).
  3. `tests/unit/modules/passwords/LEGACY_test_passwords_screen_ui.py` – 8 findings (redefinições e variáveis não usadas) mantendo código histórico.

## Resultados de Bandit (segurança)
- Comandos: `python -m bandit -q -r src infra adapters` e `python -m bandit -r src infra adapters -f json -o bandit.json`.
- Findings por severidade: **0** (LOW/MEDIUM/HIGH).
- Regras disparadas: nenhuma – apenas avisos sobre comentários que continham a palavra “test”.
- Arquivos críticos: nenhum item sinalizado; o relatório JSON confirma `results: []` e 31.7k LOC avaliadas. Único ruído são `# nosec` antigos nas utilidades de rede/zip.

## Resultados de Pyright (tipagem)
- Comando: `pyright src tests`
- Total: 8 errors, 5 warnings.
- Principais categorias:
  - **ArgumentType**: `src/modules/chatgpt/service.py:109` envia `list[dict[str, str]]` para `OpenAI.responses.create`, que espera `str|ResponseInputParam|Omit`. Precisa de adaptação do payload da API.
  - **Redeclaration**: `src/modules/clientes/viewmodel.py:335` redeclara `key_func` dentro de `_sort_rows`, confundindo Pyright (o arquivo já passou por múltiplos refactors).
  - **OptionalMemberAccess**: `src/modules/hub/views/hub_screen.py:260` assume que `context.auth` nunca é `None`; Pyright alerta acesso inseguro.
  - **Tkinter typings**: `src/ui/components/inputs.py` dispara 7 erros porque `_clear_combobox_selection` espera `tkinter.ttk.Combobox` mas recebe `ttkbootstrap.Combobox`, além de warnings porque `trace_add`/`set` são acessados sem garantir que os `StringVar` existem.
- Módulos mais afetados: `modules/chatgpt`, `modules/clientes/viewmodel`, `modules/hub/views/hub_screen.py`, `ui/components/inputs.py`.

## Síntese por módulo / prioridade
- **Senhas** – TEST-001 + INT-001 concluídos; 13 unit tests + 14 integrações passando, Bandit e Ruff limpos. Estado considerado “fechado” conforme devlogs.
- **Clientes** – Refactors MS-4 (controller headless) e FIX-TESTS-001/002 estabilizaram a suíte (~1000 testes). Ainda assim, Pyright acusa duplicidade em `viewmodel.py` e a suite global falha por crash do Tk/ttkbootstrap quando roda `tests/unit` completo. Sugestão: microfase `QA-CL-002` para blindar `client_form`/`ttkbootstrap.Style` (usar `tk_skip`, mover instância global) e resolver o warning de redeclaração.
- **Uploads** – FIX-TESTS-002 garantiu wrappers (`center_window`) e progress dialogs. Testes unitários e de módulo passam; Bandit não detectou riscos. Prioridade média para revisar dependências do uploader Supabase (ainda há wrappers de compatibilidade).
- **Auditoria** – Apenas 1 arquivo unitário em `tests/unit/modules/auditoria` e 4 testes headless em `tests/modules/auditoria`. Sem integrações e sem cobertura Tk atualizada. Fortes candidata a `REF/TEST-AUD-00X` focando viewmodel/dialogs e storage history.
- **Hub** – 180 testes unitários passando, mas Pyright acusa `context.auth` potencialmente `None` nas views. Necessário revisar contratos do hub/controller e adicionar guardas ou tipagem mais precisa (microfase HUB-TEST-001).
- **PDF Preview / UI Components** – Ruff flagou import morto em `pdf_preview_native.py` e Pyright aponta incompatibilidades entre `ttkbootstrap.Combobox` e `ttk` em `inputs.py`. Agir aqui ajuda a reduzir crashes Tk globais e melhora tipagem da camada UI.
- **ChatGPT** – Serviço headless tem erro de tipagem (payload enviado à OpenAI). Testes atuais cobrem apenas UI com skips; faltam suites headless. Candidato para microfase combinando fix de tipagem + testes de serviço.
- **Outros módulos** – Lixeira, MainWindow, Hub, Uploads e Utils têm centenas de testes passando e nenhuma falha/alerta relevante além dos pontos já citados; podem ficar em nível C (manutenção).

## Próximos passos recomendados
1. **QA-CL-002 (Clientes UI/Tk)** – tratar crash do ttkbootstrap quando a suíte completa roda, reorganizar instância de `Style`/`Tk` no `client_form` e revisar `tests/unit/modules/clientes/test_editor_cliente.py` para usar os helpers `tk_skip`. Aproveitar para corrigir o warning de Pyright em `ClientesViewModel._sort_rows`.
2. **UI-CORE-001 (Inputs & Pdf Preview)** – alinhar tipagens do `ttkbootstrap.Combobox`, revisar `_clear_combobox_selection` e limpar imports de `pdf_preview_native.py`. Microfase transversal reduz warnings e elimina o risco de regressões Tk.
3. **HUB/AUD-TEST-001** – priorizar módulos menos trabalhados (Hub e Auditoria): adicionar integrações leve (similar ao padrão de Senhas) e endereçar o acesso opcional a `context.auth`. Auditoria, em especial, ainda só tem testes unitários mínimos.

## Log de comandos executados
- pytest:
  - `python -m pytest tests/unit --no-cov -q` (falhou por crash no ttkbootstrap).
  - `python -m pytest tests/unit/core --no-cov`
  - `python -m pytest tests/unit/helpers --no-cov`
  - `python -m pytest tests/unit/infra --no-cov`
  - `python -m pytest tests/unit/adapters --no-cov`
  - `python -m pytest tests/unit/ui --no-cov`
  - `python -m pytest tests/unit/utils --no-cov`
  - `python -m pytest tests/unit/security --no-cov`
  - `python -m pytest tests/unit/src --no-cov`
  - `python -m pytest tests/unit/modules/auditoria|cashflow|chatgpt|hub|lixeira|main_window|notas|pdf_preview|profiles|sites|uploads --no-cov`
  - `python -m pytest tests/unit/modules/clientes/components --no-cov`
  - `python -m pytest tests/unit/modules/clientes/forms --no-cov`
  - `python -m pytest tests/unit/modules/clientes/views --no-cov`
  - `python -m pytest tests/unit/modules/clientes/test_clientes_delete_button.py --no-cov`
  - `python -m pytest tests/unit/modules/clientes/test_clientes_forms_finalize.py --no-cov`
  - `python -m pytest tests/unit/modules/clientes/test_clientes_forms_prepare.py --no-cov`
  - `python -m pytest tests/unit/modules/clientes/test_clientes_forms_upload.py --no-cov`
  - `python -m pytest tests/unit/modules/clientes/test_clientes_integration.py --no-cov`
  - `python -m pytest tests/unit/modules/clientes/test_clientes_order_by_combobox.py --no-cov`
  - `python -m pytest tests/unit/modules/clientes/test_clientes_service*.py --no-cov` (cobertura, fase02, fase48, qa005)
  - `python -m pytest tests/unit/modules/clientes/test_clientes_status_helpers.py --no-cov`
  - `python -m pytest tests/unit/modules/clientes/test_document_versions_timestamp.py --no-cov`
  - `python -m pytest tests/unit/modules/clientes/test_viewmodel_filters.py --no-cov`
  - `python -m pytest tests/unit/modules/clientes/test_viewmodel_round15.py --no-cov`
  - `python -m pytest tests/unit/modules/clientes/test_editor_cliente.py --no-cov`
  - `python -m pytest tests/modules --no-cov`
  - `python -m pytest tests/integration --no-cov`
- ruff:
  - `ruff check src tests infra adapters`
- bandit:
  - `python -m bandit -q -r src infra adapters`
  - `python -m bandit -r src infra adapters -f json -o bandit.json`
- pyright:
  - `pyright src tests`
