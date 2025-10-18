# 🎯 COMANDOS RÁPIDOS - Release v1.0.29

## ⚡ Execução Rápida (PowerShell)

### Pré-requisito
Obtenha seu token GitHub em: https://github.com/settings/tokens
- Scope necessário: `repo`

### Método 1: Script Automatizado (RECOMENDADO)
```powershell
# 1. Configure o token
$TOKEN = "ghp_SeuTokenAqui"

# 2. Execute
.\release-commands.ps1
```

### Método 2: Comandos Individuais

#### Substitua SEU_TOKEN em todos os comandos abaixo

```powershell
# 1. Verificar PR
curl -H "Authorization: token SEU_TOKEN" "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/pulls/1"

# 2. Merge PR
curl -X PUT -H "Authorization: token SEU_TOKEN" -H "Content-Type: application/json" "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/pulls/1/merge" -d '{\"commit_title\":\"Integrate v1.0.29 into main history\",\"merge_method\":\"merge\"}'

# 3. Obter SHA da main (copie o valor de object.sha)
curl -H "Authorization: token SEU_TOKEN" "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/git/ref/heads/main"

# 4. Criar tag (substitua SHA_DA_MAIN pelo valor copiado)
curl -X POST -H "Authorization: token SEU_TOKEN" -H "Content-Type: application/json" "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/git/refs" -d '{\"ref\":\"refs/tags/v1.0.29\",\"sha\":\"SHA_DA_MAIN\"}'

# 5. Criar Release (comando longo - veja arquivo release-curl-commands.ps1)
# Copie do arquivo release-curl-commands.ps1 linha 45-48
```

---

## 📊 Saídas Esperadas

Após executar todos os comandos, você terá:

1. **PR Mergeado**
   - URL: `https://github.com/fharmacajr-a11y/rcv1.3.13/pull/1`
   - Commit SHA: `abc123...`

2. **Tag Criada**
   - Tag: `v1.0.29`
   - SHA: (mesmo da main)

3. **Release Publicada**
   - URL: `https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.0.29`
   - Assets: ZIP será adicionado pelo workflow

4. **Workflow Disparado**
   - Nome: "RC - release"
   - Trigger: tag `v1.0.29`
   - URL: `https://github.com/fharmacajr-a11y/rcv1.3.13/actions`

---

## 🔐 Após Workflow Completar

```powershell
# 1. Baixe o ZIP da Release
Start-Process "https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.0.29"

# 2. Calcule SHA256
Get-FileHash -Algorithm SHA256 ".\RC-Gestor-v1.0.29.zip"

# 3. Verifique tamanho
(Get-Item ".\RC-Gestor-v1.0.29.zip").Length / 1MB
```

---

## 📝 Template para Documentação

Após obter todos os dados, adicione ao `docs/CLAUDE-SONNET-v1.0.29/LOG.md`:

```markdown
## Release v1.0.29

**Data:** 18 de outubro de 2025

### Links
- **PR:** #1
- **Workflow:** https://github.com/fharmacajr-a11y/rcv1.3.13/actions/runs/XXXXX
- **Release:** https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.0.29

### Asset
- **Nome:** RC-Gestor-v1.0.29.zip
- **Tamanho:** XX.X MB
- **SHA256:** [cole aqui]

### Segurança
- [x] .env NÃO incluído
- [x] pip-audit ok
```

---

## 🚨 Resolução de Problemas

| Erro | Solução |
|------|---------|
| "Validation Failed" | PR tem conflitos ou não está open |
| "Reference already exists" | Tag já existe - delete: `git push origin :refs/tags/v1.0.29` |
| Workflow não dispara | Verifique trigger em `.github/workflows/rc-release.yml` |
| 401 Unauthorized | Token inválido ou sem scope `repo` |

---

## 📁 Arquivos Criados

1. `release-commands.ps1` - Script PowerShell completo
2. `release-commands.sh` - Script Bash completo
3. `release-curl-commands.ps1` - Comandos curl individuais
4. `RELEASE-GUIDE.md` - Guia detalhado completo
5. `QUICK-START.md` - Este arquivo (comandos rápidos)

---

## ✅ Próximos Passos

1. [ ] Execute os comandos acima
2. [ ] Aguarde workflow completar
3. [ ] Baixe o ZIP e calcule SHA256
4. [ ] Atualize LOG.md
5. [ ] Commit: `docs: Release v1.0.29 — links + SHA256`
