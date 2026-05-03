import math
import sys
from pathlib import Path


def import_3mf(mesh_path):
    import bpy

    import_operator = getattr(bpy.ops.import_mesh, "threemf", None)
    if import_operator is None:
        raise RuntimeError("Blender 3MF import operator is not available.")

    import_operator(filepath=str(mesh_path))


def scene_bounds(objects):
    import mathutils

    points = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        points.extend(obj.matrix_world @ corner for corner in obj.bound_box)

    if not points:
        return None

    min_point = mathutils.Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    max_point = mathutils.Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
    return min_point, max_point


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if len(args) < 2:
        print("Usage: blender --background --python render_3mf_thumbnail.py -- input.3mf output.png [size]", file=sys.stderr)
        return 2

    mesh_path = Path(args[0]).resolve()
    output_path = Path(args[1]).resolve()
    size = int(args[2]) if len(args) > 2 else 512
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import bpy
    import mathutils

    bpy.ops.object.delete()
    import_3mf(mesh_path)

    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    bounds = scene_bounds(mesh_objects)
    if bounds is None:
        print(f"No mesh objects imported from {mesh_path}", file=sys.stderr)
        return 1

    min_point, max_point = bounds
    center = (min_point + max_point) / 2
    radius = max((max_point - min_point).length / 2, 1)

    for obj in mesh_objects:
        obj.location -= center
        if obj.data.materials:
            continue
        material = bpy.data.materials.new("thumbnail_material")
        material.diffuse_color = (0.78, 0.82, 0.88, 1.0)
        obj.data.materials.append(material)

    bpy.ops.object.light_add(type="AREA", location=(0, -4 * radius, 5 * radius))
    light = bpy.context.object
    light.name = "thumbnail_key_light"
    light.data.energy = 450
    light.data.size = 5 * radius

    bpy.ops.object.camera_add(location=(2.4 * radius, -3.0 * radius, 2.0 * radius), rotation=(math.radians(60), 0, math.radians(38)))
    camera = bpy.context.object
    bpy.context.scene.camera = camera
    direction = mathutils.Vector((0, 0, 0)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 70
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = radius * 2.7

    bpy.context.scene.render.resolution_x = size
    bpy.context.scene.render.resolution_y = size
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.render.image_settings.file_format = "PNG"
    bpy.context.scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
