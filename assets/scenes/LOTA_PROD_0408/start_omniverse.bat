@echo off
setlocal enableextensions

REM === Omniverse Launcher ===
REM Launches Camera Simulation Composer via kit-app-template

REM -- Resolve project root (parent of launchers/) --
set "PROJECT_ROOT=%~dp0.."
pushd "%PROJECT_ROOT%" 2>nul
if errorlevel 1 (
    echo [ERROR] Cannot resolve project root.
    pause
    exit /b 1
)

REM -- Check kit-app-template path --
set "KIT_APP_DIR=D:\Tools\kit-app-template"
if not exist "%KIT_APP_DIR%\repo.bat" (
    echo [ERROR] kit-app-template not found at %KIT_APP_DIR%
    echo         Install: git clone https://github.com/NVIDIA-Omniverse/kit-app-template.git
    pause
    exit /b 1
)

echo [INFO] Launching Camera Simulation Composer...
echo [INFO] First launch may take 5-15 min for shader compilation.
echo.

pushd "%KIT_APP_DIR%"
call repo.bat launch
popd

popd
endlocal
