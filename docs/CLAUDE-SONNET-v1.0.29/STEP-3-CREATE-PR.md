# Script para criar Pull Request - Step 3

## Passo 1: Push da Branch

```powershell
git push -u origin maintenance/v1.0.29 --force-with-lease
```

> Nota: `--force-with-lease` é usado porque fizemos amend no Step 2

## Passo 2: Criar PR no GitHub/GitLab

### Via GitHub CLI (gh)
```powershell
gh pr create `
  --base feature/prehome-hub `
  --title "Step 3 – BOM Removal + Pre-commit (Black/Ruff)" `
  --body-file docs/CLAUDE-SONNET-v1.0.29/STEP-3-PR.md
```

### Via Interface Web

1. Acesse: https://github.com/[seu-usuario]/[seu-repo]/compare/feature/prehome-hub...maintenance/v1.0.29
2. Clique em "Create Pull Request"
3. Título: **Step 3 – BOM Removal + Pre-commit (Black/Ruff)**
4. Descrição: Copie o conteúdo de `docs/CLAUDE-SONNET-v1.0.29/STEP-3-PR.md`

## Resumo do PR

**3 bullets principais**:

1. ✅ **21 arquivos com BOM removidos** - Script `scripts/dev/strip_bom.py` detectou e corrigiu 21 arquivos Python com BOM (0xEF 0xBB 0xBF). UTF-8 é o encoding padrão no Python 3 (PEP 3120) e BOM é desnecessário.

2. ✅ **44 arquivos reformatados (Black) + 16 erros fixados (Ruff)** - Pre-commit hooks ativados com Black v24.8.0, Ruff v0.6.9 e hooks básicos. Primeira execução reformatou 44 arquivos, corrigiu 16 erros de linting, normalizou 15 line endings (CRLF→LF) e removeu trailing whitespace.

3. ✅ **Qualidade de código automatizada** - Pre-commit instalado em `.git/hooks/pre-commit` e executa automaticamente em cada commit: formatação Black, linting Ruff com auto-fix, normalização de line endings e correção de whitespace. Zero mudanças em assinaturas de funções.

## Estatísticas

```
76 arquivos alterados
1.675 inserções(+)
9.080 deleções(-)
```

**Breakdown**:
- 21 arquivos: BOM removido
- 44 arquivos: formatados pelo Black
- 16 arquivos: corrigidos pelo Ruff
- 15 arquivos: line endings normalizados
- 2 arquivos: end-of-file corrigido
- 1 arquivo: trailing whitespace removido

## Artefatos Anexados

- `scripts/dev/strip_bom.py` - Script de remoção de BOM
- `.pre-commit-config.yaml` - Configuração dos hooks
- `.ruff.toml` - Configuração do Ruff
- `docs/CLAUDE-SONNET-v1.0.29/STEP-3-EXECUTION.md` - Relatório detalhado
- `docs/CLAUDE-SONNET-v1.0.29/LOG.md` - Log atualizado

## Commits Incluídos

```
636af3f docs: adicionar resumo do PR Step 3
c8ebc12 Step 3 – BOM removal + pre-commit: 21 arquivos BOM, 44 reformatados (Black), 16 erros fixados (Ruff)
22a241b docs: adicionar resumo do PR Step 2
6ca9d96 Step 2 – Segredos & Build seguro: filtro de logs, .spec sem .env, smoke build validado
ad17487 Step 1 – Entrypoint unificado: confirmação de app_gui.py como entrypoint único
```

## Output do Script strip_bom.py

```
Removendo BOM de arquivos Python...

✓ fix: app_gui.py
✓ fix: adapters\__init__.py
✓ fix: application\navigation_controller.py
[... 18 arquivos mais ...]

============================================================
Total de arquivos corrigidos: 21
============================================================
```

## Output do pre-commit (segunda execução)

```
✅ black....................................................................Passed
✅ ruff.....................................................................Passed
✅ fix end of files.........................................................Passed
✅ mixed line ending........................................................Passed
✅ trim trailing whitespace.................................................Passed
```

## Próximos Steps

Após merge deste PR, aguardar instruções para **Step 4**.

---

**Branch pronta com qualidade de código automatizada! 🚀**
