@echo off
setlocal
cd /d "%~dp0"

if not exist "web\dist\index.html" (
  echo Building web UI...
  pushd web
  call npm run build
  if errorlevel 1 (
    echo npm build failed — install Node.js and run: cd web ^&^& npm install ^&^& npm run build
    popd
    goto :fallback
  )
  popd
)

pythonw "%~dp0PLG.pyw" 2>nul
if not errorlevel 1 exit /b 0

:fallback
echo PLG webview could not start. Trying legacy tkinter UI...
python "%~dp0plg_app.py"
pause
