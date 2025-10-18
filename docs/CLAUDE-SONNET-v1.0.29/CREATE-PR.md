# Script para criar Pull Request - Step 2

## Passo 1: Push da Branch

```powershell
git push -u origin maintenance/v1.0.29
```

## Passo 2: Criar PR no GitHub/GitLab

### Via GitHub CLI (gh)
```powershell
gh pr create `
  --base feature/prehome-hub `
  --title "Step 2 – Segredos & Build seguro (sem .env no bundle)" `
  --body-file docs/CLAUDE-SONNET-v1.0.29/STEP-2-PR.md
```

### Via Interface Web

1. Acesse: https://github.com/[seu-usuario]/[seu-repo]/compare/feature/prehome-hub...maintenance/v1.0.29
2. Clique em "Create Pull Request"
3. Título: **Step 2 – Segredos & Build seguro (sem .env no bundle)**
4. Descrição: Copie o conteúdo de `docs/CLAUDE-SONNET-v1.0.29/STEP-2-PR.md`

## Resumo do PR

**3 bullets principais**:

1. ✅ **`.env` confirmado ausente do bundle** - Build PyInstaller configurado para empacotar APENAS recursos públicos (`rc.ico`, `rc.png`). Verificação automatizada confirma que nenhum arquivo `.env` foi incluído no executável.

2. ✅ **Filtro de logs com redação automática** - Implementado `RedactSensitiveData` em `shared/logging/filters.py` baseado em OWASP Secrets Management. Redacta automaticamente: tokens, senhas, API keys e outros segredos nos logs.

3. ✅ **Spec seguro versionado e smoke build validado** - Arquivo `build/rc_gestor.spec` versionado com documentação inline. Build executado com sucesso, executável testado e funcional. Documentação completa em `build/BUILD.md` e `build/BUILD-REPORT.md`.

## Artefatos Anexados

- `build/BUILD-REPORT.md` - Relatório completo do build com verificações de segurança
- `build/rc_gestor.spec` - Configuração PyInstaller segura
- `docs/CLAUDE-SONNET-v1.0.29/LOG.md` - Log de todas as alterações

## Commits Incluídos

```
22a241b docs: adicionar resumo do PR Step 2
6ca9d96 Step 2 – Segredos & Build seguro: filtro de logs, .spec sem .env, smoke build validado
ad17487 Step 1 – Entrypoint unificado: confirmação de app_gui.py como entrypoint único
```

## Próximos Steps

Após merge deste PR, aguardar instruções para **Step 3**.
