"""Contract tests for the GitHub Actions workflows.

The two workflows must never sabotage each other, and a release must never
publish a commit whose CI is red. These are source-contract assertions in the
same style as ``tests/test_warning_free_stack.py`` (plain text/regex over the
YAML sources — no YAML runtime dependency, no new CI architecture).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CI = WORKFLOWS / "ci.yml"
RELEASE = WORKFLOWS / "release.yml"


def read(path: Path) -> str:
    assert path.is_file(), f"missing workflow: {path}"
    return path.read_text(encoding="utf-8")


def jobs_of(workflow: str) -> dict[str, str]:
    """Split a workflow into ``{job_id: job_body}`` (top-level keys under jobs)."""
    lines = workflow.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "jobs:")
    except StopIteration:  # pragma: no cover - guarded by read() assertions
        raise AssertionError("workflow has no `jobs:` block") from None
    jobs: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            break
        if indent == 2 and stripped.endswith(":"):
            current = stripped[:-1]
            jobs[current] = []
        elif current is not None:
            jobs[current].append(line)
    return {name: "\n".join(body) for name, body in jobs.items()}


def test_workflows_do_not_share_a_concurrency_group() -> None:
    """Each workflow's concurrency group is workflow-scoped.

    A group shared across workflows would let one workflow cancel the other's
    run (the CI ``push`` group and the release group must never alias).
    """
    ci = read(CI)
    assert re.search(
        r"(?m)^concurrency:\n(?:.*\n)*?\s+group:\s*\$\{\{\s*github\.workflow\s*\}\}", ci
    ), "ci.yml concurrency group must be prefixed with github.workflow"

    release = read(RELEASE)
    if "concurrency:" in release:
        assert "github.workflow" in release, (
            "release.yml declares concurrency, so its group must also be "
            "workflow-scoped to avoid cancelling CI runs"
        )


def test_every_job_has_a_timeout() -> None:
    """No job may inherit the 360-minute default and burn quota on a hang."""
    for path in (CI, RELEASE):
        for name, body in jobs_of(read(path)).items():
            assert re.search(r"(?m)^\s+timeout-minutes:\s*\d+", body), (
                f"{path.name}:{name} must declare timeout-minutes"
            )


def test_ci_declares_least_privilege_permissions() -> None:
    ci = read(CI)
    assert re.search(r"(?m)^permissions:\n\s+contents:\s*read\s*$", ci), (
        "ci.yml must declare `permissions: contents: read` instead of inheriting the repo default"
    )


def test_release_publish_is_gated_on_a_verifying_job() -> None:
    """`publish` must depend on a job that runs lint + type check + tests."""
    jobs = jobs_of(read(RELEASE))
    assert "publish" in jobs
    assert re.search(r"(?m)^\s+needs:\s*(\[\s*verify\s*\]|verify)\s*$", jobs["publish"]), (
        "release.yml publish job must declare `needs: [verify]`"
    )

    verify_jobs = [name for name in jobs if name != "publish"]
    assert verify_jobs, "release.yml needs a verification job ahead of publish"

    combined = "\n".join(jobs[name] for name in verify_jobs)
    assert "ruff check" in combined, "the release verification job must run ruff"
    assert "mypy src/" in combined, "the release verification job must run mypy"
    assert "pytest" in combined, "the release verification job must run the test suite"


def test_release_verification_checks_out_the_tag() -> None:
    """Verifying the default branch instead of the tag would gate the wrong code."""
    jobs = jobs_of(read(RELEASE))
    verify = "\n".join(body for name, body in jobs.items() if name != "publish")
    assert "github.event.release.tag_name" in verify, (
        "the release verification checkout must pin `ref: ${{ github.event.release.tag_name }}`"
    )


def test_release_verifier_requires_wheel_and_sdist() -> None:
    """A partial upload (sdist only) must fail the gate, not pass silently."""
    release = read(RELEASE)
    assert "bdist_wheel" in release, "the PyPI verifier must require a wheel"
    assert '"sdist"' in release or "'sdist'" in release, (
        "the PyPI verifier must require an sdist"
    )
