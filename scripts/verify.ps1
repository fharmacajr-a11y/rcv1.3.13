<#
.SYNOPSIS
    Roda todos os quality-gates do projeto em sequência.
    Qualquer falha interrompe imediatamente com exit 1.

.DESCRIPTION
    1) ruff check src/
    2) pytest tests/ -q
    3) bandit -r src/ (severity >= medium)
    4) pip-audit --desc

.EXAMPLE
    .\scripts\verify.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Step {
    param([string]$Label, [string]$Command)
    Write-Host "`n===== $Label =====" -ForegroundColor Cyan
    Invoke-Expression $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: $Label (exit code $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
    Write-Host "OK: $Label" -ForegroundColor Green
}

Invoke-Step "ruff"      "python -m ruff check src/"
Invoke-Step "pytest"    "python -m pytest tests/ -q --timeout=60"
Invoke-Step "bandit"    "python -m bandit -r src/ -c bandit.yaml --severity-level medium"
Invoke-Step "pip-audit" "python -m pip_audit --desc"

# --- Coverage (opcional: RC_WITH_COV=1) ---
if ($env:RC_WITH_COV -eq "1") {
    # Garante que o diretório de relatórios exista
    if (-not (Test-Path "reports")) { New-Item -ItemType Directory -Path "reports" | Out-Null }
    Invoke-Step "coverage" "python -m pytest tests/ -q --timeout=60 --cov=src --cov-report=term-missing:skip-covered --cov-report=json:reports/coverage.json"
}

Write-Host "`n===== ALL CHECKS PASSED =====" -ForegroundColor Green
