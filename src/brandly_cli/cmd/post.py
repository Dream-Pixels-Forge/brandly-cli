"""Commands for the ``brandly post`` group.
Moved from cli.py (structural split, no behavioral change).
Shared helpers and state still live in ``brandly_cli.cli``.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path

import click
from rich.table import Table

from brandly_cli import layout
from brandly_cli.cli import (
    _get_root,
    _print_json,
    console,
)
from brandly_cli.edit import (
    add_subtitles,
    change_speed,
    concatenate_videos,
    extract_audio,
    get_video_info,
    resize_video,
    trim_video,
)
from brandly_cli.project_manager import ProjectManager
from brandly_cli.utils import (
    human_size,
    is_valid_project_id,
    now_iso,
)


@click.command()
@click.argument("project_id")
@click.option(
    "--output",
    "-o",
    default=None,
    help="Output directory (default: .brandly/{id}/export/)",
)
@click.pass_context
def export(ctx: click.Context, project_id: str, output: str | None) -> None:
    """Export a completed project's artifacts."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    root = _get_root(ctx)
    pm = ProjectManager(root)
    proj = asyncio.run(pm.read(project_id))
    if not proj:
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)

    proj_dir = layout.resolve_project_dir(root, project_id)
    out_dir = Path(output) if output else proj_dir / "export"
    out_dir = out_dir.resolve()
    proj_dir_resolved = proj_dir.resolve()

    # Guard: if out_dir is the same as or an ancestor of proj_dir, copying would
    # recurse into itself. Error loudly so the user knows to pick a sibling dir.
    try:
        proj_dir_resolved.relative_to(out_dir)
        console.print(
            f"[red]Export aborted: output dir ({out_dir}) is the same as or an "
            f"ancestor of the project dir ({proj_dir_resolved}).[/red]\n"
            f"  Use a sibling or sub-folder, e.g. `--output {proj_dir_resolved.parent / 'export'}`"
        )
        sys.exit(1)
    except ValueError:
        pass  # out_dir is NOT an ancestor — proceed normally

    # Bookkeeping files at the project root are excluded from the export
    # by only scanning the user-facing top folders (images/videos/audio/docs).

    artifact_count = 0
    media_count = 0
    media_exts = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm", ".mp3", ".wav", ".mpga"}
    # User-facing media + docs live in these top folders of the project dir
    # (reference images are included via their images/ sub-folder).
    for search_dir in [
        proj_dir / "images",
        proj_dir / "videos",
        proj_dir / "audio",
        proj_dir / "docs",
    ]:
        if not search_dir.exists():
            continue
        for f in search_dir.rglob("*"):
            if not f.is_file():
                continue
            # Skip files inside the export output directory to avoid recursion
            try:
                f.resolve().relative_to(out_dir)
                continue
            except ValueError:
                pass
            ext = f.suffix.lower()
            rel = f.relative_to(proj_dir)
            dest = out_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(f, dest)
            if ext in media_exts:
                media_count += 1
            else:
                artifact_count += 1

    if artifact_count == 0 and media_count == 0:
        console.print("[yellow]No artifacts to export.[/yellow]")
        console.print("[dim]The project has no media or doc files under images/, videos/, audio/, or docs/.[/dim]")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    from brandly_cli.types import ExportManifest

    manifest = ExportManifest(
        project_id=project_id,
        project_name=proj.name,
        style=proj.style,
        shot_count=proj.shot_count,
        budget=proj.budget,
        spent=proj.spent,
        target_platforms=proj.target_platforms,
        created_at=proj.created_at,
        exported_at=now_iso(),
        artifact_count=artifact_count,
        media_count=media_count,
        total_files=artifact_count + media_count,
    )
    manifest_path = out_dir / "export-manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(), indent=2))

    console.print(
        f"[green]✓ Exported[/green] {artifact_count} artifacts + {media_count} media → {out_dir}"
    )
    console.print(f"  Manifest: {manifest_path}")

