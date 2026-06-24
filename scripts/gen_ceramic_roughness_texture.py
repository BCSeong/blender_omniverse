"""Generate a ceramic roughness map for grazing-angle blob visibility.

Mechanism: absorber blobs disrupt the smooth ceramic surface locally.
  - Smooth base (roughness ~0.5): sharp Fresnel at grazing → bright
  - Matte blob  (roughness ~0.9): broad Fresnel at grazing → dim
  - At normal incidence: specular is only ~4% → roughness difference invisible
  - At grazing: specular dominates → roughness contrast = high

Scale: 4096px = 40.96mm plate → 10 um/texel (UV 1:1, no tiling).
Features: 0.3-2mm (30-200 texels) → survives mip-mapping at render resolution.
Coverage: ~6%.

The roughness texture maps directly to Principled BSDF Roughness input.
White = rough (blob), Dark = smooth (base). Stored as linear grayscale.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

SIZE = 4096
PLATE_MM = 40.96
UM_PER_TEXEL = PLATE_MM * 1000.0 / SIZE  # 10 um/texel

BASE_ROUGH = 0.50      # semi-glossy ceramic (8-bit: 128)
BLOB_ROUGH = 0.90      # matte absorber defect (8-bit: 230)
COVERAGE = 0.06
SEED = 20260620

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "assets/scenes/LOTA_PROD_0408/v004/textures/ceramic_roughness.png")


def main():
    rng = np.random.default_rng(SEED)
    rough = np.full((SIZE, SIZE), BASE_ROUGH, np.float32)

    count = 0
    placed = np.zeros((SIZE, SIZE), bool)

    while placed.mean() < COVERAGE and count < 50000:
        u = rng.random()
        if u < 0.65:
            d_texels = rng.uniform(30, 80)    # 0.3-0.8mm
        elif u < 0.90:
            d_texels = rng.uniform(80, 150)   # 0.8-1.5mm
        else:
            d_texels = rng.uniform(150, 200)  # 1.5-2mm

        r = d_texels / 2.0
        cx = int(rng.integers(0, SIZE))
        cy = int(rng.integers(0, SIZE))

        # irregular shape
        aspect = rng.uniform(0.5, 1.0)
        angle = rng.uniform(0, np.pi)
        blob_rough = rng.uniform(0.80, 0.95)

        R = int(np.ceil(r * 1.2)) + 2
        yy = np.arange(cy - R, cy + R + 1)
        xx = np.arange(cx - R, cx + R + 1)
        YY, XX = np.meshgrid(yy, xx, indexing='ij')
        DY, DX = YY - cy, XX - cx
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        DX_R = DX * cos_a + DY * sin_a
        DY_R = -DX * sin_a + DY * cos_a
        dist = np.sqrt((DX_R / r) ** 2 + (DY_R / (r * aspect)) ** 2)
        prof = np.clip((1.0 - dist) / 0.3, 0.0, 1.0)
        spot = BASE_ROUGH + (blob_rough - BASE_ROUGH) * prof

        ry = yy % SIZE
        rx = xx % SIZE
        idx = np.ix_(ry, rx)
        rough[idx] = np.maximum(rough[idx], spot)
        placed[idx] |= (prof > 0.1)
        count += 1

    # add scattered small pits
    n_pits = 600
    for _ in range(n_pits):
        d = rng.uniform(15, 40)   # 150-400um
        r = d / 2.0
        cx, cy = int(rng.integers(0, SIZE)), int(rng.integers(0, SIZE))
        blob_r = rng.uniform(0.75, 0.90)
        R = int(np.ceil(r)) + 1
        yy = np.arange(cy - R, cy + R + 1)
        xx = np.arange(cx - R, cx + R + 1)
        YY, XX = np.meshgrid(yy, xx, indexing='ij')
        dist = np.sqrt((XX - cx) ** 2.0 + (YY - cy) ** 2.0)
        prof = np.clip((r - dist) / (0.4 * r + 0.5), 0.0, 1.0)
        spot = BASE_ROUGH + (blob_r - BASE_ROUGH) * prof
        ry = yy % SIZE
        rx = xx % SIZE
        idx = np.ix_(ry, rx)
        rough[idx] = np.maximum(rough[idx], spot)

    np.clip(rough, 0.0, 1.0, out=rough)
    cov = float((rough > BASE_ROUGH + 0.05).mean())

    g = np.clip(rough * 255.0, 0, 255).astype(np.uint8)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.stack([g, g, g], -1)).save(OUT)
    print(f"texels {SIZE}x{SIZE}  plate {PLATE_MM}mm  {UM_PER_TEXEL:.1f} um/texel")
    print(f"meso blobs: {count}  pits: {n_pits}  coverage: {100*cov:.1f}%")
    print(f"roughness min/base/max: {rough.min():.3f}/{BASE_ROUGH}/{rough.max():.3f}")
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
