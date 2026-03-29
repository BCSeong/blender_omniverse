# Specimen Agent (Layer 1)

## Scope
`packages/blender_authoring/src/blender_authoring/specimen/` 디렉토리만 담당.

## Responsibility
검사 대상 시편(specimen) 3D asset 생성 및 import.
다양한 사용자가 자주 사용 — MCP 자연어 인터페이스 우선.

## Public API
```python
from blender_authoring.specimen import create_specimen, import_specimen

manifest_path = create_specimen(config)       # 기본 도형 생성
manifest_path = import_specimen(file_path, material_config)  # 외부 모델 import
```

## Files
- `primitives.py`: 기본 도형 생성 (cube, sphere, cylinder, checkerboard 등)
- `importer.py`: 외부 CAD/STL/OBJ/FBX import + material 설정
- `materials.py`: PBR material 헬퍼 (diffuse, specular, emissive)
- `__init__.py`: 공용 API

## Output
- `assets/specimens/<name>/<name>.blend` + `<name>.manifest.yaml`
- .blend 내 오브젝트명: "Specimen"
- Bounding box origin: manifest에 기록

## Constraints
- machine 모듈, cam_sim 패키지 import 금지
- bpy import guard 필수
