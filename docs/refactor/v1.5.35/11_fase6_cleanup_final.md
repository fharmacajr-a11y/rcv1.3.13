# Fase 6 — Limpeza final (pastas vazias + shims legacy)

**Data**: 2026-01-03  
**Status**: ✅ Concluído

---

## 1. Objetivo

Após a conclusão das Fases 1–5 (migração completa para src-layout e atualização de build), esta fase final realiza a limpeza do repositório:

1. **Verificar e remover** pastas antigas redundantes na raiz (`infra/`, `data/`, `adapters/`, `security/`)
2. **Eliminar imports legados** e referências a caminhos antigos
3. **Remover pastas vazias** que ficaram após a migração
4. **Validar** que o repositório está limpo e funcional

**Regra de Ouro**: Apenas remoção de duplicidades/sobras. Nenhuma alteração de lógica de negócio.

---

## 2. PASSO 0 — Pre-flight: Estado Inicial

### Git Status

```powershell
git status --short | Select-Object -First 50
```

**Resultado**: Muitas mudanças acumuladas das Fases 1-5:
- **203 files changed**: 1275 insertions(+), 1712 deletions(-)
- Pastas migradas com `git mv`: `adapters/`, `data/`, `infra/`, `security/` → `src/*`
- Arquivos modificados: configs, imports corrigidos, testes atualizados
- Arquivos removidos: `helpers/`, `tools/` (scripts obsoletos)

### Observação Importante

O estado contém todas as mudanças das Fases 1-5 **não commitadas**. Esta é uma decisão intencional do projeto: manter as fases atômicas como unidades lógicas, mas commitá-las apenas após validação completa.

---

## 3. PASSO 1 — Verificar Pastas Antigas na Raiz

### Comando Executado

```powershell
foreach ($d in @("infra","data","adapters","security","helpers","tools")) {
    if (Test-Path $d) {
        Write-Host "EXISTE: $d"
        Get-ChildItem -Recurse $d -Force -ErrorAction SilentlyContinue | Select-Object -First 20 FullName
    } else {
        Write-Host "OK: NAO existe $d"
    }
}
```

### Resultado

```
OK: NAO existe infra
OK: NAO existe data
OK: NAO existe adapters
OK: NAO existe security
OK: NAO existe helpers
OK: NAO existe tools
```

**Conclusão**: ✅ Todas as pastas antigas já foram removidas pela migração com `git mv`. Não há sobras na raiz.

---

## 4. PASSO 2 — Buscar Imports Legados Remanescentes

### 4.1. Imports diretos sem `src.`

**Comando**:
```powershell
Select-String -Path "src\**\*.py","tests\**\*.py" -Pattern "(^|\s)(from|import)\s+(infra|data|adapters|security)\b" -AllMatches
```

**Resultado**: ✅ **Nenhum match encontrado**

### 4.2. Strings em patches/mocks

**Comando**:
```powershell
Select-String -Path "tests\**\*.py" -Pattern "(['\"])(infra|data|adapters|security)\." -AllMatches
```

**Resultado**: ✅ **Nenhum match encontrado**

### 4.3. Configs e build

**rcgestor.spec**:
```python
# Linhas 90-91 (CORRETAS - já atualizadas na Fase 5):
("src/infra/bin/7zip/7z.exe", "7z"),
("src/infra/bin/7zip/7z.dll", "7z"),
```
✅ Paths corretos com `src/infra/`

**sitecustomize.py**:
```python
# Linha 11 (apenas comentário explicativo):
# individuais (infra/, adapters/). Apenas garantimos que a RAIZ do projeto
```
✅ Apenas referência histórica em comentário

