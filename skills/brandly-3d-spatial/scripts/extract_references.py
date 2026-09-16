"""Extract reference frames for Agnes from Blender renders.

Supports two workflows:
1. Static camera: Single first_frame → Agnes keyframe mode
2. Animated camera: first_frame + last_frame → Agnes keyframe mode

Usage:
    python extract_references.py --input ./blender_renders --output ./agnes_references

This script:
1. Finds rendered frames from Blender
2. Selects first/last frames based on strategy
3. Copies/renames for easy Agnes integration
4. Generates metadata JSON for agnes_client.py
"""

import json
import os
import shutil
import sys
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    argv = sys.argv[1:]

    input_dir = "./blender_renders"
    output_dir = "./agnes_references"
    strategy = "first"  # first, first_last, all

    i = 0
    while i < len(argv):
        if argv[i] == "--input" and i + 1 < len(argv):
            input_dir = argv[i + 1]
            i += 2
        elif argv[i] == "--output" and i + 1 < len(argv):
            output_dir = argv[i + 1]
            i += 2
        elif argv[i] == "--strategy" and i + 1 < len(argv):
            strategy = argv[i + 1]
            i += 2
        else:
            i += 1

    return input_dir, output_dir, strategy


def find_frames(input_dir):
    """Find all rendered frames."""
    input_path = Path(input_dir)

    # Try frame_*.png pattern first
    frames = sorted(input_path.glob("frame_*.png"))

    if not frames:
        # Try other PNG patterns
        frames = sorted(input_path.glob("*.png"))
        frames = [f for f in frames if f.name not in ("scene_config.json", "first_frame.png", "last_frame.png")]

    return frames


def extract_references(input_dir, output_dir, strategy="first"):
    """Extract reference frames for Agnes."""
    frames = find_frames(input_dir)

    if not frames:
        print(f"No frames found in {input_dir}")
        return None

    print(f"Found {len(frames)} frames in {input_dir}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Select frames based on strategy
    metadata = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "strategy": strategy,
        "total_frames": len(frames),
    }

    if strategy == "first":
        # Single static frame
        first = frames[0]
        out_path = os.path.join(output_dir, "first_frame.png")
        shutil.copy2(first, out_path)
        print(f"Copied: {first.name} -> first_frame.png")
        metadata["first_frame"] = out_path
        metadata["reference_images"] = []

    elif strategy == "first_last":
        # First + last frames for animated camera
        first = frames[0]
        last = frames[-1]

        first_path = os.path.join(output_dir, "first_frame.png")
        last_path = os.path.join(output_dir, "last_frame.png")

        shutil.copy2(first, first_path)
        shutil.copy2(last, last_path)
        print(f"Copied: {first.name} -> first_frame.png")
        print(f"Copied: {last.name} -> last_frame.png")

        metadata["first_frame"] = first_path
        metadata["last_frame"] = last_path
        metadata["reference_images"] = []

    elif strategy == "all":
        # All frames as reference images
        selected = frames[:5]  # Max 5 references for Agnes
        reference_images = []
        for i, frame in enumerate(selected):
            out_name = f"reference_{i:03d}.png"
            out_path = os.path.join(output_dir, out_name)
            shutil.copy2(frame, out_path)
            reference_images.append(out_path)
            print(f"Copied: {frame.name} -> {out_name}")

        metadata["first_frame"] = reference_images[0] if reference_images else None
        metadata["reference_images"] = reference_images[1:]

    else:
        # Default to first frame
        first = frames[0]
        out_path = os.path.join(output_dir, "first_frame.png")
        shutil.copy2(first, out_path)
        metadata["first_frame"] = out_path
        metadata["reference_images"] = []

    # Save metadata
    metadata_path = os.path.join(output_dir, "references_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nReferences extracted to {output_dir}")
    print(f"Metadata saved to {metadata_path}")

    return metadata


def generate_agnes_command(metadata):
    """Generate example agnes_client.py command."""
    if not metadata or not metadata.get("first_frame"):
        return None

    first_frame = metadata["first_frame"]
    last_frame = metadata.get("last_frame")
    reference_images = metadata.get("reference_images", [])

    cmd = f'''from brandly_cli.agnes_client import create_video_task

result = await create_video_task(
    prompt="YOUR_PROMPT_HERE",
    first_frame="{first_frame}",'''

    if last_frame:
        cmd += f'\n    last_frame="{last_frame}",'

    if reference_images:
        cmd += f'\n    reference_images={reference_images},'

    cmd += '''
    model="agnes-video-2.5-flash",
    duration=4,
)'''

    return cmd


def main():
    input_dir, output_dir, strategy = parse_args()

    metadata = extract_references(input_dir, output_dir, strategy)

    if metadata:
        # Print example command
        cmd = generate_agnes_command(metadata)
        if cmd:
            print("\n--- Example Agnes Command ---")
            print(cmd)
            print("--- End Example ---\n")


if __name__ == "__main__":
    main()
