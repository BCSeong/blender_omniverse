"""Generate particle-based dust weight texture for M1 (DustyMirror.mdl).

Output: 1024x1024 grayscale PNG. Pixel value / 255 = dust scatter weight.
  0 = clean mirror, higher = more dust scatter.

Usage: python gen_dust_texture.py [output_path]
"""
import os
import sys
import numpy as np
from PIL import Image, ImageFilter

SIZE = 1024
SEED = 42


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


def generate(output_path):
    rng = np.random.RandomState(SEED)
    img = np.zeros((SIZE, SIZE), dtype=np.float32)

    # Layer 1: ambient dust noise (subtle base everywhere)
    img += rng.uniform(0.03, 0.06, (SIZE, SIZE)).astype(np.float32)

    # Layer 2: fine particles (1-2 px radius, many)
    draw_particles(img, rng, 3000, (1.0, 2.0), (0.08, 0.18))

    # Layer 3: medium particles (2-3 px radius)
    draw_particles(img, rng, 300, (2.0, 3.0), (0.12, 0.22))

    # Layer 4: large clumps (3-5 px radius, few)
    draw_particles(img, rng, 30, (3.0, 5.0), (0.15, 0.28))

    img = np.clip(img, 0.0, 1.0)
    print(f"Pre-blur: min={img.min():.4f}, max={img.max():.4f}, mean={img.mean():.4f}")

    pil_img = Image.fromarray((img * 255).astype(np.uint8), mode="L")
    pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=0.7))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pil_img.save(output_path)
    arr = np.array(pil_img)
    print(f"Saved: {output_path}")
    print(f"  Size: {SIZE}x{SIZE}")
    print(f"  Post-blur: min={arr.min()}, max={arr.max()}, mean={arr.mean():.1f}")


if __name__ == "__main__":
    default = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..",
        "assets", "scenes", "LOTA_PROD_0408", "v004", "textures",
        "sphere_M1_dust_weight.png",
    )
    output = sys.argv[1] if len(sys.argv) > 1 else default
    generate(output)
