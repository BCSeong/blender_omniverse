"""
package_parser.py: Parse CAD placement CSV and extract component info.

CSV columns:
  No., Placement ID, X, Y, Angle, Component Name, Place/Adhesive,
  Mark, Area Bad Mark, Skip, Trial, Layer, ...

Component Name encodes package type + dimensions, e.g.:
  R0402_250_H01  -> Resistor 0402, height hint 250 (0.25mm)
  C1210_H01      -> Capacitor 1210
  BGA48_8000X6000_H01 -> BGA 48-pin, 8x6mm
  TSQFP100R05_H01 -> TQFP 100-pin, 0.5mm pitch
"""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Imperial chip code -> metric (mm) length x width
CHIP_SIZES_MM = {
    "01005": (0.4, 0.2),
    "0201":  (0.6, 0.3),
    "0402":  (1.0, 0.5),
    "0603":  (1.6, 0.8),
    "0805":  (2.0, 1.25),
    "1206":  (3.2, 1.6),
    "1210":  (3.2, 2.5),
    "1812":  (4.5, 3.2),
    "2010":  (5.0, 2.5),
    "2512":  (6.3, 3.2),
}

# Default chip heights (mm) by size code
CHIP_DEFAULT_HEIGHT = {
    "01005": 0.15,
    "0201":  0.25,
    "0402":  0.35,
    "0603":  0.45,
    "0805":  0.50,
    "1206":  0.60,
    "1210":  0.60,
}

# Tantalum cap sizes (mm): length x width x height
TANT_SIZES = {
    "A": (3.2, 1.6, 1.6),
    "B": (3.5, 2.8, 1.9),
    "C": (6.0, 3.2, 2.6),
    "D": (7.3, 4.3, 2.9),
}

# SOT package sizes (mm): length x width x height, pin_count
SOT_SIZES = {
    "SOT23":    (2.9, 1.3, 1.0, 3),
    "SOT23-5":  (2.9, 1.6, 1.1, 5),
    "SOT23-6":  (2.9, 1.6, 1.1, 6),
    "SOT223":   (6.5, 3.5, 1.6, 4),
    "SOT323":   (2.0, 1.25, 0.95, 3),
    "SOT323-6": (2.0, 1.25, 0.95, 6),
    "SOT353-5": (2.0, 1.25, 0.95, 5),
    "SOT523":   (1.6, 0.8, 0.7, 3),
    "SOT553":   (1.6, 0.8, 0.55, 5),
    "SOT563-6": (1.6, 1.2, 0.55, 6),
}

# SOD package sizes (mm): length x width x height
SOD_SIZES = {
    "SOD-80":  (1.1, 0.6, 0.5),
    "SOD87":   (1.4, 0.8, 0.6),
    "SOD123":  (2.7, 1.6, 1.0),
    "SOD882":  (1.0, 0.6, 0.5),
    "SOD962":  (1.0, 0.6, 0.4),
}


@dataclass
class Placement:
    """A single component placement on the PCB."""
    index: int
    ref_des: str         # e.g. "C1", "U3", "R42"
    x_mm: float
    y_mm: float
    angle_deg: float
    component_name: str  # raw name from CSV
    layer: str = ""
    skip: bool = False

    # Parsed info
    family: str = ""     # chip, melf, sot, sod, soic, qfp, qfn, bga, tant, alcap, misc
    sub_type: str = ""   # e.g. "0402", "23-5", "48"
    body_l_mm: float = 0.0
    body_w_mm: float = 0.0
    body_h_mm: float = 0.0
    pin_count: int = 0
    pitch_mm: float = 0.0


