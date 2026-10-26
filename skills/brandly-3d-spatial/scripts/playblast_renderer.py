"""
Blender Python script for rendering spatial reference frames for Agnes AI video generation.

This script is run inside Blender via:
    blender --background --python playblast_renderer.py -- --config scene.json --output ./output_dir

It reads a JSON configuration file and renders camera position/angle frames as PNG images
suitable for use as Agnes AI video generation references (first_frame, last_frame,
reference_images).

Usage:
    blender --background --python playblast_renderer.py -- --config scene_config.json --output ./3d-spatial/cameras --mode single

Arguments:
    --config   Path to JSON configuration file (default: scene_config.json)
    --output   Output directory for rendered frames (default: ./blender_renders)
    --mode     Render mode: single, keyframes, multi (default: single)

Configuration file format:
    {
        "resolution": [1920, 1080],
        "fps": 24,
        "cameras": [
            {
                "name": "shot_001",
                "position": [1.2, 2.0, 1.6],
                "rotation": [0, 0, 0],
                "lens_mm": 50,
                "look_at": [0, 0, 1.2],
                "character_position": [0, 0, 0],
                "character_height": 1.8
            }
        ],
        "keyframes": [
            {"frame": 0, "position": [0, -5, 1.6], "look_at": [0, 0, 1.2]},
            {"frame": 48, "position": [0, -2, 1.6], "look_at": [0, 0, 1.2]}
        ]
    }
"""

import bpy
import json
import math
import os
import sys
from mathutils import Vector, Euler, Matrix


def parse_args():
    """Parse command line arguments."""
    import sys

    config = "scene_config.json"
    output = "./blender_renders"
    mode = "single"

    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]

    i = 0
    while i < len(argv):
        if argv[i] == "--config" and i + 1 < len(argv):
            config = argv[i + 1]
            i += 2
        elif argv[i] == "--output" and i + 1 < len(argv):
            output = argv[i + 1]
            i += 2
        elif argv[i] == "--mode" and i + 1 < len(argv):
            mode = argv[i + 1]
            i += 2
        else:
            i += 1

    return config, output, mode


def load_config(config_path):
    """Load JSON configuration file."""
    with open(config_path, "r") as f:
        return json.load(f)


def setup_scene(config):
    """Configure Blender scene settings."""
    scene = bpy.context.scene
    render = scene.render

    resolution = config.get("resolution", [1920, 1080])
    render.resolution_x = resolution[0]
    render.resolution_y = resolution[1]
    render.resolution_percentage = 100

    fps = config.get("fps", 24)
    render.fps = fps
    render.fps_base = 1

    # Set up world lighting
    world = bpy.context.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world

    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.1, 0.1, 0.1, 1.0)  # Dark gray background
        bg.inputs[1].default_value = 0.5  # Weak strength


def clear_scene():
    """Remove all objects from the scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def create_camera(name, position, rotation, look_at, lens_mm):
    """Create a camera at the specified position and rotation."""
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens_mm
    cam_data.sensor_width = 36.0  # Full frame 35mm

    cam_obj = bpy.data.objects.new(name, cam_data)
    cam_obj.location = Vector(position)
    cam_obj.rotation_euler = Euler(rotation, "XYZ")

    # Point camera at look_at target
    direction = Vector(look_at) - Vector(position)
    cam_obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()

    bpy.context.collection.objects.link(cam_obj)
    bpy.context.view_layer.objects.active = cam_obj

    return cam_obj


def render_frame(cam_obj, output_path, scene_config):
    """Render a single frame from the camera."""
    scene = bpy.context.scene

    # Set camera
    scene.camera = cam_obj

    # Set output path
    scene.render.filepath = str(output_path)

    # Render
    bpy.ops.render.render(write_still=True)


def render_spatial_composition(config):
    """Render all camera positions from config."""
    output_dir = config.get("output_dir", "./blender_renders")
    os.makedirs(output_dir, exist_ok=True)

    # Clear existing scene
    clear_scene()

    # Setup scene
    setup_scene(config)

    cameras = config.get("cameras", [])
    rendered = []

    for i, cam_config in enumerate(cameras):
        name = cam_config.get("name", f"camera_{i}")
        position = cam_config.get("position", [0, 0, 0])
        rotation = cam_config.get("rotation", [0, 0, 0])
        look_at = cam_config.get("look_at", [0, 0, 0])
        lens_mm = cam_config.get("lens_mm", 50)

        # Create camera
        cam_obj = create_camera(name, position, rotation, look_at, lens_mm)

        # Render frame
        output_path = os.path.join(output_dir, f"{name}.png")
        render_frame(cam_obj, output_path, config)

        rendered.append(
            {
                "name": name,
                "path": str(output_path),
                "position": position,
                "rotation": rotation,
                "lens_mm": lens_mm,
                "look_at": look_at,
            }
        )

    return rendered


def render_keyframes(config):
    """Render keyframe animations."""
    output_dir = config.get("output_dir", "./blender_renders")
    os.makedirs(output_dir, exist_ok=True)

    # Setup scene
    setup_scene(config)

    keyframes = config.get("keyframes", [])
    rendered = []

    # Create a single camera that we'll move between keyframes
    cam_obj = None

    for i, kf in enumerate(keyframes):
        position = kf.get("position", [0, 0, 0])
        rotation = kf.get("rotation", [0, 0, 0])
        look_at = kf.get("look_at", [0, 0, 0])
        lens_mm = kf.get("lens_mm", 50)
        name = kf.get("name", f"keyframe_{i}")

        if cam_obj is None:
            # Create camera on first keyframe
            cam_obj = create_camera(name, position, rotation, look_at, lens_mm)
        else:
            # Reuse existing camera
            cam_obj.location = Vector(position)
            cam_obj.rotation_euler = Euler(rotation, "XYZ")
            cam_obj.data.lens = lens_mm

        # Update scene
        scene = bpy.context.scene
        scene.camera = cam_obj

        # Render
        output_path = os.path.join(output_dir, f"{name}.png")
        render_frame(cam_obj, output_path, config)

        rendered.append(
            {
                "name": name,
                "path": str(output_path),
                "position": position,
                "rotation": rotation,
                "lens_mm": lens_mm,
                "look_at": look_at,
                "frame": kf.get("frame", i),
            }
        )

    return rendered


def main():
    config_path, output_dir, mode = parse_args()

    # Load config
    config = load_config(config_path)
    config["output_dir"] = output_dir

    # Render based on mode
    if mode == "single":
        rendered = render_spatial_composition(config)
    elif mode == "keyframes":
        rendered = render_keyframes(config)
    elif mode == "multi":
        # Render all cameras as separate frames
        rendered = render_spatial_composition(config)
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)

    # Write summary
    summary_path = os.path.join(output_dir, "render_summary.json")
    with open(summary_path, "w") as f:
        json.dump(
            {
                "config": config_path,
                "output_dir": output_dir,
                "mode": mode,
                "rendered_count": len(rendered),
                "rendered": rendered,
            },
            f,
            indent=2,
        )

    print(f"Rendered {len(rendered)} frames to {output_dir}")
    print(f"Summary saved to {summary_path}")


if __name__ == "__main__":
    main()