#!/usr/bin/env python3
"""Regenerate ``assets/studio-preview.png`` from the *live* web UI.

The README Demos image is a real screenshot of the built Brandly Studio web
bundle — not a hand-drawn mock. Running this script:

1. Seeds a throwaway demo project (``.brandly/lumina-earbuds-launch``) with a
   five-clip timeline so the capture shows a populated studio, not the empty
   "Select a Project" state.
2. Launches the FastAPI server on ``127.0.0.1`` with ``token=None`` (the loopback
   guard is the only enforcement; no auth token is required).
3. Drives a headless Chromium/Edge via ``playwright-core`` to select the demo
   project, open the "Timeline Sequencer" panel, and write a 1440x900 PNG.

Because the PNG is a capture of the actual running app, it always mirrors the
committed web sources it is rendered from:

    web/src/panelLabels.ts
    web/index.html
    web/src/components/panels/ShotListPanel.tsx
    web/src/components/panels/TransportControls.tsx

Run it any time the frontend changes (needs ``node`` on PATH and network access
for the CDN assets the SPA loads):

    python scripts/make_studio_preview.py
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = REPO_ROOT / "scripts" / "screenshot"
DRIVER = SCREENSHOT_DIR / "shot.mjs"
OUTPUT = REPO_ROOT / "assets" / "studio-preview.png"

PROJECT_ID = "lumina-earbuds-launch"
PROJECT_NAME = "Lumina Earbuds Launch"

#: A representative 5-clip launch timeline. Statuses are mixed on purpose so
#: the sequencer shows solid ("generated"), striped ("generating") and muted
#: ("pending") blocks together.
_CLIPS: tuple[tuple[str, int, int, float, str, str], ...] = (
    ("Scene-01-Shot-1", 1, 1, 4.0, "generated",
     "Cold open: charging-case lid snaps shut on a matte desk, macro."),
    ("Scene-01-Shot-2", 1, 2, 5.0, "generated",
     "Glide across the acoustic mesh, shallow depth of field."),
    ("Scene-01-Shot-3", 1, 3, 4.0, "generated",
     "Hand lifts a bud; city bokeh drifts behind, ear-anchored."),
    ("Scene-02-Shot-1", 2, 1, 6.0, "generating",
     "Runner at dawn - buds stay put through wind, sweat and motion."),
    ("Scene-02-Shot-2", 2, 2, 5.0, "pending",
     "Hero reveal: product on a reflective black plinth, key-light sweep."),
)


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _seed_demo_root(root: Path) -> None:
    """Write a demo project.json + timeline.json under ``root/.brandly/``."""
    now = datetime.now(timezone.utc).isoformat()
    proj_dir = root / ".brandly" / PROJECT_ID
    docs_tmp = proj_dir / "docs" / "tmp"
    docs_tmp.mkdir(parents=True, exist_ok=True)

    project = {
        "id": PROJECT_ID,
        "name": PROJECT_NAME,
        "slug": PROJECT_ID,
        "description": "15s hero film for the Lumina wireless-earbuds launch.",
        "status": "running",
        "style": "cinematic",
        "shot_count": len(_CLIPS),
        "budget": 500,
        "spent": 132,
        "current_phase": "produce",
        "phases": {},
        "target_platforms": ["tiktok", "instagram"],
        "created_at": now,
        "updated_at": now,
    }
    (proj_dir / "project.json").write_text(json.dumps(project, indent=2), encoding="utf-8")

    clips: list[dict] = []
    t = 0.0
    for stem, scene, idx, dur, status, prompt in _CLIPS:
        clips.append({
            "id": stem,
            "shot_id": f"shot-{scene}-{idx}",
            "scene": scene,
            "index_in_scene": idx,
            "clip_path": f"videos/scenes/{stem}.mp4",
            "prompt": prompt,
            "duration": dur,
            "actual_duration": dur if status == "generated" else None,
            "style": "cinematic",
            "transition_in": None,
            "transition_duration": 0.5,
            "volume": 1.0,
            "status": status,
            "aspect_ratio": "16:9",
            "start_time": t,
            "quality_status": None,
            "created_at": now,
            "updated_at": now,
        })
        t += dur
    timeline = {
        "project_id": PROJECT_ID,
        "clips": clips,
        "aspect_ratio": "16:9",
        "fps": 24,
        "color_grade": "cinematic",
        "created_at": now,
        "updated_at": now,
    }
    (docs_tmp / "timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")


def _start_server(root: Path, port: int) -> None:
    """Run the FastAPI app on 127.0.0.1 in a daemon thread (blocking loop)."""
    import uvicorn

    from brandly_cli.web.server import create_app

    app = create_app(root=root, token=None)
    threading.Thread(
        target=lambda: uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning"),
        daemon=True,
    ).start()


def _wait_for_health(port: int, timeout: float = 30.0) -> None:
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"server on :{port} did not become healthy")


def _ensure_playwright() -> None:
    if (SCREENSHOT_DIR / "node_modules" / "playwright-core").is_dir():
        return
    print("installing playwright-core for the screenshot driver ...")
    subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund", "playwright-core"],
        cwd=str(SCREENSHOT_DIR),
        check=True,
    )


def _screenshot(url: str, out: Path) -> None:
    subprocess.run(["node", str(DRIVER), url, str(out)], check=True)


def main() -> int:
    _ensure_playwright()

    port = _free_port()
    with tempfile.TemporaryDirectory(prefix="brandly-preview-") as tmp:
        demo_root = Path(tmp)
        _seed_demo_root(demo_root)
        print(f"serving demo project on 127.0.0.1:{port} (root={demo_root})")

        _start_server(demo_root, port)
        _wait_for_health(port)
        print("server healthy")

        _screenshot(f"http://127.0.0.1:{port}/", OUTPUT)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUTPUT.is_file():
        print(f"error: {OUTPUT} was not produced", file=sys.stderr)
        return 1
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
