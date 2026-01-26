# 📋 Plano de Consolidação de docs/

**Gerado em:** 26 de janeiro de 2026  
**Status:** PLANEJAMENTO (NÃO EXECUTAR AINDA)

---

## 1. INVENTÁRIO COMPLETO

### Estrutura Atual

```
docs/ (120 arquivos)
├── [RAIZ] 7 arquivos
│   ├── FASE_4.3_RESUMO.md (6.4 KB)
│   ├── FASE_5_RELEASE.md (5.6 KB)
│   ├── FASE_6_CI_RELEASE.md (9.7 KB)
│   ├── FASE_6_RESUMO.md (6.6 KB)
│   ├── QUICK_REFERENCE_CI.md (4.9 KB)
│   ├── README.md (3 KB)
│   └── STAGING_CHECKLIST.md (6.5 KB)
│
├── cronologia/ (2 arquivos)
│   ├── Cronologia de App.pdf
│   └── Cronologia de App2.pdf
│
├── customtk_clientes/ (71 arquivos)
│   ├── README.md (índice)
│   ├── PLANO_MIGRACAO_CUSTOMTKINTER.md
│   ├── [53 RELATÓRIOS] MICROFASE_*_RELATORIO*.md
│   └── [16 TÉCNICOS] CTK_*.md, *_POLICY.md
│
├── guides/ (1 arquivo)
│   └── MIGRACAO_CTK_GUIA_COMPLETO.ipynb
│
├── patches/ (5 arquivos)
│   ├── ANALISE_MIGRACAO_CTK_CLIENTESV2.md
│   ├── PATCH_CLIENTESV2_DOUBLECLICK_FLASH.md
│   ├── PATCH_CLIENT_FILES_BROWSER.md
│   ├── PATCH_FIX_FILES_BROWSER_ACCESS.md
│   └── PATCH_V2_DOUBLECLICK_DETERMINISTICO.md
│
├── refactor/v1.5.35/ (15 arquivos)
│   ├── README.md
│   ├── [12 DOCS] 00_contexto*.md até 12_fase7*.md
│   └── test_runs/ (6 arquivos TXT grandes: 3-12 MB)
│
└── reports/ (11 arquivos)
    ├── microfases/ (4 arquivos)
    │   ├── RELATORIO_MICROFASE_35.md
    │   ├── MICROFASE_36_RELATORIO_FINAL.md
    │   ├── RELATORIO_MICROFASE_37.md
    │   └── RELATORIO_MIGRACAO_CTK_COMPLETA.md
    └── releases/ (7 arquivos)
        ├── CI_GREEN_REPORT.md
        ├── CREATE_PR_INSTRUCTIONS.md
        ├── EXECUTIVE_SUMMARY.md
        ├── GATE_FINAL.md
        ├── NEXT_STEPS.md
        ├── PR_DESCRIPTION.md
        └── RELEASE_STATUS.md
```

### Categorização por Tipo

| Categoria | Quantidade | Localização |
|-----------|------------|-------------|
| **Status/Roadmap** | 4 | docs/FASE_*.md |
| **CI/Reference** | 2 | docs/QUICK_REFERENCE_CI.md, STAGING_CHECKLIST.md |
| **Patches** | 5 | docs/patches/ |
| **Guias** | 1 | docs/guides/ |
| **Microfases (CTK)** | 53 | docs/customtk_clientes/MICROFASE_*.md |
| **Microfases (raiz)** | 4 | docs/reports/microfases/ |
| **Releases** | 7 | docs/reports/releases/ |
| **Refactor** | 15 | docs/refactor/v1.5.35/ |
| **Cronologia** | 2 | docs/cronologia/ |
| **README** | 3 | docs/, docs/customtk_clientes/, docs/refactor/v1.5.35/ |

**TOTAL:** 120 arquivos

---

## 2. DUPLICAÇÕES DETECTADAS

### 2.1 Estrutura Repetitiva (FASE_*.md)

**Todos os 4 arquivos FASE_* seguem o mesmo template:**

