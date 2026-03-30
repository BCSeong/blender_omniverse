"""
Specimen Recipe: checkerboard_10mm
Description: 10mm x 10mm 흑백 체커보드 캘리브레이션 타겟 (5x5 grid, 2mm squares)
Unit: mm (1 Blender unit = 1 mm)
Created: 2026-03-30

재현 방법:
    blender -b --python assets/specimens/checkerboard_10mm/checkerboard_10mm.recipe.py
"""

import bpy
import os
import sys

# ━━ 설정 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SPECIMEN_NAME = "checkerboard_10mm"
ORIGIN = "center"
MATERIAL_DESCRIPTION = "5x5 checkerboard, white (0.9) + black (0.05), PBR diffuse, roughness 0.8"

BOARD_SIZE = 10.0       # mm
SQUARES = 5             # 5x5 grid
SQUARE_SIZE = BOARD_SIZE / SQUARES  # 2mm per square
THICKNESS = 0.5         # mm
CHECKER_HEIGHT = 0.01   # z-fighting 방지용 미세 돌출


# ━━ 1. Scene 초기화 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 0.001


# ━━ 2. 시편 생성 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 베이스 플레이트 (흰색)
bpy.ops.mesh.primitive_plane_add(size=BOARD_SIZE, location=(0, 0, 0))
base = bpy.context.active_object
base.name = "CheckerBase"

# 두께 부여
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, THICKNESS)})
bpy.ops.object.mode_set(mode="OBJECT")

# 흰색 material
mat_white = bpy.data.materials.new(name="White")
mat_white.use_nodes = True
bsdf_w = mat_white.node_tree.nodes["Principled BSDF"]
bsdf_w.inputs["Base Color"].default_value = (0.9, 0.9, 0.9, 1.0)
bsdf_w.inputs["Roughness"].default_value = 0.8
base.data.materials.append(mat_white)

# 검정 material
mat_black = bpy.data.materials.new(name="Black")
mat_black.use_nodes = True
bsdf_b = mat_black.node_tree.nodes["Principled BSDF"]
bsdf_b.inputs["Base Color"].default_value = (0.05, 0.05, 0.05, 1.0)
bsdf_b.inputs["Roughness"].default_value = 0.8

# 체커보드 패턴: 검정 칸
half = BOARD_SIZE / 2
for row in range(SQUARES):
    for col in range(SQUARES):
        if (row + col) % 2 == 1:
            x = -half + SQUARE_SIZE * (col + 0.5)
            y = -half + SQUARE_SIZE * (row + 0.5)
            z = THICKNESS + CHECKER_HEIGHT

            bpy.ops.mesh.primitive_plane_add(size=SQUARE_SIZE, location=(x, y, z))
            sq = bpy.context.active_object
            sq.name = f"Black_{row}_{col}"
            sq.data.materials.append(mat_black)

# 모든 오브젝트를 하나로 합치기
bpy.ops.object.select_all(action="SELECT")
bpy.context.view_layer.objects.active = bpy.data.objects["CheckerBase"]
bpy.ops.object.join()

# 이름 설정
specimen = bpy.context.active_object
specimen.name = "Specimen"
specimen.data.name = "Specimen"

# Origin 설정
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")


# ━━ 3. 저장 (headless 실행 시 자동) ━━━━━━━━━━━━━━
if bpy.app.background:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = script_dir
    for _ in range(10):
        if os.path.exists(os.path.join(project_root, "pyproject.toml")):
            break
        project_root = os.path.dirname(project_root)

    scripts_dir = os.path.join(
        project_root, "packages", "blender_authoring", "scripts"
    )
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    from save_specimen import save_current_as_specimen

    save_current_as_specimen(
        name=SPECIMEN_NAME,
        origin=ORIGIN,
        material_description=MATERIAL_DESCRIPTION,
    )
