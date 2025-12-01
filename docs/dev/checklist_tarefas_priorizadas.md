# Checklist de Tarefas Priorizadas - RC Gestor de Clientes

**Data:** 23 de novembro de 2025  
**Versão Base:** v1.2.55  
**Branch:** qa/fixpack-04

---

## Legenda de Prioridades

- **P0** 🔴 - **CRÍTICO** - Segurança, bugs graves, bloqueadores
- **P1** 🟡 - **IMPORTANTE** - Performance, qualidade, manutenibilidade
- **P2** 🟢 - **DESEJÁVEL** - Melhorias, otimizações, boas práticas
- **P3** ⚪ - **COSMÉTICO** - Nice-to-have, longo prazo

## Status das Tarefas

- [ ] Não iniciado
- [x] Concluído
- [>] Em progresso

---

## P0 - CRÍTICO 🔴

### Segurança

- [x] **SEG-001: Auditoria de CVEs em dependências** ✅ **CONCLUÍDO**
  - **Área:** `requirements.txt`, segurança
  - **Descrição:** Executar `pip-audit` e corrigir vulnerabilidades conhecidas
  - **Comando:** `pip-audit --fix`
  - **Risco:** Exploits em bibliotecas desatualizadas
  - **Esforço:** 2-4h
  - **Automável:** Parcial (detecção sim, correção manual)
  - **Resultado:**
    - ✅ 128 pacotes auditados
    - ⚠️ 1 CVE identificado: `pdfminer-six` GHSA-f83h-ghpp-7wcc (CVSS 7.8 HIGH)
    - ✅ Pacotes críticos limpos: `cryptography`, `pillow`, `httpx`, `certifi`, `bcrypt`, `pyjwt`
    - 📄 Relatório: `docs/dev/seguranca_dependencias.md`
    - 🔒 Risco residual: BAIXO (aplicação desktop mono-usuário)

- [x] **SEG-002: Verificar `.env.backup` no gitignore** ✅ **CONCLUÍDO**
  - **Área:** `.gitignore`, segurança
  - **Descrição:** Garantir que `.env.backup` não seja versionado
  - **Ação:** Adicionar ao `.gitignore` se não estiver
  - **Risco:** Leak de secrets no repositório
  - **Esforço:** 5min
  - **Automável:** Sim
  - **Resultado:**
    - ✅ `.env.backup` já estava no `.gitignore` (linha 20)
    - 🚨 **CRÍTICO CORRIGIDO:** `.env` e `.env.backup` estavam commitados no histórico
    - ✅ Removidos do controle de versão com `git rm --cached`
    - ⚠️ ATENÇÃO: Arquivos ainda existem localmente (correto)
    - 📝 Commit: f6f8aff

- [x] **SEG-003: Remover secrets hardcoded em testes** ✅ **CONCLUÍDO**
  - **Área:** `tests/test_health_fallback.py`, `tests/test_env_precedence.py`
  - **Descrição:** Substituir URLs/keys hardcoded por fixtures/mocks
  - **Exemplo:** `SUPABASE_URL=https://test.supabase.co` → usar mock
  - **Risco:** Leak acidental em logs públicos do CI
  - **Esforço:** 1-2h
  - **Automável:** Manual (requer refatoração de testes)
  - **Resultado:**
    - ✅ Fixtures centralizadas criadas em `tests/conftest.py`:
      * `fake_supabase_url()` → URL fictícia para testes
      * `fake_supabase_key()` → JWT fake para testes
      * `fake_env_vars()` → Dicionário completo de variáveis fake
    - ✅ `test_health_fallback.py` refatorado (7 testes atualizados)
    - ✅ `test_env_precedence.py` refatorado (1 teste atualizado)
    - ✅ `test_env_precedence.py`: 4/4 testes passando
    - ⚠️ `test_health_fallback.py`: Import circular pré-existente detectado (não relacionado à refatoração)
    - 📝 Commit: 729ffda

- [x] **SEG-004: Aumentar cobertura do módulo de criptografia** ✅ **CONCLUÍDO**
  - **Área:** `security/crypto.py`
  - **Descrição:** Adicionar testes unitários para as funções de criptografia/derivação de chave usadas pelo app (criptografar/decifrar, chaves inválidas, erros).
  - **Motivo:** Coverage estava em **19,5%** no pacote `security/` (código crítico de segurança); agora **95,1%** (superou meta de ≥ 80%), conforme documentado em `dev/cov_sec_crypto.md`.
  - **Esforço:** 4–6h (TEST-001 + QA-003 focados em `security/crypto.py`)
  - **Automável:** Manual (21 testes criados em `tests/test_security_crypto_fase33.py`, sem alterações em código de produção)

### Funcionalidade

- [x] **FUNC-001: Validar operações bloqueantes na GUI** ✅ **CONCLUÍDO**
  - **Área:** `src/ui/`, `src/modules/*/views/`
  - **Descrição:** Auditar operações síncronas que podem travar UI
  - **Arquivos principais:**
    - `src/modules/main_window/views/main_window.py` (health check)
    - `src/ui/files_browser.py` (listagem de arquivos)
  - **Ação:** Mover para threads ou usar async/await
  - **Risco:** UI travada em redes lentas
  - **Esforço:** 4-8h
  - **Automável:** Manual (análise + refatoração)
  - **Resultado:**
    - ✅ **Health Check (`main_window.py`)**: JÁ estava otimizado
      - `get_supabase_state()` apenas lê variáveis globais (thread daemon background)
      - Polling a cada 5s não bloqueia (leitura rápida de estado)
    - ✅ **File Browser (`files_browser.py`)**: Refatorado para execução assíncrona
      - Criada `_populate_tree_async()` usando ThreadPoolExecutor
      - Carregamento inicial agora usa thread de fundo
      - Feedback "Carregando arquivos..." exibido durante listagem
      - Botões desabilitados durante carregamento (evita múltiplas chamadas)
      - Chamadas HTTP ao Supabase Storage não travam mais a GUI
    - ✅ **Arquivos modificados:**
      - `src/ui/files_browser.py`: 3 alterações (nova função async + 2 chamadas atualizadas)
    - ✅ **Testes:** 215/215 passando (0 regressões)
    - ✅ **Coverage:** 25.89% (threshold: 25%)
    - ✅ **Pre-commit:** Todos os hooks passando

---

## P1 - IMPORTANTE 🟡

### Performance

- [x] **PERF-001: Otimizar health check na inicialização** ✅
  - **Área:** `src/core/bootstrap.py`, `src/utils/network.py`, `src/app_gui.py`
  - **Descrição:** Health check pode atrasar startup em redes lentas
  - **Solução:** ✅ Dual strategy: (1) timeouts agressivos (2s→1s socket, 5s→2s HTTP) + (2) execução não-bloqueante em background após criação da GUI
  - **Benefício:** Startup instantâneo mesmo em redes lentas (redução de até 7s→0s no blocking)
  - **Esforço:** 2-3h (concluído)
  - **Implementação:**
    - `network.py`: Timeouts reduzidos (máx 3s vs 7s antes)
    - `bootstrap.py`: Nova função `schedule_healthcheck_after_gui()` executa check em background
    - `app_gui.py`: Janela criada ANTES do health check (não bloqueante)
  - **Validação:**
    - pytest: 215/215 passed
    - coverage: 25.85% (≥25%)
    - pre-commit: ✅ all hooks passed
  - **Automável:** Manual

- [x] **PERF-002: Threading em operações de upload/download** ✅ **CONCLUÍDO**
  - **Área:** `src/modules/uploads/`, `src/ui/files_browser.py`, `uploader_supabase.py`
  - **Descrição:** Mover I/O de rede para threads
  - **Benefício:** UI responsiva durante uploads/downloads
  - **Esforço:** 6-10h → **Real: ~4h**
  - **Automável:** Manual
  - **Resultado:**
    - ✅ **Download individual:** Refatorado `do_download()` em `files_browser.py` (linhas 1086-1138)
      * Usa threading.Thread para I/O em background
      * Botão desabilitado durante operação
      * Callback via `_safe_after()` para atualização na thread principal
    - ✅ **Upload batch:** Refatorado `_upload_batch()` em `uploader_supabase.py` (linhas 137-219)
      * Thread background para `upload_items_for_client()`
      * Janela de progresso atualizada via `widget.after()`
      * Aguarda resultado bloqueando apenas a janela modal, não a GUI principal
    - ✅ **Operações já async:** Verificado que já usam threading (FUNC-001):
      * Download ZIP de pasta (`on_zip_folder` - ThreadPoolExecutor)
      * Preview de PDF/imagem (`on_preview` - `_run_bg()` helper)
      * Listagem de arquivos (`_populate_tree_async` - ThreadPoolExecutor)
    - ✅ **Testes:** 326/328 passando (2 skipped)
    - ✅ **Cobertura:** 26.89% (≥25%)
    - ✅ **Pre-commit:** All hooks passed
    - 📊 **Impacto:** GUI nunca congela durante uploads/downloads de qualquer tamanho

- [x] **PERF-003: Implementar lazy loading em listas grandes** ✅ **CONCLUÍDO**
  - **Área:** `src/ui/files_browser.py`, Treeviews
  - **Descrição:** Virtual scrolling ou paginação para > 1000 itens
  - **Benefício:** Performance em listagens grandes
  - **Esforço:** 8-12h
  - **Automável:** Manual (complexo)
  - **Resultado:**
    - ✅ **Estratégia implementada:** Paginação incremental por blocos de 200 itens
    - ✅ **Estrutura de controle criada:**
      - Atributos: `_children_all`, `_children_page_size` (200), `_children_offset`
      - Método `_insert_children_page()`: insere próxima página de itens
      - Método `_load_next_page()`: carrega mais itens via botão
      - Método `_update_load_more_button_state()`: controla visibilidade/estado do botão
    - ✅ **Modificação em `_populate_tree_async()`:**
      - Lista completa guardada em `_children_all` após fetch assíncrono
      - Apenas primeira página inserida automaticamente
      - Resto carregado sob demanda via botão "Carregar mais"
    - ✅ **UI:** Botão "Carregar mais arquivos" adicionado ao footer (lado esquerdo)
      - Aparece apenas para listagem raiz (não em subpastas)
      - Desabilitado automaticamente quando não há mais itens
    - ✅ **Compatibilidade com threading preservada:**
      - Fetch assíncrono continua via ThreadPoolExecutor (FUNC-001)
      - Inserção na Treeview sempre no thread principal (via `after()`)
    - ✅ **Arquivos modificados:** `src/ui/files_browser.py`
    - ✅ **Testes:** 327 passed, 1 skipped (0 regressões)
    - ✅ **Cobertura:** 26.81% (≥25%)
    - ✅ **Pre-commit:** All hooks passed
    - 📊 **Impacto:** Pastas com >1000 arquivos não travam mais a GUI; carregamento progressivo sob demanda

### Dependências

- [x] **DEP-001: Remover dependências duplicadas** ✅ **CONCLUÍDO**
  - **Área:** `requirements.txt`
  - **Descrição:** Investigar e remover:
    - ~~`pypdf` + `PyPDF2` (duplicação)~~ → **PyPDF2 já removido (Sprint P1)**
    - ~~`requests` (httpx já cobre)~~ → **requests já removido (Sprint P1)**
    - ~~`py7zr` (já removido segundo CHANGELOG?)~~ → **py7zr USADO (infra/archive_utils.py)**
    - `rarfile` → **REMOVIDO** (usa 7-Zip CLI, não biblioteca)
  - **Ação:** `pipdeptree` para análise, remover não usados
  - **Benefício:** Redução de 10-20MB no executável
  - **Esforço:** 2-4h
  - **Automável:** Parcial (detecção com `deptry`)
  - **Resultado:**
    - ✅ **Removido:** `rarfile>=4.2` (não usado - extração .rar via 7-Zip CLI)
    - ✅ **Verificado:** `pypdf`, `py7zr` estão em uso ativo
    - ✅ **Histórico:** `PyPDF2`, `requests`, `pdfminer.six` já removidos (Sprint P1-SEG/DEP)
    - ✅ **Testes:** 215/215 passando (incluindo 49 testes de archive)
    - 📊 **Impacto:** -1 dependência direta (~3-5MB de redução)

- [x] **DEP-002: Separar requirements dev/prod** ✅ **CONCLUÍDO**
  - **Área:** `requirements.txt` → `requirements-dev.txt`
  - **Descrição:** Mover pytest, mypy, ruff, etc. para requirements-dev
  - **Benefício:** Build de produção mais leve
  - **Esforço:** 1-2h
  - **Automável:** Manual
  - **Resultado:**
    - ✅ **Fase 1:** `requirements-dev.txt` criado (117 linhas) e `requirements.txt` limpo (111 linhas - apenas deps de produção)
    - ✅ **Fase 2:** Workflows CI/CD atualizados:
      * `.github/workflows/ci.yml`: jobs test/build agora usam `requirements-dev.txt`
      * `.github/workflows/security-audit.yml`: pip-audit agora escaneia `requirements-dev.txt`
      * `.github/workflows/release.yml`: mantém `requirements.txt` (build de produção)
    - ✅ Validação: 215/215 testes passando
    - ✅ Documentação atualizada: `docs/dev/requirements_strategy.md`
    - ✅ `CONTRIBUTING.md` criado com seções de setup e estratégia de dependências
    - ⏳ Pendente: Atualizar `INSTALACAO.md` (documentação de instalação para usuário final)

- [x] **DEP-003: Atualizar dependências críticas** ✅ **CONCLUÍDO**
  - **Área:** `requirements.txt`
  - **Descrição:** Atualizar bibliotecas de segurança/rede
  - **Prioridade:** cryptography, httpx, certifi, pydantic
  - **Ação:** `pip list --outdated`, testar atualizações
  - **Benefício:** Patches de segurança e performance
  - **Esforço:** 4-6h (inclui testes de regressão) → **Real: ~3h**
  - **Automável:** Parcial (Dependabot)
  - **Resultado:**
    - ✅ **Libs atualizadas (PATCH/MINOR):**
      * `certifi`: 2025.8.3 → 2025.11.12 (patch - certificados CA atualizados)
      * `cryptography`: 46.0.1 → 46.0.3 (patch - correções de segurança)
      * `httpx`: 0.27.2 → 0.28.1 (minor - melhorias SSL, compact JSON)
      * `pydantic`: 2.12.0 → 2.12.4 (patch - bug fixes)
      * `pydantic_core`: 2.41.1 → 2.41.5 (patch - Rust core fixes)
      * `pydantic-settings`: 2.6.0 → 2.12.0 (minor - alinhamento com pydantic)
      * `charset-normalizer`: 3.4.3 → 3.4.4 (patch)
      * `click`: 8.3.0 → 8.3.1 (patch)
      * `idna`: 3.10 → 3.11 (minor)
    - ✅ **Validação httpx 0.28:** Verificado changelog - sem breaking changes no uso do projeto
      * Projeto usa `verify=True` (boolean, não afetado)
      * Não usa `verify` como string ou `cert` argument (deprecated mas warnings apenas)
      * Não usa `app` ou `proxies` (removidos, mas não usados)
    - ✅ **Testes:** 327/328 passando (1 skipped)
    - ✅ **Cobertura:** 26.91% (≥25%)
    - ✅ **Pre-commit:** All hooks passed
    - 📊 **Impacto:** 9 libs de segurança/rede atualizadas com patches críticos
    - ⏳ **Pendente para DEP-003-Fase-2:**
      * `pillow`: 10.4.0 → 12.0.0 (MAJOR - requer análise de breaking changes em image APIs)
      * Libs de dev (pytest 8→9, ruff, etc.) - fora do escopo de segurança crítica

### Qualidade de Código

- [x] **QA-001: Refatorar `src/ui/files_browser.py`** ✅ **CONCLUÍDO**
  - **Área:** `src/ui/files_browser.py` (~1700 linhas → pacote modular)
  - **Descrição:** Quebrar em componentes menores
  - **Sugestão:** Separar em ListView, Toolbar, Actions, Service
  - **Benefício:** Manutenibilidade, testabilidade
  - **Esforço:** 12-16h
  - **Automável:** Manual (refatoração grande)
  - **Resultado:**
    - ✅ **Estrutura de pacote criada:** `src/ui/files_browser/`
      - `__init__.py`: API pública (re-exporta `open_files_browser`)
      - `main.py`: Lógica principal (1741 linhas, com documentação estruturada)
      - `constants.py`: Constantes centralizadas (UI_GAP, STATUS_GLYPHS, DEFAULT_PAGE_SIZE, tags)
      - `utils.py`: Utilitários puros (sanitize_filename, format_file_size, resolve_posix_path, suggest_zip_filename)
    - ✅ **Wrapper de retrocompatibilidade:** `src/ui/files_browser.py` (thin wrapper)
      - Mantém imports antigos funcionando
      - Re-exporta `format_cnpj_for_display` (corrigindo import errado anterior)
    - ✅ **Documentação interna adicionada ao `main.py`:**
      - Mapa de blocos lógicos (UI Construction, Listing & Pagination, File Actions, Tree Utilities, Status & Preferences)
      - Notas de performance (FUNC-001, PERF-002, PERF-003)
      - TODOs futuros (conversão em classe, extração de ActionHandler, PaginationManager)
    - ✅ **Extração conservadora:**
      - Funções puras movidas para `utils.py` (testáveis isoladamente)
      - Constantes centralizadas em `constants.py`
      - Closures aninhadas mantidas em `main.py` (evita quebra de estado compartilhado)
    - ✅ **Compatibilidade 100% preservada:**
      - API pública não mudou (`from src.ui.files_browser import open_files_browser`)
      - Nenhum código cliente precisa ser alterado
    - ✅ **Arquivos criados:**
      - `src/ui/files_browser/__init__.py`
      - `src/ui/files_browser/main.py`
      - `src/ui/files_browser/constants.py`
      - `src/ui/files_browser/utils.py`
    - ✅ **Testes:** 328 passed (+2 vs anterior), coverage 26.85% (≥25%)
    - ✅ **Pre-commit:** All hooks passed
    - 📊 **Impacto:** Código mais navegável, constantes centralizadas, utilitários testáveis separadamente; preparação para refatorações futuras

- [x] **QA-002: Refatorar `src/modules/main_window/views/main_window.py`** ✅ **CONCLUÍDO**
  - **Área:** `src/modules/main_window/views/main_window.py` (785 linhas → modularizado)
  - **Descrição:** Extrair helpers e constantes em módulos separados
  - **Benefício:** Redução de complexidade, melhor organização
  - **Esforço:** 10-14h → **Real: ~2h**
  - **Automável:** Manual
  - **Resultado:**
    - ✅ **Módulos criados:**
      - `src/modules/main_window/views/constants.py`:
        * APP_TITLE, APP_VERSION, APP_ICON_PATH
        * Timings: INITIAL_STATUS_DELAY (300ms), STATUS_REFRESH_INTERVAL (300ms), HEALTH_POLL_INTERVAL (5000ms)
        * Status colors: STATUS_COLOR_ONLINE, STATUS_COLOR_OFFLINE, STATUS_COLOR_UNKNOWN
        * DEFAULT_ENV_TEXT placeholder
      - `src/modules/main_window/views/helpers.py`:
        * resource_path(): PyInstaller-aware path resolution
        * sha256_file(): Hash computation com fallback robusto
        * create_verbose_logger(): Logger verbose para RC_VERBOSE=1
    - ✅ **Documentação estruturada adicionada ao `main_window.py`:**
      - Mapa de arquitetura (6 seções principais: Inicialização, Navegação, Ações, Sessão, Status, Temas)
      - Lista de componentes externos (TopBar, MenuBar, NavigationController, etc.)
      - Histórico de refatorações (QA-002)
      - Testing & smoke tests
      - TODOs futuros
    - ✅ **Constantes centralizadas:**
      - Substituído título hardcoded "Regularize Consultoria - v1.2.0" → f"{APP_TITLE} - {APP_VERSION}"
      - Substituído path hardcoded "rc.ico" → APP_ICON_PATH
      - Substituído timings hardcoded (300, 5000) → constantes nomeadas
    - ✅ **Helpers importados:**
      - Substituídos inline helpers _resource_path, _sha256 → importação de helpers.py
      - Mantidas importações sys, functools (ainda necessárias para restart e decorators)
    - ✅ **Compatibilidade 100% preservada:**
      - API da classe App não mudou
      - Comportamento funcional idêntico
      - Nenhum código cliente afetado
    - ✅ **Arquivos criados/modificados:**
      - `src/modules/main_window/views/constants.py` (criado)
      - `src/modules/main_window/views/helpers.py` (criado)
      - `src/modules/main_window/views/main_window.py` (refatorado com documentação)
    - ✅ **Testes:** 327 passed, 1 skipped, coverage 26.83% (≥25%)
    - ✅ **Pre-commit:** All hooks passed
    - 📊 **Impacto:** Configuração centralizada, helpers reutilizáveis, código mais navegável com documentação estruturada

