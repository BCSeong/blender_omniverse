"""
pcb_assembler.py: Generate parametric 3D components and place them on a PCB.

Usage (from Blender MCP):
    import sys
    sys.path.insert(0, r"<PROJECT_ROOT>/packages/blender_authoring/scripts")
    from pcb_assembler import assemble_pcb
    assemble_pcb(r"<path_to_csv>")

Each component family has a parametric generator that creates geometry
based on parsed dimensions from the CSV component name.
"""

import bpy
import bmesh
import math
from mathutils import Vector, Euler


# ─── Material cache ────────────────────────────────────────────────

_materials = {}


def _get_material(name, base_color, metallic=0.0, roughness=0.5):
    """Get or create a cached material."""
    if name in _materials:
        return _materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    _materials[name] = mat
    return mat


def mat_body_dark():
    return _get_material("PKG_Body_Dark", (0.03, 0.03, 0.04, 1), 0.0, 0.85)

def mat_body_beige():
    return _get_material("PKG_Body_Beige", (0.55, 0.45, 0.30, 1), 0.0, 0.7)

def mat_body_brown():
    return _get_material("PKG_Body_Brown", (0.25, 0.15, 0.08, 1), 0.0, 0.6)

def mat_body_green():
    return _get_material("PKG_Body_Green", (0.08, 0.20, 0.08, 1), 0.0, 0.6)

def mat_lead():
    return _get_material("PKG_Lead_Metal", (0.75, 0.72, 0.68, 1), 0.95, 0.25)

def mat_cap_aluminum():
    return _get_material("PKG_Cap_Aluminum", (0.6, 0.6, 0.6, 1), 0.85, 0.35)

def mat_tant_orange():
    return _get_material("PKG_Tant_Orange", (0.8, 0.4, 0.1, 1), 0.0, 0.5)

def mat_pcb():
    return _get_material("PCB_Board", (0.0, 0.25, 0.08, 1), 0.0, 0.7)

def mat_melf():
    return _get_material("PKG_MELF_Body", (0.15, 0.10, 0.05, 1), 0.0, 0.5)


# ─── Generators ─────────────────────────────────────────────────────

def gen_chip(name, l, w, h, **kw):
    """Chip resistor/capacitor: simple box with terminal bands."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (l, w, h)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat_body_beige())

    # Terminal bands (two end caps)
    band_w = l * 0.15
    for sign in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1,
            location=(sign * (l / 2 - band_w / 2), 0, h / 2))
        band = bpy.context.active_object
        band.name = f"{name}_term"
        band.scale = (band_w, w + 0.02, h + 0.02)
        bpy.ops.object.transform_apply(scale=True)
        band.data.materials.append(mat_lead())
        band.parent = obj

    return obj


def gen_melf(name, l, w, h, **kw):
    """MELF: cylindrical body with metal end caps."""
    radius = min(w, h) / 2
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16, radius=radius, depth=l,
        location=(0, 0, radius), rotation=(0, math.pi / 2, 0))
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat_melf())

    # End caps
    cap_len = l * 0.12
    for sign in (-1, 1):
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=16, radius=radius + 0.02, depth=cap_len,
            location=(sign * (l / 2 - cap_len / 2), 0, radius),
            rotation=(0, math.pi / 2, 0))
        cap = bpy.context.active_object
        cap.name = f"{name}_cap"
        cap.data.materials.append(mat_lead())
        cap.parent = obj

    return obj


def gen_tant(name, l, w, h, **kw):
    """Tantalum capacitor: rounded box with polarity band."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (l, w, h)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat_tant_orange())

    # Polarity band on one end
    band_w = l * 0.12
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(-l / 2 + band_w / 2, 0, h / 2))
    band = bpy.context.active_object
    band.name = f"{name}_pol"
    band.scale = (band_w, w + 0.01, h + 0.01)
    bpy.ops.object.transform_apply(scale=True)
    band.data.materials.append(mat_lead())
    band.parent = obj

    return obj


