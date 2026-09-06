@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" verify
set "result=%errorlevel%"
if /I not "%~1"=="--no-pause" pause
exit /b %result%
