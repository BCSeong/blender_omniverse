"""Headless batch-render all lighting variants via Omniverse Kit.

Uses capture_viewport_to_file with --no-window mode.
Reads render_config.json (written by render_gui.py) for settings.
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
from pxr import Sdf, UsdGeom


PROJECT_ROOT = Path(os.environ.get(
    "BLENDER_OV_ROOT",
    Path(__file__).resolve().parent.parent
))

DEFAULT_USD_PATH = str(PROJECT_ROOT / "assets" / "scenes" / "LOTA_PROD_0408"
                       / "v004" / "lota-16m10-v3-rev2_v004.usdc")
CAMERA_PATH = "/root/_Collection/InspectionCam/InspectionCam"
ROOT_PRIM_PATH = "/root"
VARIANT_SET_NAME = "LightingConfig"

DEFAULTS = {
    "variants": [
        {"name": "1_top",    "enabled": True, "exposure": 0.0001},
        {"name": "2_mid",    "enabled": True, "exposure": 0.0001},
        {"name": "3_bot",    "enabled": True, "exposure": 0.0001},
        {"name": "4_mid_N",  "enabled": True, "exposure": 0.0001},
        {"name": "5_mid_S",  "enabled": True, "exposure": 0.0001},
        {"name": "6_mid_W",  "enabled": True, "exposure": 0.0001},
        {"name": "7_mid_E",  "enabled": True, "exposure": 0.0001},
        {"name": "9_all_off","enabled": True, "exposure": 0.0001},
    ],
    "res_width": 512,
    "res_height": 512,
    "spp": 512,
    "usd_path": DEFAULT_USD_PATH,
    "output_dir": str(PROJECT_ROOT / "output" / "renders"),
}

INIT_FRAMES = 30
STAGE_LOAD_FRAMES = 30
CAPTURE_FLUSH_FRAMES = 5


def _load_config():
    cfg = dict(DEFAULTS)
    config_path = PROJECT_ROOT / "scripts" / "render_config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                user_cfg = json.load(f)
            cfg.update(user_cfg)
            print(f"[render] Config loaded: {config_path}")
        except Exception as e:
            print(f"[render] WARNING: Config load failed: {e}")
    return cfg


CFG = _load_config()
VARIANTS = CFG["variants"]
RES_WIDTH = CFG["res_width"]
RES_HEIGHT = CFG["res_height"]
PATH_TRACE_SPP = CFG["spp"]
SAMPLES_PER_ITERATION = CFG.get("spi", 3)
MAX_SPECULAR_BOUNCES = CFG.get("max_specular_bounces", 6)
USD_PATH = CFG.get("usd_path", DEFAULT_USD_PATH)
OUTPUT_DIR = CFG["output_dir"]
CAMERA_APERTURE_OVERRIDE = CFG.get("camera_horizontal_aperture", None)


_log_file = None


def _log(msg):
    print(f"[render] {msg}", flush=True)
    carb.log_info(f"[render] {msg}")
    if _log_file is not None:
        _log_file.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
        _log_file.flush()


async def _wait_frames(n):
    app = omni.kit.app.get_app()
    for _ in range(n):
        await app.next_update_async()


async def render_all_variants():
    global _log_file
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
        if not root_prim:
            _log(f"ERROR: root prim not found at {ROOT_PRIM_PATH}")
            app.post_quit()
            return

        vset = root_prim.GetVariantSets().GetVariantSet(VARIANT_SET_NAME)
        if not vset:
            _log(f"ERROR: variant set '{VARIANT_SET_NAME}' not found")
            app.post_quit()
            return

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
                orig = cam_geom.GetHorizontalApertureAttr().Get()
                cam_geom.GetHorizontalApertureAttr().Set(
                    float(CAMERA_APERTURE_OVERRIDE))
                _log(f"Camera aperture override: {orig} -> "
                     f"{CAMERA_APERTURE_OVERRIDE} mm (in-memory only)")

        settings = carb.settings.get_settings()

        # Force render scale to 100% — Kit has two persistent paths
        scale_paths = [
            "/persistent/exts/omni.kit.viewport.window"
            "/Viewport/Viewport0/resolutionScale",
            "/persistent/app/viewport"
            "/Viewport/Viewport0/resolutionScale",
        ]
        viewport_api.fill_frame = False
        await _wait_frames(3)

        for sp in scale_paths:
            settings.set_float(sp, 1.0)
        viewport_api.resolution = (RES_WIDTH, RES_HEIGHT)
        await _wait_frames(10)

        for sp in scale_paths:
            val = settings.get(sp)
            _log(f"  {sp} = {val}")
            if val is not None and abs(val - 1.0) > 0.01:
                _log(f"ERROR: resolutionScale={val} at {sp}. "
                     f"Output would be {int(RES_WIDTH * val)}x"
                     f"{int(RES_HEIGHT * val)}. Aborting.")
                app.post_quit()
                return

        effective_res = viewport_api.resolution
        _log(f"Resolution: {RES_WIDTH}x{RES_HEIGHT}, "
             f"viewport={effective_res}")

        # Apply render quality settings from GUI config
        settings.set_int("/rtx/pathtracing/totalSpp", PATH_TRACE_SPP)
        settings.set_int("/rtx/pathtracing/spp", SAMPLES_PER_ITERATION)
        settings.set_int("/rtx/pathtracing/maxSpecularAndTransmissionBounces",
                         MAX_SPECULAR_BOUNCES)

        # Firefly filter control from config
        firefly_enabled = CFG.get("firefly_filter_enabled", False)
        firefly_paths = [
            "/rtx/pathtracing/fireflyFilter/maxPerEmissiveUnexposedIntensity",
            "/rtx/pathtracing/fireflyFilter/maxUnexposedIntensityPerSample",
            "/rtx/pathtracing/fireflyFilter/maxUnexposedIntensityPerSampleDiffuse",
        ]
        firefly_before = {}
        for p in firefly_paths:
            firefly_before[p] = settings.get(p)
        if not firefly_enabled:
            for p in firefly_paths:
                settings.set_float(p, 1e20)
            _log("Firefly filter: DISABLED (max intensity set to 1e20)")
        else:
            _log(f"Firefly filter: ENABLED (using current values)")

        # Non-uniform volume rendering control
        ptvol_enabled = CFG.get("ptvol_enabled", False)
        ptvol_before = settings.get("/rtx/pathtracing/ptvol/enabled")
        settings.set_bool("/rtx/pathtracing/ptvol/enabled", ptvol_enabled)
        _log(f"Non-uniform volumes: {'ENABLED' if ptvol_enabled else 'DISABLED'}"
             f" (was: {ptvol_before})")

        await _wait_frames(3)

        # Log effective render settings
        _log("--- Render Settings ---")
        _log(f"  Resolution: {RES_WIDTH}x{RES_HEIGHT}")
        _log(f"  resolutionScale: {[settings.get(sp) for sp in scale_paths]}")
        _log(f"  totalSpp (GUI): {PATH_TRACE_SPP}")
        rt_settings = [
            ("/rtx/pathtracing/totalSpp", "Total SPP (applied)"),
            ("/rtx/pathtracing/spp", "Samples per Pixel per Frame"),
            ("/rtx/pathtracing/maxBounces", "Max Bounces"),
            ("/rtx/pathtracing/maxSpecularAndTransmissionBounces",
             "Max Specular/Transmission Bounces"),
            ("/rtx/pathtracing/maxVolumeBounces",
             "Max SSS Volume Scattering Bounces"),
            ("/rtx/pathtracing/maxFogBounces", "Max Fog Scattering Bounces"),
            ("/rtx/pathtracing/adaptiveSampling/enabled", "Adaptive Sampling"),
        ]
        for path, label in rt_settings:
            val = settings.get(path)
            if val is not None:
                _log(f"  {label}: {val}")
        _log("--- Firefly Filter ---")
        for p in firefly_paths:
            _log(f"  {p.split('/')[-1]}: before={firefly_before[p]}, "
                 f"after={settings.get(p)}")
        _log("----------------------")

        enabled = [v for v in VARIANTS if v.get("enabled", True)]
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        log_path = os.path.join(OUTPUT_DIR, "render_log.txt")
        _log_file = open(log_path, "w", encoding="utf-8")
        _log("Render log started")

        cam_prim = stage.GetPrimAtPath(CAMERA_PATH)
        settle_frames = PATH_TRACE_SPP + 50

        # Read camera properties from USD
        cam_attrs = {}
        for attr in cam_prim.GetAttributes():
            name = attr.GetName()
            val = attr.Get()
            if val is not None and not name.startswith("xformOp"):
                try:
                    json.dumps(val)
                    cam_attrs[name] = val
                except (TypeError, ValueError):
                    cam_attrs[name] = str(val)

        # Read all active render settings from Kit runtime
        rt_paths = [
            "/rtx/pathtracing/totalSpp",
            "/rtx/pathtracing/spp",
            "/rtx/pathtracing/maxBounces",
            "/rtx/pathtracing/maxSpecularAndTransmissionBounces",
            "/rtx/pathtracing/maxVolumeBounces",
            "/rtx/pathtracing/maxFogBounces",
            "/rtx/pathtracing/adaptiveSampling/enabled",
            "/rtx/pathtracing/maxSamplesPerLaunch",
            "/rtx/rendermode",
        ] + firefly_paths
        render_settings = {}
        for p in rt_paths:
            val = settings.get(p)
            if val is not None:
                render_settings[p] = val
        render_settings["_firefly_filter_enabled"] = firefly_enabled
        render_settings["_firefly_before"] = {
            k: v for k, v in firefly_before.items() if v is not None
        }
        render_settings["/rtx/pathtracing/ptvol/enabled"] = ptvol_enabled
        render_settings["_ptvol_before"] = ptvol_before

        metadata = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "usd_path": USD_PATH,
            "resolution": {
                "width": RES_WIDTH,
                "height": RES_HEIGHT,
                "render_scale": {
                    sp: settings.get(sp) for sp in scale_paths
                },
                "viewport_resolution": list(effective_res),
            },
            "camera": {
                "prim_path": CAMERA_PATH,
                "attributes": cam_attrs,
            },
            "render_settings": render_settings,
            "variants": [
                {"name": v["name"], "exposure": v.get("exposure", 0.0001)}
                for v in enabled
            ],
            "settle_frames": settle_frames,
        }
        meta_path = os.path.join(OUTPUT_DIR, "metadata.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        _log(f"Metadata saved: {meta_path}")

        _log(f"Output: {OUTPUT_DIR}")
        _log(f"Settings: {RES_WIDTH}x{RES_HEIGHT}, settle={settle_frames} frames")
        _log(f"Rendering {len(enabled)} variants...")

        cur_time = cam_prim.GetAttribute("exposure:time").Get()
        _log(f"Camera exposure:time default = {cur_time}")

        HYDRA_SYNC_FRAMES = 60
        RESET_SETTLE_FRAMES = 10
        PRE_CAPTURE_FRAMES = 30
        convergence_frames = max(1, PATH_TRACE_SPP // SAMPLES_PER_ITERATION) + 20
        _log(f"  Convergence estimate: {convergence_frames} frames "
             f"(SPP={PATH_TRACE_SPP}/SPI={SAMPLES_PER_ITERATION} + 20)")

        for i, v in enumerate(enabled, 1):
            name = v["name"]
            exposure = v.get("exposure", 0.0001)
            _log(f"[{i}/{len(enabled)}] '{name}' (exposure:time={exposure})")

            # --- [Step 1-2] Variant switch + Hydra sync ---
            vset.SetVariantSelection(name)
            cam_prim.GetAttribute("exposure:time").Set(float(exposure))
            _log(f"  [Step 1-2] Variant set + Hydra sync "
                 f"({HYDRA_SYNC_FRAMES} frames)...")
            await _wait_frames(HYDRA_SYNC_FRAMES)

            # --- [Step 3] Reset accumulation ---
            settings.set_bool("/rtx/pathtracing/resetAccumulation", True)
            _log(f"  [Step 3] Reset accumulation + settle "
                 f"({RESET_SETTLE_FRAMES} frames)...")
            await _wait_frames(RESET_SETTLE_FRAMES)

            # --- [Step 4] Accumulate path tracing samples ---
            _log(f"  [Step 4] Accumulating {convergence_frames} frames...")
            t0 = time.time()
            for frame in range(convergence_frames):
                await app.next_update_async()
                if (frame + 1) % 100 == 0:
                    _log(f"    ... {frame+1}/{convergence_frames} frames "
                         f"({time.time()-t0:.0f}s)")
            accum_time = time.time() - t0
            _log(f"  [Step 4] Accumulation done ({accum_time:.1f}s)")

            # --- Pre-capture drain: flush GPU pipeline ---
            _log(f"  [Step 4→5] Pre-capture drain "
                 f"({PRE_CAPTURE_FRAMES} frames)...")
            await _wait_frames(PRE_CAPTURE_FRAMES)

            # --- [Step 5] Initiate capture ---
            output_path = os.path.join(OUTPUT_DIR, f"{name}.png")
            if os.path.exists(output_path):
                os.remove(output_path)

            capture_viewport_to_file(viewport_api, file_path=output_path)
            _log("  [Step 5] capture_viewport_to_file() called")

            # --- [Step 6] GPU readback ---
            rc = omni.kit.renderer_capture.acquire_renderer_capture_interface()
            rc.wait_async_capture()
            _log("  [Step 6] wait_async_capture() returned")

            # --- [Step 7-8] MUST wait until file is fully on disk ---
            # Root cause of tearing: shared readback buffer gets overwritten
            # by next capture if PNG encoding hasn't finished yet.
            # Use TIME-based timeout (not frame-based) to guarantee completion.
            FILE_TIMEOUT_SEC = 120
            STABLE_THRESHOLD = 10
            poll_start = time.time()
            prev_size = -1
            stable_count = 0
            poll_frames = 0
            while (time.time() - poll_start) < FILE_TIMEOUT_SEC:
                await app.next_update_async()
                poll_frames += 1
                if os.path.exists(output_path):
                    cur_size = os.path.getsize(output_path)
                    if cur_size > 0 and cur_size == prev_size:
                        stable_count += 1
                        if stable_count >= STABLE_THRESHOLD:
                            break
                    else:
                        stable_count = 0
                    prev_size = cur_size

            poll_elapsed = time.time() - poll_start
            fsize = os.path.getsize(output_path) if os.path.exists(output_path) else 0

            if fsize == 0:
                _log(f"  WARNING: {name}.png NOT WRITTEN after "
                     f"{poll_elapsed:.1f}s ({poll_frames} frames)!")
            elif stable_count < STABLE_THRESHOLD:
                _log(f"  WARNING: {name}.png not stable after "
                     f"{poll_elapsed:.1f}s ({poll_frames} frames, "
                     f"size={fsize/1024:.0f}KB, stable={stable_count})")
            else:
                _log(f"  [Step 7] File written: {fsize/1024:.0f}KB "
                     f"in {poll_elapsed:.1f}s ({poll_frames} frames)")

            # --- Post-capture flush ---
            await _wait_frames(CAPTURE_FLUSH_FRAMES)

            elapsed = time.time() - t0
            _log(f"  [Step 8] Done: {name}.png ({elapsed:.1f}s, "
                 f"{fsize/1024:.0f}KB)")

        _log("All variants rendered. Exiting Kit.")

    except Exception as e:
        _log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if _log_file is not None:
            _log_file.close()

    app.post_quit()


asyncio.ensure_future(render_all_variants())
