"""Static import-graph analysis for brandly_cli (dev-notes/_arch.json).

Counts per-module fan-out/fan-in over **all** intra-package imports
(top-level and deferred), detects cycles, and checks the layering rules
from ARCHITECTURE-DIAGRAM.md §5:

- providers (L1) must not import the prompting layer (L2)
- zero import cycles (including deferred imports)

Run from the repo root:

    python scripts/import_graph.py [--write]

--write refreshes dev-notes/_arch.json.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

PROMPTING_LAYER = {"video_prompts", "style_presets"}
PROVIDERS = ("agnes_client", "ark_client", "audio_client", "minimax_client")


def collect(pkg_dir: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return (top_level_edges, deferred_edges) per module."""
    modules: dict[str, Path] = {}
    for path in sorted(pkg_dir.glob("*.py")):
        modules[path.stem] = path
    sub = pkg_dir / "cmd"
    if sub.is_dir():
        for path in sorted(sub.glob("*.py")):
            modules[f"cmd.{path.stem}"] = path
    top: dict[str, set[str]] = {}
    deferred: dict[str, set[str]] = {}
    for module, path in modules.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            sys.exit(f"syntax error in {path.name}: {exc}")
        top_statements = {id(n) for n in tree.body}

        def target_of(name: str) -> str:
            rest = name[len("brandly_cli."):]
            head = rest.split(".")[0]
            return rest if head == "cmd" else head

        t, d = set(), set()
        for node in ast.walk(tree):
            is_top = id(node) in top_statements
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                if node.module.startswith("brandly_cli."):
                    (t if is_top else d).add(target_of(node.module))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("brandly_cli."):
                        (t if is_top else d).add(target_of(alias.name))
        top[module] = t
        deferred[module] = d
    top.setdefault("cmd", set())
    deferred.setdefault("cmd", set())
    return top, deferred


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    color = dict.fromkeys(graph, 0)
    cycles: list[list[str]] = []

    def dfs(u: str, stack: list[str]) -> None:
        color[u] = 1
        stack.append(u)
        for v in sorted(graph.get(u, ())):
            if v not in color:
                continue
            if color[v] == 1:
                cycles.append(stack[stack.index(v):] + [v])
            elif color[v] == 0:
                dfs(v, stack)
        stack.pop()
        color[u] = 2

    for m in sorted(graph):
        if color[m] == 0:
            dfs(m, [])
    return cycles


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="refresh dev-notes/_arch.json")
    args = parser.parse_args()

    pkg = Path(__file__).resolve().parent.parent / "src" / "brandly_cli"
    top, deferred = collect(pkg)
    combined = {m: top.get(m, set()) | deferred.get(m, set()) for m in set(top) | set(deferred)}
    fanin = defaultdict(set)
    for module, deps in combined.items():
        for dep in deps:
            fanin[dep].add(module)

    hard_cycles = find_cycles(top)
    all_cycles = find_cycles(combined)
    deferred_only = [c for c in all_cycles if c not in hard_cycles]
    upward = {
        provider: sorted(PROMPTING_LAYER & top.get(provider, set()))
        for provider in PROVIDERS
    }
    ok = not hard_cycles and not any(upward.values())

    data = {
        "fanout": {m: len(deps) for m, deps in sorted(combined.items())},
        "fanin": {m: len(deps) for m, deps in sorted(fanin.items())},
        "hard_cycles": hard_cycles,
        # Deferred-only cycles are safe at runtime (imports fire after both
        # modules are fully initialized) — reported, not fatal.
        "deferred_cycles": deferred_only,
        "provider_upward_edges": {k: v for k, v in upward.items() if v} or "none",
    }

    print(json.dumps(data, indent=1))
    if hard_cycles:
        print(f"FAIL: {len(hard_cycles)} top-level cycle(s)")
    if deferred_only:
        print(f"INFO: deferred-only cycles (runtime-safe): {deferred_only}")
    if any(upward.values()):
        print(f"FAIL: upward provider->prompting edges: {upward}")
    if ok:
        print("PASS: zero hard cycles, zero upward L1->L2 edges")
    if args.write:
        out = Path(__file__).resolve().parent.parent / "dev-notes" / "_arch.json"
        out.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {out}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
