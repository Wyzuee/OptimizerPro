@echo off
rem Optimizer Pro - gelistirme modunda calistir (deneme modu)
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" "app\main.py" --dry-run %*
