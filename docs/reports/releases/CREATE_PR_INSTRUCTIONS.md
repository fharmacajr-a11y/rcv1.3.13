# 🚀 Instruções: Criar Pull Request

## ✅ VALIDAÇÃO LOCAL CONCLUÍDA

```
Pre-commit: 20/20 PASSED ✅
Bandit:     0 issues (62,179 linhas) ✅
Pytest:     113/113 PASSED (46.81s) ✅
Branch:     Sincronizada com origin ✅
```

---

## 📋 PASSO A PASSO: CRIAR PR

### 1. Acessar URL de Criação

```
https://github.com/fharmacajr-a11y/rcv1.3.13/compare/main...refactor/estrutura-pdf-v1.5.35
```

### 2. Preencher Título

```
fix(ci): Pre-commit green (UTF-8 safe + policy hooks)
```

### 3. Preencher Corpo do PR

**Copiar integralmente o conteúdo de:** [PR_DESCRIPTION.md](PR_DESCRIPTION.md)

**OU usar este texto (resumido):**

```markdown
# fix(ci): Pre-commit green (UTF-8 safe + policy hooks)

## 🎯 Objetivo

Deixar o pipeline CI 100% verde no Windows e Linux, garantindo compatibilidade UTF-8 e enforcement de políticas de código (SSoT, docstring positioning, security).

## ✅ Gate Local - Resultados

### Pre-commit Hooks: 20/20 PASSED ✅
### Bandit Security: 0 issues (62,179 linhas) ✅
### Pytest ClientesV2: 113/113 PASSED (46.81s) ✅

## 🔧 Mudanças Implementadas

### 1. UTF-8 Hardening (3 Camadas)
- **Script:** `sys.stdout.reconfigure(encoding="utf-8")` em validate_ui_theme_policy.py
- **Hook:** `python -X utf8` flag em .pre-commit-config.yaml
- **CI:** `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8` em workflows

### 2. SSoT CustomTkinter (5 arquivos)
Migrados para `from src.ui.ctk_config import ctk`:
- scripts/smoke_ui.py
- src/modules/anvisa/views/_anvisa_history_popup_mixin.py
- src/modules/anvisa/views/anvisa_screen.py
- src/modules/lixeira/views/lixeira.py
- test_ctktreeview.py

### 3. Docstring Positioning (13 arquivos)
Movidas para antes de imports (PEP 257)

### 4. Ruff Exceptions Cirúrgicas (5 regras)
Per-file-ignores em ruff.toml com justificativas

## 📋 Checklist de Validação

### Pre-Push ✅
- [x] Pre-commit local: 20/20 PASSED
- [x] Bandit local: 0 issues
- [x] Pytest local: 113/113 PASSED
- [x] Nenhuma mudança funcional
- [x] Vendor code não refatorado

### Aguardando CI ⏳
- [ ] Windows workflow verde (8-10 min)
- [ ] Linux workflow verde (7-9 min)

## 📊 Estatísticas

```
Commit: 997c466
Files Changed: 209
Insertions: +2,983
Deletions: -7,286
Net: -4,303 lines
```

## 🔄 Breaking Changes

**Nenhum.** Todas as mudanças são backwards-compatible e não alteram comportamento funcional.

## 🎯 O que Monitorar no CI

### Windows Workflow
- ✅ `PYTHONUTF8=1` setado
- ✅ validate-ui-theme-policy com `python -X utf8`
- ✅ Bandit UTF-8 safe
- ✅ Pytest 113/113

### Linux Workflow
- ✅ Xvfb funcionando
- ✅ Pre-commit 20/20
- ✅ Pytest 113/113

---

**Status:** ✅ PRONTO PARA MERGE (após CI verde)
**Risk Level:** 🟢 BAIXO (apenas policy/lint/format)
```

### 4. Adicionar Labels

Clique em **Labels** no painel direito e adicione:
- ✅ `ci`
- ✅ `quality`
- ✅ `windows`
- ✅ `no-breaking-changes`

### 5. Reviewers (Opcional)

Se o projeto tem CODEOWNERS ou processo de review:
- Adicionar reviewers apropriados
- Aguardar aprovação

### 6. Criar Pull Request

Clique em **"Create pull request"**

---

## 📊 MONITORAR GITHUB ACTIONS

Após criar o PR, os workflows serão triggerados automaticamente:

### URL para Monitorar

```
https://github.com/fharmacajr-a11y/rcv1.3.13/actions
```

### O que Verificar

#### ✅ Windows Workflow (8-10 min)

**Etapas críticas:**

