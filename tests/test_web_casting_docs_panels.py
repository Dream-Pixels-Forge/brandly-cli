"""Contract tests for the Casting and Project Docs web panels.

User request: "casting display image of cast and sheet and docs display
all documents generated". Design: ``dev-notes/DESIGN-CASTING-DOCS-PANELS.md``.

Source-contract tests read the ``.tsx`` sources (no JS test runner in CI —
see #61); the route tests exercise the real FastAPI app against a fixture
project, including the path-safety refusals mandated by the design.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from brandly_cli.web.server import create_app

WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"
PANELS_DIR = WEB_SRC / "components" / "panels"

CAST_CATEGORIES = ("character", "wardrobe")


# ---------------------------------------------------------------------------
# Frontend source contract
# ---------------------------------------------------------------------------


def _read(rel: str) -> str:
    return (WEB_SRC / rel).read_text(encoding="utf-8")


class TestPanelRegistration:
    def test_panelkind_includes_casting_and_docs(self) -> None:
        types = _read("types.ts")
        assert "'casting'" in types, "PanelKind is missing 'casting'"
        assert "'docs'" in types, "PanelKind is missing 'docs'"

    def test_labels_registered(self) -> None:
        labels = _read("panelLabels.ts")
        assert "casting:" in labels, "PANEL_LABELS is missing 'casting'"
        assert "docs:" in labels, "PANEL_LABELS is missing 'docs'"
        assert "'Casting'" in labels
        assert "'Project Docs'" in labels

    def test_shortcuts_registered_without_collisions(self) -> None:
        labels = _read("panelLabels.ts")
        assert "'B'" in labels, "PANEL_SHORTCUTS is missing casting shortcut 'B'"
        assert "'D'" in labels, "PANEL_SHORTCUTS is missing docs shortcut 'D'"
        # No two panels may share a shortcut chip.
        chips = [
            match.group(1)
            for match in re.finditer(r"'([A-Z])'", labels)
        ]
        assert len(chips) == len(set(chips)), f"shortcut collision: {chips}"

    def test_sidebar_nav_registers_rows(self) -> None:
        nav = _read("SidebarNav.tsx")
        assert "'casting'" in nav, "SidebarNav is missing the Casting row"
        assert "'docs'" in nav, "SidebarNav is missing the Project Docs row"

    def test_shell_maps_both_panels(self) -> None:
        shell = _read("Shell.tsx")
        assert "CastingPanel" in shell, "Shell.tsx does not map CastingPanel"
        assert "DocsPanel" in shell, "Shell.tsx does not map DocsPanel"

    def test_panel_components_exist(self) -> None:
        assert (PANELS_DIR / "CastingPanel.tsx").is_file()
        assert (PANELS_DIR / "DocsPanel.tsx").is_file()


class TestDataHonesty:
    def test_casting_panel_has_empty_state_and_no_fabricated_data(self) -> None:
        src = (PANELS_DIR / "CastingPanel.tsx").read_text(encoding="utf-8")
        assert "No cast images yet" in src, (
            "CastingPanel must show an honest empty state"
        )
        # No hardcoded placeholder plates (data honesty: only server data).
        assert "Sample" not in src and "sample_" not in src
        assert "Lorem" not in src

    def test_docs_panel_has_empty_state_and_no_fabricated_data(self) -> None:
        src = (PANELS_DIR / "DocsPanel.tsx").read_text(encoding="utf-8")
        assert "No documents yet" in src, "DocsPanel must show an honest empty state"
        assert "Sample" not in src and "sample_" not in src

    def test_panels_fetch_via_authenticated_urls(self) -> None:
        casting = (PANELS_DIR / "CastingPanel.tsx").read_text(encoding="utf-8")
        docs = (PANELS_DIR / "DocsPanel.tsx").read_text(encoding="utf-8")
        assert "/cast" in casting, "CastingPanel must call the cast API"
        assert "withToken" in casting, "CastingPanel must authenticate its fetches"
        assert "/docs" in docs, "DocsPanel must call the docs API"
        assert "withToken" in docs, "DocsPanel must authenticate its fetches"


# ---------------------------------------------------------------------------
# Backend fixtures
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path, project_id: str = "proj-cast") -> Path:
    root = tmp_path
    proj_dir = root / ".brandly" / project_id
    (proj_dir / "docs" / "plan").mkdir(parents=True, exist_ok=True)
    (proj_dir / "project.json").write_text("{}", encoding="utf-8")
    return root


def _write_cast_images(tmp_path: Path, project_id: str = "proj-cast") -> None:
    # v2 media root: pre-production/<id>/<category>/
    media_root = tmp_path / "pre-production" / project_id
    (media_root / "character").mkdir(parents=True, exist_ok=True)
    (media_root / "wardrobe").mkdir(parents=True, exist_ok=True)
    (media_root / "character" / "char_maya_001.png").write_bytes(b"fake-png-maya")
    (media_root / "wardrobe" / "ward_maya_evening_001.jpg").write_bytes(b"fake-jpg-ward")
    # hq/ masters must never leak into the panel (issue #208 rule).
    (media_root / "character" / "hq").mkdir(parents=True, exist_ok=True)
    (media_root / "character" / "hq" / "char_maya_master.png").write_bytes(b"hq")


def _write_docs(tmp_path: Path, project_id: str = "proj-cast") -> None:
    docs = tmp_path / ".brandly" / project_id / "docs"
    (docs / "plan").mkdir(parents=True, exist_ok=True)
    (docs / "tmp").mkdir(parents=True, exist_ok=True)
    (docs / "plan" / "production-bible.md").write_text(
        "# Production Bible\n\nAct I.", encoding="utf-8"
    )
    (docs / "tmp" / "notes.md").write_text("working notes", encoding="utf-8")


@pytest.fixture()
def client(tmp_path: Path):
    _make_project(tmp_path)
    _write_cast_images(tmp_path)
    _write_docs(tmp_path)
    with TestClient(create_app(root=str(tmp_path))) as c:
        yield c, tmp_path


# ---------------------------------------------------------------------------
# Cast routes
# ---------------------------------------------------------------------------


class TestCastRoutes:
    def test_cast_lists_real_items(self, client) -> None:
        c, _ = client
        res = c.get("/api/projects/proj-cast/cast")
        assert res.status_code == 200
        items = res.json()["items"]
        names = {item["filename"] for item in items}
        assert "char_maya_001.png" in names
        assert "ward_maya_evening_001.jpg" in names

    def test_cast_excludes_hq_masters(self, client) -> None:
        c, _ = client
        items = c.get("/api/projects/proj-cast/cast").json()["items"]
        assert all("hq" not in item["filename"] for item in items)
        assert all(item["category"] in CAST_CATEGORIES for item in items)

    def test_cast_items_report_size_bytes(self, client) -> None:
        c, _ = client
        items = c.get("/api/projects/proj-cast/cast").json()["items"]
        maya = next(i for i in items if i["filename"] == "char_maya_001.png")
        assert maya["size_bytes"] == len(b"fake-png-maya")

    def test_cast_media_serves_image_bytes(self, client) -> None:
        c, _ = client
        res = c.get("/api/projects/proj-cast/cast/media/character/char_maya_001.png")
        assert res.status_code == 200
        assert res.content == b"fake-png-maya"

    def test_cast_media_rejects_path_traversal(self, client) -> None:
        c, _ = client
        res = c.get("/api/projects/proj-cast/cast/media/character/..%2Fsecret.png")
        assert res.status_code == 404

    def test_cast_media_rejects_unknown_category(self, client) -> None:
        c, _ = client
        res = c.get("/api/projects/proj-cast/cast/media/prop/char_maya_001.png")
        assert res.status_code == 404

    def test_cast_unknown_project_404(self, client) -> None:
        c, _ = client
        res = c.get("/api/projects/nope/cast")
        assert res.status_code == 404

    def test_cast_empty_project_returns_no_items(self, tmp_path: Path) -> None:
        _make_project(tmp_path, "empty-proj")
        with TestClient(create_app(root=str(tmp_path))) as c:
            res = c.get("/api/projects/empty-proj/cast")
            assert res.status_code == 200
            assert res.json()["items"] == []

    def test_cast_falls_back_to_legacy_tree(self, tmp_path: Path) -> None:
        _make_project(tmp_path, "legacy-proj")
        legacy = tmp_path / ".brandly" / "legacy-proj" / "images" / "character"
        legacy.mkdir(parents=True)
        (legacy / "char_old_001.png").write_bytes(b"legacy-bytes")
        with TestClient(create_app(root=str(tmp_path))) as c:
            items = c.get("/api/projects/legacy-proj/cast").json()["items"]
            assert [i["filename"] for i in items] == ["char_old_001.png"]


# ---------------------------------------------------------------------------
# Docs routes
# ---------------------------------------------------------------------------


class TestDocsRoutes:
    def test_docs_lists_all_categories(self, client) -> None:
        c, _ = client
        res = c.get("/api/projects/proj-cast/docs")
        assert res.status_code == 200
        items = res.json()["items"]
        by_path = {item["path"]: item for item in items}
        assert "plan/production-bible.md" in by_path
        assert "tmp/notes.md" in by_path  # "all documents generated" — tmp included

    def test_docs_items_report_size(self, client) -> None:
        c, _ = client
        items = c.get("/api/projects/proj-cast/docs").json()["items"]
        bible = next(i for i in items if i["filename"] == "production-bible.md")
        assert bible["size_bytes"] == len("# Production Bible\n\nAct I.")

    def test_docs_content_returns_text(self, client) -> None:
        c, _ = client
        res = c.get(
            "/api/projects/proj-cast/docs/content",
            params={"path": "plan/production-bible.md"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["content"] == "# Production Bible\n\nAct I."
        assert body["truncated"] is False
        assert body["category"] == "plan"

    def test_docs_content_rejects_escape(self, client) -> None:
        c, _ = client
        res = c.get(
            "/api/projects/proj-cast/docs/content",
            params={"path": "../../project.json"},
        )
        assert res.status_code == 404

    def test_docs_content_rejects_absolute_path(self, client) -> None:
        c, _ = client
        res = c.get(
            "/api/projects/proj-cast/docs/content",
            params={"path": "/etc/passwd"},
        )
        assert res.status_code == 404

    def test_docs_content_unknown_path_404(self, client) -> None:
        c, _ = client
        res = c.get(
            "/api/projects/proj-cast/docs/content",
            params={"path": "plan/nope.md"},
        )
        assert res.status_code == 404

    def test_docs_unknown_project_404(self, client) -> None:
        c, _ = client
        res = c.get("/api/projects/nope/docs")
        assert res.status_code == 404

    def test_docs_empty_project_returns_no_items(self, tmp_path: Path) -> None:
        _make_project(tmp_path, "empty-docs")
        with TestClient(create_app(root=str(tmp_path))) as c:
            res = c.get("/api/projects/empty-docs/docs")
            assert res.status_code == 200
            assert res.json()["items"] == []


# ---------------------------------------------------------------------------
# Server wiring
# ---------------------------------------------------------------------------


class TestServerWiring:
    def test_routes_registered_in_server(self) -> None:
        server_src = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "brandly_cli"
            / "web"
            / "server.py"
        ).read_text(encoding="utf-8")
        assert "cast" in server_src, "server.py must register the cast router"
        assert "docs" in server_src, "server.py must register the docs router"


@pytest.mark.parametrize("project_id", ["proj-cast"])
def test_smoke_docs_and_cast_alive(client, project_id: str) -> None:
    c, _ = client
    assert c.get(f"/api/projects/{project_id}/cast").status_code == 200
    assert c.get(f"/api/projects/{project_id}/docs").status_code == 200
