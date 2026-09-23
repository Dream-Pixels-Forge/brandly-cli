"""Commands for the ``brandly providers`` group.
Moved from cli.py (structural split, no behavioral change).
Shared helpers and state still live in ``brandly_cli.cli``.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import click
from rich.table import Table

from brandly_cli import layout
from brandly_cli.agent_tools import get_builtin_tools
from brandly_cli.agnes_client import (
    agent_tool_loop,
    cancel_job,
    list_jobs,
    list_text_models,
    poll_video,
)
from brandly_cli.ark_client import (
    cancel_job as ark_cancel_job,
)
from brandly_cli.ark_client import (
    create_video_task as ark_create_video_task,
)
from brandly_cli.ark_client import (
    generate_image as ark_generate_image,
)
from brandly_cli.ark_client import (
    list_jobs as ark_list_jobs,
)
from brandly_cli.ark_client import (
    poll_video as ark_poll_video,
)
from brandly_cli.cli import (
    _find_project_by_video_id,
    _get_root,
    _print_json,
    _save_artifact,
    console,
)
from brandly_cli.constants import (
    PROVIDER_RATE_LIMITS,
    STYLE_PRESET_OPTIONS,
    get_all_models,
    get_model_info,
)
from brandly_cli.minimax_client import (
    create_video_task as minimax_create_video,
)
from brandly_cli.minimax_client import (
    generate_image as minimax_generate_image,
)
from brandly_cli.minimax_client import (
    list_jobs as minimax_list_jobs,
)
from brandly_cli.minimax_client import (
    poll_video as minimax_poll_video,
)
from brandly_cli.project_manager import ProjectManager
from brandly_cli.style_presets import apply_style_preset
from brandly_cli.utils import (
    is_valid_project_id,
    now_iso,
)


@click.command()
@click.option(
    "-c",
    "--category",
    type=click.Choice(["image", "video", "audio", "all"]),
    default="all",
    help="Filter by category",
)
@click.option(
    "-q",
    "--query",
    default=None,
    help="Search models by name or provider",
)
@click.option(
    "-o",
    "--output",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def models(category: str, query: str | None, output: str) -> None:
    """List all available AI generation models."""
    all_models = get_all_models()
    results: dict[str, list[dict[str, Any]]] = {}

    cats = ["image", "video", "audio"] if category == "all" else [category]
    for cat in cats:
        models_list = all_models.get(cat, [])
        if query:
            q = query.lower()
            models_list = [
                m
                for m in models_list
                if q in m["name"].lower()
                or q in m["provider"].lower()
                or any(q in f.lower() for f in m.get("features", []))
            ]
        if models_list:
            results[cat] = models_list

    if output == "json":
        _print_json(results)
        return


    for cat, models_list in results.items():
        table = Table(title=f"{cat.title()} Models ({len(models_list)})")
        table.add_column("ID", style="cyan", max_width=28)
        table.add_column("Name", style="white")
        table.add_column("Provider", style="dim")
        table.add_column("Quality", style="green")
        table.add_column("Cost", style="yellow")
        table.add_column("Features", style="dim")
        for m in models_list:
            table.add_row(
                m["id"],
                m["name"],
                m.get("provider", ""),
                m.get("quality", ""),
                f"{m.get('cost', '?')} credits",
                ", ".join(m.get("features", [])[:3]),
            )
        console.print(table)
        console.print()

@click.command()
@click.argument("model_id")
@click.option("-o", "--output", type=click.Choice(["text", "json"]), default="text")
def model(model_id: str, output: str) -> None:
    """Show detailed info about a specific AI model."""
    info = get_model_info(model_id)
    if not info:
        console.print(f"[red]Model not found: {model_id}[/red]")
        console.print("  Use 'brandly models' to see available models.")
        sys.exit(1)
    if output == "json":
        _print_json(info)
        return
    from rich.panel import Panel as RPanel

    sections = [
        (f"[bold cyan]{info['name']}[/bold cyan]", ""),
        ("Provider", info.get("provider", "")),
        ("Category", f"{info.get('category', '')} / {info.get('subtype', 'general')}"),
        ("Description", info.get("description", "")),
        ("Cost", f"{info.get('cost_credits', '?')} credits"),
        ("Features", ", ".join(info.get("features", []))),
    ]
    extra = {
        "max_duration": "max_duration",
        "max_resolution": "max_resolution",
        "speed": "speed",
        "quality": "quality",
    }
    for key, label in extra.items():
        if key in info:
            sections.append((label.title(), str(info[key])))
    lines = []
    for label, value in sections:
        if label and value:
            lines.append(f"[bold]{label}:[/bold] {value}")
        elif label:
            lines.append(f"[bold]{label}:[/bold]")
    console.print(RPanel("\n".join(lines), title=f"Model: {model_id}"))

@click.command(name="rate-limits")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def rate_limits(output: str) -> None:
    """Show provider rate limits for Agnes AI and MiniMax.

    Values mirror the official documentation (Agnes Token Plan FAQ + MiniMax
    rate-limits page). Use these to plan batch / parallel generation.
    """
    if output == "json":
        # Emit raw, non-wrapped JSON so it is directly parseable.
        console.print(
            json.dumps(PROVIDER_RATE_LIMITS, indent=2, ensure_ascii=False),
            soft_wrap=True,
        )
        return

    for provider, limits in PROVIDER_RATE_LIMITS.items():
        table = Table(title=f"{provider} rate limits")
        table.add_column("Limit", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Notes", style="dim")
        for key, value in limits.items():
            if key in ("docs",):
                continue
            notes = ""
            if key == "image_rpm_by_size":
                value = " | ".join(f"{sz}:{rpm}" for sz, rpm in value.items())
                notes = "effective RPM on a free/default key"
            elif key == "h3_concurrent_tasks_free":
                notes = "parallel H3 video tasks (free tier)"
            elif key == "h3_concurrent_tasks_paid":
                notes = "parallel H3 video tasks (paid)"
            table.add_row(key, str(value), notes)
        console.print(table)
        console.print(f"[dim]Source: {limits.get('docs', '')}[/dim]")
        console.print()

@click.command()
@click.option("-s", "--status", default=None, help="Filter by status (pending, completed, failed)")
@click.option("-n", "--limit", default=20, help="Max number of jobs to show")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def jobs(status: str | None, limit: int, output: str) -> None:
    """List recent video generation jobs from the API."""
    async def _jobs(status: str | None, limit: int, output: str) -> None:
        job_list = await list_jobs(status=status, limit=limit)
        if output == "json":
            _print_json(job_list)
            return
        if not job_list:
            console.print("[dim]No jobs found.[/dim]")
            return
        table = Table(title=f"Video Jobs ({len(job_list)})")
        table.add_column("ID", style="cyan", max_width=20)
        table.add_column("Status", style="green")
        table.add_column("Progress", style="yellow")
        table.add_column("Model", style="dim")
        table.add_column("Prompt Preview", style="dim")
        table.add_column("Created", style="dim")
        for j in job_list:
            table.add_row(
                j["video_id"][:20],
                j["status"],
                f"{j['progress']}%",
                j.get("model", ""),
                (j.get("prompt", "") or "")[:40],
                (j.get("created_at", "") or "")[:16],
            )
        console.print(table)
        console.print("[dim]Tip: Use 'brandly job-resume <id>' to poll for completion[/dim]")
    asyncio.run(_jobs(status, limit, output))

@click.command()
@click.argument("video_id")
@click.option(
    "--project-id",
    default=None,
    help="Project to save the video under (default: auto-detect from project.json)",
)
@click.option("--max-wait", default=600, help="Max wait seconds while polling (default: 600)")
@click.option(
    "--model",
    default="agnes-video-2.5-flash",
    help="Agnes video model name used when polling (2.5-flash is the current default)",
)
@click.option("--no-download", is_flag=True, help="Only report status, do not download the video")
@click.pass_context
def job_resume(
    ctx: click.Context,
    video_id: str,
    project_id: str | None,
    max_wait: int,
    model: str,
    no_download: bool,
) -> None:
    """Poll a video job to completion and download the video to disk.

    If the job is still running, polls until it completes (or --max-wait is
    reached). Once a URL is available the video is downloaded to
    .brandly/<project>/videos/scenes/ — use --no-download to skip saving.
    """
    from brandly_cli.agnes_client import get_video_status

    root = _get_root(ctx)

    # Locate the owning project (explicit, auto-detected, or none).
    if project_id is not None and not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)
    if project_id is None:
        project_id = _find_project_by_video_id(root, video_id)

    console.print(f"[dim]Checking status for {video_id}...[/dim]")
    try:
        result = asyncio.run(get_video_status(video_id, model_name=model))
    except Exception as e:
        console.print(f"[red]Status check failed: {e}[/red]")
        console.print(
            "[dim]If the job is still queued, retry later — polling retries "
            "rate-limit errors automatically.[/dim]"
        )
        sys.exit(1)

    status = result.get("status", "unknown")
    console.print(f"  Status: {status}")
    console.print(f"  Progress: {result.get('progress', 0)}%")
    if result.get("error"):
        console.print(f"[red]  Error: {result['error']}[/red]")

    # Poll until completion if still in progress.
    if status not in ("completed", "failed"):
        console.print(f"[dim]Job still running — polling (max {max_wait}s)...[/dim]")
        try:
            result = asyncio.run(
                poll_video(video_id, max_wait_seconds=max_wait, model_name=model)
            )
        except TimeoutError as e:
            console.print(f"[yellow]⚠ {e}[/yellow]")
            console.print(f"[dim]Re-run 'brandly job-resume {video_id}' later.[/dim]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error polling video: {e}[/red]")
            sys.exit(1)
        status = result.get("status", "unknown")
        console.print(f"  Status: {status}")

    if status == "failed":
        console.print(f"[red]✗ Job failed: {result.get('error') or 'unknown error'}[/red]")
        sys.exit(1)
    if status != "completed":
        console.print(f"[yellow]⚠ Job not completed yet (status: {status}).[/yellow]")
        console.print(f"[dim]Re-run 'brandly job-resume {video_id}' later.[/dim]")
        return

    url = result.get("url") or ""
    console.print(f"[green]  URL: {url or 'none'}[/green]")
    if not url:
        console.print("[yellow]⚠ No download URL available for this job.[/yellow]")
        return
    if no_download:
        return

    if project_id is None:
        console.print(
            "[yellow]⚠ Could not detect the owning project — passing "
            "--project-id will save the video to the project tree.[/yellow]"
        )
        console.print(f"[dim]URL: {url}[/dim]")
        return

    saved = _save_artifact(
        url,
        project_id,
        "videos",
        root=root,
        prompt_hint=video_id[:20],
        category="scenes",
    )
    if saved:
        console.print(f"[green]✓ Video downloaded:[/green] {saved}")
        pm = ProjectManager(root)
        asyncio.run(
            pm.update(
                project_id,
                {
                    "last_video_job": {
                        "video_id": video_id,
                        "url": url,
                        "saved_path": str(saved),
                        "model": model,
                        "created_at": now_iso(),
                    }
                },
            )
        )
        # Mark the newest video plan COMPLETED in the production plan.
        plan_dir = layout.docs_dir(layout.project_dir(root, project_id), "plan")
        plan_files = sorted(plan_dir.glob("plan_video_*.md")) if plan_dir.exists() else []
        if plan_files:
            from brandly_cli.utils import upsert_production_plan

            upsert_production_plan(
                project_id,
                root=root,
                plan_file=str(plan_files[-1]),
                asset_type="video",
                model=model,
                status="COMPLETED",
                source="brandly job-resume",
            )
    else:
        console.print("[yellow]⚠ Could not save the video, but the URL is available.[/yellow]")
        console.print(f"[dim]URL: {url}[/dim]")

@click.command()
@click.argument("video_id")
def job_cancel(video_id: str) -> None:
    """Cancel a pending video generation job."""
    result = asyncio.run(cancel_job(video_id))
    if result.get("status") == "cancelled":
        console.print(f"[green]✓ Job {video_id} cancelled successfully.[/green]")
    else:
        console.print(f"[red]✗ Failed to cancel job: {result.get('error', 'unknown error')}[/red]")

@click.command(name="agnes-chat")
@click.argument("prompt")
@click.option("--model", default="agnes-2.5-flash",
              help="Agnes text model (2.5-flash, 2.0-flash, 1.5-flash)")
@click.option("--tools", is_flag=True,
              help="Enable built-in tools (projects, jobs, models, image gen)")
@click.option("--list-models", "list_models_flag", is_flag=True,
              help="List available Agnes text models and exit")
@click.option("--list-tools", "list_tools_flag", is_flag=True,
              help="List built-in agent tools and exit")
@click.option("-o", "--output", type=click.Choice(["text", "json"]), default="text")
def agnes_chat(
    prompt: str,
    model: str,
    tools: bool,
    list_models_flag: bool,
    list_tools_flag: bool,
    output: str,
) -> None:
    """Chat with an Agnes AI text model, optionally as a tool-calling agent.

    With --tools the model can call built-in tools (list_projects, get_project,
    list_jobs, generate_image, list_models) and reason over their results in a
    multi-turn agent loop. Requires AGNES_API_KEY.
    """
    if list_models_flag:
        for m in list_text_models():
            console.print(
                f"  [bold]{m['id']}[/bold]  ctx={m['context']} out={m['max_output']}"
            )
            console.print(f"    [dim]{m['use']}[/dim]")
        return

    if list_tools_flag:
        from brandly_cli.agent_tools import describe_tools

        for name, spec in describe_tools().items():
            console.print(f"  [bold]{name}[/bold] - {spec['description']}")
        return

    if not os.getenv("AGNES_API_KEY"):
        console.print(
            "[red]AGNES_API_KEY is not set. Get one from https://apihub.agnes-ai.com,"
            " or use --list-models / --list-tools (no key required).[/red]"
        )
        sys.exit(1)

    tool_specs = get_builtin_tools() if tools else None
    messages = [{"role": "user", "content": prompt}]
    if tool_specs:
        result = asyncio.run(agent_tool_loop(messages, tool_specs, model=model))
        if output == "json":
            _print_json(result)
            return
        iterations = result.get("iterations", 1)
        console.print(
            f"[bold]Agnes agent: {model}[/bold]  ({iterations} iteration(s))"
        )
        console.print(result.get("content") or "(no content)")
    else:
        from brandly_cli.agnes_client import chat_completion

        data = asyncio.run(chat_completion(messages, model=model))
        if output == "json":
            _print_json(data)
            return
        msg = (data.get("choices") or [{}])[0].get("message") or {}
        console.print(msg.get("content") or "(no content)")

@click.command()
@click.argument("prompt")
@click.option("--model", default="image-01", help="Model ID (image-01 or image-01-live)")
@click.option("--ratio", default="16:9",
              help="Aspect ratio (1:1, 16:9, 4:3, 3:2, 2:3, 3:4, 9:16, 21:9)")
@click.option("--width", default=None, type=int, help="Image width in px (512-2048)")
@click.option("--height", default=None, type=int, help="Image height in px (512-2048)")
@click.option("-n", "--count", default=1,
              type=click.IntRange(1, 9), help="Number of images to generate")
@click.option("--subject", default=None, help="Subject reference image URL for i2i generation")
@click.option("--seed", default=None, type=int, help="Seed for reproducible generations")
@click.option("--style", "style_setting", default=None,
              help="Art style for image-01-live (e.g. cinematic, anime, oil-painting)")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def minimax_image(
    prompt: str,
    model: str,
    ratio: str,
    width: int | None,
    height: int | None,
    count: int,
    subject: str | None,
    seed: int | None,
    style_setting: str | None,
    output: str,
) -> None:
    """Generate images using MiniMax API."""
    async def _minimax_image(prompt, model, ratio, width, height, count, subject, seed, style_setting, output):
        subject_ref = None
        if subject:
            subject_ref = [{"type": "character", "image_file": subject}]

        style_obj = {"style": style_setting} if style_setting else None

        result = await minimax_generate_image(
            prompt,
            model=model,
            aspect_ratio=ratio,
            width=width,
            height=height,
            n=count,
            subject_reference=subject_ref,
            seed=seed,
            image_style_setting=style_obj,
        )

        if output == "json":
            _print_json(result)
            return

        console.print("[bold]MiniMax Image Generation[/bold]")
        console.print(f"  Model: {result.get('model', model)}")
        console.print(f"  Success: {result.get('success_count', 0)}")
        console.print(f"  Failed: {result.get('failed_count', 0)}")
        urls = result.get("urls", [])
        if urls:
            console.print("[bold]Generated Images:[/bold]")
            for i, url in enumerate(urls, 1):
                console.print(f"  {i}. [link={url}]{url}[/link]")
        else:
            console.print("[yellow]No images generated.[/yellow]")
    asyncio.run(_minimax_image(prompt, model, ratio, width, height, count, subject, seed, style_setting, output))

@click.command()
@click.argument("prompt")
@click.option("--model", default="MiniMax-H3", help="Model (MiniMax-H3 or MiniMax-H3-Max)")
@click.option("--resolution", default="768P", help="Resolution (480P, 768P, 2K)")
@click.option("--duration", default=5, type=click.IntRange(4, 15), help="Duration in seconds")
@click.option("--ratio", default="adaptive", help="Aspect ratio")
@click.option("--first-frame", default=None, help="First frame image URL or local file path")
@click.option("--last-frame", default=None, help="Last frame image URL or local file path")
@click.option("--reference-images", default=None, help="Comma-separated reference image URLs or local file paths")
@click.option("--reference-videos", default=None, help="Comma-separated reference video URLs")
@click.option("--reference-audios", default=None, help="Comma-separated reference audio URLs")
@click.option("--wait", is_flag=True, help="Wait for completion")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def minimax_video(
    prompt: str,
    model: str,
    resolution: str,
    duration: int,
    ratio: str,
    first_frame: str | None,
    last_frame: str | None,
    reference_images: str | None,
    reference_videos: str | None,
    reference_audios: str | None,
    wait: bool,
    output: str,
) -> None:
    """Generate videos using MiniMax API."""
    async def _minimax_video(prompt, model, resolution, duration, ratio, first_frame, last_frame, reference_images, reference_videos, reference_audios, wait, output):
        imgs = [
            u.strip() for u in reference_images.split(",") if u.strip()
        ] if reference_images else None
        vids = [
            u.strip() for u in reference_videos.split(",") if u.strip()
        ] if reference_videos else None
        auds = [
            u.strip() for u in reference_audios.split(",") if u.strip()
        ] if reference_audios else None

        result = await minimax_create_video(
            prompt,
            model=model,
            resolution=resolution,
            duration=duration,
            ratio=ratio,
            first_frame=first_frame,
            last_frame=last_frame,
            reference_images=imgs,
            reference_videos=vids,
            reference_audios=auds,
        )

        if output == "json":
            _print_json(result)
            return

        task_id = result.get("task_id", "")
        console.print("[bold]MiniMax Video Generation[/bold]")
        console.print(f"  Model: {model}")
        console.print(f"  Task ID: {task_id}")
        console.print(f"  Status: {result.get('status', 'pending')}")

        if wait and task_id:
            console.print("[dim]Waiting for completion...[/dim]")
            try:
                final = await minimax_poll_video(task_id, max_wait_seconds=600)
                console.print(f"  Final Status: {final.get('status')}")
                if final.get("url"):
                    console.print(f"[green]  URL: {final['url']}[/green]")
                if final.get("error"):
                    console.print(f"[red]  Error: {final['error']}[/red]")
            except TimeoutError:
                console.print("[yellow]⚠ Generation timed out. Check status manually.[/yellow]")
                console.print("  Use: brandly minimax-jobs to view pending tasks")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        else:
            console.print("[dim]Tip: Use 'brandly minimax-jobs' to check status[/dim]")
    asyncio.run(_minimax_video(prompt, model, resolution, duration, ratio, first_frame, last_frame, reference_images, reference_videos, reference_audios, wait, output))

@click.command()
@click.option("--status", default=None,
              help="Filter by status (queued, running, succeeded, failed, cancelled)")
@click.option("-n", "--limit", default=20, help="Max number of jobs to show")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def minimax_jobs(status: str | None, limit: int, output: str) -> None:
    """List recent MiniMax video generation jobs."""
    async def _minimax_jobs(status, limit, output):
        job_list = await minimax_list_jobs(status=status, limit=limit)
        if output == "json":
            _print_json(job_list)
            return
        if not job_list:
            console.print("[dim]No MiniMax jobs found.[/dim]")
            return
        table = Table(title=f"MiniMax Video Jobs ({len(job_list)})")
        table.add_column("Task ID", style="cyan", max_width=18)
        table.add_column("Status", style="green")
        table.add_column("Model", style="dim")
        table.add_column("Resolution", style="dim")
        table.add_column("Duration", style="dim")
        table.add_column("Created", style="dim")
        table.add_column("URL", style="blue", max_width=35)
        for j in job_list:
            table.add_row(
                j["task_id"][:18],
                j["status"],
                j.get("model", ""),
                j.get("resolution", ""),
                f"{j.get('duration', '?')}s",
                (j.get("created_at") or "")[:16],
                (j.get("url") or "")[:35],
            )
        console.print(table)
    asyncio.run(_minimax_jobs(status, limit, output))

@click.command(name="ark-image")
@click.option("--prompt", "-p", required=True, help="Image generation prompt")
@click.option(
    "--model",
    default="seedream-4.0",
    type=click.Choice(["seedream-4.0", "seedream-3.5"]),
    help="Seedream model (default: seedream-4.0)",
)
@click.option("--size", default="16:9", help="Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)")
@click.option("--n", default=1, help="Number of images to generate (1-4)")
@click.option(
    "--style-preset",
    default=None,
    type=click.Choice(STYLE_PRESET_OPTIONS),
    help="Style preset to enhance prompt",
)
@click.pass_context
def ark_image(
    ctx: click.Context,
    prompt: str,
    model: str,
    size: str,
    n: int,
    style_preset: str | None,
) -> None:
    """Generate image via BytePlus Ark (Seedream)."""
    console.print(f"[dim]Generating image with {model}...[/dim]")
    try:
        # Style presets are applied by the caller (providers stay dumb).
        enhanced = apply_style_preset(prompt, style_preset) if style_preset else prompt
        result = asyncio.run(
            ark_generate_image(enhanced, model=model, size=size, n=n)
        )
    except Exception as e:
        console.print(f"[red]Error generating image: {e}[/red]")
        sys.exit(1)

    urls = result.get("urls", [])
    if urls:
        console.print("[green]✓ Image(s) generated:[/green]")
        for url in urls:
            console.print(f"  {url}")
        # Save first URL to disk
        if urls and ctx.obj.get("root"):
            root = Path(ctx.obj["root"])
            saved = _save_artifact(
                urls[0],
                "ark",
                "images",
                root=root,
                prompt_hint=prompt,
                category="general",
            )
            if saved:
                console.print(f"  Saved → {saved}")
    else:
        console.print("[yellow]⚠ No URLs in response[/yellow]")
    _print_json(result)

@click.command(name="ark-video")
@click.argument("project_id")
@click.option("--prompt", "-p", required=True, help="Video generation prompt")
@click.option(
    "--model",
    default="seedance-1.0-t2v",
    type=click.Choice(["seedance-1.0-t2v", "seedance-1.0-i2v"]),
    help="Seedance model (default: seedance-1.0-t2v)",
)
@click.option("--duration", "-d", default=5, help="Duration in seconds (default: 5)")
@click.option("--aspect-ratio", default="16:9", help="Aspect ratio")
@click.option(
    "--reference-images",
    "-r",
    default=None,
    help="Comma-separated image URLs or local file paths for i2v mode",
)
@click.option("--wait", is_flag=True, help="Poll until generation completes")
@click.option("--max-wait", default=300, help="Max wait seconds (default: 300)")
@click.pass_context
def ark_video(
    ctx: click.Context,
    project_id: str,
    prompt: str,
    model: str,
    duration: int,
    aspect_ratio: str,
    reference_images: str | None,
    wait: bool,
    max_wait: int,
) -> None:
    """Generate video via BytePlus Ark (Seedance)."""
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    imgs = (
        [u.strip() for u in reference_images.split(",") if u.strip()]
        if reference_images
        else []
    )

    console.print(f"[dim]Creating video task with {model}...[/dim]")
    try:
        # Legacy parity: the Ark provider used to apply the "cinematic" preset
        # internally; that now happens in the caller (providers stay dumb).
        enhanced = apply_style_preset(prompt, "cinematic")
        task = asyncio.run(
            ark_create_video_task(
                enhanced,
                model=model,
                duration=duration,
                aspect_ratio=aspect_ratio,
                reference_images=imgs if imgs else None,
            )
        )
    except Exception as e:
        console.print(f"[red]Error creating video task: {e}[/red]")
        sys.exit(1)

    task_id = task["task_id"]
    console.print(f"[green]✓ Task created:[/green] {task_id}")
    console.print(f"  Status: {task['status']}  Progress: {task.get('progress', 0)}%")

    if wait:
        console.print(f"[dim]Polling (max {max_wait}s)...[/dim]")
        try:
            result = asyncio.run(ark_poll_video(task_id, max_wait_seconds=max_wait))
        except TimeoutError as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print(f"[dim]Video ID: {task_id} - check status manually[/dim]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error polling video: {e}[/red]")
            sys.exit(1)

        url = result.get("url") or ""
        console.print(f"[green]✓ Video ready:[/green] {url or 'no URL'}")
        if url:
            root = _get_root(ctx)
            saved = _save_artifact(
                url, project_id, "videos", root=root, prompt_hint=prompt, category="scenes"
            )
            if saved:
                console.print(f"  Saved → {saved}")

    _print_json(task)

@click.command(name="ark-jobs")
@click.option("--status", default=None, help="Filter by status")
@click.option("-n", "--limit", default=20, help="Max number of jobs to show")
@click.option("-o", "--output", type=click.Choice(["table", "json"]), default="table")
def ark_jobs(status: str | None, limit: int, output: str) -> None:
    """List recent BytePlus Ark (Seedance) video jobs."""
    async def _ark_jobs(status, limit, output):
        job_list = await ark_list_jobs(status=status, limit=limit)
        if output == "json":
            _print_json(job_list)
            return
        if not job_list:
            console.print("[dim]No Ark jobs found.[/dim]")
            return
        table = Table(title=f"Ark Video Jobs ({len(job_list)})")
        table.add_column("Task ID", style="cyan", max_width=18)
        table.add_column("Status", style="green")
        table.add_column("Model", style="dim")
        table.add_column("Created", style="dim")
        table.add_column("URL", style="blue", max_width=40)
        for j in job_list:
            table.add_row(
                j["task_id"][:18],
                j["status"],
                j.get("model", ""),
                (j.get("created_at") or "")[:16],
                (j.get("url") or "")[:40],
            )
        console.print(table)
    asyncio.run(_ark_jobs(status, limit, output))

@click.command(name="ark-cancel")
@click.argument("task_id")
def ark_cancel(task_id: str) -> None:
    """Cancel an in-progress BytePlus Ark video generation job."""
    async def _ark_cancel(task_id):
        result = await ark_cancel_job(task_id)
        console.print(f"Status: {result['status']}")
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/red]")
    asyncio.run(_ark_cancel(task_id))

def register(cli) -> None:
    cli.add_command(models)
    cli.add_command(model)
    cli.add_command(rate_limits)
    cli.add_command(jobs)
    cli.add_command(job_resume)
    cli.add_command(job_cancel)
    cli.add_command(agnes_chat)
    cli.add_command(minimax_image)
    cli.add_command(minimax_video)
    cli.add_command(minimax_jobs)
    cli.add_command(ark_image)
    cli.add_command(ark_video)
    cli.add_command(ark_jobs)
    cli.add_command(ark_cancel)
