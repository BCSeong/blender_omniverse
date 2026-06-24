# Chrome Sphere Dust Texture 실험 기록

## Best Configuration: M1 (DustyMirror.mdl) — W2 + A2 + Oxide 0.0045

**USD:** `lota-16m10-v3-rev2_v004_2x.usdc`
**Texture:** `sphere_M1_dust_weight.png` (= sweep A2, 1024×1024), `sphere_M1_oxide.png` (1024×1024)

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| MDL | `DustyMirror.mdl` | custom weighted_layer + oxide absorption |
| base_color | (0.8, 0.8, 0.8) | mirror base |
| dust_roughness | 0.10 | scatter 집중도 (낮을수록 speckle 뚜렷) |
| dust_scatter_color | (1.0, 1.0, 1.0) | white scatter |
| dust_weight_constant | 0.04 | (texture influence=1.0이면 무시됨) |
| dust_weight_texture_influence | 1.0 | texture 100% |
| oxide_strength | 0.0045 | 산화층 흡수 강도 (O1~O2 중간값) |
| oxide_thickness_texture | sphere_M1_oxide.png | 산화층 두께 분포 (고주파 noise) |
| oxide_thickness_influence | 1.0 | texture 100% |

**텍스처 생성 파라미터:**
| 파라미터 | 값 |
|---------|-----|
| Fine particles | 150,000 (r=1-2 texel) |
| Fine weight range | 0.15 - 0.30 (W2) |
| Medium particles | 300 (r=2-3, w=0.12-0.22) |
| Large particles | 30 (r=3-5, w=0.15-0.28) |
| Ambient base | 0.08 - 0.12 (A2) |
| Gaussian blur | r=0.7 |
| Seed | 63 |

**DustyMirror.mdl 구조:**
```mdl
// 1. Dust scatter layer
combined = df::weighted_layer(
    weight = dust_texture,
    layer  = microfacet_ggx(roughness=dust_roughness),
    base   = microfacet_ggx(roughness=0.001)  // mirror
)
// 2. Oxide thin-film absorption (grazing-angle darkening)
tau_normal = oxide_strength * oxide_texture
transmittance = exp(-tau_normal / cos(theta))  // Beer-Lambert
final = df::tint(color(transmittance), combined)
```

**Oxide 텍스처 생성 파라미터:**
| 파라미터 | 값 |
|---------|-----|
| Noise scales | 256, 512, 1024 |
| Noise weights | 0.25, 0.40, 0.35 |
| Contrast | percentile 5-95 stretch |
| Gaussian blur | r=0.5 |
| Seed | 77 |

---

### Previous Best: D26 (OmniPBR roughness texture 방식, gamma renderer)

```python
# === 텍스처 생성 파라미터 (D26) ===
size = 512
base_rough = 0.07
base_metallic = 0.95

# Layer 1: 4-level discrete particles → Gaussian blur
levels = [
    # (name,        rough_range,    metallic,  coverage)
    ("super_low",  (0.10, 0.18),   0.855,     0.40),
    ("more_low",   (0.14, 0.24),   0.884,     0.28),
    ("low",        (0.18, 0.30),   0.912,     0.18),
    ("current",    (0.25, 0.40),   0.95,      0.12),
]
# → Gaussian blur radius=1 적용

# Layer 2: Perlin noise modulation [0.3, 1.0]
# 3 octaves: scale 8, 16, 32 (weights 0.5, 0.3, 0.2)

# Layer 3: 40 large discrete particles
# radius: 2-3 texel, roughness: 0.30-0.55, metallic: 0.70-0.85
# center-weighted fade: 1.0 - 0.3 * (dist/radius)

# 최종 stats: rough max=0.541, metal min=0.706
```

Material 설정:
- Principled BSDF, base_color = (0.4, 0.4, 0.4)
- Roughness: texture map 연결 (sphere_D25_rough.png)
- Metallic: texture map 연결 (sphere_D25_metallic.png)
- Coat: 0 (사용 안 함)

## Parameter → Phenomenon 매핑

