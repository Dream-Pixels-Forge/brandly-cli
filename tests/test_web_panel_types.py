"""Contract tests: panel item types must exist and match the server payload.

RED on main: ``CastingPanel.tsx`` and ``DocsPanel.tsx`` imported
``PanelCastItem`` / ``PanelDocItem`` from ``web/src/types.ts``, which never
declared them, so ``tsc`` (``npm run build``) failed with TS2305 and the
``web-quality`` job could not go green.

Verified at the source level, in the repo convention (no JS test runner in CI).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "web" / "src"
TYPES_TS = WEB_SRC / "types.ts"
ROUTES = ROOT / "src" / "brandly_cli" / "web" / "routes"

# A named export in types.ts: `export interface X {`, `export type X =`, …
_EXPORT_RE = re.compile(r"(?m)^export\s+(?:interface|type|enum|const)\s+(\w+)")
# `import type { A, B } from '../../types'` (any relative depth, no .ts suffix)
_IMPORT_RE = re.compile(
    r"import\s+type\s*\{([^}]+)\}\s*from\s*['\"][^'\"]*types['\"]"
)


def _exported_names() -> set[str]:
    return set(_EXPORT_RE.findall(TYPES_TS.read_text(encoding="utf-8")))


def _declared_body(name: str) -> str:
    """Body text of an exported interface/type alias named ``name``."""
    source = TYPES_TS.read_text(encoding="utf-8")
    match = re.search(
        rf"(?ms)^export\s+(?:interface|type)\s+{name}\s*(?:=\s*)?\{{(.*?)^\}}", source
    )
    assert match is not None, f"types.ts must declare `{name}`"
    return match.group(1)


def _server_item_keys(module: str) -> set[str]:
    """JSON keys the route module writes into each listed item."""
    source = (ROUTES / module).read_text(encoding="utf-8")
    return set(re.findall(r'"(\w+)":', source))


class TestTypeImportsResolve:
    def test_every_imported_type_is_exported(self) -> None:
        """Every `import type { X } from '.../types'` must resolve."""
        exported = _exported_names()
        assert exported, "types.ts must export named types"
        checked = 0
        for path in WEB_SRC.rglob("*.ts*"):
            text = path.read_text(encoding="utf-8")
            for raw in _IMPORT_RE.findall(text):
                names = [n.strip() for n in raw.split(",") if n.strip()]
                for name in names:
                    checked += 1
                    assert name in exported, (
                        f"{path.relative_to(ROOT)} imports type '{name}' from types.ts, "
                        f"but types.ts does not export it (TS2305)"
                    )
        assert checked > 0, "no type imports found — the parser is stale"


class TestPanelItemShapes:
    def test_cast_item_matches_server_payload(self) -> None:
        keys = _server_item_keys("cast.py")
        assert {"category", "filename", "size_bytes"} <= keys, keys
        body = _declared_body("PanelCastItem")
        for key in ("category", "filename", "size_bytes"):
            assert re.search(rf"(?m)^\s+{key}\??\s*:", body), (
                f"PanelCastItem must declare `{key}` (emitted by routes/cast.py)"
            )

    def test_doc_item_matches_server_payload(self) -> None:
        keys = _server_item_keys("docs.py")
        assert {"path", "category", "filename", "size_bytes"} <= keys, keys
        body = _declared_body("PanelDocItem")
        for key in ("path", "category", "filename", "size_bytes"):
            assert re.search(rf"(?m)^\s+{key}\??\s*:", body), (
                f"PanelDocItem must declare `{key}` (emitted by routes/docs.py)"
            )
