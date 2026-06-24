# Material Study — Blender Principled BSDF

## Polished Ball Bearing (Chrome)

| Parameter | Value |
|-----------|-------|
| Base Color | (0.9, 0.9, 0.9) |
| Metallic | 1.0 |
| Roughness | 0.15 |

## Quadrant Backplate Materials

| Quadrant | Object Name | Material | Description |
|----------|-------------|----------|-------------|
| Q1 | Q1_Aluminum | Al_Unified | Aluminum |
| Q2 | Q2_PCB_Green | Mat_PCB_Green | PCB green |
| Q3 | Q3_Gray_Scattering_Target | Mat_Gray_Scattering_Target | Gray scattering target |
| Q4 | Q4_Mirror | Mat_Mirror | Mirror |

## Specimen Material Assignment

| Object Type | Material Rule |
|-------------|--------------|
| Hemisphere, Pillar, Pyramid | Same as quadrant backplate |
| Center_Hemisphere | Chrome (polished ball bearing) |
| SMT Cap | CapBody, CapTerminal, CopperPad, Solder |
| SMT IC (SOP-4) | ICBody, ICLead, CopperPad, Solder |

## Specimen Dimensions

| Object | Dimensions | Placement |
|--------|-----------|-----------|
| Hemisphere | ∅1mm | Q1–Q4, top position |
| Pillar | ∅1mm × H2mm | Q1–Q4, left position |
| Pyramid | 2×2mm base, H1.5mm | Q1–Q4, center position |
| SMT Cap 2512 | 6.35×3.18×2.54mm (×1/3) | Q1–Q4, right position |
| SOP-4 IC | 4.9×3.9×1.5mm (×1/2) | Q1–Q4, bottom position |
| Center_Hemisphere | ∅6mm | FoV center (0,0,0) |

## Lighting & Camera

| Parameter | Value |
|-----------|-------|
| LED energy | 5,000,000 (5e6) |
| Exposure time | 0.0002s (200µs) |
| Spot size | 100° |
| Spot blend | 0.4557 |
| LED count | 652 (top:96, mid:352, bot:192, coax:12) |

## Simulation Tip — LED Light ↔ Cap 간섭 방지 (발광 구체 흡수)

**팁:** Blender의 spot light는 점광원이 아니라 **물리적 발광 구체 반경**(`shadow_soft_size`, 여기선 0.1cm)을 가진다.
이 발광 구체가 LED cap 같은 **불투명 geometry와 겹치면, cap이 그 부분의 빛을 흡수**해 광량이 줄고 방향성이 왜곡된다.

**해결:** 각 LED light를 cap 밖으로 밀어낸다 —
`offset = cap-tip 거리(법선 방향) + light 반경(shadow_soft_size)`
→ 발광 구체가 cap을 완전히 벗어나 흡수 없음. 동시에 cap은 visible(WhiteEpoxy)로 유지해 chrome sphere 반사에 활용.

**v003 차폐 문제와는 다른 메커니즘:**
| 버전 | 메커니즘 | 해결 |
|------|---------|------|
| v003 | cap **메쉬가 beam 경로를 차폐** (occlusion) | cap을 조명 collection에서 exclude |
| v004 | light **발광 구체가 cap에 묻혀 흡수** (emitter overlap) | light를 cap-tip + 반경만큼 offset |

> cap-tip 거리는 bounding box가 아니라 **vertex 투영**으로 측정한다 (각진 형상에서 bbox는 40~60% 과대평가).

---

# Optical Diffuser (v004) — Blender → Omniverse

## 핵심 결론
Optical diffuser는 **Blender export로 만들 수 없고, Omniverse에서 OmniSurface(MDL)로 작성**해야 한다.
그리고 clear glass가 아니라 **white translucent(내부 산란)** 로 모델링해야 chrome sphere에 반사되어 보인다.

## 왜 Blender export로 안 되나
- Blender USD export는 material을 **UsdPreviewSurface**로 내보낸다.
- UsdPreviewSurface에는 **진짜 specular transmission이 없다** — `opacity`만 있다.
  - `opacity=1` → 빛 100% 차단 (시편이 캄캄)
  - `opacity=0` → 완전 투명 → 거울 sphere에 안 보임