def gen_alcap(name, l, w, h, **kw):
    """Aluminum electrolytic capacitor: cylinder."""
    radius = l / 2
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=24, radius=radius, depth=h,
        location=(0, 0, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat_cap_aluminum())

    # Top scoring line (K-mark)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=24, radius=radius - 0.2, depth=0.05,
        location=(0, 0, h + 0.01))
    top = bpy.context.active_object
    top.name = f"{name}_top"
    top.data.materials.append(mat_body_dark())
    top.parent = obj

    return obj


def gen_sot(name, l, w, h, pin_count=3, **kw):
    """SOT package: small body with gull-wing leads."""
    # Body
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (l, w, h)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat_body_dark())

    # Simple leads as small boxes
    lead_h = 0.1
    lead_w = 0.25
    lead_ext = 0.3  # extension beyond body

    if pin_count == 3:
        # 2 pins on one side, 1 on other
        positions = [
            (-l * 0.25, -(w / 2 + lead_ext / 2), lead_h / 2),
            (l * 0.25, -(w / 2 + lead_ext / 2), lead_h / 2),
            (0, (w / 2 + lead_ext / 2), lead_h / 2),
        ]
    else:
        # Dual-row: split pins evenly
        n_side = pin_count // 2
        rest = pin_count % 2
        positions = []
        spacing = l * 0.7 / max(n_side - 1, 1)
        start_x = -l * 0.35
        for i in range(n_side):
            x = start_x + i * spacing
            positions.append((x, -(w / 2 + lead_ext / 2), lead_h / 2))
        for i in range(n_side + rest):
            x = start_x + i * spacing if (n_side + rest) > 1 else 0
            positions.append((x, (w / 2 + lead_ext / 2), lead_h / 2))

    for i, pos in enumerate(positions):
        bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
        lead = bpy.context.active_object
        lead.name = f"{name}_lead{i}"
        lead.scale = (lead_w, lead_ext, lead_h)
        bpy.ops.object.transform_apply(scale=True)
        lead.data.materials.append(mat_lead())
        lead.parent = obj

    return obj


