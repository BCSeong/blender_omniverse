@echo off
setlocal enableextensions

REM === M1 DustyMirror Parameter Sweep ===
REM Step 1: Generate particle-based dust texture (if needed)
REM Step 2: Run Kit sweep (4 parameter combinations)
REM Output: M1a_sweep/ M1b_sweep/ M1c_sweep/ M1d_sweep/

set "PROJECT_ROOT=%~dp0.."
set "TEX_DIR=%PROJECT_ROOT%\assets\scenes\LOTA_PROD_0408\v004\textures"
set "TEX_FILE=%TEX_DIR%\sphere_M1_dust_weight.png"
set "GEN_SCRIPT=%~dp0gen_dust_texture.py"
set "SWEEP_SCRIPT=%~dp0render_m1_sweep.py"
set "KIT_DIR=D:\Tools\kit-app-template\_build\windows-x86_64\release"
set "KIT_EXE=%KIT_DIR%\kit\kit.exe"
set "KIT_APP=%KIT_DIR%\apps\kohyoung.cam_sim.kit"

if not exist "%KIT_EXE%" (
    echo [ERROR] kit.exe not found: %KIT_EXE%
    pause
    exit /b 1
)

REM --- Step 1: Generate dust texture ---
if not exist "%TEX_FILE%" (
    echo [INFO] Generating dust weight texture...
    python "%GEN_SCRIPT%" "%TEX_FILE%"
    if errorlevel 1 (
        echo [ERROR] Texture generation failed. Check numpy/PIL installation.
        pause
        exit /b 1
    )
    echo [INFO] Texture generated: %TEX_FILE%
) else (
    echo [INFO] Dust texture exists: %TEX_FILE%
)

REM --- Step 2: Run Kit sweep ---
echo.
echo [INFO] Starting M1 parameter sweep...
echo [INFO] Variants: M1a (r=0.3) M1b (r=0.4) M1c (r=0.5) M1d (r=0.4, blend)

copy /Y "%SWEEP_SCRIPT%" "%TEMP%\render_m1_sweep.py" >nul

set "BLENDER_OV_ROOT=%PROJECT_ROOT%"

"%KIT_EXE%" "%KIT_APP%" ^
    --exec "%TEMP%\render_m1_sweep.py" ^
    --/app/content/emptyStageOnStart=true ^
    --/app/renderer/resolution/width=450 ^
    --/app/renderer/resolution/height=450 ^
    "--/persistent/exts/omni.kit.viewport.window/Viewport/Viewport0/resolutionScale=1.0" ^
    --/app/window/dpiScaleOverride=1.0 ^
    --/app/window/width=450 ^
    --/app/window/height=450

echo.
echo [INFO] M1 sweep complete.
echo [INFO] Check output: M1a_sweep/ M1b_sweep/ M1c_sweep/ M1d_sweep/
echo [INFO] Summary: m1_sweep_summary.json
pause

endlocal
