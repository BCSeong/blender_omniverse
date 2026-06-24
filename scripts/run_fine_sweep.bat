@echo off
setlocal enableextensions

REM === Fine-Only Coverage Sweep ===
REM Fine particles only: 6x/8x/10x, medium/large stay at base (300/30)
REM Compared against Cov4x (12K+1200+120) as reference

set "PROJECT_ROOT=%~dp0.."
set "GEN_SCRIPT=%~dp0gen_dust_texture_fine.py"
set "SWEEP_SCRIPT=%~dp0render_fine_sweep.py"
set "KIT_DIR=D:\Tools\kit-app-template\_build\windows-x86_64\release"
set "KIT_EXE=%KIT_DIR%\kit\kit.exe"
set "KIT_APP=%KIT_DIR%\apps\kohyoung.cam_sim.kit"

if not exist "%KIT_EXE%" (
    echo [ERROR] kit.exe not found: %KIT_EXE%
    pause
    exit /b 1
)

REM --- Generate fine-only textures ---
echo [INFO] Generating fine-only textures (6x/8x/10x)...
python "%GEN_SCRIPT%"
if errorlevel 1 (
    echo [ERROR] Texture generation failed.
    pause
    exit /b 1
)

REM --- Run Kit sweep ---
echo.
echo [INFO] Fine coverage sweep (roughness=0.10 fixed)
echo [INFO] Cov4x(ref) Fine6x(18K) Fine8x(24K) Fine10x(30K)
echo [INFO] Medium=300 Large=30 (fixed at base)

copy /Y "%SWEEP_SCRIPT%" "%TEMP%\render_fine_sweep.py" >nul
set "BLENDER_OV_ROOT=%PROJECT_ROOT%"

"%KIT_EXE%" "%KIT_APP%" ^
    --exec "%TEMP%\render_fine_sweep.py" ^
    --/app/content/emptyStageOnStart=true ^
    --/app/renderer/resolution/width=450 ^
    --/app/renderer/resolution/height=450 ^
    "--/persistent/exts/omni.kit.viewport.window/Viewport/Viewport0/resolutionScale=1.0" ^
    --/app/window/dpiScaleOverride=1.0 ^
    --/app/window/width=450 ^
    --/app/window/height=450

echo.
echo [INFO] Fine sweep complete.
echo [INFO] Output: Cov4x_sweep/ Fine6x_sweep/ Fine8x_sweep/ Fine10x_sweep/
pause

endlocal
