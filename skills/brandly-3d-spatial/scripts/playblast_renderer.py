"""Blender PlayBlast renderer for Agnes pipeline.

IMPORTANT: PlayBlast (bpy.ops.render.opengl) requires OpenGL context
and does NOT work in Blender background mode (--background).

For command-line rendering, use the fallback render engine (EEVEE/Cycles)
with optimized settings for speed.

Usage:
    # Interactive (PlayBlast works)
    blender --python playblast_renderer.py -- --config scene.json --output ./renders

    # Background (PlayBlast unavailable, uses EEVEE fallback)
    blender --background --python playblast_renderer.py -- --config scene.json --output ./renders
"""

import bpy
import json
import os
import sys
import math
from mathutils import Vector


def parse_args():
    """Parse command line arguments after '--'."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    config_path = None
    output_dir = "./blender_renders"
    render_mode = "single"  # single, first_last, animation

    i = 0
    while i < len(argv):
        if argv[i] == "--config" and i + 1 < len(argv):
            config_path = argv[i + 1]
            i += 2
        elif argv[i] == "--output" and i + 1 < len(argv):
            output_dir = argv[i + 1]
            i += 2
        elif argv[i] == "--mode" and i + 1 < len(argv):
            render_mode = argv[i + 1]
            i += 2
        else:
            i += 1

    return config_path, output_dir, render_mode


def clear_scene():
    """Remove all objects."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def create_camera(name, position, look_at, focal_length=50):
    """Create a camera."""
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = focal_length
    cam_obj = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = position

    direction = Vector(look_at) - Vector(position)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()

    return cam_obj


def create_character_placeholder(position, height=1.8):
    """Create simple character placeholder."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.2,
        depth=height * 0.6,
        location=(position[0], position[1], position[2] + height * 0.5)
    )
    body = bpy.context.active_object
    body.name = 'Character_Body'

    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.15,
        location=(position[0], position[1], position[2] + height * 0.85)
    )
    head = bpy.context.active_object
    head.name = 'Character_Head'

    mat = bpy.data.materials.new(name='Character')
    body.data.materials.append(mat)
    head.data.materials.append(mat)

    return body, head


def create_ground(size=20):
    """Create ground plane."""
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = 'Ground'
    return ground


def try_playblast(total_frames):
    """Attempt PlayBlast render (requires OpenGL context).

    Returns True if successful, False if unavailable.
    """
    # Check if we're in background mode
    if bpy.app.background:
        print("PlayBlast unavailable in background mode")
        return False

    # Check if opengl operator exists
    if not hasattr(bpy.ops.render, 'opengl'):
        print("PlayBlast operator not available")
        return False

    try:
        # PlayBlast - viewport render
        bpy.ops.render.opengl(animation=True)
        print("PlayBlast render completed")
        return True
    except RuntimeError as e:
        print(f"PlayBlast failed: {e}")
        return False


def setup_eevee_fast():
    """Configure EEVEE for fast rendering."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'

    # Reduce samples for speed
    if hasattr(scene, 'eevee'):
        scene.eevee.taa_render_samples = 4  # Minimal samples


def setup_scene(resolution=(1920, 1080), fps=24):
    """Configure scene settings."""
    scene = bpy.context.scene
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.fps = fps
    scene.frame_start = 0


def animate_camera(camera, keyframes):
    """Animate camera with keyframes."""
    scene = bpy.context.scene

    for kf in keyframes:
        frame = kf['frame']
        scene.frame_set(frame)

        camera.location = kf['position']
        camera.keyframe_insert(data_path='location', frame=frame)

        pos = Vector(kf['position'])
        look = Vector(kf['look_at'])
        direction = look - pos
        rot_quat = direction.to_track_quat('-Z', 'Y')
        camera.rotation_euler = rot_quat.to_euler()
        camera.keyframe_insert(data_path='rotation_euler', frame=frame)

        if 'focal_length' in kf:
            camera.data.lens = kf['focal_length']
            camera.data.keyframe_insert(data_path='lens', frame=frame)