def gen_sod(name, l, w, h, **kw):
    """SOD diode: small body with polarity band and 2 leads."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (l, w, h)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat_body_dark())

    # Cathode band
    band_w = l * 0.1
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(-l / 2 + l * 0.2, 0, h / 2))
    band = bpy.context.active_object
    band.name = f"{name}_cathode"
    band.scale = (band_w, w + 0.01, h + 0.01)
    bpy.ops.object.transform_apply(scale=True)
    band.data.materials.append(mat_lead())
    band.parent = obj

    return obj


def gen_soic(name, l, w, h, pin_count=8, pitch=1.27, **kw):
    """SOIC/SSOP/TSSOP: body with gull-wing leads on two sides."""
    # Body
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (l, w, h)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat_body_dark())

    # Leads on +Y and -Y sides
    n_side = pin_count // 2
    lead_w = pitch * 0.4
    lead_ext = 0.6
    lead_h = 0.15

    for side in (-1, 1):
        for i in range(n_side):
            x = (i - (n_side - 1) / 2) * pitch
            y = side * (w / 2 + lead_ext / 2)
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, lead_h / 2))
            lead = bpy.context.active_object
            lead.name = f"{name}_lead"
            lead.scale = (lead_w, lead_ext, lead_h)
            bpy.ops.object.transform_apply(scale=True)
            lead.data.materials.append(mat_lead())
            lead.parent = obj

    # Pin 1 dot
    bpy.ops.mesh.primitive_circle_add(
        vertices=8, radius=0.2, fill_type='NGON',
        location=(-l / 2 + 0.5, -w / 2 + 0.5, h + 0.01))
    dot = bpy.context.active_object
    dot.name = f"{name}_pin1"
    dot.data.materials.append(mat_lead())
    dot.parent = obj

    return obj


def gen_qfp(name, l, w, h, pin_count=100, pitch=0.5, **kw):
    """QFP: body with gull-wing leads on 4 sides."""
    body_half_l = l / 2
    body_half_w = w / 2

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (l, w, h)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat_body_dark())

    pins_per_side = pin_count // 4
    lead_w = pitch * 0.45
    lead_ext = 0.8
    lead_h = 0.12

    for side in range(4):
        for i in range(pins_per_side):
            offset = (i - (pins_per_side - 1) / 2) * pitch

            if side == 0:    # bottom (-Y)
                x, y = offset, -(body_half_w + lead_ext / 2)
            elif side == 1:  # right (+X)
                x, y = (body_half_l + lead_ext / 2), offset
            elif side == 2:  # top (+Y)
                x, y = -offset, (body_half_w + lead_ext / 2)
            else:            # left (-X)
                x, y = -(body_half_l + lead_ext / 2), -offset

            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, lead_h / 2))
            lead = bpy.context.active_object
            lead.name = f"{name}_lead"

            if side in (0, 2):
                lead.scale = (lead_w, lead_ext, lead_h)
            else:
                lead.scale = (lead_ext, lead_w, lead_h)

            bpy.ops.object.transform_apply(scale=True)
            lead.data.materials.append(mat_lead())
            lead.parent = obj

    return obj


def gen_qfn(name, l, w, h, pin_count=24, pitch=0.5, **kw):
    """QFN/LGA: body with bottom pads (visible as edge pads)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (l, w, h)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat_body_dark())

    # Edge pads (visible from side)
    pins_per_side = pin_count // 4
    pad_w = pitch * 0.4
    pad_ext = 0.2  # tiny edge exposure
    pad_h = 0.1

    for side in range(4):
        for i in range(pins_per_side):
            offset = (i - (pins_per_side - 1) / 2) * pitch
            if side == 0:
                x, y = offset, -(w / 2 - pad_ext / 2)
            elif side == 1:
                x, y = (l / 2 - pad_ext / 2), offset
            elif side == 2:
                x, y = -offset, (w / 2 - pad_ext / 2)
            else:
                x, y = -(l / 2 - pad_ext / 2), -offset

            bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, pad_h / 2))
            pad = bpy.context.active_object
            pad.name = f"{name}_pad"
            if side in (0, 2):
                pad.scale = (pad_w, pad_ext, pad_h)
            else:
                pad.scale = (pad_ext, pad_w, pad_h)
            bpy.ops.object.transform_apply(scale=True)
            pad.data.materials.append(mat_lead())
            pad.parent = obj

    return obj


