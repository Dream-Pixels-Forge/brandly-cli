"""Shared pytest fixtures for the brandly test-suite.

Issue #124 added a process-level video-create spacing guard in
``agnes_client`` (``_LAST_VIDEO_CREATE_AT`` + ``MIN_VIDEO_CREATE_GAP_SECONDS``).
The guard is correct in production — the provider counts every create against
its 1 request/minute window — but it is module state, so tests that create
videos back to back would sleep out the remainder of the window inside
*unrelated* tests (each extra create costs up to 60s).

Reset it before every test: a test that exercises the spacing (see
``tests/test_issue_124.py``) sets the timestamp/gap explicitly.
"""

from __future__ import annotations

import pytest

from brandly_cli import agnes_client


@pytest.fixture(autouse=True)
def _reset_video_create_spacing_guard() -> None:
    """Keep the #124 create-spacing guard from leaking across tests."""
    agnes_client._LAST_VIDEO_CREATE_AT = None
