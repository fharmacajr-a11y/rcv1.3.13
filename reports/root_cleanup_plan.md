# Plano de Limpeza da Raiz do Projeto

**Data:** 2025-12-04  
**Versão do Projeto:** v1.3.61  
**Branch:** qa/fixpack-04

## Contexto

Este documento classifica todos os itens na raiz do projeto RC Gestor para identificar arquivos/pastas que podem ser removidos com segurança.

**Nota:** Não foi encontrado arquivo `.zip` de release na raiz do projeto para usar como referência. A classificação foi feita com base nas regras fornecidas e análise do conteúdo dos arquivos.

---

## Legenda de Categorias

| Categoria | Descrição |
|-----------|-----------|
| **ESSENCIAL** | Arquivo/pasta necessário para código, build ou configuração do projeto |
| **GERADO / TEMPORÁRIO** | Cache, log, relatório de ferramenta ou arquivo de debug temporário |
| **DÚVIDA** | Item que requer avaliação manual |

---

## Classificação dos Itens da Raiz

| Item | Tipo | Categoria | Motivo | Ação Sugerida | Status |
|------|------|-----------|--------|---------------|--------|
| `.bandit` | arquivo | ESSENCIAL | Configuração do Bandit (security linter) | manter | - |
| `.coveragerc` | arquivo | ESSENCIAL | Configuração do coverage.py | manter | - |
| `.editorconfig` | arquivo | ESSENCIAL | Configuração de formatação do editor | manter | - |
| `.env` | arquivo | ESSENCIAL | Variáveis de ambiente (produção/dev) | manter | - |
| `.env.backup` | arquivo | DÚVIDA | Backup de .env - pode ser temporário ou importante | avaliar manualmente | - |
| `.env.example` | arquivo | ESSENCIAL | Template de variáveis de ambiente | manter | - |
| `.git/` | pasta | ESSENCIAL | Repositório Git | manter | - |
| `.gitattributes` | arquivo | ESSENCIAL | Configuração do Git | manter | - |
| `.github/` | pasta | ESSENCIAL | Workflows e configurações do GitHub | manter | - |
| `.gitignore` | arquivo | ESSENCIAL | Lista de arquivos ignorados pelo Git | manter | - |
| `.pre-commit-config.yaml` | arquivo | ESSENCIAL | Configuração de hooks pre-commit | manter | - |
| `.pytest_cache/` | pasta | GERADO / TEMPORÁRIO | Cache do pytest | pode apagar | - |
| `.ruff_cache/` | pasta | GERADO / TEMPORÁRIO | Cache do ruff linter | pode apagar | - |
| `.venv/` | pasta | ESSENCIAL | Ambiente virtual Python (não deve ser apagado) | manter | - |
| `.vscode/` | pasta | ESSENCIAL | Configurações do VS Code para o projeto | manter | - |
| `adapters/` | pasta | ESSENCIAL | Código de adaptadores do projeto | manter | - |
| `assets/` | pasta | ESSENCIAL | Recursos visuais (imagens, ícones) | manter | - |
| `bandit.json` | arquivo | GERADO / TEMPORÁRIO | Relatório JSON do Bandit | pode apagar | - |
| `bandit_report.txt` | arquivo | GERADO / TEMPORÁRIO | Relatório texto do Bandit | pode apagar | - |
| `CHANGELOG.md` | arquivo | ESSENCIAL | Histórico de mudanças do projeto | manter | - |
| `config/` | pasta | ESSENCIAL | Configurações do projeto | manter | - |
| `config.yml` | arquivo | ESSENCIAL | Configuração principal YAML | manter | - |
| `CONTRIBUTING.md` | arquivo | ESSENCIAL | Guia de contribuição | manter | - |
| `coverage_annotate/` | pasta | GERADO / TEMPORÁRIO | Arquivos de anotação de cobertura | pode apagar | - |
| `data/` | pasta | ESSENCIAL | Código de dados/repositórios | manter | - |
| `docs/` | pasta | ESSENCIAL | Documentação do projeto | manter | - |
| `helpers/` | pasta | ESSENCIAL | Código auxiliar (contém `__init__.py`) | manter | - |
| `infra/` | pasta | ESSENCIAL | Código de infraestrutura | manter | - |
| `installer/` | pasta | ESSENCIAL | Scripts de instalação (Inno Setup) | manter | - |
| `main.py` | arquivo | ESSENCIAL | Entry point alternativo | manter | - |
| `migrations/` | pasta | ESSENCIAL | Migrações de banco de dados | manter | - |
| `oks/` | pasta | ESSENCIAL | Pasta do projeto (verificar conteúdo) | manter | - |
| `plan.txt` | arquivo | GERADO / TEMPORÁRIO | Arquivo vazio de planejamento temporário | pode apagar | - |
| `pyproject.toml` | arquivo | ESSENCIAL | Configuração do projeto Python | manter | - |
| `pyrightconfig.json` | arquivo | ESSENCIAL | Configuração do Pyright | manter | - |
| `pytest-clientes.log` | arquivo | GERADO / TEMPORÁRIO | Log de execução de testes | pode apagar | - |
| `pytest-full.log` | arquivo | GERADO / TEMPORÁRIO | Log de execução de testes | pode apagar | - |
| `pytest-unit-nocov.log` | arquivo | GERADO / TEMPORÁRIO | Log de execução de testes | pode apagar | - |
| `pytest-unit-noeditor.log` | arquivo | GERADO / TEMPORÁRIO | Log de execução de testes | pode apagar | - |
| `pytest-unit-notform.log` | arquivo | GERADO / TEMPORÁRIO | Log de execução de testes | pode apagar | - |
| `pytest-unit.log` | arquivo | GERADO / TEMPORÁRIO | Log de execução de testes | pode apagar | - |
| `pytest.ini` | arquivo | ESSENCIAL | Configuração do pytest | manter | - |
| `rc.ico` | arquivo | ESSENCIAL | Ícone do aplicativo (Windows) | manter | - |
| `rc.png` | arquivo | ESSENCIAL | Ícone do aplicativo (PNG) | manter | - |
| `rcgestor.spec` | arquivo | ESSENCIAL | Spec do PyInstaller para build | manter | - |
| `README.md` | arquivo | ESSENCIAL | Documentação principal | manter | - |
| `reports/` | pasta | ESSENCIAL | Relatórios do projeto | manter | - |
| `requirements-dev.txt` | arquivo | ESSENCIAL | Dependências de desenvolvimento | manter | - |
| `requirements.in` | arquivo | ESSENCIAL | Dependências base (pip-tools) | manter | - |
| `requirements.txt` | arquivo | ESSENCIAL | Dependências de produção | manter | - |
| `ruff.toml` | arquivo | ESSENCIAL | Configuração do ruff linter | manter | - |
| `security/` | pasta | ESSENCIAL | Código de segurança | manter | - |
| `sitecustomize.py` | arquivo | ESSENCIAL | Customização do Python (configura sys.path) | manter | - |
| `src/` | pasta | ESSENCIAL | Código-fonte principal | manter | - |
| `tests/` | pasta | ESSENCIAL | Testes do projeto | manter | - |
| `test_combobox_style_debug.py` | arquivo | GERADO / TEMPORÁRIO | Script de debug temporário (não é teste real) | pode apagar | - |
| `test_error.txt` | arquivo | GERADO / TEMPORÁRIO | Arquivo vazio de erro de teste | pode apagar | - |
| `third_party/` | pasta | ESSENCIAL | Bibliotecas de terceiros | manter | - |
| `typings/` | pasta | ESSENCIAL | Stubs de tipos para type checking | manter | - |
| `version_file.txt` | arquivo | ESSENCIAL | Metadados de versão (PyInstaller) | manter | - |
| `warn-test.log` | arquivo | GERADO / TEMPORÁRIO | Log de warnings de teste | pode apagar | - |
| `__pycache__/` | pasta | GERADO / TEMPORÁRIO | Cache de bytecode Python | pode apagar | - |

