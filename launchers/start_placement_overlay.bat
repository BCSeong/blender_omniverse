@echo off
setlocal enableextensions

REM === Placement Overlay Launcher ===
REM Generates annotated board image with component Placement IDs

REM -- Resolve project root (parent of launchers/) --
set "PROJECT_ROOT=%~dp0.."
pushd "%PROJECT_ROOT%" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to resolve project root.
    goto FAIL
)
set "PROJECT_ROOT=%CD%"
popd

echo [INFO] Project root: %PROJECT_ROOT%

REM -- Find Python with Pillow --
set "PYTHON_PATH="

REM Try common venv locations
for %%P in (
    "%USERPROFILE%\.venv39\Scripts\python.exe"
    "%USERPROFILE%\.venv\Scripts\python.exe"
    "%PROJECT_ROOT%\.venv\Scripts\python.exe"
    "%PROJECT_ROOT%\venv\Scripts\python.exe"
) do (
    if exist %%P (
        %%P -c "from PIL import Image" >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_PATH=%%~P"
            goto PYTHON_FOUND
        )
    )
)

REM Try system python
where python >nul 2>&1
if not errorlevel 1 (
    python -c "from PIL import Image" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_PATH=python"
        goto PYTHON_FOUND
    )
)

echo [ERROR] Python with Pillow not found.
echo   Install Pillow: pip install Pillow
goto FAIL

:PYTHON_FOUND
echo [INFO] Python: %PYTHON_PATH%

REM -- Check claude CLI --
where claude >nul 2>&1
if errorlevel 1 (
    echo [ERROR] claude command not found in PATH.
    goto FAIL
)

if not exist "%PROJECT_ROOT%\launchers\contexts\placement-overlay.md" (
    echo [ERROR] launchers\contexts\placement-overlay.md not found.
    goto FAIL
)

REM -- Get input paths --
echo.
echo ================================================
echo   Placement Overlay Generator
echo ================================================
echo.
echo   Generates an annotated board image with
echo   component Placement IDs from CSV data.
echo.
echo   Required: CSV file + Board thumbnail image
echo   Optional: GBX (Gerber) files in the same dir
echo.

set /p "CSV_PATH=CSV file path: "
if not exist "%CSV_PATH%" (
    echo [ERROR] CSV file not found: %CSV_PATH%
    goto FAIL
)

set /p "IMG_PATH=Board thumbnail path: "
if not exist "%IMG_PATH%" (
    echo [ERROR] Image file not found: %IMG_PATH%
    goto FAIL
)

echo.
echo [INFO] CSV: %CSV_PATH%
echo [INFO] Image: %IMG_PATH%
echo [INFO] Starting Claude Code (placement-overlay context)...
echo.

cd /d "%PROJECT_ROOT%"
set "PYTHON_PATH=%PYTHON_PATH%"
cmd /k claude --append-system-prompt-file launchers\contexts\placement-overlay.md "CSV: %CSV_PATH% / Thumbnail: %IMG_PATH% / Generate placement overlay. Use python at: %PYTHON_PATH%"

goto DONE

:FAIL
echo.
echo [FAIL] See messages above.
echo.
pause
goto :eof

:DONE
echo.
pause
goto :eof