```markdown
# FASE X: [Título]
Data: 2026-01-24
Status: ✅ CONCLUÍDO

## 📋 Objetivos
[lista de objetivos]

## ✅ Execução
[passos executados]

## 📊 Resultados
[métricas e validações]

## 🎯 Próximos Passos
[ações futuras]
```

**Análise de Conteúdo:**

| Arquivo | Tamanho | Seções | Sobreposição |
|---------|---------|--------|--------------|
| FASE_4.3_RESUMO.md | 6.5 KB | 7 H2 | ~30% com FASE_5 (dead code + Bandit) |
| FASE_5_RELEASE.md | 5.8 KB | 7 H2 | ~40% com FASE_6 (UTF-8 + CI) |
| FASE_6_CI_RELEASE.md | 9.9 KB | 11 H2 | ~50% com FASE_6_RESUMO (CI completo) |
| FASE_6_RESUMO.md | 6.8 KB | 10 H2 | Resumo do FASE_6_CI_RELEASE |

**Duplicações Específicas:**

1. **FASE_6_CI_RELEASE.md vs FASE_6_RESUMO.md**
   - `FASE_6_RESUMO.md` é basicamente um sumário do `FASE_6_CI_RELEASE.md`
   - ~60% de conteúdo sobreposto (objetivos, arquivos criados, validações)
   - **Conclusão:** Um pode ser arquivado

2. **FASE_5_RELEASE.md vs FASE_6_CI_RELEASE.md**
   - Ambos documentam UTF-8 fix no CI
   - `FASE_6` expande sobre `FASE_5` (adiciona workflows, staging)
   - ~30% de conteúdo duplicado (encoding, Bandit config)

3. **QUICK_REFERENCE_CI.md vs FASE_6_CI_RELEASE.md**
   - `QUICK_REFERENCE` é versão condensada de `FASE_6` (comandos úteis)
   - Propósito diferente: FASE_6 = documentação completa, QUICK = guia rápido
   - **Conclusão:** Ambos úteis, mas poderiam ser consolidados

### 2.2 Relatórios de Microfases Espalhados

**Problema:** 57 relatórios de microfases em 2 locais:

- `docs/customtk_clientes/MICROFASE_*.md` (53 arquivos)
- `docs/reports/microfases/` (4 arquivos)

**Sobreposição:**
- `RELATORIO_MIGRACAO_CTK_COMPLETA.md` resume todas as 34 microfases anteriores
- Arquivos individuais (MICROFASE_2.md até MICROFASE_34.md) contêm detalhes que estão no relatório completo

**Estimativa:** ~70% do conteúdo dos 53 arquivos individuais está no relatório completo.

### 2.3 Documentos de Release Redundantes

**Em `docs/reports/releases/`:**

1. **EXECUTIVE_SUMMARY.md** + **RELEASE_STATUS.md**
   - Ambos descrevem status do projeto
   - Conteúdo ~40% sobreposto

2. **PR_DESCRIPTION.md** + **CREATE_PR_INSTRUCTIONS.md**
   - PR_DESCRIPTION é template de PR
   - CREATE_PR_INSTRUCTIONS ensina a criar PR
   - Propósito diferente mas relacionado

3. **GATE_FINAL.md** + **CI_GREEN_REPORT.md**
   - Ambos documentam validações finais
   - Conteúdo ~50% sobreposto

4. **NEXT_STEPS.md**
   - Documento de planejamento futuro
   - Pode estar desatualizado

---

## 3. PROPOSTA DE ESTRUTURA FINAL (ENXUTA)

