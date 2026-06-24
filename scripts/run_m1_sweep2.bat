@echo off
setlocal enableextensions

REM === M1 Sweep Round 2: Lower Roughness ===
REM M1e(0.10) M1f(0.15) M1g(0.20) M1h(0.25)

set "PROJECT_ROOT=%~dp0.."
set "SWEEP_SCRIPT=%~dp0render_m1_sweep2.py"
set "KIT_DIR=D:\Tools\kit-app-template\_build\windows-x86_64\release"
set "KIT_EXE=%KIT_DIR%\kit\kit.exe"
set "KIT_APP=%KIT_DIR%\apps\kohyoung.cam_sim.kit"

if not exist "%KIT_EXE%" (
    echo [ERROR] kit.exe not found: %KIT_EXE%
    pause
    exit /b 1
)

copy /Y "%SWEEP_SCRIPT%" "%TEMP%\render_m1_sweep2.py" >nul

set "BLENDER_OV_ROOT=%PROJECT_ROOT%"

echo [INFO] M1 Sweep Round 2: roughness 0.10 / 0.15 / 0.20 / 0.25
echo [INFO] Texture: sphere_M1_dust_weight.png (particle-based)

"%KIT_EXE%" "%KIT_APP%" ^
    --exec "%TEMP%\render_m1_sweep2.py" ^
    --/app/content/emptyStageOnStart=true ^
    --/app/renderer/resolution/width=450 ^
    --/app/renderer/resolution/height=450 ^
    "--/persistent/exts/omni.kit.viewport.window/Viewport/Viewport0/resolutionScale=1.0" ^
    --/app/window/dpiScaleOverride=1.0 ^
    --/app/window/width=450 ^
    --/app/window/height=450

echo.
echo [INFO] Sweep 2 complete.
echo [INFO] Output: M1e_sweep/ M1f_sweep/ M1g_sweep/ M1h_sweep/
pause

endlocal
