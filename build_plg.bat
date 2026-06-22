@echo off
setlocal
cd /d "%~dp0"

echo Building PLG.exe with bundled starter sounds...
python -c "from starter_kit import ensure_starter_kit; ensure_starter_kit()" || goto :fail

where pyinstaller >nul 2>&1
if errorlevel 1 (
  echo Installing PyInstaller...
  pip install pyinstaller
)

pyinstaller --noconfirm PLG.spec
if errorlevel 1 goto :fail

echo.
echo Done: dist\PLG.exe
echo Starter sounds are inside the exe — no Signature Sounds download needed.
pause
exit /b 0

:fail
echo Build failed.
pause
exit /b 1
