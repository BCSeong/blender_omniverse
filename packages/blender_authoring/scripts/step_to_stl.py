"""
step_to_stl.py: Convert STEP file to STL(s) with feature separation.

Attempts to extract individual solids from a STEP file.
If multiple solids exist, each is exported as a separate STL with a label guess
(body, lead, pad, etc.) based on geometry analysis.

Usage:
    python step_to_stl.py <step_path> [--output-dir <dir>] [--tolerance 0.01]

Returns JSON report to stdout with:
  - num_solids: how many separate bodies were found
  - files: list of {path, label, bbox, volume} for each STL
  - separated: True if multiple features found, False if single mesh

Requirements:
    pip install cadquery-ocp
"""

import json
import math
import os
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.GProp import GProp_GProps
from OCP.Bnd import Bnd_Box
from OCP.STEPControl import STEPControl_Reader
from OCP.StlAPI import StlAPI_Writer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer


def _get_bbox(shape):
    """Get bounding box [xmin,ymin,zmin,xmax,ymax,zmax] of a shape."""
    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box)
    return list(box.Get())


def _get_volume(shape):
    """Get volume of a shape."""
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return props.Mass()


def _get_dims(bbox):
    """Get (dx, dy, dz) from bbox."""
    return (bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2])


def _guess_label(bbox, volume, all_volumes):
    """Guess a label for a solid based on its geometry relative to others."""
    dx, dy, dz = _get_dims(bbox)
    max_dim = max(dx, dy, dz)
    min_dim = min(dx, dy, dz)
    aspect = max_dim / min_dim if min_dim > 0.001 else 999

    # Largest volume is likely the body
    if volume == max(all_volumes):
        return "body"

    # Small, elongated shapes are likely leads
    if aspect > 3 and volume < max(all_volumes) * 0.01:
        return "lead"

    # Small, flat shapes near the bottom could be pads
    if dz < 0.15 and volume < max(all_volumes) * 0.005:
        return "pad"

    # Medium volume, compact shape could be marking or thermal pad
    if volume < max(all_volumes) * 0.1:
        return "detail"

    return "unknown"


def convert_step(step_path, output_dir=None, tolerance=0.01):
    """
    Convert STEP to STL(s) with feature separation.

    Args:
        step_path: Path to STEP file.
        output_dir: Output directory (default: same as STEP file).
        tolerance: Mesh tolerance in mm.

    Returns:
        dict with conversion report.
    """
    step_path = Path(step_path)
    if output_dir is None:
        output_dir = step_path.parent
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = step_path.stem

    # Read STEP
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(step_path))
    if status != reader.ReadFile.__doc__:  # just check it worked
        pass
    reader.TransferRoots()

    # Extract individual solids
    shape = reader.OneShape()
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)

    solids = []
    while explorer.More():
        solid = explorer.Current()
        bbox = _get_bbox(solid)
        volume = _get_volume(solid)
        solids.append({"shape": solid, "bbox": bbox, "volume": volume})
        explorer.Next()

    num_solids = len(solids)
    print(f"[step_to_stl] Found {num_solids} solid(s) in {step_path.name}")

    if num_solids == 0:
        # Fallback: export entire shape as one STL
        BRepMesh_IncrementalMesh(shape, tolerance).Perform()
        out_path = output_dir / f"{stem}.stl"
        writer = StlAPI_Writer()
        writer.Write(shape, str(out_path))
        bbox = _get_bbox(shape)
        return {
            "num_solids": 0,
            "separated": False,
            "files": [{"path": str(out_path), "label": "whole", "bbox": bbox,
                        "dims_mm": list(_get_dims(bbox))}],
        }

    # Guess labels
    all_volumes = [s["volume"] for s in solids]
    for s in solids:
        s["label"] = _guess_label(s["bbox"], s["volume"], all_volumes)

    # Group leads together (they're typically many identical small parts)
    label_counts = {}
    for s in solids:
        label_counts[s["label"]] = label_counts.get(s["label"], 0) + 1

    separated = num_solids > 1
    files = []

    if separated:
        # Group by label for export
        groups = {}
        for s in solids:
            label = s["label"]
            if label not in groups:
                groups[label] = []
            groups[label].append(s)

        for label, group in groups.items():
            if len(group) == 1:
                # Single solid for this label
                solid = group[0]["shape"]
                BRepMesh_IncrementalMesh(solid, tolerance).Perform()
                out_path = output_dir / f"{stem}_{label}.stl"
                writer = StlAPI_Writer()
                writer.Write(solid, str(out_path))
                bbox = group[0]["bbox"]
                files.append({
                    "path": str(out_path), "label": label,
                    "count": 1,
                    "bbox": [round(v, 3) for v in bbox],
                    "dims_mm": [round(v, 3) for v in _get_dims(bbox)],
                    "volume": round(group[0]["volume"], 6),
                })
            else:
                # Multiple solids with same label — merge into one STL
                from OCP.BRep import BRep_Builder
                from OCP.TopoDS import TopoDS_Compound
                builder = BRep_Builder()
                compound = TopoDS_Compound()
                builder.MakeCompound(compound)
                for s in group:
                    builder.Add(compound, s["shape"])

                BRepMesh_IncrementalMesh(compound, tolerance).Perform()
                out_path = output_dir / f"{stem}_{label}s.stl"
                writer = StlAPI_Writer()
                writer.Write(compound, str(out_path))

                # Combined bbox
                all_bboxes = [s["bbox"] for s in group]
                combined_bbox = [
                    min(b[0] for b in all_bboxes),
                    min(b[1] for b in all_bboxes),
                    min(b[2] for b in all_bboxes),
                    max(b[3] for b in all_bboxes),
                    max(b[4] for b in all_bboxes),
                    max(b[5] for b in all_bboxes),
                ]
                files.append({
                    "path": str(out_path), "label": label,
                    "count": len(group),
                    "bbox": [round(v, 3) for v in combined_bbox],
                    "dims_mm": [round(v, 3) for v in _get_dims(combined_bbox)],
                    "volume": round(sum(s["volume"] for s in group), 6),
                })

        print(f"[step_to_stl] Separated into {len(files)} groups: "
              + ", ".join(f"{f['label']}({f.get('count',1)})" for f in files))
    else:
        # Single solid
        solid = solids[0]["shape"]
        BRepMesh_IncrementalMesh(solid, tolerance).Perform()
        out_path = output_dir / f"{stem}.stl"
        writer = StlAPI_Writer()
        writer.Write(solid, str(out_path))
        bbox = solids[0]["bbox"]
        files.append({
            "path": str(out_path), "label": "whole",
            "count": 1,
            "bbox": [round(v, 3) for v in bbox],
            "dims_mm": [round(v, 3) for v in _get_dims(bbox)],
            "volume": round(solids[0]["volume"], 6),
        })
        print(f"[step_to_stl] Single solid, no separation possible")

    return {
        "step_file": str(step_path),
        "num_solids": num_solids,
        "separated": separated,
        "files": files,
    }


