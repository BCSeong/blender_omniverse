@echo off
setlocal enableextensions

REM === Package Authoring Launcher ===
REM Create 3D models of electronic component packages
REM Assets are saved for PCB assembly pipeline

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

if not exist "%PROJECT_ROOT%\launchers\contexts\build-package.md" (
    echo [ERROR] launchers\contexts\build-package.md not found.
    goto FAIL
)

REM -- Launch --
echo.
echo ================================================
echo   Package Authoring
echo   (electronic component 3D modeling)
echo ================================================
echo.
echo   Create reusable 3D package assets for PCB assembly.
echo   Assets are matched by gerber component name.
echo.

echo [INFO] Starting Blender (empty scene, mm units)...
start "Blender" "%BLENDER_PATH%" --python-expr "import bpy; [bpy.data.objects.remove(o) for o in list(bpy.data.objects)]; bpy.context.scene.unit_settings.system='METRIC'; bpy.context.scene.unit_settings.scale_length=0.001; [setattr(s.region_3d, 'view_perspective', 'ORTHO') for a in bpy.context.screen.areas if a.type=='VIEW_3D' for s in a.spaces if s.type=='VIEW_3D']"

echo.
echo [INFO] Waiting for Blender to start...
timeout /t 5 /nobreak >nul
echo [INFO] Starting Claude Code (package authoring context)...
echo   Make sure Blender MCP addon is enabled.
echo.
cd /d "%PROJECT_ROOT%"
cmd /k claude --append-system-prompt-file launchers\contexts\build-package.md "Print the welcome guide and verify MCP connection."
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
