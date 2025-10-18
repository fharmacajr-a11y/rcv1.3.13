# ================================================
# RELEASE v1.0.29 - COMANDOS POWERSHELL
# ================================================
# Substitua YOUR_GITHUB_TOKEN pelo seu token com scope 'repo'

$TOKEN = "YOUR_GITHUB_TOKEN"
$REPO = "fharmacajr-a11y/rcv1.3.13"
$PR_NUMBER = 1

$headers = @{
    "Authorization" = "token $TOKEN"
    "Accept" = "application/vnd.github.v3+json"
}

Write-Host "=================================================="
Write-Host "PASSO 1: Verificar status do PR #1"
Write-Host "=================================================="

$prStatus = Invoke-RestMethod -Uri "https://api.github.com/repos/$REPO/pulls/$PR_NUMBER" -Headers $headers
Write-Host "Estado: $($prStatus.state)"
Write-Host "Mergeável: $($prStatus.mergeable)"
Write-Host "Merged: $($prStatus.merged)"
Write-Host "Título: $($prStatus.title)"
Write-Host ""

Write-Host "=================================================="
Write-Host "PASSO 2: Fazer merge do PR #1"
Write-Host "=================================================="

$mergeBody = @{
    commit_title = "Integrate v1.0.29 into main history"
    merge_method = "merge"
} | ConvertTo-Json

$mergeResponse = Invoke-RestMethod -Uri "https://api.github.com/repos/$REPO/pulls/$PR_NUMBER/merge" `
    -Method Put `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $mergeBody

Write-Host "Merged: $($mergeResponse.merged)"
Write-Host "SHA: $($mergeResponse.sha)"
Write-Host "Message: $($mergeResponse.message)"
Write-Host ""

Write-Host "=================================================="
Write-Host "PASSO 3: Obter SHA da branch main"
Write-Host "=================================================="

$mainRef = Invoke-RestMethod -Uri "https://api.github.com/repos/$REPO/git/ref/heads/main" -Headers $headers
$mainSHA = $mainRef.object.sha
Write-Host "Main SHA: $mainSHA"
Write-Host ""

Write-Host "=================================================="
Write-Host "PASSO 4: Criar tag v1.0.29"
Write-Host "=================================================="

$tagBody = @{
    ref = "refs/tags/v1.0.29"
    sha = $mainSHA
} | ConvertTo-Json

$tagResponse = Invoke-RestMethod -Uri "https://api.github.com/repos/$REPO/git/refs" `
    -Method Post `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $tagBody

Write-Host "Tag criada: $($tagResponse.ref)"
Write-Host "SHA: $($tagResponse.object.sha)"
Write-Host ""

Write-Host "=================================================="
Write-Host "PASSO 5: Criar Release v1.0.29"
Write-Host "=================================================="

$releaseBody = @{
    tag_name = "v1.0.29"
    target_commitish = "main"
    name = "v1.0.29"
    body = @"
### v1.0.29 – Highlights

- CI/Build
  - Pipeline "RC – test & build" com Python 3.12 e pip-audit (report-only)
  - Estrutura unificada de scripts/healthcheck
  - Smoke + priorização de testes de PDF
  - Retry de rede com ``urllib3.Retry`` e timeouts
  - 24 testes estabilizados

- Código & Features
  - Dedup de utils/imports
  - HubScreen adicionado à navegação
  - Entrypoint unificado (app_core/gui)
  - Filtros de logs e ajustes spec/env

- Qualidade & Docs
  - Pré-commit: remoção de BOM e reformatação (44 arquivos)
  - ``.gitattributes`` normalizado (EOL)
  - ZIP de referência via LFS
  - Segurança: pip-audit rodando no CI

> Observação: aviso benigno no job de testes — "No files were found for .pytest_cache."
"@
    draft = $false
    prerelease = $false
} | ConvertTo-Json

$releaseResponse = Invoke-RestMethod -Uri "https://api.github.com/repos/$REPO/releases" `
    -Method Post `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $releaseBody

Write-Host "Release ID: $($releaseResponse.id)"
Write-Host "Release URL: $($releaseResponse.html_url)"
Write-Host "Tag: $($releaseResponse.tag_name)"
Write-Host "Published: $($releaseResponse.published_at)"
Write-Host ""

Write-Host "=================================================="
Write-Host "✓ RELEASE CONCLUÍDA"
Write-Host "=================================================="
Write-Host "Release URL: $($releaseResponse.html_url)"
Write-Host ""
Write-Host "Próximos passos:"
Write-Host "1. Aguarde o workflow 'RC - release' completar"
Write-Host "2. Baixe o ZIP do asset"
Write-Host "3. Calcule SHA256: Get-FileHash -Algorithm SHA256 arquivo.zip"
Write-Host "4. Atualize docs/CLAUDE-SONNET-v1.0.29/LOG.md"
Write-Host "=================================================="
