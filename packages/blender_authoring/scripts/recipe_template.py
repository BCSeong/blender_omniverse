"""
Specimen Recipe: <SPECIMEN_NAME>
Description: <간단한 설명>
Unit: mm (1 Blender unit = 1 mm)
Created: <YYYY-MM-DD>

재현 방법:
    blender -b --python <this_file>.py
"""

import bpy
import os
import sys

# ━━ 설정 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SPECIMEN_NAME = "template_specimen"
ORIGIN = "center"  # "center" 또는 "bottom_center"
MATERIAL_DESCRIPTION = "기본 회색 diffuse"


# ━━ 1. Scene 초기화 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bpy.ops.wm.read_factory_settings(use_empty=True)
# 단위를 mm로 설정
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 0.001  # 1 unit = 1 mm


# ━━ 2. 시편 생성 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 여기에 bpy 코드를 작성합니다.
# 예시: 10mm x 10mm x 1mm 판
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
obj = bpy.context.active_object
obj.scale = (10, 10, 1)
bpy.ops.object.transform_apply(scale=True)

# Material 예시
mat = bpy.data.materials.new(name="SpecimenMaterial")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
obj.data.materials.append(mat)


# ━━ 3. 저장 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# headless 실행 시 자동 저장
if bpy.app.background:
    # 프로젝트 루트 찾기
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = script_dir
    for _ in range(10):
        if os.path.exists(os.path.join(project_root, "pyproject.toml")):
            break
        project_root = os.path.dirname(project_root)

    # save_specimen.py를 sys.path에 추가
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
