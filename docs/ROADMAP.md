# 🗺️ Roadmap do Projeto - Histórico de Fases

**Documento vivo:** Atualizado conforme evolução do projeto

---

## 📖 Contexto Histórico

Este projeto passou por diversas fases de evolução, desde a refatoração estrutural até a migração completa de UI para CustomTkinter e estabelecimento de CI/CD robusto.

---

## FASE 1-3: Fundação (2024-2025)

### Contexto Inicial

- **Base:** Python 3.11, ttkbootstrap para UI
- **Estrutura:** Monolítico, poucos testes
- **Desafios:** Código acoplado, sem type hints, dependências desorganizadas

### Principais Realizações

- ✅ Refatoração para src-layout
- ✅ Separação de concerns (adapters, infra, core)
- ✅ Implementação de testes unitários básicos
- ✅ Migração inicial de módulos críticos

**Documentação completa:** [refactor/v1.5.35/](refactor/v1.5.35/)

---

## FASE 4: Limpeza e Segurança (Jan 2026)

### FASE 4.3: Dead Code + Bandit

**Data:** 2026-01-24  
**Duração:** ~2 horas  
**Status:** ✅ Concluído

#### Objetivos

1. Remover código morto com Vulture
2. Validar segurança com Bandit
3. Garantir CI/CD estável com pre-commit
4. Documentar resultados para auditoria

#### Execução

**1. Dead Code Removal (Vulture)**

```bash
vulture src/ tests/ --min-confidence 80
```

**Resultados:**
- 16 issues globais (imports não usados)
- 0 issues em `src/modules/clientes/` ✅
- 19 legacy form files identificados para arquivamento

**Ação:** Criado whitelist (`vulture_whitelist.py`) para false positives

**2. Bandit Security Scan**

```bash
bandit -c .bandit -r src infra adapters data security
```

**Issues encontradas:**
- B112 (try-except-continue) em fallback patterns
- B606/B404 (subprocess) em file operations
- B603/B607 (shell=False) em xdg-open

**Solução:** Tratamento pontual com `# nosec` + justificativas

**3. Pre-commit Integration**

- 20 hooks configurados
- Bandit integrado com UTF-8 safe encoding
- Validação automática em todos os commits

#### Resultados

- ✅ **0 security issues** (todos tratados)
- ✅ **Pre-commit 100% verde**
- ✅ **Código limpo** (dead code removido)
- ✅ **Whitelist documentada** (vulture_whitelist.py)

**Documentação:** Arquivado em [_archive/FASE_4.3_RESUMO.md](_archive/FASE_4.3_RESUMO.md)

---

## FASE 5: Release + CI Estável (Jan 2026)

**Data:** 2026-01-24  
**Tag:** `v1.5.62-fase4.3`  
**Commit:** `6ea22e2`  
**Status:** ✅ Concluído

### Objetivos

1. Corrigir Bandit/Unicode no pre-commit (Windows)
2. Padronizar encoding no CI/DevEnv
3. Criar tag anotada de release
4. Verificação final de estabilidade

### Problema: UTF-8 no Windows

**Erro:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2705'
in position 2000: character maps to <undefined>
```

**Causa:** Windows usa cp1252 por padrão, incompatível com emojis nos outputs do Bandit

### Solução Implementada

**1. Bandit UTF-8 Safe Wrapper**

Criado hook personalizado em `.pre-commit-config.yaml`:

```yaml
- id: bandit-utf8-safe
  name: Bandit Security Scan (UTF-8 safe)
  entry: python -X utf8 -m bandit
  language: system
  types: [python]
  args: [-c, .bandit, -r, src, infra, adapters, data, security]