def render_frame_by_frame(output_dir, total_frames):
    """Fallback: render frames using EEVEE."""
    scene = bpy.context.scene
    os.makedirs(output_dir, exist_ok=True)

    setup_eevee_fast()

    rendered = []
    for frame_num in range(total_frames):
        scene.frame_set(frame_num)
        filepath = os.path.join(output_dir, f'frame_{frame_num:04d}.png')
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        rendered.append(filepath)
        print(f"Rendered frame {frame_num}: {filepath}")

    return rendered


def render_single_frame(output_dir):
    """Render single frame from active camera."""
    scene = bpy.context.scene
    os.makedirs(output_dir, exist_ok=True)

    setup_eevee_fast()

    filepath = os.path.join(output_dir, 'first_frame.png')
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)
    print(f"Rendered single frame: {filepath}")

    return filepath


def render_first_and_last(output_dir, total_frames):
    """Render first and last frames for Agnes keyframe mode."""
    scene = bpy.context.scene
    os.makedirs(output_dir, exist_ok=True)

    setup_eevee_fast()

    # First frame
    scene.frame_set(0)
    first_path = os.path.join(output_dir, 'first_frame.png')
    scene.render.filepath = first_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered first frame: {first_path}")

    # Last frame
    scene.frame_set(total_frames - 1)
    last_path = os.path.join(output_dir, 'last_frame.png')
    scene.render.filepath = last_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered last frame: {last_path}")

    return first_path, last_path


def main():
    config_path, output_dir, render_mode = parse_args()

    # Load config
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {
            "resolution": [1920, 1080],
            "fps": 24,
            "cameras": [
                {
                    "name": "Main Camera",
                    "position": [0, -5, 1.6],
                    "look_at": [0, 0, 1.2],
                    "focal_length": 50
                }
            ],
            "character_position": [0, 0, 0],
            "character_height": 1.8,
            "ground_size": 20
        }

    # Clear scene
    clear_scene()

    # Setup scene
    setup_scene(
        resolution=config.get("resolution", [1920, 1080]),
        fps=config.get("fps", 24)
    )

    # Create ground
    create_ground(config.get("ground_size", 20))

    # Create character
    char_pos = config.get("character_position", [0, 0, 0])
    char_height = config.get("character_height", 1.8)
    create_character_placeholder(char_pos, char_height)

    # Create cameras
    cameras = []
    for cam_config in config.get("cameras", []):
        cam = create_camera(
            cam_config.get("name", "Camera"),
            cam_config.get("position", [0, -5, 1.6]),
            cam_config.get("look_at", [0, 0, 0]),
            cam_config.get("focal_length", 50)
        )
        cameras.append(cam)

    # Set first camera as active
    if cameras:
        bpy.context.scene.camera = cameras[0]

    # Animate if keyframes present
    if "keyframes" in config:
        animate_camera(cameras[0], config["keyframes"])
        total_frames = max(kf["frame"] for kf in config["keyframes"]) + 1
    else:
        total_frames = config.get("total_frames", 48)

    # Render based on mode
    os.makedirs(output_dir, exist_ok=True)

    # Try PlayBlast first (only works in interactive mode)
    playblast_ok = try_playblast(total_frames)

    if not playblast_ok:
        # Fallback to EEVEE rendering
        print("Using EEVEE fallback rendering...")
        setup_eevee_fast()

        if render_mode == "single":
            render_single_frame(output_dir)
        elif render_mode == "first_last":
            render_first_and_last(output_dir, total_frames)
        else:
            render_frame_by_frame(output_dir, total_frames)

    # Save config
    config_path_out = os.path.join(output_dir, 'scene_config.json')
    with open(config_path_out, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\nDone! Output in {output_dir}")


if __name__ == "__main__":
    main()
