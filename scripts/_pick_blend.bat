@echo off
setlocal enabledelayedexpansion

REM Helper: find .blend files in a directory and let user pick one.
REM Writes selected path to a temp file (arg 2).
REM Usage: _pick_blend.bat "C:\path\to\folder" "C:\temp\output.txt"

set "SEARCH_DIR=%~1"
set "OUTFILE=%~2"

set "COUNT=0"
set "LAST_FILE="

for %%F in ("%SEARCH_DIR%\*.blend") do (
    set /a COUNT+=1
    set "BFILE_!COUNT!=%%F"
    set "LAST_FILE=%%~fF"
)

if "!COUNT!"=="0" (
    echo [ERROR] No .blend file found in: %SEARCH_DIR%
    exit /b 1
)

if "!COUNT!"=="1" (
    echo [INFO] Found: !LAST_FILE!
    echo !LAST_FILE!>"%OUTFILE%"
    exit /b 0
)

echo [INFO] Multiple .blend files found:
echo.
for /l %%I in (1,1,!COUNT!) do (
    for %%P in ("!BFILE_%%I!") do echo   %%I. %%~nxP
)
echo.
set /p "PICK=Select file number [1-!COUNT!]: "

set "SELECTED=!BFILE_%PICK%!"
if not defined SELECTED (
    echo [ERROR] Invalid selection: %PICK%
    exit /b 1
)

echo [INFO] Selected: !SELECTED!
echo !SELECTED!>"%OUTFILE%"
exit /b 0
