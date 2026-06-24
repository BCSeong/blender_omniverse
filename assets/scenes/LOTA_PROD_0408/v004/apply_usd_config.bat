@echo off
setlocal

set ROOT=%~dp0..\..\..\..
set PYTHON=%ROOT%\.venv_py312\Scripts\python.exe
set SCRIPT=%ROOT%\scripts\add_lighting_variants.py
set USD_FILE=%~dp0lota-16m10-v3-rev2_v004.usdc
set CONFIG=%~dp0usd_config.json

echo Applying USD config...
echo   USD:    %USD_FILE%
echo   Config: %CONFIG%
echo.

"%PYTHON%" "%SCRIPT%" "%USD_FILE%" "%CONFIG%"

echo.
if %ERRORLEVEL% EQU 0 (
    echo Done.
) else (
    echo ERROR: Script failed with exit code %ERRORLEVEL%
)

pause
