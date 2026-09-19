"""Issue tracker — report bugs / feature requests to GitHub with user consent."""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO = "Dream-Pixels-Forge/brandly-cli"
ISSUE_TEMPLATE_URL = (
    "https://github.com/Dream-Pixels-Forge/brandly-cli/issues/new"
    "?template=bug_report.md&title={title}"
)
CONSENT_FILE_NAME = ".brandly_report_consent.json"


def _app_data_dir() -> Path:
    """Return a writeable app-data dir for brandly consent state."""
    if sys.platform == "win32":
        base = Path.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    return base / "brandly-cli"


def _consent_path() -> Path:
    return _app_data_dir() / CONSENT_FILE_NAME


def _load_consent() -> dict[str, Any]:
    p = _consent_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_consent(state: dict[str, Any]) -> None:
    p = _consent_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


def collect_context(
    *,
    error: Exception | None = None,
    project_id: str | None = None,
    root: str | Path | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Gather diagnostic context for an issue report."""
    ctx: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "brandly_version": _version(),
        "project_id": project_id,
        "root": str(root) if root else None,
    }
    if error is not None:
        ctx["error_type"] = type(error).__name__
        ctx["error_message"] = str(error)
        ctx["traceback"] = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    if extra:
        ctx.update(extra)
    # Peek at cost state if available
    if project_id and root:
        cost_path = Path(root) / ".brandly" / project_id / "cost.json"
        if cost_path.exists():
            try:
                ctx["cost_state"] = json.loads(cost_path.read_text())
            except Exception:
                pass
    return ctx


def format_issue_body(ctx: dict[str, Any]) -> str:
    """Format collected context as a GitHub issue body."""
    lines: list[str] = []
    lines.append(f"**Brandly CLI**: v{ctx['brandly_version']}")
    lines.append(f"**Python**: {ctx['python_version']}")
    lines.append(f"**Platform**: {ctx['platform']}")
    if ctx.get("project_id"):
        lines.append(f"**Project**: `{ctx['project_id']}`")
    if ctx.get("root"):
        lines.append(f"**Root**: `{ctx['root']}`")
    lines.append("")
    lines.append("## What happened")
    if ctx.get("error_type"):
        lines.append(f"Exception: **{ctx['error_type']}**")
        lines.append(f"Message: `{ctx.get('error_message', '')}`")
    lines.append("")
    lines.append("## Steps to reproduce")
    lines.append("1. ")
    lines.append("2. ")
    lines.append("3. ")
    lines.append("")
    lines.append("## Expected behavior")
    lines.append("")
    lines.append("## Actual behavior")
    lines.append("")
    tb = ctx.get("traceback")
    if tb:
        lines.append("```")
        lines.append(tb[:3000])
        if len(tb) > 3000:
            lines.append("... (truncated)")
        lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("*Auto-generated issue report from brandly-cli.*")
    return "\n".join(lines)


def ask_permission(ctx: dict[str, Any], body: str, *, dry_run: bool = False) -> bool:
    """Show the issue preview and ask the user whether to submit.

    Returns True if the user consents (or auto-consented via stored preference).
    """
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    cons = _load_consent()
    auto = cons.get("auto_report", False)

    if auto and not dry_run:
        return True

    console = Console()
    console.print()
    console.print(
        Panel(
            Markdown(body),
            title="[bold red]Issue Report Preview[/bold red]",
            border_style="red",
        )
    )
    console.print()
    console.print(
        "[dim]This will be submitted as a GitHub issue on "
        f"[link={ISSUE_TEMPLATE_URL}]dream-pixels-forge/brandly-cli[/link].[/dim]"
    )
    console.print()
    choice = console.input(
        "[bold]Submit issue?[/bold] [y/n/a] (y=submit, n=skip, a=auto-next-time): "
    ).strip().lower()
    if choice in ("y", "yes"):
        return True
    if choice in ("a", "auto"):
        cons["auto_report"] = True
        _save_consent(cons)
        console.print("[dim]Auto-report consent saved for future issues.[/dim]")
        return True
    return False


def submit_issue(ctx: dict[str, Any], body: str) -> dict[str, Any]:
    """POST the issue to GitHub via the API. Returns result dict."""
    token = _resolve_token()
    if not token:
        return {"ok": False, "error": "No GITHUB_TOKEN found. Set it in your environment."}
    title = _pick_title(ctx)
    url = f"https://api.github.com/repos/{REPO}/issues"
    payload = {"title": title, "body": body}
    try:
        resp = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return {"ok": True, "url": data.get("html_url", ""), "number": data.get("number")}
        return {
            "ok": False,
            "status": resp.status_code,
            "body": resp.text[:500],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _pick_title(ctx: dict[str, Any]) -> str:
    etype = ctx.get("error_type", "Bug")
    emsg = (ctx.get("error_message") or "").strip()
    preview = emsg[:60] if emsg else etype
    return f"[auto] {etype}: {preview}"


def _resolve_token() -> str | None:
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        val = sys.environ.get(key)
        if val:
            return val.strip()
    # Try ~/.config/gh/hosts.yml style config — simple fallback
    gh_config = Path.home() / ".config" / "gh" / "hosts.yml"
    if gh_config.exists():
        try:
            import yaml
            cfg = yaml.safe_load(gh_config.read_text())
            for _host, entry in (cfg or {}).items():
                if isinstance(entry, dict) and entry.get("oauth_token"):
                    return entry["oauth_token"]
        except Exception:
            pass
    return None


def _version() -> str:
    try:
        from brandly_cli import __version__
        return __version__
    except Exception:
        return "unknown"


def report_from_exception(
    exc: BaseException,
    *,
    project_id: str | None = None,
    root: str | Path | None = None,
    skip_if_silent: bool = False,
) -> None:
    """Convenience: show a one-line prompt after an exception and optionally file.

    Only asks when the caller passes ``ask=True``; otherwise reports silently
    (subject to stored consent).
    """
    ctx = collect_context(error=exc, project_id=project_id, root=root)
    body = format_issue_body(ctx)
    cons = _load_consent()
    if cons.get("auto_report") or skip_if_silent:
        from rich.console import Console
        console = Console()
        console.print("[dim]Reporting issue to GitHub...[/dim]")
        result = submit_issue(ctx, body)
        if result.get("ok"):
            console.print(f"[green]✓ Issue opened: {result['url']}[/green]")
        else:
            console.print(f"[yellow]Report failed: {result.get('error') or result}[/yellow]")
        return
    # Interactive — only ask if we're in a TTY
    if not sys.stdout.isatty() and not sys.stderr.isatty():
        return
    from rich.console import Console
    console = Console()
    console.print()
    console.print(
        f"[red]Unhandled exception: {type(exc).__name__}: {exc}[/red]"
    )
    console.print("[dim]Would you like to file a GitHub issue with this error?[/dim]")
    if ask_permission(ctx, body):
        result = submit_issue(ctx, body)
        if result.get("ok"):
            console.print(f"[green]✓ Issue opened: {result['url']}[/green]")
        else:
            console.print(
                f"[yellow]Report failed: {result.get('error') or result}[/yellow]"
            )
    else:
        console.print("[dim]Issue report skipped.[/dim]")
