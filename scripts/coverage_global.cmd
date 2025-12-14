@echo off
REM coverage_global.cmd
REM Gera relatório de cobertura completo do projeto na raiz (versão CMD)

setlocal
cd /d "%~dp0.."

set "COVERAGE_FILE="

py -m pytest -q -c pytest.ini --cov-report=term-missing --cov-report=html:htmlcov --cov-report=json:coverage.json
echo.
echo OK: htmlcov\index.html e coverage.json na raiz
endlocal
