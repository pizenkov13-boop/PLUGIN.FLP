@echo off
cd /d "%~dp0"
pythonw "%~dp0PLG.pyw" 2>nul
if errorlevel 1 (
  echo PLG could not start. Trying with console for error details...
  python "%~dp0plg_app.py"
  pause
)
