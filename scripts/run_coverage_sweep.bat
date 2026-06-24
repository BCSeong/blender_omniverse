@echo off
setlocal enableextensions

REM === Coverage Sweep: particle count only, roughness=0.10 fixed ===
REM Cov1x(3K) Cov2x(6K) Cov3x(9K) Cov4x(12K)

set "PROJECT_ROOT=%~dp0.."
set "GEN_SCRIPT=%~dp0gen_dust_texture_coverage.py"
set "SWEEP_SCRIPT=%~dp0render_coverage_sweep.py"
set "KIT_DIR=D:\Tools\kit-app-template\_build\windows-x86_64\release"
set "KIT_EXE=%KIT_DIR%\kit\kit.exe"
set "KIT_APP=%KIT_DIR%\apps\kohyoung.cam_sim.kit"

if not exist "%KIT_EXE%" (
    echo [ERROR] kit.exe not found: %KIT_EXE%
    pause
    exit /b 1
)

REM --- Step 1: Generate coverage textures ---
echo [INFO] Generating 2x/3x/4x coverage textures...
python "%GEN_SCRIPT%"
if errorlevel 1 (
    echo [ERROR] Texture generation failed.
    pause
    exit /b 1
)

REM --- Step 2: Run Kit sweep ---
echo.
echo [INFO] Starting coverage sweep (roughness=0.10 fixed)
echo [INFO] Cov1x(3K) Cov2x(6K) Cov3x(9K) Cov4x(12K)

copy /Y "%SWEEP_SCRIPT%" "%TEMP%\render_coverage_sweep.py" >nul
set "BLENDER_OV_ROOT=%PROJECT_ROOT%"

"%KIT_EXE%" "%KIT_APP%" ^
    --exec "%TEMP%\render_coverage_sweep.py" ^
    --/app/content/emptyStageOnStart=true ^
    --/app/renderer/resolution/width=450 ^
    --/app/renderer/resolution/height=450 ^
    "--/persistent/exts/omni.kit.viewport.window/Viewport/Viewport0/resolutionScale=1.0" ^
    --/app/window/dpiScaleOverride=1.0 ^
    --/app/window/width=450 ^
    --/app/window/height=450

echo.
echo [INFO] Coverage sweep complete.
echo [INFO] Output: Cov1x_sweep/ Cov2x_sweep/ Cov3x_sweep/ Cov4x_sweep/
pause

endlocal
