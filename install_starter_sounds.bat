@echo off
setlocal
cd /d "%~dp0"
echo PLG — optional CC0 starter upgrade
echo Bundled sounds are already included — skip this unless you want trap packs.
echo.
python download_starter_pack.py
echo.
pause