```
docs/
├── README.md                    [MANTÉM] Índice principal
│
├── STATUS.md                    [NOVO] Estado atual + próximos passos
│   ├── Onde estamos agora
│   ├── Checklist rápido
│   ├── Issues conhecidos
│   └── Próximos marcos
│
├── ROADMAP.md                   [NOVO] Histórico consolidado
│   ├── FASE 1-3: [contexto histórico]
│   ├── FASE 4: Limpeza e segurança
│   ├── FASE 5: UTF-8 + Release
│   ├── FASE 6: CI/CD robusto
│   └── FASE 7+: Planejamento futuro
│
├── ci/
│   ├── README.md                [NOVO] Visão geral do CI/CD
│   ├── REFERENCE.md             [CONSOLIDADO] Quick reference + comandos
│   └── STAGING_CHECKLIST.md    [MANTÉM] Roteiro de smoke test
│
├── releases/
│   ├── RELEASE_NOTES.md         [CONSOLIDADO] Todas as releases
│   │   ├── v1.5.62 (FASE 4-6)
│   │   ├── v1.5.61 (...)
│   │   └── (...)
│   └── TEMPLATES.md             [CONSOLIDADO] Templates de PR/Release
│
├── customtk/
│   ├── README.md                [MANTÉM] Índice da migração CTK
│   ├── MIGRATION_SUMMARY.md     [CONSOLIDADO] Resumo completo
│   │   ├── Contexto e decisões
│   │   ├── Fases principais (resumo das 53 microfases)
│   │   └── Lições aprendidas
│   ├── TECHNICAL_DOCS.md        [CONSOLIDADO] Políticas e configs
│   │   ├── CTK_IMPORT_POLICY
│   │   ├── SECURITY_MODEL
│   │   ├── UI_AUDIT
│   │   └── (outros docs técnicos)
│   └── _archive/                [NOVO] Microfases individuais
│       └── MICROFASE_*.md       (53 arquivos arquivados)
│
├── refactor/
│   └── v1.5.35/                 [MANTÉM] Documentação da refatoração
│       ├── README.md
│       ├── [12 docs de fases]
│       └── test_runs/           ⚠️ (6 arquivos, 20+ MB total)
│
├── patches/                     [MANTÉM] 5 arquivos
│
├── guides/                      [MANTÉM] 1 notebook
│
├── cronologia/                  [MANTÉM] 2 PDFs
│
└── _archive/                    [NOVO] Docs obsoletos
    ├── FASE_4.3_RESUMO.md
    ├── FASE_5_RELEASE.md
    ├── FASE_6_CI_RELEASE.md
    ├── FASE_6_RESUMO.md
    └── releases/                (7 arquivos consolidados)
```

### Estrutura Reduzida

