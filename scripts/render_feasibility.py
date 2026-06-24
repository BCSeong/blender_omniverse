"""Feasibility test: M1-M4 material methods in a single Kit session.

Tests if each shader loads and renders. Renders 4_mid_N variant per method.
Output: {base_dir}/M{n}_feasibility/4_mid_N.png
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

RENDER_VARIANT = "4_mid_N"
RENDER_EXPOSURE = 0.0012

INIT_FRAMES = 30
STAGE_LOAD_FRAMES = 30
MDL_COMPILE_FRAMES = 120
CAPTURE_FLUSH_FRAMES = 5


def _load_config():
    config_path = PROJECT_ROOT / "scripts" / "render_config.json"
    cfg = {}
    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
    return cfg


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
TEX_DIR = "./textures"

BASE_OUTPUT = str(Path(CFG.get("output_dir",
    str(PROJECT_ROOT / "output/renders/v0.13/2x_"))).parent)


def _log(msg):
    print(f"[feasibility] {msg}", flush=True)


async def _wait_frames(n):
    app = omni.kit.app.get_app()
    for _ in range(n):
        await app.next_update_async()


def _clear_all_inputs(shader):
    ALL = [
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
    for name in ALL:
        inp = shader.GetInput(name)
        if inp and inp.GetAttr().IsAuthored():
            inp.GetAttr().Clear()


def _cleanup_sub_prims(stage):
    for name in SUB_PRIM_NAMES:
        path = f"{MATERIAL_PATH}/{name}"
        prim = stage.GetPrimAtPath(path)
        if prim and prim.IsValid():
            stage.RemovePrim(path)
            _log(f"  Removed sub-prim: {path}")


def apply_m1(shader, stage):
    """M1: Custom DustyMirror.mdl (weighted_layer)."""
    _clear_all_inputs(shader)
    _cleanup_sub_prims(stage)
    shader.SetSourceAsset(Sdf.AssetPath("./DustyMirror.mdl"), "mdl")
    shader.SetSourceAssetSubIdentifier("DustyMirror", "mdl")
    shader.CreateInput("base_color", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    shader.CreateInput("dust_weight_constant", Sdf.ValueTypeNames.Float).Set(0.04)
    shader.CreateInput("dust_weight_texture", Sdf.ValueTypeNames.Asset).Set(
        f"{TEX_DIR}/sphere_D32_dust_weight.png")
    shader.CreateInput("dust_weight_texture_influence", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("dust_roughness", Sdf.ValueTypeNames.Float).Set(0.4)
    shader.CreateInput("dust_scatter_color", Sdf.ValueTypeNames.Color3f).Set((1.0, 1.0, 1.0))
    return False


def apply_m2(shader, stage):
    """M2: OmniSurface.mdl (coat with texture)."""
    _clear_all_inputs(shader)
    _cleanup_sub_prims(stage)
    shader.SetSourceAsset(Sdf.AssetPath("OmniSurface.mdl"), "mdl")
    shader.SetSourceAssetSubIdentifier("OmniSurface", "mdl")
    shader.CreateInput("metalness", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("diffuse_reflection_weight", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("diffuse_reflection_color", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    shader.CreateInput("specular_reflection_weight", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("specular_reflection_roughness", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("specular_reflection_color", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    shader.CreateInput("coat_weight", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("coat_weight_image", Sdf.ValueTypeNames.Asset).Set(
        f"{TEX_DIR}/sphere_D32_dust_weight.png")
    shader.CreateInput("coat_roughness", Sdf.ValueTypeNames.Float).Set(0.4)
    shader.CreateInput("coat_ior", Sdf.ValueTypeNames.Float).Set(1.0)
    return False


def apply_m3(shader, stage):
    """M3: OmniSurfaceBlend.mdl (two sub-materials)."""
    _clear_all_inputs(shader)
    _cleanup_sub_prims(stage)
    shader.SetSourceAsset(Sdf.AssetPath("OmniSurfaceBlend.mdl"), "mdl")
    shader.SetSourceAssetSubIdentifier("OmniSurfaceBlend", "mdl")

    mirror_path = f"{MATERIAL_PATH}/MirrorBase"
    mirror_prim = stage.DefinePrim(mirror_path, "Shader")
    mirror_sh = UsdShade.Shader(mirror_prim)
    mirror_sh.SetSourceAsset(Sdf.AssetPath("OmniPBR.mdl"), "mdl")
    mirror_sh.SetSourceAssetSubIdentifier("OmniPBR", "mdl")
    mirror_sh.CreateInput("metallic_constant", Sdf.ValueTypeNames.Float).Set(1.0)
    mirror_sh.CreateInput("reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.0)
    mirror_sh.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    mirror_out = mirror_sh.CreateOutput("out", Sdf.ValueTypeNames.Token)

    hazy_path = f"{MATERIAL_PATH}/HazyBlend"
    hazy_prim = stage.DefinePrim(hazy_path, "Shader")
    hazy_sh = UsdShade.Shader(hazy_prim)
    hazy_sh.SetSourceAsset(Sdf.AssetPath("OmniPBR.mdl"), "mdl")
    hazy_sh.SetSourceAssetSubIdentifier("OmniPBR", "mdl")
    hazy_sh.CreateInput("metallic_constant", Sdf.ValueTypeNames.Float).Set(1.0)
    hazy_sh.CreateInput("reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.4)
    hazy_sh.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    hazy_out = hazy_sh.CreateOutput("out", Sdf.ValueTypeNames.Token)

    base_inp = shader.CreateInput("base_material", Sdf.ValueTypeNames.Token)
    base_inp.ConnectToSource(mirror_out)
    blend_inp = shader.CreateInput("blend_material", Sdf.ValueTypeNames.Token)
    blend_inp.ConnectToSource(hazy_out)
    shader.CreateInput("blend_weight", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("blend_weight_image", Sdf.ValueTypeNames.Asset).Set(
        f"{TEX_DIR}/sphere_D32_dust_weight.png")
    return False


def apply_m4(shader, stage):
    """M4: DustyVolume.mdl (volume scatter). Returns True = needs ptvol."""
    _clear_all_inputs(shader)
    _cleanup_sub_prims(stage)
    shader.SetSourceAsset(Sdf.AssetPath("./DustyVolume.mdl"), "mdl")
    shader.SetSourceAssetSubIdentifier("DustyVolume", "mdl")
    shader.CreateInput("base_color", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    shader.CreateInput("dust_fraction", Sdf.ValueTypeNames.Float).Set(0.05)
    shader.CreateInput("scatter_density", Sdf.ValueTypeNames.Float).Set(100.0)
    shader.CreateInput("scatter_color", Sdf.ValueTypeNames.Color3f).Set((1.0, 1.0, 1.0))
    shader.CreateInput("scatter_anisotropy", Sdf.ValueTypeNames.Float).Set(0.0)
    return True


def apply_d31_5b(shader, stage):
    """Restore D31-5b (best result)."""
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
    return False


METHODS = [
    ("M1", apply_m1, "Custom MDL (DustyMirror.mdl, weighted_layer)"),
    ("M2", apply_m2, "OmniSurface.mdl (coat with texture)"),
    ("M3", apply_m3, "OmniSurfaceBlend.mdl (two sub-materials)"),
    ("M4", apply_m4, "DustyVolume.mdl (volume scatter)"),
]


async def render_feasibility():
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
                cam_geom = UsdGeom.Camera(cam_prim_obj)
                cam_geom.GetHorizontalApertureAttr().Set(
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

        # Disable firefly filter — record before/after values
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
        _log("Firefly filter: DISABLED")

        # Set variant to 4_mid_N
        vset.SetVariantSelection(RENDER_VARIANT)
        cam_prim = stage.GetPrimAtPath(CAMERA_PATH)
        cam_prim.GetAttribute("exposure:time").Set(float(RENDER_EXPOSURE))
        _log(f"Variant: {RENDER_VARIANT}, exposure: {RENDER_EXPOSURE}")

        convergence_frames = max(1, PATH_TRACE_SPP // SAMPLES_PER_ITERATION) + 20
        _log(f"Resolution: {RES_WIDTH}x{RES_HEIGHT}, SPP: {PATH_TRACE_SPP}")
        _log(f"Convergence: {convergence_frames} frames")

        shader = UsdShade.Shader.Get(stage, SHADER_PATH)
        results = {}

        for method_name, apply_fn, description in METHODS:
            _log(f"\n{'='*50}")
            _log(f"Testing {method_name}: {description}")
            _log(f"{'='*50}")

            needs_ptvol = apply_fn(shader, stage)
            settings.set_bool("/rtx/pathtracing/ptvol/enabled", needs_ptvol)
            if needs_ptvol:
                _log("  ptvol: ENABLED for volume scatter")

            # MDL shader change requires extra settling for compilation
            _log(f"  Waiting for MDL compilation ({MDL_COMPILE_FRAMES} frames)...")
            await _wait_frames(MDL_COMPILE_FRAMES)

            # Reset and accumulate
            settings.set_bool("/rtx/pathtracing/resetAccumulation", True)
            await _wait_frames(10)
            _log(f"  Accumulating {convergence_frames} frames...")
            t0 = time.time()
            for frame in range(convergence_frames):
                await app.next_update_async()
                if (frame + 1) % 100 == 0:
                    _log(f"    ... {frame+1}/{convergence_frames}")
            accum_time = time.time() - t0
            _log(f"  Accumulation done ({accum_time:.1f}s)")

            await _wait_frames(30)

            # Capture
            out_dir = os.path.join(BASE_OUTPUT, f"{method_name}_feasibility")
            os.makedirs(out_dir, exist_ok=True)
            output_path = os.path.join(out_dir, f"{RENDER_VARIANT}.png")
            if os.path.exists(output_path):
                os.remove(output_path)

            capture_viewport_to_file(viewport_api, file_path=output_path)
            rc = omni.kit.renderer_capture.acquire_renderer_capture_interface()
            rc.wait_async_capture()

            # Wait for file
            poll_start = time.time()
            prev_size = -1
            stable = 0
            while (time.time() - poll_start) < 60:
                await app.next_update_async()
                if os.path.exists(output_path):
                    sz = os.path.getsize(output_path)
                    if sz > 0 and sz == prev_size:
                        stable += 1
                        if stable >= 10:
                            break
                    else:
                        stable = 0
                    prev_size = sz

            fsize = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            ok = fsize > 0
            results[method_name] = {
                "ok": ok,
                "file": output_path,
                "size_kb": fsize / 1024,
                "render_time_s": accum_time,
            }
            _log(f"  Result: {'OK' if ok else 'FAILED'} "
                 f"({fsize/1024:.0f}KB, {accum_time:.1f}s)")

            await _wait_frames(CAPTURE_FLUSH_FRAMES)

        # Restore D31-5b as best result
        _log("\n" + "="*50)
        _log("Restoring D31-5b (best result)...")
        apply_d31_5b(shader, stage)
        settings.set_bool("/rtx/pathtracing/ptvol/enabled", False)
        stage.GetRootLayer().Save()
        _log("USD saved with D31-5b applied.")

        # Save summary
        summary_path = os.path.join(BASE_OUTPUT, "feasibility_summary.json")
        with open(summary_path, "w") as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "methods": results,
                "settings": {
                    "resolution": f"{RES_WIDTH}x{RES_HEIGHT}",
                    "spp": PATH_TRACE_SPP,
                    "variant": RENDER_VARIANT,
                    "firefly_filter_enabled": False,
                    "firefly_before": {
                        k: v for k, v in firefly_before.items()
                        if v is not None
                    },
                    "firefly_after": {
                        k: v for k, v in firefly_after.items()
                        if v is not None
                    },
                },
            }, f, indent=2)
        _log(f"Summary saved: {summary_path}")

        _log("\n=== FEASIBILITY RESULTS ===")
        for name, r in results.items():
            status = "OK" if r["ok"] else "FAILED"
            _log(f"  {name}: {status} ({r['size_kb']:.0f}KB)")

    except Exception as e:
        _log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    app.post_quit()


asyncio.ensure_future(render_feasibility())