| Parameter | 올리면 | 내리면 | 적정 범위 |
|-----------|--------|--------|-----------|
| **Roughness (texture)** | haze/scatter 강해짐, 반사 흐려짐 | 깨끗한 mirror | 0.07(base)~0.40(dust) |
| **Metallic** | 순수 specular만 (어두움) | diffuse 추가 → 밝고 부드러운 haze | 0.90~0.95 |
| **Coverage (%)** | 촘촘한 grain | 듬성듬성 | 60~100% |
| **Gaussian blur radius** | 연속적/매끄러운 grain | discrete speckle 보임 | r=1 |
| **Perlin modulation range** | 넓으면 영역차 뚜렷 (haze 약해질 수 있음) | 좁으면 차이 안 보임 | [0.3, 1.0] + roughness 보정 |
| **Large particle count** | 이물질 많아 보임 | 깨끗한 표면 | 20~40개 |
| **Large particle radius** | 눈에 띄는 dark spot | 안 보임 | 2-3 texel |

## 핵심 교훈 (실수 방지)

### 1. Clearcoat는 metallic 표면에서 무의미
- Coat Fresnel ~4% vs metal base ~60-90% → coat haze가 보이지 않음
- 해결: roughness texture로 직접 scatter 구현

### 2. 연속 noise는 보이지 않음 — discrete particle 필요
- Gaussian 연속 roughness variation (0.08~0.18)은 렌더에서 구분 불가
- 반드시 base(0.07)와 sharp하게 차이나는 discrete particle이 필요
- 이후 Gaussian blur로 부드럽게 만드는 것은 OK

### 3. Dielectric dust (metallic=0)는 반사를 파괴
- D3에서 metallic=0 dust가 카메라 반사를 완전히 없앰
- metallic 0.85~0.95 범위가 적절 (약간의 diffuse만 추가)

### 4. 큰 particle (radius 4-5)은 페인트처럼 보임
- D14에서 확인: r=4-5 texel → 15-25 pixel in render → 비현실적
- radius 1-3 texel이 적절

### 5. PIL로 텍스처 저장해야 함 (Blender image save 버그)
- `bpy.data.images.new()` + `foreach_set()` + `save()` → BLACK PNG 생성 가능
- 반드시 `PIL.Image.fromarray().save()` 사용
- 저장 후 반드시 on-disk 파일 검증 (min < max 확인)

### 6. Perlin modulation은 roughness 보정 필수
- [0.3, 1.0] 범위 적용 시 평균 roughness가 ~65%로 감소
- base roughness를 ~1.5배 올려서 보정해야 haze 수준 유지

### 7. Metallic 0.95가 최적 (base)
- 1.0: 순수 metal — grain 대비 약함, 어두움
- 0.9: diffuse 너무 많음 — wash-out, 밝아짐
- 0.95: 적절한 대비 + 약간의 diffuse haze

### 8. Coverage 계산 시 overlap 고려
- 4개 레벨 합산 coverage target 98% → 실제 ~63% (pixel overlap)
- target 대비 실제 coverage는 항상 낮음

## 실험 이력 요약

| # | 핵심 변경 | 결과 | 교훈 |
|---|----------|------|------|
| D1 | 2% discrete dust, rough 0.3-0.5 | haze 잘 보임 | discrete particle 방식 유효 |
| D3 | Dielectric dust (met=0) | 반사 파괴 | metallic 유지 필수 |
| D5 | 큰 particle (r=3-5) | 비현실적 | r=1만 사용 |
| D9 | Coverage 30%, rough 분포 | real과 비슷해짐 | 밀도+분포 중요 |
| D12 | 연속 noise floor | 전체 반사 흐려짐 | 연속 noise 방식 실패 |
| D14 | Size variation (r=1-5) | 큰 blob | r=1만 사용 확정 |
| D15-D19 | 4-level contrast, coverage 조정 | 점진적 개선 | 다중 대비 레벨 효과적 |
| D21 | Gaussian blur r=1 | 연속 grain 달성 | blur 방식 전환점 |
| D22 | Blur + roughness 보정 | haze 회복 | blur 후 peak 감소 보정 필요 |
| D22_m95 | Metallic 0.95 | 최적 대비 발견 | met=0.95 확정 |
| D25 | Perlin + 큰 particle 20개 | 좋음 | 3-layer 구조 완성 |
| **D26** | **큰 particle 40개, r=2-3** | **최종 best (gamma renderer)** | particle 수+크기 증가 → 자연스러운 이물질 |
| D27 | D26 rough stretched (floor 18→0), F0=0.8 | haze 부족, mirror는 유지 | roughness stretch로는 haze 보충 불가 |
| D28 | OmniPBR_ClearCoat + D26 base 텍스처 | coat 작동 확인, 미세 조정 불가 | coat Fresnel ~5%: 0.2→효과없음, 0.8→matte |
| D28-1 | D28 + clearcoat_roughness=0.2 | D26과 동일 | coat 효과 미미 |
| D28-2 | D28 + roughness 2x amplify | 먼지↑ mirror↓ | 전체 증폭은 mirror 파괴 |
| **D28-3** | **D28 + clearcoat_roughness=0.5** | **현재 best** | mirror 유지+dust 준수, 외곽 dark band |
| D29 | roughness stretch [18,138]→[0,255] | D28-3과 유사 | floor 제거만으로는 변화 미미 |
| D29-1 | D29 + gamma=0.5 boost | mirror 완전 상실 | gamma 0.5 과도 |
| D29-2 | D26-18 (floor만 제거), OmniPBR | scatter→shift 문제 | 512px texel이 커서 LED가 밀림 |
| D30 | D26 알고리즘 4096x4096, OmniPBR | shift 개선, haze 없음 | 해상도↑ → shift↓ 확인. roughness 방식 한계 |
| D31 | metallic 기반 dust (roughness 균일 ~0.02) | mid_N에서 약한 haze 확인 | diffuse scatter 방향 맞음, 강도 부족 |
| **D31-1** | **D31 + dust_strength=2.0** | **렌더 대기** | metallic mean 0.86→0.76, diffuse 14%→25% |

