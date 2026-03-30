"""
heightmap_to_blender.py: Convert height map + texture map pair to a Blender mesh.

Intended for synthetic / ground-truth data where the maps are pixel-accurate.
For experimental data with noise, use the interactive MCP workflow instead.

Usage (headless):
    blender -b --python heightmap_to_blender.py -- \\
        --height path/to/height.tif \\
        --texture path/to/texture.png \\
        --name my_specimen \\
        --pixel-pitch 0.01 \\
        --downsample 4

Usage (from MCP / script editor):
    exec(open("packages/blender_authoring/scripts/heightmap_to_blender.py").read())
    build_specimen_from_maps(
        height_path="blender_model_example/img_height.tif",
        texture_path="blender_model_example/img_max.png",
        name="pcb_board",
        pixel_pitch_mm=0.01,
        downsample=8,
    )
"""

import bpy
import bmesh
import numpy as np
import os
import sys


def build_specimen_from_maps(
    height_path: str,
    texture_path: str,
    name: str = "Specimen",
    pixel_pitch_mm: float = 0.01,
    downsample: int = 1,
    z_scale: float = 1.0,
    z_clip_sigma: float = 0.0,
) -> bpy.types.Object:
    """Build a textured mesh from height map + texture map.

    Args:
        height_path: Path to height map image (float TIFF, values in mm).
        texture_path: Path to texture image (RGB).
        name: Object name in Blender.
        pixel_pitch_mm: Physical size of one pixel in mm.
        downsample: Downsample factor (1 = full resolution).
        z_scale: Multiplier for height values.
        z_clip_sigma: If > 0, clip Z outliers beyond mean +/- sigma * std.

    Returns:
        The created Blender object.
    """

    # ---- Load height map via bpy ----
    height_img = bpy.data.images.load(height_path, check_existing=True)
    height_img.colorspace_settings.name = "Non-Color"
    W, H = height_img.size  # width, height in pixels

    all_px = np.array(height_img.pixels[:], dtype=np.float32).reshape(H, W, 4)
    height_full = all_px[:, :, 0]  # R channel, bottom-to-top (bpy convention)

    # Downsample
    hmap = height_full[::downsample, ::downsample]
    h, w = hmap.shape
    print(f"[heightmap] Original: {W}x{H}, Downsampled: {w}x{h} (factor {downsample})")
    print(f"[heightmap] Z range: {hmap.min():.3f} ~ {hmap.max():.3f} mm")

    # Apply z_scale
    hmap = hmap * z_scale

    # Optional outlier clipping
    if z_clip_sigma > 0:
        mean = hmap.mean()
        std = hmap.std()
        lo = mean - z_clip_sigma * std
        hi = mean + z_clip_sigma * std
        clipped = np.clip(hmap, lo, hi)
        n_clipped = int((hmap < lo).sum() + (hmap > hi).sum())
        hmap = clipped
        print(f"[heightmap] Clipped {n_clipped} outliers at {z_clip_sigma} sigma")

    # ---- Build mesh ----
    dx = downsample * pixel_pitch_mm
    dy = downsample * pixel_pitch_mm
    x_offset = (w - 1) * dx / 2
    y_offset = (h - 1) * dy / 2

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    for row in range(h):
        for col in range(w):
            x = col * dx - x_offset
            y = row * dy - y_offset
            z = float(hmap[row, col])
            bm.verts.new((x, y, z))

    bm.verts.ensure_lookup_table()

    for row in range(h - 1):
        for col in range(w - 1):
            i = row * w + col
            face = bm.faces.new([
                bm.verts[i],
                bm.verts[i + 1],
                bm.verts[i + 1 + w],
                bm.verts[i + w],
            ])
            # UV: grid position normalized to 0..1
            coords = [
                (col / (w - 1), row / (h - 1)),
                ((col + 1) / (w - 1), row / (h - 1)),
                ((col + 1) / (w - 1), (row + 1) / (h - 1)),
                (col / (w - 1), (row + 1) / (h - 1)),
            ]
            for loop, uv in zip(face.loops, coords):
                loop[uv_layer].uv = uv

    mesh = bpy.data.meshes.new(f"{name}Mesh")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    print(f"[heightmap] Mesh created: {w*h} verts, {(w-1)*(h-1)} faces")

    # ---- Material with texture ----
    tex_img = bpy.data.images.load(texture_path, check_existing=True)

    mat = bpy.data.materials.new(name=f"{name}_Material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.6

    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.image = tex_img
    tex_node.location = (-300, 300)
    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

    obj.data.materials.append(mat)

    # Smooth shading
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()

    print(f"[heightmap] Done: {name}")
    return obj


# ---- CLI entry point (headless) ----
if __name__ == "__main__" or (hasattr(bpy.app, "background") and bpy.app.background):
    argv = sys.argv
    if "--" in argv:
        import argparse

        args = argv[argv.index("--") + 1:]
        parser = argparse.ArgumentParser(description="Height map to Blender mesh")
        parser.add_argument("--height", required=True, help="Path to height map (.tif)")
        parser.add_argument("--texture", required=True, help="Path to texture map (.png)")
        parser.add_argument("--name", default="Specimen", help="Object/specimen name")
        parser.add_argument("--pixel-pitch", type=float, default=0.01, help="mm per pixel")
        parser.add_argument("--downsample", type=int, default=4, help="Downsample factor")
        parser.add_argument("--z-scale", type=float, default=1.0, help="Z multiplier")
        parser.add_argument("--z-clip-sigma", type=float, default=0.0, help="Clip outliers")
        parser.add_argument("--save", action="store_true", help="Save as specimen asset")
        opts = parser.parse_args(args)

        # Init scene
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.unit_settings.system = "METRIC"
        bpy.context.scene.unit_settings.scale_length = 0.001

        obj = build_specimen_from_maps(
            height_path=os.path.abspath(opts.height),
            texture_path=os.path.abspath(opts.texture),
            name=opts.name,
            pixel_pitch_mm=opts.pixel_pitch,
            downsample=opts.downsample,
            z_scale=opts.z_scale,
            z_clip_sigma=opts.z_clip_sigma,
        )

        if opts.save:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = script_dir
            for _ in range(10):
                if (os.path.exists(os.path.join(project_root, "pyproject.toml"))
                        and os.path.exists(os.path.join(project_root, "assets"))):
                    break
                project_root = os.path.dirname(project_root)

            scripts_dir = os.path.join(
                project_root, "packages", "blender_authoring", "scripts"
            )
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)

            from save_specimen import save_current_as_specimen
            save_current_as_specimen(name=opts.name)
