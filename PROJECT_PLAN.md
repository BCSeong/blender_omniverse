# Camera Image Modeling Project

> Omniverse 기반 공학적 카메라 이미지 모델링 및 데이터셋 생성

## 1. 프로젝트 목표

광학 설계 데이터(Zemax, CodeV)로부터 출발하여, 3D 시뮬레이션 환경에서 물리적으로 정확한 카메라 이미지를 생성하고, 다양한 조건(조명, 피사체 위치 등)에서의 이미지 데이터베이스를 구축한다.

```
[Lens Data] → [3D Scene] → [Omniverse Rendering] → [Image Dataset]
 Zemax/CodeV    Blender/USD    RTX + Replicator      DB
```

---

## 2. 프로젝트 사양 (확정)

| 항목 | 확정 내용 |
|------|----------|
| **타겟 광학계** | 머신비전 + 현미경. NA ~0.5, telecentric/hypercentric 렌즈 포함 |
| **정밀도 요구** | Sensor 이미지 수준. Field별 PSF/왜곡 필요 (paraxial 부족). Perspective 화각 구현 필수 |
| **센서** | GMAX0505 등 — 사용자가 모델 제공 시 파라미터 목록 정리 |
| **GPU** | NVIDIA RTX 4060 |
| **기존 자산** | Zemax + CodeV 파일 모두 보유. 시작은 pinhole model로 충분 |
| **최종 활용** | 알고리즘 개발/검증 + 실측 이미지 비교 |
| **배포 목표** | 실험 매칭 확인 후 타인 사용 가능한 파이프라인으로 배포. 현재는 unit test부터 시작 |

### 근사화 전략 (단계별 고도화)

| Level | 방법 | 구현 | 비고 |
|-------|------|------|------|
| **L1** (시작) | Pinhole + Brown-Conrady distortion | OpenCV 왜곡 모델 (k1~k6, p1,p2). Zemax field별 distortion → 계수 fitting | MVP |
| **L2** | Field-dependent PSF map | Zemax Huygens PSF를 grid (5x5 field points)로 추출 → 위치별 PSF convolution | |
| **L3** | Vignetting + relative illumination | Zemax relative illumination 데이터 → field별 밝기 보정 맵 | |
| **L4** (고도화) | Full ray-traced image simulation | Zemax→Python ray bundle trace, spot diagram 기반 이미지 합성 | |

---

## 3. 확정 방법론: 하이브리드 (방법론 E)

```
                    ┌─────────────────────────────┐
                    │   Scene Authoring (Blender)  │
                    │  - 렌즈 geometry (OptiCore)  │
                    │  - 피사체 모델링/import       │
                    │  - Material 설정             │
                    │  - 조명 배치                  │
                    └──────────┬──────────────────┘
                               │ USD Export
                               ▼
                    ┌─────────────────────────────┐
                    │  Omniverse (Isaac Sim 또는   │
                    │   Kit App에서 렌더링)         │
                    │  - OmniLensDistortion 적용   │
                    │  - Exposure/ISO 설정         │
                    │  - Replicator로 batch 생성    │
                    └──────────┬──────────────────┘
                               │
                               ▼
                    ┌─────────────────────────────┐
                    │   Post-Processing (Python)   │
                    │  - 센서 노이즈 모델 적용      │
                    │  - PSF convolution (선택)     │
                    │  - 메타데이터 기록            │
                    └──────────┬──────────────────┘
                               │
                               ▼
                    ┌─────────────────────────────┐
                    │      Image Dataset + DB      │
                    └─────────────────────────────┘
```

**선정 이유**: 각 도구의 강점만 활용
- **Blender**: scene 구성 (모델링, material, 조명, Zemax import) — 3D 모델링 최강, OptiCore로 .zmx 직접 import
- **Omniverse RTX**: 물리 기반 렌더링 + 카메라 모델 (왜곡, DoF, exposure) — Python API로 직접 제어
- **Python 후처리**: 센서 노이즈, PSF/MTF 등 Omniverse가 커버하지 못하는 광학 현상

> **참고**: 방법론 A~D를 검토한 결과 E(하이브리드)가 scene authoring 자유도(Blender)와 렌더링/카메라 모델 제어(Omniverse)를 모두 확보하는 최적 조합으로 확정. 렌더링 엔진은 어느 경로든 동일한 Omniverse RTX Renderer를 사용하므로 품질 차이 없음.

---

## 4. 3-Layer 아키텍처

### Layer 구성

| Layer | 패키지 | 역할 | 인터페이스 |
|-------|--------|------|-----------|
| **Layer 1: Object Generation** | `blender_authoring` (specimen) | 검사 대상 시편 생성/import | Blender MCP + bpy |
| **Layer 2: Machine Authoring** | `blender_authoring` (machine) | 검사기 구축 (카메라, 렌즈, 조명) | Blender MCP + bpy |
| **Layer 3: Simulation** | `cam_sim` | 광학 모델, 센서 물리, 렌더링, 후처리 | Pure Python |

### Layer 간 데이터 흐름

