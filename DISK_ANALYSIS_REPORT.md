# 📊 Relatório de Análise de Disco

**Gerado em:** 2024  
**Branch:** chore/organize-repo-structure  
**Status:** Pós-reorganização (PR #10)

---

## 1. ONDE ESTÁ O PESO? 🎯

```
TOTAL ANALISADO: ~525 MB (excluindo .git)

├─ .venv/               376.31 MB  (71.6%) ✅ RECRIÁVEL
├─ .mypy_cache/          82.55 MB  (15.7%) ✅ RECRIÁVEL
├─ htmlcov/              28.52 MB  ( 5.4%) ✅ RECRIÁVEL
├─ reports/              27.50 MB  ( 5.2%) ⚠️ VERSIONADO
├─ coverage/              2.03 MB  ( 0.4%) ✅ RECRIÁVEL
├─ artifacts/             1.68 MB  ( 0.3%) ✅ RECRIÁVEL
├─ .pytest_cache/         1.01 MB  ( 0.2%) ✅ RECRIÁVEL
├─ .ruff_cache/           1.01 MB  ( 0.2%) ✅ RECRIÁVEL
├─ diagnostics/           0.27 MB  ( 0.1%) ✅ RECRIÁVEL
└─ Outros/                3.81 MB  ( 0.7%)

.git/: 152.14 MB (não contabilizado acima - IMPORTANTE)
```

**Peso Líquido Total:** ~677 MB (.venv + .git + caches + versionados)

---

## 2. TOP 30 MAIORES ARQUIVOS 📁

### A) Ambiente Virtual (.venv) - 10 arquivos no top 30
1. **38.68 MB** - `.venv\Scripts\ruff.exe`
2. **23.70 MB** - `.venv\Lib\site-packages\pymupdf\mupdfcpp64.dll`
3. **17.26 MB** - `.venv\Lib\site-packages\4c842c94c09923bae9e4__mypyc.cp3...`
4. **11.34 MB** - `.venv\Lib\site-packages\pymupdf\_mupdf.pyd`
5. **8.82 MB** - `.venv\Lib\site-packages\cryptography\hazmat\bindings\_rust.pyd`
6. **7.47 MB** - `.venv\Lib\site-packages\PIL\_avif.pyd`
7. **5.19 MB** - `.venv\Lib\site-packages\pydantic_core\_pydantic_core.cp313-win_amd64.pyd`

### B) Tools
8. **5.09 MB** - `tools\ripgrep\ripgrep-14.1.0-x86_64-pc-windows-msvc\rg.exe`

### C) Test Outputs (docs/refactor/)
9. **3.15 MB** - `docs\refactor\v1.5.35\test_runs\pytest_maxfail50_after.txt`
10. **3.03 MB** - `docs\refactor\v1.5.35\test_runs\pytest_stdout_after_fix.txt`
11. **2.92 MB** - `docs\refactor\v1.5.35\test_runs\pytest_maxfail10_after.txt`
12. **2.72 MB** - `docs\refactor\v1.5.35\test_runs\pytest_maxfail5_after.txt`

### D) Coverage Reports
13. **2.61 MB** - `reports\coverage.json`
14. **1.95 MB** - `htmlcov\function_index.html`
15. **1.39 MB** - `htmlcov\class_index.html`

### E) Caches
16. **1.89 MB** - `.mypy_cache\3.13\builtins.data.json`
17. **1.83 MB** - `.mypy_cache\3.13\collections\__init__.data.json`

---

## 3. TOP 20 MAIORES DIRETÓRIOS 📂

| # | Diretório | Tamanho | Categoria | Status |
|---|-----------|---------|-----------|--------|
| 1 | `.venv` | 376.31 MB | (A) Recriável | ✅ Ignorado |
| 2 | `.git` | 152.14 MB | (B) Importante | 🔒 VCS |
| 3 | `.mypy_cache` | 82.55 MB | (A) Recriável | ✅ Ignorado |
| 4 | `tests` | 42.52 MB | (B) Importante | 🔒 Versionado |
| 5 | `htmlcov` | 28.52 MB | (A) Recriável | ✅ Ignorado |
| 6 | `reports` | 27.50 MB | **(C) DEPENDE** | ⚠️ Versionado |
| 7 | `.venv\Lib\site-packages\pymupdf` | 49.03 MB | (A) Recriável | ✅ Part of .venv |
| 8 | `.venv\Scripts` | 45.69 MB | (A) Recriável | ✅ Part of .venv |
| 9 | `reports\_qa` | 23.35 MB | (A) Recriável | ⚠️ Part of reports/ |
| 10 | `coverage` | 2.03 MB | (A) Recriável | ✅ Ignorado |
| 11 | `artifacts` | 1.68 MB | (A) Recriável | ✅ Ignorado |
| 12 | `.pytest_cache` | 1.01 MB | (A) Recriável | ✅ Ignorado |
| 13 | `.ruff_cache` | 1.01 MB | (A) Recriável | ✅ Ignorado |
| 14 | `diagnostics` | 0.27 MB | (A) Recriável | ✅ Ignorado |
| 15 | `exports` | 0 KB | (B) Importante | 🔒 Versionado |

---

## 4. CLASSIFICAÇÃO DETALHADA 🏷️

### (A) RECRIÁVEIS - PODE DELETAR SEM MEDO ✅
**Total: ~521.69 MB (87% do peso não-.git)**

1. **`.venv/` (376.31 MB)**
   - Ambiente virtual Python 3.13
   - Recria com: `python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt`
   - **Impacto:** 71.6% do peso total

2. **`.mypy_cache/` (82.55 MB)**
   - Cache do type checker mypy
   - Recria automaticamente no próximo `mypy`
   - **Impacto:** 15.7%

3. **`htmlcov/` (28.52 MB)**
   - Relatórios HTML de cobertura
   - Recria com: `pytest --cov --cov-report=html`
   - **Impacto:** 5.4%

4. **`coverage/` (2.03 MB)**
   - Artefatos de cobertura (.coverage, trace/)
   - Recria com: `pytest --cov`
   - **Impacto:** 0.4%

5. **`.pytest_cache/` (1.01 MB)**
   - Cache de testes pytest
   - Recria automaticamente no próximo `pytest`
   - **Impacto:** 0.2%

6. **`.ruff_cache/` (1.01 MB)**
   - Cache do linter ruff
   - Recria automaticamente no próximo `ruff check`
   - **Impacto:** 0.2%

7. **`artifacts/local/` (1.68 MB)**
   - Arquivos temporários movidos na reorganização
   - Todos ignorados pelo git
   - **Impacto:** 0.3%

8. **`diagnostics/` (0.27 MB)**
   - Logs e diagnósticos antigos
   - Desversionizados na reorganização
   - **Impacto:** 0.1%

### (B) IMPORTANTES - NÃO DELETAR 🔒
**Total: ~194.66 MB**

1. **`.git/` (152.14 MB)**
   - Repositório Git completo
   - Contém histórico de commits, branches, objetos
   - **Motivo:** Controle de versão essencial

2. **`tests/` (42.52 MB)**
   - Suite de testes pytest (113 testes)
   - Código fonte de testes
   - **Motivo:** Validação de qualidade

3. **`exports/` (0 KB)**
   - Diretório para exports (vazio mas versionado)
   - **Motivo:** Estrutura do projeto

### (C) DEPENDE - PRECISA CONFIRMAÇÃO ⚠️
**Total: ~27.50 MB**

1. **`reports/` (27.50 MB) - VERSIONADO**
   - Contém: `coverage.json` (2.61 MB), `_qa/` (23.35 MB)
   - **Questão:** Relatórios de QA precisam estar versionados?
   - **Opções:**
     - Manter versionado se equipe depende deles no Git
     - Desversionar se são regeneráveis (adicionar ao .gitignore)
   - **Recomendação:** DESVERSIONAR (adicionar `/reports/` ao .gitignore)
     - Motivo: São artefatos de build/teste, não código fonte
     - Economia: 27.5 MB no repositório Git
     - Comando: `git rm -r --cached reports && git commit -m "chore: desversionar reports/"`

2. **`tools/ripgrep/` (5.09 MB) - NÃO VERSIONADO**
   - Ferramenta binária ripgrep.exe
   - **Questão:** Precisa estar no repositório?
   - **Opções:**
     - Deletar e instalar via: `choco install ripgrep` ou `winget install BurntSushi.ripgrep.MSVC`
     - Manter para equipes sem acesso a package managers
   - **Recomendação:** DELETAR se equipe tem acesso a choco/winget
     - Economia: 5.09 MB

3. **`docs/refactor/v1.5.35/test_runs/` (~12 MB) - VERSIONADO**
   - Outputs de testes pytest (4 arquivos de 2-3 MB cada)
   - **Questão:** Outputs de testes precisam estar versionados?
   - **Opções:**
     - Manter se são referências históricas importantes
     - Desversionar se são apenas logs temporários
   - **Recomendação:** DESVERSIONAR
     - Motivo: Logs de testes são regeneráveis
     - Economia: ~12 MB

---

## 5. PROPOSTA DE LIMPEZA EM 2 NÍVEIS 🧹

### NÍVEL 1: DELETAR IGNORADOS/ARTEFATOS (BAIXO RISCO) ✅

**Alvo:** Apenas arquivos/diretórios ignorados pelo git  
**Economia:** ~521.69 MB  
**Risco:** BAIXO (todos recriáveis)

```powershell
# Deletar caches e artefatos
Remove-Item -Path .venv -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path .mypy_cache -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path .pytest_cache -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path .ruff_cache -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path htmlcov -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path coverage -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path diagnostics -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path artifacts/local -Recurse -Force -ErrorAction SilentlyContinue

# Verificar economia
Write-Host "Limpeza Nível 1 concluída!" -ForegroundColor Green
```

**Recriação:**
```powershell
# Recriar ambiente
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Executar testes com cobertura
pytest --cov --cov-report=html

# Executar análise estática
mypy src tests
ruff check .
```

---

### NÍVEL 2: DESVERSIONAR ARTEFATOS DE BUILD (MÉDIO RISCO) ⚠️

**Alvo:** Artefatos versionados que são recriáveis  
**Economia:** ~39.5 MB no repositório Git  
**Risco:** MÉDIO (precisa confirmação que equipe não depende deles)

```powershell
# 1. Desversionar reports/
git rm -r --cached reports
echo "/reports/" >> .gitignore
git add .gitignore
git commit -m "chore: desversionar reports/ (artefatos de build)"

# 2. Desversionar test outputs
git rm --cached docs/refactor/v1.5.35/test_runs/*.txt
echo "docs/refactor/**/test_runs/*.txt" >> .gitignore
git add .gitignore
git commit -m "chore: desversionar test outputs (logs temporários)"

# 3. Deletar ripgrep local (se equipe tem choco/winget)
Remove-Item -Path tools/ripgrep -Recurse -Force
# Instalar globalmente: choco install ripgrep
```

**⚠️ ATENÇÃO:** Antes de executar Nível 2:
1. Confirmar com equipe que `reports/` não é necessário no Git
2. Verificar se há CI/CD dependendo de `reports/`
3. Confirmar que equipe pode instalar ripgrep via package manager

---

## 6. RESUMO EXECUTIVO 📋

### Situação Atual
- **Peso total do workspace:** ~677 MB
- **Distribuição:** 71.6% ambiente virtual, 22.5% Git, 5.9% outros
- **Artefatos recriáveis:** ~521.69 MB (77% do total)
- **Artefatos versionados questionáveis:** ~39.5 MB

### Oportunidades de Economia

| Nível | Alvo | Economia | Risco | Ação |
|-------|------|----------|-------|------|
| 1 | Caches e .venv | ~521.69 MB | BAIXO ✅ | Deletar sem confirmação |
| 2 | Artefatos versionados | ~39.5 MB | MÉDIO ⚠️ | Confirmar com equipe |

### Recomendação Final 🎯

**EXECUTE NÍVEL 1 IMEDIATAMENTE:**
- Deletar .venv, caches, artefatos locais
- Economia: 521.69 MB (77% do peso)
- Zero risco (todos recriáveis)

**CONSIDERE NÍVEL 2 APÓS CONFIRMAÇÃO:**
- Desversionar `reports/` e test outputs
- Economia adicional: 39.5 MB no repositório Git
- Requer validação com equipe

---

## 7. COMANDOS RÁPIDOS 🚀

### Executar Limpeza Completa (Nível 1)
```powershell
# Script único para Nível 1
$dirs = @('.venv', '.mypy_cache', '.pytest_cache', '.ruff_cache', 'htmlcov', 'coverage', 'diagnostics', 'artifacts/local')
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        Remove-Item -Path $dir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "✅ Deletado: $dir" -ForegroundColor Green
    }
}
Write-Host "`n🎉 Limpeza Nível 1 concluída! Economia: ~521.69 MB" -ForegroundColor Yellow
```

### Verificar Tamanho Atual
```powershell
$size = (Get-ChildItem -Recurse -File -Force -ErrorAction SilentlyContinue | 
         Where-Object { -not $_.FullName.Contains('.git\') } | 
         Measure-Object -Property Length -Sum).Sum
Write-Host "Tamanho atual: $([math]::Round($size / 1MB, 2)) MB" -ForegroundColor Cyan
```

---

**Relatório gerado após reorganização do PR #10**  
**Branch:** chore/organize-repo-structure  
**Status do PR:** https://github.com/fharmacajr-a11y/rcv1.3.13/pull/10  
**Próximos passos:** Executar Nível 1, revisar Nível 2, aguardar merge do PR
