"""Commands for the ``brandly generation`` group.
Moved from cli.py (structural split, no behavioral change).
Shared helpers and state still live in ``brandly_cli.cli``.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import click
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from brandly_cli import layout, shot_runner
from brandly_cli.agnes_client import (
    create_video_task,
    generate_image,
    poll_video,
)
from brandly_cli.audio_client import generate_music, generate_tts, list_voices
from brandly_cli.cli import (
    REFERENCE_SUBJECTS,
    _get_root,
    _human_review_gate,
    _load_project_reference,
    _print_gate_report,
    _print_json,
    _record_media_spend,
    _save_artifact,
    _standardize_reference_format,
    _write_review_note,
    build_reference_prompt,
    console,
)
from brandly_cli.constants import (
    STYLE_PRESET_OPTIONS,
)
from brandly_cli.director import get_director_prompt
from brandly_cli.project_manager import ProjectManager
from brandly_cli.style_presets import apply_style_preset
from brandly_cli.utils import (
    get_reference_image_urls,
    is_valid_project_id,
    load_sheet_reference,
    now_iso,
    sanitize_filename,
)
from brandly_cli.video_prompts import (
    build_enhanced_video_prompt,
    build_single_shot_prompt,
    build_video_prompt,
    list_video_styles,
)


@click.command(name="reference")
@click.argument("project_id")
@click.option(
    "--subject-type",
    "subject_type",
    required=True,
    type=click.Choice(list(REFERENCE_SUBJECTS.keys())),
    help="What kind of asset this reference is (object, character, location, etc.)",
)
@click.option(
    "--subject",
    "-s",
    required=True,
    help=(
        "The asset itself, e.g. 'Nike Air Max 1, white colorway, visible Air unit'. "
        "This is the asset that subsequent videos will reference."
    ),
)
@click.option(
    "--style-preset",
    default="commercial",
    type=click.Choice(STYLE_PRESET_OPTIONS),
    help="Style preset (default: commercial — best for product references)",
)
@click.option("--size", default="2K", help="Image size tier (1K, 2K, 3K, 4K)")
@click.option(
    "--ratio",
    default="16:9",
    help=(
        "Aspect ratio (16:9 default; multi-view grid for object/character, full-frame for location)"
    ),
)
@click.option(
    "--model",
    default="agnes-image-2.1-flash",
    help="Agnes image model (2.1-flash default, 2.0-flash for higher quality)",
)
@click.option(
    "--gate/--no-gate",
    "run_gate",
    default=True,
    help="Run the quality gate (AI check) on the generated sheet (default: on)",
)
@click.option(
    "--image",
    "import_image",
    default=None,
    help="Import an existing local image file as the project's primary "
    "reference instead of generating one (issue #23: adopt client-supplied "
    "plates without spending credits).",
)
@click.option(
    "--no-generate",
    "no_generate",
    is_flag=True,
    default=False,
    help="With --image: skip generation entirely and just register the file.",
)
@click.option(
    "--format",
    "ref_format",
    type=click.Choice(["jpg", "png"]),
    default="jpg",
    show_default=True,
    help=(
        "Standardized reference format (issue #41): the plate is converted to "
        "this format and duplicate twins (same stem, other extension) in the "
        "category folder are removed. A resolution sanity warning is printed "
        "for plates smaller than 512px on the short side."
    ),
)
@click.pass_context
def reference(
    ctx: click.Context,
    project_id: str,
    subject_type: str,
    subject: str,
    style_preset: str,
    size: str,
    ratio: str,
    model: str,
    run_gate: bool,
    import_image: str | None,
    no_generate: bool,
    ref_format: str,
) -> None:
    """Generate the primary reference image for a project.

    The primary reference is a GOLD-grade image that locks the appearance of a
    key asset (object, character, location, etc.) across all subsequent
    `brandly video` generations. Should be the FIRST generation step.

    The generated image is saved to
    .brandly/<project_id>/images/<category>/ (e.g. images/prop/ for objects)
    with the prefix `reference_<subject_type>_*` and is auto-detected by
    `brandly video` (auto-injected as the strongest reference image).
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    subject_skill = REFERENCE_SUBJECTS[subject_type]
    prompt = build_reference_prompt(subject_type, subject)
    if not prompt:
        console.print(f"[red]Unknown subject type: {subject_type}[/red]")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Issue #23: import an existing local plate as the primary reference.
    # No generation, no credit spend — just register and lock the file.
    # ------------------------------------------------------------------
    if import_image:
        if not no_generate:
            console.print(
                "[yellow]⚠ --image implies --no-generate: the existing file is "
                "registered as-is (no new image is generated).[/yellow]"
            )
        src = Path(import_image)
        if not src.is_file():
            console.print(f"[red]Image not found: {src}[/red]")
            sys.exit(1)

        root = _get_root(ctx)
        category = layout.image_category_for_subject(subject_type)
        target_dir = layout.media_dir(layout.project_dir(root, project_id), "images", category)
        target_dir.mkdir(parents=True, exist_ok=True)
        stem = sanitize_filename(src.stem) or "plate"
        dest = target_dir / f"reference_{subject_type}_{stem}{src.suffix or '.png'}"
        shutil.copyfile(src, dest)
        dest = _standardize_reference_format(dest, ref_format)
        console.print(f"[green]✓ Imported reference plate:[/green] {dest}")

        from brandly_cli.utils import write_generation_plan

        plan, plan_reused = write_generation_plan(
            project_id,
            "reference",
            root=root,
            prompt=subject,
            model="imported",
            style=style_preset or "default",
            extra_config={
                "subject_type": subject_type,
                "role": "primary_reference",
                "imported_from": str(src),
            },
            source="brandly reference --image",
        )
        console.print(f"[dim]Plan {'reused' if plan_reused else 'written'}: {plan}[/dim]")

        reference_meta = {
            "subject_type": subject_type,
            "skill": subject_skill,
            "subject": subject,
            "image_path": str(dest),
            "source_url": "",
            "generated_at": now_iso(),
            "model": "imported",
            "style_preset": style_preset,
            "imported_from": str(src),
        }
        pm = ProjectManager(root)
        update_result = asyncio.run(
            pm.update(  # type: ignore[arg-type]
                project_id, {"primary_reference": reference_meta}
            )
        )
        if update_result is None:
            console.print("[red]✗ Failed to update project metadata.[/red]")
            sys.exit(1)
        console.print("[green]✓ Project primary_reference metadata updated.[/green]")

        approved, note = _human_review_gate(
            "reference", f"the imported {subject_type} reference for '{subject}'"
        )
        if note:
            _write_review_note(root, project_id, "reference", note, extra=f"subject: {subject}")
        if not approved:
            console.print(
                "[red]✗ Imported reference rejected at the human gate — the "
                "plan stays PENDING; remove it or import a different file.[/red]"
            )
            sys.exit(1)
        console.print("[green]✓ Human gate passed — reference approved.[/green]")

        from brandly_cli.utils import write_generation_doc

        write_generation_doc(
            project_id,
            "reference",
            dest,
            root=root,
            prompt=subject,
            model="imported",
            style=style_preset,
            metadata={
                "subject_type": subject_type,
                "imported_from": str(src),
                "role": "primary_reference",
            },
            source="brandly reference --image",
            plan_file=str(plan),
        )
        console.print(
            f"\n[bold]Next:[/bold] run [cyan]brandly video {project_id} ...[/cyan] — "
            f"the imported reference will be auto-injected as a reference image."
        )
        return

    # Add the project's idea as additional context (for multi-asset campaigns)
    root = _get_root(ctx)
    try:
        proj = asyncio.run(ProjectManager(root).read(project_id))
        if proj and getattr(proj, "description", None):
            prompt += f"\n\nCampaign context: {proj.description}"
    except Exception:
        pass  # project read failure is non-fatal for reference

    # Apply style preset
    prompt = apply_style_preset(prompt, style_preset, media="still") if style_preset else prompt

    # Load subject-skill reference docs for richer prompting
    skill_data = load_sheet_reference(subject_skill, root)
    if skill_data and skill_data.get("references"):
        prompt_variants = skill_data["references"].get("prompt-variants.md", "")
        if prompt_variants:
            prompt += f"\n\n[Reference skill: {subject_skill}]\n{prompt_variants[:500]}"

    # Write pre-generation plan
    from brandly_cli.utils import write_generation_plan

    plan, plan_reused = write_generation_plan(
        project_id,
        "reference",
        root=root,
        prompt=subject,
        model=model,
        style=style_preset or "default",
        extra_config={
            "subject_type": subject_type,
            "size": size,
            "ratio": ratio,
            "role": "primary_reference",
        },
        source="brandly reference",
    )
    console.print(f"[dim]Plan {'reused' if plan_reused else 'written'}: {plan}[/dim]")

    console.print(
        f"[dim]Generating {subject_type} reference with model {model} "
        f"({style_preset} style)...[/dim]"
    )
    console.print(f"[dim]Subject skill: {subject_skill}[/dim]")

    try:
        result = asyncio.run(generate_image(prompt, model=model, size=size, ratio=ratio))
    except Exception as e:
        console.print(f"[red]Error generating reference: {e}[/red]")
        if project_id:
            docs_dir = layout.docs_dir(layout.project_dir(root, project_id), "tmp")
            docs_dir.mkdir(parents=True, exist_ok=True)
            fail_doc = (
                docs_dir / f"reference_fail_{now_iso().replace(':', '-').replace('.', '_')}.md"
            )
            fail_doc.write_text(
                f"# Reference Generation Failed\n\n"
                f"**Subject type:** {subject_type}\n\n**Error:** {e}\n\n"
                f"**Subject:** {subject}\n\n**Status:** FAILED\n",
                encoding="utf-8",
            )
            from brandly_cli.utils import upsert_production_plan

            upsert_production_plan(
                project_id,
                root=root,
                plan_file=str(plan),
                asset_type="reference",
                model=model,
                status="FAILED",
                source="brandly reference",
            )
        sys.exit(1)

    url = result.get("url") or ""
    if not url:
        console.print("[yellow]Reference generated (base64 returned) — no URL to save[/yellow]")
        sys.exit(1)

    from brandly_cli.utils import write_generation_doc

    # Primary references live in images/<category>/ — the matching sub-folder.
    saved = _save_artifact(
        url,
        project_id,
        "images",
        root=root,
        prompt_hint=f"reference_{subject_type}_{subject}",
        category=layout.image_category_for_subject(subject_type),
    )
    if saved:
        # Rename to the conventional sheet name:
        #   character -> char_<name>  ·  location -> loc_<name>  ·  object -> prop_<name>
        timestamp = now_iso().replace(":", "-").replace(".", "_")
        ext = saved.suffix or ".png"
        stem = layout.build_sheet_filename(subject_type, subject, timestamp)
        new_path = saved.parent / f"{stem}{ext}"
        try:
            saved.rename(new_path)
        except OSError:
            new_path = saved  # fall back to the original name if rename fails
        saved = new_path
        saved = _standardize_reference_format(saved, ref_format)
        console.print(f"[green]✓ Reference image saved:[/green] {saved}")

        # Persist the primary reference metadata on the project so downstream
        # tools (e.g. `brandly video`) can read it.
        reference_meta = {
            "subject_type": subject_type,
            "skill": subject_skill,
            "subject": subject,
            "image_path": str(saved),
            "source_url": url,
            "generated_at": now_iso(),
            "model": model,
            "style_preset": style_preset,
        }
        pm = ProjectManager(root)
        result = asyncio.run(
            pm.update(  # type: ignore[arg-type]
                project_id, {"primary_reference": reference_meta}
            )
        )
        if result is None:
            console.print("[red]✗ Failed to update project metadata.[/red]")
            sys.exit(1)
        console.print("[green]✓ Project primary_reference metadata updated.[/green]")

        if run_gate:
            from brandly_cli import quality_gate

            gate_result = asyncio.run(
                quality_gate.verify_element(
                    saved,
                    description=subject,
                    expect_matt_background=True,
                    use_ai=True,
                    root=root,
                    project_id=project_id,
                )
            )
            _print_gate_report(gate_result)
            if gate_result.status == quality_gate.FAIL:
                console.print(
                    "[yellow]⚠ Quality gate failed — review or regenerate the "
                    "sheet before using it as a reference.[/yellow]"
                )

        # Human-in-the-loop gate: confirm the result matches expectations
        approved, note = _human_review_gate(
            "reference", f"the {subject_type} reference for '{subject}'"
        )
        if note:
            _write_review_note(root, project_id, "reference", note, extra=f"subject: {subject}")
        if not approved:
            console.print(
                "[red]✗ Reference rejected at the human gate — adjust the prompt "
                "or subject details and regenerate.[/red]"
            )
            sys.exit(1)
        console.print("[green]✓ Human gate passed — reference approved.[/green]")

        # Only after approval: write the generation doc and flip the plan to
        # COMPLETED in the production plan (a rejection keeps it PENDING so
        # the next run reuses the same plan).
        write_generation_doc(
            project_id,
            "reference",
            saved,
            root=root,
            prompt=prompt,
            model=model,
            style=style_preset,
            metadata={
                "subject_type": subject_type,
                "size": size,
                "ratio": ratio,
                "source_url": url,
            },
            source="brandly reference",
            plan_file=str(plan),
        )

        console.print(
            f"\n[bold]Next:[/bold] run [cyan]brandly video {project_id} ...[/cyan] — the "
            f"primary reference image will be auto-injected as a reference image."
        )
    else:
        console.print("[yellow]⚠ Could not save reference artifact[/yellow]")
        sys.exit(1)


