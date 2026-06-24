"""Generic parameter sweep renderer for Kit.

Reads scripts/sweep_config.json to determine which textures to render.
Applies DustyMirror.mdl, swaps texture per variant, captures PNG.
Restores D31-5b and saves USD at the end.

Supports sweep_config.json fields:
  texture_input: which shader input to swap (default: dust_weight_texture)
  shader_setup: dict of extra shader params to set during init
  variants[].params: dict of per-variant shader param overrides

Usage: kit.exe app.kit --exec render_param_sweep.py
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

INIT_FRAMES = 30
STAGE_LOAD_FRAMES = 30
MDL_COMPILE_FRAMES = 120
TEXTURE_SETTLE_FRAMES = 60
CAPTURE_FLUSH_FRAMES = 5

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
    "oxide_strength", "oxide_thickness_texture", "oxide_thickness_influence",
]


def _log(msg):
    print(f"[sweep] {msg}", flush=True)


def _load_render_config():
    p = PROJECT_ROOT / "scripts" / "render_config.json"
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {}


def _load_sweep_config():
    p = PROJECT_ROOT / "scripts" / "sweep_config.json"
    with open(p) as f:
        return json.load(f)


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
    shader.CreateInput("reflection_roughness_texture_influence",
                       Sdf.ValueTypeNames.Float).Set(0.5)
    shader.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set(
        (0.8, 0.8, 0.8))


async def _capture_to_file(viewport_api, out_path, app):
    if os.path.exists(out_path):
        os.remove(out_path)
    capture_viewport_to_file(viewport_api, file_path=out_path)
    rc = omni.kit.renderer_capture.acquire_renderer_capture_interface()
    rc.wait_async_capture()

    poll_start = time.time()
    prev_size, stable = -1, 0
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
    return os.path.exists(out_path) and os.path.getsize(out_path) > 0


async def main():
    app = omni.kit.app.get_app()
    try:
        rcfg = _load_render_config()
        scfg = _load_sweep_config()

        sweep_name = scfg["sweep_name"]
        dust_roughness = scfg.get("dust_roughness", 0.10)
        variants = scfg["variants"]
        texture_input = scfg.get("texture_input", "dust_weight_texture")
        shader_setup = scfg.get("shader_setup", {})

        if "lighting_variants" in scfg:
            lightings = scfg["lighting_variants"]
        else:
            lightings = [scfg.get("lighting_variant", "4_mid_N")]

        usd_path = rcfg.get("usd_path", str(
            PROJECT_ROOT / "assets/scenes/LOTA_PROD_0408/v005/"
            "lota-16m10-v3-rev2_v005.usdc"))
        res_w = rcfg.get("res_width", 450)
        res_h = rcfg.get("res_height", 450)
        spp = rcfg.get("spp", 512)
        spi = rcfg.get("spi", 1)
        max_bounces = rcfg.get("max_specular_bounces", 16)
        cam_aperture = rcfg.get("camera_horizontal_aperture", None)

        exposure_map = {v["name"]: v["exposure"]
                        for v in rcfg.get("variants", [])
                        if "name" in v}

        out_base = PROJECT_ROOT / "output" / "renders" / "v0.13" / "2x_"
        out_dir = out_base / f"{sweep_name}_sweep"
        os.makedirs(str(out_dir), exist_ok=True)

        _log(f"=== {sweep_name.upper()} SWEEP ===")
        _log(f"Variants: {len(variants)}, roughness={dust_roughness}, "
             f"lightings={lightings}")

        await _wait_frames(INIT_FRAMES)

        _log(f"Opening USD: {usd_path}")
        usd_ctx = omni.usd.get_context()
        result, error = await usd_ctx.open_stage_async(usd_path)
        if not result:
            _log(f"ERROR: {error}")
            app.post_quit()
            return

        await _wait_frames(STAGE_LOAD_FRAMES)
        stage = usd_ctx.get_stage()

        root_prim = stage.GetPrimAtPath(ROOT_PRIM_PATH)
        vset = root_prim.GetVariantSets().GetVariantSet(VARIANT_SET_NAME)

        viewport_api = get_active_viewport()
        if viewport_api is None:
            _log("ERROR: No active viewport")
            app.post_quit()
            return

        viewport_api.camera_path = Sdf.Path(CAMERA_PATH)
        if cam_aperture is not None:
            cam_prim = stage.GetPrimAtPath(CAMERA_PATH)
            if cam_prim and cam_prim.IsA(UsdGeom.Camera):
                UsdGeom.Camera(cam_prim).GetHorizontalApertureAttr().Set(
                    float(cam_aperture))

        settings = carb.settings.get_settings()
        scale_path = ("/persistent/exts/omni.kit.viewport.window"
                      "/Viewport/Viewport0/resolutionScale")
        settings.set_float(scale_path, 1.0)
        viewport_api.fill_frame = False
        await _wait_frames(3)
        viewport_api.resolution = (res_w, res_h)
        await _wait_frames(5)

        settings.set_int("/rtx/pathtracing/totalSpp", spp)
        settings.set_int("/rtx/pathtracing/spp", spi)
        settings.set_int("/rtx/pathtracing/maxSpecularAndTransmissionBounces",
                         max_bounces)

        firefly_paths = [
            "/rtx/pathtracing/fireflyFilter/maxPerEmissiveUnexposedIntensity",
            "/rtx/pathtracing/fireflyFilter/maxUnexposedIntensityPerSample",
            "/rtx/pathtracing/fireflyFilter/maxUnexposedIntensityPerSampleDiffuse",
        ]
        for p in firefly_paths:
            before = settings.get(p)
            settings.set_float(p, 1e20)
            after = settings.get(p)
            _log(f"  firefly {p.split('/')[-1]}: {before} -> {after}")

        convergence = max(1, spp // spi) + 20
        cam_obj = stage.GetPrimAtPath(CAMERA_PATH)

        shader = UsdShade.Shader.Get(stage, SHADER_PATH)
        _clear_all_inputs(shader)
        _cleanup_sub_prims(stage)
        shader.SetSourceAsset(Sdf.AssetPath("./DustyMirror.mdl"), "mdl")
        shader.SetSourceAssetSubIdentifier("DustyMirror", "mdl")
        shader.CreateInput("base_color", Sdf.ValueTypeNames.Color3f).Set(
            (0.8, 0.8, 0.8))
        shader.CreateInput("dust_scatter_color", Sdf.ValueTypeNames.Color3f).Set(
            (1.0, 1.0, 1.0))
        shader.CreateInput("dust_roughness", Sdf.ValueTypeNames.Float).Set(
            dust_roughness)
        shader.CreateInput("dust_weight_constant", Sdf.ValueTypeNames.Float).Set(0.04)
        shader.CreateInput("dust_weight_texture_influence",
                           Sdf.ValueTypeNames.Float).Set(1.0)

        for skey, sval in shader_setup.items():
            if isinstance(sval, str):
                shader.CreateInput(skey, Sdf.ValueTypeNames.Asset).Set(
                    f"{TEX_DIR}/{sval}")
                _log(f"  setup: {skey} = {sval}")
            elif isinstance(sval, (int, float)):
                shader.CreateInput(skey, Sdf.ValueTypeNames.Float).Set(
                    float(sval))
                _log(f"  setup: {skey} = {sval}")

        _log(f"MDL compile wait ({MDL_COMPILE_FRAMES} frames)...")
        await _wait_frames(MDL_COMPILE_FRAMES)

        results = {}
        for lighting in lightings:
            exposure = exposure_map.get(lighting, 0.0012)
            vset.SetVariantSelection(lighting)
            cam_obj.GetAttribute("exposure:time").Set(float(exposure))
            _log(f"\n{'='*50}")
            _log(f"Lighting: {lighting}, exposure: {exposure}")
            _log(f"{'='*50}")

            settings.set_bool("/rtx/pathtracing/resetAccumulation", True)
            await _wait_frames(TEXTURE_SETTLE_FRAMES)

            for v in variants:
                name = v["name"]
                _log(f"\n--- {name} @ {lighting}: "
                     f"{v.get('label', v['texture'])} ---")

                shader.CreateInput(
                    texture_input, Sdf.ValueTypeNames.Asset
                ).Set(f"{TEX_DIR}/{v['texture']}")

                for pkey, pval in v.get("params", {}).items():
                    shader.CreateInput(pkey, Sdf.ValueTypeNames.Float).Set(
                        float(pval))

                settings.set_bool("/rtx/pathtracing/resetAccumulation", True)
                await _wait_frames(TEXTURE_SETTLE_FRAMES)

                t0 = time.time()
                for frame in range(convergence):
                    await app.next_update_async()
                    if (frame + 1) % 100 == 0:
                        _log(f"  {frame+1}/{convergence}")
                dt = time.time() - t0

                await _wait_frames(30)

                out_path = str(out_dir / f"{name}_{lighting}.png")
                ok = await _capture_to_file(viewport_api, out_path, app)
                fsize = os.path.getsize(out_path) if ok else 0
                key = f"{name}_{lighting}"
                results[key] = {"ok": ok, "size_kb": fsize / 1024,
                                "time_s": dt}
                _log(f"  {'OK' if ok else 'FAIL'} "
                     f"({fsize/1024:.0f}KB, {dt:.1f}s)")
                await _wait_frames(CAPTURE_FLUSH_FRAMES)

        _log("\nRestoring D31-5b...")
        _apply_d31_5b(shader, stage)
        stage.GetRootLayer().Save()
        _log("USD saved.")

        summary = {
            "sweep_name": sweep_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "params": {"dust_roughness": dust_roughness,
                       "lightings": lightings},
            "results": results,
        }
        summary_path = str(out_dir / "summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        _log(f"\n=== {sweep_name.upper()} SWEEP DONE ===")
        for key, r in results.items():
            _log(f"  {key}: {'OK' if r['ok'] else 'FAIL'}")

    except Exception as e:
        _log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    app.post_quit()


asyncio.ensure_future(main())
