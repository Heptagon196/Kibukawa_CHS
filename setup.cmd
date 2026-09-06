@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0games/01-kamen-gensou/scripts/setup.ps1"
set "result=%errorlevel%"
pause
exit /b %result%
