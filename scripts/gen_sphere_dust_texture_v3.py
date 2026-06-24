"""Chrome sphere dust texture: subpixel dust with density variation.

D31-4: All dust is 1-texel (subpixel in render). No visible individual
particles. Haze pattern comes from LOCAL DENSITY variation of subpixel
dust, controlled by multi-scale Perlin noise.

Real observation: dust particles are subpixel — they manifest as smooth
haze, not visible blobs. Spatial variation comes from density, not size.
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

    base_metal = 0.98
    base_rough = 0.015

    # === Step 1: Multi-scale density map ===
    # Controls local probability of dust at each texel
    # Small scales (64-128) = fine patches, large scales (4-8) = regional zones
    density = np.zeros((size, size), np.float32)
    scales_weights = [
        (4,   0.25),   # very large regional zones
        (8,   0.20),   # medium zones
        (16,  0.15),   # neighborhood variation
        (32,  0.15),   # fine patches
        (64,  0.13),   # micro patches
        (128, 0.12),   # grain-level variation
    ]
    for scale, weight in scales_weights:
        density += perlin_noise_2d(size, scale, rng) * weight

    density = (density - density.min()) / (density.max() - density.min() + 1e-8)
    # density ∈ [0, 1]: 0 = clean zone, 1 = dusty zone

    # === Step 2: Convert density to per-pixel metallic ===
    # In dusty zones (density→1): low metallic, more diffuse scatter
    # In clean zones (density→0): high metallic, pure mirror
    #
    # Add per-pixel randomness so it's not perfectly smooth
    pixel_noise = rng.uniform(0, 1, (size, size)).astype(np.float32)

    # local_coverage: probability that this pixel has dust
    # Combine density map with random threshold
    # density=1.0 → ~80% of pixels get dust
    # density=0.5 → ~30% of pixels get dust
    # density=0.0 → ~5% of pixels get dust
    coverage_curve = 0.05 + 0.75 * density ** 1.5  # [0.05, 0.80]
    coverage_curve *= dust_strength
    np.clip(coverage_curve, 0, 0.95, out=coverage_curve)

    is_dust = pixel_noise < coverage_curve

    # Metallic values for dust pixels: also modulated by density
    # Dense areas: metallic 0.35-0.65 (strong scatter)
    # Sparse areas: metallic 0.70-0.88 (light scatter)
    met_low = 0.35 + (1.0 - density) * 0.35    # [0.35, 0.70]
    met_high = 0.65 + (1.0 - density) * 0.23   # [0.65, 0.88]
    dust_met = rng.uniform(0, 1, (size, size)).astype(np.float32)
    dust_met = met_low + dust_met * (met_high - met_low)

    metal = np.where(is_dust, dust_met, base_metal)

    # Roughness: barely elevated at dust pixels
    rough = np.full((size, size), base_rough, np.float32)
    dust_rough = rng.uniform(0.02, 0.06, (size, size)).astype(np.float32)
    rough = np.where(is_dust, np.maximum(rough, dust_rough), rough)

    # === Step 3: Gaussian blur to blend subpixel particles ===
    # r=2 blur: each render pixel (~2x2 texels) sees a smooth average
    m_u8 = np.clip(metal * 255, 0, 255).astype(np.uint8)
    metal = np.array(Image.fromarray(m_u8).filter(
        ImageFilter.GaussianBlur(radius=2))).astype(np.float32) / 255.0

    r_u8 = np.clip(rough * 255, 0, 255).astype(np.uint8)
    rough = np.array(Image.fromarray(r_u8).filter(
        ImageFilter.GaussianBlur(radius=2))).astype(np.float32) / 255.0

    np.clip(metal, 0.0, 1.0, out=metal)
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
    print(f"Metallic:  min={m_u8.min()}, max={m_u8.max()}, mean={m_u8.mean():.1f}")
    print(f"  mean metallic = {m_u8.mean()/255:.3f}, diffuse = {1 - m_u8.mean()/255:.3f}")
    pcts = [5, 10, 25, 50, 75, 90, 95]
    met_pcts = np.percentile(m_u8, pcts)
    print(f"  metallic percentiles: " +
          ", ".join(f"p{p}={int(v)}" for p, v in zip(pcts, met_pcts)))
    clean_pct = (metal > 0.93).mean() * 100
    dusty_pct = (metal < 0.70).mean() * 100
    print(f"  clean(>0.93): {clean_pct:.1f}%, dusty(<0.70): {dusty_pct:.1f}%")
    print(f"Saved: {rough_path}")
    print(f"Saved: {metal_path}")


if __name__ == "__main__":
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 4096
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "assets/scenes/LOTA_PROD_0408/v004/textures"
    name = sys.argv[3] if len(sys.argv) > 3 else "sphere_D31-4"
    strength = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    generate(size, out_dir, name, strength)
