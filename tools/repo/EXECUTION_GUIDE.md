# 🧹 GUIA DE EXECUÇÃO - LIMPEZA DO REPOSITÓRIO

**Data:** 26/01/2026  
**Status:** Pronto para execução

---

## 📋 DRY RUN PLAN

### Arquivos que serão DESVERSIONADOS (mantidos no disco):

**Pastas de artefatos:**
- `__pycache__/`
- `.mypy_cache/`
- `.pytest_cache/`
- `.ruff_cache/`
- `htmlcov/`
- `coverage/`
- `diagnostics/`

**Arquivos temporários (14 arquivos):**
- `audit_ctk.txt`
- `audit_ttk.txt`
- `audit_ttkbootstrap.txt`
- `baseline_ttk_inventory.txt`
- `hub_35.txt`
- `hub_final_result.txt`
- `hub_final_results.txt`
- `hub_results_v2.txt`
- `hub_results_v3.txt`
- `hub_results_v4.txt`
- `hub_results_v5.txt`
- `hub_results_v6.txt`
- `hub_stats.txt`
- `hub_test_results.txt`

### Arquivos que serão MOVIDOS:

**Para docs/patches/ (5 arquivos):**
- `PATCH_V2_DOUBLECLICK_DETERMINISTICO.md`
- `PATCH_CLIENTESV2_DOUBLECLICK_FLASH.md`
- `PATCH_CLIENT_FILES_BROWSER.md`
- `PATCH_FIX_FILES_BROWSER_ACCESS.md`
- `ANALISE_MIGRACAO_CTK_CLIENTESV2.md`

**Para docs/reports/microfases/ (4 arquivos):**
- `RELATORIO_MICROFASE_35.md`
- `MICROFASE_36_RELATORIO_FINAL.md`
- `RELATORIO_MICROFASE_37.md`
- `RELATORIO_MIGRACAO_CTK_COMPLETA.md`

**Para docs/reports/releases/ (7 arquivos):**
- `EXECUTIVE_SUMMARY.md`
- `GATE_FINAL.md`
- `CI_GREEN_REPORT.md`
- `RELEASE_STATUS.md`
- `NEXT_STEPS.md`
- `CREATE_PR_INSTRUCTIONS.md`
- `PR_DESCRIPTION.md`

**Para docs/guides/ (1 arquivo):**
- `MIGRACAO_CTK_GUIA_COMPLETO.ipynb`

**Para tools/migration/ (2 arquivos):**
- `fix_ctk_advanced.py`
- `fix_ctk_padding.py`

**Para tests/experiments/ (1 arquivo):**
- `test_ctktreeview.py`

**TOTAL:** 34 arquivos movidos/desversionados

---

## 🚀 EXECUÇÃO

### PASSO 1: Commit mudanças pendentes

Você tem 20 arquivos com mudanças. Primeiro, commite ou stash:

```powershell
# Opção A: Commit
git add -A
git commit -m "fix: correções no ClientesV2 e client_files_dialog"

# Opção B: Stash (para aplicar depois)
git stash push -m "WIP: mudanças antes da reorganização"
```

### PASSO 2: Executar script de limpeza

**Windows (PowerShell):**
```powershell
# Dar permissão de execução (se necessário)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Executar
.\cleanup_repo.ps1
```

**Linux/macOS (Bash):**
```bash
# Dar permissão de execução
chmod +x cleanup_repo.sh

# Executar
./cleanup_repo.sh
```

O script irá:
1. ✅ Verificar que está em um repo Git
2. ✅ Avisar sobre mudanças pendentes (se houver)
3. ✅ Criar branch `chore/organize-repo-structure`
4. ✅ Desversionar artefatos (sem apagar)
5. ✅ Mover arquivos para estrutura organizada
6. ✅ Mostrar resumo das mudanças

### PASSO 3: Atualizar .gitignore

```powershell
# Abrir .gitignore
code .gitignore

# Adicionar as linhas de gitignore_additions.txt ao final
Get-Content gitignore_additions.txt | Add-Content .gitignore
```

Ou manualmente: copie o conteúdo de `gitignore_additions.txt` para o final do `.gitignore`.

### PASSO 4: Atualizar README.md na raiz (versão curta)

Edite `README.md` para uma versão mais concisa, mantendo:
- Badge e descrição
- Início rápido
- Link para `docs/README.md` (índice completo)

Exemplo:
```markdown
# RC – Gestor de Clientes

![Versão](https://img.shields.io/badge/versão-1.5.62-blue)

Sistema desktop para gestão de clientes, documentos e senhas.

## 🚀 Início Rápido

[Ver documentação completa →](docs/README.md)
```

### PASSO 5: Revisar mudanças

```powershell
# Ver status
git status

# Ver diff detalhado
git diff --cached --stat

# Ver arquivos movidos
git diff --cached --name-status | Select-String "^R"
```

### PASSO 6: Commit

