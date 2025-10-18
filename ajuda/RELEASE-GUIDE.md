# 🚀 Guia de Finalização da Release v1.0.29

## 📋 Informações

- **Repositório:** `fharmacajr-a11y/rcv1.3.13`
- **PR de Integração:** `#1 – "Integrate v1.0.29 into main history"`
- **Branch Base:** `main`
- **Branch Compare:** `integrate/v1.0.29`
- **Tag da Release:** `v1.0.29`

---

## 🎯 Opções de Execução

### Opção 1: PowerShell Script Automatizado (RECOMENDADO)

Execute o script completo:

```powershell
# 1. Edite o arquivo e substitua YOUR_GITHUB_TOKEN
notepad release-commands.ps1

# 2. Execute o script
.\release-commands.ps1
```

### Opção 2: Comandos cURL Individuais

Execute os comandos do arquivo `release-curl-commands.ps1` um por um, copiando e colando no terminal.

### Opção 3: Bash Script (Git Bash/WSL)

```bash
# 1. Edite o arquivo e substitua YOUR_GITHUB_TOKEN
nano release-commands.sh

# 2. Execute o script
bash release-commands.sh
```

---

## 📝 Passo a Passo Manual (API GitHub)

### 1️⃣ Verificar Status do PR #1

```powershell
curl -X GET `
  -H "Authorization: token SEU_TOKEN_AQUI" `
  -H "Accept: application/vnd.github.v3+json" `
  "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/pulls/1"
```

**Verificar:**
- `"state": "open"` ✓
- `"mergeable": true` ✓
- Checks podem estar pendentes (pip-audit é report-only)

---

### 2️⃣ Fazer Merge do PR #1

```powershell
curl -X PUT `
  -H "Authorization: token SEU_TOKEN_AQUI" `
  -H "Accept: application/vnd.github.v3+json" `
  -H "Content-Type: application/json" `
  "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/pulls/1/merge" `
  -d '{\"commit_title\":\"Integrate v1.0.29 into main history\",\"merge_method\":\"merge\"}'
```

**Resposta esperada:**
```json
{
  "sha": "abc123...",
  "merged": true,
  "message": "Pull Request successfully merged"
}
```

---

### 3️⃣ Obter SHA da Branch Main

```powershell
curl -X GET `
  -H "Authorization: token SEU_TOKEN_AQUI" `
  -H "Accept: application/vnd.github.v3+json" `
  "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/git/ref/heads/main"
```

**Copie o SHA retornado:**
```json
{
  "ref": "refs/heads/main",
  "object": {
    "sha": "COPIE_ESTE_SHA",
    "type": "commit"
  }
}
```

---

### 4️⃣ Criar Tag v1.0.29

Substitua `MAIN_SHA_AQUI` pelo SHA copiado no passo anterior:

```powershell
curl -X POST `
  -H "Authorization: token SEU_TOKEN_AQUI" `
  -H "Accept: application/vnd.github.v3+json" `
  -H "Content-Type: application/json" `
  "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/git/refs" `
  -d '{\"ref\":\"refs/tags/v1.0.29\",\"sha\":\"MAIN_SHA_AQUI\"}'
```

**Resposta esperada:**
```json
{
  "ref": "refs/tags/v1.0.29",
  "object": {
    "sha": "abc123...",
    "type": "commit"
  }
}
```

---

### 5️⃣ Criar Release v1.0.29

