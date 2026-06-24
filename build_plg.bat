@echo off

setlocal

cd /d "%~dp0"



set BUILD_MODE=%1

if /I "%BUILD_MODE%"=="release" set PLG_BUILD_RELEASE=1



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



echo Generating app icon from logo...

python scripts\make_icon.py || goto :fail



where pyinstaller >nul 2>&1

if errorlevel 1 (

  echo Installing PyInstaller...

  pip install pyinstaller

)



pyinstaller --noconfirm PLG.spec

if errorlevel 1 goto :fail



if defined PLG_BUILD_RELEASE (

  echo Copying release .env template to dist...

  copy /Y ".env.release" "dist\.env" >nul

  echo.

  echo RELEASE BUILD — edit dist\.env with SUPABASE_URL and SUPABASE_ANON_KEY before shipping.

  echo See desktop\clean-windows-test.md for VM checklist.

)



if not defined PLG_SIGN_TIMESTAMP set PLG_SIGN_TIMESTAMP=http://timestamp.digicert.com

if defined PLG_SIGN_CERT (

  echo Signing with PLG_SIGN_CERT...

  signtool sign /fd SHA256 /tr "%PLG_SIGN_TIMESTAMP%" /td SHA256 /n "%PLG_SIGN_CERT%" "dist\PLG.exe"

) else if defined PLG_SIGN_THUMBPRINT (

  echo Signing with thumbprint...

  signtool sign /fd SHA256 /tr "%PLG_SIGN_TIMESTAMP%" /td SHA256 /sha1 "%PLG_SIGN_THUMBPRINT%" "dist\PLG.exe"

) else (

  echo Skipping code sign — set PLG_SIGN_CERT or PLG_SIGN_THUMBPRINT. See desktop\release-signing.md

)



echo.

echo Done: dist\PLG.exe

if defined PLG_BUILD_RELEASE echo Config: dist\.env

echo Starter sounds + web UI are inside the exe.

pause

exit /b 0



:fail

echo Build failed.

pause

exit /b 1

