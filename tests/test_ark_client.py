"""Tests for ark_client BytePlus Ark API client module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from brandly_cli.ark_client import (
    _headers,
    _retry_with_backoff,
    cancel_job,
    create_video_task,
    generate_image,
    get_video_status,
    list_jobs,
    poll_video,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = "test-ark-key-12345"
    monkeypatch.setenv("ARK_API_KEY", key)
    monkeypatch.setenv("ARK_BASE_URL", "https://test-ark.example.com/api/v3")
    return key


def _make_mock_client(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a properly structured mock for httpx.AsyncClient context manager."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    resp.headers = {}

    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    client.get = AsyncMock(return_value=resp)
    client.delete = AsyncMock(return_value=resp)

    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=client)
    mock_context.__aexit__ = AsyncMock(return_value=False)

    return mock_context


# ---------------------------------------------------------------------------
# _headers
# ---------------------------------------------------------------------------


class TestHeaders:
    def test_headers_contains_api_key(self, mock_api_key: str) -> None:
        headers = _headers()
        assert headers["Authorization"] == f"Bearer {mock_api_key}"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_missing_api_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ARK_API_KEY", raising=False)
        with pytest.raises(OSError, match="ARK_API_KEY"):
            _headers()


# ---------------------------------------------------------------------------
# _retry_with_backoff
# ---------------------------------------------------------------------------


class TestRetryWithBackoff:
    async def test_succeeds_on_first_try(self) -> None:
        async def ok_request() -> dict:
            return {"ok": True}

        result = await _retry_with_backoff(ok_request)
        assert result == {"ok": True}

    async def test_retries_on_429(self) -> None:
        call_count = 0

        async def flaky_request() -> dict:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                resp = MagicMock()
                resp.status_code = 429
                resp.headers = {}
                raise httpx.HTTPStatusError(
                    "rate limited", request=MagicMock(), response=resp
                )
            return {"ok": True}

        result = await _retry_with_backoff(flaky_request, max_retries=3, base_delay=0.01)
        assert result == {"ok": True}
        assert call_count == 3

    async def test_raises_after_exhausted_retries(self) -> None:
        async def always_fail() -> None:
            resp = MagicMock()
            resp.status_code = 429
            resp.headers = {}
            raise httpx.HTTPStatusError(
                "rate limited", request=MagicMock(), response=resp
            )

        with pytest.raises(httpx.HTTPStatusError):
            await _retry_with_backoff(always_fail, max_retries=0, base_delay=0.01)


# ---------------------------------------------------------------------------
# generate_image
# ---------------------------------------------------------------------------


class TestGenerateImage:
    async def test_success(self, mock_api_key: str) -> None:
        mock_data = {
            "data": [{"url": "https://cdn.example.com/img.png", "revised_prompt": "better prompt"}]
        }
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _make_mock_client(mock_data)
            result = await generate_image("a cat", model="seedream-4.0", size="16:9")

        assert result["model"] == "seedream-4.0"
        assert "generated_at" in result

    async def test_urls_extracted(self, mock_api_key: str) -> None:
        mock_data = {
            "data": [
                {"url": "https://cdn.example.com/img1.png"},
                {"url": "https://cdn.example.com/img2.png"},
            ]
        }
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _make_mock_client(mock_data)
            result = await generate_image("test", n=2)

        assert result["urls"] == ["https://cdn.example.com/img1.png", "https://cdn.example.com/img2.png"]

    async def test_output_nested_structure(self, mock_api_key: str) -> None:
        mock_data = {
            "output": {"result": {"url": "https://cdn.example.com/nested.png"}}
        }
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _make_mock_client(mock_data)
            result = await generate_image("test")

        assert result["urls"] == ["https://cdn.example.com/nested.png"]


# ---------------------------------------------------------------------------
# create_video_task
# ---------------------------------------------------------------------------


class TestCreateVideoTask:
    async def test_success(self, mock_api_key: str) -> None:
        mock_data = {"id": "task-001", "video_id": "vid-001", "status": "pending", "progress": 0}
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _make_mock_client(mock_data)
            result = await create_video_task("a cat walking", model="seedance-1.0-t2v")

        assert result["task_id"] == "task-001"
        assert result["status"] == "pending"

    async def test_i2v_model(self, mock_api_key: str) -> None:
        mock_data = {"id": "task-002", "status": "pending"}
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _make_mock_client(mock_data)
            await create_video_task(
                "animate this",
                model="seedance-1.0-i2v",
                reference_images=["https://img.example.com/ref.jpg"],
            )

            call_args = mock_ctx.return_value.__aenter__.return_value.post.call_args
            body = call_args.kwargs.get("json") or call_args[1]["json"]
            assert "images" in body
            assert body["images"] == ["https://img.example.com/ref.jpg"]

    async def test_duration_set(self, mock_api_key: str) -> None:
        mock_data = {"id": "task-003", "status": "pending"}
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _make_mock_client(mock_data)
            await create_video_task("test", model="seedance-1.0-t2v", duration=10)

            call_args = mock_ctx.return_value.__aenter__.return_value.post.call_args
            body = call_args.kwargs.get("json") or call_args[1]["json"]
            assert body["duration"] == 10


# ---------------------------------------------------------------------------
# get_video_status
# ---------------------------------------------------------------------------


class TestGetVideoStatus:
    async def test_completed(self, mock_api_key: str) -> None:
        mock_data = {
            "id": "vid-001",
            "video_id": "vid-001",
            "status": "completed",
            "progress": 100,
            "url": "https://cdn.example.com/vid.mp4",
        }
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _make_mock_client(mock_data)
            result = await get_video_status("vid-001")

        assert result["status"] == "completed"
        assert result["url"] == "https://cdn.example.com/vid.mp4"

    async def test_error_field_parsed(self, mock_api_key: str) -> None:
        mock_data = {
            "id": "vid-002",
            "status": "failed",
            "error": {"message": "GPU timeout"},
        }
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _make_mock_client(mock_data)
            result = await get_video_status("vid-002")

        assert result["error"] == "GPU timeout"

    async def test_not_found(self, mock_api_key: str) -> None:
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            resp = MagicMock()
            resp.status_code = 404
            resp.json.return_value = {}
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "not found", request=MagicMock(), response=resp
            )
            resp.headers = {}

            client = AsyncMock()
            client.get = AsyncMock(return_value=resp)
            ctx = MagicMock()
            ctx.__aenter__ = AsyncMock(return_value=client)
            ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx

            result = await get_video_status("vid-missing")

        assert result["status"] == "not_found"


# ---------------------------------------------------------------------------
# poll_video
# ---------------------------------------------------------------------------


class TestPollVideo:
    async def test_completes_on_success(self, mock_api_key: str) -> None:
        calls = [
            {"status": "processing", "progress": 40, "task_id": "vid-001"},
            {"status": "completed", "progress": 100, "url": "https://cdn.example.com/v.mp4"},
        ]

        call_idx = 0

        async def mock_get(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_idx
            data = calls[call_idx]
            call_idx += 1
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = data
            resp.raise_for_status.return_value = None
            resp.headers = {}
            return resp

        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            ctx = MagicMock()
            client = AsyncMock()
            client.get = mock_get
            ctx.__aenter__ = AsyncMock(return_value=client)
            ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.return_value = ctx

            result = await poll_video("vid-001", max_wait_seconds=5, interval_seconds=0.01)

        assert result["status"] == "completed"
        assert "https://cdn.example.com/v.mp4" in result["url"]

    async def test_times_out(self, mock_api_key: str) -> None:
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"status": "processing", "progress": 10}
            resp.raise_for_status.return_value = None
            resp.headers = {}

            client = AsyncMock()
            client.get = AsyncMock(return_value=resp)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(TimeoutError, match="timed out"):
                await poll_video("vid-999", max_wait_seconds=0.05, interval_seconds=0.01)

    async def test_failed_status_raises(self, mock_api_key: str) -> None:
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "status": "failed",
                "error": {"message": "render error"},
            }
            resp.raise_for_status.return_value = None
            resp.headers = {}

            client = AsyncMock()
            client.get = AsyncMock(return_value=resp)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(RuntimeError, match="render error"):
                await poll_video("vid-fail", max_wait_seconds=0.05, interval_seconds=0.01)


# ---------------------------------------------------------------------------
# list_jobs
# ---------------------------------------------------------------------------


class TestListJobs:
    async def test_success(self, mock_api_key: str) -> None:
        mock_data = {"data": [{"id": "vid-001", "status": "completed", "progress": 100}]}
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _make_mock_client(mock_data)
            jobs = await list_jobs(limit=5)

        assert len(jobs) == 1
        assert jobs[0]["task_id"] == "vid-001"

    async def test_empty_list(self, mock_api_key: str) -> None:
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _make_mock_client({"data": []})
            jobs = await list_jobs()
        assert jobs == []

    async def test_api_error_returns_empty(self, mock_api_key: str) -> None:
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(
                side_effect=httpx.HTTPError("network down")
            )
            jobs = await list_jobs()
        assert jobs == []


# ---------------------------------------------------------------------------
# cancel_job
# ---------------------------------------------------------------------------


class TestCancelJob:
    async def test_success(self, mock_api_key: str) -> None:
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            mock_ctx.return_value = _make_mock_client({"status": "cancelled"})
            result = await cancel_job("vid-001")

        assert result["status"] == "cancelled"
        assert result["task_id"] == "vid-001"

    async def test_not_found(self, mock_api_key: str) -> None:
        with patch("brandly_cli.ark_client.httpx.AsyncClient") as mock_ctx:
            resp = MagicMock()
            resp.status_code = 404
            resp.json.return_value = {}
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "not found", request=MagicMock(), response=resp
            )
            resp.headers = {}

            client = AsyncMock()
            client.delete = AsyncMock(return_value=resp)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=client)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await cancel_job("vid-999")
        assert result["status"] == "error"