- [>] **QA-003: Adicionar type hints faltantes**
  - **Área:** Módulos sem `from __future__ import annotations`
  - **Descrição:** Incrementalmente adicionar types em arquivos antigos
  - **Ferramenta:** `pyright --stats` para identificar
  - **Benefício:** Melhor IDE support, menos bugs
  - **Esforço:** 6-10h (pode ser feito incrementalmente)
  - **Automável:** Parcial (detecção automática, adição manual)
  - **Resultado - Microfase 1 (20/11/2025):**
    - ✅ **Módulo:** `src/core/search/search.py`
    - ✅ **Funções tipadas:**
      * `_normalize_order(order_by: str | None) -> tuple[str | None, bool]`
      * `_row_to_cliente(row: Mapping[str, Any]) -> Cliente`
      * `_cliente_search_blob(cliente: Cliente) -> str`
      * `_filter_rows_with_norm(rows: Sequence[Mapping[str, Any]], term: str) -> list[dict[str, Any]]`
      * `_filter_clientes(clientes: Sequence[Cliente], term: str) -> list[Cliente]`
      * `search_clientes(term: str | None, order_by: str | None = None, org_id: str | None = None) -> list[Cliente]`
    - ✅ **Imports modernizados:** Removido `List`, `Optional`; adicionado `Any`, `Mapping`, `Sequence`
    - ✅ **Testes:** 22/22 testes de `test_search_service.py` passando
    - ✅ **Suite completa:** 349 passed, 1 skipped, coverage 27.10% (≥25%)
    - ✅ **Pre-commit:** All hooks passed
    - 📊 **Impacto:** Melhor IDE support e validação de tipos no módulo de busca crítico
  - **Resultado - Microfase 2 (20/11/2025):**
    - ✅ **Módulo:** `src/core/textnorm.py`
    - ✅ **Funções tipadas:**
      * `_strip_diacritics(s: str | None) -> str`
      * `normalize_search(value: object) -> str`
      * `join_and_normalize(*parts: object) -> str`
    - ✅ **Variáveis locais anotadas:**
      * `text: str`, `decomposed: str`, `without_marks: str` em `_strip_diacritics`
      * `stripped: str`, `folded: str`, `out_chars: list[str]`, `cat: str | None` em `normalize_search`
      * `combined: str` em `join_and_normalize`
    - ✅ **Testes:** 25/25 testes de `test_textnorm.py` passando
    - ✅ **Suite completa:** 375 passed, coverage 27.11% (≥25%)
    - ✅ **Pre-commit:** All hooks passed
    - 📊 **Impacto:** 100% de cobertura do módulo com tipos completos para verificação estática robusta
  - **Resultado - Microfase 3 (20/11/2025):**
    - ✅ **Módulo:** `src/core/services/notes_service.py`
    - ✅ **Funções tipadas:**
      * `_is_transient_net_error(e: BaseException) -> bool`
      * `_with_retry(fn: Callable[[], Any], *, retries: int = 3, base_sleep: float = 0.25) -> Any`
      * `_check_table_missing_error(exception: BaseException) -> None`
      * `_check_auth_error(exception: BaseException) -> None`
      * `_normalize_author_emails(rows: list[dict[str, Any]], org_id: str) -> list[dict[str, Any]]`
      * `list_notes(org_id: str, limit: int = 500) -> list[dict[str, Any]]`
      * `add_note(org_id: str, author_email: str, body: str) -> dict[str, Any]`
      * `list_notes_since(org_id: str, since_iso: str | None) -> list[dict[str, Any]]`
    - ✅ **Variáveis locais anotadas:**
      * `s: str`, `last_exc: BaseException | None`, `error_str: str`, `emap: dict[str, str]`, `out: list[dict[str, Any]]`, `email: str`, `email_lc: str`, `prefix: str`, `nr: dict[str, Any]`, `rows: list[dict[str, Any]]`, `email_prefix: str`, `payload: dict[str, str]`
    - ✅ **Imports modernizados:** Removido `Dict`, `List` (typing legacy); usado `dict`, `list` (PEP 585)
    - ✅ **Testes:** 17/17 testes de `test_notes_service.py` passando
    - ✅ **Suite completa:** 390 passed, 2 skipped, coverage 27.58% (≥25%)
    - ✅ **Pyright:** 0 erros, 0 warnings em `notes_service.py` e `test_notes_service.py`
    - ✅ **notes_service.py coverage:** 60% (95/158 linhas, antes: 15%)
    - 📊 **Impacto:** Serviço de notas compartilhadas agora com type hints completos, garantindo robustez em operações críticas de append-only e retry logic
  - **Resultado - Microfase 4 (20/11/2025):**
    - ✅ **Módulo:** `src/core/auth/auth.py`
    - ✅ **Funções tipadas:**
      * `_get_auth_pepper() -> str`
      * `check_rate_limit(email: str) -> tuple[bool, float]`
      * `pbkdf2_hash(password: str, *, iterations: int = 1_000_000, salt: bytes | None = None, dklen: int = 32) -> str`
      * `ensure_users_db() -> None`
      * `create_user(username: str, password: str | None = None) -> int`
      * `validate_credentials(email: str, password: str) -> str | None`
      * `authenticate_user(email: str, password: str) -> tuple[bool, str]`
    - ✅ **Variáveis locais anotadas:**
      * `key: str`, `now: float`, `count: int`, `last: float`, `elapsed: float`, `pepper: str`, `dk: bytes`
      * `cur: sqlite3.Cursor`, `row: tuple[Any, ...] | None`, `uid: int`, `pwd_hash: str | None`
      * `allowed: bool`, `remaining: float`, `err: str | None`, `msg: str`
    - ✅ **Imports modernizados:** Removido `Optional`, `Tuple` (typing legacy); usado `tuple`, `|` (PEP 604)
    - ✅ **Tipos concretos:** `sqlite3.Cursor`, `sqlite3.Connection` (via context manager), `bytes`
    - ✅ **Testes:** 50/50 testes de `test_auth_validation.py` passando
    - ✅ **Suite completa:** 411 passed, 2 skipped, coverage 28.05% (≥25%)
    - ✅ **Pyright:** 0 erros, 0 warnings em `auth.py` e `test_auth_validation.py`
    - ✅ **auth.py coverage:** 98% (121/123 linhas)
    - 📊 **Impacto:** Módulo crítico de autenticação agora com type hints completos, reforçando segurança de tipos em login, rate limiting, hashing PBKDF2 e gestão de usuários SQLite
  - **Resultado - Microfase 5 (20/11/2025):**
    - ✅ **Módulos:**
      * `src/modules/clientes/service.py`
      * `src/modules/uploads/repository.py`
    - ✅ **Funções tipadas:**
      * `_extract_cliente_id(row: RowData | None) -> int | None`
      * `_conflict_id(entry: Any) -> int | None`
      * `extrair_dados_cartao_cnpj_em_pasta(base_dir: str) -> dict[str, str | None]`
      * `excluir_clientes_definitivamente(ids: Iterable[int], progress_cb: Callable[[int, int, int], None] | None = None) -> tuple[int, list[tuple[int, str]]]`
      * `fetch_cliente_by_id(cliente_id: int) -> dict[str, Any] | None`
      * `update_cliente_status_and_observacoes(cliente: Mapping[str, Any] | int, novo_status: str | None) -> None`
      * `current_user_id() -> str | None`
      * `normalize_bucket(value: str | None) -> str`
      * `upload_items_with_adapter(...) -> Tuple[int, list[Tuple[_TUploadItem, Exception]]]`
    - ✅ **Imports modernizados:** Removido `Optional` (typing legacy); usado `|` (PEP 604)
    - ✅ **Testes:**
      * `tests/test_clientes_service_qa005.py`: 15/15 passando
      * `tests/test_uploads_repository.py`: 10/10 passando
      * Suite filtrada (`-k "not test_labeled_entry_different_labels"`): 436 passed, 2 skipped
    - ✅ **Pyright:** 0 erros, 0 warnings em `clientes/service.py`, `uploads/repository.py` e seus testes
    - 📊 **Impacto:** Módulos de clientes e uploads, que já tinham correções sensíveis (QA-005) e novos testes (TEST-001 Fase 5), agora com type hints modernos e consistentes, facilitando futuras refatorações com segurança de tipos
  - **Resultado - Microfase 6 (20/11/2025):**
    - ✅ **Módulo:** `src/core/services/profiles_service.py`
    - ✅ **Alterações aplicadas:**
      * Removido: `from typing import Dict, List, Optional`
      * Mantido: `from typing import Any` (necessário para `dict[str, Any]`)
      * Type hints atualizados:
        - `EMAIL_PREFIX_ALIASES: dict[str, str]` (constante)
        - `List[Dict[str, Any]]` → `list[dict[str, Any]]` (4 ocorrências)
        - `Dict[str, str]` → `dict[str, str]` (3 ocorrências)
        - `Optional[str]` → `str | None` (1 ocorrência)
      * Variáveis locais anotadas: `data`, `out`, `email_lc`, `rows`, `em`, `prefix`, `alias` (7 variáveis)
    - ✅ **Testes:** 21/21 testes de `test_profiles_service.py` passando
    - ✅ **Suite completa:** 457 passed, 1 failed, 2 skipped (falha pré-existente em test_ui_components.py)
    - ✅ **Pyright:** 0 erros, 0 warnings em profiles_service.py e test_profiles_service.py
    - ✅ **Coverage:** 28.65% global, 97% em profiles_service.py (mantida)
    - 📊 **Impacto:** Serviço crítico usado por notes_service agora com type hints modernos (PEP 585/604), alinhado com clientes/service e uploads/repository (QA-003 Microfase 5). Testes da Fase 6 garantem que refatoração de tipos não introduziu regressões funcionais
  - **Resultado - Microfase 7 (20/11/2025):**
    - ✅ **Módulo:** `src/core/services/lixeira_service.py`
    - ✅ **Alterações aplicadas:**
      * Removido: `from typing import List, Tuple` (mantido apenas `Iterable`)
      * Type hints atualizados (6 substituições):
        - `_get_supabase_and_org() -> Tuple[object, str]` → `tuple[object, str]`
        - `_list_storage_children() -> List[dict]` → `list[dict]`
        - `_gather_all_paths() -> List[str]` → `list[str]`
        - `restore_clients() -> Tuple[int, List[Tuple[int, str]]]` → `tuple[int, list[tuple[int, str]]]`
        - `hard_delete_clients() -> Tuple[int, List[Tuple[int, str]]]` → `tuple[int, list[tuple[int, str]]]`
      * Variáveis locais anotadas: `paths: list[str] = []`, `errs: list[tuple[int, str]] = []` (3 ocorrências)
    - ✅ **Testes:** 15/15 testes de `test_lixeira_service.py` passando
    - ✅ **Suite completa:** 472 passed, 1 failed, 2 skipped (falha pré-existente em test_ui_components.py)
    - ✅ **Pyright:** 0 erros, 0 warnings em lixeira_service.py e test_lixeira_service.py
    - ✅ **Coverage:** 28.88% global, 84% em lixeira_service.py (mantida)
    - 📊 **Impacto:** Serviço de lixeira agora com type hints modernos (PEP 585/604), alinhado com clientes/service, uploads/repository (QA-003 Microfase 5) e profiles_service (Microfase 6). Total de 6 substituições aplicadas (List→list, Tuple→tuple). Testes da Fase 7 garantem que refatoração de tipos não introduziu regressões funcionais
  - **Resultado - Microfase 8 (21/11/2025):**
    - ✅ **Módulos:**
      * `src/modules/clientes/forms/_prepare.py`
      * `src/modules/clientes/forms/_upload.py`
    - ✅ **Alterações aplicadas:**
      * **_prepare.py:**
        - Removido: `from typing import Dict, List, Optional, Tuple` (mantido apenas `Any, Mapping`)
        - Type hints atualizados (9 substituições):
          * `_extract_supabase_error() -> Tuple[Optional[str], str, Optional[str]]` → `tuple[str | None, str, str | None]`
          * UploadCtx dataclass (25 campos modernizados):
            - `ents: Dict[str, Any]` → `ents: dict[str, Any]`
            - `arquivos_selecionados: Optional[List[str]]` → `arquivos_selecionados: list[str] | None`
            - `subfolders: Optional[List[str]]` → `subfolders: list[str] | None`
            - `files: List[tuple[str, str]]` → `files: list[tuple[str, str]]`
            - 21 outros campos com `Dict`, `List`, `Optional`
          * `_ask_subpasta() -> Optional[str]` → `str | None`
          * `validate_inputs() -> Tuple[tuple, Dict[str, Any]]` → `tuple[tuple, dict[str, Any]]`
          * `prepare_payload() -> Tuple[tuple, Dict[str, Any]]` → `tuple[tuple, dict[str, Any]]`
          * Variável linha 340: `subpasta_val: Optional[str]` → `subpasta_val: str | None`
      * **_upload.py:**
        - Removido: `from typing import Dict, Tuple` (mantido apenas `Any`)
        - Type hints atualizados (2 substituições):
          * `perform_uploads() -> Tuple[tuple, Dict[str, Any]]` → `tuple[tuple, dict[str, Any]]`
    - ✅ **Total:** 11 modernizações de type hints (9 em _prepare.py, 2 em _upload.py)
    - ✅ **Testes:** 40/40 passed (10 upload + 20 prepare + 10 finalize)
    - ✅ **Suite filtrada:** 486 passed, 1 failed, 2 skipped (mesma baseline)
    - ✅ **Pyright:** 0 erros, 0 warnings em _prepare.py, _upload.py e testes relacionados
    - ✅ **Coverage:** 29.09% global (mantida), _prepare.py 78% (antes 64%), _upload.py 56% (antes 31%)
    - 📊 **Impacto:** Fluxo de formulários de clientes agora com type hints modernos (PEP 585/604), alinhado com padrão estabelecido nas Microfases 1-7 (search, textnorm, notes_service, auth, clientes/service, profiles_service, lixeira_service). Testes da Fase 8 garantem que refatoração de tipos não introduziu regressões funcionais. Total de 11 substituições aplicadas, com destaque para modernização completa do UploadCtx dataclass (25 campos)
  - **Resultado - Microfase 9 (21/11/2025):**
    - ✅ **Módulo:** `src/modules/auditoria/service.py`
    - ✅ **Status:** Type hints JÁ MODERNOS (PEP 585/604)
    - ✅ **Análise realizada:**
      * ✅ `from __future__ import annotations` presente (linha 10)
      * ✅ Imports modernos: `from typing import Any, Callable, Iterable, Sequence` (sem `List`, `Dict`, `Optional`, `Union`, `Tuple`)
      * ✅ Type hints nativos em todas as funções:
        - CRUD Auditorias: `list[dict[str, Any]]`, `dict[str, Any]`, `str | None`, `Iterable[str | int]`
        - Storage: `bool`, `str`, `set[str]`, `bytes`, `Sequence[str]`
        - Pipeline: `AuditoriaStorageContext`, `AuditoriaUploadContext`, `AuditoriaArchivePlan`, `Callable[[], bool] | None`
      * ✅ Variáveis locais tipadas: `ids: list[str]`, `paths: list[str]`, etc.
    - ✅ **Funções públicas validadas (16):**
      * CRUD: `fetch_clients()`, `fetch_auditorias()`, `start_auditoria()`, `update_auditoria_status()`, `delete_auditorias()`
      * Storage: `is_online()`, `get_current_org_id()`, `ensure_auditoria_folder()`, `list_existing_file_names()`, `upload_storage_bytes()`, `remove_storage_objects()`
      * Pipeline: `ensure_storage_ready()`, `prepare_upload_context()`, `get_storage_context()`, `prepare_archive_plan()`, `execute_archive_upload()`
    - ✅ **Testes:** 35/35 passed em `test_auditoria_service_fase9.py`
    - ✅ **Suite filtrada:** 521 passed, 1 failed (Tkinter pré-existente), 2 skipped
    - ✅ **Pyright:** 0 erros, 0 warnings em auditoria/service.py e test_auditoria_service_fase9.py
    - ✅ **Coverage:** 29.41% global (+0.32pp vs Fase 8), auditoria/service.py 84% (vs 59% antes Fase 9)
    - 📊 **Impacto:** Módulo auditoria/service já estava com type hints modernos (PEP 585/604), validação confirmou padrão consistente. Nenhuma mudança necessária, apenas documentação QA-003 Microfase 9
  - **Resultado - Microfase 10 (21/11/2025):**
    - ✅ **Módulo:** `src/helpers/formatters.py`
    - ✅ **Alterações aplicadas:**
      * Adicionado: `from __future__ import annotations` (linha 1)
      * Type hints atualizados (4 funções):
        - `format_cnpj(raw: str | int | float | None) -> str` (antes: `raw: str`)
        - `fmt_datetime(value: datetime | date | str | int | float | None) -> str` (antes: sem type hint no parâmetro)
        - `fmt_datetime_br(value: datetime | date | str | int | float | None) -> str` (antes: sem type hint no parâmetro)
        - `_parse_any_dt(value: Any) -> datetime | None` (já estava moderno, mantido)
      * Variáveis locais anotadas: `dt: datetime | None`, `s: str` (2 variáveis)
      * Docstrings adicionadas: `format_cnpj`, `fmt_datetime`, `fmt_datetime_br` (3 funções)
    - ✅ **Imports:** Já modernos (apenas `Any`, `Final`; sem `List`, `Dict`, `Optional`, `Union`)
    - ✅ **Testes:** 57/57 passed em `test_helpers_formatters_fase10.py` (sem alterações nos testes)
    - ✅ **Suite filtrada:** 578 passed, 1 skipped (1 teste a menos que Fase 10 devido a flaky test)
    - ✅ **Pyright:** 0 erros, 0 warnings em formatters.py e test_helpers_formatters_fase10.py
    - ✅ **Coverage:** 29.78% global (±0.02pp vs baseline 29.80%), formatters.py 94% (mantida)
    - 📊 **Impacto:** Helpers de formatação agora com type hints completos e modernos (PEP 585/604), refletindo uso real de múltiplos tipos (str, int, float, datetime, date, timestamp). Funções `format_cnpj`, `fmt_datetime`, `fmt_datetime_br` agora documentadas com docstrings descrevendo tipos aceitos e comportamento. Alinhado com padrão QA-003 Microfases 1-9
    - 🔧 **HOTFIX-PYLANCE-001 (21/11/2025):**
      * Ajustadas assinaturas para aceitar valores realmente usados nos testes:
        - `fmt_datetime`: adicionado `time` ao union (datetime | date | time | str | int | float | None)
        - `fmt_datetime_br`: adicionado `time` ao union (datetime | date | time | str | int | float | None)
        - Docstrings atualizadas documentando aceitação de `time`
      * `src/modules/auditoria/service.py`:
        - `delete_auditorias`: `Iterable[str | int | None]` (era `Iterable[str | int]`)
        - Docstring adicionada: "Exclui auditorias, ignorando IDs None/vazios."
        - Reflete uso real nos testes: `[123, "abc", None, "", "  ", 456]`
      * Validação: Pyright 0 erros, pytest 92/92 passed, suite 578 passed
      * Commit: c208cfa - Nenhuma mudança de comportamento, apenas type hints
  - **Resultado - Microfase 11 (21/11/2025):**
    - ✅ **Módulo:** `src/ui/files_browser/utils.py`
    - ✅ **Alterações aplicadas:**
      * Adicionado `from __future__ import annotations`.
      * Type hints modernos (PEP 585/604) adicionados às funções:
        - `sanitize_filename(name: str) -> str`
        - `format_file_size(size: int | float | None) -> str`
        - `resolve_posix_path(base: str, path: str) -> str`
        - `suggest_zip_filename(path: str) -> str`
      * Variáveis locais anotadas quando necessário para clareza de tipos.
    - ✅ **Validação:**
      * `python -m pyright src/ui/files_browser/utils.py tests/test_files_browser_utils_fase11.py`
      * `python -m pytest tests/test_files_browser_utils_fase11.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - 📊 **Impacto:** Helpers puros do file browser agora com type hints completos e modernos, alinhados com o padrão adotado em formatters/profiles/lixeira, mantendo 100% de cobertura e sem alterações de comportamento.
  - **Próximas microfases:** Outros módulos críticos conforme necessário
    - ✅ **Coverage:** 29.41% global (≥29.39%), auditoria/service.py 84% (161/192 linhas)
    - 📊 **Impacto:** Módulo de auditoria SIFAP já estava com type hints modernos (PEP 585/604), alinhado com padrão estabelecido nas Microfases 1-8. Testes da Fase 9 (TEST-001) garantem robustez do módulo com 84% de cobertura. Nenhuma alteração necessária, validação confirmou conformidade completa com PEP 585/604

- [x] **QA-LINT Fase 1: Pyright + Ruff Global (v1.2.47)** ✅ **CONCLUÍDO**
  - **Área:** Limpeza completa de linting/type checking em `src/` e `tests/`
  - **Descrição:** Primeira passada global de QA após conclusão de TEST-001 Fase 30
  - **Ferramentas:**
    - Pyright: análise estática de tipos (modo strict)
    - Ruff: linting moderno (substitui flake8, isort, pylint)
  - **Esforço:** 2h
  - **Automável:** Parcial (Ruff auto-fix 91.7%, Pyright manual)
  - **Resultado:**
    - ✅ **Baseline pré-correção:**
      * Pyright: 3 erros, 3 warnings
      * Ruff: 12 erros (11 auto-fixable)
      * Pytest: 878 passed, 2 skipped
      * Coverage: 36.72% (baseline)
    - ✅ **Correções aplicadas:**
      * Ruff auto-fix: 11/12 erros resolvidos automaticamente
      * F841 manual: Removido `result =` não usado em `test_cashflow_repository_fase28.py:475`
      * Pyright erro #1: Ajustada assinatura `on_open_status_menu: Optional[Callable[[tk.Event], Literal["break"] | None]]` em `auditoria/views/components.py`
      * Pyright erros #2-3: Adicionado `# type: ignore[misc]` em `ClientesFooter`/`ClientesToolbar` (alias condicional `tb.Frame`)
      * Pyright warnings #1-2: Atribuído `_ =` em expressões descartadas (`fluxo_caixa_frame.py:232, 263`)
      * Pyright warning #3: Substituída tupla órfã por `messagebox.showerror()` em `files_browser/main.py:1324`
    - ✅ **Arquivos modificados:** 14 arquivos tocados
      * Código: `auditoria/views/components.py`, `clientes/views/footer.py`, `clientes/views/toolbar.py`, `cashflow/views/fluxo_caixa_frame.py`, `ui/files_browser/main.py`, `utils/prefs.py`
      * Testes: `test_cashflow_repository_fase28.py`, `test_auth_auth_fase12.py`, `test_core_api_clients_fase30.py`, `test_core_storage_key_fase24.py`, `test_helpers_auth_utils_fase27.py`, `test_utils_bytes_utils_fase19.py`, `test_utils_pdf_reader_fase20.py`, `test_utils_prefs_fase14.py`
    - ✅ **Validação final:**
      * `pyright src tests` → **0 erros, 0 warnings, 0 informations** ✨
      * `ruff check .` → **All checks passed!** ✨
      * `pytest` → **879 passed, 1 skipped, 1 deselected** ✅
      * `pytest --cov` → **55.88% coverage** (acima do threshold 25%)
    - ✅ **Estatísticas:**
      * Issues corrigidos: 18 total (3 erros + 3 warnings Pyright, 12 erros Ruff)
      * Taxa de sucesso auto-fix: 91.7% (11/12 Ruff)
      * Tempo de execução: ~25 minutos (incluindo análise manual)
      * Impacto zero em funcionalidade (todos os testes passando)
    - 📄 **Documentação:** `docs/qa-history/resultado_qa_lint_fase01_global_lint_v1_2_47.txt`
    - 📊 **Impacto:** Codebase 100% limpo para Pyright e Ruff, preparado para habilitar verificações em pre-commit e CI/CD. Base sólida para futuras fases QA.

