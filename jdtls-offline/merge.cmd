@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0merge.ps1"
if errorlevel 1 (echo Merge failed. & pause & exit /b 1)
pause
