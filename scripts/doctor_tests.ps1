Write-Host "=== RC Doctor: repo/venv/pytest/coverage ==="

Write-Host "`n[Repo]"
Write-Host ("PWD=" + (Get-Location))
Write-Host ("has tests/conftest.py? " + (Test-Path .\tests\conftest.py))
Write-Host ("has src/? " + (Test-Path .\src))

Write-Host "`n[Python/venv]"
try { (Get-Command python).Source | ForEach-Object { Write-Host ("python=" + $_) } } catch { Write-Host "python not found in PATH" }
python -c "import sys,os; print('sys.executable=',sys.executable); print('version=',sys.version); print('VIRTUAL_ENV=',os.getenv('VIRTUAL_ENV'))"
python -m pip -V

Write-Host "`n[Pytest]"
python -m pytest --version

Write-Host "`n[Env vars relevantes]"
$vars = @('PYTEST_ADDOPTS','PYTHONPATH','RC_TESTING','RC_RUN_GUI_TESTS','COVERAGE_FILE','COVERAGE_RCFILE')
foreach ($v in $vars) {
    $val = Get-Item -Path "Env:$v" -ErrorAction SilentlyContinue
    Write-Host ("$v=" + $val.Value)
}

Write-Host "`n[Cache]"
Write-Host (".pytest_cache exists? " + (Test-Path .\.pytest_cache))
if (Test-Path .\.pytest_cache) {
  $count = (Get-ChildItem .\.pytest_cache -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
  Write-Host ("pytest cache entries=" + $count)
}

Write-Host "`n[Coverage files]"
Write-Host (".coverage exists? " + (Test-Path .\.coverage))
if (Test-Path .\.coverage) {
  $size = (Get-Item .\.coverage).Length
  Write-Host (".coverage bytes=" + $size)
}

Write-Host "`n[Sanity: Tk]"
python -c "import tkinter as tk; r=tk.Tk(); r.withdraw(); print('tk ok, patchlevel=', r.tk.call('info','patchlevel')); r.destroy()"