- RTX는 이 재질을 "전부 흡수" 또는 "전부 투과"로만 렌더 → diffuser 거동이 안 나옴.
- → diffuser는 **OmniSurface MDL**로 작성해야 함.

## 핵심 물리: 왜 sphere에 안 보였나 (가장 중요한 발견)
- Chrome sphere는 거울이라 **위에 있는 diffuser를 반사**한다.
  기하학상 sphere 이미지의 **반경 11.6~38% 위치에 고리(ring)** 로 비쳐야 하고,
  중앙은 aperture 구멍이라 **어두운 원반**이 된다. (즉 위치 문제 아님)
- **순수 transmission(clear)** 재질은 반사 ray가 **그냥 통과**해 위쪽 어두운 공간을 봄 → 투명하게 사라짐.
  transmissive 재질은 스스로 빛나지 않으므로, 빛을 안 받으면 거울에 비춰도 어둠.
- **보이게 만드는 메커니즘 = ambient bounce**:
  white ceramic backplate가 LED 빛을 받아 **위로 되쏘는** ambient 광원처럼 작동 →
  diffuser 아랫면을 비춤. 이 빛을 **white diffuse/subsurface 성분**이 sphere 쪽으로 되산란 → 보임.
- 이는 실제 재질과 일치: opal glass·TiO₂ 섞인 frosted acrylic은 **내부 산란 때문에 하얗다**.
  → clear glass가 아니라 **white translucent**로 모델링하는 것이 물리적으로 옳다.

## OmniSurface 최종 파라미터 (Omniverse에서 튜닝)
| Parameter | Value | 의미 |
|-----------|-------|------|
| `enable_specular_transmission` | True | 투과 켜짐 |
| `specular_transmission_weight` | 0.60 | 60% 투과 |
| `enable_diffuse_transmission` | True | **translucency(subsurface) 켜짐** |
| `subsurface_weight` | 1.0 | 강한 내부 산란 |
| `subsurface_scattering_color` | (2, 2, 2) | white scatter |
| `subsurface_scale` | 1.0 | |
| `specular_reflection_weight` | 1.0 | |
| `specular_reflection_color` | (1, 1, 1) | |
| `specular_reflection_roughness` | 1.0 | 완전 frosted |
| `thin_walled` | True | 얇은 판 |
| `enable_opacity` | False | opacity 미사용 (geometry_opacity 0.27은 무시됨) |
| mdl | `OmniSurface.mdl` / `OmniSurface` | |

**Trade-off:** sphere 가시성 ↔ 투과율은 반대 방향. white diffuse/subsurface ↑ = 더 잘 보임 + 전방 투과 ↓.
실사 이미지의 diffuser 밝기에 맞춰 `specular_transmission_weight`를 조정한다.

## Diffuser 형상 (3개)
| 객체 | 위치/방향 | 비고 |
|------|----------|------|
| `optical_diffuser` | 수평, z≈6.28cm, 88×88×1.5mm, 중앙 aperture r=1.43cm | top/imaging 경로 메인 |
| `optical_diffuser.001` (→ `optical_diffuser_001`) | 수직, coax 조명 arm | coax 경로 |
| `optical_diffuser_TEST` | sphere 위 임시 복사본 | 검증용, 추후 삭제 |

> 참고: Blender mesh의 거리/두께는 axis-aligned bounding box가 아니라 **실제 vertex 투영**으로 측정해야 정확하다 (bbox는 각진 형상에서 40~60% 과대평가).

## 재현 가능 파이프라인 (저장 + 자동 재적용)
OmniSurface 재질은 Omniverse에서 작성하므로 Blender 재export 시 사라진다.
→ 별도 라이브러리로 저장하고 post-process에서 자동 바인딩한다.

| 파일 | 역할 |
|------|------|
| `assets/materials/optical_diffuser.usda` | **저장** — OmniSurface 재질 라이브러리 (git 버전관리) |
| `usd_config.json` → `diffuserMaterial` | 라이브러리 경로 + 바인딩 대상 prefix |
| `scripts/add_lighting_variants.py` → `apply_diffuser_material()` | 재질 복사 + `optical_diffuser*` 모든 mesh에 바인딩 |

