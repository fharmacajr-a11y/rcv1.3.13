# Instruções para Criar PR: Melhorias UI/Tema

## 🎯 Branch Info
- **Branch atual**: `postrelease/v1.5.64-rc.1`
- **Branch base**: `main`
- **Commits**: 4 commits (20e748e...646a3d1)

## 📋 Criar PR via GitHub Web

1. Acesse: https://github.com/fharmacajr-a11y/rcv1.3.13/compare/main...postrelease/v1.5.64-rc.1

2. **Título do PR**:
   ```
   feat(ui): melhorias de tema ttk + robustez
   ```

3. **Corpo do PR**:
   Copiar conteúdo completo de `PR_MELHORIAS_UI_TEMA.md`

4. **Labels** (adicionar):
   - `quality`
   - `windows`
   - `no-breaking-changes`
   - `ui/theme` (criar se não existir)

5. **Reviewers**: Adicionar revisores apropriados

6. **Milestone**: v1.5.64-rc.1 (criar se não existir)

## 🚀 Criar PR via GitHub CLI (alternativa)

```bash
# Se tiver gh CLI instalado:
gh pr create \
  --base main \
  --head postrelease/v1.5.64-rc.1 \
  --title "feat(ui): melhorias de tema ttk + robustez" \
  --body-file PR_MELHORIAS_UI_TEMA.md \
  --label "quality,windows,no-breaking-changes,ui/theme"
```

## ✅ Após Criar PR

1. Aguardar CI passar (Windows + Linux)
2. Se CI verde → solicitar review
3. Após aprovação → merge usando "Squash and merge" ou "Rebase and merge"
4. Após merge → criar tag RC (ver próximo arquivo)

## 🏷️ Criar Tag RC (após merge)

```bash
# Após merge do PR em main:
git checkout main
git pull origin main

# Criar tag anotada:
git tag -a v1.5.64-rc.1 -m "Release Candidate 1.5.64-rc.1

Melhorias de UI/tema com ttk_compat e robustez:
- Sistema de callbacks do theme_manager
- Padrão ttk_compat.py para widgets ttk
- Propagação ao módulo ClientesV2
- Cleanup automático para prevenir memory leaks
- CI com Xvfb para GUI tests headless

Gate local: ✅ compileall, pre-commit, bandit, pytest
Testes: 120/120 passing"

# Push da tag:
git push origin v1.5.64-rc.1
```

## 📦 Monitorar Release

1. Acesse: https://github.com/fharmacajr-a11y/rcv1.3.13/actions
2. Aguardar workflow `release.yml` completar
3. Verificar assets gerados em: https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.5.64-rc.1
   - rcgestor-v1.5.64-rc.1.exe (instalador)
   - SHA256SUMS.txt (checksums)

## 🧪 Executar Smoke Test

Após assets estarem disponíveis:

1. Baixar `rcgestor-v1.5.64-rc.1.exe`
2. Instalar em máquina Windows limpa (sem Python)
3. Executar checklist de `SMOKE_TEST_v1.5.64.md`:
   - Alternar tema Light/Dark → sem crash
   - Abrir ClientesV2 → Treeview renderiza
   - Verificar encoding UTF-8 → sem erros
4. Registrar resultado no arquivo smoke test
5. Commit e push do resultado

## 🎓 Referências

- GitHub PR: https://github.com/fharmacajr-a11y/rcv1.3.13/pulls
- GitHub Releases: https://github.com/fharmacajr-a11y/rcv1.3.13/releases
- GitHub Actions: https://github.com/fharmacajr-a11y/rcv1.3.13/actions
