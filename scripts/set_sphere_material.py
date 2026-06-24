"""Switch ChromeMirrorClean shader between methods for feasibility test.

Usage:
  python set_sphere_material.py M1       # Custom MDL (DustyMirror.mdl)
  python set_sphere_material.py M2       # OmniSurface coat with texture
  python set_sphere_material.py M3       # OmniSurfaceBlend (two sub-materials)
  python set_sphere_material.py M4       # Volume scatter (DustyVolume.mdl)
  python set_sphere_material.py D31-5B   # OmniPBR roughness scatter (best)
  python set_sphere_material.py D32      # OmniPBR_ClearCoat (reference)
  python set_sphere_material.py M1 path/to/file.usdc  # optional USD path
"""
import sys
from pxr import Usd, Sdf, UsdShade

USD_PATH = "assets/scenes/LOTA_PROD_0408/v005/lota-16m10-v3-rev2_v005.usdc"
SHADER_PATH = "/root/_materials/ChromeMirrorClean/Shader"
MATERIAL_PATH = "/root/_materials/ChromeMirrorClean"
TEX_DIR = "./textures"


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
    "coat_weight", "coat_weight_image", "coat_roughness", "coat_roughness_image", "coat_ior",
    "blend_weight", "blend_weight_image",
    "base_material", "blend_material",
    "scatter_density", "scatter_color", "scatter_anisotropy", "dust_fraction",
    "oxide_strength", "oxide_thickness_texture", "oxide_thickness_influence",
]

SUB_PRIM_NAMES = ["MirrorBase", "HazyBlend"]


def clear_inputs(shader, names):
    for name in names:
        inp = shader.GetInput(name)
        if inp and inp.GetAttr().IsAuthored():
            inp.GetAttr().Clear()


def cleanup_sub_prims(stage):
    """Remove M3 sub-material prims if they exist."""
    for name in SUB_PRIM_NAMES:
        path = f"{MATERIAL_PATH}/{name}"
        prim = stage.GetPrimAtPath(path)
        if prim and prim.IsValid():
            stage.RemovePrim(path)
            print(f"  Removed sub-prim: {path}")


