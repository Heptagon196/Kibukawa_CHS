@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" extract
set "result=%errorlevel%"
if not "%result%"=="0" echo Extraction failed. See the error above.
if /I not "%~1"=="--no-pause" pause
exit /b %result%