```powershell
git add -A

git commit -m "chore: reorganize repository structure

- Desversionar artefatos gerados (__pycache__, caches, htmlcov, coverage, diagnostics)
- Desversionar resultados temporários (audit_*.txt, hub_*.txt)
- Mover documentação para estrutura organizada em docs/
  - Patches → docs/patches/
  - Relatórios de microfases → docs/reports/microfases/
  - Relatórios de releases → docs/reports/releases/
  - Guias → docs/guides/
- Mover scripts de migração para tools/migration/
- Mover testes experimentais para tests/experiments/
- Criar docs/README.md como índice completo da documentação
- Atualizar .gitignore com padrões seguros
- Manter arquivos essenciais na raiz"
```

---

## ✅ VALIDAÇÃO

Execute os seguintes comandos para garantir que nada quebrou:

### 1. Ativar ambiente virtual

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Executar testes

```powershell
# Testes completos
pytest -v

# Com cobertura (verifica se htmlcov/ é recriado)
pytest --cov=src --cov-report=html

# Verificar que htmlcov/ foi regenerado
Test-Path htmlcov/index.html
# Deve retornar: True
```

### 3. Linters e type checker

```powershell
# Ruff (linter)
ruff check src/ tests/

# Pyright (type checker)
pyright src/

# Bandit (security)
bandit -c .bandit -r src/ -f screen
```

### 4. Verificar imports

```powershell
# Testar imports básicos
python -c "import sys; import src; from src.ui import ctk_config; print('✓ Imports OK')"
```

### 5. Verificar build (opcional)

```powershell
# Limpar build anterior
Remove-Item build/, dist/ -Recurse -Force -ErrorAction SilentlyContinue

# Build com PyInstaller
pyinstaller rcgestor.spec --noconfirm --clean

# Verificar executável
Test-Path dist/rcgestor.exe
# Deve retornar: True
```

### 6. Verificar que artefatos permanecem no disco

```powershell
# Verificar que arquivos NÃO foram apagados
Test-Path diagnostics/, htmlcov/, coverage/, audit_ctk.txt, hub_35.txt
# Todos devem retornar: True
```

---

## 🔗 CORRIGIR LINKS (Pós-Execução)

Após mover os arquivos, alguns links relativos podem estar quebrados. Busque e corrija:

```powershell
# Buscar referências a patches movidos
Select-String -Path "docs/patches/*.md" -Pattern "PATCH_|ANALISE_" | Select-Object Path, LineNumber

# Buscar referências em customtk_clientes/
Select-String -Path "docs/customtk_clientes/*.md" -Pattern "RELATORIO_|MICROFASE_" | Select-Object Path, LineNumber
```

**Links conhecidos a corrigir:**

1. **PATCH_V2_DOUBLECLICK_DETERMINISTICO.md** (linha 4):
   ```markdown
   # Antes (se houver)
   substitui PATCH_CLIENTESV2_DOUBLECLICK_FLASH.md

   # Depois (se necessário)
   substitui [PATCH_CLIENTESV2_DOUBLECLICK_FLASH.md](PATCH_CLIENTESV2_DOUBLECLICK_FLASH.md)
   ```

2. **PATCH_FIX_FILES_BROWSER_ACCESS.md** (linha 164, 207):
   ```markdown
   # Corrigir referências a PATCH_CLIENT_FILES_BROWSER.md
   # Usar link relativo dentro de docs/patches/
   ```

---

## 📊 RESULTADO ESPERADO

### Raiz limpa (~35 arquivos essenciais)

```
rcgestor/
├── .github/              ← CI/CD
├── assets/               ← Assets
├── config/               ← Configs
├── docs/                 ← Documentação organizada ⭐
├── scripts/              ← Scripts
├── src/                  ← Código-fonte
├── tests/                ← Testes
├── tools/                ← Dev tools + migration/ ⭐
├── main.py               ← Entrypoint
├── README.md             ← Visão geral (curto) ⭐
├── CHANGELOG.md          ← Histórico
├── CONTRIBUTING.md       ← Guia contribuição
├── pyproject.toml        ← Build system
├── requirements.txt      ← Dependências
└── ... (configs essenciais)
```

### docs/ organizada

```
docs/
├── README.md ⭐                    ← Índice completo (NOVO)
├── patches/ ⭐                     ← Patches técnicos (NOVO)
├── reports/ ⭐                     ← Relatórios (NOVO)
│   ├── microfases/
│   └── releases/
├── guides/ ⭐                      ← Guias (NOVO)
├── customtk_clientes/             ← Existente
├── refactor/                      ← Existente
└── ... (existentes)
```

---

## 🎯 CHECKLIST FINAL

- [ ] Commit/stash mudanças pendentes
- [ ] Executar `cleanup_repo.ps1` (ou `.sh`)
- [ ] Atualizar `.gitignore` com `gitignore_additions.txt`
- [ ] Atualizar `README.md` na raiz (versão curta)
- [ ] Revisar `git status`
- [ ] Corrigir links quebrados em .md
- [ ] Executar validação completa (pytest, ruff, pyright)
- [ ] Commit final
- [ ] Push branch: `git push -u origin chore/organize-repo-structure`

---

## ⚠️ AVISOS

- ✅ `git rm --cached` mantém arquivos no disco
- ✅ Todos os arquivos movidos estão versionados (seguro usar `git mv`)
- ✅ Scripts verificam existência antes de operar
- ⚠️ Revise links em .md após movimentação
- ⚠️ Validar que testes passam antes do commit final

---

**Boa organização! 🎉**
