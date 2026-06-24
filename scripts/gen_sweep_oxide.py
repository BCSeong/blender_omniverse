"""Generate oxide thickness texture and sweep config for thin-film absorption.

Generates one noise texture (organic spatial variation of oxide thickness)
and a sweep_config.json that varies oxide_strength across 4 levels.
Same texture for all variants; only the MDL oxide_strength parameter changes.

Also writes sweep_config.json for render_param_sweep.py and montage.py.
"""
import json
import os
import numpy as np
from PIL import Image, ImageFilter

SIZE = 1024
SEED = 77

OXIDE_TEXTURE_NAME = "sphere_M1_oxide.png"
DUST_TEXTURE_NAME = "sphere_M1_dust_weight.png"

CONFIGS = [
    ("O1", 0.003, "O1: str=0.003"),
    ("O2", 0.006, "O2: str=0.006"),
    ("O3", 0.010, "O3: str=0.010"),
    ("O4", 0.020, "O4: str=0.020"),
]


def generate_oxide_noise(size, seed):
    """Multi-octave noise simulating organic oxide thickness variation."""
    rng = np.random.RandomState(seed)
    result = np.zeros((size, size), dtype=np.float32)

    scales = [256, 512, 1024]
    weights = [0.25, 0.40, 0.35]

    for scale, weight in zip(scales, weights):
        grid = rng.rand(scale, scale).astype(np.float32)
        small = Image.fromarray((grid * 255).astype(np.uint8), mode="L")
        big = small.resize((size, size), Image.BICUBIC)
        result += np.array(big).astype(np.float32) / 255.0 * weight

    result = (result - result.min()) / (result.max() - result.min() + 1e-10)
    return result


if __name__ == "__main__":
    tex_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..",
        "assets", "scenes", "LOTA_PROD_0408", "v005", "textures",
    )
    os.makedirs(tex_dir, exist_ok=True)

    noise = generate_oxide_noise(SIZE, SEED)
    p_lo, p_hi = np.percentile(noise, [5, 95])
    noise = np.clip((noise - p_lo) / (p_hi - p_lo + 1e-10), 0.0, 1.0)
    pil = Image.fromarray((noise * 255).astype(np.uint8), mode="L")
    pil = pil.filter(ImageFilter.GaussianBlur(radius=0.5))

    path = os.path.join(tex_dir, OXIDE_TEXTURE_NAME)
    pil.save(path)
    arr = np.array(pil)
    print(f"Oxide texture: {OXIDE_TEXTURE_NAME}")
    print(f"  min={arr.min()}, max={arr.max()}, mean={arr.mean():.1f}")

    variants = []
    for name, strength, label in CONFIGS:
        variants.append({
            "name": name,
            "texture": OXIDE_TEXTURE_NAME,
            "params": {"oxide_strength": strength},
            "label": label,
        })

    config = {
        "sweep_name": "oxide",
        "texture_input": "oxide_thickness_texture",
        "dust_roughness": 0.10,
        "shader_setup": {
            "dust_weight_texture": DUST_TEXTURE_NAME,
            "oxide_thickness_influence": 1.0,
        },
        "lighting_variants": ["4_mid_N", "2_mid"],
        "baseline_images": [
            {
                "label": "A2W2 (no oxide)",
                "path_template":
                    "output/renders/v0.13/2x_/ambient_sweep/A2_{lighting}.png",
            },
        ],
        "variants": variants,
    }
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "sweep_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\nConfig written: {config_path}")
