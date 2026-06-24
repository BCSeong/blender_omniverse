@echo off
setlocal enableextensions

REM === Oxide Thin-Film Absorption Sweep ===
REM Fixed dust (W2+A2 best), fixed oxide noise texture.
REM Varies oxide_strength: O1(0.03) O2(0.06) O3(0.10) O4(0.15)

set "PROJECT_ROOT=%~dp0.."
set "SCRIPTS=%~dp0"
set "KIT_DIR=D:\Tools\kit-app-template\_build\windows-x86_64\release"
set "KIT_EXE=%KIT_DIR%\kit\kit.exe"
set "KIT_APP=%KIT_DIR%\apps\kohyoung.cam_sim.kit"

if not exist "%KIT_EXE%" (
    echo [ERROR] kit.exe not found: %KIT_EXE%
    pause
    exit /b 1
)

REM --- Step 1: Generate oxide texture + sweep_config.json ---
echo [Step 1/3] Generating oxide thickness texture...
python "%SCRIPTS%gen_sweep_oxide.py"
if errorlevel 1 (
    echo [ERROR] Texture generation failed.
    pause
    exit /b 1
)

REM --- Step 2: Kit render ---
echo.
echo [Step 2/3] Rendering oxide sweep variants in Kit...
copy /Y "%SCRIPTS%render_param_sweep.py" "%TEMP%\render_param_sweep.py" >nul
set "BLENDER_OV_ROOT=%PROJECT_ROOT%"

"%KIT_EXE%" "%KIT_APP%" ^
    --exec "%TEMP%\render_param_sweep.py" ^
    --/app/content/emptyStageOnStart=true ^
    --/app/renderer/resolution/width=450 ^
    --/app/renderer/resolution/height=450 ^
    "--/persistent/exts/omni.kit.viewport.window/Viewport/Viewport0/resolutionScale=1.0" ^
    --/app/window/dpiScaleOverride=1.0 ^
    --/app/window/width=450 ^
    --/app/window/height=450

REM --- Step 3: Create montage ---
echo.
echo [Step 3/3] Creating montages...
python "%SCRIPTS%montage.py" "%SCRIPTS%sweep_config.json"

echo.
echo [DONE] Oxide sweep complete.
echo Output: output\renders\v0.13\2x_\oxide_sweep\
echo Montage: montage_4_mid_N.png, montage_2_mid.png
pause

endlocal
