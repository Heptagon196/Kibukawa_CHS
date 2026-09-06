@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" bepinex
set "result=%errorlevel%"
if not "%result%"=="0" echo Build failed. Check the error above.
if /I not "%~1"=="--no-pause" pause
exit /b %result%