def gen_bga(name, l, w, h, pin_count=48, pitch=0.8, **kw):
    """BGA: body with ball array on bottom (top is just a dark package)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (l, w, h)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat_body_dark())
    return obj


def gen_misc(name, l, w, h, **kw):
    """Generic box for unrecognized components."""
    if l <= 0:
        l = 2.0
    if w <= 0:
        w = 2.0
    if h <= 0:
        h = 1.0
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, h / 2))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (l, w, h)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(mat_body_green())
    return obj


# Family -> generator mapping
GENERATORS = {
    "chip":  gen_chip,
    "melf":  gen_melf,
    "tant":  gen_tant,
    "alcap": gen_alcap,
    "sot":   gen_sot,
    "sod":   gen_sod,
    "soic":  gen_soic,
    "qfp":   gen_qfp,
    "qfn":   gen_qfn,
    "bga":   gen_bga,
    "misc":  gen_misc,
}


# ─── Assembly ───────────────────────────────────────────────────────

def assemble_pcb(csv_path: str, pcb_thickness: float = 1.6,
                 families: list = None, max_components: int = 0):
    """
    Main entry point: load CSV, create PCB board, generate and place components.

    Args:
        csv_path: Path to placement CSV.
        pcb_thickness: PCB thickness in mm (default 1.6mm).
        families: List of families to include (None = all).
        max_components: Max components to place (0 = all).
    """
    import sys, os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from package_parser import load_placement_csv, summarize_placements

    placements = load_placement_csv(csv_path)
    summary = summarize_placements(placements)
    print(f"[PCB] Loaded {summary['total']} placements, "
          f"{len(summary['by_component'])} unique types")

    # Filter by family if specified
    if families:
        placements = [p for p in placements if p.family in families]
        print(f"[PCB] Filtered to {len(placements)} placements "
              f"(families: {families})")

    if max_components > 0:
        placements = placements[:max_components]

    # Compute PCB board size from placement extents
    if not placements:
        print("[PCB] No placements to process.")
        return

    xs = [p.x_mm for p in placements]
    ys = [p.y_mm for p in placements]
    margin = 5.0
    pcb_x_min = min(xs) - margin
    pcb_x_max = max(xs) + margin
    pcb_y_min = min(ys) - margin
    pcb_y_max = max(ys) + margin
    pcb_w = pcb_x_max - pcb_x_min
    pcb_h = pcb_y_max - pcb_y_min
    pcb_cx = (pcb_x_min + pcb_x_max) / 2
    pcb_cy = (pcb_y_min + pcb_y_max) / 2

    print(f"[PCB] Board: {pcb_w:.1f} x {pcb_h:.1f} mm, "
          f"center ({pcb_cx:.1f}, {pcb_cy:.1f})")

    # Create PCB board
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(pcb_cx, pcb_cy, -pcb_thickness / 2))
    pcb_obj = bpy.context.active_object
    pcb_obj.name = "PCB_Board"
    pcb_obj.scale = (pcb_w, pcb_h, pcb_thickness)
    bpy.ops.object.transform_apply(scale=True)
    pcb_obj.data.materials.append(mat_pcb())

    # Place components using shared meshes per component type
    # Cache: component_name -> mesh data (for instancing)
    proto_cache = {}
    placed = 0
    skipped = 0

    for p in placements:
        if p.skip:
            skipped += 1
            continue

        gen_fn = GENERATORS.get(p.family, gen_misc)

        # Create prototype if not cached
        if p.component_name not in proto_cache:
            proto_obj = gen_fn(
                name=f"proto_{p.component_name}",
                l=p.body_l_mm, w=p.body_w_mm, h=p.body_h_mm,
                pin_count=p.pin_count, pitch=p.pitch_mm,
            )
            proto_cache[p.component_name] = proto_obj
            # Hide prototype
            proto_obj.hide_set(True)
            proto_obj.hide_render = True
            # Also hide children
            for child in proto_obj.children:
                child.hide_set(True)
                child.hide_render = True

        proto = proto_cache[p.component_name]

        # Create linked duplicate (instance)
        inst = proto.copy()
        inst.data = proto.data  # shared mesh
        inst.name = p.ref_des
        inst.hide_set(False)
        inst.hide_render = False
        bpy.context.collection.objects.link(inst)

        # Position: CSV X,Y are mm coordinates, Z = on top of PCB (z=0)
        inst.location = (p.x_mm, p.y_mm, 0)
        inst.rotation_euler = (0, 0, math.radians(p.angle_deg))

        # Copy children (leads, terminals) as linked duplicates
        for child in proto.children:
            child_inst = child.copy()
            child_inst.data = child.data
            child_inst.hide_set(False)
            child_inst.hide_render = False
            bpy.context.collection.objects.link(child_inst)
            child_inst.parent = inst
            child_inst.matrix_parent_inverse = child.matrix_parent_inverse.copy()

        placed += 1

    print(f"[PCB] Placed {placed} components, skipped {skipped}")
    print(f"[PCB] Prototype cache: {len(proto_cache)} unique types")

    # Add sun light
    existing_suns = [o for o in bpy.data.objects if o.type == 'LIGHT' and o.data.type == 'SUN']
    if not existing_suns:
        bpy.ops.object.light_add(type='SUN', location=(pcb_cx, pcb_cy, 50))
        sun = bpy.context.active_object
        sun.name = "Sun"
        sun.data.energy = 3.0

    # Set viewport to material mode
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces[0].shading.type = 'MATERIAL'
            # Frame all
            region = area.spaces[0].region_3d
            region.view_location = (pcb_cx, pcb_cy, 0)
            region.view_distance = max(pcb_w, pcb_h) * 1.2
            euler = Euler((math.radians(60), 0, math.radians(30)), 'XYZ')
            region.view_rotation = euler.to_quaternion()
            break

    print(f"[PCB] Assembly complete!")
    return pcb_obj
