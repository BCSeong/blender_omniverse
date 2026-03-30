@echo off
setlocal enableextensions

REM === Specimen From Maps Launcher ===
REM Converts height map + texture map into Blender 3D model
REM For clean ground-truth data only

REM -- Resolve project root (parent of scripts/) --
set "PROJECT_ROOT=%~dp0.."
pushd "%PROJECT_ROOT%" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to resolve project root.
    goto FAIL
)
set "PROJECT_ROOT=%CD%"
popd

echo [INFO] Project root: %PROJECT_ROOT%

REM -- Load blender.env --
set "ENV_FILE=%PROJECT_ROOT%\blender.env"
if not exist "%ENV_FILE%" (
    echo.
    echo [ERROR] blender.env not found.
    echo   1. copy blender.env.example blender.env
    echo   2. Edit blender.env and set BLENDER_PATH
    echo.
    goto FAIL
)

set "BLENDER_PATH="
for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
    if /i "%%A"=="BLENDER_PATH" set "BLENDER_PATH=%%B"
)

if "%BLENDER_PATH%"=="" (
    echo [ERROR] BLENDER_PATH not set in blender.env
    goto FAIL
)

echo [INFO] Blender: %BLENDER_PATH%

if not exist "%BLENDER_PATH%" (
    echo [ERROR] Blender not found: %BLENDER_PATH%
    goto FAIL
)

where claude >nul 2>&1
if errorlevel 1 (
    echo [ERROR] claude command not found in PATH.
    goto FAIL
)

if not exist "%PROJECT_ROOT%\scripts\specimen_from_maps_context.md" (
    echo [ERROR] scripts\specimen_from_maps_context.md not found.
    goto FAIL
)

REM -- Launch --
echo.
echo ================================================
echo   Specimen From Maps
echo   (height map + texture map -> Blender model)
echo ================================================
echo.
echo   For clean ground-truth data only.
echo   For noisy experimental data, use start_specimen.bat instead.
echo.

echo [INFO] Starting Blender (empty scene, mm units)...
start "Blender" "%BLENDER_PATH%" --python-expr "import bpy; [bpy.data.objects.remove(o) for o in list(bpy.data.objects)]; bpy.context.scene.unit_settings.system='METRIC'; bpy.context.scene.unit_settings.scale_length=0.001"

echo.
echo [INFO] Waiting for Blender to start...
timeout /t 5 /nobreak >nul
echo [INFO] Starting Claude Code (specimen from maps context)...
echo   Make sure Blender MCP addon is enabled.
echo.
cd /d "%PROJECT_ROOT%"
cmd /k claude --append-system-prompt-file scripts\specimen_from_maps_context.md "Print the welcome guide and verify MCP connection."
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
