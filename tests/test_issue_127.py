"""Issue #127: review queue — approve/reject auto-approved keyframes + takes.

Human-in-the-loop gates auto-approve in non-interactive/piped runs — exactly
how agent-driven production runs execute — so the web UI restores the human
*asynchronously*, after the agent finishes:

- everything that auto-approved since the last human review session is queued
  (storyboard keyframes, generated clips with gate score/issues, reference
  sheets)
- reject writes the standard review note and un-completes the shot in the
  progress log, so the next ``--only <id>`` / re-run picks it up
- approve stamps reviewer + timestamp into the generation record
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

REVIEWER = "qa@studio"


def _project(root: Path, project_id: str = "proj-a") -> Path:
    proj = root / ".brandly" / project_id
    (proj / "docs" / "tmp").mkdir(parents=True, exist_ok=True)
    (proj / "project.json").write_text(
        json.dumps({"id": project_id, "name": "Review Fixture"}), encoding="utf-8"
    )
    return proj


def _media_root(root: Path, project_id: str = "proj-a") -> Path:
    from brandly_cli import layout

    return layout.resolve_media_root(root, project_id, "images")


def _keyframe(root: Path, stem: str, project_id: str = "proj-a") -> Path:
    path = _media_root(root, project_id) / "storyboard" / f"{stem}.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-keyframe-bytes")
    return path


def _clip(root: Path, stem: str, project_id: str = "proj-a") -> Path:
    from brandly_cli import layout

    path = layout.resolve_media_root(root, project_id, "videos") / "scenes" / f"{stem}.mp4"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-clip-bytes")
    return path


def _sheet(root: Path, name: str, project_id: str = "proj-a") -> Path:
    path = _media_root(root, project_id) / "character" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-sheet-bytes")
    return path


def _shots(root: Path, ids: list[str], project_id: str = "proj-a") -> Path:
    shots = root / ".brandly" / project_id / "shots.json"
    shots.write_text(
        json.dumps([{"id": sid, "prompt": f"prompt for {sid}", "duration": 5} for sid in ids]),
        encoding="utf-8",
    )
    return shots


def _progress(root: Path, lines: list[str], stage: str = "produce",
              project_id: str = "proj-a") -> Path:
    proj = root / ".brandly" / project_id
    name = "produce_progress.txt" if stage == "produce" else "storyboard_progress.txt"
    path = proj / "docs" / "tmp" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _video_record(root: Path, stem: str, project_id: str = "proj-a") -> Path:
    """A generation record for a clip (what approve stamps)."""
    from brandly_cli import layout

    docs = layout.docs_dir(layout.project_dir(root, project_id), "tmp")
    record = docs / "video_20260926-180000.json"
    record.write_text(
        json.dumps(
            {
                "asset_type": "video",
                "output_file": str(_clip(root, stem, project_id)),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"clip_id": stem},
            }
        ),
        encoding="utf-8",
    )
    return record


GATE_MD = """\
# Quality Gate Report — videos/scenes/Scene-01-Shot-1-1.mp4

**Status:** ✗ FAIL (38/100)

Gate policy: pre-checks; artifact fail cutoffs distortion≥6, slop≥7, drift≥6

## Failures

- Severe distortion detected (7/10)

