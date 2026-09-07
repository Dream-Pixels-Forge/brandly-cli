"""Cloud sharing and file upload for finished videos."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Share providers
# ---------------------------------------------------------------------------

class ShareProvider:
    """Base class for cloud storage providers."""

    async def upload(self, file_path: Path) -> dict[str, Any]:
        """Upload file and return share info. Override in subclass."""
        raise NotImplementedError


class LocalShareProvider(ShareProvider):
    """Local filesystem sharing (for testing/local use)."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, file_path: Path) -> dict[str, Any]:
        """Copy file to share directory and return path."""
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}

        # Copy to share directory with timestamp
        import shutil
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = self.base_dir / f"{timestamp}_{file_path.name}"
        shutil.copy2(file_path, dest)

        return {
            "provider": "local",
            "share_url": str(dest),
            "file_size_bytes": dest.stat().st_size,
        }


class S3ShareProvider(ShareProvider):
    """AWS S3 sharing (stub for future implementation)."""

    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.bucket = bucket
        self.region = region

    async def upload(self, file_path: Path) -> dict[str, Any]:
        """Upload to S3 (stub — returns placeholder URL)."""
        # TODO: Implement real S3 upload with boto3
        return {
            "provider": "s3",
            "share_url": f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{file_path.name}",
            "bucket": self.bucket,
            "note": "Stub implementation - S3 upload not yet integrated",
        }


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

PROVIDERS: dict[str, type[ShareProvider]] = {
    "local": LocalShareProvider,
    "s3": S3ShareProvider,
}


async def share_file(
    file_path: Path,
    provider: str = "local",
    *,
    expires_days: int | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Upload file to cloud and return shareable URL.

    Args:
        file_path: Path to the file to share.
        provider: Provider name ("local" or "s3").
        expires_days: Optional expiration in days.
        root: Optional project root.

    Returns:
        Dict with share URL and metadata.
    """
    file_path = Path(file_path)

    if provider not in PROVIDERS:
        return {"error": f"Unknown provider: {provider}. Use: {list(PROVIDERS)}"}
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    # Initialize provider
    if provider == "local":
        if root:
            base_dir = Path(root) / ".brandly" / "shares"
        else:
            base_dir = Path.cwd() / ".brandly" / "shares"
        p = LocalShareProvider(base_dir)
    elif provider == "s3":
        p = S3ShareProvider("default-bucket")
    else:
        return {"error": f"Unsupported provider: {provider}"}

    return await p.upload(file_path)


async def list_providers() -> list[str]:
    """List available share providers."""
    return sorted(PROVIDERS.keys())