| Categoria | Antes | Depois | Redução |
|-----------|-------|--------|---------|
| **Raiz docs/** | 7 | 3 | -4 (-57%) |
| **customtk/** | 71 | 5 + _archive/ | -66 arquivos na raiz |
| **releases/** | 7 | 2 | -5 (-71%) |
| **ci/** | 2 na raiz | 3 em ci/ | Organizado |
| **Outros** | 33 | 33 | Mantidos |
| **TOTAL** | 120 | ~46 + 74 archived | **-62% na estrutura ativa** |

---

## 4. MAPA DE MIGRAÇÃO (NÃO EXECUTAR)

### 4.1 Documentos FASE_* → ROADMAP.md

**Ação:** Consolidar em `docs/ROADMAP.md`

| Arquivo Atual | Destino | Ação | Conteúdo |
|--------------|---------|------|----------|
| FASE_4.3_RESUMO.md | ROADMAP.md | Virar seção "FASE 4" | Dead code + Bandit |
| FASE_5_RELEASE.md | ROADMAP.md | Virar seção "FASE 5" | UTF-8 + Release |
| FASE_6_CI_RELEASE.md | ROADMAP.md | Virar seção "FASE 6" | CI/CD completo |
| FASE_6_RESUMO.md | _archive/ | Arquivar (redundante com FASE_6_CI) | - |

**Comandos (NÃO EXECUTAR):**
```bash
# Criar ROADMAP.md consolidando os 3 principais
# (conteúdo será gerado manualmente)
git mv docs/FASE_4.3_RESUMO.md docs/_archive/
git mv docs/FASE_5_RELEASE.md docs/_archive/
git mv docs/FASE_6_CI_RELEASE.md docs/_archive/
git mv docs/FASE_6_RESUMO.md docs/_archive/
```

### 4.2 CI/Reference → ci/

**Ação:** Criar `docs/ci/` e consolidar

| Arquivo Atual | Destino | Ação |
|--------------|---------|------|
| QUICK_REFERENCE_CI.md | ci/REFERENCE.md | Mover + renomear |
| STAGING_CHECKLIST.md | ci/STAGING_CHECKLIST.md | Mover |
| (FASE_6_CI_RELEASE.md) | ci/README.md | Extrair seção "Configuração" |

**Comandos (NÃO EXECUTAR):**
```bash
mkdir -p docs/ci
git mv docs/QUICK_REFERENCE_CI.md docs/ci/REFERENCE.md
git mv docs/STAGING_CHECKLIST.md docs/ci/STAGING_CHECKLIST.md
# Criar docs/ci/README.md manualmente
```

### 4.3 Releases → releases/RELEASE_NOTES.md

**Ação:** Consolidar 7 arquivos em 2

| Arquivo Atual | Destino | Ação | Conteúdo |
|--------------|---------|------|----------|
| EXECUTIVE_SUMMARY.md | RELEASE_NOTES.md | Consolidar (seção intro) | Resumo executivo |
| RELEASE_STATUS.md | RELEASE_NOTES.md | Consolidar (seção status) | Estado atual |
| CI_GREEN_REPORT.md | RELEASE_NOTES.md | Consolidar (seção validações) | Validações CI |
| GATE_FINAL.md | RELEASE_NOTES.md | Consolidar (seção gate) | Critérios de gate |
| NEXT_STEPS.md | STATUS.md (raiz) | Mover para novo STATUS.md | Próximos passos |
| PR_DESCRIPTION.md | TEMPLATES.md | Consolidar | Template de PR |
| CREATE_PR_INSTRUCTIONS.md | TEMPLATES.md | Consolidar | Instruções PR |

**Comandos (NÃO EXECUTAR):**
```bash
# Criar docs/releases/RELEASE_NOTES.md consolidando 5 arquivos
# Criar docs/releases/TEMPLATES.md consolidando 2 arquivos
git mv docs/reports/releases docs/releases
git mv docs/reports/releases/*.md docs/_archive/releases/
```

### 4.4 CustomTk Clientes → customtk/

**Ação:** Arquivar 53 microfases individuais

| Arquivo Atual | Destino | Ação |
|--------------|---------|------|
| customtk_clientes/MICROFASE_*.md (53) | customtk/_archive/ | Arquivar todos |
| customtk_clientes/RELATORIO_*.md | MIGRATION_SUMMARY.md | Consolidar |
| customtk_clientes/CTK_*.md (16 técnicos) | TECHNICAL_DOCS.md | Consolidar |
| customtk_clientes/README.md | customtk/README.md | Mover |

**Comandos (NÃO EXECUTAR):**
```bash
# Renomear diretório
git mv docs/customtk_clientes docs/customtk

# Criar _archive/ e mover microfases
mkdir -p docs/customtk/_archive
git mv docs/customtk/MICROFASE_*.md docs/customtk/_archive/
git mv docs/customtk/CLIENTES_MICROFASE_*.md docs/customtk/_archive/

# Criar docs consolidados
# (MIGRATION_SUMMARY.md e TECHNICAL_DOCS.md serão criados manualmente)
```

### 4.5 Reports → STATUS.md (raiz)

**Ação:** Criar `docs/STATUS.md` com status atual

| Arquivo Atual | Destino | Ação |
|--------------|---------|------|
| reports/releases/NEXT_STEPS.md | STATUS.md | Extrair próximos passos |
| reports/releases/RELEASE_STATUS.md | STATUS.md | Extrair estado atual |
| reports/microfases/MICROFASE_37.md | STATUS.md | Extrair última fase |

**Comandos (NÃO EXECUTAR):**
```bash
# Criar docs/STATUS.md manualmente consolidando 3 fontes
```

---

## 5. LINKS A ATUALIZAR

### 5.1 Em docs/README.md

**Antes:**
```markdown
- [FASE_4.3_RESUMO.md](FASE_4.3_RESUMO.md)
- [FASE_5_RELEASE.md](FASE_5_RELEASE.md)
- [FASE_6_CI_RELEASE.md](FASE_6_CI_RELEASE.md)
- [FASE_6_RESUMO.md](FASE_6_RESUMO.md)
- [QUICK_REFERENCE_CI.md](QUICK_REFERENCE_CI.md)
```

**Depois:**
```markdown
- [STATUS.md](STATUS.md) - Estado atual do projeto
- [ROADMAP.md](ROADMAP.md) - Histórico de fases
- [ci/REFERENCE.md](ci/REFERENCE.md) - Quick reference CI/CD
- [ci/STAGING_CHECKLIST.md](ci/STAGING_CHECKLIST.md)
```

### 5.2 Em README.md (raiz)

**Verificar se há referências a:**
- `docs/FASE_*.md`
- `docs/QUICK_REFERENCE_CI.md`
- `docs/customtk_clientes/`

**Atualizar para:**
- `docs/ROADMAP.md`
- `docs/ci/REFERENCE.md`
- `docs/customtk/`

### 5.3 Em PR_BODY.md / CONTRIBUTING.md

**Verificar se há links para:**
- Documentos FASE_*
- Relatórios em `docs/reports/`

**Atualizar para estrutura nova.**

---

## 6. ENTREGÁVEL - PLANO OBJETIVO

### 6.1 Arquivos Finais (13 arquivos principais)

**Raiz docs/ (3):**
1. `README.md` - Índice (atualizado)
2. `STATUS.md` - Estado atual + próximos passos (NOVO)
3. `ROADMAP.md` - Histórico consolidado de fases (NOVO)

**ci/ (3):**
4. `ci/README.md` - Visão geral CI/CD (NOVO)
5. `ci/REFERENCE.md` - Quick reference (ex-QUICK_REFERENCE_CI.md)
6. `ci/STAGING_CHECKLIST.md` - Roteiro smoke test (mantém)

**releases/ (2):**
7. `releases/RELEASE_NOTES.md` - Consolidado de 5 docs (NOVO)
8. `releases/TEMPLATES.md` - Templates PR/Release (NOVO)

**customtk/ (5):**
9. `customtk/README.md` - Índice migração CTK (mantém)
10. `customtk/MIGRATION_SUMMARY.md` - Resumo completo (NOVO)
11. `customtk/TECHNICAL_DOCS.md` - Políticas técnicas (NOVO)
12. `customtk/_archive/` - 53 microfases (arquivadas)
13. `customtk/_archive/README.md` - Índice do arquivo (NOVO)

**Outros (mantidos):**
- `patches/` (5 arquivos)
- `guides/` (1 arquivo)
- `cronologia/` (2 arquivos)
- `refactor/v1.5.35/` (15 arquivos)

---

### 6.2 Arquivos a Consolidar (18 arquivos)

**FASE_* (4) → ROADMAP.md:**
- FASE_4.3_RESUMO.md
- FASE_5_RELEASE.md
- FASE_6_CI_RELEASE.md
- FASE_6_RESUMO.md (redundante)

**Releases (7) → releases/RELEASE_NOTES.md + TEMPLATES.md:**
- EXECUTIVE_SUMMARY.md
- RELEASE_STATUS.md
- CI_GREEN_REPORT.md
- GATE_FINAL.md
- NEXT_STEPS.md
- PR_DESCRIPTION.md
- CREATE_PR_INSTRUCTIONS.md

**CustomTk Técnicos (16) → customtk/TECHNICAL_DOCS.md:**
- CTK_IMPORT_POLICY.md
- CTK_VALIDATION_QUICKSTART.md
- SECURITY_MODEL.md
- UI_AUDIT.md
- ENFORCEMENT_PATCH.md
- ENFORCEMENT_SUMMARY.md
- TESTS_SKIPS_REPORT.md
- VSCODE_TESTING_CONFIG.md
- VSCODE_TESTS_NO_AUTO_POPUP.md
- CLIENTES_POLIMENTO_VISUAL.md
- CLIENTES_PYLANCE_CUSTOMTKINTER_FIX.md
- CLIENTES_THEME_IMPLEMENTATION.md
- ANALISE_MIGRACAO_CUSTOMTKINTER_PENDENTE.md
- PLANO_MIGRACAO_CUSTOMTKINTER.md
- relatorio_analise_lista_clientes.md
- MIGRACAO_HUB_TTKBOOTSTRAP_PARA_CUSTOMTKINTER.md

**CustomTk Relatórios (4) → customtk/MIGRATION_SUMMARY.md:**
- RELATORIO_MIGRACAO_CLIENTES_100_CUSTOMTKINTER.md
- RELATORIO_POS_MIGRACAO_TTKBOOTSTRAP.md
- CLIENTES_HEALTHCHECK.md
- 2025-12-30_reorganizacao-estrutura.md

---

### 6.3 Arquivos a Arquivar (74 arquivos)

**Microfases CustomTk (53) → customtk/_archive/:**
- MICROFASE_2.md até MICROFASE_34.md
- CLIENTES_MICROFASE_*.md (20 arquivos)

**FASE_* obsoletos (4) → _archive/:**
- FASE_4.3_RESUMO.md
- FASE_5_RELEASE.md
- FASE_6_CI_RELEASE.md
- FASE_6_RESUMO.md

**Releases consolidados (7) → _archive/releases/:**
- EXECUTIVE_SUMMARY.md
- RELEASE_STATUS.md
- CI_GREEN_REPORT.md
- GATE_FINAL.md
- NEXT_STEPS.md
- PR_DESCRIPTION.md
- CREATE_PR_INSTRUCTIONS.md

**CustomTk técnicos obsoletos (10) → customtk/_archive/:**
- Arquivos técnicos duplicados ou muito antigos

---

### 6.4 Riscos e Dependências

#### 🔴 RISCO ALTO

1. **Links externos (GitHub Issues/PRs)**
   - Verificar se há issues/PRs referenciando `docs/FASE_*.md`
   - Atualizar issues abertas se necessário

2. **docs/refactor/v1.5.35/test_runs/**
   - 6 arquivos TXT totalizando **20+ MB**
   - Considerar compactar ou mover para artifacts/local/
   - **Recomendação:** Adicionar ao .gitignore e manter apenas README com link para download

3. **customtk_clientes/MICROFASE_*.md (53 arquivos)**
   - Histórico valioso da migração
   - Não deletar, apenas arquivar em `_archive/`
   - Manter README no _archive/ explicando estrutura

#### 🟡 RISCO MÉDIO

1. **docs/README.md é referenciado em:**
   - README.md (raiz) → Link atualizado recentemente (PR #10)
   - Precisa atualizar links para nova estrutura

2. **CONTRIBUTING.md pode referenciar:**
   - `docs/QUICK_REFERENCE_CI.md` → Atualizar para `docs/ci/REFERENCE.md`

3. **PR templates podem referenciar:**
   - Documentos em `docs/reports/releases/`
   - Verificar `.github/PULL_REQUEST_TEMPLATE.md` (se existir)

#### 🟢 RISCO BAIXO

1. **cronologia/ (2 PDFs)**
   - Não referenciados em outros docs
   - Podem ser mantidos como estão

2. **patches/ (5 arquivos)**
   - Estrutura já organizada
   - Links corretos em docs/README.md

3. **guides/ (1 notebook)**
   - Autocontido, sem dependências

---

### 6.5 Checklist de Execução (Quando Aprovado)

**FASE 1: Preparação (NÃO DESTRUTIVO)**
- [ ] Criar branch `chore/docs-consolidation`
- [ ] Backup de docs/ (export para arquivo local)
- [ ] Criar novos diretórios vazios:
  - [ ] `docs/ci/`
  - [ ] `docs/releases/`
  - [ ] `docs/customtk/` (renomear de customtk_clientes)
  - [ ] `docs/_archive/`
  - [ ] `docs/_archive/releases/`
  - [ ] `docs/customtk/_archive/`

**FASE 2: Consolidação (CRIAR NOVOS ARQUIVOS)**
- [ ] Criar `docs/STATUS.md`
- [ ] Criar `docs/ROADMAP.md` (consolidar FASE_*)
- [ ] Criar `docs/ci/README.md`
- [ ] Criar `docs/ci/REFERENCE.md` (consolidar QUICK_REFERENCE_CI)
- [ ] Criar `docs/releases/RELEASE_NOTES.md` (consolidar 5 docs)
- [ ] Criar `docs/releases/TEMPLATES.md` (consolidar 2 docs)
- [ ] Criar `docs/customtk/MIGRATION_SUMMARY.md` (consolidar 4 relatórios)
- [ ] Criar `docs/customtk/TECHNICAL_DOCS.md` (consolidar 16 técnicos)
- [ ] Criar `docs/customtk/_archive/README.md` (índice do arquivo)

**FASE 3: Movimentação (GIT MV)**
- [ ] `git mv docs/customtk_clientes docs/customtk`
- [ ] `git mv docs/QUICK_REFERENCE_CI.md docs/ci/REFERENCE.md`
- [ ] `git mv docs/STAGING_CHECKLIST.md docs/ci/STAGING_CHECKLIST.md`
- [ ] `git mv docs/customtk/MICROFASE_*.md docs/customtk/_archive/` (53 arquivos)
- [ ] `git mv docs/customtk/CLIENTES_MICROFASE_*.md docs/customtk/_archive/`
- [ ] `git mv docs/FASE_*.md docs/_archive/` (4 arquivos)
- [ ] `git mv docs/reports/releases/*.md docs/_archive/releases/` (7 arquivos)

**FASE 4: Atualização de Links**
- [ ] Atualizar `docs/README.md` (links para nova estrutura)
- [ ] Atualizar `README.md` (raiz) se houver referências
- [ ] Atualizar `CONTRIBUTING.md` se houver referências
- [ ] Verificar `PR_BODY.md` e `PR_VALIDATION_COMMENT.md`
- [ ] Buscar referências pendentes: `rg "FASE_[0-9]|QUICK_REFERENCE" *.md`

**FASE 5: Validação**
- [ ] Verificar todos os links em docs/README.md
- [ ] Verificar todos os links em docs/customtk/README.md
- [ ] Verificar todos os links em docs/ci/README.md
- [ ] Teste: navegar por toda estrutura de docs/
- [ ] Pre-commit: `pre-commit run --all-files`
- [ ] Git status: confirmar que tudo foi rastreado

**FASE 6: Commit & Push**
- [ ] `git add -A`
- [ ] `git commit -m "docs: consolidate structure (120→46 active files)"`
- [ ] `git push`
- [ ] Criar PR com este plano como descrição
- [ ] Aguardar review

---

### 6.6 Economia Estimada

| Métrica | Antes | Depois | Economia |
|---------|-------|--------|----------|
| **Arquivos ativos em docs/** | 120 | 46 | **-62%** |
| **Arquivos na raiz de docs/** | 7 | 3 | **-57%** |
| **Relatórios de microfases visíveis** | 57 | 2 + 55 arquivados | **-96% na visibilidade** |
| **Docs de releases** | 7 | 2 | **-71%** |
| **Profundidade máxima** | 3 níveis | 3 níveis | Mantida |
| **Arquivos consolidados** | 0 | 8 novos | +8 docs essenciais |

**Navegação estimada:**
- **Antes:** "Onde está a info sobre CI?" → Buscar em 7 arquivos (FASE_*, QUICK_*, STAGING_*)
- **Depois:** "Onde está a info sobre CI?" → `docs/ci/` (3 arquivos organizados)

---

## 7. PRÓXIMOS PASSOS

1. **Review deste plano**
   - Validar estrutura proposta
   - Aprovar nomes de arquivos
   - Confirmar riscos aceitáveis

2. **Decisão sobre test_runs/**
   - Opção A: Compactar em `.tar.gz` e commitar (1 arquivo ~5 MB)
   - Opção B: Mover para artifacts/local/ e ignorar no git
   - Opção C: Manter como está (20+ MB no repositório)
   - **Recomendação:** Opção B

3. **Executar consolidação**
   - Seguir checklist da seção 6.5
   - Criar PR com este plano como referência
   - Validar links antes de merge

4. **Documentar processo**
   - Adicionar nota em CHANGELOG.md
   - Atualizar CONTRIBUTING.md se necessário

---

**Fim do Plano de Consolidação**

*Este documento é um plano de ação. NÃO executar mudanças sem aprovação.*