---

## Resumo

### Itens que PODEM SER APAGADOS (GERADO / TEMPORÁRIO)

| Item | Tipo | Motivo |
|------|------|--------|
| `.pytest_cache/` | pasta | Cache do pytest |
| `.ruff_cache/` | pasta | Cache do ruff linter |
| `bandit.json` | arquivo | Relatório JSON do Bandit |
| `bandit_report.txt` | arquivo | Relatório texto do Bandit |
| `coverage_annotate/` | pasta | Arquivos de anotação de cobertura |
| `plan.txt` | arquivo | Arquivo vazio de planejamento temporário |
| `pytest-clientes.log` | arquivo | Log de execução de testes |
| `pytest-full.log` | arquivo | Log de execução de testes |
| `pytest-unit-nocov.log` | arquivo | Log de execução de testes |
| `pytest-unit-noeditor.log` | arquivo | Log de execução de testes |
| `pytest-unit-notform.log` | arquivo | Log de execução de testes |
| `pytest-unit.log` | arquivo | Log de execução de testes |
| `test_combobox_style_debug.py` | arquivo | Script de debug temporário |
| `test_error.txt` | arquivo | Arquivo vazio de erro de teste |
| `warn-test.log` | arquivo | Log de warnings de teste |
| `__pycache__/` | pasta | Cache de bytecode Python |

