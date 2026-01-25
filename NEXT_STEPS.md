# 🚀 Próximos Passos - CI/Release

## ✅ Status Atual

### Commits Pushed
```
8198fd9 docs(ci): add PR description and validation report
997c466 fix(ci): pre-commit green (utf-8 safe + policy hooks)
```

### Branch Remote
```
refactor/estrutura-pdf-v1.5.35 → origin/refactor/estrutura-pdf-v1.5.35
```

### Gate Local (Validado)
- ✅ Pre-commit: 20/20 PASSED
- ✅ Bandit: 0 issues (62,179 linhas)
- ✅ Pytest: 113/113 PASSED (47.55s)

---

## 📋 TAREFA 1: Acompanhar GitHub Actions CI

### 1.1 Acessar Workflows

```
URL: https://github.com/fharmacajr-a11y/rcv1.3.13/actions
```

### 1.2 Verificar Workflow `ci.yml`

Procurar por:
- **Run ID:** Mais recente para `refactor/estrutura-pdf-v1.5.35`
- **Commit:** `8198fd9` ou `997c466`
- **Status:** 🟡 In Progress → 🟢 Success (esperado)

### 1.3 Monitorar Jobs

#### Job 1: **Windows (Python 3.13)**

**Etapas críticas:**
1. ✅ **Setup Python**
   - Verificar: `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8` setados
   - Esperado: Python 3.13.x instalado

2. ✅ **Install dependencies**
   - Verificar: `pip install -r requirements.txt requirements-dev.txt`
   - Esperado: Sem erros de encoding

3. ✅ **Run pre-commit hooks**
   - Comando: `pre-commit run --all-files`
   - Esperado: 20/20 PASSED (incluindo `validate-ui-theme-policy`)
   - **CRÍTICO:** Verificar que não há `UnicodeEncodeError`

4. ✅ **Security scan with Bandit**
   - Comando: `python -X utf8 -m bandit -c .bandit -r src`
   - Esperado: "No issues identified" (62,179 linhas)
   - **CRÍTICO:** Verificar execução com UTF-8 flag

5. ✅ **Run tests**
   - Comando: `python -X utf8 -m pytest tests/modules/clientes_v2/ -v`
   - Esperado: 113/113 passed in ~42-47s
   - **CRÍTICO:** Nenhum `ImportError` de `ctk_config`

**Duração esperada:** ~8-10 minutos

#### Job 2: **Linux (Python 3.13 + Xvfb)**

**Etapas críticas:**
1. ✅ **Setup Xvfb**
   - Verificar: `Xvfb :99 -screen 0 1024x768x24 &`
   - Esperado: Display `:99` ativo

2. ✅ **Setup Python**
   - Verificar: Python 3.13.x com UTF-8 padrão (Linux)
   - Esperado: Sem necessidade de `PYTHONUTF8` (já é UTF-8)

3. ✅ **Run pre-commit hooks**
   - Comando: `pre-commit run --all-files`
   - Esperado: 20/20 PASSED
   - **CRÍTICO:** Line endings CRLF→LF já normalizados (não deve haver warnings)

4. ✅ **Security scan with Bandit**
   - Comando: `python -X utf8 -m bandit -c .bandit -r src`
   - Esperado: "No issues identified"

5. ✅ **Run tests**
   - Comando: `python -X utf8 -m pytest tests/modules/clientes_v2/ -v`
   - Esperado: 113/113 passed (com Xvfb funcionando)
   - **CRÍTICO:** GUI tests não devem falhar por falta de display

**Duração esperada:** ~7-9 minutos

---

## 🔍 Logs Críticos (O que Buscar)

### ✅ SUCESSOS A CONFIRMAR:

```
[POLICY] Validando política UI/Theme...
   Analisando 200+ arquivos Python em src/
   ✓ Validando SSoT (set_appearance_mode)...
   ✓ Validando ttk.Style(master=)...
   ✓ Validando ausência de tb.Style()...
   ✓ Validando ausência de imports ttkbootstrap...
   ✓ Validando ausência de widgets ttk simples...
   ✓ Validando ausência de icecream em src/...
   ✓ Validando ausência de 'ttk' (inclusive comentários)...
   ✓ Validando VCS dependencies com commit hash...
   ✓ Validando vendor com LICENSE + README...

✅ Todas as validações passaram!
   - SSoT: OK
   - ttk.Style(master=): OK
   - Zero ttkbootstrap: OK
   - Widgets ttk: OK
   - icecream: OK
   - Token 'ttk': OK
   - VCS deps com pin: OK
   - Vendor com LICENSE: OK
```

