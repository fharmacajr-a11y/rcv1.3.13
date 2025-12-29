@echo off
setlocal
cd /d "%~dp0"

set "PYEXE=python"
if exist ".venv\Scripts\python.exe" set "PYEXE=.venv\Scripts\python.exe"

rem Inicia o app (Tkinter)
"%PYEXE%" "main.py"

endlocal
