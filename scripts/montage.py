"""Create labeled montage from sweep renders + real reference.

Supports multiple lighting variants — creates one montage per lighting.
Output: {sweep_name}_sweep/montage_{lighting}.png

Usage: python montage.py [sweep_config.json]
"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "scripts" / "sweep_config.json"
REAL_REF_DIR = PROJECT_ROOT / "output" / "renders" / "v0.13" / "2x_" / "real" / "450"
OUTPUT_BASE = PROJECT_ROOT / "output" / "renders" / "v0.13" / "2x_"
LABEL_H = 32
PAD = 4
BG_COLOR = (30, 30, 30)
LABEL_COLOR = (255, 255, 255)


def load_font(size=15):
    for name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_montage(panels, output_path):
    if len(panels) < 2:
        print(f"  Not enough images ({len(panels)} found), skipping")
        return None

    font = load_font()
    ref_img = Image.open(panels[0][1])
    cell_w, cell_h = ref_img.size
    ref_img.close()

    n = len(panels)
    cols = min(n, 5)
    rows = (n + cols - 1) // cols

    canvas_w = cols * (cell_w + PAD) - PAD
    canvas_h = rows * (cell_h + LABEL_H + PAD) - PAD
    canvas = Image.new("RGB", (canvas_w, canvas_h), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    for i, (label, path) in enumerate(panels):
        r, c = divmod(i, cols)
        x = c * (cell_w + PAD)
        y = r * (cell_h + LABEL_H + PAD)

        img = Image.open(path)
        if img.size != (cell_w, cell_h):
            img = img.resize((cell_w, cell_h), Image.LANCZOS)
        if img.mode != "RGB":
            img = img.convert("RGB")
        canvas.paste(img, (x, y))

        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        tx = x + (cell_w - tw) // 2
        ty = y + cell_h + 4
        draw.text((tx, ty), label, fill=LABEL_COLOR, font=font)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(output_path))
    print(f"  Montage: {output_path} ({canvas_w}x{canvas_h}, {n} panels)")
    return str(output_path)


def create_montages(config_path):
    with open(config_path) as f:
        cfg = json.load(f)

    sweep_name = cfg["sweep_name"]
    variants = cfg["variants"]
    sweep_dir = OUTPUT_BASE / f"{sweep_name}_sweep"

    if "lighting_variants" in cfg:
        lightings = cfg["lighting_variants"]
    else:
        lightings = [cfg.get("lighting_variant", "4_mid_N")]

    for lighting in lightings:
        print(f"\n[montage] {lighting}:")
        panels = []

        real_path = REAL_REF_DIR / f"{lighting}.png"
        if real_path.exists():
            panels.append((f"Real ({lighting})", real_path))
        else:
            print(f"  Real ref not found: {real_path}")

        for bl in cfg.get("baseline_images", []):
            bl_path = PROJECT_ROOT / bl["path_template"].format(lighting=lighting)
            if bl_path.exists():
                panels.append((bl["label"], bl_path))
            else:
                print(f"  Baseline not found: {bl_path}")

        for v in variants:
            img_path = sweep_dir / f"{v['name']}_{lighting}.png"
            if not img_path.exists():
                img_path = sweep_dir / f"{v['name']}.png"
            if img_path.exists():
                panels.append((v["label"], img_path))
            else:
                print(f"  SKIP: {img_path}")

        out_path = sweep_dir / f"montage_{lighting}.png"
        build_montage(panels, out_path)


if __name__ == "__main__":
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CONFIG
    if not cfg_path.exists():
        print(f"Config not found: {cfg_path}")
        sys.exit(1)
    create_montages(cfg_path)