def _probe_image(path: Path) -> tuple[str | None, int | None, int | None]:
    """Best-effort image format + dimensions; Nones when unreadable (issue #73)."""
    try:
        from PIL import Image

        with Image.open(path) as im:
            im.load()
            return im.format or "unknown", im.size[0], im.size[1]
    except Exception:
        return None, None, None


def _print_machine_json(obj: Any) -> None:
    """Emit machine-readable JSON on stdout, verbatim (no rich wrapping).

    Rich console output wraps long lines, which corrupts JSON for machine
    consumers — issue #73 requires stdout to parse as exactly one JSON
    document.
    """
    print(json.dumps(obj, indent=2, ensure_ascii=False))


@click.command()
@click.option("--project-id", default=None, help="Optional project UUID")
@click.option("--prompt", "-p", required=True, help="Image generation prompt")
@click.option(
    "--model",
    default="agnes-image-2.5-flash",
    help="Agnes image model (2.5-flash is the current default)",
)
@click.option("--size", default="2K", help="Image size tier (1K, 2K, 3K, 4K)")
@click.option("--ratio", default="16:9", help="Aspect ratio")
@click.option(
    "--style-preset",
    default=None,
    type=click.Choice(STYLE_PRESET_OPTIONS),
    help="Style preset to avoid AI slop",
)
@click.option(
    "--output",
    "output",
    default=None,
    type=click.Path(),
    help="Explicit destination file for the generated image. The image is "
    "downloaded atomically, validated as a supported image format, and "
    "written to exactly this path (issue #73).",
)
@click.option(
    "--json",
    "json_out",
    is_flag=True,
    help="Emit only a machine-readable JSON result (success object or "
    "structured error) instead of human-readable console output (issue #73).",
)
@click.pass_context
def image(
    ctx: click.Context,
    project_id: str | None,
    prompt: str,
    model: str,
    size: str,
    ratio: str,
    style_preset: str | None,
    output: str | None,
    json_out: bool,
) -> None:
    """Generate an image via Agnes AI."""
    # Issue #73: in --json mode, suppress rich console output entirely
    # (including client-level progress/warning prints) so stdout carries
    # only the machine-readable result object. Restored right before the
    # JSON emission (which itself goes through the rich console).
    quiet_original = console.quiet
    if json_out:
        console.quiet = True

    enhanced = apply_style_preset(prompt, style_preset, media="still") if style_preset else prompt

    # Try to load sheet reference for better prompting if project has context
    root = _get_root(ctx)
    if project_id:
        skill_names = [
            "brandly-vehicle-sheet",
            "brandly-character-sheet",
            "brandly-object-sheet",
            "brandly-location-sheet",
            "brandly-animal-sheet",
            "brandly-plant-sheet",
            "brandly-mecha-sheet",
        ]
        for skill in skill_names:
            sheet = load_sheet_reference(skill, root)
            if sheet and sheet["references"]:
                sheet_hint = sheet["references"].get("prompt-variants.md", "")
                if sheet_hint:
                    enhanced += f"\n\n[Sheet reference from {skill}]\n{sheet_hint[:300]}"
                    console.print(f"[dim]Loaded sheet reference: {skill}[/dim]")
                    break

        # Also auto-detect existing artifacts as references
        auto_refs = get_reference_image_urls(project_id, root)
        if auto_refs:
            enhanced += (
                f"\n\nReference images ({len(auto_refs)}): "
                "Use these as visual guides for consistency."
            )
            console.print(f"[dim]Found {len(auto_refs)} artifact(s) for reference[/dim]")

    # Write pre-generation plan BEFORE API call
    plan_file_ref: str | None = None
    if project_id:
        from brandly_cli.utils import write_generation_plan

        plan, plan_reused = write_generation_plan(
            project_id,
            "image",
            root=root,
            prompt=prompt,
            model=model,
            style=style_preset or "default",
            extra_config={"size": size, "ratio": ratio},
            source="brandly image",
        )
        plan_file_ref = str(plan)
        console.print(f"[dim]Plan {'reused' if plan_reused else 'written'}: {plan}[/dim]")

    console.print(
        f"[dim]Generating image with model {model} ({style_preset or 'default'} style)...[/dim]"
    )

    try:
        result = asyncio.run(generate_image(enhanced, model=model, size=size, ratio=ratio))
    except Exception as e:
        if json_out:
            console.quiet = quiet_original
            _print_machine_json(
                {
                    "status": "error",
                    "error_code": "provider_error",
                    "error_message": str(e),
                    "task_id": None,
                }
            )
            sys.exit(1)
        console.print(f"[red]Error generating image: {e}[/red]")
        if project_id:
            # Update plan to show failure
            from brandly_cli.utils import write_generation_doc

            docs_dir = layout.docs_dir(layout.project_dir(root, project_id), "tmp")
            docs_dir.mkdir(parents=True, exist_ok=True)
            fail_doc = docs_dir / f"image_fail_{now_iso().replace(':', '-').replace('.', '_')}.md"
            fail_doc.write_text(
                f"# Image Generation Failed\n\n"
                f"**Error:** {e}\n\n**Prompt:** {prompt}\n\n**Status:** FAILED\n",
                encoding="utf-8",
            )
            from brandly_cli.utils import upsert_production_plan

            if plan_file_ref:
                upsert_production_plan(
                    project_id,
                    root=root,
                    plan_file=plan_file_ref,
                    asset_type="image",
                    model=model,
                    status="FAILED",
                    source="brandly image",
                )
        sys.exit(1)

    url = result.get("url") or ""
    b64 = result.get("b64_json") or ""
    task_id = result.get("task_id")
    saved: Path | None = None
    fmt: str | None = None
    width: int | None = None
    height: int | None = None

    if output:
        # Issue #73: explicit output path — atomic download + full-decode
        # validation. A partial file is never left at the requested path.
        from brandly_cli.io import ImageFetchError, fetch_image_atomic

        if not url and not b64:
            payload_error = "Provider returned no image payload (no URL, no base64)."
            if json_out:
                console.quiet = quiet_original
                _print_machine_json(
                    {
                        "status": "error",
                        "error_code": "no_image",
                        "error_message": payload_error,
                        "task_id": task_id,
                    }
                )
            else:
                console.print(f"[red]✗ {payload_error}[/red]")
            sys.exit(1)

        dest = Path(output).expanduser()
        try:
            info = fetch_image_atomic(url or None, dest, b64_json=b64 or None)
        except ImageFetchError as e:
            if json_out:
                console.quiet = quiet_original
                _print_machine_json(
                    {
                        "status": "error",
                        "error_code": "image_download_failed",
                        "error_message": str(e),
                        "task_id": task_id,
                    }
                )
            else:
                console.print(f"[red]✗ {e}[/red]")
            sys.exit(1)
        saved = Path(info["path"])
        fmt = info["format"]
        width = info["width"]
        height = info["height"]
        if not json_out:
            console.print(f"[green]✓ Image written to: {saved}[/green]")
        if project_id:
            from brandly_cli.utils import write_generation_doc

            write_generation_doc(
                project_id,
                "image",
                saved,
                root=root,
                prompt=enhanced,
                model=model,
                style=style_preset,
                metadata={"size": size, "ratio": ratio, "source_url": url or None},
                source="brandly image",
                plan_file=plan_file_ref,
            )
    elif url:
        console.print(f"[green]✓ Image generated:[/green] {url}")
        if project_id:
            # Always save to disk, under the selected project context
            saved = _save_artifact(url, project_id, "images", root=root, prompt_hint=prompt)
            if saved:
                fmt, width, height = _probe_image(saved)
                console.print(f"  Saved → {saved}")
                # Write generation document
                from brandly_cli.utils import write_generation_doc

                write_generation_doc(
                    project_id,
                    "image",
                    saved,
                    root=root,
                    prompt=enhanced,
                    model=model,
                    style=style_preset,
                    metadata={"size": size, "ratio": ratio, "source_url": url},
                    source="brandly image",
                    plan_file=plan_file_ref,
                )
                console.print(f"  Doc → {saved.parent.parent / 'docs'}")
            else:
                console.print("[yellow]⚠ Could not save artifact, but URL is available[/yellow]")
        else:
            # Issue #75: no intentional project context. This branch used to
            # fall back to an implicit "untitled" project and write media +
            # generation docs under that phantom project dir. Instead, report
            # the context explicitly and create nothing.
            console.print(
                "[dim]No --project-id was selected, so this image is not recorded "
                "under any project (no metadata written). Use --output <path> to "
                "save it externally, or --project-id <id> to record it under a "
                "project.[/dim]"
            )
    else:
        console.print("[yellow]Image generated (base64 returned)[/yellow]")
        if project_id:
            from brandly_cli.utils import write_generation_doc

            write_generation_doc(
                project_id,
                "image",
                Path("base64_output"),
                root=root,
                prompt=enhanced,
                model=model,
                style=style_preset,
                metadata={"size": size, "ratio": ratio, "note": "base64 output"},
                source="brandly image",
                plan_file=plan_file_ref,
            )

    if project_id:
        root = _get_root(ctx)
        pm = ProjectManager(root)
        asyncio.run(
            pm.update(
                project_id,
                {
                    "image_analysis": {
                        "generated_url": url,
                        "prompt": prompt,
                        "enhanced_prompt": enhanced,
                        "style_preset": style_preset,
                        "model": model,
                        "generated_at": now_iso(),
                    }
                },
            )
        )
        # Auto-record credit spend so budget gates can fire.
        _record_media_spend(root, project_id, "image", model)

    # Issue #73: machine-readable terminal state (reached only on success —
    # all error paths above exit with their own structured/text error).
    if json_out:
        console.quiet = quiet_original
        _print_machine_json(
            {
                "status": "success",
                "task_id": task_id,
                "provider_url": url or None,
                "path": str(saved) if saved is not None else None,
                "format": fmt,
                "width": width,
                "height": height,
                "model": model,
                "generated_at": result.get("generated_at"),
            }
        )
    else:
        _print_json(result)


