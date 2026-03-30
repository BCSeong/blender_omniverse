# Specimen Agent (Layer 1)

## Scope
`packages/blender_authoring/src/blender_authoring/specimen/` 디렉토리만 담당.

## Responsibility
검사 대상 시편(specimen) 3D asset 생성 및 import.
다양한 사용자가 자주 사용 — MCP 자연어 인터페이스 우선.

## Specimen 생성 Workflow

### 진입점
```cmd
scripts\start_specimen.bat
```
대화형 메뉴:
1. **New specimen** — 빈 scene (mm 단위)으로 Blender 실행
2. **Open existing .blend** — 기존 파일을 열어 수정

Blender 실행 후 Claude Code가 specimen context와 함께 자동 시작됨.

> 설정: `blender.env`에 Blender 경로 지정 (blender.env.example 참고)

### 새 시편 생성 (MCP Interactive)
```
1. start_specimen.bat → "New specimen" 선택
2. Blender + Claude 시작 → MCP 연결 확인
3. 자연어로 시편 생성 ("10mm 체커보드 만들어줘")
4. 만족 → "저장해줘" 요청
5. Claude가:
   a. 생성에 사용한 bpy 코드를 recipe .py로 정리
   b. save_specimen.py 호출하여 .blend + manifest 생성
6. 결과: assets/specimens/<name>/
     ├── <name>.recipe.py          ← 재현용 (source of truth)
     ├── <name>.blend              ← Blender 파일
     └── <name>.manifest.yaml      ← 메타데이터
```

### 기존 시편 수정
```
1. start_specimen.bat → "Open existing .blend" 선택 → 경로 입력
2. Blender + Claude 시작 → MCP 연결 확인
3. get_scene_info로 현재 scene 파악
4. 자연어로 수정 ("roughness를 0.5로 바꿔줘")
5. 저장 시 recipe 업데이트 + .blend + manifest 재생성
```

### 재현 (headless)
```bash
blender -b --python assets/specimens/<name>/<name>.recipe.py
```

## MCP 사용 시 규칙

### 시편 생성 중
1. **단위**: 항상 mm (Blender scene unit = METRIC, scale_length = 0.001)
2. **명명**: 최종 오브젝트명은 "Specimen" (save_specimen.py가 자동 처리)
3. **원점**: bounding box center 기본 (save_specimen.py가 자동 처리)
4. **Material**: Principled BSDF 기반 PBR material 사용

### 저장 요청 시 Claude가 할 일
1. MCP로 생성한 코드를 recipe .py로 정리
   - `scripts/recipe_template.py` 구조를 따름
   - SPECIMEN_NAME, ORIGIN, MATERIAL_DESCRIPTION 설정
   - scene 초기화 → 생성 코드 → 자동 저장 구조
2. recipe 파일을 `assets/specimens/<name>/<name>.recipe.py`에 저장
3. `save_specimen.py`의 `save_current_as_specimen()` 호출

### Recipe .py 필수 구조
```python
"""
Specimen Recipe: <name>
Description: <설명>
Unit: mm (1 Blender unit = 1 mm)
Created: <YYYY-MM-DD>
"""
import bpy, os, sys

SPECIMEN_NAME = "<name>"
ORIGIN = "center"
MATERIAL_DESCRIPTION = "<설명>"

# 1. Scene 초기화
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 0.001

# 2. 시편 생성 (bpy 코드)
...

# 3. 저장 (headless 시 자동)
if bpy.app.background:
    # save_specimen import 후 save_current_as_specimen() 호출
    ...
```

## Public API
```python
from blender_authoring.specimen import create_specimen, import_specimen

manifest_path = create_specimen(config)
manifest_path = import_specimen(file_path, material_config)
```

## Files
- `primitives.py`: 기본 도형 생성 (cube, sphere, cylinder, checkerboard 등)
- `importer.py`: 외부 CAD/STL/OBJ/FBX import + material 설정
- `materials.py`: PBR material 헬퍼 (diffuse, specular, emissive)
- `__init__.py`: 공용 API

## Scripts
- `scripts/start_specimen.bat`: Blender + Claude 런처 (repo root)
- `scripts/specimen_context.md`: Claude 시편 전용 프롬프트 (repo root)
- `packages/blender_authoring/scripts/save_specimen.py`: scene → .blend + manifest 저장
- `packages/blender_authoring/scripts/recipe_template.py`: recipe 표준 템플릿

## Output
- `assets/specimens/<name>/<name>.recipe.py` (재현용 source of truth)
- `assets/specimens/<name>/<name>.blend`
- `assets/specimens/<name>/<name>.manifest.yaml`

## Constraints
- machine 모듈, cam_sim 패키지 import 금지
- bpy import guard 필수
- 단위는 항상 mm