```
[bandit] Run started
[bandit] No issues identified.

Run metrics:
        Total lines of code: 62179
        Total issues (by severity):
                Undefined: 0
                Low: 0
                Medium: 0
                High: 0
        Total issues (by confidence):
                Undefined: 0
                Low: 0
                Medium: 0
                High: 0
```

```
======================== test session starts =========================
platform win32 -- Python 3.13.x, pytest-8.4.2
collected 113 items

tests/modules/clientes_v2/test_busca.py::test_* PASSED [ 1%]
...
tests/modules/clientes_v2/test_whatsapp.py::test_* PASSED [100%]

======================== 113 passed in 47.55s ========================
```

### ❌ ERROS QUE NÃO DEVEM APARECER:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2705' in position 0
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0
ModuleNotFoundError: No module named 'customtkinter'
ImportError: cannot import name 'ctk' from 'src.ui.ctk_config'
ERROR tests/modules/clientes_v2/test_*.py - ImportError
FAILED tests/modules/clientes_v2/test_*.py::test_* - AssertionError
AssertionError: assert False (GUI tests falhando por Xvfb)
```

---

## 📝 TAREFA 2: Criar Pull Request

### 2.1 Acessar GitHub PR

```
URL: https://github.com/fharmacajr-a11y/rcv1.3.13/compare/main...refactor/estrutura-pdf-v1.5.35
```

### 2.2 Título do PR

```
fix(ci): Pre-commit green (UTF-8 safe + policy hooks)
```

### 2.3 Corpo do PR

**Copiar conteúdo de:** `PR_DESCRIPTION.md`

**Seções principais:**
1. 🎯 Objetivo
2. ✅ Gate Local - Resultados
3. 🔧 Mudanças Implementadas
4. 📋 Checklist de Validação
5. 📊 Estatísticas do Commit
6. 🔄 Breaking Changes (Nenhum)
7. 🚨 Rollback Plan

### 2.4 Reviewers (Opcional)

Se o projeto tem CODEOWNERS ou processo de review:
- Adicionar reviewers apropriados
- Aguardar aprovação

### 2.5 Labels (Sugeridos)

- `ci` - Mudanças em CI/CD
- `quality` - Code quality improvements
- `windows` - Windows compatibility
- `no-breaking-changes` - Safe to merge

---

## 🎯 TAREFA 3: Validar CI Green

### 3.1 Aguardar Conclusão

- Tempo total esperado: ~15-20 minutos (Windows + Linux)
- Verificar status: 🟢 All checks passed

### 3.2 Se CI Passar (Verde)

**Ação:** ✅ Aprovar merge do PR

```bash
# Se for você o reviewer:
# Clicar em "Approve" no GitHub

# Se CI estiver verde e PR aprovado:
# Clicar em "Merge pull request"
```

### 3.3 Se CI Falhar (Vermelho)

**Ação:** 🔴 Investigar e corrigir

#### Passo 1: Identificar Job/Step que falhou
- Acessar logs do workflow
- Localizar erro exato

#### Passo 2: Reproduzir localmente
```powershell
# Se falhou no Windows:
$env:PYTHONUTF8=1
$env:PYTHONIOENCODING="utf-8"
python -X utf8 -m <comando_que_falhou>

# Se falhou no Linux:
# Usar WSL ou container Docker
docker run -it --rm -v ${PWD}:/workspace python:3.13 bash
cd /workspace
python -X utf8 -m <comando_que_falhou>
```

#### Passo 3: Corrigir e push
```bash
# Fazer correção local
git add <arquivos_corrigidos>
git commit -m "fix(ci): <descrição_da_correção>"
git push origin refactor/estrutura-pdf-v1.5.35

# CI será re-triggerado automaticamente
```

---

## 🏷️ TAREFA 4: Release (Opcional)

### 4.1 Confirmar Staging Checklist

**Pré-requisitos:**
- [ ] CI passou em Windows e Linux
- [ ] PR aprovado e mergeado em `main`
- [ ] Smoke tests executados manualmente
- [ ] Changelog atualizado (já foi no commit 997c466)

### 4.2 Decidir Versão

**Atual:** `v1.5.62-fase4.3`  
**Próxima sugerida:** `v1.5.63`

**Tipo de release:**
- ✅ **Patch** (correções de CI/policy, sem features)
- ❌ Minor (novas features - não é o caso)
- ❌ Major (breaking changes - não há)

### 4.3 Criar Tag Anotada

```bash
# Checkout branch main (após merge do PR)
git checkout main
git pull origin main

# Criar tag
git tag -a v1.5.63 -m "Release v1.5.63 - Pre-commit green + UTF-8 safe