@click.command()
@click.argument("project_id")
@click.option("--prompt", "-p", required=True, help="Video generation prompt")
@click.option(
    "--model",
    default="agnes-video-2.5-flash",
    help="Agnes video model (2.5-flash is the current default; 720P, 4-12s)",
)
@click.option(
    "--style",
    default="cinematic",
    type=click.Choice(list_video_styles()),
    help="Video style preset for consistent output",
)
@click.option(
    "--mode",
    default="auto",
    type=click.Choice(["auto", "text", "keyframe", "reference"]),
    help=(
        "Generation mode. 'auto' (default) infers it: keyframe when a start/"
        "end frame is provided, reference when reference images are provided, "
        "text otherwise."
    ),
)
@click.option("--duration", "-d", default=10, help="Duration in seconds (default: 10)")
@click.option("--aspect-ratio", default="16:9", help="Aspect ratio")
@click.option(
    "--first-frame", default=None, help="Start frame image URL or local file path (keyframe mode)"
)
@click.option(
    "--last-frame", default=None, help="End frame image URL or local file path (keyframe mode)"
)
@click.option(
    "--reference-images",
    "-r",
    default=None,
    help="Comma-separated image URLs or local file paths for character/object consistency (reference mode)",
)
@click.option(
    "--character",
    "-c",
    default=None,
    help="Character description for identity locking (e.g. 'woman in red dress, blonde hair')",
)
@click.option(
    "--wait/--no-wait",
    "wait",
    default=True,
    help="Poll until generation completes and download the video to disk (default: on)",
)
@click.option("--max-wait", default=600, help="Max wait seconds (default: 600)")
@click.option(
    "--require-reference/--no-require-reference",
    "require_reference",
    default=False,
    help="If set, fail when project has no primary reference image.",
)
@click.option(
    "--allow-referenceless",
    "allow_referenceless",
    is_flag=True,
    help="Bypass the require-reference check (escape hatch for re-runs/edge cases).",
)
@click.option(
    "--gate/--no-gate",
    "run_gate",
    default=True,
    help="Run the quality gate on the generated video (default: on)",
)
@click.option(
    "--reference-audios",
    default=None,
    help="Comma-separated reference audio URLs (reference mode)",
)
@click.option(
    "--no-auto-refs",
    "auto_refs_enabled",
    flag_value=False,
    default=True,
    help="Do NOT auto-inject every project image as a reference (issue #20: "
    "prevents payload bloat and style bleed between visual worlds).",
)
@click.option(
    "--scene",
    type=int,
    default=None,
    help="Scene number for the deterministic clip name "
    "(Scene-<scene:02d>-Shot-<scene>-<shot>.mp4). Needs --shot.",
)
@click.option(
    "--shot",
    "shot_number",
    type=int,
    default=None,
    help="Shot number inside --scene (the trailing number of the clip name).",
)
@click.option(
    "--auto-ref-category",
    default=None,
    help="Scope auto-injected references to one image category "
    "(e.g. 'prop', 'character', 'location') instead of all images.",
)
@click.option(
    "--open-ui",
    is_flag=True,
    default=False,
    help="Open the timeline editor UI after generation completes.",
)
@click.pass_context
def video(
    ctx: click.Context,
    project_id: str,
    prompt: str,
    model: str,
    style: str,
    mode: str,
    duration: int,
    aspect_ratio: str,
    first_frame: str | None,
    last_frame: str | None,
    reference_images: str | None,
    character: str | None,
    wait: bool,
    max_wait: int,
    require_reference: bool | None,
    allow_referenceless: bool,
    run_gate: bool,
    reference_audios: str | None,
    auto_refs_enabled: bool,
    auto_ref_category: str | None,
    scene: int | None,
    shot_number: int | None,
    open_ui: bool,
    expected_characters: tuple[str, ...] | None = None,
) -> None:
    """Generate an AI video via Agnes AI.

    For best results, the project should have a primary reference image
    generated first via `brandly reference`. The reference is auto-injected
    as the FIRST reference image (strongest influence). Use --require-reference
    to fail if the reference is missing.

    By default the command polls until generation completes and downloads
    the video to .brandly/<project>/videos/scenes/ (disable with --no-wait).

    Mode is auto-inferred unless --mode is given explicitly:
    text (no image inputs) → reference (reference images provided) →
    keyframe (start/end frame provided).
    """
    if not is_valid_project_id(project_id):
        console.print("[red]Invalid project ID format.[/red]")
        sys.exit(1)

    if (scene is None) != (shot_number is None):
        console.print(
            "[yellow]⚠ --scene and --shot must be used together — using the "
            "default (timestamped) clip name.[/yellow]"
        )

    # Auto-detect project artifacts as additional reference images
    root = _get_root(ctx)
    # Enforce: production plan must exist before video generation (director → prompt phase).
    from brandly_cli.planning import production_plan_path

    plan_path = production_plan_path(project_id, root=root)
    if not plan_path.exists():
        console.print(
            "[red]⚠ Production plan missing — run director before video.[/red]\n"
            f"  Required: {plan_path.relative_to(root)}\n"
            "  Generate it first:\n"
            "    brandly director\n"
            "  Then proceed with video generation:\n"
            f"    brandly video {project_id} --prompt '...'"
        )
        sys.exit(1)
    auto_refs = get_reference_image_urls(project_id, root) if auto_refs_enabled else []
    # Issue #20: optionally scope auto-injected references to one category
    # (e.g. images/prop/, images/location/) so each scene is anchored to
    # exactly its own plates instead of receiving the whole images tree.
    if auto_ref_category:
        marker = f"images{os.sep}{auto_ref_category}{os.sep}"
        auto_refs = [p for p in auto_refs if marker in p or f"images/{auto_ref_category}/" in p]
        if not auto_refs:
            console.print(
                f"[yellow]⚠ No images found in category '{auto_ref_category}' — "
                "auto references are empty for this run.[/yellow]"
            )

    # Read the project's primary_reference metadata (set by `brandly reference`)
    reference: dict[str, Any] | None = _load_project_reference(project_id, root)

    # Build the list of paths to pass as the FIRST reference (strongest influence).
    # Include the local file path (if on disk) and the source URL (if any).
    ref_paths: list[str] = []
    if reference is not None:
        path = reference.get("image_path", "")
        if path and Path(path).exists():
            ref_paths.append(path)
        src_url = reference.get("source_url", "")
        if src_url:
            ref_paths.append(src_url)
        if not ref_paths:
            reference = None  # stale metadata, no usable path

    missing = reference is None
    if missing and not allow_referenceless:
        next_cmd = (
            f"brandly reference {project_id} --subject-type object "
            f"--subject '<product/character/location description>'"
        )
        if require_reference:
            console.print(
                f"[red]⚠ No primary reference for project {project_id}.[/red]\n"
                f"  Video generation without a reference produces high-drift output.\n"
                f"  Generate one first:\n"
                f"    [cyan]{next_cmd}[/cyan]\n"
            )
            console.print(
                "[red]Aborting because --require-reference was set. "
                "Use --allow-referenceless to override.[/red]"
            )
            sys.exit(2)
        else:
            console.print(
                f"[yellow]⚠ No primary reference for project {project_id}.[/yellow]\n"
                f"  Video generation without a reference produces high-drift output.\n"
                f"  Generate one first:\n"
                f"    [cyan]{next_cmd}[/cyan]\n"
            )
            console.print(
                "[dim]Continuing without reference. Pass --require-reference to "
                "enforce, --allow-referenceless to silence this warning.[/dim]"
            )
    elif reference is not None:
        ref_name = Path(ref_paths[0]).name if ref_paths else reference.get("source_url", "")[:50]
        console.print(
            f"[green]✓ Primary reference:[/green] "
            f"{reference.get('subject_type', 'unknown')} ({ref_name})"
        )

    # Merge references: primary reference first (strongest influence),
    # then user-supplied, then auto-detected artifacts.
    user_imgs = (
        [u.strip() for u in reference_images.split(",") if u.strip()] if reference_images else []
    )
    imgs = ref_paths + user_imgs + auto_refs

    # Parse reference audio URLs
    auds = (
        [u.strip() for u in reference_audios.split(",") if u.strip()] if reference_audios else None
    )

    # Enhance prompt with style and character consistency
    # Scene-aware boilerplate (issue #32): if the prompt already specifies
    # its own lighting/grade/style, the generic preset lines are not
    # appended — they would overwrite the shot's correct film direction.
    from brandly_cli.video_prompts import detect_scene_direction

    enhanced = build_enhanced_video_prompt(
        prompt, style, character=character, reference_images=imgs, **detect_scene_direction(prompt)
    )

    # Try to load sheet reference for better prompting
    skill_names = [
        "brandly-vehicle-sheet",
        "brandly-character-sheet",
        "brandly-object-sheet",
        "brandly-location-sheet",
        "brandly-animal-sheet",
        "brandly-plant-sheet",
        "brandly-mecha-sheet",
    ]
    sheet_hint = ""
    loaded_skill = "none"
    for skill in skill_names:
        sheet = load_sheet_reference(skill, root)
        if sheet and sheet["references"]:
            sheet_hint = sheet["references"].get("prompt-variants.md", "")
            if sheet_hint:
                enhanced += f"\n\n[Sheet reference from {skill}]\n{sheet_hint[:500]}"
                loaded_skill = skill
            break

    console.print(f"[dim]Creating video task with model {model} (style: {style})...[/dim]")
    # Note: 2.5-flash is the only Agnes video model; rate-limited (1 req/min)
    console.print(f"[dim]Model: {model} | Style: {style} | Mode: {mode}[/dim]")
    if character:
        console.print(f"[dim]Character anchor: {character[:60]}...[/dim]")
    if imgs:
        console.print(f"[dim]Reference images: {len(imgs)}[/dim]")
    if sheet_hint:
        console.print(f"[dim]Loaded sheet reference: {loaded_skill}[/dim]")

    # Write pre-generation plan BEFORE API call
    from brandly_cli.utils import write_generation_plan

    plan, plan_reused = write_generation_plan(
        project_id,
        "video",
        root=root,
        prompt=prompt,
        model=model,
        style=style,
        extra_config={
            "mode": mode,
            "duration": f"{duration}s",
            "aspect_ratio": aspect_ratio,
            "reference_images": len(imgs),
            "sheet_reference": loaded_skill,
        },
        source="brandly video",
    )
    console.print(f"[dim]Plan {'reused' if plan_reused else 'written'}: {plan}[/dim]")

    # Archive local keyframes into the project (images/keyframe/)
    if project_id and (first_frame or last_frame) and mode in ("auto", "keyframe"):
        for label, frame in (("start_frame", first_frame), ("end_frame", last_frame)):
            if not frame:
                continue
            frame_path = Path(frame)
            if not frame_path.is_file():
                continue  # remote URL or missing local file
            keyframe_dir = layout.resolve_media_root(root, project_id, "images") / "keyframe"
            keyframe_dir.mkdir(parents=True, exist_ok=True)
            slug = layout.image_name_token(frame_path.stem) or "frame"
            target = keyframe_dir / f"{label}_{slug}{frame_path.suffix or '.png'}"
            try:
                shutil.copyfile(frame_path, target)
                console.print(f"[dim]Keyframe archived: {target}[/dim]")
            except OSError:
                pass

    try:
        # Issue #21 + provider demotion: the preset follows --style instead of
        # being hardcoded — cinematic only for cinematic; disabled for
        # non-photographic styles (sumi-e ink, cel animation, ...). Applied
        # here (prompt layer) because providers no longer import style_presets.
        if style == "cinematic":
            enhanced = apply_style_preset(enhanced, "cinematic")
        task = asyncio.run(
            create_video_task(
                enhanced,
                model=model,
                mode=mode,
                duration=duration,
                aspect_ratio=aspect_ratio,
                first_frame=first_frame,
                last_frame=last_frame,
                reference_images=imgs if imgs else None,
                reference_audios=auds,
            )
        )
    except Exception as e:
        # Issue #24: never print an empty message — show the exception type
        # and whatever detail we have (timeout exceptions often have none).
        detail = str(e).strip()
        console.print(
            f"[red]Error creating video task: {type(e).__name__}: "
            f"{detail or '(no error message — likely a timeout; see retry log above)'}"
            f"[/red]"
        )
        console.print(
            "[dim]Tip: large reference payloads can time out the create endpoint — "
            "references are now auto-converted to smaller webp/jpeg copies; use "
            "--no-auto-refs / --auto-ref-category to slim the request further.[/dim]"
        )
        from brandly_cli.utils import upsert_production_plan

        upsert_production_plan(
            project_id,
            root=root,
            plan_file=str(plan),
            asset_type="video",
            model=model,
            status="FAILED",
            source="brandly video",
        )
        sys.exit(1)

    video_id = task["video_id"]
    console.print(f"[green]✓ Task created:[/green] {video_id}")
    console.print(f"  Status: {task['status']}  Progress: {task['progress']}%")
    if task.get("mode"):
        mode = task["mode"]
        console.print(f"  Mode: {mode}")

    if wait:
        console.print(f"[dim]Polling (max {max_wait}s)...[/dim]")
        try:
            result = asyncio.run(poll_video(video_id, max_wait_seconds=max_wait, model_name=model))
        except TimeoutError as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print(
                f"[dim]Video ID: {video_id} — run "
                f"'brandly job-resume {video_id} --project-id {project_id}' to poll later.[/dim]"
            )
            # Update plan to show timeout
            from brandly_cli.utils import (
                upsert_production_plan,
                write_generation_doc,
            )

            write_generation_doc(
                project_id,
                "video",
                Path("timeout"),
                root=root,
                prompt=enhanced,
                model=model,
                style=style,
                metadata={"video_id": video_id, "status": "timeout", "error": str(e)},
                source="brandly video",
            )
            upsert_production_plan(
                project_id,
                root=root,
                plan_file=str(plan),
                asset_type="video",
                model=model,
                status="FAILED",
                source="brandly video",
            )
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error polling video: {e}[/red]")
            sys.exit(1)

        url = result.get("url") or ""
        console.print(f"[green]✓ Video ready:[/green] {url or 'no URL'}")
        task["url"] = url
        task["final_status"] = result.get("status")
        # Always save video to disk if URL exists
        if url:
            clip_name = (
                shot_runner.clip_filename(scene, shot_number)
                if scene is not None and shot_number is not None
                else None
            )
            saved = _save_artifact(
                url,
                project_id,
                "videos",
                root=root,
                prompt_hint=prompt,
                category="scenes",
                filename=clip_name,
            )
            if saved:
                console.print(f"  Saved → {saved}")
                # Record the job so `brandly job-resume <id>` can locate the project.
                # (The generation doc + plan COMPLETED upsert happen after the
                # human gate approves, or later via `job-resume`.)
                pm = ProjectManager(root)
                asyncio.run(
                    pm.update(
                        project_id,
                        {
                            "last_video_job": {
                                "video_id": video_id,
                                "url": url,
                                "saved_path": str(saved),
                                "mode": mode,
                                "model": model,
                                "created_at": now_iso(),
                            }
                        },
                    )
                )
            else:
                console.print("[yellow]⚠ Could not save artifact, but URL is available[/yellow]")
    else:
        console.print(
            f"[dim]Not waiting (use --wait to poll). To download when the video "
            f"is ready, run:\n  brandly job-resume {video_id} --project-id {project_id}[/dim]"
        )

    # Quality gate: verify the generated video before the next step.
    if run_gate:
        from brandly_cli import quality_gate

        _saved_media = locals().get("saved")
        if isinstance(_saved_media, Path) and _saved_media.exists():
            gate_result = asyncio.run(
                quality_gate.verify_element(
                    _saved_media,
                    description=character or prompt,
                    expect_matt_background=False,
                    use_ai=True,
                    root=root,
                    project_id=project_id,
                    # Issue #51: when 2+ characters co-appear, ask the gate
                    # to verify each is rendered distinctly (not the
                    # dominant reference's face on every figure).
                    expected_characters=list(expected_characters or []),
                )
            )
            _print_gate_report(gate_result)
            if gate_result.status == quality_gate.FAIL:
                console.print(
                    "[yellow]⚠ Quality gate failed — review or regenerate "
                    "before editing/publishing.[/yellow]"
                )

    # Human-in-the-loop gate: confirm the video before the next step
    # (only when an artifact was actually downloaded and saved).
    _media_local = locals().get("saved")
    _media_local = (
        _media_local if isinstance(_media_local, Path) and _media_local.exists() else None
    )
    if _media_local:
        approved, note = _human_review_gate("video", f"video {video_id} ({_media_local.name})")
        if note:
            _write_review_note(root, project_id, "video", note, extra=f"video_id: {video_id}")
        if not approved:
            console.print(
                "[red]✗ Video rejected at the human gate — regenerate with an "
                "adjusted prompt (the plan is reused until the config changes).[/red]"
            )
            sys.exit(1)
        console.print("[green]✓ Human gate passed — video approved.[/green]")

        # Only after approval: write the generation doc and flip the plan to
        # COMPLETED in the production plan.
        from brandly_cli.utils import write_generation_doc

        write_generation_doc(
            project_id,
            "video",
            _media_local,
            root=root,
            prompt=enhanced,
            model=model,
            style=style,
            metadata={
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "source_url": url,
                "video_id": video_id,
            },
            source="brandly video",
            plan_file=str(plan),
        )
        console.print(f"  Doc → {_media_local.parent.parent / 'docs'}")

    # Persist to project
    root = _get_root(ctx)
    pm = ProjectManager(root)
    asyncio.run(pm.update(project_id, {"current_phase": "asset"}))
    # Auto-record credit spend so budget gates can fire.
    _record_media_spend(root, project_id, "video", model)

    _print_json(task)

    # Open UI if requested
    if open_ui:
        console.print("[dim]Opening timeline editor...[/dim]")
        try:
            import threading

            from brandly_cli.web import start_server

            def _open_ui():
                import time

                time.sleep(1)  # give server a moment to start
                start_server(str(root), port=8765, open_browser=True)

            t = threading.Thread(target=_open_ui, daemon=True)
            t.start()
        except ImportError:
            console.print(
                "[yellow]Web UI not available — install with: pip install brandly-cli[web][/yellow]"
            )