def parse_component_name(name: str) -> dict:
    """Extract package family and dimensions from component name string."""
    info = {"family": "misc", "sub_type": "", "body_l": 0, "body_w": 0, "body_h": 0,
            "pin_count": 0, "pitch": 0}

    n = name.upper().replace("PARTNO_", "")

    # --- Chip resistors/capacitors: R0402_250_H01, C1210_H01 ---
    m = re.match(r'^(R|C|LED|CNET|IND)(01005|0201|0402|0603|0805|1206|1210|1812|2010|2512)', n)
    if m:
        prefix = m.group(1)
        code = m.group(2)
        info["family"] = "chip"
        info["sub_type"] = code
        l, w = CHIP_SIZES_MM.get(code, (1.0, 0.5))
        info["body_l"] = l
        info["body_w"] = w
        # Try to extract height from name: e.g. _250_ means 0.25mm, _700_ means 0.70mm
        hm = re.search(r'_(\d{2,4})_', name)
        if hm:
            info["body_h"] = int(hm.group(1)) / 1000.0
        else:
            info["body_h"] = CHIP_DEFAULT_HEIGHT.get(code, 0.5)
        info["pin_count"] = 2
        return info

    # --- MELF (cylindrical): MELF_0805_900_H01 ---
    m = re.match(r'^MELF_(0402|0603|0805|1206)', n)
    if m:
        code = m.group(1)
        info["family"] = "melf"
        info["sub_type"] = code
        l, w = CHIP_SIZES_MM.get(code, (2.0, 1.25))
        info["body_l"] = l
        info["body_w"] = w
        hm = re.search(r'_(\d{3,4})_', name)
        if hm:
            info["body_h"] = int(hm.group(1)) / 1000.0
        else:
            info["body_h"] = w  # cylindrical: height ≈ width
        info["pin_count"] = 2
        return info

    # --- Tantalum: TANTA_H01, TANTB_H01, ... ---
    m = re.match(r'^TANT([A-D])', n)
    if m:
        size_code = m.group(1)
        info["family"] = "tant"
        info["sub_type"] = size_code
        l, w, h = TANT_SIZES.get(size_code, (3.5, 2.8, 1.9))
        info["body_l"] = l
        info["body_w"] = w
        info["body_h"] = h
        info["pin_count"] = 2
        return info

    # --- Aluminum electrolytic cap: ALCAP_7000X7000_H01 ---
    m = re.match(r'^ALCAP_(\d+)X(\d+)', n)
    if m:
        info["family"] = "alcap"
        info["body_l"] = int(m.group(1)) / 1000.0
        info["body_w"] = int(m.group(2)) / 1000.0
        info["body_h"] = info["body_l"]  # cylindrical: height ≈ diameter
        info["pin_count"] = 2
        return info

    # --- SOT: SOT23_1000_H01, SOT23-5_1100_H01, SOT323-6_H01, SOT563-6_H01 ---
    m = re.match(r'^SOT(\d{2,3})(-\d)?', n)
    if m:
        base = m.group(1)
        suffix = m.group(2) or ""
        key = f"SOT{base}{suffix}"
        info["family"] = "sot"
        info["sub_type"] = key
        if key in SOT_SIZES:
            l, w, h, pins = SOT_SIZES[key]
            info["body_l"] = l
            info["body_w"] = w
            info["body_h"] = h
            info["pin_count"] = pins
        else:
            info["body_l"] = 2.0
            info["body_w"] = 1.3
            info["body_h"] = 1.0
            info["pin_count"] = 3
        return info

    # --- SOD: SOD123_H01, SOD882_H01 ---
    m = re.match(r'^SOD[_-]?(\d{2,3})', n)
    if m:
        code = m.group(1)
        info["family"] = "sod"
        key = f"SOD{code}"
        if key in SOD_SIZES:
            l, w, h = SOD_SIZES[key]
            info["body_l"] = l
            info["body_w"] = w
            info["body_h"] = h
        else:
            info["body_l"] = 1.5
            info["body_w"] = 0.8
            info["body_h"] = 0.6
        info["pin_count"] = 2
        return info

    # --- SOIC: SO8_4200X3500_H01, SO16_9500X3100_H01, SSOP20_H01, TSSOP20_H01 ---
    m = re.match(r'^(SUPER-)?SO(\d+)_(\d+)X(\d+)', n)
    if m:
        pins = int(m.group(2))
        info["family"] = "soic"
        info["sub_type"] = f"SO{pins}"
        info["body_l"] = int(m.group(3)) / 1000.0
        info["body_w"] = int(m.group(4)) / 1000.0
        info["body_h"] = 1.5
        info["pin_count"] = pins
        info["pitch"] = 1.27
        return info

    m = re.match(r'^(T?S?SOP)(\d+)', n)
    if m:
        pkg = m.group(1)
        pins = int(m.group(2))
        info["family"] = "soic"
        info["sub_type"] = f"{pkg}{pins}"
        info["pin_count"] = pins
        if "TSSOP" in pkg:
            info["pitch"] = 0.65
            info["body_l"] = 6.5
            info["body_w"] = 4.4
        else:
            info["pitch"] = 0.65
            info["body_l"] = 7.8
            info["body_w"] = 5.3
        info["body_h"] = 1.2
        return info

    # --- QFP: TSQFP100R05_H01, TQFP32R08_H01, TSQFP64R04_6700X6700_H01 ---
    m = re.match(r'^T?S?QFP(\d+)R(\d{2})', n)
    if m:
        pins = int(m.group(1))
        pitch = int(m.group(2)) / 100.0
        info["family"] = "qfp"
        info["sub_type"] = f"QFP{pins}"
        info["pin_count"] = pins
        info["pitch"] = pitch
        # Try to get body size from name
        sm = re.search(r'_(\d{4,5})X(\d{4,5})', n)
        if sm:
            info["body_l"] = int(sm.group(1)) / 1000.0
            info["body_w"] = int(sm.group(2)) / 1000.0
        else:
            # Estimate from pin count and pitch
            pins_per_side = pins // 4
            span = (pins_per_side - 1) * pitch
            body = span + 2.0  # add margin
            info["body_l"] = body
            info["body_w"] = body
        info["body_h"] = 1.2
        return info

    # --- QFN: QFN44R05_H01, DHVQFN24R05_H01, X2SON_DQN_H01 ---
    m = re.match(r'^(DH?V?)?QFN(\d+)R(\d{2})', n)
    if m:
        pins = int(m.group(2))
        pitch = int(m.group(3)) / 100.0
        info["family"] = "qfn"
        info["sub_type"] = f"QFN{pins}"
        info["pin_count"] = pins
        info["pitch"] = pitch
        pins_per_side = pins // 4
        body = (pins_per_side - 1) * pitch + 1.0
        info["body_l"] = max(body, 3.0)
        info["body_w"] = max(body, 3.0)
        info["body_h"] = 0.85
        return info

    # --- BGA: BGA48_8000X6000_H01, BGA48R08_H01 ---
    m = re.match(r'^BGA(\d+)', n)
    if m:
        pins = int(m.group(1))
        info["family"] = "bga"
        info["sub_type"] = f"BGA{pins}"
        info["pin_count"] = pins
        sm = re.search(r'_(\d{4,5})X(\d{4,5})', n)
        if sm:
            info["body_l"] = int(sm.group(1)) / 1000.0
            info["body_w"] = int(sm.group(2)) / 1000.0
        else:
            # Estimate: sqrt(pins) * pitch
            import math
            side = int(math.ceil(math.sqrt(pins)))
            pm = re.search(r'R(\d{2})', n)
            pitch = int(pm.group(1)) / 100.0 if pm else 0.8
            info["pitch"] = pitch
            body = side * pitch + 1.0
            info["body_l"] = body
            info["body_w"] = body
        info["body_h"] = 1.0
        return info

    # --- DSBGA: DSBGA5_H01 ---
    m = re.match(r'^DSBGA(\d+)', n)
    if m:
        pins = int(m.group(1))
        info["family"] = "bga"
        info["sub_type"] = f"DSBGA{pins}"
        info["pin_count"] = pins
        info["body_l"] = 1.5
        info["body_w"] = 1.5
        info["body_h"] = 0.6
        return info

    # --- LGA: LGA-10_H01 ---
    m = re.match(r'^LGA-?(\d+)', n)
    if m:
        pins = int(m.group(1))
        info["family"] = "qfn"
        info["sub_type"] = f"LGA{pins}"
        info["pin_count"] = pins
        info["body_l"] = 3.0
        info["body_w"] = 3.0
        info["body_h"] = 0.8
        return info

    # --- Dpak ---
    m = re.match(r'^DPAK_(\d+)X(\d+)', n)
    if m:
        info["family"] = "soic"
        info["sub_type"] = "DPAK"
        info["body_l"] = int(m.group(1)) / 1000.0
        info["body_w"] = int(m.group(2)) / 1000.0
        info["body_h"] = 2.3
        info["pin_count"] = 3
        return info

    # --- Generic with dimensions: *_NNNNxNNNN_* ---
    m = re.search(r'(\d{4,5})X(\d{4,5})', n)
    if m:
        info["family"] = "misc"
        info["body_l"] = int(m.group(1)) / 1000.0
        info["body_w"] = int(m.group(2)) / 1000.0
        info["body_h"] = max(info["body_l"], info["body_w"]) * 0.3
        return info

    return info


