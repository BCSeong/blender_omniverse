"""Generate meso-scale ceramic absorber albedo texture.

The blob visibility mechanism on the sphere rim is PERCEPTUAL:
  - Direct ceramic view: subtle albedo variation on a bright uniform surface → barely visible
  - Sphere rim reflection: same variation in a narrow bright band against dark background → prominent

Scale: 4096px = 40.96mm plate → 10 um/texel (matches render resolution 10um/px).
Features: 0.2-1.0mm (20-100 texels = 2-10 render pixels) — above mip-mapping threshold.
Contrast: ~20-30% darker (matches measured microscopy albedo ratio ~0.8).
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

SIZE = 4096
PLATE_MM = 40.96
UM_PER_TEXEL = PLATE_MM * 1000.0 / SIZE  # 10 um/texel
BASE = 0.90
COVERAGE = 0.06
SEED = 20260620

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    "assets/scenes/LOTA_PROD_0408/v004/textures/ceramic_blobs_albedo.png")


def main():
    rng = np.random.default_rng(SEED)
    alb = np.full((SIZE, SIZE), BASE, np.float32)
    # subtle base grain
    alb += rng.normal(0.0, 0.01, (SIZE, SIZE)).astype(np.float32)

    count = 0
    placed = np.zeros((SIZE, SIZE), bool)

    while placed.mean() < COVERAGE and count < 80000:
        u = rng.random()
        if u < 0.60:
            d_texels = rng.uniform(20, 50)    # 0.2-0.5mm (2-5 px)
        elif u < 0.88:
            d_texels = rng.uniform(50, 80)    # 0.5-0.8mm (5-8 px)
        else:
            d_texels = rng.uniform(80, 100)   # 0.8-1.0mm (8-10 px)

        r = d_texels / 2.0
        cx = int(rng.integers(0, SIZE))
        cy = int(rng.integers(0, SIZE))

        # darkening: 20-35% darker than base
        dark_factor = rng.uniform(0.60, 0.82)

        # slightly elliptical
        aspect = rng.uniform(0.6, 1.0)
        angle = rng.uniform(0, np.pi)

        R = int(np.ceil(r * 1.2)) + 2
        yy = np.arange(cy - R, cy + R + 1)
        xx = np.arange(cx - R, cx + R + 1)
        YY, XX = np.meshgrid(yy, xx, indexing='ij')
        DY, DX = YY - cy, XX - cx
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        DX_R = DX * cos_a + DY * sin_a
        DY_R = -DX * sin_a + DY * cos_a
        dist = np.sqrt((DX_R / r) ** 2 + (DY_R / (r * aspect)) ** 2)
        prof = np.clip((1.0 - dist) / 0.35, 0.0, 1.0)
        spot = BASE * (1.0 - (1.0 - dark_factor) * prof)

        ry = yy % SIZE
        rx = xx % SIZE
        idx = np.ix_(ry, rx)
        alb[idx] = np.minimum(alb[idx], spot)
        placed[idx] |= (prof > 0.1)
        count += 1

    np.clip(alb, 0.0, 1.0, out=alb)
    cov = float((alb < BASE * 0.95).mean())

    g = np.clip(alb * 255.0, 0, 255).astype(np.uint8)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.stack([g, g, g], -1)).save(OUT)
    print(f"texels {SIZE}x{SIZE}  plate {PLATE_MM}mm  {UM_PER_TEXEL:.1f} um/texel")
    print(f"blobs: {count}  coverage: {100*cov:.1f}%")
    print(f"albedo min/base/max: {alb.min():.3f}/{BASE}/{alb.max():.3f}")
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
