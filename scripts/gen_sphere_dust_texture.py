"""Generate chrome sphere dust roughness + metallic textures.

D30: D26 algorithm at 4096x4096 resolution.
Hypothesis: 512px texels are too large (scatter -> shift). 4096px should
produce 8x finer texels, enabling smooth micro-scatter instead of
macro-displacement of LED reflections.

D26 algorithm:
  Layer 1: 4-level discrete particles with Gaussian blur r=1
  Layer 2: Perlin noise modulation [0.3, 1.0]
  Layer 3: 40 large discrete particles (r=2-3 texel)

At 4096, particle sizes stay in texel units, so they become 8x smaller
in world space -- finer grain, matching real dust scale better.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

SEED = 20260624

# Particle density levels (D26 algorithm)
LEVELS = [
    # (name,        rough_range,    metallic,  coverage)
    ("super_low",  (0.10, 0.18),   0.855,     0.40),
    ("more_low",   (0.14, 0.24),   0.884,     0.28),
    ("low",        (0.18, 0.30),   0.912,     0.18),
    ("current",    (0.25, 0.40),   0.95,      0.12),
]

BASE_ROUGH = 0.07
BASE_METALLIC = 0.95

N_LARGE_PARTICLES = 40
LARGE_R_MIN = 2
LARGE_R_MAX = 3
LARGE_ROUGH_RANGE = (0.30, 0.55)
LARGE_METALLIC_RANGE = (0.70, 0.85)

PERLIN_OCTAVES = [(8, 0.5), (16, 0.3), (32, 0.2)]
PERLIN_RANGE = (0.3, 1.0)

BLUR_RADIUS = 1


def perlin_noise_2d(size, scale, rng):
    """Simple gradient-noise approximation via interpolated random grid."""
    grid_sz = max(2, size // scale + 2)
    angles = rng.uniform(0, 2 * np.pi, (grid_sz, grid_sz))
    gx = np.cos(angles)
    gy = np.sin(angles)

    xs = np.linspace(0, grid_sz - 1, size, endpoint=False)
    ys = np.linspace(0, grid_sz - 1, size, endpoint=False)
    X, Y = np.meshgrid(xs, ys)

    x0 = X.astype(int)
    y0 = Y.astype(int)
    x1 = x0 + 1
    y1 = y0 + 1
    dx = X - x0
    dy = Y - y0

    def dot_grad(ix, iy, fx, fy):
        ix_m = ix % grid_sz
        iy_m = iy % grid_sz
        return gx[iy_m, ix_m] * fx + gy[iy_m, ix_m] * fy

    n00 = dot_grad(x0, y0, dx, dy)
    n10 = dot_grad(x1, y0, dx - 1, dy)
    n01 = dot_grad(x0, y1, dx, dy - 1)
    n11 = dot_grad(x1, y1, dx - 1, dy - 1)

    u = dx * dx * (3 - 2 * dx)
    v = dy * dy * (3 - 2 * dy)

    nx0 = n00 * (1 - u) + n10 * u
    nx1 = n01 * (1 - u) + n11 * u
    return nx0 * (1 - v) + nx1 * v


def generate_textures(size, out_dir, name_prefix):
    rng = np.random.default_rng(SEED)
    rough = np.full((size, size), BASE_ROUGH, np.float32)
    metal = np.full((size, size), BASE_METALLIC, np.float32)

    # Layer 1: 4-level discrete particles
    for level_name, (r_lo, r_hi), met_val, coverage in LEVELS:
        n_pixels = int(size * size * coverage)
        ys = rng.integers(0, size, n_pixels)
        xs = rng.integers(0, size, n_pixels)
        rvals = rng.uniform(r_lo, r_hi, n_pixels).astype(np.float32)
        rough[ys, xs] = np.maximum(rough[ys, xs], rvals)
        metal[ys, xs] = np.minimum(metal[ys, xs], met_val)

    # Gaussian blur r=1
    rough_u8 = np.clip(rough * 255, 0, 255).astype(np.uint8)
    rough_img = Image.fromarray(rough_u8)
    rough_img = rough_img.filter(ImageFilter.GaussianBlur(radius=BLUR_RADIUS))
    rough = np.array(rough_img).astype(np.float32) / 255.0

    metal_u8 = np.clip(metal * 255, 0, 255).astype(np.uint8)
    metal_img = Image.fromarray(metal_u8)
    metal_img = metal_img.filter(ImageFilter.GaussianBlur(radius=BLUR_RADIUS))
    metal = np.array(metal_img).astype(np.float32) / 255.0

    # Layer 2: Perlin noise modulation [0.3, 1.0]
    noise = np.zeros((size, size), np.float32)
    for scale, weight in PERLIN_OCTAVES:
        noise += perlin_noise_2d(size, scale, rng) * weight
    noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
    noise = PERLIN_RANGE[0] + noise * (PERLIN_RANGE[1] - PERLIN_RANGE[0])

    dust_mask = rough > BASE_ROUGH + 0.005
    rough_dust = rough.copy()
    rough_dust[dust_mask] = BASE_ROUGH + (rough[dust_mask] - BASE_ROUGH) * noise[dust_mask]

    # Layer 3: Large discrete particles
    for _ in range(N_LARGE_PARTICLES):
        r = rng.integers(LARGE_R_MIN, LARGE_R_MAX + 1)
        cx = int(rng.integers(0, size))
        cy = int(rng.integers(0, size))
        p_rough = rng.uniform(*LARGE_ROUGH_RANGE)
        p_metal = rng.uniform(*LARGE_METALLIC_RANGE)

        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                dist = np.sqrt(dx * dx + dy * dy)
                if dist <= r:
                    fade = 1.0 - 0.3 * (dist / r)
                    py = (cy + dy) % size
                    px = (cx + dx) % size
                    rough_dust[py, px] = max(rough_dust[py, px], p_rough * fade)
                    metal[py, px] = min(metal[py, px], p_metal)

    np.clip(rough_dust, 0.0, 1.0, out=rough_dust)
    np.clip(metal, 0.0, 1.0, out=metal)

    # Floor subtraction (clean area -> 0 roughness)
    floor = BASE_ROUGH
    rough_final = np.maximum(rough_dust - floor, 0.0)

    # Save
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rough_path = out_dir / f"{name_prefix}_rough.png"
    metal_path = out_dir / f"{name_prefix}_metallic.png"

    r_u8 = np.clip(rough_final * 255, 0, 255).astype(np.uint8)
    m_u8 = np.clip(metal * 255, 0, 255).astype(np.uint8)

    Image.fromarray(r_u8).save(rough_path)
    Image.fromarray(m_u8).save(metal_path)

    print(f"Size: {size}x{size}")
    print(f"Roughness: min={r_u8.min()}, max={r_u8.max()}, mean={r_u8.mean():.1f}")
    print(f"  (pre-floor: min={rough_dust.min():.3f}, max={rough_dust.max():.3f}, mean={rough_dust.mean():.3f})")
    print(f"Metallic:  min={m_u8.min()}, max={m_u8.max()}, mean={m_u8.mean():.1f}")
    print(f"Saved: {rough_path}")
    print(f"Saved: {metal_path}")


if __name__ == "__main__":
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 4096
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "assets/scenes/LOTA_PROD_0408/v004/textures"
    name = sys.argv[3] if len(sys.argv) > 3 else "sphere_D30"
    generate_textures(size, out_dir, name)