def load_placement_csv(csv_path: str) -> list[Placement]:
    """Load CAD placement CSV and return list of Placement objects."""
    placements = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                p = Placement(
                    index=int(row["No."]),
                    ref_des=row["Placement ID"].strip(),
                    x_mm=float(row["X"]),
                    y_mm=float(row["Y"]),
                    angle_deg=float(row["Angle"]),
                    component_name=row["Component Name"].strip(),
                    layer=row.get("Layer", "").strip(),
                    skip=(row.get("Skip", "No").strip().lower() == "yes"),
                )
            except (ValueError, KeyError):
                continue

            # Parse component info
            info = parse_component_name(p.component_name)
            p.family = info["family"]
            p.sub_type = info["sub_type"]
            p.body_l_mm = info["body_l"]
            p.body_w_mm = info["body_w"]
            p.body_h_mm = info["body_h"]
            p.pin_count = info["pin_count"]
            p.pitch_mm = info["pitch"]

            placements.append(p)

    return placements


def summarize_placements(placements: list[Placement]) -> dict:
    """Group placements by family and count."""
    from collections import Counter
    family_counts = Counter(p.family for p in placements)
    comp_counts = Counter(p.component_name for p in placements)
    return {
        "total": len(placements),
        "by_family": dict(family_counts.most_common()),
        "by_component": dict(comp_counts.most_common()),
        "families": sorted(set(p.family for p in placements)),
    }


if __name__ == "__main__":
    import sys
    import json
    if len(sys.argv) < 2:
        print("Usage: python package_parser.py <csv_path>")
        sys.exit(1)

    placements = load_placement_csv(sys.argv[1])
    summary = summarize_placements(placements)
    print(f"Total placements: {summary['total']}")
    print(f"\nBy family:")
    for fam, cnt in summary["by_family"].items():
        print(f"  {fam:8s}: {cnt:4d}")
    print(f"\nTop 20 component types:")
    for comp, cnt in list(summary["by_component"].items())[:20]:
        print(f"  {comp:40s}: {cnt:4d}")
