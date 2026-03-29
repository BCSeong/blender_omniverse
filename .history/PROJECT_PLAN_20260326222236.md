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

## 4. 하위 프로젝트 구성

| # | Sub-Project | 설명 | 우선순위 |
|---|-------------|------|----------|
| SP1 | Lens Import | Zemax(.zmx)/CodeV(.seq) 렌즈 데이터 파싱 및 카메라 모델 생성 | P0 |
| SP2 | Camera/Sensor Model | 센서 특성(pixel pitch, resolution, QE 등) 모델링 | P0 |
| SP3 | Object Import | 피사체 3D 모델 import 및 material 설정 | P1 |
| SP4 | Lighting Setup | 조명 모델(종류, 위치, 스펙트럼) 구성 | P1 |
| SP5 | Scene Composition | SP1~SP4 통합, USD scene 구성 자동화 | P1 |
| SP6 | Image Acquisition | 다양한 조건 조합으로 이미지 batch 생성 | P2 |
| SP7 | Dataset Management | 메타데이터 포함 DB 구축 및 관리 | P2 |

---

## 5. 모듈 아키텍처

### 디렉토리 구조

```
blender_omniverse/
├── README.md
├── pyproject.toml              # 패키지 설정
├── src/
│   └── cam_sim/                # 메인 패키지
│       ├── __init__.py
│       ├── pipeline.py         # 전체 파이프라인 오케스트레이터
│       │
│       ├── lens/               # SP1: 렌즈 데이터 모듈
│       │   ├── __init__.py     # 공용 API (load_lens, LensModel)
│       │   ├── pinhole.py      # Level 1: pinhole model
│       │   ├── distortion.py   # Level 2: Brown-Conrady distortion
│       │   └── zemax_parser.py # .zmx 파싱
│       │
│       ├── sensor/             # SP2: 센서 모듈
│       │   ├── __init__.py     # 공용 API (SensorModel)
│       │   ├── spec.py         # 센서 스펙 정의
│       │   └── noise.py        # 노이즈 모델
│       │
│       ├── scene/              # SP3+SP4+SP5: 씬 구성
│       │   ├── __init__.py     # 공용 API (build_scene)
│       │   ├── objects.py      # 피사체 생성/import
│       │   ├── lighting.py     # 조명 설정
│       │   ├── camera.py       # 카메라 배치
│       │   └── usd_export.py   # USD 내보내기
│       │
│       └── render/             # SP6: 렌더링 + 후처리
│           ├── __init__.py     # 공용 API (render_scene)
│           ├── omniverse.py    # Omniverse RTX 렌더링
│           └── postprocess.py  # PSF convolution, 노이즈 적용
│
├── tests/                      # Unit tests (모듈별 분리)
│   ├── test_lens/
│   ├── test_sensor/
│   ├── test_scene/
│   └── test_render/
│
├── configs/                    # 설정 파일 (YAML)
│   ├── lens_pinhole.yaml
│   └── sensor_gmax0505.yaml
│
└── docs/                       # 모듈별 이력/설계 문서
    ├── lens.md
    ├── sensor.md
    └── changelog.md
```

### 설계 원칙

1. **모듈 독립성**: 각 모듈의 `__init__.py`가 공용 API 역할. 다른 모듈은 이것만 import
   ```python
   from cam_sim.lens import load_lens, LensModel
   from cam_sim.scene import build_scene
   from cam_sim.render import render_scene
   ```

2. **Config 기반 실행**: 코드 수정 없이 YAML로 실험 조건 변경
   ```python
   pipeline.run("configs/experiment_01.yaml")
   ```

3. **독립 업데이트**: lens 모듈 업데이트 시 scene/render에 영향 없음 (인터페이스만 유지)

4. **이력 관리**: 각 모듈의 `docs/*.md`에 변경 이력 기록

5. **테스트 우선**: 모듈별 unit test 분리, pinhole부터 검증 후 점진 확장

### 모듈 간 데이터 흐름

```
pipeline.py (오케스트레이터)
    │
    ├── lens.load_lens(config)        → LensModel
    ├── sensor.load_sensor(config)    → SensorModel
    ├── scene.build_scene(            → USD file path
    │       lens_model,
    │       sensor_model,
    │       object_config,
    │       lighting_config)
    ├── render.render_scene(          → Raw image(s)
    │       usd_path,
    │       render_config)
    └── render.postprocess(           → Final image(s) + metadata
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
