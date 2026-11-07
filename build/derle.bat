@echo off
rem Optimizer Pro - hizli derleme
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo [hata] .venv bulunamadi. Once: python -m venv .venv
  exit /b 1
)
".venv\Scripts\python.exe" "build\build.py" %*
exit /b %errorlevel%