```
Layer 1 (시편 생성)          Layer 2 (검사기 구축)
  Blender MCP / bpy            Blender MCP / bpy
        │                            │
        ▼                            ▼
  .blend + manifest.yaml       .blend + manifest.yaml
  assets/specimens/            assets/machines/
        │                            │
        └──────────┬─────────────────┘
                   │
                   ▼
         Layer 3 (시뮬레이션)
         ┌─────────────────────────────┐
         │  assembly: manifest 로드     │
         │  → USD export (headless)     │
         │  → Omniverse RTX 렌더링     │
         │  → 후처리 (PSF, noise)       │
         │  → 최종 이미지 + 메타데이터   │
         └─────────────────────────────┘
```

### Blender MCP 사용 정책 (Hybrid)
- **자연어 MCP**: interactive 시편 생성, 프리뷰, 탐색적 작업 (Layer 1 위주)
- **Python bpy 스크립트**: 재현 가능한 검사기 구성, batch 작업 (Layer 2 위주)
- **cam_sim은 bpy 미사용**: Blender 필요 시 subprocess로 headless 호출만 허용

---

## 5. 모듈 아키텍처

### 디렉토리 구조 (모노레포, 2 패키지)

```
blender_omniverse/
├── pyproject.toml                    # workspace 선언
├── .mcp.json                         # Blender MCP 설정
│
├── packages/
│   ├── blender_authoring/            # 패키지 1: Blender 의존 (Layer 1+2)
│   │   ├── pyproject.toml
│   │   ├── src/blender_authoring/
│   │   │   ├── specimen/             # Layer 1: 시편 생성
│   │   │   │   ├── primitives.py     #   기본 도형 생성
│   │   │   │   ├── importer.py       #   CAD/STL/OBJ import
│   │   │   │   └── materials.py      #   PBR material 헬퍼
│   │   │   ├── machine/              # Layer 2: 검사기 구축
│   │   │   │   ├── lens_asset.py     #   OptiCore .zmx import
│   │   │   │   ├── camera_asset.py   #   카메라 배치
│   │   │   │   ├── lighting_asset.py #   조명 리그
│   │   │   │   └── grouping.py       #   공간 그룹 빌더
│   │   │   └── export/               # 공용 export 유틸리티
│   │   │       ├── blend_export.py
│   │   │       └── usd_export.py
│   │   ├── tests/
│   │   ├── configs/
│   │   └── scripts/                  # bpy batch 스크립트
│   │
│   └── cam_sim/                      # 패키지 2: Pure Python (Layer 3)
│       ├── pyproject.toml
│       ├── src/cam_sim/
│       │   ├── pipeline.py           # 전체 파이프라인 오케스트레이터
│       │   ├── lens/                 # 광학 모델
│       │   │   ├── pinhole.py        #   Pinhole projection
│       │   │   ├── distortion.py     #   Brown-Conrady distortion
│       │   │   └── zemax_parser.py   #   .zmx 파싱
│       │   ├── sensor/               # 센서 물리
│       │   │   ├── spec.py           #   센서 스펙
│       │   │   └── noise.py          #   노이즈 모델
│       │   ├── assembly/             # Asset 로딩 + 조합
│       │   │   ├── loader.py         #   manifest 읽기, USD export
│       │   │   └── grouping.py       #   asset swap API
│       │   └── render/               # 렌더링 + 후처리
│       │       ├── omniverse.py      #   Omniverse RTX 렌더링
│       │       └── postprocess.py    #   PSF convolution, 노이즈
│       ├── tests/
│       └── configs/
│
├── assets/                           # Layer 간 교환 저장소
│   ├── specimens/                    #   Layer 1 출력
│   ├── machines/                     #   Layer 2 출력
│   └── usd/                          #   USD export 결과
│
├── docs/                             # 프로젝트 문서
└── blender_model_example/            # 참고 모델
```

### 설계 원칙

1. **패키지 분리**: Blender 의존(`blender_authoring`)과 Pure Python(`cam_sim`)을 별도 패키지로 분리
   ```python
   # cam_sim은 blender_authoring을 import하지 않음
   from cam_sim.lens import load_lens, LensModel
   from cam_sim.assembly import load_assembly
   from cam_sim.render import render_scene
   ```

2. **Asset 기반 교환**: Layer 간 데이터 교환은 `.blend` + `.manifest.yaml` 파일
   - 스키마 정의: `docs/manifest_schema.md`

3. **Config 기반 실행**: 코드 수정 없이 YAML로 실험 조건 변경

4. **모듈 독립성**: 각 모듈의 `__init__.py`가 공용 API. 모듈 간 직접 import 금지

5. **테스트 우선**: 모듈별 unit test 분리, pinhole부터 검증 후 점진 확장

### 모듈 간 데이터 흐름

