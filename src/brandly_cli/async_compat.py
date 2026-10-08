"""Async compatibility utilities for handling coroutines in both sync and async contexts."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any


def run_async(coro: Any) -> Any:
    """Run an async coroutine, handling both sync and async contexts.

    If there's already a running event loop, run the coroutine in a separate
    thread with its own event loop to avoid "RuntimeError: This event loop
    is already running". Otherwise, use asyncio.run().

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop - safe to use asyncio.run()
        return asyncio.run(coro)
    else:
        # Already in an event loop - run in a separate thread with its own loop
        # to avoid "RuntimeError: This event loop is already running"

        def run_in_thread() -> Any:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_thread)
            return future.result()


def async_run_ffmpeg(cmd: list[str]) -> tuple[int, str, str]:
    """Run ffmpeg command asynchronously, compatible with both sync and async contexts."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop - safe to use asyncio.run()
        return asyncio.run(_async_run_ffmpeg(cmd))
    else:
        # Already in an event loop - run in a separate thread with its own loop

        def run_in_thread() -> tuple[int, str, str]:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(_async_run_ffmpeg(cmd))
            finally:
                new_loop.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_thread)
            return future.result()


async def _async_run_ffmpeg(cmd: list[str]) -> tuple[int, str, str]:
    """Actually run ffmpeg command and capture output."""
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        # communicate() implies termination, but returncode is Optional —
        # narrow it instead of asserting (mypy return-value fix, PR #264).
        returncode = process.returncode if process.returncode is not None else 1
        return returncode, stdout.decode(), stderr.decode()
    except FileNotFoundError:
        return 1, "", "ffmpeg not found"
    except Exception as e:
        return 1, "", str(e)
