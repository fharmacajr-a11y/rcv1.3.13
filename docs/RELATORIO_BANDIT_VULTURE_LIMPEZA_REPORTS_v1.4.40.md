# Relatório: Correção Bandit, Limpeza Reports e Análise Vulture

**Data:** 2025-01-27  
**Branch:** `chore/auditoria-limpeza-v1.4.40`  
**Executor:** GitHub Copilot  
**Contexto:** Fase 2 da auditoria v1.4.40 — correção de tooling, limpeza de reports e análise de dead code

---

## 1. Resumo Executivo

Este relatório documenta três ações principais realizadas na fase 2 da auditoria:

1. **Correção da configuração do Bandit** — flag `-c` alterado para `--ini` no README.md
2. **Limpeza da pasta reports/** — remoção de 24 arquivos antigos/grandes (16.24 MB)
3. **Execução do Vulture** — análise de dead code com 4 issues encontrados

**Resultado:** Todas as ferramentas de QA (Ruff, Bandit, Vulture, Compileall) executadas com sucesso ✅

---

## 2. Correção da Configuração do Bandit

### 2.1 Problema Identificado

O comando no [README.md](../README.md#L166) estava usando `-c .bandit`, mas o arquivo `.bandit` é um INI, não YAML/TOML:

```bash
# ❌ Comando INCORRETO (causava erro de parsing YAML)
bandit -c .bandit -r src/
```

**Erro gerado:**
```
yaml.scanner.ScannerError: while scanning for the next token
found character '[' that cannot start any token
```

### 2.2 Solução Implementada

**Opção escolhida:** Manter `.bandit` como INI e corrigir o flag para `--ini`

**Arquivo alterado:** [README.md](../README.md#L166)

```bash
# ✅ Comando CORRETO (executa sem erros)
bandit --ini .bandit -r src adapters infra helpers
```

**Justificativa:**
- Menor impacto (não requer modificar `.bandit` existente)
- Documentação Bandit confirma: `-c` para YAML/TOML, `--ini` para INI
- Expande escopo para `adapters`, `infra`, `helpers` (antes só analisava `src/`)

### 2.3 Locais Atualizados

| Arquivo | Linha | Status |
|---------|-------|--------|
| [README.md](../README.md#L166) | 166 | ✅ Corrigido |
| `.pre-commit-config.yaml` | N/A | ⚠️ Sem hook Bandit (execução manual apenas) |
| `.bandit` | N/A | ✅ Mantido como INI |

---

## 3. Limpeza da Pasta reports/

### 3.1 Estado Inicial

```
reports/
├── bandit_initial_report.txt          15.74 MB  ❌ REMOVIDO
├── bandit_report_20250126_205537.json  107 KB   ❌ REMOVIDO
├── ruff_report_20250126_205537.json     24 KB   ❌ REMOVIDO
├── coverage_report_*.json              ~200 KB  ❌ REMOVIDO
├── pyproject_*.toml                    ~300 KB  ❌ REMOVIDO
├── ... (20+ arquivos)                  ~100 KB  ❌ REMOVIDO
├── root_cleanup_plan.md                  7 KB   ✅ MANTIDO
└── _qa/
    └── bandit_latest.txt                 3 KB   ✅ MANTIDO (novo)
```

**Total removido:** 24 arquivos, **16.24 MB**

### 3.2 Critérios de Remoção

✅ **Pode remover:**
- Arquivos com timestamp no nome (`*_20250126_*.json`)
- Relatórios muito grandes (`bandit_initial_report.txt` 15.74 MB)
- Arquivos duplicados/antigos de coverage, pyproject, ruff

❌ **Não remover:**
- `root_cleanup_plan.md` — documento de planejamento ativo
- `_qa/bandit_latest.txt` — resultado mais recente (gerado nesta sessão)
- `_qa/vulture_latest.txt` — resultado mais recente (gerado nesta sessão)

### 3.3 Atualização .gitignore

Adicionada nova seção para excluir relatórios QA gerados:

```gitignore
# QA reports (generated artifacts)
reports/_qa/
```

---

## 4. Execução e Resultados do Bandit

### 4.1 Comando Executado

```bash
python -m bandit --ini .bandit -r src adapters infra helpers
```

**Status:** ✅ Executado com sucesso (sem erros de parsing)

### 4.2 Resultados

**Resumo:**
- **Linhas de código analisadas:** 46.920
- **Issues encontrados:** 6 (todos Low severity)
- **Issues suprimidos:** 12 (via `#nosec`)

**Detalhamento (todos em [src/modules/uploads/service.py](../src/modules/uploads/service.py)):**

| Linha | Issue ID | Descrição | Severidade | Confiança |
|-------|----------|-----------|------------|-----------|
| 38 | B404 | Consider possible security implications associated with the subprocess module | LOW | HIGH |
| 44 | B606 | Starting a process with a partial executable path (os.startfile) | LOW | MEDIUM |
| 49 | B607 | Starting a process with a partial executable path (subprocess.Popen) | LOW | HIGH |
| 49 | B603 | subprocess call - check for execution of untrusted input | LOW | HIGH |
| 62 | B607 | Starting a process with a partial executable path (subprocess.Popen) | LOW | HIGH |
| 62 | B603 | subprocess call - check for execution of untrusted input | LOW | HIGH |

**Análise:**
- ✅ Todos os issues são **Low severity** e relacionados ao uso legítimo de `subprocess` para abrir arquivos
- ✅ Código utiliza `os.startfile` (Windows), `open` (macOS), `xdg-open` (Linux) — comportamento esperado
- ⚠️ **Recomendação:** Adicionar `#nosec` com justificativa se revisão manual confirmar segurança

**Relatório completo:** [reports/_qa/bandit_latest.txt](../reports/_qa/bandit_latest.txt)

---

## 5. Execução e Resultados do Vulture

### 5.1 Comando Executado

```bash
python -m vulture src adapters infra helpers --min-confidence 90 \
  --exclude "**/migrations/*,**/third_party/*,**/typings/*,**/.venv/*,**/venv/*,**/__pycache__/*" \
  > reports/_qa/vulture_latest.txt
```

**Status:** ✅ Executado com sucesso (4 issues encontrados)

### 5.2 Resultados

**Issues encontrados (100% confidence):**

1. **[src/modules/lixeira/views/lixeira_helpers.py](../src/modules/lixeira/views/lixeira_helpers.py#L297) linha 297**  
   ```
   unused variable 'has_pending_changes'
   ```
   - **Tipo:** Variável não utilizada
   - **Confiança:** 100%
   - **Ação recomendada:** Verificar se pode ser removida ou se é usado em debug

2. **[src/modules/uploads/form_service.py](../src/modules/uploads/form_service.py#L35) linha 35**  
   ```
   unreachable code after 'raise'
   ```
   - **Tipo:** Código morto (after raise)
   - **Confiança:** 100%
   - **Ação recomendada:** Remover código após raise (nunca será executado)

3. **[src/modules/uploads/views/browser.py](../src/modules/uploads/views/browser.py#L462) linha 462**  
   ```
   unused variable 'signature'
   ```
   - **Tipo:** Variável não utilizada
   - **Confiança:** 100%
   - **Ação recomendada:** Verificar se é resultado de refactor incompleto

4. **[src/ui/dialogs/file_select.py](../src/ui/dialogs/file_select.py#L116) linha 116**  
   ```
   unreachable code after 'return'
   ```
   - **Tipo:** Código morto (after return)
   - **Confiança:** 100%
   - **Ação recomendada:** Remover código após return (nunca será executado)

**Análise:**
- ✅ **4 issues** com 100% de confiança (baixo risco de falso positivo)
- ✅ Divididos em: **2 variáveis não usadas** + **2 blocos de código inalcançável**
- ⚠️ **Nota:** Código inalcançável após `return`/`raise` pode indicar refactoring incompleto ou lógica morta

**Relatório completo:** [reports/_qa/vulture_latest.txt](../reports/_qa/vulture_latest.txt)

---

## 6. Validações Executadas

### 6.1 Ruff

```bash
ruff check src adapters infra helpers main.py
```

**Status:** ✅ All checks passed!

### 6.2 Compileall

```bash
python -m compileall -q src adapters infra helpers main.py
```

**Status:** ✅ Compileall: OK (sem erros de sintaxe)

---

## 7. Resumo de Alterações

### 7.1 Arquivos Modificados

| Arquivo | Tipo de Mudança | Impacto |
|---------|----------------|---------|
| [README.md](../README.md#L166) | Correção comando Bandit (`-c` → `--ini`) | Alto — fix crítico |
| [.gitignore](../.gitignore) | Adição de `reports/_qa/` | Médio — previne bloat futuro |
| `reports/` | Remoção de 24 arquivos (16.24 MB) | Alto — cleanup significativo |

### 7.2 Arquivos Criados

| Arquivo | Tamanho | Descrição |
|---------|---------|-----------|
| [reports/_qa/bandit_latest.txt](../reports/_qa/bandit_latest.txt) | 3.47 KB | Resultado Bandit (6 Low issues) |
| [reports/_qa/vulture_latest.txt](../reports/_qa/vulture_latest.txt) | 0.5 KB | Resultado Vulture (4 issues) |
| Este relatório | ~10 KB | Documentação fase 2 |

---

## 8. Próximos Passos Recomendados

### 8.1 Prioridade Alta

1. **Revisar issues do Vulture**
   - [ ] Remover código inalcançável após `return`/`raise` ([uploads/form_service.py:35](../src/modules/uploads/form_service.py#L35), [file_select.py:116](../src/ui/dialogs/file_select.py#L116))
   - [ ] Investigar variáveis não usadas ([lixeira_helpers.py:297](../src/modules/lixeira/views/lixeira_helpers.py#L297), [browser.py:462](../src/modules/uploads/views/browser.py#L462))

2. **Adicionar `#nosec` com justificativa no código de Bandit**
   - [ ] Documentar uso de subprocess em [uploads/service.py](../src/modules/uploads/service.py#L38) (linhas 38, 44, 49, 62)

### 8.2 Prioridade Média

3. **Considerar hook do Bandit no pre-commit**
   - Atualmente `.pre-commit-config.yaml` não tem hook Bandit
   - Avaliar se faz sentido adicionar (pode deixar CI mais lento)

4. **Automatizar limpeza de reports/**
   - Script de manutenção periódica (`scripts/cleanup_reports.py`)
   - Adicionar task no `pyproject.toml` ou `Makefile`

### 8.3 Prioridade Baixa

5. **Expandir cobertura de análise estática**
   - Considerar mypy para type checking (se não estiver em uso)
   - Avaliar pylint para análise adicional

---

## 9. Métricas Finais

| Métrica | Antes | Depois | Diferença |
|---------|-------|--------|-----------|
| Tamanho reports/ | ~16.25 MB | ~1 MB | -16.24 MB (-94%) |
| Bandit status | ❌ Erro parsing | ✅ 6 Low issues | Fix crítico |
| Arquivos reports/ | 26 | 2 | -24 (-92%) |
| Issues Vulture | N/A | 4 (100% conf) | Baseline criado |

**Total liberado (Fase 1 + Fase 2):** ~2.14 GB + 16.24 MB = **~2.16 GB**

---

## 10. Checklist de Verificação

- [x] Bandit executa sem erros de parsing
- [x] README.md atualizado com comando correto
- [x] reports/ limpo (apenas arquivos essenciais)
- [x] .gitignore atualizado para prevenir bloat futuro
- [x] Vulture executado e relatório gerado
- [x] Ruff passa sem erros
- [x] Compileall passa sem erros de sintaxe
- [x] Relatório de fase 2 criado
- [ ] Commit das mudanças no branch `chore/auditoria-limpeza-v1.4.40`

---

**Fim do relatório.**