**흐름:** `Blender export → add_lighting_variants.py (재질 복사·바인딩 + lighting variants) → 최종 USD`
Blender에서 geometry를 다시 export해도 매번 OmniSurface diffuser 재질이 자동 재적용된다.

**재튜닝 시:** Omniverse에서 조정 → Flattened 저장(.usda) → 그 파일에서 `/root/Looks/<material>`을
`Sdf.CopySpec`으로 `optical_diffuser.usda`에 재추출 → 파이프라인 재실행.

## Optical Diffuser — Transmission 비활성화 (2026-06-22)

**발견:** Omniverse에서 `enable_specular_transmission` / `enable_diffuse_transmission`이 켜져 있으면
top LED 빛이 diffuser를 통과하지 못해 scene이 매우 어두워진다.
OmniSurface의 transmission 모델이 실제 optical diffuser의 산란 투과를 정확히 모사하지 못하고,
빛을 과도하게 흡수/차단하기 때문.

**조치:** 두 transmission을 모두 OFF로 설정 → `optical_diffuser.usda`에 영구 반영.
- `enable_specular_transmission = 0`
- `enable_diffuse_transmission = 0`

**결과:** Diffuser가 빛을 차단하지 않으므로 LED 광량이 정상적으로 전달.
실제 optical diffuser는 빛을 거의 100% 투과(각도만 확산)하므로, 현 단계에서는 OFF가 더 정확.
향후 custom scattering material이 필요할 수 있음.

---

## Ceramic Backplate Parameter Study (2026-06-22)

### 실험 테이블

| ID | Roughness | Metallic | Base Color | 결과 |
|----|-----------|----------|------------|------|
| C0 | 0.0 | 0.0 | 0.8 | baseline, gradient 강함, rim 반사 없음 |
| C1 | 0.15 | 0.0 | 0.8 | rim 반사 보임, gradient 여전히 강함 |
| C3 | 0.40 | 0.0 | 0.8 | rim 반사 너무 흐림, gradient 변화 없음 |
| C6 | 0.05 | 0.0 | 0.8 | rim 반사 없음 (C0과 동일) |
| C7 | 0.10 | 0.0 | 0.8 | rim 반사 약함 |
| C8 | 0.15 | 0.1 | 0.8 | 약간 어두움, gradient 비슷 |
| **C9** | **0.15** | **0.3** | **0.8** | **gradient 비율 개선 (exposure 보정 시 real과 유사)** |
| C10 | 0.05 | 0.3 | 0.8 | 거울처럼 동작, diffuser 실루엣 보임 |
| C11 | 0.10 | 0.3 | 0.8 | C9보다 specular 강함 |
| C12 | 0.60 | 0.0 | 0.8 | diffuse scattering 강화 테스트 |

### Phase 1 결론 (Roughness + Metallic 단독)
- **Roughness**: 0.15가 rim 반사의 임계점. 0.10 이하에서는 안 보임, 0.40 이상은 너무 흐림.
- **Metallic**: gradient 비율 개선에 효과 있음. 0.3에서 exposure 보정 시 real과 유사.
- **Glossy plate (C9)**: roughness=0.15, metallic=0.3 — mid_E 조명에서 가장 유사.
- **Top lighting에서 문제**: metallic=0.3일 때 LED 격자 패턴이 backplate에 보임.
- **근본 한계**: Metallic은 모든 각도에서 specular → 정면(top)에서도 LED 격자 반사.

### Phase 2: Coat (Clear Coat) 모델 도입 (2026-06-22)

**핵심 발견**: Real ceramic은 두 층 구조이다.
1. **Bulk (내부)**: Lambertian diffuse scatterer → 균일한 backplate
2. **Surface (유약/glaze)**: Fresnel 기반 glossy 코팅 → 측면에서만 반사

이는 Principled BSDF의 **Coat** 파라미터로 모델링 가능:
- Normal incidence (정면): Fresnel 반사 ~4% → 거의 투명 → diffuse만 보임
- Grazing angle (측면): Fresnel 반사 → 100% → glossy 반사 보임

