"""Contract tests for async hygiene (issues #246, #249).

RED: a prior session converted ``asyncio.run()`` call sites to
``run_async()`` but missed the import in ``cmd/production.py`` and
``project_manager.py`` — every CLI command touching those modules raised
``NameError: name 'run_async' is not defined`` (33 test failures).
Issue #246's repro additionally showed ``asyncio.run()`` being called
from a running event loop in the video-generation path.

These tests pin, at source level (no JS runner needed):

1. every module calling ``run_async()`` imports it,
2. the #246 site (``create_video_task``) goes through ``run_async`` —
   never bare ``asyncio.run`` in the generation path,
3. ``run_async`` works from inside a running event loop without
   raising or emitting RuntimeWarnings.
"""

from __future__ import annotations

import asyncio
import warnings
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "brandly_cli"

_IMPORT = "from brandly_cli.async_compat import run_async"


def _modules_calling_run_async() -> list[Path]:
    return [
        p
        for p in SRC.rglob("*.py")
        if "run_async(" in p.read_text(encoding="utf-8")
    ]


class TestRunAsyncImportContract:
    def test_every_run_async_caller_imports_it(self) -> None:
        offenders: list[str] = []
        for p in _modules_calling_run_async():
            if p.name == "async_compat.py":
                continue  # the module that defines run_async
            body = p.read_text(encoding="utf-8")
            if _IMPORT not in body:
                offenders.append(str(p.relative_to(SRC.parent.parent)))
        assert not offenders, (
            f"modules call run_async() without importing it: {offenders} "
            "(issues #246/#249 — NameError at runtime)"
        )


class TestCreateVideoTaskSite:
    def test_create_video_task_uses_run_async(self) -> None:
        gen = (SRC / "cmd" / "generation.py").read_text(encoding="utf-8")
        assert "run_async(" in gen and "create_video_task(" in gen, (
            "generation.py must call create_video_task"
        )
        assert _IMPORT in gen, (
            "generation.py must import run_async from async_compat"
        )
        # The call site itself must be wrapped in run_async, not asyncio.run.
        site = gen[gen.index("create_video_task(") - 200 : gen.index("create_video_task(")]
        assert "run_async(" in site, (
            "create_video_task must be routed through run_async "
            "(issue #246 — asyncio.run() inside a running event loop)"
        )
        assert "asyncio.run(" not in site, (
            "bare asyncio.run() at the create_video_task site crashes "
            "when the pipeline runs inside an event loop (issue #246)"
        )


class TestRunAsyncFromRunningLoop:
    def test_no_runtime_warning_inside_a_loop(self) -> None:
        from brandly_cli.async_compat import run_async

        async def _leaf() -> int:
            await asyncio.sleep(0)
            return 7

        async def inner() -> int:
            # run_async called synchronously from inside a running loop —
            # must fall back to a thread loop, never raise, never warn.
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                return run_async(_leaf())

        assert asyncio.run(inner()) == 7
