"""Generate video clips from images using Stable Video Diffusion (free, local)."""
import asyncio
from pathlib import Path
import torch
from PIL import Image
import imageio

try:
    from diffusers import StableVideoDiffusionPipeline
except ImportError:
    StableVideoDiffusionPipeline = None


async def generate_video_from_image(
    image_path: str,
    output_path: str,
    seed: int = 42,
    duration_frames: int = 25,
    noise_aug_strength: float = 0.02,
) -> str:
    """Generate a short video clip from a single image using SVD."""
    if StableVideoDiffusionPipeline is None:
        raise ImportError("diffusers not installed. Run: pip install diffusers[torch]")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Device: {device}")

    # Load the pipeline (downloads model ~2.5GB on first run)
    print(f"  Loading Stable Video Diffusion model...")
    pipe = StableVideoDiffusionPipeline.from_pretrained(
        "stabilityai/stable-video-diffusion-img2vid-xt",
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipe = pipe.to(device)
    pipe.enable_model_cpu_offload()

    # Load and preprocess image
    image = Image.open(image_path).convert("RGB")
    image = image.resize((1024, 576))  # 16:9 aspect ratio
    image_tensor = pipe.image_processor.preprocess(image)

    # Generate
    generator = torch.Generator(device=device).manual_seed(seed)
    with torch.no_grad():
        frames = pipe(
            image_tensor,
            decode_chunk_size=8,
            motion_bucket_id=127,
            noise_aug_strength=noise_aug_strength,
            num_frames=duration_frames,
            generator=generator,
        ).frames[0]

    # Save as GIF (lightweight, no codec issues)
    frame_paths = []
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, frame in enumerate(frames):
        frame_path = out_dir / f"frame_{i:03d}.png"
        Image.fromarray(frame).save(frame_path)
        frame_paths.append(str(frame_path))

    # Write GIF
    imageio.mimsave(output_path, [Image.open(p) for p in frame_paths], fps=8)

    # Cleanup frame files
    for p in frame_paths:
        Path(p).unlink(missing_ok=True)

    print(f"  Saved: {output_path}")
    return output_path


async def main():
    base = Path(r"C:\Users\Patrick\Documents\DREAM-PIXELS-FORGE\plugins\pypi-packages\brandly-cli\.brandly\projects\8640683f-bc7e-49a5-87b2-c23de8fdbe91\artifacts\videos")
    images = sorted(Path(r"C:\Users\Patrick\Documents\DREAM-PIXELS-FORGE\plugins\pypi-packages\brandly-cli\.brandly\projects\8640683f-bc7e-49a5-87b2-c23de8fdbe91\artifacts\images").glob("*.png"))

    if not images:
        print("No images found!")
        return

    output_dir = base / "svd_clips"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(images)} images. Generating SVD video clips...")
    print("Note: First run downloads ~2.5GB model. Be patient.")

    for i, img_path in enumerate(images[:3]):  # Limit to 3 to save time
        print(f"\n[{i+1}/{min(3, len(images))}] Processing: {img_path.name}")
        output = output_dir / f"{img_path.stem}_svd.gif"
        try:
            await generate_video_from_image(str(img_path), str(output), seed=42+i)
        except Exception as e:
            print(f"  Failed: {e}")

    print("\nDone! Check the output directory for SVD clips.")


if __name__ == "__main__":
    asyncio.run(main())
