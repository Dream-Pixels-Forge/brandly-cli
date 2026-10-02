r"""Shot-side reference selection: enforce the layout, cap to the model limit.

Covers the three guarantees for the shot/reference consumer:

* **Enforce layout** — the shot-side plate resolver honours the canonical
  category layout: ``wardrobe`` is a resolvable reference category (matching
  ``layout.IMAGE_CATEGORIES``) and ``hq/`` masters are never eligible as live
  references (only the optimized working twin at a category root is).
* **Only what the shot needs** — a shot's references are resolved to exactly
  the plates it declares; nothing unrelated is pulled in.
* **Respect the model's image limit** — a shot's reference list is capped to
  ``MAX_SHOT_REFERENCE_IMAGES`` (5, the strictest video-model cap), keeping the
  highest-priority (earliest-declared) references and recording the rest on
  ``Shot.dropped_references`` so the producer can warn instead of the create
  call hard-failing.

Run under ``.venv\Scripts\python`` (editable install points at ``src/``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from brandly_cli import layout, shot_runner


def _plate(root: Path, pid: str, category: str, name: str) -> Path:
    """Create a tiny PNG plate at ``pre-production/<pid>/<category>/<name>``."""
    p = root / "pre-production" / pid / category / name
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (0, 0, 0)).save(p, "PNG")
    return p


class TestLayoutEnforced:
    def test_wardrobe_is_a_reference_category(self) -> None:
        # The shot-side resolver must honour the wardrobe folder added to the
        # layout, in sync with the generation-side category map.
        assert "wardrobe" in shot_runner.REF_CATEGORIES
        assert "wardrobe" in layout.IMAGE_CATEGORIES

    def test_wardrobe_plate_resolves(self, tmp_path: Path) -> None:
        _plate(tmp_path, "wp", "wardrobe", "costume_red.opt.jpg")
        got = shot_runner.resolve_plate(
            "costume_red", tmp_path / "pre-production" / "wp"
        )
        assert got.parent.name == "wardrobe"
        assert got.name == "costume_red.opt.jpg"

    def test_character_precedence_over_wardrobe(self, tmp_path: Path) -> None:
        # When a stem exists in both character and wardrobe, character wins
        # (REF_CATEGORIES order), exactly like location/prop today.
        _plate(tmp_path, "pp", "wardrobe", "hero.opt.jpg")
        _plate(tmp_path, "pp", "character", "hero.opt.jpg")
        got = shot_runner.resolve_plate("hero", tmp_path / "pre-production" / "pp")
        assert got.parent.name == "character"

    def test_hq_master_is_never_a_live_reference(self, tmp_path: Path) -> None:
        # Only an HQ master exists (no optimized working twin at the category
        # root). It must not be resolvable as a live reference.
        master = (
            tmp_path / "pre-production" / "hp" / "character" / "hq" / "char_x.jpg"
        )
        master.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8), (0, 0, 0)).save(master, "JPEG")
        with pytest.raises(FileNotFoundError):
            shot_runner.resolve_plate("char_x", tmp_path / "pre-production" / "hp")


class TestReferenceCap:
    def test_constant_is_the_model_limit(self) -> None:
        assert shot_runner.MAX_SHOT_REFERENCE_IMAGES == 5

    def test_keeps_first_five_in_order(self) -> None:
        refs = [f"/r/{i}.jpg" for i in range(7)]
        kept, dropped = shot_runner.cap_reference_selection(
            refs, shot_runner.MAX_SHOT_REFERENCE_IMAGES
        )
        assert kept == [f"/r/{i}.jpg" for i in range(5)]
        assert dropped == ["/r/5.jpg", "/r/6.jpg"]

    def test_dedupes_before_capping(self) -> None:
        kept, dropped = shot_runner.cap_reference_selection(
            ["/r/a.jpg", "/r/a.jpg", "/r/b.jpg"], 5
        )
        assert kept == ["/r/a.jpg", "/r/b.jpg"]
        assert dropped == []

    def test_under_limit_is_noop(self) -> None:
        kept, dropped = shot_runner.cap_reference_selection(["/r/a.jpg"], 5)
        assert kept == ["/r/a.jpg"]
        assert dropped == []

    def test_empty_selection(self) -> None:
        kept, dropped = shot_runner.cap_reference_selection([], 5)
        assert kept == []
        assert dropped == []

    def test_flatten_shots_caps_shot_refs_to_five(self, tmp_path: Path) -> None:
        pid = "cap"
        for i in range(6):
            _plate(tmp_path, pid, "character", f"char{i}.opt.jpg")
        data = {
            "acts": {
                "act1": {
                    "shots": [
                        {
                            "id": "s1",
                            "prompt": "p",
                            "refs": [f"char{i}" for i in range(6)],
                        }
                    ]
                }
            }
        }
        (shot,) = shot_runner.flatten_shots(
            data, tmp_path / "pre-production" / pid
        )
        assert len(shot.refs) == 5
        # The earliest-declared (highest-priority) references survive.
        assert "char0" in Path(shot.refs[0]).name
        # Exactly one over-limit reference is recorded, not silently dropped.
        assert len(shot.dropped_references) == 1
        assert "char5" in Path(shot.dropped_references[0]).name

    def test_flatten_shots_within_limit_drops_nothing(self, tmp_path: Path) -> None:
        pid = "ok"
        for i in range(3):
            _plate(tmp_path, pid, "location", f"loc{i}.opt.jpg")
        data = {
            "acts": {
                "act1": {
                    "shots": [
                        {
                            "id": "s1",
                            "prompt": "p",
                            "refs": [f"loc{i}" for i in range(3)],
                        }
                    ]
                }
            }
        }
        (shot,) = shot_runner.flatten_shots(data, tmp_path / "pre-production" / pid)
        assert len(shot.refs) == 3
        assert shot.dropped_references == []