### D27 상세

**Note: D27부터 linear renderer 사용** (D26까지는 gamma renderer)

```python
# D27 = D26 기반 + roughness histogram stretch + F0 변경
# Roughness texture: sphere_D27_rough.png (D26에서 floor=18 제거, max=138 유지)
# Metallic texture: sphere_D26_metallic.png (D26과 동일)
```

Material 설정:
- Principled BSDF, base_color = (0.8, 0.8, 0.8)  ← F0 증가 (D26: 0.4)
- Roughness: sphere_D27_rough.png (stretched)
- Metallic: sphere_D26_metallic.png
- Coat: 0
- **Renderer: linear** (no gamma curve)

결과: mirror 특성은 유지되나 real 대비 haze/dust 부족. 
Single-layer 한계 확인 → D28에서 coat 모델로 전환.

### D28 시리즈: Coat 모델 + Roughness 조정 실험

**Note: 모든 D28/D29 실험은 linear renderer 사용**

**MDL 셰이더 조사 결과:**
- OmniPBR.mdl: coat 파라미터가 파라미터 목록에 없음 → coat 값 무시됨
- OmniPBR_ClearCoat.mdl: coat 작동 확인. 단 coat weight/roughness 텍스처 없음 (uniform만)
- OmniSurface.mdl: coat_weight_image, coat_roughness_image 텍스처 지원 → **Kit에서 로드 실패** (원인 불명)

**D28-3 (현재 best) 설정:**
- OmniPBR_ClearCoat.mdl, D26 base 텍스처 (roughness + metallic)
- metallic_constant=0.95, roughness_constant=0.07
- enable_clearcoat=true, clearcoat_weight=1.0, clearcoat_roughness=0.5
- clearcoat_ior=1.56

**핵심 발견:**
- Clearcoat은 metallic 표면에서 임계값 동작: roughness 0.2~0.5→효과없음, 0.8→갑자기 matte
- 원인: coat Fresnel ~5% vs metal F0 ~60-80%. 5% 산란은 80% 정반사에 묻힘
- Base roughness 증폭(D28-2, D29-1)은 mirror를 파괴
- 512px 텍스처의 texel이 너무 커서 LED가 scatter 대신 shift됨 (D29-2)

**미해결 → D30 방향:**
- 텍스처 해상도 증가 (512→2048+): texel 크기 감소로 smooth scatter 기대
- Coat IOR ≈ 1.0~1.1: dust particle IOR가 air에 가까우면 미세 산란만 발생

## Omniverse 먼지 모델링 방법론 (블로그 참고)

| # | 방법 | 적합성 | 비고 |
|---|------|--------|------|
| 1 | **OmniSurface Coat layer** | ✅ 현재 D28 접근법 | coat_roughness 0.5-0.8, IOR 1.4-1.5, noise map → coat_weight |
| 2 | Substance 3D Painter | ❌ | 수동 텍스처 베이킹, 프로그래밍 파이프라인에 부적합 |
| 3 | Material Blend (OmniGraph) | △ 대안 | 두 재질(base + dust OmniPBR) blend, noise map으로 mask |
| 4 | **Particle Instancing** | △ 향후 검토 | 실제 3D 먼지 mesh scatter, 초근접/센서 시뮬레이션에 적합, 리소스 큼 |

