# Camera Image Modeling Pipeline - Orchestrator

## Project Overview
Omniverse 기반 카메라 이미지 모델링 파이프라인.
Blender(scene authoring) -> USD -> Omniverse RTX(rendering) -> Python(후처리)

## Architecture
```
pipeline.py (orchestrator)
  ├── lens.load_lens(config)        -> LensModel
  ├── sensor.load_sensor(config)    -> SensorModel
  ├── scene.build_scene(...)        -> USD file path
  ├── render.render_scene(...)      -> Raw image(s)
  └── render.postprocess(...)       -> Final image(s) + metadata
```

## Module Contracts (interfaces)
각 모듈은 `__init__.py`의 공용 API만 외부에 노출한다. 모듈 간 직접 import 금지.

- **lens**: `load_lens(config) -> LensModel`, `LensModel.project(point_3d) -> point_2d`
- **sensor**: `load_sensor(config) -> SensorModel`, `SensorModel.apply_noise(image) -> image`
- **scene**: `build_scene(lens_model, sensor_model, object_config, lighting_config, output_usd_path) -> str`
- **render**: `render_scene(usd_path, render_config) -> list[image]`, `postprocess(raw_images, sensor_model, lens_model) -> list[image]`

## Approximation Levels (incremental)
| Level | Method | Status |
|-------|--------|--------|
| L1 | Pinhole + Brown-Conrady distortion | In progress |
| L2 | Field-dependent PSF map | Planned |
| L3 | Vignetting + relative illumination | Planned |
| L4 | Full ray-traced simulation | Planned |

## Agent Delegation Rules
- 모듈별 작업은 해당 모듈 디렉토리의 CLAUDE.md를 참고하여 Agent tool로 위임
- Orchestrator는 모듈 간 인터페이스 일관성과 통합만 담당
- 각 agent는 자기 모듈 scope 내에서만 파일 수정
- 모듈 인터페이스 변경 시 반드시 이 파일의 Module Contracts 섹션 업데이트

## Conventions
- Language: Python 3.12+
- Config: YAML 기반
- Test: pytest, 모듈별 tests/ 하위 디렉토리
- 한국어 주석/문서 허용, 코드는 영문