**docs/**:
- Referências encontradas são **apenas históricas** explicando a migração
- Exemplo: "Mover `infra/` → `src/infra/`" (descrição do que foi feito)
- **Não requer correção** - é documentação do processo

**Conclusão**: ✅ Nenhum import legado ativo. Apenas referências documentais válidas.

---

## 5. PASSO 3 — Remover Pastas Vazias

### Comando Executado

```powershell
Get-ChildItem -Recurse -Directory -Path src,tests -ErrorAction SilentlyContinue |
    Where-Object { (Get-ChildItem $_.FullName -Force -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0 } |
    Select-Object FullName
```

### Pastas Vazias Encontradas

1. `C:\Users\Pichau\Desktop\v1.5.27\src\clientes_docs`
2. `C:\Users\Pichau\Desktop\v1.5.27\src\db`
3. `C:\Users\Pichau\Desktop\v1.5.27\src\modules\main_window\views\components`

### Verificação de Versionamento

```powershell
git ls-files src/clientes_docs src/db src/modules/main_window/views/components
```

**Resultado**: (vazio) - **Não estão versionadas**

### Remoção

```powershell
Remove-Item "src\clientes_docs" -Recurse -Force
Remove-Item "src\db" -Recurse -Force
Remove-Item "src\modules\main_window\views\components" -Recurse -Force
```

**Resultado**: ✅ **Pastas vazias removidas** (não afeta git, eram artefatos locais)

---

## 6. PASSO 4 — Validações Obrigatórias

### 6.1. Sintaxe

```powershell
python -m py_compile main.py
python -m compileall -q src tests
```

**Resultado**: ✅ **Sintaxe OK** (exit code 0)

### 6.2. Imports

```powershell
python -c "import src; import src.infra, src.data, src.adapters, src.security; print('✅ imports ok')"
```

**Resultado**: ✅ **imports ok**

### 6.3. Pytest

```powershell
pytest -q --tb=no
```

**Resultado**:
```
........................................................................... [100%]
============================== warnings summary ===============================
[... apenas warnings de deprecation conhecidos ...]
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

$LASTEXITCODE
0
```

✅ **Todos os testes passaram** (exit code 0)
- Stderr limpo (Fase 4B funcionando)
- Apenas deprecation warnings esperados (`src.ui.*` → `src.modules.*`)

### 6.4. PyInstaller Build

```powershell
pyinstaller rcgestor.spec --noconfirm --log-level ERROR
```

**Resultado**:
```
Name                            Length LastWriteTime
----                            ------ -------------
RC-Gestor-Clientes-1.4.93.exe 72231047 03/01/2026 15:33:29
```

✅ **Build bem-sucedido**
- Executável: ~69 MB (mesmo tamanho da Fase 5)
- Sem erros no build
- Binários 7zip incluídos corretamente

---

## 7. Resumo de Itens Removidos/Limpos

### Pastas antigas na raiz (já removidas pelo `git mv` das fases anteriores)
- ❌ `infra/` → ✅ movida para `src/infra/`
- ❌ `data/` → ✅ movida para `src/data/`
- ❌ `adapters/` → ✅ movida para `src/adapters/`
- ❌ `security/` → ✅ movida para `src/security/`
- ❌ `helpers/` → ✅ removida (D helpers/__init__.py no git)
- ❌ `tools/` → ✅ 4 scripts removidos (coverage_gaps.py, etc.)

### Pastas vazias removidas (não versionadas)
- ✅ `src/clientes_docs/`
- ✅ `src/db/`
- ✅ `src/modules/main_window/views/components/`

### Imports legados
- ✅ **0 imports legados** encontrados em código/testes
- ✅ **0 patches/mocks** com paths antigos
- ✅ Configs e docs corretos

---

## 8. Estado Final do Repositório

### Git Status (após limpeza)

```powershell
git status --short
```

**Resultado**: Mesmas 203 mudanças das Fases 1-5 (nada adicionado pela Fase 6, pois apenas removeu artefatos locais não versionados)

### Git Diff Stats

```
203 files changed, 1275 insertions(+), 1712 deletions(-)
```

**Principais categorias**:
- Arquivos movidos (`R`): adapters/, data/, infra/, security/ → src/
- Arquivos modificados (`M`): imports corrigidos, configs atualizados
- Arquivos removidos (`D`): helpers/, tools/

---

## 9. Observações e Follow-ups

### ✅ Verificações Concluídas

1. **Código limpo**: Nenhum import legado, nenhuma pasta antiga na raiz
2. **Testes passando**: 100% dos testes com exit code 0
3. **Build funcional**: PyInstaller gera executável sem erros
4. **Sintaxe válida**: Compileall passa em todos os arquivos

### ⚠️ Warnings Conhecidos (Não Bloqueantes)

**Deprecation warnings no pytest**:
- `src.ui.hub` → `src.modules.hub`
- `src.ui.login` → `src.ui.login_dialog`
- `src.ui.main_window` → `src.modules.main_window`
- etc.

**Causa**: Shims de compatibilidade em `src/ui/` para não quebrar imports legados durante transição.

**Ação recomendada**: Manter por ora (não afeta funcionalidade). Remover em release futuro após refatoração completa de `src.ui/`.

### 📊 Estatísticas Finais

| Métrica | Valor |
|---------|-------|
| Pastas migradas | 4 (infra, data, adapters, security) |
| Pastas vazias removidas | 3 (artefatos locais) |
| Imports legados encontrados | 0 ✅ |
| Testes falhando | 0 ✅ |
| Build PyInstaller | Sucesso ✅ |
| Tamanho do executável | ~69 MB |

---

## 10. Checklist de Conclusão

- [x] Verificar pastas antigas na raiz (nenhuma encontrada)
- [x] Buscar imports legados (0 encontrados)
- [x] Remover pastas vazias (3 removidas)
- [x] Validar sintaxe (OK)
- [x] Validar imports (OK)
- [x] Rodar pytest (100% passando)
- [x] Build PyInstaller (executável gerado)
- [x] Documentação criada (este arquivo)
- [x] README.md atualizado

---

## 11. Conclusão

A **Fase 6 - Limpeza final** foi concluída com sucesso. O repositório está:
- ✅ **Limpo**: Sem pastas antigas, sem imports legados, sem artefatos órfãos
- ✅ **Funcional**: Testes passando, build gerando executável
- ✅ **Organizado**: Toda a estrutura consolidada em `src/`

**Próximos Passos Recomendados**:
1. Commit das Fases 1-6 em um único commit atômico (ou em 6 commits separados seguindo o histórico)
2. Refatoração futura de `src/ui/` para remover shims de compatibilidade
3. Distribuição do executável gerado

---

## 12. Commit Sugerido

### Opção A: Commit Único (Recomendado)

```bash
git add -A
git commit -m "Fases 1-6: Migração completa para src-layout + limpeza final

FASE 1: Migração infra/ → src/infra/ (312 imports corrigidos)
FASE 2: Migração data/ → src/data/ (47 imports corrigidos)
FASE 3: Migração adapters/ → src/adapters/ (30 imports corrigidos)
FASE 4: Migração security/ → src/security/ (6 imports corrigidos)
FASE 4B: Fix pytest Tkinter Image.__del__ (Python 3.13)
FASE 5: Atualização sitecustomize.py + rcgestor.spec
FASE 6: Limpeza final (0 imports legados, 3 pastas vazias removidas)

Validações: sintaxe ✓ imports ✓ pytest ✓ build ✓

Refs: Migração src-layout v1.5.35"
```

### Opção B: Commits Separados (Histórico Detalhado)

```bash
# Fase 1
git add infra/ src/infra/ [arquivos com imports corrigidos]
git commit -m "Fase 1: Migra infra/ → src/infra/ (312 imports)"

# Fase 2
git add data/ src/data/ [arquivos com imports corrigidos]
git commit -m "Fase 2: Migra data/ → src/data/ (47 imports)"

# Fase 3
git add adapters/ src/adapters/ [arquivos com imports corrigidos]
git commit -m "Fase 3: Migra adapters/ → src/adapters/ (30 imports)"

# Fase 4
git add security/ src/security/ [arquivos com imports corrigidos]
git commit -m "Fase 4: Migra security/ → src/security/ (6 imports)"

# Fase 4B
git add tests/conftest.py docs/refactor/v1.5.35/09_fase4b_pytest_stabilization.md
git commit -m "Fase 4B: Fix pytest Tkinter (Python 3.13)"

# Fase 5
git add sitecustomize.py rcgestor.spec docs/refactor/v1.5.35/10_fase5_sitecustomize_pyinstaller.md
git commit -m "Fase 5: Atualiza sitecustomize + PyInstaller"

# Fase 6
git add docs/refactor/v1.5.35/11_fase6_cleanup_final.md docs/refactor/v1.5.35/README.md
git commit -m "Fase 6: Limpeza final (docs)"
```

---

## 13. Referências

- Fase 1: [05_fase1_infra.md](05_fase1_infra.md)
- Fase 2: [06_fase2_data.md](06_fase2_data.md)
- Fase 3: [07_fase3_adapters.md](07_fase3_adapters.md)
- Fase 4: [08_fase4_security.md](08_fase4_security.md)
- Fase 4B: [09_fase4b_pytest_stabilization.md](09_fase4b_pytest_stabilization.md)
- Fase 5: [10_fase5_sitecustomize_pyinstaller.md](10_fase5_sitecustomize_pyinstaller.md)
- Roadmap: [README.md](README.md)
