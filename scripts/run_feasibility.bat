@echo off
setlocal enableextensions

REM === M1-M4 Material Feasibility Test ===
REM Tests all 4 material methods in a single Kit session.
REM Renders 4_mid_N variant for each method.
REM Output: output/renders/v0.13/2x_/M{n}_feasibility/

set "PROJECT_ROOT=%~dp0.."
set "SCRIPT=%~dp0render_feasibility.py"
set "KIT_DIR=D:\Tools\kit-app-template\_build\windows-x86_64\release"
set "KIT_EXE=%KIT_DIR%\kit\kit.exe"
set "KIT_APP=%KIT_DIR%\apps\kohyoung.cam_sim.kit"

if not exist "%KIT_EXE%" (
    echo [ERROR] kit.exe not found: %KIT_EXE%
    pause
    exit /b 1
)

if not exist "%SCRIPT%" (
    echo [ERROR] render_feasibility.py not found: %SCRIPT%
    pause
    exit /b 1
)

REM Copy script to temp to avoid file lock issues
copy /Y "%SCRIPT%" "%TEMP%\render_feasibility.py" >nul

set "BLENDER_OV_ROOT=%PROJECT_ROOT%"

echo [INFO] Starting M1-M4 Feasibility Test...
echo [INFO] Kit: %KIT_EXE%
echo [INFO] Script: %SCRIPT%
echo [INFO] Methods: M1 (DustyMirror), M2 (OmniSurface), M3 (OmniSurfaceBlend), M4 (DustyVolume)

"%KIT_EXE%" "%KIT_APP%" ^
    --exec "%TEMP%\render_feasibility.py" ^
    --/app/content/emptyStageOnStart=true ^
    --/app/renderer/resolution/width=450 ^
    --/app/renderer/resolution/height=450 ^
    "--/persistent/exts/omni.kit.viewport.window/Viewport/Viewport0/resolutionScale=1.0" ^
    --/app/window/dpiScaleOverride=1.0 ^
    --/app/window/width=450 ^
    --/app/window/height=450

echo.
echo [INFO] Feasibility test complete.
echo [INFO] Check output directories for results:
echo          M1_feasibility/  M2_feasibility/
echo          M3_feasibility/  M4_feasibility/
echo [INFO] Summary: feasibility_summary.json
pause

endlocal