@click.command()
@click.option("--subject", "-s", required=True, help="Main subject (person, product, or object)")
@click.option("--action", "-a", required=True, help="What the subject does")
@click.option("--environment", "-e", required=True, help="Where the scene takes place")
@click.option("--shots", "-n", default=3, help="Number of shots (1-6, default: 3)")
@click.option(
    "--style",
    "-st",
    default="cinematic",
    type=click.Choice(list_video_styles()),
    help="Video style preset",
)
@click.option("--character", "-c", default=None, help="Character description for identity locking")
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Choice(["text", "code"]),
    help="Output format (default: text)",
)
@click.pass_context
def prompt(
    ctx: click.Context,
    subject: str,
    action: str,
    environment: str,
    shots: int,
    style: str,
    character: str | None,
    output: str | None,
) -> None:
    """Generate a cinematic video prompt for Agnes AI."""
    if shots < 1 or shots > 6:
        console.print("[red]Shots must be between 1 and 6.[/red]")
        sys.exit(1)

    if shots == 1:
        result = build_single_shot_prompt(
            subject=subject,
            action=action,
            environment=environment,
            style=style,
            character_description=character,
        )
    else:
        result = build_video_prompt(
            subject=subject,
            action=action,
            environment=environment,
            shots=shots,
            style=style,
            character_description=character,
        )

    console.print(
        f"\n[bold]Generated Prompt — {shots} shot"
        f"{'s' if shots > 1 else ''} ({style} style)[/bold]\n"
    )
    console.print(result)
    console.print("\n[dim]Tip: Use this prompt with 'brandly video' or copy it directly.[/dim]")


