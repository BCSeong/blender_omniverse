# Camera Image Modeling Pipeline — Root Orchestrator

## Role: Router Only
이 CLAUDE.md는 **라우터** 역할만 한다. 직접 모듈 코드를 수정하지 않는다.
사용자 의도를 파악하여 해당 패키지 orchestrator에게 Agent tool로 위임한다.

## Architecture: 3-Layer
```
Layer 1: Object Generation (시편 생성)     → packages/blender_authoring/specimen/
Layer 2: Machine Authoring (검사기 구축)    → packages/blender_authoring/machine/
Layer 3: Simulation (시뮬레이션 실행)       → packages/cam_sim/
```

## Routing Rules

| 사용자 의도 | 위임 대상 |
|------------|----------|
| 시편/피사체 생성, import, material | `packages/blender_authoring/` → specimen agent |
| 검사기 구성 (카메라, 렌즈, 조명) | `packages/blender_authoring/` → machine agent |
| Blender scene export (USD, .blend) | `packages/blender_authoring/` → export |
| 렌즈 광학 모델 (distortion, PSF) | `packages/cam_sim/` → lens agent |
| 센서 모델 (noise, QE) | `packages/cam_sim/` → sensor agent |
| Asset 로딩, 조합, swap | `packages/cam_sim/` → assembly agent |
| Omniverse 렌더링, 후처리 | `packages/cam_sim/` → render agent |
| **Manifest 스키마 변경** | **Root가 직접 조율** (양쪽 패키지 영향) |

## Cross-Package Interface
- 교환 형식: `.blend` + `.manifest.yaml` (assets/ 디렉토리)
- `blender_authoring`이 생성 → `cam_sim.assembly`가 소비
- 스키마 정의: `docs/manifest_schema.md`

## Conventions
- Language: Python 3.10+
- Config: YAML 기반
- Test: pytest
- 한국어 주석/문서 허용, 코드는 영문
