"""Generate chrome sphere dust textures: metallic-based dust model.

Haze comes from METALLIC variation (diffuse scatter), NOT roughness (specular blur).

Physics: Dust on chrome = partial coverage.
  Clean: metallic ~1.0 → pure mirror
  Dusty: metallic low → mirror + diffuse scatter
  Roughness stays LOW → LED shapes remain sharp

Usage:
  python gen_sphere_dust_texture_v2.py [size] [out_dir] [name] [dust_strength]
  dust_strength: 1.0 = baseline, 2.0 = 2x stronger metallic reduction
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

    base_rough = 0.02
    base_metal = 0.98

    rough = np.full((size, size), base_rough, np.float32)
    metal = np.full((size, size), base_metal, np.float32)

    # Layer 1: dust particles — metallic reduction scaled by dust_strength
    dust_levels = [
        # (name,      base_metallic_range, coverage)
        ("light",    (0.75, 0.85),         0.35),
        ("medium",   (0.60, 0.75),         0.20),
        ("heavy",    (0.45, 0.60),         0.10),
        ("dense",    (0.35, 0.50),         0.05),
    ]

    for level_name, (met_lo_base, met_hi_base), coverage in dust_levels:
        # Scale metallic reduction from base_metal
        drop_lo = (base_metal - met_hi_base) * dust_strength
        drop_hi = (base_metal - met_lo_base) * dust_strength
        met_hi = max(base_metal - drop_lo, 0.02)
        met_lo = max(base_metal - drop_hi, 0.02)

        n_pixels = int(size * size * coverage)
        ys = rng.integers(0, size, n_pixels)
        xs = rng.integers(0, size, n_pixels)
        met_vals = rng.uniform(met_lo, met_hi, n_pixels).astype(np.float32)
        metal[ys, xs] = np.minimum(metal[ys, xs], met_vals)

        if met_lo < 0.50:
            rough[ys, xs] = np.maximum(rough[ys, xs],
                                       rng.uniform(0.03, 0.10, n_pixels).astype(np.float32))

    # Gaussian blur
    for arr_name in ['metal', 'rough']:
        arr = metal if arr_name == 'metal' else rough
        u8 = np.clip(arr * 255, 0, 255).astype(np.uint8)
        blurred = np.array(Image.fromarray(u8).filter(
            ImageFilter.GaussianBlur(radius=1))).astype(np.float32) / 255.0
        if arr_name == 'metal':
            metal = blurred
        else:
            rough = blurred

    # Layer 2: Perlin noise modulation
    noise = np.zeros((size, size), np.float32)
    for scale, weight in [(8, 0.5), (16, 0.3), (32, 0.2)]:
        noise += perlin_noise_2d(size, scale, rng) * weight
    noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
    noise = 0.5 + noise * 0.5

    dust_mask = metal < (base_metal - 0.02)
    metal[dust_mask] = base_metal + (metal[dust_mask] - base_metal) * noise[dust_mask]

    # Layer 3: Large visible speckles
    n_large = int(50 * dust_strength)
    for _ in range(n_large):
        r = rng.integers(2, 5)
        cx, cy = int(rng.integers(0, size)), int(rng.integers(0, size))
        p_metal = max(rng.uniform(0.30, 0.55) - (dust_strength - 1.0) * 0.20, 0.05)
        p_rough = min(rng.uniform(0.05, 0.12) * dust_strength, 0.20)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                dist = np.sqrt(dx * dx + dy * dy)
                if dist <= r:
                    fade = 1.0 - 0.3 * (dist / r)
                    py, px = (cy + dy) % size, (cx + dx) % size
                    metal[py, px] = min(metal[py, px], p_metal * fade + base_metal * (1 - fade))
                    rough[py, px] = max(rough[py, px], p_rough * fade)

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
    print(f"  → mean metallic = {m_u8.mean()/255:.3f}, diffuse fraction = {1 - m_u8.mean()/255:.3f}")
    dust_pct = (metal < 0.90).mean() * 100
    print(f"Dust coverage (met<0.90): {dust_pct:.1f}%")
    print(f"Saved: {rough_path}")
    print(f"Saved: {metal_path}")


if __name__ == "__main__":
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 4096
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "assets/scenes/LOTA_PROD_0408/v004/textures"
    name = sys.argv[3] if len(sys.argv) > 3 else "sphere_D31"
    strength = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    generate(size, out_dir, name, strength)