@click.command()
@click.option("--project-id", default=None, help="Optional project UUID")
@click.option("--prompt", "-p", required=True, help="Music description prompt")
@click.option("--model", default="music-3.0", help="Music generation model (music-3.0, music-2.6)")
@click.option("--duration", "-d", default=30, help="Duration in seconds")
@click.option("--instrumental", is_flag=True, default=True, help="Instrumental only")
@click.option("--lyrics", default=None, help="Song lyrics (\\n separated, max 3500 chars)")
@click.pass_context
def music(
    ctx: click.Context,
    project_id: str | None,
    prompt: str,
    model: str,
    duration: int,
    instrumental: bool,
    lyrics: str | None,
) -> None:
    """Generate background music via MiniMax Audio."""
    console.print(f"[dim]Generating music ({model}, {duration}s)...[/dim]")
    result = asyncio.run(
        generate_music(
            prompt, model=model, duration_seconds=duration, instrumental=instrumental, lyrics=lyrics
        )
    )
    url = result.get("url") or ""
    if url:
        console.print(f"[green]✓ Music generated:[/green] {url}")
        # Save to disk
        pid = project_id or ""
        root = _get_root(ctx)
        saved = _save_artifact(
            url, pid, "audio", root=root, prompt_hint=prompt, category="soundtrack"
        )
        if saved:
            console.print(f"  Saved → {saved}")
    _print_json(result)


