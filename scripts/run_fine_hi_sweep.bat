@echo off
setlocal enableextensions

REM === High Coverage Fine Sweep + Multi-Variant ===
REM Phase 1: 20x/30x/40x/50x fine with 4_mid_N
REM Phase 2: 50x with 1_top/2_mid/3_bot

set "PROJECT_ROOT=%~dp0.."
set "GEN_SCRIPT=%~dp0gen_dust_texture_fine_hi.py"
set "SWEEP_SCRIPT=%~dp0render_fine_hi_sweep.py"
set "KIT_DIR=D:\Tools\kit-app-template\_build\windows-x86_64\release"
set "KIT_EXE=%KIT_DIR%\kit\kit.exe"
set "KIT_APP=%KIT_DIR%\apps\kohyoung.cam_sim.kit"

if not exist "%KIT_EXE%" (
    echo [ERROR] kit.exe not found: %KIT_EXE%
    pause
    exit /b 1
)

REM --- Generate textures ---
echo [INFO] Generating fine textures (20x/30x/40x/50x)...
python "%GEN_SCRIPT%"
if errorlevel 1 (
    echo [ERROR] Texture generation failed.
    pause
    exit /b 1
)

REM --- Run Kit sweep ---
echo.
echo [INFO] Phase 1: coverage 20x/30x/40x/50x (4_mid_N)
echo [INFO] Phase 2: 50x lighting variants (1_top/2_mid/3_bot)

copy /Y "%SWEEP_SCRIPT%" "%TEMP%\render_fine_hi_sweep.py" >nul
set "BLENDER_OV_ROOT=%PROJECT_ROOT%"

"%KIT_EXE%" "%KIT_APP%" ^
    --exec "%TEMP%\render_fine_hi_sweep.py" ^
    --/app/content/emptyStageOnStart=true ^
    --/app/renderer/resolution/width=450 ^
    --/app/renderer/resolution/height=450 ^
    "--/persistent/exts/omni.kit.viewport.window/Viewport/Viewport0/resolutionScale=1.0" ^
    --/app/window/dpiScaleOverride=1.0 ^
    --/app/window/width=450 ^
    --/app/window/height=450

echo.
echo [INFO] Sweep complete.
echo [INFO] Coverage: Fine20x_sweep/ Fine30x_sweep/ Fine40x_sweep/ Fine50x_sweep/
echo [INFO] 50x variants: Fine50x_sweep/1_top.png 2_mid.png 3_bot.png 4_mid_N.png
pause

endlocal
