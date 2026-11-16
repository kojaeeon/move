@echo off
cd /d "%~dp0"
copy /b "wordcraft-0.18.1-windows-x64-portable.zip.001"+"wordcraft-0.18.1-windows-x64-portable.zip.002"+"wordcraft-0.18.1-windows-x64-portable.zip.003"+"wordcraft-0.18.1-windows-x64-portable.zip.004"+"wordcraft-0.18.1-windows-x64-portable.zip.005" "wordcraft-0.18.1-windows-x64-portable.zip"
if errorlevel 1 exit /b 1
echo ZIP merged. Extract the ZIP to run WordCraft.
pause
