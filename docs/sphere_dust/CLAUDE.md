# Chrome Sphere Dust Model — Specialist Agent

## Scope
Chrome sphere 먼지/haze 모델 수립. LOTA 검사 장비 시뮬레이션에서 real 이미지와 일치하는 sphere material 구현.

## 핵심 목표
**Mirror 특성을 유지하면서 dust/haze를 재현**

## Physical Correctness 기준
- **동일한 dust model로 mid_all vs mid_N 렌더 시 haze 가시성이 달라야 함**
  - mid_N (2 blocks): exposure 길음 → LED 밝음 → scatter 절대량이 noise floor 초과 → haze 보임
  - mid_all (8 blocks): exposure 짧음 → LED 어두움 → scatter 절대량이 noise floor 미만 → haze 안 보임
  - 핵심 원인: **LED 밝기 차이** (exposure time). 빛의 방향성은 부차적 요인
  - 동일한 dust에서 이 차이가 자연스럽게 재현되면 physically correct한 모델

## Key Files

| 파일 | 역할 |
|------|------|
| `docs/sphere_dust_experiments.md` | 전체 실험 이력 (D1~D29+) |
| `docs/material_study.md` | C20 ceramic + sphere 파라미터 문서 |
| `assets/scenes/LOTA_PROD_0408/v004/lota-16m10-v3-rev2_v004_2x.usdc` | 렌더 USD |
| `assets/scenes/LOTA_PROD_0408/v004/textures/` | Roughness/metallic 텍스처 |
| `scripts/render_config.json` | 렌더 설정 (SPP, resolution, exposure) |
| `scripts/render_all_variants.py` | Kit headless batch renderer |
| `output/renders/v0.13/2x_/real/450/` | Real reference 이미지 |
| `output/renders/v0.13/2x_/D28-3/` | 현재 best 시뮬레이션 결과 |

## Material Model 지식

### Omniverse MDL Shader 계층
```
OmniPBR.mdl           → OmniPBR_ClearCoat.mdl  → OmniPBRBase.mdl
(coat 파라미터 없음)      (coat 있음, texture 없음)    (실제 렌더 로직)

OmniSurface.mdl       → OmniSurfaceBase.mdl
(coat texture 지원)       (Kit에서 로드 실패 — 원인 불명)
```

### 확인된 작동 셰이더
- **OmniPBR.mdl**: base roughness/metallic 텍스처 ✅
- **OmniPBR_ClearCoat.mdl**: 위 + clearcoat (uniform only, 텍스처 불가) ✅
- **OmniSurface.mdl**: coat texture 지원하나 **Kit에서 로드 실패** ❌

### MDL 텍스처 연결 방법
```python
# OmniPBR/OmniPBR_ClearCoat base texture 연결
shader.CreateInput('reflectionroughness_texture', Sdf.ValueTypeNames.Asset).Set('./textures/xxx.png')
shader.CreateInput('reflection_roughness_texture_influence', Sdf.ValueTypeNames.Float).Set(1.0)
shader.CreateInput('metallic_texture', Sdf.ValueTypeNames.Asset).Set('./textures/xxx.png')
shader.CreateInput('metallic_texture_influence', Sdf.ValueTypeNames.Float).Set(1.0)
```

### Clearcoat 동작 특성 (metallic 표면)
- Coat Fresnel ~5% vs Metal F0 ~60-80%
- **임계값 동작**: roughness 0.2~0.5 → 효과 없음, 0.8 → 갑자기 matte
- 미세 조절 불가능 — coat은 metallic 표면에서 subtle haze 용도로 부적합

## 현재 Best: D28-3

```
Shader: OmniPBR_ClearCoat.mdl
metallic_constant: 0.95
reflection_roughness_constant: 0.07
reflectionroughness_texture: sphere_D26_rough.png (512x512)
metallic_texture: sphere_D26_metallic.png (512x512)
enable_clearcoat: true
clearcoat_weight: 1.0
clearcoat_reflection_roughness: 0.5
clearcoat_ior: 1.56
diffuse_color_constant: (0.8, 0.8, 0.8)
```

평가: mirror 준수, dust/haze 준수, 외곽 dark band (coat artifact)

## 핵심 교훈 (실수 방지)

1. **Clearcoat은 metallic에서 무의미** — Fresnel 5% vs metal 60-80%, 임계값 동작
2. **Roughness 증폭은 mirror를 파괴** — single layer에서 haze↑ = mirror↓ (반비례)
3. **512px 텍스처는 scatter 대신 shift** — texel이 render pixel보다 크면 LED가 통째로 밀림
4. **PIL로 텍스처 저장** — bpy image save는 BLACK PNG 생성 가능
5. **Metallic 0.95가 최적** — 1.0: grain 대비 약함, 0.9: diffuse 과다
6. **Perlin noise normal map 금지** — metallic에서 fake shadow 생성
7. **Large particle radius 1-3 texel** — 4-5 texel은 페인트처럼 보임
8. **Linear renderer 사용** (D27부터) — real camera에 gamma 없음

## D26 텍스처 생성 알고리즘

```python
size = 512  # → 4096으로 scale 시 particle이 8x 작아져 finer grain
base_rough = 0.07
base_metallic = 0.95

# Layer 1: 4-level discrete particles → Gaussian blur r=1
levels = [
    ("super_low",  (0.10, 0.18), 0.855, 0.40),
    ("more_low",   (0.14, 0.24), 0.884, 0.28),
    ("low",        (0.18, 0.30), 0.912, 0.18),
    ("current",    (0.25, 0.40), 0.95,  0.12),
]

# Layer 2: Perlin noise [0.3, 1.0], 3 octaves (scale 8, 16, 32)
# Layer 3: 40 large particles, r=2-3 texel, roughness 0.30-0.55
```

## 미해결 방향

1. **텍스처 해상도 증가** (512→4096): texel 크기 감소 → smooth scatter 기대
2. **Dust IOR ≈ air (1.0~1.1)**: 미세 산란만 발생, coat model 필요
3. **OmniSurface 로드 문제 해결**: coat texture 지원하는 유일한 셰이더
4. **Particle Instancing (Method 4)**: 실제 3D 먼지 mesh, 물리적 최정확

## Conventions
- 실험 이름: D{번호} 또는 D{번호}-{sub} (예: D28-3, D30)
- 텍스처 파일명: sphere_D{번호}_{type}.png
- 렌더 출력: output/renders/v0.13/2x_/D{이름}/
- 한국어 문서, 영문 코드
