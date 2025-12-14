# coverage_global.ps1
# Gera relatório de cobertura completo do projeto na raiz

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

# Evita redirecionamento por ambiente (causa 'some/aparece')
Remove-Item Env:COVERAGE_FILE -ErrorAction SilentlyContinue

# Opcional: limpar antes de gerar (mantém sempre consistente)
Remove-Item -Recurse -Force ".\reports\coverage" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\htmlcov" -ErrorAction SilentlyContinue
Remove-Item -Force ".\coverage.json" -ErrorAction SilentlyContinue
Get-ChildItem -Force ".\.coverage*" -ErrorAction SilentlyContinue | Remove-Item -Force

# Rodar cobertura global gerando tudo na raiz
py -m pytest -q -c pytest.ini `
  --cov-report=term-missing `
  --cov-report=html:htmlcov `
  --cov-report=json:coverage.json

Write-Host ""
Write-Host "OK: gerado htmlcov\index.html e coverage.json na raiz."
Write-Host "Dica: abra htmlcov\index.html no navegador."
