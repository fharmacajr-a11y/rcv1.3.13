# coverage_clean.ps1
# Remove todos os artefatos de coverage gerados anteriormente

$ErrorActionPreference = "SilentlyContinue"

Remove-Item -Recurse -Force ".\reports\coverage"
Remove-Item -Recurse -Force ".\htmlcov"
Remove-Item -Force ".\coverage.json"
Get-ChildItem -Force ".\.coverage*" | Remove-Item -Force

Write-Host "OK: coverage artifacts removidos (reports/coverage, htmlcov, coverage.json, .coverage*)"