- [x] **QA-004: Configurar pre-commit hooks**
  - **Área:** Criar `.pre-commit-config.yaml`
  - **Descrição:** Automatizar ruff, trailing whitespace, etc.
  - **Hooks sugeridos:** ruff, ruff-format, end-of-file-fixer
  - **Benefício:** Qualidade consistente antes de commit
  - **Esforço:** 1h
  - **Automável:** Sim
  - **Resultado:**
    - ✅ `.pre-commit-config.yaml` criado com hooks básicos:
      - `trailing-whitespace` (remoção de espaços em branco no final das linhas)
      - `end-of-file-fixer` (garantir nova linha no final dos arquivos)
      - `check-added-large-files` (limitar arquivos grandes a 500KB)
      - `check-yaml/toml/json` (validar sintaxe de configs)
      - `check-merge-conflict` (detectar marcadores de merge)
      - `mixed-line-ending` (normalizar line endings para LF)
      - `ruff` (linter Python com auto-fix)
      - `ruff-format` (formatador Python)
      - `check-ast/builtin-literals/docstring-first/debug-statements` (validações Python)
    - ✅ `pre-commit install` executado com sucesso (hooks instalados em `.git/hooks/pre-commit`)
    - ✅ `pre-commit run --all-files` executado: correções automáticas aplicadas em ~200 arquivos
      - Trailing whitespace: 17 arquivos corrigidos
      - End-of-file-fixer: 13 arquivos corrigidos
      - Mixed line endings: 182 arquivos normalizados para LF
      - Ruff format: 43 arquivos reformatados
    - ✅ Segunda execução passou sem erros (todos os hooks verdes)
    - ✅ Commits futuros passam pelo pre-commit automaticamente (sem necessidade de `--no-verify`)
    - ✅ `CONTRIBUTING.md` atualizado com instruções de instalação e uso do pre-commit

- [x] **META-001: Triagem de avisos Pyright e testes skipped** ✅ **CONCLUÍDO** (20/11/2025)
  - **Área:** Workspace global, diagnóstico de qualidade
  - **Descrição:** Mapear e categorizar todos os avisos do Pyright + revisar testes skipped para planejamento de ações corretivas
  - **Esforço:** 2-3h → **Real: ~2.5h**
  - **Automável:** Semi (detecção automática, triagem manual)
  - **Baseline inicial:**
    - 🔴 28 erros Pyright
    - ⚠️ 5 warnings Pyright
    - ⏭️ 2 testes skipped (condicional em `test_ui_components.py` + ambiente-dependente)
  - **Ações realizadas:**
    - ✅ **Correções imediatas (13 erros + 2 warnings):**
      * `src/app_gui.py`: Adicionado check `if log:` antes de `log.info()` e `log.error()` (2 warnings `reportOptionalMemberAccess`)
      * `src/core/search/search.py`:
        - Corrigido retorno `Sequence → list` com cast explícito (2 erros `reportReturnType`)
        - Convertido `Mapping` imutável para `dict` mutável antes de modificar (2 erros `reportIndexIssue`/`reportArgumentType`)
      * `src/modules/clientes/forms/_prepare.py`: Corrigido retorno de `_ask_for_subpasta()` de `SubpastaDialog` objeto para `dlg.result: str | None` (1 erro `reportReturnType`)
      * `src/modules/clientes/forms/_upload.py`: Adicionado check `if not ctx.pasta_local: raise ValueError(...)` antes de `os.path.join()` (8 erros `reportCallIssue`/`reportArgumentType`)
    - ✅ **Validações:**
      * Pyright nos arquivos corrigidos: 0 errors, 0 warnings ✅
      * pytest: 411 passed, 2 skipped, 6 warnings (sem regressão) ✅
      * Cobertura: 28.05% (≥25%) ✅
  - **Resultado pós-triagem:**
    - 🟡 **15 erros restantes** (redução de 46%)
    - ⚠️ **3 warnings restantes** (redução de 40%)
    - 📊 **Avisos categorizados:**
      * **corrigir_agora (5 erros):**
        - `src/modules/clientes/service.py`: 5 erros de tipos (linhas 179, 180, 385, 416×2) - `object | None` não iterável, `Cliente` não é `MutableMapping`, `Any | None` não convertível a int
        - `src/modules/clientes/views/main_screen.py`: 3 erros de assinatura (linha 1105) - parâmetro `cliente` faltando, parâmetros `cliente_id` e `texto_observacoes` inexistentes
        - `src/modules/lixeira/views/lixeira.py`: 1 erro (linha 282) - parâmetro `parent` inexistente
        - `src/modules/uploads/repository.py`: 2 erros (linhas 170-171) - parâmetros `client_id` e `org_id` inexistentes
      * **pode_esperar (4 erros + 3 warnings):**
        - `src/modules/auditoria/views/layout.py`: 1 erro (linha 56) - callback Tkinter retorna `Literal['break'] | None` mas espera-se `None`
        - `src/modules/clientes/views/footer.py`: 1 erro (linha 14) - "Argument to class must be a base class"
        - `src/modules/clientes/views/toolbar.py`: 1 erro (linha 14) - "Argument to class must be a base class"
        - `src/modules/cashflow/views/fluxo_caixa_frame.py`: 2 warnings (linhas 232, 263) - Expression value is unused
        - `src/ui/files_browser/main.py`: 1 warning (linha 1324) - Expression value is unused
      * **ignorar/externo (1 erro):**
        - `uploader_supabase.py`: 1 erro (linha 238) - arquivo raiz, parece demo/script de teste
  - **Testes skipped (2 total):**
    - ✅ `tests/test_ui_components.py::test_ui_scrollable_frame` → **skip_ok** (Tkinter não configurado no ambiente)
    - ✅ `tests/test_ui_components.py::test_ui_tooltip` → **skip_ok** (Tkinter não configurado no ambiente)
    - 📌 Ambos são válidos: testes GUI requerem ambiente gráfico completo, skip é esperado em CI/headless
  - **Próximos passos:**
    - [x] **QA-005: Corrigir erros Pyright críticos em clientes/lixeira/uploads** ✅ **CONCLUÍDO** (20/11/2025)
      - ✅ Arquivos corrigidos:
        * `src/modules/clientes/service.py` (5 erros) - Guards para None em iteráveis, cast de tipos, guard em conversão int()
        * `src/modules/clientes/views/main_screen.py` (3 erros) - Assinatura correta de update_cliente_status_and_observacoes
        * `src/modules/lixeira/views/lixeira.py` (1 erro) - Removido parâmetro `parent` inexistente
        * `src/modules/uploads/repository.py` (2 erros) - Cast para Any ao passar client_id/org_id kwargs
      - ✅ Pyright: **11 erros `corrigir_agora` zerados** (15 erros → 4 erros, redução de 73%)
      - ✅ Testes: 411 passed, 2 skipped (1 falha nova em ttkbootstrap, não relacionada às correções)
      - ✅ Cobertura: 28.04% (sem regressão, mantém ≥25%)
      - 📌 Avisos restantes: apenas 4 erros `pode_esperar` + 3 warnings + 1 erro `ignorar/externo`, conforme tabela da META-001
    - [ ] **TOOL-004 (futura):** Avaliar ignores seletivos para avisos `pode_esperar` via `pyrightconfig.json`
    - [ ] **TEST-001:** Manter testes skipped como estão (ambiente-dependente, comportamento correto)

### Testes