def set_m1(shader, stage=None):
    """M1: Custom MDL - weighted_layer with dust texture."""
    clear_inputs(shader, ALL_KNOWN_INPUTS)
    if stage:
        cleanup_sub_prims(stage)

    shader.SetSourceAsset(Sdf.AssetPath("./DustyMirror.mdl"), "mdl")
    shader.SetSourceAssetSubIdentifier("DustyMirror", "mdl")

    shader.CreateInput("base_color", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    shader.CreateInput("dust_weight_constant", Sdf.ValueTypeNames.Float).Set(0.04)
    shader.CreateInput("dust_weight_texture", Sdf.ValueTypeNames.Asset).Set(
        f"{TEX_DIR}/sphere_M1_dust_weight.png")
    shader.CreateInput("dust_weight_texture_influence", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("dust_roughness", Sdf.ValueTypeNames.Float).Set(0.10)
    shader.CreateInput("dust_scatter_color", Sdf.ValueTypeNames.Color3f).Set((1.0, 1.0, 1.0))

    shader.CreateInput("oxide_strength", Sdf.ValueTypeNames.Float).Set(0.0045)
    shader.CreateInput("oxide_thickness_texture", Sdf.ValueTypeNames.Asset).Set(
        f"{TEX_DIR}/sphere_M1_oxide.png")
    shader.CreateInput("oxide_thickness_influence", Sdf.ValueTypeNames.Float).Set(1.0)

    print("M1: Custom DustyMirror.mdl")
    print("  weighted_layer(weight=dust_texture, layer=scatter, base=mirror)")
    print("  oxide thin-film absorption: strength=0.0045")


def set_m2(shader, stage=None):
    """M2: OmniSurface with coat_weight_image texture."""
    clear_inputs(shader, ALL_KNOWN_INPUTS)
    if stage:
        cleanup_sub_prims(stage)

    shader.SetSourceAsset(Sdf.AssetPath("OmniSurface.mdl"), "mdl")
    shader.SetSourceAssetSubIdentifier("OmniSurface", "mdl")

    # Base: metallic mirror
    shader.CreateInput("metalness", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("diffuse_reflection_weight", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("diffuse_reflection_color", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    shader.CreateInput("specular_reflection_weight", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("specular_reflection_roughness", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("specular_reflection_color", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))

    # Coat: dust haze with texture
    shader.CreateInput("coat_weight", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("coat_weight_image", Sdf.ValueTypeNames.Asset).Set(
        f"{TEX_DIR}/sphere_D32_dust_weight.png")
    shader.CreateInput("coat_roughness", Sdf.ValueTypeNames.Float).Set(0.4)
    shader.CreateInput("coat_ior", Sdf.ValueTypeNames.Float).Set(1.5)

    print("M2: OmniSurface.mdl")
    print("  base: metallic=1.0, roughness=0.0 (perfect mirror)")
    print("  coat: weight=texture, roughness=0.4, IOR=1.5")


def set_m3(shader, stage=None):
    """M3: OmniSurfaceBlend - mirror + hazy material blend with sub-prims."""
    clear_inputs(shader, ALL_KNOWN_INPUTS)

    shader.SetSourceAsset(Sdf.AssetPath("OmniSurfaceBlend.mdl"), "mdl")
    shader.SetSourceAssetSubIdentifier("OmniSurfaceBlend", "mdl")

    if stage is None:
        print("M3: ERROR - stage required for sub-material prim creation")
        return

    cleanup_sub_prims(stage)

    # Sub-shader 1: mirror base (OmniPBR, metallic=1, roughness=0)
    mirror_path = f"{MATERIAL_PATH}/MirrorBase"
    mirror_prim = stage.DefinePrim(mirror_path, "Shader")
    mirror_sh = UsdShade.Shader(mirror_prim)
    mirror_sh.SetSourceAsset(Sdf.AssetPath("OmniPBR.mdl"), "mdl")
    mirror_sh.SetSourceAssetSubIdentifier("OmniPBR", "mdl")
    mirror_sh.CreateInput("metallic_constant", Sdf.ValueTypeNames.Float).Set(1.0)
    mirror_sh.CreateInput("reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.0)
    mirror_sh.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    mirror_out = mirror_sh.CreateOutput("out", Sdf.ValueTypeNames.Token)

    # Sub-shader 2: hazy blend (OmniPBR, metallic=1, roughness=0.4)
    hazy_path = f"{MATERIAL_PATH}/HazyBlend"
    hazy_prim = stage.DefinePrim(hazy_path, "Shader")
    hazy_sh = UsdShade.Shader(hazy_prim)
    hazy_sh.SetSourceAsset(Sdf.AssetPath("OmniPBR.mdl"), "mdl")
    hazy_sh.SetSourceAssetSubIdentifier("OmniPBR", "mdl")
    hazy_sh.CreateInput("metallic_constant", Sdf.ValueTypeNames.Float).Set(1.0)
    hazy_sh.CreateInput("reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.4)
    hazy_sh.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    hazy_out = hazy_sh.CreateOutput("out", Sdf.ValueTypeNames.Token)

    # Connect sub-materials to OmniSurfaceBlend inputs
    base_inp = shader.CreateInput("base_material", Sdf.ValueTypeNames.Token)
    base_inp.ConnectToSource(mirror_out)
    blend_inp = shader.CreateInput("blend_material", Sdf.ValueTypeNames.Token)
    blend_inp.ConnectToSource(hazy_out)

    # Blend weight: dust density texture
    shader.CreateInput("blend_weight", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("blend_weight_image", Sdf.ValueTypeNames.Asset).Set(
        f"{TEX_DIR}/sphere_D32_dust_weight.png")

    print("M3: OmniSurfaceBlend.mdl")
    print(f"  base_material -> {mirror_path} (OmniPBR mirror)")
    print(f"  blend_material -> {hazy_path} (OmniPBR hazy)")
    print("  blend_weight_image: dust density texture")


def set_m4(shader, stage=None):
    """M4: Volume scatter (DustyVolume.mdl). Requires ptvol enabled."""
    clear_inputs(shader, ALL_KNOWN_INPUTS)
    if stage:
        cleanup_sub_prims(stage)

    shader.SetSourceAsset(Sdf.AssetPath("./DustyVolume.mdl"), "mdl")
    shader.SetSourceAssetSubIdentifier("DustyVolume", "mdl")

    shader.CreateInput("base_color", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    shader.CreateInput("dust_fraction", Sdf.ValueTypeNames.Float).Set(0.05)
    shader.CreateInput("scatter_density", Sdf.ValueTypeNames.Float).Set(100.0)
    shader.CreateInput("scatter_color", Sdf.ValueTypeNames.Color3f).Set((1.0, 1.0, 1.0))
    shader.CreateInput("scatter_anisotropy", Sdf.ValueTypeNames.Float).Set(0.0)

    print("M4: DustyVolume.mdl (volume scatter)")
    print("  surface: 95% mirror + 5% transmit")
    print("  volume: scatter_density=100, isotropic")
    print("  NOTE: Requires ptvol_enabled=true in render_config.json")


def set_d31_5b(shader, stage=None):
    """D31-5b: OmniPBR + roughness scatter (best result)."""
    clear_inputs(shader, ALL_KNOWN_INPUTS)
    if stage:
        cleanup_sub_prims(stage)

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

    print("D31-5b: OmniPBR.mdl (roughness scatter, best result)")
    print("  metallic: 0.95, texture=sphere_D31-5_metallic.png, influence=1.0")
    print("  roughness: 0.015, texture=sphere_D31-5_rough.png, influence=0.5")
    print("  diffuse_color: (0.8, 0.8, 0.8)")


def set_d32(shader, stage=None):
    """D32: OmniPBR_ClearCoat (current reference)."""
    clear_inputs(shader, ALL_KNOWN_INPUTS)
    if stage:
        cleanup_sub_prims(stage)

    shader.SetSourceAsset(Sdf.AssetPath("OmniPBR_ClearCoat.mdl"), "mdl")
    shader.SetSourceAssetSubIdentifier("OmniPBR_ClearCoat", "mdl")

    shader.CreateInput("metallic_constant", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("metallic_texture_influence", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("reflection_roughness_texture_influence", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set((0.8, 0.8, 0.8))
    shader.CreateInput("enable_clearcoat", Sdf.ValueTypeNames.Bool).Set(True)
    shader.CreateInput("clearcoat_weight", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("clearcoat_reflection_roughness", Sdf.ValueTypeNames.Float).Set(0.4)
    shader.CreateInput("clearcoat_ior", Sdf.ValueTypeNames.Float).Set(1.5)

    print("D32: OmniPBR_ClearCoat.mdl (reference: no spatial variation)")
    print("  base: metallic=1.0, roughness=0.0")
    print("  coat: uniform weight=1.0, roughness=0.4, IOR=1.5")


if __name__ == "__main__":
    method = sys.argv[1] if len(sys.argv) > 1 else "M1"
    usd_path = sys.argv[2] if len(sys.argv) > 2 else USD_PATH

    stage = Usd.Stage.Open(usd_path)
    shader = UsdShade.Shader.Get(stage, SHADER_PATH)

    if not shader.GetPrim().IsValid():
        # Fresh Blender export uses Principled_BSDF — rename to Shader
        blender_path = MATERIAL_PATH + "/Principled_BSDF"
        blender_prim = stage.GetPrimAtPath(blender_path)
        if blender_prim and blender_prim.IsValid():
            # Remove all Blender shader children and create clean Shader prim
            mat_prim = stage.GetPrimAtPath(MATERIAL_PATH)
            for child in list(mat_prim.GetAllChildren()):
                stage.RemovePrim(child.GetPath())
                print(f"  Removed Blender prim: {child.GetPath()}")
            shader_prim = stage.DefinePrim(SHADER_PATH, "Shader")
            shader = UsdShade.Shader(shader_prim)
            # Re-bind material outputs
            mat = UsdShade.Material(mat_prim)
            mat.CreateSurfaceOutput("mdl").ConnectToSource(
                UsdShade.ConnectableAPI(shader_prim), "out")
            print(f"  Created fresh Shader prim at {SHADER_PATH}")
        else:
            print(f"ERROR: No shader found at {SHADER_PATH} or {blender_path}")
            sys.exit(1)

    dispatch = {
        "M1": set_m1, "M2": set_m2, "M3": set_m3, "M4": set_m4,
        "D31-5B": set_d31_5b, "D32": set_d32,
    }
    if method.upper() not in dispatch:
        print(f"Unknown method: {method}. Use M1, M2, M3, M4, D31-5B, or D32")
        sys.exit(1)

    dispatch[method.upper()](shader, stage=stage)
    stage.GetRootLayer().Save()
    print(f"\nUSD saved: {usd_path}")
