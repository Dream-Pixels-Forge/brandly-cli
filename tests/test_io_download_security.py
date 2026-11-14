"""Security tests for ``brandly_cli.io.download_file`` (SSRF hardening, CWE-918).

Provider-controlled media URLs are downloaded to disk, so a malicious or
compromised provider must not be able to point the downloader at loopback,
link-local, RFC1918, cloud-metadata (169.254.169.254), or other reserved
addresses, nor at non-http schemes.

RED-first: these tests exercise the SSRF guard added to :func:`download_file`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from brandly_cli.io import (
    MAX_DOWNLOAD_BYTES,
    _url_resolves_to_private_address,
    download_file,
)

# ---------------------------------------------------------------------------
# _url_resolves_to_private_address — URL classification
# ---------------------------------------------------------------------------


class TestUrlResolvesToPrivateAddress:
    def test_public_url_allowed(self) -> None:
        assert _url_resolves_to_private_address("https://api.agence.ai/video.mp4") is False
        assert _url_resolves_to_private_address("http://example.com/path/file.mp4") is False

    def test_loopback_refused(self) -> None:
        for url in (
            "http://127.0.0.1/",
            "http://localhost:8000/",
            "http://[::1]/",
        ):
            assert _url_resolves_to_private_address(url) is True, url

    def test_link_local_refused(self) -> None:
        assert _url_resolves_to_private_address("http://169.254.169.254/latest/meta-data") is True

    def test_rfc1918_refused(self) -> None:
        for url in (
            "http://10.0.0.1/secret",
            "http://192.168.1.1/",
            "http://172.16.0.1/",
        ):
            assert _url_resolves_to_private_address(url) is True, url

    def test_non_http_scheme_refused(self) -> None:
        for url in ("ftp://evil/x", "file:///etc/passwd", "gopher://internal/"):
            assert _url_resolves_to_private_address(url) is True, url

    def test_unresolvable_host_not_treated_as_private(self) -> None:
        # A host that has no DNS record must not be refused here — httpx will
        # report a connection error on its own. Using an unresolvable domain
        # keeps these tests hermetic (no network).
        assert _url_resolves_to_private_address("https://cdn.example.com/a.png") is False


# ---------------------------------------------------------------------------
# download_file — refusal on non-public URLs
# ---------------------------------------------------------------------------


class TestDownloadFileRefusesSsrf:
    async def _refuses(self, url: str) -> None:
        with pytest.raises(ValueError, match="refusing to download"):
            await download_file(url, Path("/tmp/brandly-sec-test-should-not-exist"))

    def test_private_urls_are_refused(self) -> None:
        for url in (
            "http://127.0.0.1/",
            "http://169.254.169.254/",
            "http://10.0.0.1/",
            "ftp://evil/x",
        ):
            asyncio.run(self._refuses(url))

    def test_download_file_constant_exists(self) -> None:
        assert isinstance(MAX_DOWNLOAD_BYTES, int) and MAX_DOWNLOAD_BYTES > 0
