@echo off
setlocal enableextensions

REM === Specimen Authoring Launcher ===
REM Launches Blender + Claude Code with specimen context

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

if not exist "%PROJECT_ROOT%\scripts\specimen_context.md" (
    echo [ERROR] scripts\specimen_context.md not found.
    goto FAIL
)

REM -- Interactive menu --
echo.
echo ================================================
echo   Specimen Authoring Launcher
echo ================================================
echo.
echo   1. New specimen (blank scene, mm units)
echo   2. Open existing .blend file
echo   3. Cancel
echo.
set /p "CHOICE=Select [1/2/3]: "

if "%CHOICE%"=="3" goto DONE
if "%CHOICE%"=="2" goto OPEN_EXISTING
if "%CHOICE%"=="1" goto NEW_SCENE

echo [ERROR] Invalid choice: %CHOICE%
goto FAIL

:OPEN_EXISTING
echo.
echo   Enter path to a .blend file or a folder containing one.
set /p "USER_PATH=Path: "

if not exist "%USER_PATH%" (
    echo [ERROR] Path not found: %USER_PATH%
    goto FAIL
)

REM -- If directory, use helper to pick .blend via temp file --
if exist "%USER_PATH%\*" (
    set "TMPFILE=%TEMP%\_specimen_pick.txt"
    cmd /c ""%~dp0_pick_blend.bat" "%USER_PATH%" "%TEMP%\_specimen_pick.txt""
    if errorlevel 1 goto FAIL
    if not exist "%TEMP%\_specimen_pick.txt" (
        echo [ERROR] No file selected.
        goto FAIL
    )
    set /p BLEND_FILE=<"%TEMP%\_specimen_pick.txt"
    del "%TEMP%\_specimen_pick.txt" 2>nul
) else (
    set "BLEND_FILE=%USER_PATH%"
)

if not exist "%BLEND_FILE%" (
    echo [ERROR] File not found: %BLEND_FILE%
    goto FAIL
)

echo [INFO] Opening: %BLEND_FILE%
start "Blender" "%BLENDER_PATH%" "%BLEND_FILE%"
goto START_CLAUDE

:NEW_SCENE
echo [INFO] Starting Blender (empty scene, mm units)...
start "Blender" "%BLENDER_PATH%" --python-expr "import bpy; [bpy.data.objects.remove(o) for o in list(bpy.data.objects)]; bpy.context.scene.unit_settings.system='METRIC'; bpy.context.scene.unit_settings.scale_length=0.001"
goto START_CLAUDE

:START_CLAUDE
echo.
echo [INFO] Waiting for Blender to start...
timeout /t 5 /nobreak >nul
echo [INFO] Starting Claude Code (specimen context)...
echo   Make sure Blender MCP addon is enabled.
echo.
cd /d "%PROJECT_ROOT%"
cmd /k claude --append-system-prompt-file scripts\specimen_context.md "Print the welcome guide and verify MCP connection."
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
