"""Blender integration module — detects installed Blender version.

This module provides:
- Blender version detection (installed on user's computer)
- Blender executable path resolution
- Version-compatible script execution
- 3D spatial reference frame generation for Agnes pipeline
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BlenderVersion:
    """Detected Blender version info."""
    major: int
    minor: int
    patch: int
    raw: str
    path: Path
    render_engine: str  # BLENDER_EEVEE, BLENDER_WORKBENCH, CYCLES


# Common Blender installation paths by OS
BLENDER_PATHS: dict[str, list[str]] = {
    "win32": [
        r"C:\Program Files\Blender Foundation\Blender {version}\blender.exe",
        r"C:\Program Files (x86)\Blender Foundation\Blender {version}\blender.exe",
        r"{appdata}\Blender Foundation\Blender\{version}\blender.exe",
    ],
    "darwin": [
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/Applications/Blender {version}.app/Contents/MacOS/Blender",
    ],
    "linux": [
        "/usr/bin/blender",
        "/usr/local/bin/blender",
        "/snap/bin/blender",
        "{home}/.local/bin/blender",
    ],
}

# Version-to-render-engine mapping
RENDER_ENGINES: dict[int, str] = {
    4: "BLENDER_EEVEE",      # Blender 4.x
    5: "BLENDER_EEVEE",      # Blender 5.x (renamed from BLENDER_EEVEE_NEXT)
}


def _run_blender_version(blender_path: Path) -> str | None:
    """Run blender --version and return output."""
    try:
        result = subprocess.run(
            [str(blender_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _parse_version(version_output: str) -> tuple[int, int, int] | None:
    """Parse Blender version from --version output."""
    for line in version_output.splitlines():
        if "Blender" in line:
            # Format: "Blender 5.1.0"
            parts = line.split()
            if len(parts) >= 2:
                version_str = parts[1]
                nums = version_str.split(".")
                if len(nums) >= 3:
                    return int(nums[0]), int(nums[1]), int(nums[2])
                elif len(nums) == 2:
                    return int(nums[0]), int(nums[1]), 0
    return None


def detect_blender() -> BlenderVersion | None:
    """Detect installed Blender on the system.

    Returns BlenderVersion if found, None otherwise.
    """
    platform = sys.platform
    paths_to_check = BLENDER_PATHS.get(platform, [])

    # Get common version directories to check
    appdata = os.environ.get("APPDATA", "")
    home = os.path.expanduser("~")

    # Try to find any Blender version
    for version in ["5.1", "5.0", "4.4", "4.3", "4.2", "4.1", "4.0", "3.6", "3.5"]:
        for path_template in paths_to_check:
            path_str = path_template.format(
                version=version,
                appdata=appdata,
                home=home,
            )
            blender_path = Path(path_str)

            if blender_path.exists():
                version_output = _run_blender_version(blender_path)
                if version_output:
                    parsed = _parse_version(version_output)
                    if parsed:
                        major, minor, patch = parsed
                        render_engine = RENDER_ENGINES.get(major, "BLENDER_EEVEE")
                        return BlenderVersion(
                            major=major,
                            minor=minor,
                            patch=patch,
                            raw=version_output.strip(),
                            path= blender_path,
                            render_engine=render_engine,
                        )

    # Try system PATH
    try:
        result = subprocess.run(
            ["blender", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            parsed = _parse_version(result.stdout)
            if parsed:
                major, minor, patch = parsed
                render_engine = RENDER_ENGINES.get(major, "BLENDER_EEVEE")
                # Find blender path from which
                which_result = subprocess.run(
                    ["where", "blender"] if sys.platform == "win32" else ["which", "blender"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                path_str = which_result.stdout.strip().splitlines()[0] if which_result.stdout.strip() else "blender"
                return BlenderVersion(
                    major=major,
                    minor=minor,
                    patch=patch,
                    raw=result.stdout.strip(),
                    path=Path(path_str),
                    render_engine=render_engine,
                )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return None


def get_blender_path() -> Path | None:
    """Get the path to the installed Blender executable."""
    version = detect_blender()
    return version.path if version else None


def get_blender_version_string() -> str | None:
    """Get the Blender version as a string (e.g., '5.1.0')."""
    version = detect_blender()
    if version:
        return f"{version.major}.{version.minor}.{version.patch}"
    return None


def is_blender_available() -> bool:
    """Check if Blender is available on the system."""
    return detect_blender() is not None


def run_blender_script(
    script_path: str | Path,
    args: list[str] | None = None,
    background: bool = True,
) -> tuple[bool, str]:
    """Run a Blender script.

    Args:
        script_path: Path to the Python script to run.
        args: Additional arguments to pass after '--'.
        background: Run in background mode (no GUI).

    Returns:
        Tuple of (success, output_message).
    """
    blender_path = get_blender_path()
    if not blender_path:
        return False, "Blender not found on system"

    cmd = [str(blender_path)]
    if background:
        cmd.append("--background")
    cmd.extend(["--python", str(script_path)])
    if args:
        cmd.append("--")
        cmd.extend(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Blender script timed out"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

def print_blender_info():
    """Print detected Blender information."""
    version = detect_blender()
    if version:
        print(f"Blender found: {version.path}")
        print(f"Version: {version.major}.{version.minor}.{version.patch}")
        print(f"Render engine: {version.render_engine}")
    else:
        print("Blender not found on system")


if __name__ == "__main__":
    print_blender_info()
