# Machine Agent (Layer 2)

## Scope
`packages/blender_authoring/src/blender_authoring/machine/` 디렉토리만 담당.

## Responsibility
검사기(inspection machine) asset 구축: 카메라, 렌즈, 조명 배치 및 그룹핑.
광학 엔지니어가 사용 — 정밀도 중요, bpy 스크립트 우선.

## Public API
```python
from blender_authoring.machine import build_machine

manifest_path = build_machine(config)  # 검사기 전체 구성
```

## Files
- `lens_asset.py`: OptiCore .zmx import, 렌즈 geometry 생성
- `camera_asset.py`: 카메라 body + sensor plane 배치
- `lighting_asset.py`: 조명 리그 (ring, coaxial, dome, HDRI)
- `grouping.py`: 공간 그룹 빌더 — 오브젝트에 role 태그 부여, 위치 관계 설정
- `__init__.py`: 공용 API

## Output
- `assets/machines/<name>/<name>.blend` + `<name>.manifest.yaml`
- manifest에 camera_params (focal_length, sensor_size, telecentric 등) 필수 포함
- group 내 각 오브젝트에 role 태그 (camera, lens, ring_light 등)

## Domain Knowledge
- 타겟: 머신비전 + 현미경, NA ~0.5, telecentric/hypercentric
- OptiCore addon으로 .zmx 렌즈 geometry import
- Telecentric 렌즈 → orthographic projection 고려

## Constraints
- specimen 모듈, cam_sim 패키지 import 금지
- bpy import guard 필수
- manifest의 camera_params는 cam_sim.assembly가 읽으므로 스키마 준수 필수
