# Changelog

## [v004] - 2026-06-18 — Optical Diffuser Material (OmniSurface) — WIP

### Summary
Optical diffuser를 물리적으로 그럴듯하게 만들고, chrome sphere 표면에 반사되어 보이도록 한 버전.
핵심: diffuser는 Blender export(UsdPreviewSurface)로는 불가능 → Omniverse OmniSurface(MDL)로 작성,
clear glass가 아니라 **white translucent**로 모델링해야 sphere에 보인다. (v005 미진입)

### Added
- `assets/materials/optical_diffuser.usda` — OmniSurface diffuser 재질 라이브러리 (Omniverse 튜닝본 추출, 재사용 가능)
- `usd_config.json` → `diffuserMaterial` 섹션 (라이브러리 경로, 바인딩 대상 prefix)
- `add_lighting_variants.py` → `apply_diffuser_material()`: 재질 복사 + 모든 `optical_diffuser*` mesh 바인딩
- `add_lighting_variants.py` → `apply_render_settings()`: RTX render settings를 root layer `customLayerData`에 기록 (Blender export엔 없는 설정을 재현 가능하게)
- `usd_config.json` → `renderSettings` 섹션: **firefly Max Ray Intensity = 25000** (×3) — 기본값 3200은 간접광을 과도하게 clamp
- LED cap에 WhiteEpoxy material, PCB에 CoatedGreenPCB (Coat layer = solder mask 광택)
- `optical_diffuser_TEST` — sphere 위 임시 검증용 복사본 (aperture 절반 축소)

### Changed (validated lighting recipe)
- LED energy 배합 (Blender): **top 600M, mid/bot/coax 500k** (top은 diffuser 손실 보상으로 mid 대비 매우 높음)
- Camera `exposure:time`: 0.0002 → **0.002**

### Key Findings
- UsdPreviewSurface에는 실제 transmission이 없음 (`opacity`만) → 투과성 재질은 OmniSurface 필요
- Chrome sphere의 diffuser 반사가 안 보인 원인: transmissive 재질은 반사 ray가 통과 → radiance 없음
- 가시성 메커니즘: white ceramic backplate의 **ambient bounce**가 diffuser를 비춤 →
  white diffuse/subsurface 성분이 이를 sphere로 되산란 → 보임
- Diffuser는 내부 산란으로 하얗게 보이는 재질 → clear가 아닌 **white translucent**로 모델링 (물리적으로 정확)
- 재질을 Omniverse에서 작성 시 Blender 재export로 사라짐 → 라이브러리 + post-process 바인딩으로 재현성 확보
- **LED light ↔ cap 간섭 방지 (시뮬레이션 팁):** spot light는 물리적 발광 구체 반경(`shadow_soft_size`)을 가짐.
  구체가 cap에 묻히면 cap이 빛을 흡수 → light를 `cap-tip 거리 + light 반경`만큼 cap 밖으로 offset.
  (v003의 cap 메쉬 beam 차폐 = collection exclude와는 다른 메커니즘)
- 상세: `docs/material_study.md` 참조

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