@click.command()
@click.option("--project-id", default=None, help="Optional project UUID")
@click.argument("text")
@click.option("--model", default="speech-2.8-hd", help="TTS model")
@click.option(
    "--voice-id",
    default="English_Insightful_Speaker",
    help="Voice ID (e.g. English_Insightful_Speaker)",
)
@click.option("--speed", default=1.0, help="Speech speed (0.5–2.0)")
@click.option("--vol", default=1.0, help="Volume (0.1-2.0)")
@click.option(
    "--pitch", default=0, type=click.IntRange(-12, 12), help="Pitch shift in semitones (-12 to 12)"
)
@click.option("--emotion", default=None, help="Emotion tag: happy, sad, angry, fearful, neutral")
@click.pass_context
def tts(
    ctx: click.Context,
    project_id: str | None,
    text: str,
    model: str,
    voice_id: str,
    speed: float,
    vol: float,
    pitch: int,
    emotion: str | None,
) -> None:
    """Generate voiceover via MiniMax TTS."""
    console.print(f"[dim]Generating TTS ({model}, voice={voice_id})...[/dim]")
    result = asyncio.run(
        generate_tts(
            text,
            model=model,
            voice_id=voice_id,
            speed=speed,
            vol=vol,
            pitch=pitch,
            emotion=emotion,
        )
    )
    url = result.get("url") or ""
    if url:
        console.print(f"[green]✓ Voiceover generated:[/green] {url}")
        # Save to disk
        pid = project_id or ""
        root = _get_root(ctx)
        saved = _save_artifact(
            url,
            pid,
            "audio",
            root=root,
            prompt_hint=text[:60],
            category="voiceover",
        )
        if saved:
            console.print(f"  Saved → {saved}")
    _print_json(result)


