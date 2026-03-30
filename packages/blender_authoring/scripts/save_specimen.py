"""
save_specimen.py: Blender 내에서 실행하여 현재 scene을 specimen asset으로 저장

Usage (Blender Script Editor 또는 MCP에서):
    exec(open("packages/blender_authoring/scripts/save_specimen.py").read())

또는 recipe에서 import:
    from save_specimen import save_current_as_specimen
    save_current_as_specimen("my_specimen")
"""

import bpy
import os
import json
from datetime import datetime
from mathutils import Vector

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def _get_project_root() -> str:
    """프로젝트 루트 경로 탐색 (assets/ 디렉토리가 있는 pyproject.toml 기준)"""
    path = os.path.dirname(os.path.abspath(__file__))
    for _ in range(10):
        if (os.path.exists(os.path.join(path, "pyproject.toml"))
                and os.path.exists(os.path.join(path, "assets"))):
            return path
        path = os.path.dirname(path)
    raise FileNotFoundError("프로젝트 루트를 찾을 수 없습니다 (pyproject.toml + assets/ 필요)")


def _get_bounding_box_mm(obj) -> list[float]:
    """오브젝트의 world-space bounding box 크기 (mm 단위, Blender unit = mm 가정)"""
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    xs = [c.x for c in bbox_corners]
    ys = [c.y for c in bbox_corners]
    zs = [c.z for c in bbox_corners]
    return [
        round(max(xs) - min(xs), 4),
        round(max(ys) - min(ys), 4),
        round(max(zs) - min(zs), 4),
    ]


def save_current_as_specimen(
    name: str,
    origin: str = "center",
    material_description: str = "",
    output_dir: str | None = None,
) -> str:
    """현재 scene의 객체를 specimen asset으로 저장

    Args:
        name: specimen 이름 (디렉토리명 + 파일명에 사용)
        origin: "center" 또는 "bottom_center"
        material_description: material 요약 (사람 참고용)
        output_dir: 저장 경로 (None이면 assets/specimens/<name>/)

    Returns:
        manifest 파일 경로
    """
    # 저장 디렉토리 결정
    if output_dir is None:
        project_root = _get_project_root()
        output_dir = os.path.join(project_root, "assets", "specimens", name)
    os.makedirs(output_dir, exist_ok=True)

    # Mesh 오브젝트 수집
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not mesh_objects:
        raise ValueError("Scene에 mesh 오브젝트가 없습니다")

    # 여러 오브젝트가 있으면 하나로 join
    if len(mesh_objects) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in mesh_objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = mesh_objects[0]
        bpy.ops.object.join()

    # 오브젝트명 강제
    specimen = bpy.context.view_layer.objects.active
    if specimen is None:
        specimen = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"][0]
    specimen.name = "Specimen"
    if specimen.data:
        specimen.data.name = "Specimen"

    # Origin 설정
    bpy.ops.object.select_all(action="DESELECT")
    specimen.select_set(True)
    bpy.context.view_layer.objects.active = specimen
    if origin == "center":
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    elif origin == "bottom_center":
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
        # bottom_center: origin을 bbox 하단 중심으로 이동
        bbox_z_min = min(
            (specimen.matrix_world @ Vector(corner)).z
            for corner in specimen.bound_box
        )
        bbox_center = specimen.location.copy()
        offset = bbox_center.z - bbox_z_min
        specimen.location.z += offset

    # Bounding box 계산
    bounding_box_mm = _get_bounding_box_mm(specimen)

    # .blend 저장
    blend_path = os.path.join(output_dir, f"{name}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    # Manifest 생성
    manifest = {
        "format_version": "1.0",
        "asset_type": "specimen",
        "name": name,
        "blend_file": f"{name}.blend",
        "object_name": "Specimen",
        "bounding_box_mm": bounding_box_mm,
        "origin": origin,
        "material_description": material_description or "not specified",
        "created_by": "blender_authoring.specimen",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    manifest_path = os.path.join(output_dir, f"{name}.manifest.yaml")
    with open(manifest_path, "w", encoding="utf-8") as f:
        if HAS_YAML:
            yaml.dump(manifest, f, default_flow_style=False, allow_unicode=True)
        else:
            # Fallback: 간단한 YAML 직렬화 (PyYAML 없을 때)
            for key, value in manifest.items():
                if isinstance(value, list):
                    f.write(f"{key}: {json.dumps(value)}\n")
                elif isinstance(value, str):
                    f.write(f'{key}: "{value}"\n')
                else:
                    f.write(f"{key}: {value}\n")

    print(f"[save_specimen] Saved: {manifest_path}")
    return manifest_path


# ── Blender에서 직접 실행 시 ──
if __name__ == "__main__":
    import sys

    # headless에서 인자로 이름 전달: blender -b --python save_specimen.py -- my_name
    argv = sys.argv
    if "--" in argv:
        args = argv[argv.index("--") + 1 :]
        if args:
            save_current_as_specimen(args[0])
        else:
            print("Usage: blender -b scene.blend --python save_specimen.py -- <specimen_name>")
    else:
        print("Usage: blender -b scene.blend --python save_specimen.py -- <specimen_name>")
        print("  또는 Blender Script Editor에서: save_current_as_specimen('my_specimen')")
