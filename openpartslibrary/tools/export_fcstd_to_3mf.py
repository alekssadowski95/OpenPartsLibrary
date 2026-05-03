import sys
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("Usage: export_fcstd_to_3mf.py input.FCStd output.3mf", file=sys.stderr)
        return 2

    input_path = Path(sys.argv[-2]).resolve()
    output_path = Path(sys.argv[-1]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import FreeCAD
        import Mesh
    except ImportError as error:
        print(f"FreeCAD Python modules are not available: {error}", file=sys.stderr)
        return 1

    document = FreeCAD.openDocument(str(input_path))
    export_objects = [
        obj
        for obj in document.Objects
        if hasattr(obj, "Shape") and not getattr(obj.Shape, "isNull", lambda: True)()
    ]
    if not export_objects:
        print(f"No exportable shape objects found in {input_path}", file=sys.stderr)
        return 1

    Mesh.export(export_objects, str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
