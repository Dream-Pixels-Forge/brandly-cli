import os
import re
import subprocess
from pathlib import Path


def test_frontend_lint_has_no_warnings() -> None:
    result = subprocess.run(
        ["npm.cmd" if os.name == "nt" else "npm", "--prefix", "web", "run", "lint"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    output = result.stdout + result.stderr
    assert not re.search(r"Found [1-9]\d* warnings?", output), output
    assert not re.search(r"Found [1-9]\d* errors?", output), output
