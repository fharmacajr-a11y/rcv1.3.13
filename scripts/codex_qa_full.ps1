$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

# repo root (scripts/ -> raiz)
Set-Location (Resolve-Path "$PSScriptRoot\..")

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$logDir = Join-Path (Get-Location) ("logs\qa_full_" + $ts)
New-Item -ItemType Directory -Force $logDir | Out-Null

$summary = New-Object System.Collections.Generic.List[object]

function Run-Step([string]$name, [scriptblock]$cmd) {
  Write-Host ""
  Write-Host "===================="
  Write-Host "STEP: $name"
  Write-Host "===================="

  $log = Join-Path $logDir ($name + ".log.txt")

  # Executa e loga stdout+stderr
  & $cmd 2>&1 | Tee-Object -FilePath $log

  # Captura exit code (quando aplicável)
  $code = $LASTEXITCODE
  if ($null -eq $code) { $code = 0 }

  $summary.Add([pscustomobject]@{
    step = $name
    exitCode = $code
    log = $log
  }) | Out-Null

  Write-Host ("ExitCode=" + $code)
  Write-Host ("Log=" + $log)
}

# (0) Doctor do projeto (já existe)
Run-Step "doctor_tests" { .\scripts\doctor_tests.ps1 }

# (1) Sanidade: compilar (pega SyntaxError cedo)
Run-Step "compileall" { python -m compileall src adapters infra data security -q }

# (2) Ruff: registrar antes + auto-fix + format + recheck
Run-Step "ruff_check_before" { python -m ruff check . }
Run-Step "ruff_fix"          { python -m ruff check . --fix }
Run-Step "ruff_format"       { python -m ruff format . }
Run-Step "ruff_check_after"  { python -m ruff check . }

# (3) Type checkers
Run-Step "pyright" { pyright }
Run-Step "mypy"    { python -m mypy src adapters infra data security }

# (4) Dependências
Run-Step "deptry" { deptry . }

# (5) Dead code
Run-Step "vulture" { python -m vulture }

# (6) Segurança (usa seu bandit.yaml)
Run-Step "bandit" { bandit -r src infra adapters data security -c bandit.yaml }

# (7) Pytest modo rápido (sem cobertura) + smoke (se quiser primeiro)
Run-Step "pytest_smoke" { python -m pytest --smoke -c pytest.ini -ra --continue-on-collection-errors }

# (8) Pytest FULL + COBERTURA GLOBAL (usa pytest_cov.ini do repo)
# Obs: seu pytest_cov.ini já define --cov-report html/json/xml e --cov-config.
Run-Step "pytest_cov_full" { python -m pytest -c pytest_cov.ini -ra --continue-on-collection-errors }

# (9) Ranking de cobertura (usa reports/coverage.json como fallback)
Run-Step "coverage_ranking" { python .\scripts\coverage_ranking.py }

# Salvar sumário
$summary | Format-Table -AutoSize | Out-String | Set-Content -Encoding UTF8 (Join-Path $logDir "SUMMARY.txt")
$summary | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $logDir "SUMMARY.json")

Write-Host ""
Write-Host "✅ QA FULL terminou. Veja:"
Write-Host ("  - " + (Join-Path $logDir "SUMMARY.txt"))
Write-Host ("  - logs em: " + $logDir)
Write-Host ""
Write-Host "Cobertura (se gerou): htmlcov\index.html e reports\coverage.json"
Write-Host ""

exit 0