```
pipeline.py (오케스트레이터)
    │
    ├── lens.load_lens(config)                  → LensModel
    ├── sensor.load_sensor(config)              → SensorModel
    ├── assembly.load_assembly(                 → AssemblyConfig
    │       machine_manifest,
    │       specimen_manifest,
    │       pose)
    ├── render.render_scene(                    → Raw image(s)
    │       assembly.usd_export_path,
    │       render_config)
    └── render.postprocess(                     → Final image(s) + metadata
            raw_images,
            sensor_model,
            lens_model)
```

---

## 6. 도구별 라이선스 정리 (무료 한정)

| 도구 | 라이선스 | 기업 사용 가능? | 비고 |
|------|----------|----------------|------|
| **Blender** | GPL v2+ | ✅ 완전 무료 | 상용 포함 제한 없음 |
| **OptiCore** (Blender addon) | MIT | ✅ 무료 | Zemax .zmx import |
| **Omniverse Kit SDK** | NVIDIA Free SDK | ⚠️ 개발/평가만 무료 | 상용 배포 시 Enterprise 필요 |
| **Isaac Sim** | Apache 2.0 | ✅ 무료 | Kit 배포는 별도 라이선스 |
| **Omniverse Replicator** | Omniverse Kit 포함 | ⚠️ 개발/평가 무료 | Enterprise는 유료 |
| **ZOSPy** | MIT | ✅ 무료 | Zemax 라이선스 별도 필요 |
| **Python / NumPy / OpenCV** | BSD/MIT | ✅ 무료 | |

> ⚠️ **기업 사용자 주의**: Omniverse Kit SDK 기반 도구(Replicator 포함)는 **내부 개발/평가** 목적으로는 무료이나, **프로덕션 배포**에는 Enterprise 라이선스 필요. 내부 R&D 용도로 사용하는 것은 일반적으로 무료 범위에 해당.

---

## 7. 권장 시작 전략 (Incremental Approach)

### Phase 1: 기본 검증 (MVP)
- [ ] Blender 설치 + OptiCore 애드온 설치
- [ ] 간단한 Zemax .zmx 파일로 렌즈 import 테스트
- [ ] Blender 기본 카메라 + 단순 피사체 + 점광원으로 첫 렌더링
- [ ] USD export 테스트
- **목표**: 파이프라인 동작 확인

### Phase 2: Omniverse 연동
- [ ] Omniverse 설치 + Blender Connector 설정
- [ ] USD scene을 Omniverse에서 열기
- [ ] RTX 렌더러로 렌더링 비교 (Blender Cycles vs RTX)
- [ ] OmniLensDistortion 적용 테스트
- **목표**: Omniverse 렌더링 파이프라인 확립

### Phase 3: 자동화 + 데이터 생성
- [ ] Python 스크립트로 scene 파라미터 자동 변경
- [ ] Replicator API로 batch 이미지 생성
- [ ] 메타데이터(조명조건, 카메라 파라미터, 피사체 위치) 기록
- **목표**: 자동화된 이미지 데이터셋 생성

### Phase 4: 고도화
- [ ] 실제 렌즈 처방 데이터로 다중 element 모델링
- [ ] 센서 노이즈 모델 추가 (read noise, shot noise, dark current)
- [ ] 스펙트럼 조명 모델
- [ ] 실측 이미지와 비교 검증
- **목표**: 공학적 정밀도 확보

---

## 8. 핵심 참고 자료

- [NVIDIA Omniverse](https://www.nvidia.com/en-us/omniverse/)
- [Omniverse Cameras & Lens Distortion](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/cameras.html)
- [Omniverse Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html)
- [Omniverse Synthetic Data Examples (GitHub)](https://github.com/NVIDIA-Omniverse/synthetic-data-examples)
- [OptiCore - Blender Optical Elements (GitHub)](https://github.com/CodeFHD/OptiCore)
- [ZOSPy - Python Zemax API](https://zospy.readthedocs.io/)
- [Blender-Omniverse Connector](https://docs.omniverse.nvidia.com/connect/latest/blender.html)
- [Isaac Sim](https://developer.nvidia.com/isaac/sim)
- [Omniverse 라이선스 약관](https://www.nvidia.com/en-us/agreements/enterprise-software/product-specific-terms-for-omniverse/)

---

## 9. 대안 참고 (방법론 E 선정 과정에서 검토됨)

| 방법론 | 접근 | 불채택 사유 |
|--------|------|------------|
| A: Blender + Omniverse Connector | Blender에서 모든 것 구성 후 USD export | OmniLensDistortion 등 카메라 파라미터 Blender에서 설정 불가 |
| B: Isaac Sim 단독 | Isaac Sim에서 직접 scene 구성 | 3D 모델링 도구 없음, Zemax import 불가 |
| C: Kit SDK 직접 개발 | 최대 커스터마이징 | 개발 비용 최대, Enterprise 라이선스 필요 |
| D: Unreal Engine + USD | 최고 렌더링 품질 | 광학 기능 없음, C++ 중심, 로열티 |
| **Mitsuba 3** (향후 고려) | 물리 기반 스펙트럼 렌더러 | 미분 가능 렌더링, BSD 무료. Phase 4 고도화 시 PSF/MTF 정밀 시뮬레이션 후보 |
