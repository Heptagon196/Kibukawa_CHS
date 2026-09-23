@echo off
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" serve.py
) else (
  python serve.py
)
pause