#### 제약 조건 (동시 만족 필요)
| 제약 | 요구 | 방향 |
|------|------|------|
| Top 균일 | LED 격자 없음 | base roughness 높게 |
| Mid ≈ Bot 밝기 | Lambertian (각도 무관) | base roughness 높게 |
| Rim indirect highlight | Fresnel specular 필요 | coat weight 높게 |

#### Phase 2 실험 테이블

| ID | Roughness | Metallic | Coat Weight | Coat Roughness | 결과 |
|----|-----------|----------|-------------|----------------|------|
| C13 | 0.20 | 0.0 | — | — | (coat 도입 전) top LED 격자 약간 |
| C14 | 1.0 | 0.0 | 0.5 | 0.15 | top 가장자리 LED 격자, mid 너무 어두움 |
| C15 | 1.0 | 0.0 | 0.5 | 0.30 | top 깨끗, mid rim highlight 부족 |
| C16 | 0.5 | 0.0 | 0.5 | 0.30 | rim highlight 약간 보임, top에 orange 링 |
| C17 | 0.1 | 0.0 | 0.5 | 0.30 | top LED 격자 심함 (에너지 밀도 집중) |
| C18 | 0.3 | 0.0 | 0.5 | 0.30 | mid/bot 밝기 불균형 |
| C19 | 1.0 | 0.0 | 1.0 | 0.20 | mid rim highlight 보임! top 약간 반사 |
| **C20** | **1.0** | **0.0** | **1.0** | **0.30** | **✅ top 균일 + mid rim highlight + mid≈bot 밝기** |

#### Sphere 조정 (C20 ceramic 기준)

| ID | Sphere 변경 | 결과 |
|----|------------|------|
| C21 | base_color 0.7→1.0 | 너무 밝음 |
| C22 | roughness 0.07→0.0 | 차이 없음 |

### 최종 결론: C20 채택

**Ceramic (WhiteCeramic):**
| 파라미터 | 값 | 역할 |
|---------|-----|------|
| Base Color | 0.8 | 백색 세라믹 |
| Roughness | 1.0 | Lambertian diffuse (균일 산란) |
| Metallic | 0.0 | 순수 dielectric |
| Coat Weight | 1.0 | 강한 Fresnel 코팅 |
| Coat Roughness | 0.3 | 코팅 블러 (LED 격자 방지) |

**Sphere (ChromeMirrorClean) — DustyMirror.mdl (M1, 2026-06-24 확정):**

*Dust scatter (먼지 입자 산란):*
| 파라미터 | 값 | 설명 |
|---------|-----|------|
| MDL | DustyMirror.mdl | weighted_layer + oxide absorption |
| base_color | (0.8, 0.8, 0.8) | mirror base |
| dust_roughness | 0.10 | scatter 집중도 |
| dust_scatter_color | (1.0, 1.0, 1.0) | white scatter |
| dust_weight_texture | sphere_M1_dust_weight.png | W2+A2 조합 (1024×1024) |
| dust_weight_texture_influence | 1.0 | texture 100% |

*Oxide thin-film absorption (산화층 rim darkening):*
| 파라미터 | 값 | 설명 |
|---------|-----|------|
| oxide_strength | 0.0045 | 흡수 강도 (O1~O2 중간값) |
| oxide_thickness_texture | sphere_M1_oxide.png | 산화 두께 분포 (1024×1024, 고주파 noise) |
| oxide_thickness_influence | 1.0 | texture 100% |

*물리 모델:* `transmittance = exp(-oxide_strength × texture / cos(θ))` — 정면은 투명, rim에서 Beer-Lambert 흡수로 dark blob 재현.

> 이전 방식: OmniPBR + roughness/metallic texture (D26). 상세: `docs/sphere_dust_experiments.md`

**Top LED energy**: 6e6 (mid LED 5e5 대비 12:1)
**Exposure**: 0.0001

**왜 C20이 작동하는가:**
- Base roughness=1.0: 순수 Lambertian → top 균일, mid≈bot 밝기 동일
- Coat weight=1.0 + roughness=0.3: Fresnel이 grazing angle에서 LED 빛을 ceramic→sphere rim으로 전달 (indirect highlight), 동시에 normal incidence에서는 ~4% 반사만 발생하여 개별 LED spot이 blur되어 보이지 않음
