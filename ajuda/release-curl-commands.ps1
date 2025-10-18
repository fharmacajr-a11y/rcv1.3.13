# ================================================
# RELEASE v1.0.29 - COMANDOS CURL (Windows/PowerShell)
# ================================================
# Substitua YOUR_GITHUB_TOKEN pelo seu token com scope 'repo'
# Execute cada comando em ordem e aguarde o resultado

# ========================================
# PASSO 1: Verificar status do PR #1
# ========================================

curl -X GET `
  -H "Authorization: token YOUR_GITHUB_TOKEN" `
  -H "Accept: application/vnd.github.v3+json" `
  "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/pulls/1"

# ========================================
# PASSO 2: Fazer merge do PR #1
# ========================================

curl -X PUT `
  -H "Authorization: token YOUR_GITHUB_TOKEN" `
  -H "Accept: application/vnd.github.v3+json" `
  -H "Content-Type: application/json" `
  "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/pulls/1/merge" `
  -d '{\"commit_title\":\"Integrate v1.0.29 into main history\",\"merge_method\":\"merge\"}'

# ========================================
# PASSO 3: Obter SHA da branch main
# ========================================

curl -X GET `
  -H "Authorization: token YOUR_GITHUB_TOKEN" `
  -H "Accept: application/vnd.github.v3+json" `
  "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/git/ref/heads/main"

# Copie o SHA retornado (campo "sha" dentro de "object") e substitua MAIN_SHA_AQUI abaixo

# ========================================
# PASSO 4: Criar tag v1.0.29
# ========================================

curl -X POST `
  -H "Authorization: token YOUR_GITHUB_TOKEN" `
  -H "Accept: application/vnd.github.v3+json" `
  -H "Content-Type: application/json" `
  "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/git/refs" `
  -d '{\"ref\":\"refs/tags/v1.0.29\",\"sha\":\"MAIN_SHA_AQUI\"}'

# ========================================
# PASSO 5: Criar Release v1.0.29
# ========================================

curl -X POST `
  -H "Authorization: token YOUR_GITHUB_TOKEN" `
  -H "Accept: application/vnd.github.v3+json" `
  -H "Content-Type: application/json" `
  "https://api.github.com/repos/fharmacajr-a11y/rcv1.3.13/releases" `
  -d '{\"tag_name\":\"v1.0.29\",\"target_commitish\":\"main\",\"name\":\"v1.0.29\",\"body\":\"### v1.0.29 – Highlights\n\n- CI/Build\n  - Pipeline \\\"RC – test & build\\\" com Python 3.12 e pip-audit (report-only)\n  - Estrutura unificada de scripts/healthcheck\n  - Smoke + priorização de testes de PDF\n  - Retry de rede com `urllib3.Retry` e timeouts\n  - 24 testes estabilizados\n\n- Código & Features\n  - Dedup de utils/imports\n  - HubScreen adicionado à navegação\n  - Entrypoint unificado (app_core/gui)\n  - Filtros de logs e ajustes spec/env\n\n- Qualidade & Docs\n  - Pré-commit: remoção de BOM e reformatação (44 arquivos)\n  - `.gitattributes` normalizado (EOL)\n  - ZIP de referência via LFS\n  - Segurança: pip-audit rodando no CI\n\n> Observação: aviso benigno no job de testes — \\\"No files were found for .pytest_cache.\\\"\",\"draft\":false,\"prerelease\":false}'

# ========================================
# DEPOIS: Calcular SHA256 do ZIP
# ========================================

# Após o workflow completar e o ZIP estar disponível na Release:
# Get-FileHash -Algorithm SHA256 C:\caminho\para\RC-Gestor-v1.0.29.zip