```powershell
curl -X POST `
  -H "Authorization: token SEU_TOKEN_AQUI" `
  -H "Accept: application/vnd.github.v3+json" `
  -H "Content-Type: application/json" `
  "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/releases" `
  -d '{\"tag_name\":\"v1.0.29\",\"target_commitish\":\"main\",\"name\":\"v1.0.29\",\"body\":\"### v1.0.29 – Highlights\n\n- CI/Build\n  - Pipeline \\\"RC – test & build\\\" com Python 3.12 e pip-audit (report-only)\n  - Estrutura unificada de scripts/healthcheck\n  - Smoke + priorização de testes de PDF\n  - Retry de rede com `urllib3.Retry` e timeouts\n  - 24 testes estabilizados\n\n- Código & Features\n  - Dedup de utils/imports\n  - HubScreen adicionado à navegação\n  - Entrypoint unificado (app_core/gui)\n  - Filtros de logs e ajustes spec/env\n\n- Qualidade & Docs\n  - Pré-commit: remoção de BOM e reformatação (44 arquivos)\n  - `.gitattributes` normalizado (EOL)\n  - ZIP de referência via LFS\n  - Segurança: pip-audit rodando no CI\n\n> Observação: aviso benigno no job de testes — \\\"No files were found for .pytest_cache.\\\"\",\"draft\":false,\"prerelease\":false}'
```

**Resposta esperada:**
```json
{
  "id": 123456,
  "html_url": "https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.0.29",
  "tag_name": "v1.0.29",
  "name": "v1.0.29",
  "published_at": "2025-10-18T..."
}
```

---

## 🔍 Monitorar Workflow

Após criar a tag, o workflow **"RC - release"** será disparado automaticamente:

1. Acesse: https://github.com/fharmacajr-a11y/rcv1.3.13/actions
2. Procure pelo workflow acionado pela tag `v1.0.29`
3. Aguarde a conclusão (~5-10 minutos)
4. O ZIP será anexado à Release automaticamente

---

## 🔐 Calcular SHA256 do ZIP

Após o workflow completar:

```powershell
# 1. Baixe o ZIP da Release
# https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.0.29

# 2. Calcule o SHA256
Get-FileHash -Algorithm SHA256 "C:\Downloads\RC-Gestor-v1.0.29.zip"
```

---

## 📄 Atualizar Documentação

Após obter todos os dados, atualize `docs/CLAUDE-SONNET-v1.0.29/LOG.md`:

```markdown
## Release v1.0.29

**Data:** 18 de outubro de 2025

### Links
- **PR de Integração:** https://github.com/fharmacajr-a11y/rcv1.3.13/pull/1
- **Workflow Run:** https://github.com/fharmacajr-a11y/rcv1.3.13/actions/runs/XXXXXXX
- **Release:** https://github.com/fharmacajr-a11y/rcv1.3.13/releases/tag/v1.0.29

### Asset
- **Nome:** `RC-Gestor-v1.0.29.zip`
- **Tamanho:** XX.X MB
- **SHA256:** `abcdef1234567890...`

### Checklist de Segurança
- [x] `.env` NÃO incluído no bundle
- [x] pip-audit executado (report-only)
- [x] Hash SHA256 verificado
```

---

## ✅ Checklist Final

- [ ] PR #1 mergeado na `main`
- [ ] Tag `v1.0.29` criada
- [ ] Release publicada
- [ ] Workflow "RC - release" concluído
- [ ] ZIP anexado à Release
- [ ] SHA256 calculado
- [ ] Documentação atualizada
- [ ] `.env` confirmado como ausente no ZIP

---

## 🆘 Troubleshooting

### Erro: "Validation Failed" no merge
- Verifique se há conflitos no PR
- Certifique-se de que o PR está aberto (`state: open`)

### Erro: "Reference already exists" na criação da tag
- A tag já existe. Delete-a primeiro:
  ```powershell
  git push origin :refs/tags/v1.0.29
  ```

### Workflow não dispara automaticamente
- Verifique se o arquivo `.github/workflows/rc-release.yml` tem trigger em `tags`
- Dispare manualmente via Actions → "RC - release" → Run workflow

---

## 📞 Suporte

Em caso de dúvidas, verifique:
- [GitHub REST API Documentation](https://docs.github.com/en/rest)
- [Actions Documentation](https://docs.github.com/en/actions)
