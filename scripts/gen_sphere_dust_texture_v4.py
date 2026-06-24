"""Chrome sphere dust: roughness-based specular scatter.

D31-5: Return to roughness approach with density-modulated subpixel texels.

Key insight: specular scatter is inherently DIRECTIONAL.
  - Where LED light arrives → scatter visible (haze)
  - Where no light → no scatter → stays dark (transparent dust)
  - No diffuse component needed → metallic stays 0.95 everywhere

Previous roughness attempts failed because:
  D26-D29 (512px): texels too large → macro displacement
  D30 (4096px): too few high-roughness texels → insufficient scatter

Fix: density-modulated roughness at 4096px.
  - Clean zones: 95% texels at r=0.015 → mirror
  - Dusty zones: 50-70% texels at r=0.3-0.5 → broadened specular lobe
  - Multiple subpixel texels average within each render pixel
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


def generate(size, out_dir, name_prefix, dust_strength=1.0):
    rng = np.random.default_rng(SEED)

    base_rough = 0.015
    base_metal = 0.95
    dust_rough_range = (0.25, 0.50)  # specular lobe broadening

    # === Step 1: Multi-scale density map ===
    density = np.zeros((size, size), np.float32)
    for scale, weight in [(4, 0.25), (8, 0.20), (16, 0.15),
                           (32, 0.15), (64, 0.13), (128, 0.12)]:
        density += perlin_noise_2d(size, scale, rng) * weight
    density = (density - density.min()) / (density.max() - density.min() + 1e-8)

    # === Step 2: Per-pixel roughness based on density ===
    pixel_noise = rng.uniform(0, 1, (size, size)).astype(np.float32)

    # Coverage curve: density → probability of high-roughness texel
    coverage = 0.03 + 0.65 * density ** 1.3  # [0.03, 0.68]
    coverage *= dust_strength
    np.clip(coverage, 0, 0.85, out=coverage)

    is_dust = pixel_noise < coverage

    # Roughness for dust texels: drawn from dust_rough_range
    dust_r = rng.uniform(dust_rough_range[0], dust_rough_range[1],
                         (size, size)).astype(np.float32)

    rough = np.where(is_dust, dust_r, base_rough)

    # Metallic: uniform 0.95 (NO diffuse component)
    metal = np.full((size, size), base_metal, np.float32)

    # === Step 3: Blur to smooth subpixel transitions ===
    # Light blur (r=1) so subpixel mixing happens via path tracing, not texture blur
    r_u8 = np.clip(rough * 255, 0, 255).astype(np.uint8)
    rough = np.array(Image.fromarray(r_u8).filter(
        ImageFilter.GaussianBlur(radius=1))).astype(np.float32) / 255.0

    np.clip(rough, 0.0, 1.0, out=rough)

    # Save
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rough_path = out_dir / f"{name_prefix}_rough.png"
    metal_path = out_dir / f"{name_prefix}_metallic.png"

    r_u8 = np.clip(rough * 255, 0, 255).astype(np.uint8)
    m_u8 = np.clip(metal * 255, 0, 255).astype(np.uint8)
    Image.fromarray(r_u8).save(rough_path)
    Image.fromarray(m_u8).save(metal_path)

    print(f"Size: {size}x{size}, dust_strength: {dust_strength}")
    print(f"Roughness: min={r_u8.min()}, max={r_u8.max()}, mean={r_u8.mean():.1f}")
    print(f"  mean roughness = {r_u8.mean()/255:.3f}")
    pcts = [5, 10, 25, 50, 75, 90, 95]
    r_pcts = np.percentile(r_u8, pcts)
    print(f"  roughness percentiles: " +
          ", ".join(f"p{p}={int(v)}({v/255:.3f})" for p, v in zip(pcts, r_pcts)))
    clean_pct = (rough < 0.03).mean() * 100
    dusty_pct = (rough > 0.10).mean() * 100
    print(f"  clean(<0.03): {clean_pct:.1f}%, dusty(>0.10): {dusty_pct:.1f}%")
    print(f"Metallic: uniform {base_metal}")
    print(f"Saved: {rough_path}")
    print(f"Saved: {metal_path}")


if __name__ == "__main__":
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 4096
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "assets/scenes/LOTA_PROD_0408/v004/textures"
    name = sys.argv[3] if len(sys.argv) > 3 else "sphere_D31-5"
    strength = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    generate(size, out_dir, name, strength)
