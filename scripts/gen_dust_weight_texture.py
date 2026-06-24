"""Generate dust weight texture for DustyMirror.mdl.

Output: grayscale PNG where pixel value = dust scatter weight.
  - 0 (black) = clean mirror, no scatter
  - 255 (white) = maximum scatter

The shader reads this as float [0, 1] and uses it as weighted_layer weight.
Typical range: 0.0 ~ 0.10 (0-10% scatter).
So texture values 0~25 (in 8-bit) map to 0~10% scatter in shader.

Usage:
  python gen_dust_weight_texture.py [size] [out_dir] [name] [max_weight]
  max_weight: peak dust scatter fraction (default 0.08 = 8%)
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

SEED = 20260624


def perlin_noise_2d(size, scale, rng):
    grid_sz = max(2, size // scale + 2)
    angles = rng.uniform(0, 2 * np.pi, (grid_sz, grid_sz))
    gx, gy = np.cos(angles), np.sin(angles)
    xs = np.linspace(0, grid_sz - 1, size, endpoint=False)
    ys = np.linspace(0, grid_sz - 1, size, endpoint=False)
    X, Y = np.meshgrid(xs, ys)
    x0, y0 = X.astype(int), Y.astype(int)
    dx, dy = X - x0, Y - y0

    def dot_grad(ix, iy, fx, fy):
        return gx[iy % grid_sz, ix % grid_sz] * fx + gy[iy % grid_sz, ix % grid_sz] * fy

    n00 = dot_grad(x0, y0, dx, dy)
    n10 = dot_grad(x0 + 1, y0, dx - 1, dy)
    n01 = dot_grad(x0, y0 + 1, dx, dy - 1)
    n11 = dot_grad(x0 + 1, y0 + 1, dx - 1, dy - 1)
    u = dx * dx * (3 - 2 * dx)
    v = dy * dy * (3 - 2 * dy)
    return (n00 * (1 - u) + n10 * u) * (1 - v) + (n01 * (1 - u) + n11 * u) * v


def generate(size, out_dir, name_prefix, max_weight=0.08):
    rng = np.random.default_rng(SEED)

    # Multi-scale density map (same as D31-5)
    density = np.zeros((size, size), np.float32)
    for scale, weight in [(4, 0.25), (8, 0.20), (16, 0.15),
                           (32, 0.15), (64, 0.13), (128, 0.12)]:
        density += perlin_noise_2d(size, scale, rng) * weight
    density = (density - density.min()) / (density.max() - density.min() + 1e-8)

    # Per-pixel dust probability (density-modulated)
    pixel_noise = rng.uniform(0, 1, (size, size)).astype(np.float32)
    coverage = 0.03 + 0.65 * density ** 1.3  # [0.03, 0.68]
    is_dust = pixel_noise < coverage

    # Dust weight for each dust texel: modulated by density
    dust_w = rng.uniform(0.3, 1.0, (size, size)).astype(np.float32)
    dust_w *= density ** 0.8  # higher density → higher weight

    weight_map = np.where(is_dust, dust_w * max_weight, 0.0).astype(np.float32)

    # Light blur for smooth transitions
    w_u8 = np.clip(weight_map * 255, 0, 255).astype(np.uint8)
    weight_map = np.array(Image.fromarray(w_u8).filter(
        ImageFilter.GaussianBlur(radius=1))).astype(np.float32) / 255.0

    # Save
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name_prefix}_dust_weight.png"

    w_u8 = np.clip(weight_map * 255, 0, 255).astype(np.uint8)
    Image.fromarray(w_u8).save(out_path)

    print(f"Size: {size}x{size}, max_weight: {max_weight}")
    print(f"Weight texture: min={w_u8.min()}, max={w_u8.max()}, mean={w_u8.mean():.1f}")
    print(f"  mean scatter weight = {w_u8.mean()/255:.4f} ({w_u8.mean()/255*100:.2f}%)")
    pcts = [50, 75, 90, 95, 99]
    w_pcts = np.percentile(w_u8, pcts)
    print(f"  percentiles: " +
          ", ".join(f"p{p}={int(v)}({v/255:.3f})" for p, v in zip(pcts, w_pcts)))
    clean_pct = (w_u8 == 0).mean() * 100
    dusty_pct = (w_u8 > 5).mean() * 100
    print(f"  clean(=0): {clean_pct:.1f}%, dusty(>5): {dusty_pct:.1f}%")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 4096
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "assets/scenes/LOTA_PROD_0408/v004/textures"
    name = sys.argv[3] if len(sys.argv) > 3 else "sphere_D32"
    max_w = float(sys.argv[4]) if len(sys.argv) > 4 else 0.08
    generate(size, out_dir, name, max_w)
