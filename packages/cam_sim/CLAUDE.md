# Camera Simulation — Package Orchestrator (Layer 3)

## Role
Pure Python 시뮬레이션 패키지. 광학 모델, 센서 물리, 렌더링, 후처리를 담당한다.
Blender/bpy를 직접 import하지 않는다.

## Pipeline
```
pipeline.py (orchestrator)
  ├── lens.load_lens(config)            -> LensModel
  ├── sensor.load_sensor(config)        -> SensorModel
  ├── assembly.load_assembly(manifests) -> AssemblyConfig
  ├── render.render_scene(usd, config)  -> Raw image(s)
  └── render.postprocess(images, ...)   -> Final image(s) + metadata
```

## Sub-agents

| Module | CLAUDE.md 위치 | 역할 |
|--------|----------------|------|
| lens | `src/cam_sim/lens/CLAUDE.md` | 광학 모델 (pinhole, distortion, PSF) |
| sensor | `src/cam_sim/sensor/CLAUDE.md` | 센서 물리 (noise, QE, ADC) |
| assembly | `src/cam_sim/assembly/CLAUDE.md` | Asset 로딩, 조합, swap |
| render | `src/cam_sim/render/CLAUDE.md` | Omniverse 렌더링 + 후처리 |

## Module Contracts
- **lens**: `load_lens(config) -> LensModel`, `LensModel.project(point_3d) -> point_2d`
- **sensor**: `load_sensor(config) -> SensorModel`, `SensorModel.apply_noise(image) -> image`
- **assembly**: `load_assembly(machine_manifest, specimen_manifest, pose) -> AssemblyConfig`
- **render**: `render_scene(usd_path, config) -> list[image]`, `postprocess(images, sensor, lens) -> list[image]`

## Input Contract
- `assets/` 디렉토리의 `.manifest.yaml` 파일을 읽어 asset 정보 획득
- blender_authoring 패키지 코드를 직접 import하지 않음
- Blender 필요 시 subprocess로 headless 호출만 허용

## Approximation Levels
| Level | Method | Status |
|-------|--------|--------|
| L1 | Pinhole + Brown-Conrady distortion | In progress |
| L2 | Field-dependent PSF map | Planned |
| L3 | Vignetting + relative illumination | Planned |
| L4 | Full ray-traced simulation | Planned |

## Constraints
- blender_authoring 패키지 import 금지
- bpy import 금지 (subprocess만 허용)
- numpy, opencv, scipy, pyyaml 사용 가능
