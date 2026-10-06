@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo First install the project as described in README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -B -m solar_simulator gui
if errorlevel 1 pause
