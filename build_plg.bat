@echo off
setlocal
cd /d "%~dp0"

echo Building web UI...
pushd web
call npm run build
if errorlevel 1 (
  echo npm build failed.
  popd
  goto :fail
)
popd

echo Building PLG.exe with bundled starter sounds...
python -c "from build_bundled_sounds import ensure_bundled_sounds; ensure_bundled_sounds()" || goto :fail
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
echo Starter sounds + web UI are inside the exe.
pause
exit /b 0

:fail
echo Build failed.
pause
exit /b 1
