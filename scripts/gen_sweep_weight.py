"""Generate dust textures for weight intensity sweep.

Fine=150K, Medium=300, Large=30 (same as Fine50x).
Same seed=63 for all variants so particle positions are identical;
only the fine particle weight range varies.

Also writes sweep_config.json for render_param_sweep.py and montage.py.
"""
import json
import os
import numpy as np
from PIL import Image, ImageFilter

SIZE = 1024
FINE_COUNT = 150000
MEDIUM_COUNT = 300
LARGE_COUNT = 30
SEED = 63
AMBIENT_RANGE = (0.03, 0.06)
MEDIUM_W_RANGE = (0.12, 0.22)
LARGE_W_RANGE = (0.15, 0.28)

CONFIGS = [
    ("W1", (0.08, 0.18), "W1: w=0.08-0.18"),
    ("W2", (0.15, 0.30), "W2: w=0.15-0.30"),
    ("W3", (0.25, 0.45), "W3: w=0.25-0.45"),
    ("W4", (0.35, 0.60), "W4: w=0.35-0.60"),
]


def draw_particles(img, rng, count, r_range, w_range):
    for _ in range(count):
        cx, cy = rng.randint(0, SIZE, 2)
        r = rng.uniform(*r_range)
        w = rng.uniform(*w_range)
        ri = int(np.ceil(r))
        y0, y1 = max(0, cy - ri), min(SIZE, cy + ri + 1)
        x0, x1 = max(0, cx - ri), min(SIZE, cx + ri + 1)
        if y0 >= y1 or x0 >= x1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r ** 2
        region = img[y0:y1, x0:x1]
        region[mask] = np.maximum(region[mask], w)


def generate_one(output_path, fine_w_range):
    rng = np.random.RandomState(SEED)
    img = np.zeros((SIZE, SIZE), dtype=np.float32)
    img += rng.uniform(*AMBIENT_RANGE, (SIZE, SIZE)).astype(np.float32)
    draw_particles(img, rng, FINE_COUNT, (1.0, 2.0), fine_w_range)
    draw_particles(img, rng, MEDIUM_COUNT, (2.0, 3.0), MEDIUM_W_RANGE)
    draw_particles(img, rng, LARGE_COUNT, (3.0, 5.0), LARGE_W_RANGE)

    img = np.clip(img, 0.0, 1.0)
    pil = Image.fromarray((img * 255).astype(np.uint8), mode="L")
    pil = pil.filter(ImageFilter.GaussianBlur(radius=0.7))
    pil.save(output_path)

    arr = np.array(pil)
    print(f"  {os.path.basename(output_path)}: min={arr.min()}, max={arr.max()}, "
          f"mean={arr.mean():.1f}")


if __name__ == "__main__":
    tex_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..",
        "assets", "scenes", "LOTA_PROD_0408", "v005", "textures",
    )
    os.makedirs(tex_dir, exist_ok=True)

    variants = []
    for name, fine_w, label in CONFIGS:
        fname = f"sphere_M1_sweep_{name}.png"
        path = os.path.join(tex_dir, fname)
        print(f"Generating {name} (fine weight {fine_w[0]:.2f}-{fine_w[1]:.2f})...")
        generate_one(path, fine_w)
        variants.append({"name": name, "texture": fname, "label": label})

    config = {
        "sweep_name": "weight",
        "dust_roughness": 0.10,
        "lighting_variants": ["4_mid_N", "2_mid"],
        "variants": variants,
    }
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "sweep_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\nConfig written: {config_path}")