@click.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--start", default=0.0, help="Start time in seconds")
@click.option("--end", default=None, help="End time in seconds")
@click.option("--duration", default=None, help="Duration in seconds (alternative to --end)")
@click.option("--codec", default="libx264", help="Video codec")
@click.option("--preset", default="fast", help="Encoding preset")
def edit(
    input: str,
    output: str,
    start: float,
    end: float | None,
    duration: float | None,
    codec: str,
    preset: str,
) -> None:
    """Trim a video to a segment."""
    async def _edit(input, output, start, end, duration, codec, preset):
        result = await trim_video(
            input, output, start=start, end=end,
            duration=duration, codec=codec, preset=preset,
        )
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(f"[green]✓ Trimmed to {output}[/green]")
        console.print(f"  Duration: {result.get('duration_seconds', '?')}s")
        console.print(f"  Size: {human_size(result.get('size_bytes', 0))}")
    asyncio.run(_edit(input, output, start, end, duration, codec, preset))

@click.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--width", default=None, type=int, help="Target width in pixels")
@click.option("--height", default=None, type=int, help="Target height in pixels")
@click.option("--aspect", default=None, help="Aspect ratio (16:9, 9:16, 1:1, 4:3)")
@click.option("--codec", default="libx264", help="Video codec")
def resize(
    input: str,
    output: str,
    width: int | None,
    height: int | None,
    aspect: str | None,
    codec: str,
) -> None:
    """Resize a video to given dimensions or aspect ratio."""
    async def _resize(input, output, width, height, aspect, codec):
        result = await resize_video(
            input, output, width=width, height=height,
            aspect=aspect, codec=codec,
        )
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(f"[green]✓ Resized to {output}[/green]")
        if width:
            console.print(f"  Width: {width}px")
        if height:
            console.print(f"  Height: {height}px")
    asyncio.run(_resize(input, output, width, height, aspect, codec))

