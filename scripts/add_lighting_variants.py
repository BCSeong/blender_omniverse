"""Post-process exported USD file using a JSON config.

Applies stage settings, camera exposure, and lighting variant sets.

Usage:
    python scripts/add_lighting_variants.py <input.usdc> <config.json> [output.usdc]
    If output is omitted, overwrites input.
"""
import json
import sys
from pathlib import Path
from pxr import Gf, Usd, UsdGeom, UsdShade, Sdf



def remove_env_lights(stage, prim_paths):
    """Remove environment lights (e.g. Omniverse auto-generated DomeLight)."""
    removed = 0
    for path in prim_paths:
        prim = stage.GetPrimAtPath(path)
        if prim:
            stage.RemovePrim(path)
            removed += 1
            print(f"  removed: {path}")
        else:
            print(f"  not found (skip): {path}")
    print(f"  total removed: {removed}")


def apply_render_settings(stage, cfg):
    """Write RTX render settings (e.g. firefly clamp) into the root layer's
    customLayerData so Omniverse restores them when the stage is opened.

    Blender does not export these; this makes the validated render settings the
    reproducible default of the pipeline.
    """
    rl = stage.GetRootLayer()
    cld = dict(rl.customLayerData)
    rs = dict(cld.get("renderSettings", {}))
    for key, val in cfg.items():
        rs[key] = val
        print(f"  {key} = {val}")
    cld["renderSettings"] = rs
    rl.customLayerData = cld


def categorize_lights(stage, root_prim, groups_config):
    groups = {k: [] for k in groups_config}
    for prim in Usd.PrimRange(root_prim):
        name = prim.GetName()
        for group_key, prefix in groups_config.items():
            if name.startswith(prefix):
                groups[group_key].append(prim.GetPath())
                break
    return groups


def apply_stage_settings(stage, cfg):
    if "metersPerUnit" in cfg:
        UsdGeom.SetStageMetersPerUnit(stage, cfg["metersPerUnit"])
        print(f"  metersPerUnit: {cfg['metersPerUnit']}")
    if "upAxis" in cfg:
        UsdGeom.SetStageUpAxis(stage, cfg["upAxis"])
        print(f"  upAxis: {cfg['upAxis']}")


def apply_camera_settings(stage, cfg):
    prim = stage.GetPrimAtPath(cfg["primPath"])
    if not prim:
        print(f"  ERROR: camera prim not found at {cfg['primPath']}")
        return

    cam = UsdGeom.Camera(prim)

    direct_attrs = {
        "focalLength": cam.GetFocalLengthAttr,
        "horizontalAperture": cam.GetHorizontalApertureAttr,
        "verticalAperture": cam.GetVerticalApertureAttr,
        "fStop": cam.GetFStopAttr,
    }
    for key, getter in direct_attrs.items():
        if key in cfg:
            getter().Set(cfg[key])
            print(f"  {key}: {cfg[key]}")

    if "clippingRange" in cfg:
        r = cfg["clippingRange"]
        cam.GetClippingRangeAttr().Set(Gf.Vec2f(r[0], r[1]))
        print(f"  clippingRange: {r}")

    if "exposure" in cfg:
        for key, val in cfg["exposure"].items():
            attr_name = f"exposure:{key}"
            attr = prim.GetAttribute(attr_name)
            if attr:
                attr.Set(val)
            else:
                attr = prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Float)
                attr.Set(val)
            print(f"  {attr_name}: {val}")


def apply_light_properties(stage, root_prim, cfg):
    """Patch light attributes after Blender export.

    Blender exports SphereLights with narrow cone angles and no IES profiles.
    This function corrects them to match the validated Omniverse configuration.
    """
    defaults = cfg.get("defaults", {})
    overrides = cfg.get("groupOverrides", {})
    groups_config = cfg.get("groups", {})

    type_map = {
        bool: Sdf.ValueTypeNames.Bool,
        float: Sdf.ValueTypeNames.Float,
        str: Sdf.ValueTypeNames.Asset,
    }

    patched = 0
    group_counts = {}
    for prim in Usd.PrimRange(root_prim):
        if "Light" not in prim.GetTypeName():
            continue

        name = prim.GetName()
        matched_group = None
        for group_key, prefix in groups_config.items():
            if name.startswith(prefix):
                matched_group = group_key
                break

        attrs_to_set = dict(defaults)
        if matched_group and matched_group in overrides:
            attrs_to_set.update(overrides[matched_group])

        for attr_name, val in attrs_to_set.items():
            attr = prim.GetAttribute(attr_name)
            if isinstance(val, str) and attr_name.endswith(":file"):
                if attr:
                    attr.Set(Sdf.AssetPath(val))
                else:
                    prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Asset).Set(
                        Sdf.AssetPath(val))
            elif attr:
                attr.Set(val)
            else:
                sdf_type = type_map.get(type(val), Sdf.ValueTypeNames.Float)
                prim.CreateAttribute(attr_name, sdf_type).Set(val)

        patched += 1
        group_counts[matched_group or "other"] = group_counts.get(
            matched_group or "other", 0) + 1

    for g, c in sorted(group_counts.items()):
        grp_overrides = overrides.get(g, {})
        extra = f" + overrides: {grp_overrides}" if grp_overrides else ""
        print(f"  {g}: {c} lights{extra}")
    print(f"  defaults: {defaults}")
    print(f"  total patched: {patched}")


