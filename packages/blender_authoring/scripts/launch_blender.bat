@echo off
REM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REM  Blender 실행 (시편 생성용)
REM  - 빈 scene으로 시작
REM  - MCP addon 활성화 상태에서 시작
REM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REM Blender 경로 설정 (환경에 맞게 수정)
if not defined BLENDER_PATH (
    set BLENDER_PATH=C:\Tools\blender-4.5\blender.exe
)

REM Blender 존재 확인
if not exist "%BLENDER_PATH%" (
    echo [ERROR] Blender not found: %BLENDER_PATH%
    echo   BLENDER_PATH 환경변수를 설정하거나 이 파일의 기본값을 수정하세요.
    echo   예: set BLENDER_PATH=C:\Tools\blender-4.5\blender.exe
    pause
    exit /b 1
)

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Specimen Authoring Mode
echo  Blender: %BLENDER_PATH%
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo  1. MCP 연결 후 자연어로 시편 생성
echo  2. 완성 후 "저장" 요청 시 recipe + .blend + manifest 생성
echo.

REM Blender 실행 (기본 큐브 제거하는 초기화 스크립트 포함)
"%BLENDER_PATH%" --python-expr "import bpy; [bpy.data.objects.remove(o) for o in list(bpy.data.objects)]; bpy.context.scene.unit_settings.system='METRIC'; bpy.context.scene.unit_settings.scale_length=0.001; print('[init] Empty scene ready (unit: mm)')"
