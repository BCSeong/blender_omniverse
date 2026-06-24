@echo off
setlocal enableextensions

REM === Omniverse Batch Renderer GUI ===
REM Launches PySide6 render configuration and monitoring GUI.
REM Requires: Python 3.10+, PySide6

set "SCRIPT=%~dp0render_gui.py"
set "VENV=%~dp0..\.venv_py312\Scripts\activate.bat"

if exist "%VENV%" (
    call "%VENV%"
)

if not exist "%SCRIPT%" (
    echo [ERROR] render_gui.py not found: %SCRIPT%
    pause
    exit /b 1
)

python -c "import PySide6" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] PySide6 not found. Installing...
    pip install PySide6
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install PySide6. Check Python/pip setup.
        pause
        exit /b 1
    )
)

echo [INFO] Starting Render GUI...
python "%SCRIPT%"
endlocal
