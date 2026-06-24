"""Autonomous ablation study for chrome sphere roughness map parameters.

Generates different roughness textures, renders via Kit, crops center regions,
and compares with real reference images. Saves study log and montages.

Usage: python scripts/ablation_study.py
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEXTURE_PATH = PROJECT_ROOT / "assets/scenes/LOTA_PROD_0408/v004/textures/sphere_dust_roughness.png"
USD_PATH = str(PROJECT_ROOT / "assets/scenes/LOTA_PROD_0408/v004/lota-16m10-v3-rev2_v004_2x.usdc")
CONFIG_PATH = PROJECT_ROOT / "scripts" / "render_config.json"

KIT_DIR = r"D:\Tools\kit-app-template\_build\windows-x86_64\release"
KIT_EXE = os.path.join(KIT_DIR, "kit", "kit.exe")
KIT_APP = os.path.join(KIT_DIR, "apps", "kohyoung.cam_sim.kit")
RENDER_SCRIPT = str(PROJECT_ROOT / "scripts" / "render_all_variants.py")

STUDY_ROOT = PROJECT_ROOT / "output" / "renders" / "v0.13" / "2x_"
REAL_450 = STUDY_ROOT / "real" / "450"
STUDY_LOG = STUDY_ROOT / "ablation_study.md"
STUDY_STATE = STUDY_ROOT / "ablation_state.json"

VARIANTS = ["1_top", "2_mid", "3_bot", "4_mid_N"]
ALL_VARIANT_DEFS = [
    {"name": "1_top",   "exposure": 0.0003},
    {"name": "2_mid",   "exposure": 0.0003},
    {"name": "3_bot",   "exposure": 0.0012},
    {"name": "4_mid_N", "exposure": 0.0012},
    {"name": "5_mid_S", "exposure": 0.0012},
    {"name": "6_mid_W", "exposure": 0.0012},
    {"name": "7_mid_E", "exposure": 0.0012},
    {"name": "9_all_off","exposure": 0.0012},
]

CROP_SIZE = 450
RES = 2048
SPP = 256
SPI = 3
SPECULAR = 6


# ---------------------------------------------------------------------------
# Texture generation
# ---------------------------------------------------------------------------

def generate_roughness_texture(coverage, mean, std, size=512, seed=42):
    rng = np.random.default_rng(seed)
    canvas = np.zeros((size, size), dtype=np.float32)
    total = size * size
    n_dots = int(total * coverage)
    if n_dots == 0:
        n_dots = 1

    indices = rng.choice(total, size=n_dots, replace=False)
    values = rng.normal(loc=mean, scale=std, size=n_dots)
    values = np.clip(values, 0.01, 1.0)

    canvas.flat[indices] = values

    img = Image.fromarray((canvas * 255).astype(np.uint8), mode="L")
    img.save(str(TEXTURE_PATH))

    return {
        "n_dots": n_dots,
        "actual_coverage": n_dots / total,
        "val_mean": float(values.mean()),
        "val_std": float(values.std()),
        "val_min": float(values.min()),
        "val_max": float(values.max()),
    }


# ---------------------------------------------------------------------------
# USD material modification
# ---------------------------------------------------------------------------

def modify_usd_material(specular=None, diffuse_color=None, metallic=None,
                        reconnect_metallic_tex=False, disconnect_metallic_tex=False):
    from pxr import Usd, UsdShade, Gf
    stage = Usd.Stage.Open(USD_PATH)
    shader = UsdShade.Shader(stage.GetPrimAtPath(
        "/root/_materials/ChromeMirrorClean/Principled_BSDF"))

    changes = {}
    if specular is not None:
        shader.GetInput("specular").Set(float(specular))
        changes["specular"] = specular

    if diffuse_color is not None:
        shader.GetInput("diffuseColor").Set(Gf.Vec3f(*diffuse_color))
        changes["diffuseColor"] = list(diffuse_color)

    if disconnect_metallic_tex:
        inp = shader.GetInput("metallic")
        inp.DisconnectSource()
        inp.Set(float(metallic if metallic is not None else 1.0))
        changes["metallic"] = metallic if metallic is not None else 1.0
        changes["metallic_tex"] = "disconnected"

    if reconnect_metallic_tex:
        met_tex = UsdShade.Shader(stage.GetPrimAtPath(
            "/root/_materials/ChromeMirrorClean/D15_Metallic"))
        shader.GetInput("metallic").ConnectToSource(
            met_tex.ConnectableAPI(), "r")
        changes["metallic_tex"] = "reconnected"

    if metallic is not None and not disconnect_metallic_tex and not reconnect_metallic_tex:
        inp = shader.GetInput("metallic")
        inp.DisconnectSource()
        inp.Set(float(metallic))
        changes["metallic"] = metallic

    stage.GetRootLayer().Save()
    return changes


# ---------------------------------------------------------------------------
# Render via Kit
# ---------------------------------------------------------------------------

def write_render_config(output_dir, variants=VARIANTS):
    enabled_set = set(variants)
    variant_list = [
        {"name": v["name"], "enabled": v["name"] in enabled_set,
         "exposure": v["exposure"]}
        for v in ALL_VARIANT_DEFS
    ]
    config = {
        "variants": variant_list,
        "res_width": RES,
        "res_height": RES,
        "spp": SPP,
        "spi": SPI,
        "max_specular_bounces": SPECULAR,
        "usd_path": USD_PATH,
        "output_dir": str(output_dir),
        "kit_dir": KIT_DIR,
    }
    with open(str(CONFIG_PATH), "w") as f:
        json.dump(config, f, indent=2)


def run_kit_render(output_dir, timeout=600):
    import shutil
    import tempfile

    tmp_dir = os.path.join(tempfile.gettempdir(), "ov_render")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_script = os.path.join(tmp_dir, "render_all_variants.py")
    shutil.copy2(RENDER_SCRIPT, tmp_script)

    args = [
        KIT_EXE, KIT_APP,
        "--no-window",
        "--exec", tmp_script,
        "--/app/content/emptyStageOnStart=true",
        f"--/app/renderer/resolution/width={RES}",
        f"--/app/renderer/resolution/height={RES}",
        "--/persistent/exts/omni.kit.viewport.window"
        "/Viewport/Viewport0/resolutionScale=1.0",
        "--/app/window/dpiScaleOverride=1.0",
        f"--/app/window/width={RES}",
        f"--/app/window/height={RES}",
    ]
    env = os.environ.copy()
    env["BLENDER_OV_ROOT"] = str(PROJECT_ROOT)

    kit_log = os.path.join(output_dir, "kit_stdout.log")
    render_log = os.path.join(output_dir, "render_log.txt")
    t0 = time.time()
    rc = 0
    with open(kit_log, "w") as log_f:
        proc = subprocess.Popen(args, env=env, stdout=log_f,
                                stderr=subprocess.STDOUT)
        # Poll render_log for completion instead of waiting for Kit exit
        while (time.time() - t0) < timeout:
            if proc.poll() is not None:
                rc = proc.returncode
                break
            if os.path.exists(render_log):
                try:
                    with open(render_log, "r", encoding="utf-8") as rl:
                        content = rl.read()
                    if "All variants rendered" in content:
                        time.sleep(3)  # brief grace for file flush
                        proc.kill()
                        rc = 0
                        break
                except OSError:
                    pass
            time.sleep(2)
        else:
            proc.kill()
            rc = -1

    elapsed = time.time() - t0
    return {"returncode": rc, "elapsed": elapsed}


# ---------------------------------------------------------------------------
# Image comparison
# ---------------------------------------------------------------------------

def crop_center(img, crop=CROP_SIZE):
    w, h = img.size
    left = (w - crop) // 2
    top = (h - crop) // 2
    return img.crop((left, top, left + crop, top + crop))


def load_sim_crop(path):
    img = Image.open(path)
    if img.mode == "RGB":
        img = img.convert("L")
    return crop_center(img)


def compare_images(real_path, sim_path):
    real = np.array(Image.open(real_path)).astype(np.float64) / 255.0
    sim = np.array(load_sim_crop(Image.open(sim_path) if False else
                                  _load_sim(sim_path))).astype(np.float64) / 255.0

    mae = float(np.mean(np.abs(real - sim)))

    r_c = real - real.mean()
    s_c = sim - sim.mean()
    denom = np.sqrt(np.sum(r_c ** 2) * np.sum(s_c ** 2))
    ncc = float(np.sum(r_c * s_c) / denom) if denom > 0 else 0.0

    mu_r, mu_s = real.mean(), sim.mean()
    var_r, var_s = real.var(), sim.var()
    cov = float(np.mean((real - mu_r) * (sim - mu_s)))
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    ssim = float(((2 * mu_r * mu_s + C1) * (2 * cov + C2)) /
                 ((mu_r ** 2 + mu_s ** 2 + C1) * (var_r + var_s + C2)))

    h_r, _ = np.histogram(real, bins=256, range=(0, 1))
    h_s, _ = np.histogram(sim, bins=256, range=(0, 1))
    h_r = h_r / h_r.sum()
    h_s = h_s / h_s.sum()
    hist = float(np.sum(np.minimum(h_r, h_s)))

    return {"mae": mae, "ncc": ncc, "ssim": ssim, "hist": hist}


def _load_sim(path):
    img = Image.open(path)
    if img.mode != "L":
        img = img.convert("L")
    return img


def compare_variant(variant, sim_dir):
    real_path = str(REAL_450 / f"{variant}.png")
    sim_path = str(Path(sim_dir) / f"{variant}.png")
    if not os.path.exists(real_path) or not os.path.exists(sim_path):
        return None

    real = np.array(Image.open(real_path)).astype(np.float64) / 255.0
    sim_img = _load_sim(sim_path)
    sim_crop = crop_center(sim_img)
    sim = np.array(sim_crop).astype(np.float64) / 255.0

    mae = float(np.mean(np.abs(real - sim)))
    r_c, s_c = real - real.mean(), sim - sim.mean()
    denom = np.sqrt(np.sum(r_c ** 2) * np.sum(s_c ** 2))
    ncc = float(np.sum(r_c * s_c) / denom) if denom > 0 else 0.0

    mu_r, mu_s = real.mean(), sim.mean()
    var_r, var_s = real.var(), sim.var()
    cov = float(np.mean((real - mu_r) * (sim - mu_s)))
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    ssim = float(((2 * mu_r * mu_s + C1) * (2 * cov + C2)) /
                 ((mu_r ** 2 + mu_s ** 2 + C1) * (var_r + var_s + C2)))

    return {"mae": mae, "ncc": ncc, "ssim": ssim}


def make_montage(sim_dir, out_path, variants=VARIANTS):
    """Side-by-side montage: real | sim for each variant, left to right."""
    pairs = []
    for v in variants:
        rp = REAL_450 / f"{v}.png"
        sp = Path(sim_dir) / f"{v}.png"
        if rp.exists() and sp.exists():
            r_img = Image.open(str(rp)).convert("L")
            s_img = crop_center(_load_sim(str(sp)))
            pairs.append((r_img, s_img))

    if not pairs:
        return
    n = len(pairs)
    gap = 4
    w = CROP_SIZE * 2 * n + gap * (n - 1)
    montage = Image.new("L", (w, CROP_SIZE), 80)
    for i, (r, s) in enumerate(pairs):
        x = i * (CROP_SIZE * 2 + gap)
        montage.paste(r, (x, 0))
        montage.paste(s, (x + CROP_SIZE, 0))
    montage.save(out_path)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state():
    if STUDY_STATE.exists():
        with open(STUDY_STATE) as f:
            return json.load(f)
    return {"iterations": [], "best": None, "phase": "coverage_coarse",
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S")}


def save_state(state):
    with open(STUDY_STATE, "w") as f:
        json.dump(state, f, indent=2)


def write_log(state):
    with open(STUDY_LOG, "w", encoding="utf-8") as f:
        f.write("# Ablation Study: Chrome Sphere Material\n\n")
        f.write(f"Started: {state.get('start_time', '?')}\n")
        f.write(f"Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Iterations: {len(state['iterations'])}\n")
        f.write(f"Phase: {state.get('phase', '?')}\n\n")

        if state.get("best"):
            b = state["best"]
            f.write("## Best Result\n\n")
            f.write(f"- Iteration: **{b['name']}**\n")
            f.write(f"- Avg SSIM: **{b['avg_ssim']:.4f}**\n")
            for k, v in b.get("params", {}).items():
                f.write(f"- {k}: {v}\n")
            f.write("\n")

        f.write("## Summary Table\n\n")
        f.write("| # | Name | Coverage | R.Mean | R.Std | Specular | DiffCol | "
                "Avg SSIM | Avg NCC | Avg MAE | Time |\n")
        f.write("|---|------|----------|--------|-------|----------|---------|"
                "----------|---------|---------|------|\n")
        for it in state["iterations"]:
            p = it["params"]
            m = it.get("avg_metrics", {})
            spec = p.get("specular", "1.0")
            dc = p.get("diffuseColor", "0.7")
            if isinstance(dc, list):
                dc = f"{dc[0]:.1f}"
            f.write(
                f"| {it['idx']} | {it['name']} "
                f"| {p.get('coverage', '-'):.1%} "
                f"| {p.get('roughness_mean', '-'):.3f} "
                f"| {p.get('roughness_std', '-'):.3f} "
                f"| {spec} | {dc} "
                f"| {m.get('ssim', 0):.4f} | {m.get('ncc', 0):.4f} "
                f"| {m.get('mae', 0):.4f} | {it.get('render_time', 0):.0f}s |\n"
            )

        f.write("\n## Per-Variant Detail\n\n")
        for it in state["iterations"]:
            f.write(f"### {it['name']}\n")
            pv = it.get("per_variant", {})
            for v in VARIANTS:
                if v in pv:
                    vm = pv[v]
                    f.write(f"  - {v}: SSIM={vm['ssim']:.4f} "
                            f"NCC={vm['ncc']:.4f} MAE={vm['mae']:.4f}\n")
            if it.get("notes"):
                f.write(f"  - **Notes**: {it['notes']}\n")
            f.write("\n")

        if state.get("analysis"):
            f.write("## Analysis & Decisions\n\n")
            for a in state["analysis"]:
                f.write(f"- {a}\n")


# ---------------------------------------------------------------------------
# Run one iteration
# ---------------------------------------------------------------------------

def run_one(name, params, state):
    out_dir = STUDY_ROOT / name
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Iteration {len(state['iterations'])+1}: {name}")
    print(f"  Params: {params}")
    print(f"{'='*60}")

    # Generate texture
    tex = generate_roughness_texture(
        params["coverage"], params["roughness_mean"], params["roughness_std"])
    print(f"  Texture: {tex['n_dots']} dots, mean={tex['val_mean']:.3f}")

    # Apply USD material changes if requested
    usd_changes = {}
    if "specular" in params or "diffuseColor" in params or "metallic" in params:
        usd_changes = modify_usd_material(
            specular=params.get("specular"),
            diffuse_color=params.get("diffuseColor"),
            metallic=params.get("metallic"),
            disconnect_metallic_tex=params.get("disconnect_metallic_tex", False),
            reconnect_metallic_tex=params.get("reconnect_metallic_tex", False),
        )
        print(f"  USD changes: {usd_changes}")

    # Write config & render
    write_render_config(str(out_dir))
    print(f"  Rendering... ", end="", flush=True)
    kit_result = run_kit_render(str(out_dir))
    print(f"done ({kit_result['elapsed']:.0f}s, rc={kit_result['returncode']})")

    # Compare
    per_variant = {}
    for v in VARIANTS:
        m = compare_variant(v, str(out_dir))
        if m:
            per_variant[v] = m

    avg = {}
    if per_variant:
        for key in ["mae", "ncc", "ssim"]:
            avg[key] = float(np.mean([m[key] for m in per_variant.values()]))
        print(f"  Avg SSIM={avg['ssim']:.4f}  NCC={avg['ncc']:.4f}  MAE={avg['mae']:.4f}")

    # Montage
    make_montage(str(out_dir), str(out_dir / "montage.png"))

    iteration = {
        "idx": len(state["iterations"]) + 1,
        "name": name,
        "params": params,
        "texture_stats": tex,
        "usd_changes": usd_changes,
        "per_variant": per_variant,
        "avg_metrics": avg,
        "render_time": kit_result["elapsed"],
        "returncode": kit_result["returncode"],
        "notes": "",
    }
    state["iterations"].append(iteration)

    if avg and (state["best"] is None
                or avg.get("ssim", 0) > state["best"].get("avg_ssim", 0)):
        state["best"] = {"name": name, "params": params,
                         "avg_ssim": avg["ssim"]}

    save_state(state)
    write_log(state)
    return iteration


def best_of(state, prefix):
    group = [it for it in state["iterations"] if it["name"].startswith(prefix)]
    if not group:
        return None
    return max(group, key=lambda x: x.get("avg_metrics", {}).get("ssim", 0))


def add_analysis(state, msg):
    state.setdefault("analysis", [])
    state["analysis"].append(f"[{time.strftime('%H:%M')}] {msg}")
    print(f"  >> {msg}")


# ---------------------------------------------------------------------------
# Main study loop
# ---------------------------------------------------------------------------

def main():
    state = load_state()
    if "analysis" not in state:
        state["analysis"] = []

    print("=" * 60)
    print("  Chrome Sphere Material Ablation Study")
    print(f"  Phase: {state['phase']}")
    print(f"  Prior iterations: {len(state['iterations'])}")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Phase 1: Coarse coverage sweep (fix mean=0.08, std=0.02)
    # ------------------------------------------------------------------
    if state["phase"] == "coverage_coarse":
        add_analysis(state, "Phase 1: Coarse coverage sweep [1%..20%], mean=0.08, std=0.02")
        for cov in [0.01, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]:
            name = f"cov_{int(cov*100):02d}pct"
            if any(it["name"] == name for it in state["iterations"]):
                continue
            run_one(name, {"coverage": cov, "roughness_mean": 0.08,
                           "roughness_std": 0.02}, state)

        b = best_of(state, "cov_")
        if b:
            state["best_coverage"] = b["params"]["coverage"]
            add_analysis(state, f"Phase 1 done. Best coverage={state['best_coverage']:.0%} "
                         f"(SSIM={b['avg_metrics']['ssim']:.4f})")
        state["phase"] = "coverage_fine"
        save_state(state)

    # ------------------------------------------------------------------
    # Phase 2: Fine coverage around best
    # ------------------------------------------------------------------
    if state["phase"] == "coverage_fine":
        bc = state.get("best_coverage", 0.05)
        fine = sorted(set([
            max(0.005, bc - 0.02), max(0.005, bc - 0.01),
            bc + 0.01, bc + 0.02
        ]))
        add_analysis(state, f"Phase 2: Fine coverage around {bc:.0%}: {fine}")

        for cov in fine:
            name = f"cov_f_{int(cov*1000):03d}"
            if any(it["name"] == name for it in state["iterations"]):
                continue
            run_one(name, {"coverage": cov, "roughness_mean": 0.08,
                           "roughness_std": 0.02}, state)

        b = best_of(state, "cov_")
        if b:
            state["best_coverage"] = b["params"]["coverage"]
            add_analysis(state, f"Phase 2 done. Best coverage={state['best_coverage']:.1%}")
        state["phase"] = "roughness_mean"
        save_state(state)

    # ------------------------------------------------------------------
    # Phase 3: Roughness mean sweep
    # ------------------------------------------------------------------
    if state["phase"] == "roughness_mean":
        bc = state.get("best_coverage", 0.05)
        add_analysis(state, f"Phase 3: Roughness mean sweep, coverage={bc:.1%}")

        for m in [0.02, 0.04, 0.06, 0.08, 0.10, 0.15, 0.20, 0.30]:
            name = f"mean_{int(m*100):03d}"
            if any(it["name"] == name for it in state["iterations"]):
                continue
            run_one(name, {"coverage": bc, "roughness_mean": m,
                           "roughness_std": 0.02}, state)

        b = best_of(state, "mean_")
        if b:
            state["best_mean"] = b["params"]["roughness_mean"]
            add_analysis(state, f"Phase 3 done. Best mean={state['best_mean']:.3f}")
        state["phase"] = "roughness_std"
        save_state(state)

    # ------------------------------------------------------------------
    # Phase 4: Roughness std sweep
    # ------------------------------------------------------------------
    if state["phase"] == "roughness_std":
        bc = state.get("best_coverage", 0.05)
        bm = state.get("best_mean", 0.08)
        add_analysis(state, f"Phase 4: Roughness std sweep, cov={bc:.1%}, mean={bm:.3f}")

        for s in [0.005, 0.01, 0.02, 0.04, 0.06, 0.10]:
            name = f"std_{int(s*1000):03d}"
            if any(it["name"] == name for it in state["iterations"]):
                continue
            run_one(name, {"coverage": bc, "roughness_mean": bm,
                           "roughness_std": s}, state)

        b = best_of(state, "std_")
        if b:
            state["best_std"] = b["params"]["roughness_std"]
            add_analysis(state, f"Phase 4 done. Best std={state['best_std']:.3f}")
        state["phase"] = "specular"
        save_state(state)

    # ------------------------------------------------------------------
    # Phase 5: Specular sweep
    # ------------------------------------------------------------------
    if state["phase"] == "specular":
        bc = state.get("best_coverage", 0.05)
        bm = state.get("best_mean", 0.08)
        bs = state.get("best_std", 0.02)
        add_analysis(state, f"Phase 5: Specular sweep")

        for spec in [0.3, 0.5, 0.7, 1.0]:
            name = f"spec_{int(spec*10):02d}"
            if any(it["name"] == name for it in state["iterations"]):
                continue
            run_one(name, {"coverage": bc, "roughness_mean": bm,
                           "roughness_std": bs, "specular": spec}, state)

        b = best_of(state, "spec_")
        if b:
            state["best_specular"] = b["params"].get("specular", 1.0)
            add_analysis(state, f"Phase 5 done. Best specular={state['best_specular']}")
            modify_usd_material(specular=state["best_specular"])
        state["phase"] = "diffuse_color"
        save_state(state)

    # ------------------------------------------------------------------
    # Phase 6: Diffuse color sweep (affects metallic base reflectance)
    # ------------------------------------------------------------------
    if state["phase"] == "diffuse_color":
        bc = state.get("best_coverage", 0.05)
        bm = state.get("best_mean", 0.08)
        bs = state.get("best_std", 0.02)
        add_analysis(state, "Phase 6: DiffuseColor sweep (metallic base color)")

        for gray in [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            name = f"dc_{int(gray*10):02d}"
            if any(it["name"] == name for it in state["iterations"]):
                continue
            run_one(name, {"coverage": bc, "roughness_mean": bm,
                           "roughness_std": bs,
                           "diffuseColor": [gray, gray, gray]}, state)

        b = best_of(state, "dc_")
        if b:
            state["best_dc"] = b["params"].get("diffuseColor", [0.7, 0.7, 0.7])
            add_analysis(state, f"Phase 6 done. Best diffuseColor={state['best_dc']}")
            modify_usd_material(diffuse_color=state["best_dc"])
        state["phase"] = "metallic_tex"
        save_state(state)

    # ------------------------------------------------------------------
    # Phase 7: Try reconnecting metallic texture (dust = non-metallic)
    # ------------------------------------------------------------------
    if state["phase"] == "metallic_tex":
        bc = state.get("best_coverage", 0.05)
        bm = state.get("best_mean", 0.08)
        bs = state.get("best_std", 0.02)
        add_analysis(state, "Phase 7: Metallic texture reconnect test")

        name = "met_tex_on"
        if not any(it["name"] == name for it in state["iterations"]):
            run_one(name, {"coverage": bc, "roughness_mean": bm,
                           "roughness_std": bs,
                           "reconnect_metallic_tex": True}, state)

        name = "met_tex_off"
        if not any(it["name"] == name for it in state["iterations"]):
            run_one(name, {"coverage": bc, "roughness_mean": bm,
                           "roughness_std": bs,
                           "disconnect_metallic_tex": True,
                           "metallic": 1.0}, state)

        # Choose better
        on = next((it for it in state["iterations"] if it["name"] == "met_tex_on"), None)
        off = next((it for it in state["iterations"] if it["name"] == "met_tex_off"), None)
        if on and off:
            on_s = on.get("avg_metrics", {}).get("ssim", 0)
            off_s = off.get("avg_metrics", {}).get("ssim", 0)
            if on_s > off_s:
                add_analysis(state, f"Metallic tex ON wins (SSIM {on_s:.4f} vs {off_s:.4f})")
                modify_usd_material(reconnect_metallic_tex=True)
            else:
                add_analysis(state, f"Metallic tex OFF wins (SSIM {off_s:.4f} vs {on_s:.4f})")
                modify_usd_material(disconnect_metallic_tex=True, metallic=1.0)

        state["phase"] = "final"
        save_state(state)

    # ------------------------------------------------------------------
    # Phase 8: Final high-quality render with best params
    # ------------------------------------------------------------------
    if state["phase"] == "final":
        add_analysis(state, "Phase 8: Final render with best parameters (SPP=512)")
        bc = state.get("best_coverage", 0.05)
        bm = state.get("best_mean", 0.08)
        bs = state.get("best_std", 0.02)

        global SPP
        SPP = 512

        generate_roughness_texture(bc, bm, bs)
        best_spec = state.get("best_specular", 1.0)
        best_dc = state.get("best_dc", [0.7, 0.7, 0.7])
        modify_usd_material(specular=best_spec, diffuse_color=best_dc)

        name = "final_best"
        if not any(it["name"] == name for it in state["iterations"]):
            run_one(name, {"coverage": bc, "roughness_mean": bm,
                           "roughness_std": bs, "specular": best_spec,
                           "diffuseColor": best_dc}, state)

        state["phase"] = "done"
        save_state(state)
        write_log(state)
        add_analysis(state, f"Study complete. Best: {state.get('best', {})}")

    print("\n" + "=" * 60)
    print("  STUDY COMPLETE")
    print(f"  Total iterations: {len(state['iterations'])}")
    print(f"  Best: {state.get('best', {})}")
    print(f"  Results: {STUDY_ROOT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
