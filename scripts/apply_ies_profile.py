"""Apply IES profile to all SphereLights in a USD stage.

Sets the IES file path, widens cone angle to avoid clipping,
and configures IES normalization.

Usage:
    python scripts/apply_ies_profile.py <input.usdc> <ies_file>
"""
import sys
from pathlib import Path
from pxr import Usd, UsdLux, Sdf


def apply_ies(stage, ies_path):
    """Set IES profile on every SphereLight in the stage."""
    count = 0
    for prim in stage.Traverse():
        if prim.GetTypeName() != "SphereLight":
            continue

        light = UsdLux.SphereLight(prim)

        # Widen cone so it doesn't clip IES distribution
        cone_attr = prim.GetAttribute("inputs:shaping:cone:angle")
        if cone_attr:
            cone_attr.Set(90.0)

        soft_attr = prim.GetAttribute("inputs:shaping:cone:softness")
        if soft_attr:
            soft_attr.Set(0.0)

        # Set IES file (asset path relative to USD)
        ies_attr = prim.GetAttribute("inputs:shaping:ies:file")
        if not ies_attr:
            ies_attr = prim.CreateAttribute(
                "inputs:shaping:ies:file", Sdf.ValueTypeNames.Asset
            )
        ies_attr.Set(Sdf.AssetPath(ies_path))

        # Normalize IES so peak=1.0, let USD intensity control brightness
        norm_attr = prim.GetAttribute("inputs:shaping:ies:normalize")
        if not norm_attr:
            norm_attr = prim.CreateAttribute(
                "inputs:shaping:ies:normalize", Sdf.ValueTypeNames.Bool
            )
        norm_attr.Set(True)

        count += 1

    return count


def main():
    if len(sys.argv) < 3:
        print("Usage: python %s <input.usdc> <ies_file>" % sys.argv[0])
        sys.exit(1)

    usd_path = Path(sys.argv[1])
    ies_file = sys.argv[2]

    stage = Usd.Stage.Open(str(usd_path))
    if not stage:
        print("ERROR: cannot open %s" % usd_path)
        sys.exit(1)

    print("[apply_ies_profile]")
    print("  USD: %s" % usd_path)
    print("  IES: %s" % ies_file)

    count = apply_ies(stage, ies_file)
    print("  Applied to %d SphereLights" % count)

    # Verify a sample light
    for prim in stage.Traverse():
        if prim.GetTypeName() == "SphereLight":
            cone = prim.GetAttribute("inputs:shaping:cone:angle").Get()
            soft = prim.GetAttribute("inputs:shaping:cone:softness").Get()
            ies = prim.GetAttribute("inputs:shaping:ies:file").Get()
            norm = prim.GetAttribute("inputs:shaping:ies:normalize").Get()
            print("\n  Sample: %s" % prim.GetPath())
            print("    cone:angle    = %s" % cone)
            print("    cone:softness = %s" % soft)
            print("    ies:file      = %s" % ies)
            print("    ies:normalize = %s" % norm)
            break

    stage.GetRootLayer().Save()
    print("\nSaved: %s" % usd_path)


if __name__ == "__main__":
    main()
