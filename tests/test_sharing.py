"""Tests for sharing module — cloud export and link sharing."""

from __future__ import annotations

import asyncio
from pathlib import Path

from brandly_cli import sharing


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


class TestShareProviders:
    """Tests for share provider list."""

    def test_list_providers(self) -> None:
        """Returns list of available providers."""
        providers = _run(sharing.list_providers())
        assert "local" in providers
        assert "s3" in providers

    def test_all_providers_defined(self) -> None:
        """All expected providers exist."""
        expected = {"local", "s3"}
        actual = set(sharing.PROVIDERS.keys())
        assert expected == actual


class TestLocalProvider:
    """Tests for local share provider."""

    def test_upload_file(self, tmp_path: Path) -> None:
        """Uploads file to local share directory."""
        src = tmp_path / "video.mp4"
        src.write_bytes(b"fake video content")

        provider = sharing.LocalShareProvider(tmp_path / "shares")
        result = asyncio.run(provider.upload(src))

        assert "error" not in result
        assert result["provider"] == "local"
        assert "share_url" in result
        assert Path(result["share_url"]).exists()

    def test_upload_missing_file(self, tmp_path: Path) -> None:
        """Returns error for missing file."""
        provider = sharing.LocalShareProvider(tmp_path / "shares")
        result = asyncio.run(provider.upload(tmp_path / "missing.mp4"))
        assert "error" in result
        assert "not found" in result["error"].lower()


class TestS3Provider:
    """Tests for S3 share provider (stub)."""

    def test_upload_returns_placeholder(self) -> None:
        """S3 provider returns placeholder URL."""
        provider = sharing.S3ShareProvider("test-bucket")
        result = asyncio.run(provider.upload(Path("/fake/path.mp4")))
        assert result["provider"] == "s3"
        assert "share_url" in result
        assert "Stub" in result.get("note", "")


class TestShareFile:
    """Tests for share_file function."""

    def test_share_local_file(self, tmp_path: Path) -> None:
        """Shares a local file successfully."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"test content")

        result = _run(sharing.share_file(video, provider="local", root=tmp_path))
        assert "error" not in result
        assert "share_url" in result

    def test_share_invalid_provider(self, tmp_path: Path) -> None:
        """Returns error for invalid provider."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"test")
        result = _run(sharing.share_file(video, provider="invalid"))
        assert "error" in result

    def test_share_missing_file(self, tmp_path: Path) -> None:
        """Returns error for missing file."""
        result = _run(sharing.share_file(tmp_path / "missing.mp4"))
        assert "error" in result
        assert "not found" in result["error"].lower()
