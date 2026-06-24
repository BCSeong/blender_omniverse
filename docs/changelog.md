# Changelog

## [v004] - 2026-06-18 ~ 2026-06-24 — Material Tuning & DustyMirror.mdl

### Summary
모든 주요 재질(diffuser, ceramic, chrome sphere)을 실측 이미지와 비교하며 체계적으로 튜닝한 버전.
Chrome sphere는 custom MDL(DustyMirror.mdl)로 전환하여 dust scatter + oxide rim darkening을 구현.
Ceramic backplate는 Coat(Fresnel) 모델(C20)로 확정. Diffuser는 transmission OFF로 최종 조정.

### Added — Optical Diffuser (OmniSurface)
- `assets/materials/optical_diffuser.usda` — OmniSurface diffuser 재질 라이브러리
- `usd_config.json` → `diffuserMaterial` 섹션 (라이브러리 경로, 바인딩 대상 prefix)
- `add_lighting_variants.py` → `apply_diffuser_material()`, `apply_render_settings()`
- `usd_config.json` → `renderSettings`: firefly Max Ray Intensity = 25000

### Added — Chrome Sphere (DustyMirror.mdl)
- `DustyMirror.mdl` — custom MDL: `weighted_layer(dust_scatter, mirror)` + oxide absorption
- `sphere_M1_dust_weight.png` — 먼지 밀도 텍스처 (Fine 150K + W2 weight + A2 ambient)
- `sphere_M1_oxide.png` — 산화층 두께 분포 (고주파 noise, seed=77)
- `scripts/set_sphere_material.py` — M1/M2/M3/M4/D31-5B/D32 material switcher
- `scripts/gen_sweep_*.py` — parameter sweep 텍스처 생성기 (weight, ambient, oxide)
- `scripts/render_param_sweep.py` — Kit sweep renderer (generic, multi-lighting)
- `scripts/montage.py` — sweep 결과 몽타주 생성기
- `scripts/run_sweep_*.bat` — sweep 3-step launchers

### Added — Ceramic Backplate
- Coat 모델(C20): roughness=1.0, metallic=0.0, coat_weight=1.0, coat_roughness=0.3
- Phase 1 (C0-C12): roughness+metallic 탐색
- Phase 2 (C13-C20): Coat(Fresnel) 모델 도입 → C20 채택

### Changed
- Sphere material: OmniPBR roughness/metallic texture (D26) → **DustyMirror.mdl (M1)**
- Diffuser transmission: ON → **OFF** (OmniSurface transmission이 빛을 과도 차단)
- LED energy: top 600M, mid/bot/coax 500k
- Camera exposure: 0.0001

### Key Findings
- **DustyMirror.mdl**: `weighted_layer`가 roughness texture보다 우수 — scatter 에너지 직접 제어 가능
- **Oxide thin-film absorption**: Beer-Lambert `exp(-τ/cos θ)` — 정면 투명, rim에서만 dark blob 재현
  - 물리 근거: chrome 도금의 미세 산화(Cr₂O₃/rust)가 grazing에서만 가시화
  - oxide_strength 0.003~0.006이 적정 (0.03만 되어도 완전 검정)
- **Ceramic Coat 모델**: base roughness=1.0(Lambertian) + coat weight=1.0(Fresnel) →
  정면: 균일 diffuse, 측면: glossy 반사 (real ceramic 유약 구조와 일치)
- **Diffuser**: UsdPreviewSurface에 진짜 transmission 없음 → OmniSurface 필요
  하지만 OmniSurface transmission도 과도 차단 → OFF가 현 단계에서 가장 정확
- **Sweep 방법론**: texture 생성 → Kit 렌더 → montage → 비교 파이프라인 확립
- 상세: `docs/material_study.md`, `docs/sphere_dust_experiments.md`

---

## [v003] - 2026-06-17 — LOTA Probe Import & Hemisphere Verification

### Summary
LOTA 검사기 프로브를 Blender에서 USD로 export하고, Omniverse에서 조명 동작을 검증한 버전.
Metallic hemisphere(polished ball bearing)를 이용해 LED 방향성과 반사 특성을 시각적으로 확인.

### Added
- 652개 LED 조명 (top:96, mid:352, bot:192, coax:12) + azimuth 기반 네이밍
- LightingConfig variant set (all, top/mid/bot/coax_only, all_off)
- Test specimen 20개 (Hemisphere, Pillar, Pyramid, SMT Cap, SOP-4 IC × Q1–Q4)
- Center_Hemisphere (∅6mm, Chrome material) — polished ball bearing reference
- `scripts/add_lighting_variants.py` — USD post-processing (stage, camera, env light, variants)
- `docs/material_study.md` — material 속성 실험 기록

### Key Findings
- Blender USD export는 회전 방향을 올바르게 보존 (transpose 불필요)
- LED cap mesh가 빛을 차단하는 것이 mid/bot 조명 불량의 원인 → collection exclude로 해결
- Polished ball bearing: Principled BSDF (Metallic=1.0, Roughness=0.15)
- Variant별 exposure 불필요 → camera에 고정 설정 (exposure:time=0.0002s)

---

## [0.1.1] - 2026-03-29

### Added
- docs/BLENDER_MCP_SETUP.md: Blender MCP 설정 및 사용 가이드
  - 설치부터 연결까지 전체 워크플로우
  - MCP 도구 전체 목록 및 설명
  - 프로시저럴 텍스처, 조명 등 실전 코드 예시
  - 트러블슈팅 및 다른 PC 재현 가이드

## [0.1.0] - 2026-03-26

### Added
- 프로젝트 초기 구조 생성 (src/cam_sim)
- lens, sensor, scene, render 모듈 skeleton
- 각 모듈 NOTES.md (개발 이력 관리)
- pyproject.toml 패키지 설정
- configs/ 템플릿 (lens_pinhole.yaml, sensor_gmax0505.yaml)
- docs/INSTALL.md 설치 가이드
2