@click.command()
@click.argument("inputs", nargs=-1, required=True, type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--codec", default="libx264", help="Video codec")
def concat(inputs: tuple[str, ...], output: str, codec: str) -> None:
    """Concatenate multiple videos into one."""
    async def _concat(inputs, output, codec):
        result = await concatenate_videos(list(inputs), output, codec=codec)
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(
            f"[green]✓ Concatenated {result.get('input_count', len(inputs))} "
            f"videos → {output}[/green]"
        )
        console.print(f"  Duration: {result.get('duration_seconds', '?')}s")
    asyncio.run(_concat(inputs, output, codec))

@click.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.option("--format", "fmt", default="mp3", help="Audio format (mp3, wav, m4a)")
@click.option("--bitrate", default="192k", help="Audio bitrate")
def audio(input: str, output: str, fmt: str, bitrate: str) -> None:
    """Extract audio track from a video file."""
    async def _audio(input, output, fmt, bitrate):
        result = await extract_audio(input, output, format=fmt, bitrate=bitrate)
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(f"[green]✓ Audio extracted to {output}[/green]")
        console.print(f"  Format: {fmt}")
        console.print(f"  Bitrate: {bitrate}")
    asyncio.run(_audio(input, output, fmt, bitrate))

@click.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.argument("text")
@click.option("--font-size", default=24, type=int)
@click.option("--position", default="bottom", type=click.Choice(["top", "middle", "bottom"]))
@click.option("--codec", default="libx264")
def captions(
    input: str,
    output: str,
    text: str,
    font_size: int,
    position: str,
    codec: str,
) -> None:
    """Add burned-in subtitles to a video."""
    async def _captions(input, output, text, font_size, position, codec):
        result = await add_subtitles(
            input, output, text,
            font_size=font_size, position=position, codec=codec,
        )
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(f"[green]✓ Subtitles added to {output}[/green]")
    asyncio.run(_captions(input, output, text, font_size, position, codec))

@click.command()
@click.argument("input", type=click.Path(exists=True))
@click.argument("output", type=click.Path())
@click.argument("speed", type=float)
@click.option("--codec", default="libx264")
def speed(
    input: str, output: str, speed: float, codec: str
) -> None:
    """Change video playback speed."""
    async def _speed(input, output, speed, codec):
        result = await change_speed(input, output, speed, codec=codec)
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        console.print(f"[green]✓ Speed changed to {speed}x → {output}[/green]")
    asyncio.run(_speed(input, output, speed, codec))

@click.command(name="probe")
@click.argument("input", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def probe(input: str, output: str) -> None:
    """Analyze a video file's metadata and properties."""
    info = asyncio.run(get_video_info(input))
    if "error" in info:
        console.print(f"[red]Error: {info['error']}[/red]")
        sys.exit(1)
    if output == "json":
        _print_json(info)
        return
    table = Table(title=f"Video Analysis: {Path(input).name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Duration", f"{info.get('duration_seconds', 0):.1f}s")
    table.add_row("Size", human_size(info.get("size_bytes", 0)))
    table.add_row("Resolution", f"{info.get('video_width', 0)}×{info.get('video_height', 0)}")
    table.add_row("Aspect Ratio", info.get("video_aspect", ""))
    table.add_row("Frame Rate", info.get("video_fps", ""))
    table.add_row("Video Codec", info.get("video_codec", ""))
    table.add_row("Audio Codec", info.get("audio_codec", "none"))
    table.add_row("Has Audio", "yes" if info.get("has_audio") else "no")
    table.add_row("Format", info.get("format", ""))
    console.print(table)

@click.command()
@click.argument("clips", nargs=-1, required=True)
@click.argument("output")
@click.option("--transition", default="fade", help="Transition type (fade, dissolve, wipe, slide)")
@click.option("--transition-duration", default=0.5, help="Transition duration in seconds")
@click.option(
    "--color-grade", default="cinematic",
    help="Color grade (cinematic, warm, cool, desaturated, none)",
)
@click.option("--ratio", default=None, help="Target aspect ratio (e.g. 2.39:1, 9:16) — G4 assembly-time crop/pad")
@click.option(
    "--fit", default="crop", type=click.Choice(["crop", "pad"]),
    help="How to reach --ratio: crop (center-crop, default) or pad (letterbox with black bars)",
)
@click.option("--root", default=None, help="Working directory")
def stitch(
    clips: tuple[str, ...],
    output: str,
    transition: str,
    transition_duration: float,
    color_grade: str,
    ratio: str | None,
    fit: str,
    root: str | None,
) -> None:
    """Stitch multiple video clips with transitions and color grading."""
    from brandly_cli.stitch import stitch_videos
    clip_paths = [Path(c) for c in clips]
    output_path = Path(output)
    console.print(f"[bold]Stitching[/bold] {len(clip_paths)} clips → {output_path}")
    result = asyncio.run(
        stitch_videos(
            clip_paths,
            output_path,
            transition=transition,
            transition_duration=transition_duration,
            color_grade=color_grade,
            ratio=ratio,
            fit=fit,
        )
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Output:[/green] {result['output_path']}")
    console.print(
        f"  Duration: {result['duration_seconds']:.1f}s | Size: {result['size_bytes']//1024}KB"
    )
    console.print(f"  Transitions: {', '.join(result['transitions_applied']) or 'none'}")
    console.print(f"  Color grade: {result['color_grade']}")
    if ratio:
        console.print(f"  Ratio: {ratio} (fit: {fit})")

@click.command()
@click.argument("project_id")
@click.option(
    "--platforms", multiple=True,
    help="Target platforms (tiktok, instagram_reel, youtube_standard, etc.)",
)
@click.option("--output", default=None, help="Output directory")
@click.option(
    "--fit", default="crop", type=click.Choice(["crop", "pad"]),
    help="G4 ratio semantics: crop (default; center-crop to the platform ratio) or pad (letterbox to standard resolution)",
)
@click.option("--root", default=None, help="Working directory")
def export_platforms(project_id, platforms, output, fit, root):
    """Export project to platform-optimized formats."""
    from brandly_cli.export_platforms import export_for_platform

    if not platforms:
        platforms = ("tiktok", "youtube_standard")
    proj_dir = layout.resolve_project_dir(Path(root or "."), project_id)
    if not proj_dir.exists():
        console.print(f"[red]Project not found: {project_id}[/red]")
        sys.exit(1)
    videos_root = proj_dir / "videos"
    video_file = next((videos_root.rglob("*.mp4")), None)
    if not video_file:
        console.print("[yellow]No video found in project[/yellow]")
        sys.exit(1)
    out_dir = Path(output) if output else proj_dir / "export"
    for platform in platforms:
        console.print(f"Exporting for [bold]{platform}[/bold]...")
        result = asyncio.run(
            export_for_platform(video_file, platform, out_dir, root=root, fit=fit)
        )
        if "error" in result:
            console.print(f"[red]  Error: {result['error']}[/red]")
        else:
            console.print(f"  ✓ {result['output_path']} ({result['duration_seconds']:.1f}s)")

@click.command()
@click.argument("project_id")
@click.option("--count", default=5, help="Number of thumbnails to generate")
@click.option("--style", default="commercial", help="Style preset (commercial, minimal, bold)")
@click.option("--root", default=None, help="Working directory")
def thumbnail(project_id: str, count: int, style: str, root: str | None) -> None:
    """Generate thumbnails from project video."""
    from brandly_cli.thumbnails import generate_thumbnails
    proj_dir = layout.resolve_project_dir(Path(root or "."), project_id)
    videos_root = proj_dir / "videos"
    video_file = next((videos_root.rglob("*.mp4")), None)
    if not video_file:
        console.print(f"[red]No video found in project: {project_id}[/red]")
        sys.exit(1)
    output_dir = layout.media_dir(proj_dir, "images", "general")
    result = asyncio.run(
        generate_thumbnails(
            video_file, output_dir, count=count, style_preset=style,
            root=Path(root) if root else None,
        )
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Generated {result['count']} thumbnails[/green]")
    for thumb in result.get("thumbnails", []):
        console.print(f"  {thumb.get('path', thumb)}")

@click.command(name="voice-match")
@click.argument("video_path")
@click.option("--source", default="en", help="Source language code")
@click.option(
    "--target", required=True,
    help="Target language code (en, es, fr, de, ja, ko, zh, pt, ar, hi)",
)
@click.option("--voice-style", default="professional", help="Voice style")
@click.option("--output", default=None, help="Output path")
@click.option("--root", default=None, help="Working directory")
def voice_match(
    video_path: str, source: str, target: str, voice_style: str,
    output: str | None, root: str | None,
) -> None:
    """Dub a video to a target language."""
    from brandly_cli.dubbing import dub_video
    result = asyncio.run(
        dub_video(
            Path(video_path), source, target,
            voice_style=voice_style,
            output_path=Path(output) if output else None,
            root=Path(root) if root else None,
        )
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Dubbed to {result['target_lang']}[/green]")
    console.print(f"  Output: {result['output_path']}")
    console.print(f"  Duration: {result['duration_seconds']:.1f}s")

@click.command(name="beat-sync")
@click.argument("video_path")
@click.argument("audio_path")
@click.option("--output", required=True, help="Output video path")
@click.option("--threshold", default=0.5, help="Beat detection threshold")
@click.option("--min-duration", default=1.0, help="Minimum clip duration")
@click.option("--root", default=None, help="Working directory")
def beat_sync(
    video_path: str, audio_path: str, output: str,
    threshold: float, min_duration: float, root: str | None,
) -> None:
    """Cut video to match beat positions in audio."""
    from brandly_cli.beat_sync import beat_sync as bs_sync
    result = asyncio.run(
        bs_sync(
            Path(video_path), Path(audio_path), Path(output),
            beat_threshold=threshold,
            min_clip_duration=min_duration,
            root=Path(root) if root else None,
        )
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print(f"[green]✓ Beat-synced {result['clips_created']} segments[/green]")
    console.print(f"  Beats detected: {result['beats_detected']}")
    console.print(f"  Output: {result['output_path']}")

@click.command()
@click.argument("category", default=None, required=False)
@click.option("--platforms", multiple=True, help="Filter by platforms")
@click.option("--json", is_flag=True, help="Output as JSON")
def trend(category: str | None, platforms: tuple[str, ...], json: bool) -> None:
    """Research trending video formats."""
    from brandly_cli.trends import list_categories, research_trends
    cats = list_categories()
    if not category:
        console.print("[bold]Available categories:[/bold]")
        for c in cats:
            console.print(f"  {c}")
        return
    if category not in cats:
        console.print(f"[red]Unknown category: {category}. Available: {cats}[/red]")
        sys.exit(1)
    result = asyncio.run(research_trends(category, list(platforms) if platforms else None))
    if json:
        _print_json(result)
        return
    console.print(f"[bold]{category.capitalize()} Trending Formats[/bold]")
    console.print(f"  Recommended: {result['recommended_format']}")
    console.print()
    for fmt in result["trending_formats"]:
        console.print(f"  • {fmt['name']} — {fmt['description']} (virality: {fmt['virality']:.0%})")

@click.command()
@click.argument("video_path")
@click.option("--script", default=None, help="Script text for hook analysis")
@click.option("--style", default="cinematic", help="Visual style")
@click.option("--root", default=None, help="Working directory")
def analyze(video_path: str, script: str | None, style: str, root: str | None) -> None:
    """Analyze video performance prediction."""
    from brandly_cli.analyzer import analyze_video
    result = asyncio.run(
        analyze_video(
            Path(video_path), script=script, style=style,
            root=Path(root) if root else None,
        )
    )
    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]")
        sys.exit(1)
    console.print("[bold]Video Performance Analysis[/bold]")
    console.print(f"  Overall Score: [green]{result['overall_score']}[/green]/10")
    console.print(f"  Hook Strength:   {result['hook_strength']}/10")
    console.print(f"  Pacing Score:    {result['pacing_score']}/10")
    console.print(f"  Visual Quality:  {result['visual_quality']}/10")
    console.print(f"  CTR Prediction:  {result['ctr_prediction']}/10")
    console.print(f"  Platform Fit:    {result['platform_fit']}/10")
    if result["recommendations"]:
        console.print()
        console.print("[bold]Recommendations:[/bold]")
        for rec in result["recommendations"]:
            console.print(f"  • {rec}")

@click.command()
@click.argument("name")
@click.option("--style", default="ugc", help="Style preset")
@click.option("--shots", default=5, help="Number of shots")
@click.option("--duration", default=30, help="Duration in seconds")
@click.option("--budget", default=300, help="Budget in credits")
@click.option("--platforms", multiple=True, help="Target platforms")
@click.option("--save", is_flag=True, help="Save as custom template")
@click.option("--root", default=None, help="Working directory")
def template(
    name: str, style: str, shots: int, duration: int, budget: int,
    platforms: tuple[str, ...], save: bool, root: str | None,
) -> None:
    """Create or manage project templates."""
    from brandly_cli.templates import create_from_template, save_template
    if save:
        config = {
            "style": style, "shots": shots, "duration": duration,
            "budget": budget, "platforms": list(platforms) or ["tiktok"],
        }
        asyncio.run(save_template(name, config, root=Path(root) if root else None))
        console.print(f"[green]✓ Template saved: {name}[/green]")
    else:
        console.print(f"[bold]Template: {name}[/bold]")
        config = asyncio.run(create_from_template(name))
        for k, v in config.items():
            console.print(f"  {k}: {v}")

@click.command(name="template-list")
@click.option("--root", default=None, help="Working directory")
def template_list(root: str | None) -> None:
    """List available templates."""
    from brandly_cli.templates import list_custom_templates, list_templates
    builtins = asyncio.run(list_templates())
    customs = asyncio.run(list_custom_templates(root=Path(root) if root else None))
    console.print("[bold]Built-in Templates[/bold]")
    for t in builtins:
        console.print(f"  • {t}")
    if customs:
        console.print()
        console.print("[bold]Custom Templates[/bold]")
        for t in customs:
            console.print(f"  ★ {t}")

def register(cli) -> None:
    cli.add_command(export)
    cli.add_command(edit)
    cli.add_command(resize)
    cli.add_command(concat)
    cli.add_command(audio)
    cli.add_command(captions)
    cli.add_command(speed)
    cli.add_command(probe)
    cli.add_command(stitch)
    cli.add_command(export_platforms)
    cli.add_command(thumbnail)
    cli.add_command(voice_match)
    cli.add_command(beat_sync)
    cli.add_command(trend)
    cli.add_command(analyze)
    cli.add_command(template)
    cli.add_command(template_list)