**Total: 16 itens**

### Itens que REQUEREM AVALIAÇÃO MANUAL (DÚVIDA)

| Item | Tipo | Motivo |
|------|------|--------|
| `.env.backup` | arquivo | Backup de .env - pode ser temporário ou importante |

**Total: 1 item**

---

## Histórico de Execução

| Data | Ação | Itens Afetados |
|------|------|----------------|
| 2025-12-04 | Plano criado | - |
| 2025-12-04 | Limpeza executada | 16 itens removidos |
| 2025-12-04 | Pastas ESSENCIAIS verificadas | `installer/`, `migrations/`, `typings/`, `oks/` – todas existentes |
| 2025-12-04 | `.venv` antigo renomeado | `.venv` → `.venv_backup_20251204` (recriação de ambiente) |
| 2025-12-04 | Ambiente virtual recriado | `.venv` novo criado, dependências instaladas a partir de requirements.txt e requirements-dev.txt |

---

## Itens Removidos (2025-12-04)

✅ **Pastas removidas (4):**
- `.pytest_cache/`
- `.ruff_cache/`
- `__pycache__/`
- `coverage_annotate/`

✅ **Arquivos removidos (12):**
- `bandit.json`
- `bandit_report.txt`
- `plan.txt`
- `test_error.txt`
- `warn-test.log`
- `pytest-clientes.log`
- `pytest-full.log`
- `pytest-unit-nocov.log`
- `pytest-unit-noeditor.log`
- `pytest-unit-notform.log`
- `pytest-unit.log`
- `test_combobox_style_debug.py`

---

## Itens Mantidos para Avaliação Manual

⚠️ `.env.backup` - Verificar se contém dados importantes antes de remover

---

## Pastas ESSENCIAIS confirmadas (resumo)

**Verificação realizada em:** 2025-12-04

Todas as pastas abaixo foram confirmadas como **existentes no disco** e classificadas como **ESSENCIAL**:

- `installer/` – manter (scripts de instalação Inno Setup)
- `migrations/` – manter (migrações de banco de dados)
- `typings/` – manter (stubs de tipos para type checking)
- `oks/` – manter (pasta de arquivos específicos do fluxo RC Gestor)
- `src/` – manter (código-fonte principal)
- `tests/` – manter (testes do projeto)
- `infra/` – manter (código de infraestrutura)
- `adapters/` – manter (código de adaptadores)
- `data/` – manter (código de dados/repositórios)
- `helpers/` – manter (código auxiliar)
- `security/` – manter (código de segurança)
- `docs/` – manter (documentação do projeto)
- `assets/` – manter (recursos visuais)
- `config/` – manter (configurações do projeto)
- `third_party/` – manter (bibliotecas de terceiros)
- `reports/` – manter (relatórios do projeto)
- `.github/` – manter (workflows e configurações GitHub)
- `.vscode/` – manter (configurações do VS Code)
- `.git/` – manter (repositório Git)
