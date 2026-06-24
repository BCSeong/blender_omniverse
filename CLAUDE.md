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

## Routing Rules — 1-hop 직접 위임

Root는 중간 orchestrator를 거치지 않고 **leaf agent CLAUDE.md로 직접 위임**한다.
Agent tool 호출 시 해당 leaf CLAUDE.md 경로를 프롬프트에 포함하여 scope를 전달한다.

| 사용자 의도 | 위임 CLAUDE.md (leaf) |
|------------|----------------------|
| 시편/피사체 생성, import, material | `packages/blender_authoring/src/blender_authoring/specimen/CLAUDE.md` |
| 검사기 구성 (카메라, 렌즈, 조명) | `packages/blender_authoring/src/blender_authoring/machine/CLAUDE.md` |
| Blender scene export (USD, .blend) | `packages/blender_authoring/CLAUDE.md` |
| 렌즈 광학 모델 (distortion, PSF) | `packages/cam_sim/src/cam_sim/lens/CLAUDE.md` |
| 센서 모델 (noise, QE) | `packages/cam_sim/src/cam_sim/sensor/CLAUDE.md` |
| Asset 로딩, 조합, swap | `packages/cam_sim/src/cam_sim/assembly/CLAUDE.md` |
| Omniverse 렌더링, 후처리 | `packages/cam_sim/src/cam_sim/render/CLAUDE.md` |
| Omniverse 연결, Connector, USD export 설정 | `docs/omniverse_connector/CLAUDE.md` |
| Chrome sphere dust 모델 (텍스처, material, 실험) | `docs/sphere_dust/CLAUDE.md` |
| Manifest 스키마 변경 | `docs/CLAUDE.md` (양쪽 패키지 영향 → docs agent가 조율) |

## Launcher Redirect 규칙

**launchers/contexts/*.md는 bat 런처 전용이다. Root 세션에서 직접 실행하지 않는다.**

아래 작업을 Root 세션에서 요청받으면, 코드 작업 대신 해당 launcher 실행을 안내한다:

| 작업 유형 | 안내할 런처 |
|----------|-----------|
| 시편 대화형 생성 | `launchers\start_specimen.bat` |
| Height map → 시편 | `launchers\start_specimen_with_data.bat` |
| 전자부품 패키지 모델링 | `launchers\start_package_authoring.bat` |
| Placement overlay 생성 | `launchers\start_placement_overlay.bat` |

이유: launcher context(.md)는 수천 토큰의 도메인 프롬프트를 포함하며,
이를 Root에 로드하면 컨텍스트 비대화로 라우팅 성능이 저하된다.
단, 런처/context 파일 자체의 **편집·수정** 요청은 Root에서 처리 가능하다.

## Cross-Package Interface
- 교환 형식: `.blend` + `.manifest.yaml` (assets/ 디렉토리)
- `blender_authoring`이 생성 → `cam_sim.assembly`가 소비
- 스키마 정의: `docs/manifest_schema.md`

## Conventions
- Language: Python 3.10+
- Config: YAML 기반
- Test: pytest
- 한국어 주석/문서 허용, 코드는 영문
