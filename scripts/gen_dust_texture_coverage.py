"""Generate dust weight textures at different coverage levels.

Output: sphere_M1_dust_weight_{mult}x.png for each multiplier.
All use same weight range — only particle COUNT changes.

Usage: python gen_dust_texture_coverage.py
"""
import os
import sys
import numpy as np
from PIL import Image, ImageFilter

SIZE = 1024
BASE_FINE = 3000
BASE_MEDIUM = 300
BASE_LARGE = 30
MULTIPLIERS = [2, 3, 4]


def draw_particles(img, rng, count, r_range, w_range):
    for _ in range(count):
        cx, cy = rng.randint(0, SIZE, 2)
        r = rng.uniform(*r_range)
        w = rng.uniform(*w_range)
        ri = int(np.ceil(r))
        y0 = max(0, cy - ri)
        y1 = min(SIZE, cy + ri + 1)
        x0 = max(0, cx - ri)
        x1 = min(SIZE, cx + ri + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r ** 2
        region = img[y0:y1, x0:x1]
        region[mask] = np.maximum(region[mask], w)


def generate_one(output_path, mult, seed):
    rng = np.random.RandomState(seed)
    img = np.zeros((SIZE, SIZE), dtype=np.float32)

    img += rng.uniform(0.03, 0.06, (SIZE, SIZE)).astype(np.float32)
    draw_particles(img, rng, BASE_FINE * mult, (1.0, 2.0), (0.08, 0.18))
    draw_particles(img, rng, BASE_MEDIUM * mult, (2.0, 3.0), (0.12, 0.22))
    draw_particles(img, rng, BASE_LARGE * mult, (3.0, 5.0), (0.15, 0.28))

    img = np.clip(img, 0.0, 1.0)
    pil_img = Image.fromarray((img * 255).astype(np.uint8), mode="L")
    pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=0.7))

    pil_img.save(output_path)
    arr = np.array(pil_img)
    print(f"  {mult}x: min={arr.min()}, max={arr.max()}, mean={arr.mean():.1f}")


if __name__ == "__main__":
    tex_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..",
        "assets", "scenes", "LOTA_PROD_0408", "v004", "textures",
    )
    for mult in MULTIPLIERS:
        path = os.path.join(tex_dir, f"sphere_M1_dust_weight_{mult}x.png")
        generate_one(path, mult, seed=42 + mult)
        print(f"Saved: {path}")