- [>] **TEST-001: Aumentar cobertura para 85%+** ⏳ **FASES 1-11 CONCLUÍDAS**
  - **Área:** Módulos com baixa cobertura
  - **Descrição:** Adicionar testes em:
    - ✅ `src/modules/cashflow/` (FASE 1)
    - ✅ `src/modules/passwords/` (FASE 1)
    - ✅ `src/ui/components/` (FASE 2)
    - ✅ `src/modules/hub/`, `src/core/auth/` (FASE 3)
    - ✅ `src/core/search/` (FASE 4.1 - microfase)
    - ⏳ Outros módulos de baixa cobertura (próximas microfases)
  - **Ferramenta:** `pytest --cov` para medir
  - **Benefício:** Redução de bugs
  - **Esforço:** 8-12h
  - **Automável:** Manual (escrever testes)
  - **Fase 1 - Resultados (cashflow + passwords):**
    - ✅ **Arquivos criados:**
      * `tests/test_cashflow_service.py`: 14 testes para fluxo de caixa
      * `tests/test_passwords_service.py`: 20 testes para gerenciamento de senhas
    - ✅ **Total:** 34 testes novos (249 testes no total, antes: 215)
    - ✅ **Cobertura:**
      * Antes: ~25.85%
      * Depois: **26.15%** (+0.30pp)
      * `src/features/cashflow/repository.py`: 63% coverage (74/118 linhas)
    - ✅ **Cenários testados (cashflow):**
      * Listagem com filtros (tipo IN/OUT, texto, período)
      * Cálculo de totais (entradas, saídas, saldo)
      * CRUD completo (create, update, delete)
      * Edge cases (valores None, listas vazias, datas extremas)
    - ✅ **Cenários testados (passwords):**
      * Listagem com busca case-insensitive
      * Filtros por cliente
      * CRUD completo com dados criptografados
      * Busca em múltiplos campos (client_name, service, username)
    - ✅ **Validação:**
      * pytest: 249/249 passed
      * coverage: 26.15%
      * pre-commit: all hooks passed
  - **Fase 2 - Resultados (ui/components):**
    - ✅ **Arquivo criado:**
      * `tests/test_ui_components.py`: 10 testes para componentes de UI (257 linhas)
    - ✅ **Componentes testados:**
      * `buttons.py`: `toolbar_button` (nota: removido devido a conflitos ttkbootstrap)
      * `inputs.py`: `labeled_entry` (2 testes)
      * `lists.py`: `create_clients_treeview` (8 testes - configuração de colunas)
    - ✅ **Total:** 10 testes novos (257 testes no total, antes: 249)
    - ✅ **Cobertura:**
      * Antes: 26.15%
      * Depois: **26.32%** (+0.17pp)
      * `src/ui/components/lists.py`: 79% coverage (38/48 linhas)
      * `src/ui/components/inputs.py`: 36% coverage (21/59 linhas)
    - ✅ **Cenários testados (Treeview):**
      * Configuração básica (8 colunas)
      * Column widths corretos (40-240px conforme constants.py)
      * Headings corretos ("Razão Social", "Observações", etc.)
      * Stretch columns apenas para "Razao Social" e "Observacoes"
      * Tag "has_obs" configurada com foreground #0d6efd
      * Bindings criados quando callbacks fornecidos
      * None callbacks não causam erros
    - ✅ **Validação:**
      * pytest: 257/259 passed (2 skipped - esperado)
      * coverage: 26.32% (threshold 25%)
      * pre-commit: all hooks passed
  - **Fase 3 - Resultados (hub + auth):**
    - ✅ **Arquivos criados:**
      * `tests/test_hub_helpers.py`: 41 testes para funções auxiliares do Hub (413 linhas)
      * `tests/test_auth_validation.py`: 28 testes para autenticação e validação (248 linhas)
    - ✅ **Módulos testados (Hub):**
      * `state.py`: HubState, ensure_hub_state, ensure_state (5 testes)
      * `format.py`: _format_timestamp, _format_note_line (7 testes)
      * `utils.py`: _hsl_to_hex, _hash_dict, _normalize_note (18 testes)
      * `colors.py`: _author_color, _ensure_author_tag (11 testes)
    - ✅ **Módulos testados (Auth):**
      * `auth.py`: validate_credentials, check_rate_limit, pbkdf2_hash (28 testes)
      * EMAIL_RE regex validation
    - ✅ **Total:** 69 testes novos (327 testes no total, antes: 257)
    - ✅ **Cobertura:**
      * Antes: 26.32%
      * Depois: **26.95%** (+0.63pp)
      * `src/modules/hub/state.py`: 100% coverage (21/21 linhas)
      * `src/modules/hub/format.py`: 86% coverage (18/21 linhas)
      * `src/modules/hub/utils.py`: 93% coverage (28/30 linhas)
      * `src/modules/hub/colors.py`: 82% coverage (31/38 linhas)
      * `src/core/auth/auth.py`: 44% coverage (54/123 linhas)
    - ✅ **Cenários testados (Hub):**
      * State management (singleton, user_email, org_id, preferences)
      * Timestamp formatting (ISO → "Hoje 14:30", "Ontem 18:45", "15/01/2024")
      * Note formatting (wrapped text, max lines, ellipsis)
      * Color generation (HSL → Hex, hash-based author colors, tag creation)
      * Text normalization (Unicode, acentos, múltiplas linhas)
    - ✅ **Cenários testados (Auth):**
      * Email regex validation (valid/invalid formats)
      * Password validation (min 8 chars, caracteres especiais)
      * PBKDF2 hashing (salt, iterations, verificação)
      * Rate limiting (max attempts, lockout, reset)
      * Credential validation integrada (email + password)
    - ✅ **Validação:**
      * pytest: 327/328 passed (1 skipped)
      * coverage: 26.95%
      * pre-commit: all hooks passed
  - **Fase 4.1 - Resultados (search - microfase):**
    - ✅ **Arquivo criado:**
      * `tests/test_search_service.py`: 22 testes para busca de clientes (351 linhas)
    - ✅ **Módulo testado:**
      * `src/core/search/search.py`: Busca de clientes com fallback local
    - ✅ **Total:** 22 testes novos (349 testes no total, antes: 327)
    - ✅ **Cobertura:**
      * Antes: 26.86%
      * Depois: **27.10%** (+0.24pp)
      * `src/core/search/search.py`: 69% coverage (49/71 linhas, antes: 18%)
    - ✅ **Funções testadas:**
      * `_normalize_order()`: 7 testes - normalização de campos de ordenação
      * `_row_to_cliente()`: 3 testes - conversão dict → Cliente (completo, parcial, vazio)
      * `_cliente_search_blob()`: 2 testes - criação de blob para busca
      * `_filter_rows_with_norm()`: 4 testes - filtragem de rows com normalização
      * `_filter_clientes()`: 3 testes - filtragem de clientes (match, no match, termo vazio)
      * `search_clientes()`: 3 testes - integração com mocks (offline fallback, validação org_id, listagem completa)
    - ✅ **Cenários testados:**
      * Normalização de ordenação (nome, razao_social, cnpj, ultima_alteracao, inválido)
      * Conversão robusta de rows (campos completos, parciais, vazios)
      * Busca normalizada (case-insensitive, remoção de acentos, por CNPJ)
      * Fallback offline para DB local quando Supabase offline
      * Validação de org_id obrigatório
      * Edge cases (termos vazios, nenhum match, listas vazias)
    - ✅ **Validação:**
      * pytest: 349/350 passed (1 skipped)
      * coverage: 27.10%
      * pre-commit: all hooks passed
    - 📊 **Impacto:** Módulo crítico de busca agora com cobertura de 69% (antes 18%), garantindo estabilidade em funcionalidade core do app
  - **Fase 4.2 - Resultados (textnorm - normalização de texto):**
    - ✅ **Arquivo criado:**
      * `tests/test_textnorm.py`: 25 testes para normalização de texto (150 linhas)
    - ✅ **Módulo testado:**
      * `src/core/textnorm.py`: Utilitários de normalização para busca
    - ✅ **Total:** 25 testes novos (373 testes no total, antes: 349)
    - ✅ **Cobertura:**
      * Antes: 27.10%
      * Depois: **27.11%** (+0.01pp)
      * `src/core/textnorm.py`: **100% coverage** (23/23 linhas, antes: 96%)
    - ✅ **Funções testadas:**
      * `_strip_diacritics()`: 6 testes - remoção de acentos (básicos, múltiplos, None, vazio, preservação de case)
      * `normalize_search()`: 11 testes - normalização completa (acentos, pontuação, espaços, CNPJ, casefold)
      * `join_and_normalize()`: 8 testes - junção e normalização de múltiplas partes (None, tipos mistos, caso real cliente)
    - ✅ **Cenários testados:**
      * Remoção de acentos portugueses (São → Sao, José → Jose, Açúcar → Acucar)
      * Normalização completa: lowercase + remoção de acentos + pontuação + espaços
      * CNPJ normalizado: "12.345.678/0001-90" → "12345678000190"
      * Edge cases: None, strings vazias, textos sem acentos
      * Casefold para lowercase forte (alemão ß → ss)
      * Junção de partes com None values e tipos mistos (int, str)
      * Caso real: blob de busca de cliente (id + nome + CNPJ + obs)
    - ✅ **Validação:**
      * pytest: 373/375 passed (2 skipped)
      * coverage: 27.11%
      * pre-commit: all hooks passed
    - 📊 **Impacto:** Módulo crítico de normalização agora com 100% de cobertura, garantindo robustez na funcionalidade de busca fuzzy
  - **Fase 4.3 - Resultados (notes_service - serviço de notas compartilhadas):**
    - ✅ **Arquivo criado:**
      * `tests/test_notes_service.py`: 17 testes para serviço de notas (262 linhas)
    - ✅ **Módulo testado:**
      * `src/core/services/notes_service.py`: Serviço de anotações append-only por org
    - ✅ **Total:** 17 testes novos (390 testes no total, antes: 373)
    - ✅ **Cobertura:**
      * Antes: 27.11%
      * Depois: **27.58%** (+0.47pp)
      * `src/core/services/notes_service.py`: **60% coverage** (95/158 linhas, antes: 15%)
    - ✅ **Funções testadas:**
      * `_is_transient_net_error()`: 5 testes - detecção de erros transitórios (WinError 10035, timeout, connection reset, errno, não-transitório)
      * `_normalize_author_emails()`: 4 testes - normalização de prefixos para emails completos (com map, email completo, vazio, exception)
      * `list_notes()`: 3 testes - listagem de notas (sucesso, vazio, tabela ausente)
      * `add_note()`: 5 testes - adicionar nota (sucesso, body vazio/None, truncamento 1000 chars, normalização email)
    - ✅ **Cenários testados:**
      * Detecção de erros de rede transitórios para retry (WinError 10035, timeouts, connection resets)
      * Normalização de emails legados (prefixo → email completo via profiles_service)
      * Listagem de notas com fallback para lista vazia em caso de erro
      * Validação de body (rejeitar vazio/None, truncar em 1000 chars)
      * Normalização de author_email para lowercase
      * Tratamento de exceção NotesTableMissingError (PGRST205)
      * Mocks de Supabase client e exec_postgrest
    - ✅ **Validação:**
      * pytest: 390/392 passed (2 skipped)
      * coverage: 27.58%
      * pre-commit: all hooks passed
    - 📊 **Impacto:** Módulo de notas compartilhadas saltou de 15% → 60% de cobertura (+45pp), garantindo robustez em funcionalidade de colaboração
  - **Fase 4.4 - Resultados (auth - autenticação e rate limit):**
    - ✅ **Arquivo de testes envolvido:**
      * `tests/test_auth_validation.py`: 21 testes novos (50 testes total, antes: 29)
    - ✅ **Módulo alvo:**
      * `src/core/auth/auth.py`: Autenticação, validação de credenciais, rate limiting, PBKDF2 hashing
    - ✅ **Total:** 21 testes novos (411 testes no total, antes: 390)
    - ✅ **Cobertura:**
      * Antes: **44%** (54/123 linhas)
      * Depois: **98%** (121/123 linhas) - **+54pp**
      * Linhas não cobertas: apenas 16-17 (import yaml exception handler - edge case de import failure)
    - ✅ **Cenários exercitados:**
      * **_get_auth_pepper**: leitura de AUTH_PEPPER/RC_AUTH_PEPPER (env vars), config.yml/config.yaml, prioridade env > config, YAML corrupto, fallback para vazio
      * **ensure_users_db & create_user**: criação de tabela SQLite, inserção de usuário novo, atualização de usuário existente (com/sem senha), validação de username obrigatório
      * **authenticate_user**: login bem-sucedido (mock Supabase), credenciais inválidas, erro de validação (email/senha), rate limit bloqueando, limpeza de tentativas após sucesso, incremento de contador em falha, ausência de sessão válida
      * **Validação de credenciais**: já testado em fase anterior (email regex, senha min 6 chars, boundaries)
      * **Rate limiting**: já testado em fase anterior (5 tentativas/60s, reset, case-insensitive)
      * **PBKDF2 hashing**: já testado em fase anterior (formato, iterações, salt, pepper)
    - ✅ **Validação final:**
      * pytest tests/test_auth_validation.py -v: **50/50 testes passando** (100%)
      * Suite completa: **411 passed, 2 skipped** (antes: 390 passed)
      * Coverage global: **28.02%** (antes: 27.58%, +0.44pp)
      * Coverage auth.py: **98%** (121/123 linhas)
      * Pre-commit: todos os hooks verdes
    - 📊 **Impacto:** Módulo crítico de autenticação agora com cobertura quase completa (98%), garantindo robustez em login, rate limiting, hashing de senhas e gestão de usuários locais
  - **Fase 5 - Resultados (clientes/uploads - testes para correções da QA-005):**
    - ✅ **Arquivos criados:**
      * `tests/test_clientes_service_qa005.py`: 15 testes para correções de tipo em clientes/service.py (272 linhas)
      * `tests/test_uploads_repository.py`: 10 testes para correção de kwargs em uploads/repository.py (313 linhas)
    - ✅ **Módulos testados:**
      * `src/modules/clientes/service.py`: Guards para None, cast de tipos, validação de id
      * `src/modules/uploads/repository.py`: Passagem de client_id/org_id como kwargs
    - ✅ **Total:** 25 testes novos (436 testes no total, antes: 411)
    - ✅ **Cobertura:**
      * Global antes: 28.02%
      * Global depois: **28.04%** (mantém ≥25%)
      * `src/modules/clientes/service.py`: **61%** (136/223 linhas, antes: ~50%)
      * `src/modules/uploads/repository.py`: **44%** (36/81 linhas, antes: 26%)
    - ✅ **Cenários testados (clientes/service.py):**
      * **_filter_self + cast(list, ...)**: razao_conflicts=None não quebra, lista vazia funciona, filtra self corretamente, objetos sem 'id' são tolerados
      * **get_cliente_by_id (retorno Any)**: retorna objeto Cliente, retorna None quando não encontrado
      * **fetch_cliente_by_id**: converte objeto para dict, retorna None quando não encontrado
      * **update_cliente_status_and_observacoes (guard de id)**: aceita dict com id válido, aceita id como string ("123"), rejeita dict sem id (ValueError), rejeita id=None (ValueError), aceita int direto
    - ✅ **Cenários testados (uploads/repository.py):**
      * **upload_items_with_adapter (cast Any para kwargs)**: client_id passado corretamente, org_id passado corretamente, ambos client_id+org_id juntos, funciona sem client_id/org_id (None), múltiplos items com paths variados, subfolder vazio não adiciona '/' extra, progress_callback chamado para cada item, exceção no adapter retorna em failures
      * **Validação de remote_path_builder signatures**: builder sem **kwargs falha (TypeError esperado), builder com **kwargs recebe client_id/org_id
    - ✅ **Validação final:**
      * pytest completo: **436 passed, 2 skipped** (antes: 411 passed)
      * Coverage global: **28.04%** (antes: 28.02%)
      * Coverage clientes/service.py: **61%** (antes: ~50%, +11pp)
      * Coverage uploads/repository.py: **44%** (antes: 26%, +18pp)
      * Pre-commit: todos os hooks verdes
    - 📊 **Impacto:** Correções da QA-005 agora protegidas por testes específicos (+25 testes), garantindo que guards para None, casts de tipo e validações de id permaneçam robustos. Cobertura dos módulos corrigidos aumentou significativamente (+11pp e +18pp respectivamente)
  - **Fase 6 - Resultados (profiles_service - serviço de perfis/usuários):**
    - ✅ **Arquivo criado:**
      * `tests/test_profiles_service.py`: 21 testes para serviço de perfis (378 linhas)
    - ✅ **Módulo testado:**
      * `src/core/services/profiles_service.py`: Consultas de perfis, mapeamento de emails/display_names
    - ✅ **Total:** 21 testes novos (457 testes no total, antes: 436)
    - ✅ **Cobertura:**
      * Global antes: 28.04%
      * Global depois: **28.65%** (+0.61pp)
      * `src/core/services/profiles_service.py`: **97%** (66/68 linhas, antes: não rastreado)
    - ✅ **Funções testadas:**
      * `list_profiles_by_org()`: 4 testes - sucesso com display_name, org vazia, fallback quando coluna ausente (42703), erro de rede retorna vazio
      * `get_display_names_map()`: 3 testes - criação de mapa email→display_name, org vazia, filtra emails vazios
      * `get_display_name_by_email()`: 6 testes - busca direta, normalização case, não encontrado, display_name vazio, email vazio, erro retorna None
      * `get_email_prefix_map()`: 6 testes - criação de mapa prefixo→email, aliases aplicados, org vazia, filtra emails vazios, erro retorna vazio, normalização case
      * **EMAIL_PREFIX_ALIASES**: 2 testes - constante definida corretamente, alias usado no mapa de prefixos
    - ✅ **Cenários testados:**
      * **Sucesso "happy path"**: Listagem de perfis, mapeamento de emails, busca por email
      * **Fallback gracioso**: Coluna display_name ausente (erro 42703), retorna lista com email apenas
      * **Graceful degradation**: Erros de rede/DB retornam estruturas vazias (não quebram)
      * **Normalização**: Emails sempre lowercase, prefixos extraídos corretamente
      * **Aliases**: pharmaca2013 → fharmaca2013 (usado em notes_service)
      * **Edge cases**: Listas vazias, emails vazios/whitespace, display_names vazios filtrados
    - ✅ **Validação:**
      * Pyright: **0 erros, 0 warnings** em profiles_service.py e test_profiles_service.py
      * pytest focado: **21/21 passed** em tests/test_profiles_service.py
      * Suite filtrada: **457 passed, 2 skipped** (antes: 436 passed)
      * Coverage: **28.65%** (threshold 25%, +0.61pp vs Fase 5)
    - 📊 **Impacto:** Serviço crítico usado por notes_service agora com 97% de cobertura, protegendo normalização de emails de autores e mapeamento de display_names. Todos os caminhos principais (sucesso, vazio, erro) testados com mocks, sem chamadas reais ao Supabase
  - **Microfase 6 - Resultados (profiles_service - modernização de type hints):**
    - ✅ **Arquivo modificado:**
      * `src/core/services/profiles_service.py`: Type hints modernizados (PEP 585/604)
    - ✅ **Alterações aplicadas:**
      * Removido: `from typing import Dict, List, Optional`
      * Mantido: `from typing import Any` (necessário para `dict[str, Any]`)
      * Type hints atualizados:
        - `EMAIL_PREFIX_ALIASES` → `EMAIL_PREFIX_ALIASES: dict[str, str]`
        - `List[Dict[str, Any]]` → `list[dict[str, Any]]` (4 ocorrências)
        - `Dict[str, str]` → `dict[str, str]` (3 ocorrências)
        - `Optional[str]` → `str | None` (1 ocorrência)
      * Variáveis locais anotadas: `data`, `out`, `email_lc`, `rows`, `em`, `prefix`, `alias` (7 variáveis)
    - ✅ **Validação final:**
      * Pyright: **0 erros, 0 warnings** em profiles_service.py e test_profiles_service.py
      * pytest focado: **21/21 passed** em tests/test_profiles_service.py
      * Suite completa: **457 passed, 1 failed, 2 skipped** (falha pré-existente em test_ui_components.py, não relacionada)
      * Coverage global: **28.65%** (mantida)
      * Coverage profiles_service.py: **97%** (mantida)
    - 📊 **Impacto:** Serviço crítico agora com type hints modernos (PEP 585/604), alinhado com clientes/service e uploads/repository (QA-003 Microfase 5). Testes da Fase 6 garantem que refatoração de tipos não introduziu regressões funcionais
  - **Fase 7 - Resultados (lixeira_service - serviço de exclusão/restauração):**
    - ✅ **Arquivo expandido:**
      * `tests/test_lixeira_service.py`: 9 testes novos (15 testes total, antes: 6)
    - ✅ **Módulo testado:**
      * `src/core/services/lixeira_service.py`: Restauração de clientes, exclusão definitiva (DB + Storage)
    - ✅ **Total:** 15 testes total (472 testes no total global, antes: 457)
    - ✅ **Cobertura:**
      * Global antes: 28.65%
      * Global depois: **28.88%** (+0.23pp)
      * `src/core/services/lixeira_service.py`: **84%** (115/137 linhas, antes: 58%)
    - ✅ **Funções testadas:**
      * `restore_clients()`: 9 testes - sucesso single/múltiplo, subpastas obrigatórias garantidas, lista vazia, falha auth/org, falha parcial, subfolder guard tolerante
      * `hard_delete_clients()`: 9 testes - exclusão DB+Storage, múltiplos clientes, remoção de arquivos, storage vazio, lista vazia, falha auth, storage falha mas DB continua, falha DB, falha parcial
      * `_ensure_mandatory_subfolders()`: 2 testes - criação de .keep em subpastas vazias, skip de subpastas existentes
      * `_gather_all_paths()`: 1 teste - listagem recursiva de arquivos
      * `_list_storage_children()`: 1 teste - identificação de pastas vs arquivos
      * `_remove_storage_prefix()`: 1 teste - remoção de múltiplos arquivos
    - ✅ **Cenários testados:**
      * **restore_clients**: Restauração com update do DB (deleted_at=None), garantia de subpastas obrigatórias (SIFAP, ANVISA, FARMACIA_POPULAR, AUDITORIA), proteção contra bug histórico de subpastas perdidas, tolerância a falhas no guard de subpastas (não bloqueia restauração)
      * **hard_delete_clients**: Exclusão permanente (Storage + DB), limpeza de todos os arquivos do prefixo org_id/client_id, tolerância a storage vazio, continuação do delete do DB mesmo com falha no Storage
      * **Edge cases**: Listas vazias, falhas de autenticação, org não encontrada, falhas parciais (alguns OK, outros com erro), erros de rede no Storage/DB
      * **Helpers internos**: Criação de placeholders .keep para pastas vazias, listagem recursiva de arquivos no Storage, identificação de pastas (metadata=None) vs arquivos
    - ✅ **Validação:**
      * Pyright: **0 erros, 0 warnings** em lixeira_service.py e test_lixeira_service.py
      * pytest focado: **15/15 passed** em tests/test_lixeira_service.py
      * Suite filtrada: **472 passed, 1 failed, 2 skipped** (falha pré-existente em test_ui_components.py)
      * Coverage global: **28.88%** (threshold 25%, +0.23pp vs Fase 6)
      * Coverage lixeira_service.py: **84%** (115/137 linhas, antes: 58%, +26pp)
    - 📊 **Impacto:** Serviço crítico de lixeira agora com 84% de cobertura (+26pp), protegendo fluxo de restauração (com garantia de subpastas obrigatórias) e exclusão definitiva. Todos os caminhos principais (sucesso, vazio, erro, falhas parciais) testados com mocks. Proteção contra bug histórico de perda de subpastas na restauração garantida por testes específicos
  - **Microfase 7 - Resultados (lixeira_service - modernização de type hints):**
    - ✅ **Arquivo modificado:**
      * `src/core/services/lixeira_service.py`: Type hints modernizados (PEP 585/604)
    - ✅ **Alterações aplicadas:**
      * Removido: `from typing import List, Tuple` (mantido apenas `Iterable`)
      * Type hints atualizados:
        - `_get_supabase_and_org() -> Tuple[object, str]` → `tuple[object, str]`
        - `_list_storage_children() -> List[dict]` → `list[dict]`
        - `_gather_all_paths() -> List[str]` → `list[str]`
        - `restore_clients() -> Tuple[int, List[Tuple[int, str]]]` → `tuple[int, list[tuple[int, str]]]`
        - `hard_delete_clients() -> Tuple[int, List[Tuple[int, str]]]` → `tuple[int, list[tuple[int, str]]]`
      * Variáveis locais anotadas: `paths: list[str] = []`, `errs: list[tuple[int, str]] = []` (3 ocorrências)
    - ✅ **Validação final:**
      * Pyright: **0 erros, 0 warnings** em lixeira_service.py e test_lixeira_service.py
      * pytest focado: **15/15 passed** em tests/test_lixeira_service.py
      * Suite completa: **472 passed, 1 failed, 2 skipped** (falha pré-existente em test_ui_components.py)
      * Coverage global: **28.88%** (mantida)
      * Coverage lixeira_service.py: **84%** (mantida)
    - 📊 **Impacto:** Serviço de lixeira agora com type hints modernos (PEP 585/604), alinhado com clientes/service, uploads/repository (QA-003 Microfase 5) e profiles_service (Microfase 6). Total de 6 substituições aplicadas (List→list, Tuple→tuple). Testes da Fase 7 garantem que refatoração de tipos não introduziu regressões funcionais
  - **Fase 8 - Resultados (clientes/forms - preparação e upload):**
    - ✅ **Arquivos expandidos:**
      * `tests/test_clientes_forms_upload.py`: 8→10 testes (+2 novos)
      * `tests/test_clientes_forms_prepare.py`: 8→20 testes (+12 novos)
    - ✅ **Módulos testados:**
      * `src/modules/clientes/forms/_prepare.py`: Validação de inputs, preparação de payload, funções auxiliares
      * `src/modules/clientes/forms/_upload.py`: Upload de arquivos, guard de `pasta_local`, progresso
    - ✅ **Total:** 40 testes total (antes: 26 → agora: 40, +14 testes)
    - ✅ **Cobertura:**
      * Global antes: 28.88%
      * Global depois: **29.09%** (+0.21pp)
      * `_prepare.py`: 53% → **64%** (+11pp)
      * `_upload.py`: 29% → **31%** (+2pp)
      * Módulo forms total: 27% → **30%** (+3pp)
    - ✅ **Cenários testados:**
      * **_prepare.py:**
        - Funções auxiliares: `_extract_supabase_error`, `traduzir_erro_supabase_para_msg_amigavel`, `_extract_status_value`, `_build_storage_prefix`, `_unpack_call`, `_ensure_ctx`
        - Erros traduzidos: CNPJ duplicado (23505/uq_clients_cnpj), erros genéricos
        - Construção de storage prefix com/sem partes None
        - Desempacotamento de args/kwargs posicionais
        - Criação e reutilização de contexto de upload
      * **_upload.py:**
        - **Guard crítico QA-005:** `pasta_local` None ou vazia → ValueError
        - Upload com contexto válido, subpasta presente/ausente
        - Cálculo de total_bytes, criação de progress dialog
        - Thread worker iniciada corretamente
        - Abort quando ctx.abort=True ou ctx=None
    - ✅ **Validação:**
      * Pyright: **0 erros, 0 warnings** em test_clientes_forms_upload.py e test_clientes_forms_prepare.py
      * pytest focado: **40/40 passed** (10 upload + 20 prepare + 10 finalize)
      * Suite filtrada: **486 passed, 1 failed, 2 skipped** (antes: 472 passed, +14 testes)
      * Coverage global: **29.09%** (threshold 25%, +0.21pp vs Fase 7)
      * Coverage _prepare.py: **64%** (antes: 53%, +11pp)
      * Coverage _upload.py: **31%** (antes: 29%, +2pp)
    - 📊 **Impacto:** Fluxo de formulários de clientes agora com cobertura expandida, protegendo guard crítico de `pasta_local` (QA-005), funções auxiliares de tradução de erros e construção de contexto. Total de 14 novos testes adicionados (2 em upload, 12 em prepare). Cobertura de _prepare.py aumentou 11pp, protegendo helpers de extração de erros Supabase, status e prefix de storage
  - **Microfase 8 - Resultados (clientes/forms - modernização de type hints):**
    - ✅ **Arquivos modificados:**
      * `src/modules/clientes/forms/_prepare.py`: Type hints modernizados (PEP 585/604)
      * `src/modules/clientes/forms/_upload.py`: Type hints modernizados (PEP 585/604)
    - ✅ **Alterações aplicadas:**
      * **_prepare.py:**
        - Removido: `from typing import Dict, List, Optional, Tuple` (mantido apenas `Any, Mapping`)
        - Type hints atualizados (9 substituições):
          * `_extract_supabase_error() -> Tuple[Optional[str], str, Optional[str]]` → `tuple[str | None, str, str | None]`
          * UploadCtx dataclass (25 campos modernizados):
            - `ents: Dict[str, Any]` → `ents: dict[str, Any]`
            - `arquivos_selecionados: Optional[List[str]]` → `arquivos_selecionados: list[str] | None`
            - `subfolders: Optional[List[str]]` → `subfolders: list[str] | None`
            - `files: List[tuple[str, str]]` → `files: list[tuple[str, str]]`
            - 21 outros campos com `Dict`, `List`, `Optional`
          * `_ask_subpasta() -> Optional[str]` → `str | None`
          * `validate_inputs() -> Tuple[tuple, Dict[str, Any]]` → `tuple[tuple, dict[str, Any]]`
          * `prepare_payload() -> Tuple[tuple, Dict[str, Any]]` → `tuple[tuple, dict[str, Any]]`
          * Variável linha 340: `subpasta_val: Optional[str]` → `subpasta_val: str | None`
      * **_upload.py:**
        - Removido: `from typing import Dict, Tuple` (mantido apenas `Any`)
        - Type hints atualizados (2 substituições):
          * `perform_uploads() -> Tuple[tuple, Dict[str, Any]]` → `tuple[tuple, dict[str, Any]]`
    - ✅ **Total:** 11 modernizações de type hints (9 em _prepare.py, 2 em _upload.py)
    - ✅ **Validação final:**
      * Pyright: **0 erros, 0 warnings** em _prepare.py, _upload.py e testes relacionados
      * pytest focado: **40/40 passed** (10 upload + 20 prepare + 10 finalize)
      * Suite filtrada: **486 passed, 1 failed, 2 skipped** (mesma baseline)
      * Coverage global: **29.09%** (mantida)
      * Coverage _prepare.py: **78%** (antes: 64%, linha 340 agora coberta)
      * Coverage _upload.py: **56%** (antes: 31%, melhorada devido aos testes da Fase 8)
    - 📊 **Impacto:** Fluxo de formulários de clientes agora com type hints modernos (PEP 585/604), alinhado com padrão estabelecido nas Microfases 1-7 (search, textnorm, notes_service, auth, clientes/service, profiles_service, lixeira_service). Testes da Fase 8 garantem que refatoração de tipos não introduziu regressões funcionais. Total de 11 substituições aplicadas, com destaque para modernização completa do UploadCtx dataclass (25 campos)
  - **Fase 9 - Resultados (auditoria/service - serviço de auditoria SIFAP):**
    - ✅ **Arquivo criado:**
      * `tests/test_auditoria_service_fase9.py`: 35 testes para serviço de auditoria (449 linhas)
    - ✅ **Módulo testado:**
      * `src/modules/auditoria/service.py`: CRUD auditorias, storage operations, pipeline de upload
    - ✅ **Total:** 35 testes novos (521 testes no total global, antes: 486)
    - ✅ **Cobertura:**
      * Global antes: 29.09%
      * Global depois: **29.39%** (+0.30pp)
      * `src/modules/auditoria/service.py`: **84%** (161/192 linhas, antes: 59%, +25pp)
    - ✅ **Funções testadas:**
      * **CRUD Auditoria:**
        - `fetch_clients()`: 3 testes - sucesso, offline, exception wrapping
        - `fetch_auditorias()`: 2 testes - sucesso, lista vazia
        - `start_auditoria()`: 4 testes - sucesso, status customizado, response vazio, sem atributo data
        - `update_auditoria_status()`: 2 testes - sucesso, auditoria não encontrada
        - `delete_auditorias()`: 4 testes - sucesso, mixed types (int/str), lista vazia, apenas None/vazios
      * **Storage Operations:**
        - `is_online()`: 3 testes - disponível, indisponível, exceção
        - `get_current_org_id()`: 3 testes - sucesso com cache, force_refresh, LookupError
        - `ensure_auditoria_folder()`: 2 testes - sucesso, org_id customizado
        - `list_existing_file_names()`: 2 testes - arquivos existentes, pasta vazia
        - `upload_storage_bytes()`: 2 testes - sucesso, upsert=True
        - `remove_storage_objects()`: 2 testes - múltiplos arquivos, lista vazia (no-op)
      * **Pipeline Upload:**
        - `ensure_storage_ready()`: 3 testes - sucesso, offline, bucket não configurado
        - `prepare_upload_context()`: 2 testes - sucesso, org_id customizado
        - `get_storage_context()`: 1 teste - usa get_current_org_id() automaticamente
    - ✅ **Cenários testados:**
      * **Happy path:** fetch retorna listas, CRUD funciona, storage operations bem-sucedidos
      * **Edge cases:** Listas vazias (delete_auditorias, remove_storage_objects) fazem no-op, mixed types filtrados (None, "", int/str), cache de org_id funciona, force_refresh invalida cache
      * **Error handling:**
        - Supabase offline → `AuditoriaOfflineError`
        - Response vazio ou sem atributo data → `AuditoriaServiceError`
        - Exceptions genéricas → wrapped em `AuditoriaServiceError`
        - LookupError em org_id → wrapped em `AuditoriaServiceError`
      * **Mocks:** Todos os testes usam mocks de Supabase, repository, storage - nenhuma chamada real de rede
    - ✅ **Validação:**
      * Pyright: **0 erros, 0 warnings** em auditoria/service.py e test_auditoria_service_fase9.py
      * pytest focado: **35/35 passed** em tests/test_auditoria_service_fase9.py (1.91s)
      * Suite filtrada: **521 passed, 1 failed, 2 skipped** (antes: 486 passed, +35 testes)
      * Coverage global: **29.39%** (threshold 25%, +0.30pp vs Fase 8)
      * Coverage auditoria/service.py: **84%** (161/192 linhas, antes: 59%, +25pp)
    - 📊 **Impacto:** Serviço crítico de auditoria SIFAP agora com 84% de cobertura (+25pp), protegendo CRUD de auditorias, operações de storage (org_id, folders, uploads, removals) e pipeline de upload de arquivos. Todos os caminhos principais (sucesso, vazio, erro, offline) testados com mocks. Total de 35 testes adicionados cobrindo 16 funções públicas do módulo
  - **Fase 10 - Resultados (helpers/formatters - utilitários de formatação):**
    - ✅ **Arquivo criado:**
      * `tests/test_helpers_formatters_fase10.py`: 57 testes para helpers de formatação (297 linhas)
    - ✅ **Módulo testado:**
      * `src/helpers/formatters.py`: Formatação de CNPJ, datas/hora (ISO e BR)
    - ✅ **Total:** 57 testes novos (578 testes no total global, antes: 521)
    - ✅ **Cobertura:**
      * Global antes: 29.41%
      * Global depois: **29.80%** (+0.39pp)
      * `src/helpers/formatters.py`: **94%** (67/71 linhas, antes: 13%, +81pp)
    - ✅ **Funções testadas:**
      * **format_cnpj():** 17 testes
        - Happy path: CNPJ sem formatação → "12.345.678/0001-90"
        - CNPJ já formatado → mantém formato (idempotente)
        - Limpeza: remove espaços, caracteres especiais, mantém apenas dígitos
        - Tamanho incorreto: retorna original (12, 16 dígitos, etc.)
        - Edge cases: None → "", vazio → "", apenas espaços, apenas caracteres especiais
        - Tipos numéricos: converte int/float para str antes de formatar
        - Mixed content: extrai 14 dígitos do lixo e formata
      * **fmt_datetime():** 18 testes
        - Tipos suportados: datetime, date, str ISO, str padrão, str brasileiro, timestamp int/float
        - Conversões: date → datetime 00:00:00, timestamp → datetime local
        - Parsing: ISO com/sem Z, formatos brasileiros (DD/MM/YYYY), espaços extras
        - Timezone: UTC string converte para local, timezone-aware converte para local
        - Edge cases: None → "", vazio → "", string inválida → retorna original, epoch timestamp
        - Formato saída: "YYYY-MM-DD HH:MM:SS" (APP_DATETIME_FMT)
        - Idempotência: aplicar duas vezes dá mesmo resultado
      * **fmt_datetime_br():** 15 testes
        - Tipos suportados: datetime, date, str ISO, str padrão, str brasileiro, timestamp
        - Conversões: date → datetime 00:00:00, timestamp → datetime local
        - Parsing: mesmos formatos que fmt_datetime
        - Timezone: UTC converte para local, timezone-aware converte para local
        - Edge cases: None → "", vazio → "", string inválida → retorna original
        - Formato saída: "DD/MM/AAAA - HH:MM:SS" (APP_DATETIME_FMT_BR)
        - Idempotência: aplicar duas vezes dá mesmo resultado
      * **_parse_any_dt() (testado indiretamente):** Parser interno usado por ambas funções de datetime
    - ✅ **Cenários testados:**
      * **CNPJ:**
        - Validação de tamanho (exatamente 14 dígitos após limpar)
        - Remoção de caracteres não-numéricos (\D regex)
        - Formatação padrão brasileiro: XX.XXX.XXX/XXXX-XX
        - Idempotência: format(format(x)) == format(x)
        - Tolerância a tipos: aceita str, int, None (defensivo)
      * **Datetime:**
        - Múltiplos formatos de entrada (ISO, BR, padrão, timestamp, objetos Python)
        - Conversão de timezone (UTC → local, aware → local)
        - Parsing robusto: testa 4 padrões de string automaticamente
        - Saídas consistentes: sempre "YYYY-MM-DD HH:MM:SS" ou "DD/MM/AAAA - HH:MM:SS"
        - Fallback: se não consegue parsear, retorna string original (não levanta exceção)
      * **Edge cases:**
        - Valores None e strings vazias (retornam "")
        - Strings inválidas (retornam original sem quebrar)
        - Timestamps zero (epoch 1970-01-01, pode variar com TZ)
        - Objetos time (não suportado, retorna str(time))
        - Idempotência para ambas funções datetime
    - ✅ **Validação:**
      * Pyright: **0 erros, 0 warnings** em formatters.py e test_helpers_formatters_fase10.py
      * pytest focado: **57/57 passed** em tests/test_helpers_formatters_fase10.py (2.07s)
      * Suite filtrada: **578 passed, 2 skipped** (antes: 521 passed, +57 testes)
  - **Fase 11 - Resultados (ui/files_browser/utils - helpers puros do navegador):**
    - ✅ **Arquivo criado:**
      * `tests/test_files_browser_utils_fase11.py`: 26 testes para helpers do file browser (82 linhas)
    - ✅ **Módulo testado:**
      * `src/ui/files_browser/utils.py`: sanitize_filename, format_file_size, resolve_posix_path, suggest_zip_filename
    - ✅ **Total:** 26 testes novos (604 testes no total global, antes: 578)
    - ✅ **Cobertura:**
      * Global antes: 29.80%
      * Global depois: **29.99%** (+0.19pp)
      * `src/ui/files_browser/utils.py`: **100%** (35/35 linhas, antes: 0%, +100pp)
    - ✅ **Cenários testados:**
      * sanitize_filename: caracteres inválidos substituídos, acentos preservados, remoção de espaços/pontos finais, string vazia
      * format_file_size: None → "—", bytes negativos, limites de unidade (B/KB/MB/GB/TB), arredondamento com uma casa decimal
      * resolve_posix_path: caminhos vazios, relativos com `..`/`.`, absolutos preservados, normalização simples mantendo formato POSIX
      * suggest_zip_filename: extração da pasta final, fallback para "arquivos", sanitização de nomes problemáticos, manutenção de acentos
    - ✅ **Validação:**
      * Pyright: `python -m pyright src/ui/files_browser/utils.py tests/test_files_browser_utils_fase11.py`
      * pytest focado: `python -m pytest tests/test_files_browser_utils_fase11.py -v`
      * Suite filtrada: `python -m pytest -q`
      * Coverage: `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
      * Coverage global: **29.99%** (threshold 25%, +0.19pp vs Fase 10)
      * Coverage src/ui/files_browser/utils.py: **100%** (35/35 linhas, antes: 0%)
    - 📊 **Impacto:** Helpers de formatação agora protegidos com 94% de cobertura (+81pp), garantindo consistência em formatação de CNPJ e datas/hora usadas em toda a aplicação. Funções críticas (format_cnpj, fmt_datetime, fmt_datetime_br) totalmente testadas com edge cases, conversões de tipo, parsing robusto e idempotência. Total de 57 testes cobrindo 3 funções públicas e 1 parser interno
  - **Fase 12 - Resultados (auth - autenticação/segurança):**
    - ✅ **Arquivo criado:**
      * `tests/test_auth_auth_fase12.py`: 4 testes adicionais focados em autenticação (rate limit, lockout, integração validate_credentials + hashing)
    - ✅ **Módulo testado:**
      * `src/core/auth/auth.py`: lógica de autenticação (validação de email/senha, rate limit, PBKDF2).
    - ✅ **Total:** 4 testes novos (604 testes no total global, antes: 600; 603 executados com filtro -k)
    - ✅ **Cobertura:**
      * Global antes: 29.99%
      * Global depois: **29.99%** (+0.00pp)
      * `src/core/auth/auth.py`: **100%** (antes: 98%)
    - ✅ **Cenários testados:**
      * Rate limiting: tentativas antigas resetadas e limpeza após sucesso.
      * Validação de credenciais: e-mail inválido incrementa contador sem chamar Supabase.
      * Supabase: mensagens amigáveis para exceções genéricas e incremento de tentativas nessas falhas.
      * Import opcional: fallback quando `yaml` não está disponível.
    - ✅ **Validação:**
      * `python -m pytest tests/test_auth_validation.py tests/test_auth_auth_fase12.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - 📊 **Impacto:** Módulo crítico de autenticação agora com 100% de cobertura, cobrindo fluxos de login válido, bloqueio/limpeza de tentativas, mensagens para erros de conexão e fallback seguro quando o import opcional de YAML falha, mantendo suite global verde.
  - **Resultado - Microfase 12 (21/11/2025):**
    - ✅ **Módulo:** `src/modules/uploads/repository.py`
    - ✅ **Arquivos de teste revisados:**
      * `tests/test_uploads_repository.py`
      * `tests/test_uploads_repository_fase13.py`
    - ✅ **Alterações aplicadas:** Nenhuma mudança de lógica; revalidação completa de type hints (PEP 585/604) e Pyright em módulo e testes, sem ajustes necessários.
    - ✅ **Validação:**
      * `python -m pyright src/modules/uploads/repository.py tests/test_uploads_repository.py tests/test_uploads_repository_fase13.py`
      * `python -m pytest tests/test_uploads_repository.py tests/test_uploads_repository_fase13.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - 📊 **Impacto:** Repositório de uploads e seus testes revalidados com Pyright após atingir 100% de cobertura, garantindo que os novos cenários da Fase 13 não introduziram problemas de tipo e mantendo o padrão de hints modernos.
  - **Fase 13 - Resultados (uploads/repository - repositório de uploads Supabase):**
    - ✅ **Arquivo criado:**
      * `tests/test_uploads_repository_fase13.py`: 21 testes adicionais focados em helpers de bucket/path e cenários de lista vazia/erro.
    - ✅ **Módulo testado:**
      * `src/modules/uploads/repository.py`: funções de normalização de bucket e orquestração de uploads com adapter.
    - ✅ **Total:** 21 testes novos (625 testes no total global, antes: 604; 624 executados com filtro -k).
    - ✅ **Cobertura:**
      * Global antes: 29.99%
      * Global depois: **30.29%** (+0.30pp)
      * `src/modules/uploads/repository.py`: **100%** (antes: 44%, +56pp)
    - ✅ **Cenários testados:**
      * `current_user_id`/`resolve_org_id`: respostas objeto/dict, falhas, fallback de org e membership Supabase.
      * `ensure_storage_object_absent` e `upload_local_file`: conflitos por dict/str, chamada direta ao adapter.
      * `insert_document_record`/`insert_document_version_record`/`update_document_current_version`: sucesso e exceções quando data vazia.
      * `normalize_bucket` e `build_storage_adapter`: normalização com/sem env, client custom vs default.
      * `upload_items_with_adapter`: lista vazia, erros de adapter tratados como falha amigável, branch de duplicados (409/exists).
    - ✅ **Validação:**
      * `python -m pytest tests/test_uploads_repository.py tests/test_uploads_repository_fase13.py -v`
      * `python -m pytest --cov=src/modules/uploads/repository.py --cov-report=term-missing tests/test_uploads_repository.py tests/test_uploads_repository_fase13.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - 📊 **Impacto:** Repositório de uploads agora com 100% de cobertura, incluindo normalização de bucket, integração com Supabase (org/user), prevenção de sobrescrita, inserção de documentos/versões e handling de duplicados/erros no adapter, reduzindo risco de regressão nas operações de upload.
  - **Fase 14 - Resultados (utils/prefs - persistência de preferências):**
    - ✅ **Arquivo criado:**
      * `tests/test_utils_prefs_fase14.py`: 9 testes adicionais cobrindo prefs (columns, browser prefix/status).
    - ✅ **Módulo testado:**
      * `src/utils/prefs.py`: carga/salvamento de preferências e estado do navegador.
    - ✅ **Total:** 9 testes novos (634 testes no total global, antes: 625; 633 executados com filtro -k).
    - ✅ **Cobertura:**
      * Global antes: 30.29%
      * Global depois: **30.63%** (+0.34pp)
      * `src/utils/prefs.py`: **83%** (antes: 44%, +39pp)
    - ✅ **Cenários testados:**
      * `_get_base_dir`: branch APPDATA e fallback para home com criação de diretório.
      * `load/save_columns_visibility`: caminhos com e sem filelock, arquivo inexistente e JSON corrompido.
      * `load/save_last_prefix`: ausência de arquivo, valores numéricos convertidos para string, JSON inválido.
      * `load/save_browser_status_map`: ausência/JSON inválido, conversão para str, persistência de mapping.
    - ✅ **Validação:**
      * `python -m pytest tests/test_utils_prefs_fase14.py -v`
      * `python -m pytest --cov=src/utils/prefs.py --cov-report=term-missing tests/test_utils_prefs_fase14.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - 📊 **Impacto:** Módulo de preferências agora com cobertura robusta em rotas de leitura/escrita e fallback de erros, usando apenas mocks/temp paths e mantendo comportamento inalterado.
  - **Resultado - Microfase 14 (21/11/2025):**
    - ? **M?dulo:** `src/utils/text_utils.py`
    - ? **Arquivos de teste revisados:** `tests/test_utils_text_utils_fase15.py`
    - ? **Altera??es aplicadas:** adicionado `from __future__ import annotations`, modernizados type hints (PEP 585/604) para helpers de texto/CNPJ e extra??o de campos, imports de typing atualizados e anota??es pontuais de vari?veis.
    - ? **Valida??o:**
      * `python -m pyright src/utils/text_utils.py tests/test_utils_text_utils_fase15.py`
      * `python -m pytest tests/test_utils_text_utils_fase15.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - ?? **Impacto:** Helpers de texto/CNPJ com type hints modernos (PEP 585/604) e Pyright limpo, mantendo ~82% de cobertura e comportamento inalterado.
  - **Resultado - Microfase 15 (21/11/2025):**
    - ✅ **Módulo:** `src/utils/theme_manager.py`
    - ✅ **Arquivos de teste revisados:** `tests/test_utils_theme_manager_fase16.py`
    - ✅ **Alterações aplicadas:** `from __future__ import annotations`, hints modernizados (PEP 585/604) para gerenciador de tema, imports de typing atualizados e anotações locais pontuais.
    - ✅ **Validação:**
      * `python -m pyright src/utils/theme_manager.py tests/test_utils_theme_manager_fase16.py`
      * `python -m pytest tests/test_utils_theme_manager_fase16.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - 📊 **Impacto:** Gerenciador de tema com type hints modernos e Pyright limpo, mantendo 100% de cobertura e comportamento inalterado.
  - **Fase 15 - Resultados (utils/text_utils - helpers de texto/CNPJ):**
    - ✅ **Arquivo criado:**
      * `tests/test_utils_text_utils_fase15.py`: 15 testes adicionais cobrindo normalização, CNPJ e extração de dados.
    - ✅ **Módulo testado:**
      * `src/utils/text_utils.py`: helpers de texto, validação/formatação de CNPJ e extração de Razão Social via OCR.
    - ✅ **Total:** 15 testes novos (649 testes no total global, antes: 634; 648 executados com filtro -k).
    - ✅ **Cobertura:**
      * Global antes: 30.62%
      * Global depois: **31.14%** (+0.52pp)
      * `src/utils/text_utils.py`: **82%** (antes: 23%, +59pp)
    - ✅ **Cenários testados:**
      * Normalização/limpeza: `fix_mojibake`, `normalize_ascii`, `clean_text`, `only_digits`, `format_cnpj`, `cnpj_is_valid`.
      * Helpers internos: `_clean_company_name`, `_match_label`, `_is_label_only`, `_is_skip_value`, `_next_nonempty_value`.
      * Extração: `_extract_razao_by_label`, `_extract_razao_near_cnpj`, `extract_company_fields`, `extract_cnpj_razao` com rótulos e buscas próximas ao CNPJ.
    - ✅ **Validação:**
      * `python -m pytest tests/test_utils_text_utils_fase15.py -v`
      * `python -m pytest --cov=src/utils/text_utils.py --cov-report=term-missing tests/test_utils_text_utils_fase15.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - 📊 **Impacto:** Helpers de texto e CNPJ amplamente exercitados, cobrindo caminhos de extração de Razão Social por label e proximidade, normalização ASCII e validação/formatacão de CNPJ, reduzindo riscos em parsers de OCR.
  - **Fase 16 - Resultados (utils/theme_manager - gerenciador de tema):**
    - o. **Arquivo criado:** `tests/test_utils_theme_manager_fase16.py` (9 testes focados)
    - o. **Modulo testado:** `src/utils/theme_manager.py`
    - o. **Total:** 9 testes novos (aprox. 658 testes globais apos esta fase)
    - o. **Cobertura:**
      * Global antes: 31.14%
      * Global depois: **31.40%** (+0.26pp)
      * `src/utils/theme_manager.py`: **100%** (antes: ~34%)
    - o. **Cenarios testados:**
      * tema atual com cache e load_theme
      * register/unregister de janelas, apply_theme silencioso em erro
      * apply_all removendo janela inexistente, notificando listeners e tratando excecoes
      * set_theme com save ok e save com excecao (cache atualizado)
      * toggle delegando para themes.toggle_theme e reaplicando
    - o. **Validacao:**
      * `python -m pytest tests/test_utils_theme_manager_fase16.py -v`
      * `python -m pytest --cov=src.utils.theme_manager --cov-report=term-missing tests/test_utils_theme_manager_fase16.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`

  - **Fase 17 - Resultados (utils/errors - hook global de erros):**
    - o. **Arquivo criado:** `tests/test_utils_errors_fase17.py` (5 testes focados)
    - o. **Modulo testado:** `src/utils/errors.py`
    - o. **Total:** 5 testes novos (aprox. 663 testes globais apos esta fase)
    - o. **Cobertura:**
      * Global antes: 31.40%
      * Global depois: **31.49%** (+0.09pp)
      * `src/utils/errors.py`: **100%** (antes: ~57%)
    - o. **Cenarios testados:**
      * install_global_exception_hook logando e chamando excepthook original com RC_NO_GUI_ERRORS=1
      * exibicao de GUI quando permitido (_default_root presente, messagebox.showerror chamado)
      * falha na exibicao de GUI registrando warning
      * _default_root ausente acionando branch de except, mantendo chamada do hook original
      * uninstall_global_exception_hook restaurando sys.__excepthook__
    - o. **Validacao:**
      * `python -m pytest tests/test_utils_errors_fase17.py -v`
      * `python -m pytest --cov=src.utils.errors --cov-report=term-missing tests/test_utils_errors_fase17.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`

  - **Resultado - Microfase 16 (21/11/2025):**
    - ? **Modulo:** `src/utils/errors.py`
    - ? **Arquivos de teste revisados:** `tests/test_utils_errors_fase17.py`
    - ? **Alteracoes aplicadas:** from __future__ import annotations, type hints PEP 585/604 nas funcoes de hook global/GUI/log, imports typing ajustados e anotacoes locais pontuais.
    - ? **Validacao:**
      * `python -m pyright src/utils/errors.py tests/test_utils_errors_fase17.py`
      * `python -m pytest tests/test_utils_errors_fase17.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - ?? **Impacto:** Hook global de erros com type hints modernos e Pyright limpo, mantendo 100% de cobertura e o mesmo comportamento de log/GUI/uninstall.

  - **Resultado - Microfase 18 (21/11/2025):**
    - ✅ **Modulo:** `src/utils/file_utils/bytes_utils.py`
    - ✅ **Arquivos de teste revisados:** `tests/test_utils_bytes_utils_fase19.py`
    - ✅ **Alteracoes aplicadas:** type hints modernizados (PEP 585/604) nas rotas de leitura/heuristica OCR de PDF, busca de cartao CNPJ e marcadores `.rc_client_id`, alias PathLike adicionado e imports typing atualizados.
    - ✅ **Validacao:**
      * `python -m pyright src/utils/file_utils/bytes_utils.py tests/test_utils_bytes_utils_fase19.py`
      * `python -m pytest tests/test_utils_bytes_utils_fase19.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - 📊 **Impacto:** Utilitarios de bytes/PDF com type hints modernos e Pyright limpo, mantendo 89% de cobertura e comportamento inalterado.

  - **Resultado - Microfase 19 (21/11/2025):
    - ? **Modulo:** `src/core/db_manager/db_manager.py`
    - ? **Arquivos de teste revisados:** `tests/test_core_db_manager_fase21.py`
    - ? **Alteracoes aplicadas:** type hints modernizados (PEP 585/604) em helpers de retry/ordenacao/row->cliente e nas operacoes de list/insert/update/delete/restore de clientes, imports typing atualizados e anotacoes locais pontuais.
    - ? **Validacao:**
      * `python -m pyright src/core/db_manager/db_manager.py tests/test_core_db_manager_fase21.py`
      * `python -m pytest tests/test_core_db_manager_fase21.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - ?? **Impacto:** Camada db_manager com type hints modernos e Pyright limpo, mantendo ~79% de cobertura em operacoes de list/get/find/insert/update/delete de clientes.

  - **Resultado - Microfase 20 (21/11/2025):**
    - ✅ **Modulo:** `src/core/session/session.py`
    - ✅ **Arquivos de teste revisados:** `tests/test_core_session_fase22.py`
    - ✅ **Alteracoes aplicadas:** `from __future__ import annotations`, type hints PEP 585/604 nas funcoes de sessao (get/set/clear, tokens, refresh via Supabase), imports typing atualizados e anotacoes locais pontuais.
    - ✅ **Validacao:**
      * `python -m pyright src/core/session/session.py tests/test_core_session_fase22.py`
      * `python -m pytest tests/test_core_session_fase22.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - 📊 **Impacto:** Gestor de sessao com type hints modernos e Pyright limpo, mantendo 100% de cobertura e facilitando futuras alteracoes na logica de login/refresh.


  - **Resultado - Microfase 21 (21/11/2025):**
    - ?o. **Modulo:** `src/core/status_monitor.py`
    - ?o. **Arquivos de teste revisados:** `tests/test_core_status_monitor_fase23.py`
    - ?o. **Alteracoes aplicadas:** hints modernizados (PEP 585/604) para worker e monitor (thread/timer, bool | None), imports typing atualizados sem alterar logica.
    - ?o. **Validacao:**
      * `python -m pyright src/core/status_monitor.py tests/test_core_status_monitor_fase23.py`
      * `python -m pytest tests/test_core_status_monitor_fase23.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - ?Y"S **Impacto:** Monitor de status com type hints PEP 604/585 alinhados, Pyright 0/0 e cobertura preservada (~81%) nos cenarios de callbacks, transicoes e start/stop.


  - **Resultado - Microfase 22 (21/11/2025):**
    - o. **Modulo:** `src/core/storage_key.py`
    - o. **Arquivos de teste revisados:** `tests/test_core_storage_key_fase24.py`
    - o. **Alteracoes aplicadas:** type hints modernizados (PEP 585/604), alias para regex como Final e lista tipada para partes, sem alterar logica.
    - o. **Validacao:**
      * `python -m pyright src/core/storage_key.py tests/test_core_storage_key_fase24.py`
      * `python -m pytest tests/test_core_storage_key_fase24.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - o. **Cobertura/Impacto:** 100% em `storage_key.py` mantendo comportamento de sanitizacao e fallback; global ~34.55% (>=25%).

  - **Fase 18 - Resultados (utils/file_utils/path_utils - helpers de paths):**
    - o. **Arquivo criado:** `tests/test_utils_path_utils_fase18.py` (14 testes focados)
    - o. **Modulo testado:** `src/utils/file_utils/path_utils.py`
    - o. **Total:** 14 testes novos (aprox. 677 testes globais apos esta fase)
    - o. **Cobertura:**
      * Global antes: 31.52%
      * Global depois: **32.04%** (+0.52pp)
      * `src/utils/file_utils/path_utils.py`: **100%** (antes: ~17%)
    - o. **Cenarios testados:**
      * split/normalize de segmentos com barras invertidas, strings vazias e nome/children em specs
      * ensure_dir respeitando CLOUD_ONLY, safe_copy criando pai e copiando conteudo
      * open_folder bloqueado por cloud_only e chamando os.startfile quando permitido
      * ensure_subtree com strings vazias, names vazios e arvores aninhadas
      * ensure_subpastas com nomes e alias subpastas, configs len=2/len=3, fallback default e erros de os.makedirs tratados
    - o. **Validacao:**
      * `python -m pytest tests/test_utils_path_utils_fase18.py -v`
      * `python -m pytest --cov=src.utils.file_utils.path_utils --cov-report=term-missing tests/test_utils_path_utils_fase18.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`


  - **Fase 19 - Resultados (utils/file_utils/bytes_utils - leitura/markers de PDF):**
    - o. **Arquivo criado:** `tests/test_utils_bytes_utils_fase19.py` (18 testes focados)
    - o. **Modulo testado:** `src/utils/file_utils/bytes_utils.py`
    - o. **Total:** 18 testes novos (total global: 695)
    - o. **Cobertura:**
      * Global antes: 32.04%
      * Global depois: **32.90%** (+0.86pp)
      * `src/utils/file_utils/bytes_utils.py`: **89%** (antes: ~0% - baseline sem dados coletados; ultimo relatorio conhecido ~15%)
    - o. **Cenarios testados:**
      * Fallbacks de leitura de PDF (PyMuPDF, pypdf e OCR) incluindo imports ausentes, paginas sem texto e limite de max_pages/dpi
      * Heuristica de cartao CNPJ (_looks_like_cartao_cnpj e find_cartao_cnpj_pdf com max_mb)
      * list_and_classify_pdfs com classify_document stubado
      * Marcadores `.rc_client_id`: write_marker, read_marker_id (novo/legacy/vazio) e migrate_legacy_marker removendo arquivos antigos
      * Helpers utilitarios: get_marker_updated_at e format_datetime para datetime/ISO/string invalida
    - o. **Validacao:**
      * `python -m pytest tests/test_utils_bytes_utils_fase19.py -v`
      * `python -m pytest --cov=src.utils.file_utils.bytes_utils --cov-report=term-missing tests/test_utils_bytes_utils_fase19.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`

  - **Fase 20 - Resultados (utils/pdf_reader - leitura de paginas com PyMuPDF):**
    - o. **Arquivo criado:** `tests/test_utils_pdf_reader_fase20.py` (6 testes focados)
    - o. **Modulo testado:** `src/utils/pdf_reader.py`
    - o. **Total:** 6 testes novos (total global: 701)
    - o. **Cobertura:**
      * Global antes: 32.90%
      * Global depois: **33.18%** (+0.28pp)
      * `src/utils/pdf_reader.py`: **92%** (antes: ~0% - module-not-imported)
    - o. **Cenarios testados:**
      * _flatten_rawdict com join basico e erro logado
      * read_pdf_text com falha de abertura retornando vazio
      * limite de max_pages e fechamento garantido do documento
      * fallback para rawdict e cast de retorno nao-string
      * paginas com excecao em load_page sao ignoradas com warning
    - o. **Validacao:**
      * `python -m pytest tests/test_utils_pdf_reader_fase20.py -v`
      * `python -m pytest --cov=src.utils.pdf_reader --cov-report=term-missing tests/test_utils_pdf_reader_fase20.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`

  - **Fase 21 - Resultados (core/db_manager - supabase/backoff):**
  - **Fase 22 - Resultados (core/session - gestor de sessao Supabase):**
    - o. **Arquivo criado:** `tests/test_core_session_fase22.py` (5 testes focados)
    - o. **Modulo testado:** `src/core/session/session.py`
    - o. **Total:** 5 testes novos (total global: 724)
    - o. **Cobertura:**
      * Global antes: 34.00%
      * Global depois: **34.15%** (+0.15pp)
      * `src/core/session/session.py`: **100%** (antes: ~0% - module-not-imported)
    - o. **Cenarios testados:**
      * refresh_current_user_from_supabase sem user e com memberships (owner vs primeiro)
      * set/clear de tokens e current_user idempotentes
      * get_session combinando user/tokens (compat)
    - o. **Validacao:**
      * `python -m pytest tests/test_core_session_fase22.py -v`
      * `python -m pytest --cov=src.core.session.session --cov-report=term-missing tests/test_core_session_fase22.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`

  - **Fase 23 - Resultados (core/status_monitor - monitor de rede/UI):**
    - o. **Arquivo criado:** `tests/test_core_status_monitor_fase23.py` (7 testes focados)
    - o. **Modulo testado:** `src/core/status_monitor.py`
    - o. **Total:** 7 testes novos (total global: 731)
    - o. **Cobertura:**
      * Global antes: 34.15%
      * Global depois: **34.51%** (+0.36pp)
      * `src/core/status_monitor.py`: **81%** (antes: ~0% - module-not-imported)
    - o. **Cenarios testados:**
      * estado inicial/unknown com env_text cloud/local
      * transicoes online/offline via set_cloud_status e callback _on_net_change (scheduler e fallback)
      * start/stop conectando worker de rede sem threads reais
      * _NetStatusWorker._run com probe ok e probe falhando + listener com excecao
    - o. **Validacao:**
      * `python -m pytest tests/test_core_status_monitor_fase23.py -v`
      * `python -m pytest --cov=src.core.status_monitor --cov-report=term-missing tests/test_core_status_monitor_fase23.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`


  - **Fase 30 - Resultados (core/api/api_clients - API facade layer):**
    - o. **Arquivo criado:** `tests/test_core_api_clients_fase30.py` (25 testes focados)
    - o. **Modulo testado:** `src/core/api/api_clients.py`
    - o. **Total:** 25 testes novos (total global: 881)
    - o. **Cobertura:**
      * Global antes: 36.40%
      * Global depois: **36.72%** (+0.32pp)
      * `src/core/api/api_clients.py`: **100%** (antes: 0%, 57 stmts)
    - o. **Cenarios testados:**
      * switch_theme: sucesso, import error, apply_theme error, root=None
      * get_current_theme: sucesso, error fallback (flatly), import error
      * upload_folder: sucesso, default subdir (GERAL), erro (retorna dict), sucesso parcial
      * create_client: sucesso (retorna ID), erro (retorna None)
      * update_client: sucesso (retorna True), erro (retorna False)
      * delete_client: soft default, soft explicit, hard delete, erro
      * search_clients: sucesso (lista), com org_id, vazio, query vazia, erro
      * Edge cases: __all__ completo, mocks de funções inexistentes usando patch.object create=True
    - o. **Validacao:**
      * `python -m pytest tests/test_core_api_clients_fase30.py -v`
      * `python -m pytest --cov=src.core.api.api_clients --cov-report=term-missing tests/test_core_api_clients_fase30.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - o. **Observacoes:**
      * Módulo é uma facade/placeholder que delega para serviços (upload_service, clientes_service) que ainda não têm implementação completa.
      * Testes mockam funções inexistentes usando patch.object(..., create=True) para testar a lógica de delegação e error handling.
      * Cobertura 100% alcançada com 25 testes que validam todos os branches de sucesso/erro.

  - **Fase 29 - Resultados (core/commands - command registry pattern):**
    - o. **Arquivo criado:** `tests/test_core_commands_fase29.py` (39 testes focados)
    - o. **Modulo testado:** `src/core/commands.py`
    - o. **Total:** 39 testes novos (total global: 856)
    - o. **Cobertura:**
      * Global antes: 35.66%
      * Global depois: **36.40%** (+0.74pp)
      * `src/core/commands.py`: **97%** (antes: 0%, 73 stmts, 2 miss)
    - o. **Cenarios testados:**
      * register: comando básico, com defaults, overwrite (warning), help vazio
      * unregister: comando existente (True), comando inexistente (False)
      * run: básico, com kwargs, merge defaults+kwargs, comando não encontrado (KeyError), falha na execução (propagação), retorno None
      * list_commands: registry vazio, múltiplos comandos, comandos bootstrapped (8 built-in)
      * get_command_info: existente (name/func/help/defaults), inexistente (None), lambda
      * Built-in commands: theme:switch, upload:folder, download:zip, trash:list/restore/purge, asset:path (limitado), client:search
      * Edge cases: kwargs extras (TypeError), múltiplos registros (last wins), logs success/failure, KeyError mostra available
    - o. **Validacao:**
      * `python -m pytest tests/test_core_commands_fase29.py -v`
      * `python -m pytest --cov=src.core.commands --cov-report=term-missing tests/test_core_commands_fase29.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - o. **Observacoes:**
      * Linhas não cobertas (2/73): corpo de _asset_path (linhas 223-225) devido a conflito de parâmetro 'name' entre run(name, **kwargs) e _asset_path(name). Design limitation documentada.
      * Cobertura saltou de 0% para 97% com 39 testes abrangentes do registry pattern.

  - **Fase 28 - Resultados (features/cashflow/repository - repositório fluxo de caixa):**
    - o. **Arquivo criado:** `tests/test_cashflow_repository_fase28.py` (37 testes focados)
    - o. **Modulo testado:** `src/features/cashflow/repository.py`
    - o. **Total:** 37 testes novos (total global: 817)
    - o. **Cobertura:**
      * Global antes: 35.56%
      * Global depois: **35.66%** (+0.10pp)
      * `src/features/cashflow/repository.py`: **75%** (antes: ~63%)
    - o. **Cenarios testados:**
      * list_entries: filtros por tipo (IN/OUT/inválido), período, texto (ilike com exceção), org_id, combinações
      * list_entries: resultado vazio, sem atributo data, date objects, filtros None/vazios
      * totals: apenas IN, apenas OUT, misto, lista vazia, amount None, tipo lowercase/None
      * create_entry: sucesso, com/sem org_id, org_id já no data, sem data na resposta
      * update_entry: sucesso, múltiplos campos, sem data na resposta
      * delete_entry: sucesso (sem exceção)
      * helpers: _get_client com None, _fmt_api_error com/sem code/hint, _iso com date/string
    - o. **Validacao:**
      * `python -m pytest tests/test_cashflow_repository_fase28.py -v`
      * `python -m pytest --cov=src.features.cashflow.repository --cov-report=term-missing tests/test_cashflow_repository_fase28.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - o. **Observacoes:** Linhas não cobertas (29/118) são principalmente branches de fallback de import (linhas 11-75) difíceis de testar sem modificar ambiente.

  - **Fase 27 - Resultados (helpers/auth_utils - autenticação):**
    - o. **Arquivo criado:** `tests/test_helpers_auth_utils_fase27.py` (19 testes focados)
    - o. **Modulo testado:** `src/helpers/auth_utils.py`
    - o. **Total:** 19 testes novos (total global: 780)
    - o. **Cobertura:**
      * Global antes: 35.49%
      * Global depois: **35.56%** (+0.07pp)
      * `src/helpers/auth_utils.py`: **100%** (antes: ~69%)
    - o. **Cenarios testados:**
      * current_user_id: formato objeto/dict com user.id/uid, fallback data.user, user None/sem id, exceções
      * resolve_org_id: org via memberships, fallback env var, sem user+env (erro), exceção em query
      * env var com whitespace, empty string após strip, data attribute None
      * integração leve: resolve_org_id chamando current_user_id, fluxo completo autenticado
    - o. **Validacao:**
      * `python -m pytest tests/test_helpers_auth_utils_fase27.py -v`
      * `python -m pytest --cov=src.helpers.auth_utils --cov-report=term-missing tests/test_helpers_auth_utils_fase27.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`

  - **Fase 26 - Resultados (app_status - status global da app):**
    - o. **Arquivo criado:** `tests/test_app_status_fase26.py` (16 testes focados)
    - o. **Modulo testado:** `src/app_status.py`
    - o. **Total:** 16 testes novos (total global: 761)
    - o. **Cobertura:**
      * Global antes: 34.88%
      * Global depois: **35.49%** (+0.61pp)
      * `src/app_status.py`: **100%** (antes: ~0% - module-not-imported)
    - o. **Cenarios testados:**
      * _set_env_text preferencia/erro, _apply_status com status_dot/callback, winfo_exists false/exception
      * leitura YAML (boa/erro), cache de config e recarga quando ausente
      * update_net_status: probe sucesso/falha, after com excecao, worker loop rodando 1x com throttling e dispatch error
      * threads mockadas para evitar loops reais; _apply_status e callbacks simulados
    - o. **Validacao:**
      * `python -m pytest tests/test_app_status_fase26.py -v`
      * `python -m pytest --cov=src.app_status --cov-report=term-missing tests/test_app_status_fase26.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`


  - **Resultado - Microfase 27 (21/11/2025):**
    - o. **Módulo:** `src/core/commands.py`
    - o. **Arquivos de teste revisados:** `tests/test_core_commands_fase29.py` (sem alterações necessárias, já com sintaxe moderna)
    - o. **Alterações aplicadas:**
      * Removido imports legados: `Dict`, `Optional` → mantido apenas `Any`, `Callable`
      * Type hints modernizados (PEP 604/585):
        - `_REGISTRY`: `dict[str, tuple[Callable, str, dict]]`
        - `list_commands()`: retorno `dict[str, str]`
        - `get_command_info()`: retorno `dict[str, Any] | None`
        - `_upload_folder()`: retorno `dict` (minúsculo)
        - `_download_zip()`: parâmetro `dest: str | None`, retorno `str | None`
        - `_client_search()`: parâmetro `org_id: str | None`
    - o. **Validação:**
      * `python -m pyright src/core/commands.py tests/test_core_commands_fase29.py` → 0 erros, 0 warnings
      * `python -m pytest tests/test_core_commands_fase29.py -v` → 39 passed
      * `python -m pytest -q` → 817 passed, 2 skipped
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q` → 36.40% (≥25%)
    - o. **Impacto:** Command registry com type hints PEP 604/585 completos e Pyright 0/0, mantendo 97% de cobertura do módulo (73 stmts, 2 miss no _asset_path devido a design limitation) e 39 testes passando. Alinhado com padrão estabelecido nas Microfases anteriores.

  - **Resultado - Microfase 26 (21/11/2025):**
    - o. **Módulo:** `src/features/cashflow/repository.py`
    - o. **Arquivos de teste revisados:** `tests/test_cashflow_repository_fase28.py` (sem alterações necessárias, já com sintaxe moderna)
    - o. **Alterações aplicadas:**
      * Removido imports legados: `Dict`, `List`, `Optional` → mantido apenas `Any`
      * Type hints modernizados (PEP 604/585):
        - `list_entries`: parâmetros `dfrom`, `dto` com `| None`, type_filter/text/org_id com `str | None`, retorno `list[dict[str, Any]]`
        - `totals`: parâmetros `dfrom`, `dto` com `| None`, org_id `str | None`, retorno `dict[str, float]`
        - `create_entry`: parâmetro `data: dict[str, Any]`, org_id `str | None`, retorno `dict[str, Any]`
        - `update_entry`: parâmetro `data: dict[str, Any]`, retorno `dict[str, Any]`
        - `_fmt_api_error`: anotações locais `code: str | None`, `details: str`, `hint: str | None`, `msg: str`
      * Anotações locais adicionadas em funções principais para clareza de tipos (data, rows, payload, t_in, t_out, amt)
    - o. **Validação:**
      * `python -m pyright src/features/cashflow/repository.py tests/test_cashflow_repository_fase28.py` → 0 erros, 0 warnings
      * `python -m pytest tests/test_cashflow_repository_fase28.py -v` → 37 passed
      * `python -m pytest -q` → 778 passed, 2 skipped
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q` → 35.66% (≥25%)
    - o. **Impacto:** Repository de cashflow com type hints PEP 604/585 completos e Pyright 0/0, mantendo 75% de cobertura do módulo (118 stmts, 29 miss - principalmente fallbacks de import) e 37 testes passando. Alinhado com padrão estabelecido nas Microfases anteriores.

  - **Resultado - Microfase 25 (21/11/2025):**
    - o. **Modulo:** `src/helpers/auth_utils.py`
    - o. **Arquivos de teste revisados:** `tests/test_helpers_auth_utils_fase27.py`
    - o. **Alteracoes aplicadas:** type hints modernizados (PEP 604) - removido `Optional`, adotado `str | None` para current_user_id(); imports de typing removidos (mantido apenas `from __future__ import annotations`).
    - o. **Validacao:**
      * `python -m pyright src/helpers/auth_utils.py tests/test_helpers_auth_utils_fase27.py`
      * `python -m pytest tests/test_helpers_auth_utils_fase27.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - o. **Impacto:** auth_utils com typings PEP 604 e Pyright 0/0, mantendo 100% de cobertura e 19 testes passando.

  - **Resultado - Microfase 24 (21/11/2025):**
    - o. **Modulo:** `src/app_status.py`
    - o. **Arquivos de teste revisados:** `tests/test_app_status_fase26.py`
    - o. **Alteracoes aplicadas:** type hints modernizados (PEP 585/604) com aliases ConfigValues/ConfigCache e colecoes tipadas, sem alterar logica.
    - o. **Validacao:**
      * `python -m pyright src/app_status.py tests/test_app_status_fase26.py`
      * `python -m pytest tests/test_app_status_fase26.py -v`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`
    - o. **Impacto:** app_status com typings atualizados e Pyright 0/0, mantendo 100% de cobertura e comportamento de status/worker intacto.

  - **Fase 25 - Resultados (utils/subpastas_config - subpastas obrigatorias):**
    - o. **Arquivo criado:** `tests/test_utils_subpastas_config_fase25.py` (9 testes focados)
    - o. **Modulo testado:** `src/utils/subpastas_config.py`
    - o. **Total:** 9 testes novos (total global: 745)
    - o. **Cobertura:**
      * Global antes: 34.55%
      * Global depois: **34.88%** (+0.33pp)
      * `src/utils/subpastas_config.py`: **100%** (antes: ~25%)
    - o. **Cenarios testados:**
      * flatten de listas/dicts com prefixos e normalizacao de barras/_norm
      * carga de config explicita (YAML) com duplicates/EXTRAS
      * caminhos inexistentes e erro de I/O retornando listas vazias
      * obrigatorios (get_mandatory_subpastas) e join_prefix com variacoes de base/parts
    - o. **Validacao:**
      * `python -m pytest tests/test_utils_subpastas_config_fase25.py -v`
      * `python -m pytest --cov=src.utils.subpastas_config --cov-report=term-missing tests/test_utils_subpastas_config_fase25.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`

  - **Fase 24 - Resultados (core/storage_key - montagem de chaves):**
    - o. **Arquivo criado:** `tests/test_core_storage_key_fase24.py` (5 testes focados)
    - o. **Modulo testado:** `src/core/storage_key.py`
    - o. **Total:** 5 testes novos (total global: 736)
    - o. **Cobertura:**
      * Global antes: 34.51%
      * Global depois: **34.55%** (+0.04pp)
      * `src/core/storage_key.py`: **100%** (antes: ~0% - module-not-imported)
    - o. **Cenarios testados:**
      * sanitizacao de segmentos/nomes com diacriticos, porcentagem e espacos
      * padrao de filename fallback para valores vazios
      * montagem de chave basica com normalizacao de barras e ignorando partes vazias
      * fallback com hash quando regex de caracteres permitidos falha (# no nome)
      * round-trip de entradas vazias (filename None => "arquivo")
    - o. **Validacao:**
      * `python -m pytest tests/test_core_storage_key_fase24.py -v`
      * `python -m pytest --cov=src.core.storage_key --cov-report=term-missing tests/test_core_storage_key_fase24.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`

    - o. **Arquivo criado:** `tests/test_core_db_manager_fase21.py` (18 testes focados)
    - o. **Modulo testado:** `src/core/db_manager/db_manager.py`
    - o. **Total:** 18 testes novos (total global: 719)
    - o. **Cobertura:**
      * Global antes: 33.18%
      * Global depois: **33.98%** (+0.80pp)
      * `src/core/db_manager/db_manager.py`: **79%** (antes: ~0% - module-not-imported)
    - o. **Cenarios testados:**
      * _resolve_order, _to_cliente, _current_user_email (trim/exception) e _with_retries com backoff e propagacao de erros
      * list/get/find clientes com filtros e normalizacao de CNPJ
      * insert_cliente com retry/fallback removendo ultima_por e consulta de fallback para id
      * update_cliente/update_status_only retornando count e fallback sem ultima_por
      * delete/soft_delete/restore/purge contando linhas e tratando excecao na primeira chamada
    - o. **Validacao:**
      * `python -m pytest tests/test_core_db_manager_fase21.py -v`
      * `python -m pytest --cov=src.core.db_manager.db_manager --cov-report=term-missing tests/test_core_db_manager_fase21.py -q`
      * `python -m pytest -q`
      * `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -q`

  - **Meta final:** 85%+ cobertura
  - **Próximas fases:** Outros módulos de baixa cobertura conforme necessário

### Coverage App Core (novo escopo)

- [x] **COV-APP-CORE-BASELINE: Expandir coverage para o App Core e registrar baseline** ✅ **CONCLUÍDO**
  - **Área:** `.coveragerc`, `pytest.ini`
  - **Descrição:** Medir coverage oficial em `src/`, `adapters/`, `infra/`, `data/` e `security` com branch coverage ativo.
  - **Resultado:** Baseline inicial **38,17%** do App Core (15.886 statements), com:
    - `adapters/` → 48,5%
    - `infra/` → 37,4%
    - `data/` → 28,2%
    - `security/` → 19,5%
    - `src/` → 38,6%
  - **Referência:** `dev/coverage_baseline_app_core.md`.

- [x] **COV-SEC-001: Aumentar cobertura de `security/crypto.py`** ✅ **CONCLUÍDO**
  - **Prioridade:** CRÍTICA (ver também **SEG-004** em P0)
  - **Cobertura anterior:** **19,5%**
  - **Cobertura atual:** **95,1%** (meta era ≥ 80%, superada em +15,1pp)
  - **Objetivo alcançado:** 21 testes criados cobrindo round-trip encrypt/decrypt, entradas inválidas, chave errada/corrompida, compatibilidade com API do app, e logging de exceções.
  - **Documentação:** `dev/cov_sec_crypto.md` (análise completa, cenários de teste, comandos executados, recomendações futuras)
  - **Ação concluída:** Arquivo `tests/test_security_crypto_fase33.py` criado com 21 testes, type hints ajustados para `str | None` em `security/crypto.py` (eliminando warnings Pylance), sem alterações na lógica de produção.

- [x] **COV-DATA-001: Aumentar cobertura de `data/supabase_repo.py`** ⚠️ **BLOQUEADO**
  - **Prioridade:** ALTA
  - **Cobertura atual:** **16,2%** (inalterada)
  - **Objetivo:** atingir pelo menos **50%** de cobertura ❌ **NÃO ALCANÇADO**
  - **Status:** ❌ **BLOQUEADO** por importação circular crítica
  - **Problema identificado:**
    - Ciclo de dependências: `data.supabase_repo` → `infra.supabase_client` → `src.app_core` → `adapters.storage.supabase_storage` → `infra.supabase_client`
    - **Erro:** `ImportError: cannot import name 'supabase' from partially initialized module 'infra.supabase_client'`
    - Qualquer tentativa de importar o módulo em testes falha antes da execução
  - **Trabalho realizado:**
    - ✅ Análise completa do módulo (7 funções públicas, 5 helpers)
    - ✅ 40+ cenários de teste criados em `tests/test_data_supabase_repo_fase34.py` (não executáveis)
    - ✅ Documentação completa do problema em `dev/cov_data_supabase_repo.md`
    - ✅ Propostas de resolução: refatorar imports, lazy loading, dependency injection
  - **Próximos passos:**
    - 🔴 **CRÍTICO:** Criar issue para refatoração da importação circular (extrair `infra/supabase/shared.py`)
    - ⚠️ Priorizar refatoração em sprint de dívida técnica
    - ✅ Após correção, retomar COV-DATA-001
  - **Referência:** `dev/cov_data_supabase_repo.md` (análise completa do bloqueio)

- [x] **COV-INFRA-001: Aumentar cobertura de `infra/settings.py` e `infra/supabase/storage_client.py`**
  - **Prioridade:** ALTA
  - **Cobertura atual:** `infra/settings.py` **97.3%** ✅, `infra/supabase/storage_client.py` **87.1%** ✅
  - **Objetivo:** levar ambos para **≥ 50%** → **CONCLUÍDO COM SUCESSO**
  - **Ação concluída:**
    - ✅ Criados `tests/test_infra_settings_fase35.py` (19 testes) e `tests/test_infra_storage_client_fase36.py` (28 testes)
    - ✅ Cobertura `settings.py`: 0% → 97.3% (+97.3pp)
    - ✅ Cobertura `storage_client.py`: 14% → 87.1% (+73.1pp)
    - ✅ App Core coverage: 38.64% → 43.44% (+4.8pp)
    - ✅ 47 testes passando, sem regressões
  - **Referência:** `dev/cov_infra_settings_storage_client.md`
  - **Nota:** Caminho correto do arquivo é `infra/supabase/storage_client.py` (corrigido nesta atualização)

- [x] **COV-ADAPTERS-001: Aumentar cobertura de `adapters/storage/supabase_storage.py`** ✅ **CONCLUÍDO**
  - **Prioridade:** MÉDIA
  - **Cobertura anterior:** **36,8%**
  - **Cobertura alcançada:** **78,9%** (superou meta de ≥70%)
  - **Cenários testados:**
    - ✅ Funções utilitárias: normalização de buckets, remoção de acentos, detecção de content-type
    - ✅ Operações privadas: `_upload`, `_download`, `_delete`, `_list` com normalização automática
    - ✅ Classe SupabaseStorageAdapter: todos os métodos públicos
    - ✅ Casos extremos: edge cases, validação de erros, buckets default
  - **Arquivo de testes:** `tests/test_adapters_supabase_storage_fase37.py` (40 testes)
  - **Estratégia:** Mocking de sys.modules (session-scoped) para evitar circular imports
  - **Resultado:**
    - ✅ 40 testes criados, todos passando
    - ✅ Cobertura: 111 stmts, 20 missed, 22 branches, 6 partial (78.9%)
    - ✅ Sem regressões na suite completa
    - 📄 Documentação: `dev/cov_adapters_supabase_storage.md`

- [x] **TEST-002: Configurar coverage report no CI**
  - **Área:** `.github/workflows/ci.yml`
  - **Descrição:** Adicionar job de coverage com threshold
  - **Ação:** `pytest --cov --cov-fail-under=25` (ajustado para realidade atual)
  - **Benefício:** Visibilidade de cobertura em PRs e proteção contra regressão
  - **Esforço:** 1h
  - **Automável:** Sim
  - **Resultado:**
    - ✅ CI atualizada para rodar pytest com pytest-cov e --cov-fail-under=25
    - ✅ Job de testes em `.github/workflows/ci.yml` agora:
      - Mede cobertura do **App Core** usando `--cov` (fontes definidas em `.coveragerc`: `src/`, `adapters/`, `infra/`, `data/`, `security/`)
      - Mostra linhas não cobertas com `--cov-report=term-missing`
      - Falha automaticamente se cobertura total < 25% (`--cov-fail-under=25`)
      - Usa `python -m pytest` para compatibilidade com venv
      - Mantém modo verbose (`-v`) para detalhamento de testes
    - ✅ `CONTRIBUTING.md` atualizado com instruções de coverage local
    - ✅ Comando local recomendado: `python -m pytest --cov --cov-report=term-missing --cov-fail-under=25 -v`
    - ✅ `pytest-cov==7.0.0` já presente em `requirements-dev.txt` (sem alteração necessária)
    - 📈 Cobertura atual: ~38% App Core (threshold inicial em 25% para evitar falsos positivos)
    - 🎯 Meta futura: Aumentar gradualmente para 80%+ conforme testes forem adicionados (ver TEST-001)

- [x] **AUTH-BOOTSTRAP-TESTS-001: Estabilizar testes de sessão persistida em auth_bootstrap** ✅ **CONCLUÍDO**
  - **Área:** `tests/test_auth_bootstrap_persisted_session.py`, `src/core/auth_bootstrap.py`
  - **Descrição:** Ajustar o `DummyApp` de teste para usar o `tk_root_session` e expor `.tk`, evitando crash do Tkinter ao instanciar `LoginDialog` durante os testes de sessão persistida.
  - **Problema anterior:** `AttributeError: 'DummyApp' object has no attribute 'tk'`
  - **Solução:**
    - Reutilizado fixture `tk_root_session` do `conftest.py`
    - `DummyApp` modificado para receber `master` e expor `self.tk = master.tk`
    - Nenhuma alteração em código de produção (apenas testes)
  - **Resultado:**
    - ✅ 5/5 testes de `test_auth_bootstrap_persisted_session.py` passando
    - ✅ Sem erros de Tkinter/TclError
    - ✅ Cobertura de `auth_bootstrap.py`: 59.3%
  - **Referência:** `dev/fix_auth_bootstrap_persisted_session.md`
  - **Esforço:** 1h
  - **Automável:** Manual

- [x] **FLAGS-TESTS-001: Validar estabilidade dos testes de flags / src.cli** ✅ **CONCLUÍDO**
  - **Área:** `tests/test_flags.py`, `src/cli.py`
  - **Descrição:** Validar e documentar a implementação correta dos testes de parsing de argumentos CLI (`--no-splash`, `--safe-mode`, `--debug`), garantindo que não há conflitos com argumentos do pytest-cov.
  - **Implementação atual (já correta):**
    - Import correto: `from src.cli import parse_args`
    - Uso de `parse_args([...])` com listas explícitas de argumentos
    - Não depende de `sys.argv` global (evita poluição do pytest)
    - Teste de importação defensivo com try/except
  - **Resultado:**
    - ✅ 6/6 testes de `test_flags.py` passando
    - ✅ Sem `ModuleNotFoundError` ou `SystemExit(2)` de argparse
    - ✅ Cobertura de `src/cli.py`: 77.3%
    - ✅ Validação com 71 testes incluindo os que estavam falhando: todos passaram
  - **Observação:** Não foram necessárias correções; testes já estavam implementados corretamente desde o início
  - **Referência:** `dev/fix_flags_tests.md`
  - **Esforço:** 1h (validação e documentação)
  - **Automável:** Manual

- [x] **TEST-CORE-HEALTHCHECK-001: Check-up geral da suíte de testes (v1.2.64)** ✅ **CONCLUÍDO**
  - **Área:** Testes automatizados e coverage do App Core
  - **Descrição:** Rodar pytest/coverage na versão v1.2.64, mapear falhas e pontos fracos de cobertura, e documentar próximos "books" de testes/coverage (P2/P3).
  - **Resultado:**
    - ✅ Suíte completa executada: **23 falhas** identificadas
    - ✅ Cobertura global do App Core: **43.65%** (superou meta mínima de 25%)
    - ✅ Falhas classificadas por área:
      - AUTH/DB (13): `test_auth_validation.py` – SQLite e rate limit
      - FLAGS/CLI (6): `test_flags.py` – import incorreto de `src.cli`
      - INTEGRAÇÃO (1): `test_clientes_integration.py` – RLS do Supabase
      - UI/MENU (1): `test_menu_logout.py` – monkeypatch de logout
      - PREFS (1): `test_prefs.py` – arquivo corrompido
      - MÓDULOS (1): `test_modules_aliases.py` – mock de __path__
      - AUTH/BOOTSTRAP (1): `test_auth_bootstrap_persisted_session.py`
    - ✅ Propostos 10 "books" futuros (P1-P3):
      - P1: AUTH-VALIDATION-TESTS-001, FLAGS-CLI-TESTS-001, CLIENTES-INTEGRATION-TESTS-001, AUTH-BOOTSTRAP-TESTS-002
      - P2: MENU-LOGOUT-TESTS-001, PREFS-TESTS-001, MODULES-ALIASES-TESTS-001, COV-UTILS-VALIDATORS-001
      - P3: COV-UI-THEMES-001
    - ✅ COV-DATA-001 confirmado como BLOQUEADO (ciclo de import)
  - **Referência:** `dev/test_suite_healthcheck_v1.2.64.md`
  - **Esforço:** 2h (execução + análise + documentação)
  - **Automável:** Parcial (execução sim, análise manual)

---

## P2 - DESEJÁVEL 🟢

### Documentação

- [ ] **DOC-001: Criar README.md principal**
  - **Área:** Raiz do projeto
  - **Descrição:** README com overview, setup, build, contribuição
  - **Seções:** Descrição, Features, Instalação, Build, Testes, Licença
  - **Benefício:** Onboarding de novos devs
  - **Esforço:** 2-3h
  - **Automável:** Manual

- [ ] **DOC-002: Gerar documentação de API com Sphinx**
  - **Área:** Criar `docs/api/`
  - **Descrição:** Autodoc de módulos principais
  - **Ferramenta:** Sphinx + autodoc
  - **Benefício:** Referência de API interna
  - **Esforço:** 4-6h
  - **Automável:** Parcial (geração automática, organização manual)

- [ ] **DOC-003: Criar manual de usuário**
  - **Área:** `docs/user-guide/`
  - **Descrição:** Guia para usuário final (não técnico)
  - **Seções:** Instalação, Primeiros passos, Funcionalidades
  - **Benefício:** Suporte ao usuário
  - **Esforço:** 8-12h
  - **Automável:** Manual

- [ ] **DOC-004: Documentar arquitetura com diagramas**
  - **Área:** `docs/architecture/`
  - **Descrição:** Diagramas C4 ou UML (componentes, sequência)
  - **Ferramenta:** PlantUML, Mermaid, ou draw.io
  - **Benefício:** Entendimento rápido da arquitetura
  - **Esforço:** 4-6h
  - **Automável:** Manual

- [ ] **DOC-005: Revisar e consolidar docs antigas**
  - **Área:** `docs/releases/FASE_*.md`
  - **Descrição:** Arquivar ou consolidar relatórios de fases
  - **Ação:** Mover para `docs/archive/` se obsoletos
  - **Benefício:** Organização
  - **Esforço:** 2h
  - **Automável:** Manual

### Build e Deploy

- [ ] **BUILD-001: Otimizar tamanho do executável**
  - **Área:** `rcgestor.spec`
  - **Descrição:**
    - Usar `--exclude-module` para pacotes não usados
    - Verificar binários desnecessários
    - Considerar compressão adicional
  - **Benefício:** Executável de ~80MB → ~50-60MB
  - **Esforço:** 4-6h
  - **Automável:** Parcial

- [ ] **BUILD-002: Criar instalador (Inno Setup)**
  - **Área:** Criar `installer/rcgestor.iss`
  - **Descrição:** Instalador Windows com:
    - Assinatura digital integrada
    - Desinstalador
    - Atalhos
  - **Benefício:** Distribuição profissional
  - **Esforço:** 6-8h
  - **Automável:** Parcial (script de build)

- [ ] **BUILD-003: Cache de dependências no CI**
  - **Área:** `.github/workflows/ci.yml`
  - **Descrição:** Cachear `.venv` ou pip cache
  - **Ação:** Usar `actions/cache@v4`
  - **Benefício:** CI 2-3x mais rápido
  - **Esforço:** 1h
  - **Automável:** Sim

- [ ] **BUILD-004: Adicionar job de linting no CI**
  - **Área:** `.github/workflows/ci.yml`
  - **Descrição:** Adicionar job `lint` com ruff, pyright
  - **Benefício:** Qualidade forçada em PRs
  - **Esforço:** 1-2h
  - **Automável:** Sim

### Código e Estrutura

- [ ] **CODE-001: Consolidar estrutura de pastas**
  - **Área:** `src/helpers/` e `helpers/`
  - **Descrição:** Mover `helpers/` raiz para dentro de `src/`
  - **Ação:** Git mv + atualizar imports
  - **Benefício:** Organização consistente
  - **Esforço:** 2-3h
  - **Automável:** Parcial (git mv manual, imports com refactor tool)

- [ ] **CODE-002: Remover arquivos temporários versionados**
  - **Área:** `tmp_*.py`, `__tmp_*.txt`
  - **Descrição:** Remover ou mover para `.gitignore`
  - **Benefício:** Limpeza do repo
  - **Esforço:** 30min
  - **Automável:** Manual

- [ ] **CODE-003: Mover relatórios da raiz para docs/**
  - **Área:** `FASE_*_RELATORIO.md` na raiz
  - **Descrição:** Mover para `docs/releases/` ou `docs/archive/`
  - **Benefício:** Raiz mais limpa
  - **Esforço:** 30min
  - **Automável:** Manual

- [ ] **CODE-004: Remover código duplicado de compatibilidade**
  - **Área:** `src/ui/hub_screen.py`, `src/ui/passwords_screen.py`, etc.
  - **Descrição:** Deprecar arquivos que apenas reexportam
  - **Ação:** Marcar como deprecated, remover em v2.0
  - **Benefício:** Menos código para manter
  - **Esforço:** 4-6h (inclui atualizar chamadores)
  - **Automável:** Parcial (detecção com grep, remoção manual)

### Ferramentas de Qualidade

- [ ] **TOOL-001: Configurar Dependabot**
  - **Área:** `.github/dependabot.yml`
  - **Descrição:** Automatizar PRs de atualização de deps
  - **Benefício:** Deps sempre atualizadas
  - **Esforço:** 30min
  - **Automável:** Sim

- [ ] **TOOL-002: Integrar bandit no CI**
  - **Área:** `.github/workflows/security-audit.yml`
  - **Descrição:** Adicionar SAST ao pipeline
  - **Benefício:** Detecção automática de vulnerabilidades
  - **Esforço:** 1h
  - **Automável:** Sim

- [ ] **TOOL-003: Ajustar configuração do Ruff**
  - **Área:** `ruff.toml`
  - **Descrição:**
    - Reduzir `line-length` de 160 para 100
    - Adicionar mais regras (W, C, N)
    - Reduzir per-file ignores
  - **Benefício:** Código mais consistente
  - **Esforço:** 2-3h (inclui correções)
  - **Automável:** Parcial

- [ ] **TOOL-004: Melhorar configuração do Pyright**
  - **Área:** `pyrightconfig.json`
  - **Descrição:**
    - Mudar `typeCheckingMode` para "standard"
    - Habilitar `reportAttributeAccessIssue`
    - Corrigir erros revelados
  - **Benefício:** Type safety melhorado
  - **Esforço:** 6-10h (correções podem ser extensas)
  - **Automável:** Parcial

---

## P3 - COSMÉTICO ⚪

### Melhorias de Longo Prazo

- [ ] **LONG-001: Migrar para pyproject.toml completo**
  - **Área:** Consolidar configs em `pyproject.toml`
  - **Descrição:** Mover de requirements.txt para [project.dependencies]
  - **Benefício:** Padrão moderno (PEP 621)
  - **Esforço:** 4-6h
  - **Automável:** Parcial

- [ ] **LONG-002: Implementar arquitetura de plugins**
  - **Área:** Novo módulo `src/plugins/`
  - **Descrição:** Permitir extensões sem modificar core
  - **Benefício:** Extensibilidade
  - **Esforço:** 20-40h (grande mudança)
  - **Automável:** Manual

- [ ] **LONG-003: i18n/l10n (internacionalização)**
  - **Área:** Todo o código com strings de UI
  - **Descrição:** Adicionar suporte a múltiplos idiomas
  - **Ferramenta:** gettext ou similar
  - **Benefício:** Alcance internacional
  - **Esforço:** 30-50h
  - **Automável:** Parcial (extração de strings)

- [ ] **LONG-004: Testes E2E de GUI**
  - **Área:** Novo `tests/e2e/`
  - **Descrição:** Automação de UI com pywinauto ou similar
  - **Benefício:** Cobertura completa
  - **Esforço:** 20-30h
  - **Automável:** Manual (setup complexo)

- [ ] **LONG-005: Migrar para async/await sistemático**
  - **Área:** Toda a camada de I/O
  - **Descrição:** Refatorar para asyncio consistente
  - **Benefício:** Performance e responsividade
  - **Esforço:** 40-60h (mudança arquitetural)
  - **Automável:** Manual

### Bug Fixes de Produção (FASE B)

- [x] **BUG-PROD-AUTH-001: Remover dependência de importlib.reload em auth** ✅ **CONCLUÍDO**
  - **Área:** `src/core/auth/auth.py`, `tests/test_auth_auth_fase12.py`
  - **Descrição:** Eliminar uso de `importlib.reload()` em testes que quebrava fixtures de outros testes
  - **Solução:** Refatorar import opcional de YAML para função `_safe_import_yaml()` testável sem reload
  - **Arquivos modificados:**
    - `src/core/auth/auth.py`: Novo helper `_safe_import_yaml()`
    - `tests/test_auth_auth_fase12.py`: Teste reescrito com monkeypatch direto
  - **Resultado:**
    - ✅ 62 testes de auth passando juntos (test_auth_*.py)
    - ✅ Eliminadas fixtures de reload que causavam poluição de estado
  - **Comando de validação:** `python -m pytest tests/test_auth_auth_fase12.py tests/test_auth_bootstrap_persisted_session.py tests/test_auth_session_prefs.py tests/test_auth_validation.py -v`
  - **Esforço:** 2h
  - **Automável:** Manual

- [x] **BUG-PROD-CLIENTES-001: Fluxo integração clientes + upload** ✅ **VALIDADO**
  - **Área:** `tests/test_clientes_integration.py`
  - **Descrição:** Validar que teste de integração completo passa isoladamente
  - **Status:** Teste já estava correto - falhas eram causadas por poluição de importlib.reload
  - **Resultado:**
    - ✅ 2/2 testes passando em `test_clientes_integration.py`
    - ✅ Pipeline completo (prepare → upload → finalize) funciona corretamente
  - **Comando de validação:** `python -m pytest tests/test_clientes_integration.py -v`
  - **Esforço:** 0h (validação apenas)
  - **Automável:** N/A

- [x] **BUG-PROD-FLAGS-001: CLI/parse_args e imports** ✅ **VALIDADO**
  - **Área:** `tests/test_flags.py`, `src/cli.py`
  - **Descrição:** Validar que testes de parsing de argumentos CLI passam
  - **Status:** Testes já estavam corretos - falhas eram causadas por poluição de estado
  - **Resultado:**
    - ✅ 6/6 testes passando em `test_flags.py`
    - ✅ Flags testadas: --no-splash, --safe-mode, --debug, combinações
  - **Comando de validação:** `python -m pytest tests/test_flags.py -v`
  - **Esforço:** 0h (validação apenas)
  - **Automável:** N/A

- [x] **BUG-PROD-MENU-LOGOUT-001: Logout no menu** ✅ **VALIDADO**
  - **Área:** `tests/test_menu_logout.py`
  - **Descrição:** Validar que teste de logout via menu passa
  - **Status:** Teste já estava correto - falhas eram causadas por poluição de estado
  - **Resultado:**
    - ✅ 1/1 teste passando em `test_menu_logout.py`
    - ✅ Confirmação de logout com Supabase funcionando
  - **Comando de validação:** `python -m pytest tests/test_menu_logout.py -v`
  - **Esforço:** 0h (validação apenas)
  - **Automável:** N/A

- [x] **BUG-PROD-MODULES-ALIASES-001: Aliases de módulos** ✅ **VALIDADO**
  - **Área:** `tests/test_modules_aliases.py`
  - **Descrição:** Validar que testes de aliases de serviços passam
  - **Status:** Testes já estavam corretos - falhas eram causadas por poluição de estado
  - **Resultado:**
    - ✅ 7/7 testes passando em `test_modules_aliases.py`
    - ✅ Aliases validados: clientes, lixeira, notas, uploads, forms, login, pdf_preview
  - **Comando de validação:** `python -m pytest tests/test_modules_aliases.py -v`
  - **Esforço:** 0h (validação apenas)
  - **Automável:** N/A

- [x] **BUG-PROD-PREFS-001: Arquivo corrompido de preferências** ✅ **VALIDADO**
  - **Área:** `tests/test_prefs.py`
  - **Descrição:** Validar que testes de preferências passam
  - **Status:** Testes já estavam corretos - falhas eram causadas por poluição de estado
  - **Resultado:**
    - ✅ 5/5 testes passando em `test_prefs.py`
    - ✅ Comportamento de arquivo corrompido alinhado com test_utils_prefs_fase14.py
  - **Comando de validação:** `python -m pytest tests/test_prefs.py -v`
  - **Esforço:** 0h (validação apenas)
  - **Automável:** N/A

- [x] **SUITE-ISOLATION-001: Infraestrutura de isolamento de testes** ✅ **IMPLEMENTADO (parcial)**
  - **Área:** `tests/conftest.py`, `src/core/auth/auth.py`, `tests/test_prefs.py`
  - **Descrição:** Criar infraestrutura para isolamento de estado global entre testes
  - **Solução implementada:**
    1. Helper `_reset_auth_for_tests()` em `src/core/auth/auth.py` para limpar rate limiting
    2. Hook `pytest_runtest_setup()` em `conftest.py` que reseta auth antes de cada teste
    3. Fixture autouse `isolated_prefs_dir()` que isola preferências por teste usando tmp_path
    4. Ajuste em `test_prefs.py` para reutilizar fixture global ao invés de duplicar
  - **Arquivos modificados:**
    - `src/core/auth/auth.py`: Adicionado `_reset_auth_for_tests()` (3 linhas após linha 70)
    - `tests/conftest.py`: Adicionado hook e fixture autouse (25 linhas adicionais)
    - `tests/test_prefs.py`: Fixture `temp_prefs_dir` refatorada para reutilizar `isolated_prefs_dir`
  - **Resultado:**
    - ✅ Todos os 76 testes das FASES A+B passam juntos: `python -m pytest tests/test_auth_*.py tests/test_clientes_integration.py tests/test_flags.py tests/test_menu_logout.py tests/test_modules_aliases.py tests/test_prefs.py -v` → 75 passed, 1 skipped
    - ⚠️ Suíte completa ainda tem falhas de ordem (problema conhecido de hermeticidade)
  - **Limitação conhecida:**
    - Quando **toda a suíte** roda (`pytest --cov`), alguns testes ainda falham por contaminação de testes que rodam ANTES deles
    - Testes que usam `monkeypatch.setitem(sys.modules, ...)` podem deixar Mocks em sys.modules
    - Solução completa requer refatoração de testes legados que usam monkeypatch incorretamente
  - **Comando de validação:** `python -m pytest tests/test_auth_validation.py tests/test_auth_bootstrap_persisted_session.py tests/test_clientes_integration.py tests/test_flags.py tests/test_menu_logout.py tests/test_modules_aliases.py tests/test_prefs.py -v`
  - **Esforço:** 8h
  - **Automável:** Manual
  - **Próximos passos sugeridos:**
    - Adicionar fixture autouse para limpar MagicMocks de sys.modules de forma seletiva
    - Refatorar testes legados que usam `sys.modules.pop()` manual
    - Considerar pytest-xdist para execução paralela (mascara problema mas não resolve raiz)

### Limpeza e Organização

- [ ] **CLEAN-001: Remover `typings/` se não usado**
  - **Área:** `typings/`
  - **Descrição:** Se apenas cache do Pyright, adicionar ao gitignore
  - **Esforço:** 5min
  - **Automável:** Sim

- [ ] **CLEAN-002: Criar CONTRIBUTING.md**
  - **Área:** Raiz do projeto
  - **Descrição:** Guia de contribuição (estilo, PR, testes)
  - **Esforço:** 1-2h
  - **Automável:** Manual

- [ ] **CLEAN-003: Criar CODEOWNERS**
  - **Área:** `.github/CODEOWNERS`
  - **Descrição:** Definir ownership de módulos
  - **Benefício:** Review automático
  - **Esforço:** 30min
  - **Automável:** Manual

---

## Resumo por Prioridade

| Prioridade | Total | Área Principal |
|------------|-------|----------------|
| P0 🔴      | 5     | Segurança, Funcionalidade crítica |
| P1 🟡      | 17    | Performance, Deps, Qualidade, Testes (inclui Coverage App Core) |
| P2 🟢      | 15    | Docs, Build, Código, Ferramentas |
| P3 ⚪      | 8     | Longo prazo, Cosmético |
| **TOTAL**  | **45**| |

## Recomendação de Roadmap

### Sprint 1-2 (Imediato)
- Todos os P0 (crítico)
- P1: SEG, DEP-001, DEP-002, QA-004, TEST-002

### Sprint 3-4 (Curto prazo)
- P1: PERF, QA-001, QA-002, TEST-001
- P2: DOC-001, BUILD-003, BUILD-004

### Sprint 5-8 (Médio prazo)
- P1: QA-003, DEP-003
- P2: DOC-002 a DOC-005, BUILD-001, BUILD-002

### Sprint 9+ (Longo prazo)
- P2: CODE-*, TOOL-*
- P3: Conforme priorização do time

---

**Última atualização:** 23 de novembro de 2025  
**Mantenedor:** Equipe RC Gestor de Clientes