1. **Setup Python**
   ```yaml
   env:
     PYTHONUTF8: 1
     PYTHONIOENCODING: utf-8
   ```
   ✅ Verificar: Variáveis setadas

2. **Run pre-commit hooks**
   ```bash
   pre-commit run --all-files
   ```
   ✅ Esperado: 20/20 PASSED
   ❌ NÃO deve aparecer: UnicodeEncodeError

3. **Security scan with Bandit**
   ```bash
   python -X utf8 -m bandit -c .bandit -r src
   ```
   ✅ Esperado: "No issues identified"

4. **Run tests**
   ```bash
   python -X utf8 -m pytest tests/modules/clientes_v2/
   ```
   ✅ Esperado: 113 passed

#### ✅ Linux Workflow (7-9 min)

**Etapas críticas:**

1. **Setup Xvfb**
   ```bash
   Xvfb :99 -screen 0 1024x768x24 &
   ```
   ✅ Verificar: Display :99 ativo

2. **Run pre-commit hooks**
   ✅ Esperado: 20/20 PASSED

3. **Run tests**
   ✅ Esperado: 113 passed (com Xvfb)

---

## 🔍 LOGS CRÍTICOS A BUSCAR

### ✅ SUCESSOS (Devem Aparecer)

```
[POLICY] Validando política UI/Theme...
✅ Todas as validações passaram!

[bandit] No issues identified.
Total lines of code: 62179

======================== 113 passed in ~42s ========================
```

### ❌ ERROS (NÃO Devem Aparecer)

```
UnicodeEncodeError: 'charmap' codec can't encode
ModuleNotFoundError: No module named 'customtkinter'
ImportError: cannot import name 'ctk' from 'src.ui.ctk_config'
FAILED tests/modules/clientes_v2/
```

---

## 🐛 SE CI FALHAR

### Reproduzir Localmente (Windows)

```powershell
$env:PYTHONUTF8=1
$env:PYTHONIOENCODING="utf-8"
python -X utf8 -m <comando_que_falhou>
```

### Hotfix Mínimo

1. Identificar erro exato nos logs
2. Reproduzir localmente
3. Corrigir
4. Commit: `fix(ci): <descrição>`
5. Push (CI re-triggerado automaticamente)

---

## ✅ APÓS CI VERDE

### Merge para Main

1. Verificar: "All checks passed" ✅
2. Clicar em **"Merge pull request"**
3. Confirmar merge

### Validar Main

```bash
git checkout main
git pull origin main
git log --oneline -3

# Confirmar que main está verde
# (GitHub Actions deve rodar automaticamente)
```

---

## 🏷️ CRIAR TAG DE RELEASE (Após Merge)

### Versão Sugerida: v1.5.63

```bash
# Checkout main atualizada
git checkout main
git pull origin main

# Criar tag anotada
git tag -a v1.5.63 -m "Release v1.5.63 - CI green + Windows UTF-8 safe

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
Nenhum. Todas as mudanças são backwards-compatible."

# Push da tag
git push origin v1.5.63
```

### Monitorar Release Workflow

**URL:** https://github.com/fharmacajr-a11y/rcv1.3.13/actions

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

### Validar Release Criada

```
URL: https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.5.63
```

**Verificar:**
- [ ] Release notes gerados
- [ ] Executável Windows anexado
- [ ] Checksum SHA256 anexado
- [ ] Tag aponta para commit correto

---

## 📝 CHECKLIST FINAL

### Antes do Merge
- [ ] PR criado com título correto
- [ ] Corpo do PR completo
- [ ] Labels adicionadas (ci, quality, windows, no-breaking-changes)
- [ ] CI Windows verde
- [ ] CI Linux verde
- [ ] Review aprovado (se aplicável)

### Após o Merge
- [ ] Main atualizada
- [ ] Tag v1.5.63 criada
- [ ] Release workflow verde
- [ ] Artefatos gerados
- [ ] Release page criada

---

## 🎯 RESUMO RÁPIDO

```bash
# 1. Criar PR (manual no GitHub)
# URL: https://github.com/fharmacajr-a11y/rcv1.3.13/compare/main...refactor/estrutura-pdf-v1.5.35

# 2. Aguardar CI (15-20 min)
# URL: https://github.com/fharmacajr-a11y/rcv1.3.13/actions

# 3. Merge PR (após CI verde)

# 4. Criar tag de release
git checkout main && git pull origin main
git tag -a v1.5.63 -m "Release v1.5.63 - CI green + Windows UTF-8 safe"
git push origin v1.5.63

# 5. Validar release
# URL: https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.5.63
```

---

**Status Atual:** ✅ Pronto para criar PR  
**Próxima Ação:** Acessar GitHub e criar Pull Request manualmente