```

**2. Encoding Global**

```powershell
$env:PYTHONUTF8=1
$env:PYTHONIOENCODING="utf-8"
```

**3. Tag Anotada**

```bash
git tag -a v1.5.62-fase4.3 -m "Release FASE 4.3 - Security + CI"
git push origin v1.5.62-fase4.3
```

### Resultados

- ✅ **Pre-commit funcional no Windows**
- ✅ **UTF-8 garantido em todos os ambientes**
- ✅ **Release taggeada**
- ✅ **Documentação atualizada**

**Documentação:** Arquivado em [_archive/FASE_5_RELEASE.md](_archive/FASE_5_RELEASE.md)

---

## FASE 6: CI/CD Robusto + Staging (Jan 2026)

**Data:** 2026-01-24  
**Versão:** 1.5.62  
**Status:** ✅ Concluído

### Objetivos

1. Workflow de CI robusto para Windows e Linux
2. Encoding UTF-8 garantido em todos os pipelines
3. Release automatizada via tags anotadas
4. Checklist de Staging para validação manual

### Contexto

**Problemas Identificados:**
- FASE 5 rodava localmente com `python -X utf8`, mas CI não configurado
- Processo de release manual, sem validação completa
- Sem roteiro documentado para smoke tests

### Solução Implementada

**1. Workflows CI/CD**

- ✅ GitHub Actions configurado (`.github/workflows/`)
- ✅ Encoding UTF-8 nativo no Windows
- ✅ Matrix testing (Linux + Windows)
- ✅ Validação em pull requests

**2. Release Automatizada**

```bash
# 1. Criar tag anotada
git tag -a v1.5.63 -m "Release v1.5.63 - Feature X"

# 2. Push (dispara workflow)
git push origin v1.5.63

