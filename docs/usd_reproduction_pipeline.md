# USD Reproduction Pipeline

Blender `.blend` 소스 파일에서 렌더링 가능한 USD를 재현하는 3단계 파이프라인.

## 왜 필요한가

USD 파일은 Blender export + 여러 후처리 단계를 거쳐 완성된다.
`.blend` 파일만 버전 관리하고, USD는 파이프라인으로 재현함으로써:
- `.blend` 가 single source of truth
- USD 변경 이력 추적 불필요 (바이너리 diff 무의미)
- 후처리 설정이 코드로 문서화됨

## 파이프라인 개요

```
.blend ──[Step 1]──> raw .usdc ──[Step 2]──> .usdc + lighting/render ──[Step 3]──> .usdc + material
```

| Step | Script | 입력 | 출력 |
|------|--------|------|------|
| 1. USD Export | `scripts/export_usd.py` | `.blend` | `.usdc` (raw geometry + Blender materials) |
| 2. Lighting & Render | `scripts/add_lighting_variants.py` | `.usdc` + `usd_config.json` | `.usdc` + lighting variants, render settings, diffuser material |
| 3. Sphere Material | `scripts/set_sphere_material.py M1` | `.usdc` | `.usdc` + DustyMirror.mdl (dust + oxide) |

## Step 1: Blender Headless USD Export

```batch
"D:\Tools\blender-4.5.8-windows-x64\blender.exe" -b ^
  assets/scenes/LOTA_PROD_0408/v005/lota-16m10-v3-rev2_v005.blend ^
  --python scripts/export_usd.py -- ^
  assets/scenes/LOTA_PROD_0408/v005/lota-16m10-v3-rev2_v005.usdc
```

주요 설정:
- `export_textures=False` — Blender가 불필요한 텍스처를 복사하지 않음
- `relative_paths=True` — 텍스처 경로가 USD 기준 상대경로
- 소요 시간: ~3초

> **Note**: Blender export 후 `textures/` 에 `color_121212.hdr`, `sphere_D26_*.png` 등이
> 자동 생성될 수 있다. Step 3 이후 USD가 참조하지 않는 파일은 삭제해도 무방.

### 텍스처 관리

Blender export는 텍스처를 복사하지 않음. 프로덕션 텍스처는 별도 생성:
- `sphere_M1_dust_weight.png` — `scripts/gen_sweep_weight.py` (dust particle map)
- `sphere_M1_oxide.png` — `scripts/gen_sweep_oxide.py` (oxide thickness map)

이 텍스처들은 `textures/` 폴더에 미리 배치되어야 함.

## Step 2: Lighting Variants + Render Settings

```batch
python scripts/add_lighting_variants.py ^
  assets/scenes/LOTA_PROD_0408/v005/lota-16m10-v3-rev2_v005.usdc ^
  assets/scenes/LOTA_PROD_0408/v005/usd_config.json
```

적용 내용 (`usd_config.json` 설정 기반):

1. **Camera exposure**: fStop=8.0, responsivity=1.0, time=0.0003
2. **환경광 제거**: `/root/env_light`, `/Environment/defaultLight`
3. **Diffuser material 적용**: OmniSurface (optical_diffuser.usda)
4. **Render settings**:
   - PathTracing, maxBounces=63, spp=3
   - `tonemap:op=1` (Linear Off — Clamp이 아닌 선형 톤맵)
   - `fireflyFilter:enabled=false` (per-sample intensity clamping 비활성)
5. **LED 속성 패치** (Blender export 후 Omniverse 설정으로 교정):
   - `cone:angle=90°` (Blender 기본 25° → 90°로 확대)
   - `cone:softness=0.0`
   - IES 프로파일 적용 (`led_profile.ies`)
   - Top LED intensity: 1,909,859 (mid/bot/coax: Blender 기본값 159,155)
6. **9개 Lighting variant** (VariantSet `LightingConfig`):
   `1_top`, `2_mid`, `3_bot`, `4_mid_N/S/W/E`, `8_all_on`, `9_all_off`
   - 기본 variant: `6_mid_W`

설정 파일: `v005/usd_config.json`

## Step 3: Sphere Material (DustyMirror.mdl)

```batch
python scripts/set_sphere_material.py M1
```

적용 내용:
- Blender의 `Principled_BSDF` shader → `DustyMirror.mdl`로 교체
- Dust scatter: weight texture + roughness=0.10
- Oxide thin-film absorption: strength=0.0045, thickness texture

DustyMirror.mdl은 `v005/DustyMirror.mdl`에 위치.

## 전체 실행 (one-liner)

```batch
@rem Step 1: Blender export
"D:\Tools\blender-4.5.8-windows-x64\blender.exe" -b ^
  assets/scenes/LOTA_PROD_0408/v005/lota-16m10-v3-rev2_v005.blend ^
  --python scripts/export_usd.py -- ^
  assets/scenes/LOTA_PROD_0408/v005/lota-16m10-v3-rev2_v005.usdc

@rem Step 2: Lighting + render settings
python scripts/add_lighting_variants.py ^
  assets/scenes/LOTA_PROD_0408/v005/lota-16m10-v3-rev2_v005.usdc ^
  assets/scenes/LOTA_PROD_0408/v005/usd_config.json

@rem Step 3: Sphere material
python scripts/set_sphere_material.py M1
```

## v005 파일 구조

```
v005/
├── lota-16m10-v3-rev2_v005.blend   (source of truth)
├── lota-16m10-v3-rev2_v005.usdc    (pipeline output)
├── DustyMirror.mdl                  (custom MDL shader)
├── usd_config.json                  (pipeline config)
├── led_profile.ies                  (IES light profile)
└── textures/
    ├── sphere_M1_dust_weight.png    (dust particle distribution)
    └── sphere_M1_oxide.png          (oxide thickness variation)
```

## 검증 결과 (v005 vs v004_2x)

| 항목 | v004_2x (reference) | v005 pipeline |
|------|---------------------|---------------|
| Meshes | 781 | 781 |
| Lights | 652 | 652 |
| Camera hAperture | 1.125 (실험용) | 5.12 (GMAX0505) |
| exposure:time | 0.0003 | 0.0003 |
| exposure:fStop | 8.0 | 8.0 |
| exposure:responsivity | 1.0 | 1.0 |
| tonemap:op | 1 (Linear Off) | 1 (Linear Off) |
| fireflyFilter:enabled | false | false |
| rendermode | PathTracing | PathTracing |
| cone:angle | 90° | 90° |
| IES profile | led_profile.ies | led_profile.ies |
| Top LED intensity | 1,909,859 | 1,909,859 |
| Sphere material | DustyMirror.mdl | DustyMirror.mdl |
| oxide_strength | 0.0045 | 0.0045 |

> Camera hAperture 차이: v004_2x의 1.125는 실험적 값.
> Pipeline은 GMAX0505 물리 사양(5.12mm)을 기본값으로 사용.
> render_config.json에서 `camera_horizontal_aperture`로 override 가능.
