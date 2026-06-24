"""Coverage sweep: roughness=0.10 fixed, only particle count changes.

  Cov1x: sphere_M1_dust_weight.png     (3000 fine — baseline)
  Cov2x: sphere_M1_dust_weight_2x.png  (6000 fine)
  Cov3x: sphere_M1_dust_weight_3x.png  (9000 fine)
  Cov4x: sphere_M1_dust_weight_4x.png  (12000 fine)
"""
import asyncio
import json
import os
import time
from pathlib import Path

import carb
import omni.kit.app
import omni.kit.renderer_capture
import omni.usd
from omni.kit.viewport.utility import get_active_viewport, capture_viewport_to_file
from pxr import Sdf, UsdGeom, UsdShade


PROJECT_ROOT = Path(os.environ.get(
    "BLENDER_OV_ROOT",
    Path(__file__).resolve().parent.parent
))

CAMERA_PATH = "/root/_Collection/InspectionCam/InspectionCam"
ROOT_PRIM_PATH = "/root"
VARIANT_SET_NAME = "LightingConfig"
SHADER_PATH = "/root/_materials/ChromeMirrorClean/Shader"
MATERIAL_PATH = "/root/_materials/ChromeMirrorClean"
SUB_PRIM_NAMES = ["MirrorBase", "HazyBlend"]
TEX_DIR = "./textures"

RENDER_VARIANT = "4_mid_N"
RENDER_EXPOSURE = 0.0012

INIT_FRAMES = 30
STAGE_LOAD_FRAMES = 30
MDL_COMPILE_FRAMES = 120
TEXTURE_SETTLE_FRAMES = 60
CAPTURE_FLUSH_FRAMES = 5

DUST_ROUGHNESS = 0.10


def _load_config():
    config_path = PROJECT_ROOT / "scripts" / "render_config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


CFG = _load_config()
USD_PATH = CFG.get("usd_path",
    str(PROJECT_ROOT / "assets/scenes/LOTA_PROD_0408/v004/"
        "lota-16m10-v3-rev2_v004_2x.usdc"))
RES_WIDTH = CFG.get("res_width", 450)
RES_HEIGHT = CFG.get("res_height", 450)
PATH_TRACE_SPP = CFG.get("spp", 512)
SAMPLES_PER_ITERATION = CFG.get("spi", 1)
MAX_SPECULAR_BOUNCES = CFG.get("max_specular_bounces", 16)
CAMERA_APERTURE_OVERRIDE = CFG.get("camera_horizontal_aperture", None)

BASE_OUTPUT = str(Path(CFG.get("output_dir",
    str(PROJECT_ROOT / "output/renders/v0.13/2x_"))).parent)

SWEEP_VARIANTS = [
    {"name": "Cov1x", "texture": "sphere_M1_dust_weight.png",     "desc": "1x (3K fine)"},
    {"name": "Cov2x", "texture": "sphere_M1_dust_weight_2x.png",  "desc": "2x (6K fine)"},
    {"name": "Cov3x", "texture": "sphere_M1_dust_weight_3x.png",  "desc": "3x (9K fine)"},
    {"name": "Cov4x", "texture": "sphere_M1_dust_weight_4x.png",  "desc": "4x (12K fine)"},
]


ALL_KNOWN_INPUTS = [
    "metallic_constant", "metallic_texture", "metallic_texture_influence",
    "reflection_roughness_constant", "reflection_roughness_texture_influence",
    "reflectionroughness_texture", "diffuse_color_constant",
    "enable_clearcoat", "clearcoat_weight",
    "clearcoat_reflection_roughness", "clearcoat_ior",
    "base_color", "dust_weight_constant", "dust_weight_texture",
    "dust_weight_texture_influence", "dust_roughness", "dust_scatter_color",
    "metalness", "specular_reflection_roughness", "specular_reflection_weight",
    "specular_reflection_color",
    "diffuse_reflection_weight", "diffuse_reflection_color",
    "coat_weight", "coat_weight_image", "coat_roughness",
    "coat_roughness_image", "coat_ior",
    "blend_weight", "blend_weight_image",
    "base_material", "blend_material",
    "scatter_density", "scatter_color", "scatter_anisotropy", "dust_fraction",
]


def _log(msg):
    print(f"[cov-sweep] {msg}", flush=True)


async def _wait_frames(n):
    app = omni.kit.app.get_app()
    for _ in range(n):
        await app.next_update_async()


def _clear_all_inputs(shader):
    for name in ALL_KNOWN_INPUTS:
        inp = shader.GetInput(name)
        if inp and inp.GetAttr().IsAuthored():
            inp.GetAttr().Clear()