@click.command(name="voices")
@click.pass_context
def voices_cmd(ctx: click.Context) -> None:
    """List available TTS voices."""
    results = asyncio.run(list_voices())
    if results:
        table = Table(title="MiniMax TTS Voices")
        table.add_column("Voice ID", style="cyan")
        table.add_column("Language", style="white")
        table.add_column("Gender", style="dim")
        for v in results:
            table.add_row(v.get("voice_id", ""), v.get("language", ""), v.get("gender", ""))
        console.print(table)
    else:
        console.print("[dim]No voices found or API not configured.[/dim]")


@click.command()
@click.pass_context
def director(ctx: click.Context) -> None:
    """Show the Director prompt for AI tools."""
    prompt = get_director_prompt()
    console.print(Panel(Markdown(prompt), title="Brandly Director Mode"))


# ---------------------------------------------------------------------------
# Produce-runner helpers (moved out of cli.py — P2-8; sibling of the `video`
# command so _generate_shot can ctx.invoke it without a cli -> cmd.generation edge)
# ---------------------------------------------------------------------------


def _presence_character(shot: dict[str, Any]) -> str | None:
    """Character anchor from a flat shot dict (issue #38): explicit
    ``character`` wins; else the shot's ``characters`` presence declaration
    (list or comma-separated string)."""
    if shot.get("character"):
        return str(shot["character"])
    chars = shot.get("characters")
    if isinstance(chars, str):
        chars = [c.strip() for c in chars.split(",") if c.strip()]
    if isinstance(chars, (list, tuple)) and chars:
        return ", ".join(str(c) for c in chars)
    return None


def _expected_character_names(shot: dict[str, Any]) -> list[str] | None:
    """Distinct co-appearing character *names* for the identity-bleed gate
    check (issue #51).

    Returns a list of names when 2+ characters are declared present in the
    shot (via the ``characters`` presence key — a list or a comma-separated
    string), else ``None``. A single-character or object shot gets ``None``
    so the gate prompt is unchanged. The names are taken from the leading
    token of each declared character (the part before the first comma in a
    descriptor like "Silas Vanesky, 62, gaunt white man..."), which is what
    the vision prompt uses to refer to each figure.
    """
    chars = shot.get("characters")
    if isinstance(chars, str):
        chars = [c.strip() for c in chars.split(",") if c.strip()]
    if not isinstance(chars, (list, tuple)) or len(chars) < 2:
        return None
    names = []
    for c in chars:
        c = str(c).strip()
        if not c:
            continue
        # If the entry is a short name (no descriptor comma), use it whole;
        # otherwise use the first clause before a descriptive comma run. A
        # simple heuristic: take the text up to the first ", " that is
        # followed by a digit (age descriptor) OR keep the whole token when
        # it is short (<= 3 words).
        first = c.split(",")[0].strip()
        names.append(first if first else c)
    # De-dup while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out or None


