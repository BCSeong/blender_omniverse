"""Headless Blender USD export.

Opens .blend file and exports to .usdc with settings matching v004 pipeline.
Run via: blender -b <file.blend> --python export_usd.py -- <output.usdc>

Arguments after '--' are passed to the script:
  output_path: path to write .usdc (required)
"""
import sys
import bpy

argv = sys.argv
if "--" in argv:
    script_args = argv[argv.index("--") + 1:]
else:
    script_args = []

if not script_args:
    print("Usage: blender -b file.blend --python export_usd.py -- output.usdc")
    sys.exit(1)

output_path = script_args[0]

print(f"[export_usd] Exporting to: {output_path}")

bpy.ops.wm.usd_export(
    filepath=output_path,
    selected_objects_only=False,
    visible_objects_only=False,
    export_animation=False,
    export_hair=False,
    export_uvmaps=True,
    export_normals=True,
    export_materials=True,
    export_textures=False,
    relative_paths=True,
)

print(f"[export_usd] Done: {output_path}")