def apply_diffuser_material(stage, cfg):
    """Copy an OmniSurface material from a library USD and bind it to diffuser meshes.

    The material (e.g. tuned in Omniverse) is copied verbatim into the stage so the
    result is self-contained, then bound to every Mesh under any Xform whose name
    starts with one of the configured prefixes. This survives Blender re-exports
    because it runs after export.
    """
    lib_path = Path(cfg["libraryPath"])
    lib_layer = Sdf.Layer.FindOrOpen(str(lib_path))
    if not lib_layer:
        print(f"  ERROR: material library not found at {lib_path}")
        return

    src_prim = cfg["sourcePrim"]
    dst_prim = cfg["targetPath"]
    Sdf.CopySpec(lib_layer, Sdf.Path(src_prim), stage.GetRootLayer(), Sdf.Path(dst_prim))
    material = UsdShade.Material(stage.GetPrimAtPath(dst_prim))
    print(f"  material: {dst_prim} (from {lib_path}:{src_prim})")

    prefixes = tuple(cfg.get("bindToXformPrefixes", ["optical_diffuser"]))
    bound = []
    for prim in stage.Traverse():
        if prim.GetTypeName() == "Xform" and prim.GetName().startswith(prefixes):
            for d in Usd.PrimRange(prim):
                if d.GetTypeName() == "Mesh":
                    UsdShade.MaterialBindingAPI(d).Bind(material)
                    bound.append(d.GetPath().pathString)
    print(f"  bound to {len(bound)} diffuser mesh(es):")
    for b in bound:
        print(f"    {b}")


def apply_lighting_variants(stage, root_prim, cfg):
    light_groups = categorize_lights(stage, root_prim, cfg["groups"])
    for k, paths in light_groups.items():
        print(f"  {k}: {len(paths)} lights")

    vset_name = cfg["variantSetName"]
    vset = root_prim.GetVariantSets().AddVariantSet(vset_name)

    for variant_name, variant_cfg in cfg["variants"].items():
        visible_groups = variant_cfg["lights"]

        vset.AddVariant(variant_name)
        vset.SetVariantSelection(variant_name)

        with vset.GetVariantEditContext():
            for group_key, paths in light_groups.items():
                vis = "inherited" if group_key in visible_groups else "invisible"
                for path in paths:
                    prim = stage.GetPrimAtPath(path)
                    UsdGeom.Imageable(prim).GetVisibilityAttr().Set(vis)

        print(f"  variant '{variant_name}': lights={visible_groups}")

    default = cfg.get("defaultVariant", "all")
    vset.SetVariantSelection(default)
    print(f"  default: '{default}'")


def process_usd(input_path, config_path, output_path=None):
    if output_path is None:
        output_path = input_path

    with open(config_path, "r") as f:
        config = json.load(f)

    stage = Usd.Stage.Open(str(input_path))
    root_path = config.get("stage", {}).get("rootPrimPath", "/root")
    root_prim = stage.GetPrimAtPath(root_path)
    if not root_prim:
        print(f"ERROR: root prim not found at {root_path}")
        return

    if "stage" in config:
        print("[stage]")
        apply_stage_settings(stage, config["stage"])

    if "camera" in config:
        print("[camera]")
        apply_camera_settings(stage, config["camera"])

    if "removeEnvLights" in config:
        print("[removeEnvLights]")
        remove_env_lights(stage, config["removeEnvLights"])

    if "diffuserMaterial" in config:
        print("[diffuserMaterial]")
        apply_diffuser_material(stage, config["diffuserMaterial"])

    if "renderSettings" in config:
        print("[renderSettings]")
        apply_render_settings(stage, config["renderSettings"])

    if "lightProperties" in config:
        print("[lightProperties]")
        apply_light_properties(stage, root_prim, config["lightProperties"])

    if "lightingVariants" in config:
        print("[lightingVariants]")
        apply_lighting_variants(stage, root_prim, config["lightingVariants"])

    stage.GetRootLayer().Save()
    if str(output_path) != str(input_path):
        stage.GetRootLayer().Export(str(output_path))

    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <input.usdc> <config.json> [output.usdc]")
        sys.exit(1)

    inp = Path(sys.argv[1])
    cfg = Path(sys.argv[2])
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    process_usd(inp, cfg, out)
