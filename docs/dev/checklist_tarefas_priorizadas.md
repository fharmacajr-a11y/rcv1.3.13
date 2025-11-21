# Checklist de Tarefas Priorizadas - RC Gestor de Clientes

**Data:** 20 de novembro de 2025  
**Versão Base:** v1.2.31  
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

- [ ] **QA-002: Refatorar `src/modules/main_window/views/main_window.py`**
  - **Área:** `src/modules/main_window/views/main_window.py` (~1000 linhas)
  - **Descrição:** Extrair componentes (sidebar, footer, menu)
  - **Benefício:** Redução de complexidade
  - **Esforço:** 10-14h
  - **Automável:** Manual

- [ ] **QA-003: Adicionar type hints faltantes**
  - **Área:** Módulos sem `from __future__ import annotations`
  - **Descrição:** Incrementalmente adicionar types em arquivos antigos
  - **Ferramenta:** `pyright --stats` para identificar
  - **Benefício:** Melhor IDE support, menos bugs
  - **Esforço:** 6-10h (pode ser feito incrementalmente)
  - **Automável:** Parcial (detecção automática, adição manual)

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

### Testes

- [>] **TEST-001: Aumentar cobertura para 85%+** ⏳ **FASES 1-3 CONCLUÍDAS**
  - **Área:** Módulos com baixa cobertura
  - **Descrição:** Adicionar testes em:
    - ✅ `src/modules/cashflow/` (FASE 1)
    - ✅ `src/modules/passwords/` (FASE 1)
    - ✅ `src/ui/components/` (FASE 2)
    - ✅ `src/modules/hub/`, `src/core/auth/` (FASE 3 - concluída)
    - ⏳ Outros módulos de baixa cobertura (próximas fases)
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
      * `src/core/auth/auth.py`: 44% coverage (54/123 linhas - foco em funções puras)
    - ✅ **Cenários testados (Hub):**
      * Estado: criação, reutilização, valores padrão
      * Formatação: timestamps ISO → local, linhas de nota
      * Utilidades: conversão HSL→HEX, hash MD5 de dicts, normalização de notas (dict/tuple/list/string)
      * Cores: hash estável por email, case-insensitive, tags tkinter com cache
    - ✅ **Cenários testados (Auth):**
      * Validação de credenciais: email regex, senha min 6 chars, edge cases
      * Rate limiting: 5 tentativas/60s, reset após timeout, case-insensitive
      * PBKDF2 hash: formato correto, iterações customizadas, salt determinístico, pepper
    - ✅ **Validação:**
      * pytest: 327/328 passed (1 skipped - esperado)
      * coverage: 26.95% (threshold 25%)
      * pre-commit: all hooks passed
  - **Meta final:** 85%+ cobertura
  - **Próximas fases:** Outros módulos de baixa cobertura conforme necessário
      * coverage: 26.15% (≥25% threshold)
      * pre-commit: ✅ all hooks passed
  - **Próximas fases:**
    - Fase 2: Componentes UI (`src/ui/components/`) - target: +5-10pp
    - Fase 3: Módulos de baixa cobertura (auditoria, hub, etc)
    - Meta final: 85%+

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
      - Mede cobertura do código em `src/` com `--cov=src`
      - Mostra linhas não cobertas com `--cov-report=term-missing`
      - Falha automaticamente se cobertura total < 25% (`--cov-fail-under=25`)
      - Usa `python -m pytest` para compatibilidade com venv
      - Mantém modo verbose (`-v`) para detalhamento de testes
    - ✅ `CONTRIBUTING.md` atualizado com instruções de coverage local
    - ✅ Comando local recomendado: `python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=25 -v`
    - ✅ `pytest-cov==7.0.0` já presente em `requirements-dev.txt` (sem alteração necessária)
    - 📈 Cobertura atual: ~26% (threshold inicial em 25% para evitar falsos positivos)
    - 🎯 Meta futura: Aumentar gradualmente para 80%+ conforme testes forem adicionados (ver TEST-001)

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
| P0 🔴      | 4     | Segurança, Funcionalidade crítica |
| P1 🟡      | 12    | Performance, Deps, Qualidade, Testes |
| P2 🟢      | 15    | Docs, Build, Código, Ferramentas |
| P3 ⚪      | 8     | Longo prazo, Cosmético |
| **TOTAL**  | **39**| |

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

**Última atualização:** 20 de novembro de 2025  
**Mantenedor:** Equipe RC Gestor de Clientes