**Method 1 vs 4 비교:**
- Method 1 (Coat): 텍스처 기반, 가볍고 빠름, haze/scatter 표현에 적합
- Method 4 (Particle): 개별 먼지 형상, 물리적으로 가장 정확, 렌더 비용 높음
- 현재 검사 장비 해상도(~2µm/pixel)에서는 먼지 개별 형상이 보일 수 있어 Method 4도 유효

## Rim 회색 밴드 (미해결)
- Sphere rim이 회색인 이유: ceramic 배경의 texture를 반사하기 때문
- Sphere dust로는 해결 불가 → ceramic backplate texture (Task A)로 해결 예정

---

## M1 DustyMirror.mdl 실험 (2026-06-22 ~ 2026-06-24)

D26~D31의 OmniPBR roughness/metallic texture 방식이 한계에 도달하여,
custom MDL shader(DustyMirror.mdl)를 사용한 새로운 접근법으로 전환.

### 접근법: weighted_layer

`df::weighted_layer(weight, layer, base)`:
- **base**: perfect mirror (microfacet_beckmann_smith, roughness ≈ 0)
- **layer**: diffuse scatter (dust_roughness로 제어)
- **weight**: dust_weight_texture (0~1, 텍스처 기반 dust 밀도)
- IOR 1.0 (optically transparent dust) — Fresnel 없이 weight로 직접 제어

### Feasibility Test: M1 vs M2 vs M3 vs M4

| Method | 셰이더 | 먼지 메커니즘 | 결과 |
|--------|--------|-------------|------|
| **M1** | DustyMirror.mdl (custom) | weighted_layer(texture, scatter, mirror) | **✅ 선택** — 직접적 scatter 제어 |
| M2 | OmniSurface.mdl | coat_weight_image (Fresnel coat) | coat Fresnel이 metal에 묻힘 |
| M3 | OmniSurfaceBlend.mdl | 두 sub-material blend | blend 작동하나 M1이 더 직관적 |
| M4 | DustyVolume.mdl (custom) | volume scatter | 렌더 시간 과도, 가시적 효과 미미 |

### Roughness Sweep (dust_roughness)

| ID | roughness | 결과 |
|----|-----------|------|
| M1a | 0.50 | dust 거의 안 보임 (scatter가 넓게 퍼져 per-pixel 밝기 감소) |
| M1b | 0.40 | 거의 안 보임 |
| M1c | 0.30 | 미세하게 보임 |
| M1d | 0.20 | 약간 보임 |
| M1e | 0.15 | speckle 보임 — real과 가장 유사 |
| M1f | 0.10 | speckle 더 뚜렷 — **채택** |
| M1g | 0.05 | 보이지만 너무 점 형태 |

**교훈:** roughness가 높으면 scatter가 넓은 solid angle에 분산 → per-pixel 밝기 감소 → 보이지 않음.
0.10~0.15가 speckle이 집중되면서도 자연스러운 범위.

### Coverage Sweep (fine particle count)

roughness=0.10 고정, fine/medium/large 비례 증가.

| ID | Fine | Medium | Large | 결과 |
|----|------|--------|-------|------|
| Cov1x | 3K | 300 | 30 | 거의 안 보임 |
| Cov2x | 6K | 600 | 60 | 약간 |
| Cov3x | 9K | 900 | 90 | 보임 |
| **Cov4x** | **12K** | **1200** | **120** | **real에 가장 가까움** — 더 올릴 수 있음 |

### Fine-Only Sweep (medium/large 고정)

Cov4x에서 큰 입자가 비현실적 → fine만 증가, medium=300/large=30 고정.

| ID | Fine | 결과 |
|----|------|------|
| Fine6x | 18K | 약간 개선 |
| Fine8x | 24K | 더 보임 |
| Fine10x | 30K | 좋음 |
| Fine20x | 60K | 더 좋음 |
| Fine30x | 90K | 밀도 증가 |
| Fine40x | 120K | real에 가까워짐 |
| **Fine50x** | **150K** | **real speckle 밀도 근접** — 채택 |

**교훈:** real 이미지의 먼지는 대부분 미세 입자. 큰 입자(r=3-5)는 비현실적.
Fine 150K + Medium 300 + Large 30이 최적 비율.

### Weight Intensity Sweep (fine particle 밝기)

Fine50x 고정, 입자 위치 동일(seed=63), fine weight range만 변화.