def _cleanup_sub_prims(stage):
    for name in SUB_PRIM_NAMES:
        path = f"{MATERIAL_PATH}/{name}"
        prim = stage.GetPrimAtPath(path)
        if prim and prim.IsValid():
            stage.RemovePrim(path)


def _apply_d31_5b(shader, stage):
    _clear_all_inputs(shader)
    _cleanup_sub_prims(stage)
    shader.SetSourceAsset(Sdf.AssetPath("OmniPBR.mdl"), "mdl")
    shader.SetSourceAssetSubIdentifier("OmniPBR", "mdl")
    shader.CreateInput("metallic_constant", Sdf.ValueTypeNames.Float).Set(0.95)
    shader.CreateInput("metallic_texture", Sdf.ValueTypeNames.Asset).Set(
        f"{TEX_DIR}/sphere_D31-5_metallic.png")
    shader.CreateInput("metallic_texture_influence", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.015)
    shader.CreateInput("reflectionroughness_texture", Sdf.ValueTypeNames.Asset).Set(
        f"{TEX_DIR}/sphere_D31-5_rough.png")
    shader.CreateInput("reflection_roughness_texture_influence", Sdf.ValueTypeNames.Float).Set(0.5)
    shader.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))


async def main():
    app = omni.kit.app.get_app()

    try:
        _log("Waiting for Kit initialization...")
        await _wait_frames(INIT_FRAMES)

        _log(f"Opening USD: {USD_PATH}")
        usd_context = omni.usd.get_context()
        result, error = await usd_context.open_stage_async(USD_PATH)
        if not result:
            _log(f"ERROR: Failed to open USD - {error}")
            app.post_quit()
            return

        _log("Stage opened. Waiting for load...")
        await _wait_frames(STAGE_LOAD_FRAMES)

        stage = usd_context.get_stage()
        root_prim = stage.GetPrimAtPath(ROOT_PRIM_PATH)
        vset = root_prim.GetVariantSets().GetVariantSet(VARIANT_SET_NAME)

        viewport_api = get_active_viewport()
        if viewport_api is None:
            _log("ERROR: No active viewport")
            app.post_quit()
            return

        viewport_api.camera_path = Sdf.Path(CAMERA_PATH)

        if CAMERA_APERTURE_OVERRIDE is not None:
            cam_prim_obj = stage.GetPrimAtPath(CAMERA_PATH)
            if cam_prim_obj and cam_prim_obj.IsA(UsdGeom.Camera):
                UsdGeom.Camera(cam_prim_obj).GetHorizontalApertureAttr().Set(
                    float(CAMERA_APERTURE_OVERRIDE))

        settings = carb.settings.get_settings()

        scale_path = ("/persistent/exts/omni.kit.viewport.window"
                      "/Viewport/Viewport0/resolutionScale")
        settings.set_float(scale_path, 1.0)
        viewport_api.fill_frame = False
        await _wait_frames(3)
        viewport_api.resolution = (RES_WIDTH, RES_HEIGHT)
        await _wait_frames(5)

        settings.set_int("/rtx/pathtracing/totalSpp", PATH_TRACE_SPP)
        settings.set_int("/rtx/pathtracing/spp", SAMPLES_PER_ITERATION)
        settings.set_int("/rtx/pathtracing/maxSpecularAndTransmissionBounces",
                         MAX_SPECULAR_BOUNCES)

        # Disable firefly
        firefly_paths = [
            "/rtx/pathtracing/fireflyFilter/maxPerEmissiveUnexposedIntensity",
            "/rtx/pathtracing/fireflyFilter/maxUnexposedIntensityPerSample",
            "/rtx/pathtracing/fireflyFilter/maxUnexposedIntensityPerSampleDiffuse",
        ]
        firefly_before = {}
        for p in firefly_paths:
            firefly_before[p] = settings.get(p)
        for p in firefly_paths:
            settings.set_float(p, 1e20)
        firefly_after = {}
        for p in firefly_paths:
            firefly_after[p] = settings.get(p)
        _log("--- Firefly Filter ---")
        for p in firefly_paths:
            _log(f"  {p.split('/')[-1]}: "
                 f"before={firefly_before[p]}, after={firefly_after[p]}")

        # Set variant
        vset.SetVariantSelection(RENDER_VARIANT)
        cam_prim = stage.GetPrimAtPath(CAMERA_PATH)
        cam_prim.GetAttribute("exposure:time").Set(float(RENDER_EXPOSURE))
        _log(f"Variant: {RENDER_VARIANT}, exposure: {RENDER_EXPOSURE}")

        convergence_frames = max(1, PATH_TRACE_SPP // SAMPLES_PER_ITERATION) + 20
        _log(f"Resolution: {RES_WIDTH}x{RES_HEIGHT}, SPP: {PATH_TRACE_SPP}")
        _log(f"Fixed: dust_roughness={DUST_ROUGHNESS}")

        shader = UsdShade.Shader.Get(stage, SHADER_PATH)

        # Set DustyMirror.mdl once
        _log("\nSetting DustyMirror.mdl...")
        _clear_all_inputs(shader)
        _cleanup_sub_prims(stage)
        shader.SetSourceAsset(Sdf.AssetPath("./DustyMirror.mdl"), "mdl")
        shader.SetSourceAssetSubIdentifier("DustyMirror", "mdl")
        shader.CreateInput("base_color", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
        shader.CreateInput("dust_scatter_color", Sdf.ValueTypeNames.Color3f).Set((1.0, 1.0, 1.0))
        shader.CreateInput("dust_roughness", Sdf.ValueTypeNames.Float).Set(DUST_ROUGHNESS)
        shader.CreateInput("dust_weight_constant", Sdf.ValueTypeNames.Float).Set(0.04)
        shader.CreateInput("dust_weight_texture_influence", Sdf.ValueTypeNames.Float).Set(1.0)

        _log(f"Waiting for MDL compilation ({MDL_COMPILE_FRAMES} frames)...")
        await _wait_frames(MDL_COMPILE_FRAMES)

        results = {}

        for v in SWEEP_VARIANTS:
            name = v["name"]
            _log(f"\n{'='*50}")
            _log(f"Testing {name}: {v['desc']}")
            _log(f"  texture: {v['texture']}")
            _log(f"{'='*50}")

            # Switch texture only
            shader.CreateInput(
                "dust_weight_texture", Sdf.ValueTypeNames.Asset
            ).Set(f"{TEX_DIR}/{v['texture']}")

            settings.set_bool("/rtx/pathtracing/resetAccumulation", True)
            _log(f"  Settling ({TEXTURE_SETTLE_FRAMES} frames)...")
            await _wait_frames(TEXTURE_SETTLE_FRAMES)

            _log(f"  Accumulating {convergence_frames} frames...")
            t0 = time.time()
            for frame in range(convergence_frames):
                await app.next_update_async()
                if (frame + 1) % 100 == 0:
                    _log(f"    ... {frame+1}/{convergence_frames}")
            dt = time.time() - t0
            _log(f"  Accumulation done ({dt:.1f}s)")

            await _wait_frames(30)

            out_dir = os.path.join(BASE_OUTPUT, f"{name}_sweep")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "4_mid_N.png")
            if os.path.exists(out_path):
                os.remove(out_path)

            capture_viewport_to_file(viewport_api, file_path=out_path)
            rc = omni.kit.renderer_capture.acquire_renderer_capture_interface()
            rc.wait_async_capture()

            poll_start = time.time()
            prev_size = -1
            stable = 0
            while (time.time() - poll_start) < 60:
                await app.next_update_async()
                if os.path.exists(out_path):
                    sz = os.path.getsize(out_path)
                    if sz > 0 and sz == prev_size:
                        stable += 1
                        if stable >= 10:
                            break
                    else:
                        stable = 0
                    prev_size = sz

            fsize = os.path.getsize(out_path) if os.path.exists(out_path) else 0
            ok = fsize > 0
            results[name] = {
                "ok": ok, "file": out_path,
                "size_kb": fsize / 1024, "render_time_s": dt,
            }
            _log(f"  Result: {'OK' if ok else 'FAILED'} "
                 f"({fsize/1024:.0f}KB, {dt:.1f}s)")

            await _wait_frames(CAPTURE_FLUSH_FRAMES)

        # Restore D31-5b
        _log(f"\n{'='*50}")
        _log("Restoring D31-5b...")
        _apply_d31_5b(shader, stage)
        stage.GetRootLayer().Save()
        _log("USD saved with D31-5b applied.")

        summary_path = os.path.join(BASE_OUTPUT, "coverage_sweep_summary.json")
        with open(summary_path, "w") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "fixed_params": {"dust_roughness": DUST_ROUGHNESS,
                                 "dust_weight_constant": 0.04,
                                 "influence": 1.0},
                "methods": results,
                "settings": {
                    "resolution": f"{RES_WIDTH}x{RES_HEIGHT}",
                    "spp": PATH_TRACE_SPP,
                    "variant": RENDER_VARIANT,
                    "firefly_before": firefly_before,
                    "firefly_after": firefly_after,
                },
            }, f, indent=2, default=str)
        _log(f"Summary saved: {summary_path}")

        _log("\n=== COVERAGE SWEEP RESULTS ===")
        for name, r in results.items():
            _log(f"  {name}: {'OK' if r['ok'] else 'FAILED'} ({r['size_kb']:.0f}KB)")

    except Exception as e:
        _log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    app.post_quit()


asyncio.ensure_future(main())
