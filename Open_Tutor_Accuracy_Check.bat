@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_tutor_accuracy_check.ps1"
if errorlevel 1 pause