## Correções
- UTF-8 hardening (Windows cp1252 → UTF-8)
- SSoT CustomTkinter enforcement (5 arquivos)
- Docstring positioning PEP 257 (13 arquivos)
- Ruff exceptions cirúrgicas (5 per-file-ignores)

## Validações
- Pre-commit: 20/20 PASSED
- Bandit: 0 issues (62,179 linhas)
- Pytest: 113/113 PASSED (ClientesV2 suite)

## Breaking Changes
Nenhum. Todas as mudanças são backwards-compatible.
"

# Push da tag
git push origin v1.5.63
```

### 4.4 Acompanhar Release Workflow

**Workflow:** `.github/workflows/release.yml`

**Etapas esperadas:**
1. ✅ Pre-commit hooks (gate)
2. ✅ Bandit security scan (gate)
3. ✅ Pytest suite completa (gate)
4. ✅ Build executável Windows (PyInstaller)
5. ✅ Gerar checksum SHA256
6. ✅ Upload artifacts
7. ✅ Criar GitHub Release

**Artefatos esperados:**
- `rcgestor-v1.5.63-windows.exe`
- `rcgestor-v1.5.63-windows.exe.sha256`

### 4.5 Validar Release Criada

```
URL: https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.5.63
```

**Verificar:**
- [ ] Release notes gerados (da tag annotation)
- [ ] Executável Windows anexado
- [ ] Checksum SHA256 anexado
- [ ] Tag aponta para commit correto (após merge do PR)

### 4.6 Smoke Test do Release

```powershell
# Download do executável
# Executar em máquina limpa (sem Python instalado)
# Verificar:
# - App abre sem erros
# - Tema light/dark alterna corretamente
# - Módulo ClientesV2 funciona
# - Sem warnings de encoding
```

---

## 🐛 Troubleshooting

### Problema: CI falha com UnicodeEncodeError

**Sintoma:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2705'
```

**Causa:** Variável de ambiente não setada ou script não usa `-X utf8`

**Fix:**
```yaml
# .github/workflows/ci.yml
env:
  PYTHONUTF8: 1
  PYTHONIOENCODING: utf-8

# E/ou
- name: Run hook
  run: python -X utf8 scripts/validate_ui_theme_policy.py
```

### Problema: CI falha com Import Error

**Sintoma:**
```
ImportError: cannot import name 'ctk' from 'src.ui.ctk_config'
```

**Causa:** Arquivo novo adicionado com import direto

**Fix:**
```python
# ERRADO:
import customtkinter as ctk

# CORRETO:
from src.ui.ctk_config import ctk
```

### Problema: Xvfb não iniciou (Linux)

**Sintoma:**
```
RuntimeError: could not connect to display :99
```

**Causa:** Xvfb não foi iniciado antes dos testes

**Fix:**
```yaml
# .github/workflows/ci.yml
- name: Setup Xvfb
  run: |
    sudo apt-get update
    sudo apt-get install -y xvfb
    Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
    sleep 3  # Aguardar Xvfb iniciar
  env:
    DISPLAY: :99
```

---

## 📊 Checklist Final

### Antes do Merge
- [x] Gate local verde (20/20, 0 issues, 113/113)
- [x] Commit criado com mensagem descritiva
- [x] PR description preparado
- [x] Push para remote executado
- [ ] CI Windows verde
- [ ] CI Linux verde
- [ ] PR aprovado (se houver reviewers)

### Após o Merge
- [ ] Branch `main` atualizada
- [ ] Tag `v1.5.63` criada (se for release)
- [ ] Release workflow verde
- [ ] Artefatos gerados
- [ ] Smoke test do executável

### Comunicação
- [ ] Notificar equipe sobre PR mergeado
- [ ] Atualizar issue tracker (se houver)
- [ ] Documentar lições aprendidas

---

## 📚 Referências

- **PR:** [PR_DESCRIPTION.md](PR_DESCRIPTION.md)
- **Relatório Completo:** [CI_GREEN_REPORT.md](CI_GREEN_REPORT.md)
- **Workflows:** `.github/workflows/ci.yml`, `.github/workflows/release.yml`
- **Documentação FASE 6:** `docs/FASE_6_CI_RELEASE.md`, `docs/QUICK_REFERENCE_CI.md`

---

## ✅ Status Atual: AGUARDANDO CI

**Próxima ação manual:** Acessar GitHub Actions e monitorar workflows

**URL:** https://github.com/fharmacajr-a11y/rcv1.3.13/actions

**Tempo estimado até merge:** ~20-30 minutos (CI + review + merge)