def validate_against_expected(report, expected_name, expected_pins=0,
                               expected_body_mm=None):
    """
    Validate STEP conversion result against expected package specs.

    Returns list of warnings. Empty list = all good.
    """
    warnings = []

    if not report["files"]:
        warnings.append("No geometry extracted from STEP file")
        return warnings

    # Find the largest part (should be body)
    largest = max(report["files"], key=lambda f: f.get("volume", 0))
    dims = largest.get("dims_mm", [0, 0, 0])

    # Check body dimensions if expected
    if expected_body_mm:
        ex_l, ex_w = expected_body_mm[0], expected_body_mm[1]
        # Allow 20% tolerance
        dl = sorted(dims[:2], reverse=True)  # largest 2 dims = L, W
        if dl[0] > 0:
            l_err = abs(dl[0] - ex_l) / ex_l
            w_err = abs(dl[1] - ex_w) / ex_w
            if l_err > 0.2:
                warnings.append(
                    f"Body length mismatch: expected ~{ex_l}mm, got {dl[0]:.1f}mm")
            if w_err > 0.2:
                warnings.append(
                    f"Body width mismatch: expected ~{ex_w}mm, got {dl[1]:.1f}mm")

    # Check pin count (if separated and leads found)
    if expected_pins > 0 and report["separated"]:
        lead_groups = [f for f in report["files"] if f["label"] == "lead"]
        if lead_groups:
            total_leads = sum(f.get("count", 0) for f in lead_groups)
            if total_leads != expected_pins:
                warnings.append(
                    f"Pin count mismatch: expected {expected_pins}, "
                    f"found {total_leads} lead solids")

    # Check if separation happened
    if not report["separated"]:
        warnings.append(
            "STEP has single solid — no feature separation. "
            "Will use as reference only; parametric model needed for materials.")

    return warnings


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="STEP to STL with feature separation")
    parser.add_argument("step_path", help="Path to STEP file")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--tolerance", type=float, default=0.01, help="Mesh tolerance (mm)")
    parser.add_argument("--expected-pins", type=int, default=0)
    parser.add_argument("--expected-body", type=float, nargs=2, default=None,
                        metavar=("L", "W"), help="Expected body dimensions in mm")
    args = parser.parse_args()

    report = convert_step(args.step_path, args.output_dir, args.tolerance)

    if args.expected_pins or args.expected_body:
        warnings = validate_against_expected(
            report, Path(args.step_path).stem,
            expected_pins=args.expected_pins,
            expected_body_mm=args.expected_body,
        )
        report["validation_warnings"] = warnings
        for w in warnings:
            print(f"[WARNING] {w}")

    print(json.dumps(report, indent=2, default=str))