| ID | Fine weight range | 4_mid_N | 2_mid |
|----|------------------|---------|-------|
| W1 | 0.08 - 0.18 | speckle 약함 | 약함 |
| **W2** | **0.15 - 0.30** | **real과 유사** | **적절** |
| W3 | 0.25 - 0.45 | 더 밝음 | 약간 과함 |
| W4 | 0.35 - 0.60 | 밝음 | 2_mid에서 bloomy |

**채택: W2** — 4_mid_N과 2_mid 양쪽에서 균형 잡힌 speckle.

### Ambient Base Sweep (전체 haze)

W2 고정, ambient base level만 변화.

| ID | Ambient range | 결과 |
|----|--------------|------|
| A1 | 0.03 - 0.06 | 현재 baseline |
| **A2** | **0.08 - 0.12** | **specular 근처 약간 haze 추가 — 채택** |
| A3 | 0.12 - 0.18 | highlight 영역 bloomy |
| A4 | 0.18 - 0.25 | 과도한 bloom |

**교훈:** ambient는 밝은 영역의 haze만 증가시킴. 어두운 영역은 입사광이 없어 weight 증가 효과 없음.
어두운 영역의 밝기 gap은 환경광/센서 noise 등 다른 요인.

### Oxide Thin-Film Absorption Sweep (rim darkening)

W2+A2 dust 고정. DustyMirror.mdl에 Beer-Lambert 산화층 흡수 추가.
공식: `transmittance = exp(-oxide_strength * oxide_tex / cos(theta))`
→ 정면(cos≈1): 거의 투명. Rim(cos→0): 흡수 급증 → dark blob.

**물리적 근거:** Chrome ball bearing의 산화층(Cr₂O₃) 또는 micro-crack에서의 rust.
- 표면 기계적 품질(조도)은 균일하지만 화학적 상태(산화)는 비균일
- 육안으로 보이지 않는 nm급 산화층이 grazing angle에서만 가시화

**Sweep 1: 강도 탐색 (broad grain)**

| ID | oxide_strength | 결과 |
|----|---------------|------|
| O1 | 0.03 | 과도하게 어두움 |
| O2 | 0.06 | 거의 검정 |
| O3 | 0.10 | 완전 검정 |
| O4 | 0.15 | 완전 검정 |

→ 10배 축소 필요 확인

**Sweep 2: 강도 재탐색 (fine grain)**

| ID | oxide_strength | 결과 |
|----|---------------|------|
| O1 | 0.003 | subtle rim darkening |
| O2 | 0.006 | moderate — real과 유사 |
| O3 | 0.010 | 약간 강함 |
| O4 | 0.020 | 과함 |

**채택: 0.0045** (O1~O2 중간값) — 4_mid_N, 2_mid 양쪽에서 real의 rim 어두움과 일치.

**Grain 크기 튜닝 이력:**
| 시행 | Noise scales | 결과 |
|------|-------------|------|
| 1차 | 8, 16, 32, 64 | 패치 너무 큼 (broad blob) |
| 2차 | 32, 64, 128, 256 | 개선, 아직 큼 |
| 3차 | 128, 256, 512 | 거의 적절 |
| **4차** | **256, 512, 1024** | **pixel-level grain — 채택** |

### M1 핵심 교훈

1. **Roughness texture 방식의 한계**: OmniPBR roughness texture는 scatter 방향을 바꿀 뿐 에너지를 추가하지 않음. High roughness = 넓은 scatter = 어두움.
2. **weighted_layer가 정답**: mirror + scatter를 weight로 혼합하면 scatter 에너지를 직접 제어 가능.
3. **IOR=1.0 필수**: dust IOR > 1이면 Fresnel이 개입하여 weight 제어가 어려워짐.
4. **Texture 검증 필수**: 생성된 텍스처가 BLACK인지 반드시 on-disk에서 min/max 확인.
5. **Montage 비교법**: 개별 폴더 대신 sweep 결과를 한 장에 합성하면 비교 효율 극대화.
6. **Oxide absorption은 극소값**: Beer-Lambert의 1/cos(θ)가 grazing에서 급증하므로 oxide_strength 0.003~0.006 수준이 적절. 0.03만 되어도 완전 검정.
7. **Grain 크기가 중요**: 산화 패턴의 noise scale이 너무 낮으면(8~64) 비현실적 broad patch. Pixel-level(256~1024)이 자연스러움.
8. **Rim darkening은 MDL runtime 계산**: cos(θ)는 매 픽셀 실시간 계산. 텍스처는 산화 두께 분포만 제공하며, 카메라 위치와 무관하게 고정.
