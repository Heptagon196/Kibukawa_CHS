@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" bepinex
set "result=%errorlevel%"
if not "%result%"=="0" echo Build failed. Do not use output without build_report.json.
if /I not "%~1"=="--no-pause" pause
exit /b %result%
