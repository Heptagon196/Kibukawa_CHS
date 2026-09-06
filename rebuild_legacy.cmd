@echo off
setlocal
echo Legacy offline resource build. Use rebuild.cmd for the BepInEx full package.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" legacy-build
set "result=%errorlevel%"
if /I not "%~1"=="--no-pause" pause
exit /b %result%