# 3. Workflow cria release automaticamente
```

**3. Staging Checklist**

Criado roteiro completo de smoke test manual:
- Login e autenticação
- CRUD de clientes
- Upload de arquivos
- Exportação de dados
- Navegação entre módulos

**Documentação:** [ci/STAGING_CHECKLIST.md](ci/STAGING_CHECKLIST.md)

**4. Quick Reference**

Guia rápido para desenvolvimento diário:
- Comandos essenciais
- Workflow de dev/release
- Troubleshooting comum

**Documentação:** [ci/REFERENCE.md](ci/REFERENCE.md)

### Resultados

- ✅ **CI rodando sem erros de encoding**
- ✅ **Pre-commit + Bandit integrados**
- ✅ **Release process documentado**
- ✅ **Staging checklist completo**
- ✅ **20/20 hooks passando**

**Documentação:** Arquivado em [_archive/FASE_6_CI_RELEASE.md](_archive/FASE_6_CI_RELEASE.md) e [_archive/FASE_6_RESUMO.md](_archive/FASE_6_RESUMO.md)

---

## FASE 7: Organização e Consolidação (Jan 2026)

**Data:** 2026-01-26  
**Status:** 🔄 Em andamento

### Objetivos

1. Limpar raiz do repositório (82→52 itens)
2. Organizar documentação (docs/ 120→46 ativos)
3. Garantir `src/core/logs` versionado (safe com git clean)
4. Otimizar disk space (remover caches e artifacts)

### 7.1: Reorganização do Repositório

**PR:** [#10](https://github.com/fharmacajr-a11y/rcv1.3.13/pull/10)  
**Branch:** `chore/organize-repo-structure`  
**Commits:** 5 (74d07f0 → 661278f)

**Mudanças:**

1. **Documentação → docs/**
   - 17 arquivos movidos para docs/patches/, docs/reports/
   - Índice completo criado em docs/README.md

2. **Scripts → tools/migration/**
   - fix_ctk_advanced.py, fix_ctk_padding.py
   - test_ctktreeview.py → tests/experiments/

3. **Artefatos → artifacts/local/**
   - 15 arquivos temporários (audit_*.txt, hub_*.txt)
   - diagnostics/ desversionado

4. **Ferramentas → tools/repo/**
   - cleanup_repo.ps1, cleanup_repo.sh
   - EXECUTION_GUIDE.md, gitignore_additions.txt

5. **Fix Critical: src/core/logs/**
   - Implementado módulo real de logging
   - Garantido versionamento (não removido por git clean -fdX)
   - Sem side effects no import

**Resultados:**
- ✅ **52 itens na raiz** (antes: 82) - **-37%**
- ✅ **Pre-commit 20/20 passing**
- ✅ **Pytest 112/112 passing**
- ✅ **Ruff 0 errors**

### 7.2: Limpeza de Disk Space

**Objetivo:** Reduzir tamanho do workspace removendo artifacts recriáveis

**Ação executada:**
```bash
git clean -fdX  # Remove arquivos ignorados
```

**Resultados:**
- ✅ **568 MB economizados** (591 MB → 23 MB)
- ✅ Removidos: .venv (376 MB), .mypy_cache (82 MB), htmlcov (28 MB)
- ⚠️ **Incidente:** src/core/logs/ foi removido (estava ignorado)
- ✅ **Resolução:** Módulo recriado e versionado (commit 661278f)

**Ambiente recriado:**
- Python 3.13.7 + pip 25.3
- Dependências reinstaladas
- Validações 100% verde

### 7.3: Consolidação de Documentação

**Branch:** `chore/docs-consolidation` (atual)  
**Objetivo:** Reduzir docs/ de 120 para 46 arquivos ativos

**Estrutura proposta:**

```
docs/
├── STATUS.md (novo) - Estado atual + próximos passos
├── ROADMAP.md (novo) - Este documento
├── ci/ - Referências de CI/CD
├── releases/ - Notas de release consolidadas
├── customtk/ - Migração CustomTkinter consolidada
├── patches/, guides/, cronologia/ - Mantidos
└── _archive/ - 74 arquivos históricos
```

**Em execução:** Esta fase

---

## FASE 8+: Planejamento Futuro

### 8.1: Estabilização de Testes

- Resolver 36 erros de coleta em testes legacy
- Atualizar imports para nova estrutura
- Meta: 150+ testes passando

### 8.2: Type Safety

- Reduzir Pyright errors (61→30)
- Adicionar type hints incrementais
- Configurar Pyright no pre-commit

### 8.3: v1.6.0 - Migração CTK Completa

- Completar migração de todos os módulos
- Remover dependências de ttkbootstrap
- Atualizar para Python 3.13 oficial no PyInstaller

### 8.4: CI/CD Avançado

- GitHub Actions matrix (Python 3.11, 3.12, 3.13)
- Build automatizado de executáveis
- Deploy para staging automático

---

## 📚 Lições Aprendidas

### Encoding e CI/CD

- **Lição:** UTF-8 não é padrão no Windows
- **Solução:** `python -X utf8` + env vars
- **Impacto:** 100% dos problemas de encoding resolvidos

### Git Clean e Versionamento

- **Lição:** `git clean -fdX` remove arquivos ignorados, mesmo com código
- **Solução:** Usar exceções no .gitignore (`!src/core/logs/`)
- **Impacto:** Código crítico protegido

### Organização de Repositório

- **Lição:** Raiz limpa facilita navegação
- **Solução:** Mover docs para docs/, scripts para tools/
- **Impacto:** -37% itens na raiz, -62% docs ativos

### Pre-commit Hooks

- **Lição:** Validação automática previne regressões
- **Solução:** 20 hooks cobrindo qualidade, segurança, formatação
- **Impacto:** Zero surpresas no CI

---

## 🔗 Navegação

### Documentação Técnica

- [STATUS.md](STATUS.md) - Estado atual e checklist
- [ci/REFERENCE.md](ci/REFERENCE.md) - Quick reference
- [ci/STAGING_CHECKLIST.md](ci/STAGING_CHECKLIST.md) - Smoke test
- [releases/RELEASE_NOTES.md](releases/RELEASE_NOTES.md) - Releases
- [customtk/MIGRATION_SUMMARY.md](customtk/MIGRATION_SUMMARY.md) - Migração CTK

### Histórico Arquivado

- [_archive/](archive/) - Documentação histórica de fases
- [customtk/_archive/](customtk/_archive/) - 53 microfases da migração CTK

---

**Fim do Roadmap**

*Este documento é atualizado a cada marco importante do projeto.*
