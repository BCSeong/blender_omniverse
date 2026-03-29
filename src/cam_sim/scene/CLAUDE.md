# Scene Module Agent

## Scope
이 agent는 `src/cam_sim/scene/` 디렉토리만 담당한다.

## Responsibility
Blender를 활용한 3D scene 구성 및 USD export 자동화.

## Public API (반드시 유지)
```python
from cam_sim.scene import build_scene

usd_path = build_scene(
    lens_model,        # LensModel instance
    sensor_model,      # SensorModel instance
    object_config,     # dict: 피사체 설정
    lighting_config,   # dict: 조명 설정
    output_usd_path,   # str: 출력 USD 경로
)
```

## Files
- `camera.py`: 카메라 배치 (position, orientation, FOV from lens_model)
- `objects.py`: 피사체 생성/import (mesh, material)
- `lighting.py`: 조명 설정 (type, position, intensity, spectrum)
- `usd_export.py`: Blender scene -> USD 내보내기
- `__init__.py`: 공용 API

## Domain Knowledge
- Blender Python API (bpy) 기반
- OptiCore addon으로 .zmx 렌즈 geometry import 가능
- USD export: Blender 내장 USD exporter 또는 Omniverse Connector
- Telecentric 렌즈의 경우 orthographic projection 고려

## Constraints
- lens, sensor 모듈의 공용 API만 사용 (내부 구현 접근 금지)
- Blender 의존 코드는 bpy import guard 적용 (`if bpy available`)
- 외부 API 변경 시 루트 CLAUDE.md의 Module Contracts 업데이트 필요