def _generate_shot(
    project_id: str,
    shot: dict[str, Any],
    *,
    ctx: click.Context,
    root: Path,
    auto_refs_enabled: bool = True,
    allow_referenceless: bool = False,
    max_wait: int = 600,
    scene: int | None = None,
    shot_number: int | None = None,
) -> bool:
    """Generate ONE shot through the standard ``brandly video`` pipeline.

    This keeps every per-shot safeguard: pre-generation plan, quality gate,
    human gate, generation doc and credit recording. Returns True when the
    shot finished successfully.
    """
    references = shot.get("references")
    if isinstance(references, list):
        references = ",".join(str(r) for r in references if str(r).strip())

    try:
        ctx.invoke(
            video,
            project_id=project_id,
            prompt=str(shot.get("prompt", "")),
            duration=int(shot.get("duration", 5)),
            style=str(shot.get("style", "cinematic")),
            reference_images=references or None,
            # Issue #38: presence-declared characters only — either a single
            # string anchor or the shot's comma-separated/listed roster.
            character=_presence_character(shot),
            wait=True,
            max_wait=max_wait,
            require_reference=False,
            auto_refs_enabled=auto_refs_enabled,
            allow_referenceless=allow_referenceless,
            scene=scene,
            shot_number=shot_number,
            # Issue #51: when the shot declares 2+ co-appearing characters,
            # hand their names to the gate so it can flag cross-character
            # identity bleed (the dominant face painted onto every figure).
            expected_characters=tuple(_expected_character_names(shot) or ()),
        )
    except SystemExit as exc:
        return exc.code in (0, None)
    return True


def _run_produce_runner(
    ctx: click.Context,
    project_id: str,
    data: dict[str, Any] | list[dict[str, Any]],
    root: Path,
    interval: float,
    no_auto_refs: bool,
    character: str | None,
    allow_referenceless: bool,
    max_wait: int,
    only: tuple[str, ...],
    max_shots: int,
    *,
    retries: int = 0,
    split_long_shots: bool = False,
    aspect_ratio: str | None = None,
    no_plan: bool = False,
) -> None:
    """Progress-file runner path for ``brandly produce`` (see produce())."""
    project_dir = layout.resolve_project_dir(root, project_id)
    # v2-aware roots (issue #43): migrated projects keep media next to
    # .brandly/ — pre-production/<p>/ for plates, production/<p>/videos/ for clips.
    images_dir = layout.resolve_media_root(root, project_id, "images")
    videos_root = layout.resolve_media_root(root, project_id, "videos")
    scenes_dir = videos_root / "scenes"
    progress = shot_runner.ProgressLog(
        layout.docs_dir(project_dir, "tmp") / shot_runner.PROGRESS_FILENAME
    )
    shots = shot_runner.flatten_shots(data, images_dir, character=character)

    # Issue #35: duration validation at plan time. Agnes clamps every take
    # to ~5-6s regardless of the requested duration, so shots longer than
    # one segment burn full credits for a clamped result. --split-long-shots
    # slices them instead of letting the model silently clamp them.
    over = [s for s in shots if s.duration > shot_runner.SPLIT_SEGMENT_DURATION]
    if over:
        console.print(
            f"[yellow]⚠ {len(over)} shot(s) exceed {shot_runner.SPLIT_SEGMENT_DURATION}s and "
            f"will be silently clamped to ~5-6s by the Agnes model: "
            f"{', '.join(s.id for s in over[:8])}" + ("…" if len(over) > 8 else "")
        )
        if not split_long_shots:
            console.print(
                "[dim]  Re-run with --split-long-shots to slice them into "
                f"≤{shot_runner.SPLIT_SEGMENT_DURATION}s parts instead of burning full "
                "credits on clamped takes.[/dim]"
            )
    if split_long_shots:
        shots = shot_runner.split_long_shots(shots)
        if over:
            console.print(f"[green]✓ Split over-long shots → {len(shots)} total shots.[/green]")

    # Issue #49: under --split-long-shots, a --only targeting a pre-split
    # parent ID (e.g. "shot04_silas") must expand to its split parts
    # (shot04_silas-p1, shot04_silas-p2), else the runner matches nothing
    # and silently exits with "all pending shots complete".
    if split_long_shots and only:
        expanded = shot_runner.expand_only_ids(set(only), shots)
        changed = sorted(expanded - set(only))
        if changed:
            console.print(
                f"[dim]--only targets a split parent; expanding to parts: "
                f"{', '.join(changed)}[/dim]"
            )
        only = tuple(expanded)

    # Issue #36: keep project.json live as production progresses.
    def _sync_project(status: str) -> None:
        from brandly_cli.project_manager import sync_production_state

        result = sync_production_state(
            root,
            project_id,
            status=status,
            current_phase="video",
            shot_count=len(shots),
        )
        if result is not None:
            console.print(
                f"[dim]project.json synced: status={status} shot_count={len(shots)}[/dim]"
            )

    _sync_project("in_progress")

    # Issue #37: register every shot on the production plan with its shot ID
    # so a reviewer can match plan files to shots without opening them.
    plan_files: dict[str, Path] = {}
    if not no_plan:
        from brandly_cli.utils import write_generation_plan

        model = "agnes-video-2.5-flash"
        for shot in shots:
            plan, _ = write_generation_plan(
                project_id,
                "video",
                root=root,
                prompt=shot.prompt,
                model=model,
                style=shot.style,
                extra_config={
                    "Shot": shot.id,
                    "Duration": f"{shot.duration}s",
                    "Act": shot.act or "—",
                    "Role": "shot",
                },
                source="brandly produce",
                shot_id=shot.id,
                scene=shot.scene,
                act=shot.act or None,
            )
            plan_files[shot.id] = plan

    def _on_shot_done(shot: shot_runner.Shot, ok: bool) -> None:
        # Issue #37: update the plan row; Issue #36: sync project.json.
        plan = plan_files.get(shot.id)
        if plan is not None:
            from brandly_cli.utils import upsert_production_plan

            upsert_production_plan(
                project_id,
                root=root,
                plan_file=str(plan),
                asset_type="video",
                model="agnes-video-2.5-flash",
                status="COMPLETED" if ok else "FAILED",
                source="brandly produce",
                shot_id=shot.id,
            )
        _sync_project("in_progress")

    def generate_one(shot: shot_runner.Shot) -> tuple[bool, int, str]:
        ok = _generate_shot(
            project_id,
            {**shot.to_video_kwargs(), "character": shot.character},
            ctx=ctx,
            root=root,
            auto_refs_enabled=not no_auto_refs,
            allow_referenceless=allow_referenceless,
            max_wait=max_wait,
            # Names the download Scene-XX-Shot-X-Y.mp4 at save time.
            scene=shot.scene,
            shot_number=shot.index_in_scene,
        )
        return ok, 0 if ok else 1, ""

    config = shot_runner.RunnerConfig(
        shots=shots,
        generate_one=generate_one,
        scenes_dir=scenes_dir,
        progress=progress,
        interval=interval,
        only=set(only) if only else None,
        max_shots=max_shots,
        say=lambda msg: console.print(f"[dim]{msg}[/dim]"),
        retries=retries,
        on_shot_done=_on_shot_done,
        aspect_ratio=aspect_ratio,
    )
    rc = shot_runner.run_shots(config)
    _sync_project("complete" if rc == 0 else "failed")
    sys.exit(rc)


def register(cli) -> None:
    cli.add_command(reference)
    cli.add_command(image)
    cli.add_command(video)
    cli.add_command(prompt)
    cli.add_command(music)
    cli.add_command(tts)
    cli.add_command(voices_cmd)
    cli.add_command(director)