_Written to .brandly/{project}/docs/tmp/_
"""


class TestReviewQueue:
    def test_auto_approved_keyframe_is_queued(self, tmp_path: Path) -> None:
        from brandly_cli.web import review

        _project(tmp_path)
        _keyframe(tmp_path, "Scene-01-Shot-1-1")
        # The agent's run auto-approved it: an OK line, no human decision.
        _progress(tmp_path, ["2026-09-26T18:01:00Z Scene-01-Shot-1-1 OK exit=0"], stage="storyboard")

        queue = review.queue(tmp_path, "proj-a")
        items = [i for i in queue["items"] if i["stage"] == "storyboard"]
        assert [i["item_id"] for i in items] == ["storyboard:Scene-01-Shot-1-1"]
        assert items[0]["path"].endswith("storyboard/Scene-01-Shot-1-1.jpg")
        assert items[0]["decided"] is False

    def test_clips_are_queued_with_gate_score_and_issues(self, tmp_path: Path) -> None:
        from brandly_cli.web import review

        _project(tmp_path)
        _clip(tmp_path, "Scene-01-Shot-1-1")
        docs = tmp_path / ".brandly" / "proj-a" / "docs" / "tmp"
        (docs / "gate_video_20260926-180000.md").write_text(GATE_MD, encoding="utf-8")

        queue = review.queue(tmp_path, "proj-a")
        items = [i for i in queue["items"] if i["stage"] == "video"]
        assert [i["item_id"] for i in items] == ["video:Scene-01-Shot-1-1"]
        assert items[0]["gate"] == {
            "score": 38,
            "status": "fail",
            "issues": ["Severe distortion detected (7/10)"],
        }
        assert items[0]["scene"] == 1

    def test_reference_sheets_are_queued(self, tmp_path: Path) -> None:
        from brandly_cli.web import review

        _project(tmp_path)
        _sheet(tmp_path, "char_hero.png")

        queue = review.queue(tmp_path, "proj-a")
        items = [i for i in queue["items"] if i["stage"] == "reference"]
        assert [i["item_id"] for i in items] == ["reference:char_hero"]

    def test_nothing_auto_approved_is_an_empty_queue(self, tmp_path: Path) -> None:
        from brandly_cli.web import review

        _project(tmp_path)
        queue = review.queue(tmp_path, "proj-a")
        assert queue["items"] == []

    def test_decided_items_leave_the_queue_and_persist(self, tmp_path: Path) -> None:
        from brandly_cli.web import review

        _project(tmp_path)
        _keyframe(tmp_path, "Scene-01-Shot-1-1")

        first = review.queue(tmp_path, "proj-a")
        assert len(first["items"]) == 1

        result = review.approve(
            tmp_path, "proj-a", "storyboard:Scene-01-Shot-1-1", reviewer=REVIEWER
        )
        assert result["status"] == "approved"

        second = review.queue(tmp_path, "proj-a")
        assert second["items"] == []  # removed from the queue

        third = review.queue(tmp_path, "proj-a")  # decision persists on disk
        assert third["items"] == []

    def test_filters_stage_scene_and_below_threshold(self, tmp_path: Path) -> None:
        from brandly_cli.web import review

        _project(tmp_path)
        _keyframe(tmp_path, "Scene-02-Shot-2-1")
        _clip(tmp_path, "Scene-01-Shot-1-1")
        docs = tmp_path / ".brandly" / "proj-a" / "docs" / "tmp"
        (docs / "gate_video_20260926-180000.md").write_text(GATE_MD, encoding="utf-8")

        by_stage = review.queue(tmp_path, "proj-a", stage="video")
        assert [i["item_id"] for i in by_stage["items"]] == ["video:Scene-01-Shot-1-1"]

        by_scene = review.queue(tmp_path, "proj-a", scene=2)
        assert [i["item_id"] for i in by_scene["items"]] == ["storyboard:Scene-02-Shot-2-1"]

        below = review.queue(tmp_path, "proj-a", below_threshold=50)
        assert [i["item_id"] for i in below["items"]] == ["video:Scene-01-Shot-1-1"]

        strict = review.queue(tmp_path, "proj-a", below_threshold=10)
        assert strict["items"] == []  # nothing scores below 10

    def test_unknown_project_is_404_via_deps(self, tmp_path: Path) -> None:
        import pytest
        from fastapi import HTTPException

        from brandly_cli.web import review

        _project(tmp_path)
        with pytest.raises(HTTPException) as excinfo:
            review.queue(tmp_path, "nope")
        assert excinfo.value.status_code == 404


class TestApproveReject:
    def test_reject_writes_review_note_and_unreflags_the_shot(self, tmp_path: Path) -> None:
        from brandly_cli.web import review

        _project(tmp_path)
        # Realistic run: the shot list id is what the progress log records;
        # the keyframe is named by the deterministic clip stem, which for a
        # flat shot list carries the "-shots" act suffix (Shot.clip_name).
        _shots(tmp_path, ["shot16"])
        _keyframe(tmp_path, "Scene-01-Shot-1-1-shots")
        _progress(
            tmp_path,
            ["2026-09-26T18:01:00Z shot16 OK exit=0"],
            stage="storyboard",
        )

        result = review.reject(
            tmp_path, "proj-a", "storyboard:Scene-01-Shot-1-1-shots",
            note="face drift vs plate", reviewer=REVIEWER,
        )
        assert "error" not in result
        assert result["shot_id"] == "shot16"

        # The standard review note lands in docs/tmp/.
        docs = tmp_path / ".brandly" / "proj-a" / "docs" / "tmp"
        notes = sorted(docs.glob("review_storyboard_*.md"))
        assert len(notes) == 1
        assert "REJECTED" in notes[0].read_text(encoding="utf-8")
        assert "face drift vs plate" in notes[0].read_text(encoding="utf-8")

        # The shot is re-flagged: its OK line is gone from the progress log,
        # so the next storyboard re-run / --only picks it up.
        log = (docs / "storyboard_progress.txt").read_text(encoding="utf-8")
        assert "shot16 OK" not in log

        # And the item is decided (out of the queue).
        assert review.queue(tmp_path, "proj-a")["items"] == []

    def test_approve_stamps_the_generation_record(self, tmp_path: Path) -> None:
        from brandly_cli.web import review

        _project(tmp_path)
        _clip(tmp_path, "Scene-01-Shot-1-1")
        record = _video_record(tmp_path, "Scene-01-Shot-1-1")

        result = review.approve(tmp_path, "proj-a", "video:Scene-01-Shot-1-1", reviewer=REVIEWER)
        assert "error" not in result

        stamped = json.loads(record.read_text(encoding="utf-8"))
        assert stamped["review"]["reviewer"] == REVIEWER
        assert stamped["review"]["decision"] == "approved"
        assert stamped["review"]["reviewed_at"]

        assert review.queue(tmp_path, "proj-a")["items"] == []

    def test_reject_of_an_unknown_item_is_a_clean_error(self, tmp_path: Path) -> None:
        from brandly_cli.web import review

        _project(tmp_path)
        result = review.reject(tmp_path, "proj-a", "storyboard:missing", note="x", reviewer=REVIEWER)
        assert "error" in result

    def test_approve_of_an_unknown_item_is_a_clean_error(self, tmp_path: Path) -> None:
        from brandly_cli.web import review

        _project(tmp_path)
        result = review.approve(tmp_path, "proj-a", "video:missing", reviewer=REVIEWER)
        assert "error" in result


class TestReviewRoutes:
    def _client(self, tmp_path: Path) -> TestClient:
        from brandly_cli.web.server import create_app

        app = create_app(root=str(tmp_path))
        return TestClient(app, base_url="http://127.0.0.1:8765")

    def test_queue_route_with_filters(self, tmp_path: Path) -> None:

        _project(tmp_path)
        _keyframe(tmp_path, "Scene-01-Shot-1-1")

        client = self._client(tmp_path)
        res = client.get("/api/projects/proj-a/review/queue")
        assert res.status_code == 200
        data = res.json()
        assert [i["item_id"] for i in data["items"]] == ["storyboard:Scene-01-Shot-1-1"]

        res = client.get("/api/projects/proj-a/review/queue?stage=video")
        assert res.status_code == 200
        assert res.json()["items"] == []

    def test_queue_route_unknown_project_404(self, tmp_path: Path) -> None:
        _project(tmp_path)
        client = self._client(tmp_path)
        assert client.get("/api/projects/nope/review/queue").status_code == 404

    def test_reject_route_then_queue_empty(self, tmp_path: Path) -> None:

        _project(tmp_path)
        _keyframe(tmp_path, "Scene-01-Shot-1-1")
        _progress(
            tmp_path,
            ["2026-09-26T18:01:00Z Scene-01-Shot-1-1 OK exit=0"],
            stage="storyboard",
        )

        client = self._client(tmp_path)
        res = client.post(
            "/api/projects/proj-a/review/storyboard:Scene-01-Shot-1-1/reject",
            json={"note": "composition off", "reviewer": REVIEWER},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "rejected"
        assert client.get("/api/projects/proj-a/review/queue").json()["items"] == []

    def test_approve_route_stamps_and_dequeues(self, tmp_path: Path) -> None:

        _project(tmp_path)
        _keyframe(tmp_path, "Scene-01-Shot-1-1")

        client = self._client(tmp_path)
        res = client.post(
            "/api/projects/proj-a/review/storyboard:Scene-01-Shot-1-1/approve",
            json={"reviewer": REVIEWER},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "approved"
        assert client.get("/api/projects/proj-a/review/queue").json()["items"] == []

    def test_review_item_media_is_served_contained(self, tmp_path: Path) -> None:
        _project(tmp_path)
        _keyframe(tmp_path, "Scene-01-Shot-1-1")

        client = self._client(tmp_path)
        res = client.get("/api/projects/proj-a/review/storyboard:Scene-01-Shot-1-1/media")
        assert res.status_code == 200
        assert res.content == b"fake-keyframe-bytes"

        # A crafted id can never reach outside the project.
        assert client.get("/api/projects/proj-a/review/storyboard:..%2F..%2Fsecret/media").status_code == 404
